"""Affected new method/data-entry contracts; NN0, no original or sealed corpus."""

import builtins
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .common import resolve_config, target_value
from .distance_steps import (
    CONDITIONS,
    VIEWS,
    recipe,
    require_main_volume,
    significant_improvement,
    transform_score,
    view_manifest,
)
from .sampling import EarlyStopping
from .terminal_cache import validate_terminal_metadata


def terminal_row(reason="goal", side=1):
    final = [0, 3] if reason == "goal" else [7, 8]
    z = (1 if side == 1 else -1) if reason == "goal" else (0 if reason == "threefold" else None)
    margin = final[(side - 1) ^ 1] - final[side - 1]
    return {
        "side": side,
        "prefix": [],
        "research_ruleset": "new-rules",
        "z": z,
        "primary_eligible": reason != "unknown",
        "terminal_targets": {
            "provenance": {
                "schema": "quoridor-terminal-teachers-v1",
                "reason": reason,
                "ruleset": "new-rules",
                "final_prefix": [],
                "winner": 1 if reason == "goal" else None,
                "terminal_distance_p1_p2": None if reason == "unknown" else final,
                "final_distance_p1_p2": final,
            },
            "current_distance_steps_stm_opponent": [8, 8],
            "outcome_z": z,
            "margin_target_steps": None
            if reason == "unknown"
            else (0 if reason == "threefold" else margin),
            "terminal_geometric_margin_steps": None if reason == "unknown" else margin,
        },
    }


class DistanceStepContracts(unittest.TestCase):
    def config(self, condition):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "recipe.json"
            p.write_text(json.dumps(recipe(condition)))
            return resolve_config(p)

    def test_four_conditions_and_six_views_share_one_recipe(self):
        configs = [self.config(c) for c in CONDITIONS]
        for config in configs:
            for name in ["optimizer", "training", "evaluation"]:
                left = {k: v for k, v in config[name].items() if k != "target"}
                right = {k: v for k, v in configs[0][name].items() if k != "target"}
                self.assertEqual(left, right)
            with self.assertRaisesRegex(ValueError, "unset"):
                require_main_volume(config)
        for name, (condition, transform) in VIEWS.items():
            view = view_manifest(self.config(condition), name)
            self.assertEqual(view["model"]["deploy_transform"], transform)
            self.assertEqual(view["model"]["train_transform"], CONDITIONS[condition][2])

    def test_N_refusal_actual_train_precedes_torch_and_corpus(self):
        from . import train

        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "config.json"
            p.write_text(json.dumps(recipe("A")))
            original = builtins.__import__

            def reject_model(name, *args, **kwargs):
                if name.split(".")[0] in {"torch", "onnxruntime"}:
                    raise AssertionError("framework must stay closed")
                return original(name, *args, **kwargs)

            with (
                patch("builtins.__import__", side_effect=reject_model),
                patch.object(train, "load", side_effect=AssertionError("corpus must stay closed")),
            ):
                with self.assertRaisesRegex(ValueError, "unset"):
                    train.train("missing", "missing", p)

    def test_common_legacy_model_identity_and_new_teacher_units(self):
        cfg = resolve_config()
        self.assertNotIn("distance_bypass", cfg["model"])
        self.assertEqual(target_value({"outcome_steps": 80}, "outcome_steps"), 80)
        self.assertEqual(target_value({"terminal_margin": -37}, "terminal_margin"), -37)
        self.assertIsNone(target_value({"terminal_margin": None}, "terminal_margin"))
        for value in [81, math.inf, math.nan, True]:
            with self.assertRaises(ValueError):
                target_value({"terminal_margin": value}, "terminal_margin")

    def test_unknown_draw_and_absolute_row_STM(self):
        for side in (1, 2):
            r = terminal_row("goal", side)
            validate_terminal_metadata(r)
            self.assertEqual(r["z"], 1 if side == 1 else -1)
            r = terminal_row("threefold", side)
            validate_terminal_metadata(r)
            self.assertEqual(r["terminal_targets"]["margin_target_steps"], 0)
            self.assertNotEqual(r["terminal_targets"]["terminal_geometric_margin_steps"], 0)
            r = terminal_row("unknown", side)
            validate_terminal_metadata(r)
            r["primary_eligible"] = True
            with self.assertRaises(ValueError):
                validate_terminal_metadata(r)
        r = terminal_row()
        r["terminal_targets"]["margin_target_steps"] = -3
        with self.assertRaises(ValueError):
            validate_terminal_metadata(r)
        r = terminal_row()
        r["z"] = True
        with self.assertRaises(ValueError):
            validate_terminal_metadata(r)

    def test_explicit_boolean_and_unknown_prefix_receipts(self):
        for value in (None, 1, "true"):
            row = terminal_row()
            row["primary_eligible"] = value
            with self.assertRaises(ValueError):
                validate_terminal_metadata(row)
        row = terminal_row()
        row["terminal_targets"]["provenance"]["final_prefix"] = None
        with self.assertRaises(ValueError):
            validate_terminal_metadata(row)

    def test_CSV_keeps_both_teacher_units_and_scopes(self):
        import csv
        from .train import _curve_csv

        metrics = {
            "target_game_equal_mse": 0.2,
            "target_mse": 0.3,
            "outcome_steps_raw_mse": 1920,
            "terminal_margin_raw_mse": 3200,
            "outcome_steps_mse": 0.3,
            "terminal_margin_mse": 0.5,
            "bias": 2,
            "large_abs_step_score_fraction": 0.1,
            "rows": 4,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "curve.csv"
            _curve_csv([{"train": metrics, "validation": metrics, "kind": "full_selector"}], path)
            with path.open() as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(float(row["train_outcome_steps_raw_mse"]), 1920)
            self.assertEqual(float(row["validation_terminal_margin_mse"]), 0.5)
            self.assertEqual(row["validation_scope"], "full_selector")

    def test_F_units_linear_margin_and_significant_not_strict_reset(self):
        self.assertEqual(transform_score(0, "F"), 0)
        self.assertEqual(transform_score(-37, "raw"), -37)
        self.assertAlmostEqual(transform_score(80, "F"), 80 * math.tanh(1))
        self.assertTrue(significant_improvement(0.9, 1))
        self.assertFalse(significant_improvement(0.99999, 1))
        self.assertFalse(significant_improvement(1e-10, 2e-10))
        tracker = EarlyStopping(8, 1e-8, 1e-4)
        tracker.observe(1)
        strict_best = 0.99999
        self.assertLess(strict_best, 1)
        significant, stop = tracker.observe(strict_best)
        self.assertFalse(significant)
        self.assertFalse(stop)
        self.assertEqual(tracker.best, 1)


if __name__ == "__main__":
    unittest.main()
