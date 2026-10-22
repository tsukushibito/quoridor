"""Canned protocols/analytic scores only; no native/model payload/scientific RNG."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from othello_arena import __main__ as arena, generation, matches
from othello_arena.engines import NativePlayer
from othello_arena.protocol import EngineError, Native


def search(evaluation):
    return {
        "ok": True,
        "move": 20,
        "score": 25,
        "scoreKind": "heuristic",
        "completedDepth": 8,
        "nodes": 123,
        "elapsedMs": 999.5,
        "timedOut": True,
        "cancelled": False,
        "proven": False,
        "evaluation": evaluation,
    }


def fixtures():
    """Opaque canned authority results; these are not generated legal games."""
    families = [{"id": f"development/comparison/{i:02}", "moves": [0] * 8} for i in range(16)]
    evaluations = {"candidate": {"kind": "fixtureCandidate"}, "opponent": {"kind": "v1Heuristic"}}
    results = []
    for family in families:
        for side in (1, 2):
            results.append(
                {
                    "family": family["id"],
                    "opponent": "heuristic",
                    "candidateSide": side,
                    "completed": True,
                    "failure": None,
                    "blackMinusWhite": 0,
                    "candidateScore": 0.5,
                    "status": {"terminal": True, "black": 32, "white": 32},
                    "moves": [{"side": 1, "move": 0, "opening": True} for _ in range(8)]
                    + [
                        {
                            "side": side,
                            "move": 20,
                            "opening": False,
                            "wallMs": 1001,
                            "search": search(evaluations["candidate"]),
                        }
                    ],
                }
            )
    return families, evaluations, results


def score(result, value):
    diff = (
        2 * (1 if result["candidateSide"] == 1 else -1)
        if value == 1
        else -2 * (1 if result["candidateSide"] == 1 else -1)
        if value == 0
        else 0
    )
    result.update(
        candidateScore=value,
        blackMinusWhite=diff,
        status={"terminal": True, "black": 32 + diff // 2, "white": 32 - diff // 2},
    )


def preparation_config():
    return {
        "purpose": "native_evaluator_comparison",
        "stage": "openings",
        "labelKind": None,
        "seed": 2026102202,
        "launchBinding": {"fixture": True},
        "namespace": "development/comparison",
        "slots": [
            {
                "gameId": f"development/comparison/g{i}",
                "openingFamily": f"development/comparison/f{i}",
                "split": "D",
            }
            for i in range(16)
        ],
        "samplePlacements": [],
        "duplicatePolicy": generation.DUPLICATE_POLICY,
        "source": generation._ref(generation.__file__),
        "limits": {
            "openingAttempts": 256,
            "inputBytes": 65536,
            "evidenceBytes": 65536,
            "retainedBytes": 1048576,
        },
        "openingExclusions": [
            {"count": n, "file": {"fixture": n}, "recordsKey": "records"} for n in (4, 24, 128)
        ],
    }


class ConstantDraws:
    def __init__(self, seed):
        assert seed == 2026102203

    def randrange(self, n):
        assert n == 16
        return 0


class NativeComparisonTests(unittest.TestCase):
    def test_retired_tiny_comparison_refused_before_process_start(self):
        spec = {"argv": ["/unused"], "cwd": "/unused"}
        bound = {
            "purpose": "native_evaluator_comparison",
            "superiorityClaim": False,
            "launchBinding": {"fixture": True},
            "families": [
                {"id": str(i), "moves": [], "split": "protocol-smoke-only"} for i in range(4)
            ],
            "rules": spec,
            "candidate": spec,
            "opponents": [dict(spec, id="external", protocol="fixed_jsonl")],
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(arena, "Process", side_effect=AssertionError("must not start")):
                code = arena.run(bound, Path(tmp) / "out")
            report = json.loads((Path(tmp) / "out/result.json").read_text())
        self.assertEqual(code, 1)
        self.assertEqual(report["failure"]["kind"], "ValueError")
        self.assertEqual(report["cleanup"], [])
        self.assertEqual(report["byOpponent"]["external"]["unrun"], 8)

    def test_existing_external_factory_branches_remain_protocol_cost_only(self):
        for protocol in ("fixed_jsonl", "gtp"):
            fixed, gtp = object(), object()

            class Process:
                cleanup = None

                def __init__(self, *args, **kw):
                    pass

                def close(self):
                    self.cleanup = {"directReaped": True, "unexpectedExit": False, "errors": []}

            spec = {"argv": ["/unused"], "cwd": "/unused"}
            bound = {
                "purpose": "protocol_cost",
                "superiorityClaim": False,
                "launchBinding": {"fixture": True},
                "timeMs": 1000,
                "overheadMs": 100,
                "threads": 1,
                "ttMiB": 32,
                "book": False,
                "ponder": False,
                "families": [
                    {"id": str(i), "moves": [], "split": "protocol-smoke-only"} for i in range(4)
                ],
                "rules": spec,
                "candidate": spec,
                "opponents": [dict(spec, id="external", protocol=protocol, engine="edax")],
            }

            def paired(rules, candidate, opponent, *args, **kw):
                self.assertIs(opponent, fixed if protocol == "fixed_jsonl" else gtp)
                yield {
                    "family": "0",
                    "candidateSide": 1,
                    "completed": False,
                    "candidateScore": None,
                    "failure": {"kind": "fixture-stop"},
                }

            with tempfile.TemporaryDirectory() as tmp:
                with (
                    patch.object(arena, "Process", Process),
                    patch.object(arena, "checked_spec"),
                    patch.object(arena, "EgaroucidFixedTime", return_value=fixed),
                    patch.object(arena, "GTP", return_value=gtp),
                    patch.object(arena, "paired", paired),
                ):
                    code = arena.run(bound, Path(tmp) / "out")
                report = json.loads((Path(tmp) / "out/result.json").read_bytes())
            self.assertEqual(code, 1)
            self.assertEqual(report["byOpponent"]["external"]["planned"], 8)
            self.assertEqual(report["byOpponent"]["external"]["unrun"], 7)
            self.assertNotIn("comparison", report)

    def test_r7_percentiles_use16_family_means_and_exact10000_resamples(self):
        families, evaluations, results = fixtures()
        for index, result in enumerate(results):
            score(result, 0 if index < 2 else 1 if index < 4 else 0.5)

        class Draws:
            calls = 0

            def __init__(self, seed):
                self.calls = 0
                assert seed == 2026102203

            def randrange(self, n):
                assert n == 16
                sample = self.calls // 16
                self.calls += 1
                Draws.calls += 1
                return 0 if sample < 250 else 2 if sample < 9750 else 1

        with patch.object(matches.random, "Random", Draws):
            summary = self.summarize(results, families, evaluations)
        self.assertEqual(Draws.calls, 160000)
        self.assertAlmostEqual(summary["familyBootstrap95"][0], 0.4875)
        self.assertAlmostEqual(summary["familyBootstrap95"][1], 0.5125)
        self.assertEqual(summary["familyMeanScore"], 0.5)
        self.assertIsNone(summary["acceptance"])

    def test_unknown_bounds_invalid_plan_and_mandatory_pass_evidence(self):
        families, evaluations, results = fixtures()
        score(results[0], 1)
        results[-1]["candidateScore"] = None
        with patch.object(matches.random, "Random", side_effect=AssertionError("UNKNOWN RNG")):
            summary = self.summarize(results, families, evaluations)
        self.assertEqual(summary["knownPoints"], 16)
        self.assertEqual(summary["scoreRateBoundsIncludingUnknown"], [16 / 32, 17 / 32])
        self.assertEqual(summary["unknownGames"], 1)
        families, evaluations, results = fixtures()
        duplicate_families = copy.deepcopy(families)
        duplicate_families[-1] = duplicate_families[0]
        with patch.object(matches.random, "Random", side_effect=AssertionError("invalid plan RNG")):
            summary = self.summarize(results, duplicate_families, evaluations)
        self.assertEqual(summary["unknownGames"], 32)
        self.assertNotIn("familyBootstrap95", summary)
        results[0]["moves"].append(
            {"side": 2, "move": None, "opening": False, "wallMs": 0, "forcedPass": True}
        )
        with patch.object(matches.random, "Random", ConstantDraws):
            self.assertTrue(self.summarize(results, families, evaluations)["ciEligible"])
        results[0]["moves"][-1]["wallMs"] = 1
        with patch.object(matches.random, "Random", side_effect=AssertionError("bad pass RNG")):
            self.assertFalse(self.summarize(results, families, evaluations)["ciEligible"])

    def test_first_bad_search_retains_raw_clock_and_paired_stops_without_refill(self):
        expected = {"candidate": {"kind": "fixtureCandidate"}, "opponent": {"kind": "v1Heuristic"}}[
            "candidate"
        ]

        class Rules:
            def request(self, op, **kw):
                if op == "new":
                    return {"state": {"version": 1, "board": [0] * 64, "toMove": 1}}
                if op == "status":
                    return {
                        "status": {
                            "terminal": False,
                            "mustPass": False,
                            "legalMoves": [20],
                            "black": 2,
                            "white": 2,
                        }
                    }
                raise AssertionError("failed search must not be applied")

        class Process:
            def json_request(self, *args, **kw):
                return search({"kind": "foreign"})

        player = NativePlayer(Native(Process()), evaluation=expected)
        families = [{"id": str(i), "moves": []} for i in range(16)]
        results = list(matches.paired(Rules(), player, player, families))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["failure"]["kind"], "identity")
        self.assertFalse(results[0]["completed"])
        self.assertEqual(results[0]["moves"][0]["search"]["evaluation"], {"kind": "foreign"})
        self.assertGreaterEqual(results[0]["moves"][0]["wallMs"], 0)

    def test_asset_guard_checks_sha_bytes_mode_on_fake_software_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "binary"
            asset = Path(tmp) / "asset"
            binary.write_bytes(b"fake software")
            binary.chmod(0o755)
            asset.write_bytes(b"fake metadata bytes")
            asset.chmod(0o600)
            ref = generation._ref(asset)
            ref["mode"] = "0644"
            spec = {"argv": [str(binary)], "binary": generation._ref(binary), "assets": [ref]}
            with self.assertRaisesRegex(ValueError, "mode mismatch"):
                arena.checked_spec(spec)
            asset.chmod(0o644)
            arena.checked_spec(spec)
            spec["assets"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "FileRef mismatch"):
                arena.checked_spec(spec)

    def summarize(self, results, families, evaluations, qualified=True):
        return matches.comparison_summary(
            results, families, evaluations, run_qualified=qualified, opponent_id="heuristic"
        )

    def test_unlabeled16_preparation_profile_excludes_all156_prior_roots(self):
        prepared = preparation_config()
        with patch.object(
            generation.random, "Random", side_effect=AssertionError("scientific RNG")
        ):
            generation._validate(prepared)
        for bad in (
            dict(prepared, labelKind="teacherEstimate"),
            dict(prepared, seed=2026102203),
            dict(prepared, stage="games"),
            dict(prepared, openingExclusions=prepared["openingExclusions"][:2]),
        ):
            with self.assertRaises(generation.GenerationStop):
                generation._validate(bad)

        def read(reference, maximum):
            return {
                "records": [
                    {"state": {"key": f"{reference['fixture']}/{i}"}}
                    for i in range(reference["fixture"])
                ]
            }

        with patch.object(generation, "_read", side_effect=read):
            keys = generation._excluded_keys(prepared, lambda s: s["key"].encode())
        self.assertEqual(len(keys), 156)
        self.assertIn(b"128/127", keys)  # includes held root identity; no traversal/label

    def test_native_identity_and_exact_search_options_no_node_cap(self):
        expected = {"candidate": {"kind": "fixtureCandidate"}, "opponent": {"kind": "v1Heuristic"}}[
            "candidate"
        ]
        calls = []

        class Process:
            evaluation = expected

            def json_request(self, payload, **kw):
                calls.append(payload)
                if payload["op"] == "new":
                    return {"ok": True, "state": {"version": 1, "board": [0] * 64, "toMove": 1}}
                if payload["op"] == "evaluate":
                    return {"ok": True, "score": 0, "evaluation": self.evaluation}
                return search(self.evaluation)

        process = Process()
        player = NativePlayer(Native(process), evaluation=expected)
        player.initialize(deadline=100)
        self.assertEqual(player.choose({"opaque": "state"}, deadline=100), 20)
        self.assertEqual(
            calls[-1],
            {
                "op": "search",
                "state": {"opaque": "state"},
                "timeMs": 1000,
                "ttMiB": 32,
                "maxDepth": 64,
                "exactEmpties": 12,
            },
        )
        process.evaluation = {"kind": "v1Heuristic"}
        with self.assertRaises(EngineError):
            player.choose({}, deadline=100)
        self.assertEqual(player.last_search["evaluation"], {"kind": "v1Heuristic"})

    def test_all_original_pairs_only_analytic_bootstrap_classification(self):
        families, evaluations, results = fixtures()
        for value, expected in ((1, True), (0, False), (0.5, None)):
            for result in results:
                score(result, value)
            with patch.object(matches.random, "Random", ConstantDraws):
                summary = self.summarize(results, families, evaluations)
            self.assertEqual(summary["familyBootstrap95"], [value, value])
            self.assertEqual(summary["familyMeanScore"], value)
            self.assertIs(summary["acceptance"], expected)
            self.assertEqual(len(summary["familyMeans"]), 16)

    def test_missing_failed_duplicate_foreign_side_and_cleanup_never_resample_subset(self):
        families, evaluations, original = fixtures()
        variants = [original[:-1]]
        for key, value in (
            ("family", "foreign"),
            ("candidateSide", 3),
            ("candidateSide", True),
            ("opponent", "foreign"),
            ("candidateScore", None),
            ("failure", {"kind": "timeout"}),
        ):
            bad = copy.deepcopy(original)
            bad[-1][key] = value
            variants.append(bad)
        bad = copy.deepcopy(original)
        bad[-1] = copy.deepcopy(bad[0])
        variants.append(bad)
        bad = copy.deepcopy(original)
        bad[-1]["moves"][-1]["wallMs"] = 1100.1
        variants.append(bad)
        bad = copy.deepcopy(original)
        bad[-1]["moves"][-1]["search"]["evaluation"] = {}
        variants.append(bad)
        with patch.object(matches.random, "Random", side_effect=AssertionError("incomplete RNG")):
            for bad in variants:
                summary = self.summarize(bad, families, evaluations)
                self.assertFalse(summary["ciEligible"])
                self.assertNotIn("familyBootstrap95", summary)
                self.assertIsNone(summary["acceptance"])
                self.assertEqual(summary["planned"], 32)
                self.assertGreater(summary["unknownGames"], 0)
            summary = self.summarize(original, families, evaluations, qualified=False)
            self.assertNotIn("familyBootstrap95", summary)
            self.assertEqual(summary["knownPoints"], 16)
            self.assertEqual(summary["scoreRateBoundsIncludingUnknown"], [0.5, 0.5])


if __name__ == "__main__":
    unittest.main()
