"""New managed SearchWallTime receipt/drain crossing; no scientific work."""

import copy
import importlib.util
import os
from pathlib import Path
import sys
import unittest

SOURCE = Path(
    os.environ.get(
        "CEDAR_RECEIPT_LIFECYCLE",
        Path(__file__).resolve().parents[2] / "scripts/dev/research-lifecycle.py",
    )
)
spec = importlib.util.spec_from_file_location("managed_receipt_target", SOURCE)
lc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lc
spec.loader.exec_module(lc)


class ManagedReceiptDrain(unittest.TestCase):
    def test_actual_managed_crossing_and_unchanged_rejections(self):
        config = dict(
            management_cpu_core=6,
            arena=dict(comparison="search_wall_time", decision_only=True),
            engines=[
                dict(
                    kind="nnue", zero_stock_safe_race=False, zero_stock_safe_race_method="manhattan"
                )
            ],
        )
        row = dict(
            observations=[
                dict(
                    engine_index=0,
                    accepted=True,
                    failure=None,
                    engine_error=None,
                    action=13,
                    caller_seconds=0.000000096,
                    thinking_seconds=0.000000090,
                    value_stm=0.2,
                    returned_ns=95,
                    admission_checked_ns=96,
                    accepted_ns=96,
                    deadline_ns=100,
                    completed_depth=4,
                    pv=[13],
                    counters=dict(
                        authority_receipt_ns=90,
                        drain_finished_ns=95,
                        inflight_after_drain=0,
                        completed_snapshot_validation_failed=False,
                        actual_zero_stock_safe_race_enabled=False,
                        requested_zero_stock_safe_race_method="manhattan",
                        actual_zero_stock_safe_race_method_id=None,
                    ),
                )
            ]
        )
        lc.arena_observation(config, row)
        for case in range(4):
            bad = copy.deepcopy(row)
            observation = bad["observations"][0]
            counters = observation["counters"]
            if case == 0:
                counters["authority_receipt_ns"] = 100
            elif case == 1:
                counters["drain_finished_ns"] = 94
            elif case == 2:
                counters["inflight_after_drain"] = 1
            else:
                observation["returned_ns"] = 89
                counters["drain_finished_ns"] = 89
            with self.assertRaisesRegex(lc.Refused, "main receipt/terminal drain"):
                lc.arena_observation(config, bad)
        config["management_cpu_core"] = None
        for mode in ["search_wall_time", "evaluator_wall_time"]:
            config["arena"]["comparison"] = mode
            with self.assertRaisesRegex(lc.Refused, "main receipt/terminal drain"):
                lc.arena_observation(config, row)
            direct = copy.deepcopy(row)
            direct["observations"][0]["returned_ns"] = 90
            direct["observations"][0]["counters"]["drain_finished_ns"] = 90
            lc.arena_observation(config, direct)


if __name__ == "__main__":
    unittest.main()
