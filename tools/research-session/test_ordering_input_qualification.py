"""New360 admission/final-publication definitions; no model or Search calls."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "lc360", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


class OrderingQualificationTests(unittest.TestCase):
    def fixture(self):
        f = lambda h: {
            "path": "/fake/bound-input",
            "sha256": h,
            "bytes": 1,
            "mode": "0644",
        }
        return {
            "phase": "ordering-qualification",
            "planned_slots": 20,
            "batch": None,
            "numerical_qualification": None,
            "build_manifest": f("a" * 64),
            "config": f(
                "4a1bb65baea495a99501a087aa59c8391fadbc9fa0719ad9c8350563388c2aa0"
            ),
            "schedule": f(
                "6671bbf8d04ed31fedbfeccdbfaf28dcf5c713e02866544f0d9c8de2110b8671"
            ),
            "canonical_plan_sha256": "ddb46782feb000f77f5e45d99ffde19d27bce9eaae0e7999afed97bb0a54948e",
            "models": [
                {
                    "descriptor": {
                        **f(
                            "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1"
                        ),
                        "bytes": 677,
                        "mode": "0600",
                    },
                    "weights": {
                        **f(
                            "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841"
                        ),
                        "bytes": 49284,
                    },
                    "evaluator_sha256": "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875",
                }
            ],
            "inputs": [f("b" * 64) for _ in range(6)],
            "dynamic_libraries": [
                {"file": f("c" * 64), "version": "FAKE"} for _ in range(5)
            ],
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
                self.assertEqual(
                    failed["data"]["numerical_qualification"]["status"], "UNKNOWN"
                )
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
                "observations.jsonl": b"".join(
                    json.dumps(x).encode() + b"\n" for x in r["roots"]
                ),
            }

        self.assertEqual(
            lc.ordering_qualification_evidence(e, build, values(report)), claim
        )
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
            lc,
            "document",
            return_value={"schema": lc.COMPLETION_SCHEMA, "status": "PASS"},
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


class Perf349Tests(unittest.TestCase):
    def fixture(self, batch=1):
        e = OrderingQualificationTests().fixture()

        def f(name):
            return {
                "path": "/fake/" + name,
                "sha256": "a" * 64,
                "bytes": 1,
                "mode": "0644",
            }

        plan = {
            "schema": "quoridor.current-search-perf349.inputs.v1",
            **{
                k: f(k)
                for k in (
                    "book",
                    "warm_origin",
                    "warm_config",
                    "warm_journal",
                    "assessment",
                    "resources",
                )
            },
        }
        plan["resources"].update(sha256=lc.PERF349_SUPPORT, bytes=7126)
        config = {
            "schema": lc.PERF349_SCHEMA,
            "algorithm": "cheap-static376-integer-parent-v1",
            "process_index": batch,
            "image_role": "A" if batch < 3 else "B",
            "plan": plan,
        }
        e.update(
            phase="compare",
            planned_slots=6,
            batch=batch,
            numerical_qualification=f("original-Q"),
            config=f("config"),
            schedule=f("schedule"),
            inputs=[
                plan[k]
                for k in (
                    "book",
                    "warm_origin",
                    "warm_config",
                    "warm_journal",
                    "assessment",
                    "resources",
                )
            ],
            canonical_plan_sha256=plan["assessment"]["sha256"],
        )
        e["argv"][1] = "ordering-cheap-assess"
        method = {
            "schema": "quoridor.current-search-perf349.assessment.v1",
            "algorithm": config["algorithm"],
            "planned_Search_calls": 36,
            "D4_calls": 30,
            "D6_calls": 6,
            "planned_sessions": 18,
            "node_liability": 108000000,
            "plain_calls": 24,
            "sampled_calls": 12,
            "calls_per_process": 6,
            "schedule_sha256": e["schedule"]["sha256"],
            "fixed_order": [
                "A/plain-before",
                "A/perf-sampled",
                "A/plain-after",
                "B/plain-before",
                "B/perf-sampled",
                "B/plain-after",
            ],
            "sampling": copy.deepcopy(lc.PERF349_SAMPLING),
        }
        docs = {
            e["config"]["path"]: config,
            e["schedule"]["path"]: lc.perf349_schedule(),
            plan["assessment"]["path"]: method,
            plan["resources"]["path"]: {
                "issue": "quoridor-4lc.349",
                "whole_B": 80 * 1048576,
            },
        }
        s = {
            "owner": "/fake",
            "output": "/fake/operation",
            "data_root": "/fake/native",
            "support": plan["resources"],
            "TMP": "/fake/TMP",
            "owned_outputs": ["/fake/TMP"],
            "env": {"TMPDIR": "/fake/TMP"},
            "data": [
                {"name": k, "path": "/fake/native/" + v, "limit_B": 512 * 1024}
                for k, v in (
                    ("planned", "planned.json"),
                    ("observations", "observations.jsonl"),
                    ("costs", "costs.jsonl"),
                    ("result", "result.json"),
                )
            ],
        }
        if batch % 3 == 1:
            s["perf"] = {
                "tool": {**f("perf"), "path": "/usr/bin/perf"},
                "output": "/fake/operation/perf.data",
            }
            s["data"].append(
                {
                    "name": "perf_data",
                    "path": s["perf"]["output"],
                    "limit_B": 12 * 1048576,
                }
            )
        return e, s, docs

    def test_perf349_projection_and_fixed_authority_refusals(self):
        rows = lc.perf349_schedule()
        self.assertEqual(len(rows), 36)
        self.assertEqual(sum(r["node_cap"] for r in rows), 108000000)
        for batch in range(6):
            local = [r for r in rows if r["process_index"] == batch]
            self.assertEqual(
                [(r["original_root_index"], r["depth"], r["session"]) for r in local],
                [(3, 4, 0), (1, 6, 1), (4, 4, 2), (5, 4, 2), (6, 4, 2), (7, 4, 2)],
            )
            self.assertEqual([r["local_ply"] for r in local], [None, None, 0, 2, 4, 6])
            e, _, docs = self.fixture(batch)
            with patch.object(lc, "document", side_effect=lambda r: docs[r["path"]]):
                lc.perf349_config(e)
                for key, value in (
                    ("planned_slots", 20),
                    ("batch", 9),
                    ("numerical_qualification", None),
                ):
                    wrong = copy.deepcopy(e)
                    wrong[key] = value
                    with self.assertRaises(lc.Refused):
                        lc.perf349_config(wrong)
                docs[e["schedule"]["path"]][batch * 6 + 2]["original_root_index"] = 6
                with self.assertRaises(lc.Refused):
                    lc.perf349_config(e)
        e, _, docs = self.fixture()
        with patch.object(lc, "document", side_effect=lambda r: docs[r["path"]]):
            docs[e["inputs"][4]["path"]]["sampling"]["frequency_Hz"] = 99
            with self.assertRaises(lc.Refused):
                lc.perf349_config(e)

    def test_perf349_standard_wrapper_plain_origin_and_partial_census_refusals(self):
        for batch in range(6):
            e, s, docs = self.fixture(batch)
            native = [
                "/fake/current-image",
                "ordering-cheap-assess",
                "--experiment",
                "/fake/experiment",
                "--experiment-sha256",
                "a" * 64,
            ]
            with (
                patch.object(lc, "document", side_effect=lambda r: docs[r["path"]]),
                patch.object(lc, "read_ref", return_value=b"tool"),
                patch.object(lc, "owned", side_effect=lambda p, o: Path(p)),
                patch.object(lc.os.path, "lexists", return_value=False),
            ):
                argv = lc.perf349_argv(s, e, native)
                if batch % 3 == 1:
                    self.assertEqual(
                        argv[:8],
                        [
                            "/usr/bin/perf",
                            "record",
                            "-e",
                            "cpu-clock:u",
                            "-F",
                            "49",
                            "--call-graph",
                            "dwarf,8192",
                        ],
                    )
                    self.assertEqual(argv[15:], ["--", *native])
                    for mutation in (
                        lambda w: w["perf"].update(output="/foreign/perf.data"),
                        lambda w: w["perf"]["tool"].update(path="/fake/perf"),
                        lambda w: w["data"][-1].update(limit_B=32 * 1048576),
                    ):
                        wrong = copy.deepcopy(s)
                        mutation(wrong)
                        with self.assertRaises(lc.Refused):
                            lc.perf349_argv(wrong, e, native)
                else:
                    self.assertEqual(argv, native)
                    s["perf"] = {}
                    with self.assertRaises(lc.Refused):
                        lc.perf349_argv(s, e, native)
        e, s, docs = self.fixture()
        with patch.object(lc, "document", side_effect=lambda r: docs[r["path"]]):
            with self.assertRaises((KeyError, ValueError)):
                lc.perf349_evidence(
                    s,
                    e,
                    {
                        "planned": b"{}",
                        "result": b"{}",
                        "observations": b"",
                        "costs": b"",
                        "perf_data": b"",
                    },
                )
            s["experiment"] = {"sha256": "e" * 64}
            selected = [
                row for row in lc.perf349_schedule() if row["process_index"] == 1
            ]
            expected = [
                {
                    "id": row["local_request_id"],
                    "pass": row["session"],
                    "diagnostic": False,
                    "profile": row["profile"],
                    "depth": row["depth"],
                    "root": row["original_root_index"],
                    "warm": row["warm"],
                    "node_cap": row["node_cap"],
                }
                for row in selected
            ]
            origin = {
                "guardian": {"pid": 10, "start_ticks": "100", "boot_id": "fake"},
                "profiler": {"pid": 11, "start_ticks": "101", "boot_id": "fake"},
            }
            planned = {
                "schema": "quoridor.current-search-perf349.intent.v1",
                "fixed_projection": selected,
                "requests": expected,
                "runtime_launch_origin": origin,
            }
            result = {
                "schema": "quoridor.current-search-perf349.result.v1",
                "experiment_sha256": "e" * 64,
                "config_sha256": e["config"]["sha256"],
                "schedule_sha256": e["schedule"]["sha256"],
                "process_index": 1,
                "image_role": "A",
                "campaign_planned": 36,
                "planned": 6,
                "planned_sessions": 3,
                "perf_sampled": True,
                "attempted": 6,
                "actual_Search_invocations": 6,
                "returned_Ok": 6,
                "returned_Err": 0,
                "session_setup_Ok": 3,
                "session_setup_Err": 0,
                "completed_requested_depth": 5,
                "planned_UNKNOWN": 1,
                "node_liability": 18000000,
                "status": "COMPLETED_WITH_UNKNOWN",
                "passes": [{"requests": n} for n in (1, 1, 4)],
                "root_whole_intervals": [{} for _ in range(6)],
                "runtime_launch_origin": origin,
            }
            values = {
                "planned": json.dumps(planned).encode(),
                "result": json.dumps(result).encode(),
                "observations": b"\n".join(
                    json.dumps(
                        {"request": r, "status": "UNKNOWN" if i == 5 else "COMPLETE"}
                    ).encode()
                    for i, r in enumerate(expected)
                ),
                "costs": b"\n".join(
                    json.dumps({"request_id": i}).encode() for i in range(6)
                ),
                "perf_data": b"PERFILE2fake",
            }
            with patch.object(Path, "exists", return_value=False):
                evidence = lc.perf349_evidence(s, e, values)
                self.assertEqual(evidence["UNKNOWN"], 1)
                self.assertIn("UNKNOWN", evidence["profiling_sufficiency"])
                wrong = dict(values)
                wrong["result"] = json.dumps(
                    {**result, "actual_Search_invocations": 5}
                ).encode()
                with self.assertRaises(lc.Refused):
                    lc.perf349_evidence(s, e, wrong)
                wrong = dict(values)
                wrong["observations"] = b"\n".join(
                    values["observations"].splitlines()[:5]
                )
                with self.assertRaises(lc.Refused):
                    lc.perf349_evidence(s, e, wrong)


if __name__ == "__main__":
    unittest.main()
