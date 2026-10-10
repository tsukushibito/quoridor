"""One affected publisher-to-consumer scope, synthetic files and zero engine calls."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import lifecycle355 as life
import observations355 as observations
import stream355 as stream
import test_lifecycle_repair355 as fixture


class ArenaInputIntegration(unittest.TestCase):
    def test_bound_owed_inventory_deduplicates_only_within_its_operation(self):
        evidence = Path(__file__).resolve().parents[3] / (
            ".artifacts/value-search-strength355-analysis-v1/owed-inventory-repair-v20/TMP"
        )
        evidence.mkdir(exist_ok=True)
        for case in (
            "215_unique",
            "receipt_missing",
            "receipt_hash_drift",
            "undeclared_receipt",
            "descriptor_conflict",
            "cross_operation",
            "partial_FAILED",
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory(dir=evidence) as directory:
                with mock.patch.object(fixture, "EVIDENCE", Path(directory)):
                    f = fixture.ConsumerPublisherIntegration("runTest")
                    f.setUp()
                try:
                    book_ref = f.document(
                        "inventory-book.json",
                        {
                            "compiled_sources": {
                                k: v
                                for k, v in f.compiled_hashes.items()
                                if k != "runner/sigma_qualification.rs"
                            }
                        },
                    )
                    f.input = book_ref
                    f.config = f.document(
                        "inventory-plan.json",
                        {
                            "schema": "quoridor.value-search-strength.compare.v2",
                            "canonical_plan": {"sha256": stream.s.PLAN_SHA},
                            "book": book_ref,
                        },
                    )
                    experiment_ref, experiment = f.experiment("compare")
                    files = [
                        f.file(f"inventory-data/{name}", b"")
                        for name in (
                            [f"matched-{i}.json" for i in range(96)]
                            + [f"stronger-{i}.json" for i in range(108)]
                            + [f"tree-{i}.json" for i in range(8)]
                        )
                    ]
                    # Empty synthetic payloads test inventory only; no row/tree parser runs.
                    header = f.document(
                        "inventory-data/planned.json",
                        {
                            "schema": "quoridor.value-search-strength.compare-intent.v2",
                            "experiment_sha256": experiment_ref["sha256"],
                            "config_sha256": f.config["sha256"],
                            "build_manifest": f.build_ref,
                        },
                    )
                    selection = f.document("inventory-data/selection.json", {"SYNTHETIC": True})
                    footer = f.document(
                        "inventory-data/result.json",
                        {
                            "schema": "quoridor.value-search-strength.compare-result.v2",
                            "experiment_sha256": experiment_ref["sha256"],
                            "config_sha256": f.config["sha256"],
                            "book_sha256": book_ref["sha256"],
                            "fixed_denominator": {
                                "matched_positions": 32,
                                "natural4": 96,
                                "common_trees": 8,
                                "stronger_max_cases": 16,
                            },
                            "outputs": files,
                        },
                    )
                    direct = [header, selection, footer]
                    inventory = direct + files
                    self.assertEqual(len(inventory), 215)
                    data = fixture.publisher.collect_data(
                        {
                            "owner": str(f.root),
                            "data": [
                                {"name": str(i), "path": r["path"], "limit_B": 131072}
                                for i, r in enumerate(direct)
                            ],
                        },
                        experiment,
                    )
                    original = {"type": "SyntheticOrigin", "message": "original partial failure"}
                    finalizer = fixture.publisher.finalize
                    receipt_paths = []

                    def publish_with_receipt(operation, job, **kwargs):
                        candidate = fixture.publisher.document(
                            fixture.publisher.bound(operation / "candidate.json")[0]
                        )
                        obligation = candidate["owed_finalizers"][0]
                        refs = copy.deepcopy(inventory)
                        if case == "descriptor_conflict":
                            refs[0]["sha256"] = "f" * 64
                        receipt = {
                            "schema": "quoridor.research.data-finalizer.v1",
                            "status": "PASS",
                            "remaining": [],
                            "intent_sha256": candidate["intent"]["sha256"],
                            "files": refs,
                        }
                        path = Path(obligation["path"])
                        f.file(str(path.relative_to(f.root)), json.dumps(receipt).encode())
                        receipt_paths.append(path)
                        return finalizer(operation, job, **kwargs)

                    with mock.patch.object(
                        fixture.publisher, "finalize", side_effect=publish_with_receipt
                    ):
                        completions = []
                        for i in range(2 if case == "cross_operation" else 1):
                            ref, completed = f.operation(
                                "run",
                                experiment_ref,
                                data,
                                primary=original if case == "partial_FAILED" else None,
                                secondary=[{"stage": "origin", "message": "retained secondary"}],
                                owed=[
                                    {
                                        "kind": "data",
                                        "path": str(f.root / f"owed-{i}.json"),
                                        "limit_B": 131072,
                                    }
                                ],
                            )
                            completions.append(ref)
                    generation_ref, _ = f.experiment("generation")
                    generation_completion, _ = f.operation(
                        "run",
                        generation_ref,
                        {"status": "FAILED", "files": [book_ref, f.schedule], "errors": []},
                        primary={
                            "type": "SyntheticGeneration",
                            "message": "partial input evidence",
                        },
                    )
                    completions.insert(0, generation_completion)
                    if case == "receipt_missing":
                        receipt_paths[0].unlink()
                    elif case == "receipt_hash_drift":
                        receipt_paths[0].write_bytes(b"{}")
                    elif case == "undeclared_receipt":
                        # An attack on the published shape, not a fabricated positive authority.
                        completed["owed_finalizers"][0]["path"] = str(f.root / "undeclared.json")
                        path = Path(completions[1]["path"])
                        path.write_text(json.dumps(completed))
                        completions[1] = fixture.publisher.bound(path)[0]
                    refs = [book_ref, f.schedule, f.config, *inventory]
                    index = {
                        "schema": "quoridor.strength355.stopped-input-index.v1",
                        "plan_SHA256": stream.s.PLAN_SHA,
                        "provenance": "ACTUAL_GENERATED",  # Shape only, synthetic inputs.
                        "files": {
                            str(i): {
                                "path": r["path"],
                                "SHA256": r["sha256"],
                                "bytes": r["bytes"],
                                "mode": r["mode"],
                            }
                            for i, r in enumerate(refs)
                        },
                        "build_manifest": f.build_ref,
                        "producer_completions": completions,
                        "book": "0",
                        "schedule": "1",
                        "engineering_plan": "2",
                        "engineering_intent": "3",
                        "selection": "4",
                        "engineering_footer": "5",
                        "matched_rows": [str(i) for i in range(6, 102)],
                        "stronger_rows": [
                            {"file": str(i), "kind": "natural"} for i in range(102, 210)
                        ],
                        "trees": [str(i) for i in range(210, 218)],
                        "batches": [],
                    }
                    metadata, inputs = life.Metadata(), stream.Inputs(index)
                    # Unchanged book/schedule mathematics is outside this inventory-only scope.
                    book = {"source_book_SHA256": book_ref["sha256"]}
                    with (
                        mock.patch.object(stream.s, "adapt_generated_book", return_value=book),
                        mock.patch.object(stream.s, "adapt_schedule", return_value={}),
                    ):
                        if case not in ("215_unique", "partial_FAILED"):
                            with self.assertRaises((ValueError, OSError)):
                                stream.scientific_inputs(
                                    index,
                                    inputs,
                                    metadata,
                                    f.build_ref,
                                    f.build,
                                    {"inputs": refs, "schedule": f.schedule},
                                )
                            continue
                        _, _, available, _, provenance = stream.scientific_inputs(
                            index,
                            inputs,
                            metadata,
                            f.build_ref,
                            f.build,
                            {"inputs": refs, "schedule": f.schedule},
                        )
                    self.assertEqual(len(available), 217)
                    comparison_owners = [available[str(i)][0] for i in range(3, 218)]
                    self.assertTrue(
                        all(owner is comparison_owners[0] for owner in comparison_owners)
                    )
                    self.assertEqual(len(comparison_owners), 215)
                    self.assertEqual(len(metadata.progress["operation_provenance"]), 2)
                    self.assertEqual(len(completed["data"]["files"]), 3)
                    self.assertEqual(len(completed["owed_finalizers"]), 1)
                    if case == "partial_FAILED":
                        self.assertEqual(provenance[1]["status"], "FAILED")
                        self.assertEqual(provenance[1]["primary"], original)
                        self.assertTrue(provenance[1]["cleanup_complete"])
                        self.assertEqual(
                            provenance[1]["secondary"][0]["message"], "retained secondary"
                        )
                    self.assertEqual(inputs.progress["rows_read"], 0)
                finally:
                    f.doCleanups()

    def test_finalized_journal_result_context_and_partial_provenance(self):
        evidence = Path(__file__).resolve().parents[3] / (
            ".artifacts/value-search-strength355-analysis-v1/arena-consumer-repair-v18/TMP"
        )
        evidence.mkdir(exist_ok=True)
        cases = (
            "valid",
            "display",
            "global_family",
            "prefix",
            "colour",
            "clock",
            "schedule",
            "native_family",
            "run_id",
            "duplicate",
            "hash_drift",
            "result_hash_drift",
            "provisional",
            "candidate",
            "partial_FAILED",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(dir=evidence) as directory:
                with mock.patch.object(fixture, "EVIDENCE", Path(directory)):
                    f = fixture.ConsumerPublisherIntegration("runTest")
                    f.setUp()
                try:
                    self.exercise(f, case)
                finally:
                    f.doCleanups()

    def exercise(self, f, case):
        s = stream.s
        prefixes = [
            [],
            [13, 67],
            [3, 77, 152, 206],
            [3, 75, 196, 182, 187, 66],
            [95, 175, 13, 107, 198, 149, 116, 90],
            [3, 208, 4, 140, 5, 75, 119, 148, 95, 182],
            [3, 67, 4, 151, 192, 199, 141, 183, 179, 68, 105, 82],
            [112, 115, 3, 75, 12, 83, 96, 145, 157, 66, 13, 136, 4, 67],
        ]
        families, attempts = [], []
        for fid in range(128):
            length = (4, 8, 12, 16)[fid // 32]
            prefix = [fid] * (length - 1) + [208 - fid]
            history = [[f"SYNTHETIC-{fid}-{i}", 1] for i in range(length + 1)]
            families.append(
                {
                    "family_id": fid,
                    "id": f"strength355-family-{fid:03d}",
                    "attempt_id": 0,
                    "seed": 35520261009 + 8 * fid,
                    "prefix": prefix,
                    "root_key": history[-1][0],
                    "history_counts": history,
                }
            )
            attempts.append(
                {
                    "family_id": fid,
                    "attempt_id": 0,
                    "seed": 35520261009 + 8 * fid,
                    "requested_plies": length,
                    "prefix": prefix,
                    "rejection": None,
                }
            )
        book = {
            "schema": "quoridor.value-search-strength.book.v1",
            "plan_sha256": s.PLAN_SHA,
            "complete": True,
            "rules": life.RULES,
            "old_open8_prefixes": prefixes,
            "old_open8_sha256": s.digest(prefixes),
            "compiled_sources": {
                k: v for k, v in f.compiled_hashes.items() if k != "runner/sigma_qualification.rs"
            },
            "attempted": 128,
            "attempts": attempts,
            "transitions": sum(len(a["prefix"]) for a in attempts),
            "families": families,
            "limitation": "different translated display" if case == "display" else "display only",
        }
        book_ref = f.document("arena-book.json", book)
        schedule = [
            {
                "slot": r["slot_id"],
                "batch": r["batch_id"],
                "matchup": s.MATCHUPS.index(r["matchup"]),
                "family_id": r["family_id"],
                "candidate_color": r["candidate_colour"],
                "local_game": r["local_game"],
            }
            for r in s.planned_slots()
        ]
        planned = [r for r in schedule if r["batch"] == 2]
        if case == "schedule":
            schedule[64]["family_id"] = 127
        schedule_ref = f.document("arena-schedule.json", schedule)
        config = {
            "run_id": "SYNTHETIC-bound-batch2",
            "games": 32,
            "ruleset": "standard_2p_threefold",
            "inference": None,
            "inference_cpu_core": None,
            "arena": {
                "comparison": "evaluator_wall_time",
                "clock_policy": "strict_unknown",
                "return_reserve_ms": 5,
                "tt_entries": 4096,
                "first_candidate_colors": [r["candidate_color"] for r in planned[::2]],
                "book": {
                    "openings": [
                        {
                            "prefix": families[r["family_id"]]["prefix"],
                            "reference": {"settings": {"family_id": r["family_id"]}},
                        }
                        for r in planned[::2]
                    ]
                },
            },
            "engines": [
                {
                    "kind": kind,
                    "model": f.models[1]["descriptor"]["path"] if kind == "nnue" else None,
                    "distance_a": 0,
                    "distance_b": 0 if kind == "nnue" else 8,
                    "time_ms": 100,
                    "depth": 64,
                    "max_nodes": 1000000,
                }
                for kind in ("nnue", "distance")
            ],
        }
        rows = [
            {
                "game": r["local_game"],
                "family": f"{config['run_id']}-family-{r['local_game'] // 2:06}",
                "candidate_color": r["candidate_color"],
                "started": False,
                "status": "unknown",
                "winner": None,
                "reason": "SYNTHETIC unentered observation",
                "failure": None,
                "plies": len(families[r["family_id"]]["prefix"]),
                "moves": families[r["family_id"]]["prefix"],
                "observations": [],
            }
            for r in planned
        ]
        if case == "global_family":
            config["arena"]["book"]["openings"][0]["reference"]["settings"]["family_id"] = 0
        elif case == "prefix":
            config["arena"]["book"]["openings"][0]["prefix"] = [0] * 4
        elif case == "colour":
            rows[0]["candidate_color"] ^= 1
        elif case == "clock":
            config["engines"][0]["time_ms"] = 101
        elif case == "native_family":
            rows[0]["family"] = "SYNTHETIC-wrong-family"
        elif case == "run_id":
            config["run_id"] = "SYNTHETIC-other-run"
        elif case == "duplicate":
            rows[-1] = copy.deepcopy(rows[0])
        elif case == "partial_FAILED":
            rows.pop()
        config_ref = f.document("arena-config.json", config)
        _, generation = f.experiment("generation")
        generation.update(inputs=[book_ref], schedule=schedule_ref)
        generation_ref = f.document("generation-context.json", generation)
        original = {"type": "SyntheticOrigin", "message": "unchanged original input failure"}
        generation_completion, _ = f.operation(
            "run",
            generation_ref,
            {"status": "FAILED", "files": [book_ref, schedule_ref], "errors": []},
            primary=original,
            secondary=[{"stage": "origin", "message": "original secondary"}],
        )
        _, arena = f.experiment("arena")
        arena.update(
            config=config_ref,
            inputs=[book_ref],
            models=[f.models[1]],
            schedule=schedule_ref,
            planned_slots=512,
            batch=2,
        )
        numeric = {
            "schema": "quoridor.research.numerical-qualification.v1",
            "status": "PASS",
            "phase": "arena",
            "artifact_sha256": f.artifact["sha256"],
            "compiled_sources_sha256": life.compiled_digest(f.compiled_hashes),
            "config_sha256": config_ref["sha256"],
            "schedule_sha256": schedule_ref["sha256"],
            "input_sha256": [book_ref["sha256"]],
            "descriptor_sha256": [f.models[1]["descriptor"]["sha256"]],
            "weights_sha256": [f.models[1]["weights"]["sha256"]],
            "evaluator_sha256": [f.models[1]["evaluator_sha256"]],
            "rules": life.RULES,
            "distance_units": life.UNITS,
            "value_perspective": life.PERSPECTIVE,
            "remaining": [],
        }
        arena["numerical_qualification"] = f.document("arena-numerical.json", numeric)
        arena_ref = f.document("arena-experiment.json", arena)
        journal_ref = f.file(
            "arena-data/completed.jsonl",
            b"".join((json.dumps(r) + "\n").encode() for r in rows),
        )
        result_ref = f.document(
            "arena-data/result.json",
            {"planned": 32, "all_workers_joined": True, "stopped": None, "outcomes": rows},
        )
        spec = {
            "owner": str(f.root),
            "data": [
                {"name": name, "path": ref["path"], "limit_B": 131072}
                for name, ref in (("journal", journal_ref), ("result", result_ref))
            ],
        }
        data = fixture.publisher.collect_data(spec, arena)
        completion_ref, completed = f.operation("run", arena_ref, data)
        all_refs = [book_ref, schedule_ref, config_ref, journal_ref, result_ref]
        index = {
            "schema": "quoridor.strength355.stopped-input-index.v1",
            "plan_SHA256": s.PLAN_SHA,
            "provenance": "ACTUAL_GENERATED",  # Synthetic typed shape, never actual input.
            "files": {
                name: {
                    "path": ref["path"],
                    "SHA256": ref["sha256"],
                    "bytes": ref["bytes"],
                    "mode": ref["mode"],
                }
                for name, ref in zip(("book", "schedule", "config", "journal", "result"), all_refs)
            },
            "build_manifest": f.build_ref,
            "producer_completions": [generation_completion, completion_ref],
            "book": "book",
            "schedule": "schedule",
            "batches": [
                {"batch": 2, "config": "config", "completed": "journal", "result": "result"}
            ],
            "matched_rows": [],
            "trees": [],
            "selection": None,
            "stronger_rows": [],
            "engineering_footer": None,
            "producer_bindings": {},
            "partial_errors": [],
        }
        analysis = {"inputs": all_refs, "schedule": schedule_ref}
        if case == "hash_drift":
            Path(journal_ref["path"]).write_bytes(b"changed after finalization\n")
        elif case == "result_hash_drift":
            Path(result_ref["path"]).write_bytes(b"changed after finalization\n")
            # The maintained parent owns every declared input integrity check.
            with self.assertRaises(fixture.publisher.Refused):
                fixture.publisher.read_ref(result_ref)
            return
        elif case == "provisional":
            (Path(completion_ref["path"]).parent / "INCOMPLETE").touch()
        elif case == "candidate":
            index["producer_completions"][-1] = f.document("candidate.json", completed)
        inputs, metadata, partial = stream.Inputs(index), life.Metadata(), {}
        if case not in ("valid", "display", "partial_FAILED"):
            with self.assertRaises((ValueError, fixture.publisher.Refused)):
                self.consume(index, inputs, metadata, f, analysis, partial)
            return
        summary = self.consume(index, inputs, metadata, f, analysis, partial)
        self.assertEqual(summary["games"]["matchups"][s.MATCHUPS[1]]["observed_records"], len(rows))
        self.assertEqual(summary["games"]["matchups"][s.MATCHUPS[1]]["UNKNOWN_games"], 256)
        self.assertEqual(summary["matched"]["UNKNOWN_or_partial"], 96)
        self.assertEqual(summary["stronger"]["status"], "UNKNOWN")
        self.assertEqual(len(summary["unentered_tree_family_ids"]), 8)
        self.assertEqual(metadata.progress["operation_provenance"][0]["status"], "FAILED")
        self.assertEqual(metadata.progress["operation_provenance"][0]["primary"], original)
        self.assertTrue(metadata.progress["operation_provenance"][0]["secondary"])
        if case == "partial_FAILED":
            self.assertEqual(completed["status"], "FAILED")
            self.assertTrue(metadata.progress["operation_provenance"][1]["data_errors"])
            self.assertEqual(completed["data"]["missing_local_games"], [31])

    @staticmethod
    def consume(index, inputs, metadata, f, analysis, partial):
        book, schedule, _, _, _ = stream.scientific_inputs(
            index, inputs, metadata, f.build_ref, f.build, analysis
        )
        return observations.aggregate_observations(index, inputs, partial, book, schedule, {})
