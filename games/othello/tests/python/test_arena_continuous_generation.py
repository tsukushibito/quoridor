"""New model-free continuous-stage fixtures; execution belongs to Root."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from othello_arena import generation


def config():
    return {
        "stage": "continuous-development",
        "purpose": "development_trajectory_roots",
        "labelKind": None,
        "H": 0,
        "namespace": "development/continuous-fixture",
        "families": [
            {"id": f"development/continuous-fixture/f{i}", "seed": 100 + i, "split": "development"}
            for i in range(4)
        ],
        "samplePlacements": [16, 32, 48, 56],
        "samplePassPolicy": "after-mandatory-pass",
        "commonPrefixPlacements": [0, 7],
        "duplicatePolicy": generation.CONTINUOUS_DUPLICATE_POLICY,
        "launchBinding": {"fixture": True},
        "source": {"fixture": True},
        "canonicalSource": {"fixture": True},
        "engine": {"binary": {"fixture": True}},
        "exposureCoverage": "complete",
        "requiredExposureScopes": ["prior-development"],
        "exposureMetadata": [{"scope": "prior-development", "file": {"bytes": 1}, "count": 1}],
        "limits": {
            "actionsPerTrajectory": 128,
            "inputBytes": 4096,
            "evidenceBytes": 1024 * 1024,
            "retainedBytes": 2 * 1024 * 1024,
        },
    }


class CannedNative:
    """Opaque canned states/statuses, no Othello geometry or move computation."""

    def __init__(self, terminal_at=None):
        self.family = -1
        self.terminal_at = terminal_at
        self.requests = []

    def position(self):
        return {"family": self.family, "placement": self.placement, "passed": self.passed}

    def request(self, op, **_):
        self.requests.append(op)
        if op == "new":
            self.family += 1
            self.placement, self.passed = 0, False
        elif op == "status":
            must_pass = self.placement == 16 and not self.passed
            return {
                "status": {
                    "terminal": self.terminal_at is not None and self.placement >= self.terminal_at,
                    "mustPass": must_pass,
                    "legalMoves": [] if must_pass else [9, 3],
                    "black": 4 + self.placement,
                    "white": 0,
                }
            }
        elif op == "play":
            self.placement += 1
            self.passed = False
        elif op == "pass":
            self.passed = True
        else:
            raise AssertionError("no simple/search/evaluate or extra owner op")
        return {"state": self.position()}


class FirstChoice:
    def choice(self, values):
        if values != [3, 9]:
            raise AssertionError("actual legal choices must be sorted")
        return values[0]


def identity(position):
    return f"{position['family']}/{position['placement']}".encode()


class ContinuousGenerationTests(unittest.TestCase):
    def test_semantic_stage_and_unknown_exposure_rejection_before_native(self):
        value = config()
        with patch.object(generation, "_matches_ref", return_value=True):
            generation._validate(value)
            unknown = deepcopy(value)
            unknown["exposureCoverage"] = "UNKNOWN"
            with self.assertRaisesRegex(generation.GenerationStop, "UNKNOWN"):
                generation._validate(unknown)
            invalid_id = deepcopy(value)
            invalid_id["families"][0]["id"] += "/space invalid"
            with self.assertRaises(generation.GenerationStop):
                generation._validate(invalid_id)
            labels = deepcopy(value)
            labels["labelKind"] = "gameOutcome"
            with self.assertRaises(generation.GenerationStop):
                generation._validate(labels)

    def test_targets_count_placements_and_freeze_after_mandatory_pass(self):
        value, native = config(), CannedNative()
        package, evidence, report = {}, [], {}
        with patch.object(generation.random, "Random", side_effect=lambda _: FirstChoice()) as rng:
            generation._continuous(
                native, value, identity, set(), package, evidence, report, lambda: False
            )
        self.assertEqual([call.args[0] for call in rng.call_args_list], [100, 101, 102, 103])
        self.assertEqual(native.requests.count("new"), 4)
        self.assertEqual(native.requests.count("play"), 224)
        self.assertEqual(native.requests.count("pass"), 4)
        self.assertEqual(generation._continuous_deficits(value, package), [])
        for family, history in zip(package["families"], evidence, strict=True):
            self.assertEqual([r["placement"] for r in family["roots"]], [16, 32, 48, 56])
            self.assertTrue(family["roots"][0]["state"]["passed"])
            self.assertEqual(family["generationActions"], 57)
            self.assertEqual(len(history["replay"]), 57)
            self.assertIsNone(history["replay"][16]["move"])
            self.assertEqual(history["replay"][16]["placement"], 16)
            self.assertEqual(history["canonicalHistory"][0]["placement"], 8)
            self.assertEqual(
                [e["action"] for e in history["canonicalHistory"] if e["placement"] == 16],
                [16, 17],
            )
            self.assertEqual(family["roots"][-1]["fixedDepth"], 4)
            self.assertTrue(history["complete"])
            self.assertNotIn("labelKind", family["roots"][0])

    def test_early_terminal_and_action_cap_retain_exact_deficits_no_replacement(self):
        for terminal, cap in ((20, 128), (None, 17)):
            with self.subTest(terminal=terminal, cap=cap):
                value, native = config(), CannedNative(terminal_at=terminal)
                value["limits"]["actionsPerTrajectory"] = cap
                package, evidence, report = {}, [], {}
                with patch.object(generation.random, "Random", return_value=FirstChoice()):
                    with self.assertRaises(generation.GenerationStop):
                        generation._continuous(
                            native, value, identity, set(), package, evidence, report, lambda: False
                        )
                self.assertEqual(len(generation._continuous_deficits(value, package)), 15)
                self.assertEqual(native.requests.count("new"), 1)
                self.assertFalse(evidence[0]["complete"])
                self.assertEqual([f["status"] for f in package["families"]][1:], ["UNRUN"] * 3)

    def test_exposure_and_whole_family_collision_stop_without_refill(self):
        for exposed in (True, False):
            value, native = config(), CannedNative()
            package, evidence, report = {}, [], {}

            def key(position):
                return b"shared" if position["placement"] == 8 else identity(position)

            with patch.object(generation.random, "Random", return_value=FirstChoice()):
                with self.assertRaisesRegex(generation.GenerationStop, "collision"):
                    generation._continuous(
                        native,
                        value,
                        key,
                        {b"shared"} if exposed else set(),
                        package,
                        evidence,
                        report,
                        lambda: False,
                    )
            self.assertEqual(native.requests.count("new"), 1 if exposed else 2)
            self.assertEqual(
                len(generation._continuous_deficits(value, package)), 16 if exposed else 12
            )
            self.assertEqual(report["collision"]["placement"], 8)
            self.assertEqual(report["collision"]["priorExposure"], exposed)

    def test_checked_identity_metadata_refusal_and_complete_domain(self):
        value = config()
        package = {
            "coverageStatus": "UNKNOWN",
            "scope": "prior-development",
            "domain": "canonical-states-placement8+-pass-inclusive",
            "canonicalSource": value["canonicalSource"],
            "canonicalKeys": ["00" * 64],
        }
        with patch.object(generation, "_read", side_effect=generation.GenerationStop("FileRef")):
            with self.assertRaisesRegex(generation.GenerationStop, "FileRef"):
                generation._continuous_exclusions(value)
        with patch.object(generation, "_read", return_value=package):
            with self.assertRaisesRegex(generation.GenerationStop, "UNKNOWN"):
                generation._continuous_exclusions(value)
            package["coverageStatus"] = "complete"
            self.assertEqual(generation._continuous_exclusions(value), {bytes(64)})

    def test_cancel_stops_before_first_rules_call_without_rng_or_native_replacement(self):
        value, native = config(), CannedNative()
        package, evidence, report = {}, [], {}
        with patch.object(generation.random, "Random", return_value=FirstChoice()) as rng:
            with self.assertRaisesRegex(generation.GenerationStop, "cancelled"):
                generation._continuous(
                    native, value, identity, set(), package, evidence, report, lambda: True
                )
        rng.assert_not_called()
        self.assertEqual(native.requests, [])
        self.assertEqual(len(generation._continuous_deficits(value, package)), 16)

    def test_new_stage_run_writes_only_unlabeled_roots_and_chronological_evidence(self):
        from pathlib import Path
        import json
        import tempfile

        value, native = config(), CannedNative()
        value.update(seed=None, openingExclusions=[])
        value["limits"]["inputBytes"] = 1024 * 1024

        class CannedProcess:
            def __init__(self, *_args, **_kwargs):
                self.cleanup = {"unexpectedExit": False, "directReaped": True, "errors": []}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        value["engine"].update(argv=["fixture-only"], cwd="/fixture")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-output"
            with (
                patch.object(generation, "_read", return_value=value),
                patch.object(generation, "_ref", return_value={"fixture": True}),
                patch.object(generation, "_matches_ref", return_value=True),
                patch.object(generation, "_canonical", return_value=identity),
                patch.object(generation, "_continuous_exclusions", return_value=set()),
                patch.object(generation, "checked_spec"),
                patch.object(generation, "Process", CannedProcess),
                patch.object(generation, "Native", return_value=native),
                patch.object(generation.random, "Random", return_value=FirstChoice()),
            ):
                report = generation.run({"fixture": True}, output)
            roots = json.loads((output / "roots.json").read_bytes())
            evidence = json.loads((output / "generation-evidence.json").read_bytes())
            self.assertEqual(report["status"], "complete")
            self.assertEqual(report["rootsComplete"], 16)
            self.assertEqual(report["rootDeficits"], [])
            self.assertTrue(report["cleanup"]["directReaped"])
            self.assertTrue(roots["complete"])
            self.assertFalse(roots["outcomeLabels"])
            self.assertEqual(len(roots["families"]), 4)
            self.assertEqual(len(evidence["games"]), 4)
            self.assertEqual(list(output.glob("training*")), [])


if __name__ == "__main__":
    unittest.main()
