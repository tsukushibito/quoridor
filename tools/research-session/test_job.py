"""Background-job tests use temporary commands and fake RPC, never research/model jobs."""

from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def issue(self, issue):
        return self.items[issue]

    async def connect(self, timeout):
        return self.server


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
            {"phase": "queued", "job_id": "unique-job", "issue": "work", "thread_id": "target"},
        )
        self.backend = Backend()

    def complete(self):
        j.write(
            self.directory,
            "state.json",
            {"phase": "finished", "job_id": "unique-job", "issue": "work", "thread_id": "target"},
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
        self.config["argv"] = [sys.executable, "-c", "print('X'*20000); print('THE-END')"]
        result = self.execute()
        self.assertEqual(result["outcome"], "succeeded")
        self.assertTrue(result["cleanup_complete"])
        self.assertGreater(result["log_bytes_seen"], 20000)
        self.assertLessEqual((self.directory / "output.log").stat().st_size, 128)
        self.assertIn(b"THE-END", (self.directory / "output.log").read_bytes())

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

        def issue(issue_id):
            nonlocal calls
            calls += 1
            if calls > 2:
                self.backend.items["work"]["assignee"] = "other"
            return original(issue_id)

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


class NotificationTests(Fixture, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.setup()
        self.complete()

    async def notify(self):
        return await j.notify_once(self.directory, self.config, self.root, self.backend)

    async def test_idle_woken_once_and_settings_preserved(self):
        self.assertEqual((await self.notify())["status"], "delivered")
        await self.notify()
        self.assertEqual(len(self.backend.server.calls), 1)
        method, params = self.backend.server.calls[0]
        self.assertEqual(method, "turn/start")
        self.assertEqual(set(params), {"threadId", "input"})
        self.assertIn("unique-job", params["input"][0]["text"])

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
        self.assertEqual(set(self.backend.server.calls[0][1]), {"threadId", "excludeTurns"})

    async def test_paused_or_closed_never_wakes(self):
        for item in (self.backend.items["goal"], self.backend.items["work"]):
            item["status"] = "closed"
            self.assertEqual((await self.notify())["status"], "pending")
            item["status"] = "in_progress"
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
        await self.notify()
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
