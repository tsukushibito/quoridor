"""New SearchWallTime plan admission only; no native/model/old tests execute."""

import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(os.environ.get("ARENA_361_MAIN_ROOT", Path(__file__).resolve().parents[2]))
SPEC = importlib.util.spec_from_file_location(
    "search_wall_plan_fixture", ROOT / "tools/research-session/test_arena_plan.py"
)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
lc = HELPER.lc


class SearchWallTimePlanTests(unittest.TestCase):
    def test_same_evaluator_policy_difference_and_guarded_identity(self):
        helper = HELPER.ArenaPlanTests()
        with tempfile.TemporaryDirectory() as temp:
            helper.tmp = type("Temp", (), {"name": temp})()
            _, experiment, plan, config, slots = helper.fixture(1, 4)
            engine = copy.deepcopy(config["engines"][0])
            engine.update(
                time_ms=100,
                ordering_profile="control",
                lmr=True,
                lmr_method="depth_rank",
                zero_stock_safe_race=True,
                zero_stock_safe_race_method="path_tail",
            )
            config["engines"] = [engine, copy.deepcopy(engine)]
            config["engines"][1].update(
                zero_stock_safe_race=False, zero_stock_safe_race_method="manhattan"
            )
            config.update(management_cpu_core=6, cpu_cores=[2, 4])
            arena = config["arena"]
            arena.update(
                comparison="search_wall_time",
                return_reserve_ms=5,
                max_total_nodes=500000000,
                evaluator_sha256=[plan["models"][0]["evaluator_sha256"]] * 2,
            )
            plan["comparison"] = "search_wall_time"

            def bind(candidate):
                plan["matchups"][0]["engines"] = copy.deepcopy(candidate["engines"])
                plan["matchups"][0]["evaluator_sha256"] = candidate["arena"]["evaluator_sha256"][:]
                bound = helper.json_file("current-config.json", candidate)
                experiment["config"] = plan["batches"][0]["config"] = bound

            bind(config)
            planned, resolved = lc.arena_plan_check(experiment, plan)
            self.assertEqual(planned, slots)
            self.assertTrue(resolved["engines"][0]["zero_stock_safe_race"])
            self.assertFalse(resolved["engines"][1]["zero_stock_safe_race"])
            self.assertEqual(len(plan["models"]), 1)
            for mutate in (
                lambda c: c["arena"]["evaluator_sha256"].__setitem__(1, "b" * 64),
                lambda c: c["engines"][1].update(kind="distance", model=None),
            ):
                changed = copy.deepcopy(config)
                mutate(changed)
                bind(changed)
                with self.assertRaisesRegex(lc.Refused, "search comparison requires"):
                    lc.arena_plan_check(experiment, plan)
            changed = copy.deepcopy(config)
            changed["arena"]["search_artifact_sha256"][1] = "d" * 64
            bind(changed)
            with self.assertRaisesRegex(lc.Refused, "arena equal runtime"):
                lc.arena_plan_check(experiment, plan)


if __name__ == "__main__":
    unittest.main()
