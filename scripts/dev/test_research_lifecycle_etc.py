"""New ETC-only metadata definition. UNRUN here; Root canonical import only."""

import importlib.util
from pathlib import Path
import sys
import unittest


class EtcMetadataBoundary(unittest.TestCase):
    def test_etc31_typed_mixed_custody_and_namespace_correspondence(self):
        root = Path("/workspaces/quoridor")
        spec = importlib.util.spec_from_file_location(
            "etc31_canonical_lifecycle", root / "scripts/dev/research-lifecycle.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        self.assertEqual(module.resolved_etc({}, "control"), "off")
        config = dict(etc="depth3_top2", search_threads=1, lmr_method="depth_rank")
        self.assertEqual(module.resolved_etc(config, "control"), "depth3_top2")
        for patch in [
            dict(etc=None),
            dict(etc=True),
            dict(etc="on"),
            dict(search_threads=2),
            dict(probcut={}),
            dict(probcut_samples=8),
            dict(root_ordering_quality=True),
            dict(neighbour_opportunity="off_shadow"),
            dict(history_provenance=[]),
            dict(lmr_method="fixed_one"),
        ]:
            with self.assertRaises(module.Refused):
                module.resolved_etc({**config, **patch}, "control")
        with self.assertRaises(module.Refused):
            module.resolved_etc(config, "cheap")
        with self.assertRaises(module.Refused):
            module.resolved_etc(config, "control", supported=False)
        record = dict(etc_requested="depth3_top2", etc_effective="depth3_top2")
        namespace = "etc-depth3-top2-v1:actual-normal-Control"
        module.etc_correspondence(
            config, record, profile="control", namespace=namespace
        )
        for bad in [
            {**record, "etc_effective": "off"},
            {**record, "etc_requested": None},
        ]:
            with self.assertRaises(module.Refused):
                module.etc_correspondence(
                    config, bad, profile="control", namespace=namespace
                )
        with self.assertRaises(module.Refused):
            module.etc_correspondence(
                config, record, profile="control", namespace="ordinary-Control"
            )
        with self.assertRaises(module.Refused):
            module.etc_correspondence(
                {}, record, profile="control", namespace=namespace
            )

        # Exercise the actual owner, not only its ETC helper. These are bounded
        # synthetic metadata fixtures; no native publication or geometry claim.
        from copy import deepcopy

        evaluator = "a" * 64
        baseline = dict(
            intercept=0.7844,
            log_divisor=2.4696,
            min_depth=3,
            min_rank=4,
            max_extra=3,
        )
        off_engine = dict(
            kind="nnue",
            simd=False,
            ordering_profile="control",
            search_threads=1,
            lmr=True,
            lmr_method="depth_rank",
            lmr_parameters=baseline,
            zero_stock_safe_race_method="path_tail",
        )
        on_engine = dict(off_engine, etc="depth3_top2")

        def alpha_observation(index, action, *, on):
            return dict(
                engine_index=index,
                accepted=True,
                failure=None,
                engine_error=None,
                action=action,
                accepted_ns=120,
                admission_checked_ns=110,
                returned_ns=100,
                deadline_ns=150,
                caller_seconds=0.01,
                thinking_seconds=0.008,
                value_stm=0.25,
                completed_depth=2,
                pv=[action],
                stop="time_limit",
                last_completed_iteration_ns=70,
                completed_iteration_counters=dict(nodes=1),
                counters=dict(
                    actual_search_namespace=dict(
                        evaluator="nnue-f32:sha256:" + evaluator + ":simd=false",
                        rules="research-standard-2p-threefold-goal-first-v1",
                        selectivity=("etc-depth3-top2-v1:" if on else "")
                        + "PVS-Control",
                    ),
                    requested_lmr_method="depth_rank",
                    actual_lmr_method_id="depth_rank",
                    lmr_reduction_rule="depth-rank",
                    requested_lmr_parameters=baseline,
                    actual_lmr_parameters=baseline,
                    actual_lmr_enabled=True,
                    actual_zero_stock_safe_race_enabled=True,
                    requested_zero_stock_safe_race_method="path_tail",
                    actual_zero_stock_safe_race_method_id="path_tail",
                    completed_snapshot_validation_failed=False,
                    authority_receipt_ns=80,
                    drain_finished_ns=100,
                    inflight_after_drain=0,
                    etc_requested="depth3_top2" if on else None,
                    etc_effective="depth3_top2" if on else "off",
                    requested_probcut_parameters=None,
                    actual_probcut_parameters=None,
                    requested_probcut_samples=0,
                    actual_probcut_samples=0,
                ),
            )

        def arena_fixture(engines, observations):
            return (
                dict(
                    engines=engines,
                    management_cpu_core=0,
                    arena=dict(
                        comparison="search_wall_time",
                        evaluator_sha256=[evaluator] * len(engines),
                        book=dict(openings=[dict(prefix=[4])]),
                    ),
                ),
                dict(
                    game=0,
                    observations=observations,
                    moves=[4] + [o["action"] for o in observations if o["accepted"]],
                ),
            )

        alpha_rows = [
            alpha_observation(0, 13, on=True),
            alpha_observation(1, 67, on=False),
        ]
        alpha_config, alpha_row = arena_fixture([on_engine, off_engine], alpha_rows)
        module.arena_observation(alpha_config, alpha_row)
        # Every mismatch is in the earlier ON observation, while the final OFF
        # observation remains valid. The old dedented block misses all three.
        for change in ["effective", "requested", "namespace"]:
            bad = deepcopy(alpha_row)
            counters = bad["observations"][0]["counters"]
            if change == "effective":
                counters["etc_effective"] = "off"
            elif change == "requested":
                counters["etc_requested"] = None
            else:
                counters["actual_search_namespace"]["selectivity"] = "PVS-Control"
            with self.subTest(earlier_on=change), self.assertRaises(module.Refused):
                module.arena_observation(alpha_config, bad)

        off_config, off_row = arena_fixture(
            [off_engine], [alpha_observation(0, 13, on=False)]
        )
        module.arena_observation(off_config, off_row)
        for change in ["effective", "requested", "namespace"]:
            bad = deepcopy(off_row)
            counters = bad["observations"][0]["counters"]
            if change == "effective":
                counters["etc_effective"] = "depth3_top2"
            elif change == "requested":
                counters["etc_requested"] = "depth3_top2"
            else:
                counters["actual_search_namespace"]["selectivity"] = (
                    "etc-depth3-top2-v1:PVS-Control"
                )
            with self.subTest(hidden_off=change), self.assertRaises(module.Refused):
                module.arena_observation(off_config, bad)

        # Retain existing real-owner LMR, acceptance, PV and receipt predicates.
        for change in ["parameters", "PV", "clock", "typed_acceptance"]:
            bad = deepcopy(alpha_row)
            observation = bad["observations"][0]
            if change == "parameters":
                observation["counters"]["actual_lmr_parameters"] = dict(
                    baseline, min_depth=4
                )
            elif change == "PV":
                observation["pv"] = [99]
            elif change == "clock":
                observation["counters"]["authority_receipt_ns"] = 150
            else:
                observation["accepted"] = 1
            with self.subTest(ordinary=change), self.assertRaises(module.Refused):
                module.arena_observation(alpha_config, bad)

        def nonalpha_observation(index, action, *, claustrophobia):
            observation = alpha_observation(index, action, on=False)
            observation.update(value_stm=None, completed_depth=None, pv=[])
            if claustrophobia:
                observation["counters"] = dict(
                    direct_child_reaped=True,
                    secondary=[],
                    authority_legal=True,
                    completed_simulations=1,
                    head_calls=1,
                )
            else:
                observation["counters"] = dict(
                    authority_receipt_ns=80,
                    authority_legal=True,
                    completed_simulations=1,
                    inflight_after_drain=0,
                    drain_finished_ns=100,
                    clock_contract="authority-action-receipt-v1",
                    clock_contract_sha256="04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d",
                )
            return observation

        for claustrophobia in [False, True]:
            engine = (
                dict(
                    kind="claustrophobia",
                    claustrophobia=dict(simulations=1, max_head_calls=1),
                )
                if claustrophobia
                else dict(kind="mcts")
            )
            rows = [
                nonalpha_observation(0, 13, claustrophobia=claustrophobia),
                nonalpha_observation(0, 67, claustrophobia=claustrophobia),
            ]
            config, row = arena_fixture([engine], rows)
            with self.subTest(all_nonalpha=engine["kind"]):
                module.arena_observation(config, row)
            # Continue rows after alpha must not reuse its engine/counters.
            mixed_config, mixed_row = arena_fixture(
                [on_engine, engine],
                [
                    alpha_observation(0, 13, on=True),
                    nonalpha_observation(1, 67, claustrophobia=claustrophobia),
                ],
            )
            module.arena_observation(mixed_config, mixed_row)
            bad = deepcopy(row)
            bad["observations"][0]["counters"]["authority_legal"] = False
            with self.assertRaises(module.Refused):
                module.arena_observation(config, bad)

        # Unaccepted records continue before any alpha engine/counter access.
        rejected_config, rejected_row = arena_fixture(
            [off_engine],
            [dict(engine_index=0, accepted=False, action=13)],
        )
        module.arena_observation(rejected_config, rejected_row)


if __name__ == "__main__":
    unittest.main()
