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

    def test_saved_subset_publication_keeps_exact_parent_and_refuses_exposed_or_partial_members(
        self,
    ):
        import hashlib

        source_path = Path(__file__).with_name("public_static_prepare.py")
        names = {"prefix_fixture_rows", "series_fixture_rows", "saved_subset_fixture_authority"}
        tree = ast.parse(source_path.read_text())
        definitions = ast.Module(
            body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names],
            type_ignores=[],
        )
        namespace = {}
        exec(compile(definitions, str(source_path), "exec"), namespace)

        def reference(name):
            return {"path": "/synthetic/" + name, "sha256": "a" * 64}

        seed = 19
        parent_rows = [
            {
                "game": f"observation-{i}",
                "family": f"family-{i}",
                "prefix": [13 + i],
                "split": "train",
            }
            for i in range(3)
        ]
        original = {
            "partition": {
                "seed": seed,
                "schema": "synthetic-native",
                "rounding": "synthetic",
                "assignments": parent_rows,
            },
            "source_series": {a["game"]: a["game"] for a in parent_rows},
            "requested": {"train": 3, "validation": 0, "test": 0},
            "actual": {"train": 3, "validation": 0, "test": 0},
            "deficits": {"train": 0, "validation": 0, "test": 0},
        }
        ranked = sorted(
            [a["family"] for a in parent_rows],
            key=lambda f: (hashlib.sha256(f"{seed}:{f}".encode()).hexdigest(), f),
        )
        counts = {"train": 1, "validation": 1, "test": 0}
        authority = {
            "schema": "quoridor-prefix-series-saved-subset-v1",
            "source_schedule": reference("schedule"),
            "source_partition": reference("parent"),
            "source_observations": reference("native-history"),
            "source_config": reference("config"),
            "census": reference("census"),
            "exposure_parent": reference("selected-exposed"),
            "excluded_prefix_components": 1,
            "split_counts": counts,
            "actual_observations": counts,
        }
        inherited = {
            "prefixProjection": reference("TVH"),
            "clockBook": reference("clock"),
            "staticExclusionManifest": reference("static"),
        }
        source_config = {
            "split_seed": seed,
            "trajectory": {"split_counts": original["requested"]},
            "excluded_books": [inherited["prefixProjection"], inherited["clockBook"]],
            "excluded_static_inputs": inherited["staticExclusionManifest"],
        }
        census = {
            "schema": "research.identity-only-component-census.v1",
            "columns": [
                "rank0",
                "component",
                "member_ids",
                "source_series_ids",
                "disposition",
                "prospective_split",
            ],
            "selected64": authority["exposure_parent"],
            "partition": authority["source_partition"],
            "publishedScheduleByRef": authority["source_schedule"],
            "nativeInputConfig": authority["source_config"],
            "componentRankSeed": seed,
            "sourceExclusionAuthority": inherited,
            "counts": {
                "originalSurvivors": 3,
                "originalDeficit": 0,
                "excludedDev64": 1,
                "eligibleNamedScope": 2,
            },
            "prospective": {
                "selected": 2,
                "train": 1,
                "validation": 1,
                "holdout": 0,
                "deficitWithinNamedScope": 0,
            },
            "records": [],
        }
        for rank, family in enumerate(ranked):
            member = next(a["game"] for a in parent_rows if a["family"] == family)
            census["records"].append(
                [
                    rank,
                    family,
                    [member],
                    [member],
                    "excluded_dev64" if rank == 0 else "eligible_named_scope",
                    None if rank == 0 else "train" if rank == 1 else "validation",
                ]
            )
        selected = [
            {**a, "split": "train" if a["family"] == ranked[1] else "validation"}
            for a in parent_rows
            if a["family"] != ranked[0]
        ]
        partition = {
            **original,
            "partition": {**original["partition"], "assignments": selected},
            "source_series": {a["game"]: a["game"] for a in selected},
            "requested": counts,
            "actual": counts,
            "selection": authority,
        }
        common = {
            "schema": "quoridor-prefix-series-observations-v1",
            "partition": reference("selected"),
            "source_observations": authority["source_observations"],
            "teacher_labels": False,
        }
        fit = {
            **common,
            "observations": [
                {
                    "id": a["game"],
                    "source_series": a["game"],
                    "prefix": a["prefix"],
                    "family": a["family"],
                    "split": a["split"],
                }
                for a in selected
            ],
        }
        holdout = {**common, "observations": []}
        project = namespace["series_fixture_rows"]
        rows, held, lineage = project(fit, holdout, partition, original, census, source_config)
        self.assertEqual(sorted(r["functional_split"] for r in rows), ["T", "V"])
        self.assertEqual(held, [])
        self.assertFalse(lineage["H_teacher_labels"])
        self.assertEqual(len(original["partition"]["assignments"]), 3)
        for mutation in (
            "rank",
            "members",
            "exposure",
            "exposed_selected",
            "split",
            "partial",
            "parent",
        ):
            bad_census, bad_partition = copy.deepcopy(census), copy.deepcopy(partition)
            if mutation == "rank":
                bad_census["records"].reverse()
            elif mutation == "members":
                bad_census["records"][1][2] = []
            elif mutation == "exposure":
                bad_census["records"][0][4] = "eligible_named_scope"
            elif mutation == "exposed_selected":
                exposed = next(a for a in parent_rows if a["family"] == ranked[0])
                bad_partition["partition"]["assignments"][0] = {**exposed, "split": "train"}
            elif mutation == "split":
                bad_census["records"][1][5] = "validation"
            elif mutation == "partial":
                bad_partition["partition"]["assignments"].pop()
            else:
                bad_partition["selection"]["source_partition"] = reference("other-parent")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                project(fit, holdout, bad_partition, original, bad_census, source_config)


if __name__ == "__main__":
    unittest.main()
