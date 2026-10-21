"""New pure joint stopping boundary; no optimizer, model or library imports."""

import unittest
from quoridor_training.policy_value_training import observe_joint_overfit


class JointStoppingTests(unittest.TestCase):
    def test_same_forward_policy_metrics_mask_illegal_logits(self):
        # UNRUN here: Root may admit this new tensor-only software definition.
        import math
        import torch
        from .policy_value_training import policy_diagnostics

        logits = torch.zeros((2, 209), dtype=torch.float32)
        logits[0, 0] = math.log(3)
        logits[0, 208] = 1000  # Illegal mass must never win.
        target = torch.zeros_like(logits)
        target[0, 0], target[0, 1], target[1, 3] = 0.2, 0.8, 1
        legal = torch.zeros_like(logits, dtype=torch.bool)
        legal[0, :2], legal[1, 3] = True, True
        measured = policy_diagnostics(logits, target, legal, torch.tensor([1.0, 3.0]))
        entropy = -(0.2 * math.log(0.2) + 0.8 * math.log(0.8))
        ce = -(0.2 * math.log(0.75) + 0.8 * math.log(0.25))
        self.assertAlmostEqual(measured["teacher_entropy"], entropy / 4, places=6)
        self.assertAlmostEqual(measured["policy_kl"], (ce - entropy) / 4, places=6)
        self.assertEqual(measured["policy_top1"], 0.75)
        self.assertEqual(measured["policy_top3"], 1.0)

    def test_three_completed_divergences_minimum_draws_and_restored_state(self):
        controls = dict(
            minimum_training_draws=8,
            overfit_observations=3,
            overfit_validation_absolute=0,
            overfit_validation_relative=0,
            overfit_training_absolute=0,
            overfit_training_relative=0,
        )
        state = {}
        self.assertFalse(observe_joint_overfit(controls, state, 0.5, 0.5, 0))
        self.assertFalse(observe_joint_overfit(controls, state, 0.6, 0.4, 1))
        self.assertFalse(observe_joint_overfit(controls, state, 0.7, 0.3, 2))
        # Fresh dict is the actual checkpoint publication/restoration representation.
        import json

        state = json.loads(json.dumps(state))
        self.assertFalse(observe_joint_overfit(controls, state, 0.8, 0.2, 3))
        self.assertTrue(observe_joint_overfit(controls, state, 0.9, 0.1, 8))
        self.assertEqual(state["joint_stop_reason"], "TRAIN_IMPROVES_VALIDATION_WORSENS")
        with self.assertRaises(ValueError):
            observe_joint_overfit(controls, state, 0.9, 0.1, 8)
        with self.assertRaises(ValueError):
            observe_joint_overfit(controls, state, float("nan"), 0.1, 9)
        self.assertFalse(observe_joint_overfit(controls, state, 0.8, 0.1, 9))
        self.assertEqual(state["joint_overfit_observations"], 0)


if __name__ == "__main__":
    unittest.main()
