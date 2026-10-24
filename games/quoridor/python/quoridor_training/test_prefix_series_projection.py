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

    def test_coverage_saved_subset_preserves_H_and_refuses_rank_or_partial_H_nn0(self):
        import hashlib

        source_path = Path(__file__).with_name("public_static_prepare.py")
        names = {"prefix_fixture_rows", "series_fixture_rows", "saved_subset_fixture_authority"}
        tree = ast.parse(source_path.read_text())
        definitions = ast.Module(
            body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names],
            type_ignores=[],
        )
        ns = {}
        exec(compile(definitions, str(source_path), "exec"), ns)
        ref = lambda name: {"path": "/synthetic/" + name, "sha256": "a" * 64}
        old = [
            {"game": f"m{i}", "family": f"f{i}", "prefix": [13 + i], "split": "train"}
            for i in range(3)
        ]
        seed = 19
        ranked = sorted(
            [a["family"] for a in old],
            key=lambda f: (hashlib.sha256(f"{seed}:{f}".encode()).hexdigest(), f),
        )
        counts = {"train": 1, "validation": 1, "test": 1}
        split = dict(zip(ranked, ("train", "validation", "test"), strict=True))
        original = {
            "partition": {
                "seed": seed,
                "schema": "synthetic-native",
                "rounding": "synthetic",
                "assignments": old,
            },
            "source_series": {a["game"]: a["game"] for a in old},
            "requested": {"train": 8192, "validation": 0, "test": 0},
            "actual": {"train": 3, "validation": 0, "test": 0},
            "deficits": {"train": 8189, "validation": 0, "test": 0},
        }
        authority = {
            "schema": "quoridor-prefix-series-saved-subset-v2",
            "source_schedule": ref("schedule"),
            "source_partition": ref("parent"),
            "source_observations": ref("history"),
            "source_config": ref("config"),
            "census": ref("census"),
            "exposure_parent": ref("exclusions"),
            "excluded_prefix_components": 0,
            "split_counts": counts,
            "actual_observations": counts,
        }
        excluded = {
            "excluded_books": [ref("all-old-prefix-components")],
            "excluded_static_inputs": ref("old-static-inputs"),
        }
        config = {
            "families": 8192,
            "split_seed": seed,
            "trajectory": {
                "split_counts": original["requested"],
                "wall_layer_observations": [0, 1, 0],
            },
            **excluded,
        }
        census = {
            "schema": "research.identity-only-component-census.v2",
            "columns": [
                "rank0",
                "component",
                "member_ids",
                "source_series_ids",
                "disposition",
                "prospective_split",
            ],
            "exposureParent": authority["exposure_parent"],
            "partition": authority["source_partition"],
            "publishedScheduleByRef": authority["source_schedule"],
            "nativeInputConfig": authority["source_config"],
            "componentRankSeed": seed,
            "sourceExclusionAuthority": excluded,
            "counts": {
                "originalSurvivors": 3,
                "originalDeficit": 8189,
                "excludedComponents": 0,
                "eligibleNamedScope": 3,
            },
            "prospective": {
                "selected": 3,
                "train": 1,
                "validation": 1,
                "holdout": 1,
                "deficitWithinNamedScope": 0,
            },
            "records": [
                [
                    i,
                    f,
                    [next(a["game"] for a in old if a["family"] == f)],
                    [next(a["game"] for a in old if a["family"] == f)],
                    "eligible_named_scope",
                    split[f],
                ]
                for i, f in enumerate(ranked)
            ],
        }
        chosen = [{**a, "split": split[a["family"]]} for a in old]
        partition = {
            **original,
            "partition": {**original["partition"], "assignments": chosen},
            "requested": counts,
            "actual": counts,
            "deficits": {"train": 0, "validation": 0, "test": 0},
            "selection": authority,
        }
        rows = [
            {
                "id": a["game"],
                "source_series": a["game"],
                "prefix": a["prefix"],
                "family": a["family"],
                "split": a["split"],
            }
            for a in chosen
        ]
        base = {
            "schema": "quoridor-prefix-series-observations-v1",
            "partition": ref("selected"),
            "source_observations": ref("history"),
            "teacher_labels": False,
        }
        fit = {**base, "observations": [a for a in rows if a["split"] != "test"]}
        held = {**base, "observations": [a for a in rows if a["split"] == "test"]}
        result, protected, lineage = ns["series_fixture_rows"](
            fit, held, partition, original, census, config
        )
        self.assertEqual(len(result), 2)
        self.assertEqual(len(protected), 1)
        self.assertFalse(lineage["H_teacher_labels"])
        missing = {**held, "observations": []}
        with self.assertRaises(ValueError):
            ns["series_fixture_rows"](fit, missing, partition, original, census, config)
        wrong = copy.deepcopy(census)
        wrong["records"][2][5] = "train"
        with self.assertRaises(ValueError):
            ns["series_fixture_rows"](fit, held, partition, original, wrong, config)

        changed = copy.deepcopy(config)
        changed["excluded_books"] = []
        with self.assertRaises(ValueError):
            ns["series_fixture_rows"](fit, held, partition, original, census, changed)
        wrong_schema = copy.deepcopy(census)
        wrong_schema["schema"] = "research.identity-only-component-census.v1"
        with self.assertRaises(ValueError):
            ns["series_fixture_rows"](fit, held, partition, original, wrong_schema, config)

    def test_32768_first5120_singletons_and_H0_refuse_corrupt_parent_or_census_nn0(self):
        import hashlib

        source_path = Path(__file__).with_name("public_static_prepare.py")
        names = {"prefix_fixture_rows", "series_fixture_rows", "saved_subset_fixture_authority"}
        tree = ast.parse(source_path.read_text())
        definitions = ast.Module(
            body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names],
            type_ignores=[],
        )
        ns = {}
        exec(compile(definitions, str(source_path), "exec"), ns)
        ref = lambda name: {"path": "/synthetic/" + name, "sha256": "a" * 64}
        old = [
            {"game": f"m{i}", "family": f"f{i}", "prefix": [i // 209, i % 209], "split": "train"}
            for i in range(5121)
        ]
        seed = 19
        ranked = sorted(
            [a["family"] for a in old],
            key=lambda f: (hashlib.sha256(f"{seed}:{f}".encode()).hexdigest(), f),
        )
        counts = {"train": 4096, "validation": 1024, "test": 0}
        split = {f: "train" if i < 4096 else "validation" for i, f in enumerate(ranked[:5120])}
        original = {
            "partition": {
                "seed": seed,
                "schema": "synthetic-native",
                "rounding": "synthetic",
                "assignments": old,
            },
            "source_series": {a["game"]: a["game"] for a in old},
            "requested": {"train": 32768, "validation": 0, "test": 0},
            "actual": {"train": 5121, "validation": 0, "test": 0},
            "deficits": {"train": 27647, "validation": 0, "test": 0},
        }
        authority = {
            "schema": "quoridor-prefix-series-saved-subset-v3",
            "source_schedule": ref("schedule"),
            "source_partition": ref("parent"),
            "source_observations": ref("history"),
            "source_config": ref("config"),
            "census": ref("census"),
            "exposure_parent": ref("exclusions"),
            "excluded_prefix_components": 0,
            "split_counts": counts,
            "actual_observations": counts,
        }
        excluded = {
            "excluded_books": [ref("all-old-prefix-components")],
            "excluded_static_inputs": ref("old-static-inputs"),
        }
        excluded["excluded_parent"] = {"collection": ref("complete-old-parent-port")}
        config = {
            "families": 32768,
            "split_seed": seed,
            "trajectory": {
                "split_counts": original["requested"],
                "wall_layer_observations": [0, 1, 0],
            },
            **excluded,
        }
        synthetic_member = {a["family"]: a["game"] for a in old}
        census = {
            "schema": "research.identity-only-component-census.v2",
            "columns": [
                "rank0",
                "component",
                "member_ids",
                "source_series_ids",
                "disposition",
                "prospective_split",
            ],
            "exposureParent": authority["exposure_parent"],
            "partition": authority["source_partition"],
            "publishedScheduleByRef": authority["source_schedule"],
            "nativeInputConfig": authority["source_config"],
            "componentRankSeed": seed,
            "sourceExclusionAuthority": excluded,
            "counts": {
                "originalSurvivors": 5121,
                "originalDeficit": 27647,
                "excludedComponents": 0,
                "eligibleNamedScope": 5121,
            },
            "prospective": {
                "selected": 5120,
                "train": 4096,
                "validation": 1024,
                "holdout": 0,
                "deficitWithinNamedScope": 0,
            },
            "records": [
                [
                    i,
                    f,
                    [synthetic_member[f]],
                    [synthetic_member[f]],
                    "eligible_named_scope",
                    split.get(f),
                ]
                for i, f in enumerate(ranked)
            ],
        }
        chosen = [{**a, "split": split[a["family"]]} for a in old if a["family"] in split]
        partition = {
            **original,
            "partition": {**original["partition"], "assignments": chosen},
            "source_series": {a["game"]: original["source_series"][a["game"]] for a in chosen},
            "requested": counts,
            "actual": counts,
            "deficits": {"train": 0, "validation": 0, "test": 0},
            "selection": authority,
        }
        rows = [
            {
                "id": a["game"],
                "source_series": a["game"],
                "prefix": a["prefix"],
                "family": a["family"],
                "split": a["split"],
            }
            for a in chosen
        ]
        base = {
            "schema": "quoridor-prefix-series-observations-v1",
            "partition": ref("selected"),
            "source_observations": ref("history"),
            "teacher_labels": False,
        }
        fit = {**base, "observations": [a for a in rows if a["split"] != "test"]}
        held = {**base, "observations": [a for a in rows if a["split"] == "test"]}
        result, protected, lineage = ns["series_fixture_rows"](
            fit, held, partition, original, census, config
        )
        self.assertEqual(len(result), 5120)
        self.assertEqual(len(protected), 0)
        self.assertFalse(lineage["H_teacher_labels"])

        self.assertEqual(sum(r["functional_split"] == "T" for r in result), 4096)
        self.assertEqual(sum(r["functional_split"] == "V" for r in result), 1024)
        self.assertEqual(len(set(r["family"] for r in result)), 5120)
        # This is a labelled synthetic metadata port, never a geometry proof.
        for fault in (
            "rank",
            "source",
            "partial-member",
            "new-H",
            "missing-fit",
            "multimember",
            "wrong-old-schema",
        ):
            with self.subTest(fault=fault):
                f, h, p, o, c, cfg = copy.deepcopy((fit, held, partition, original, census, config))
                if fault == "rank":
                    c["records"][0][0] = 1
                elif fault == "source":
                    c["records"][0][3] = ["wrong-source"]
                elif fault == "partial-member":
                    c["records"][0][2] = []
                elif fault == "new-H":
                    p["selection"]["split_counts"]["test"] = 1
                elif fault == "missing-fit":
                    f["observations"].pop()
                elif fault == "wrong-old-schema":
                    p["selection"]["schema"] = "quoridor-prefix-series-saved-subset-v2"
                else:
                    family = ranked[0]
                    member = {
                        "game": "extra-member",
                        "family": family,
                        "prefix": [7, 8],
                        "split": "train",
                    }
                    o["partition"]["assignments"].append(member)
                    o["source_series"]["extra-member"] = "extra-member"
                    c["records"][0][2].append("extra-member")
                    c["records"][0][3].append("extra-member")
                with self.assertRaises(ValueError):
                    ns["series_fixture_rows"](f, h, p, o, c, cfg)


if __name__ == "__main__":
    unittest.main()
