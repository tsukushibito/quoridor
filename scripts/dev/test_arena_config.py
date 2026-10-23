"""Current configurable arena/decision/analysis NN0 metadata checks."""

import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
loader = importlib.util.spec_from_file_location(
    "arena_lifecycle377", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class ConfiguredArenaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.root = Path(self.temp.name)
        self.serial = 0

    def tearDown(self):
        self.temp.cleanup()

    def store(self, data, label="record"):
        self.serial += 1
        p = self.root / f"{label}-{self.serial}.json"
        p.write_text(json.dumps(data))
        return lc.bound(p)[0]

    def fixture(self, families, ids, mode="evaluator_fixed_depth", off=False, decision=False):
        width = 1 if decision else 2
        fams = [
            {
                "family_id": f,
                "id": f"parent-{f}",
                "seed": f + 1,
                "attempt_id": 0,
                "prefix": [13 + i],
                "root_key": "FAKE",
                "history_counts": [["FAKE", 1]],
            }
            for i, f in enumerate(families)
        ]
        openings = [
            {"id": f["id"], "prefix": f["prefix"], "original_seed": f["seed"]} for f in fams
        ]
        book = self.store(
            {
                "complete": True,
                "rules": "research-standard-2p-threefold-goal-first-v1",
                "families": fams,
                "frozen_before_candidate_results": True,
                "openings": openings,
            },
            "book",
        )
        model_file = self.store({"synthetic_only": True}, "never-loaded-model")
        model = {
            "descriptor": model_file,
            "weights": model_file,
            "evaluator_sha256": "b" * 64,
        }

        def engine(kind):
            return {
                "kind": kind,
                "model": model_file["path"] if kind == "nnue" else None,
                "depth": 4,
                "max_nodes": 1234,
                "time_ms": None if mode == "evaluator_fixed_depth" else 90,
                "simd": False,
                "distance_a": 0,
                "distance_b": 0,
            }

        schedule, batches, matchups = [], [], []
        configs = []
        for batch, identity in enumerate(ids):
            engines = (
                [engine("nnue" if batch % 2 == 0 else "distance")]
                if decision
                else (
                    [engine("distance"), engine("nnue")]
                    if batch % 2 == 0
                    else [engine("nnue"), engine("distance")]
                )
            )
            hashes = ["b" * 64 if e["kind"] == "nnue" else "a" * 64 for e in engines]
            slots = []
            for local, f in enumerate(families):
                for color in range(width):
                    slots.append(len(schedule))
                    schedule.append(
                        {
                            "slot": len(schedule),
                            "batch": batch,
                            "matchup": identity,
                            "local_game": local * width + color,
                            "family_id": f,
                            "candidate_color": color,
                        }
                    )
            local_openings = copy.deepcopy(openings)
            if not decision:
                for o, f in zip(local_openings, fams):
                    o["reference"] = {
                        "source_sha256": book["sha256"],
                        "settings": {k: f[k] for k in ("family_id", "root_key", "history_counts")},
                    }
            c = {
                "run_id": f"synthetic-{batch}",
                "output": str(self.root / f"data-{batch}"),
                "ruleset": "standard_2p_threefold",
                "games": len(slots),
                "workers": 1,
                "active_games": 1,
                "max_batch": 1,
                "max_output_bytes": 1048576,
                "max_plies": 10,
                "engines": engines,
                "arena": {
                    "comparison": mode,
                    "clock_policy": "strict_unknown",
                    "return_reserve_ms": 0 if mode == "evaluator_fixed_depth" else 7,
                    "tt_entries": 37,
                    "evaluator_sha256": hashes,
                    "search_artifact_sha256": ["c" * 64] * width,
                    "retained_outcome_bytes": 32768,
                    "decision_only": decision,
                    "disable_continuation_static_ordering": off,
                    "first_candidate_colors": [0] * len(families),
                    "book": {"openings": local_openings},
                },
            }
            cref = self.store(c, "config")
            configs.append(c)
            matchups.append({"id": identity, "engines": engines, "evaluator_sha256": hashes})
            batches.append({"batch": batch, "matchup": identity, "config": cref, "slots": slots})
        sr = self.store(schedule, "schedule")
        plan = {
            "schema": "quoridor.research.arena-plan.v1",
            "phase": "compare" if decision else "arena",
            "comparison": mode,
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "book": book,
            "inputs": [book],
            "models": [model],
            "schedule": sr,
            "family_ids": families,
            "matchups": matchups,
            "batches": batches,
            "planned_slots": len(schedule),
        }
        pref = self.store(plan, "plan")
        exp = {
            "phase": plan["phase"],
            "argv": [
                "/synthetic-not-executed",
                "decisions" if decision else "arena",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
            "batch": 0,
            "config": batches[0]["config"],
            "dynamic_libraries": [],
            "canonical_plan_sha256": pref["sha256"],
            "build_manifest": self.store({"synthetic_only": True}, "not-a-native-qualification"),
            **{
                k: plan[k]
                for k in (
                    "rules",
                    "distance_units",
                    "value_perspective",
                    "inputs",
                    "models",
                    "schedule",
                    "planned_slots",
                )
            },
        }
        return plan, pref, exp, configs

    def test_native_family_seed_and_attempt_types_refuse_matching_null_metadata(self):
        missing = object()
        cases = [(0, 0), (2**64 - 1, 2**64 - 1)]
        cases += [(v, 0) for v in (None, False, True, -1, 2**64)]
        cases += [(0, v) for v in (missing, None, False, True, -1, 2**64)]
        for seed, attempt in cases:
            with self.subTest(seed=seed, attempt=attempt):
                plan, _, exp, configs = self.fixture([0], [0])
                book = lc.document(plan["book"])
                family = book["families"][0]
                family["seed"] = seed
                if attempt is missing:
                    family.pop("attempt_id")
                else:
                    family["attempt_id"] = attempt
                book_ref = self.store(book, "typed-book")
                plan["book"] = book_ref
                plan["inputs"] = exp["inputs"] = [book_ref]
                opening = configs[0]["arena"]["book"]["openings"][0]
                opening["original_seed"] = seed
                opening["reference"]["source_sha256"] = book_ref["sha256"]
                config_ref = self.store(configs[0], "typed-config")
                plan["batches"][0]["config"] = exp["config"] = config_ref
                exp["canonical_plan_sha256"] = self.store(plan, "typed-plan")["sha256"]
                if (
                    type(seed) is int
                    and 0 <= seed < 2**64
                    and type(attempt) is int
                    and 0 <= attempt < 2**64
                ):
                    lc.arena_plan_check(exp, plan)
                else:
                    with self.assertRaisesRegex(lc.Refused, "unsigned seed/attempt identity"):
                        lc.arena_plan_check(exp, plan)

    def test_native_family_shape_refuses_producer_only_fields_before_entry(self):
        changes = [
            None,
            {"canonical_prefix": []},
            {"id": None},
            {"root_key": 0},
            {"prefix": None},
            {"prefix": [2**16]},
            {"history_counts": "not-a-list"},
            {"history_counts": [["FAKE", 2**16]]},
            {"history_counts": [["FAKE", 1, 2]]},
            {"family_id": True},
        ]
        for change in changes:
            with self.subTest(change=change):
                plan, _, exp, configs = self.fixture([0], [0])
                book = lc.document(plan["book"])
                producer = self.store({"synthetic_producer": True}, "producer")
                book["producer_source"] = producer
                if change:
                    book["families"][0].update(change)
                book_ref = self.store(book, "projected-native-book")
                plan["book"] = book_ref
                plan["inputs"] = exp["inputs"] = [book_ref, producer]
                opening = configs[0]["arena"]["book"]["openings"][0]
                opening["reference"]["source_sha256"] = book_ref["sha256"]
                config_ref = self.store(configs[0], "projected-native-config")
                plan["batches"][0]["config"] = exp["config"] = config_ref
                exp["canonical_plan_sha256"] = self.store(plan, "projected-native-plan")["sha256"]
                if change is None:
                    lc.arena_plan_check(exp, plan)
                else:
                    with self.assertRaisesRegex(lc.Refused, "native book family fields"):
                        lc.arena_plan_check(exp, plan)

    def analysis(self, plan, pref, base):
        config = {
            "schema": "quoridor.arena-analysis.v1",
            "arena_plan": pref,
            "decision_plan": None,
            "diagnostic_selection": None,
            "bootstrap_resamples": 7,
            "bootstrap_seed": 19,
            "central_interval": "80%",
            "batches": [{"batch": b["batch"], "completion": None} for b in plan["batches"]],
            "decision_batches": [],
        }
        c = self.store(config, "analysis")
        e = {
            **base,
            "phase": "analysis",
            "batch": None,
            "config": c,
            "inputs": [pref],
            "argv": [
                "/synthetic-python",
                "-B",
                str(lc.ROOT / "scripts/dev/research-lifecycle.py"),
                "arena-analysis",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        }
        spec = {
            "owner": str(self.root),
            "cwd": str(ROOT),
            "limits": {},
            "support": None,
            "artifact": {},
            "caller_sources": [],
            "env": {},
            "data_root": str(self.root / "analysis-output"),
            "data": [],
            "finalizers": [],
            "approved_plan": pref,
            "experiment": self.store(e),
            "selection_index": 0,
        }
        spec["data"] = [
            {
                "name": name,
                "path": str(Path(spec["data_root"]) / file),
                "limit_B": 1048576,
            }
            for name, file in (("summary", "summary.json"), ("report", "report.md"))
        ]
        spec["settings"] = self.store(
            {"kind": "sequence", "runs": [copy.deepcopy(spec)]}, "issued-settings"
        )
        return spec, e, config

    def test_configured_counts_ids_engine_order_depth_clock_history_and_ordering(self):
        for families, ids, mode in (
            ([19, 71], [7], "evaluator_fixed_depth"),
            ([5, 90, 102], [42, 9], "whole_wall_time"),
        ):
            for off in (False, True):
                plan, _, e, configs = self.fixture(families, ids, mode, off)
                for batch in plan["batches"]:
                    selected = {**e, "batch": batch["batch"], "config": batch["config"]}
                    rows, c = lc.arena_plan_check(selected, plan)
                    self.assertEqual(len(rows), 2 * len(families))
                    self.assertEqual(c["engines"], plan["matchups"][batch["batch"]]["engines"])
                bad = copy.deepcopy(plan)
                bad["batches"][0]["slots"][1] = bad["batches"][0]["slots"][0]
                with self.assertRaises(lc.Refused):
                    lc.arena_plan_check(e, bad)
                c = copy.deepcopy(configs[0])
                c["arena"]["book"]["openings"][0]["reference"]["settings"]["history_counts"] = [
                    ["DRIFT", 1]
                ]
                cref = self.store(c)
                altered = copy.deepcopy(plan)
                altered["batches"][0]["config"] = cref
                with self.assertRaises(lc.Refused):
                    lc.arena_plan_check({**e, "config": cref}, altered)

    def test_decision_census_above_old_caps_and_completed_depth(self):
        plan, _, e, _ = self.fixture(list(range(100, 197)), [73, 2, 900, 11], decision=True)
        rows, _ = lc.arena_decision_plan_check(e, plan)
        self.assertEqual(len(rows), 97)
        self.assertEqual(e["planned_slots"], 388)
        bad = copy.deepcopy(plan)
        bad["matchups"][0]["engines"][0]["kind"] = "mcts"
        with self.assertRaises(lc.Refused):
            lc.arena_decision_plan_check(e, bad)
        plan, _, e, _ = self.fixture(
            [19, 71], [73], mode="whole_wall_time", off=True, decision=True
        )
        rows, _ = lc.arena_decision_plan_check(e, plan)
        self.assertEqual(len(rows), 2)

    def test_analysis_missing_denominators_collector_and_immutable_selection(self):
        for families, ids in (([19, 71], [7]), ([5, 90, 102], [42, 9])):
            plan, pref, e, _ = self.fixture(families, ids)
            spec, e, config = self.analysis(plan, pref, e)
            summary, _ = lc.arena_analysis(spec, e)
            self.assertEqual(summary["planned"], 2 * len(families) * len(ids))
            self.assertEqual(summary["bootstrap_seed"], 19)
            for table in summary["matchups"]:
                self.assertEqual(table["counts"]["unknown"], 2 * len(families))
                self.assertEqual(table["planned_game_missingness_bounds"], [0, 1])
                self.assertIsNone(table["conditional_complete_pair_interval"])
            Path(spec["data_root"]).mkdir(exist_ok=True)
            (Path(spec["data_root"]) / "summary.json").write_text(json.dumps(summary))
            (Path(spec["data_root"]) / "report.md").write_text("synthetic NN0")
            self.assertEqual(lc.collect_data(spec, e)["status"], "PASS")
            bad = copy.deepcopy(plan)
            bad["family_ids"][0] += 1
            newref = self.store(bad, "substituted-plan")
            changed = copy.deepcopy(config)
            changed["arena_plan"] = newref
            changedexp = {
                **e,
                "config": self.store(changed),
                "canonical_plan_sha256": newref["sha256"],
            }
            changed_spec = {
                **spec,
                "approved_plan": newref,
                "experiment": self.store(changedexp),
            }
            with self.assertRaises(lc.Refused):
                lc.arena_analysis_check(changed_spec, changedexp)
            summary["planned"] += 1
            (Path(spec["data_root"]) / "summary.json").write_text(json.dumps(summary))
            self.assertEqual(lc.collect_data(spec, e)["status"], "FAILED")
            (Path(spec["data_root"]) / "summary.json").write_text('{"torn":')
            self.assertEqual(lc.collect_data(spec, e)["status"], "FAILED")

    def test_diagnostic_ids_roles_and_missing_proposal_census(self):
        plan, pref, e, _ = self.fixture([19, 71], [42])
        spec, e, config = self.analysis(plan, pref, e)
        decision, dref, _, _ = self.fixture(
            [3, 90], [99, 0], mode="whole_wall_time", off=True, decision=True
        )
        # Arbitrary IDs and two engines; no requirement to contain IDs0/1/2.
        selection = self.store(
            {
                "selected_before_outputs": True,
                "parents": [{"id": 3}, {"id": 90}],
                "exclusions": [],
            }
        )
        config.update(
            decision_plan=dref,
            diagnostic_selection=selection,
            decision_batches=[
                {"batch": b["batch"], "completion": None} for b in decision["batches"]
            ],
            linked_examples_limit=1,
        )
        e = {**e, "config": self.store(config), "inputs": [pref, dref, selection]}
        spec["experiment"] = self.store(e)
        spec["settings"] = self.store({"kind": "sequence", "runs": [copy.deepcopy(spec)]})
        result, _ = lc.arena_analysis(spec, e)
        self.assertEqual(result["diagnostic_planned"], 4)
        self.assertEqual(result["diagnostics"]["missing"], 4)
        self.assertEqual(result["diagnostics"]["complete_all_engine_parents"], 0)
        self.assertEqual(result["diagnostics"]["engine_ids"], [99, 0])
        obs = {
            "action": 13,
            "pv": [13],
            "completed_depth": None,
            "stop": "budget",
            "value_stm": 0.25,
            "counters": {},
        }
        self.assertIsNone(
            lc.diagnostic_proposal({"slot": 0, "matchup": 99}, obs, {"kind": "mcts"})[
                "searched_value_stm"
            ]
        )
        self.assertEqual(
            lc.diagnostic_proposal({"slot": 1, "matchup": 0}, obs, {"kind": "nnue"})[
                "searched_value_stm"
            ],
            0.25,
        )

    def test_partial_producer_and_sigma_declared_identity_refusals(self):
        plan, pref, base, _ = self.fixture([19, 71], [7])
        spec, e, config = self.analysis(plan, pref, base)
        origin = {
            **spec,
            "writer": "synthetic377",
            "approved_plan": pref,
            "experiment": self.store(base),
        }
        origin["settings"] = self.store(
            {
                "kind": "sequence",
                "arena": {"range": [0, 0], "template": copy.deepcopy(origin)},
            }
        )
        intent = self.store(origin)
        completed = {
            "schema": lc.COMPLETION_SCHEMA,
            "kind": "run",
            "status": "FAILED",
            "primary": {"stage": "interrupted"},
            "secondary": [],
            "cleanup_complete": True,
            "remaining": [],
            "checks": [],
            "experiment": origin["experiment"],
            "intent": intent,
            "data": {"files": []},
        }
        cref = self.store(completed)
        config["batches"][0]["completion"] = cref
        e = {
            **e,
            "config": self.store(config),
            "inputs": [pref, cref, intent, origin["experiment"], base["config"]],
        }
        spec["experiment"] = self.store(e)
        spec["settings"] = self.store({"kind": "sequence", "runs": [copy.deepcopy(spec)]})
        summary, _ = lc.arena_analysis(spec, e)
        self.assertEqual(len(summary["errors"]), 1)
        self.assertEqual(summary["matchups"][0]["counts"]["unknown"], 4)
        self.assertEqual(summary["operation_provenance"][0]["status"], "FAILED")
        # Typed identity metadata, no model/library load or backend session.
        fake = self.store({"no_model_payload": True})
        sigma = copy.deepcopy(plan)
        sigma["comparison"] = "whole_wall_time"
        sigma["models"] = []
        sigma["inputs"].append(fake)
        m = sigma["matchups"][0]
        m["engines"] = [
            {"kind": "mcts", "model": None},
            {"kind": "distance", "model": None},
        ]
        m["evaluator_sha256"] = [fake["sha256"], "a" * 64]
        m["inference"] = {
            "backend": "ort",
            "model": fake["path"],
            "model_sha": fake["sha256"],
            "library": "/synthetic/not-loaded-ort.so",
        }
        current = {"dynamic_libraries": [{"file": {"path": m["inference"]["library"]}}]}
        lc.arena_model_check(current, sigma, 2)
        with self.assertRaises(lc.Refused):
            lc.arena_model_check({"dynamic_libraries": []}, sigma, 2)
        m["inference"]["model_sha"] = "0" * 64
        with self.assertRaises(lc.Refused):
            lc.arena_model_check(current, sigma, 2)

    def test_synthetic_colour_pair_scores_partial_bounds_and_selected_resampling(self):
        plan, _, _, _ = self.fixture([19, 71], [7])
        schedule = lc.document(plan["schedule"])
        rows = {
            0: ({"started": True, "status": "goal", "winner": 0, "failure": None}, {}),
            1: (
                {"started": True, "status": "draw", "winner": None, "failure": None},
                {},
            ),
            2: (
                {
                    "started": True,
                    "status": "unknown",
                    "winner": None,
                    "failure": "ply_cap",
                },
                {},
            ),
            3: ({"started": True, "status": "goal", "winner": 0, "failure": None}, {}),
        }
        config = {
            "bootstrap_resamples": 7,
            "bootstrap_seed": 19,
            "central_interval": "80%",
        }
        table = lc.arena_score_tables(plan, schedule, rows, config)[0]
        self.assertEqual(table["counts"]["planned"], 4)
        self.assertEqual(table["counts"]["cap"], 1)
        self.assertEqual(table["complete_colour_pairs"], 1)
        self.assertEqual(table["complete_pair_mean"], 0.75)
        self.assertEqual(table["planned_game_missingness_bounds"], [0.375, 0.625])
        self.assertEqual(lc.arena_score_tables(plan, schedule, rows, config)[0], table)
        rows[2] = (
            {"started": True, "status": "goal", "winner": 1, "failure": None},
            {},
        )
        known = lc.arena_score_tables(plan, schedule, rows, config)[0]
        self.assertEqual(known["counts"]["unknown"], 0)
        self.assertEqual(known["complete_pair_mean"], 0.375)
        self.assertEqual(len(known["conditional_complete_pair_interval"]), 2)
        # Original128-family/256-slot denominator arithmetic, without any old
        # result read or10000-sample replay.
        self.assertEqual(2 * 128, 256)
        self.assertEqual((128 + 64) / 256, 0.75)

    def test_original_interval_arithmetic_and_invalid_selected_parameters(self):
        tail = lc.interval_tail("98.33333333333333%")
        self.assertEqual(math.floor(9999 * tail), 9999 // 120)
        self.assertEqual(math.ceil(9999 * (1 - tail)), (119 * 9999 + 119) // 120)
        for interval in ("0%", "100%", "NaN%", True, "80"):
            with self.assertRaises(lc.Refused):
                lc.interval_tail(interval)
        plan, pref, e, _ = self.fixture([19], [7])
        spec, e, config = self.analysis(plan, pref, e)
        for field, value in (
            ("bootstrap_seed", True),
            ("bootstrap_resamples", 0),
            ("central_interval", "Infinity%"),
        ):
            bad = {**config, field: value}
            newexp = {**e, "config": self.store(bad)}
            # Use the original immutable selected config: even a pair of new
            # mutually agreeing files cannot replace its issuing settings.
            with self.assertRaises(lc.Refused):
                lc.arena_analysis_check(spec, newexp)

    def test_interval_requires_two_complete_colour_pairs(self):
        config = {
            "bootstrap_resamples": 7,
            "bootstrap_seed": 19,
            "central_interval": "80%",
        }
        for families in ([19], [19, 71]):
            with self.subTest(families=families):
                plan, _, _, _ = self.fixture(families, [7])
                rows = {
                    0: (
                        {
                            "started": True,
                            "status": "goal",
                            "winner": 0,
                            "failure": None,
                        },
                        {},
                    ),
                    1: (
                        {
                            "started": True,
                            "status": "goal",
                            "winner": 0,
                            "failure": None,
                        },
                        {},
                    ),
                }
                if len(families) == 2:
                    rows[2] = (
                        {
                            "started": True,
                            "status": "goal",
                            "winner": 1,
                            "failure": None,
                        },
                        {},
                    )
                    rows[3] = (
                        {
                            "started": True,
                            "status": "unknown",
                            "winner": None,
                            "failure": "ply_cap",
                        },
                        {},
                    )
                table = lc.arena_score_tables(plan, lc.document(plan["schedule"]), rows, config)[0]
                self.assertEqual(table["complete_colour_pairs"], 1)
                self.assertEqual(table["complete_pair_mean"], 0.5)
                self.assertIsNone(table["conditional_complete_pair_interval"])
                self.assertEqual(
                    table["conditional_interval_unavailable_reason"],
                    "fewer_than_two_complete_colour_pairs",
                )
                self.assertEqual(table["counts"]["planned"], 2 * len(families))
                self.assertEqual(table["counts"]["unknown"], len(families) - 1)
                self.assertEqual(
                    table["planned_game_missingness_bounds"],
                    [0.5, 0.5] if len(families) == 1 else [0.25, 0.5],
                )

    def test_unverified_diagnostic_selection_relation_is_explicit(self):
        plan, pref, e, _ = self.fixture([19, 71], [42])
        spec, e, config = self.analysis(plan, pref, e)
        _, dref, _, _ = self.fixture(
            [3, 90], [99, 0], mode="whole_wall_time", off=True, decision=True
        )
        selection = self.store(
            {
                "selected_before_outputs": True,
                "parents": [{"family_id": 3}, {"family_id": 3}],
                "exclusions": [],
            }
        )
        config.update(
            decision_plan=dref,
            diagnostic_selection=selection,
            decision_batches=[
                {"batch": 0, "completion": None},
                {"batch": 1, "completion": None},
            ],
        )
        e = {**e, "config": self.store(config), "inputs": [pref, dref, selection]}
        spec["experiment"] = self.store(e)
        spec["settings"] = self.store({"kind": "sequence", "runs": [copy.deepcopy(spec)]})
        summary, report = lc.arena_analysis(spec, e)
        self.assertEqual(summary["diagnostic_selection_relation"], "OPAQUE_UNVERIFIED")
        self.assertIn("opaque/unverified", report)
        self.assertEqual(summary["diagnostic_planned"], 4)
        self.assertEqual(summary["diagnostics"]["unknown"], 4)

    def test_shared_pcg64_linear_reuses_one_table_and_refuses_incomplete_pairs(self):
        # Fake deterministic table/interface only: no NumPy/RNG/model/geometry call.
        import struct
        import sys
        from types import SimpleNamespace
        from unittest import mock

        class FixedIndices(list):
            def astype(self, dtype, *, copy):
                self_dtype = dtype
                assert self_dtype == "<u8" and copy is False
                return self

            def tobytes(self, *, order):
                assert order == "C"
                return b"".join(struct.pack("<QQ", *row) for row in self)

        indices = FixedIndices([[0, 0], [1, 1], [0, 1], [1, 0]])
        rng = SimpleNamespace(integers=mock.Mock(return_value=indices))
        quantile = mock.Mock(
            side_effect=lambda values, _q, *, method: SimpleNamespace(
                tolist=lambda: [min(values), max(values)]
            )
        )
        fake = SimpleNamespace(
            __version__="NN0-FAKE-NOT-NUMPY",
            uint64=object(),
            random=SimpleNamespace(
                PCG64=mock.Mock(return_value="fake-PCG64"),
                Generator=mock.Mock(return_value=rng),
            ),
            quantile=quantile,
        )
        plan = {"family_ids": [0, 1], "matchups": [{"id": m} for m in range(3)]}
        schedule = []
        observed = {}
        for matchup in range(3):
            for family in range(2):
                for colour in range(2):
                    slot = 4 * matchup + 2 * family + colour
                    schedule.append(
                        {
                            "slot": slot,
                            "matchup": matchup,
                            "family_id": family,
                            "candidate_color": colour,
                        }
                    )
                    draw = matchup == 2
                    observed[slot] = (
                        {
                            "started": True,
                            "status": "draw" if draw else "goal",
                            "winner": None
                            if draw
                            else (colour if (matchup + family) % 2 == 0 else 1 - colour),
                            "failure": None,
                        },
                        None,
                    )
        config = {
            "bootstrap_method": "shared_pcg64_linear",
            "bootstrap_resamples": 4,
            "bootstrap_seed": 19,
            "central_interval": "295/3%",
        }
        with mock.patch.dict(sys.modules, {"numpy": fake}):
            tables = lc.arena_score_tables(plan, schedule, observed, config)
            fake.random.PCG64.assert_called_once_with(19)
            fake.random.Generator.assert_called_once_with("fake-PCG64")
            rng.integers.assert_called_once_with(0, 2, size=(4, 2), dtype=fake.uint64)
            self.assertEqual([t["counts"]["planned"] for t in tables], [4, 4, 4])
            self.assertEqual([t["complete_pair_mean"] for t in tables], [0.5] * 3)
            self.assertEqual(quantile.call_count, 3)
            for call in quantile.call_args_list:
                self.assertEqual(call.args[1], [1 / 120, 119 / 120])
                self.assertEqual(call.kwargs, {"method": "linear"})
            self.assertEqual(quantile.call_args_list[0].args[0], [0.0, 0.5, 0.5, 1.0])
            self.assertEqual(quantile.call_args_list[1].args[0], [0.0, 0.5, 0.5, 1.0])
            self.assertEqual(quantile.call_args_list[2].args[0], [0.5] * 4)
            self.assertEqual(len({t["family_resampling"]["index_sha256"] for t in tables}), 1)
            fake.random.PCG64.reset_mock()
            rng.integers.reset_mock()
            quantile.reset_mock()
            incomplete = lc.arena_score_tables(
                plan, schedule, {k: v for k, v in observed.items() if k != 0}, config
            )
            self.assertEqual(sum(t["counts"]["planned"] for t in incomplete), 12)
            self.assertEqual(sum(t["counts"]["unknown"] for t in incomplete), 1)
            self.assertTrue(
                all(
                    t["conditional_complete_pair_interval"] is None
                    and t["conditional_interval_unavailable_reason"]
                    == "incomplete_planned_colour_pair_in_shared_contrasts"
                    for t in incomplete
                )
            )
            fake.random.PCG64.assert_not_called()
            rng.integers.assert_not_called()
            quantile.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
