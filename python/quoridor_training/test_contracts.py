import unittest
import tempfile
import json
from pathlib import Path
import numpy as np
from quoridor_training.cache import sha, load
from quoridor_training.plotting import render_learning_curves


class Contracts(unittest.TestCase):
    def test_test_cache_rejected_before_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "cache.json").write_text(
                json.dumps({"feature_count": 312, "rows": 1, "allow_test": True})
            )
            with self.assertRaisesRegex(ValueError, "test cache forbidden"):
                load(path)

    def test_hash_binding_and_mmap_bulk(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            np.zeros((1, 2, 312), dtype="<f4").tofile(path / "x.f32")
            np.zeros((1, 2), dtype="<f4").tofile(path / "distance.f32")
            np.zeros((1, 2), dtype="<f4").tofile(path / "labels.f32")
            (path / "rows.jsonl").write_text(json.dumps({"id": "a", "split": "train"}) + "\n")
            names = ["x.f32", "distance.f32", "labels.f32", "rows.jsonl"]
            (path / "cache.json").write_text(
                json.dumps(
                    {
                        "feature_count": 312,
                        "rows": 1,
                        "allow_test": False,
                        "sha256": {name: sha(path / name) for name in names},
                    }
                )
            )
            _, rows, x, _, _ = load(path)
            self.assertIsInstance(x, np.memmap)
            self.assertEqual(rows[0]["id"], "a")
            (path / "x.f32").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "binding changed"):
                load(path)

    def test_curve_artifact_has_multiple_measured_points(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "curve.svg"
            curves = [
                {
                    "step": i,
                    "train": {"target_game_equal_mse": 1 / (i + 1)},
                    "validation": {"target_game_equal_mse": 0.5 + i / 20},
                }
                for i in [0, 1, 2, 5, 10]
            ]
            render_learning_curves(curves, output)
            text = output.read_text()
            self.assertEqual(text.count("<polyline"), 2)
            self.assertIn("Actual optimizer steps", text)


if __name__ == "__main__":
    unittest.main()
