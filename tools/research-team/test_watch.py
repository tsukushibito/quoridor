"""Read/ownership/record contracts; no real scheduler or App Server is started."""

import importlib.util
import contextlib
import io
from types import SimpleNamespace
import json
import signal
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location(
    "watch", Path(__file__).resolve().parents[2] / "scripts/dev/research-watch.py"
)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class WatchTests(unittest.TestCase):
    def test_overlap_hardlink_allocation(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            a = root / "a"
            a.write_bytes(b"x" * 5000)
            (root / "b").hardlink_to(a)
            self.assertEqual(
                w.allocated([root, a]), root.stat().st_blocks * 512 + a.stat().st_blocks * 512
            )

    def test_selection_keeps_overflow_source_hash_without_copying_history(self):
        item = {"id": "x", "notes": "n" * 100000, "description": "d" * 10000}
        result = w.select_issue(item)
        self.assertTrue(result["notes"]["overflow"])
        self.assertEqual(len(result["notes"]["tail"]), 1024)
        self.assertEqual(result["notes"]["source_bytes"], 100000)
        self.assertTrue(result["description"]["overflow"])
        self.assertEqual(len(result["description"]["text"]), 3072)

    def test_nested_dependencies_do_not_copy_parent_notes(self):
        dependency = {"id": "quoridor-4lc", "status": "in_progress", "notes": "n" * 330000}
        selected = w.select_issue({"id": "quoridor-4lc.40", "dependencies": [dependency] * 20})
        relation = selected["dependencies"]
        self.assertEqual(relation["source_count"], 20)
        self.assertEqual(relation["omitted_count"], 4)
        self.assertGreater(relation["source_bytes"], 330000)
        self.assertNotIn("notes", relation["items"][0])
        self.assertLess(len(json.dumps(selected).encode()), 8192)

    def test_unknown_state_cap_or_binding_rejected(self):
        with tempfile.TemporaryDirectory() as name, patch.object(w.time, "sleep"):
            root = Path(name)
            expected = {
                "state_dir": name,
                "binding": {"thread_id": "saved"},
                "process": {"pid": 123},
            }
            state = {
                "binding": expected["binding"],
                "phase": "running",
                "process": expected["process"],
                "owned": {"thread_id": "saved", "max_turn_seconds": None},
            }
            (root / "state.json").write_text(json.dumps(state))
            self.assertIsNone(w.state_read(expected)["owned"]["max_turn_seconds"])
            state["owned"]["max_turn_seconds"] = 180
            (root / "state.json").write_text(json.dumps(state))
            with self.assertRaises(w.Unavailable):
                w.state_read(expected)
            state["owned"] = None
            state["binding"] = {"thread_id": "other"}
            (root / "state.json").write_text(json.dumps(state))
            with self.assertRaises(w.Unavailable):
                w.state_read(expected)

    def test_record_cap_refuses_without_saving_pass(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaises(w.Unavailable):
                w.save_record(
                    root / "run" / "large.json",
                    {"supervisor_output": name},
                    {"data": "x" * w.RECORD_CAP},
                )
            self.assertFalse((root / "run" / "large.json").exists())
            receipt = json.loads((root / "run" / "large.refusal.json").read_text())
            self.assertGreater(receipt["requested_record_bytes"], w.RECORD_CAP)
            self.assertFalse(receipt["record_saved"])

    def test_unknown_or_other_identity_never_signalled(self):
        with (
            patch.object(w.scheduler, "alive", return_value=True),
            patch.object(w, "state_read", return_value={"process": {"pid": 456}}),
            patch.object(w, "capture") as capture,
        ):
            with self.assertRaises(w.Unavailable):
                w.stop_exact({"process": {"pid": 123}})
            capture.assert_not_called()

    def test_cumulative_command_cap_before_spawn(self):
        with (
            tempfile.TemporaryDirectory() as name,
            patch.object(w, "admit"),
            patch.object(w, "capture") as capture,
        ):
            root = Path(name)
            (root / "command-budget.json").write_text(json.dumps({"commands": 24}))
            expected = {
                "_output": str(root / "record.json"),
                "supervisor_forecast_bytes": 512 * 1024,
            }
            with self.assertRaises(w.Unavailable):
                w.wrapper(expected, ["ready", "--json"], [])
            capture.assert_not_called()

    def test_input_changed_before_admission(self):
        with tempfile.TemporaryDirectory() as name:
            p = Path(name) / "config"
            p.write_text("new")
            with self.assertRaises(w.Unavailable):
                w.check_inputs({"input_hashes": {str(p): "old"}})


class CaptureTests(unittest.TestCase):
    def run_capture(self, *, interruption=False, alive=True, waits=(0,)):
        child = MagicMock(pid=900001)
        child.poll.return_value = None
        child.wait.side_effect = list(waits)
        selector = MagicMock()
        selector.get_map.return_value = {"pipe": 1} if interruption else {}
        selector.select.side_effect = w.Unavailable("mock outer soft stop")
        receipts = []
        with (
            patch.object(w.subprocess, "Popen", return_value=child),
            patch.object(w.selectors, "DefaultSelector", return_value=selector),
            patch.object(
                w.scheduler,
                "process_identity",
                return_value={"pid": child.pid, "ticks": 1, "boot": "mock"},
            ),
            patch.object(w.scheduler, "alive", return_value=alive),
            patch.object(w.os, "killpg") as kill,
        ):
            if interruption:
                with self.assertRaises(w.Unavailable):
                    w.capture(
                        ["mock"], Path(__file__).resolve().parents[2], receipt=receipts.append
                    )
            else:
                w.capture(["mock"], Path(__file__).resolve().parents[2], receipt=receipts.append)
            signals = kill.call_args_list
        return receipts, signals

    def test_normal_completion_receipt(self):
        rows, signals = self.run_capture()
        self.assertEqual([r["phase"] for r in rows], ["started", "completed"])
        self.assertTrue(rows[-1]["child_reaped"])
        self.assertEqual(rows[-1]["exit_code"], 0)
        self.assertFalse(signals)
        self.assertFalse(rows[-1]["process_group_absence_certified"])

    def test_soft_interrupt_reaps_and_records_failure(self):
        rows, signals = self.run_capture(interruption=True, waits=(-15,))
        self.assertTrue(rows[-1]["child_reaped"])
        self.assertIn("capture_interrupted", rows[-1]["refusal"])
        self.assertEqual(signals[0].args, (900001, signal.SIGTERM))
        self.assertFalse(rows[-1]["streams"]["stdout"]["complete"])

    def test_unknown_identity_not_signalled_or_certified(self):
        expiry = subprocess.TimeoutExpired("mock", 3)
        rows, signals = self.run_capture(interruption=True, alive=False, waits=(expiry, expiry))
        self.assertFalse(signals)
        self.assertFalse(rows[-1]["child_reaped"])
        self.assertEqual(rows[-1]["recovery_error"], "TimeoutExpired")

    def test_bounded_escalation_requires_exact_identity(self):
        rows, signals = self.run_capture(
            interruption=True, waits=(subprocess.TimeoutExpired("mock", 3), -9)
        )
        self.assertEqual([c.args[1] for c in signals], [signal.SIGTERM, signal.SIGKILL])
        self.assertEqual(rows[-1]["exit_code"], -9)

    def test_receipt_cap_refusal_prevents_spawn(self):
        with (
            tempfile.TemporaryDirectory() as name,
            patch.object(w, "admit"),
            patch.object(w, "save_record", side_effect=w.Unavailable("cap")),
            patch.object(w, "capture") as spawn,
        ):
            expected = {
                "_output": str(Path(name) / "finish.json"),
                "supervisor_forecast_bytes": 512 * 1024,
                "root": str(Path(__file__).resolve().parents[2]),
                "deadlines": {"supervisor": "2099-01-01T00:00:00Z"},
            }
            with self.assertRaises(w.Unavailable):
                w.wrapper(expected, ["backup", "sync"], [], selection=False)
            spawn.assert_not_called()

    def test_each_command_receipt_survives_later_interruption(self):
        with tempfile.TemporaryDirectory() as name, patch.object(w, "admit"):
            expected = {
                "_output": str(Path(name) / "run" / "finish.json"),
                "supervisor_output": name,
                "supervisor_forecast_bytes": 512 * 1024,
                "root": str(Path(__file__).resolve().parents[2]),
                "deadlines": {"supervisor": "2099-01-01T00:00:00Z"},
            }

            def mock_capture(_argv, _root, *, timeout, receipt):
                receipt({"phase": "started", "child_reaped": False})
                if "second" in _argv:
                    raise w.Unavailable("mock hard stop before completed receipt")
                meta = {"phase": "completed", "exit_code": 0, "refusal": None, "child_reaped": True}
                receipt(meta)
                return {"stdout": "ok", "stderr": ""}, meta

            with patch.object(w, "capture", side_effect=mock_capture):
                w.wrapper(expected, ["first"], [], selection=False)
                with self.assertRaises(w.Unavailable):
                    w.wrapper(expected, ["second"], [], selection=False)
            import json

            first = json.loads((Path(name) / "run/command-01-child.json").read_text())
            second = json.loads((Path(name) / "run/command-02-child.json").read_text())
            self.assertTrue(first["child_reaped"])
            self.assertFalse(second["child_reaped"])
            self.assertNotIn("stdout", first)

    def test_cumulative_capture_exhaustion_never_spawns(self):
        budget = w.FinishBudget(0)
        with (
            patch.object(w.time, "monotonic", return_value=16),
            patch.object(w.subprocess, "Popen") as spawn,
        ):
            with self.assertRaises(w.Unavailable):
                w.capture(["mock"], ".", budget=budget)
            spawn.assert_not_called()

    def test_reap_waits_do_not_reset_cumulative_remaining(self):
        child = MagicMock(pid=900001)
        child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired("mock", 0), -9]
        selector = MagicMock()
        selector.get_map.return_value = {"pipe": 1}
        now = [0.0]
        budget = w.FinishBudget(0)

        def interrupt(*_):
            now[0] = 22
            raise w.Unavailable("mock late soft stop")

        selector.select.side_effect = interrupt
        receipts = []
        with (
            patch.object(w.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(w.subprocess, "Popen", return_value=child),
            patch.object(w.selectors, "DefaultSelector", return_value=selector),
            patch.object(w.scheduler, "process_identity", return_value={"pid": child.pid}),
            patch.object(w.scheduler, "alive", return_value=True),
            patch.object(w.os, "killpg"),
        ):
            with self.assertRaises(w.Unavailable):
                w.capture(["mock"], ".", budget=budget, receipt=receipts.append)
        self.assertEqual([c.kwargs["timeout"] for c in child.wait.call_args_list], [0, 0])
        self.assertTrue(receipts[-1]["child_reaped"])
        self.assertFalse(receipts[-1]["process_group_absence_certified"])


class FinishTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, *, notes="bounded", items=None, duration=0, admit_duration=0):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            registry = root / "registry.json"
            registry.write_text(json.dumps({"roles": {"coordinator": {"thread_id": "coord"}}}))
            note = root / "notes.txt"
            note.write_text(notes)
            output = root / "run" / "finish.json"
            expected = {
                "root": name,
                "_output": str(output),
                "supervisor_output": name,
                "supervisor_forecast_bytes": 512 * 1024,
                "deadlines": {"supervisor": "2099-01-01T00:00:00Z"},
                "binding": {"thread_id": "saved", "registry": str(registry)},
            }
            args = SimpleNamespace(command="finish", output=str(output), notes_file=str(note))
            state = {"owned": {"run_id": "run"}}
            current = [0.0]
            calls = []
            items = (
                items
                if items is not None
                else [
                    {
                        "id": "quoridor-4lc",
                        "status": "in_progress",
                        "assignee": "codex:coord",
                        "labels": [],
                    },
                    {
                        "id": "quoridor-4lc.40",
                        "status": "in_progress",
                        "assignee": "codex:saved",
                        "labels": [],
                    },
                ]
            )

            def admit(*_args, **_kwargs):
                current[0] += admit_duration
                return state

            def capture(argv, _root, *, timeout, receipt, budget):
                calls.append({"args": argv[2:], "timeout": timeout})
                receipt({"phase": "started", "child_reaped": False})
                current[0] += duration
                meta = {"phase": "completed", "exit_code": 0, "refusal": None, "child_reaped": True}
                receipt(meta)
                text = json.dumps(items) if argv[2] == "show" else "ok"
                return {"stdout": text, "stderr": ""}, meta

            with (
                patch.object(w, "PROCESS_STARTED", 0),
                patch.object(w.time, "monotonic", side_effect=lambda: current[0]),
                patch.object(w, "admit", side_effect=admit),
                patch.object(w, "capture", side_effect=capture),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                yield args, expected, calls, current

    def test_finish_authenticates_one_batch_and_preserves_conditional_order(self):
        with self.fixture() as (args, expected, calls, _):
            self.assertEqual(w.observer(args, expected), 0)
            self.assertEqual([x["args"][0] for x in calls], ["show", "update", "backup"])
            self.assertEqual(
                calls[0]["args"],
                ["show", "quoridor-4lc", "quoridor-4lc.40", "--json", "--brief-deps"],
            )
            self.assertIn("--if-assignee", calls[1]["args"])
            self.assertIn("--if-status", calls[1]["args"])
            result = json.loads(Path(args.output).read_text())
            self.assertEqual(result["finish"]["append"], "completed")
            self.assertEqual(result["finish"]["backup"], "completed")
            self.assertFalse(result["cumulative_budget"]["whole_outer_success_certified"])

    def test_notes_cap_refuses_before_any_read_admission_or_child(self):
        with self.fixture(notes="x" * 1025) as (args, expected, calls, _):
            self.assertEqual(w.observer(args, expected), 2)
            self.assertEqual(calls, [])
            self.assertEqual(
                json.loads(Path(args.output).with_name("finish-backup.json").read_text())["backup"],
                "not_reached",
            )
            w.admit.assert_not_called()

    def test_malformed_ids_status_owner_and_pause_never_append(self):
        good = [
            {
                "id": "quoridor-4lc",
                "status": "in_progress",
                "assignee": "codex:coord",
                "labels": [],
            },
            {
                "id": "quoridor-4lc.40",
                "status": "in_progress",
                "assignee": "codex:saved",
                "labels": [],
            },
        ]
        variants = [[good[0]], [good[1], good[1]], [good[0], {**good[1], "id": "foreign"}]]
        for index, field, value in [
            (0, "assignee", "foreign"),
            (1, "assignee", "foreign"),
            (1, "status", "open"),
            (0, "status", "closed"),
            (1, "labels", ["paused-by-user"]),
            (0, "labels", "malformed"),
        ]:
            rows = [dict(x) for x in good]
            rows[index][field] = value
            variants.append(rows)
        for rows in variants:
            with self.subTest(rows=rows), self.fixture(items=rows) as (args, expected, calls, _):
                self.assertEqual(w.observer(args, expected), 2)
                self.assertEqual([x["args"][0] for x in calls], ["show"])

    def test_admission_and_storage_time_consume_same_budget_before_spawn(self):
        with self.fixture(admit_duration=8) as (args, expected, calls, _):
            self.assertEqual(w.observer(args, expected), 2)
            self.assertEqual(calls, [])
            self.assertIn(
                "cumulative remaining", json.loads(Path(args.output).read_text())["reason"]
            )

    def test_each_timeout_shrinks_and_backup_not_reached_is_recorded(self):
        with self.fixture(duration=8) as (args, expected, calls, _):
            self.assertEqual(w.observer(args, expected), 2)
            self.assertEqual([x["args"][0] for x in calls], ["show", "update"])
            self.assertEqual([x["timeout"] for x in calls], [15, 7])
            separate = json.loads(Path(args.output).with_name("finish-backup.json").read_text())
            self.assertEqual(separate["backup"], "not_reached")
            self.assertFalse(separate["whole_finish_observed"])

    def test_unknown_append_outcome_prevents_duplicate_retry(self):
        with self.fixture() as (args, expected, calls, _):
            original = w.capture.side_effect

            def fail_append(argv, root, **kwargs):
                if argv[2] == "update":
                    kwargs["receipt"]({"phase": "started", "child_reaped": False})
                    raise w.Unavailable("communication outcome unknown")
                return original(argv, root, **kwargs)

            w.capture.side_effect = fail_append
            self.assertEqual(w.observer(args, expected), 2)
            before = w.capture.call_count
            self.assertEqual(w.observer(args, expected), 2)
            self.assertEqual(w.capture.call_count, before)
            result = json.loads(Path(args.output).read_text())
            self.assertIn("previous append outcome unknown", result["reason"])

    def test_confirmed_append_also_never_duplicates_on_repeat(self):
        with self.fixture() as (args, expected, calls, _):
            self.assertEqual(w.observer(args, expected), 0)
            before = w.capture.call_count
            self.assertEqual(w.observer(args, expected), 2)
            self.assertEqual(w.capture.call_count, before)
            self.assertIn(
                "previous append outcome confirmed",
                json.loads(Path(args.output).read_text())["reason"],
            )

    def test_owned_change_in_wrapper_prevents_spawn(self):
        with self.fixture() as (args, expected, calls, _):
            w.admit.side_effect = [{"owned": {"run_id": "run"}}, {"owned": {"run_id": "other"}}]
            self.assertEqual(w.observer(args, expected), 2)
            self.assertEqual(calls, [])

    def test_original_backup_failure_remains_uncertain_not_whole_finish_success(self):
        with self.fixture() as (args, expected, calls, _):
            original = w.capture.side_effect

            def fail_backup(argv, root, **kwargs):
                if argv[2] == "backup":
                    kwargs["receipt"]({"phase": "started", "child_reaped": False})
                    raise w.Unavailable("backup communication unknown")
                return original(argv, root, **kwargs)

            w.capture.side_effect = fail_backup
            self.assertEqual(w.observer(args, expected), 2)
            separate = json.loads(Path(args.output).with_name("finish-backup.json").read_text())
            self.assertEqual(separate["append"], "completed")
            self.assertIn("unknown", separate["backup"])
            self.assertFalse(separate["whole_finish_observed"])

    def test_recording_overrun_cannot_leave_observed_result(self):
        with self.fixture() as (args, expected, _calls, clock):
            original = w.save_record

            def delayed(path, exp, value):
                original(path, exp, value)
                if Path(path).name == "finish.json":
                    clock[0] += 30

            with patch.object(w, "save_record", side_effect=delayed):
                self.assertEqual(w.observer(args, expected), 2)
            result = json.loads(Path(args.output).read_text())
            self.assertEqual(result["status"], "unavailable")
            self.assertIn("recording exceeded", result["reason"])


if __name__ == "__main__":
    unittest.main()
