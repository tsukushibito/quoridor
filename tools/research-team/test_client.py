"""Checks for dispatch safety and response/notification handling."""

import asyncio
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

SOURCE = Path(__file__).resolve().parents[2] / "scripts/dev/research-team.py"
spec = importlib.util.spec_from_file_location("research_team", SOURCE)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class DispatchSafety(unittest.TestCase):
    def test_definition_drift_does_not_block_observation_or_stop(self):
        data = {"definitions_root": "/missing", "roles": {
            "experiment": {"thread_id": "running", "definition_sha256": "old"},
        }}
        self.assertEqual(client.role_entry(data, "experiment", check_definition=False)["thread_id"], "running")
        with patch.object(client, "role_definition", return_value=("new", "new")):
            with self.assertRaises(client.TeamError):
                client.role_entry(data, "experiment")

    def test_failed_or_unfinished_bootstrap_never_counts_as_initialized(self):
        for turns in [[], [{"status": "failed"}], [{"status": "interrupted"}], [{"status": "inProgress"}]]:
            with self.subTest(turns=turns), self.assertRaises(client.TeamError):
                client.require_completed_bootstrap(turns, "experiment")
        client.require_completed_bootstrap([{"status": "completed"}], "experiment")

    def test_paused_and_unready_issues_never_dispatch(self):
        for status, labels in [("blocked", []), ("deferred", []), ("closed", []), ("in_progress", ["paused-by-user"])]:
            with self.subTest(status=status, labels=labels), patch.object(client, "command_json", return_value=[{
                "id": "quoridor-test", "status": status, "labels": labels,
            }]):
                with self.assertRaises(client.TeamError):
                    client.require_issue("quoridor-test", Path("/project"))

    def test_active_delivery_preserves_settings_and_uses_current_turn(self):
        method, params = client.delivery_params(
            {"id": "role", "cwd": "/worktree", "status": {"type": "active"}},
            [{"id": "current", "status": "inProgress"}, {"id": "old", "status": "completed"}],
            "new evidence", None,
        )
        self.assertEqual(method, "turn/steer")
        self.assertEqual(params["expectedTurnId"], "current")
        self.assertNotIn("model", params)
        self.assertNotIn("effort", params)

    def test_active_delivery_cannot_move_worktree_or_guess_turn(self):
        thread = {"id": "role", "cwd": "/worktree", "status": {"type": "active"}}
        with self.assertRaises(client.TeamError):
            client.delivery_params(thread, [], "report", None)
        with self.assertRaises(client.TeamError):
            client.delivery_params(thread, [{"id": "t", "status": "inProgress"}], "report", "/other")

    def test_idle_delivery_starts_turn_without_changing_model(self):
        method, params = client.delivery_params(
            {"id": "role", "status": {"type": "idle"}}, [], "next task", None,
        )
        self.assertEqual(method, "turn/start")
        self.assertEqual(set(params), {"threadId", "input"})


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
    async def test_bootstrap_wait_uses_events_before_history_is_flushed(self):
        server = client.AppServer({}, timeout=0.2)
        server.ws = FakeSocket([{"method": "turn/completed", "params": {
            "threadId": "new-role", "turn": {"id": "bootstrap", "status": "completed"},
        }}])
        with patch.object(server, "turns", new_callable=AsyncMock) as read_history:
            result = await server.wait("new-role", 0.2, subscribe=False,
                                       target={"id": "bootstrap", "status": "inProgress"})
            self.assertEqual(result["turn"]["status"], "completed")
            read_history.assert_not_called()

    async def test_interleaved_events_and_server_requests_do_not_corrupt_response(self):
        server = client.AppServer({}, timeout=0.2)
        server.ws = FakeSocket([
            {"method": "turn/completed", "params": {"threadId": "worker"}},
            {"id": 1, "method": "item/tool/call", "params": {}},
            {"id": 1, "result": {"thread": {"id": "target"}}},
        ])
        result = await server.request("thread/read", {"threadId": "target"})
        self.assertEqual(result["thread"]["id"], "target")
        self.assertEqual(server.notifications[0]["method"], "turn/completed")
        self.assertEqual(server.ws.sent[1]["error"]["code"], -32601)

    async def test_rpc_error_is_failure_and_timeout_is_bounded(self):
        server = client.AppServer({}, timeout=0.01)
        server.ws = FakeSocket([{"id": 1, "error": {"code": -1, "message": "failure"}}])
        with self.assertRaises(client.TeamError):
            await server.request("turn/start", {})
        server.ws = FakeSocket([])
        with self.assertRaises(TimeoutError):
            await server.request("thread/read", {})


if __name__ == "__main__":
    unittest.main()
