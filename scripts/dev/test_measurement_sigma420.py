"""NN0 regression for the native Sigma model-free measurement admission."""

import ast
from copy import deepcopy
from pathlib import Path
import unittest


class SigmaMeasurementAdmission(unittest.TestCase):
    def test_native_sigma_closed_metadata_and_old_evaluators_nn0(self):
        path = Path(__file__).with_name("research-lifecycle.py")
        selected = [
            node
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.FunctionDef)
            and node.name in ("measurement_config", "experiment_phase_check")
        ]
        self.assertEqual(len(selected), 2)

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        scope = {"require": require, "document": lambda value: value}
        exec(
            compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"),
            scope,
        )
        config = {
            "roots": [{"input": 0, "pointer": "", "field": "actions", "label": "toy"}],
            "profile": "control",
            "tt_entries": 37,
            "use_tt": True,
            "use_pvs": True,
            "lmr": False,
            "output_bytes": 4096,
            "record_bytes": 1024,
            "namespace": {
                "evaluator": "sigma-value-onnx-cpu:sha256:" + "c" * 64,
                "rules": "rules",
                "selectivity": "PVS",
            },
            "inference": {
                "backend": "ort",
                "model": "/FAKE/model.onnx",
                "model_sha": "a" * 64,
                "library": "/FAKE/libort.so",
                "logical_row_limit": 9,
            },
        }
        experiment = {
            "phase": "compare",
            "argv": ["/FAKE/runner", "measure"],
            "rules": "rules",
            "config": config,
            "schedule": [
                {"id": "one", "session": "cold", "root": 0, "depth": 1, "node_cap": 17}
            ],
            "inputs": [
                {"path": "/FAKE/roots.json", "sha256": "d" * 64},
                {"path": "/FAKE/model.onnx", "sha256": "a" * 64},
            ],
            "models": [],
            "dynamic_libraries": [
                {
                    "file": {"path": "/FAKE/libort.so", "sha256": "b" * 64},
                    "version": "FAKE",
                }
            ],
        }
        check = scope["measurement_config"]
        phase = scope["experiment_phase_check"]
        self.assertEqual(check(experiment), (config, experiment["schedule"]))
        phase(experiment)
        for bad in (None, 0, -1, True, "9"):
            changed = deepcopy(experiment)
            changed["config"]["inference"]["logical_row_limit"] = bad
            with self.assertRaises(ValueError):
                check(changed)
        for case in range(6):
            changed = deepcopy(experiment)
            if case == 0:
                changed["inputs"].pop()
            elif case == 1:
                changed["dynamic_libraries"].clear()
            elif case == 2:
                changed["models"] = [{}]
            elif case == 3:
                changed["config"]["namespace"]["evaluator"] = "nnue"
            elif case == 4:
                changed["config"]["loss_leaf_419"] = True
            else:
                changed["config"]["lmr"] = True
            with self.assertRaises(ValueError):
                check(changed)
        for evaluator, models in (("original-distance-a0-b8-tanh", []), ("nnue", [{}])):
            changed = deepcopy(experiment)
            changed["config"].pop("inference")
            changed["config"]["namespace"]["evaluator"] = evaluator
            changed["models"] = models
            check(changed)
            phase(changed)


if __name__ == "__main__":
    unittest.main()
