"""Only C2/C3/C4 discriminators using owned small synthetic metadata."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import lifecycle355 as life
import stream355
from test_lifecycle355 import ref

HERE = Path(__file__).resolve().parent


class AdapterRepair(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="synthetic-C2C3C4-v11-", dir=HERE)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def source(self):
        compiled = {key: hashlib.sha256(key.encode()).hexdigest() for key in life.COMPILED_KEYS}
        files = {key: ref(self.root / key.replace("/", "_"), sha) for key, sha in compiled.items()}
        files["runner/Cargo.toml"]["path"] = str(self.root / "crates/quoridor-runner/Cargo.toml")
        files["Cargo.lock"]["path"] = str(self.root / "Cargo.lock")
        manifest = ref(self.root / "Cargo.toml", "f" * 64)
        return {
            "workspace": str(self.root),
            "manifest": manifest,
            "lock": files["Cargo.lock"],
            "compiled_sources": files,
            "files": [manifest, *files.values()],
            "cargo_configs": [{"path": str(self.root / ".cargo/config.toml"), "file": None}],
        }, compiled

    def test_producer_shaped_workspace_and_runner_manifests_are_distinct(self):
        source, compiled = self.source()
        self.assertNotEqual(source["manifest"], source["compiled_sources"]["runner/Cargo.toml"])
        life.source_projection(source, compiled)
        self.assertEqual(source["manifest"]["path"], str(self.root / "Cargo.toml"))
        self.assertEqual(source["lock"]["path"], str(self.root / "Cargo.lock"))

    def test_manifest_membership_path_and_lock_drift_refuse(self):
        source, compiled = self.source()
        for change in (
            "equated_manifests",
            "workspace_not_member",
            "crate_wrong_path",
            "lock_wrong_path",
        ):
            bad = copy.deepcopy(source)
            if change == "equated_manifests":
                bad["manifest"] = bad["compiled_sources"]["runner/Cargo.toml"]
            elif change == "workspace_not_member":
                bad["files"] = [r for r in bad["files"] if r["path"] != bad["manifest"]["path"]]
            elif change == "crate_wrong_path":
                bad["compiled_sources"]["runner/Cargo.toml"]["path"] = str(self.root / "Cargo.toml")
            else:
                bad["lock"]["path"] = str(self.root / "other/Cargo.lock")
            with self.subTest(change=change), self.assertRaises(ValueError):
                life.source_projection(bad, compiled)

    def job(self, raw, config):
        path = self.root / "job-config.json"
        path.write_bytes(raw)
        path.chmod(0o644)
        file = {
            "path": str(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mode": "0644",
        }
        identity = {"pid": 123, "start_ticks": "456", "boot_id": "SYNTHETIC"}
        return {
            "status": "FAILED",
            "process_cleanup_complete": False,
            "outer_job_state": ref(self.root / "state"),
            "originating_job": {
                "runtime": str(self.root),
                "job_id": "SYNTHETIC",
                "config": file,
                "config_sha256": hashlib.sha256(
                    json.dumps(config, sort_keys=True).encode()
                ).hexdigest(),
                "supervisor": identity,
                "child": identity,
            },
            "checks": [
                {
                    "name": "synthetic failed command",
                    "role": "version",
                    "argv": ["SYNTHETIC"],
                    "status": "FAILED",
                    "guardian_return": None,
                    "full_log": None,
                    "persisted_process_receipt": None,
                    "capture_complete": False,
                    "primary": {"message": "unreturned"},
                    "secondary": [],
                }
            ],
        }

    def test_actual_bound_raw_config_and_default_normalization_domains(self):
        config = {"z": ["SYNTHETIC", 1], "a": "日本語"}
        fingerprints = []
        raw_hashes = []
        for raw in (
            (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode(),
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode(),
        ):
            job = self.job(raw, config)
            fingerprints.append(job["originating_job"]["config_sha256"])
            raw_hashes.append(job["originating_job"]["config"]["sha256"])
            self.assertNotEqual(fingerprints[-1], raw_hashes[-1])
            metadata = life.Metadata()
            life.originating_build(job, metadata)
            self.assertEqual(
                metadata.progress["files_returned"], [str(self.root / "job-config.json")]
            )
            self.assertIsNone(job["checks"][0]["guardian_return"])
        self.assertEqual(fingerprints[0], fingerprints[1])
        self.assertNotEqual(raw_hashes[0], raw_hashes[1])

    def test_wrong_canonical_digest_raw_digest_and_actual_file_drift_refuse(self):
        config = {"b": "SYNTHETIC", "a": 1}
        raw = (json.dumps(config, indent=2) + "\n").encode()
        job = self.job(raw, config)
        wrongs = (
            job["originating_job"]["config"]["sha256"],
            hashlib.sha256(
                json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        )
        for sha in wrongs:
            bad = copy.deepcopy(job)
            bad["originating_job"]["config_sha256"] = sha
            with self.assertRaises(ValueError):
                life.originating_build(bad, life.Metadata())
        path = self.root / "job-config.json"
        path.write_bytes(raw.replace(b"SYNTHETIC", b"CHANGED__"))
        with self.assertRaises(ValueError):
            life.originating_build(job, life.Metadata())

    def owed_failure(self):
        first, second = (
            OSError("first actual missing receipt"),
            OSError("second actual missing receipt"),
        )
        cause = RuntimeError("originating cause retained")
        first.__cause__ = cause
        receipts = [ref(self.root / ("owed-" + str(i))) for i in range(3)]
        manifest = {
            "status": "PASS",
            "intent": ref(self.root / "intent"),
            "owed_finalizers": [
                {"kind": "data", "path": r["path"], "limit_B": 4096, "actual_receipt": r}
                for r in receipts
            ],
        }
        returned = {
            "schema": life.PREFIX + "data-finalizer.v1",
            "status": "PASS",
            "remaining": [],
            "intent_sha256": "a" * 64,
            "files": [],
        }
        metadata = mock.Mock()
        metadata.read.side_effect = [first, second, returned]

        def actual_owed(*args, **kwargs):
            return life.owed_facts(metadata, manifest)

        return first, second, cause, metadata, actual_owed

    def invoke_failure(self, owed, output):
        experiment_ref = ref(self.root / "experiment")
        root = self.root / "data"
        intent = {
            "experiment": experiment_ref,
            "data_root": str(root),
            "data": [{"name": "failure", "path": str(root / "failure.json"), "limit_B": 16384}],
        }
        patches = [
            mock.patch.object(
                life, "child_context", return_value=(intent, ref(self.root / "intent"))
            ),
            mock.patch.object(
                life.Metadata,
                "read",
                return_value={"build_manifest": ref(self.root / "manifest.json")},
            ),
            mock.patch.object(life, "authoritative", side_effect=owed),
        ]
        with patches[0], patches[1], patches[2], output:
            try:
                stream355.child_entry(
                    experiment_ref["path"], experiment_ref["sha256"], str(self.root / "intent")
                )
            except OSError as actual:
                return actual, root
        self.fail("originating owed failure was incorrectly accepted")

    def test_actual_multiple_owed_failures_survive_outer_handler_and_report(self):
        first, second, cause, metadata, owed = self.owed_failure()
        actual, root = self.invoke_failure(
            owed, mock.patch.object(stream355, "write_data", wraps=stream355.write_data)
        )
        self.assertIs(actual, first)
        self.assertIs(actual.__cause__, cause)
        self.assertEqual(actual.strength355_secondary_errors, [second])
        self.assertEqual(metadata.read.call_count, 3)
        facts = actual.strength355_owed_available
        self.assertIs(actual.strength355_available_evidence["owed_finalizer_available"], facts)
        self.assertEqual(len(facts), 3)
        self.assertTrue(facts[2]["validated_PASS"])
        record = json.loads((root / "failure.json").read_text())
        self.assertFalse(record["authoritative"])
        self.assertEqual(record["secondary"][0]["message"], str(second))
        self.assertIn("originating cause retained", record["primary_cause"])
        self.assertEqual(record["available"]["owed_finalizer_available"], facts)
        self.assertFalse((root / "manifest.json").exists())

    def test_outer_publication_failure_appends_after_inherited_error_objects(self):
        first, second, cause, metadata, owed = self.owed_failure()
        publication = OSError("outer publication refused")
        actual, root = self.invoke_failure(
            owed, mock.patch.object(stream355, "write_data", side_effect=publication)
        )
        self.assertIs(actual, first)
        self.assertIs(actual.__cause__, cause)
        self.assertEqual(actual.strength355_secondary_errors, [second, publication])
        self.assertEqual(metadata.read.call_count, 3)
        self.assertEqual(len(actual.strength355_available_evidence["owed_finalizer_available"]), 3)
        self.assertIs(
            actual.strength355_owed_available[0]["obligation"]["actual_receipt"],
            actual.strength355_available_evidence["owed_finalizer_available"][0]["obligation"][
                "actual_receipt"
            ],
        )
        self.assertFalse(root.exists())
        self.assertTrue(any("outer publication refused" in note for note in actual.__notes__))
