"""New lifecycle adapter discriminators: tiny owned metadata, no real science."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import lifecycle355 as life
import observations355
import stream355
import strength355 as s

HERE = Path(__file__).resolve().parent


def ref(path, sha="a" * 64):
    return {"path": str(path), "sha256": sha, "bytes": 1, "mode": "0644"}


class LifecycleAdapter(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="synthetic-lifecycle-v9-", dir=HERE)
        self.root = Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)

    def test_artifact_and_raw_ordered_numerical_arrays(self):
        experiment = {
            "phase": "analysis",
            "config": ref(self.root / "config"),
            "schedule": ref(self.root / "schedule", "b" * 64),
            "inputs": [ref(self.root / "i1", "c" * 64), ref(self.root / "i2", "d" * 64)],
            "models": [],
            "numerical_qualification": ref(self.root / "numeric"),
        }
        build = {
            "artifact": ref(self.root / "artifact", "e" * 64),
        }
        numerical = {
            "schema": life.PREFIX + "numerical-qualification.v1",
            "status": "PASS",
            "phase": "analysis",
            "artifact_sha256": "e" * 64,
            "config_sha256": "a" * 64,
            "schedule_sha256": "b" * 64,
            "input_sha256": ["c" * 64, "d" * 64],
            "descriptor_sha256": [],
            "weights_sha256": [],
            "evaluator_sha256": [],
            "rules": life.RULES,
            "distance_units": life.UNITS,
            "value_perspective": life.PERSPECTIVE,
            "remaining": [],
        }
        metadata = mock.Mock()
        metadata.read.return_value = numerical
        self.assertIs(life.numerical(metadata, experiment, build), numerical)
        for key, value in (
            ("input_sha256", ["d" * 64, "c" * 64]),
            ("input_sha256", "c" * 64),
            ("remaining", None),
            ("artifact_sha256", "f" * 64),
            ("distance_units", "integer-step"),
        ):
            metadata.read.return_value = dict(numerical, **{key: value})
            with self.assertRaises((ValueError, AssertionError)):
                life.numerical(metadata, experiment, build)

    def test_child_raw_intent_identity_parent_and_argv_no_nested_lock(self):
        operation = self.root / "operation"
        operation.mkdir()
        (operation / "INCOMPLETE").touch()
        path = self.root / "intent.json"
        intent = {
            "schema": life.PREFIX + "lifecycle-intent.v1",
            "kind": "run",
            "output": str(operation),
            "argv": ["python", "SYNTHETIC"],
            "admission": {},
        }
        intent["intent_sha256"] = s.digest({k: v for k, v in intent.items() if k != "admission"})
        raw = json.dumps(intent).encode()
        path.write_bytes(raw)
        path.chmod(0o644)
        sha = hashlib.sha256(raw).hexdigest()
        environment = {"QUORIDOR_LIFECYCLE_INTENT": sha, "QUORIDOR_LIFECYCLE_PARENT_PID": "12345"}
        metadata = life.Metadata()
        self.assertNotEqual(sha, intent["intent_sha256"])
        actual, descriptor = life.child_context(path, metadata, environment, 12345, intent["argv"])
        self.assertEqual(actual, intent)
        self.assertEqual(descriptor["sha256"], sha)
        for env, pid, argv in (
            (
                dict(environment, QUORIDOR_LIFECYCLE_INTENT=intent["intent_sha256"]),
                12345,
                intent["argv"],
            ),
            (environment, 12346, intent["argv"]),
            (environment, 12345, ["wrong"]),
        ):
            with self.assertRaises((ValueError, AssertionError)):
                life.child_context(path, life.Metadata(), env, pid, argv)
        self.assertFalse(hasattr(stream355, "fcntl"))
        self.assertFalse(hasattr(life, "fcntl"))

    def test_later_matched_failure_keeps_earlier_returned_row_and_primary(self):
        primary = ValueError("second matched file incomplete")
        inputs = mock.Mock()
        inputs.progress = {"available_sections": []}
        inputs.get.side_effect = [{"actual": "synthetic first"}, primary]
        index = {"batches": [], "matched_rows": ["first", "second"]}
        returned = {"family_id": 0, "status": "UNKNOWN", "available_value": 0.25}
        partial = {}
        with (
            mock.patch.object(s, "aggregate_games", return_value={"planned_games": 512}),
            mock.patch.object(observations355.p, "search_row", return_value=returned),
        ):
            with self.assertRaises(ValueError) as caught:
                observations355.aggregate_observations(index, inputs, partial, {}, {}, {})
        self.assertIs(caught.exception, primary)
        self.assertEqual(partial["matched_available_rows"], [returned])
        self.assertEqual(partial["games"]["planned_games"], 512)
        self.assertIs(primary.strength355_available_evidence, partial)

    def test_data_writer_cannot_finalize_or_replace_and_declared_limit_is_real(self):
        root = self.root / "data"
        intent = {
            "data_root": str(root),
            "data": [{"name": "summary", "path": str(root / "summary.json"), "limit_B": 16}],
        }
        stream355.write_data(intent, {"summary": b'{"SYNTHETIC":1}'})
        self.assertEqual({p.name for p in root.iterdir()}, {"summary.json"})
        with self.assertRaises(FileExistsError):
            stream355.write_data(intent, {"summary": b"{}"})
        intent["data"][0]["limit_B"] = 1
        with self.assertRaises((ValueError, AssertionError)):
            stream355.write_data(intent, {"summary": b"{}"})
        self.assertFalse((root / "manifest.json").exists())

    def test_clock_and_current_conditions_are_checked_without_game_outcomes(self):
        experiment = {"batch": 0, "models": [{"descriptor": ref(self.root / "model")}]}
        config = {
            "ruleset": "standard_2p_threefold",
            "inference": None,
            "inference_cpu_core": None,
            "arena": {
                "comparison": "evaluator_wall_time",
                "clock_policy": "strict_unknown",
                "return_reserve_ms": 5,
                "tt_entries": 4096,
            },
            "engines": [
                {
                    "time_ms": 100,
                    "depth": 64,
                    "max_nodes": 1000000,
                    "kind": "nnue",
                    "distance_a": 0,
                    "distance_b": 8,
                    "model": str(self.root / "model"),
                },
                {
                    "time_ms": 100,
                    "depth": 64,
                    "max_nodes": 1000000,
                    "kind": "distance",
                    "distance_a": 0,
                    "distance_b": 8,
                    "model": None,
                },
            ],
        }
        life.arena_clock(config)
        life.arena_conditions(config, experiment)
        for key, value in (
            ("time_ms", True),
            ("max_nodes", 999999),
            ("distance_b", 0),
            ("model", "/OTHER"),
        ):
            bad = copy.deepcopy(config)
            bad["engines"][0][key] = value
            with self.assertRaises((ValueError, AssertionError)):
                life.arena_clock(bad)
                life.arena_conditions(bad, experiment)

    def test_analysis_zero_operation_slots_is_not_scientific_zero_denominator(self):
        file, build = ref(self.root / "experiment"), ref(self.root / "manifest.json")
        value = {
            "schema": life.PREFIX + "experiment.v1",
            "phase": "analysis",
            "build_manifest": build,
            "canonical_plan_sha256": s.PLAN_SHA,
            "planned_slots": 0,
            "batch": None,
            "rules": life.RULES,
            "distance_units": life.UNITS,
            "value_perspective": life.PERSPECTIVE,
            "config": ref(self.root / "config"),
            "schedule": ref(self.root / "schedule"),
            "inputs": [],
            "models": [],
            "numerical_qualification": ref(self.root / "numeric"),
            "dynamic_libraries": [],
        }
        inputs = mock.Mock()
        inputs.refs = {
            "experiment": {
                "path": file["path"],
                "SHA256": file["sha256"],
                "bytes": 1,
                "mode": "0644",
            }
        }
        inputs.get.return_value = value
        # Model identity checks are tested separately; this fixture isolates slots.
        with mock.patch.object(life, "models"):
            self.assertEqual(life.experiment(inputs, file, build, "analysis")["planned_slots"], 0)
            inputs.get.return_value = dict(value, planned_slots=512)
            with self.assertRaises((ValueError, AssertionError)):
                life.experiment(inputs, file, build, "analysis")
        self.assertEqual(len(s.MATCHED_IDS), 32)
        self.assertEqual(len(s.TREE_IDS), 8)

    def test_fixed_model_order_and_required_numerical_descriptor(self):
        rows = []
        for i, (manifest, weights, evaluator) in enumerate(life.MODELS):
            model_ref = ref(self.root / f"model{i}", manifest)
            model_ref["mode"] = "0644" if i == 0 else "0600"
            rows.append(
                {
                    "descriptor": model_ref,
                    "weights": ref(self.root / f"weights{i}", weights),
                    "evaluator_sha256": evaluator,
                }
            )
        experiment = {"phase": "analysis", "models": rows}
        life.models(experiment)
        with self.assertRaises((ValueError, AssertionError)):
            life.models(dict(experiment, models=list(reversed(rows))))
        with self.assertRaises((ValueError, AssertionError)):
            life.descriptor(None)
        # Individual full-file hashes remain arrays, including exactly one model.
        arena = {"phase": "arena", "batch": 1, "models": [rows[1]]}
        life.models(arena)
        with self.assertRaises((ValueError, AssertionError)):
            life.models(dict(arena, models=[rows[0]]))

    def test_failure_publication_keeps_original_exception_and_secondary(self):
        primary, publication = (
            ValueError("originating input failure"),
            OSError("failure output refused"),
        )
        path = self.root / "experiment.json"
        experiment = ref(path)
        intent = {"experiment": experiment, "data": [{"name": "failure"}]}
        with (
            mock.patch.object(
                life, "child_context", return_value=(intent, ref(self.root / "intent"))
            ),
            mock.patch.object(life.Metadata, "read", side_effect=primary),
            mock.patch.object(stream355, "write_data", side_effect=publication) as write,
        ):
            with self.assertRaises(ValueError) as caught:
                stream355.child_entry(str(path), experiment["sha256"], str(self.root / "intent"))
        self.assertIs(caught.exception, primary)
        self.assertEqual(primary.strength355_secondary_errors, [publication])
        self.assertEqual(primary.strength355_available_evidence, {})
        record = json.loads(write.call_args.args[1]["failure"])
        self.assertFalse(record["authoritative"])
        self.assertIn("originating input failure", record["primary"])
