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
                "search_source_sha256": ["c" * 64, "c" * 64],
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
            "source": {"files": [], "compiled_sources": {}},
            "compiled_sources": {},
            "checks": [{"role": role} for role in ("test", "lint", "build", "bindings")],
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
                for n, file in (("journal", "completed.jsonl"), ("result", "result.json"))
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

    def ports(self):
        # Only unrelated prior build/source/caller membership ports are synthetic.
        stack = ExitStack()
        stack.enter_context(patch.object(lc, "source_check", return_value=None))
        stack.enter_context(patch.object(lc, "caller_source_refs", return_value=[]))
        stack.enter_context(patch.object(lc, "build_input_refs", return_value=[]))
        return stack

    def test_two_counts_depths_and_model_refs_cross_actual_entry_then_publication(self):
        for families, depth in ((2, 4), (3, 5)):
            with self.subTest(families=families, depth=depth), tempfile.TemporaryDirectory() as t:
                self.tmp = type("TMP", (), {"name": t})()
                spec, e, _, config, slots = self.fixture(families, depth)
                with self.ports():
                    actual, _, _ = lc.experiment_check(spec)
                self.assertEqual(actual, e)
                Path(spec["data_root"]).mkdir()
                rows = [
                    {
                        "game": s["local_game"],
                        "family": f"{config['run_id']}-family-{s['local_game'] // 2:06}",
                        "candidate_color": s["candidate_color"],
                        "status": "unknown",
                        "failure": "ply_cap",
                        "moves": [],
                        "observations": [],
                    }
                    for s in slots
                ]
                Path(spec["data"][0]["path"]).write_text(
                    "".join(json.dumps(r) + "\n" for r in rows)
                )
                Path(spec["data"][1]["path"]).write_text(
                    json.dumps(
                        {
                            "run_id": config["run_id"],
                            "planned": len(slots),
                            "all_workers_joined": True,
                            "stopped": None,
                            "outcomes": rows,
                        }
                    )
                )
                data = lc.collect_data(spec, e)
                self.assertEqual(data["status"], "PASS", data["errors"])
                self.assertEqual(data["observed_local_games"], list(range(len(slots))))
                self.assertFalse(data["global_campaign_complete"])
                self.assertEqual(data["planned_slots"], families * 2)
                # Available valid prefix survives a partial directory, with explicit missing UNKNOWN.
                Path(spec["data"][0]["path"]).write_text(json.dumps(rows[0]) + "\n")
                partial = lc.collect_data(spec, e)
                self.assertEqual(partial["status"], "FAILED")
                self.assertEqual(len(partial["files"]), 2)
                self.assertEqual(partial["observed_local_games"], [0])
                self.assertEqual(partial["missing_local_games"], list(range(1, len(slots))))
                self.assertEqual(partial["planned_slots"], families * 2)

    def test_validated_prefix_survives_torn_tail_but_invalid_boundary_stops(self):
        # Actual approved-plan/collect_data FileRef path; fixture assets are metadata only.
        with tempfile.TemporaryDirectory() as t:
            self.tmp = type("TMP", (), {"name": t})()
            spec, e, _, config, slots = self.fixture(2, 4)
            Path(spec["data_root"]).mkdir()
            rows = [
                {
                    "game": slot["local_game"],
                    "family": f"{config['run_id']}-family-{slot['local_game'] // 2:06}",
                    "candidate_color": slot["candidate_color"],
                    "status": "unknown",
                    "failure": "ply_cap",
                    "moves": [],
                    "observations": [],
                }
                for slot in slots
            ]
            journal = Path(spec["data"][0]["path"])
            result = Path(spec["data"][1]["path"])
            result.write_text(
                json.dumps(
                    {
                        "run_id": config["run_id"],
                        "planned": len(slots),
                        "all_workers_joined": True,
                        "stopped": None,
                        "outcomes": rows,
                    }
                )
            )
            row0 = json.dumps(rows[0]).encode()
            invalid = {**rows[1], "candidate_color": 0}
            cases = (
                (row0 + b'\n{"game":1', [0], "Refused", "partial journal tail"),
                (row0, [], "Refused", "partial journal tail"),
                (
                    row0
                    + b"\n"
                    + json.dumps(invalid).encode()
                    + b"\n"
                    + json.dumps(rows[2]).encode()
                    + b'\n{"game":3',
                    [0],
                    "Refused",
                    "journal family/colour drift",
                ),
                (
                    b"{bad}\n" + row0 + b'\n{"game":1',
                    [],
                    "JSONDecodeError",
                    "Expecting property name",
                ),
            )
            for raw, observed, error_type, message in cases:
                with self.subTest(observed=observed, error=message, raw=raw):
                    journal.write_bytes(raw)
                    expected_refs = [lc.bound(journal)[0], lc.bound(result)[0]]
                    data = lc.collect_data(spec, e)
                    self.assertEqual(data["status"], "FAILED")
                    self.assertEqual(data["planned_slots"], len(slots))
                    self.assertEqual(data["planned_global_slots"], list(range(len(slots))))
                    self.assertEqual(data["observed_local_games"], observed)
                    self.assertEqual(
                        data["missing_local_games"],
                        [i for i in range(len(slots)) if i not in observed],
                    )
                    self.assertEqual(data["files"], expected_refs)
                    self.assertEqual(journal.read_bytes(), raw)
                    self.assertFalse(data["global_campaign_complete"])
                    self.assertEqual(len(data["errors"]), 1)
                    error = data["errors"][0]
                    self.assertEqual(error["stage"], "scientific_journal")
                    self.assertEqual(error["type"], error_type)
                    self.assertIn(message, error["message"])

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
            row = {"moves": [13], "observations": [obs]}
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
            partial["moves"] = []
            lc.arena_observation(c, partial)
            c["arena"]["comparison"] = "evaluator_wall_time"
            obs["deadline_ns"] = 10
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
