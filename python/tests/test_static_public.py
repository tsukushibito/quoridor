"""New NN0 boundaries: multiplicity, true LR split closure and scalar alignment."""

import unittest

import numpy as np

from quoridor_training.public_features import (
    MODEL_INPUT,
    features,
    input_records,
    lr_group_keys,
    model_keys,
    reflected_keys,
)
from quoridor_training.static_public import CLASS, ClassObservations, exact_lookup


def fixture():
    rows = np.zeros(3, dtype=MODEL_INPUT)
    rows["geometry"]["pawns"] = ((3, 75), (5, 77), (12, 65))
    rows["geometry"]["stocks"] = 10
    rows["distance"] = ((0.1, 0.2), (0.1, 0.2), (0.3, 0.4))
    keys = model_keys(rows)
    # First two are an actual LR pair. Third is V, without an unused LR label.
    classes = np.zeros(3, dtype=CLASS)
    classes["key"] = keys
    classes["observations"] = (3, 1, 2)
    classes["split"] = (0, 0, 1)
    return classes[np.argsort(classes["key"])], keys


class StaticPublicTests(unittest.TestCase):
    def test_multiplicity_and_actual_reflected_target(self):
        classes, keys = fixture()
        corpus = ClassObservations(classes, chunk_rows=1)
        self.assertEqual(corpus.counts, {"train": 4, "validation": 2})
        slots = corpus.offsets("train", np.arange(4))
        counts = np.bincount(slots, minlength=3)
        np.testing.assert_array_equal(
            counts, np.where(classes["split"] == 0, classes["observations"], 0)
        )
        labels = np.array([0.125, -0.75, 0.625], dtype="<f4")
        mask = np.array([True, False, True, False])
        original = corpus.offsets("train", np.arange(4))
        x, distance, y = corpus.batch("train", np.arange(4), labels, mask, training=True)
        expected = exact_lookup(corpus.keys, reflected_keys(corpus.keys[original[mask]]))
        np.testing.assert_array_equal(y[mask], labels[expected])
        np.testing.assert_array_equal(
            x[mask], features(input_records(corpus.keys[expected])["geometry"])
        )
        np.testing.assert_array_equal(distance, input_records(corpus.keys[original])["distance"])
        np.testing.assert_array_equal(lr_group_keys(keys[:1]), lr_group_keys(keys[1:2]))
        self.assertNotEqual(
            float(labels[exact_lookup(corpus.keys, keys[:1])[0]]),
            float(labels[exact_lookup(corpus.keys, keys[1:2])[0]]),
        )

    def test_split_or_missing_lr_cannot_be_hidden(self):
        classes, keys = fixture()
        bad = classes.copy()
        bad["split"][exact_lookup(bad["key"], keys[1:2])] = 1
        with self.assertRaisesRegex(ValueError, "LR"):
            ClassObservations(bad)
        with self.assertRaisesRegex(ValueError, "LR"):
            ClassObservations(classes[classes["key"] != keys[1]])
        with self.assertRaisesRegex(ValueError, "outside"):
            exact_lookup(classes["key"], reflected_keys(keys[2:]))

    def test_zero_count_view_does_not_add_observations(self):
        classes, keys = fixture()
        classes["observations"][exact_lookup(classes["key"], keys[1:2])] = 0
        corpus = ClassObservations(classes)
        self.assertEqual(corpus.counts["train"], 3)
        labels = np.arange(3, dtype="<f4") / 4
        corpus.batch("train", np.arange(3), labels, np.ones(3, dtype=bool), training=True)
        with self.assertRaisesRegex(ValueError, "T-only"):
            corpus.offsets("validation", np.arange(2), np.ones(2, dtype=bool))
        with self.assertRaisesRegex(ValueError, "outside"):
            corpus.offsets("train", np.array([3]))

    def test_key_order_duplicate_and_nonfinite_refused(self):
        classes, _ = fixture()
        for bad in (classes[::-1], np.concatenate((classes[:1], classes))):
            with self.assertRaisesRegex(ValueError, "sorted"):
                ClassObservations(bad)
        broken = input_records(classes["key"]).copy()
        broken["distance"][0, 0] = np.nan
        classes["key"] = model_keys(broken)
        classes.sort(order="key")
        with self.assertRaisesRegex(ValueError, "finite"):
            ClassObservations(classes)

    def test_protected_alias_priority_and_original_zero_not_a_filter(self):
        import hashlib
        import io
        import tempfile
        from pathlib import Path

        from quoridor_training.static_public import (
            accumulate_inputs,
            create_class_accumulator,
            write_class_table,
        )

        classes, keys = fixture()
        # Choose a seed solely to populate both splits in this tiny NN0 fixture;
        # production seeds remain recipe-owned, never selected from outcomes.
        seed = next(
            n
            for n in range(100)
            if len(
                {
                    int.from_bytes(
                        hashlib.sha256(n.to_bytes(8, "little") + bytes(k)).digest()[:8],
                        "little",
                    )
                    % 2
                    for k in lr_group_keys(keys[[0, 2]])
                }
            )
            == 2
        )
        with tempfile.TemporaryDirectory() as directory:
            connection = create_class_accumulator(Path(directory) / "inputs.sqlite")
            try:
                mapping = accumulate_inputs(connection, keys[[0, 0, 1, 2]], np.zeros(4, dtype="u1"))
                self.assertEqual(len(mapping), 4 * 56)
                stream = io.BytesIO()
                counts = write_class_table(
                    connection,
                    stream,
                    split_seed=seed,
                    validation_parts=1,
                    split_parts=2,
                )
                self.assertEqual(counts["qualified_original_observations"], 4)
                table = np.frombuffer(stream.getvalue(), dtype=CLASS)
                self.assertEqual(int(table["observations"].sum()), 4)
                ClassObservations(table, chunk_rows=1)
                # Later existing sealed occurrence of the opposite LR input
                # protects the entire group, including earlier apparent T rows.
                accumulate_inputs(connection, keys[1:2], np.array([1], dtype="u1"))
                stream = io.BytesIO()
                counts = write_class_table(
                    connection,
                    stream,
                    split_seed=seed,
                    validation_parts=1,
                    split_parts=2,
                )
                table = np.frombuffer(stream.getvalue(), dtype=CLASS)
                self.assertEqual(counts["protected_original_observations"], 4)
                self.assertEqual(counts["train"] + counts["validation"], 1)
                self.assertFalse(
                    np.isin(lr_group_keys(keys[:1]), lr_group_keys(table["key"])).any()
                )
            finally:
                connection.close()
            with self.assertRaises(FileExistsError):
                create_class_accumulator(Path(directory) / "inputs.sqlite")

    def test_original_half_decoder_never_opens_labels_or_naive_lr(self):
        import io
        import tempfile
        import zipfile
        from pathlib import Path

        from quoridor_training.public_sigma import original_plane_chunks

        source = np.zeros((4, 8, 9, 9), dtype="<f4")
        source[0].fill(1)
        source[1].fill(2)
        source[2:].fill(99)  # old incorrect reflected half must never be yielded
        body = io.BytesIO()
        np.save(body, source)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.npz"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("states.npy", body.getvalue())
                # No values.npy at all: new static ingress cannot touch labels.
            batches = list(original_plane_chunks(path, {"rows": 4}, with_values=False))
            self.assertEqual(len(batches), 1)
            ids, planes, labels = batches[0]
            np.testing.assert_array_equal(ids, np.array([0, 1], dtype="<u4"))
            np.testing.assert_array_equal(planes[:, 0, 0, 0], [1, 2])
            self.assertIsNone(labels)
            with self.assertRaises(KeyError):
                list(original_plane_chunks(path, {"rows": 4}, with_values=True))


if __name__ == "__main__":
    unittest.main()
