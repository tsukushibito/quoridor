"""Root-only NN0 definition against the actual maintained measurement function."""

import ast
import copy
from pathlib import Path
import unittest


class ZeroStockMethod407Tests(unittest.TestCase):
    def test_method_defaults_independent_activation_and_exact_name_refusals(self):
        path = Path("/workspaces/quoridor/scripts/dev/research-lifecycle.py")
        function = next(
            n
            for n in ast.parse(path.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "measurement_config"
        )

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        env = {"document": lambda value: value, "require": require}
        exec(
            compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"),
            env,
        )
        config = {
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
            "config": config,
            "schedule": [],
            "rules": "standard",
            "inputs": [{}],
        }
        check = env["measurement_config"]
        self.assertEqual(check(copy.deepcopy(experiment))[0], config)
        for method in ["race", "fixed_d"]:
            for threshold in [None, 0, 4, 20]:
                selected = copy.deepcopy(experiment)
                selected["config"].update(
                    zero_stock_approx_method=method,
                    zero_stock_approx_min_root_walls=threshold,
                )
                self.assertEqual(check(selected)[0], selected["config"])
        for method in [None, True, False, 0, 1.0, "", "FixedD", "solver", [], {}]:
            with self.subTest(method=method), self.assertRaises(ValueError):
                selected = copy.deepcopy(experiment)
                selected["config"]["zero_stock_approx_method"] = method
                check(selected)


if __name__ == "__main__":
    unittest.main()
