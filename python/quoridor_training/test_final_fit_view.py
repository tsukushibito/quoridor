"""New zero-forward metadata joins; all bodies below are labelled toy JSON."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

OWN = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("final_fit_common", OWN / "common.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


class Fixture:
    def __init__(self, root):
        self.root = root
        self.bodies = {}
        self.scale = {
            "starting_weights_sha256": "1" * 64,
            "descriptor_sha256": "2" * 64,
            "evaluator_sha256": "3" * 64,
            "scale_policy": "incumbent_descriptor_T_only",
        }
        self.rows = [2, 3, 1, 2, 4, 1]
        self.eligible = [2, 2, 1, 1, 3, 0]
        self.prefixes = [[10 + i, 70 + i] + ([81 + i, 145 + i] if i % 2 else []) for i in range(6)]
        self.final_splits = ["train", "train", "validation", "train", "train", "validation"]
        self.source_splits = ["train", "validation", *self.final_splits[2:]]
        self.schedule = self.scheduled(6)
        self.final_partition = self.partition(6, self.final_splits)
        self.original_partition = self.partition(2, self.source_splits[:2])
        self.cfg = self.config(
            6,
            0,
            6,
            self.put("schedule", self.schedule),
            self.put("partition", self.final_partition),
        )
        first = self.config(
            2,
            0,
            2,
            self.put("original-schedule", self.scheduled(2)),
            self.put("original-partition", self.original_partition),
        )
        second = {**self.cfg, "batch_start": 2, "batch_count": 4}
        self.native = [
            {
                "common_study": cfg,
                "simulations": 64,
                "inference": {"model_sha": "8" * 64},
                "output": str(root / f"output-{i}"),
            }
            for i, cfg in enumerate((first, second))
        ]
        self.native_refs = [self.put(f"native-{i}", v) for i, v in enumerate(self.native)]
        self.list_ref = self.put("native-list", self.native_refs)
        self.final_ref = self.put("view", self.cfg)
        self.inlet = {
            "model_scale_authority": copy.deepcopy(self.scale),
            "final_fit_view": self.final_ref,
        }
        bindings = [
            {
                "path": str(root / f"output-{i}" / "dataset" / "manifest.json"),
                "sha256": "cd"[i] * 64,
            }
            for i in range(2)
        ]
        assignments = [
            {
                "global_id": i,
                "game": f"game-{i}",
                "request_id": f"fixed-d-family-{i:06}",
                "source_index": 0 if i < 2 else 1,
                "family": f"{i + 1:064x}",
                "prefix": self.prefixes[i],
                "source_split": self.source_splits[i],
                "view_split": self.final_splits[i],
            }
            for i in range(6)
        ]
        self.m = {
            "schema": "quoridor-common-corpus-terminal-geometry-v3",
            "rows": 13,
            "common_corpus": {
                "config": copy.deepcopy(self.cfg),
                "planned_families": 6,
                "raw_file": "completed-root-raw.f32",
                "common_mask_file": "common-eligible.u8",
                "sampling_file": "sampling.bin",
                "teacher_A": "actual_final_z",
                "rootmean_is_raw": True,
                "common_eligible_rows": 9,
                "common_eligible_by_split": {"train": 8, "validation": 1},
            },
            "source_binding": bindings,
            "source_content": [
                {"encoding": "native-teacher-dataset-shards-v1", "manifest": copy.deepcopy(r)}
                for r in bindings
            ],
            "stream_intake": {
                "status": "complete",
                "scope": "common-corpus",
                "publication_protocol": "incomplete-marker-last-v1",
                "batches": [
                    {
                        "batch_start": cfg["batch_start"],
                        "batch_count": cfg["batch_count"],
                        "config": ref,
                    }
                    for cfg, ref in zip((first, second), self.native_refs)
                ],
            },
            "schedule_sha256": self.cfg["schedule"]["sha256"],
            "family_partition_sha256": self.cfg["partition"]["sha256"],
            "dataset_sha": self.list_ref["sha256"],
            "mcts_source": {"model_sha256": "8" * 64, "completed_simulations": 64},
            "mcts_datasets": [
                {
                    "dataset": str(root / f"output-{i}" / "dataset"),
                    "manifest_sha256": "cd"[i] * 64,
                    "rows": n,
                }
                for i, n in enumerate((5, 8))
            ],
            "mcts_native_configs": self.list_ref,
            "model_scale_authority": copy.deepcopy(self.scale),
            "input_binding": self.put("input-binding", self.inlet),
            "final_fit_view": {
                "config": self.final_ref,
                "scope": "sampling-only-original-source-validated",
                "realized_games": 6,
                "changed_global_ids": [1],
                "assignments": assignments,
            },
            "sampling": {
                "families": [
                    {"family": f"{i + 1:064x}", "game": f"game-{i}", "split": s}
                    for i, s in enumerate(self.final_splits)
                ],
                "games": [
                    {"game": f"game-{i}", "family_code": i, "start": sum(self.rows[:i]), "rows": n}
                    for i, n in enumerate(self.rows)
                ],
                "rows_by_family": self.rows.copy(),
                "common_eligible_by_family": self.eligible.copy(),
            },
        }

    def put(self, name, value):
        path = self.root / (name + ".json")
        raw = (json.dumps(value, indent=2) + "\n").encode()
        path.write_bytes(raw)
        self.bodies[name] = copy.deepcopy(value)
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}

    def scheduled(self, n):
        return {
            "scheduled": [
                {
                    "game": i,
                    "request_id": f"fixed-d-family-{i:06}",
                    "requested_prefix_length": len(self.prefixes[i]),
                    "prefix": self.prefixes[i],
                    "scheduled_failure": None,
                }
                for i in range(n)
            ]
        }

    def partition(self, n, splits):
        return {
            "schema": "quoridor-terminal-family-partition-v1",
            "seed": 77,
            "rounding": "toy canonical-owner result, no partition computation",
            "assignments": [
                {
                    "game": f"fixed-d-family-{i:06}",
                    "prefix": self.prefixes[i],
                    "family": f"{i + 1:064x}",
                    "split": splits[i],
                }
                for i in range(n)
            ],
        }

    def config(self, n, start, count, schedule, partition):
        return {
            "families": n,
            "prefix_seed": 66,
            "prefix_lengths": [2, 4],
            "split_seed": 77,
            "root_value_policy": "outcome_only",
            "schedule": schedule,
            "partition": partition,
            "batch_start": start,
            "batch_count": count,
            "excluded_books": [],
        }

    def rebind_native(self, index):
        ref = self.put(f"native-{index}", self.native[index])
        self.native_refs[index] = ref
        self.m["stream_intake"]["batches"][index]["config"] = ref
        self.list_ref = self.put("native-list", self.native_refs)
        self.m["mcts_native_configs"] = self.list_ref
        self.m["dataset_sha"] = self.list_ref["sha256"]

    def rebind_final(self):
        self.final_ref = self.put("view", self.cfg)
        self.m["common_corpus"]["config"] = copy.deepcopy(self.cfg)
        self.m["schedule_sha256"] = self.cfg["schedule"]["sha256"]
        self.m["family_partition_sha256"] = self.cfg["partition"]["sha256"]
        self.m["final_fit_view"]["config"] = self.final_ref
        self.inlet["final_fit_view"] = self.final_ref
        self.m["input_binding"] = self.put("input-binding", self.inlet)


class FinalFitViewNN0(unittest.TestCase):
    def reject_cases(self, edits):
        for name, edit in edits:
            with self.subTest(case=name), tempfile.TemporaryDirectory(dir=OWN) as directory:
                fixture = Fixture(Path(directory))
                edit(fixture)
                with self.assertRaises((ValueError, KeyError, TypeError, OSError)):
                    common.common_cache_config(fixture.m)

    def test_valid_bound_mapping_original_split_immutable_and_final_sampling(self):
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            f = Fixture(Path(directory))
            before = {p: p.read_bytes() for p in f.root.iterdir()}
            self.assertIs(common.common_cache_config(f.m), f.m["common_corpus"]["config"])
            self.assertEqual(f.m["final_fit_view"]["changed_global_ids"], [1])
            self.assertEqual(
                (
                    f.m["final_fit_view"]["assignments"][1]["source_split"],
                    f.m["sampling"]["families"][1]["split"],
                ),
                ("validation", "train"),
            )
            self.assertEqual(before, {p: p.read_bytes() for p in f.root.iterdir()})
            # The reader must not open the absent toy dataset manifests/models.
            self.assertFalse((f.root / "output-0" / "dataset" / "manifest.json").exists())
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            f = Fixture(Path(directory))
            part = copy.deepcopy(f.final_partition)
            part["assignments"][4]["family"] = part["assignments"][3]["family"]
            ref = f.put("joined-final-partition", part)
            f.cfg["partition"] = ref
            f.native[1]["common_study"]["partition"] = ref
            f.rebind_native(1)
            f.rebind_final()
            f.m["final_fit_view"]["assignments"][4]["family"] = f"{4:064x}"
            f.m["sampling"]["families"].pop(4)
            f.m["sampling"]["games"][4]["family_code"] = 3
            f.m["sampling"]["games"][5]["family_code"] = 4
            f.m["sampling"]["rows_by_family"] = [2, 3, 1, 6, 1]
            f.m["sampling"]["common_eligible_by_family"] = [2, 2, 1, 4, 0]
            common.common_cache_config(f.m)
            self.assertEqual(
                (f.m["final_fit_view"]["realized_games"], len(f.m["sampling"]["families"])), (6, 5)
            )

    def test_exact_typed_mapping_ids_prefix_source_and_changes_refuse_tamper(self):
        edits = []
        for key, value in (
            ("global_id", True),
            ("global_id", 2),
            ("game", "game-01"),
            ("request_id", "fixed-d-family-00001"),
            ("source_index", True),
            ("source_index", 1),
            ("family", "f" * 64),
            ("prefix", [11]),
            ("source_split", "train"),
            ("view_split", "validation"),
        ):
            edits.append(
                (
                    key + str(value),
                    lambda f, k=key, v=value: f.m["final_fit_view"]["assignments"][1].__setitem__(
                        k, v
                    ),
                )
            )
        for value in ([], [True], [1, 1], [2]):
            edits.append(
                (
                    "changed" + str(value),
                    lambda f, v=value: f.m["final_fit_view"].__setitem__("changed_global_ids", v),
                )
            )
        edits.extend(
            [
                ("reordered", lambda f: f.m["final_fit_view"]["assignments"].reverse()),
                ("missing", lambda f: f.m["final_fit_view"]["assignments"].pop()),
                (
                    "extra",
                    lambda f: f.m["final_fit_view"]["assignments"][0].__setitem__("alias", 0),
                ),
                ("census", lambda f: f.m["final_fit_view"].__setitem__("realized_games", 5)),
                (
                    "typed-census",
                    lambda f: f.m["final_fit_view"].__setitem__("realized_games", True),
                ),
                ("scope", lambda f: f.m["final_fit_view"].__setitem__("scope", "source-rewritten")),
            ]
        )
        self.reject_cases(edits)

    def test_bound_original_config_schedule_partition_list_and_digest_refusals(self):
        def source(f, kind):
            if kind == "seed":
                f.native[0]["common_study"]["prefix_seed"] += 1
            if kind == "range":
                f.native[0]["common_study"]["batch_count"] = 1
            if kind == "output":
                f.native[0]["output"] = str(f.root / "wrong")
            if kind == "model":
                f.native[0]["inference"]["model_sha"] = "7" * 64
            if kind == "sims":
                f.native[0]["simulations"] = True
            if kind in ("request-alias", "prefix", "slot-order"):
                schedule = f.scheduled(2)
                if kind == "request-alias":
                    schedule["scheduled"][0]["request_id"] += "0"
                if kind == "prefix":
                    schedule["scheduled"][0]["prefix"][0] += 1
                if kind == "slot-order":
                    schedule["scheduled"].reverse()
                f.native[0]["common_study"]["schedule"] = f.put("bad-original-schedule", schedule)
            if kind in ("family", "source-split", "partition-alias", "partition-order"):
                part = copy.deepcopy(f.original_partition)
                if kind == "family":
                    part["assignments"][0]["family"] = "f" * 64
                if kind == "source-split":
                    part["assignments"][0]["split"] = "validation"
                if kind == "partition-alias":
                    part["assignments"][0]["game"] += "0"
                if kind == "partition-order":
                    part["assignments"].reverse()
                f.native[0]["common_study"]["partition"] = f.put("bad-original-partition", part)
            f.rebind_native(0)

        kinds = (
            "seed",
            "range",
            "output",
            "model",
            "sims",
            "request-alias",
            "prefix",
            "slot-order",
            "family",
            "source-split",
            "partition-alias",
            "partition-order",
        )
        edits = [(k, lambda f, k=k: source(f, k)) for k in kinds]

        def reverse_list(f):
            f.m["mcts_native_configs"] = f.put("reversed-list", list(reversed(f.native_refs)))
            f.m["dataset_sha"] = f.m["mcts_native_configs"]["sha256"]

        def bad_final(f):
            part = copy.deepcopy(f.final_partition)
            part["assignments"][1]["split"] = "validation"
            f.cfg["partition"] = f.put("bad-final-partition", part)
            f.rebind_final()

        def drift(f):
            (f.root / "original-schedule.json").write_text("{}")

        def alias(f):
            path = f.root / "alias.json"
            path.symlink_to(f.root / "input-binding.json")
            f.m["input_binding"]["path"] = str(path)

        def oversized(f):
            raw = b" " * (1048576 + 1)
            p = f.root / "oversize.json"
            p.write_bytes(raw)
            f.m["input_binding"] = {"path": str(p), "sha256": hashlib.sha256(raw).hexdigest()}

        edits += [
            ("list-order", reverse_list),
            ("final-split", bad_final),
            ("body-SHA-drift", drift),
            ("symlink-alias", alias),
            ("bounded-size", oversized),
        ]
        self.reject_cases(edits)

    def test_final_sampling_game_family_per_source_and_eligible_census(self):
        edits = [
            (
                "family-split",
                lambda f: f.m["sampling"]["families"][1].__setitem__("split", "validation"),
            ),
            (
                "family-alias",
                lambda f: f.m["sampling"]["families"][1].__setitem__("game", "game-01"),
            ),
            ("family-order", lambda f: f.m["sampling"]["families"].reverse()),
            ("missing-game", lambda f: f.m["sampling"]["games"].pop()),
            ("game-code", lambda f: f.m["sampling"]["games"][0].__setitem__("family_code", True)),
            ("game-order", lambda f: f.m["sampling"]["games"].reverse()),
            ("game-start", lambda f: f.m["sampling"]["games"][1].__setitem__("start", 1)),
            ("family-row-total", lambda f: f.m["sampling"]["rows_by_family"].__setitem__(0, 3)),
            (
                "eligible-bool",
                lambda f: f.m["sampling"]["common_eligible_by_family"].__setitem__(0, True),
            ),
            (
                "eligible-overflow",
                lambda f: f.m["sampling"]["common_eligible_by_family"].__setitem__(0, 3),
            ),
            (
                "eligible-split",
                lambda f: f.m["common_corpus"].__setitem__(
                    "common_eligible_by_split", {"train": 7, "validation": 2}
                ),
            ),
        ]

        def moved_rows(f):
            f.rows[1] -= 1
            f.rows[2] += 1
            for i, g in enumerate(f.m["sampling"]["games"]):
                g.update(start=sum(f.rows[:i]), rows=f.rows[i])
            f.m["sampling"]["rows_by_family"] = f.rows.copy()

        edits.append(("coherent-global-but-wrong-source-count", moved_rows))
        self.reject_cases(edits)

    def test_optional_mode_bound_inlet_omission_and_scale_conflicts(self):
        def omit_inlet_view(f):
            del f.inlet["final_fit_view"]
            f.m["input_binding"] = f.put("input-binding", f.inlet)

        def fragment_only(f):
            f.m["input_binding"] = f.put("input-binding", {"final_fit_view": f.final_ref})

        def alpha_view(f):
            for key in ("mcts_source", "mcts_datasets", "mcts_native_configs"):
                f.m.pop(key)
            f.m["common_corpus"]["rootmean_is_raw"] = False
            f.m["source_content"] = [
                {
                    "encoding": "gzip-single-member-v1",
                    "compressed": {**r, "bytes": 10, "mode": "0644"},
                    "raw_sha256": "e" * 64,
                    "raw_bytes": 20,
                }
                for r in f.m["source_binding"]
            ]

        edits = [
            ("stripped-manifest", lambda f: f.m.pop("final_fit_view")),
            ("stripped-binding", lambda f: f.m.pop("input_binding")),
            ("stripped-inlet-view", omit_inlet_view),
            ("standalone-fragment", fragment_only),
            ("no-scale", lambda f: f.m.pop("model_scale_authority")),
            (
                "scale-conflict",
                lambda f: f.m["model_scale_authority"].__setitem__("descriptor_sha256", "4" * 64),
            ),
            ("Alpha-view-not-permitted", alpha_view),
        ]
        self.reject_cases(edits)
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            f = Fixture(Path(directory))
            del f.m["final_fit_view"]
            del f.m["input_binding"]
            with patch.object(Path, "read_bytes", side_effect=AssertionError("no-view body read")):
                common.common_cache_config(f.m)
            # An ordinary data-only old route remains metadata-only and does not
            # gain fit permission; old methods/success suites are not invoked.
            del f.m["model_scale_authority"]
            common.common_cache_config(f.m)
            f.inlet.pop("final_fit_view")
            f.m["input_binding"] = f.put("old-no-view-binding", f.inlet)
            common.common_cache_config(f.m)


if __name__ == "__main__":
    names = sys.argv[1:] or unittest.defaultTestLoader.getTestCaseNames(FinalFitViewNN0)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(FinalFitViewNN0(name) for name in names)
    )
    print(
        json.dumps(
            {
                "new_definitions": result.testsRun,
                "passed": result.wasSuccessful(),
                "real_model_forward_rows": 0,
                "old_test_methods_run": 0,
            }
        )
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
