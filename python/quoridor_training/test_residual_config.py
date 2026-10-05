"""NN0 checks for the maintained architecture/configuration boundary."""

import unittest

from .common import resolve_config


class ResidualConfigurationTests(unittest.TestCase):
    def test_explicit_residual_and_signed_distance_fit(self):
        config = resolve_config(
            overrides=[
                'model.architecture="distance_residual"',
                "model.distance_a=-0.25",
                "model.distance_b=8.0",
                'training.target="z"',
                'evaluation.monitor="row"',
            ]
        )
        self.assertEqual(config["model"]["architecture"], "distance_residual")
        self.assertEqual(config["model"]["distance_a"], -0.25)
        self.assertEqual(config["training"]["target"], "z")

    def test_unknown_model_and_nonfinite_coefficient_rejected(self):
        for value in ['model.architecture="unknown"', "model.distance_b=NaN"]:
            with self.assertRaises(ValueError):
                resolve_config(overrides=[value])

    def test_default_architecture_remains_explicit_scaled(self):
        self.assertEqual(resolve_config()["model"]["architecture"], "scaled")


if __name__ == "__main__":
    unittest.main()
