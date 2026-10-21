"""Only new exception/finally transport; tiny Python children, no engine or model."""

import copy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
_loader = importlib.util.spec_from_file_location(
    "exception_cleanup_lifecycle", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(lc)


class ExceptionCleanupOutcomeTests(unittest.TestCase):
    def command(self, root, cancel=False):
        process = lc.process
        cpu = min(os.sched_getaffinity(0))

        class Resources:
            deadline = None
            cpu_plan = process.CPUPlan([cpu], {"run": [cpu]})

            def check(self, members=None):
                if cancel and members:
                    raise process.CycleStopped("cycle paused by unit cancellation")

        argv = [
            sys.executable,
            "-B",
            "-c",
            "import time; time.sleep(5)" if cancel else "raise SystemExit(7)",
        ]
        return (
            dict(
                limits=dict(log_B=65536),
                cwd=str(root),
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            ),
            dict(name="failure", argv=argv),
            Resources(),
        )

    def test_failed_and_cancelled_execute_transports_after_finally_without_success(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                tmp = root / "TMP"
                (tmp / "nested" / "empty").mkdir(parents=True)
                spec, row, resources = self.command(root, cancel)
                ledger = []
                with self.assertRaises(lc.process.CycleStopped) as raised:
                    lc.command(spec, row, root, resources, ledger=ledger)
                self.assertIn(
                    "cycle paused" if cancel else "cycle child failed", str(raised.exception)
                )
                check = ledger[0]
                self.assertEqual(check["status"], "FAILED")
                self.assertIsNone(check["guardian_return"])
                self.assertFalse(check["capture_complete"])
                outcome = check["guardian_exception_outcome"]
                self.assertIs(outcome, raised.exception.cycle_cleanup_outcome)
                self.assertFalse(outcome["normal_return"])
                actual = outcome["record"]
                for key in (
                    "direct_child_reaped",
                    "process_cleanup_complete",
                    "handle_closes_complete",
                ):
                    self.assertTrue(actual[key], key)
                self.assertEqual(actual["remaining"], [])
                self.assertEqual(actual["signal_mask_restoration"], "completed")
                self.assertEqual(actual["final_record_persist"], "completed")
                self.assertFalse(lc.process.alive(actual["child"]))
                disk = lc.document(check["persisted_process_receipt"])
                self.assertEqual(disk["signal_mask_restoration"], "pending")
                self.assertEqual(disk["final_record_persist"], "attempted")
                lc.remove_empty_owned_tmp(
                    tmp, root, check["guardian_return"], exception_outcome=outcome
                )
                self.assertFalse(tmp.exists())
                # This remains an exception, not a returned successful command/capture.
                self.assertIsNone(check["guardian_return"])
                self.assertFalse(check["capture_complete"])

    def test_finalization_failure_keeps_tmp_and_preserves_primary(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            tmp = root / "TMP"
            tmp.mkdir()
            spec, row, resources = self.command(root)
            save = lc.process.save_record

            def receipt(path, record):
                if record.get("final_record_persist") == "attempted":
                    raise OSError("injected final receipt persist failure")
                return save(path, record)

            ledger = []
            with patch.object(lc.process, "save_record", side_effect=receipt):
                with self.assertRaises(BaseExceptionGroup) as raised:
                    lc.command(spec, row, root, resources, ledger=ledger)
            self.assertTrue(
                any(isinstance(e, lc.process.CycleStopped) for e in raised.exception.exceptions)
            )
            self.assertTrue(any(isinstance(e, OSError) for e in raised.exception.exceptions))
            check = ledger[0]
            outcome = check["guardian_exception_outcome"]
            actual = outcome["record"]
            self.assertEqual(actual["exit_code"], 7)
            self.assertEqual(actual["remaining"], [])
            self.assertTrue(actual["direct_child_reaped"])
            self.assertEqual(actual["final_record_persist"], "failed_or_partial_UNKNOWN")
            self.assertFalse(lc.process.alive(actual["child"]))
            with self.assertRaisesRegex(lc.Refused, "exception guardian finalization incomplete"):
                lc.remove_empty_owned_tmp(tmp, root, None, exception_outcome=outcome)
            self.assertTrue(tmp.is_dir())
            self.assertIsNone(check["guardian_return"])
            self.assertFalse(check["capture_complete"])

    def test_pending_disk_and_incomplete_exception_proof_refuse_tmp_removal(self):
        closed = dict(
            command=["unit"],
            direct_child_reaped=True,
            process_cleanup_complete=True,
            handle_closes_complete=True,
            remaining=[],
            signal_mask_restoration="completed",
            final_record_persist="completed",
            finalization_errors=[],
        )
        changes = (
            {"signal_mask_restoration": "pending"},
            {"final_record_persist": "attempted"},
            {"finalization_errors": [{"stage": "close"}]},
            {"direct_child_reaped": False},
            {"handle_closes_complete": False},
            {"process_cleanup_complete": False},
            {"remaining": [{"pid": 9999999}]},
        )
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for index, change in enumerate(changes):
                with self.subTest(change=change):
                    tmp = root / f"TMP-{index}"
                    tmp.mkdir()
                    record = {**copy.deepcopy(closed), **change}
                    with self.assertRaises(lc.Refused):
                        lc.remove_empty_owned_tmp(
                            tmp,
                            root,
                            None,
                            exception_outcome=dict(normal_return=False, record=record),
                        )
                    self.assertTrue(tmp.is_dir())
            for index, outcome in enumerate((None, dict(normal_return=True, record=closed))):
                tmp = root / f"no-proof-{index}"
                tmp.mkdir()
                with self.assertRaises(lc.Refused):
                    lc.remove_empty_owned_tmp(tmp, root, None, exception_outcome=outcome)
                self.assertTrue(tmp.is_dir())


if __name__ == "__main__":
    unittest.main()
