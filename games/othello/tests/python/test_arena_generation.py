"""Focused connector fixtures only; real generation is issued separately by Root."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from othello_arena import generation


class FixtureNative:
    """Canned JSONL authority responses, deliberately no Python Othello rules."""

    def __init__(self):
        self.step = 0
        self.simple_calls = 0

    def position(self):
        return {"version": 1, "board": [0] * 64, "toMove": 1 if self.step % 2 == 0 else 2}

    def request(self, op, **_):
        if op == "new":
            self.step = 0
        elif op in ("play", "pass"):
            self.step += 1
        elif op == "simple":
            self.simple_calls += 1
            return {"move": 0}
        elif op == "status":
            return {
                "status": {
                    "terminal": self.step == 10,
                    "mustPass": self.step == 8,
                    "legalMoves": [] if self.step == 8 else [0],
                    "black": 13,
                    "white": 8,
                }
            }
        return {"state": self.position()}


class GenerationTests(unittest.TestCase):
    def test_duplicate_policy_excludes_both_splits_and_keeps_lexical_first(self):
        def sample(game, family, split, placement, key):
            return {
                "placement": placement,
                "split": split,
                "row": {
                    "gameId": game,
                    "openingFamily": family,
                    "state": {"opaqueKey": key},
                    "labelKind": "gameOutcome",
                    "targetCentidiscs": 100,
                },
            }

        values = [
            sample("t1", "a", "T", 8, b"cross"),
            sample("v1", "b", "V", 12, b"cross"),
            sample("t3", "c", "T", 8, b"within"),
            sample("t2", "d", "T", 12, b"within"),
            sample("t2", "d", "T", 8, b"within"),
        ]
        rows, facts = generation._deduplicate(
            values, {"a", "b", "c", "d"}, lambda state: state["opaqueKey"]
        )
        self.assertEqual([row["gameId"] for row in rows], ["t2"])
        self.assertEqual(facts["crossSplitExcluded"], 2)
        self.assertEqual(facts["withinSplitExcluded"], 2)
        self.assertEqual(facts["zeroSampleFamilies"], ["a", "b", "c"])

    def test_labels_use_terminal_authority_and_sample_once_before_forced_pass(self):
        native = FixtureNative()
        opening = {
            "gameId": "development/p/T01",
            "openingFamily": "development/p/f01",
            "split": "T",
            "moves": [0] * 8,
            "state": native.position(),
        }
        evidence = {"replay": [], "complete": False}
        samples = generation._play_game(native, opening, evidence, lambda: False)
        self.assertEqual(native.simple_calls, 1)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["placement"], 8)
        row = samples[0]["row"]
        self.assertEqual(
            set(row), {"gameId", "openingFamily", "state", "labelKind", "targetCentidiscs"}
        )
        self.assertEqual(row["targetCentidiscs"], 500)
        self.assertEqual(row["labelKind"], "gameOutcome")
        self.assertEqual(len(evidence["replay"]), 10)
        self.assertIsNone(evidence["replay"][8]["move"])
        self.assertTrue(evidence["complete"])
        self.assertEqual(evidence["actualBlackMinusWhite"], 5)
        native = FixtureNative()
        with self.assertRaises(generation.GenerationStop):
            generation._play_game(native, opening, {"replay": []}, lambda: True)

    def test_frozen_fileref_is_checked_before_json_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_bytes(b"not valid JSON")
            reference = generation._ref(path)
            reference["sha256"] = "0" * 64
            with patch.object(generation.json, "loads", side_effect=AssertionError("parsed early")):
                with self.assertRaises(generation.GenerationStop):
                    generation._read(reference, 1024)

    def test_same_tree_canonical_integration(self):
        expected = Path(generation.__file__).resolve().parents[1] / "othello_arena/canonical.py"
        self.assertTrue(expected.is_file(), "same-tree arena canonical source is required")
        canonical = generation._canonical({"canonicalSource": generation._ref(expected)})
        position = {"version": 1, "board": [1, 2] + [0] * 62, "toMove": 1}
        flipped = {"version": 1, "board": [2, 1] + [0] * 62, "toMove": 2}
        self.assertEqual(canonical(position), canonical(flipped))


if __name__ == "__main__":
    unittest.main()
