"""One new normal-metadata boundary, canonical lifecycle owner after adoption."""

import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "new29_lifecycle", ROOT / "scripts/dev/research-lifecycle.py"
)
LC = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LC
SPEC.loader.exec_module(LC)


class RootAspirationMetadata(unittest.TestCase):
    def test_typed_current_control_only_and_invalid_fields(self):
        self.assertIsNone(LC.resolved_root_aspiration({}, "control"))
        value = dict(half_width=0.125, growth=2.0, activation_depth=3, max_retries=4)
        self.assertEqual(LC.resolved_root_aspiration(dict(root_aspiration=value), "control"), value)
        for change in [
            None,
            {},
            {**value, "half_width": 0},
            {**value, "growth": 1},
            {**value, "half_width": math.nan},
            {**value, "activation_depth": True},
            {**value, "max_retries": 9},
            {**value, "unknown": 1},
        ]:
            with self.assertRaises(LC.Refused):
                LC.resolved_root_aspiration(dict(root_aspiration=change), "control")
        for config, profile, supported in [
            (dict(root_aspiration=value), "cheap", True),
            (dict(root_aspiration=value, search_threads=2), "control", True),
            (dict(root_aspiration=value), "control", False),
        ]:
            with self.assertRaises(LC.Refused):
                LC.resolved_root_aspiration(config, profile, supported=supported)


if __name__ == "__main__":
    unittest.main()
