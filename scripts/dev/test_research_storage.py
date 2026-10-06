"""Capacity accounting must survive overlap, links, races and repeated observations."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "research_storage", Path(__file__).with_name("research-storage.py")
)
storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage)


class StorageTests(unittest.TestCase):
    def test_links_overlap_exclusion_and_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            kept = root / "kept"
            kept.mkdir()
            data = kept / "data"
            data.write_bytes(b"x" * 5000)
            os.link(data, kept / "alias")
            hidden = root / "hidden"
            hidden.mkdir()
            (hidden / "excluded").write_bytes(b"x" * 10000)
            (root / "reference").symlink_to(hidden, target_is_directory=True)
            entries = [
                {"name": "first", "path": str(root), "category": "a", "exclude": ["hidden"]},
                {"name": "overlap", "path": str(kept), "category": "b"},
            ]
            reserved = 100000
            result = storage.observe(
                entries, [{"category": "a", "reserved_bytes": reserved}], 1234, 200000
            )
            allocated = sum(p.lstat().st_blocks * 512 for p in [root, kept, data])
            self.assertEqual(result["retained_allocated_inode_bytes"], allocated)
            self.assertEqual(result["category_current_allocated_bytes"], {"a": allocated, "b": 0})
            self.assertEqual(result["current_plus_unused_known_bytes"], reserved + 1234)
            self.assertEqual(result["roots"][0]["files"], 1)
            self.assertEqual(result["roots"][0]["symlinks"], 1)
            self.assertEqual(result["roots"][1]["allocated_inode_bytes"], 0)
            self.assertEqual(result["admission"], "within")

    def test_cache_is_local_to_observation_and_excludes_are_per_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            child = root / "child"
            child.mkdir()
            data = child / "data"
            data.write_bytes(b"x")
            entries = [
                {"name": "excluded", "path": str(root), "category": "a", "exclude": ["child"]},
                {"name": "included", "path": str(root), "category": "b"},
            ]
            first = storage.observe(entries, unknown_retained_bytes=0)
            self.assertEqual(first["roots"][0]["files"], 0)
            self.assertEqual(first["roots"][1]["files"], 1)
            data.write_bytes(b"x" * 100000)
            second = storage.observe(entries, unknown_retained_bytes=0)
            self.assertGreater(
                second["retained_allocated_inode_bytes"], first["retained_allocated_inode_bytes"]
            )
            self.assertEqual(second["roots"][1]["logical_file_bytes"], 100000)

    def test_failed_metadata_cannot_admit_and_workers_preserve_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data").write_bytes(b"content")
            entries = [{"name": "files", "path": str(root), "category": "a"}]
            serial = storage.observe(entries, unknown_retained_bytes=0, metadata_workers=1)
            parallel = storage.observe(entries, unknown_retained_bytes=0, metadata_workers=8)
            for key in [
                "roots",
                "category_current_allocated_bytes",
                "current_plus_unused_known_bytes",
            ]:
                self.assertEqual(serial[key], parallel[key])
            with patch.object(
                storage.MetadataSnapshot, "entry_metadata", return_value=(None, FileNotFoundError)
            ):
                failed = storage.observe(entries, unknown_retained_bytes=0)
            self.assertEqual(failed["admission"], "unknown")
            self.assertEqual(failed["errors"][0]["error"], "missing/raced")
            self.assertTrue(failed["roots"][0]["missing"])
            self.assertEqual(storage.observe(entries)["admission"], "unknown")

    def test_capacity_and_invalid_manifest_are_not_relaxed(self):
        with tempfile.TemporaryDirectory() as folder:
            entries = [{"name": "root", "path": folder, "category": "a"}]
            result = storage.observe(entries, unknown_retained_bytes=100, cap_bytes=0)
            self.assertEqual(result["admission"], "over")
            with self.assertRaises(ValueError):
                storage.observe(
                    entries,
                    [{"category": "a", "reserved_bytes": 0}] * 2,
                    unknown_retained_bytes=0,
                )
            with self.assertRaises(ValueError):
                storage.observe(entries, metadata_workers=0)


if __name__ == "__main__":
    unittest.main()
