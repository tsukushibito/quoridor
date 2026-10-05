#!/usr/bin/env python3
"""Directed current storage accounting. No deletions, history scan or reservation reset."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat


def observe(entries, reservations=(), unknown_retained_bytes=None, cap_bytes=None):
    categories = [r["category"] for r in reservations]
    if len(categories) != len(set(categories)):
        raise ValueError("RESERVATION_CATEGORY_DUPLICATE: split categories by owner/scope first")
    for number in [r["reserved_bytes"] for r in reservations] + [unknown_retained_bytes, cap_bytes]:
        if number is not None and (type(number) is not int or number < 0):
            raise ValueError("Storage amounts must be known nonnegative integer bytes or null")
    seen = {}
    rows = []
    errors = []
    category_current = {}
    for entry in entries:
        root = Path(entry["path"])
        exclude = set(entry.get("exclude", []))
        row = {
            **entry,
            "logical_file_bytes": 0,
            "allocated_inode_bytes": 0,
            "overlap_allocated_bytes": 0,
            "files": 0,
            "symlinks": 0,
            "missing": False,
        }
        stack = [root]
        local = set()
        while stack:
            path = stack.pop()
            try:
                info = path.lstat()
                identity = (info.st_dev, info.st_ino)
                if identity in local:
                    continue
                local.add(identity)
                if stat.S_ISLNK(info.st_mode):
                    row["symlinks"] += 1
                    continue  # Asset links are references, not a second traversal.
                if stat.S_ISDIR(info.st_mode):
                    with os.scandir(path) as children:
                        stack.extend(
                            Path(child.path) for child in children if child.name not in exclude
                        )
                if stat.S_ISREG(info.st_mode):
                    row["logical_file_bytes"] += info.st_size
                    row["files"] += 1
                allocated = info.st_blocks * 512
                if identity in seen:
                    row["overlap_allocated_bytes"] += allocated
                else:
                    seen[identity] = entry["name"]
                    row["allocated_inode_bytes"] += allocated
            except FileNotFoundError:
                row["missing"] = True
                errors.append({"path": str(path), "error": "missing/raced"})
            except OSError as error:
                errors.append({"path": str(path), "error": type(error).__name__})
        rows.append(row)
        category_current[entry["category"]] = (
            category_current.get(entry["category"], 0) + row["allocated_inode_bytes"]
        )
    unused = []
    for reservation in reservations:
        category = reservation["category"]
        # The reservation contains actual held files; charge only its still unused part.
        allocated = category_current.get(category, 0)
        unused.append(
            {
                **reservation,
                "current_allocated_bytes": allocated,
                "unused_bytes": max(0, reservation["reserved_bytes"] - allocated),
            }
        )
    retained = sum(category_current.values())
    known_total = retained + sum(r["unused_bytes"] for r in unused)
    if unknown_retained_bytes is not None:
        known_total += unknown_retained_bytes
    complete = not errors and unknown_retained_bytes is not None
    status = (
        "unknown"
        if not complete
        else "within"
        if cap_bytes is None or known_total <= cap_bytes
        else "over"
    )
    return {
        "schema": "quoridor-current-storage-v1",
        "at": datetime.now(timezone.utc).isoformat(),
        "metric": "unique dev/inode st_blocks; reflink shared physical extents unknown",
        "roots": rows,
        "category_current_allocated_bytes": category_current,
        "retained_allocated_inode_bytes": retained,
        "reservations": unused,
        "unknown_retained_bytes": unknown_retained_bytes,
        "current_plus_unused_known_bytes": known_total,
        "cap_bytes": cap_bytes,
        "admission": status,
        "errors": errors,
        "past_peak_bytes": "not added to current; refer to original run receipts",
        "unknown_is_free": False,
        "deleted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest", type=Path, help="Explicit directed roots/category/reservation JSON"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = json.loads(args.manifest.read_text())
    result = observe(
        config["roots"],
        config.get("reservations", []),
        config.get("unknown_retained_bytes"),
        config.get("cap_bytes"),
    )
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "at",
                    "retained_allocated_inode_bytes",
                    "current_plus_unused_known_bytes",
                    "admission",
                    "errors",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
