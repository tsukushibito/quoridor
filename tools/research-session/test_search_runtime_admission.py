"""New timed cohort/CPU reachability only; old fixture assertions never run."""

import copy
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path("/workspaces/quoridor")
SOURCE = Path(os.environ["ARENA_361_LIFECYCLE"])
loader = importlib.util.spec_from_file_location("search_runtime_v2", SOURCE)
lc = importlib.util.module_from_spec(loader)
sys.modules[loader.name] = lc
loader.loader.exec_module(lc)
loader = importlib.util.spec_from_file_location(
    "existing_cohort_fixture", ROOT / "tools/research-session/test_lifecycle_arena_cohort.py"
)
existing = importlib.util.module_from_spec(loader)
loader.loader.exec_module(existing)
existing.lc = lc


class SearchRuntimeBoundary(unittest.TestCase):
    def test_managed_search_short_lanes_keep_actual_cpu_ram_and_holding(self):
        fixture = existing.ArenaCohortBoundary()
        fixture.setUp()  # Metadata construction only; no old test body.
        self.addCleanup(fixture.doCleanups)
        for lane, settings in enumerate(fixture.settings):
            item = fixture.specs[lane]
            config = lc.document(lc.document(item["experiment"])["config"])
            config.update(workers=1, active_games=1, max_batch=1, inference_cpu_core=None)
            config["arena"]["comparison"] = "search_wall_time"
            config_ref = fixture.save(fixture.root / f"lane-{lane}/new-config.json", config)
            experiment = dict(phase="arena", config=config_ref)
            experiment_ref = fixture.save(
                fixture.root / f"lane-{lane}/new-experiment.json", experiment
            )
            count = (11, 11, 10)[lane]
            settings["runs"] = settings["runs"][:count]
            for run in settings["runs"]:
                run["experiment"] = experiment_ref
            member = fixture.cohort["members"][lane]
            member["settings_body_sha256"] = lc.canonical_sha(
                {k: v for k, v in settings.items() if k != "arena_cohort"}
            )
            item.update(
                experiment=experiment_ref,
                child_cpu_cores=[*member["AI_workers"], member["main_cpu"]],
            )
        cohort_ref = fixture.save(fixture.shared / "short-cohort.json", fixture.cohort)
        for lane, settings in enumerate(fixture.settings):
            settings["arena_cohort"] = cohort_ref
            item = fixture.specs[lane]
            item.update(
                settings=fixture.save(
                    Path(fixture.cohort["members"][lane]["settings_path"]), settings
                ),
                arena_cohort=cohort_ref,
            )
            self.assertEqual(lc.arena_cohort(item)[1]["lane"], lane)
            self.assertEqual(lc.arena_cpu_cores(item), item["child_cpu_cores"])
            bad = copy.deepcopy(item)
            bad["child_cpu_cores"] = [0, 2, 4]
            with self.assertRaisesRegex(lc.Refused, "actual native launch affinity"):
                lc.arena_cpu_cores(bad)
            bad = copy.deepcopy(item)
            bad["limits"]["family_B"] -= 1
            with self.assertRaises(lc.Refused):
                lc.arena_cpu_cores(bad)
            bad = copy.deepcopy(item)
            bad["limits"]["owned_B"] += 1
            with self.assertRaises(lc.Refused):
                lc.arena_cohort(bad)

    def test_experiment_check_reaches_search_managed_cpu_guard(self):
        reference = dict(path="/synthetic/metadata", sha256="a" * 64, bytes=2)
        artifact = dict(path="/synthetic/runner", sha256="b" * 64, bytes=1)
        experiment = dict(
            schema=lc.EXPERIMENT_SCHEMA,
            phase="arena",
            config=reference,
            inputs=[],
            models=[],
            schedule=reference,
            build_manifest=reference,
            dynamic_libraries=[],
            planned_slots=32,
            argv=[artifact["path"], "arena"],
        )
        spec = dict(experiment=reference, artifact=artifact, approved_plan=reference)

        class ReachedCpuGuard(Exception):
            pass

        with (
            patch.object(lc, "charged_roots"),
            patch.object(
                lc,
                "document",
                side_effect=[
                    experiment,
                    {"arena": {"comparison": "search_wall_time"}, "management_cpu_core": 6},
                ],
            ),
            patch.object(lc, "experiment_phase_check"),
            patch.object(lc, "accepted_build", return_value={"artifact": artifact}),
            patch.object(lc, "caller_source_refs", return_value=[]),
            patch.object(lc, "read_ref", return_value=b"{}"),
            patch.object(lc, "approved_plan", return_value={}),
            patch.object(lc, "arena_plan_check"),
            patch.object(lc, "arena_cpu_cores", side_effect=ReachedCpuGuard) as cpu_guard,
        ):
            with self.assertRaises(ReachedCpuGuard):
                lc.experiment_check(spec)
        cpu_guard.assert_called_once_with(spec)


if __name__ == "__main__":
    unittest.main()
