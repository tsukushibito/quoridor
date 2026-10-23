"""NN0 checks for closed Sigma fixed-depth model and three-core admission."""

import ast
from copy import deepcopy
import math
from pathlib import Path
import unittest


class SigmaArenaAdmission(unittest.TestCase):
    def test_sigma_completed_observation_typed_namespace_nn0(self):
        source = Path(__file__).with_name("research-lifecycle.py")
        selected = [
            node
            for node in ast.parse(source.read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == "arena_observation"
        ]
        self.assertEqual(len(selected), 1)

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        scope = {"require": require, "math": math}
        exec(
            compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"),
            scope,
        )
        config = {
            "engines": [
                {
                    "kind": "sigma_value",
                    "ordering_profile": "control",
                    "simd": False,
                    "lmr": False,
                    "lmr_method": "depth_rank",
                    "depth": 2,
                }
            ],
            "arena": {
                "comparison": "evaluator_fixed_depth",
                "evaluator_sha256": ["a" * 64],
                "book": {"openings": [{"prefix": []}]},
            },
        }
        observation = {
            "engine_index": 0,
            "caller_seconds": 0.1,
            "thinking_seconds": 0.09,
            "value_stm": 0.25,
            "accepted": True,
            "failure": None,
            "engine_error": None,
            "action": 13,
            "accepted_ns": 5,
            "admission_checked_ns": 4,
            "returned_ns": 3,
            "completed_depth": 2,
            "stop": "depth_cap",
            "deadline_ns": None,
            "pv": [13, 67],
            "counters": {
                "actual_search_namespace": {
                    "evaluator": "sigma-value-onnx-cpu:sha256:" + "a" * 64 + ":simd=false",
                    "rules": "research-standard-2p-threefold-goal-first-v1",
                    "selectivity": "fullwidth",
                },
                "requested_lmr_method": "depth_rank",
                "actual_lmr_enabled": False,
                "actual_lmr_method_id": None,
                "lmr_reduction_rule": None,
                "completed_snapshot_validation_failed": False,
            },
        }
        row = {"game": 0, "moves": [13], "observations": [observation]}
        check = scope["arena_observation"]
        check(config, row)
        for case in range(4):
            changed = deepcopy(row)
            obs = changed["observations"][0]
            if case == 0:
                obs["counters"]["actual_search_namespace"]["evaluator"] = (
                    "sigma-value-onnx-cpu:sha256:" + "b" * 64 + ":simd=false"
                )
            elif case == 1:
                obs["counters"]["actual_search_namespace"]["evaluator"] = (
                    "distance-tanh-f32:sha256:" + "a" * 64 + ":simd=false"
                )
            elif case == 2:
                obs["completed_depth"] = 1
            else:
                obs["counters"]["actual_lmr_enabled"] = True
            with self.assertRaises(ValueError):
                check(config, changed)

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
            "dynamic_libraries": [{"file": {"path": inference["library"], "sha256": "b" * 64}}]
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

    def test_nnue_mcts_completed_receipt_and_no_zero_work_fallback_nn0(self):
        source = Path(__file__).with_name("research-lifecycle.py")
        nodes = [
            n
            for n in ast.parse(source.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "arena_observation"
        ]
        self.assertEqual(len(nodes), 1)

        def require(condition, message):
            if not condition:
                raise ValueError(message)

        scope = {"require": require, "math": math}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), scope)
        config = {
            "engines": [{"kind": "nnue_mcts"}],
            "arena": {"comparison": "whole_wall_time", "book": {"openings": [{"prefix": []}]}},
        }
        observation = {
            "engine_index": 0,
            "caller_seconds": 0.1,
            "thinking_seconds": 0.09,
            "value_stm": 0.25,
            "accepted": True,
            "failure": None,
            "engine_error": None,
            "action": 13,
            "accepted_ns": 125,
            "admission_checked_ns": 124,
            "returned_ns": 123,
            "deadline_ns": 100,
            "completed_depth": None,
            "pv": [],
            "counters": {
                "authority_receipt_ns": 90,
                "authority_legal": True,
                "inflight_after_drain": 0,
                "completed_simulations": 2,
                "clock_contract": "authority-action-receipt-v1",
                "clock_contract_sha256": "04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d",
                "drain_finished_ns": 123,
            },
        }
        # Synthetic observation only: no source imports, model/geometry/Search or OS lifetime proof.
        check = scope["arena_observation"]
        row = {"game": 0, "moves": [13], "observations": [observation]}
        check(config, row)
        for field, value in [
            ("completed_depth", 1),
            ("pv", [13]),
            ("engine_error", "NNUE_ROW_LIMIT"),
        ]:
            bad = deepcopy(row)
            bad["observations"][0][field] = value
            with self.assertRaises(ValueError):
                check(config, bad)
        for field, value in [
            ("authority_receipt_ns", 100),
            ("inflight_after_drain", None),
            ("drain_finished_ns", 122),
            ("authority_legal", False),
        ]:
            bad = deepcopy(row)
            bad["observations"][0]["counters"][field] = value
            with self.assertRaises(ValueError):
                check(config, bad)
        zero = deepcopy(row)
        zero["observations"][0]["value_stm"] = None
        zero["observations"][0]["counters"].update(
            completed_simulations=0,
            selection_reason="legal_fallback_no_completed_simulation",
            completed_simulation_counters=None,
            last_completed_simulation_ns=None,
        )
        with self.assertRaises(ValueError):
            check(config, zero)
        # Existing Sigma fallback contract remains unchanged; NNUE producer forbids it.
        sigma = deepcopy(config)
        sigma["engines"][0]["kind"] = "mcts"
        check(sigma, zero)
        refused = deepcopy(zero)
        refused["moves"] = []
        refused["observations"][0]["accepted"] = False
        refused["observations"][0]["failure"] = "NoCompletedSimulation"
        check(config, refused)


if __name__ == "__main__":
    unittest.main()
