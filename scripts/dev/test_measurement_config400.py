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


if __name__ == "__main__":
    unittest.main()
