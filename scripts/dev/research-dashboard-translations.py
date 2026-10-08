#!/usr/bin/env python3
"""Merge Japanese DISPLAY text bound to fresh read-only dashboard originals.

Run: python3 -B scripts/dev/research-dashboard-translations.py DELTA.json
Only one latest, disposable cache is published; canonical sources never change.
SHA256 is over the exact bounded English snapshot field encoded as UTF-8.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

CACHE_BYTES = 1048576
ENTRY_BYTES = 8192
ENTRY_LIMIT = 1024
ISSUE_FIELDS = frozenset({"title", "stage", "next_action", "wait_reason", "close_reason"})
MISSING = "未記入／確認不能"
PENDING = "日本語説明の更新待ち"


class TranslationError(ValueError):
    pass


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def catalog(snapshot):
    """Only currently displayed source text; never status, decisions or notes."""
    result = {}

    def add(kind, identity, field, value):
        key = (kind, identity, field)
        if key in result and result[key] != value:
            raise TranslationError("Conflicting displayed originals")
        result[key] = value

    for group in snapshot["groups"]:
        if group.get("name_supplied"):
            add("owner", group["owner"], "name", group["name"])
        for issue in group["issues"]:
            for field in issue["source_fields"]:
                add("issue", issue["id"], field, issue[field])
            for dependency in issue["dependencies"]:
                if dependency["title"]:
                    add("issue", dependency["id"], "title", dependency["title"])
    if len(result) > ENTRY_LIMIT:
        raise TranslationError("Displayed text exceeds entry bound")
    return result


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TranslationError("Duplicate JSON object key")
        result[key] = value
    return result


def decode(raw):
    if len(raw) > CACHE_BYTES:
        raise TranslationError("Translation JSON exceeds 1MiB")
    value = json.loads(raw, object_pairs_hook=object_pairs)
    if not isinstance(value, dict) or set(value) != {"version", "entries"}:
        raise TranslationError("Invalid translation envelope")
    entries = value["entries"]
    if type(value["version"]) is not int or value["version"] != 1:
        raise TranslationError("Unsupported translation version")
    if not isinstance(entries, list) or len(entries) > ENTRY_LIMIT:
        raise TranslationError("Invalid translation entry count")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "kind",
            "id",
            "field",
            "originalEnglishSHA256",
            "ja",
        }:
            raise TranslationError("Invalid translation record")
        kind, identity, field = entry["kind"], entry["id"], entry["field"]
        if kind not in ("owner", "issue") or not isinstance(identity, str):
            raise TranslationError("Invalid translation identity")
        if not identity or len(identity) > 160 or "\0" in identity:
            raise TranslationError("Invalid translation identity")
        if not isinstance(field, str) or field not in (
            {"name"} if kind == "owner" else ISSUE_FIELDS
        ):
            raise TranslationError("Forbidden translation field")
        original = entry["originalEnglishSHA256"]
        japanese = entry["ja"]
        if not isinstance(original, str) or not re.fullmatch(r"[0-9a-f]{64}", original):
            raise TranslationError("Invalid source SHA256")
        if (
            not isinstance(japanese, str)
            or not japanese.strip()
            or "\0" in japanese
            or len(japanese.encode("utf-8")) > ENTRY_BYTES
        ):
            raise TranslationError("Invalid bounded Japanese text")
        key = (kind, identity, field)
        if key in result:
            raise TranslationError("Duplicate translation identity/field")
        result[key] = entry
    return result


def read(path, *, missing_ok=False):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if missing_ok:
            return {}
        raise
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > CACHE_BYTES:
            raise TranslationError("Translation input is not a bounded regular file")
        raw = stream.read(CACHE_BYTES + 1)
    return decode(raw)


def encode(entries):
    value = {"version": 1, "entries": [entries[key] for key in sorted(entries)]}
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(raw) > CACHE_BYTES:
        raise TranslationError("Merged translation cache exceeds 1MiB")
    return raw


def merge(originals, previous, delta):
    # Validate the entire delta before any publication, including obsolete keys.
    for key, entry in delta.items():
        if key not in originals or entry["originalEnglishSHA256"] != sha(originals[key]):
            raise TranslationError("Delta does not match current displayed source: " + repr(key))
    result = {
        key: entry
        for key, entry in previous.items()
        if key in originals and entry["originalEnglishSHA256"] == sha(originals[key])
    }
    result.update(delta)
    return result


def display(snapshot, entries):
    originals = catalog(snapshot)
    pending = 0

    def field(kind, identity, name):
        nonlocal pending
        key = (kind, identity, name)
        if key not in originals:
            return MISSING
        entry = entries.get(key)
        if entry is not None and entry["originalEnglishSHA256"] == sha(originals[key]):
            return entry["ja"]
        pending += 1
        return PENDING

    owners = {g["owner"]: field("owner", g["owner"], "name") for g in snapshot["groups"]}
    issues = {}
    # Deduplicate dependency titles so pending is a field count, not a row count.
    identities = {issue["id"] for g in snapshot["groups"] for issue in g["issues"]} | {
        dependency["id"]
        for g in snapshot["groups"]
        for issue in g["issues"]
        for dependency in issue["dependencies"]
    }
    displayed = {issue["id"] for g in snapshot["groups"] for issue in g["issues"]}
    for identity in sorted(identities):
        fields = ISSUE_FIELDS if identity in displayed else {"title"}
        issues[identity] = {name: field("issue", identity, name) for name in sorted(fields)}
    return {"owner_names": owners, "issues": issues, "pending": pending}


def dashboard_module():
    spec = importlib.util.spec_from_file_location(
        "dashboard_translation_source", Path(__file__).with_name("research-dashboard.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def update(dashboard, ports, delta_path, cache_path):
    delta = read(delta_path)
    snapshot = dashboard.collect(ports)
    originals = catalog(snapshot)
    previous = read(cache_path, missing_ok=True)
    merged = merge(originals, previous, delta)
    dashboard.publish(cache_path, encode(merged), limit=CACHE_BYTES)
    return display(snapshot, merged)["pending"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delta", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--runtime-python", type=Path)
    args = parser.parse_args(argv)
    dashboard = dashboard_module()
    try:
        pending = update(
            dashboard,
            dashboard.Ports(args.root, args.runtime_python),
            args.delta,
            args.root / ".artifacts/research-dashboard/translations-ja.json",
        )
    except (OSError, ValueError, dashboard.CollectionError, subprocess.SubprocessError) as error:
        print(
            f"Translation cache not updated ({type(error).__name__}); old cache preserved",
            file=sys.stderr,
        )
        return 1
    print(f"Japanese DISPLAY cache updated; pending fields: {pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
