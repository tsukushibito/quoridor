"""Selected-target/provenance checks without models or numerical frameworks."""

import math
import unittest

from .common import selected_teacher_types, target_value, validate_target_tensor


def row(**changes):
    return {
        "split": "train",
        "primary_eligible": True,
        "teacher_type": "external_terminal_outcome",
        "rootmean": None,
        "z": 1.0,
    } | changes


class SelectedTargetTests(unittest.TestCase):
    def test_external_z_does_not_need_rootmean(self):
        self.assertEqual(selected_teacher_types([row()], "z"), {"external_terminal_outcome"})
        validate_target_tensor([row()], [1.0], "z")

    def test_missing_z_is_not_rootmean(self):
        r = row(rootmean=0.75, z=None)
        self.assertIsNone(target_value(r, "z"))
        validate_target_tensor([r], [math.nan], "z")
        with self.assertRaises(ValueError):
            validate_target_tensor([r], [0.75], "z")

    def test_invalid_selected_labels_rejected(self):
        for value in (math.inf, math.nan, 1.01, -1.01, True, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                target_value(row(z=value), "z")

    def test_tensor_column_cannot_be_exchanged(self):
        with self.assertRaises(ValueError):
            validate_target_tensor([row(rootmean=-1)], [-1], "z")

    def test_eligible_teacher_mix_rejected(self):
        with self.assertRaises(ValueError):
            selected_teacher_types([row(), row(teacher_type="mcts")], "z")

    def test_missing_or_excluded_teacher_does_not_mix(self):
        rows = [
            row(),
            row(z=None, teacher_type="mcts"),
            row(primary_eligible=False, teacher_type="other"),
        ]
        self.assertEqual(selected_teacher_types(rows, "z"), {"external_terminal_outcome"})

    def test_test_partition_rejected(self):
        with self.assertRaises(ValueError):
            selected_teacher_types([row(split="test")], "z")

    def test_native_explicit_draw_is_not_globally_removed(self):
        # Public reason-unavailable zeros are excluded in its dataset predicate.
        # The general trainer must retain a separately proved native RuleA draw.
        validate_target_tensor([row(z=0, teacher_type="mcts")], [0], "z")
        self.assertEqual(selected_teacher_types([row(z=0, teacher_type="mcts")], "z"), {"mcts"})


if __name__ == "__main__":
    unittest.main()
