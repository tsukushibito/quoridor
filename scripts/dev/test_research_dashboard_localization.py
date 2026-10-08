"""Focused NN0 localization regressions; mocked read ports, no science/network."""

from copy import deepcopy
from datetime import datetime, timezone
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class NoExternal(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {
            "torch",
            "onnx",
            "onnxruntime",
            "numpy",
            "websockets",
            "requests",
            "quoridor_training",
            "httpx",
            "openai",
        }:
            raise AssertionError("Forbidden dependency: " + fullname)
        return None


sys.meta_path.insert(0, NoExternal())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = load("localized_dashboard_test", Path(__file__).with_name("research-dashboard.py"))
t = d.translations
NOW = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
OWNER = "codex:00000000-0000-0000-0000-000000000001"


def row(identity="demo-1", **extra):
    return {
        "id": identity,
        "title": "Current task",
        "assignee": OWNER,
        "status": "open",
        "metadata": {"dashboard": {"stage": "Preparation", "next_action": "Read source"}},
        "dependencies": [],
        "labels": [],
        **extra,
    }


class Ports:
    def __init__(self, root, rows=None):
        self.root = root
        self.rows = rows if rows is not None else [row()]
        self.deps = []
        self.name = "Actual owner"
        self.status = "active"
        self.calls = []

    def issues(self):
        self.calls.append("issues")
        return deepcopy(self.rows)

    def dependencies(self, ids):
        self.calls.append(("dependencies", ids))
        return deepcopy(self.deps)

    def thread(self, identity):
        self.calls.append(("status", identity))
        if isinstance(self.status, Exception):
            raise self.status
        return {
            "thread": {
                "id": identity,
                "name": self.name,
                "status": {"type": self.status},
                "preview": "PRIVATE_PROMPT",
                "turns": ["PRIVATE_TURN"],
            }
        }

    def identities(self, identities):
        self.calls.append(("identities", identities))
        return [False] * len(identities)


def record(
    kind="issue", identity="demo-1", field="title", source="Current task", ja="現在のタスク"
):
    return {
        "kind": kind,
        "id": identity,
        "field": field,
        "originalEnglishSHA256": t.sha(source),
        "ja": ja,
    }


def records(*values):
    return t.decode(
        json.dumps({"version": 1, "entries": list(values)}, ensure_ascii=False).encode()
    )


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ports = Ports(self.root)
        self.cache = self.root / ".artifacts/research-dashboard/translations-ja.json"
        self.delta = self.root / "delta.json"

    def snapshot(self):
        return d.collect(self.ports, NOW)

    def write_delta(self, values):
        self.delta.write_bytes(t.encode(records(*values)))

    def write_cache(self, values):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_bytes(t.encode(records(*values)))

    def test_original_facts_counts_waits_dependencies_and_admin_closure(self):
        closed = row(
            "demo-closed", status="closed", close_reason="Accepted", closed_at=NOW.isoformat()
        )
        closed["metadata"]["dashboard"].update(
            wait_reason="Await acceptance", wait_kind="human_decision"
        )
        paused = row("demo-paused", labels=["paused-by-user"])
        waiting = row("demo-wait")
        waiting["metadata"]["dashboard"].update(wait_reason="Await resource", wait_kind="resource")
        waiting["dependencies"] = [{"depends_on_id": "external-1", "type": "blocks"}]
        human = row("demo-human")
        human["metadata"]["dashboard"].update(
            wait_reason="Choose method", wait_kind="human_decision"
        )
        self.ports.rows = [row(), closed, paused, waiting, human, row("demo-other", assignee=None)]
        self.ports.deps = [row("external-1")]
        snapshot = self.snapshot()
        self.assertEqual(
            snapshot["counts"], {"running_jobs": 0, "waiting_issues": 3, "human_decisions": 1}
        )
        groups = {group["owner"]: group for group in snapshot["groups"]}
        self.assertEqual(set(groups), {OWNER, "Unassigned"})
        self.assertEqual((groups[OWNER]["name"], groups[OWNER]["llm"]), ("Actual owner", "active"))
        self.assertEqual(
            (groups["Unassigned"]["name"], groups["Unassigned"]["llm"]), ("Not supplied", "unknown")
        )
        issues = {issue["id"]: issue for group in snapshot["groups"] for issue in group["issues"]}
        expected = {
            "demo-1": ("open", False, False, "Not supplied", "Not supplied", "", ""),
            "demo-closed": (
                "closed",
                False,
                False,
                "Await acceptance",
                "human_decision",
                "Accepted",
                NOW.isoformat(),
            ),
            "demo-paused": ("open", True, True, "Paused by user", "Not supplied", "", ""),
            "demo-wait": ("open", False, True, "Await resource", "resource", "", ""),
            "demo-human": ("open", False, True, "Choose method", "human_decision", "", ""),
            "demo-other": ("open", False, False, "Not supplied", "Not supplied", "", ""),
        }
        self.assertEqual(set(issues), set(expected))
        for identity, facts in expected.items():
            issue = issues[identity]
            self.assertEqual(
                tuple(
                    issue[key]
                    for key in (
                        "status",
                        "paused",
                        "waiting",
                        "wait_reason",
                        "wait_kind",
                        "close_reason",
                        "closed_at",
                    )
                ),
                facts,
            )
            self.assertEqual(
                (issue["title"], issue["stage"], issue["next_action"]),
                ("Current task", "Preparation", "Read source"),
            )
            self.assertEqual(issue["jobs"], [])
            self.assertEqual(issue["evidence_paths"], [])
        self.assertEqual(
            issues["demo-wait"]["dependencies"],
            [{"id": "external-1", "type": "blocks", "title": "Current task", "status": "open"}],
        )
        self.assertTrue(
            all(
                not issue["dependencies"]
                for identity, issue in issues.items()
                if identity != "demo-wait"
            )
        )
        self.assertEqual(snapshot["warnings"], [])
        original = deepcopy(snapshot)
        d.render(snapshot, translation_entries=records(record()))
        self.assertEqual(snapshot, original)

    def test_job_phases_exact_identity_results_and_unknown_cleanup(self):
        missing = "State/result boundary is missing or inconsistent"
        cases = [
            ("queued", False, "preparing", "Not supplied"),
            ("starting", False, "preparing", "Not supplied"),
            ("running", True, "running", "Exact child identity confirmed at collection"),
            (
                "running",
                False,
                "recovery needed",
                "Running claim has no fresh matching child identity",
            ),
            ("running", None, "unavailable", "Running claim has no fresh matching child identity"),
            ("finished", False, "unconfirmed", missing),
        ]
        for phase, alive, status, result in cases:
            with self.subTest(phase=phase, alive=alive):
                view = d.job_view(
                    "/tmp/job", {"phase": phase, "job_id": "job"}, None, "timestamp", alive
                )
                self.assertEqual(
                    {k: view[k] for k in ("root", "status", "source_at", "result")},
                    {
                        "root": "/tmp/job",
                        "status": status,
                        "source_at": "timestamp",
                        "result": result,
                    },
                )
        state = {"phase": "finished", "job_id": "job"}
        base = {
            "job_id": "job",
            "outcome": "succeeded",
            "exit_code": 0,
            "direct_child_reaped": True,
            "cleanup_complete": True,
            "finished_at": NOW.isoformat(),
        }
        for patch_result, status, unknown_cleanup in (
            ({}, "command finished", False),
            ({"outcome": "failed", "exit_code": 1}, "command failed", False),
            ({"cleanup_complete": False}, "recovery needed", True),
            ({"cleanup_complete": None}, "recovery needed", True),
            ({"direct_child_reaped": False}, "recovery needed", True),
            ({"remaining": [{"pid": 12}]}, "recovery needed", True),
            ({"cleanup_errors": ["wait failed"]}, "recovery needed", True),
        ):
            with self.subTest(patch_result=patch_result):
                value = {**base, **patch_result}
                view = d.job_view("/tmp/job", state, value, "timestamp", False)
                self.assertEqual(view["status"], status)
                self.assertEqual(view["cleanup_unconfirmed"], unknown_cleanup)
                self.assertEqual(view["finished_at"], NOW.isoformat())
                expected_result = f"Controller outcome: {value['outcome']}; exit code: {value['exit_code']}. Scientific success is not qualified here."
                if unknown_cleanup:
                    expected_result += " Cleanup is incomplete or unknown."
                self.assertEqual(view["result"], expected_result)
        without_cleanup = dict(base)
        del without_cleanup["cleanup_complete"]
        self.assertEqual(
            d.job_view("/tmp/job", state, without_cleanup, "timestamp", False)["status"],
            "recovery needed",
        )
        mismatch = {**base, "job_id": "other"}
        view = d.job_view("/tmp/job", state, mismatch, "timestamp", False)
        self.assertEqual((view["status"], view["result"]), ("unconfirmed", missing))

    def test_current_translation_and_dependency_title_share_identity(self):
        self.ports.rows[0]["dependencies"] = [{"depends_on_id": "demo-2", "type": "blocks"}]
        self.ports.rows.append(row("demo-2"))
        view = t.display(self.snapshot(), records(record(identity="demo-2")))
        self.assertEqual(view["issues"]["demo-2"]["title"], "現在のタスク")
        self.assertEqual(
            len([k for k in t.catalog(self.snapshot()) if k == ("issue", "demo-2", "title")]), 1
        )

    def test_missing_dependency_title_is_explicit_not_a_renderer_failure(self):
        self.ports.rows[0]["dependencies"] = [{"depends_on_id": "external-1", "type": "blocks"}]
        self.ports.deps = [row("external-1", title="")]
        snapshot = self.snapshot()
        self.assertEqual(t.display(snapshot, {})["issues"]["external-1"]["title"], t.MISSING)
        self.assertIn(t.MISSING, d.render(snapshot).decode())

    def test_missing_cache_is_pending_and_raw_english_remains(self):
        page = d.render(self.snapshot()).decode()
        self.assertIn(t.PENDING, page)
        self.assertIn("Current task", page)
        self.assertEqual(
            t.display(self.snapshot(), {})["issues"]["demo-1"]["wait_reason"], t.MISSING
        )

    def test_stale_hash_never_displays_old_japanese(self):
        self.ports.rows[0]["title"] = "Changed source"
        view = t.display(self.snapshot(), records(record(ja="古い日本語")))
        self.assertEqual(view["issues"]["demo-1"]["title"], t.PENDING)
        self.assertNotIn(
            "古い日本語",
            d.render(
                self.snapshot(), translation_entries=records(record(ja="古い日本語"))
            ).decode(),
        )

    def test_missing_name_and_literal_sentinel_source_distinct(self):
        self.ports.name = None
        self.ports.rows[0]["metadata"]["dashboard"]["stage"] = "Not supplied"
        view = t.display(self.snapshot(), {})
        self.assertEqual(view["owner_names"][OWNER], t.MISSING)
        self.assertEqual(view["issues"]["demo-1"]["stage"], t.PENDING)

    def test_unknown_llm_never_idle_and_not_loaded_separate(self):
        self.ports.status = d.CollectionError("offline")
        group = self.snapshot()["groups"][0]
        self.assertEqual(group["llm"], "unavailable")
        self.assertEqual(t.display(self.snapshot(), {})["owner_names"][OWNER], t.MISSING)
        self.ports.status = "notLoaded"
        self.assertEqual(self.snapshot()["groups"][0]["llm"], "notLoaded")

    def test_finished_cleanup_unknown_is_recovery_not_science_success(self):
        state = {"phase": "finished", "job_id": "job"}
        result = {"job_id": "job", "outcome": "succeeded", "exit_code": 0, "cleanup_complete": None}
        view = d.job_view("/tmp/job", state, result, NOW.isoformat(), False)
        self.assertEqual(view["status"], "recovery needed")
        self.assertTrue(view["cleanup_unconfirmed"])
        self.assertIn("Scientific success is not qualified", view["result"])

    def test_admin_closure_is_allowed_text_only_and_hidden_when_open(self):
        self.ports.rows[0].update(
            status="closed", close_reason="Accepted", closed_at=NOW.isoformat()
        )
        original = t.catalog(self.snapshot())
        self.assertEqual(original[("issue", "demo-1", "close_reason")], "Accepted")
        self.assertNotIn(("issue", "demo-1", "closed_at"), original)
        self.ports.rows[0]["status"] = "open"
        self.assertNotIn(("issue", "demo-1", "close_reason"), t.catalog(self.snapshot()))

    def test_latest_replacement_and_pruning_without_histories(self):
        self.write_cache(
            [
                record(ja="旧訳"),
                record(identity="removed", ja="削除対象"),
                record(field="stage", source="Old stage", ja="古い段階"),
            ]
        )
        self.write_delta([record(ja="新訳")])
        t.update(d, self.ports, self.delta, self.cache)
        self.assertEqual(list(t.read(self.cache)), [("issue", "demo-1", "title")])
        self.write_delta([record(ja="最新版")])
        t.update(d, self.ports, self.delta, self.cache)
        self.assertIn("最新版", self.cache.read_text())
        self.assertNotIn("新訳", self.cache.read_text())
        self.assertEqual(list(self.cache.parent.iterdir()), [self.cache])

    def test_source_change_before_merge_refuses_whole_delta_keeps_cache(self):
        self.write_cache([record()])
        previous = self.cache.read_bytes()
        self.write_delta([record(), record(field="stage", source="Preparation", ja="準備")])
        self.ports.rows[0]["title"] = "Changed source"
        with self.assertRaises(t.TranslationError):
            t.update(d, self.ports, self.delta, self.cache)
        self.assertEqual(previous, self.cache.read_bytes())

    def test_unrequested_delta_and_forbidden_state_refused(self):
        for value in (
            record(identity="not-displayed"),
            record(field="status"),
            record(kind="owner", field="llm"),
        ):
            with self.subTest(value=value):
                self.write_cache([record()])
                previous = self.cache.read_bytes()
                with self.assertRaises(t.TranslationError):
                    self.write_delta([value])
                    t.update(d, self.ports, self.delta, self.cache)
                self.assertEqual(previous, self.cache.read_bytes())

    def test_atomic_replace_failure_preserves_cache_and_cleans_temp(self):
        self.write_cache([record()])
        self.write_delta([record(ja="更新")])
        previous = self.cache.read_bytes()
        with patch.object(d.os, "replace", side_effect=OSError("REPLACE_FAILED")):
            with self.assertRaisesRegex(OSError, "REPLACE_FAILED"):
                t.update(d, self.ports, self.delta, self.cache)
        self.assertEqual(previous, self.cache.read_bytes())
        self.assertEqual(list(self.cache.parent.iterdir()), [self.cache])

    def test_dual_failure_keeps_primary_and_cleanup_note(self):
        self.write_cache([record()])
        self.write_delta([record(ja="更新")])
        previous = self.cache.read_bytes()
        with (
            patch.object(d.os, "replace", side_effect=OSError("REPLACE_FAILED")),
            patch.object(Path, "unlink", side_effect=OSError("UNLINK_FAILED")),
        ):
            with self.assertRaisesRegex(OSError, "REPLACE_FAILED") as caught:
                t.update(d, self.ports, self.delta, self.cache)
        self.assertIn("UNLINK_FAILED", " ".join(caught.exception.__notes__))
        self.assertEqual(previous, self.cache.read_bytes())

    def test_input_cap_symlink_and_duplicate_refusals(self):
        for raw in (
            b" " * (t.CACHE_BYTES + 1),
            b'{"version":1,"version":1,"entries":[]}',
            json.dumps({"version": 1, "entries": [record(), record()]}).encode(),
        ):
            self.delta.write_bytes(raw)
            with self.assertRaises(t.TranslationError):
                t.read(self.delta)
        self.delta.unlink()
        self.delta.symlink_to(self.cache)
        with self.assertRaises(OSError):
            t.read(self.delta)

    def test_merged_cap_refused_before_publish(self):
        values = {
            ("issue", str(i), "title"): record(identity=str(i), ja="あ" * 2700) for i in range(130)
        }
        with self.assertRaises(t.TranslationError):
            t.encode(values)

    def test_malformed_cache_generator_warns_no_stale_fallback(self):
        self.cache.parent.mkdir(parents=True)
        self.cache.write_text("MALFORMED")
        output = self.root / "snapshot.html"
        d.generate(self.ports, output)
        self.assertIn('"cache_warning":true', output.read_text())
        self.assertIn(t.PENDING, output.read_text())

    def test_generator_only_reads_saved_cache_no_updater(self):
        self.write_cache([record()])
        with (
            patch.object(t, "update", side_effect=AssertionError("Automatic update forbidden")),
            patch.object(d.subprocess, "Popen", side_effect=AssertionError("Unexpected command")),
        ):
            d.generate(self.ports, self.root / "snapshot.html")
        self.assertEqual(self.ports.calls, ["issues", ("dependencies", []), ("status", OWNER[6:])])
        self.assertNotIn("PRIVATE_PROMPT", (self.root / "snapshot.html").read_text())

    def test_malicious_japanese_source_and_path_are_escaped_data(self):
        attack = (
            '</script><script>globalThis.INJECTED=341</script><img src="https://invalid.test/">'
        )
        self.ports.rows[0]["title"] = attack
        self.ports.rows[0]["metadata"]["dashboard"]["evidence_paths"] = ["/tmp/" + attack]
        page = d.render(
            self.snapshot(),
            translation_entries=records(record(source=attack, ja="日本語 " + attack)),
        ).decode()
        self.assertNotIn(attack, page)
        self.assertIn("\\u003c/script\\u003e", page)
        self.assertNotIn("PRIVATE_TURN", page)
        self.assertIn('<html lang="ja">', page)


if __name__ == "__main__":
    unittest.main()
