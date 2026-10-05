"""NN0 current learner tests: configuration/input factory boundaries only."""

import ast
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from learner import (
    SOURCE_FILES,
    argument_parser,
    source_bindings,
    train,
    validate_checkpoint_scaling,
)
from scaled_model import load_statistics, validate_statistics
from test_input_contract import row


class LearnerEntryTests(unittest.TestCase):
    def test_explicit_scale_float32_and_invalid_sigma(self):
        stats = validate_statistics({"mu_f32": [0.1, 0.2], "sigma_f32": [1, 0.5]})
        self.assertEqual(stats["mu_f32"], [0.10000000149011612, 0.20000000298023224])
        for difference in [
            {"sigma_f32": [0, 1]},
            {"sigma_f32": [1e-100, 1]},
            {"sigma_f32": [-1, 1]},
            {"sigma_f32": [float("nan"), 1]},
            {"mu_f32": [1e100, 0]},
            {"mu_f32": [True, 0]},
            {"mu_f32": [0]},
        ]:
            with self.subTest(difference=difference), self.assertRaises(ValueError):
                validate_statistics({**stats, **difference})

    def test_scale_is_explicit_and_bound_to_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scale.json"
            path.write_text(
                json.dumps({"mu_f32": [0, 0.5], "sigma_f32": [1, 1], "version": "synthetic-only"})
            )
            stats, info = load_statistics(path)
            self.assertEqual(stats["sigma_f32"], [1, 1])
            self.assertEqual(info["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(info["statistics_estimated"])
            with self.assertRaises(FileNotFoundError):
                load_statistics(Path(directory) / "not-provided")

    def test_dry_run_does_not_call_model_factory_or_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            rows = [
                {**row("a", "train"), "rootmean": 0.25},
                {**row("b", "validation", distance=[0.3, 0.4]), "rootmean": 0.5},
            ]
            data = directory / "synthetic.json"
            data.write_text(json.dumps(rows))
            stats = directory / "scale.json"
            stats.write_text(json.dumps({"mu_f32": [0.1, 0.2], "sigma_f32": [1, 1]}))
            output, weights = directory / "runs", directory / "weights"
            base = [
                "--data",
                str(data),
                "--run-id",
                "synthetic",
                "--output",
                str(output),
                "--checkpoints",
                str(weights),
                "--dry-run",
            ]
            for options in ([], ["--scale-statistics", str(stats)]):
                args = argument_parser().parse_args(base + options)
                with redirect_stdout(io.StringIO()) as captured:
                    train(
                        args, model_factory=lambda *_: self.fail("NN0 must not construct a model")
                    )
                result = json.loads(captured.getvalue())
                self.assertEqual(result["data"]["counts"], {"train": 1, "validation": 1})
                self.assertEqual(result["constant"], 0.25)
                self.assertEqual(result["scaling"] is not None, bool(options))
            self.assertFalse(output.exists())
            self.assertFalse(weights.exists())
            self.assertNotIn("torch", sys.modules)

    def test_checkpoint_scale_cannot_be_silently_reinterpreted(self):
        validate_checkpoint_scaling({}, None)  # Existing raw checkpoints stay valid.
        validate_checkpoint_scaling({"scaling_sha256": "a"}, {"sha256": "a"})
        for checkpoint, scale in [
            ({}, {"sha256": "a"}),
            ({"scaling_sha256": "b"}, {"sha256": "a"}),
            ({"scaling_sha256": "a"}, None),
        ]:
            with self.assertRaises(ValueError):
                validate_checkpoint_scaling(checkpoint, scale)

    def test_current_entry_has_no_frame_loader_or_ast_patch(self):
        tree = ast.parse(Path(__file__).with_name("learner.py").read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(module and module.startswith("frame") for module in imports))
        imported_names = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        self.assertNotIn("ast", imported_names)
        self.assertNotIn("loader", imported_names)

    def test_source_binding_covers_current_model_and_data_closure(self):
        bindings = source_bindings()
        self.assertEqual({Path(path).name for path in bindings}, set(SOURCE_FILES))
        for path, digest in bindings.items():
            self.assertEqual(digest, hashlib.sha256(Path(path).read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            factory = Path(directory) / "model.py"
            factory.write_text("# synthetic factory source only\n")
            expanded = source_bindings([factory])
            self.assertEqual(len(expanded), len(SOURCE_FILES) + 1)


if __name__ == "__main__":
    unittest.main()
