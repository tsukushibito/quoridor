"""NN0 metadata consumers; no geometry/Search/models or data payloads."""

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
loader = importlib.util.spec_from_file_location(
    "lifecycle", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)


def fixture():
    config = {
        "engines": [
            {
                "kind": "distance",
                "simd": False,
                "ordering_profile": "control",
                "lmr": True,
            }
        ],
        "arena": {
            "comparison": "whole_wall_time",
            "evaluator_sha256": ["e" * 64],
            "book": {"openings": [{"prefix": []}]},
        },
    }
    observation = {
        "engine_index": 0,
        "caller_seconds": 0.027,
        "thinking_seconds": 0.02,
        "value_stm": None,
        "accepted": True,
        "failure": None,
        "engine_error": None,
        "action": 13,
        "accepted_ns": 27_000_000,
        "admission_checked_ns": 26_000_000,
        "returned_ns": 25_000_000,
        "deadline_ns": 100_000_000,
        "completed_depth": None,
        "pv": [],
        "last_completed_iteration_ns": None,
        "completed_iteration_counters": None,
        "counters": {
            "completed_snapshot_validation_failed": False,
            "selection_reason": "legal_fallback_no_completed_iteration",
            "authority_receipt_ns": 20_000_000,
            "drain_finished_ns": 25_000_000,
            "inflight_after_drain": 0,
            "actual_search_namespace": {
                "evaluator": "distance-tanh-f32:sha256:" + "e" * 64 + ":simd=false",
                "rules": "research-standard-2p-threefold-goal-first-v1",
                "selectivity": "fullwidth-PVS-MPC-OFF-v1:cheap-static376-integer-parent-v1:control:lmr400-late4-depth3-minus1-pvs-verify-v1",
            },
            "actual_lmr_enabled": True,
        },
    }
    return config, {"game": 0, "observations": [observation], "moves": [13]}


class ArenaLmr400Tests(unittest.TestCase):
    def test_lmr400_actual_factory_method_and_typed_mode_are_required(self):
        config, row = fixture()
        lc.arena_observation(config, row)
        for mutate in ["profile", "mode", "typed_mode", "evaluator"]:
            bad = copy.deepcopy(row)
            c = bad["observations"][0]["counters"]
            if mutate == "profile":
                c["actual_search_namespace"]["selectivity"] = (
                    "fullwidth-PVS-MPC-OFF-v1:cheap-static376-integer-parent-v1:cheap:lmr400-late4-depth3-minus1-pvs-verify-v1"
                )
            elif mutate == "mode":
                c["actual_lmr_enabled"] = False
            elif mutate == "typed_mode":
                c["actual_lmr_enabled"] = 1
            else:
                c["actual_search_namespace"]["evaluator"] = "foreign-model:simd=false"
            with self.assertRaises(Exception):
                lc.arena_observation(config, bad)

    def test_lmr400_zero_completed_fallback_and_failure_are_not_completed_work(self):
        config, row = fixture()
        lc.arena_observation(config, row)
        self.assertIsNone(row["observations"][0]["completed_depth"])
        self.assertIsNone(row["observations"][0]["value_stm"])
        failed = copy.deepcopy(row)
        failed["observations"][0]["accepted"] = False
        failed["observations"][0]["failure"] = "engine_error"
        failed["observations"][0]["engine_error"] = "synthetic"
        failed["moves"] = []
        lc.arena_observation(config, failed)
        self.assertFalse(failed["observations"][0]["accepted"])
        forged = copy.deepcopy(row)
        forged["observations"][0]["failure"] = "engine_error"
        with self.assertRaises(Exception):
            lc.arena_observation(config, forged)

    def test_lmr400_declared_arena_resources_match_actual_family_and_roles(self):
        from unittest.mock import patch

        config = dict(
            workers=1,
            active_games=1,
            max_batch=1,
            cpu_cores=[2, 6],
            management_cpu_core=4,
            inference_cpu_core=None,
            arena=dict(comparison="whole_wall_time"),
        )
        for issue, gib in [("quoridor-4lc.374", 3), ("quoridor-4lc.400", 4)]:
            spec = dict(
                kind="run",
                experiment={},
                support={},
                child_cpu_cores=[2, 4, 6],
                limits=dict(worker_cpu=2, guardian_cpu=4, family_B=gib * 1024**3),
            )
            support = dict(
                issue=issue,
                resources=dict(
                    CPU=3,
                    threads=1,
                    GPU=0,
                    controller_included=True,
                    family_RAM_B=gib * 1024**3,
                ),
            )
            with patch.object(
                lc,
                "document",
                side_effect=[dict(phase="arena", config={}), config, support],
            ):
                self.assertEqual(lc.arena_cpu_cores(spec), [2, 4, 6])
            for invalid in [0, -1, True, (gib + 1) * 1024**3]:
                bad = copy.deepcopy(support)
                bad["resources"]["family_RAM_B"] = invalid
                with patch.object(
                    lc,
                    "document",
                    side_effect=[dict(phase="arena", config={}), config, bad],
                ):
                    with self.assertRaisesRegex(ValueError, "issued three-core"):
                        lc.arena_cpu_cores(spec)
            bad = copy.deepcopy(spec)
            bad["child_cpu_cores"] = [2, 3, 4]
            with patch.object(
                lc, "document", side_effect=[dict(phase="arena", config={}), config]
            ):
                with self.assertRaisesRegex(ValueError, "launch affinity"):
                    lc.arena_cpu_cores(bad)

    def test_arena400_false_serde_defaults_and_exact_publication_boundaries(self):
        import gzip
        import json

        def encode(value):
            return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

        def saved(config, actual):
            raw = (
                encode(
                    dict(
                        game=0,
                        started=False,
                        status="unknown",
                        failure="not_started",
                        observations=[],
                    )
                )
                + b"\n"
            )
            journal = gzip.compress(raw, mtime=0)

            def ref(name, data):
                return dict(
                    path=config["output"] + "/" + name,
                    sha256=lc.sha(data),
                    bytes=len(data),
                    mode="0644",
                )

            files = dict(journal=ref("completed.jsonl.gz", journal))
            publication = dict(
                schema=lc.ARENA_PUBLICATION,
                report=dict(
                    outcomes=[],
                    run_id="toy",
                    planned=1,
                    stopped=None,
                    all_workers_joined=True,
                ),
                archive=dict(
                    encoding="gzip-single-member-v1",
                    compressed=files["journal"],
                    raw_sha256=lc.sha(raw),
                    raw_bytes=len(raw),
                ),
                outcome_count=1,
                journal_count=1,
                journal_bytes=len(raw),
                journal_sha256=lc.sha(raw),
                failure_attribution=None,
                archive_wall_seconds=0.0,
                archive_allocated_bytes=4096,
            )
            result = encode(publication)
            files["result"] = ref("result.json", result)
            manifest = dict(
                result=publication,
                binding=dict(config=actual),
                cleanup=dict(archive_closed_verified=True, all_workers_joined=True),
                artifacts={
                    "completed.jsonl.gz": {
                        k: files["journal"][k] for k in ("sha256", "bytes", "mode")
                    },
                    "result.json": {
                        k: files["result"][k] for k in ("sha256", "bytes", "mode")
                    },
                },
            )
            native = encode(manifest)
            files["native_manifest"] = ref("manifest.json", native)
            return files, dict(journal=journal, result=result, native_manifest=native)

        base = dict(
            output="/synthetic-not-written/arena",
            games=1,
            run_id="toy",
            max_plies=1,
            arena=dict(retained_outcome_bytes=16384),
        )
        for flag in ("disable_continuation_static_ordering", "decision_only"):
            for enabled in (False, True):
                declared = copy.deepcopy(base)
                declared["arena"][flag] = enabled
                actual = copy.deepcopy(base)
                if enabled:
                    actual["arena"][flag] = True
                files, values = saved(declared, actual)
                result = lc.arena_reference_report(declared, files, values)
                self.assertEqual(result["outcomes"][0]["status"], "unknown")
                bad = copy.deepcopy(actual)
                bad["arena"][flag] = not enabled
                files, values = saved(declared, bad)
                with self.assertRaisesRegex(
                    ValueError,
                    "closed native manifest/summary/config/cleanup correspondence",
                ):
                    lc.arena_reference_report(declared, files, values)
        changed = copy.deepcopy(base)
        changed["max_plies"] = 2
        files, values = saved(base, changed)
        with self.assertRaisesRegex(
            ValueError, "closed native manifest/summary/config/cleanup correspondence"
        ):
            lc.arena_reference_report(base, files, values)
        files, values = saved(base, base)
        values["journal"] += b"x"
        with self.assertRaisesRegex(ValueError, "actual closed saved-file bytes"):
            lc.arena_reference_report(base, files, values)

    def test_arena400_typed_evaluator_content_binding_and_foreign_refusal(self):
        config, row = fixture()
        for engine, kind in [
            ("distance", "distance-tanh-f32"),
            ("nnue", "nnue-f32"),
            ("nnue", "nnue-residual-f32"),
            ("nnue_quantized", "nnue-i16"),
        ]:
            config["engines"][0]["kind"] = engine
            selected = copy.deepcopy(row)
            selected["observations"][0]["counters"]["actual_search_namespace"][
                "evaluator"
            ] = kind + ":sha256:" + "e" * 64 + ":simd=false"
            lc.arena_observation(config, selected)
            for wrong in [
                "e" * 64 + ":simd=false",
                kind + ":sha256:" + "f" * 64 + ":simd=false",
                "foreign:sha256:" + "e" * 64 + ":simd=false",
                kind + ":sha256:" + "e" * 64 + ":simd=true",
            ]:
                bad = copy.deepcopy(selected)
                bad["observations"][0]["counters"]["actual_search_namespace"][
                    "evaluator"
                ] = wrong
                with self.assertRaisesRegex(
                    ValueError,
                    "configured/actual arena ordering-LMR method correspondence",
                ):
                    lc.arena_observation(config, bad)
        config["engines"][0]["kind"] = "distance"
        wrong = copy.deepcopy(row)
        wrong["observations"][0]["counters"]["actual_search_namespace"]["evaluator"] = (
            "nnue-residual-f32:sha256:" + "e" * 64 + ":simd=false"
        )
        with self.assertRaisesRegex(
            ValueError, "configured/actual arena ordering-LMR method correspondence"
        ):
            lc.arena_observation(config, wrong)


if __name__ == "__main__":
    unittest.main()
