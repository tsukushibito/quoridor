"""Epoch coverage and loss weighting without model inference."""

import unittest

import numpy as np

from .common import resolve_config
from .sampling import EpochSampler, loss_weights


class EpochSamplingTests(unittest.TestCase):
    def test_complete_epochs_and_small_tail(self):
        training = [2, 5, 7, 11, 13, 17, 19]
        sampler = EpochSampler(training, 3, 123)
        epochs = []
        for number in range(2):
            batches = []
            for size in [3, 3, 1]:
                self.assertEqual(sampler.next_batch_size, size)
                batches.append(sampler.next_batch())
            self.assertEqual([len(batch) for batch in batches], [3, 3, 1])
            rows = np.concatenate(batches)
            self.assertEqual(sorted(rows.tolist()), training)
            self.assertEqual(len(np.unique(rows)), len(training))
            self.assertNotIn(23, rows)  # A validation row never enters the training index set.
            self.assertEqual(sampler.completed_epochs, number + 1)
            self.assertEqual(sampler.partial_epoch_fraction, 0)
            epochs.append(rows)
        self.assertFalse(np.array_equal(*epochs))
        self.assertEqual(sampler.seen, 14)

    def test_seed_reproduction_and_partial_epoch(self):
        left, right = EpochSampler(range(7), 3, 42), EpochSampler(range(7), 3, 42)
        for _ in range(4):
            np.testing.assert_array_equal(left.next_batch(), right.next_batch())
        self.assertEqual(left.completed_epochs, 1)
        self.assertEqual(left.partial_epoch_fraction, 3 / 7)
        self.assertEqual(left.seen, 10)

    def test_invalid_training_rows(self):
        for rows, batch in [([], 3), ([1, 1], 3), ([1], 0)]:
            with self.assertRaises(ValueError):
                EpochSampler(rows, batch, 1)

    def test_group_normalization_and_objective(self):
        groups = ["short", "long", "long", "long"]
        squared_errors = np.asarray([4, 1, 1, 1], dtype=np.float32)
        weighted = loss_weights(groups, "group")
        self.assertAlmostEqual(float(weighted.mean()), 1)
        self.assertAlmostEqual(
            float((weighted * squared_errors).mean()),
            (4 + 1) / 2,
            delta=4 * np.finfo(np.float32).eps,
        )
        self.assertAlmostEqual(float(squared_errors.mean()), (4 + 3) / 4)
        np.testing.assert_array_equal(loss_weights(groups, "row"), np.ones(4))

    def test_config_default_and_no_double_group_weight(self):
        self.assertEqual(resolve_config()["training"]["sampling"], "epoch")
        cfg = resolve_config(overrides=('training.loss_weighting="group"',))
        self.assertEqual(cfg["training"]["sampling"], "epoch")
        with self.assertRaises(ValueError):
            resolve_config(
                overrides=('training.sampling="game"', 'training.loss_weighting="group"')
            )


if __name__ == "__main__":
    unittest.main()
