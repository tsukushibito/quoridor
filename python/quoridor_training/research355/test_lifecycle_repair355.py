"""Consumer integration with the maintained publisher and tiny synthetic records."""

from contextlib import nullcontext
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import lifecycle355 as life
import stream355 as stream

MAIN = Path("/workspaces/quoridor")
OWN = Path(__file__).resolve().parents[3]
EVIDENCE = OWN / ".artifacts/lifecycle-consumer-n3l7-v1"
spec = importlib.util.spec_from_file_location(
    "consumer_test_publisher", MAIN / "scripts/dev/research-lifecycle.py"
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class NoResources:
    def __init__(self, _spec):
        pass

    def check(self, *, extra_B=0):
        assert type(extra_B) is int and extra_B >= 0


class ConsumerPublisherIntegration(unittest.TestCase):
    def setUp(self):
        tmp = EVIDENCE / "TMP"
        tmp.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-consumer-", dir=tmp)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.serial = 0
        self.source = self.file("source.py", b"# SYNTHETIC source, never executed\n")
        manifest = self.file("Cargo.toml", b"[workspace]\n")
        lock = self.file("Cargo.lock", b"SYNTHETIC lock\n")
        runner = self.file("crates/quoridor-runner/Cargo.toml", b"# SYNTHETIC crate\n")
        self.compiled = {"opaque-historical-provenance": self.source}
        self.compiled["Cargo.lock"] = lock
        self.compiled["runner/Cargo.toml"] = runner
        self.compiled_hashes = {key: ref["sha256"] for key, ref in self.compiled.items()}
        self.source_info = {
            "workspace": str(self.root),
            "commit": "1" * 40,
            "patch": None,
            "untracked_inputs": [],
            "manifest": manifest,
            "lock": lock,
            "cargo_configs": [],
            "compiled_sources": self.compiled,
        }
        self.artifact = self.file("target/private/runner", b"SYNTHETIC artifact, never executed")
        # Saved adapter tests use synthetic compiler/Git facts; the actual owning
        # BUILD checks are covered by test_build_provenance.py, never claimed here.
        source_port = mock.patch.object(publisher, "source_check", return_value=None)
        source_port.start()
        self.addCleanup(source_port.stop)
        self.build_ref, self.build = self.operation("build")
        models = []
        fingerprints = []
        for index in range(2):
            descriptor = self.file(
                f"descriptor{index}.json", b"SYNTHETIC descriptor " + str(index).encode()
            )
            if index == 1:
                Path(descriptor["path"]).chmod(0o600)
                descriptor = publisher.bound(Path(descriptor["path"]))[0]
            weights = self.file(f"weights{index}", b"SYNTHETIC weights " + str(index).encode())
            evaluator = hashlib.sha256(f"synthetic-evaluator{index}".encode()).hexdigest()
            models.append(
                {"descriptor": descriptor, "weights": weights, "evaluator_sha256": evaluator}
            )
            fingerprints.append((descriptor["sha256"], weights["sha256"], evaluator))
        # Only fixture metadata fingerprints are substituted. No model or evaluator executes.
        model_scope = mock.patch.object(life, "MODELS", fingerprints)
        model_scope.start()
        self.addCleanup(model_scope.stop)
        self.models = models
        self.config = self.document("compare-config.json", {"SYNTHETIC": True})
        self.input = self.document("input.json", {"SYNTHETIC": "input"})
        self.schedule = self.document("schedule.json", [{"slot": i} for i in range(512)])

    def file(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o644)
        self.assertLessEqual(publisher.allocated(self.root), 1048576)
        return publisher.bound(path)[0]

    def document(self, name, value):
        return self.file(name, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())

    def experiment(self, phase="compare"):
        value = {
            "schema": publisher.EXPERIMENT_SCHEMA,
            "phase": phase,
            "build_manifest": self.build_ref,
            "canonical_plan_sha256": life.s.PLAN_SHA,
            "models": self.models if phase != "generation" else [],
            "planned_slots": 0,
            "batch": None,
            "rules": life.RULES,
            "distance_units": life.UNITS,
            "value_perspective": life.PERSPECTIVE,
            "config": self.config,
            "inputs": [self.input],
            "schedule": self.schedule,
            "dynamic_libraries": [],
            "numerical_qualification": None,
        }
        if phase != "generation":
            value["numerical_qualification"] = self.document(
                f"numerical-{self.serial}.json",
                {
                    "schema": life.PREFIX + "numerical-qualification.v1",
                    "status": "PASS",
                    "phase": phase,
                    "artifact_sha256": self.artifact["sha256"],
                    "config_sha256": self.config["sha256"],
                    "schedule_sha256": self.schedule["sha256"],
                    "input_sha256": [self.input["sha256"]],
                    "descriptor_sha256": [m["descriptor"]["sha256"] for m in self.models],
                    "weights_sha256": [m["weights"]["sha256"] for m in self.models],
                    "evaluator_sha256": [m["evaluator_sha256"] for m in self.models],
                    "rules": life.RULES,
                    "distance_units": life.UNITS,
                    "value_perspective": life.PERSPECTIVE,
                    "remaining": [],
                },
            )
        return self.document(f"experiment-{self.serial}.json", value), value

    def operation(
        self,
        kind,
        experiment=None,
        data=None,
        primary=None,
        owed=None,
        command_failed=False,
        secondary=None,
    ):
        self.serial += 1
        prefix = f"operation-{self.serial}"
        operation = self.root / prefix
        operation.mkdir()
        (operation / "INCOMPLETE").touch()
        intent = self.document(
            prefix + "-intent.json",
            {
                "schema": "quoridor.research.lifecycle-intent.v1",
                "kind": kind,
                "owner": str(self.root),
                "output": str(operation),
                "source": self.source_info,
                "tools": {},
                "env": {},
                "target": str(self.root / "target"),
                "private": self.artifact["path"],
                "TMP": str(self.root / "TMP"),
                "data_root": str(self.root / "synthetic-native-output"),
                "finalizers": [],
                "limits": {"owned_B": 1048576},
            },
        )
        runtime = self.root / f"job-{self.serial}"
        cfg = {
            "argv": [
                sys.executable,
                "-B",
                str(MAIN / "scripts/dev/research-lifecycle.py"),
                kind,
                "--intent",
                intent["path"],
                "--sha256",
                intent["sha256"],
            ]
        }
        config = self.document(f"job-{self.serial}/config.json", cfg)
        identity = {"pid": 999991, "start_ticks": "2", "boot_id": "SYNTHETIC"}
        origin = {
            "runtime": str(runtime),
            "job_id": f"SYNTHETIC-{self.serial}",
            "config": config,
            "config_sha256": publisher.sha(json.dumps(cfg, sort_keys=True).encode()),
            "supervisor": identity,
            "child": identity,
        }
        outcome = "failed" if primary or command_failed else "succeeded"
        self.document(
            f"job-{self.serial}/state.json",
            {
                "phase": "finished",
                "job_id": origin["job_id"],
                "config_sha256": origin["config_sha256"],
                "supervisor": identity,
                "child": identity,
                "outcome": outcome,
            },
        )
        job = self.document(
            f"job-{self.serial}/result.json",
            {
                "job_id": origin["job_id"],
                "outcome": outcome,
                "exit_code": 1 if outcome == "failed" else 0,
                "finished_at": "SYNTHETIC stopped",
                "direct_child_reaped": True,
                "cleanup_complete": True,
                "remaining": [],
                "cleanup_errors": [],
            },
        )
        checks = []
        roles = ("test", "lint", "build") if kind == "build" else ("run",)
        cargo_artifact = {
            "reason": "compiler-artifact",
            "target": {"name": "quoridor-runner", "kind": ["bin"]},
            "profile": {"test": False},
            "executable": self.artifact["path"],
            "fresh": False,
        }
        for role in roles:
            events = [cargo_artifact, {"reason": "build-finished", "success": True}]
            raw = b"\n".join(json.dumps(event).encode() for event in events) + b"\n"
            log = self.file(prefix + f"/{role}.full.log", raw)
            returned = {
                "status": "failed" if command_failed else "complete",
                "exit_code": 1 if command_failed else 0,
                "direct_child_reaped": True,
                "cleanup_complete": True,
                "remaining": [],
                "finalization_errors": [],
                "log_bytes_seen": len(raw),
                "signal_mask_restoration": "completed",
                "final_record_persist": "completed",
            }
            disk = self.document(
                prefix + f"/{role}.process.json",
                dict(returned, signal_mask_restoration="pending", final_record_persist="attempted"),
            )
            checks.append(
                {
                    "name": role,
                    "role": role,
                    "argv": ["SYNTHETIC no execution"],
                    "status": "FAILED" if command_failed else "PASS",
                    "guardian_return": returned,
                    "full_log": log,
                    "persisted_process_receipt": disk,
                    "capture_complete": True,
                    "primary": primary,
                    "secondary": [],
                }
            )
        candidate = {
            "schema": publisher.BUILD_SCHEMA if kind == "build" else publisher.COMPLETION_SCHEMA,
            "kind": kind,
            "status": "FAILED" if primary else "PENDING_FINALIZATION",
            "intent": intent,
            "originating_job": origin,
            "checks": checks,
            "primary": primary,
            "secondary": secondary or [],
            "cleanup_complete": True,
            "remaining": [],
            "process_cleanup_complete": True,
            "owed_finalizers": owed or [],
        }
        if kind == "build":
            # Synthetic metadata for the maintained finalizer's current adoption
            # contract. No prior software receipt or actual BUILD is asserted.
            source_adoption = self.document(
                prefix + "/source-adoption.json",
                {
                    "schema": "quoridor.research.source-adoption.v1",
                    "status": "ACCEPTED",
                    "source": self.source_info,
                    "prior_software": None,
                    "limitation": "SYNTHETIC finalizer fixture; no source qualification",
                },
            )
            candidate.update(
                artifact=self.artifact,
                source=self.source_info,
                source_adoption=source_adoption,
                compiled_sources=self.compiled_hashes,
                cargo_artifact=cargo_artifact,
                artifact_target="quoridor-runner",
                tools={},
                env={},
            )
        else:
            candidate.update(build_manifest=self.build_ref, experiment=experiment, data=data)
        self.document(prefix + "/candidate.json", candidate)
        completed = publisher.finalize(
            operation, job, guard=lambda _: None, lock=nullcontext, resource_factory=NoResources
        )
        # Only synthetic admission/resource ports are replaced; the maintained finalizer runs.
        self.assertFalse((operation / "INCOMPLETE").exists())
        self.assertLessEqual(publisher.allocated(self.root), 1048576)
        return publisher.bound(operation / "manifest.json")[0], completed

    def partial_data(self, display="display metadata"):
        output = self.document(
            f"partial-{self.serial}.json", {"available_rows": 1, "unknown_rows": 511}
        )
        return {
            "status": "PASS",
            "files": [output],
            "errors": [],
            "generation": {
                "schema": "quoridor.research.generation-evidence.v1",
                "limitation": display,
                "external_finalization": display,
            },
        }

    def test_publisher_finalization_is_completion_authority_and_text_is_display_only(self):
        for text in ("PENDING", "arbitrary translated display text"):
            experiment, value = self.experiment("generation")
            manifest, _ = self.operation("run", experiment, self.partial_data(text))
            metadata = life.Metadata()
            result, actual = life.finalized_input(metadata, manifest, self.build_ref)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["data"]["generation"]["limitation"], text)
            self.assertEqual(actual, value)
            self.assertIsNone(life.numerical(metadata, actual, self.build))

    def test_failed_partial_and_independent_owed_facts_survive_without_receipt_reopening(self):
        experiment, _ = self.experiment()
        primary = {
            "type": "SYNTHETIC original",
            "message": "first failure",
            "notes": ["cause: original"],
        }
        inherited = [{"stage": "original secondary", "message": "retained"}]
        data = self.partial_data()
        data.update(status="FAILED", errors=[{"stage": "partial", "message": "unknown rest"}])
        a = self.document(
            "owed-failed.json",
            {
                "schema": "quoridor.research.data-finalizer.v1",
                "status": "FAILED",
                "remaining": [],
                "files": [],
                "intent_sha256": "a" * 64,
            },
        )
        owed = [
            {"kind": "data", "path": a["path"], "limit_B": 4096},
            {"kind": "data", "path": str(self.root / "absent-receipt.json"), "limit_B": 4096},
        ]
        manifest, published = self.operation(
            "run", experiment, data, primary, owed, secondary=inherited
        )
        metadata = life.Metadata()
        actual, value = life.finalized_input(metadata, manifest, self.build_ref)
        self.assertEqual(actual, published)
        self.assertEqual(actual["status"], "FAILED")
        self.assertEqual(actual["primary"], primary)
        self.assertEqual(actual["secondary"][0], inherited[0])
        self.assertEqual(len([e for e in actual["secondary"] if e["stage"] == "owed_finalizer"]), 2)
        self.assertEqual(actual["data"]["files"], data["files"])
        self.assertEqual(actual["owed_finalizers"][0]["actual_receipt"], a)
        self.assertNotIn("actual_receipt", actual["owed_finalizers"][1])
        self.assertNotIn(a["path"], metadata.seen)
        life.numerical(metadata, value, self.build)
        with self.assertRaises(ValueError):
            life.authoritative(metadata, manifest, "build-manifest", "build")

    def test_wrong_experiment_input_and_missing_critical_binding_refuse(self):
        experiment, _ = self.experiment()
        data = self.partial_data()
        manifest, _ = self.operation("run", experiment, data)
        metadata = life.Metadata()
        with self.assertRaises(ValueError):
            life.finalized_input(metadata, manifest, dict(self.build_ref, sha256="f" * 64))
        _, value = life.finalized_input(metadata, manifest, self.build_ref)
        wrong = copy.deepcopy(value)
        wrong["inputs"][0]["sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            life.numerical(metadata, wrong, self.build)
        wrong = dict(value, config=dict(value["config"], sha256="f" * 64))
        with self.assertRaises(ValueError):
            life.numerical(metadata, wrong, self.build)
        wrong_experiment = dict(value, canonical_plan_sha256="f" * 64)
        wrong_ref = self.document("wrong-experiment.json", wrong_experiment)
        wrong_completion, _ = self.operation("run", wrong_ref, data)
        with self.assertRaises(ValueError):
            life.finalized_input(life.Metadata(), wrong_completion, self.build_ref)
        build = life.authoritative(metadata, self.build_ref, "build-manifest", "build")
        with self.assertRaises((ValueError, KeyError)):
            life.descriptor(dict(build["artifact"], bytes=None))

    def test_non_authoritative_candidate_incomplete_and_hash_drift_refuse(self):
        metadata = life.Metadata()
        candidate = publisher.bound(Path(self.build_ref["path"]).with_name("candidate.json"))[0]
        metadata.add(candidate)
        with self.assertRaises(ValueError):
            life.authoritative(metadata, candidate, "build-manifest", "build")
        marker = Path(self.build_ref["path"]).with_name("INCOMPLETE")
        marker.touch()
        metadata.add(self.build_ref)
        with self.assertRaises(ValueError):
            life.authoritative(metadata, self.build_ref, "build-manifest", "build")
        marker.unlink()
        wrong = dict(self.build_ref, sha256="f" * 64)
        with self.assertRaises(ValueError):
            life.Metadata().read(wrong)

    def test_finalized_scientific_file_integrity_is_checked_at_consumption(self):
        experiment, _ = self.experiment()
        raw = b'{"game":0,"status":"unknown"}\n'
        journal = self.file("journal.jsonl", raw)
        data = {"status": "PASS", "files": [journal], "errors": []}
        manifest, _ = self.operation("run", experiment, data)
        value, _ = life.finalized_input(life.Metadata(), manifest, self.build_ref)
        file = value["data"]["files"][0]
        index = {
            "schema": "quoridor.strength355.stopped-input-index.v1",
            "plan_SHA256": life.s.PLAN_SHA,
            "provenance": "ACTUAL_GENERATED",
            "files": {
                "journal": {
                    "path": file["path"],
                    "SHA256": file["sha256"],
                    "bytes": file["bytes"],
                    "mode": file["mode"],
                }
            },
        }
        inputs = stream.Inputs(index)
        self.assertEqual(list(inputs.lines("journal"))[0]["status"], "unknown")
        Path(journal["path"]).write_bytes(raw.replace(b"unknown", b"goal   "))
        with self.assertRaises(ValueError):
            list(stream.Inputs(index).lines("journal"))

    def test_later_pairing_failure_keeps_failed_producer_progress_and_unknowns(self):
        experiment, _ = self.experiment()
        data = self.partial_data()
        manifest, _ = self.operation(
            "run", experiment, data, primary={"type": "SYNTHETIC", "message": "partial retained"}
        )
        file = data["files"][0]
        index = {"build_manifest": self.build_ref, "producer_completions": [manifest]}
        inputs = mock.Mock(
            refs={
                "partial": {
                    "path": file["path"],
                    "SHA256": file["sha256"],
                    "bytes": file["bytes"],
                    "mode": file["mode"],
                }
            }
        )
        analysis = {"inputs": [file]}
        metadata = life.Metadata()
        with self.assertRaises(KeyError):
            stream.scientific_inputs(index, inputs, metadata, self.build_ref, self.build, analysis)
        provenance = metadata.progress["operation_provenance"]
        self.assertEqual(provenance[0]["status"], "FAILED")
        self.assertEqual(provenance[0]["primary"]["message"], "partial retained")
        self.assertEqual(provenance[0]["data_errors"], data["errors"])
        self.assertEqual(provenance[0]["generation"], data["generation"])

    def test_failed_provenance_precedes_invalid_numerical_pairing(self):
        experiment, value = self.experiment()
        numerical = json.loads(Path(value["numerical_qualification"]["path"]).read_bytes())
        numerical["input_sha256"] = ["f" * 64]
        value["numerical_qualification"] = self.document("wrong-numerical.json", numerical)
        experiment = self.document("invalid-pair-experiment.json", value)
        data = self.partial_data()
        primary = {"type": "SYNTHETIC", "message": "origin before pairing"}
        manifest, _ = self.operation("run", experiment, data, primary=primary)
        file = data["files"][0]
        inputs = mock.Mock(
            refs={
                "partial": {
                    "path": file["path"],
                    "SHA256": file["sha256"],
                    "bytes": file["bytes"],
                    "mode": file["mode"],
                }
            }
        )
        index = {"build_manifest": self.build_ref, "producer_completions": [manifest]}
        metadata = life.Metadata()
        with self.assertRaisesRegex(ValueError, "actual numerical coupling input_sha256"):
            stream.scientific_inputs(
                index, inputs, metadata, self.build_ref, self.build, {"inputs": [file]}
            )
        self.assertEqual(metadata.progress["operation_provenance"][0]["primary"], primary)
        self.assertEqual(metadata.progress["operation_provenance"][0]["status"], "FAILED")

    def test_actual_publisher_full512_obligation_refuses_32_only_census(self):
        for slots in (512, 32):
            experiment, _ = self.experiment()
            next_intent = self.root / f"operation-{self.serial + 1}-intent.json"
            intent_raw = (
                json.dumps(
                    {
                        "schema": "quoridor.research.lifecycle-intent.v1",
                        "kind": "run",
                        "owner": str(self.root),
                        "output": str(self.root / f"operation-{self.serial + 1}"),
                    },
                    indent=2,
                    allow_nan=False,
                )
                + "\n"
            ).encode()
            receipt = self.document(
                f"census-{slots}.json",
                {
                    "schema": "quoridor.research.data-finalizer.v1",
                    "status": "PASS",
                    "remaining": [],
                    "intent_sha256": hashlib.sha256(intent_raw).hexdigest(),
                    "files": [],
                    "planned_slots": slots,
                    "complete_planned_census": True,
                },
            )
            self.assertEqual(next_intent.name, f"operation-{self.serial + 1}-intent.json")
            manifest, completed = self.operation(
                "run",
                experiment,
                self.partial_data(),
                owed=[{"kind": "journal", "path": receipt["path"], "limit_B": 4096}],
            )
            actual, _ = life.finalized_input(life.Metadata(), manifest, self.build_ref)
            self.assertEqual(actual["status"], "PASS" if slots == 512 else "FAILED")
            self.assertEqual(actual["status"], completed["status"])
            if slots == 32:
                self.assertTrue(any(e["stage"] == "owed_finalizer" for e in actual["secondary"]))

    def test_stopped_generation_publisher_through_consumer_keeps_failed_origin(self):
        producer_path = Path(
            "/workspaces/quoridor/tools/research-session/stopped_generation_publisher_v2.py"
        )
        self.assertEqual(
            hashlib.sha256(producer_path.read_bytes()).hexdigest(),
            "e00c27989006aa2dc1da5d6d09f2af2b292863248d8bb6edfd4a2cc81d309a17",
        )
        spec = importlib.util.spec_from_file_location("combined_stopped_publisher", producer_path)
        actual = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(actual)
        # The stopped owner requires its exact arena34/research35 key domains.
        # Populate only synthetic metadata hashes, never real source/model data.
        self.compiled = {key: self.source for key in actual.RESEARCH_SOURCE_KEYS}
        self.compiled_hashes = {key: ref["sha256"] for key, ref in self.compiled.items()}
        self.source_info["compiled_sources"] = self.compiled
        self.build_ref, self.build = self.operation("build")
        # Canonical plan is small source metadata only; no actual book/model/artifact read.
        plan = actual.bound(
            "/workspaces/quoridor/research-data/ai-sigma/value-search-strength355/plan-v1.json",
            32768,
        )[0]
        self.assertEqual(plan["sha256"], life.s.PLAN_SHA)
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
        old = self.document("synthetic-OPEN8.json", prefixes)
        schedule = []
        for group in range(8):
            for order in range(2):
                for family in range(group * 16, group * 16 + 16):
                    for color in range(2):
                        schedule.append(
                            {
                                "slot": len(schedule),
                                "batch": 2 * group + order,
                                "matchup": (group + order) % 2,
                                "family_id": family,
                                "candidate_color": (family + group + color) % 2,
                                "local_game": 2 * (family % 16) + color,
                            }
                        )
        frozen_schedule = self.document("synthetic-frozen-schedule.json", schedule)
        data_root = self.root / "synthetic-generation"
        request = {
            "plan": {k: plan[k] for k in ("path", "sha256")},
            "old_prefixes": {k: old[k] for k in ("path", "sha256")},
            "output": str(data_root),
        }
        experiment_ref, experiment = self.experiment("generation")
        experiment.update(
            config=self.document("synthetic-generation-request.json", request),
            inputs=[plan, old],
            schedule=frozen_schedule,
            argv=[
                self.artifact["path"],
                "strength-book",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        )
        experiment_ref = self.document("synthetic-generation-experiment.json", experiment)
        native = {
            k: v for k, v in self.compiled_hashes.items() if k != "runner/sigma_qualification.rs"
        }
        start = {
            "compiled_sources": native,
            "request": request,
            "planned_families": 128,
            "attempt_upper": 1024,
            "transition_upper": 16384,
            "models_loaded": 0,
            "search_calls": 0,
            "games_started": 0,
        }
        book = {
            "schema": "quoridor.value-search-strength.book.v1",
            "complete": True,
            "families": [{"family_id": i} for i in range(128)],
            "compiled_sources": native,
            "plan_sha256": life.s.PLAN_SHA,
            "rules": life.RULES,
            "old_open8_sha256": old["sha256"],
            "old_open8_prefixes": prefixes,
            "attempted": 128,
            "attempts": [{} for _ in range(128)],
            "transitions": 0,
            "limitation": "translated display text; no legal-history qualification",
        }
        start_ref = self.document("synthetic-generation/generation-start.json", start)
        book_ref = self.document("synthetic-generation/book.json", book)
        schedule_ref = self.file(
            "synthetic-generation/schedule.json",
            json.dumps(schedule, separators=(",", ":")).encode(),
        )
        result = {
            "schema": book["schema"],
            "complete": True,
            "families": 128,
            "attempted": 128,
            "transitions": 0,
            "models_loaded": 0,
            "search_calls": 0,
            "games_started": 0,
            "book_sha256": book_ref["sha256"],
            "schedule_sha256": schedule_ref["sha256"],
            "external_finalization": "arbitrary display metadata, never admission",
        }
        result_ref = self.document("synthetic-generation/generation-result.json", result)
        command_argv = [
            a.replace("@EXPERIMENT@", experiment_ref["path"]).replace(
                "@EXPERIMENT_SHA256@", experiment_ref["sha256"]
            )
            for a in experiment["argv"]
        ]
        generation_spec = {
            "owner": str(self.root),
            "kind": "run",
            "experiment": experiment_ref,
            "artifact": self.artifact,
            "data_root": str(data_root),
            "argv": command_argv,
            "limits": {"log_B": 65536},
            "data": [
                {"name": n, "path": str(data_root / f), "limit_B": 65536}
                for n, f in actual.GENERATION_FILES.items()
            ],
        }
        data = actual.collect_data(generation_spec, experiment)
        self.assertEqual(data["status"], "PASS", data["errors"])  # Metadata correspondence only.
        data["status"] = "FAILED"
        data["errors"] = [
            {"stage": "generation_metadata", "message": "original arena34/research35 mismatch"}
        ]
        primary = {
            "type": "Refused",
            "message": "original source-domain mismatch",
            "notes": ["original cause"],
        }
        inherited = [{"stage": "origin secondary", "message": "preserve object fields"}]
        original_document = self.document

        def shaped_document(name, value):
            if name.endswith("-intent.json"):
                value = {**value, **generation_spec}
            if name.endswith("/candidate.json"):
                value["checks"][0]["argv"] = command_argv
            return original_document(name, value)

        with (
            mock.patch.object(self, "document", side_effect=shaped_document),
            mock.patch.dict(globals(), publisher=actual),
        ):
            completion_ref, completion = self.operation(
                "run", experiment_ref, data, primary=primary, secondary=inherited
            )
        raw_manifest = Path(completion_ref["path"]).read_bytes()
        original_files = {
            r["path"]: Path(r["path"]).read_bytes()
            for r in (start_ref, book_ref, schedule_ref, result_ref)
        }
        with mock.patch.object(actual, "read_ref", wraps=actual.read_ref) as reads:
            available = actual.generation_input_data(completion_ref)
        self.assertNotIn(self.artifact["path"], [c.args[0]["path"] for c in reads.call_args_list])
        self.assertEqual(available["status"], "PASS")
        self.assertEqual(available["origin_status"], "FAILED")
        self.assertEqual(available["origin_primary"], primary)
        self.assertEqual(available["origin_secondary"], completion["secondary"])
        self.assertIsNone(available["numerical_qualification"])
        metadata = life.Metadata()
        accepted, actual_experiment = life.finalized_input(metadata, completion_ref, self.build_ref)
        self.assertEqual(accepted["status"], "FAILED")
        self.assertEqual(accepted["data"]["errors"], data["errors"])
        self.assertEqual(accepted["secondary"][0], inherited[0])
        self.assertIsNone(life.numerical(metadata, actual_experiment, self.build))
        evidence = available["generation"]
        self.assertEqual(evidence["book_sha256"], book_ref["sha256"])
        self.assertEqual(evidence["schedule_sha256"], schedule_ref["sha256"])
        self.assertNotEqual(evidence["book_sha256"], evidence["book_semantic_sha256"])
        self.assertNotEqual(evidence["schedule_sha256"], evidence["schedule_semantic_sha256"])
        self.assertEqual(evidence["schedule_semantic_sha256"], actual.canonical_sha(schedule))
        self.assertNotEqual(frozen_schedule["sha256"], schedule_ref["sha256"])
        for r in (start_ref, book_ref, schedule_ref, result_ref):
            self.assertEqual(Path(r["path"]).read_bytes(), original_files[r["path"]])
        self.assertEqual(Path(completion_ref["path"]).read_bytes(), raw_manifest)
        with self.assertRaises(ValueError):
            life.authoritative(metadata, completion_ref, "build-manifest", "build")

    def test_current_caller_intent_membership_and_originating_errors_remain(self):
        # Exact stopped interface shape; this is synthetic source metadata, not RUN admission.
        interface_path = Path(
            "/workspaces/quoridor/tools/research-session/fixtures/stopped-caller-interface-v2.json"
        )
        raw_interface = interface_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw_interface).hexdigest(),
            "55cd66f620e055c2898187a03e2c24a1ae38245e47928b2af8f3fc21419a5b10",
        )
        interface = json.loads(raw_interface)
        relative = interface["required_paths"] + interface["analysis_additional_paths"]
        refs = [
            self.file("current-callers/" + name, b"SYNTHETIC current caller, never executed")
            for name in relative
        ]
        paths = [r["path"] for r in refs[4:]]
        self.assertEqual(len(paths), 6)
        operation = self.root / "current-caller-operation"
        operation.mkdir()
        (operation / "INCOMPLETE").touch()
        argv = [sys.executable, "-B", paths[0], "--experiment", "SYNTHETIC"]
        current = {
            "schema": life.PREFIX + "lifecycle-intent.v1",
            "kind": "run",
            "output": str(operation),
            "argv": argv,
            "caller_sources": refs,
            "admission": {},
        }
        current["intent_sha256"] = life.s.digest(
            {k: v for k, v in current.items() if k != "admission"}
        )
        intent_ref = self.document("current-caller-intent.json", current)
        environment = {
            "QUORIDOR_LIFECYCLE_INTENT": intent_ref["sha256"],
            "QUORIDOR_LIFECYCLE_PARENT_PID": str(os.getppid()),
        }
        actual, raw_ref = life.child_context(
            Path(intent_ref["path"]), life.Metadata(), environment=environment, argv=argv
        )
        self.assertEqual(raw_ref["sha256"], intent_ref["sha256"])
        self.assertNotEqual(raw_ref["sha256"], current["intent_sha256"])
        life.analysis_source(actual, paths)
        # Build's historical Python membership/hash has no authority over current RUN callers.
        historical = copy.deepcopy(self.build)
        historical["source"]["files"] = []
        with self.assertRaises(KeyError):
            life.analysis_source(historical, paths)
        for bad in (
            dict(actual, caller_sources=refs[:-1]),
            dict(actual, caller_sources=refs + [refs[-1]]),
        ):
            with self.assertRaises(ValueError):
                life.analysis_source(bad, paths)
        with self.assertRaises(ValueError):
            life.analysis_source(actual, [str(self.root / "unbound-import.py")])
        bad = copy.deepcopy(current)
        bad["caller_sources"][4]["sha256"] = "f" * 64
        changed = self.document("changed-current-caller-intent.json", bad)
        with self.assertRaises(ValueError):
            life.child_context(
                Path(changed["path"]), life.Metadata(), environment=environment, argv=argv
            )
        primary, inherited, publication, cause = (
            OSError("originating"),
            ValueError("inherited"),
            OSError("publication"),
            RuntimeError("cause"),
        )
        primary.__cause__ = cause
        primary.strength355_secondary_errors = [inherited]
        experiment_ref, _ = self.experiment()
        intent = {
            "experiment": experiment_ref,
            "data_root": str(self.root / "failure"),
            "data": [
                {
                    "name": "failure",
                    "path": str(self.root / "failure/failure.json"),
                    "limit_B": 4096,
                }
            ],
        }
        with (
            mock.patch.object(life, "child_context", return_value=(intent, self.source)),
            mock.patch.object(
                life.Metadata, "read", return_value={"build_manifest": self.build_ref}
            ),
            mock.patch.object(life, "authoritative", side_effect=primary),
            mock.patch.object(stream, "write_data", side_effect=publication),
        ):
            with self.assertRaises(OSError) as caught:
                stream.child_entry(
                    experiment_ref["path"], experiment_ref["sha256"], str(self.root / "intent")
                )
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.__cause__, cause)
        self.assertEqual(primary.strength355_secondary_errors, [inherited, publication])
