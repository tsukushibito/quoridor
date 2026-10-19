"""New accounting inlet race boundary only; no engines, archives or DB."""

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
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


lc = module("resource_snapshot_lc", SOURCE / "scripts/dev/research-lifecycle.py")
fixture = module(
    "resource_snapshot_fixture", ROOT / "tools/research-session/test_cohort_control.py"
)
fixture.lc = lc


class ResourceStateSnapshotTests(fixture.MetadataFixture, unittest.TestCase):
    def test_accounting_reads_atomic_coherent_snapshots_and_keeps_normal_refusals(self):
        self.setup_metadata()
        states = {}
        for member, cfg in zip(self.cohort["members"], self.children, strict=True):
            runtime = Path(member["job_runtime"])
            fixture.fresh_file(runtime / "config.json", cfg)
            state = dict(
                job_id=f"actual-lane-{member['lane']}",
                issue="work",
                thread_id="target",
                config_sha256=lc.sha(json.dumps(cfg, sort_keys=True).encode()),
                supervisor=self.controller,
                child=None,
                phase="starting",
            )
            states[runtime / "state.json"] = state
            fixture.j.write(runtime, "state.json", state)
        peer = self.cohort["members"][1]
        peer_state_path = Path(peer["job_runtime"]) / "state.json"
        peer_state = dict(
            states[peer_state_path],
            supervisor=dict(pid=201, start_ticks="21", boot_id="boot"),
            child=dict(pid=202, start_ticks="22", boot_id="boot"),
        )
        self.processes[201] = dict(peer_state["supervisor"], parent=101, state="S", rss=1000)
        self.processes[202] = dict(peer_state["child"], parent=201, state="S", rss=1000)
        states[peer_state_path] = peer_state
        fixture.j.write(peer_state_path.parent, "state.json", peer_state)
        inner_path = Path(peer["output"]) / "run-000/runtime/state.json"
        inner_path.parent.mkdir(parents=True)
        states[inner_path] = dict(job_id="inner-not-started", child=None)
        fixture.j.write(inner_path.parent, "state.json", states[inner_path])
        states[self.state_path] = self.state
        actual_bound = lc.bound
        reads = []

        def replace_after_read(path, *args, **kwargs):
            value = actual_bound(path, *args, **kwargs)
            if Path(path) in states:
                old = json.loads(value[1])
                reads.append(str(path))
                fixture.j.write(
                    Path(path).parent, "state.json", dict(old, updated_at=f"refresh-{len(reads)}")
                )
            return value

        spec = dict(arena_cohort=self.cohort_ref)
        own_runtime = self.cohort["members"][0]["job_runtime"]

        def check():
            return lc.arena_cohort_lifetime(spec, outer_runtime=own_runtime)

        with (
            patch.object(lc, "arena_cohort", return_value=(self.cohort, self.cohort["members"][0])),
            patch.object(
                lc.process, "members", side_effect=lambda root, known: [self.processes[root["pid"]]]
            ),
        ):
            with patch.object(lc, "bound", side_effect=replace_after_read):
                facts = check()
                self.assertIn(1, facts["origins"])
                # Eight outer snapshots, one inner, one parent, one own-role read.
                self.assertEqual(len(reads), 11)
                self.assertEqual(set(reads), {str(p) for p in states})
            for changed in (
                dict(peer_state, issue="wrong-issue"),
                dict(peer_state, thread_id="wrong-thread"),
                dict(peer_state, config_sha256="wrong-config"),
            ):
                fixture.j.write(peer_state_path.parent, "state.json", changed)
                with self.assertRaisesRegex(lc.Refused, "actual original outer job/config/runtime"):
                    check()
            fixture.j.write(peer_state_path.parent, "state.json", peer_state)
            # Wrong actual supervisor still fails the resource owner's exact identity.
            own_path = Path(own_runtime) / "state.json"
            fixture.j.write(
                own_path.parent, "state.json", dict(states[own_path], supervisor=self.supervisor)
            )
            with self.assertRaisesRegex(lc.Refused, "exact declared outer supervisor"):
                check()
            fixture.j.write(own_path.parent, "state.json", states[own_path])
            malformed = peer_state_path.with_suffix(".tmp")
            malformed.write_text("{")
            malformed.replace(peer_state_path)
            with self.assertRaises(json.JSONDecodeError):
                check()
            fixture.j.write(peer_state_path.parent, "state.json", peer_state)
            # Immutable normal config still uses hash-bound rereads and refuses drift.
            config_path = Path(peer["job_runtime"]) / "config.json"

            def replace_immutable(path, *args, **kwargs):
                value = actual_bound(path, *args, **kwargs)
                if Path(path) == config_path:
                    fixture.j.write(
                        config_path.parent, "config.json", dict(self.children[1], issue="foreign")
                    )
                return value

            with patch.object(lc, "bound", side_effect=replace_immutable):
                with self.assertRaisesRegex(lc.Refused, "reference drift"):
                    check()
        print(
            json.dumps(
                dict(
                    healthy_atomic_state_replacements=11,
                    live_state_paths=10,
                    fail_closed=[
                        "wrong-issue",
                        "wrong-thread",
                        "wrong-config",
                        "wrong-supervisor",
                        "malformed-state",
                        "immutable-config-drift",
                    ],
                    native_archive_model_DB_calls=0,
                )
            ),
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
