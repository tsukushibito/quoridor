"""Checks for dispatch safety and response/notification handling."""

import asyncio
import importlib.util
import json
import os
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/dev/research-session.py"
spec = importlib.util.spec_from_file_location("research_session", SOURCE)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class LayoutSafety(unittest.TestCase):
    def test_main_and_managed_worktree_are_explicit_write_destinations(self):
        root = Path("/project")
        records = SimpleNamespace(
            stdout="worktree /project\n\nworktree /project/.worktree/task\n\n"
        )
        with (
            patch.object(client, "project_root", return_value=root),
            patch.object(client.subprocess, "run", return_value=records),
        ):
            self.assertEqual(client.resolve_task_cwd("/project", root), "/project")
            self.assertEqual(
                client.resolve_task_cwd("/project/.worktree/task", root), "/project/.worktree/task"
            )
            for target in (
                "/project/tools",
                "/project/.worktree/retired",
                "/project/.worktree/assets",
                "/project/.worktree/assets/models",
            ):
                with self.assertRaises(client.SessionError):
                    client.resolve_task_cwd(target, root)
        with patch.object(client, "project_root", return_value=Path("/other")):
            with self.assertRaises(client.SessionError):
                client.resolve_task_cwd("/other", root)


class DispatchSafety(unittest.TestCase):
    def test_paused_and_unready_issues_never_dispatch(self):
        for status, labels in [
            ("blocked", []),
            ("deferred", []),
            ("closed", []),
            ("in_progress", ["paused-by-user"]),
        ]:
            with (
                self.subTest(status=status, labels=labels),
                patch.object(
                    client,
                    "command_json",
                    return_value=[
                        {
                            "id": "quoridor-test",
                            "status": status,
                            "labels": labels,
                        }
                    ],
                ),
            ):
                with self.assertRaises(client.SessionError):
                    client.require_issue("quoridor-test", Path("/project"))

    def test_active_delivery_preserves_settings_and_uses_current_turn(self):
        method, params = client.delivery_params(
            {"id": "task-session", "cwd": "/worktree", "status": {"type": "active"}},
            [{"id": "current", "status": "inProgress"}, {"id": "old", "status": "completed"}],
            "new evidence",
            None,
        )
        self.assertEqual(method, "turn/steer")
        self.assertEqual(params["expectedTurnId"], "current")
        self.assertNotIn("model", params)
        self.assertNotIn("effort", params)

    def test_active_delivery_cannot_move_worktree_or_guess_turn(self):
        thread = {"id": "task-session", "cwd": "/worktree", "status": {"type": "active"}}
        with self.assertRaises(client.SessionError):
            client.delivery_params(thread, [], "report", None)
        with self.assertRaises(client.SessionError):
            client.delivery_params(
                thread, [{"id": "t", "status": "inProgress"}], "report", "/other"
            )

    def test_idle_delivery_starts_turn_without_changing_model(self):
        method, params = client.delivery_params(
            {"id": "task-session", "status": {"type": "idle"}},
            [],
            "next task",
            None,
        )
        self.assertEqual(method, "turn/start")
        self.assertEqual(set(params), {"threadId", "input"})


class CommandTests(unittest.IsolatedAsyncioTestCase):
    class Server:
        def __init__(self):
            self.calls = []
            self.state = "idle"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def read_thread(self, thread_id):
            self.calls.append(("thread/read", {"threadId": thread_id}))
            return {"id": thread_id, "cwd": "/project", "status": {"type": self.state}}

        async def turns(self, thread_id, limit=1):
            return [{"id": "current", "status": "inProgress"}]

        async def request(self, method, params):
            self.calls.append((method, params))
            if method == "thread/start":
                return {"thread": {"id": "created"}}
            if method == "turn/start":
                return {"turn": {"id": "started"}}
            if method == "turn/steer":
                return {"turnId": "current"}
            return {}

    async def invoke(self, command, server, **kwargs):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / "task.md"
            body.write_text("Actual implementation task")
            args = SimpleNamespace(
                command=command,
                issue="work",
                body_file=str(body),
                thread="target",
                cwd=None,
                instructions_file=None,
                name=None,
                **kwargs,
            )
            issue_item = {"id": "work", "status": "open", "assignee": "codex:target"}
            with (
                patch.object(client, "project_root", return_value=Path(directory)),
                patch.object(client, "resolve_task_cwd", return_value="/project"),
                patch.object(
                    client,
                    "require_issue",
                    return_value=issue_item,
                ),
                patch.object(
                    client,
                    "creation_issue",
                    return_value={"id": "work", "status": "open", "assignee": ""},
                ),
                patch.object(
                    client,
                    "assign_created_issue",
                    side_effect=lambda issue, root, original, thread_id: issue_item.update(
                        assignee="codex:" + thread_id
                    ),
                ),
                patch.object(
                    client, "command_json", return_value={"status": "running", "socketPath": "fake"}
                ),
                patch.object(client, "AppServer", return_value=server),
            ):
                return await client.run(args)

    async def test_create_starts_only_real_task_without_registry_or_bootstrap(self):
        server = self.Server()
        result = await self.invoke("create", server)
        self.assertEqual(result["thread_id"], "created")
        self.assertEqual([m for m, _ in server.calls], ["thread/start", "turn/start"])
        start = server.calls[0][1]
        self.assertNotIn("developerInstructions", start)
        self.assertNotIn("model", start)
        self.assertIn("Actual implementation task", server.calls[1][1]["input"][0]["text"])

    async def test_send_reads_only_explicit_target_and_steers_exact_active_turn(self):
        server = self.Server()
        server.state = "active"
        result = await self.invoke("send", server)
        self.assertEqual(result["method"], "turn/steer")
        self.assertEqual(server.calls[-1][1]["expectedTurnId"], "current")
        self.assertNotIn("cwd", server.calls[-1][1])
        self.assertEqual(server.calls[0][1]["threadId"], "target")

    async def test_send_refuses_owner_change_after_network_wait(self):
        server = self.Server()
        with patch.object(
            client, "require_owner", side_effect=[{}, client.SessionError("owner changed")]
        ):
            with self.assertRaises(client.SessionError):
                await self.invoke("send", server)
        self.assertFalse(any(m in ("turn/start", "turn/steer") for m, _ in server.calls))

    async def test_send_foreign_owner_never_contacts_target(self):
        server = self.Server()
        with patch.object(
            client, "require_owner", side_effect=client.SessionError("foreign owner")
        ):
            with self.assertRaises(client.SessionError):
                await self.invoke("send", server)
        self.assertEqual(server.calls, [])

    async def test_archive_never_interrupts_active_session(self):
        server = self.Server()
        server.state = "active"
        with self.assertRaises(client.SessionError):
            await self.invoke("archive", server)
        self.assertFalse(any(m == "thread/archive" for m, _ in server.calls))
        server.state = "idle"
        self.assertTrue((await self.invoke("archive", server))["archived"])


class OwnershipTests(unittest.TestCase):
    def test_creation_refuses_foreign_issue_before_thread_start(self):
        with (
            patch.object(
                client,
                "require_issue",
                return_value={"id": "work", "status": "open", "assignee": "codex:foreign"},
            ),
            patch.dict(os.environ, CODEX_THREAD_ID="operator"),
        ):
            with self.assertRaises(client.SessionError):
                client.creation_issue("work", Path("/project"))

    def test_transfer_is_guarded_and_then_verifies_recipient(self):
        original = {"status": "open", "assignee": "codex:operator"}
        with (
            patch.object(client, "command_json") as command,
            patch.object(client, "require_owner") as verify,
        ):
            client.assign_created_issue("work", Path("/project"), original, "created")
            args = command.call_args.args[0]
            self.assertEqual(args[args.index("--if-assignee") + 1], "codex:operator")
            self.assertEqual(args[args.index("--if-status") + 1], "open")
            self.assertNotIn("--force", args)
            verify.assert_called_once_with("work", Path("/project"), "created")


class FakeSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    async def send(self, message):
        self.sent.append(json.loads(message))

    async def recv(self):
        if self.messages:
            return json.dumps(self.messages.pop(0))
        await asyncio.sleep(1)


class ProtocolSafety(unittest.IsolatedAsyncioTestCase):
    async def test_wait_uses_completion_events_before_history_is_flushed(self):
        server = client.AppServer({}, timeout=0.2)
        server.ws = FakeSocket(
            [
                {
                    "method": "turn/completed",
                    "params": {
                        "threadId": "new-session",
                        "turn": {"id": "actual-task", "status": "completed"},
                    },
                }
            ]
        )
        with patch.object(server, "turns", new_callable=AsyncMock) as read_history:
            result = await server.wait(
                "new-session",
                0.2,
                subscribe=False,
                target={"id": "actual-task", "status": "inProgress"},
            )
            self.assertEqual(result["turn"]["status"], "completed")
            read_history.assert_not_called()

    async def test_interleaved_events_and_server_requests_do_not_corrupt_response(self):
        server = client.AppServer({}, timeout=0.2)
        server.ws = FakeSocket(
            [
                {"method": "turn/completed", "params": {"threadId": "worker"}},
                {"id": 1, "method": "item/tool/call", "params": {}},
                {"id": 1, "result": {"thread": {"id": "target"}}},
            ]
        )
        result = await server.request("thread/read", {"threadId": "target"})
        self.assertEqual(result["thread"]["id"], "target")
        self.assertEqual(server.notifications[0]["method"], "turn/completed")
        self.assertEqual(server.ws.sent[1]["error"]["code"], -32601)

    async def test_rpc_error_is_failure_and_timeout_is_bounded(self):
        server = client.AppServer({}, timeout=0.01)
        server.ws = FakeSocket([{"id": 1, "error": {"code": -1, "message": "failure"}}])
        with self.assertRaises(client.SessionError):
            await server.request("turn/start", {})
        server.ws = FakeSocket([])
        with self.assertRaises(TimeoutError):
            await server.request("thread/read", {})


if __name__ == "__main__":
    unittest.main()
