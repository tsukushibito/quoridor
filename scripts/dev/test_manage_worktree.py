#!/usr/bin/env python3
"""Worktree management regressions using isolated Git repositories only."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name("manage_worktree.sh")


class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="quoridor-worktree-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "main repo"
        self.root.mkdir()
        self.run_git("init", "--initial-branch=main")
        self.run_git("config", "user.name", "Fixture")
        self.run_git("config", "user.email", "fixture@example.invalid")
        self.script = self.root / "scripts/dev/manage_worktree.sh"
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE, self.script)
        (self.root / ".gitignore").write_text(".worktree/\n", encoding="utf-8")
        self.run_git("add", "scripts/dev/manage_worktree.sh", ".gitignore")
        self.run_git("commit", "--quiet", "-m", "fixture")

    def run_git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

    def helper(self, *args, checkout=None, check=True):
        checkout = checkout or self.root
        return subprocess.run(
            ["bash", str(checkout / "scripts/dev/manage_worktree.sh"), *args],
            cwd=self.temporary.name,
            capture_output=True,
            text=True,
            check=check,
            timeout=15,
        )

    def test_linked_helper_uses_main_managed_root(self):
        self.helper("create", "first", "fixture/first")
        first = self.root / ".worktree/first"
        self.helper("create", "second", "fixture/second", checkout=first)
        second = self.root / ".worktree/second"
        self.assertTrue(second.is_dir())
        self.assertFalse((first / ".worktree").exists())
        records = self.run_git("worktree", "list", "--porcelain").stdout
        self.assertEqual(records.count("locked managed by quoridor"), 2)
        self.helper("verify", checkout=first)
        self.helper("remove", "second", checkout=first)
        self.assertFalse(second.exists())
        self.run_git("show-ref", "--verify", "refs/heads/fixture/second")

    def test_verify_and_lock_existing_from_linked_checkout(self):
        self.helper("create", "first", "fixture/first")
        first = self.root / ".worktree/first"
        self.run_git("worktree", "unlock", str(first))
        failure = self.helper("verify", checkout=first, check=False)
        self.assertNotEqual(failure.returncode, 0)
        self.assertIn(str(first), failure.stderr)
        self.helper("lock-existing", checkout=first)
        self.helper("verify")

    def test_dirty_removal_refused_and_branch_preserved(self):
        self.helper("create", "first", "fixture/first")
        first = self.root / ".worktree/first"
        (first / "unsaved.txt").write_text("must survive", encoding="utf-8")
        failure = self.helper("remove", "first", check=False)
        self.assertNotEqual(failure.returncode, 0)
        self.assertIn("Refusing to remove dirty worktree", failure.stderr)
        self.assertEqual((first / "unsaved.txt").read_text(), "must survive")
        self.assertIn(
            "locked managed by quoridor",
            self.run_git("worktree", "list", "--porcelain").stdout,
        )
        self.run_git("show-ref", "--verify", "refs/heads/fixture/first")

    def test_sparse_creation_from_linked_checkout(self):
        self.helper("create", "first", "fixture/first")
        first = self.root / ".worktree/first"
        self.helper("create-sparse", "sparse", "fixture/sparse", "HEAD", "scripts", checkout=first)
        sparse = self.root / ".worktree/sparse"
        self.assertTrue((sparse / "scripts/dev/manage_worktree.sh").is_file())
        self.helper("verify", checkout=sparse)

    def test_invalid_names_refused(self):
        for name in ("..", ".", "../escape", "/absolute"):
            failure = self.helper("create", name, "fixture/no", check=False)
            self.assertEqual(failure.returncode, 2)
        self.assertFalse((self.root / ".worktree").exists())


if __name__ == "__main__":
    unittest.main()
