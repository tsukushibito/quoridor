"""NN0 asset resolution contracts; only temporary synthetic files are read."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "research_assets", Path(__file__).with_name("research-assets.py")
)
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class AssetResolutionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.category = self.root / "assets/models"
        self.category.mkdir(parents=True)
        self.file = self.category / "sample.f32"
        self.file.write_bytes(b"synthetic")
        (self.root / "research-paths.json").write_text(
            json.dumps({"models": "assets/models", "asset_migration_manifest": "mapping.json"})
        )
        (self.root / "mapping.json").write_text(
            json.dumps(
                {
                    "assets": [
                        {
                            "old_path": "/old/input.f32",
                            "kind": "models",
                            "name": "sample.f32",
                            "bytes": 9,
                            "sha256": assets.sha256(self.file),
                        }
                    ]
                }
            )
        )

    def test_existing_category(self):
        self.assertEqual(assets.resolve_asset(self.root, "models", "sample.f32"), self.file)

    def test_missing_is_failure(self):
        with self.assertRaises(FileNotFoundError):
            assets.resolve_asset(self.root, "models", "absent")

    def test_traversal_and_absolute_rejected(self):
        for name in ["../input", "/absolute"]:
            with self.assertRaises(ValueError):
                assets.resolve_asset(self.root, "models", name)

    def test_symlink_escape_rejected(self):
        outside = self.root / "outside"
        outside.write_bytes(b"protected")
        (self.category / "escape").symlink_to(outside)
        with self.assertRaises(ValueError):
            assets.resolve_asset(self.root, "models", "escape")

    def test_legacy_mapping_and_changed_size(self):
        self.assertEqual(assets.resolve_legacy(self.root, "/old/input.f32"), self.file)
        self.file.write_bytes(b"different")
        with self.assertRaises(ValueError):
            assets.resolve_legacy(self.root, "/old/input.f32")
        self.file.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            assets.resolve_legacy(self.root, "/old/input.f32")

    def test_unmapped_does_not_fall_back(self):
        with self.assertRaises(ValueError):
            assets.resolve_legacy(self.root, "/old/unknown")


if __name__ == "__main__":
    unittest.main()
