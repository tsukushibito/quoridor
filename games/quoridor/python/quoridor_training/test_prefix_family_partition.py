"""New metadata-only family boundary; no native geometry, model or teacher."""

import unittest


class PrefixFamilyPartitionTests(unittest.TestCase):
    def test_large_declared_source_retains_native_64_row_boundary(self):
        from unittest.mock import patch
        from .public_static_prepare import native_prefix_keys, prefix_fixture_rows

        rows = [
            dict(
                fixture=i,
                family=i // 64,
                history=[i % 64],
                functional_split="T" if i < 64 else "V",
            )
            for i in range(65)
        ]
        self.assertEqual(prefix_fixture_rows(dict(fixed_prefixes=rows)), rows)
        counts = []

        class Function:
            def __call__(self, actions, length, starts, count, keys, status):
                counts.append(count)
                return 0

        class Library:
            quoridor_public_prefix_keys = Function()

        # Explicit native ABI metadata port; zero keys are synthetic and never
        # published or accepted as native legal/geometry/model evidence.
        with patch("ctypes.CDLL", return_value=Library()):
            pairs = native_prefix_keys(rows, "/synthetic/native")
        self.assertEqual(counts, [64, 1])
        self.assertEqual(len(pairs), 65)
        with self.assertRaises(ValueError):
            prefix_fixture_rows(dict(fixed_prefixes=[*rows[:64], {**rows[0], "fixture": 99}]))
        with self.assertRaises(ValueError):
            prefix_fixture_rows(
                dict(
                    fixed_prefixes=[{k: v for k, v in row.items() if k != "family"} for row in rows]
                )
            )

    def test_declared_family_stays_in_one_split_and_lineage_survives(self):
        from .public_static_prepare import prefix_fixture_partition, prefix_fixture_rows

        rows = [
            {"fixture": 0, "family": 7, "history": [], "functional_split": "T"},
            {"fixture": 1, "family": 7, "history": [13], "functional_split": "T"},
            {"fixture": 2, "family": 8, "history": [67], "functional_split": "V"},
        ]
        self.assertIs(prefix_fixture_rows({"fixed_prefixes": rows}), rows)
        # Explicit synthetic native-key ports only, not generated legal boards.
        pairs = [(bytes([i]) * 28, bytes([i + 10]) * 28) for i in range(3)]
        _, _, provenance = prefix_fixture_partition(rows, pairs)
        self.assertEqual([r["family"] for r in provenance], [7, 7, 8])
        self.assertEqual([r["history"] for r in provenance], [[], [13], [67]])
        for replacement in (7, True, -1):
            changed = [dict(row) for row in rows]
            changed[-1]["family"] = replacement
            with self.assertRaises(ValueError):
                prefix_fixture_rows({"fixed_prefixes": changed})
        mixed = [dict(row) for row in rows]
        del mixed[-1]["family"]
        with self.assertRaises(ValueError):
            prefix_fixture_rows({"fixed_prefixes": mixed})


if __name__ == "__main__":
    unittest.main()
