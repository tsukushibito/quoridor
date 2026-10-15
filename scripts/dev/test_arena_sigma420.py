"""NN0 checks for closed Sigma fixed-depth model and three-core admission."""

import ast
from copy import deepcopy
from pathlib import Path
import unittest


class SigmaArenaAdmission(unittest.TestCase):
    def test_closed_model_and_three_core_fixed_depth_nn0(self):
        source = Path(__file__).with_name("research-lifecycle.py")
        selected = [
            node
            for node in ast.parse(source.read_text()).body
            if isinstance(node, ast.FunctionDef)
            and node.name in ("arena_model_check", "arena_cpu_cores")
        ]
        self.assertEqual(len(selected), 2)

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        scope = {"require": require, "document": lambda value: value}
        exec(
            compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"),
            scope,
        )
        inference = {
            "backend": "ort",
            "model": "/FAKE/model.onnx",
            "model_sha": "a" * 64,
            "library": "/FAKE/libort.so",
            "device": 0,
            "cuda_graph": False,
            "logical_row_limit": 97,
        }
        plan = {
            "comparison": "evaluator_fixed_depth",
            "models": [],
            "inputs": [{"path": inference["model"], "sha256": inference["model_sha"]}],
            "matchups": [
                {
                    "id": "one",
                    "engines": [
                        {"kind": "sigma_value", "model": None},
                        {"kind": "distance", "model": None},
                    ],
                    "evaluator_sha256": ["c" * 64, "d" * 64],
                    "inference": inference,
                }
            ],
        }
        experiment = {
            "dynamic_libraries": [
                {"file": {"path": inference["library"], "sha256": "b" * 64}}
            ]
        }
        check = scope["arena_model_check"]
        check(experiment, plan, 2)
        for case in range(12):
            changed = deepcopy(plan)
            match = changed["matchups"][0]
            if case == 0:
                changed["comparison"] = "whole_wall_time"
            elif case == 1:
                match["inference"]["device"] = 1
            elif case == 2:
                match["inference"]["cuda_graph"] = True
            elif case in (3, 4, 5):
                match["inference"]["logical_row_limit"] = (0, True, None)[case - 3]
            elif case == 6:
                match["engines"][0]["model"] = "/FAKE/descriptor.json"
            elif case == 7:
                changed["inputs"].clear()
            elif case == 8:
                match["inference"]["model_sha"] = "f" * 64
            elif case == 9:
                match["inference"]["library"] = "/FAKE/missing.so"
            elif case == 10:
                match["evaluator_sha256"][0] = "z" * 64
            else:
                match["engines"][0]["kind"] = "unbound"
            with self.assertRaises(ValueError):
                check(experiment, changed, 2)
        config = {
            "arena": {"comparison": "evaluator_fixed_depth"},
            "workers": 1,
            "active_games": 1,
            "max_batch": 1,
            "inference_cpu_core": None,
            "cpu_cores": [2, 6],
            "management_cpu_core": 4,
        }
        spec = {
            "kind": "run",
            "experiment": {"phase": "arena", "config": config},
            "limits": {"worker_cpu": 2, "guardian_cpu": 4, "family_B": 4 * 1024**3},
            "child_cpu_cores": [2, 4, 6],
            "support": {
                "resources": {
                    "CPU": 3,
                    "threads": 1,
                    "GPU": 0,
                    "controller_included": True,
                    "family_RAM_B": 4 * 1024**3,
                }
            },
        }
        cpu_check = scope["arena_cpu_cores"]
        self.assertEqual(cpu_check(spec), [2, 4, 6])
        control = deepcopy(spec)
        control["experiment"]["config"]["arena"]["comparison"] = "whole_wall_time"
        self.assertEqual(cpu_check(control), [2, 4, 6])
        for case in range(5):
            changed = deepcopy(spec)
            if case == 0:
                changed["child_cpu_cores"] = [2, 4]
            elif case == 1:
                changed["experiment"]["config"]["cpu_cores"] = [2, 2]
            elif case == 2:
                changed["experiment"]["config"]["management_cpu_core"] = 6
            elif case == 3:
                changed["support"]["resources"]["CPU"] = 1
            else:
                changed["support"]["resources"]["family_RAM_B"] = 1
            with self.assertRaises(ValueError):
                cpu_check(changed)


if __name__ == "__main__":
    unittest.main()
