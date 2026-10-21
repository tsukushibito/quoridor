"""New observation arithmetic definitions; no model, sampler or old-suite replay."""

import unittest

import numpy as np

from quoridor_training.public_replay import _add_outcome_slice, _outcome_slice_result


class OutcomeSliceTests(unittest.TestCase):
    def test_family_macro_differs_from_row_and_draw_is_separate(self):
        bank = {}
        _add_outcome_slice(
            bank, np.array([0.0, 1.0, 1.0]), np.array([0, 0, 1]), np.array([4, 9, 9])
        )
        result = _outcome_slice_result(bank)
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["canonical_family_count"], 2)
        self.assertAlmostEqual(result["row_z_mse"], 1 / 3)
        self.assertEqual(result["canonical_family_z_mse"], 0.25)
        self.assertEqual(result["z_sign"]["0"]["rows"], 2)
        self.assertEqual(result["z_sign"]["0"]["prediction_zero_rows"], 1)
        self.assertEqual(result["draw_rows"], 2)
        self.assertEqual(result["draw_mean_abs_post"], 0.5)
        self.assertEqual(result["decisive_rows"], 1)
        self.assertEqual(result["decisive_correct_sign_rows"], 1)
        self.assertEqual(result["z_sign"]["1"]["rows"], 1)
        self.assertEqual(result["saturated_99_rows"], 2)

    def test_actual_f32_threshold_neighbors_and_signed_zero(self):
        p = np.asarray(
            [
                np.float32(0.9),
                np.nextafter(np.float32(0.9), np.float32(np.inf)),
                -np.float32(0.99),
                np.nextafter(np.float32(0.99), np.float32(-np.inf)),
                -0.0,
            ],
            dtype=np.float32,
        )
        bank = {}
        _add_outcome_slice(bank, p, np.zeros(len(p)))
        result = _outcome_slice_result(bank)
        self.assertEqual(result["saturated_90_rows"], 3)
        self.assertEqual(result["saturated_99_rows"], 1)
        self.assertEqual(result["z_sign"]["0"]["prediction_zero_rows"], 1)
        self.assertIsNone(result["canonical_family_count"])

    def test_chunked_family_membership_and_empty_band(self):
        bank = {}
        _add_outcome_slice(bank, np.array([1.0]), np.array([-1]), np.array([8]))
        _add_outcome_slice(bank, np.array([0.0, 1.0]), np.array([0, 1]), np.array([8, 4]))
        result = _outcome_slice_result(bank)
        self.assertEqual(result["canonical_family_count"], 2)
        self.assertEqual(result["canonical_family_z_mse"], 1.0)
        self.assertEqual(sum(v["rows"] for v in result["z_sign"].values()), 3)
        empty = {}
        _add_outcome_slice(empty, np.array([]), np.array([]), np.array([], dtype=int))
        result = _outcome_slice_result(empty)
        self.assertEqual(result["rows"], 0)
        self.assertEqual(result["canonical_family_count"], 0)
        self.assertIsNone(result["row_z_mse"])
        self.assertIsNone(result["canonical_family_z_mse"])
        self.assertIsNone(result["saturation_99_fraction"])
        self.assertIsNone(result["draw_mean_abs_post"])
