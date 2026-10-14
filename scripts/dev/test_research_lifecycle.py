"""Owning lifecycle boundaries for bulk data and configured operation paths."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def load_lifecycle():
    path = Path(__file__).with_name("research-lifecycle.py")
    loader = importlib.util.spec_from_file_location("lifecycle_test", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


class LifecycleDataAndPaths(unittest.TestCase):
    def test_corpus_stream_is_hashed_without_control_buffer(self):
        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            stream = root / "terminal.stream"
            stream.write_bytes(b"\xff\x00\x80" * 1024)
            result = root / "generation.json"
            result.write_text(json.dumps({"scheduled": 1, "recorded": 0}))
            spec = {
                "owner": str(root),
                "data": [
                    {"name": "pilot_stream", "path": str(stream), "limit_B": 4096},
                    {"name": "generation_result", "path": str(result), "limit_B": 4096},
                ],
            }
            experiment = {
                "phase": "corpus",
                "argv": ["unused", "teacher-pilot"],
                "planned_slots": 1,
            }
            original_bound = lc.bound

            def bounded_control(path, *args, **kwargs):
                self.assertNotEqual(Path(path), stream, "bulk stream loaded as control")
                return original_bound(path, *args, **kwargs)

            with patch.object(lc, "bound", bounded_control):
                actual = lc.collect_data(spec, experiment)
            self.assertEqual(actual["status"], "PASS")
            self.assertEqual(actual["corpus"], {"scheduled": 1, "recorded": 0})
            self.assertIn(lc.artifact_ref(stream), actual["files"])
            self.assertFalse(actual["errors"])
            spec["data"][0]["limit_B"] = stream.stat().st_size - 1
            rejected = lc.collect_data(spec, experiment)
            self.assertEqual(rejected["status"], "FAILED")
            self.assertEqual(rejected["errors"][0]["stage"], "pilot_stream")

    def test_sequence_operation_stays_in_exact_nested_output(self):
        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            experiment = root / "experiment.json"
            experiment.write_text(
                json.dumps(
                    {
                        "phase": "corpus",
                        "argv": ["unused", "teacher-pilot", "@EXPERIMENT@"],
                    }
                )
            )
            template = {
                "kind": "run",
                "owner": str(root),
                "data_root": str(root / "data"),
                "experiment": lc.artifact_ref(experiment),
                "env": {},
                "finalizers": [],
            }
            selected_output = root / "nested" / "sequence"
            settings = root / "settings.json"
            settings.write_text(
                json.dumps(
                    {
                        "kind": "sequence",
                        "owner": str(root),
                        "output": str(selected_output),
                        "runs": [template],
                    }
                )
            )
            selected_ref = lc.artifact_ref(settings)
            actual_ref = lc.prepare_selected_operation(selected_ref, "run", 0)
            actual = lc.document(actual_ref)
            phase = selected_output / "run-000"
            self.assertEqual(Path(actual_ref["path"]), phase / "intent.json")
            self.assertEqual(actual["output"], str(phase / "operation"))
            self.assertEqual(actual["TMP"], str(phase / "TMP"))
            self.assertEqual(actual["data_root"], template["data_root"])
            self.assertFalse((root / "sequence").exists())
            with self.assertRaises(lc.Refused):
                lc.prepare_selected_operation(selected_ref, "run", 0)
            # An output outside the owner must fail before any operation is created.
            escaped = lc.document(selected_ref)
            escaped["output"] = str(root.parent / (root.name + "-escape"))
            outside = root / "outside-settings.json"
            outside.write_text(json.dumps(escaped))
            with self.assertRaises(lc.Refused):
                lc.prepare_selected_operation(lc.artifact_ref(outside), "run", 0)
            self.assertFalse(Path(escaped["output"]).exists())


if __name__ == "__main__":
    unittest.main()
