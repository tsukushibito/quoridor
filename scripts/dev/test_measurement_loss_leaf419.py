"""One NN0 owning definition for the function-only measurement admission change."""

import ast
from copy import deepcopy
from pathlib import Path
import unittest


def measurement_config():
    source = Path(__file__).with_name("research-lifecycle.py")
    tree = ast.parse(source.read_text())
    selected = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "measurement_config"
    )

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    # This test owns functional shape admission, not file verification/job launch.
    namespace = {"document": lambda value: value, "require": require}
    exec(
        compile(ast.Module(body=[selected], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return namespace["measurement_config"]


class LossLeaf419Admission(unittest.TestCase):
    def test_fixed_scope_and_explicit_boolean_refusals_nn0(self):
        check = measurement_config()
        ids = [
            "distance-slot004-ply011",
            "distance-slot004-ply039",
            "distance-slot005-ply012",
        ]
        config = {
            "loss_leaf_419": True,
            "roots": [
                {
                    "input": 0,
                    "pointer": f"/parents/{i}",
                    "field": "from_prefix_actions",
                    "label": name,
                }
                for i, name in enumerate(ids)
            ],
            "profile": "control",
            "tt_entries": 1048576,
            "use_tt": True,
            "use_pvs": True,
            "lmr": False,
            "namespace": {
                "evaluator": "typed-owner",
                "rules": "rules",
                "selectivity": "scope",
            },
            "output_bytes": 100000,
            "record_bytes": 10000,
        }
        requests = [
            {
                "id": f"{name}:{engine}:H{depth}:normal",
                "session": f"{i}-{depth}-{engine}",
                "root": i,
                "depth": depth,
                "node_cap": 1000000,
            }
            for i, name in enumerate(ids)
            for depth in (2, 3)
            for engine in ("N", "D")
        ]
        experiment = {
            "config": config,
            "schedule": requests,
            "rules": "rules",
            "inputs": [
                {
                    "sha256": "b26fb4d5f21bac5b9614610504aac7022850223a6af67b4680530c08e8429304"
                }
            ],
        }
        self.assertEqual(check(experiment), (config, requests))
        for bad in (None, 0, "true"):
            changed = deepcopy(experiment)
            changed["config"]["loss_leaf_419"] = bad
            with self.assertRaises(ValueError):
                check(changed)
        changed = deepcopy(experiment)
        changed["schedule"][0]["time_limit_ms"] = 1
        with self.assertRaises(ValueError):
            check(changed)
        changed = deepcopy(experiment)
        changed["inputs"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            check(changed)
        changed = deepcopy(experiment)
        del changed["config"]["loss_leaf_419"]
        self.assertEqual(check(changed), (changed["config"], changed["schedule"]))


if __name__ == "__main__":
    unittest.main()
