"""New360 admission/final-publication definitions; no model or Search calls."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lc360", ROOT / "scripts/dev/research-lifecycle.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


class OrderingQualificationTests(unittest.TestCase):
    def fixture(self):
        f = lambda h: {"path": "/fake/bound-input", "sha256": h, "bytes": 1, "mode": "0644"}
        return {
            "phase": "ordering-qualification",
            "planned_slots": 20,
            "batch": None,
            "numerical_qualification": None,
            "build_manifest": f("a" * 64),
            "config": f("4a1bb65baea495a99501a087aa59c8391fadbc9fa0719ad9c8350563388c2aa0"),
            "schedule": f("6671bbf8d04ed31fedbfeccdbfaf28dcf5c713e02866544f0d9c8de2110b8671"),
            "canonical_plan_sha256": "ddb46782feb000f77f5e45d99ffde19d27bce9eaae0e7999afed97bb0a54948e",
            "models": [
                {
                    "descriptor": {
                        **f("46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1"),
                        "bytes": 677,
                        "mode": "0600",
                    },
                    "weights": {
                        **f("046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841"),
                        "bytes": 49284,
                    },
                    "evaluator_sha256": "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875",
                }
            ],
            "inputs": [f("b" * 64) for _ in range(6)],
            "dynamic_libraries": [{"file": f("c" * 64), "version": "FAKE"} for _ in range(5)],
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "argv": [
                "/fake/current-image",
                "ordering-qualify",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        }

    def test_exact_bootstrap_and_phase_caller_model_config_drift(self):
        e = self.fixture()
        lc.experiment_phase_check(e)
        for key, value in [
            ("phase", "compare"),
            ("planned_slots", True),
            ("planned_slots", 21),
            ("numerical_qualification", {}),
            ("models", []),
        ]:
            wrong = copy.deepcopy(e)
            wrong[key] = value
            with self.assertRaises(lc.Refused):
                lc.experiment_phase_check(wrong)
        for key in ["config", "schedule"]:
            wrong = copy.deepcopy(e)
            wrong[key]["sha256"] = "0" * 64
            with self.assertRaises(lc.Refused):
                lc.experiment_phase_check(wrong)
        wrong = copy.deepcopy(e)
        wrong["argv"][1] = "ordering-assess"
        with self.assertRaises(lc.Refused):
            lc.experiment_phase_check(wrong)
        wrong = copy.deepcopy(e)
        wrong["models"][0]["weights"]["sha256"] = "0" * 64
        with self.assertRaises(lc.Refused):
            lc.experiment_phase_check(wrong)

    def test_only_authoritative_clean_finalize_admits_claim(self):
        e = self.fixture()
        candidate = {
            "kind": "run",
            "experiment": {},
            "status": "PASS",
            "cleanup_complete": True,
            "remaining": [],
            "data": {"numerical_qualification": {"status": None}},
        }
        with patch.object(lc, "document", return_value=e):
            clean = copy.deepcopy(candidate)
            lc.finalize_numerical_claim(clean)
            self.assertEqual(clean["data"]["numerical_qualification"]["status"], "PASS")
            for key, value in [
                ("status", "FAILED"),
                ("status", "CANCELLED"),
                ("cleanup_complete", False),
                ("remaining", [1]),
            ]:
                failed = copy.deepcopy(candidate)
                failed[key] = value
                lc.finalize_numerical_claim(failed)
                self.assertEqual(failed["data"]["numerical_qualification"]["status"], "UNKNOWN")
        self.assertIsNone(candidate["data"]["numerical_qualification"]["status"])

    def test_full_journal_partial_precision_and_current_artifact_subject(self):
        e = self.fixture()
        build = {"artifact": {"sha256": "a" * 64}}
        claim = lc.numerical_fields({**e, "phase": "compare"}, build)
        claim["status"] = None
        rows = [
            {
                "id": i,
                "status": "QUALIFIED",
                "Search_calls": 0,
                "model_evaluations_attempted": 2,
                "model_evaluations_returned": 2,
                "parent_unchanged": True,
                "plain_bits": 0,
                "scratch_bits": 0,
                "plain_value": 0.0,
                "scratch_value": 0.0,
            }
            for i in range(20)
        ]
        report = {
            "schema": "quoridor.continuation360.input-qualification.v1",
            "status": "COMPLETE",
            "planned": 20,
            "qualified": 20,
            "Search_calls": 0,
            "roots": rows,
            "numerical_qualification": claim,
        }

        def values(r):
            return {
                "result.json": json.dumps(r).encode(),
                "observations.jsonl": b"".join(json.dumps(x).encode() + b"\n" for x in r["roots"]),
            }

        self.assertEqual(lc.ordering_qualification_evidence(e, build, values(report)), claim)
        for mutate in [
            lambda r: r["roots"].pop(),
            lambda r: r["roots"][0].update(status="UNKNOWN"),
            lambda r: r["roots"][0].update(scratch_bits=1),
            lambda r: r["numerical_qualification"].update(artifact_sha256="c" * 64),
        ]:
            wrong = copy.deepcopy(report)
            mutate(wrong)
            with self.assertRaises(lc.Refused):
                lc.ordering_qualification_evidence(e, build, values(wrong))

    def test_publication_error_preserves_original_and_all_secondary(self):
        primary = {"type": "Original", "message": "native failed"}
        old = {"stage": "owed_finalizer", "message": "close failed"}
        c = {
            "kind": "run",
            "experiment": {},
            "status": "FAILED",
            "primary": primary,
            "secondary": [old],
            "cleanup_complete": False,
            "remaining": [],
            "data": {"numerical_qualification": {"status": None}},
        }
        with patch.object(lc, "document", side_effect=OSError("input drift")):
            lc.finalize_numerical_claim(c)
        self.assertIs(c["primary"], primary)
        self.assertIs(c["secondary"][0], old)
        self.assertEqual(c["secondary"][1]["stage"], "numerical_claim_finalization")
        self.assertEqual(c["data"]["numerical_qualification"]["status"], "UNKNOWN")

    def test_provisional_or_failed_manifest_cannot_admit_Search(self):
        e = self.fixture()
        e["phase"] = "compare"
        e["argv"][1] = "ordering-assess"
        e["numerical_qualification"] = {"path": "/fake/candidate.json"}
        with patch.object(
            lc, "document", return_value={"schema": lc.COMPLETION_SCHEMA, "status": "PASS"}
        ):
            with self.assertRaises(lc.Refused):
                lc.numerical_check(e, {})
        e["numerical_qualification"] = {"path": "/fake/manifest.json"}
        failed = {
            "schema": lc.COMPLETION_SCHEMA,
            "status": "FAILED",
            "cleanup_complete": True,
            "remaining": [],
            "primary": {"message": "outer"},
            "secondary": [{"stage": "owed"}],
            "data": {"status": "PASS"},
        }
        with patch.object(lc, "document", return_value=failed):
            with self.assertRaises(lc.Refused):
                lc.numerical_check(e, {})


if __name__ == "__main__":
    unittest.main()
