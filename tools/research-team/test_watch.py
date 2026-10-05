"""Read/ownership/record contracts; no real scheduler or App Server is started."""

import importlib.util
import json
import signal
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location(
    "watch", Path(__file__).resolve().parents[2] / "scripts/dev/research-watch.py"
)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WatchTests(unittest.TestCase):
    def test_overlap_hardlink_allocation(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            a = root / "a"
            a.write_bytes(b"x" * 5000)
            (root / "b").hardlink_to(a)
            self.assertEqual(
                w.allocated([root, a]), root.stat().st_blocks * 512 + a.stat().st_blocks * 512
            )

    def test_selection_keeps_overflow_source_hash_without_copying_history(self):
        item = {"id": "x", "notes": "n" * 100000, "description": "d" * 10000}
        result = w.select_issue(item)
        self.assertTrue(result["notes"]["overflow"])
        self.assertEqual(len(result["notes"]["tail"]), 1024)
        self.assertEqual(result["notes"]["source_bytes"], 100000)
        self.assertTrue(result["description"]["overflow"])
        self.assertEqual(len(result["description"]["text"]), 3072)

    def test_nested_dependencies_do_not_copy_parent_notes(self):
        dependency = {"id": "quoridor-4lc", "status": "in_progress", "notes": "n" * 330000}
        selected = w.select_issue({"id": "quoridor-4lc.40", "dependencies": [dependency] * 20})
        relation = selected["dependencies"]
        self.assertEqual(relation["source_count"], 20)
        self.assertEqual(relation["omitted_count"], 4)
        self.assertGreater(relation["source_bytes"], 330000)
        self.assertNotIn("notes", relation["items"][0])
        self.assertLess(len(json.dumps(selected).encode()), 8192)

    def test_unknown_state_cap_or_binding_rejected(self):
        with tempfile.TemporaryDirectory() as name, patch.object(w.time, "sleep"):
            root = Path(name)
            expected = {
                "state_dir": name,
                "binding": {"thread_id": "saved"},
                "process": {"pid": 123},
            }
            state = {
                "binding": expected["binding"],
                "phase": "running",
                "process": expected["process"],
                "owned": {"thread_id": "saved", "max_turn_seconds": None},
            }
            (root / "state.json").write_text(json.dumps(state))
            self.assertIsNone(w.state_read(expected)["owned"]["max_turn_seconds"])
            state["owned"]["max_turn_seconds"] = 180
            (root / "state.json").write_text(json.dumps(state))
            with self.assertRaises(w.Unavailable):
                w.state_read(expected)
            state["owned"] = None
            state["binding"] = {"thread_id": "other"}
            (root / "state.json").write_text(json.dumps(state))
            with self.assertRaises(w.Unavailable):
                w.state_read(expected)

    def test_record_cap_refuses_without_saving_pass(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaises(w.Unavailable):
                w.save_record(
                    root / "run" / "large.json",
                    {"supervisor_output": name},
                    {"data": "x" * w.RECORD_CAP},
                )
            self.assertFalse((root / "run" / "large.json").exists())
            receipt = json.loads((root / "run" / "large.refusal.json").read_text())
            self.assertGreater(receipt["requested_record_bytes"], w.RECORD_CAP)
            self.assertFalse(receipt["record_saved"])

    def test_unknown_or_other_identity_never_signalled(self):
        with (
            patch.object(w.scheduler, "alive", return_value=True),
            patch.object(w, "state_read", return_value={"process": {"pid": 456}}),
            patch.object(w, "capture") as capture,
        ):
            with self.assertRaises(w.Unavailable):
                w.stop_exact({"process": {"pid": 123}})
            capture.assert_not_called()

    def test_cumulative_command_cap_before_spawn(self):
        with (
            tempfile.TemporaryDirectory() as name,
            patch.object(w, "admit"),
            patch.object(w, "capture") as capture,
        ):
            root = Path(name)
            (root / "command-budget.json").write_text(json.dumps({"commands": 24}))
            expected = {
                "_output": str(root / "record.json"),
                "supervisor_forecast_bytes": 512 * 1024,
            }
            with self.assertRaises(w.Unavailable):
                w.wrapper(expected, ["ready", "--json"], [])
            capture.assert_not_called()

    def test_input_changed_before_admission(self):
        with tempfile.TemporaryDirectory() as name:
            p = Path(name) / "config"
            p.write_text("new")
            with self.assertRaises(w.Unavailable):
                w.check_inputs({"input_hashes": {str(p): "old"}})


class CaptureTests(unittest.TestCase):
    def run_capture(self, *, interruption=False, alive=True, waits=(0,)):
        child = MagicMock(pid=900001)
        child.poll.return_value = None
        child.wait.side_effect = list(waits)
        selector = MagicMock()
        selector.get_map.return_value = {"pipe": 1} if interruption else {}
        selector.select.side_effect = w.Unavailable("mock outer soft stop")
        receipts = []
        with (
            patch.object(w.subprocess, "Popen", return_value=child),
            patch.object(w.selectors, "DefaultSelector", return_value=selector),
            patch.object(
                w.scheduler,
                "process_identity",
                return_value={"pid": child.pid, "ticks": 1, "boot": "mock"},
            ),
            patch.object(w.scheduler, "alive", return_value=alive),
            patch.object(w.os, "killpg") as kill,
        ):
            if interruption:
                with self.assertRaises(w.Unavailable):
                    w.capture(
                        ["mock"], Path(__file__).resolve().parents[2], receipt=receipts.append
                    )
            else:
                w.capture(["mock"], Path(__file__).resolve().parents[2], receipt=receipts.append)
            signals = kill.call_args_list
        return receipts, signals

    def test_normal_completion_receipt(self):
        rows, signals = self.run_capture()
        self.assertEqual([r["phase"] for r in rows], ["started", "completed"])
        self.assertTrue(rows[-1]["child_reaped"])
        self.assertEqual(rows[-1]["exit_code"], 0)
        self.assertFalse(signals)
        self.assertFalse(rows[-1]["process_group_absence_certified"])

    def test_soft_interrupt_reaps_and_records_failure(self):
        rows, signals = self.run_capture(interruption=True, waits=(-15,))
        self.assertTrue(rows[-1]["child_reaped"])
        self.assertIn("capture_interrupted", rows[-1]["refusal"])
        self.assertEqual(signals[0].args, (900001, signal.SIGTERM))
        self.assertFalse(rows[-1]["streams"]["stdout"]["complete"])

    def test_unknown_identity_not_signalled_or_certified(self):
        expiry = subprocess.TimeoutExpired("mock", 3)
        rows, signals = self.run_capture(interruption=True, alive=False, waits=(expiry, expiry))
        self.assertFalse(signals)
        self.assertFalse(rows[-1]["child_reaped"])
        self.assertEqual(rows[-1]["recovery_error"], "TimeoutExpired")

    def test_bounded_escalation_requires_exact_identity(self):
        rows, signals = self.run_capture(
            interruption=True, waits=(subprocess.TimeoutExpired("mock", 3), -9)
        )
        self.assertEqual([c.args[1] for c in signals], [signal.SIGTERM, signal.SIGKILL])
        self.assertEqual(rows[-1]["exit_code"], -9)

    def test_receipt_cap_refusal_prevents_spawn(self):
        with (
            tempfile.TemporaryDirectory() as name,
            patch.object(w, "admit"),
            patch.object(w, "save_record", side_effect=w.Unavailable("cap")),
            patch.object(w, "capture") as spawn,
        ):
            expected = {
                "_output": str(Path(name) / "finish.json"),
                "supervisor_forecast_bytes": 512 * 1024,
                "root": str(Path(__file__).resolve().parents[2]),
                "deadlines": {"supervisor": "2099-01-01T00:00:00Z"},
            }
            with self.assertRaises(w.Unavailable):
                w.wrapper(expected, ["backup", "sync"], [], selection=False)
            spawn.assert_not_called()

    def test_each_command_receipt_survives_later_interruption(self):
        with tempfile.TemporaryDirectory() as name, patch.object(w, "admit"):
            expected = {
                "_output": str(Path(name) / "run" / "finish.json"),
                "supervisor_output": name,
                "supervisor_forecast_bytes": 512 * 1024,
                "root": str(Path(__file__).resolve().parents[2]),
                "deadlines": {"supervisor": "2099-01-01T00:00:00Z"},
            }

            def mock_capture(_argv, _root, *, timeout, receipt):
                receipt({"phase": "started", "child_reaped": False})
                if "second" in _argv:
                    raise w.Unavailable("mock hard stop before completed receipt")
                meta = {"phase": "completed", "exit_code": 0, "refusal": None, "child_reaped": True}
                receipt(meta)
                return {"stdout": "ok", "stderr": ""}, meta

            with patch.object(w, "capture", side_effect=mock_capture):
                w.wrapper(expected, ["first"], [], selection=False)
                with self.assertRaises(w.Unavailable):
                    w.wrapper(expected, ["second"], [], selection=False)
            import json

            first = json.loads((Path(name) / "run/command-01-child.json").read_text())
            second = json.loads((Path(name) / "run/command-02-child.json").read_text())
            self.assertTrue(first["child_reaped"])
            self.assertFalse(second["child_reaped"])
            self.assertNotIn("stdout", first)


if __name__ == "__main__":
    unittest.main()
