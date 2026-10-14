"""New synthetic392 admission ports; no kernel/native/model/Search execution."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MAIN = Path("/workspaces/quoridor")
loader = importlib.util.spec_from_file_location(
    "lc_fixed_d392", MAIN / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class FixedDAdmission392(unittest.TestCase):
    def test_model_free_fixed_d_and_original_nnue_profile_boundaries(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            config = {
                "roots": [
                    {"input": 0, "pointer": "", "field": "prefix", "label": "root"}
                ],
                "profile": "control",
                "tt_entries": 4096,
                "use_tt": True,
                "use_pvs": True,
                "namespace": {
                    "evaluator": "original-distance-a0-b8-tanh",
                    "rules": "research-standard-2p-threefold-goal-first-v1",
                    "selectivity": "fixedD-completed-D4-D6",
                },
                "output_bytes": 65536,
                "record_bytes": 4096,
            }
            requests = [
                {
                    "id": "r",
                    "session": "cold",
                    "root": 0,
                    "depth": 4,
                    "node_cap": 2000000,
                }
            ]
            schedule = root / "requests.json"
            schedule.write_text(json.dumps(requests))
            config_path = root / "config.json"
            experiment = {
                "phase": "compare",
                "argv": ["unused-never-executed", "measure"],
                "inputs": [{}],
                "models": [],
                "rules": config["namespace"]["rules"],
                "schedule": lc.bound(schedule)[0],
            }

            def check(models, evaluator, profile):
                config["namespace"]["evaluator"] = evaluator
                config["profile"] = profile
                config_path.write_text(json.dumps(config))
                experiment["config"] = lc.bound(config_path)[0]
                experiment["models"] = models
                lc.measurement_config(experiment)
                lc.experiment_phase_check(experiment)

            fixed = "original-distance-a0-b8-tanh"
            for profile in ("control", "coverage"):
                check([], fixed, profile)
            for profile in ("control", "cheap"):
                check([{"synthetic": "not loaded"}], "immutable-nnue-identity", profile)
            for models, evaluator, profile in (
                ([{}], fixed, "control"),
                ([], fixed, "cheap"),
                ([], "foreign-fixed-D", "control"),
                ([{}], "immutable-nnue-identity", "coverage"),
                ([{}, {}], "immutable-nnue-identity", "control"),
            ):
                with self.assertRaises(lc.Refused):
                    check(models, evaluator, profile)

    def test_corpus_physical_width_reserves_siblings_and_arena_isolation(self):
        with tempfile.TemporaryDirectory() as name:
            fixture = Path(name)
            (fixture / "proc").mkdir()
            for cpu in range(20):
                top = fixture / f"sys/devices/system/cpu/cpu{cpu}/topology"
                top.mkdir(parents=True)
                (top / "physical_package_id").write_text("0")
                (top / "core_id").write_text(str(cpu // 2))
            spec = {
                "kind": "run",
                "experiment": {},
                "child_cpu_cores": list(range(0, 20, 2)),
                "limits": {
                    "worker_cpu": 0,
                    "guardian_cpu": 16,
                    "family_B": 8 * 1024**3,
                    "host_reserve_B": 4 * 1024**3,
                },
            }
            real_path = Path
            with (
                patch.object(
                    lc,
                    "Path",
                    side_effect=lambda p: real_path(fixture) / str(p).lstrip("/"),
                ),
                patch.object(lc.process, "available_memory", return_value=16 * 1024**3),
                patch.object(lc.os, "sched_getaffinity", return_value=set(range(20))),
                patch.object(lc.os, "sched_setaffinity") as set_affinity,
                patch.object(
                    lc, "document", return_value={"phase": "corpus"}
                ) as document,
                patch.object(
                    lc,
                    "arena_cpu_cores",
                    side_effect=lc.Refused("arena owning boundary"),
                ) as arena,
            ):
                lc.physical_and_quiet(spec)
                set_affinity.assert_called_once_with(0, {16})
                arena.assert_not_called()
                sibling = copy.deepcopy(spec)
                sibling["child_cpu_cores"][1] = 1
                with self.assertRaisesRegex(lc.Refused, "distinct physical"):
                    lc.physical_and_quiet(sibling)
                missing = copy.deepcopy(spec)
                missing["limits"]["guardian_cpu"] = 17
                with self.assertRaises(lc.Refused):
                    lc.physical_and_quiet(missing)
                with patch.object(lc.os, "sched_getaffinity", return_value={0, 2, 4}):
                    with self.assertRaisesRegex(lc.Refused, "affinity"):
                        lc.physical_and_quiet(spec)
                with patch.object(
                    lc.process, "available_memory", return_value=10 * 1024**3
                ):
                    with self.assertRaisesRegex(lc.Refused, "RAM"):
                        lc.physical_and_quiet(spec)
                document.return_value = {"phase": "arena"}
                with self.assertRaisesRegex(lc.Refused, "arena owning"):
                    lc.physical_and_quiet(spec)
                arena.assert_called_once_with(spec)

    def test_command_forwards_only_corpus_affinity_and_keeps_exact_arena_owner(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            cpus = list(range(0, 20, 2))
            spec = {
                "kind": "run",
                "cwd": str(MAIN),
                "env": {"SYNTHETIC": "no child is launched"},
                "experiment": {},
                "limits": {"worker_cpu": 0, "log_B": 1024},
                "child_cpu_cores": cpus,
            }
            resources = object()
            seen = []

            def execute(argv, log, deadline, **kwargs):
                seen.append((argv, deadline, kwargs))
                self.assertIs(kwargs["resources"], resources)
                kwargs["output_sink"](b"synthetic\n")
                return {
                    "status": "complete",
                    "exit_code": 0,
                    "direct_child_reaped": True,
                    "cleanup_complete": True,
                    "remaining": [],
                    "signal_mask_restoration": "completed",
                    "final_record_persist": "completed",
                    "log_bytes_seen": 10,
                }

            with (
                patch.object(
                    lc, "document", return_value={"phase": "corpus"}
                ) as document,
                patch.object(lc, "arena_cpu_cores", return_value=[0, 2, 4]) as arena,
            ):
                lc.command(
                    spec,
                    {"name": "corpus", "argv": ["never-launched"]},
                    directory,
                    resources,
                    executor=execute,
                )
                self.assertEqual(seen[-1][2]["cpu_cores"], cpus)
                self.assertIsNone(seen[-1][2]["cpu_core"])
                self.assertEqual(seen[-1][2]["env"], spec["env"])
                arena.assert_not_called()
                document.return_value = {"phase": "arena"}
                lc.command(
                    spec,
                    {"name": "arena", "argv": ["never-launched"]},
                    directory,
                    resources,
                    executor=execute,
                )
                self.assertEqual(seen[-1][2]["cpu_cores"], [0, 2, 4])
                arena.assert_called_once_with(spec)
                self.assertEqual(len(seen), 2)


if __name__ == "__main__":
    unittest.main()
