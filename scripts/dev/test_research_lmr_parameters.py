"""New typed LMR metadata boundary only; no native/model/game execution."""

import ast
import copy
import math
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name("research-lifecycle.py")
NAMES = {
    "Refused",
    "require",
    "resolved_lmr_parameters",
    "comparison_conditions",
    "apply_comparison_cost",
    "apply_comparison_arena",
}
TREE = ast.parse(SOURCE.read_text())
NODES = [node for node in TREE.body if getattr(node, "name", None) in NAMES]
assert {node.name for node in NODES} == NAMES
SCOPE = dict(math=math, copy=copy)
exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), "exec"), SCOPE)
resolve = SCOPE["resolved_lmr_parameters"]


class LmrParameterMetadataTests(unittest.TestCase):
    def test_complete_finite_integer_and_supported_inlet(self):
        baseline = resolve({}, "control")
        self.assertEqual(
            baseline,
            dict(intercept=0.7844, log_divisor=2.4696, min_depth=3, min_rank=4, max_extra=3),
        )
        for parameters in [
            None,
            {},
            dict(baseline, foreign=0),
            dict(baseline, intercept=True),
            dict(baseline, intercept=float("nan")),
            dict(baseline, log_divisor=0),
            dict(baseline, min_depth=3.0),
            dict(baseline, min_rank=True),
            dict(baseline, max_extra=9),
        ]:
            with self.subTest(parameters=parameters), self.assertRaises(SCOPE["Refused"]):
                resolve(dict(lmr_parameters=parameters), "control")
        for profile, method, supported in [
            ("cheap", "depth_rank", True),
            ("control", "fixed_one", True),
            ("control", "depth_rank", False),
        ]:
            with self.subTest(profile=profile, method=method), self.assertRaises(SCOPE["Refused"]):
                resolve(
                    dict(lmr_parameters=baseline, lmr_method=method), profile, supported=supported
                )
        self.assertEqual(resolve(dict(lmr=False, lmr_parameters=baseline), "control"), baseline)
        self.assertEqual(
            resolve(dict(lmr_parameters=dict(baseline, intercept=-0.0)), "control")[
                "intercept"
            ].hex(),
            "0x0.0p+0",
        )

    def test_preparation_reaches_both_normal_consumers_and_clears_stale_template(self):
        common = dict(
            evaluators=["distance"],
            profiles=["control"],
            tt_entries=1048576,
            use_tt=True,
            use_pvs=True,
            rules="standard",
            ruleset="standard_2p_threefold",
            family_B=2**30,
            controller_B=64 * 2**20,
            host_reserve_B=4 * 2**30,
            arena=dict(
                AI_workers=[2, 4],
                management_guardian=0,
                depth=64,
                max_nodes=1000000,
                time_ms=100,
                return_reserve_ms=5,
                max_plies=200,
            ),
        )
        parameters = dict(resolve({}, "control"), intercept=1.0)
        for selected in [common, dict(common, lmr_parameters=parameters, lmr_values=[False, True])]:
            variants = SCOPE["comparison_conditions"](selected)
            for variant in variants:
                cost = dict(namespace={}, lmr_parameters={"stale": True})
                SCOPE["apply_comparison_cost"](cost, selected, variant)
                arena = dict(
                    arena={},
                    engines=[
                        dict(kind="distance", lmr_parameters={"stale": True}) for _ in range(2)
                    ],
                )
                SCOPE["apply_comparison_arena"](arena, selected, [variant, variant])
                for config in [cost, *arena["engines"]]:
                    if "lmr_parameters" in selected:
                        self.assertEqual(config["lmr_parameters"], parameters)
                        self.assertIsNot(config["lmr_parameters"], parameters)
                    else:
                        self.assertNotIn("lmr_parameters", config)
                    self.assertIs(config["lmr"], variant["lmr"])
                    self.assertEqual(config["lmr_method"], "depth_rank")
        with self.assertRaises(SCOPE["Refused"]):
            SCOPE["comparison_conditions"](
                dict(common, profiles=["cheap"], lmr_parameters=parameters)
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
