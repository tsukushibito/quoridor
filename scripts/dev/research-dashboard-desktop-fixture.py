"""Produce an offline, bounded desktop dashboard fixture for browser verification."""

import importlib.util
from pathlib import Path
import sys


def load(path):
    spec = importlib.util.spec_from_file_location("dashboard_fixture_source", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dashboard = load(Path(__file__).with_name("research-dashboard.py"))


def issue(identity, title, *, status="open", stage="Not supplied", next_action="Not supplied"):
    return {
        "id": identity,
        "title": title,
        "status": status,
        "updated_at": "2026-10-08T00:00:00+00:00",
        "close_reason": "Not supplied",
        "closed_at": "Not supplied",
        "stage": stage,
        "next_action": next_action,
        "wait_reason": "Not supplied",
        "wait_kind": "Not supplied",
        "paused": False,
        "waiting": False,
        "dependencies": [],
        "evidence_paths": [],
        "jobs": [],
        "source_fields": ["title", "stage", "next_action"],
    }


def group(owner, name, llm, issues, primary):
    return {
        "owner": owner,
        "name": name,
        "name_supplied": True,
        "llm": llm,
        "llm_source_at": "2026-10-08T00:00:00+00:00",
        "issues": issues,
        "primary_issue_id": primary,
    }


def snapshot(reloaded=False):
    hostile = '</script><img src="https://evil.invalid/">'
    long_title = "Current implementation task " + "LONG_TITLE_" * 42
    first = issue("alpha-1", "Other unresolved task", stage="Earlier source work")
    current = issue(
        "alpha-2",
        long_title if not reloaded else "Updated file after manual generation",
        status="in_progress",
        stage="Reported implementation stage " + "LONG_STAGE_" * 45,
        next_action="Next exact action " + "LONG_NEXT_" * 52,
    )
    current["evidence_paths"] = ["/tmp/desktop-fixture/evidence"]
    current["title"] += hostile
    closed = issue("alpha-0", "Completed history", status="closed")
    closed["close_reason"] = "Administrative completion " + "LONG_CLOSE_" * 50
    closed["source_fields"].append("close_reason")
    paused = issue("pause-1", "Explicit user pause", status="in_progress")
    paused.update(
        paused=True, waiting=True, wait_kind="human_decision", wait_reason="User requested pause"
    )
    human = issue("human-1", "Decision pending", status="blocked")
    human.update(waiting=True, wait_kind="human_decision", wait_reason="Choose next direction")
    review = issue("review-1", "Review pending", status="blocked")
    review.update(waiting=True, wait_kind="review", wait_reason="Review source")
    dep = issue("dep-1", "Dependency pending", status="blocked")
    dep.update(waiting=True, wait_kind="dependency", wait_reason="Waiting for dependency")
    dep["dependencies"] = [
        {"id": "external-1", "title": "External task", "type": "blocks", "status": "open"}
    ]
    calc = issue("calc-1", "Calculation task", status="in_progress")
    calc["jobs"] = [
        {
            "root": "/tmp/desktop-fixture/runtime",
            "status": "running",
            "source_at": "2026-10-08T00:00:00+00:00",
            "result": "Exact child identity confirmed at collection",
            "result_code": "identity_confirmed",
        }
    ]
    unknown = issue("unknown-1", "Unknown activity")
    groups = [
        group(
            "codex:00000000-0000-0000-0000-000000000001",
            "English owner",
            "active",
            [first, current, closed],
            "alpha-2",
        ),
        group(
            "codex:00000000-0000-0000-0000-000000000002",
            "Paused owner",
            "idle",
            [paused],
            "pause-1",
        ),
        group(
            "codex:00000000-0000-0000-0000-000000000003",
            "Human owner",
            "notLoaded",
            [human],
            "human-1",
        ),
        group(
            "codex:00000000-0000-0000-0000-000000000004",
            "Review owner",
            "idle",
            [review],
            "review-1",
        ),
        group(
            "codex:00000000-0000-0000-0000-000000000005", "Dependency owner", "idle", [dep], "dep-1"
        ),
        group(
            "codex:00000000-0000-0000-0000-000000000006",
            "Calculation owner",
            "idle",
            [calc],
            "calc-1",
        ),
        group(
            "codex:00000000-0000-0000-0000-000000000007",
            "Unknown owner",
            "notLoaded",
            [unknown],
            "unknown-1",
        ),
    ]
    return {
        "generated_at": "2026-10-08T00:00:00+00:00",
        "beads_read_at": "2026-10-08T00:00:00+00:00",
        "groups": groups,
        "warnings": [],
        "warning_details": [],
        "counts": {"running_jobs": 1, "waiting_issues": 4, "human_decisions": 2},
    }


def main():
    output = Path(sys.argv[1])
    reloaded = len(sys.argv) > 2 and sys.argv[2] == "--reloaded"
    source = snapshot(reloaded)
    current = source["groups"][0]["issues"][1]
    record = {
        ("issue", "alpha-2", "title"): {
            "kind": "issue",
            "id": "alpha-2",
            "field": "title",
            "originalEnglishSHA256": dashboard.translations.sha(current["title"]),
            "ja": "現在の実装タスク",
        }
    }
    # The prior translation becomes stale after source changes on manual regeneration.
    if reloaded:
        record[("issue", "alpha-2", "title")]["originalEnglishSHA256"] = "0" * 64
    content = dashboard.render(source, translation_entries=record)
    dashboard.publish(output, content)
    print(len(content))


if __name__ == "__main__":
    main()
