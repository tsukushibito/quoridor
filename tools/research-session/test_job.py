"""Background-job tests use temporary commands and fake RPC, never research/model jobs."""

import asyncio
from datetime import timedelta
import importlib.util
import json
import io
import itertools
from types import SimpleNamespace
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/dev/research-job.py"
spec = importlib.util.spec_from_file_location("research_job_test", SOURCE)
j = importlib.util.module_from_spec(spec)
spec.loader.exec_module(j)


class Server:
    def __init__(self):
        self.state = "idle"
        self.calls = []
        self.turns = []
        self.lost_response = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def read_thread(self, thread_id):
        return {"id": thread_id, "status": {"type": self.state}}

    async def request(self, method, params):
        self.calls.append((method, params))
        if method == "thread/resume":
            self.state = "idle"
            return {}
        if method == "thread/turns/list":
            assert params["itemsView"] == "full"
            return {"data": self.turns, "nextCursor": None}
        if method == "turn/start":
            turn = {
                "id": "completion-turn",
                "items": [{"type": "userMessage", "content": params["input"]}],
            }
            self.turns.append(turn)
            self.state = "active"
            if self.lost_response:
                raise TimeoutError("Response lost after accepting turn")
            return {"turn": turn}
        raise AssertionError(method)


class Backend:
    def __init__(self):
        self.server = Server()
        self.items = {
            "goal": {"id": "goal", "status": "in_progress", "labels": []},
            "work": {
                "id": "work",
                "status": "in_progress",
                "labels": [],
                "assignee": "codex:target",
            },
        }

    def issue(self, issue, *, timeout=30):
        return self.items[issue]

    def issues(self, issues, *, timeout):
        # Fake per-record ports retain mutation/error injection. The production
        # backend uses one CLI invocation, checked separately below.
        end = time.monotonic() + timeout
        return [self.issue(issue, timeout=end - time.monotonic()) for issue in issues]

    async def connect(self, timeout):
        return self.server


class AuthorityBatchTests(unittest.TestCase):
    def test_serialized_read_over_five_seconds_preserves_authority_checks(self):
        config = {"goal_issue": "goal", "issue": "work", "thread_id": "target"}
        for mutation in (None, "paused", "closed", "owner"):
            backend = Backend()
            if mutation == "paused":
                backend.items["goal"]["labels"] = ["paused-by-user"]
            elif mutation == "closed":
                backend.items["work"]["status"] = "closed"
            elif mutation == "owner":
                backend.items["work"]["assignee"] = "codex:other"
            with (
                self.subTest(mutation=mutation),
                patch.object(j.time, "monotonic", side_effect=[0.0, 6.0]),
                patch.object(backend, "issues", return_value=list(backend.items.values())) as read,
            ):
                if mutation is None:
                    self.assertEqual(
                        j.authority(config, None, backend, horizon=None)["thread_id"], "target"
                    )
                else:
                    with self.assertRaises(j.JobError):
                        j.authority(config, None, backend, horizon=None)
                read.assert_called_once()
                self.assertGreater(read.call_args.kwargs["timeout"], 60.0)
                self.assertLessEqual(read.call_args.kwargs["timeout"], 65.0)

    def test_one_store_invocation_binds_all_requested_records(self):
        backend = j.runtime.AppBackend(Path("/workspaces/quoridor"))
        rows = [{"id": "work", "status": "in_progress"}, {"id": "goal", "status": "open"}]
        with patch.object(j.runtime.client, "command_json", return_value=rows) as call:
            self.assertEqual(backend.issues(["goal", "work", "goal"], timeout=0.25), rows[::-1])
        call.assert_called_once_with(
            [
                "bash",
                "/workspaces/quoridor/scripts/dev/beads.sh",
                "show",
                "goal",
                "work",
                "--brief-deps",
                "--json",
            ],
            timeout=0.25,
        )

    def test_missing_duplicate_or_unrequested_records_refuse(self):
        backend = j.runtime.AppBackend(Path("/workspaces/quoridor"))
        for rows in (
            [{"id": "goal"}],
            [{"id": "goal"}, {"id": "goal"}],
            [{"id": "goal"}, {"id": "other"}],
            [{"id": "goal"}, None],
        ):
            with (
                self.subTest(rows=rows),
                patch.object(j.runtime.client, "command_json", return_value=rows),
            ):
                with self.assertRaises(j.runtime.RuntimeError):
                    backend.issues(["goal", "work"], timeout=0.25)

    def test_authority_has_one_finite_clipped_batch_and_rejects_late_return(self):
        backend = Backend()
        config = {"goal_issue": "goal", "issue": "work", "thread_id": "target"}
        fixed = j.now()
        horizon = (fixed + timedelta(seconds=0.05)).isoformat()
        with (
            patch.object(j, "now", return_value=fixed),
            patch.object(backend, "issues", wraps=backend.issues) as call,
        ):
            self.assertEqual(
                j.authority(config, None, backend, horizon=horizon)["thread_id"], "target"
            )
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.kwargs["timeout"], 0.05)
        with (
            patch.object(backend, "issues", return_value=list(backend.items.values())),
            patch.object(j.time, "monotonic", side_effect=[0.0, j.CONTROL_READ_SECONDS]),
        ):
            with self.assertRaisesRegex(j.JobError, "budget exhausted"):
                j.authority(config, None, backend, horizon=None)
        with patch.object(backend, "issues") as call, patch.object(j, "now", return_value=fixed):
            with self.assertRaisesRegex(j.JobError, "budget exhausted"):
                j.authority(
                    config, None, backend, horizon=(fixed - timedelta(seconds=1)).isoformat()
                )
        call.assert_not_called()


class Fixture:
    def setup(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "contract.md").write_text("Artificial test command only, no model")
        self.config = {
            "issue": "work",
            "goal_issue": "goal",
            "thread_id": "target",
            "cwd": str(self.root),
            "argv": [sys.executable, "-c", "print('finished')"],
            "end_at": (j.now() + timedelta(seconds=60)).isoformat(),
            "notify_until": (j.now() + timedelta(seconds=120)).isoformat(),
            "max_runtime_seconds": 10,
            "control_interval_seconds": 1,
            "notify_interval_seconds": 1,
            "request_timeout_seconds": 1,
            "log_max_bytes": 128,
            "resource_contract": str(self.root / "contract.md"),
        }
        self.directory = self.root / "job"
        self.directory.mkdir()
        j.write(self.directory, "config.json", self.config)
        j.write(
            self.directory,
            "state.json",
            {
                "phase": "queued",
                "job_id": "unique-job",
                "issue": "work",
                "thread_id": "target",
            },
        )
        self.backend = Backend()

    def complete(self):
        j.write(
            self.directory,
            "state.json",
            {
                "phase": "finished",
                "job_id": "unique-job",
                "issue": "work",
                "thread_id": "target",
            },
        )
        j.write(
            self.directory,
            "result.json",
            {"outcome": "succeeded", "exit_code": 0, "cleanup_complete": True},
        )
        j.write(self.directory, "notification.json", {"status": "pending"})


class CommandTests(Fixture, unittest.TestCase):
    def setUp(self):
        self.setup()

    def execute(self):
        return j.execute(self.directory, self.config, self.root, self.backend)

    def test_completion_and_bounded_log(self):
        self.config["argv"] = [
            sys.executable,
            "-c",
            "print('X'*20000); print('THE-END')",
        ]
        result = self.execute()
        self.assertEqual(result["outcome"], "succeeded")
        self.assertTrue(result["cleanup_complete"])
        self.assertGreater(result["log_bytes_seen"], 20000)
        self.assertLessEqual((self.directory / "output.log").stat().st_size, 128)
        self.assertIn(b"THE-END", (self.directory / "output.log").read_bytes())

    def test_no_deadline_or_runtime_limit_completes_and_reaps(self):
        self.config.update(end_at=None, notify_until=None, max_runtime_seconds=None)
        validated = j.validate(self.config, self.root)
        self.assertIsNone(validated["end_at"])
        self.assertIsNone(validated["notify_until"])
        self.assertIsNone(validated["max_runtime_seconds"])
        result = self.execute()
        self.assertEqual(result["outcome"], "succeeded")
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(result["remaining"], [])

    def test_no_time_limit_still_stops_for_user_pause(self):
        self.config.update(end_at=None, notify_until=None, max_runtime_seconds=None)
        self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(30)"]
        original = self.backend.issue
        calls = 0

        def issue(issue_id, *, timeout=30):
            nonlocal calls
            calls += 1
            if calls > 2:
                self.backend.items["goal"]["labels"] = ["paused-by-user"]
            return original(issue_id, timeout=timeout)

        self.backend.issue = issue
        result = self.execute()
        self.assertEqual(result["outcome"], "control_error")
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(result["remaining"], [])

    def test_no_time_limit_still_honors_explicit_cancel(self):
        self.config.update(end_at=None, notify_until=None, max_runtime_seconds=None)
        j.write(self.directory, "cancel.json", {})
        with patch.object(j.subprocess, "Popen") as spawn:
            self.assertEqual(self.execute()["outcome"], "not_started")
            spawn.assert_not_called()

    def test_failure_does_not_become_scientific_success(self):
        self.config["argv"] = [sys.executable, "-c", "raise SystemExit(7)"]
        self.assertEqual(self.execute()["exit_code"], 7)
        self.assertEqual(j.read(self.directory, "result.json")["outcome"], "failed")

    def test_timeout_stops_group_and_reaps_child(self):
        self.config["max_runtime_seconds"] = 1
        self.config["argv"] = [
            sys.executable,
            "-c",
            "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); time.sleep(30)",
        ]
        result = self.execute()
        self.assertEqual(result["outcome"], "timed_out")
        self.assertTrue(result["cleanup_complete"])
        self.assertEqual(result["remaining"], [])

    def test_timeout_stops_recorded_separate_session_child(self):
        self.config["max_runtime_seconds"] = 2
        self.config["argv"] = [
            sys.executable,
            "-c",
            "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True);time.sleep(30)",
        ]
        result = self.execute()
        self.assertEqual(result["outcome"], "timed_out")
        self.assertTrue(result["cleanup_complete"])

    def test_cancel_before_spawn(self):
        j.write(self.directory, "cancel.json", {})
        with patch.object(j.subprocess, "Popen") as spawn:
            self.assertEqual(self.execute()["outcome"], "not_started")
            spawn.assert_not_called()

    def test_paused_before_spawn(self):
        self.backend.items["goal"]["labels"] = ["paused-by-user"]
        self.assertEqual(self.execute()["outcome"], "not_started")

    def test_owner_change_during_command_stops_it(self):
        original = self.backend.issue
        calls = 0

        def issue(issue_id, *, timeout=30):
            nonlocal calls
            calls += 1
            if calls > 2:
                self.backend.items["work"]["assignee"] = "other"
            return original(issue_id, timeout=timeout)

        self.backend.issue = issue
        self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(30)"]
        result = self.execute()
        self.assertEqual(result["outcome"], "control_error")
        self.assertTrue(result["cleanup_complete"])

    def test_completed_command_is_not_rerun(self):
        self.execute()
        with self.assertRaises(j.JobError):
            self.execute()

    def test_invalid_configuration(self):
        for field, value in [
            ("argv", "shell command"),
            ("max_runtime_seconds", True),
            ("end_at", "2026-01-01"),
            ("argv", ["python", "-c", "pass"]),
        ]:
            with (
                self.subTest(field=field, value=value),
                self.assertRaises((j.JobError, j.runtime.RuntimeError)),
            ):
                j.validate({**self.config, field: value}, self.root)

    def test_orphan_process_is_not_reported_clean(self):
        self.config["argv"] = [
            sys.executable,
            "-c",
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])",
        ]
        result = self.execute()
        self.assertEqual(result["outcome"], "cleanup_required")
        self.assertTrue(result["cleanup_complete"])

    def test_real_detached_completion_survives_submitter_exit(self):
        # The actual supervisor runs in another process. Its fake backend only logs
        # one synthetic turn; no live Beads/AppServer or LLM is contacted.
        harness = self.root / "harness.py"
        harness.write_text(f"""import importlib.util,json,sys
from pathlib import Path
s=importlib.util.spec_from_file_location("jobtest",{str(Path(__file__).resolve())!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=m.Backend();d=Path(sys.argv[1]);m.j.run(d,d.parent,b)
(d/"fake-rpc.json").write_text(json.dumps(b.server.calls))
""")
        launcher = self.root / "launcher.py"
        launcher.write_text(f"""import subprocess,sys
subprocess.Popen([sys.executable,{str(harness)!r},{str(self.directory)!r}],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
""")
        subprocess.run([sys.executable, str(launcher)], check=True, timeout=3)
        import time

        until = time.monotonic() + 5
        while not (self.directory / "fake-rpc.json").exists() and time.monotonic() < until:
            time.sleep(0.05)
        calls = json.loads((self.directory / "fake-rpc.json").read_text())
        self.assertEqual([x[0] for x in calls], ["turn/start"])
        self.assertEqual(j.read(self.directory, "result.json")["outcome"], "succeeded")

    def test_cleanup_discovery_and_signal_errors_still_wait_and_publish(self):
        for fault in ("track_descendants", "signal_members"):
            with self.subTest(fault=fault):
                self.setup()
                self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(10)"]
                if fault == "signal_members":
                    self.config["max_runtime_seconds"] = 1
                launched = []
                real_launch = j.subprocess.Popen

                def launch(*args, **kwargs):
                    child = real_launch(*args, **kwargs)
                    launched.append(child)
                    return child

                with (
                    patch.object(j, fault, side_effect=OSError("fixture cleanup")),
                    patch.object(j.subprocess, "Popen", side_effect=launch),
                ):
                    result = self.execute()
                self.assertIsNotNone(launched[0].returncode)
                self.assertTrue(result["direct_child_reaped"])
                self.assertFalse(result["cleanup_complete"])
                self.assertTrue(result["cleanup_errors"])
                self.assertEqual(j.read(self.directory, "result.json"), result)
                self.assertEqual(j.read(self.directory, "state.json")["phase"], "finished")

    def test_explicit_execution_horizon_rejects_expired_submit_and_execute(self):
        self.config.update(
            end_at=(j.now() - timedelta(seconds=1)).isoformat(),
            notify_until=(j.now() + timedelta(minutes=1)).isoformat(),
        )
        j.write(self.directory, "config.json", self.config)
        with (
            patch.object(self.backend, "issue", wraps=self.backend.issue) as issue,
            patch.object(j.subprocess, "Popen") as launch,
        ):
            self.assertEqual(self.execute()["outcome"], "not_started")
            with self.assertRaises(j.JobError):
                j.submit(
                    self.directory / "config.json",
                    self.root / "never-submitted",
                    self.root,
                    self.backend,
                )
            issue.assert_not_called()
            launch.assert_not_called()
        self.assertFalse((self.root / "never-submitted").exists())

    def test_dual_signal_failures_preserve_both_receipt_facts_and_direct_wait(self):
        child = SimpleNamespace(
            pid=999999999,
            stdout=io.BytesIO(),
            returncode=None,
            poll=Mock(side_effect=[ValueError("primary control failure"), None, None]),
            send_signal=Mock(side_effect=OSError("fallback Popen failure")),
        )

        def waited(*args, **kwargs):
            child.returncode = 7
            return 7

        child.wait = Mock(side_effect=waited)
        identity = {"pid": child.pid, "start_ticks": "1", "boot_id": "synthetic"}
        fd = j.os.open("/dev/null", j.os.O_RDONLY)
        with (
            patch.object(j, "authority", return_value={"thread_id": "target"}),
            patch.object(j.subprocess, "Popen", return_value=child),
            patch.object(j.os, "pidfd_open", return_value=fd),
            patch.object(j.runtime, "process_identity", return_value=identity),
            patch.object(j, "track_descendants", return_value=[]),
            patch.object(j, "descendants_in_group", return_value=[]),
            patch.object(
                j.signal, "pidfd_send_signal", side_effect=OSError("original pidfd failure")
            ),
            patch.object(j.time, "monotonic", side_effect=itertools.count()),
            patch.object(j.time, "sleep"),
        ):
            result = self.execute()
        child.wait.assert_called_once_with(timeout=3)
        self.assertTrue(child.stdout.closed)
        self.assertTrue(result["direct_child_reaped"])
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual(result["error"], "primary control failure")
        saved = j.read(self.directory, "result.json")
        for stage in ("direct_term", "direct_kill"):
            facts = {fact["stage"]: fact["message"] for fact in saved["cleanup_errors"]}
            self.assertEqual(facts[stage + "_pidfd"], "original pidfd failure")
            self.assertEqual(facts[stage + "_popen"], "fallback Popen failure")

    def test_pidfd_signal_failure_reaps_owned_direct_child(self):
        self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(10)"]
        self.config["max_runtime_seconds"] = 0.1
        with patch.object(j.signal, "pidfd_send_signal", side_effect=OSError("pidfd fixture")):
            result = self.execute()
        self.assertTrue(result["direct_child_reaped"])
        self.assertEqual(result["remaining"], [])
        self.assertFalse(result["cleanup_complete"])
        self.assertTrue(
            any(error["stage"] == "direct_term_pidfd" for error in result["cleanup_errors"])
        )

    def test_missing_identity_waits_without_claiming_visibility(self):
        self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(10)"]
        with patch.object(j.runtime, "process_identity", return_value=None):
            result = self.execute()
        self.assertTrue(result["direct_child_reaped"])
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual(result["descendant_visibility"], "unavailable")
        self.assertIn("Cannot record child identity", result["error"])

    def test_log_and_receipt_failures_do_not_skip_later_publication(self):
        self.config["argv"] = [sys.executable, "-c", "raise SystemExit(7)"]
        with patch.object(Path, "write_bytes", side_effect=OSError("log fixture")):
            result = self.execute()
        self.assertEqual(result["exit_code"], 7)
        self.assertFalse(result["cleanup_complete"])
        self.assertEqual(result["cleanup_errors"][0]["stage"], "log_publish")
        self.setup()
        original = j.write
        calls = []

        def fail_receipt(directory, name, value):
            calls.append(name)
            if name == "result.json":
                raise OSError("receipt fixture")
            return original(directory, name, value)

        with patch.object(j, "write", side_effect=fail_receipt):
            with self.assertRaises(BaseExceptionGroup) as error:
                self.execute()
        self.assertEqual(calls[-3:], ["result.json", "state.json", "notification.json"])
        self.assertIn('"direct_child_reaped": true', error.exception.__notes__[0])

    def test_authority_deadline_bounds_two_reads_and_propagates_backend_timeout(self):
        budgets = []

        def slow(issue, *, timeout):
            budgets.append(timeout)
            import time

            time.sleep(min(timeout, 0.015))
            return self.backend.items[issue]

        self.backend.issue = slow
        j.authority(
            self.config, self.root, self.backend, horizon=self.config["end_at"], timeout=0.05
        )
        self.assertEqual(len(budgets), 2)
        self.assertLess(budgets[1], budgets[0])
        self.assertLessEqual(sum(budgets), 0.1)

        def timed_out(issue, *, timeout):
            raise subprocess.TimeoutExpired("fake beads", timeout)

        self.backend.issue = timed_out
        with self.assertRaises(subprocess.TimeoutExpired):
            j.authority(
                self.config, self.root, self.backend, horizon=self.config["end_at"], timeout=0.01
            )

    def test_slow_authority_inside_loop_observes_cancel_with_finite_no_deadline_bound(self):
        import time

        self.config.update(end_at=None, notify_until=None, max_runtime_seconds=None)
        self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(10)"]
        original = self.backend.issue
        calls = 0

        def slow(issue, *, timeout):
            nonlocal calls
            calls += 1
            if calls == 3:
                self.assertLessEqual(timeout, j.CONTROL_READ_SECONDS)
                j.write(self.directory, "cancel.json", {})
                time.sleep(0.05)
            return original(issue, timeout=timeout)

        self.backend.issue = slow
        started = time.monotonic()
        result = self.execute()
        self.assertEqual(result["outcome"], "cancelled")
        self.assertTrue(result["direct_child_reaped"])
        self.assertLess(time.monotonic() - started, 2)

    def test_beads_wrapper_timeout_owns_and_reaps_the_actual_cli(self):
        # An isolated synthetic store and CLI, never the project's Beads store.
        import shlex

        wrapper = self.root / "beads.sh"
        source = SOURCE.with_name("beads.sh")
        wrapper.write_text(source.read_text())
        fake = self.root / "fake-bd"
        fake.write_text("#!" + sys.executable + "\nimport time; time.sleep(10)\n")
        fake.chmod(0o700)
        (self.root / "metadata.json").write_text("{}")
        (self.root / "beads-env.sh").write_text(
            "beads_binary="
            + shlex.quote(str(fake))
            + "\n"
            + "BEADS_DIR="
            + shlex.quote(str(self.root))
            + "\n"
            + "beads_lock="
            + shlex.quote(str(self.root / "synthetic.lock"))
            + "\n"
        )
        launched = []
        original = j.client.subprocess.Popen

        def launch(*args, **kwargs):
            child = original(*args, **kwargs)
            launched.append(child)
            return child

        with patch.object(j.client.subprocess, "Popen", side_effect=launch):
            with self.assertRaises(subprocess.TimeoutExpired):
                j.client.command_json(["bash", str(wrapper), "show", "synthetic"], timeout=0.15)
        self.assertEqual(len(launched), 1)
        self.assertIsNotNone(launched[0].returncode)
        self.assertFalse(Path(f"/proc/{launched[0].pid}").exists())
        # With --no-fork the stable flock PID is replaced by the CLI: no unowned child.
        self.assertIn("--no-fork", wrapper.read_text())

    def test_slow_backend_timeout_is_bounded_by_remaining_runtime_and_waited(self):
        import time

        self.config.update(end_at=None, max_runtime_seconds=0.08)
        self.config["argv"] = [sys.executable, "-c", "import time; time.sleep(10)"]
        calls = 0

        def slow(issue, *, timeout):
            nonlocal calls
            calls += 1
            if calls > 2:
                self.assertLessEqual(timeout, 0.08)
                time.sleep(timeout)
                raise subprocess.TimeoutExpired("fake beads", timeout)
            return self.backend.items[issue]

        self.backend.issue = slow
        started = time.monotonic()
        result = self.execute()
        self.assertEqual(result["outcome"], "timed_out")
        self.assertTrue(result["direct_child_reaped"])
        self.assertTrue(result["cleanup_complete"])
        self.assertLess(time.monotonic() - started, 1.5)

    def test_concurrent_atomic_writers_use_independent_temporaries(self):
        barrier = threading.Barrier(2)
        replace = j.runtime.os.replace
        failures = []
        path = self.root / "cancel.json"

        def synchronized(source, destination):
            barrier.wait(timeout=2)
            replace(source, destination)

        def publish(value):
            try:
                j.runtime.atomic_json(path, {"writer": value})
            except BaseException as error:
                failures.append(error)

        with patch.object(j.runtime.os, "replace", side_effect=synchronized):
            writers = [threading.Thread(target=publish, args=(n,)) for n in (1, 2)]
            for writer in writers:
                writer.start()
            for writer in writers:
                writer.join(timeout=3)
        self.assertFalse(any(writer.is_alive() for writer in writers))
        self.assertEqual(failures, [])
        self.assertIn(json.loads(path.read_text())["writer"], (1, 2))
        before = path.read_bytes()
        with patch.object(j.runtime.os, "replace", side_effect=OSError("replace fixture")):
            with self.assertRaisesRegex(OSError, "replace fixture"):
                j.runtime.atomic_json(path, {"writer": 3})
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(self.root.glob("*.tmp")), [])


class NotificationTests(Fixture, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.setup()
        self.complete()

    async def notify(self):
        return await j.notify_once(self.directory, self.config, self.root, self.backend)

    async def test_past_execution_horizon_future_and_null_notify_deliver_once(self):
        fixed = j.now()
        for notify_until in ((fixed + timedelta(minutes=1)).isoformat(), None):
            with self.subTest(notify_until=notify_until):
                self.backend = Backend()
                self.complete()
                self.config.update(
                    end_at=(fixed - timedelta(seconds=1)).isoformat(), notify_until=notify_until
                )
                with patch.object(j, "now", return_value=fixed):
                    self.assertEqual((await self.notify())["status"], "delivered")
                    self.assertEqual((await self.notify())["status"], "delivered")
                self.assertEqual([name for name, _ in self.backend.server.calls], ["turn/start"])

    async def test_active_deferred_before_end_at_then_idle_after_end_at_delivers_once(self):
        fixed = j.now()
        self.config.update(
            end_at=(fixed + timedelta(seconds=1)).isoformat(),
            notify_until=(fixed + timedelta(minutes=1)).isoformat(),
        )
        self.backend.server.state = "active"
        with patch.object(j, "now", return_value=fixed):
            self.assertEqual((await self.notify())["status"], "pending")
        self.assertEqual(self.backend.server.calls, [])
        self.backend.server.state = "idle"
        with patch.object(j, "now", return_value=fixed + timedelta(seconds=2)):
            self.assertEqual((await self.notify())["status"], "delivered")
            self.assertEqual((await self.notify())["status"], "delivered")
        self.assertEqual([name for name, _ in self.backend.server.calls], ["turn/start"])

    async def test_past_end_at_rejects_expired_notify_pause_and_owner_change(self):
        fixed = j.now()
        self.config["end_at"] = (fixed - timedelta(seconds=1)).isoformat()
        for cause in ("expired", "paused", "owner"):
            with self.subTest(cause=cause):
                self.backend = Backend()
                self.complete()
                self.config["notify_until"] = (fixed + timedelta(minutes=1)).isoformat()
                if cause == "expired":
                    self.config["notify_until"] = (fixed - timedelta(seconds=1)).isoformat()
                elif cause == "paused":
                    self.backend.items["goal"]["labels"] = ["paused-by-user"]
                else:
                    self.backend.items["work"]["assignee"] = "other"
                with patch.object(j, "now", return_value=fixed):
                    self.assertEqual(
                        (await self.notify())["status"],
                        "expired" if cause == "expired" else "cancelled",
                    )
                self.assertEqual(self.backend.server.calls, [])
                self.assertTrue((self.directory / "result.json").exists())

    async def test_both_notification_authority_checks_bound_both_issue_reads(self):
        import time

        fixed = j.now()
        self.config.update(
            end_at=(fixed - timedelta(seconds=1)).isoformat(),
            notify_until=(fixed + timedelta(seconds=0.05)).isoformat(),
        )
        calls = []

        def issue(issue_id, *, timeout):
            calls.append((issue_id, timeout))
            time.sleep(0.004)
            return self.backend.items[issue_id]

        self.backend.issue = issue
        with patch.object(j, "now", return_value=fixed):
            self.assertEqual((await self.notify())["status"], "delivered")
        self.assertEqual([name for name, _ in calls], ["goal", "work", "goal", "work"])
        for start in (0, 2):
            self.assertGreater(calls[start + 1][1], 0)
            self.assertLess(calls[start + 1][1], calls[start][1])
            self.assertLessEqual(calls[start][1], 0.05)
        self.assertEqual([name for name, _ in self.backend.server.calls], ["turn/start"])

    async def test_null_notification_horizon_has_finite_db_budget_and_final_recheck_rejects_pause(
        self,
    ):
        fixed = j.now()
        self.config.update(end_at=(fixed - timedelta(seconds=1)).isoformat(), notify_until=None)
        calls = []

        def issue(issue_id, *, timeout):
            calls.append(timeout)
            if len(calls) == 3:
                self.backend.items["goal"]["labels"] = ["paused-by-user"]
            return self.backend.items[issue_id]

        self.backend.issue = issue
        with patch.object(j, "now", return_value=fixed):
            self.assertEqual((await self.notify())["status"], "cancelled")
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(0 < budget <= j.CONTROL_READ_SECONDS for budget in calls))
        self.assertEqual(self.backend.server.calls, [])

    async def test_notification_horizon_expiring_during_final_recheck_is_expired(self):
        fixed = j.now()
        horizon = fixed + timedelta(seconds=1)
        self.config.update(
            end_at=(fixed - timedelta(seconds=1)).isoformat(), notify_until=horizon.isoformat()
        )
        current = [fixed]
        original = self.backend.server.read_thread

        async def read_thread(thread_id):
            current[0] = horizon + timedelta(seconds=1)
            return await original(thread_id)

        self.backend.server.read_thread = read_thread
        with patch.object(j, "now", side_effect=lambda: current[0]):
            self.assertEqual((await self.notify())["status"], "expired")
        self.assertEqual(self.backend.server.calls, [])

    async def test_idle_woken_once_and_settings_preserved(self):
        self.assertEqual((await self.notify())["status"], "delivered")
        await self.notify()
        self.assertEqual(len(self.backend.server.calls), 1)
        method, params = self.backend.server.calls[0]
        self.assertEqual(method, "turn/start")
        self.assertEqual(set(params), {"threadId", "input", "approvalPolicy", "sandboxPolicy"})
        self.assertEqual(params["approvalPolicy"], "never")
        self.assertEqual(params["sandboxPolicy"], {"type": "dangerFullAccess"})
        self.assertIn("unique-job", params["input"][0]["text"])

    async def test_no_notification_deadline_delivers_once(self):
        self.config["notify_until"] = None
        self.assertEqual((await self.notify())["status"], "delivered")
        await self.notify()
        self.assertEqual(len(self.backend.server.calls), 1)

    async def test_no_notification_deadline_stops_watching_on_pause(self):
        self.config["notify_until"] = None
        self.backend.items["goal"]["labels"] = ["paused-by-user"]
        result = await asyncio.to_thread(
            j.watch_notification, self.directory, self.config, self.root, self.backend
        )
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.backend.server.calls, [])

    async def test_active_is_deferred_without_steering(self):
        self.backend.server.state = "active"
        self.assertEqual((await self.notify())["status"], "pending")
        self.assertEqual(self.backend.server.calls, [])
        self.backend.server.state = "idle"
        self.assertEqual((await self.notify())["status"], "delivered")

    async def test_not_loaded_resumed_without_model_override(self):
        self.backend.server.state = "notLoaded"
        await self.notify()
        self.assertEqual([x[0] for x in self.backend.server.calls], ["thread/resume", "turn/start"])
        self.assertEqual(
            self.backend.server.calls[0][1],
            {
                "threadId": "target",
                "excludeTurns": True,
                "sandbox": "danger-full-access",
                "approvalPolicy": "never",
            },
        )
        self.assertEqual(
            self.backend.server.calls[1][1]["sandboxPolicy"],
            {"type": "dangerFullAccess"},
        )

    async def test_paused_or_closed_never_wakes(self):
        for item in (self.backend.items["goal"], self.backend.items["work"]):
            j.write(self.directory, "notification.json", {"status": "pending"})
            item["status"] = "closed"
            self.assertEqual((await self.notify())["status"], "cancelled")
            item["status"] = "in_progress"
            j.write(self.directory, "notification.json", {"status": "pending"})
            item["labels"] = ["paused-by-user"]
            await self.notify()
            item["labels"] = []
        self.assertEqual(self.backend.server.calls, [])

    async def test_expired_notification_preserves_result(self):
        self.config["notify_until"] = (j.now() - timedelta(seconds=1)).isoformat()
        self.assertEqual((await self.notify())["status"], "expired")
        self.assertTrue((self.directory / "result.json").exists())
        self.assertEqual(self.backend.server.calls, [])

    async def test_changed_owner_never_wakes(self):
        self.backend.items["work"]["assignee"] = "another"
        self.assertEqual((await self.notify())["status"], "cancelled")
        self.assertEqual(self.backend.server.calls, [])

    async def test_lost_response_reconciled_without_second_start(self):
        self.backend.server.lost_response = True
        self.assertEqual((await self.notify())["status"], "uncertain")
        self.assertEqual((await self.notify())["status"], "delivered")
        self.assertEqual(sum(method == "turn/start" for method, _ in self.backend.server.calls), 1)

    async def test_unknown_receipt_never_blindly_retried(self):
        j.write(self.directory, "notification.json", {"status": "dispatching"})
        self.assertEqual((await self.notify())["status"], "uncertain")
        self.assertFalse(any(method == "turn/start" for method, _ in self.backend.server.calls))

    async def test_cancel_suppresses_wakeup(self):
        j.write(self.directory, "cancel.json", {})
        self.assertEqual((await self.notify())["status"], "cancelled")
        self.assertEqual(self.backend.server.calls, [])


if __name__ == "__main__":
    unittest.main()
