"""Canned protocols/analytic scores only; no native/model payload/scientific RNG."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from othello_arena import __main__ as arena, generation, matches
from othello_arena.engines import NativePlayer
from othello_arena.protocol import EngineError, Native


def config():
    image = "/immutable/othello-engine"
    binary = {
        "sha256": "2678ba8e2ff207a4f1d1f2f1047a345964fafad4375e9abcf5d9d6b34debc71d",
        "bytes": 800888,
        "mode": "0755",
    }
    model = {
        "path": "/workspaces/quoridor/.worktree/assets/models/othello-strong-teacher-n96-v1/pattern-v1.json",
        "bytes": 16161,
        "mode": "0644",
        "sha256": "7ed9fa38218f591d80cfa10f985d510635eaddcd9e2f530e3f778b16b052bd9a",
    }
    spec = {"argv": [image], "binary": binary, "cwd": "/immutable", "protocol": "native_jsonl"}
    return {
        "purpose": "native_evaluator_comparison",
        "timeMs": 1000,
        "overheadMs": 100,
        "threads": 1,
        "ttMiB": 32,
        "maxDepth": 64,
        "exactEmpties": 12,
        "book": False,
        "ponder": False,
        "superiorityClaim": False,
        "launchBinding": {"fixture": True},
        "model": model,
        "rules": copy.deepcopy(spec),
        "opponents": [dict(copy.deepcopy(spec), id="heuristic")],
        "candidate": dict(
            copy.deepcopy(spec),
            assets=[model],
            argv=[image, "--pattern", model["path"], "--model-id", "sha256:" + model["sha256"]],
        ),
    }


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
    evaluations = arena.comparison_bindings(config())
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
    def test_image_hash_preflight_failure_retains32_unrun_and_guard_wall(self):
        families, _, _ = fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(arena, "comparison_families", return_value=families),
                patch.object(
                    arena, "checked_spec", side_effect=ValueError("fake image hash mismatch")
                ),
                patch.object(arena, "Process", side_effect=AssertionError("must not launch")),
                patch.object(
                    matches.random, "Random", side_effect=AssertionError("must not bootstrap")
                ),
            ):
                code = arena.run(config(), Path(tmp) / "out")
            report = json.loads((Path(tmp) / "out/result.json").read_bytes())
        self.assertEqual(code, 1)
        self.assertEqual(report["failure"]["message"], "fake image hash mismatch")
        self.assertEqual(report["comparison"]["unrun"], 32)
        self.assertEqual(report["comparison"]["scoreRateBoundsIncludingUnknown"], [0, 1])
        self.assertGreaterEqual(report["setupShutdown"][0]["launchValidationMs"], 0)
        self.assertIsNone(report["setupShutdown"][0]["launchWallMs"])

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

    def test_existing_run_native_factory_init_once_shutdown_and_cleanup_failure(self):
        families, evaluations, results = fixtures()
        for bad_cleanup, foreign_init, unknown_score in (
            (False, False, False),
            (True, False, False),
            (False, True, False),
            (False, False, True),
        ):
            instances = []
            delivered = []

            class Process:
                cleanup = None

                def __init__(self, argv, **kw):
                    self.argv = argv
                    self.ops = []
                    instances.append(self)
                    self.evaluation = evaluations[
                        "candidate" if "--pattern" in argv else "opponent"
                    ]
                    if foreign_init and "--pattern" in argv:
                        self.evaluation = {"kind": "foreign"}

                def json_request(self, payload, **kw):
                    self.ops.append(payload["op"])
                    if payload["op"] == "new":
                        return {"ok": True, "state": {"version": 1, "board": [0] * 64, "toMove": 1}}
                    if payload["op"] == "evaluate":
                        return {"ok": True, "score": 0, "evaluation": self.evaluation}
                    raise AssertionError("actual search prohibited")

                def close(self):
                    self.cleanup = {
                        "directReaped": True,
                        "unexpectedExit": False,
                        "errors": ["fixture cleanup error"] if bad_cleanup else [],
                    }

            def paired(rules, candidate, opponent, *args, **kw):
                self.assertFalse(foreign_init, "identity failure must stop before games")
                self.assertIsInstance(candidate, NativePlayer)
                self.assertIsInstance(opponent, NativePlayer)
                self.assertEqual(kw, {"time_ms": 1000, "overhead_ms": 100})
                feed = copy.deepcopy(results)
                if unknown_score:
                    feed[0]["candidateScore"] = None
                for item in feed:
                    delivered.append(item)
                    yield item

            with tempfile.TemporaryDirectory() as tmp:
                with (
                    patch.object(arena, "Process", Process),
                    patch.object(arena, "checked_spec"),
                    patch.object(arena, "comparison_families", return_value=families),
                    patch.object(arena, "paired", paired),
                    patch.object(matches.random, "Random", ConstantDraws),
                ):
                    code = arena.run(config(), Path(tmp) / "out")
                report = json.loads((Path(tmp) / "out/result.json").read_bytes())
                if foreign_init:
                    self.assertFalse((Path(tmp) / "out/games.jsonl").exists())
                else:
                    self.assertEqual(
                        len((Path(tmp) / "out/games.jsonl").read_text().splitlines()),
                        1 if unknown_score else 32,
                    )
            self.assertEqual(code, 1 if bad_cleanup or foreign_init or unknown_score else 0)
            self.assertEqual(len(delivered), 0 if foreign_init else 1 if unknown_score else 32)
            self.assertEqual(len(instances), 2 if foreign_init else 3)
            self.assertEqual(
                [p.ops for p in instances],
                [["new"], ["new", "evaluate"]]
                if foreign_init
                else [["new"], ["new", "evaluate"], ["new", "evaluate"]],
            )
            for lifecycle in report["setupShutdown"]:
                for field in (
                    "launchValidationMs",
                    "launchWallMs",
                    "readyWallMs",
                    "shutdownWallMs",
                ):
                    self.assertGreaterEqual(lifecycle[field], 0)
            self.assertEqual(
                report["comparison"]["ciEligible"],
                not (bad_cleanup or foreign_init or unknown_score),
            )
            if bad_cleanup or foreign_init or unknown_score:
                self.assertNotIn("familyBootstrap95", report["comparison"])
                self.assertIsNotNone(report["failure"])

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
        expected = arena.comparison_bindings(config())["candidate"]

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

    def test_frozen16_canonical_exclusion_and_purpose_binding_use_current_generator(self):
        prepared = preparation_config()
        bound = config()
        prepared["engine"] = bound["rules"]
        prepared["canonicalSource"] = {"fixture": True}
        frozen = {
            key: copy.deepcopy(prepared[key])
            for key in (
                "purpose",
                "seed",
                "source",
                "engine",
                "canonicalSource",
                "openingExclusions",
                "labelKind",
                "samplePlacements",
                "duplicatePolicy",
                "namespace",
            )
        }
        frozen.update(complete=True, stage="openings", outcomeLabels=False, records=[])
        for index, slot in enumerate(prepared["slots"]):
            key = str(index).encode()
            frozen["records"].append(
                dict(
                    slot,
                    moves=[0] * 8,
                    state={"key": str(index)},
                    canonicalSha256=hashlib.sha256(key).hexdigest(),
                )
            )
        bound.update(openingConfig={"fixture": "config"}, openings={"fixture": "openings"})

        def read(reference, maximum):
            return prepared if reference == bound["openingConfig"] else frozen

        with (
            patch.object(generation, "_read", side_effect=read),
            patch.object(
                generation, "_canonical", return_value=lambda state: state["key"].encode()
            ),
            patch.object(generation, "_excluded_keys", return_value=set()),
        ):
            self.assertEqual(len(arena.comparison_families(bound)), 16)
            frozen["purpose"] = "foreign"
            with self.assertRaises(generation.GenerationStop):
                arena.comparison_families(bound)
            frozen["purpose"] = prepared["purpose"]
            frozen["records"][-1]["state"] = {"key": "0"}
            with self.assertRaises(generation.GenerationStop):
                arena.comparison_families(bound)

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

    def test_metadata_same_image_model_argv_binding_without_payload_read(self):
        bound = config()
        with patch.object(Path, "open", side_effect=AssertionError("payload read")):
            evaluations = arena.comparison_bindings(bound)
        self.assertEqual(evaluations["candidate"]["modelBytes"], 16161)
        self.assertEqual(evaluations["opponent"], {"kind": "v1Heuristic"})
        changes = []
        for which in ("rules", "candidate"):
            bad = config()
            bad[which]["binary"]["sha256"] = "550b" + "0" * 60
            changes.append(bad)
        bad = config()
        bad["candidate"]["argv"][-1] = "sha256:" + "0" * 64
        changes.append(bad)
        bad = config()
        bad["opponents"][0]["argv"].append("--pattern")
        changes.append(bad)
        bad = config()
        bad["candidate"]["assets"] = []
        changes.append(bad)
        bad = config()
        bad["nodeCap"] = 100
        changes.append(bad)
        bad = config()
        bad["overheadMs"] = 200
        changes.append(bad)
        for bad in changes:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                arena.comparison_bindings(bad)

    def test_native_identity_and_exact_search_options_no_node_cap(self):
        expected = arena.comparison_bindings(config())["candidate"]
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
