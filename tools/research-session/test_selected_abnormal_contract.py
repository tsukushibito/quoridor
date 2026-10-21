"""New selected-settings abnormal completion case; synthetic stopped identities, no native/ML."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

MAIN = Path("/workspaces/quoridor")
SOURCE = Path(os.environ.get("LIFECYCLE_REPAIR_SOURCE", MAIN / "scripts/dev/research-lifecycle.py"))
TMP = Path(
    os.environ.get(
        "LIFECYCLE_REPAIR_TMP", MAIN / ".artifacts/research-lifecycle-maintenance/test-TMP"
    )
)
sys.path.insert(0, str(SOURCE.resolve().parents[2] / "shared/python"))
loader = importlib.util.spec_from_file_location("selected_abnormal_lifecycle", SOURCE)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)
lc.ROOT = MAIN


class SelectedAbnormalContractTests(unittest.TestCase):
    def test_selected_contract_and_direct_contract_keep_failure_only_and_refuse_drift(self):
        TMP.mkdir(parents=True, exist_ok=True)
        for selected in (True, False):
            with (
                self.subTest(selected_settings=selected),
                tempfile.TemporaryDirectory(dir=TMP) as name,
            ):
                root = Path(name)
                operation, runtime = root / "operation", root / "runtime"
                operation.mkdir()
                runtime.mkdir()

                def write(path, value):
                    path.write_text(json.dumps(value))
                    return lc.bound(path)[0]

                support = write(root / "support.json", {"synthetic_support": True})
                settings = write(
                    root / "settings.json", {"kind": "sequence", "synthetic_metadata": True}
                )
                experiment = write(
                    root / "experiment.json",
                    {
                        "phase": "compare",
                        "argv": ["synthetic", "no-payload"],
                        "planned_slots": 2,
                        "build_manifest": {},
                    },
                )
                spec = {
                    "schema": "quoridor.research.lifecycle-intent.v1",
                    "kind": "run",
                    "owner": str(root),
                    "output": str(operation),
                    "cwd": str(MAIN),
                    "support": support,
                    "experiment": experiment,
                    "argv": ["/synthetic/native-not-executed"],
                    "data_root": str(root / "data"),
                    "data": [],
                    "limits": {"log_B": 1024},
                    "finalizers": [],
                }
                if selected:
                    spec.update(settings=settings, selection_index=0)
                spec["intent_sha256"] = lc.canonical_sha(spec)
                intent = write(root / "intent.json", spec)
                os.link(intent["path"], operation / "intent.json")
                identities = [
                    {"pid": i, "start_ticks": str(i), "boot_id": "synthetic-stopped-boot"}
                    for i in (101, 102, 103)
                ]
                expected = settings if selected else support
                config = {
                    "argv": [
                        sys.executable,
                        "-B",
                        str(MAIN / "scripts/dev/research-lifecycle.py"),
                        "run",
                        "--intent",
                        intent["path"],
                        "--sha256",
                        intent["sha256"],
                    ],
                    "cwd": str(MAIN),
                    "resource_contract": expected["path"],
                    "issue": "synthetic-selected-contract",
                    "thread_id": "synthetic-no-AppServer",
                }
                job = {
                    "job_id": "synthetic-selected-job",
                    "outcome": "cancelled",
                    "exit_code": -15,
                    "started_at": "synthetic",
                    "finished_at": "synthetic-stopped",
                    "direct_child_reaped": True,
                    "cleanup_complete": True,
                    "remaining": [],
                    "cleanup_errors": [],
                }
                result = write(runtime / "result.json", job)
                write(
                    operation / "run.process.json",
                    {"command": spec["argv"], "status": "running", "child": identities[2]},
                )
                (operation / "run.full.log").write_bytes(b"")

                def bind_original_config():
                    config_ref = write(runtime / "config.json", config)
                    fingerprint = hashlib.sha256(
                        json.dumps(config, sort_keys=True).encode()
                    ).hexdigest()
                    state = {
                        "job_id": job["job_id"],
                        "issue": config["issue"],
                        "thread_id": config["thread_id"],
                        "config_sha256": fingerprint,
                        "phase": "finished",
                        "outcome": job["outcome"],
                        "supervisor": identities[0],
                        "child": identities[1],
                        "started_at": "synthetic-started",
                    }
                    write(runtime / "state.json", state)
                    origin = {
                        "runtime": str(runtime),
                        "job_id": job["job_id"],
                        "config": config_ref,
                        "config_sha256": fingerprint,
                        "supervisor": identities[0],
                        "child": identities[1],
                    }
                    write(
                        operation / "INCOMPLETE",
                        {"status": "UNKNOWN", "intent": intent, "originating_job": origin},
                    )

                bind_original_config()
                with patch.object(lc.process, "alive", return_value=False):
                    failure = lc.abnormal_run_failure(operation, result)
                    self.assertEqual(failure["status"], "CANCELLED")
                    self.assertEqual(failure["primary"]["original_result"], job)
                    self.assertEqual(failure["data"]["status"], "FAILED")
                    self.assertIsNone(failure["data"]["numerical_qualification"])
                    self.assertIsNone(failure["checks"][0]["guardian_return"])
                    self.assertFalse(failure["checks"][0]["capture_complete"])
                    self.assertEqual(failure["abnormal_origin"]["command_cleanup"], "UNKNOWN")
                    self.assertFalse(failure["cleanup_complete"])
                    # Even an independently rebound config cannot select a different contract.
                    config["resource_contract"] = support["path"] if selected else settings["path"]
                    bind_original_config()
                    with self.assertRaisesRegex(lc.Refused, "closed original abnormal"):
                        lc.abnormal_run_failure(operation, result)
                    config["resource_contract"] = expected["path"]
                    bind_original_config()
                    path = Path(expected["path"])
                    original = path.read_bytes()
                    path.write_bytes(original + b" ")
                    with self.assertRaises(lc.Refused):
                        lc.abnormal_run_failure(operation, result)
                    path.write_bytes(original)
                self.assertTrue((operation / "INCOMPLETE").exists())
                self.assertFalse((operation / "candidate.json").exists())
                self.assertFalse((operation / "manifest.json").exists())
                self.assertFalse((operation / "finalizing").exists())


if __name__ == "__main__":
    unittest.main()
