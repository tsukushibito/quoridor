"""New model-free boundary definitions only; author execution UNRUN."""

import copy
import unittest
from unittest.mock import patch

from othello_arena import generation, matches
from othello_arena.engines import FullSearchPlayer
from othello_arena.protocol import EngineError


def trajectory_config():
    return {
        "stage": "continuous-development",
        "trajectoryProfile": "development-contest-openings",
        "purpose": "development_trajectory_roots",
        "comparisonScope": "development-contest",
        "namespace": "development/native64-prospective",
        "labelKind": None,
        "H": 0,
        "samplePassPolicy": "after-mandatory-pass",
        "commonPrefixPlacements": [0, 7],
        "samplePlacements": [16],
        "duplicatePolicy": generation.CONTINUOUS_DUPLICATE_POLICY,
        "launchBinding": {"fixture": True},
        "families": [
            {
                "id": f"development/native64-prospective/f{i:02}",
                "split": "development",
                "seed": 2026102302001 + i,
            }
            for i in range(16)
        ],
        "limits": {
            "actionsPerTrajectory": 128,
            "inputBytes": 1024,
            "evidenceBytes": 65536,
            "retainedBytes": 1048576,
        },
        "source": {"fixture": True},
        "exposureMetadata": [{"scope": "fixture-endpoint", "file": {"bytes": 0}, "count": 0}],
        "requiredExposureScopes": ["fixture-endpoint"],
        "historicalEndpointScope": {
            "domain": "sha256-canonical-board-bytes",
            "coverage": "declared-endpoints-only",
            "passInclusiveHistoryCoverage": "UNKNOWN",
        },
        "freshHistoryScope": {
            "domain": "raw-canonical-board-bytes",
            "coverage": "placement8+-pass-inclusive",
            "collisionPolicy": "stop-on-any-repeat",
        },
    }


class CannedAuthority:
    """Opaque protocol states, not Python rules. One mandatory pass at placement16."""

    def __init__(self):
        self.new_calls = 0

    def request(self, op, *, deadline, **fields):
        if op == "new":
            self.new_calls += 1
            return {"state": {"opaque": 0}}
        n = fields["state"]["opaque"]
        if op == "status":
            return {
                "status": {
                    "terminal": False,
                    "mustPass": n == 16,
                    "legalMoves": [] if n == 16 else [50],
                    "black": 10,
                    "white": 10,
                }
            }
        if op in ("play", "pass"):
            return {"state": {"opaque": n + 1}}
        raise AssertionError(op)


def identity():
    return {
        "engine": "console7.8.1-rust-singlethread-source-port",
        "upstreamCommit": "570d5e0a478c9d720d75de06a5d31995f412704a",
        "interpretation": "simd",
        "midgameId": "sha256:" + "0" * 64,
        "orderingId": "sha256:" + "1" * 64,
        "identityBinding": "callerVerified",
        "hashLevel": 20,
        "hashSeed": 20261022,
        "coefficients": {},
        "workerPool": 0,
    }


def response():
    return {
        "ok": True,
        "result": {
            "move": 20,
            "rawScore": -3,
            "score": -2,
            "scoreUnits": "engine-disc",
            "scoreKind": "heuristic",
            "proven": False,
            "completedDepth": 8,
            "selectivity": 0,
            "probability": 74,
            "isEndSearch": False,
            "nodes": 123,
            "elapsedMs": 1000,
            "stopped": "timeout",
            "interpretation": "simd",
            "ttBytes": 25165872,
            "coefficients": {},
            "mustPass": False,
            "terminal": False,
        },
    }


class Native64BoundaryTests(unittest.TestCase):
    def test_semantic16_profile_is_explicit_and_historical_history_stays_unknown(self):
        config = trajectory_config()
        with patch.object(generation, "_matches_ref", return_value=True):
            generation._validate_continuous(config)
            for key, value in (
                ("trajectoryProfile", "continuous-series"),
                ("samplePlacements", [8]),
                ("families", config["families"][:-1]),
            ):
                wrong = dict(config, **{key: value})
                with self.assertRaises(generation.GenerationStop):
                    generation._validate_continuous(wrong)
            wrong = copy.deepcopy(config)
            wrong["historicalEndpointScope"]["passInclusiveHistoryCoverage"] = "complete"
            with self.assertRaises(generation.GenerationStop):
                generation._validate_continuous(wrong)

    def test_target_is_after_mandatory_pass_and_pass_does_not_advance_placement(self):
        config = trajectory_config()
        config["families"] = config["families"][:1]
        config["engine"] = {"binary": {"fixture": "rules-only identity"}}
        native, package, evidence, report = CannedAuthority(), {}, [], {}
        generation._continuous(
            native,
            config,
            lambda state: bytes([state["opaque"]]),
            set(),
            package,
            evidence,
            report,
            lambda: False,
        )
        root = package["families"][0]["roots"][0]
        self.assertEqual(root["placement"], 16)
        self.assertEqual(root["state"], {"opaque": 17})
        self.assertEqual(root["moves"], [50] * 16 + [None])
        self.assertEqual(package["families"][0]["generationActions"], 17)

    def test_collision_stops_first_attempt_without_replacement_or_later_family(self):
        native, package, evidence, report = CannedAuthority(), {}, [], {}
        config = trajectory_config()
        with self.assertRaises(generation.GenerationStop):
            generation._continuous(
                native,
                config,
                lambda state: b"same-opaque-key",
                set(),
                package,
                evidence,
                report,
                lambda: False,
            )
        self.assertEqual(native.new_calls, 1)
        self.assertEqual(report["collision"]["priorFamily"], config["families"][0]["id"])
        self.assertEqual(len(generation._continuous_deficits(config, package)), 16)
        self.assertTrue(all(f["status"] == "UNRUN" for f in package["families"][1:]))

    def test_ordinary_nested_result_retained_identity_once_clear_and_search(self):
        calls = []

        class Process:
            def json_request(self, request, *, deadline):
                calls.append(request)
                if request["op"] == "info":
                    return {"ok": True, **identity()}
                if request["op"] == "clear":
                    return {"ok": True}
                return response()

        options = {
            "timeMs": 1000,
            "maxDepth": 60,
            "fixedDepth": None,
            "selectivity": None,
            "mpc": True,
            "etc": True,
            "stability": True,
            "parity": True,
            "shallowOrdering": True,
        }
        player = FullSearchPlayer(Process(), identity=identity(), options=options)
        player.initialize(deadline=100)
        player.reset(deadline=100)
        self.assertEqual(player.choose({"opaque": True}, deadline=100), 20)
        self.assertEqual(player.last_search, response())
        self.assertEqual([c["op"] for c in calls], ["info", "clear", "search"])
        player.options = dict(options, maxDepth=64)
        with self.assertRaises(EngineError):
            player.initialize(deadline=100)

    def test_external_evidence_qualification_is_not_legacy_native_evidence(self):
        family = {"id": "development/f", "moves": []}
        result = {
            "family": family["id"],
            "candidateSide": 1,
            "opponent": "edax",
            "completed": True,
            "failure": None,
            "blackMinusWhite": 0,
            "candidateScore": 0.5,
            "status": {"terminal": True, "black": 32, "white": 32},
            "moves": [
                {"side": 1, "move": 20, "opening": False, "wallMs": 1001, "search": response()},
                {
                    "side": 2,
                    "move": 19,
                    "opening": False,
                    "wallMs": 1001,
                    "search": {
                        "protocol": "gtp",
                        "engine": "edax",
                        "side": 2,
                        "move": 19,
                        "response": "D3",
                    },
                },
            ],
        }
        expected = {
            "candidate": {"protocol": "fullsearch_jsonl", "identity": identity()},
            "opponent": {"protocol": "gtp", "engine": "edax"},
        }
        self.assertTrue(
            matches._normal_comparison_game(
                result, family, expected, evidence_kind="fullsearch-external"
            )
        )
        self.assertFalse(matches._normal_comparison_game(result, family, expected))
        wrong = copy.deepcopy(result)
        wrong["moves"][1]["search"]["engine"] = "egaroucid"
        self.assertFalse(
            matches._normal_comparison_game(
                wrong, family, expected, evidence_kind="fullsearch-external"
            )
        )

    def test_incomplete_external_schedule_never_bootstraps_completed_subset(self):
        families = [{"id": f"development/f{i}", "moves": []} for i in range(16)]
        with patch.object(matches.random, "Random", side_effect=AssertionError("no subset CI")):
            summary = matches.comparison_summary(
                [],
                families,
                {
                    "candidate": {"protocol": "fullsearch_jsonl", "identity": identity()},
                    "opponent": {"protocol": "gtp", "engine": "edax"},
                },
                run_qualified=False,
                opponent_id="edax",
                evidence_kind="fullsearch-external",
            )
        self.assertEqual(summary["scoreRateBoundsIncludingUnknown"], [0, 1])
        self.assertFalse(summary["ciEligible"])
        self.assertIsNone(summary["familyBootstrap95"])


if __name__ == "__main__":
    unittest.main()
