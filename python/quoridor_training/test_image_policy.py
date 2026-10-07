"""Image policy with isolated actual persistence and explicit CLI; no forwards."""

import ast
import csv
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import MagicMock, patch

import numpy as np


SOURCE = Path(os.environ.get("QUORIDOR_IMAGE_POLICY_SOURCE_ROOT", Path(__file__).parent))


def plotting_module():
    spec = importlib.util.spec_from_file_location("image_policy_plotting", SOURCE / "plotting.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def point(step, diagnostic=False):
    metric = {"target_mse": 0.42744088098494515, "target_game_equal_mse": 0.5, "rows": 2}
    return {
        "step": step,
        "training_seen": step,
        "row_epoch": step / 2,
        "completed_epochs": step // 2,
        "partial_epoch_fraction": (step % 2) / 2,
        "wall_seconds": 0.1234567890123456,
        "train_scope": "fixed_diagnostic_subset",
        "scope": "fixed_target_blind_subset" if diagnostic else "all_validation",
        "kind": "fixed_diagnostic" if diagnostic else "full_selector",
        "used_for_selection": not diagnostic,
        "train": dict(metric),
        "validation": dict(metric),
    }


def save_records(module, root, records):
    path = root / "observations.jsonl.gz"
    with gzip.open(path, "wt") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
    return path


class ImagePolicyTests(unittest.TestCase):
    def test_actual_persist_keeps_all_points_and_never_launches_a_plotter(self):
        tree = ast.parse((SOURCE / "train.py").read_text())
        train = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train")
        helpers = [
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef)
            and n.name
            in {
                "write",
                "_attempt_finalization",
                "stream_json",
                "append_curve_record",
                "write_sampling_counts",
                "_curve_csv",
            }
        ]
        helpers.extend(
            n
            for n in train.body
            if isinstance(n, ast.FunctionDef)
            and n.name
            in {
                "persist_curves",
                "persist",
            }
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "plotting")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            env = {
                "Path": Path,
                "json": json,
                "np": np,
                "csv": csv,
                "gzip": gzip,
                "io": io,
                "time": time,
                "output": output,
                "curve": [],
                "diagnostic_curve": [],
                "persisted_curve_counts": {"curves": 0, "diagnostic-curves": 0},
                "completed_step": 0,
                "attempted_step": 0,
                "batch_records_logged": 0,
                "compact": True,
                "packed_supply": None,
                "unbounded": True,
                "ix_train": np.array([0, 1]),
                "sampled_rows": np.array([1, 1, 0]),
                "attempted_rows": np.array([1, 1, 0]),
                "mode": "epoch",
                "families": [],
                "group_indices": [],
                "cfg": {"training": {"loss_weighting": "row"}},
                "epoch_sampler": types.SimpleNamespace(seen=2),
                "supply": types.SimpleNamespace(training_seen=2, reflected_seen=1),
                "status": "SAVED_ONLY_FIXTURE",
                "fault": None,
                "model_state_status": "LAST_COMPLETED_UPDATE",
                "best_exposure": None,
                "last_completed_point": None,
                "checkpoint_positions": {},
                "samples": 0,
                "forward_rows": {},
                "completed_forward_rows": {},
                "phase_seconds": {"logging": 0.0},
                "start": time.monotonic(),
                "render_learning_curves": MagicMock(side_effect=AssertionError("automatic SVG")),
                "render_learning_png": MagicMock(side_effect=AssertionError("automatic PNG")),
            }
            env["position"] = lambda: {"step": env["completed_step"], "training_seen": 2}
            exec(
                compile(
                    ast.Module(body=helpers, type_ignores=[]), str(SOURCE / "train.py"), "exec"
                ),
                env,
            )
            for step in (0, 1, 2):
                env["completed_step"] = step
                env["curve"].append(point(step))
                env["diagnostic_curve"].append(point(step, diagnostic=True))
                with patch("subprocess.Popen", side_effect=AssertionError("plotter process")):
                    env["persist"]()
            for name, expected in [
                ("curves", env["curve"]),
                ("diagnostic-curves", env["diagnostic_curve"]),
            ]:
                compressed = output / (name + ".jsonl.gz")
                with gzip.open(compressed, "rt") as stream:
                    actual = [json.loads(line) for line in stream]
                self.assertEqual(actual, expected)
                with (output / (name + ".csv")).open() as stream:
                    CSV = list(csv.DictReader(stream))
                self.assertEqual([r["step"] for r in CSV], ["0", "1", "2"])
                self.assertEqual(
                    float(CSV[-1]["validation_row_mse"]), expected[-1]["validation"]["target_mse"]
                )
            self.assertEqual(list(output.glob("*.png")) + list(output.glob("*.svg")), [])
            self.assertEqual(json.loads((output / "sampling.json").read_text())["seen"], 2)
            frozen = next(
                n
                for n in tree.body
                if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "FROZEN_ARTIFACTS" for t in n.targets)
            )
            self.assertFalse(
                any(p.endswith((".png", ".svg")) for p in ast.literal_eval(frozen.value))
            )

    def test_explicit_svg_generates_only_requested_image_from_diagnostic_scope(self):
        module = plotting_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = [point(0, True), point(2, True)]
            source = save_records(module, root, records)
            before = source.read_bytes()
            out = root / "chosen.svg"
            with (
                patch.object(
                    sys,
                    "argv",
                    ["plotting", "--curves", str(source), "--output", str(out), "--format", "svg"],
                ),
                patch.object(
                    module, "render_learning_png", side_effect=AssertionError("unrequested PNG")
                ),
            ):
                module.main()
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(root.glob("*.png")), [])
            self.assertEqual(list(root.glob("*.svg")), [out])
            self.assertIn("Validation: diagnostic subset", out.read_text())

    def test_explicit_png_selects_only_png_renderer(self):
        module = plotting_module()
        records = [point(0), point(2)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = save_records(module, root, records)
            out = root / "chosen.png"
            with (
                patch.object(
                    sys, "argv", ["plotting", "--curves", str(source), "--output", str(out)]
                ),
                patch.object(module, "render_learning_png") as PNG,
                patch.object(
                    module, "render_learning_curves", side_effect=AssertionError("unrequested SVG")
                ),
            ):
                module.main()
            PNG.assert_called_once_with(records, str(out), selected_step=None)

    def test_png_preserves_full_selector_vs_fixed_diagnostic_labels(self):
        module = plotting_module()
        fake = types.ModuleType("matplotlib")
        fake.use = MagicMock()
        plt = types.ModuleType("matplotlib.pyplot")
        fake.pyplot = plt
        figure, axes = MagicMock(), [MagicMock(), MagicMock()]
        plt.subplots = MagicMock(return_value=(figure, axes))
        plt.close = MagicMock()
        for diagnostic in (False, True):
            for axis in axes:
                axis.reset_mock()
            with patch.dict(sys.modules, {"matplotlib": fake, "matplotlib.pyplot": plt}):
                module.render_learning_png([point(0, diagnostic)], "chosen.png")
            expected = "Fixed validation diagnostic subset" if diagnostic else "All validation rows"
            self.assertIn(
                expected, [call.kwargs.get("label") for call in axes[0].plot.call_args_list]
            )

    def test_conflicting_format_is_rejected_before_loading_or_rendering(self):
        module = plotting_module()
        with (
            patch.object(
                sys,
                "argv",
                ["plotting", "--curves", "unopened", "--output", "x.png", "--format", "svg"],
            ),
            patch.object(module, "render_learning_png") as PNG,
            patch.object(module, "render_learning_curves") as SVG,
            patch("sys.stderr", new=io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as error:
                module.main()
        self.assertEqual(error.exception.code, 2)
        PNG.assert_not_called()
        SVG.assert_not_called()


if __name__ == "__main__":
    unittest.main()
