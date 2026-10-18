"""Only new cancel-read faults in an already-live command's cleanup branch."""

import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]
ROOT = Path("/workspaces/quoridor")
spec = importlib.util.spec_from_file_location(
    "cleanup_read_job", SOURCE / "scripts/dev/research-job.py"
)
j = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j)


class CleanupCancelReadTests(unittest.TestCase):
    def test_unreadable_or_malformed_cancel_keeps_primary_and_finishes_independent_cleanup(self):
        for fault in ("OSError", "malformed_JSON"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                trace = []
                actual_read = j.read
                actual_identity = j.runtime.process_identity
                actual_close = os.close
                child_identity = dict(pid=2147483000, start_ticks="123", boot_id="synthetic")
                clock = [100.0]

                class Pipe(io.BytesIO):
                    def close(self):
                        trace.append("pipe_close")
                        super().close()

                class Command:
                    pid = child_identity["pid"]
                    returncode = None
                    stdout = Pipe(b"")

                    def poll(self):
                        return self.returncode

                    def terminate(self):
                        trace.append("grace_TERM")
                        if fault == "malformed_JSON":
                            raise OSError("secondary grace TERM fault")

                    def wait(self, *, timeout):
                        trace.append(["wait", timeout])
                        if timeout == 45:
                            if fault == "OSError":
                                raise subprocess.TimeoutExpired("synthetic grace", timeout)
                            raise OSError("secondary grace wait fault")
                        self.returncode = -9
                        return self.returncode

                command = Command()

                class Thread:
                    def start(self):
                        trace.append("log_start")

                    def join(self, *, timeout):
                        trace.append("log_join")

                    def is_alive(self):
                        return False

                class Tail:
                    data = b"bounded synthetic log\n"
                    bytes_seen = len(data)
                    thread = Thread()

                class Resources:
                    def check(self):
                        state = actual_read(directory, "state.json")
                        if state["phase"] == "running":
                            # The primary failure predates cleanup. No real process,
                            # signal or cancellation side effect is injected elsewhere.
                            (directory / "cancel.json").write_text(
                                "{" if fault == "malformed_JSON" else "{}"
                            )
                            raise ValueError("original primary resource refusal")

                cfg = dict(
                    issue="work",
                    goal_issue="goal",
                    thread_id="owner",
                    cwd=str(ROOT),
                    argv=[
                        sys.executable,
                        "-B",
                        str(ROOT / "scripts/dev/research-lifecycle.py"),
                        "cohort",
                        "--intent",
                        str(directory / "intent.json"),
                        "--sha256",
                        "synthetic",
                    ],
                    end_at=None,
                    notify_until=None,
                    max_runtime_seconds=60,
                    control_interval_seconds=30,
                    notify_interval_seconds=10,
                    request_timeout_seconds=1,
                    log_max_bytes=4096,
                    resource_contract=str(directory / "intent.json"),
                )
                j.write(
                    directory,
                    "state.json",
                    dict(phase="queued", job_id="same-original-job", thread_id="owner"),
                )

                def read(path, name):
                    if name == "cancel.json" and fault == "OSError":
                        trace.append("cancel_read_OSError")
                        raise OSError("secondary cancel read fault")
                    return actual_read(path, name)

                def close(fd):
                    if fd == 2147482000:
                        trace.append("pidfd_close")
                    else:
                        actual_close(fd)

                def write(path, name, value, **kwargs):
                    trace.append(["publish", name])
                    return j.runtime.atomic_json(path / name, value, **kwargs)

                def send(fd, sig):
                    trace.append(["direct_signal", int(sig)])

                backend = type(
                    "Backend",
                    (),
                    {
                        "issues": lambda self, ids, **kwargs: [
                            dict(id=i, status="in_progress", labels=[], assignee="codex:owner")
                            for i in ids
                        ]
                    },
                )()
                with (
                    patch.object(j, "read", side_effect=read),
                    patch.object(j, "write", side_effect=write),
                    patch.object(j.subprocess, "Popen", return_value=command),
                    patch.object(j, "TailLog", return_value=Tail()),
                    patch.object(j.os, "pidfd_open", return_value=2147482000),
                    patch.object(j.os, "close", side_effect=close),
                    patch.object(j.signal, "pidfd_send_signal", side_effect=send),
                    patch.object(
                        j.runtime,
                        "process_identity",
                        side_effect=lambda pid: child_identity
                        if pid == child_identity["pid"]
                        else actual_identity(pid),
                    ),
                    patch.object(
                        j.runtime,
                        "alive",
                        side_effect=lambda item: item == child_identity
                        and command.returncode is None,
                    ),
                    patch.object(j, "track_descendants", return_value=[child_identity]),
                    patch.object(j, "descendants_in_group", return_value=[]),
                    patch.object(
                        j,
                        "signal_members",
                        side_effect=lambda items, sig: trace.append(
                            ["descendant_signal", int(sig)]
                        ),
                    ),
                    patch.object(j.time, "monotonic", side_effect=lambda: clock[0]),
                    patch.object(
                        j.time,
                        "sleep",
                        side_effect=lambda duration: clock.__setitem__(0, clock[0] + duration),
                    ),
                ):
                    result = j.execute(directory, cfg, ROOT, backend, resources=Resources())
                self.assertEqual(result["error"], "original primary resource refusal")
                self.assertNotEqual(result["outcome"], "succeeded")
                self.assertFalse(result["cleanup_complete"])
                errors = result["cleanup_errors"]
                self.assertTrue(
                    any(
                        e["stage"] == "cohort_cancel_read"
                        and e["type"] == ("OSError" if fault == "OSError" else "JSONDecodeError")
                        for e in errors
                    ),
                    errors,
                )
                self.assertTrue(any(e["stage"] == "cohort_grace_wait" for e in errors), errors)
                if fault == "malformed_JSON":
                    self.assertTrue(any(e["stage"] == "cohort_grace_term" for e in errors))
                self.assertIn("grace_TERM", trace)  # No unreadable reason qualified as internal.
                self.assertIn(["wait", 45], trace)
                self.assertIn(["wait", 3], trace)
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    self.assertIn(["direct_signal", int(sig)], trace)
                    self.assertIn(["descendant_signal", int(sig)], trace)
                self.assertIn("pipe_close", trace)
                self.assertIn("pidfd_close", trace)
                self.assertIn("log_join", trace)
                for name in ("result.json", "state.json", "notification.json"):
                    self.assertIn(["publish", name], trace)
                self.assertTrue(command.stdout.closed)
                self.assertTrue(result["direct_child_reaped"])
                self.assertEqual(result["remaining"], [])
                self.assertEqual(actual_read(directory, "state.json")["phase"], "finished")
                self.assertEqual(actual_read(directory, "notification.json")["status"], "pending")
                print(
                    json.dumps(
                        dict(
                            fault=fault,
                            retained_primary=result["error"],
                            secondary=errors,
                            obligations=trace,
                            real_children=0,
                            real_signals=0,
                        )
                    ),
                    flush=True,
                )


if __name__ == "__main__":
    unittest.main()
