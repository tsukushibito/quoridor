"""Small fake checks; no Torch/model imports or real teacher labels."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from quoridor_training.route_training import (
    append_train_inputs,
    detailed_metrics,
    extra_train_inputs,
    model_input_key,
    select_cache_partition,
)
from quoridor_training.scaled_model import validate_statistics


class Adapter(unittest.TestCase):
    def fixtures(self):
        x = np.zeros((2, 2, 312), dtype=np.float32)
        x[0, 0, 1] = 1
        x[1, 0, 2] = 1
        d = np.zeros((2, 6), dtype=np.float32)
        d[:, :2] = [0.1, 0.2]
        y = np.zeros((2, 2), dtype=np.float32)
        rows = [
            {"id": "old-train", "group": "old-train", "split": "train"},
            {"id": "old-val", "group": "old-val", "split": "validation"},
        ]
        original = ({"dataset_sha": "original"}, rows, x, d, y)
        ex = np.repeat(x[1:2], 3, axis=0)
        ex[1:, 0, 2] = 0
        ex[1, 0, 3] = 1
        ex[2, 0, 4] = 1
        extra_rows = [
            {"id": f"new-{i}", "group": "new-family", "split": "train", "primary_eligible": True}
            for i in range(3)
        ]
        extra = (
            {"dataset_sha": "extra"},
            extra_rows,
            ex,
            np.repeat(d[:1, :2], 3, axis=0),
            np.zeros((3, 2), dtype=np.float32),
        )
        val = [{"id": "old-val", "state_key": "val-state", "history_key": "val-history"}]
        meta = {
            f"new-{i}": {
                "id": f"new-{i}",
                "group": "new-family",
                "split": "train",
                "state_key": f"new-state-{i}",
                "history_key": f"new-history-{i}",
            }
            for i in range(3)
        }
        meta["new-1"]["state_key"] = "val-state"
        meta["new-2"]["history_key"] = "val-history"
        return original, extra, val, meta

    def test_OR_exposure_retains_denominator_and_oldval(self):
        args = self.fixtures()
        binding, rows, _, _, _ = append_train_inputs(*args)
        self.assertEqual([r["primary_eligible"] for r in rows[2:]], [False] * 3)
        self.assertEqual(binding["extra_exposure_mask"]["planned_rows"], 3)
        self.assertEqual(binding["extra_exposure_mask"]["zeroeligible_groups"], 1)
        self.assertEqual(rows[1], args[0][1][1])

    def test_sealed_or_family_mixed_cache_rejected(self):
        args = self.fixtures()
        args[1][1][0]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "train-only"):
            append_train_inputs(*args)
        args = self.fixtures()
        args[1][1][0]["group"] = "old-val"
        with self.assertRaisesRegex(ValueError, "family overlap"):
            append_train_inputs(*args)

    def test_labels_do_not_change_exposure(self):
        a = self.fixtures()
        b = copy.deepcopy(a)
        b[1][4][:] = 0.75
        self.assertEqual(
            append_train_inputs(*a)[0]["extra_exposure_mask"],
            append_train_inputs(*b)[0]["extra_exposure_mask"],
        )

    def test_shared_cache_selects_train_before_statistics(self):
        original, extra, _, _ = self.fixtures()
        mixed = ({"schema": "fake"}, original[1], original[2], original[3][:, :2], original[4])
        _, rows, x, _, y = select_cache_partition(mixed, "train", ["old-train"])
        self.assertEqual([r["id"] for r in rows], ["old-train"])
        self.assertEqual(x.shape[0], 1)
        self.assertEqual(y.shape[0], 1)
        self.assertEqual(mixed[1][1]["split"], "validation")
        with self.assertRaisesRegex(ValueError, "unavailable"):
            select_cache_partition(mixed, "train", ["old-val"])
        mixed[1][1]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "partitions permitted"):
            select_cache_partition(mixed, "train")

    def test_partition_family_split_is_rejected(self):
        original, _, _, _ = self.fixtures()
        mixed = ({"schema": "fake"}, original[1], original[2], original[3][:, :2], original[4])
        mixed[1][1]["group"] = "old-train"
        with self.assertRaisesRegex(ValueError, "crosses partitions"):
            select_cache_partition(mixed, "train")

    def test_original_P2_ids_match_actual_STM_cache(self):
        original, extra, val, meta = self.fixtures()
        for i, row in enumerate(extra[1]):
            stm = [np.flatnonzero(extra[2][i, v]).tolist() for v in range(2)]
            # Fake opponent features are nonempty for this view-order witness.
            stm[1] = [5]
            extra[2][i, 1, 5] = 1
            meta[row["id"]].update({"side": 2, "ids": stm[::-1], "distance": extra[3][i].tolist()})
        append_train_inputs(original, extra, val, meta)
        meta["new-0"]["side"] = 1
        with self.assertRaisesRegex(ValueError, "actual STM input differs"):
            append_train_inputs(original, extra, val, meta)

    def test_censored_target_retains_rows_and_missing_denominators(self):
        rows = [
            {"group": "completed", "rootmean": 0.2, "z": 1, "cohort": "new"},
            {"group": "censored", "rootmean": None, "z": None, "cohort": "new"},
        ]
        result = detailed_metrics(rows, np.array([0.1, 0.5]), "rootmean", 0)
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["rootmean_rows"], 1)
        self.assertEqual(result["groups"]["censored"]["rootmean_rows"], 0)
        self.assertEqual(result["cohorts"]["new"]["games"], 2)
        self.assertEqual(result["z_rows"], 1)

    def test_native_metadata_schema_field_matches_published_writer(self):
        _, extra, _, meta = self.fixtures()
        for r in meta.values():
            r.update(
                {
                    "metadata_schema": "quoridor-tensor-row-v2",
                    "ids_order": "P1_then_P2",
                    "distance_order": "STM_then_opponent_f32",
                    "tensor_view_order": "STM_then_opponent",
                    "side": 1,
                    "ids": [[1], [2]],
                    "distance": [0.1, 0.2],
                    "ply": 8,
                    "feature_signature": "fake",
                }
            )
        args = SimpleNamespace(
            extra_train_groups=None, extra_train_cache="fake", extra_train_metadata="fake"
        )
        with (
            patch("quoridor_training.route_training.load_native_cache", return_value=extra),
            patch(
                "quoridor_training.route_training.read_input_metadata",
                return_value=list(meta.values()),
            ),
        ):
            result, metadata = extra_train_inputs(args)
            self.assertEqual(len(result[1]), 3)
            self.assertEqual(len(metadata), 3)
            meta["new-0"]["ids_order"] = "STM_then_opponent"
            with self.assertRaisesRegex(ValueError, "view orders differ"):
                extra_train_inputs(args)

    def test_f32_input_and_fixed_train_scale(self):
        x = np.zeros((2, 312), dtype=np.float32)
        self.assertEqual(
            model_input_key(x, np.array([0.1, 0.2])),
            model_input_key(x, np.array([0.1, 0.2], dtype=np.float32)),
        )
        with self.assertRaisesRegex(ValueError, "positive"):
            validate_statistics({"mu_f32": [0, 0], "sigma_f32": [0, 1]})


if __name__ == "__main__":
    unittest.main()
