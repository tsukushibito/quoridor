"""Fake fixed-teacher responses; no actual Rust/upstream search or data generation."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from othello_arena import generation, teacher
from othello_arena.engines import EgaroucidFixedTime
from othello_arena.protocol import EngineError
from othello_arena.teacher import estimate, response_row


class TeacherTests(unittest.TestCase):
    def observation(self):
        return {
            "gameId": "dev/t1",
            "openingFamily": "dev/f1",
            "state": {"toMove": 2},
            "legalMoves": [18, 20],
        }

    def response(self, score=-3):
        return {
            "ok": True,
            "move": 20,
            "score": score,
            "scoreKind": "engine_estimate_stm",
            "completedDepth": 20,
            "probability": 74,
            "elapsedMs": 1000.55,
            "budgetMs": 1000,
            "nodes": 123,
            "proven": False,
        }

    def test_raw_retained_and_stm_sign_not_flipped_for_white(self):
        class FakeProcess:
            def json_request(_, payload, *, deadline):
                return self.response()

        adapter = EgaroucidFixedTime(FakeProcess())
        raw = adapter.search_response(self.observation()["state"], deadline=10)
        self.assertIs(raw, adapter.last_search)
        row = response_row(self.observation(), raw, "fixed", 1001.5)
        self.assertEqual(row["targetCentidiscs"], -300)
        self.assertEqual(
            set(row["teacher"]),
            {
                "id",
                "rawSTMScore",
                "scorePerspective",
                "scoreUnits",
                "scaleToCentidiscs",
                "bound",
                "proven",
                "completedDepth",
                "reportedProbability",
                "internalElapsedMs",
                "outerWallMs",
                "requestedTimeMs",
            },
        )
        self.assertEqual(row["teacher"]["rawSTMScore"], -3)
        self.assertEqual(row["teacher"]["reportedProbability"], 74)
        self.assertEqual(row["teacher"]["internalElapsedMs"], 1000.55)
        self.assertEqual(row["teacher"]["bound"], "UNKNOWN")
        self.assertIs(row["teacher"]["proven"], False)
        row2 = response_row(self.observation(), dict(raw, score=7, proven=None), "fixed", 1001.5)
        self.assertEqual(row2["targetCentidiscs"], 700)  # Same game may have different estimates.
        self.assertIsNone(row2["teacher"]["proven"])

    def test_rejects_bad_nonfinite_illegal_incomplete(self):
        for change in (
            {"score": float("nan")},
            {"score": 65},
            {"move": None},
            {"completedDepth": 0},
            {"proven": 1},
            {"scoreKind": "unknown"},
        ):
            with self.subTest(patch=change), self.assertRaises(EngineError):
                response_row(self.observation(), dict(self.response(), **change), "fixed", 1000)

    def test_reset_outside_search_and_late_result_stops_without_retry(self):
        times = iter([0, 0.01, 0.02, 1.121])
        calls = []

        class FakeAdapter:
            def reset(_, **kwargs):
                calls.append("reset")

            def search_response(_, state, **kwargs):
                calls.append("search")
                return self.response()

        evidence = {}
        with self.assertRaises(EngineError) as failure:
            estimate(
                FakeAdapter(), self.observation(), "fixed", evidence, clock=lambda: next(times)
            )
        self.assertEqual(failure.exception.kind, "timeout")
        self.assertEqual(calls, ["reset", "search"])
        self.assertEqual(evidence["status"], "failed")
        self.assertEqual(evidence["rawResponse"]["score"], -3)

    def test_nonfinite_failure_evidence_remains_finite_json(self):
        class FakeAdapter:
            def reset(_, **kwargs):
                pass

            def search_response(_, state, **kwargs):
                return self.response(float("nan"))

        evidence = {}
        with self.assertRaises(EngineError):
            estimate(FakeAdapter(), self.observation(), "fixed", evidence)
        self.assertIsNone(evidence["rawResponse"])
        self.assertIn("NaN", evidence["rejectedRawJSON"])
        json.dumps(evidence, allow_nan=False)

    def test_persistent_initialization_once_and_first_bad_stops(self):
        calls = []

        class FakeProcess:
            cleanup = {"unexpectedExit": False, "directReaped": True}

            def __init__(_, *args, **kwargs):
                calls.append("init")

            def json_request(_, payload, **kwargs):
                op = payload["op"]
                calls.append(op)
                if op == "info":
                    return {
                        "label": "Console7.8.1-engine + fixed-time adapter",
                        "engineCommit": "570d5e0a478c9d720d75de06a5d31995f412704a",
                        "api": "tree_search_legal(time_limit_ms)",
                        "searchThreads": 1,
                        "workerPool": 0,
                        "hashLevel": 20,
                        "activeTTBytes": 25165872,
                        "book": False,
                        "ponder": False,
                    }
                if op == "search":
                    return self.response() if calls.count("search") == 1 else self.response(65)
                return {"ok": True}

            def close(_):
                calls.append("close")

        class Native:
            def request(_, *args, **kwargs):
                return {"status": {"terminal": False, "mustPass": False, "legalMoves": [20]}}

        config = {
            "teacher": {
                "id": "fixed",
                "upstreamCommit": "570d5e0a478c9d720d75de06a5d31995f412704a",
                "engine": {"argv": ["/unused"], "cwd": "/unused"},
                "source": "fixture pinned source",
                "weights": "fixture weights",
                "adapter": "fixture adapter",
                "args": ["/unused"],
            },
            "limits": {"teacherAttempts": 1024},
        }
        records = [{"placement": p, "row": self.observation()} for p in (8, 12, 20)]
        rows, requests, session = [], [], {}
        with (
            patch("othello_arena.protocol.Process", FakeProcess),
            patch("othello_arena.__main__.checked_spec"),
        ):
            with self.assertRaises(EngineError):
                teacher.collect(
                    Native(),
                    config,
                    records,
                    Path("/unused"),
                    rows,
                    requests,
                    session,
                    cancelled=lambda: False,
                )
        self.assertEqual(calls, ["init", "info", "reset", "search", "reset", "search", "close"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(requests), 2)  # third state remains UNRUN, no retry/refill
        self.assertEqual(requests[1]["status"], "failed")
        self.assertEqual(requests[1]["rawResponse"]["score"], 65)
        self.assertEqual(requests[1]["rawResponse"]["nodes"], 123)
        self.assertIsNone(session["transportMs"])
        self.assertIsNone(session["cancelJoinMs"])
        self.assertTrue(session["cleanup"]["directReaped"])

    def test_unbound_teacher_identity_is_refused_before_process_start(self):
        spec = {
            "id": "fixed",
            "upstreamCommit": "570d5e0a478c9d720d75de06a5d31995f412704a",
            "engine": {"argv": ["/unused"]},
            "source": "fixture",
            "weights": "fixture",
            "adapter": "fixture",
            "args": ["/different"],
        }
        with patch("othello_arena.protocol.Process", side_effect=AssertionError("must not start")):
            with self.assertRaisesRegex(EngineError, "args differ"):
                teacher.collect(
                    None,
                    {"teacher": spec},
                    [],
                    Path("/unused"),
                    [],
                    [],
                    {},
                    cancelled=lambda: False,
                )


class TeacherGenerationTests(unittest.TestCase):
    def test_preflight_failure_retains_scheduled_unrun_without_starting_process(self):
        config = {
            "stage": "teacher",
            "labelKind": "teacherEstimate",
            "seed": 1,
            "engine": {},
            "canonicalSource": {},
            "openingExclusions": [],
            "samplePlacements": [8],
            "samplePassPolicy": "after-mandatory-pass",
            "duplicatePolicy": generation.DUPLICATE_POLICY,
            "namespace": "development/fake",
            "limits": {
                "teacherAttempts": 1024,
                "rows": 896,
                "inputBytes": 65536,
                "evidenceBytes": 65536,
                "retainedBytes": 1048576,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(generation, "_read", return_value=config),
                patch.object(generation, "_validate"),
                patch.object(generation, "_canonical"),
                patch.object(generation, "_excluded_keys"),
                patch.object(generation, "_frozen_openings", return_value=[]),
                patch.object(generation, "_frozen_observations", return_value=[{}, {}, {}]),
                patch.object(
                    generation, "checked_spec", side_effect=ValueError("fake binary mismatch")
                ),
                patch.object(generation, "Process", side_effect=AssertionError("must not start")),
            ):
                report = generation.run({}, Path(tmp) / "output")
        self.assertEqual(report["status"], "STOP")
        self.assertEqual(report["teacherUnrun"], 3)
        self.assertEqual(report["teacherAttempted"], 0)
        self.assertEqual(report["failure"]["message"], "fake binary mismatch")

    def test_output_bound_stop_cannot_advertise_complete_observations(self):
        class Process:
            cleanup = {"unexpectedExit": False}

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        config = {
            "stage": "trajectories",
            "labelKind": "teacherEstimate",
            "seed": 1,
            "engine": {"argv": ["/unused"], "cwd": "/unused"},
            "canonicalSource": {},
            "openingExclusions": [],
            "samplePlacements": [8],
            "samplePassPolicy": "after-mandatory-pass",
            "duplicatePolicy": generation.DUPLICATE_POLICY,
            "namespace": "development/fake",
            "openings": {},
            "limits": {
                "rows": 896,
                "inputBytes": 65536,
                "evidenceBytes": 1,
                "retainedBytes": 1048576,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(generation, "_read", return_value=config),
                patch.object(generation, "_validate"),
                patch.object(generation, "_canonical"),
                patch.object(generation, "_excluded_keys"),
                patch.object(generation, "_frozen_openings", return_value=[]),
                patch.object(generation, "checked_spec"),
                patch.object(generation, "Process", Process),
                patch.object(generation, "_trajectory_samples"),
            ):
                report = generation.run({}, Path(tmp) / "output")
            observations = json.loads((Path(tmp) / "output/observations.json").read_bytes())
        self.assertEqual(report["status"], "STOP")
        self.assertFalse(observations["complete"])

    def test_explicit128_config_and_frozen_unlabeled_holdout_boundary(self):
        slots = [
            {
                "gameId": f"development/new/{s}{i:03}",
                "openingFamily": f"development/new/f{s}{i:03}",
                "split": s,
            }
            for s, n in (("T", 96), ("V", 16), ("H", 16))
            for i in range(n)
        ]
        config = {
            "labelKind": "teacherEstimate",
            "seed": 20261023,
            "stage": "trajectories",
            "purpose": "fixed teacher estimates",
            "launchBinding": {"fixture": True},
            "slots": slots,
            "namespace": "development/new",
            "duplicatePolicy": generation.DUPLICATE_POLICY,
            "limits": {
                "openingAttempts": 4096,
                "rows": 896,
                "teacherAttempts": 1024,
                "inputBytes": 1048576,
                "evidenceBytes": 2097152,
                "retainedBytes": 4194304,
            },
            "samplePlacements": [8, 12, 20, 24, 36, 40, 48, 52],
            "samplePassPolicy": "after-mandatory-pass",
            "openingExclusions": [{"count": 4}, {"count": 24}],
            "source": generation._ref(generation.__file__),
            "openings": {"fixture": "frozen"},
        }
        generation._validate(config)
        with self.assertRaises(generation.GenerationStop):
            generation._validate(
                dict(config, limits=dict(config["limits"], inputBytes=16 * 1024**2 + 1))
            )
        with self.assertRaises(generation.GenerationStop):
            generation._validate(dict(config, labelKind="gameOutcome"))
        state = {"version": 1, "board": [1] * 12 + [0] * 52, "toMove": 1}
        record = {
            "placement": 8,
            "split": "T",
            "row": {
                "gameId": slots[0]["gameId"],
                "openingFamily": slots[0]["openingFamily"],
                "state": state,
            },
        }
        package = {
            "complete": True,
            "outcomeLabels": False,
            "openings": config["openings"],
            "source": config["source"],
            "duplicatePolicy": config["duplicatePolicy"],
            "seed": config["seed"],
            "samplePlacements": config["samplePlacements"],
            "samplePassPolicy": config["samplePassPolicy"],
            "records": [record],
        }
        config["observations"] = {"fixture": "unlabeled"}
        with patch.object(generation, "_read", return_value=package):
            self.assertEqual(
                generation._frozen_observations(config, slots, lambda _: b"board"), [record]
            )
            for bad in (
                dict(record, placement=12),
                dict(record, split="H"),
                dict(record, row=dict(record["row"], targetCentidiscs=100)),
                {
                    "placement": 8,
                    "split": "H",
                    "row": {
                        "gameId": slots[-1]["gameId"],
                        "openingFamily": slots[-1]["openingFamily"],
                        "state": state,
                    },
                },
            ):
                package["records"] = [bad]
                with self.assertRaises(generation.GenerationStop):
                    generation._frozen_observations(config, slots, lambda _: b"board")

    def test_config_failure_is_primary_and_starts_no_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text('{"labelKind":"bad","seed":42}')
            with patch.object(generation, "Process", side_effect=AssertionError("must not start")):
                result = generation.run(generation._ref(config), Path(tmp) / "output")
        self.assertEqual(result["status"], "STOP")
        self.assertEqual(result["failure"]["kind"], "GenerationStop")
        self.assertIn("explicit labelKind", result["failure"]["message"])

    def test_pass_resolved_by_authority_before_observation_at_same_placement(self):
        from test_arena_generation import FixtureNative

        native = FixtureNative()
        opening = {
            "gameId": "t",
            "openingFamily": "f",
            "split": "T",
            "moves": [0] * 8,
            "state": native.position(),
        }
        evidence = {"replay": []}
        observations = generation._play_game(
            native,
            opening,
            evidence,
            lambda: False,
            label_kind="teacherEstimate",
            sample_placements=[8, 12, 20, 24, 36, 40, 48, 52],
        )
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["placement"], 8)
        self.assertEqual(observations[0]["row"]["state"]["toMove"], 2)
        self.assertEqual(observations[0]["legalMoves"], [0])
        self.assertIsNone(evidence["replay"][8]["move"])
        self.assertEqual(evidence["actualBlackMinusWhite"], 5)
        self.assertNotIn("targetCentidiscs", observations[0]["row"])

    def test_holdout_untraversed_duplicates_excluded_and_deficits_not_refilled(self):
        slots = [
            {"gameId": f"{s}{i:03}", "openingFamily": f"{s}{i:03}", "split": s, "state": {}}
            for s, n in (("T", 96), ("V", 16), ("H", 16))
            for i in range(n)
        ]
        calls = []

        def play(_, opening, evidence, *args, **kwargs):
            calls.append(opening["gameId"])
            evidence["complete"] = True
            # Two cross-split observations must both be removed before labels.
            key = "shared" if opening["gameId"] in ("T000", "V000") else opening["gameId"]
            return [
                {
                    "placement": 8,
                    "split": opening["split"],
                    "row": {
                        "gameId": opening["gameId"],
                        "openingFamily": opening["openingFamily"],
                        "state": {"opaqueKey": key},
                    },
                }
            ]

        report, evidence, observations = {}, [], []
        with patch.object(generation, "_play_game", play):
            generation._trajectory_samples(
                None,
                {"samplePlacements": [8, 12, 20, 24, 36, 40, 48, 52]},
                slots,
                evidence,
                observations,
                lambda state: state["opaqueKey"],
                report,
                lambda: False,
            )
        self.assertEqual(len(calls), 112)
        self.assertFalse(any(game.startswith("H") for game in calls))
        self.assertEqual(len(report["heldoutFamilies"]), 16)
        self.assertEqual(report["observationDeficit"], 786)
        self.assertEqual(report["duplicates"]["crossSplitExcluded"], 2)
        self.assertEqual(report["duplicates"]["zeroSampleFamilies"], ["T000", "V000"])
        self.assertEqual(len(observations), 110)

    def test_failure_keeps_previous_observations_and_unrun_counts(self):
        slots = [
            {"gameId": s, "openingFamily": s, "split": "T", "state": {}} for s in ("a", "b", "c")
        ]

        def play(_, opening, evidence, *args, **kwargs):
            if opening["gameId"] == "b":
                raise generation.GenerationStop("fake first failure")
            return [{"row": {"openingFamily": "a"}}]

        report, evidence, observations = {}, [], []
        with (
            patch.object(generation, "_play_game", play),
            self.assertRaises(generation.GenerationStop),
        ):
            generation._trajectory_samples(
                None,
                {"samplePlacements": [8]},
                slots,
                evidence,
                observations,
                lambda _: b"unused",
                report,
                lambda: False,
            )
        self.assertEqual(len(observations), 1)
        self.assertEqual(report["trajectoriesComplete"], 1)
        self.assertEqual(report["trajectoriesUnrun"], 1)
        self.assertEqual(report["rawDeficitByFamily"], {"a": 7, "b": 8, "c": 8})
        self.assertEqual(evidence[1]["failure"]["message"], "fake first failure")


if __name__ == "__main__":
    unittest.main()
