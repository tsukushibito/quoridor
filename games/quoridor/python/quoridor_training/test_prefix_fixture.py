"""Configured prefix fixture metadata; no teacher/model work in these tests."""

import copy
import io
from pathlib import Path
import struct
import tempfile
import unittest

from .public_static_prepare import prefix_fixture_rows, prefix_fixture_partition


class PrefixFixtureMetadata(unittest.TestCase):
    def rows(self):
        return [
            {"fixture": 0, "history": [], "functional_split": "T"},
            {"fixture": 1, "history": [13], "functional_split": "V"},
            {"fixture": 2, "history": [81, 163], "functional_split": "T"},
        ]

    def test_explicit_fixture_metadata_and_cross_lr_split_nn0(self):
        source = {"fixed_prefixes": self.rows()}
        self.assertEqual(prefix_fixture_rows(source), source["fixed_prefixes"])
        for change in (
            lambda r: r[1].update(fixture=0),
            lambda r: r[1].update(history=[True]),
            lambda r: r[1].update(history=[209]),
            lambda r: r[1].update(history=[13] * 201),
            lambda r: r[1].update(functional_split="sealed"),
            lambda r: r[1].update(functional_split="T"),
        ):
            rows = copy.deepcopy(source["fixed_prefixes"])
            change(rows)
            with self.assertRaises(ValueError):
                prefix_fixture_rows({"fixed_prefixes": rows})
        a, b, c = (bytes([i]) * 28 for i in (1, 2, 3))
        with self.assertRaisesRegex(ValueError, "crosses"):
            prefix_fixture_partition(self.rows()[:2], [(a, b), (b, a)])
        with self.assertRaises(ValueError):
            prefix_fixture_partition(self.rows(), [(a, b)])
        with self.assertRaises(ValueError):
            prefix_fixture_partition(self.rows(), [(a, b), (c, b"x"), (a, b)])

    def test_source_weights_reflection_and_teacher_views_are_separate_nn0(self):
        """Synthetic native-key ports, real PAIR37/sampler owners, no model/RNG."""
        from collections import Counter
        from types import SimpleNamespace
        from unittest.mock import patch
        import numpy as np

        from . import static_public
        from . import public_static_values
        from .sampling import ReflectionBatches

        a, b, c, d, symmetric = (bytes([i]) * 28 for i in range(1, 6))
        mirrors = {a: b, b: a, c: d, d: c, symmetric: symmetric}

        def reflected(keys):
            return np.asarray([mirrors[bytes(key)] for key in keys], dtype="V28")

        def grouped(keys):
            return np.asarray([min(bytes(key), mirrors[bytes(key)]) for key in keys], dtype="V28")

        rows = [
            {"fixture": i, "history": [i], "functional_split": "T" if i < 4 else "V"}
            for i in range(5)
        ]
        # Two source observations share a, one starts at b, one is self-LR.
        assignments, observations, provenance = prefix_fixture_partition(
            rows, [(a, b), (a, b), (b, a), (symmetric, symmetric), (c, d)]
        )
        self.assertEqual(observations, [a, a, b, symmetric, c])
        self.assertEqual([r["original_observations"] for r in provenance], [1] * 5)
        self.assertEqual([r["teacher_orientations"] for r in provenance], [2, 2, 2, 1, 2])
        self.assertEqual(assignments, {a: 0, symmetric: 0, c: 1})

        weights = Counter(observations)
        pairs = np.zeros(3, dtype=static_public.PAIR)
        for index, key in enumerate(sorted(assignments)):
            other = mirrors[key]
            pairs[index] = (
                key,
                (weights[key], 0 if key == other else weights[other]),
                assignments[key],
            )
        with (
            patch.object(static_public, "lr_group_keys", grouped),
            patch.object(static_public, "reflected_keys", reflected),
            patch.object(public_static_values, "reflected_keys", reflected),
        ):
            virtual = static_public.ClassObservations(pairs)
            self.assertEqual(virtual.counts, {"train": 4, "validation": 1})
            original_pair, original_orientation = virtual.offsets(
                "train", np.arange(4, dtype=np.int64)
            )
            self.assertEqual(original_pair.tolist(), [0, 0, 0, 2])
            self.assertEqual(original_orientation.tolist(), [0, 0, 1, 0])
            # A zero-weight reflected source view remains a required teacher view.
            self.assertEqual(pairs["observations"][1].tolist(), [1, 0])
            views = list(public_static_values.oriented_keys(pairs, 4))
            self.assertEqual(sum(len(keys) for _, _, keys in views), 5)
            self.assertEqual(public_static_values.actual_orientation_count(pairs), 5)
            keys = {bytes(key) for _, _, chunk in views for key in chunk}
            self.assertEqual(keys, {a, b, c, d, symmetric})
            values = np.zeros((3, 2), dtype="<f4")
            virtual.validate_values(values)
            values[1, 1] = np.nan
            with self.assertRaises(ValueError):
                virtual.validate_values(values)

            class CorpusPort:
                splits = np.asarray([0, 0, 0, 0, 1], dtype="u1")

                def batch(self, indices, mask=None):
                    return virtual.offsets("train", indices, mask, training=mask is not None)

            # Supply fixed mask inputs instead of constructing/advancing an RNG.
            reflected_batch = ReflectionBatches.__new__(ReflectionBatches)
            reflected_batch.corpus = CorpusPort()
            reflected_batch.probability = 0.5
            reflected_batch.generator = SimpleNamespace(
                random=lambda length: np.asarray([0.1, 0.9, 0.1, 0.9])
            )
            reflected_batch.training_seen = reflected_batch.reflected_seen = 0
            selected_pair, selected_orientation = reflected_batch.batch(
                np.arange(4, dtype=np.int64), training=True
            )
            self.assertEqual(selected_pair.tolist(), original_pair.tolist())
            self.assertEqual(selected_orientation.tolist(), [1, 0, 0, 0])
            self.assertEqual(reflected_batch.training_seen, 4)
            self.assertEqual(reflected_batch.reflected_seen, 2)


class PrefixFixturePublisher(unittest.TestCase):
    def test_pair37_explicit_partition_preserves_orientation_counts_and_refuses_gaps(self):
        """Root software only: existing NumPy publisher, synthetic opaque keys."""
        from .static_public import create_class_accumulator, write_class_table

        a, b = b"a" * 28, b"b" * 28
        with tempfile.TemporaryDirectory() as path:
            connection = create_class_accumulator(Path(path) / "index", max_bytes=65536)
            try:
                connection.executemany(
                    "INSERT INTO inputs VALUES (?,?,?,?)", [(a, 2, 3, 0), (b, 1, 0, 0)]
                )
                stream = io.BytesIO()
                counts = write_class_table(connection, stream, split_assignments={a: 0, b: 1})
                self.assertEqual(counts["qualified_original_observations"], 6)
                self.assertEqual((counts["train"], counts["validation"]), (5, 1))
                expected = a + struct.pack("<II", 2, 3) + b"\0"
                expected += b + struct.pack("<II", 1, 0) + b"\1"
                self.assertEqual(stream.getvalue(), expected)
                for assignments in ({a: 0}, {a: 0, b: 1, b"c" * 28: 0}, {a: 0, b: True}):
                    with self.assertRaises(ValueError):
                        write_class_table(connection, io.BytesIO(), split_assignments=assignments)
                with self.assertRaises(ValueError):
                    write_class_table(
                        connection, io.BytesIO(), split_seed=1, split_assignments={a: 0, b: 1}
                    )
                connection.execute("UPDATE inputs SET protection=1 WHERE key=?", (a,))
                with self.assertRaises(ValueError):
                    write_class_table(connection, io.BytesIO(), split_assignments={a: 0, b: 1})
            finally:
                connection.close()
