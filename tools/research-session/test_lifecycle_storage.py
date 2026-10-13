"""Whole storage and streamed identity checks; synthetic files only, no native/model."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import quoridor_training

ROOT = Path(os.environ.get("RESEARCH_TEST_ROOT", Path(__file__).resolve().parents[2]))
SOURCE = Path(
    os.environ.get(
        "RESEARCH_LIFECYCLE_SOURCE", ROOT / "scripts/dev/research-lifecycle.py"
    )
)
if os.environ.get("RESEARCH_CYCLE_SOURCE"):
    quoridor_training.__path__.insert(
        0, str(Path(os.environ["RESEARCH_CYCLE_SOURCE"]).parent)
    )
module = importlib.util.spec_from_file_location("whole_storage_lifecycle", SOURCE)
lc = importlib.util.module_from_spec(module)
module.loader.exec_module(lc)


class WholeStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("target", "private", "TMP", "operation", "prior-controls"):
            (self.root / name).mkdir()
        self.source = self.root / "target/FAKE-NOT-ELF"
        self.source.write_bytes(b"synthetic fixture" * 4096)
        self.source.chmod(0o755)
        self.destination = self.root / "private/candidate"
        self.spec = {
            "kind": "build",
            "owner": str(self.root),
            "target": str(self.root / "target"),
            "private": str(self.destination),
            "TMP": str(self.root / "TMP"),
            "output": str(self.root / "operation"),
            "owned_outputs": [
                str(self.root / "prior-controls"),
                str(self.root / "operation/nested"),
            ],
            "finalizers": [{"path": str(self.root / "operation/finalizer.json")}],
            "limits": {"owned_B": None, "free_B": None},
            "support": {"sha256": "0" * 64},
        }
        handover = self.root / "handover.json"
        handover.write_text(
            json.dumps({"fresh_private_root": str(self.destination.parent)})
        )
        self.spec["target_handover"] = lc.bound(handover)[0]

    def resources(self):
        value = object.__new__(lc.Limits)
        value.spec = self.spec
        value.charged_paths = lc.charged_roots(self.spec)
        return value

    def usage(self):
        seen = set()
        return sum(lc.allocated(p, seen=seen) for p in lc.charged_roots(self.spec))

    def test_unbudgeted_guards_do_not_scan_and_keep_pause_memory(self):
        # Real Limits construction needs no storage/support forecast fields.
        for omitted in (True, False):
            cfg = {
                "family_B": 512 * 1024**2,
                "host_reserve_B": 4 * 1024**3,
                "controller_B": 64 * 1024**2,
                "log_B": 1024**2,
            }
            if not omitted:
                cfg.update(owned_B=None, free_B=None)
            support = self.root / "support.json"
            support.write_text("{}")
            admission = self.root / "admission.json"
            admission.write_text(
                json.dumps(
                    {
                        "schema": "quoridor.research.phase-admission.v1",
                        "owner": str(self.root),
                        "limits": cfg,
                        "spec_sha256": "1" * 64,
                        "support_sha256": lc.bound(support)[0]["sha256"],
                        "ready": True,
                    }
                )
            )
            spec = {
                **self.spec,
                "limits": cfg,
                "support": lc.bound(support)[0],
                "admission": lc.bound(admission)[0],
                "intent_sha256": "1" * 64,
            }
            with patch.object(lc.process, "available_memory", return_value=8 * 1024**3):
                constructed = lc.Limits(spec)
            self.assertIsNone(constructed.output_limit)
            with (
                patch.object(lc.process.CycleResources, "check", return_value=None),
                patch.object(
                    lc,
                    "allocated",
                    side_effect=AssertionError("unbudgeted Limits must not inventory"),
                ),
            ):
                constructed.check()
        resources = self.resources()
        with (
            patch.object(lc.process.CycleResources, "check", return_value=None),
            patch.object(
                lc,
                "allocated",
                side_effect=AssertionError("ordinary tick must not inventory"),
            ),
        ):
            resources.check()
        for missing in (True, False):
            cfg = {"host_ram_reserve": 1, "max_memory_bytes": 512 * 1024**2}
            if not missing:
                cfg["max_output_bytes"] = None
            with patch.object(lc.process, "available_memory", return_value=1024**3):
                value = lc.process.CycleResources(cfg, self.root, None)
            self.assertIsNone(value.output_limit)
            with (
                patch.object(lc.process, "available_memory", return_value=1024**3),
                patch.object(
                    lc.process,
                    "directory_bytes",
                    side_effect=AssertionError("no implicit storage scan"),
                ),
            ):
                value.check()
                value.pause_file = self.root / "pause"
                value.pause_file.touch()
                with self.assertRaisesRegex(lc.process.CycleStopped, "paused"):
                    value.check()
                value.pause_file.unlink()
                value.memory_limit = 1
                with self.assertRaisesRegex(lc.process.CycleStopped, "memory_limit"):
                    value.check()

    def test_declared_whole_union_retains_controls_deduplicates_and_refuses_copy_overlap(
        self,
    ):
        prior = self.root / "prior-controls/retained"
        prior.write_bytes(b"prior controls" * 1000)
        linked = self.destination.parent / "same-inode"
        os.link(self.source, linked)
        whole = self.usage()
        roots = lc.charged_roots(self.spec)
        self.assertIn(prior.parent, roots)
        self.assertNotIn(self.root / "operation/nested", roots)
        self.assertLess(whole, sum(lc.allocated(p) for p in roots))
        resources = self.resources()
        cycle_whole = lc.allocated(self.root)
        self.assertEqual(lc.process.directory_bytes(self.root), cycle_whole)
        with patch.object(lc.process, "available_memory", return_value=1024**3):
            cycle = lc.process.CycleResources(
                {
                    "host_ram_reserve": 1,
                    "max_memory_bytes": 512 * 1024**2,
                    "max_output_bytes": cycle_whole,
                },
                self.root,
                None,
            )
        with patch.object(lc.process, "available_memory", return_value=1024**3):
            cycle.check()  # Shared inode cannot cause a false whole-budget overflow.
        self.spec["limits"]["owned_B"] = whole
        actual_cycle_check = lc.process.CycleResources.check
        with patch.object(lc.process.CycleResources, "check", return_value=None):
            resources.check()
            with self.assertRaisesRegex(lc.Refused, "owned allocation limit"):
                lc.private_copy_check(self.spec, self.source, resources=resources)
            self.assertFalse(self.destination.exists())
            actual_copy = self.root / "operation/retained-copy"
            actual_copy.write_bytes(self.source.read_bytes())
            with self.assertRaisesRegex(lc.Refused, "owned allocation limit"):
                resources.check()
            with (
                patch.object(lc.process, "available_memory", return_value=1024**3),
                self.assertRaisesRegex(lc.process.CycleStopped, "output_limit"),
            ):
                actual_cycle_check(cycle)

    def test_streamed_artifact_over_32MiB_keeps_identity_and_exclusive_path(self):
        # Finite fake sparse file distinguishes a retired executable-size cutoff.
        with self.source.open("r+b") as f:
            f.truncate(32 * 1024**2 + 1)
        expected = lc.artifact_ref(self.source)
        self.assertEqual(expected["bytes"], 32 * 1024**2 + 1)
        resources = self.resources()
        with patch.object(lc.process.CycleResources, "check", return_value=None):
            lc.private_copy_check(self.spec, self.source, resources=resources)
            actual = lc.copy_artifact(
                self.source, self.destination, resources=resources
            )
        self.assertEqual({**actual, "path": str(self.source)}, expected)
        with self.assertRaises(FileExistsError):
            lc.copy_artifact(self.source, self.destination)
        self.assertEqual(lc.artifact_ref(self.destination), actual)

    def test_source_symlink_owner_and_original_artifact_identity_drift_refuse(self):
        link = self.root / "link"
        link.symlink_to(self.source)
        with self.assertRaises(lc.Refused):
            lc.artifact_ref(link)
        with self.assertRaisesRegex(lc.Refused, "write ownership"):
            lc.private_copy_check(self.spec, self.root.parent / "foreign")
        descriptors = len(list(Path("/proc/self/fd").iterdir()))
        with self.assertRaises(lc.Refused):
            lc.artifact_ref(self.source.parent)
        self.assertEqual(len(list(Path("/proc/self/fd").iterdir())), descriptors)
        with self.assertRaisesRegex(lc.Refused, "absolute copy destination"):
            lc.copy_artifact(self.source, "refused-relative-copy")
        artifact = lc.artifact_ref(self.source)
        manifest = {
            "schema": lc.BUILD_SCHEMA,
            "status": "PASS",
            "cleanup_complete": True,
            "remaining": [],
            "checks": [{"role": r} for r in ("test", "lint", "build")],
            "artifact": artifact,
            "tools": {},
            "source": {
                "workspace": str(self.root),
                "commit": "1" * 40,
                "patch": None,
                "untracked_inputs": [],
                "manifest": {"path": str(self.root / "Cargo.toml")},
                "lock": {"path": str(self.root / "Cargo.lock")},
                "cargo_configs": [],
            },
        }
        path = self.root / "build.json"
        path.write_text(json.dumps(manifest))
        reference = lc.bound(path)[0]
        self.assertEqual(lc.accepted_build(reference)["artifact"], artifact)
        self.source.chmod(0o644)
        with self.assertRaisesRegex(lc.Refused, "artifact identity drift"):
            lc.accepted_build(reference)
        self.source.chmod(0o755)
        data = self.source.read_bytes()
        self.source.write_bytes(b"X" + data[1:])
        with self.assertRaisesRegex(lc.Refused, "artifact identity drift"):
            lc.accepted_build(reference)

    def test_copy_cancel_and_io_error_keep_partial_file_and_source(self):
        original = lc.artifact_ref(self.source)

        class Cancel:
            def check(inner):
                if self.destination.exists() and self.destination.stat().st_size:
                    raise lc.process.CycleStopped("synthetic cancellation")

        with self.assertRaisesRegex(lc.process.CycleStopped, "cancellation"):
            lc.copy_artifact(self.source, self.destination, resources=Cancel())
        self.assertGreater(self.destination.stat().st_size, 0)
        self.assertEqual(lc.artifact_ref(self.source), original)
        other = self.destination.with_name("failed-sync")
        with (
            patch.object(lc.os, "fsync", side_effect=OSError("synthetic sync failure")),
            self.assertRaisesRegex(OSError, "sync failure"),
        ):
            lc.copy_artifact(self.source, other)
        self.assertTrue(other.exists())
        self.assertEqual(lc.artifact_ref(self.source), original)
