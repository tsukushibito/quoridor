"""Only new metadata/lease/peer/progress boundaries; no model/native/arena calls."""

import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/dev/research-lifecycle.py"
spec = importlib.util.spec_from_file_location("cohort_boundary_target", SOURCE)
lc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lc
spec.loader.exec_module(lc)
lc.ROOT = Path("/workspaces/quoridor")


class ArenaCohortBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.shared = self.root / "shared"
        self.shared.mkdir()
        artifact = self.save(
            self.shared / "unit-artifact.json", {"fixture": "metadata only, not executable"}
        )
        self.cohort = dict(
            schema="quoridor.research.arena-cohort.v1",
            owner=str(self.root),
            issue="unit-issue",
            thread_id="unit-thread",
            artifact=artifact,
            global_controller_cpu=0,
            global_controller_B=256 * 1024**2,
            shared_storage_B=1024**2,
            shared_roots=[str(self.shared)],
            control_root=str(self.shared),
            notify=dict(thread_id="unit-inert", issue="unit-inert"),
            members=[],
        )
        support = self.save(
            self.shared / "support.json",
            dict(
                resources=dict(
                    CPU=10,
                    GPU=0,
                    threads=1,
                    controller_included=True,
                    family_RAM_B=3 * 3 * 1024**3 + 256 * 1024**2,
                    host_reserve_B=4 * 1024**3,
                ),
                storage_budget=dict(whole_B=4 * 1024**2, roots=[str(self.root)]),
            ),
        )
        self.cohort["support"] = support
        self.settings = []
        self.specs = []
        for lane, cores in enumerate(([2, 4, 6], [8, 10, 12], [14, 16, 18])):
            root = self.root / f"lane-{lane}"
            root.mkdir()
            output = root / "execution"
            config = self.save(
                root / "config.json",
                dict(
                    cpu_cores=cores[:2],
                    management_cpu_core=cores[2],
                    arena=dict(comparison="whole_wall_time"),
                    max_memory_bytes=3 * 1024**3 - 64 * 1024**2,
                ),
            )
            experiment = self.save(root / "experiment.json", dict(phase="arena", config=config))
            limits = dict(
                family_B=3 * 1024**3,
                controller_B=64 * 1024**2,
                owned_B=1024**2,
                worker_cpu=cores[0],
                guardian_cpu=cores[2],
                host_reserve_B=4 * 1024**3,
                log_B=65536,
            )
            template = dict(
                kind="run",
                owner=str(self.root),
                cwd=str(lc.ROOT),
                limits=limits,
                support=support,
                artifact=artifact,
                caller_sources=[],
                approved_plan=None,
                data_root=str(root / "data"),
                data=[],
                finalizers=[],
                env={},
                experiment=experiment,
                owned_outputs=[str(root)],
                argv=[artifact["path"], "arena"],
            )
            settings = dict(
                kind="sequence",
                arena_lane=lane,
                output=str(output),
                runs=[copy.deepcopy(template) for _ in range(32)],
            )
            settings_path = root / "settings.json"
            member = dict(
                lane=lane,
                AI_workers=cores[:2],
                main_cpu=cores[2],
                family_B=limits["family_B"],
                storage_B=limits["owned_B"],
                roots=[str(root)],
                output=str(output),
                settings_path=str(settings_path),
                job_runtime=str(root / "outer-runtime"),
                settings_body_sha256=lc.canonical_sha(settings),
            )
            self.cohort["members"].append(member)
            self.settings.append(settings)
            self.specs.append(copy.deepcopy(template))
        self.cohort_ref = self.save(self.shared / "cohort.json", self.cohort)
        for lane, (settings, item) in enumerate(zip(self.settings, self.specs, strict=True)):
            settings["arena_cohort"] = self.cohort_ref
            path = Path(self.cohort["members"][lane]["settings_path"])
            settings_ref = self.save(path, settings)
            phase = Path(settings["output"]) / "run-000"
            item.update(
                settings=settings_ref,
                selection_index=0,
                arena_cohort=self.cohort_ref,
                output=str(phase / "operation"),
                TMP=str(phase / "TMP"),
            )

    @staticmethod
    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n")
        return lc.bound(path)[0]

    def test_frozen_lanes_and_all_three_holding_partitions(self):
        for lane in range(3):
            self.assertEqual(lc.arena_cohort(self.specs[lane])[1]["lane"], lane)
        changed = copy.deepcopy(self.specs[0])
        changed["output"] += "-alias"
        with self.assertRaisesRegex(lc.Refused, "namespace"):
            lc.arena_cohort(changed)
        changed = copy.deepcopy(self.specs[0])
        changed["limits"]["owned_B"] += 1
        with self.assertRaises(lc.Refused):
            lc.arena_cohort(changed)
        settings_path = Path(self.cohort["members"][0]["settings_path"])
        value = copy.deepcopy(self.settings[0])
        value["runs"][7]["limits"]["family_B"] += 1
        changed = copy.deepcopy(self.specs[0])
        changed["settings"] = self.save(settings_path, value)
        with self.assertRaisesRegex(lc.Refused, "frozen lane"):
            lc.arena_cohort(changed)
        # A single-lane forecast cannot issue three simultaneous envelopes.
        cohort = copy.deepcopy(self.cohort)
        cohort["members"][2]["storage_B"] += 1024**2
        bad_ref = self.save(self.shared / "overlapping-whole.json", cohort)
        with patch.object(
            lc,
            "document",
            side_effect=lambda r: cohort if r == self.cohort_ref else lc.json.loads(lc.read_ref(r)),
        ):
            # Lane1's body is intact; the aggregate is now larger than its support.
            with self.assertRaisesRegex(lc.Refused, "simultaneous holdings"):
                lc.arena_cohort(self.specs[1])
        self.assertNotEqual(bad_ref, self.cohort_ref)

    def test_shared_source_readers_exclude_writer_and_same_lane_duplicate(self):
        self.save(self.shared / "start.json", dict(cohort=self.cohort_ref))
        with (
            patch.object(lc, "LEASE", self.root / "source.lock"),
            patch.object(lc, "ArenaCohortResources"),
        ):
            with lc.operation_lease(self.specs[0], lc.lease):
                with lc.operation_lease(self.specs[1], lc.lease):
                    with self.assertRaises(BlockingIOError):
                        with lc.lease():
                            self.fail("writer entered active readers")
                    with self.assertRaises(BlockingIOError):
                        with lc.operation_lease(self.specs[0], lc.lease):
                            self.fail("duplicate lane entered")
            with lc.lease():
                pass
        calls = []

        @contextmanager
        def ordinary():
            calls.append("exclusive-default")
            yield

        with lc.operation_lease({}, ordinary):
            pass
        self.assertEqual(calls, ["exclusive-default"])

    def test_exact_current_native_guard_matches_each_lane_without_RAM_fallback(self):
        for item in self.specs:
            self.assertIsNotNone(lc.arena_cohort(item))
            changed = copy.deepcopy(item)
            changed["limits"]["guardian_cpu"] += 1
            # Bind changed settings too, so refusal is the actual CPU/resource tuple.
            lane = self.settings[self.specs.index(item)]["arena_lane"]
            current = copy.deepcopy(self.settings[lane])
            current["runs"][0]["limits"] = changed["limits"]
            expected = copy.deepcopy(self.cohort)
            expected["members"][lane]["settings_body_sha256"] = lc.canonical_sha(
                {k: v for k, v in current.items() if k != "arena_cohort"}
            )
            changed["settings"] = self.save(
                Path(current["output"]).parent / "settings.json", current
            )
            original_document = lc.document
            with patch.object(
                lc,
                "document",
                side_effect=lambda r: expected if r == self.cohort_ref else original_document(r),
            ):
                with self.assertRaisesRegex(lc.Refused, "engine/resource"):
                    lc.arena_cohort(changed)
            # Restore the original fixture custody for the next independent lane.
            self.save(Path(item["settings"]["path"]), self.settings[lane])
            config_ref = original_document(item["experiment"])["config"]
            wrong = {**original_document(config_ref), "max_memory_bytes": 2 * 1024**3}
            with patch.object(
                lc,
                "document",
                side_effect=lambda r: wrong if r == config_ref else original_document(r),
            ):
                with self.assertRaisesRegex(lc.Refused, "engine/resource"):
                    lc.arena_cohort(item)


if __name__ == "__main__":
    unittest.main()
