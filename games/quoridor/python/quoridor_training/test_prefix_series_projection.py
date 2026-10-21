"""NN0 metadata projection: native partition/key ports are explicitly synthetic."""

import ast
import copy
from pathlib import Path
import unittest


class SeriesProjection(unittest.TestCase):
    def test_complete_native_fit_holdout_projection_and_cross_split_refusals(self):
        source = Path(__file__).with_name("public_static_prepare.py")
        names = {"prefix_fixture_rows", "series_fixture_rows", "reject_holdout_keys"}
        tree = ast.parse(source.read_text())
        definitions = ast.Module(
            body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names],
            type_ignores=[],
        )
        namespace = {}
        exec(compile(definitions, str(source), "exec"), namespace)
        rows = []
        assignments = []
        sources = {}
        for index, split in enumerate(("train", "validation", "test")):
            identity = f"synthetic-{index}"
            family = f"{index:064x}"
            prefix = [13 + index]
            sources[identity] = identity
            assignments.append(
                {"game": identity, "prefix": prefix, "family": family, "split": split}
            )
            rows.append(
                {
                    "id": identity,
                    "source_series": identity,
                    "prefix": prefix,
                    "family": family,
                    "split": split,
                    "root": {
                        "ruleset": "standard_2p_threefold",
                        "ply": 1,
                        "history": [["SYNTHETIC_NOT_NATIVE_GEOMETRY", 1]],
                    },
                }
            )
        common = {
            "schema": "quoridor-prefix-series-observations-v1",
            "partition": {"path": "/synthetic/partition", "sha256": "a" * 64},
            "source_observations": {
                "path": "/synthetic/native-history",
                "sha256": "b" * 64,
            },
            "teacher_labels": False,
        }
        fit = {**common, "observations": rows[:2]}
        holdout = {**common, "observations": rows[2:]}
        partition = {
            "partition": {"assignments": assignments},
            "source_series": sources,
            "requested": {"train": 1, "validation": 1, "test": 1},
            "actual": {"train": 1, "validation": 1, "test": 1},
            "deficits": {"train": 0, "validation": 0, "test": 0},
        }
        project = namespace["series_fixture_rows"]
        projected, excluded, lineage = project(fit, holdout, partition)
        self.assertEqual([r["functional_split"] for r in projected], ["T", "V"])
        self.assertEqual(len(excluded), 1)
        self.assertFalse(lineage["H_teacher_labels"])
        self.assertEqual(holdout["observations"][0]["split"], "test")
        missing = copy.deepcopy(holdout)
        missing["observations"] = []
        with self.assertRaisesRegex(ValueError, "census incomplete"):
            project(fit, missing, partition)
        crossed = copy.deepcopy(partition)
        crossed["partition"]["assignments"][2]["family"] = assignments[0]["family"]
        crossed_holdout = copy.deepcopy(holdout)
        crossed_holdout["observations"][0]["family"] = assignments[0]["family"]
        with self.assertRaisesRegex(ValueError, "component crosses"):
            project(fit, crossed_holdout, crossed)
        forged_source = copy.deepcopy(holdout)
        forged_source["observations"][0]["source_series"] = sources["synthetic-0"]
        with self.assertRaisesRegex(ValueError, "differs from native"):
            project(fit, forged_source, partition)
        labelled = {**holdout, "teacher_labels": True}
        with self.assertRaisesRegex(ValueError, "unlabelled"):
            project(fit, labelled, partition)
        reject = namespace["reject_holdout_keys"]
        keys = {b"a" * 28: 0}
        reject(keys, [(b"c" * 28, b"d" * 28)])
        with self.assertRaisesRegex(ValueError, "holdout exact/true-LR"):
            reject(keys, [(b"b" * 28, b"a" * 28)])
        with self.assertRaisesRegex(ValueError, "native holdout"):
            reject(keys, [(b"malformed", b"not-native")])


if __name__ == "__main__":
    unittest.main()
