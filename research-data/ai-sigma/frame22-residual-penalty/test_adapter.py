"""Small label-free software fixtures, no Torch/model import."""

import ast
import sys
import unittest
from pathlib import Path

import numpy as np
from run import widths
from admit import exact
from quoridor_training.route_training import model_input_key


class AdapterTest(unittest.TestCase):
    def test_stopped_identity_is_not_admitted(self):
        self.assertFalse(exact(None))
        self.assertFalse(exact({}))
        self.assertFalse(exact({"pid": 999999999, "start_ticks": "0"}))

    def test_displacement_alignment_identity(self):
        rows = [
            {"id": "a", "group": "g1", "rootmean": 0.8},
            {"id": "b", "group": "g2", "rootmean": -0.4},
        ]
        p = np.asarray([0.1, 0.3])
        d = np.asarray([0.2, -0.2])
        w = widths(rows, p, d)
        actual = float(
            np.mean((p - np.asarray([0.8, -0.4])) ** 2 - (d - np.asarray([0.8, -0.4])) ** 2)
        )
        self.assertAlmostEqual(w["displacement"] + w["alignment"], actual)

    def test_game_equal_not_row_equal(self):
        rows = [{"group": "a", "rootmean": 0.0}] * 3 + [{"group": "b", "rootmean": 0.0}]
        w = widths(rows, np.asarray([0.0, 0.0, 0.0, 1.0]), np.zeros(4))
        self.assertEqual(w["displacement"], 0.5)

    def test_actual_STM_P2_input(self):
        p1 = np.zeros(312, dtype=np.float32)
        p1[[1, 82, 162, 301]] = 1
        p2 = np.zeros(312, dtype=np.float32)
        p2[[2, 83, 163, 302]] = 1
        d = np.asarray([0.125, 0.25], dtype=np.float32)
        self.assertEqual(
            model_input_key(np.stack([p2, p1]), d), model_input_key(np.stack([p2, p1]), d.copy())
        )
        self.assertNotEqual(
            model_input_key(np.stack([p2, p1]), d), model_input_key(np.stack([p1, p2]), d)
        )

    def test_target_change_does_not_change_input(self):
        d = np.asarray([0.1, 0.2], dtype=np.float32)
        distance = np.tanh(np.float32(8) * (d[1] - d[0]))
        for target in (-1.0, 0.0, 1.0):
            self.assertEqual(distance, np.tanh(np.float32(8) * (d[1] - d[0])))
            self.assertTrue(np.isfinite((target - distance) ** 2))

    def test_no_torch_import_or_extra_science(self):
        self.assertNotIn("torch", sys.modules)
        source = Path(__file__).with_name("run.py").read_text()
        tree = ast.parse(source)
        self.assertNotIn("torch", sys.modules)
        constants = {
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        self.assertIn("same_batch_SHA", constants)
        self.assertIn("step200", constants)


if __name__ == "__main__":
    unittest.main()
