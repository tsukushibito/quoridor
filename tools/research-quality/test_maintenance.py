"""NN0 maintenance contracts using owned temporary repositories and files.

Project HEAD/index are never mutated. All fixture Git operations, hardlinks,
symlinks, staged changes and deletions live inside TemporaryDirectory.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/dev" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAVE = load_module("research_save_fixture_contract", "research-save.py")
STORAGE = load_module("research_storage_fixture_contract", "research-storage.py")
GIT_CONTEXT = ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE")


class SaveContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        environment = dict(os.environ)
        for key in GIT_CONTEXT:
            environment.pop(key, None)
        self.environment = environment
        self.git("init", "--quiet")
        (self.repo / "tracked.py").write_text("value = 1\n")
        (self.repo / ".gitignore").write_text("ignored/\n")
        self.git("add", "--", "tracked.py", ".gitignore")
        self.git("commit", "--quiet", "-m", "Synthetic maintenance fixture")
        (self.repo / "tracked.py").write_text("value = 2\n")
        self.env_patch = patch.dict(os.environ, environment, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def git(self, *args):
        # All mutations target this isolated repository, never ROOT.
        command = [
            "git",
            "-C",
            str(self.repo),
            "-c",
            "user.name=Maintenance Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            *args,
        ]
        return subprocess.run(
            command, check=True, capture_output=True, timeout=10, env=self.environment
        ).stdout

    def snapshot(self):
        return {
            "head": self.git("rev-parse", "HEAD"),
            "index": hashlib.sha256((self.repo / ".git/index").read_bytes()).hexdigest(),
        }

    def test_normal_index_check_is_readonly(self):
        before = self.snapshot()
        result = SAVE.inspect(self.repo, ["tracked.py"], 8192)
        self.assertEqual(result["paths"][0]["path"], "tracked.py")
        self.assertTrue(result["paths"][0]["tracked"])
        self.assertEqual(result["logical_file_bytes"], len(b"value = 2\n"))
        self.assertEqual(self.snapshot(), before)
        paths = self.repo / "explicit-paths.json"
        paths.write_text(json.dumps(["tracked.py"]))
        command = [
            sys.executable,
            "-B",
            str(ROOT / "scripts/dev/research-save.py"),
            "check",
            "--root",
            str(self.repo),
            "--paths-file",
            str(paths),
            "--max-new-bytes",
            "8192",
        ]
        process = subprocess.run(command, capture_output=True, check=True, timeout=10)
        self.assertEqual(json.loads(process.stdout)["head"], before["head"].decode().strip())
        self.assertEqual(self.snapshot(), before)

    def test_foreign_staged_change_is_retained_and_rejected(self):
        (self.repo / "foreign.py").write_text("foreign = True\n")
        self.git("add", "--", "foreign.py")
        before = self.snapshot()
        with self.assertRaises(SAVE.SaveError):
            SAVE.inspect(self.repo, ["tracked.py"], 8192)
        self.assertEqual(self.snapshot(), before)
        self.assertIn(b"foreign.py", self.git("diff", "--cached", "--name-only"))

    def test_private_index_environment_is_rejected(self):
        before = self.snapshot()
        for key in GIT_CONTEXT:
            with (
                self.subTest(key=key),
                patch.dict(os.environ, {key: str(self.root / "private.index")}),
            ):
                with self.assertRaises(SAVE.SaveError):
                    SAVE.inspect(self.repo, ["tracked.py"], 8192)
        self.assertEqual(self.snapshot(), before)

    def test_temp_index_and_runtime_paths_are_rejected(self):
        names = [
            "private.index",
            "private-index",
            "private-index.lock",
            "payload.tmp",
            ":memory:.ses",
            "model.ses",
            ".artifacts/receipt.json",
            "node_modules/package.js",
            "__pycache__/cache.pyc",
        ]
        before = self.snapshot()
        for name in names:
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic protected file\n")
            with self.subTest(name=name), self.assertRaises(SAVE.SaveError):
                SAVE.inspect(self.repo, [name], 8192)
            self.assertEqual(self.snapshot(), before)
        # A reproducibility dependency lock is intentionally allowed.
        (self.repo / "Cargo.lock").write_text("# synthetic lock only\n")
        self.assertEqual(
            SAVE.inspect(self.repo, ["Cargo.lock"], 8192)["paths"][0]["path"], "Cargo.lock"
        )

    def test_ignored_unknown_missing_and_directory_paths_are_rejected(self):
        ignored = self.repo / "ignored/data.json"
        ignored.parent.mkdir()
        ignored.write_text("{}")
        for name in ["ignored/data.json", "unknown.py", "ignored", "../outside.py", str(ignored)]:
            with self.subTest(name=name), self.assertRaises(SAVE.SaveError):
                SAVE.inspect(self.repo, [name], 8192)
        (self.repo / "tracked.py").unlink()
        result = SAVE.inspect(self.repo, ["tracked.py"], 8192)
        self.assertTrue(result["paths"][0]["deleted"])
        self.assertEqual(result["logical_file_bytes"], 0)

    def test_parent_symlink_cannot_escape_the_checkout(self):
        external = self.root / "external"
        external.mkdir()
        (external / "source.py").write_text("outside = True\n")
        (self.repo / "linked").symlink_to(external, target_is_directory=True)
        before = self.snapshot()
        with self.assertRaises(SAVE.SaveError):
            SAVE.inspect(self.repo, ["linked/source.py"], 8192)
        self.assertEqual(self.snapshot(), before)

    def test_git_pathspec_magic_is_not_an_explicit_file(self):
        before = self.snapshot()
        with self.assertRaises(SAVE.SaveError):
            SAVE.inspect(self.repo, [":(glob)*.py"], 8192)
        self.assertEqual(self.snapshot(), before)

    def test_git_forecast_must_fit_the_admission(self):
        # Source/object/metadata forecast, not logical bytes alone, must fit.
        result = SAVE.inspect(self.repo, ["tracked.py"], 8192)
        forecast = result["git_forecast_upper_bytes"]
        self.assertGreaterEqual(forecast, 2 * len(b"value = 2\n"))
        with self.assertRaises(SAVE.SaveError):
            SAVE.inspect(self.repo, ["tracked.py"], forecast - 1)
        self.assertEqual(
            SAVE.inspect(self.repo, ["tracked.py"], forecast)["git_forecast_upper_bytes"], forecast
        )


class StorageContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.file = self.root / "held.bin"
        self.file.write_bytes(b"x" * 8192)

    def entry(self, name, path, category="research"):
        return {"name": name, "path": str(path), "category": category}

    def test_hardlinked_inode_is_charged_once_across_roots(self):
        alias = self.root / "alias.bin"
        os.link(self.file, alias)
        current = self.file.stat().st_blocks * 512
        result = STORAGE.observe(
            [self.entry("original", self.file), self.entry("alias", alias)],
            unknown_retained_bytes=0,
        )
        self.assertEqual(result["retained_allocated_inode_bytes"], current)
        self.assertEqual(result["roots"][1]["allocated_inode_bytes"], 0)
        self.assertEqual(result["roots"][1]["overlap_allocated_bytes"], current)
        self.assertEqual(result["admission"], "within")

    def test_nested_scope_overlap_does_not_add_a_second_charge(self):
        subtree = self.root / "nested"
        subtree.mkdir()
        (subtree / "child.bin").write_bytes(b"y" * 4096)
        baseline = STORAGE.observe([self.entry("whole", self.root)], unknown_retained_bytes=0)
        result = STORAGE.observe(
            [self.entry("whole", self.root), self.entry("nested", subtree)],
            unknown_retained_bytes=0,
        )
        self.assertEqual(
            result["retained_allocated_inode_bytes"], baseline["retained_allocated_inode_bytes"]
        )
        self.assertEqual(result["roots"][1]["allocated_inode_bytes"], 0)
        self.assertGreater(result["roots"][1]["overlap_allocated_bytes"], 0)

    def test_actual_files_inside_reservation_are_not_charged_twice(self):
        current = self.file.stat().st_blocks * 512
        reservation = current + 4096
        result = STORAGE.observe(
            [self.entry("held", self.file)],
            [{"category": "research", "reserved_bytes": reservation}],
            unknown_retained_bytes=1024,
            cap_bytes=reservation + 1024,
        )
        self.assertEqual(result["reservations"][0]["unused_bytes"], 4096)
        self.assertEqual(result["current_plus_unused_known_bytes"], reservation + 1024)
        self.assertEqual(result["admission"], "within")
        overflow = STORAGE.observe(
            [self.entry("held", self.file)],
            [{"category": "research", "reserved_bytes": current // 2}],
            unknown_retained_bytes=0,
            cap_bytes=current - 1,
        )
        self.assertEqual(overflow["reservations"][0]["unused_bytes"], 0)
        self.assertEqual(overflow["current_plus_unused_known_bytes"], current)
        self.assertEqual(overflow["admission"], "over")

    def test_unknown_is_never_free_even_if_known_files_fit(self):
        current = self.file.stat().st_blocks * 512
        unknown = STORAGE.observe([self.entry("held", self.file)], cap_bytes=current * 2)
        self.assertEqual(unknown["admission"], "unknown")
        self.assertFalse(unknown["unknown_is_free"])
        retained = STORAGE.observe(
            [self.entry("held", self.file)],
            unknown_retained_bytes=current,
            cap_bytes=current,
        )
        self.assertEqual(retained["admission"], "over")
        missing = STORAGE.observe(
            [self.entry("unknown", self.root / "missing")],
            unknown_retained_bytes=0,
            cap_bytes=1,
        )
        self.assertEqual(missing["admission"], "unknown")
        self.assertTrue(missing["errors"])

    def test_symlink_is_a_reference_not_a_second_traversal(self):
        alias = self.root / "linked.bin"
        alias.symlink_to(self.file)
        current = self.file.stat().st_blocks * 512
        result = STORAGE.observe(
            [self.entry("held", self.file), self.entry("reference", alias)],
            unknown_retained_bytes=0,
        )
        self.assertEqual(result["retained_allocated_inode_bytes"], current)
        self.assertEqual(result["roots"][1]["symlinks"], 1)

    def test_duplicate_reservations_and_invalid_amounts_are_not_admitted(self):
        roots = [self.entry("held", self.file)]
        with self.assertRaises(ValueError):
            STORAGE.observe(
                roots,
                [
                    {"category": "research", "reserved_bytes": 16384},
                    {"category": "research", "reserved_bytes": 16384},
                ],
                unknown_retained_bytes=0,
            )
        for options in [
            {"unknown_retained_bytes": -1},
            {"unknown_retained_bytes": False},
            {"cap_bytes": -1},
            {"cap_bytes": True},
            {"reservations": [{"category": "research", "reserved_bytes": -1}]},
        ]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                STORAGE.observe(roots, **options)


if __name__ == "__main__":
    unittest.main()
