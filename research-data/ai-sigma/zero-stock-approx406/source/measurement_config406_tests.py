"""Owning definition for Root's ordinary NN0 entry, not executed by author."""

import ast
import copy
from pathlib import Path
import unittest


class ZeroStockMeasurementConfig406Tests(unittest.TestCase):
    def test_optional_threshold_accepts_only_null_or_exact_integer_zero_to_twenty(self):
        root = Path(__file__).resolve()
        while not (root / "scripts/dev/research-lifecycle.py").is_file():
            if root.parent == root:
                self.fail("maintained publisher unavailable")
            root = root.parent
        path = root / "scripts/dev/research-lifecycle.py"
        # The actual maintained function, with only pure input/require stubs.
        node = next(
            node
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == "measurement_config"
        )

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        environment = {"document": lambda value: value, "require": require}
        exec(
            compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"),
            environment,
        )
        check = environment["measurement_config"]
        base = {
            "roots": [{"input": 0, "pointer": "", "field": "moves", "label": "toy"}],
            "profile": "control",
            "tt_entries": 4096,
            "use_tt": True,
            "use_pvs": True,
            "namespace": {
                "evaluator": "toy",
                "rules": "standard",
                "selectivity": "toy",
            },
            "output_bytes": 10000,
            "record_bytes": 1000,
        }
        experiment = {
            "config": base,
            "schedule": [],
            "rules": "standard",
            "inputs": [{}],
        }
        self.assertEqual(check(copy.deepcopy(experiment))[0], base)
        for value in [None, 0, 4, 20]:
            value_config = copy.deepcopy(experiment)
            value_config["config"]["zero_stock_approx_min_root_walls"] = value
            self.assertEqual(
                check(value_config)[0]["zero_stock_approx_min_root_walls"], value
            )
        for value in [True, False, -1, 21, 1.0, "4", [], {}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                value_config = copy.deepcopy(experiment)
                value_config["config"]["zero_stock_approx_min_root_walls"] = value
                check(value_config)


if __name__ == "__main__":
    unittest.main()
