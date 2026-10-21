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

    def test_original_lr_multiplicity_and_self_lr_no_refill_nn0(self):
        rows = self.rows()
        a, b, c = (bytes([i]) * 28 for i in (1, 2, 3))
        # Opaque synthetic keys: no board geometry or model inference here.
        assignments, observations, provenance = prefix_fixture_partition(
            rows, [(b, a), (c, c), (a, b)]
        )
        self.assertEqual(assignments, {a: 0, c: 1})
        self.assertEqual(observations, [b, a, c, a, b])
        self.assertEqual([r["self_lr"] for r in provenance], [False, True, False])
        self.assertEqual([r["orientation_observations"] for r in provenance], [2, 1, 2])
        self.assertEqual([r["history"] for r in provenance], [[], [13], [81, 163]])


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
