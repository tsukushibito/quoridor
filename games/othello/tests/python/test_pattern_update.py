"""Analytic single-step checks only; never call fit or write model artifacts."""

import unittest

import numpy as np

from othello_training import pattern
from othello_training.train import loss, sgd_step


class PatternUpdate(unittest.TestCase):
    def test_one_normalized_update_matches_analytic_gradient(self):
        parameters = np.array([2.0, -1.0])
        sgd_step(parameters, {0: 2, 1: -1}, 10)
        np.testing.assert_allclose(parameters, [2.19996, -1.09998], rtol=0, atol=1e-12)

    def test_nonfinite_update_and_export_stop(self):
        with self.assertRaises(ValueError):
            loss(np.array([float("nan")]), [])
        with self.assertRaises(ValueError):
            sgd_step(np.array([float("nan")]), {0: 1}, 0)
        parameters = [0.0] * pattern.PARAMETERS
        parameters[0] = float("inf")
        with self.assertRaises(ValueError):
            pattern.quantize(parameters)
        parameters[0] = 32768
        with self.assertRaises(ValueError):
            pattern.quantize(parameters)


if __name__ == "__main__":
    unittest.main()
