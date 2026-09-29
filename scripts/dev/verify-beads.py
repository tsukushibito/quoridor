#!/usr/bin/env python3
"""Verify shared access, serialization, and full backup restoration locally."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
COMMON = Path(subprocess.check_output(
    ["git", "-C", str(HERE), "rev-parse", "--path-format=absolute", "--git-common-dir"], text=True).strip())
ROOT = COMMON.parent
WRAPPER = HERE / "beads.sh"
BD = Path.home() / ".local/bin/bd"


def run(command, **kwargs):
    return subprocess.check_output(command, text=True, **kwargs)


def bd(*args, cwd=ROOT):
    return run(["bash", str(WRAPPER), *args], cwd=cwd)


def main():
    original = json.loads(bd("list", "--all", "--limit", "0", "--json"))
    if not original:
        raise SystemExit("Register a real project task before verifying restoration.")
    # Calling the helpers stored in the main checkout and the current worktree
    # must resolve the same data, independently of cwd.
    main_wrapper = ROOT / "scripts/dev/beads.sh"
    main_view = json.loads(run(["bash", str(main_wrapper), "list", "--all", "--limit", "0", "--json"], cwd=HERE))
    assert main_view == original, "Main checkout and worktree disagree"
    with (ROOT / ".worktree/.beads-access.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        process = subprocess.Popen(["bash", str(WRAPPER), "ready", "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            time.sleep(0.3)
            assert process.poll() is None, "CLI bypassed shared access lock"
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
        stdout, stderr = process.communicate(timeout=60)
        assert process.returncode == 0, stderr
        json.loads(stdout)
    bd("backup", "sync")
    # Hold the source lock while comparing its snapshot with an isolated restore.
    with (ROOT / ".worktree/.beads-access.lock").open("a") as lock, tempfile.TemporaryDirectory(prefix="quoridor-beads-restore-") as directory:
        fcntl.flock(lock, fcntl.LOCK_EX)
        source_env = dict(os.environ, BEADS_DIR=str(ROOT / ".worktree/.beads-state"), BD_NON_INTERACTIVE="1")
        # Sync again under the held lock so later comparisons use this snapshot.
        run([str(BD), "--sandbox", "backup", "sync"], env=source_env)
        source = json.loads(run([str(BD), "--sandbox", "list", "--all", "--limit", "0", "--json"], env=source_env))
        env = dict(source_env, BEADS_DIR=str(Path(directory) / ".beads"))
        def restored(*args):
            return run([str(BD), "--sandbox", *args], env=env, cwd=directory)
        restored("init", "--stealth", "--skip-agents", "--skip-hooks", "--non-interactive", "--prefix", "quoridor")
        restored("backup", "restore", "--force", str(ROOT / ".artifacts/beads-backup"))
        assert json.loads(restored("list", "--all", "--limit", "0", "--json")) == source
        for issue in source:
            for command in ["show", "history"]:
                expected = json.loads(run([str(BD), "--sandbox", command, issue["id"], "--json"], env=source_env))
                actual = json.loads(restored(command, issue["id"], "--json"))
                assert actual == expected, f"Restored {command} differs: {issue['id']}"
    print(json.dumps({"issues": len(source), "shared_access": "passed", "serialization": "passed",
                      "full_restore_issues_dependencies_history": "passed"}, indent=2))


if __name__ == "__main__":
    main()
