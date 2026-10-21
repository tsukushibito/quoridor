"""R1 deterministic ancestor-loss/reparent boundary only; no engines or Beads."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
SOURCE = Path(__file__).resolve().parents[2]


def module(name, path):
    loader = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(loader)
    sys.modules[name] = value
    loader.loader.exec_module(value)
    return value


lc = module("cohort_coverage_lc", SOURCE / "scripts/dev/research-lifecycle.py")
lc.process = module(
    "quoridor_runtime.cohort_coverage_process",
    SOURCE / "shared/python/quoridor_runtime/cycle_process.py",
)
fixture = module("cohort_coverage_fixture", ROOT / "tools/research-session/test_cohort_control.py")
fixture.lc = lc


class ObservedCohortCoverageTests(fixture.MetadataFixture, unittest.TestCase):
    def test_reparented_observed_native_is_charged_or_refused_without_another_scan(self):
        self.setup_metadata()
        for info in self.processes.values():
            info.update(group=info["pid"], rss=1024**2)
        for lane, (member, cfg) in enumerate(
            zip(self.cohort["members"], self.children, strict=True)
        ):
            runtime = Path(member["job_runtime"])
            fixture.fresh_file(runtime / "config.json", cfg)
            fixture.j.write(
                runtime,
                "state.json",
                dict(
                    job_id=f"starting-{lane}",
                    issue="work",
                    thread_id="target",
                    config_sha256=lc.sha(json.dumps(cfg, sort_keys=True).encode()),
                    supervisor=self.controller,
                    child=None,
                    phase="starting",
                ),
            )
        guardian = dict(pid=400, start_ticks="guardian", boot_id="boot")
        native = dict(pid=500, start_ticks="native", boot_id="boot")
        # members(R) saw G/N, but G exited before the exact per-PID reread;
        # N remains alive with the same identity, its own group, and PPID1.
        self.processes[500] = dict(native, parent=1, group=500, state="S", rss=64 * 1024**2)
        self.processes[999] = dict(
            pid=999,
            start_ticks="foreign",
            boot_id="boot",
            parent=1,
            group=999,
            state="S",
            rss=2 * 1024**3,
        )
        observed = [self.supervisor, self.controller, guardian, native]
        calls = []

        def members(root, known):
            calls.append(root)
            self.assertEqual(root, self.supervisor)
            return observed

        spec = dict(arena_cohort=self.cohort_ref, limits=dict(host_reserve_B=4294967296))
        key = tuple(native[k] for k in ("pid", "start_ticks", "boot_id"))
        foreign = tuple(self.processes[999][k] for k in ("pid", "start_ticks", "boot_id"))
        with (
            patch.object(lc, "arena_cohort", return_value=(self.cohort, self.cohort["members"][0])),
            patch.object(lc.process, "members", side_effect=members),
            patch.object(lc.process, "available_memory", return_value=32 * 1024**3),
        ):
            resources = lc.ArenaCohortResources(
                spec, outer_runtime=self.cohort["members"][0]["job_runtime"]
            )
            self.assertEqual(len(calls), 1)
            facts = resources.check()
            self.assertEqual(len(calls), 2)
            self.assertIn(key, facts["all_members"])
            self.assertIn(key, facts["common_members"])
            inner = set().union(*(set(m) for m in facts["inner_members"].values()))
            self.assertFalse(inner & facts["common_members"].keys())
            self.assertEqual(set(facts["all_members"]), set(facts["common_members"]) | inner)
            self.assertNotIn(foreign, facts["all_members"])
            # The same observed reparented identity must trigger the real common
            # cap, rather than vanish from both charged lists.
            self.processes[500]["rss"] = 2 * 1024**3
            with self.assertRaisesRegex(lc.process.CycleStopped, "memory_limit"):
                resources.check()
            self.assertEqual(len(calls), 3)
            # An observed PID reused before the exact reread grants no ownership
            # of the new foreign identity and no credit for the old one.
            self.processes[500]["start_ticks"] = "reused"
            facts = resources.check()
            self.assertEqual(len(calls), 4)
            self.assertNotIn(key, facts["all_members"])
            self.assertFalse(any(v["pid"] == 500 for v in facts["all_members"].values()))
        print(
            json.dumps(
                dict(
                    observed_native_reparented=True,
                    dead_intermediate=True,
                    covered_by_total_and_conservative_common=True,
                    disjoint_charged_union=True,
                    real_common_cap_refuses=True,
                    foreign_and_reused_identity_excluded=True,
                    owned_parent_scan_per_check=1,
                    new_game_model_RAW_DB_calls=0,
                )
            ),
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
