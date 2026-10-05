"""Read/ownership/record contracts; no real scheduler or App Server is started."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
