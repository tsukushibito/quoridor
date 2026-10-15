"""New412 owning metadata definitions; author execution is forbidden."""

import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

loader = importlib.util.spec_from_file_location(
    "lmr412_current", Path("/workspaces/quoridor/scripts/dev/research-lifecycle.py")
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


class ResearchLmrStandardTests(unittest.TestCase):
    def test_lmr412_preparation_default_and_explicit_controls_reach_both_consumers(
        self,
    ):
        common = dict(
            evaluators=("distance",),
            profiles=("control",),
            tt_entries=1048576,
            use_tt=True,
            use_pvs=True,
            rules="standard",
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
        self.assertEqual(
            lc.comparison_conditions(common),
            [
                dict(
                    evaluator="distance",
                    profile="control",
                    lmr=True,
                    lmr_method="depth_rank",
                )
            ],
        )
        for selected in [
            common,
            dict(common, lmr_values=(False, True), lmr_method="fixed_one"),
        ]:
            variants = lc.comparison_conditions(selected)
            for variant in variants:
                expected_method = selected.get("lmr_method", "depth_rank")
                self.assertEqual(variant["lmr_method"], expected_method)
                config = dict(
                    namespace=dict(evaluator="toy", selectivity="native-owned"),
                    lmr=False,
                    lmr_method="stale-template",
                )
                lc.apply_comparison_cost(config, selected, variant)
                self.assertIs(config["lmr"], variant["lmr"])
                self.assertEqual(config["lmr_method"], expected_method)
                self.assertEqual(config["namespace"]["selectivity"], "native-owned")
                arena = dict(
                    arena={}, engines=[dict(kind="distance"), dict(kind="distance")]
                )
                lc.apply_comparison_arena(arena, selected, [variant, variant])
                for engine in arena["engines"]:
                    self.assertIs(engine["lmr"], variant["lmr"])
                    self.assertEqual(engine["lmr_method"], expected_method)
        # Raw config enable omission remains OFF; method omission alone is not
        # normal-research preparation. Explicit null/type errors remain errors.
        raw = dict(
            roots=[dict(input=0, pointer="", field="moves", label="toy")],
            profile="control",
            tt_entries=4096,
            use_tt=True,
            use_pvs=True,
            namespace=dict(
                evaluator="toy", rules="standard", selectivity="native-owned"
            ),
            output_bytes=1000,
            record_bytes=100,
        )
        experiment = dict(config={}, schedule={}, inputs=[{}], rules="standard")
        with patch.object(lc, "document", side_effect=[raw, []]):
            actual, _ = lc.measurement_config(experiment)
        self.assertNotIn("lmr", actual)
        for bad in [None, True, 1, "unknown"]:
            config = dict(raw, lmr_method=bad)
            with patch.object(lc, "document", side_effect=[config, []]):
                with self.assertRaises(lc.Refused):
                    lc.measurement_config(experiment)

    def test_lmr412_arena_omission_requires_new_default_and_preserves_explicit_fixed(
        self,
    ):
        sha = "0" * 64
        for enabled in [False, True]:
            engine = dict(
                kind="distance",
                ordering_profile="control",
                lmr=enabled,
                simd=False,
                depth=1,
            )
            config = dict(
                engines=[engine],
                arena=dict(
                    comparison="evaluator_fixed_depth",
                    evaluator_sha256=[sha],
                    book=dict(openings=[dict(prefix=[])]),
                ),
            )
            counters = dict(
                actual_search_namespace=dict(
                    evaluator="distance-tanh-f32:sha256:" + sha + ":simd=false",
                    rules="research-standard-2p-threefold-goal-first-v1",
                    selectivity="native-owned",
                ),
                requested_lmr_method="depth_rank",
                actual_lmr_enabled=enabled,
                actual_lmr_method_id="native-owned-method" if enabled else None,
                lmr_reduction_rule="native-owned-rule" if enabled else None,
                completed_snapshot_validation_failed=False,
            )
            observation = dict(
                engine_index=0,
                accepted=True,
                failure=None,
                engine_error=None,
                action=3,
                accepted_ns=3,
                admission_checked_ns=2,
                returned_ns=1,
                deadline_ns=None,
                completed_depth=1,
                pv=[3],
                value_stm=0.125,
                stop="depth_cap",
                counters=counters,
            )
            row = dict(game=0, moves=[3], observations=[observation])
            lc.arena_observation(config, row)
            wrong = copy.deepcopy(row)
            wrong["observations"][0]["counters"]["requested_lmr_method"] = "fixed_one"
            with self.assertRaises(lc.Refused):
                lc.arena_observation(config, wrong)
            explicit = copy.deepcopy(config)
            explicit["engines"][0]["lmr_method"] = "fixed_one"
            lc.arena_observation(explicit, wrong)
        # Placeholder metadata here deliberately does not certify native IDs;
        # the typed runtime/session412 definition owns that correspondence.

    def test_lmr413_retired_names_rejected_by_current_measurement(self):
        raw = dict(
            roots=[dict(input=0, pointer="", field="moves", label="toy")],
            profile="control",
            tt_entries=4096,
            use_tt=True,
            use_pvs=True,
            namespace=dict(
                evaluator="toy", rules="standard", selectivity="native-owned"
            ),
            output_bytes=1000,
            record_bytes=100,
        )
        experiment = dict(config={}, schedule={}, inputs=[{}], rules="standard")
        for name in [
            "depth_rank_late_one",
            "depth_rank_deep_two",
            "depth_rank_early_one",
        ]:
            for enabled in [False, True]:
                with patch.object(
                    lc,
                    "document",
                    side_effect=[dict(raw, lmr_method=name, lmr=enabled), []],
                ):
                    with self.assertRaisesRegex(lc.Refused, "measurement LMR method"):
                        lc.measurement_config(experiment)


if __name__ == "__main__":
    unittest.main()
