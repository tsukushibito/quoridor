"""Separate actual game weighting from pre-outcome family weighting."""

from types import SimpleNamespace
import unittest

from .step_measurements import measurements


class StepMeasurementGroups(unittest.TestCase):
    def test_games_and_families_have_independent_denominators(self):
        corpus = SimpleNamespace(
            rows=[
                {
                    "group": "family-a",
                    "game": "a1",
                    "outcome_steps": 80,
                    "terminal_margin": 0,
                    "z": 1,
                },
                {
                    "group": "family-a",
                    "game": "a1",
                    "outcome_steps": 80,
                    "terminal_margin": 0,
                    "z": 1,
                },
                {
                    "group": "family-a",
                    "game": "a2",
                    "outcome_steps": 80,
                    "terminal_margin": 0,
                    "z": 1,
                },
                {
                    "group": "family-b",
                    "game": "b1",
                    "outcome_steps": 80,
                    "terminal_margin": 0,
                    "z": 1,
                },
            ]
        )
        result = measurements(corpus, range(4), [80, 80, 0, 0], "outcome_steps", 0, "F")
        self.assertEqual(result["games"], 3)
        self.assertEqual(result["families"], 2)
        self.assertEqual(result["target_mse"], 0.5)
        self.assertAlmostEqual(result["target_game_equal_mse"], 2 / 3)
        self.assertAlmostEqual(result["outcome_steps_family_equal_mse"], 2 / 3)
        self.assertEqual(result["constant_game_equal_mse"], 1)
        result = measurements(corpus, range(3), [80, 80, 0], "outcome_steps", 0, "F")
        self.assertAlmostEqual(result["target_game_equal_mse"], 0.5)
        self.assertAlmostEqual(result["outcome_steps_family_equal_mse"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
