"""New33 canonical metadata boundary; definitions UNRUN privately."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path("/workspaces/quoridor")


class EtcOpportunityMetadata(unittest.TestCase):
    def test_typed_request_and_actual_multirow_measurement_evidence(self):
        sys.path.insert(0, str(ROOT / "scripts/dev"))
        spec = importlib.util.spec_from_file_location(
            "etc33_canonical_owner", ROOT / "scripts/dev/research-lifecycle.py"
        )
        owner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = owner
        spec.loader.exec_module(owner)
        config = dict(
            etc_opportunity="before_first_v1",
            profile="control",
            search_threads=1,
            use_tt=True,
            use_pvs=True,
            namespace=dict(
                evaluator="synthetic",
                rules="research-standard-2p-threefold-goal-first-v1",
                selectivity="PVS",
            ),
        )
        requests = [dict(depth=5, node_cap=10000)]
        self.assertEqual(owner.etc_opportunity_setting(config, requests), "before_first_v1")
        for change in [
            dict(etc_opportunity=None),
            dict(etc_opportunity="off"),
            dict(search_threads=2),
            dict(probcut_samples=1),
            dict(root_ordering_quality=True),
            dict(time_reserve_ms=5),
            dict(use_tt=False),
        ]:
            with self.assertRaises(Exception):
                owner.etc_opportunity_setting(dict(config, **change), requests)
        for request in [
            dict(depth=6, node_cap=10000),
            dict(depth=5, node_cap=1000001),
            dict(depth=5, node_cap=10000, time_limit_ms=100),
            dict(depth=5, node_cap=10000, observe_lmr=True),
        ]:
            with self.assertRaises(Exception):
                owner.etc_opportunity_setting(config, [request])
        counters = (
            "attempted_children",
            "legal_count",
            "children",
            "terminal_proofs",
            "terminal_cuts",
            "lookups",
            "slot_absent",
            "board_mismatch",
            "context_mismatch",
            "depth_mismatch",
            "excluded_bound",
            "nonfinite_value",
            "illegal_or_missing_best",
            "qualified_noncut",
            "true_tt_cuts",
        )
        parents = [
            dict.fromkeys(counters, 0)
            | dict(slot=i, selected=False, complete=False, witnesses=[None, None])
            for i in range(8)
        ]
        parents[0].update(
            selected=True,
            complete=True,
            depth=3,
            ply=0,
            stock=20,
            legal_count=1,
            attempted_children=1,
            children=1,
            lookups=1,
            slot_absent=1,
        )
        report = dict(
            protocol="before-first-all-legal-v1",
            parent_limit=8,
            child_limit=1672,
            parents=parents,
            capacity_unready=[0] * 8,
            infinite_window=[0] * 8,
            child_lookups=1,
            child_transitions=1,
            parent_returns=1,
            actual_namespace=dict(config["namespace"], selectivity="control:pvs:lmr"),
            shadow_only=True,
            cutoff_returns=0,
            TT_writes=0,
            history_updates=0,
            extra_evaluations=0,
        )
        measured = dict(
            returned="Ok",
            actual_selectivity="control:pvs:lmr",
            etc_opportunity_requested="before_first_v1",
            work=dict(etc_opportunity=report),
        )
        rows = [dict(status="COMPLETE", measurement=copy.deepcopy(measured)) for _ in range(2)]
        experiment = dict(
            config=dict(path="synthetic-config", sha256="0" * 64, bytes=1, mode="0644")
        )

        def evidence(records, actual_config=config):
            values = dict(
                measurements=("".join(json.dumps(row) + "\n" for row in records)).encode(),
                result=json.dumps(
                    dict(
                        measurements=records,
                        errors=[],
                        planned=len(records),
                        calls=len(records),
                        complete=sum(row.get("status") == "COMPLETE" for row in records),
                        uncompleted=sum(row.get("status") != "COMPLETE" for row in records),
                        unperformed=0,
                    )
                ).encode(),
            )
            with patch.object(owner, "document", return_value=actual_config):
                return owner.measurement_evidence({}, experiment, values)

        result = evidence(rows)
        self.assertEqual(result["journal_rows"], 2)
        self.assertTrue(result["journal_result_rows_agree"])
        self.assertFalse(result["unreturned_tail"])
        # Earlier mismatch must refuse even though the final row is valid.
        for key, value in [("child_transitions", 0), ("protocol", "wrong"), ("TT_writes", 1)]:
            bad = copy.deepcopy(rows)
            bad[0]["measurement"]["work"]["etc_opportunity"][key] = value
            with self.assertRaises(Exception):
                evidence(bad)
        bad = copy.deepcopy(rows)
        bad[0]["measurement"]["work"]["etc_opportunity"]["actual_namespace"]["selectivity"] = (
            "other-table"
        )
        with self.assertRaises(Exception):
            evidence(bad)
        # A foreign evaluator in an earlier row must not be hidden by a valid final row.
        bad = copy.deepcopy(rows)
        bad[0]["measurement"]["work"]["etc_opportunity"]["actual_namespace"]["evaluator"] = (
            "foreign-nonempty-evaluator"
        )
        self.assertEqual(
            bad[-1]["measurement"]["work"]["etc_opportunity"]["actual_namespace"]["evaluator"],
            config["namespace"]["evaluator"],
        )
        with self.assertRaises(Exception):
            evidence(bad)
        hidden = copy.deepcopy(rows)
        with self.assertRaises(Exception):
            evidence(hidden, {k: v for k, v in config.items() if k != "etc_opportunity"})
        # Error/absent data is preserved UNKNOWN, never invented as a complete report.
        error = [
            dict(
                status="UNKNOWN",
                measurement=dict(
                    returned="Err", error="synthetic", etc_opportunity_requested="before_first_v1"
                ),
            )
        ]
        self.assertEqual(evidence(error)["observed_complete"], 0)
        off = [dict(status="COMPLETE", measurement=dict(returned="Ok", work={}))]
        self.assertEqual(evidence(off, {})["journal_rows"], 1)


if __name__ == "__main__":
    unittest.main()
