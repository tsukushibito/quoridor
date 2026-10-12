"""361 affected entry/publication definitions, NOT_RUN under source-only support.

Fake native bytes/models, source-adoption ports and guardian returns are explicitly
synthetic. Actual FileRef I/O, approved admission, experiment_check, plan/schedule
and collect_data/command code run unchanged when this scope is funded. No engines,
model factory, geometry, Search, subprocess, job or existing successful test runs.
"""

from contextlib import ExitStack
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import zlib
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get("ARENA_361_MAIN_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / "python"))
SOURCE = Path(os.environ.get("ARENA_361_LIFECYCLE", ROOT / "scripts/dev/research-lifecycle.py"))
module = importlib.util.spec_from_file_location("arena361_lifecycle", SOURCE)
lc = importlib.util.module_from_spec(module)
module.loader.exec_module(lc)


class ArenaPlanTests(unittest.TestCase):
    def json_file(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, allow_nan=False))
        return lc.bound(path)[0]

    def fixture(self, families, depth):
        self.root = Path(self.tmp.name)
        artifact = self.root / "FAKE_NATIVE_NOT_EXECUTABLE"
        artifact.write_bytes(b"synthetic only; never executed")
        artifact_ref = lc.bound(artifact)[0]
        weights = self.root / f"FAKE_WEIGHTS_{depth}"
        weights.write_bytes(b"no model; metadata only")
        weights_ref = lc.bound(weights)[0]
        model = {
            "descriptor": self.json_file(
                f"descriptor-{depth}.json", {"weights_SHA": weights_ref["sha256"]}
            ),
            "weights": weights_ref,
            "evaluator_sha256": str(depth) * 64,
        }
        engine = {
            "kind": "nnue",
            "model": model["descriptor"]["path"],
            "distance_a": 0,
            "distance_b": 8,
            "depth": depth,
            "max_nodes": 999,
            "time_ms": None,
            "simd": False,
        }
        other = {**engine, "kind": "distance", "model": None}
        fs = [
            {
                "family_id": i + 100,
                "id": f"FAKE-FAMILY-{i}",
                "seed": i + 1,
                "prefix": [13 + i],
                "root_key": "FAKE_NOT_GEOMETRY",
                "history_counts": [["FAKE_NOT_GEOMETRY", 1]],
            }
            for i in range(families)
        ]
        book = self.json_file(
            "book.json",
            {
                "complete": True,
                "rules": "research-standard-2p-threefold-goal-first-v1",
                "families": fs,
            },
        )
        slots = [
            {
                "slot": i,
                "batch": 0,
                "matchup": 7,
                "local_game": i,
                "family_id": fs[i // 2]["family_id"],
                "candidate_color": i % 2,
            }
            for i in range(families * 2)
        ]
        schedule = self.json_file("schedule.json", slots)
        config = {
            "ruleset": "standard_2p_threefold",
            "run_id": "fake-generic-entry",
            "games": len(slots),
            "output": str(self.root / "science"),
            "workers": 1,
            "active_games": 1,
            "max_batch": 1,
            "max_output_bytes": 1048576,
            "engines": [engine, other],
            "arena": {
                "comparison": "evaluator_fixed_depth",
                "clock_policy": "strict_unknown",
                "return_reserve_ms": 0,
                "tt_entries": 37,
                "retained_outcome_bytes": 32768,
                "evaluator_sha256": [model["evaluator_sha256"], "b" * 64],
                "search_artifact_sha256": ["c" * 64, "c" * 64],
                "first_candidate_colors": [0] * families,
                "book": {
                    "openings": [
                        {
                            "id": f["id"],
                            "prefix": f["prefix"],
                            "original_seed": f["seed"],
                            "reference": {
                                "source_sha256": book["sha256"],
                                "settings": {
                                    k: f[k] for k in ("family_id", "root_key", "history_counts")
                                },
                            },
                        }
                        for f in fs
                    ]
                },
            },
        }
        config_ref = self.json_file("config.json", config)
        plan = {
            "schema": "quoridor.research.arena-plan.v1",
            "phase": "arena",
            "comparison": "evaluator_fixed_depth",
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "book": book,
            "inputs": [book],
            "models": [model],
            "schedule": schedule,
            "family_ids": [f["family_id"] for f in fs],
            "matchups": [
                {
                    "id": 7,
                    "engines": config["engines"],
                    "evaluator_sha256": config["arena"]["evaluator_sha256"],
                }
            ],
            "batches": [
                {"batch": 0, "matchup": 7, "config": config_ref, "slots": list(range(len(slots)))}
            ],
            "planned_slots": len(slots),
        }
        plan_ref = self.json_file("approved-plan.json", plan)
        build = {
            "schema": lc.BUILD_SCHEMA,
            "status": "PASS",
            "cleanup_complete": True,
            "remaining": [],
            "artifact": artifact_ref,
            "source": {"fixture_only": "NOT BUILD PROVENANCE"},
            "checks": [{"role": role} for role in ("test", "lint", "build")],
            "dependency_refs": [],
            "tools": {},
        }
        build_ref = self.json_file("FAKE-build.json", build)
        e = {
            "schema": lc.EXPERIMENT_SCHEMA,
            "phase": "arena",
            "build_manifest": build_ref,
            "config": config_ref,
            "inputs": [book],
            "models": [model],
            "dynamic_libraries": [],
            "schedule": schedule,
            "numerical_qualification": self.json_file(
                "FAKE-Q-NOT-SCIENCE.json", {"fixture": "No numerical certificate"}
            ),
            "canonical_plan_sha256": plan_ref["sha256"],
            "rules": plan["rules"],
            "distance_units": plan["distance_units"],
            "value_perspective": plan["value_perspective"],
            "planned_slots": len(slots),
            "batch": 0,
            "argv": [
                str(artifact),
                "arena",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        }
        e_ref = self.json_file("experiment.json", e)
        spec = {
            "kind": "run",
            "owner": str(self.root),
            "output": str(self.root / "operation"),
            "data_root": config["output"],
            "approved_plan": plan_ref,
            "experiment": e_ref,
            "artifact": artifact_ref,
            "finalizers": [],
            "intent_sha256": "f" * 64,
            "support": self.json_file("support.json", {"fixture": "not issued"}),
            "limits": {},
            "argv": [
                a.replace("@EXPERIMENT@", e_ref["path"]).replace(
                    "@EXPERIMENT_SHA256@", e_ref["sha256"]
                )
                for a in e["argv"]
            ],
            "data": [
                {"name": n, "path": str(Path(config["output"]) / file), "limit_B": 1048576}
                for n, file in (
                    ("journal", "completed.jsonl.gz"),
                    ("result", "result.json"),
                    ("native_manifest", "manifest.json"),
                )
            ],
        }
        spec["admission"] = self.json_file(
            "admission.json",
            {
                "schema": "quoridor.research.phase-admission.v1",
                "ready": True,
                "owner": spec["owner"],
                "limits": spec["limits"],
                "spec_sha256": spec["intent_sha256"],
                "support_sha256": spec["support"]["sha256"],
                "approved_plan": plan_ref,
            },
        )
        return spec, e, plan, config, slots

    def test_three_engine_374_issued_family_budget_refuses_unissued_or_wider_envelopes(self):
        spec = {"kind": "run"}
        support = {
            "schema": "quoridor.research.phase-support.v1",
            "issue": "quoridor-4lc.374",
            "resources": {
                "CPU": 1,
                "threads": 1,
                "GPU": 0,
                "controller_included": True,
                "family_RAM_B": 3 * 1024**3,
            },
        }
        self.assertEqual(lc.issued_family_upper(spec, support), 3 * 1024**3)
        self.assertEqual(lc.issued_family_upper(spec, {}), 2 * 1024**3)
        self.assertEqual(lc.issued_family_upper({"kind": "build"}, support), 6 * 1024**3)
        for key, value in (
            ("family_RAM_B", 4 * 1024**3),
            ("CPU", 2),
            ("GPU", 1),
            ("controller_included", False),
        ):
            bad = copy.deepcopy(support)
            bad["resources"][key] = value
            with self.assertRaises(lc.Refused):
                lc.issued_family_upper(spec, bad)

    def test_three_engine_374_actual_cost_phase_binds_case_order_image_plan_and_full_requests(self):
        # Real metadata FileRefs and owning guards, fake image/library/model bytes only.
        # No config/model factory, import, clock, native or backend invocation.
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            spec, e, approved, _, _ = self.fixture(1, 4)
            onnx = self.json_file("FAKE-COST-MODEL.json", {"not_loaded": True})
            lib = self.json_file("FAKE-COST-LIB.json", {"not_loaded": True})
            measured = {
                "engines": [{"kind": "mcts"}, {"kind": "distance"}],
                "arena": {"evaluator_sha256": [onnx["sha256"], "b" * 64]},
                "inference": {
                    "model": onnx["path"],
                    "model_sha": onnx["sha256"],
                    "library": lib["path"],
                },
                "cpu_cores": [3],
                "inference_cpu_core": 3,
                "max_memory_bytes": 1024**3,
                "host_ram_reserve": 4 * 1024**3,
            }
            configs = [
                {
                    "file": {k: r[k] for k in ("path", "sha256")},
                    "normalized_sha256": str(i + 1) * 64,
                }
                for i, r in enumerate(
                    [
                        self.json_file("cost-D.json", measured),
                        self.json_file("cost-NN.json", {**measured, "fixture_opponent": "NN"}),
                    ]
                )
            ]
            phases = [
                {
                    "id": mode,
                    "mode": mode,
                    "max_logical_calls": 32,
                    "workload": [
                        {
                            "id": f"FAKE-{i}",
                            "configuration": i % 2,
                            "prefix": [13],
                            "stage": "warmup-and-measurement" if index == 0 else "timed-receipt",
                            "warmup_logical_calls": 1 - index,
                            "max_logical_calls": 2,
                        }
                        for i in range(16)
                    ],
                }
                for index, mode in enumerate(("untimed", "qualified-timed"))
            ]
            cases = self.json_file("cost-cases.json", {"configurations": configs, "phases": phases})
            approved["matchups"] = [
                {
                    "id": i,
                    "engines": measured["engines"],
                    "inference": measured["inference"],
                    "evaluator_sha256": measured["arena"]["evaluator_sha256"],
                }
                for i in range(2)
            ]
            approved["sigma_cost_cases"] = cases
            spec["approved_plan"] = self.json_file("cost-approved.json", approved)
            launched = lc.time.time_ns() // 1000000 - 1000
            native = {
                "executable_sha256": spec["artifact"]["sha256"],
                "backend_sha256": "c" * 64,
                "valid_until_unix_ms": launched + 86400000,
            }
            campaign = {
                "approved_plan": spec["approved_plan"],
                "configurations": configs,
                "native": native,
                "phases": phases,
                "maximum_total_logical_backend_rows_or_requests": 64,
                "cost_formula_prebound": {"factor": 4, "additive_margin_ns": 2000000},
                "qualification_started_unix_ms": launched,
                "valid_until_unix_ms": native["valid_until_unix_ms"],
            }
            campaign_ref = self.json_file("cost-campaign.json", campaign)
            plan = {
                "phase_id": "untimed",
                "mode": "untimed",
                "native": native,
                "configurations": configs,
                "campaign": {k: campaign_ref[k] for k in ("path", "sha256")},
                "max_logical_calls": 32,
                "prior_logical_calls": 0,
                "prior_results": [],
                "workload": phases[0]["workload"],
                "output": spec["data_root"],
            }
            e.update(
                phase="sigma-cost-qualification",
                planned_slots=64,
                batch=0,
                models=[],
                numerical_qualification=None,
                schedule=cases,
                config=self.json_file("cost-plan.json", plan),
                inputs=[campaign_ref, onnx, *[lc.bound(c["file"]["path"])[0] for c in configs]],
                dynamic_libraries=[{"file": lib, "version": "SYNTHETIC-not-loaded"}],
                argv=[
                    spec["artifact"]["path"],
                    "sigma-cost-measure",
                    "--experiment",
                    "@EXPERIMENT@",
                    "--experiment-sha256",
                    "@EXPERIMENT_SHA256@",
                ],
            )
            spec["limits"] = {
                "worker_cpu": 3,
                "family_B": 3 * 1024**3,
                "controller_B": 64 * 1024**2,
                "host_reserve_B": 4 * 1024**3,
            }
            spec["data"] = [
                {
                    "name": "measurement",
                    "path": str(Path(spec["data_root"]) / "measurement-result.json"),
                    "limit_B": lc.CONTROL_BYTES,
                }
            ]
            build = {"artifact": spec["artifact"]}
            lc.sigma_cost_check(spec, e, build, approved)
            for change in ("plan", "image", "calls", "order", "output", "model", "partial_phase"):
                bad = copy.deepcopy(plan)
                wrong_e = copy.deepcopy(e)
                wrong_spec = copy.deepcopy(spec)
                wrong_build = copy.deepcopy(build)
                if change == "plan":
                    wrong_spec["approved_plan"]["sha256"] = "0" * 64
                elif change == "image":
                    wrong_build["artifact"]["sha256"] = "0" * 64
                elif change == "calls":
                    bad["max_logical_calls"] = 31
                elif change == "order":
                    bad["workload"].reverse()
                elif change == "output":
                    bad["output"] += "-wrong"
                elif change == "model":
                    wrong_e["inputs"] = [r for r in wrong_e["inputs"] if r != onnx]
                else:
                    wrong_e["batch"] = 1
                wrong_e["config"] = self.json_file("changed-cost-plan.json", bad)
                with self.assertRaises((lc.Refused, KeyError, StopIteration)):
                    lc.sigma_cost_check(wrong_spec, wrong_e, wrong_build, approved)
            root = Path(spec["data_root"])
            root.mkdir()
            result = {
                "schema": "quoridor-sigma-receipt-measurement-result-v1",
                "complete": True,
                "all_workers_joined": True,
                "inflight_after_drain": 0,
                "stopped": None,
                "games_played": 0,
                "plan_sha256": e["config"]["sha256"],
                "campaign_sha256": campaign_ref["sha256"],
                "native": native,
                "phase_id": "untimed",
                "mode": "untimed",
                "configuration_sha256": [c["normalized_sha256"] for c in configs],
                "logical_calls_attempted": 32,
                "returned_terminal_replies": 32,
                "backend_work": {"logical_rows": 32, "physical_rows": 32, "failed_rows": 0},
                "items": [
                    {
                        "id": w["id"],
                        "configuration": w["configuration"],
                        "stage": w["stage"],
                        "parent": {"prefix": w["prefix"]},
                    }
                    for w in plan["workload"]
                ],
            }
            output = root / "measurement-result.json"
            output.write_text(json.dumps(result))
            self.assertEqual(lc.collect_data(spec, e)["status"], "PASS")
            result["returned_terminal_replies"] = 31
            output.write_text(json.dumps(result))
            data = lc.collect_data(spec, e)
            self.assertEqual(data["status"], "FAILED")
            self.assertEqual(data["planned_slots"], 64)

    def test_three_engine_374_closed_sigma_backend_and_current_libraries(self):
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            _, e, plan, c, _ = self.fixture(1, 4)
            onnx = self.json_file("FAKE-ONNX-NOT-LOADED.json", {"synthetic": True})
            library = self.json_file("FAKE-ORT-NOT-LOADED.json", {"synthetic": True})
            inference = {
                "backend": "ort",
                "model": onnx["path"],
                "model_sha": onnx["sha256"],
                "library": library["path"],
                "device": 0,
                "cuda_graph": False,
            }
            plan["comparison"] = "whole_wall_time"
            plan["inputs"].append(onnx)
            e["dynamic_libraries"] = [{"file": library, "version": "synthetic-not-loaded"}]
            plan["matchups"][0]["engines"][1]["kind"] = "mcts"
            plan["matchups"][0]["evaluator_sha256"][1] = onnx["sha256"]
            cost = self.json_file(
                "FAKE-COST-NOT-QUALIFIED.json",
                {"fixture": "metadata only; not clock qualification"},
            )
            plan["matchups"][0]["sigma_cost_qualification"] = cost
            e["inputs"].append(cost)
            plan["matchups"][0]["inference"] = inference
            lc.arena_model_check(e, plan, 2)
            wrong = copy.deepcopy(plan)
            wrong["matchups"][0]["inference"]["model_sha"] = "0" * 64
            with self.assertRaises(lc.Refused):
                lc.arena_model_check(e, wrong, 2)
            wrong_e = copy.deepcopy(e)
            wrong_e["dynamic_libraries"] = []
            with self.assertRaises(lc.Refused):
                lc.arena_model_check(wrong_e, plan, 2)
            wrong = copy.deepcopy(plan)
            wrong["comparison"] = "evaluator_wall_time"
            with self.assertRaises(lc.Refused):
                lc.arena_model_check(e, wrong, 2)

    def test_three_engine_374_single_parent_engine_schedule_and_unknown_denominator(self):
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            _, e, plan, c, _ = self.fixture(1, 4)
            c["games"] = 1
            c["engines"] = [c["engines"][0]]
            c["engines"][0]["time_ms"] = 100
            a = c["arena"]
            a["comparison"] = "whole_wall_time"
            a["decision_only"] = True
            a["disable_continuation_static_ordering"] = True
            a["return_reserve_ms"] = 5
            a["evaluator_sha256"] = a["evaluator_sha256"][:1]
            a["search_artifact_sha256"] = a["search_artifact_sha256"][:1]
            book = {"frozen_before_candidate_results": True, "openings": a["book"]["openings"]}
            plan["book"] = self.json_file("synthetic-decision-book.json", book)
            plan["inputs"] = [plan["book"]]
            plan["phase"] = e["phase"] = "compare"
            plan["comparison"] = "whole_wall_time"
            plan["planned_slots"] = e["planned_slots"] = 3
            plan["matchups"] = [
                {
                    "id": i,
                    "engines": c["engines"]
                    if i == 0
                    else [{**c["engines"][0], "kind": "distance", "model": None}],
                    "evaluator_sha256": a["evaluator_sha256"] if i == 0 else ["b" * 64],
                }
                for i in range(3)
            ]
            config_ref = self.json_file("synthetic-decision-config.json", c)
            plan["batches"] = [
                {"batch": i, "matchup": i, "config": config_ref, "slots": [i]} for i in range(3)
            ]
            slots = [
                {
                    "slot": i,
                    "batch": i,
                    "matchup": i,
                    "local_game": 0,
                    "family_id": 100,
                    "candidate_color": 0,
                }
                for i in range(3)
            ]
            plan["schedule"] = self.json_file("synthetic-decisions.json", slots)
            e.update(
                config=config_ref,
                inputs=plan["inputs"],
                schedule=plan["schedule"],
                argv=[
                    e["argv"][0],
                    "decisions",
                    "--experiment",
                    "@EXPERIMENT@",
                    "--experiment-sha256",
                    "@EXPERIMENT_SHA256@",
                ],
            )
            actual, _ = lc.arena_decision_plan_check(e, plan)
            self.assertEqual(actual, [slots[0]])
            wrong = copy.deepcopy(slots)
            wrong[2]["matchup"] = 0
            wrong_ref = self.json_file("synthetic-duplicate-decisions.json", wrong)
            wrong_plan = copy.deepcopy(plan)
            wrong_e = copy.deepcopy(e)
            wrong_plan["schedule"] = wrong_e["schedule"] = wrong_ref
            with self.assertRaises(lc.Refused):
                lc.arena_decision_plan_check(wrong_e, wrong_plan)
            wrong = copy.deepcopy(slots)
            wrong[1]["candidate_color"] = 1
            wrong_ref = self.json_file("synthetic-wrong-colour.json", wrong)
            wrong_plan["schedule"] = wrong_e["schedule"] = wrong_ref
            with self.assertRaises(lc.Refused):
                lc.arena_decision_plan_check(wrong_e, wrong_plan)

    def test_three_engine_374_sigma_authority_receipt_is_distinct_from_drain(self):
        c = {
            "engines": [{"kind": "mcts"}],
            "arena": {"decision_only": True, "comparison": "whole_wall_time"},
        }
        obs = {
            "engine_index": 0,
            "caller_seconds": 0.12,
            "thinking_seconds": 0.09,
            "value_stm": 0.2,
            "accepted": True,
            "failure": None,
            "engine_error": None,
            "action": 13,
            "pv": [],
            "completed_depth": None,
            "accepted_ns": 122,
            "admission_checked_ns": 121,
            "returned_ns": 120,
            "deadline_ns": 100,
            "counters": {
                "authority_receipt_ns": 90,
                "drain_finished_ns": 120,
                "authority_legal": True,
                "inflight_after_drain": 0,
                "completed_simulations": 1,
                "clock_contract": "authority-action-receipt-v1",
                "clock_contract_sha256": "04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d",
            },
        }
        row = {"observations": [obs], "moves": [7]}
        lc.arena_observation(c, row)
        for field, value in (
            ("authority_receipt_ns", 100),
            ("inflight_after_drain", 1),
            ("completed_simulations", 0),
        ):
            wrong = copy.deepcopy(row)
            wrong["observations"][0]["counters"][field] = value
            with self.assertRaises(lc.Refused):
                lc.arena_observation(c, wrong)
        wrong = copy.deepcopy(row)
        wrong["observations"][0]["completed_depth"] = 6
        with self.assertRaises(lc.Refused):
            lc.arena_observation(c, wrong)
        obs["engine_index"] = 1
        with self.assertRaises(lc.Refused):
            lc.arena_observation(c, row)

    def test_three_engine_374_exact_full_prefix_is_distinct_from_accepted_suffix(self):
        c = {
            "engines": [{"kind": "distance", "depth": 4}],
            "arena": {
                "comparison": "evaluator_fixed_depth",
                "book": {"openings": [{"prefix": [13, 67]}]},
            },
        }
        obs = {
            "engine_index": 0,
            "caller_seconds": 0.1,
            "thinking_seconds": 0.1,
            "value_stm": 0.2,
            "accepted": True,
            "failure": None,
            "engine_error": None,
            "action": 14,
            "pv": [14],
            "completed_depth": 4,
            "stop": "depth_cap",
            "accepted_ns": 12,
            "admission_checked_ns": 11,
            "returned_ns": 10,
            "deadline_ns": None,
            "counters": {"completed_snapshot_validation_failed": False},
        }
        row = {"game": 0, "observations": [obs], "moves": [13, 67, 14]}
        lc.arena_observation(c, row)
        for moves in ([14], [13, 66, 14], [13, 67]):
            wrong = copy.deepcopy(row)
            wrong["moves"] = moves
            with self.assertRaises(lc.Refused):
                lc.arena_observation(c, wrong)

    def ports(self):
        # Only unrelated prior build/source/caller membership ports are synthetic.
        stack = ExitStack()
        stack.enter_context(patch.object(lc, "source_metadata_check", return_value=None))
        stack.enter_context(patch.object(lc, "caller_source_refs", return_value=[]))
        stack.enter_context(patch.object(lc, "numerical_check", return_value=None))
        return stack

    def test_three_engine_374_reference_roundtrip_partial_torn_and_first_primary(self):
        # Synthetic native-shaped files through the real publisher reader/collect_data.
        # No native invocation, model, framework, geometry or Search.
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            spec, e, _, config, slots = self.fixture(1, 4)
            with self.ports():
                actual, _, _ = lc.experiment_check(spec)
            self.assertEqual(actual, e)
            root = Path(spec["data_root"])
            root.mkdir()
            rows = [
                {
                    "game": slot["local_game"],
                    "family": f"{config['run_id']}-family-000000",
                    "candidate_color": slot["candidate_color"],
                    "status": "unknown",
                    "started": False,
                    "failure": "ply_cap",
                    "moves": config["arena"]["book"]["openings"][0]["prefix"],
                    "observations": [],
                    "winner": None,
                    "reason": "original exact error",
                }
                for slot in slots
            ]
            raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows)
            encoder = zlib.compressobj(wbits=31)
            compressed = encoder.compress(raw) + encoder.flush()
            journal = root / "completed.jsonl.gz"
            journal.write_bytes(compressed)
            ref = lc.bound(journal)[0]
            report = {
                "run_id": config["run_id"],
                "planned": 2,
                "all_workers_joined": True,
                "stopped": None,
                "outcomes": [],
                "pump": {"publication_failures": []},
            }
            publication = {
                "schema": lc.ARENA_PUBLICATION,
                "report": report,
                "outcome_count": 2,
                "journal_count": 2,
                "journal_bytes": len(raw),
                "journal_sha256": lc.sha(raw),
                "failure_attribution": None,
                "archive_wall_seconds": 0.1,
                "archive_allocated_bytes": 4096,
                "archive": {
                    "encoding": "gzip-single-member-v1",
                    "compressed": ref,
                    "raw_sha256": lc.sha(raw),
                    "raw_bytes": len(raw),
                },
            }

            def publish(doc):
                (root / "result.json").write_text(json.dumps(doc))
                result_ref = lc.bound(root / "result.json")[0]
                native = {
                    "result": doc,
                    "binding": {
                        "config": config,
                        "executable_sha256": spec["artifact"]["sha256"],
                    },
                    "artifacts": {
                        "completed.jsonl.gz": {
                            k: doc["archive"]["compressed"][k] for k in ("sha256", "bytes", "mode")
                        },
                        "result.json": {k: result_ref[k] for k in ("sha256", "bytes", "mode")},
                    },
                    "cleanup": {"archive_closed_verified": True, "all_workers_joined": True},
                }
                (root / "manifest.json").write_text(json.dumps(native))
                return {
                    name: lc.bound(root / filename)[0]
                    for name, filename in (
                        ("journal", "completed.jsonl.gz"),
                        ("result", "result.json"),
                        ("native_manifest", "manifest.json"),
                    )
                }

            files = publish(publication)
            decoded = lc.arena_reference_report(config, files)
            self.assertEqual(decoded["outcomes"], rows)
            self.assertEqual(publication["report"]["outcomes"], [])
            data = lc.collect_data(spec, e)
            self.assertEqual(data["status"], "PASS", data["errors"])
            self.assertEqual(data["observed_local_games"], [0, 1])
            self.assertFalse(data["global_campaign_complete"])
            partial = copy.deepcopy(publication)
            partial["report"]["stopped"] = "inference:immutable first primary"
            partial["report"]["pump"]["publication_failures"] = [
                {"game": None, "reason": "secondary sync"}
            ]
            partial["failure_attribution"] = "engine_error"
            publish(partial)
            failed = lc.collect_data(spec, e)
            self.assertEqual(failed["status"], "FAILED")
            self.assertEqual(journal.read_bytes(), compressed)
            self.assertEqual(
                lc.arena_reference_report(config, publish(partial))["stopped"],
                partial["report"]["stopped"],
            )
            # Hash-consistent torn footer, extra member, duplicate ID and missing slot refuse.
            for encoded, logical in (
                (compressed[:-3], raw),
                (compressed + compressed, raw),
                (
                    zlib.compress(raw.replace(b'"game":1', b'"game":0'), wbits=31),
                    raw.replace(b'"game":1', b'"game":0'),
                ),
                (zlib.compress(raw[:-1], wbits=31), raw[:-1]),
            ):
                journal.write_bytes(encoded)
                bad = copy.deepcopy(publication)
                bad["archive"].update(
                    compressed=lc.bound(journal)[0],
                    raw_sha256=lc.sha(logical),
                    raw_bytes=len(logical),
                )
                with self.assertRaises((lc.Refused, zlib.error)):
                    lc.arena_reference_report(config, publish(bad))
            journal.write_bytes(compressed)
            files = publish(publication)
            journal.unlink()  # Controlled synthetic missing/IO case, no research data.
            failure = lc.collect_data(spec, e)
            self.assertEqual(failure["status"], "FAILED")
            self.assertEqual(failure["planned_slots"], 2)
            self.assertEqual(failure["missing_local_games"], [0, 1])

    def test_three_engine_374_saved_analysis_keeps_missing_denominators(self):
        # Pure declared-slot metadata, zero synthetic scientific rows/outputs/models.
        # Only the admission port is mocked; aggregate bookkeeping/resampling runs unchanged.
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            self.root = Path(t)
            slots = []
            for family in range(128):
                for matchup in range(3):
                    for colour in range(2):
                        slots.append(
                            {
                                "slot": len(slots),
                                "family_id": family,
                                "matchup": matchup,
                                "candidate_color": colour,
                                "batch": len(slots) // 2,
                                "local_game": colour,
                            }
                        )
            schedule = self.json_file("synthetic-full-slot-metadata.json", slots)
            plan = self.json_file(
                "synthetic-plan.json",
                {"schedule": schedule, "matchups": [{"id": i} for i in range(3)]},
            )
            selection = self.json_file(
                "synthetic-selection.json",
                {"parents": [], "exclusions": [], "selected_before_outputs": True},
            )
            config = {
                "arena_plan": plan,
                "diagnostic_selection": selection,
                "decision_plan": None,
                "decision_batches": [],
                "batches": [{"batch": i, "completion": None} for i in range(384)],
            }
            with patch.object(lc, "arena_analysis_check", return_value=config):
                result, _ = lc.arena_analysis({}, {})
            self.assertEqual(result["planned"], 768)
            self.assertEqual(result["diagnostic_planned"], 0)
            self.assertEqual(
                result["diagnostics"]["NNUE_pretanh_posttanh_saturation"],
                "UNKNOWN_NOT_RECORDED_NO_EXTRA_FORWARD",
            )
            for table in result["matchups"]:
                self.assertEqual(table["counts"]["planned"], 256)
                self.assertEqual(table["counts"]["unknown"], 256)
                self.assertEqual(table["counts"]["missing"], 256)
                self.assertEqual(table["complete_colour_pairs"], 0)
                self.assertEqual(table["planned_game_missingness_bounds"], [0, 1])
                self.assertIsNone(table["conditional_complete_pair_interval"])
                self.assertEqual(table["empty_family_resamples"], 10000)

    def test_consistently_substituted_plan_and_experiment_cannot_change_launch_authority(self):
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            spec, e, plan, _, _ = self.fixture(2, 4)
            changed = {**plan, "family_ids": [999, 998]}
            replacement = self.json_file("substitution.json", changed)
            e["canonical_plan_sha256"] = replacement["sha256"]
            spec["experiment"] = self.json_file("substituted-experiment.json", e)
            spec["argv"] = [
                a.replace("@EXPERIMENT@", spec["experiment"]["path"]).replace(
                    "@EXPERIMENT_SHA256@", spec["experiment"]["sha256"]
                )
                for a in e["argv"]
            ]
            with self.ports(), self.assertRaisesRegex(lc.Refused, "substituted approved plan"):
                lc.experiment_check(spec)
            spec["approved_plan"] = replacement
            with self.assertRaisesRegex(lc.Refused, "integration-issued approved"):
                lc.approved_plan(spec, e)

    def test_missing_pairs_config_limit_identity_or_hash_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            _, e, plan, _, slots = self.fixture(2, 4)
            for change in (
                lambda p: p["batches"][0]["slots"].pop(),
                lambda p: p["family_ids"].append(999),
                lambda p: p["batches"][0].__setitem__("matchup", 8),
            ):
                bad = copy.deepcopy(plan)
                change(bad)
                with self.assertRaises((lc.Refused, KeyError)):
                    lc.planned_game_slice(e, slots, bad)
            path = Path(e["config"]["path"])
            config = json.loads(path.read_bytes())
            config["engines"][1]["depth"] = 3
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(lc.Refused, "reference drift"):
                lc.arena_plan_check(e, plan)

    def test_partial_depth_nonfinite_illegal_timing_and_actual_guardian_cleanup_refuse(self):
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            _, _, _, c, _ = self.fixture(2, 4)
            obs = {
                "engine_index": 0,
                "accepted": True,
                "failure": None,
                "engine_error": None,
                "action": 13,
                "pv": [13],
                "accepted_ns": 12,
                "admission_checked_ns": 11,
                "returned_ns": 10,
                "caller_seconds": 0.1,
                "thinking_seconds": 0.1,
                "value_stm": 0.2,
                "completed_depth": 4,
                "stop": "depth_cap",
                "deadline_ns": None,
                "counters": {
                    "completed_snapshot_validation_failed": False,
                    "authority_receipt_ns": 10,
                    "drain_finished_ns": 10,
                },
            }
            row = {"game": 0, "moves": [13, 13], "observations": [obs]}
            lc.arena_observation(c, row)
            for key, value in (
                ("completed_depth", 3),
                ("value_stm", float("inf")),
                ("failure", "illegal_move"),
                ("pv", [22]),
            ):
                bad = copy.deepcopy(row)
                bad["observations"][0][key] = value
                with self.assertRaises(lc.Refused):
                    lc.arena_observation(c, bad)
            partial = copy.deepcopy(row)
            partial["observations"][0].update(
                accepted=False, completed_depth=3, failure="incomplete_depth"
            )
            partial["moves"] = [13]
            lc.arena_observation(c, partial)
            c["arena"]["comparison"] = "evaluator_wall_time"
            obs["deadline_ns"] = 100
            lc.arena_observation(c, row)
            obs["counters"]["drain_finished_ns"] = 9
            with self.assertRaises(lc.Refused):
                lc.arena_observation(c, row)
            record = {
                "exit_code": 0,
                "remaining": [],
                "cleanup_complete": False,
                "direct_child_reaped": True,
            }
            directory = self.root / "command"
            directory.mkdir()
            ledger = []
            with self.assertRaises(lc.Refused):
                lc.command(
                    {"limits": {"log_B": 128, "worker_cpu": 4}, "cwd": str(self.root), "env": {}},
                    {"name": "fake-guardian", "argv": ["NOT_EXECUTED"]},
                    directory,
                    None,
                    executor=lambda *_a, **_kw: record,
                    ledger=ledger,
                )
            self.assertIs(ledger[0]["guardian_return"], record)
            self.assertEqual(ledger[0]["guardian_return"]["cleanup_complete"], False)


if __name__ == "__main__":
    unittest.main()
