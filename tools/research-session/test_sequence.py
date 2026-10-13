"""Finite execution ownership with tiny Python children; no research/model/native work."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get("QUORIDOR_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
SOURCE = Path(
    os.environ.get("RESEARCH_LIFECYCLE_SOURCE", ROOT / "scripts/dev/research-lifecycle.py")
)
loader = importlib.util.spec_from_file_location("sequence_lifecycle", SOURCE)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)
lc.ROOT = ROOT
loader = importlib.util.spec_from_file_location(
    "sequence_test_job", ROOT / "scripts/dev/research-job.py"
)
job = importlib.util.module_from_spec(loader)
loader.loader.exec_module(job)


class SequenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.affinity = os.sched_getaffinity(0)
        self.plan = self.metadata("plan.json", {"batches": [{"batch": i} for i in range(384)]})
        self.settings = {
            "kind": "sequence",
            "owner": str(self.root),
            "output": str(self.root / "finite"),
            "cwd": str(ROOT),
            "arena_block": 1,
            "serial_order": ["arena", "measure"],
            "arena": {"range": [6, 7], "template": {"approved_plan": self.plan}},
            "measurements": [{}],
        }

    def metadata(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return lc.bound(path)[0]

    def test_sequence_order_excludes_completed_prefix_and_interleaves_without_reordering(self):
        self.settings["arena"]["range"] = [6, 383]
        self.settings["arena_block"] = 32
        self.settings["measurements"] = [{} for _ in range(5)]
        order = list(lc.operation_order(self.settings))
        self.assertEqual([i for k, i in order if k == "arena"], list(range(6, 384)))
        self.assertEqual([i for k, i in order if k == "measure"], list(range(5)))
        self.assertEqual(order[0], ("arena", 6))
        self.assertEqual(order[32], ("measure", 0))
        self.assertEqual(order[33], ("arena", 38))
        self.assertEqual(order[65], ("measure", 1))
        self.assertEqual(len(order), 383)
        self.settings["serial_order"] = ["measure", "arena"]
        with self.assertRaisesRegex(lc.Refused, "arena precedes"):
            list(lc.operation_order(self.settings))
        self.settings["serial_order"] = ["arena", "measure"]
        self.settings["arena"]["range"] = [6, 384]
        with self.assertRaisesRegex(lc.Refused, "exceeds plan"):
            list(lc.operation_order(self.settings))

    def test_sequence_selected_range_and_environment_cannot_be_changed_by_a_pair(self):
        experiment = self.metadata("experiment.json", {"phase": "arena", "batch": 6})
        spec = {
            "experiment": experiment,
            "owner": str(self.root),
            "writer": "fixture",
            "cwd": str(ROOT),
            "limits": {},
            "support": {},
            "approved_plan": self.plan,
            "artifact": {},
            "caller_sources": [],
            "env": {"BOUND": "same", "TMPDIR": "old"},
        }
        self.settings["arena"]["template"] = copy.deepcopy(spec)
        spec["settings"] = self.metadata("selected.json", self.settings)
        spec["env"]["TMPDIR"] = "new-own-TMP"
        self.assertEqual(lc.selected_arena(spec), self.plan)
        spec["env"]["BOUND"] = "foreign"
        with self.assertRaisesRegex(lc.Refused, "environment drift"):
            lc.selected_arena(spec)
        spec["env"]["BOUND"] = "same"
        spec["experiment"] = self.metadata("outside.json", {"phase": "arena", "batch": 5})
        with self.assertRaisesRegex(lc.Refused, "outside selected"):
            lc.selected_arena(spec)

    def test_sequence_derives_current_pair_metadata_and_refuses_duplicate_namespace(self):
        artifact = {"path": "/synthetic/native", "sha256": "a" * 64}
        config = self.metadata("config.json", {"output": str(self.root / "original-game-output")})
        plan = {
            "batches": [{"batch": i, "config": config} for i in range(8)],
            "inputs": [],
            "models": [],
            "schedule": self.plan,
        }
        plan_ref = self.metadata("selected-plan.json", plan)
        numerical = self.metadata(
            "old-numerical.json", {"original_evidence": self.plan, "correspondence_only": True}
        )
        experiment = {
            "phase": "arena",
            "config": config,
            "batch": 6,
            "inputs": [],
            "models": [],
            "schedule": self.plan,
            "build_manifest": self.plan,
            "dynamic_libraries": [],
            "numerical_qualification": numerical,
            "canonical_plan_sha256": plan_ref["sha256"],
            "rules": "fixture",
            "distance_units": "fixture",
            "value_perspective": "fixture",
            "argv": [
                "/synthetic/native",
                "arena",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        }
        template = {
            "kind": "run",
            "owner": str(self.root),
            "writer": "fixture",
            "cwd": str(ROOT),
            "limits": {},
            "support": {},
            "approved_plan": plan_ref,
            "artifact": artifact,
            "caller_sources": [],
            "experiment": self.metadata("base-experiment.json", experiment),
            "env": {"TMPDIR": "old"},
            "data_root": "old-output",
            "owned_outputs": [],
            "data": [{"name": "journal", "path": "old-output/completed.jsonl.gz", "limit_B": 4096}],
            "admission": {"obsolete": "per-pair"},
        }
        self.settings["arena"]["template"] = template
        settings_ref = self.metadata("settings.json", self.settings)
        with patch.object(lc, "accepted_build", return_value={"artifact": artifact}):
            value = lc.prepare_selected_operation(settings_ref, "arena", 7)
            with self.assertRaisesRegex(lc.Refused, "never replay"):
                lc.prepare_selected_operation(settings_ref, "arena", 7)
        spec = lc.document(value)
        self.assertNotIn("admission", spec)
        self.assertEqual(spec["settings"], settings_ref)
        current = lc.document(spec["experiment"])
        self.assertEqual(current["batch"], 7)
        self.assertEqual(current["config"], config)
        self.assertEqual(spec["data_root"], str(self.root / "original-game-output"))
        self.assertEqual(
            lc.document(current["numerical_qualification"])["original_evidence"], self.plan
        )
        self.assertFalse(Path(spec["TMP"]).exists())

    def run_fixture(self, *, fail=None, cancel=False):
        settings_ref = self.metadata("settings.json", self.settings)
        config = {
            "issue": "fixture-owner",
            "goal_issue": "fixture-goal",
            "thread_id": "fixture-thread",
            "cwd": str(ROOT),
            "argv": [sys.executable, "-c", "pass"],
            "end_at": None,
            "notify_until": None,
            "max_runtime_seconds": 5,
            "control_interval_seconds": 1,
            "notify_interval_seconds": 1,
            "request_timeout_seconds": 1,
            "log_max_bytes": 4096,
            "resource_contract": settings_ref["path"],
        }
        origin = {"config": self.metadata("outer-config.json", config)}
        entered = []
        phases = []
        current_runtime = None
        sent_cancel = False

        class Backend:
            def issues(inner, ids, *, timeout):
                nonlocal sent_cancel
                if cancel and current_runtime is not None and not sent_cancel:
                    if (current_runtime.parent / "ready").exists():
                        sent_cancel = True
                        os.kill(os.getpid(), signal.SIGTERM)
                return [
                    {"id": i, "status": "open", "assignee": "codex:fixture-thread"} for i in ids
                ]

        def prepare(selected, kind, index):
            phase = self.root / f"{kind}-{index}"
            phase.mkdir()
            phases.append(phase)
            (phase / "TMP").mkdir()
            return self.metadata(
                str(phase / "intent.json"),
                {
                    "cwd": str(ROOT),
                    "output": str(phase / "operation"),
                    "TMP": str(phase / "TMP"),
                    "limits": {"log_B": 4096},
                    "kind": kind,
                    "index": index,
                },
            )

        def execute(directory, selected, root, backend):
            nonlocal current_runtime
            current_runtime = directory
            spec = lc.document(lc.bound(directory.parent / "intent.json")[0])
            entered.append((spec["kind"], spec["index"]))
            code = (
                "import json,os,sys,time; from pathlib import Path; p=Path(sys.argv[1]); "
                "(p/'operation').mkdir(); (p/'operation/INCOMPLETE').write_text('owned'); "
                "(p/'affinity.json').write_text(json.dumps(sorted(os.sched_getaffinity(0)))); "
                "(p/'ready').write_text('ready'); print('bounded NN0 fixture',flush=True); "
                + ("time.sleep(60)" if cancel else f"sys.exit({3 if entered[-1] == fail else 0})")
            )
            selected = {
                **selected,
                "argv": [sys.executable, "-B", "-c", code, str(directory.parent)],
            }
            # The injected entry adapter supplies an actual small Python command, not a fake guardian.
            job.write(directory, "config.json", selected)
            state = job.read(directory, "state.json")
            state["config_sha256"] = lc.sha(json.dumps(selected, sort_keys=True).encode())
            job.write(directory, "state.json", state)
            return job.execute(directory, selected, root, backend)

        def complete(operation, result_ref):
            returned = lc.document(result_ref)
            state = job.read(Path(result_ref["path"]).parent, "state.json")
            self.assertTrue(returned["direct_child_reaped"])
            self.assertTrue(returned["cleanup_complete"])
            self.assertFalse(job.runtime.alive(state["child"]))
            self.assertEqual(
                json.loads((operation.parent / "affinity.json").read_text()), sorted(self.affinity)
            )
            (operation.parent / "TMP").rmdir()
            completion = {
                "status": "PASS" if returned["outcome"] == "succeeded" else "FAILED",
                "cleanup_complete": True,
                "remaining": [],
            }
            lc.new_json(operation / "manifest.json", completion)
            (operation / "INCOMPLETE").unlink()
            return completion

        adapter = SimpleNamespace(
            runtime=job.runtime,
            validate=job.validate,
            write=job.write,
            lock=job.lock,
            authority=job.authority,
            execute=execute,
        )

        def guard(spec):
            os.sched_setaffinity(0, {min(self.affinity)})

        before_handler = signal.getsignal(signal.SIGTERM)
        with (
            patch.object(lc, "originating_job", return_value=origin),
            patch.object(lc, "project_python", return_value=Path(sys.executable)),
            patch.object(lc, "physical_and_quiet", side_effect=guard),
        ):
            if fail or cancel:
                with self.assertRaisesRegex(lc.Refused, "finite execution stopped"):
                    lc.sequence(
                        settings_ref,
                        job_module=adapter,
                        backend=Backend(),
                        prepare=prepare,
                        complete=complete,
                    )
            else:
                lc.sequence(
                    settings_ref,
                    job_module=adapter,
                    backend=Backend(),
                    prepare=prepare,
                    complete=complete,
                )
            previous_entries = list(entered)
            with self.assertRaisesRegex(lc.Refused, "no automatic restart"):
                lc.sequence(
                    settings_ref,
                    job_module=adapter,
                    backend=Backend(),
                    prepare=prepare,
                    complete=complete,
                )
            self.assertEqual(entered, previous_entries)
        self.assertEqual(os.sched_getaffinity(0), self.affinity)
        self.assertEqual(signal.getsignal(signal.SIGTERM), before_handler)
        for phase in phases:
            self.assertFalse((phase / "TMP").exists())
        result = json.loads((Path(self.settings["output"]) / "result.json").read_bytes())
        return result, entered

    def test_sequence_success_real_children_directwait_cleanup_and_affinity_restoration(self):
        result, entered = self.run_fixture()
        self.assertEqual(entered, [("arena", 6), ("measure", 0), ("arena", 7)])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completed_operations"], 3)
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(result["remaining"], [])
        self.assertTrue(
            all(x["launch_affinity"] == sorted(self.affinity) for x in result["operations"])
        )
        for operation in result["operations"]:
            self.assertNotIn("returned", operation)
            self.assertEqual(lc.document(operation["job_result"])["outcome"], "succeeded")

    def test_sequence_error_preserves_completed_prefix_and_never_starts_next_or_replays(self):
        result, entered = self.run_fixture(fail=("measure", 0))
        self.assertEqual(entered, [("arena", 6), ("measure", 0)])
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["completed_operations"], 1)
        self.assertEqual(lc.document(result["operations"][-1]["job_result"])["exit_code"], 3)
        self.assertTrue(result["cleanup_complete"])

    def test_sequence_signal_cancels_exact_owned_child_cleans_TMP_and_stops_suffix(self):
        result, entered = self.run_fixture(cancel=True)
        self.assertEqual(entered, [("arena", 6)])
        self.assertEqual(result["status"], "CANCELLED")
        self.assertEqual(result["completed_operations"], 0)
        self.assertEqual(lc.document(result["operations"][0]["job_result"])["outcome"], "cancelled")
        self.assertTrue(result["cleanup_complete"])


if __name__ == "__main__":
    unittest.main()
