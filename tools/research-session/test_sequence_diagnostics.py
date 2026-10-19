"""New sequence diagnostics and empty-owned-TMP boundaries; synthetic RSS/authority only."""

import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get("RESEARCH_TEST_ROOT", Path(__file__).resolve().parents[2]))


def load(name, source):
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lc = load(
    "sequence_diagnostic_lifecycle",
    os.environ.get("RESEARCH_LIFECYCLE_SOURCE", ROOT / "scripts/dev/research-lifecycle.py"),
)
job = load(
    "sequence_diagnostic_job",
    os.environ.get("RESEARCH_JOB_SOURCE", ROOT / "scripts/dev/research-job.py"),
)


class SequenceDiagnosticTests(unittest.TestCase):
    def test_validated_role_threshold_notes_reach_actual_job_result(self):
        # RSS/identity/cmdline and host checks are explicit metadata ports.
        # The supervisor below actually spawns, terminates and reaps a stdlib child.
        root = os.getpid()
        infos = {
            pid: {
                "pid": pid,
                "parent": parent,
                "start_ticks": str(pid),
                "boot_id": "synthetic-boot",
                "rss": rss,
            }
            for pid, parent, rss in [
                (root, 0, 3),
                (root + 100000, root, 4),
                (root + 100001, root, 5),
                (root + 100002, root + 100001, 2),
            ]
        }
        original_open = Path.open

        def cmdline(path, *args, **kwargs):
            if str(path).startswith("/proc/") and path.name == "cmdline":
                pid = int(path.parent.name)
                return io.BytesIO(
                    b"/synthetic/native\0" if pid == root + 100001 else b"/synthetic/management\0"
                )
            return original_open(path, *args, **kwargs)

        errors = {}
        for role, limits in [
            ("aggregate", (13, 10, 10)),
            ("management", (14, 6, 7)),
            ("native", (14, 7, 6)),
            (None, (14, 7, 7)),
        ]:
            guard = object.__new__(lc.SequenceResources)
            guard.root = lc.process.identity(infos[root])
            guard.known = []
            guard.native_paths = {"/synthetic/native"}
            guard.memory_limit = limits[0]
            guard.management = SimpleNamespace(memory_limit=limits[1])
            guard.native = SimpleNamespace(memory_limit=limits[2])
            with (
                patch.object(lc.process, "process_info", side_effect=infos.get),
                patch.object(lc.process, "members", return_value=list(infos.values())),
                patch.object(lc.process.CycleResources, "check", return_value=None),
                patch.object(Path, "open", cmdline),
            ):
                if role is None:
                    guard.check()
                    continue
                with self.assertRaises(lc.process.CycleStopped) as caught:
                    guard.check()
            error = caught.exception
            errors[role] = error
            self.assertEqual(str(error), "cycle memory_limit")
            note = json.loads(error.__notes__[0])
            self.assertEqual(note["role"], role)
            self.assertEqual(note["rss_B"], 14 if role == "aggregate" else 7)
            self.assertGreater(note["rss_B"], note["limit_B"])
            self.assertEqual(note["members_omitted"], 0)
            self.assertEqual(
                {x["pid"] for x in note["members"]},
                set(infos)
                if role == "aggregate"
                else {root, root + 100000}
                if role == "management"
                else {root + 100001, root + 100002},
            )
        tmp = Path(os.environ.get("RESEARCH_TEST_TMP", ROOT / ".artifacts/sequence-test-TMP"))
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp) as name:
            directory = Path(name)
            config = {
                "issue": "synthetic-work",
                "goal_issue": "synthetic-goal",
                "thread_id": "synthetic-owner",
                "cwd": str(directory),
                "argv": [sys.executable, "-B", "-c", "import time;time.sleep(5)"],
                "resource_contract": str(directory / "synthetic-contract"),
                "end_at": None,
                "notify_until": None,
                "max_runtime_seconds": 3,
                "control_interval_seconds": 1,
                "notify_interval_seconds": 1,
                "request_timeout_seconds": 1,
                "log_max_bytes": 1024,
            }
            job.write(
                directory,
                "state.json",
                {
                    "phase": "queued",
                    "job_id": "synthetic-job",
                    "thread_id": "synthetic-owner",
                },
            )

            def check():
                if job.read(directory, "state.json")["phase"] == "running":
                    raise errors["native"]

            with patch.object(job, "authority", return_value={"thread_id": "synthetic-owner"}):
                result = job.execute(
                    directory,
                    config,
                    ROOT,
                    None,
                    resources=SimpleNamespace(check=check),
                )
            self.assertEqual(result["outcome"], "control_error")
            self.assertEqual(result["error"], "cycle memory_limit")
            self.assertEqual(result["error_notes"], errors["native"].__notes__)
            self.assertEqual(job.read(directory, "result.json"), result)
            self.assertEqual(job.read(directory, "state.json")["phase"], "finished")
            self.assertTrue(result["direct_child_reaped"])
            self.assertTrue(result["cleanup_complete"])
            self.assertEqual(result["remaining"], [])
            identity = job.read(directory, "state.json")["child"]
            self.assertFalse(job.runtime.alive(identity))
            print(json.dumps({"synthetic_job_result": result, "actual_child": identity}))

    def test_empty_owned_tmp_after_closure_preserves_files_symlinks_and_foreign_paths(
        self,
    ):
        tmp = Path(os.environ.get("RESEARCH_TEST_TMP", ROOT / ".artifacts/sequence-test-TMP"))
        tmp.mkdir(parents=True, exist_ok=True)
        closed = {
            "direct_child_reaped": True,
            "process_cleanup_complete": True,
            "handle_closes_complete": True,
            "remaining": [],
        }
        with tempfile.TemporaryDirectory(dir=tmp) as name:
            base = Path(name)
            owner = base / "owner"
            owner.mkdir()
            empty = owner / "empty"
            (empty / "nested" / "empty").mkdir(parents=True)
            lc.remove_empty_owned_tmp(empty, owner, closed)
            self.assertFalse(empty.exists())
            unknown = owner / "unknown"
            unknown.mkdir()
            with self.assertRaises(lc.Refused):
                lc.remove_empty_owned_tmp(unknown, owner, None)
            self.assertTrue(unknown.is_dir())
            nonempty = owner / "nonempty"
            nonempty.mkdir()
            payload = nonempty / "keep"
            payload.write_bytes(b"synthetic retained payload")
            with self.assertRaises(OSError):
                lc.remove_empty_owned_tmp(nonempty, owner, closed)
            self.assertEqual(payload.read_bytes(), b"synthetic retained payload")
            foreign = base / "foreign"
            foreign.mkdir()
            preserved = foreign / "keep"
            preserved.write_bytes(b"foreign synthetic payload")
            linked = owner / "linked"
            linked.mkdir()
            (linked / "foreign").symlink_to(foreign, target_is_directory=True)
            with self.assertRaises(OSError):
                lc.remove_empty_owned_tmp(linked, owner, closed)
            self.assertTrue((linked / "foreign").is_symlink())
            self.assertEqual(preserved.read_bytes(), b"foreign synthetic payload")
            with self.assertRaises(lc.Refused):
                lc.remove_empty_owned_tmp(foreign, owner, closed)
            rootlink = owner / "rootlink"
            rootlink.symlink_to(foreign, target_is_directory=True)
            with self.assertRaises(lc.Refused):
                lc.remove_empty_owned_tmp(rootlink, owner, closed)
            self.assertTrue(rootlink.is_symlink())
            self.assertTrue(foreign.is_dir())


if __name__ == "__main__":
    unittest.main()
