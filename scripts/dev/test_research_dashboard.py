"""NN0 dashboard tests: mocked status ports, isolated named files, no science."""

from copy import deepcopy
from datetime import datetime, timezone
from html.parser import HTMLParser
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class NoScience(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {
            "torch",
            "onnx",
            "onnxruntime",
            "numpy",
            "quoridor_training",
            "requests",
            "websockets",
        }:
            raise AssertionError("Forbidden dependency: " + fullname)
        return None


sys.meta_path.insert(0, NoScience())
spec = importlib.util.spec_from_file_location(
    "dashboard", Path(__file__).with_name("research-dashboard.py")
)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
NOW = datetime(2026, 10, 8, 5, 0, tzinfo=timezone.utc)
OWNER = "codex:00000000-0000-0000-0000-000000000001"
IDLE = "codex:00000000-0000-0000-0000-000000000002"
IDENTITY = {"pid": 12, "start_ticks": "100", "boot_id": "boot"}


def issue(number, owner=OWNER, **metadata):
    return {
        "id": f"demo-{number}",
        "title": f"Task {number}",
        "status": "open",
        "assignee": owner,
        "updated_at": NOW.isoformat(),
        "metadata": {"dashboard": metadata},
        "dependencies": [],
        "labels": [],
    }


class FakePorts:
    def __init__(self, rows):
        self.rows = rows
        self.deps = []
        self.matches = [True]
        self.statuses = {OWNER[6:]: "active", IDLE[6:]: "idle"}
        self.names = {}
        self.calls = []

    def issues(self):
        self.calls.append("issues")
        return deepcopy(self.rows)

    def dependencies(self, ids):
        self.calls.append(("dependencies", ids))
        return self.deps

    def thread(self, thread_id):
        self.calls.append(("status", thread_id))
        value = self.statuses[thread_id]
        if isinstance(value, Exception):
            raise value
        return {
            "thread": {
                "id": thread_id,
                "status": {"type": value},
                "name": self.names.get(thread_id),
                "preview": "SECRET_PREVIEW",
                "turns": [{"prompt": "SECRET_PROMPT"}],
                "notes": "SECRET_NOTES",
            }
        }

    def identities(self, values):
        self.calls.append(("identities", deepcopy(values)))
        if isinstance(self.matches, Exception):
            raise self.matches
        return self.matches


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="dashboard-test-", dir=os.environ.get("TMPDIR")
        )
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def runtime(self, row, phase="running", result=None, **state_extra):
        directory = self.root / row["id"]
        directory.mkdir()
        state = {
            "job_id": "job-1",
            "issue": row["id"],
            "phase": phase,
            "child": IDENTITY,
            "thread_id": row["assignee"][6:] if row.get("assignee") else None,
            **state_extra,
        }
        (directory / "state.json").write_text(json.dumps(state))
        if result is not None:
            (directory / "result.json").write_text(json.dumps(result))
        row["metadata"]["dashboard"]["runtime_dirs"] = [str(directory)]
        return directory

    def snapshot(self, ports):
        return dashboard.collect(ports, NOW)

    def test_actual_thread_name_is_bounded_and_owner_identity_retained(self):
        ports = FakePorts([issue(1)])
        ports.names[OWNER[6:]] = "Actual task name " + "n" * 200
        group = self.snapshot(ports)["groups"][0]
        self.assertEqual(group["name"], ports.names[OWNER[6:]][:160])
        self.assertEqual(group["owner"], OWNER)
        self.assertEqual(group["llm"], "active")
        self.assertNotIn("SECRET_PREVIEW", dashboard.render(self.snapshot(ports)).decode())

    def test_missing_or_invalid_name_never_uses_preview(self):
        ports = FakePorts([issue(1)])
        for value in (None, "", "   ", 12, {"preview": "SECRET"}):
            ports.names[OWNER[6:]] = value
            self.assertEqual(self.snapshot(ports)["groups"][0]["name"], "Not supplied")
        unassigned = self.snapshot(FakePorts([issue(1, owner=None)]))
        self.assertEqual(unassigned["groups"][0]["name"], "Not supplied")

    def test_offline_thread_name_explicitly_unavailable(self):
        ports = FakePorts([issue(1)])
        ports.names[OWNER[6:]] = "Old name"
        self.assertEqual(self.snapshot(ports)["groups"][0]["name"], "Old name")
        ports.statuses[OWNER[6:]] = dashboard.CollectionError("offline")
        group = self.snapshot(ports)["groups"][0]
        self.assertEqual(group["name"], "unavailable")
        self.assertEqual(group["llm"], "unavailable")

    def test_name_injection_remains_data_and_template_searches_actual_name(self):
        ports = FakePorts([issue(1)])
        attack = '</script><img src="https://evil.invalid/">'
        ports.names[OWNER[6:]] = attack
        page = dashboard.render(self.snapshot(ports)).decode()
        self.assertNotIn(attack, page)
        self.assertIn("\\u003c/script\\u003e", page)
        template = Path(dashboard.__file__).with_suffix(".html").read_text()
        self.assertIn("make('div', group.name, 'owner-name')", template)
        self.assertIn("make('div', group.owner, 'muted')", template)
        search = template[template.index("function filter()") :]
        self.assertIn("group.name", search)

    def test_closed_task_has_bounded_administrative_outcome_and_date(self):
        row = issue(1)
        row.update(
            status="closed",
            close_reason="Accepted ordinary source repair " + "c" * 600,
            closed_at=NOW.isoformat(),
        )
        ports = FakePorts([row])
        snapshot = self.snapshot(ports)
        view = snapshot["groups"][0]["issues"][0]
        self.assertEqual(view["close_reason"], row["close_reason"][:512])
        self.assertEqual(view["closed_at"], NOW.isoformat())
        self.assertEqual(view["jobs"], [])
        self.assertEqual(snapshot["counts"]["running_jobs"], 0)
        template = Path(dashboard.__file__).with_suffix(".html").read_text()
        self.assertIn("if (issue.status === 'closed')", template)
        self.assertIn("field(facts, 'Administrative closure', issue.close_reason)", template)
        self.assertIn("field(facts, 'Closed at (administrative)', issue.closed_at)", template)

    def test_closure_missing_injection_and_open_task_fields(self):
        row = issue(1)
        row.update(status="closed", notes="SECRET_CLOSURE_NOTES")
        view = self.snapshot(FakePorts([row]))["groups"][0]["issues"][0]
        self.assertEqual(
            (view["close_reason"], view["closed_at"]), ("Not supplied", "Not supplied")
        )
        row.update(
            close_reason="</script><script>globalThis.CLOSED=1</script>", closed_at="d" * 200
        )
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(len(snapshot["groups"][0]["issues"][0]["closed_at"]), 80)
        self.assertNotIn(row["close_reason"], dashboard.render(snapshot).decode())
        row["status"] = "open"
        view = self.snapshot(FakePorts([row]))["groups"][0]["issues"][0]
        self.assertEqual((view["close_reason"], view["closed_at"]), ("", ""))

    def test_publication_and_cleanup_failure_preserves_primary_exception(self):
        output = self.root / "index.html"
        output.write_bytes(b"previous")
        for action in ("fsync", "replace"):
            primary = OSError("original " + action + " EIO")
            cleanup = PermissionError("owned temporary unlink EPERM")
            with (
                patch.object(dashboard.os, action, side_effect=primary),
                patch.object(Path, "unlink", side_effect=cleanup),
            ):
                with self.assertRaises(OSError) as raised:
                    dashboard.publish(output, b"new")
            self.assertIs(raised.exception, primary)
            self.assertIn("unlink EPERM", primary.__notes__[0])
            self.assertEqual(output.read_bytes(), b"previous")
            leftovers = list(self.root.glob(".dashboard-*.tmp"))
            self.assertEqual(len(leftovers), 1)
            leftovers[0].unlink()

    def test_owner_groups_preserve_pause_and_multiple_issues(self):
        a = issue(1, stage="Preparation", next_action="Submit after checks")
        b = issue(323, stage="Paused", wait_kind="human_decision")
        b["labels"] = ["paused-by-user"]
        c = issue(3, owner=None, stage="Review")
        snapshot = self.snapshot(FakePorts([a, b, c]))
        self.assertEqual(len(snapshot["groups"]), 2)
        group = next(g for g in snapshot["groups"] if g["owner"] == OWNER)
        self.assertEqual(group["llm"], "active")
        self.assertTrue(group["issues"][1]["paused"])
        self.assertEqual(
            snapshot["counts"], {"running_jobs": 0, "waiting_issues": 1, "human_decisions": 1}
        )
        self.assertTrue(snapshot["generated_at"].endswith("+09:00"))

    def test_llm_idle_can_have_confirmed_running_job(self):
        row = issue(1, owner=IDLE)
        self.runtime(row)
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["groups"][0]["llm"], "idle")
        self.assertEqual(snapshot["counts"]["running_jobs"], 1)

    def test_llm_active_job_none_and_closed_no_wait(self):
        row = issue(1, wait_kind="human_decision", wait_reason="Old question")
        row["status"] = "closed"
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["groups"][0]["llm"], "active")
        self.assertEqual(
            snapshot["counts"], {"running_jobs": 0, "waiting_issues": 0, "human_decisions": 0}
        )

    def test_dependency_hydration_includes_non_dashboard_target(self):
        row = issue(1)
        row["dependencies"] = [
            {"depends_on_id": "demo-2", "type": "blocks"},
            {"depends_on_id": "demo-3", "type": "parent-child"},
        ]
        ports = FakePorts([row])
        ports.deps = [
            {"id": "demo-2", "status": "open", "title": "Dependency"},
            {"id": "demo-3", "status": "open"},
        ]
        snapshot = self.snapshot(ports)
        self.assertTrue(snapshot["groups"][0]["issues"][0]["waiting"])
        self.assertEqual(snapshot["counts"]["human_decisions"], 0)
        ports.deps[0]["status"] = "closed"
        self.assertFalse(self.snapshot(ports)["groups"][0]["issues"][0]["waiting"])

    def test_missing_dependency_is_fatal(self):
        row = issue(1)
        row["dependencies"] = [{"depends_on_id": "demo-2", "type": "blocks"}]
        with self.assertRaises(dashboard.CollectionError):
            self.snapshot(FakePorts([row]))

    def test_reused_pid_stale_runtime_missing_identity(self):
        row = issue(1)
        directory = self.runtime(row)
        ports = FakePorts([row])
        ports.matches = [False]
        snapshot = self.snapshot(ports)
        self.assertEqual(snapshot["counts"]["running_jobs"], 0)
        self.assertEqual(snapshot["groups"][0]["issues"][0]["jobs"][0]["status"], "recovery needed")
        state = json.loads((directory / "state.json").read_text())
        del state["child"]
        (directory / "state.json").write_text(json.dumps(state))
        ports.calls.clear()
        self.snapshot(ports)
        self.assertFalse(any(isinstance(c, tuple) and c[0] == "identities" for c in ports.calls))

    def test_missing_result_finished_is_unconfirmed(self):
        row = issue(1)
        self.runtime(row, phase="finished")
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["groups"][0]["issues"][0]["jobs"][0]["status"], "unconfirmed")

    def test_cleanup_unknown_never_finished_success(self):
        for result in (
            {"job_id": "job-1", "outcome": "succeeded", "exit_code": 0},
            {"job_id": "job-1", "outcome": "succeeded", "exit_code": 0, "cleanup_complete": True},
        ):
            view = dashboard.job_view(
                "/named", {"phase": "finished", "job_id": "job-1"}, result, NOW.isoformat(), False
            )
            self.assertEqual(view["status"], "recovery needed")
            self.assertIn("Scientific success is not qualified", view["result"])

    def test_complete_controller_result_and_failure(self):
        result = {
            "job_id": "job-1",
            "outcome": "succeeded",
            "exit_code": 0,
            "cleanup_complete": True,
            "direct_child_reaped": True,
            "remaining": [],
            "cleanup_errors": [],
        }
        view = dashboard.job_view(
            "/named", {"phase": "finished", "job_id": "job-1"}, result, NOW.isoformat(), False
        )
        self.assertEqual(view["status"], "command finished")
        result.update(outcome="failed", exit_code=2)
        self.assertEqual(
            dashboard.job_view(
                "/named", {"phase": "finished", "job_id": "job-1"}, result, NOW.isoformat(), False
            )["status"],
            "command failed",
        )
        result["cleanup_errors"] = [{"message": "SECRET_LOG"}]
        self.assertEqual(
            dashboard.job_view(
                "/named", {"phase": "finished", "job_id": "job-1"}, result, NOW.isoformat(), False
            )["status"],
            "recovery needed",
        )

    def test_mismatching_result_not_replayed(self):
        row = issue(1)
        self.runtime(row, phase="finished", result={"job_id": "old-job", "cleanup_complete": True})
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["groups"][0]["issues"][0]["jobs"][0]["status"], "unconfirmed")

    def test_runtime_session_identity_must_match_owner(self):
        row = issue(1)
        self.runtime(row, thread_id=IDLE[6:])
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["counts"]["running_jobs"], 0)
        self.assertEqual(snapshot["groups"][0]["issues"][0]["jobs"][0]["status"], "unavailable")

    def test_historical_result_remains_visible_after_issue_reassignment(self):
        row = issue(1)
        self.runtime(
            row,
            phase="finished",
            thread_id=IDLE[6:],
            result={
                "job_id": "job-1",
                "outcome": "failed",
                "exit_code": 1,
                "cleanup_complete": True,
                "direct_child_reaped": True,
            },
        )
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["groups"][0]["issues"][0]["jobs"][0]["status"], "command failed")
        self.assertEqual(snapshot["counts"]["running_jobs"], 0)

    def test_thread_malformed_and_notloaded_are_distinct(self):
        row = issue(1)
        ports = FakePorts([row])
        ports.statuses[OWNER[6:]] = "notLoaded"
        self.assertEqual(self.snapshot(ports)["groups"][0]["llm"], "notLoaded")
        with patch.object(
            ports, "thread", return_value={"thread": {"id": "wrong", "status": {"type": "idle"}}}
        ):
            self.assertEqual(self.snapshot(ports)["groups"][0]["llm"], "unavailable")

    def test_runtime_root_malformed_metadata_visible(self):
        row = issue(1, runtime_dirs=[1])
        snapshot = self.snapshot(FakePorts([row]))
        self.assertIn("runtime unavailable", snapshot["warnings"][0])

    def test_no_remote_operations_in_template_and_cli_failure(self):
        template = Path(dashboard.__file__).with_suffix(".html").read_text()
        for forbidden in (
            "fetch(",
            "XMLHttpRequest",
            "WebSocket(",
            "setInterval(",
            "<link",
            "src=",
            "innerHTML",
        ):
            self.assertNotIn(forbidden, template)
        self.assertIn("location.reload()", template)
        self.assertIn("connect-src 'none'", template)
        with (
            patch.object(dashboard, "generate", side_effect=dashboard.CollectionError("secret")),
            patch.object(dashboard.sys, "stderr"),
        ):
            self.assertEqual(dashboard.main(["--root", str(self.root)]), 1)

    def test_offline_unknown_and_runtime_port_failure_no_cache(self):
        row = issue(1)
        self.runtime(row)
        ports = FakePorts([row])
        self.assertEqual(self.snapshot(ports)["counts"]["running_jobs"], 1)
        ports.matches = dashboard.CollectionError("unavailable")
        ports.statuses[OWNER[6:]] = dashboard.CollectionError("offline")
        snapshot = self.snapshot(ports)
        self.assertEqual(snapshot["groups"][0]["llm"], "unavailable")
        self.assertEqual(snapshot["counts"]["running_jobs"], 0)
        self.assertEqual(len(snapshot["warnings"]), 2)

    def test_missing_metadata_does_not_infer_from_notes(self):
        row = issue(1)
        row["metadata"] = {}
        row["notes"] = "SECRET_NOTES running Human decision"
        row["description"] = "SECRET_PROMPT"
        snapshot = self.snapshot(FakePorts([row]))
        view = snapshot["groups"][0]["issues"][0]
        self.assertEqual(view["stage"], "Not supplied")
        self.assertEqual(snapshot["counts"]["human_decisions"], 0)
        self.assertNotIn("SECRET", dashboard.render(snapshot).decode())

    def test_malicious_html_json_and_evidence_paths_are_data(self):
        attack = '</script><script>globalThis.INJECTED=1</script><img src="https://evil/">&\u2028'
        row = issue(1, stage=attack, evidence_paths=["/tmp/" + attack, "javascript:alert(1)"])
        row["title"] = attack
        snapshot = self.snapshot(FakePorts([row]))
        encoded = dashboard.render(snapshot).decode()
        self.assertNotIn(attack, encoded)
        self.assertIn("\\u003c/script\\u003e", encoded)
        self.assertEqual(snapshot["groups"][0]["issues"][0]["evidence_paths"], ["/tmp/" + attack])
        self.assertEqual(encoded.count('type="application/json"'), 1)

    def test_html_parser_sees_no_injected_elements_or_external_resources(self):
        class Tags(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []

            def handle_starttag(self, tag, attrs):
                self.tags.append((tag, dict(attrs)))

        row = issue(1, stage='</script><img src="https://evil.invalid/">')
        page = dashboard.render(self.snapshot(FakePorts([row]))).decode()
        parser = Tags()
        parser.feed(page)
        self.assertEqual(sum(tag == "script" for tag, _ in parser.tags), 2)
        self.assertFalse(any(tag in {"img", "iframe", "link"} for tag, _ in parser.tags))
        self.assertFalse(any("src" in attrs or "href" in attrs for _, attrs in parser.tags))
        ids = {attrs.get("id") for _, attrs in parser.tags}
        self.assertTrue({"search", "waiting", "reload", "owners", "snapshot"}.issubset(ids))

    def test_runtime_names_only_symlink_and_size_guard(self):
        row = issue(1)
        directory = self.runtime(row)
        (directory / "state.json").unlink()
        secret = self.root / "auth.json"
        secret.write_text('{"secret":"DO_NOT_READ"}')
        (directory / "state.json").symlink_to(secret)
        snapshot = self.snapshot(FakePorts([row]))
        self.assertEqual(snapshot["groups"][0]["issues"][0]["jobs"][0]["status"], "unavailable")
        self.assertNotIn("DO_NOT_READ", dashboard.render(snapshot).decode())
        (directory / "state.json").unlink()
        (directory / "state.json").write_bytes(b"x" * (dashboard.RUNTIME_BYTES + 1))
        with self.assertRaises(dashboard.CollectionError):
            dashboard.read_json(directory / "state.json")

    def test_atomic_collection_failure_preserves_previous(self):
        output = self.root / "index.html"
        output.write_bytes(b"previous")
        for malformed in ({"error": "unavailable"}, [None], [issue(1), issue(1)]):
            ports = FakePorts(malformed)
            with self.assertRaises(dashboard.CollectionError):
                dashboard.generate(ports, output)
            self.assertEqual(output.read_bytes(), b"previous")

    def test_atomic_publish_failure_and_size_cleanup(self):
        output = self.root / "index.html"
        output.write_bytes(b"previous")
        with patch.object(dashboard.os, "replace", side_effect=OSError("EIO")):
            with self.assertRaises(OSError):
                dashboard.publish(output, b"new")
        self.assertEqual(output.read_bytes(), b"previous")
        self.assertEqual(list(self.root.glob(".dashboard-*.tmp")), [])
        with self.assertRaises(dashboard.CollectionError):
            dashboard.publish(output, b"x" * (dashboard.HTML_BYTES + 1))
        dashboard.publish(output, b"new")
        self.assertEqual(output.read_bytes(), b"new")

    def test_read_port_timeout_nonzero_and_output_bound_direct_wait(self):
        for code in ("import time; time.sleep(2)", "raise SystemExit(2)", "print('x'*1048577)"):
            with self.assertRaises(dashboard.CollectionError):
                dashboard.command_json(
                    [sys.executable, "-B", "-c", code], cwd=self.root, seconds=0.2
                )
        self.assertEqual(
            dashboard.command_json(
                [sys.executable, "-B", "-c", 'print("[]")'], cwd=self.root, seconds=1
            ),
            [],
        )

    def test_port_arguments_readonly_wrapper_and_status_only(self):
        ports = dashboard.Ports(self.root)
        responses = [[], [], {"thread": {}}, [False]]
        with patch.object(dashboard, "command_json", side_effect=responses) as call:
            ports.issues()
            ports.dependencies(["demo-1"])
            ports.thread(OWNER[6:])
            ports.identities([IDENTITY])
        commands = [args.args[0] for args in call.call_args_list]
        self.assertIn("--brief", commands[0])
        self.assertIn("--max-rows", commands[0])
        self.assertIn("beads.sh", commands[0][1])
        self.assertIn("research-session.sh", commands[2][1])
        self.assertEqual(commands[2][2:4], ["status", "--thread"])
        self.assertFalse(
            any(
                value in {"send", "create", "resume", "archive", "submit", "run"}
                for command in commands
                for value in command
            )
        )

    def test_preparing_invalid_runtime_issue_and_malformed_json(self):
        row = issue(1)
        directory = self.runtime(row, phase="queued")
        self.assertEqual(
            self.snapshot(FakePorts([row]))["groups"][0]["issues"][0]["jobs"][0]["status"],
            "preparing",
        )
        (directory / "state.json").write_text('{"issue":"other","job_id":"job-1"}')
        self.assertEqual(
            self.snapshot(FakePorts([row]))["groups"][0]["issues"][0]["jobs"][0]["status"],
            "unavailable",
        )
        (directory / "state.json").write_text("invalid")
        self.assertEqual(self.snapshot(FakePorts([row]))["counts"]["running_jobs"], 0)


if __name__ == "__main__":
    unittest.main()
