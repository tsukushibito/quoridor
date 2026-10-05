#!/usr/bin/env python3
"""Inspect or save an explicit writer handoff using the normal Git index.

The project Git owner invokes save only after all relevant writers have stopped.
Checks leave the index untouched. Failed commits retain staged paths for review;
this tool never resets an index or advances HEAD through a private index.
"""

from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess


class SaveError(ValueError):
    pass


def git(root, *args, binary=False):
    result = subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(root), *args],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return result.stdout if binary else result.stdout.decode().strip()


def inspect(root, paths, max_bytes):
    root = Path(root).resolve()
    for key in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
        if os.environ.get(key):
            raise SaveError("Normal checkout/index required: " + key)
    if git(root, "rev-parse", "--show-toplevel") != str(root):
        raise SaveError("Use the checkout root")
    if git(root, "diff", "--cached", "--name-only", "-z"):
        raise SaveError("Existing staged changes: Git owner must review them first")
    if not paths or len(set(paths)) != len(paths):
        raise SaveError("An explicit nonempty unique path list is required")
    result = []
    total = 0
    for name in paths:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise SaveError("Relative file paths only: " + name)
        if any(
            p in {".git", ".worktree", ".artifacts", "node_modules", "__pycache__", ".venv"}
            for p in path.parts
        ):
            raise SaveError("Runtime/dependency path is not source preservation: " + name)
        if (
            path.name == ":memory:.ses"
            or path.suffix in {".tmp", ".ses"}
            or (
                path.suffix == ".lock"
                and path.name not in {"Cargo.lock", "uv.lock", "poetry.lock", "pdm.lock"}
            )
        ):
            raise SaveError("Temporary/index/lock file is protected: " + name)
        if (
            path.name in {"index", "private.index", "private-index"}
            or path.suffix == ".index"
            or name.startswith(":")
        ):
            raise SaveError("Index/pathspec state is protected: " + name)
        file = root / path
        if not file.resolve().is_relative_to(root):
            raise SaveError("Path escapes checkout through symlink: " + name)
        if file.is_symlink() or (file.exists() and not file.is_file()):
            raise SaveError("Review symlinks/directories explicitly: " + name)
        # A deleted tracked file may be intentionally included, never an unknown missing path.
        tracked = bool(git(root, "ls-files", "--", name))
        if not file.exists() and not tracked:
            raise SaveError("Missing untracked path: " + name)
        ignore_result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "check-ignore",
                "--quiet",
                "--",
                name,
            ],
            timeout=10,
        )
        if ignore_result.returncode not in (0, 1):
            raise SaveError("Cannot determine ignore status: " + name)
        ignored = ignore_result.returncode == 0
        if ignored and not tracked:
            raise SaveError(
                "Ignored live/input data requires separate preservation review: " + name
            )
        size = file.stat().st_size if file.exists() else 0
        total += size
        result.append(
            {"path": name, "bytes": size, "tracked": tracked, "deleted": not file.exists()}
        )
    forecast = total * 2 + len(paths) * 4096
    if forecast > max_bytes:
        raise SaveError(f"New object forecast exceeds admission: {forecast} > {max_bytes}")
    return {
        "head": git(root, "rev-parse", "HEAD"),
        "index": "normal; unstaged",
        "paths": result,
        "logical_file_bytes": total,
        "git_forecast_upper_bytes": forecast,
    }


@contextmanager
def exclusive(root):
    directory = root / ".artifacts"
    directory.mkdir(exist_ok=True)
    with (directory / "research-git.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def save(root, paths, max_bytes, issue, actor, message, writers_stopped):
    if not writers_stopped:
        raise SaveError("Writer stop handoff required")
    data = subprocess.run(
        ["bash", str(root / "scripts/dev/beads.sh"), "show", issue, "--json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    item = json.loads(data.stdout)[0]
    if (
        item.get("assignee") != actor
        or item.get("status") != "in_progress"
        or "paused-by-user" in item.get("labels", [])
    ):
        raise SaveError("Only the active issue's assigned Git owner may save")
    with exclusive(root):
        result = inspect(root, paths, max_bytes)
        git(root, "add", "--", *paths)
        git(root, "commit", "-m", message)
        if git(root, "diff", "--cached", "--name-only"):
            raise SaveError("Commit left staged changes; retain and review")
        result["commit"] = git(root, "rev-parse", "HEAD")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "save"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--paths-file", type=Path, required=True, help="JSON list of explicit relative files"
    )
    parser.add_argument("--max-new-bytes", type=int, default=512 * 1024**2)
    parser.add_argument("--issue")
    parser.add_argument("--actor")
    parser.add_argument("--message")
    parser.add_argument("--writers-stopped", action="store_true")
    args = parser.parse_args()
    paths = json.loads(args.paths_file.read_text())
    if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
        parser.error("Paths must be a JSON string list")
    if args.command == "save":
        if not all((args.issue, args.actor, args.message)):
            parser.error("save requires --issue, --actor, --message")
        result = save(
            args.root,
            paths,
            args.max_new_bytes,
            args.issue,
            args.actor,
            args.message,
            args.writers_stopped,
        )
    else:
        result = inspect(args.root, paths, args.max_new_bytes)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
