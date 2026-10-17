"""One unrun owning config-only NN0 definition for Root current software entry."""

import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

loader = importlib.util.spec_from_file_location(
    "measurement_config400_current",
    Path("/workspaces/quoridor/scripts/dev/research-lifecycle.py"),
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class LmrMeasurementConfig400Tests(unittest.TestCase):
    def test_optional_boolean_and_pvs_profile_boundaries(self):
        config = {
            "roots": [{"input": 0, "pointer": "", "field": "moves", "label": "toy"}],
            "profile": "control",
            "tt_entries": 4096,
            "use_tt": True,
            "use_pvs": True,
            "namespace": {
                "evaluator": "synthetic",
                "rules": "standard",
                "selectivity": "synthetic",
            },
            "output_bytes": 10000,
            "record_bytes": 1000,
        }
        experiment = {
            "config": None,
            "schedule": None,
            "rules": "standard",
            "inputs": [None],
        }
        for profile in ["control", "cheap"]:
            for enabled in [None, False, True]:
                selected = copy.deepcopy(config)
                selected["profile"] = profile
                if enabled is not None:
                    selected["lmr"] = enabled
                with patch.object(lc, "document", side_effect=[selected, []]):
                    actual, requests = lc.measurement_config(experiment)
                self.assertEqual(actual.get("lmr", False), enabled is True)
                self.assertEqual(requests, [])
        for value in [None, 0, 1, "true"]:
            selected = {**config, "lmr": value}
            with patch.object(lc, "document", side_effect=[selected, []]):
                with self.assertRaisesRegex(ValueError, "measurement LMR switch"):
                    lc.measurement_config(experiment)
        for changed in [{"profile": "coverage"}, {"use_pvs": False}]:
            selected = {**config, **changed, "lmr": True}
            with patch.object(lc, "document", side_effect=[selected, []]):
                with self.assertRaisesRegex(
                    ValueError, "measurement LMR requires PVS and Control/Cheap"
                ):
                    lc.measurement_config(experiment)

    def test_safe_race_method_is_optional_and_does_not_enable_the_leaf(self):
        config = {
            "roots": [{"input": 0, "pointer": "", "field": "moves", "label": "toy"}],
            "profile": "control",
            "tt_entries": 4096,
            "use_tt": True,
            "use_pvs": True,
            "namespace": {
                "evaluator": "synthetic",
                "rules": "standard",
                "selectivity": "synthetic",
            },
            "output_bytes": 10000,
            "record_bytes": 1000,
        }
        experiment = {"config": None, "schedule": None, "rules": "standard", "inputs": [None]}
        for method in (None, "manhattan", "path_tail"):
            for enabled in (False, True):
                selected = {
                    **config,
                    "zero_stock_safe_race_method": method,
                    "zero_stock_safe_race": enabled,
                }
                with patch.object(lc, "document", side_effect=[selected, []]):
                    actual, requests = lc.measurement_config(experiment)
                self.assertIs(actual["zero_stock_safe_race"], enabled)
                self.assertEqual(actual["zero_stock_safe_race_method"], method)
                self.assertEqual(requests, [])
        with patch.object(lc, "document", side_effect=[config, []]):
            actual, _ = lc.measurement_config(experiment)
        self.assertNotIn("zero_stock_safe_race_method", actual)
        self.assertFalse(actual.get("zero_stock_safe_race", False))
        for value in (False, 0, "", "other", []):
            selected = {**config, "zero_stock_safe_race_method": value}
            with patch.object(lc, "document", side_effect=[selected, []]):
                with self.assertRaisesRegex(ValueError, "measurement safe-race method"):
                    lc.measurement_config(experiment)

    def test_fixed_d_cheap_phase_model_binding_and_rejections(self):
        experiment = dict(phase="compare", argv=["runner", "measure"], config=None)
        for fixed_d, profiles, models in [
            (True, ["control", "cheap", "coverage"], []),
            (False, ["control", "cheap"], ["model"]),
        ]:
            evaluator = "original-distance-a0-b8-tanh" if fixed_d else "nnue"
            for profile in profiles:
                config = dict(namespace=dict(evaluator=evaluator), profile=profile)
                with patch.object(lc, "document", return_value=config):
                    lc.experiment_phase_check(dict(experiment, models=models))
                    wrong_models = ["model"] if fixed_d else []
                    with self.assertRaisesRegex(
                        ValueError, "measurement evaluator/model/profile binding"
                    ):
                        lc.experiment_phase_check(dict(experiment, models=wrong_models))
        for evaluator, profile, models in [
            ("original-distance-a0-b8-tanh", "policy", []),
            ("nnue", "coverage", ["model"]),
            ("nnue", "cheap", ["model", "second"]),
        ]:
            with patch.object(
                lc,
                "document",
                return_value=dict(namespace=dict(evaluator=evaluator), profile=profile),
            ):
                with self.assertRaisesRegex(
                    ValueError, "measurement evaluator/model/profile binding"
                ):
                    lc.experiment_phase_check(dict(experiment, models=models))


if __name__ == "__main__":
    unittest.main()
