"""NN0 checks for compact LR pairs and exact original-orientation multiplicity."""

import io
from pathlib import Path
import tempfile
import unittest

import numpy as np

from quoridor_training.public_features import (
    MODEL_INPUT,
    model_keys,
    lr_group_keys,
    reflected_keys,
)
from quoridor_training.static_public import (
    PAIR,
    ClassObservations,
    accumulate_inputs,
    create_class_accumulator,
    write_class_table,
    class_split,
)


def fixture():
    original = np.zeros(2, dtype=MODEL_INPUT)
    original["geometry"]["pawns"] = ((3, 75), (12, 65))
    original["geometry"]["stocks"] = 10
    original["distance"] = ((0.1, 0.2), (0.3, 0.4))
    keys = lr_group_keys(model_keys(original))
    pairs = np.zeros(2, dtype=PAIR)
    pairs["key"], pairs["observations"], pairs["split"] = keys, ((3, 1), (2, 0)), (0, 1)
    return pairs, keys


class StaticPairTests(unittest.TestCase):
    def test_shared_split_literal_digest_and_v_requires_both_orientations(self):
        import hashlib

        pairs, keys = fixture()
        seed = 32442026101702
        for key in keys:
            raw = bytes(key)
            digest = hashlib.sha256(
                b"full-public-teachers-v1|split|" + seed.to_bytes(8, "little") + raw
            ).digest()
            expected = int(10 * int.from_bytes(digest[:8], "big") >= 9 * 2**64)
            self.assertEqual(class_split(raw, seed), expected)
            self.assertEqual(
                class_split(bytes(lr_group_keys(reflected_keys(np.array([key])))[0]), seed),
                expected,
            )
        labels = np.array([[0.25, -0.75], [0.5, np.nan]], dtype="<f4")
        with self.assertRaisesRegex(ValueError, "finite"):
            ClassObservations(pairs).validate_values(labels)

    def test_original_multiplicity_and_independent_lr_scalar(self):
        pairs, _ = fixture()
        corpus = ClassObservations(pairs, chunk_rows=1)
        self.assertEqual(PAIR.itemsize, 37)
        self.assertEqual(corpus.counts, {"train": 4, "validation": 2})
        pair, orientation = corpus.offsets("train", np.arange(4))
        np.testing.assert_array_equal(pair, [0, 0, 0, 0])
        np.testing.assert_array_equal(orientation, [0, 0, 0, 1])
        labels = np.array([[0.25, -0.75], [0.5, 0.625]], dtype="<f4")
        corpus.validate_values(labels, chunk_rows=1)
        mask = np.array([True, False, True, False])
        x, distance, y = corpus.batch("train", np.arange(4), labels, mask, training=True)
        np.testing.assert_array_equal(y, [-0.75, 0.25, -0.75, -0.75])
        np.testing.assert_array_equal(x[:, 0, :81].argmax(axis=1), [5, 3, 5, 5])
        np.testing.assert_array_equal(
            distance, np.tile(np.array([[0.1, 0.2]], dtype="<f4"), (4, 1))
        )
        with self.assertRaisesRegex(ValueError, "T-only"):
            corpus.offsets("validation", np.arange(2), np.ones(2, dtype=bool))

    def test_missing_required_orientation_is_not_a_canonical_fallback(self):
        pairs, _ = fixture()
        corpus = ClassObservations(pairs)
        labels = np.array([[0.25, np.nan], [0.5, np.nan]], dtype="<f4")
        with self.assertRaisesRegex(ValueError, "finite"):
            corpus.validate_values(labels)
        with self.assertRaisesRegex(ValueError, "finite"):
            corpus.batch("train", np.arange(4), labels)
        with self.assertRaisesRegex(ValueError, "outside"):
            corpus.offsets("train", np.array([4]))

    def test_pair_key_uniqueness_canonicality_and_symmetric_counts(self):
        pairs, keys = fixture()
        for bad in (pairs[::-1], np.concatenate((pairs[:1], pairs))):
            with self.assertRaisesRegex(ValueError, "canonical sorted"):
                ClassObservations(bad)
        bad = pairs.copy()
        bad["key"][0] = reflected_keys(keys[:1])[0]
        with self.assertRaisesRegex(ValueError, "canonical sorted"):
            ClassObservations(bad)
        symmetric = np.zeros(1, dtype=MODEL_INPUT)
        symmetric["geometry"]["pawns"] = (4, 76)
        symmetric["geometry"]["stocks"] = 10
        symmetric["distance"] = (0.1, 0.1)
        bad = pairs.copy()
        bad["key"][0] = model_keys(symmetric)[0]
        with self.assertRaisesRegex(ValueError, "symmetric"):
            ClassObservations(bad)

    def test_cross_batch_protected_alias_wins_before_publication(self):
        _, keys = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.sqlite"
            connection = create_class_accumulator(path, max_bytes=65536)
            try:
                self.assertEqual(connection.execute("PRAGMA max_page_count").fetchone()[0], 16)
                first = np.concatenate((keys[:1], keys[:1], reflected_keys(keys[:1]), keys[1:]))
                mapping = accumulate_inputs(connection, first, np.zeros(4, dtype="u1"))
                self.assertEqual(len(mapping), 4 * 56)
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM inputs").fetchone()[0], 2)
                # A later protected reflected alias removes all prior originals
                # of that pair, without reading z or teacher values.
                accumulate_inputs(connection, reflected_keys(keys[:1]), np.array([1], dtype="u1"))
                stream = io.BytesIO()
                counts = write_class_table(connection, stream, split_seed=11)
                table = np.frombuffer(stream.getvalue(), dtype=PAIR)
                self.assertEqual(counts["qualified_original_observations"], 5)
                self.assertEqual(counts["protected_original_observations"], 4)
                self.assertEqual(counts["train"] + counts["validation"], 1)
                self.assertEqual(len(table), 1)
                self.assertEqual(table["key"][0], keys[1])
            finally:
                connection.close()
            with self.assertRaises(FileExistsError):
                create_class_accumulator(path, max_bytes=65536)


if __name__ == "__main__":
    unittest.main()
