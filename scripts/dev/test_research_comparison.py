"""Owning NN0 checks for explicit preparation; no engine or model is loaded."""

import copy
import importlib.util
from pathlib import Path
import unittest

loader = importlib.util.spec_from_file_location(
    "comparison_preparation_current",
    Path("/workspaces/quoridor/scripts/dev/research-lifecycle.py"),
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class SharedComparisonPreparationTests(unittest.TestCase):
    def test_resolved_conditions_preserve_domains_and_refuse_unsupported_arena_flags(
        self,
    ):
        common = dict(
            evaluators=("nnue", "distance"),
            profiles=("control", "cheap"),
            lmr_values=(False, True),
            tt_entries=1048576,
            use_tt=True,
            use_pvs=True,
            rules="research-standard-2p-threefold-goal-first-v1",
            ruleset="standard_2p_threefold",
            family_B=4 * 1024**3,
            controller_B=64 * 1024**2,
            host_reserve_B=4 * 1024**3,
            arena=dict(
                AI_workers=(2, 6),
                management_guardian=4,
                depth=64,
                max_nodes=1000000,
                time_ms=100,
                return_reserve_ms=5,
                max_plies=200,
            ),
        )
        variants = lc.comparison_conditions(common)
        self.assertEqual(len(variants), 8)
        self.assertEqual(
            {(v["evaluator"], v["profile"], v["lmr"]) for v in variants},
            {
                ("nnue", "control", False),
                ("nnue", "control", True),
                ("nnue", "cheap", False),
                ("nnue", "cheap", True),
                ("distance", "control", False),
                ("distance", "control", True),
                ("distance", "cheap", False),
                ("distance", "cheap", True),
            },
        )
        for variant in variants:
            config = dict(
                roots=[dict(input=0, field="moves", check_history=True)],
                namespace=dict(
                    evaluator=variant["evaluator"], selectivity="raw-method"
                ),
                output="unchanged-output",
                profile="old",
                lmr=None,
            )
            original = copy.deepcopy(config)
            lc.apply_comparison_cost(config, common, variant)
            self.assertEqual(config["tt_entries"], 1048576)
            self.assertIs(config["use_tt"], True)
            self.assertIs(config["use_pvs"], True)
            self.assertEqual(config["profile"], variant["profile"])
            self.assertIs(config["lmr"], variant["lmr"])
            self.assertEqual(config["roots"], original["roots"])
            self.assertEqual(config["output"], original["output"])
            self.assertEqual(config["namespace"]["evaluator"], variant["evaluator"])
            self.assertEqual(config["namespace"]["selectivity"], "raw-method")
            self.assertEqual(config["namespace"]["rules"], common["rules"])
        for pair in ([variants[0], variants[2]], [variants[5], variants[7]]):
            config = dict(
                arena=dict(book={"family": 23}, search_artifact_sha256=[None, None]),
                engines=[
                    dict(
                        kind=v["evaluator"],
                        model=None,
                        distance_a=0.0,
                        distance_b=8.0,
                        simd=False,
                    )
                    for v in pair
                ],
                run_id="bookkeeping",
                output="unchanged-output",
            )
            original = copy.deepcopy(config)
            lc.apply_comparison_arena(config, common, pair)
            self.assertEqual(config["arena"]["tt_entries"], 1048576)
            self.assertEqual(config["arena"]["return_reserve_ms"], 5)
            self.assertEqual(config["cpu_cores"], [2, 6])
            self.assertEqual(config["management_cpu_core"], 4)
            self.assertEqual(config["max_plies"], 200)
            self.assertEqual(config["run_id"], original["run_id"])
            self.assertEqual(config["output"], original["output"])
            self.assertEqual(config["arena"]["book"], original["arena"]["book"])
            self.assertEqual(config["arena"]["search_artifact_sha256"], [None, None])
            for engine, variant in zip(config["engines"], pair, strict=True):
                self.assertEqual(
                    (engine["depth"], engine["max_nodes"], engine["time_ms"]),
                    (64, 1000000, 100),
                )
                self.assertEqual(engine["kind"], variant["evaluator"])
                self.assertEqual(engine["ordering_profile"], variant["profile"])
                self.assertIs(engine["lmr"], variant["lmr"])
                self.assertEqual(
                    (engine["distance_a"], engine["distance_b"]), (0.0, 8.0)
                )
            bad = dict(common, use_pvs=False)
            before_refusal = copy.deepcopy(config)
            with self.assertRaises(AssertionError):
                lc.apply_comparison_arena(config, bad, pair)
            self.assertEqual(config, before_refusal)


if __name__ == "__main__":
    unittest.main()
