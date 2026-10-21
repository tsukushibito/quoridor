"""Read only this phase's new Rust fixture; model/optimizer/native calls are absent."""

import os
from pathlib import Path
import unittest

import numpy as np

from .cache import load
from .sampling import ReflectionBatches, EpochSampler
from .public_features import features, reflect
from .step_measurements import measurements
from .train import training_statistics


class NativeTerminalFixture(unittest.TestCase):
    def setUp(self):
        path = os.environ.get("QUORIDOR_TERMINAL_CACHE_FIXTURE")
        if not path:
            self.skipTest("only explicit new Rust fixture is eligible")
        self.corpus = load(Path(path) / "cache")

    def test_canonical_labels_geometry_integer_distance_and_batch(self):
        c = self.corpus
        self.assertEqual(c.row_count, 2)
        self.assertEqual(c.labels.shape, (2, 3))
        np.testing.assert_array_equal(c.labels[:, 1:], [[1, 1], [-1, -1]])
        np.testing.assert_array_equal(c.integer_distances, [[8, 8], [8, 8]])
        for i in (0, 1):
            row = c.rows[i]
            self.assertEqual(row["outcome_steps"], 80 * row["z"])
            self.assertEqual(row["terminal_margin"], row["z"])
        x, d, y = c.batch([1, 0])
        self.assertEqual(x.shape, (2, 2, 312))
        np.testing.assert_array_equal(d, np.full((2, 2), np.float32(0.1)))
        np.testing.assert_array_equal(y[:, 1:], [[-1, -1], [1, 1]])
        self.assertEqual(c.groups[0], c.groups[1])
        c.verify_binding()

    def test_reflection_sampler_preserve_targets_tail_and_no_eval_RNG(self):
        c = self.corpus
        reflection = ReflectionBatches(c, 0.5, 19080314)
        sampler = EpochSampler([0, 1], 1, 19080311)
        batches = [sampler.next_batch(), sampler.next_batch()]
        self.assertEqual(sorted(int(v[0]) for v in batches), [0, 1])
        self.assertEqual(sampler.completed_epochs, 1)
        before = str(reflection.generator.bit_generator.state)
        reflection.batch([0], training=False)
        self.assertEqual(str(reflection.generator.bit_generator.state), before)
        rows = c.records([0, 1])
        x, d, y = c.batch([0, 1], np.array([True, False]))
        np.testing.assert_array_equal(x[0], features(reflect(rows["geometry"][:1]))[0])
        np.testing.assert_array_equal(y, c.labels)
        np.testing.assert_array_equal(d, rows["distance"])

    def test_T_only_moments_target_independent_floor_and_both_errors(self):
        c = self.corpus
        a, _ = training_statistics(c, np.array([0, 1]), 1)
        b, _ = training_statistics(c, np.array([0, 1]), 2)
        self.assertEqual(a, b)
        self.assertTrue(a["target_independent"])
        self.assertEqual(a["zero_variance_coordinates"], [True, True])
        self.assertEqual(a["mu_f32"], [float(np.float32(0.1))] * 2)
        result = measurements(c, [0, 1], [80, -80], "outcome_steps", 0, "F")
        self.assertEqual(result["target_mse"], 0)
        self.assertEqual(result["terminal_margin_raw_mse"], 79**2)
        self.assertEqual(result["terminal_margin_mse"], 79**2 / 6400)
        self.assertEqual(result["z_sign_accuracy"], 1)


if __name__ == "__main__":
    unittest.main()
