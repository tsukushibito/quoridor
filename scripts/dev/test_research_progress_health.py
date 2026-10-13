"""Bounded local tests for progress-health evidence, timing and timer ownership."""

import asyncio
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("research-progress-health.py")
SPEC = importlib.util.spec_from_file_location("research_progress_health", SCRIPT)
health = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health)
dashboard = health.dashboard_module()
OWNER = "codex:01a1153d-7900-7740-837f-c300ca54764f"
NOW = datetime(2026, 10, 9, 4, 0, tzinfo=timezone.utc)


def fixture(
    *, status="in_progress", llm="idle", wait="none", jobs=None, labels=None, metadata=None
):
    ident = "quoridor-4lc.400"
    info = {
        "stage": "Authorized finite source work",
        "next_action": "Continue source",
        "wait_kind": wait,
    }
    if metadata:
        info.update(metadata)
    row = {
        "id": ident,
        "status": status,
        "assignee": OWNER,
        "updated_at": "2026-10-09T03:00:00Z",
        "labels": labels or ["dashboard"],
        "metadata": {"dashboard": info},
        "dependencies": [],
    }
    issue = {
        "id": ident,
        "status": status,
        "paused": "paused-by-user" in (labels or []),
        "waiting": wait != "none",
        "jobs": jobs or [],
        "dependencies": [],
    }
    return {"groups": [{"owner": OWNER, "llm": llm, "issues": [issue]}]}, {ident: row}


class ClassificationTests(unittest.TestCase):
    def classify(self, snapshot, rows):
        return health.candidates(snapshot, rows, dashboard)

    def test_normal_wait_pause_human_running_and_active_llm_are_quiet(self):
        for kwargs in (
            {"wait": "review"},
            {"wait": "human_decision"},
            {"status": "deferred"},
            {"labels": ["dashboard", "paused-by-user"]},
            {"jobs": [{"status": "running"}]},
            {"llm": "active", "metadata": {"health": {"authorized_active": True}}},
        ):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.classify(*fixture(**kwargs))[0], [])

    def test_idle_llm_alone_not_source_or_science_stall(self):
        self.assertEqual(self.classify(*fixture(metadata={"next_action": ""}))[0], [])
        snapshot, rows = fixture()
        found, _ = self.classify(snapshot, rows)
        self.assertEqual([item["kind"] for item in found], ["authorized_idle_no_job"])
        self.assertFalse(found[0]["immediate"])

    def test_unrelated_closed_review_not_dependency_proof(self):
        snapshot, rows = fixture(wait="review")
        rows["quoridor-4lc.999"] = {"id": "quoridor-4lc.999", "status": "closed"}
        self.assertEqual(self.classify(snapshot, rows)[0], [])

    def test_matching_stopped_reader_and_closed_target_only(self):
        target = "quoridor-4lc.401"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reader-stop.json"
            receipt = {
                "target_issue": target,
                "consumer_issue": "quoridor-4lc.400",
                "reviewer_owner": OWNER,
                "target_issue_version": "2026-10-09T02:00:00Z",
                "target_source_sha256": "a" * 64,
                "reader_stop_at": NOW.isoformat(),
                "reader_status": "STOP",
                "remaining": [],
            }
            path.write_text(json.dumps(receipt))
            snapshot, rows = fixture(
                wait="review",
                metadata={
                    "evidence_paths": [str(path)],
                    "health": {
                        "dependency_target_issue": target,
                        "reader_stop_receipt": str(path),
                        "target_source_sha256": "a" * 64,
                    },
                },
            )
            rows[target] = {
                "id": target,
                "status": "closed",
                "assignee": OWNER,
                "updated_at": "2026-10-09T02:00:00Z",
            }
            found, _ = self.classify(snapshot, rows)
            self.assertEqual(
                [(x["kind"], x["immediate"]) for x in found], [("completed_dependency_idle", True)]
            )
            rows[target]["assignee"] = "codex:someone-else"
            self.assertEqual(self.classify(snapshot, rows)[0], [])
            rows[target]["assignee"] = OWNER
            receipt["consumer_issue"] = "quoridor-4lc.other"
            path.write_text(json.dumps(receipt))
            self.assertEqual(self.classify(snapshot, rows)[0], [])
            receipt["consumer_issue"] = "quoridor-4lc.400"
            receipt["remaining"] = [123]
            path.write_text(json.dumps(receipt))
            self.assertEqual(self.classify(snapshot, rows)[0], [])

    def test_current_directed_review_controls_without_health_registry(self):
        reviewer = "quoridor-4lc.400.1"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target_path = directory / "source-stop.json"
            control_path = directory / "review-control.json"
            target = {
                "issue": "quoridor-4lc.400",
                "source_reader_STOP": NOW.isoformat(),
                "remaining_readers": [],
                "remaining_children": [],
                "TMP": [],
            }
            target_path.write_text(json.dumps(target))
            target_sha = hashlib.sha256(target_path.read_bytes()).hexdigest()
            control = {
                "issue": reviewer,
                "target_SHA256": target_sha,
                "reader_source_STOP": NOW.isoformat(),
                "owned_readers_children_jobs_TMP_remaining": [],
                "source_clear": True,
                "blockers": [],
            }
            control_path.write_text(json.dumps(control))
            snapshot, rows = fixture(
                wait="source_review", metadata={"evidence_paths": [str(target_path)]}
            )
            rows[reviewer] = {
                "id": reviewer,
                "status": "closed",
                "assignee": "codex:reviewer-thread",
                "metadata": {"dashboard": {"evidence_paths": [str(control_path)]}},
                "dependencies": [{"depends_on_id": "quoridor-4lc.400", "type": "parent-child"}],
            }
            found, _ = self.classify(snapshot, rows)
            self.assertEqual([x["kind"] for x in found], ["completed_dependency_idle"])
            self.assertTrue(found[0]["immediate"])
            self.assertEqual(found[0]["reference"], str(control_path))

            control["source_clear"] = False
            control["blockers"] = [{"code": "BLOCKED_SOURCE"}]
            control_path.write_text(json.dumps(control))
            found, _ = self.classify(snapshot, rows)
            self.assertEqual([x["kind"] for x in found], ["blocked_source_review_idle"])

            control["target_SHA256"] = "b" * 64  # stale closed reviewer, not current target
            control_path.write_text(json.dumps(control))
            self.assertEqual(self.classify(snapshot, rows)[0], [])

    def test_sigma_alias_and_missing_stopped_target_remain_conservative(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target_path = directory / "binding.json"
            control_path = directory / "completion-control.json"
            target = {
                "issue": "quoridor-4lc.400",
                "reader_substantial_STOP": NOW.isoformat(),
                "remaining_readers_writers_children_pending_direct_waits_cleanup_TMP": [],
            }
            target_path.write_text(json.dumps(target))
            target_sha = hashlib.sha256(target_path.read_bytes()).hexdigest()
            control_path.write_text(
                json.dumps(
                    {
                        "issue": "quoridor-4lc.400.2",
                        "target_binding_SHA256": target_sha,
                        "source_reader_STOP": NOW.isoformat(),
                        "remaining_readers_writers_children_pending_direct_waits_cleanup_TMP": [],
                        "control_clear": True,
                    }
                )
            )
            snapshot, rows = fixture(
                wait="dependency", metadata={"evidence_paths": [str(target_path)]}
            )
            rows["quoridor-4lc.400.2"] = {
                "id": "quoridor-4lc.400.2",
                "status": "closed",
                "assignee": "codex:reviewer",
                "metadata": {"dashboard": {"evidence_paths": [str(control_path)]}},
                "dependencies": [{"depends_on_id": "quoridor-4lc.400", "type": "parent-child"}],
            }
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]],
                ["completed_dependency_idle"],
            )
            target["remaining_readers_writers_children_pending_direct_waits_cleanup_TMP"] = [
                "reader"
            ]
            target_path.write_text(json.dumps(target))
            self.assertEqual(self.classify(snapshot, rows)[0], [])

    def test_sigma_sibling_review_integer_blockers_and_declared_review_issue(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target_path = directory / "source-review-target.json"
            control_path = directory / "completion-control.json"
            parent = "quoridor-4lc.999"
            reviewer = "quoridor-4lc.400.5"
            target = {
                "issue": "quoridor-4lc.400",
                "review_issue": reviewer,
                "source_reader_writer_STOP": NOW.isoformat(),
                "owned_readers_children_jobs_TMP_remaining": [],
            }
            target_path.write_text(json.dumps(target))
            control = {
                "issue": reviewer,
                "target_binding_SHA256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
                "source_reader_STOP": NOW.isoformat(),
                "remaining_readers_writers_children_pending_direct_waits_cleanup_TMP": [],
                "blockers": 0,
                "control_clear": True,
            }
            control_path.write_text(json.dumps(control))
            snapshot, rows = fixture(
                wait="source_review", metadata={"evidence_paths": [str(target_path)]}
            )
            rows[parent] = {"id": parent, "status": "open", "labels": [], "dependencies": []}
            rows["quoridor-4lc.400"]["dependencies"] = [
                {"depends_on_id": parent, "type": "parent-child"}
            ]
            rows[reviewer] = {
                "id": reviewer,
                "status": "closed",
                "assignee": "codex:reviewer-thread",
                "metadata": {"dashboard": {"evidence_paths": [str(control_path)]}},
                "dependencies": [{"depends_on_id": parent, "type": "parent-child"}],
            }
            found, _ = self.classify(snapshot, rows)
            self.assertEqual([x["kind"] for x in found], ["completed_dependency_idle"])
            old_path = directory / "old-stopped-target.json"
            old_path.write_text(json.dumps({**target, "version": "old"}))
            rows["quoridor-4lc.400"]["metadata"]["dashboard"]["evidence_paths"].append(
                str(old_path)
            )
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]],
                ["completed_dependency_idle"],
            )  # exact control SHA selects one target
            control["target_path"] = str(old_path)
            control_path.write_text(json.dumps(control))
            self.assertEqual(self.classify(snapshot, rows)[0], [])
            control["target_path"] = str(target_path)
            control_path.write_text(json.dumps(control))
            for invalid_blockers in (True, -1):
                control["blockers"] = invalid_blockers
                control_path.write_text(json.dumps(control))
                self.assertEqual(self.classify(snapshot, rows)[0], [])
            control["blockers"] = 1
            control_path.write_text(json.dumps(control))
            self.assertEqual(self.classify(snapshot, rows)[0], [])  # no false clear
            control["control_clear"] = False
            control_path.write_text(json.dumps(control))
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]],
                ["blocked_source_review_idle"],
            )
            target["review_issue"] = "quoridor-4lc.400.6"
            target_path.write_text(json.dumps(target))
            control["target_binding_SHA256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
            control_path.write_text(json.dumps(control))
            self.assertEqual(self.classify(snapshot, rows)[0], [])
            target.pop("review_issue")
            target_path.write_text(json.dumps(target))
            control["target_binding_SHA256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
            control["blockers"] = 0
            control["control_clear"] = True
            control_path.write_text(json.dumps(control))
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]],
                ["completed_dependency_idle"],
            )
            rows[reviewer]["dependencies"] = [
                {"depends_on_id": "quoridor-4lc.998", "type": "parent-child"}
            ]
            self.assertEqual(self.classify(snapshot, rows)[0], [])

    def test_compact_tt_stop_aliases_and_unrelated_closed_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target_path = directory / "binding-stop.json"
            control_path = directory / "control.json"
            reviewer = "quoridor-4lc.400.2"
            snapshot, rows = fixture(wait="review", metadata={"evidence_paths": [str(target_path)]})
            rows[reviewer] = {
                "id": reviewer,
                "status": "closed",
                "assignee": "codex:reviewer-thread",
                "metadata": {"dashboard": {"evidence_paths": [str(control_path)]}},
                "dependencies": [{"depends_on_id": "quoridor-4lc.400", "type": "parent-child"}],
            }
            for stop_key in (
                "source_reader_writer_STOP",
                "source_reader_writerSTOP",
                "source_STOP",
            ):
                target = {
                    "issue": "quoridor-4lc.400",
                    stop_key: NOW.isoformat(),
                    "remaining": [],
                }
                target_path.write_text(json.dumps(target))
                control_path.write_text(
                    json.dumps(
                        {
                            "issue": reviewer,
                            "target_SHA256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
                            "reader_source_STOP": NOW.isoformat(),
                            "owned_readers_children_jobs_TMP_remaining": [],
                            "source_clear": True,
                            "blockers": [],
                        }
                    )
                )
                self.assertEqual(
                    [x["kind"] for x in self.classify(snapshot, rows)[0]],
                    ["completed_dependency_idle"],
                )
            rows[reviewer]["dependencies"] = [
                {"depends_on_id": "quoridor-4lc.998", "type": "parent-child"}
            ]
            self.assertEqual(self.classify(snapshot, rows)[0], [])
            rows[reviewer]["dependencies"] = [
                {"depends_on_id": "quoridor-4lc.400", "type": "parent-child"}
            ]
            target_path.write_text(json.dumps({"issue": "quoridor-4lc.400", "remaining": []}))
            control = json.loads(control_path.read_text())
            control["target_SHA256"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
            control_path.write_text(json.dumps(control))
            self.assertEqual(self.classify(snapshot, rows)[0], [])  # no independent STOP

    def test_paused_ancestor_blocks_and_unknown_job_does_not_turn_ready(self):
        snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
        parent = "quoridor-4lc.323"
        rows[parent] = {"id": parent, "status": "open", "labels": ["paused-by-user"]}
        rows["quoridor-4lc.400"]["dependencies"] = [
            {"depends_on_id": parent, "type": "parent-child"}
        ]
        self.assertEqual(self.classify(snapshot, rows)[0], [])
        rows[parent]["labels"] = []
        grandparent = "quoridor-4lc"
        rows[grandparent] = {"id": grandparent, "status": "open", "labels": ["paused-by-user"]}
        rows[parent]["dependencies"] = [{"depends_on_id": grandparent, "type": "parent-child"}]
        self.assertEqual(self.classify(snapshot, rows)[0], [])
        rows.pop(grandparent)
        self.assertEqual(self.classify(snapshot, rows)[1], ["quoridor-4lc.400"])
        rows[parent]["dependencies"] = []
        snapshot["groups"][0]["issues"][0]["jobs"] = [{"status": "unavailable"}]
        found, unknown = self.classify(snapshot, rows)
        self.assertEqual([x["kind"] for x in found], ["operational_unknown_idle"])
        self.assertFalse(found[0]["immediate"])
        self.assertEqual(unknown, ["quoridor-4lc.400"])

    def test_exact_finished_runtime_and_notification_with_no_owner_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "config.json").write_text(
                json.dumps({"issue": "quoridor-4lc.400", "thread_id": OWNER.removeprefix("codex:")})
            )
            (root / "state.json").write_text(
                json.dumps(
                    {
                        "issue": "quoridor-4lc.400",
                        "job_id": "job1",
                        "thread_id": OWNER.removeprefix("codex:"),
                        "phase": "finished",
                    }
                )
            )
            result = {
                "job_id": "job1",
                "outcome": "failed",
                "cleanup_complete": True,
                "remaining": [],
                "finished_at": NOW.isoformat(),
            }
            (root / "result.json").write_text(json.dumps(result))
            (root / "notification.json").write_text(json.dumps({"status": "delivered"}))
            snapshot, rows = fixture(jobs=[{"status": "command failed", "root": str(root)}])
            found, _ = self.classify(snapshot, rows)
            self.assertEqual([x["kind"] for x in found], ["failed_unhandled_idle"])
            (root / "notification.json").write_text(json.dumps({"status": "uncertain"}))
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]], ["operational_unknown_idle"]
            )
            (root / "notification.json").write_text(json.dumps({"status": "delivered"}))
            result.update(
                outcome="cleanup_required",
                cleanup_complete=False,
                direct_child_reaped=True,
                cleanup_errors=[{"stage": "finalizer"}],
            )
            (root / "result.json").write_text(json.dumps(result))
            snapshot["groups"][0]["issues"][0]["jobs"][0]["status"] = "recovery needed"
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]],
                ["failed_unhandled_idle"],
            )

    def test_finished_job_completion_survives_later_beads_comment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ident = "quoridor-4lc.400"
            thread = OWNER.removeprefix("codex:")
            config = {"issue": ident, "thread_id": thread}
            state = {**config, "job_id": "job1", "phase": "finished"}
            result = {
                "job_id": "job1",
                "outcome": "succeeded",
                "cleanup_complete": True,
                "remaining": [],
                "finished_at": NOW.isoformat(),
            }
            for name, value in (
                ("config", config),
                ("state", state),
                ("result", result),
                ("notification", {"status": "delivered"}),
            ):
                (root / f"{name}.json").write_text(json.dumps(value))
            snapshot, rows = fixture(
                wait="job_completion", jobs=[{"status": "command finished", "root": str(root)}]
            )
            rows[ident]["updated_at"] = (NOW + timedelta(minutes=1)).isoformat()
            self.assertEqual(
                [x["kind"] for x in self.classify(snapshot, rows)[0]], ["finished_unconsumed_idle"]
            )
            snapshot["groups"][0]["llm"] = "active"
            self.assertEqual(self.classify(snapshot, rows)[0], [])
            dashboard.runtime_files(str(root), ident)
            with self.assertRaises(dashboard.CollectionError):
                dashboard.runtime_files(str(root), "quoridor-4lc.324")

    def test_unknown_idle_repeats_before_notification_and_stays_unknown(self):
        snapshot, rows = fixture(wait="job_completion", jobs=[{"status": "unavailable"}])
        found, unknown = self.classify(snapshot, rows)
        self.assertEqual(unknown, ["quoridor-4lc.400"])
        cursor, eligible = health.advance(
            health.empty_cursor(), found, NOW, unavailable_issues=set(unknown)
        )
        self.assertEqual(eligible, [])
        cursor, eligible = health.advance(
            cursor, found, NOW + timedelta(minutes=15), unavailable_issues=set(unknown)
        )
        self.assertEqual(eligible, [])
        cursor, eligible = health.advance(
            cursor, found, NOW + timedelta(minutes=30), unavailable_issues=set(unknown)
        )
        self.assertEqual([x["kind"] for x in eligible], ["operational_unknown_idle"])
        cursor["delivered"][found[0]["fingerprint"]] = NOW.isoformat()
        self.assertEqual(health.advance(cursor, found, NOW + timedelta(minutes=45))[1], [])
        for kwargs in (
            {"llm": "active"},
            {"wait": "human_decision"},
            {"labels": ["dashboard", "paused-by-user"]},
        ):
            self.assertEqual(
                self.classify(*fixture(jobs=[{"status": "unavailable"}], **kwargs))[0], []
            )

    def test_task_progress_uses_existing_next_action_without_health_flag(self):
        snapshot, rows = fixture(wait="task_progress")
        self.assertEqual(
            [x["kind"] for x in self.classify(snapshot, rows)[0]], ["authorized_idle_no_job"]
        )
        snapshot["groups"][0]["issues"][0]["dependencies"] = [
            {"type": "blocks", "status": "in_progress"}
        ]
        self.assertEqual(self.classify(snapshot, rows)[0], [])


class CursorTests(unittest.TestCase):
    def setUp(self):
        self.item = health.candidate("authorized_idle_no_job", "quoridor-4lc.400", "v1", "stage")

    def test_two_consecutive_ticks_are_only_15_minutes(self):
        cursor, due = health.advance(health.empty_cursor(), [self.item], NOW)
        self.assertEqual(due, [])
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=15))
        self.assertEqual(due, [])
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=30))
        self.assertEqual([x["fingerprint"] for x in due], [self.item["fingerprint"]])
        cursor["delivered"][self.item["fingerprint"]] = NOW.isoformat()
        _, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=45))
        self.assertEqual(due, [])

    def test_progression_clears_streak_and_new_version_is_distinct(self):
        cursor, _ = health.advance(health.empty_cursor(), [self.item], NOW)
        cursor, _ = health.advance(cursor, [], NOW + timedelta(minutes=15))
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=30))
        self.assertEqual(due, [])
        self.assertEqual(cursor["pending"][self.item["fingerprint"]]["seen"], 1)
        changed = health.candidate("authorized_idle_no_job", "quoridor-4lc.400", "v2", "stage")
        self.assertNotEqual(changed["fingerprint"], self.item["fingerprint"])

    def test_partial_unknown_retains_refs_breaks_streak_and_revalidates(self):
        cursor, _ = health.advance(health.empty_cursor(), [self.item], NOW)
        key = self.item["fingerprint"]
        held = dict(cursor["pending"][key])
        cursor, due = health.advance(
            cursor,
            [],
            NOW + timedelta(minutes=15),
            unavailable_issues={self.item["issue"]},
        )
        self.assertEqual(cursor["pending"][key], held)
        self.assertEqual(due, [])
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=30))
        self.assertEqual(cursor["pending"][key]["seen"], 1)
        self.assertEqual(due, [])
        cursor, _ = health.advance(cursor, [], NOW + timedelta(minutes=45))
        self.assertEqual(cursor["pending"], {})

    def test_pending_refs_survive_unread_scan_without_false_consecutive_tick(self):
        cursor, _ = health.advance(health.empty_cursor(), [self.item], NOW)
        key = self.item["fingerprint"]
        self.assertEqual(
            {k: cursor["pending"][key][k] for k in ("issue", "kind", "target_or_job", "reference")},
            {
                "issue": "quoridor-4lc.400",
                "kind": "authorized_idle_no_job",
                "target_or_job": "stage",
                "reference": "",
            },
        )
        held = json.loads(json.dumps(cursor))
        health.break_observation_streak(cursor)
        self.assertEqual(cursor["pending"], held["pending"])
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=30))
        self.assertEqual(due, [])
        self.assertEqual(cursor["pending"][key]["seen"], 1)
        self.assertEqual(cursor["pending"][key]["first"], (NOW + timedelta(minutes=30)).isoformat())

    def test_digest_marks_survive_active_gap_and_unavailable_scan(self):
        cursor, _ = health.advance(health.empty_cursor(), [self.item], NOW)
        key = self.item["fingerprint"]
        cursor["commented"][key] = NOW.isoformat()
        cursor["delivered"][key] = NOW.isoformat()
        cursor, _ = health.advance(cursor, [], NOW + timedelta(minutes=15))
        self.assertEqual(cursor["pending"], {})
        health.break_observation_streak(cursor)
        self.assertIn(key, cursor["commented"])
        self.assertIn(key, cursor["delivered"])
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=45))
        self.assertEqual(due, [])
        cursor, due = health.advance(cursor, [self.item], NOW + timedelta(minutes=75))
        self.assertEqual(due, [])
        self.assertIn(key, cursor["delivered"])

    def test_digest_history_refuses_overflow_without_forgetting_old_marks(self):
        cursor = health.empty_cursor()
        cursor["commented"] = {f"{number:064x}": NOW.isoformat() for number in range(128)}
        cursor, _ = health.advance(cursor, [self.item], NOW)
        self.assertEqual(len(cursor["commented"]), 128)
        with self.assertRaises(health.HealthError):
            health.reserve_digest(cursor["commented"], self.item["fingerprint"])

    def test_pending_reference_size_refusal_preserves_previous_cursor(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cursor.json"
            original, _ = health.advance(health.empty_cursor(), [self.item], NOW)
            health.atomic_json(path, original)
            previous = path.read_bytes()
            long_references = [
                health.candidate(
                    "authorized_idle_no_job",
                    f"quoridor-4lc.{number}",
                    "v1",
                    "stage",
                    reference="r" * 4096,
                )
                for number in range(16)
            ]
            oversized, _ = health.advance(original, long_references, NOW)
            with self.assertRaises(health.HealthError):
                health.atomic_json(path, oversized)
            self.assertEqual(path.read_bytes(), previous)

    def test_bad_cursor_shape_is_unknown_not_delivery(self):
        with self.assertRaises(health.HealthError):
            health.advance(
                {"schema": 1, "cycle": "bad", "pending": {}, "delivered": {}, "uncertain": {}},
                [self.item],
                NOW,
            )


class BoundaryTests(unittest.TestCase):
    def test_stopped_status_retains_bounded_pending_reference_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            item = health.candidate(
                "authorized_idle_no_job",
                "quoridor-4lc.400",
                "v1",
                "source-stage",
                reference="Beads:quoridor-4lc.400",
            )
            cursor, _ = health.advance(health.empty_cursor(), [item], NOW)
            health.atomic_json(state / "cursor.json", cursor)
            health.set_mode(state, "STOPPED", human_confirmed=True)
            status = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "status", "--state-dir", str(state)],
                cwd=SCRIPT.parents[2],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            self.assertEqual(json.loads(status.stdout)["pending_count"], 1)
            self.assertEqual(
                health.bounded_json(state / "cursor.json")["pending"][item["fingerprint"]][
                    "reference"
                ],
                "Beads:quoridor-4lc.400",
            )

    def test_policy_authority_uses_bounded_brief_issue_only(self):
        row = {
            "id": health.POLICY_ISSUE,
            "status": "open",
            "assignee": f"codex:{health.POLICY_THREAD}",
            "labels": [],
        }
        with mock.patch.object(dashboard, "command_json", return_value=[row]) as port:
            self.assertTrue(health.policy_allowed(Path("/workspaces/quoridor"), dashboard))
            argv = port.call_args.args[0]
            self.assertIn("--brief", argv)
            self.assertIn("--max-rows", argv)
            self.assertIn("1", argv)
            self.assertNotIn("show", argv)

    def test_directed_proof_symlink_and_aggregate_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            target = directory / "target.json"
            target.write_text('{"issue":"quoridor-4lc.400"}')
            link = directory / "link.json"
            link.symlink_to(target)
            proofs = health.DirectedProofs()
            self.assertIsNone(proofs.read(str(link)))
            proofs.files = {
                f"/tmp/held-{i}.json": ({}, "a" * 64) for i in range(health.PROOF_FILE_LIMIT)
            }
            with self.assertRaises(health.HealthError):
                proofs.read(str(target))

    def test_consultation_quiet_autonomous_revalidates_and_stopped_reads_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
            health.set_mode(state, "CONSULTATION", human_confirmed=True)
            comments = []
            sends = []
            for minutes in (0, 15, 30):
                result = health.one_check(
                    state,
                    state,
                    now=NOW + timedelta(minutes=minutes),
                    observation=(snapshot, rows),
                    commenter=lambda *_: comments.append(True),
                    sender=lambda *_: sends.append(True),
                    owner_state=lambda *_: "idle",
                )
            self.assertEqual(result["state"], "consultation")
            self.assertEqual(comments, [])
            self.assertEqual(sends, [])
            self.assertEqual(len(health.bounded_json(state / "cursor.json")["pending"]), 1)

            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            resolved = json.loads(json.dumps(snapshot))
            resolved["groups"][0]["issues"][0]["status"] = "closed"
            result = health.one_check(
                state,
                state,
                now=NOW + timedelta(minutes=45),
                observation=(resolved, rows),
                commenter=lambda *_: comments.append(True),
                sender=lambda *_: sends.append(True),
                owner_state=lambda *_: "idle",
            )
            self.assertEqual(result["state"], "quiet")
            self.assertEqual(health.bounded_json(state / "cursor.json")["pending"], {})
            self.assertEqual(comments, [])
            self.assertEqual(sends, [])

            health.set_mode(state, "STOPPED", human_confirmed=True)
            with mock.patch.object(
                health, "read_observation", side_effect=AssertionError("foreign read")
            ):
                stopped = health.one_check(state, state)
            self.assertEqual(stopped["state"], "stopped")
            with self.assertRaises(health.HealthError):
                health.start(SCRIPT.parents[2], state)
            self.assertEqual(health.read_mode(state), "STOPPED")

    def test_missing_invalid_mode_fail_quiet_and_cli_requires_explicit_choice(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            with mock.patch.object(
                health, "read_observation", side_effect=AssertionError("foreign read")
            ):
                self.assertEqual(health.one_check(state, state)["state"], "UNKNOWN")
            with self.assertRaises(health.HealthError):
                health.set_mode(state, "AUTONOMOUS")
            (state / "mode.json").write_text('{"schema":1,"mode":"AUTONOMOUS"}')
            with mock.patch.object(
                health, "read_observation", side_effect=AssertionError("foreign read")
            ):
                self.assertEqual(health.one_check(state, state)["state"], "UNKNOWN")
            cli = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "mode",
                    "--set-mode",
                    "autonomous",
                    "--state-dir",
                    str(state),
                ],
                cwd=SCRIPT.parents[2],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(cli.returncode, 0)
            self.assertEqual(
                health.set_mode(state, "CONSULTATION", human_confirmed=True), "CONSULTATION"
            )
            status = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "status", "--state-dir", str(state)],
                cwd=SCRIPT.parents[2],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            self.assertEqual(json.loads(status.stdout)["mode"], "CONSULTATION")

    def test_autonomous_pending_waits_for_idle_then_one_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
            health.set_mode(state, "CONSULTATION", human_confirmed=True)
            for minutes in (0, 15, 30):
                health.one_check(
                    state, state, now=NOW + timedelta(minutes=minutes), observation=(snapshot, rows)
                )
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            comments = []
            sends = []
            result = health.one_check(
                state,
                state,
                now=NOW + timedelta(minutes=45),
                observation=(snapshot, rows),
                commenter=lambda *_: comments.append(True),
                sender=lambda *_: sends.append(True),
                owner_state=lambda *_: "active",
            )
            self.assertEqual(result["state"], "quiet")
            self.assertEqual(comments, [True])
            self.assertEqual(sends, [])
            result = health.one_check(
                state,
                state,
                now=NOW + timedelta(minutes=60),
                observation=(snapshot, rows),
                commenter=lambda *_: comments.append(True),
                sender=lambda *_: sends.append(True),
                owner_state=lambda *_: "notLoaded",
            )
            self.assertEqual(result["state"], "sent")
            self.assertEqual(comments, [True])
            self.assertEqual(sends, [True])

    def test_locked_timer_refuses_manual_check_and_control_remove(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            with (state / "singleton.lock").open("ab") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(health.HealthError):
                    health.with_single_check_lock(SCRIPT.parents[2], state)
                command = subprocess.run(
                    [sys.executable, "-B", str(SCRIPT), "remove", "--state-dir", str(state)],
                    cwd=SCRIPT.parents[2],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(command.returncode, 0)
                self.assertTrue((state / "singleton.lock").exists())

    def test_maintained_session_idle_only_never_steers(self):
        fake = ModuleType("websockets")
        fake.__path__ = []
        fake_asyncio = ModuleType("websockets.asyncio")
        fake_asyncio.__path__ = []
        fake_client = ModuleType("websockets.asyncio.client")
        fake_client.unix_connect = lambda *_args, **_kwargs: None
        modules = {
            "websockets": fake,
            "websockets.asyncio": fake_asyncio,
            "websockets.asyncio.client": fake_client,
        }
        with mock.patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location(
                "research_session", SCRIPT.with_name("research-session.py")
            )
            session = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(session)
        active = {"id": "thread1", "cwd": "/workspaces/quoridor", "status": {"type": "active"}}
        with self.assertRaises(session.SessionError):
            session.delivery_params(
                active,
                [{"id": "turn1", "status": "inProgress"}],
                "health",
                active["cwd"],
                idle_only=True,
            )
        idle = {**active, "status": {"type": "idle"}}
        method, _ = session.delivery_params(idle, [], "health", idle["cwd"], idle_only=True)
        self.assertEqual(method, "turn/start")
        args = session.parser().parse_args(
            [
                "send",
                "--thread",
                "thread1",
                "--issue",
                "quoridor-4lc",
                "--body-file",
                "x",
                "--idle-only",
            ]
        )
        self.assertTrue(args.idle_only)
        brief_row = [
            {"id": "quoridor-4lc", "status": "open", "labels": [], "assignee": "codex:thread1"}
        ]
        with mock.patch.object(session, "command_json", return_value=brief_row) as command:
            session.require_owner(
                "quoridor-4lc", Path("/workspaces/quoridor"), "thread1", brief=True
            )
            argv = command.call_args.args[0]
            self.assertIn("--brief", argv)
            self.assertIn("--max-rows", argv)
            self.assertNotIn("show", argv)
        huge = [{**brief_row[0], "metadata": {"dashboard": {"stage": "x" * 65536}}}]
        with mock.patch.object(session, "command_json", return_value=huge):
            with self.assertRaises(session.SessionError):
                session.require_owner(
                    "quoridor-4lc", Path("/workspaces/quoridor"), "thread1", brief=True
                )
        with self.assertRaises(session.SessionError):
            session.command_json(
                [sys.executable, "-c", "import sys;sys.stdout.write('x'*65537)"],
                max_bytes=65536,
            )
        self.assertEqual(
            session.command_json([sys.executable, "-c", "print('{\"ok\":true}')"], max_bytes=65536),
            {"ok": True},
        )

        class Server:
            def __init__(self, status, after_resume=None):
                self.status = status
                self.after_resume = after_resume
                self.requests = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def read_thread(self, _thread):
                return {
                    "id": "thread1",
                    "cwd": "/workspaces/quoridor",
                    "status": {"type": self.status},
                }

            async def turns(self, _thread):
                return [{"id": "turn1", "status": "inProgress"}]

            async def request(self, method, params):
                self.requests.append((method, params))
                if method == "thread/resume" and self.after_resume is not None:
                    self.status = self.after_resume
                return {"turn": {"id": "new-turn"}}

        for status, after_resume, expected in (
            ("active", None, []),
            ("notLoaded", "active", ["thread/resume"]),
            ("notLoaded", "idle", ["thread/resume", "turn/start"]),
            ("idle", None, ["turn/start"]),
        ):
            server = Server(status, after_resume)
            with (
                mock.patch.object(
                    session, "project_root", return_value=Path("/workspaces/quoridor")
                ),
                mock.patch.object(
                    session,
                    "command_json",
                    return_value={"status": "running", "socketPath": "/tmp/fake"},
                ),
                mock.patch.object(session, "require_issue", return_value={}),
                mock.patch.object(session, "require_owner", return_value={}),
                mock.patch.object(session, "resolve_task_cwd", return_value="/workspaces/quoridor"),
                mock.patch.object(session, "dispatch_lock", return_value=nullcontext()),
                mock.patch.object(session, "AppServer", return_value=server),
                tempfile.TemporaryDirectory() as temporary,
            ):
                body = Path(temporary) / "body.txt"
                body.write_text("bounded event")
                args.body_file = str(body)
                if expected[-1:] == ["turn/start"]:
                    self.assertEqual(asyncio.run(session.run(args))["method"], "turn/start")
                else:
                    with self.assertRaises(session.SessionError):
                        asyncio.run(session.run(args))
                self.assertEqual([m for m, _ in server.requests], expected)

    def test_read_unknown_and_dispatch_uncertain_not_delivered(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            malformed = (
                {"groups": [{"owner": OWNER, "llm": "idle", "issues": [{"id": "missing"}]}]},
                {},
            )
            self.assertEqual(
                health.one_check(Path(temporary), state, observation=malformed)["state"], "UNKNOWN"
            )
            snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
            now = NOW
            for minutes in (0, 15):
                health.one_check(
                    Path(temporary),
                    state,
                    now=now + timedelta(minutes=minutes),
                    observation=(snapshot, rows),
                )

            def failed_send(*_args):
                raise health.HealthError("administrative send failed")

            result = health.one_check(
                Path(temporary),
                state,
                now=now + timedelta(minutes=30),
                observation=(snapshot, rows),
                commenter=lambda *_: None,
                owner_state=lambda *_: "idle",
                sender=failed_send,
            )
            self.assertEqual(result["state"], "UNKNOWN")
            cursor = health.bounded_json(state / "cursor.json")
            self.assertFalse(cursor["delivered"])
            self.assertEqual(len(cursor["uncertain"]), 1)

    def test_read_failure_breaks_actionable_streak(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
            first = health.one_check(state, state, now=NOW, observation=(snapshot, rows))
            self.assertEqual(first["state"], "quiet")
            malformed = (
                {"groups": [{"owner": OWNER, "llm": "idle", "issues": [{"id": "missing"}]}]},
                {},
            )
            self.assertEqual(
                health.one_check(
                    state, state, now=NOW + timedelta(minutes=15), observation=malformed
                )["state"],
                "UNKNOWN",
            )
            cursor = health.bounded_json(state / "cursor.json")
            key = next(iter(cursor["pending"]))
            self.assertEqual(cursor["pending"][key]["issue"], "quoridor-4lc.400")
            self.assertEqual(
                cursor["pending"][key]["target_or_job"], "Authorized finite source work"
            )
            self.assertEqual(
                health.one_check(
                    state, state, now=NOW + timedelta(minutes=30), observation=(snapshot, rows)
                )["state"],
                "quiet",
            )
            self.assertEqual(health.bounded_json(state / "cursor.json")["pending"][key]["seen"], 1)

    def test_active_policy_thread_keeps_one_commented_pending_event(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
            comments = []
            sends = []

            def comment(*args):
                comments.append(args[1]["fingerprint"])

            def send(*args):
                sends.append([item["fingerprint"] for item in args[2]])

            for minutes in (0, 15, 30, 45):
                result = health.one_check(
                    state,
                    state,
                    now=NOW + timedelta(minutes=minutes),
                    observation=(snapshot, rows),
                    commenter=comment,
                    sender=send,
                    owner_state=lambda *_: "active",
                )
            self.assertEqual(result["state"], "quiet")
            self.assertEqual(len(comments), 1)
            self.assertEqual(sends, [])
            cursor = health.bounded_json(state / "cursor.json")
            self.assertEqual(len(cursor["pending"]), 1)
            self.assertEqual(len(cursor["commented"]), 1)
            result = health.one_check(
                state,
                state,
                now=NOW + timedelta(minutes=60),
                observation=(snapshot, rows),
                commenter=comment,
                sender=send,
                owner_state=lambda *_: "idle",
            )
            self.assertEqual(result["state"], "sent")
            self.assertEqual(len(comments), 1)
            self.assertEqual(len(sends), 1)
            health.one_check(
                state,
                state,
                now=NOW + timedelta(minutes=75),
                observation=(snapshot, rows),
                commenter=comment,
                sender=send,
                owner_state=lambda *_: "idle",
            )
            self.assertEqual(len(sends), 1)
            rows["quoridor-4lc.400"]["metadata"]["dashboard"]["health"]["recovery_started"] = True
            health.one_check(
                state,
                state,
                now=NOW + timedelta(minutes=90),
                observation=(snapshot, rows),
                commenter=comment,
                sender=send,
                owner_state=lambda *_: "idle",
            )
            self.assertFalse(health.bounded_json(state / "cursor.json")["pending"])

    def test_two_pending_candidates_use_one_idle_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            snapshot, rows = fixture(metadata={"health": {"authorized_active": True}})
            second = json.loads(json.dumps(rows["quoridor-4lc.400"]))
            second["id"] = "quoridor-4lc.401"
            rows[second["id"]] = second
            issue = json.loads(json.dumps(snapshot["groups"][0]["issues"][0]))
            issue["id"] = second["id"]
            snapshot["groups"][0]["issues"].append(issue)
            sends = []
            for minutes in (0, 15, 30):
                health.one_check(
                    state,
                    state,
                    now=NOW + timedelta(minutes=minutes),
                    observation=(snapshot, rows),
                    commenter=lambda *_: None,
                    owner_state=lambda *_: "idle",
                    sender=lambda _root, _state, items, _dashboard: sends.append(items),
                )
            self.assertEqual(len(sends), 1)
            self.assertEqual({item["issue"] for item in sends[0]}, set(rows))

    def test_timer_singleton_exact_identity_stop_and_remove(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "CONSULTATION", human_confirmed=True)
            root = SCRIPT.parents[2]
            with mock.patch.dict(os.environ, {"RESEARCH_HEALTH_TEST_MODE": "1"}):
                first = health.start(root, state, test_idle=True)
                try:
                    self.assertEqual(first["state"], "started")
                    self.assertTrue(health.same_timer(first["owner"]))
                    self.assertEqual(
                        health.start(root, state, test_idle=True)["state"], "already-running"
                    )
                    with mock.patch.object(health, "same_timer", return_value=False):
                        with mock.patch.object(health.signal, "pidfd_send_signal") as signal_port:
                            with self.assertRaises(health.HealthError):
                                health.stop_timer(state)
                            signal_port.assert_not_called()
                    changed = {**first["owner"], "start_ticks": "0"}
                    with (
                        mock.patch.object(health, "identity", return_value=changed),
                        mock.patch.object(health.signal, "pidfd_send_signal") as signal_port,
                    ):
                        with self.assertRaises(health.HealthError):
                            health.stop_timer(state)
                        signal_port.assert_not_called()
                    self.assertTrue(health.same_timer(first["owner"]))
                    disabled = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(SCRIPT),
                            "disable",
                            "--state-dir",
                            str(state),
                            "--confirm-human-choice",
                        ],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=True,
                    )
                    self.assertEqual(json.loads(disabled.stdout)["mode"], "STOPPED")
                    health.OWNED_CHILDREN.pop(first["owner"]["pid"]).wait(timeout=5)
                    self.assertFalse(health.same_timer(first["owner"]))
                finally:
                    if health.same_timer(first["owner"]):
                        health.stop_timer(state)
            command = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "remove", "--state-dir", str(state)],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            self.assertEqual(json.loads(command.stdout)["state"], "removed")
            self.assertFalse((state / "timer-owner.json").exists())
            self.assertEqual(health.read_mode(state), "STOPPED")

    def test_pidfd_unsupported_refuses_before_spawn_and_handshake_failure_reaps_own_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            root = SCRIPT.parents[2]
            health.set_mode(state, "CONSULTATION", human_confirmed=True)
            with (
                mock.patch.object(health.os, "pidfd_open", side_effect=OSError("unsupported")),
                mock.patch.object(health.subprocess, "Popen") as spawned,
            ):
                with self.assertRaises(OSError):
                    health.start(root, state, test_idle=True)
                spawned.assert_not_called()

            children = []
            actual_popen = health.subprocess.Popen

            def record_child(*args, **kwargs):
                child = actual_popen(*args, **kwargs)
                children.append(child)
                return child

            with (
                mock.patch.dict(os.environ, {"RESEARCH_HEALTH_TEST_MODE": "1"}),
                mock.patch.object(health.subprocess, "Popen", side_effect=record_child),
                mock.patch.object(health, "same_timer", return_value=False),
            ):
                with self.assertRaises(health.HealthError) as failed:
                    health.start(root, state, test_idle=True, handshake_attempts=1)
                self.assertIn("handshake timed out", str(failed.exception))
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll())
            self.assertNotIn(children[0].pid, health.OWNED_CHILDREN)


class RecoveryTests(unittest.TestCase):
    def test_active_collection_hydrates_only_referenced_closed_dependencies(self):
        active = {
            "id": "quoridor-4lc.400",
            "status": "in_progress",
            "dependencies": [{"depends_on_id": "quoridor-4lc.401", "type": "blocks"}],
        }
        closed = {"id": "quoridor-4lc.401", "status": "closed", "dependencies": []}
        requests = []
        ports = dashboard.Ports(Path("/unused"))

        def response(argv, **kwargs):
            requests.append(argv)
            return [closed] if "--id" in argv else [active]

        with mock.patch.object(ports, "run", side_effect=response):
            cached = health.CachedPorts(dashboard, Path("/unused"))
            cached.delegate = ports
            raw = dashboard.valid_rows(cached.issues())
            targets = sorted(
                {edge["id"] for row in raw for edge in dashboard.edges(row)}
                - {row["id"] for row in raw}
            )
            self.assertEqual(cached.dependencies(targets), [closed])
            self.assertEqual(raw, [active])
        self.assertNotIn("--all", requests[0])
        self.assertEqual(
            requests[0][requests[0].index("--status") + 1], "open,in_progress,blocked,deferred"
        )
        self.assertIn("--all", requests[1])
        self.assertEqual(requests[1][requests[1].index("--id") + 1], closed["id"])
        with self.assertRaises(dashboard.CollectionError):
            dashboard.valid_rows([active] * (dashboard.ROWS + 1))

    def test_separate_collection_exception_is_unknown_and_check_continues(self):
        other = health.dashboard_module()
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            with (
                mock.patch.object(
                    other, "collect", side_effect=other.CollectionError("too many rows")
                ),
                mock.patch.object(health, "dashboard_module", side_effect=[dashboard, other]),
            ):
                result = health.one_check(SCRIPT.parents[2], state, dry_run=True)
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(result["reason"], "HealthError")
            result = health.one_check(SCRIPT.parents[2], state, dry_run=True, observation=fixture())
            self.assertEqual(result["state"], "dry-run")

    def test_timer_waits_for_exec_argv_and_retains_singleton_cleanup(self):
        root = SCRIPT.parents[2]
        actual_identity = health.identity
        attempts = 0

        def delayed(pid):
            nonlocal attempts
            attempts += 1
            current = actual_identity(pid)
            if attempts <= 2 and current is not None:
                return {**current, "argv": ["pre-exec parent"]}
            return current

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            health.set_mode(state, "AUTONOMOUS", human_confirmed=True)
            with (
                mock.patch.dict(os.environ, {"RESEARCH_HEALTH_TEST_MODE": "1"}),
                mock.patch.object(health, "identity", side_effect=delayed),
            ):
                first = health.start(root, state, test_idle=True)
            try:
                self.assertEqual(first["state"], "started")
                self.assertGreater(attempts, 2)
                self.assertTrue(health.same_timer(first["owner"]))
                self.assertEqual(
                    health.start(root, state, test_idle=True)["state"], "already-running"
                )
            finally:
                self.assertEqual(health.stop_timer(state)["state"], "stopped")
                self.assertNotIn(first["owner"]["pid"], health.OWNED_CHILDREN)
            self.assertFalse(health.same_timer(first["owner"]))
            self.assertEqual(health.read_mode(state), "AUTONOMOUS")


if __name__ == "__main__":
    unittest.main()
