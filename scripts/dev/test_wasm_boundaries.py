"""Offline Wasm feature-boundary fixtures; no compiler or model imports."""

import copy
import importlib.util
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "wasm_boundaries", ROOT / "scripts/check-boundaries.py"
)
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)

# A minimal independent Cargo fixture keeps this suite compiler-free.
SOURCE = """
[features]
default = []
rules = [
  "dep:serde",
]
ai = ["dep:quoridor-ai"]
nnue = ["ai", "dep:quoridor-nnue", "quoridor-ai/research"]
[dependencies]
serde = { version = "1", optional = true }
quoridor-ai = { path = "../ai", optional = true }
quoridor-nnue = { path = "../nnue", optional = true }
"""


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = tomllib.loads(SOURCE)

    def test_multiline_separation_and_current_source(self):
        boundary.check_boundary(self.manifest)
        # Current maintained manifest remains unchanged by this repair.
        main = Path(__file__).resolve()
        while not (main / "crates/quoridor-wasm/Cargo.toml").is_file():
            parent = main.parent
            if parent == main:
                self.fail("Current Wasm manifest not found")
            main = parent
        with (main / "crates/quoridor-wasm/Cargo.toml").open("rb") as source:
            boundary.check_boundary(tomllib.load(source))

    def test_direct_transitive_dependency_feature_and_default_inclusion_refused(self):
        for entry in ("dep:quoridor-ai", "ai", "nnue", "quoridor-ai/research", "dep:quoridor-nnue"):
            with self.subTest(entry=entry):
                value = copy.deepcopy(self.manifest)
                value["features"]["rules"].append(entry)
                with self.assertRaises(boundary.BoundaryError):
                    boundary.check_boundary(value)
        self.manifest["features"]["default"] = ["ai"]
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(self.manifest)

    def test_unknown_aliases_and_non_optional_ai_refused(self):
        for entry in ("typo", "dep:missing", "missing/research", "quoridor-ai/"):
            value = copy.deepcopy(self.manifest)
            value["features"]["rules"].append(entry)
            with self.assertRaises(boundary.BoundaryError):
                boundary.check_boundary(value)
        self.manifest["dependencies"]["quoridor-ai"]["optional"] = False
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(self.manifest)

    def test_cycles_and_weak_features_do_not_enable_optional_ai(self):
        self.manifest["features"].update({"first": ["second"], "second": ["first"]})
        self.manifest["features"]["rules"].extend(["first", "quoridor-ai?/research"])
        boundary.check_boundary(self.manifest)

    def test_renamed_ai_dependency_refused_from_rules(self):
        self.manifest["dependencies"]["engine"] = {"package": "quoridor-ai", "optional": True}
        self.manifest["features"]["rules"].append("dep:engine")
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(self.manifest)

    def renamed(self):
        value = copy.deepcopy(self.manifest)
        for package, key in (("quoridor-ai", "engine"), ("quoridor-nnue", "evaluator")):
            config = value["dependencies"].pop(package)
            value["dependencies"][key] = dict(config, package=package)
            for items in value["features"].values():
                for index, item in enumerate(items):
                    items[index] = item.replace(package, key)
        return value

    def test_full_ai_and_nnue_renames_preserve_package_boundary(self):
        value = self.renamed()
        boundary.check_boundary(value)
        for entry in ("ai", "dep:engine", "engine/research", "dep:evaluator"):
            invalid = copy.deepcopy(value)
            invalid["features"]["rules"].append(entry)
            with self.subTest(entry=entry), self.assertRaises(boundary.BoundaryError):
                boundary.check_boundary(invalid)
        value["features"]["default"] = ["ai"]
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(value)

    def test_ai_route_requires_real_ai_package_after_full_rename(self):
        value = self.renamed()
        value["features"]["ai"] = ["dep:evaluator"]
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(value)
        value = self.renamed()
        value["dependencies"]["engine"]["package"] = "unrelated"
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(value)
        value["dependencies"]["quoridor-ai"] = {"package": "unrelated", "optional": True}
        with self.assertRaises(boundary.BoundaryError):
            boundary.check_boundary(value)


if __name__ == "__main__":
    unittest.main()
