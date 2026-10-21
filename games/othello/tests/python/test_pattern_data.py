import copy
import json
import random
import unittest
from unittest.mock import patch

from othello_training import data, pattern


def inputs():
    """Synthetic parser fixtures only: no rules, games, training data or fit."""
    rng = random.Random(20261022)
    families = [f"development/{i:02}" for i in range(24)]
    openings, rows = [], []
    for index, family in enumerate(families):
        board = [0] * 64
        cells = rng.sample(range(64), 12)
        for j, cell in enumerate(cells):
            board[cell] = 1 if j < 8 else 2
        position = dict(version=1, board=board, toMove=1)
        openings.append(dict(openingFamily=family, state=position))
        rows.append(
            dict(
                gameId=f"game/{index}",
                openingFamily=family,
                state=position,
                labelKind="gameOutcome",
                targetCentidiscs=200,
            )
        )
    config = dict(
        version=1,
        seed=20261022,
        trainFamilies=families[:16],
        validationFamilies=families[16:],
        openings=openings,
        finalEvaluationNamespace="final/",
        labelSource="weak-simple-policy-game-outcome",
        samplePlacements=list(range(8, 61, 4)),
        maxEpochs=64,
        learningRate=0.1,
        ridge=0.001,
        patience=8,
        maxInputBytes=1048576,
        maxRows=1024,
        maxTrainSeconds=60,
    )
    return config, rows


def load(config, rows):
    payload = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    with patch.object(data, "bounded_bytes", return_value=payload):
        return data.load_dataset("in-memory-synthetic-parser-fixture", config)


class PatternData(unittest.TestCase):
    def test_same_game_stm_labels_must_imply_the_same_final_count(self):
        config, rows = inputs()
        later = copy.deepcopy(rows[0])
        empty = [i for i, c in enumerate(later["state"]["board"]) if c == 0]
        for index in empty[:4]:
            later["state"]["board"][index] = 1
        later["state"]["toMove"] = 2
        later["targetCentidiscs"] = -200
        parsed = load(config, rows + [later])
        self.assertEqual(parsed.inferred_final_black_minus_white[rows[0]["gameId"]], 2)
        later["targetCentidiscs"] = 200
        with self.assertRaisesRegex(ValueError, "inconsistent inferred final"):
            load(config, rows + [later])

    def test_family_assignment_and_outcome_metadata(self):
        config, rows = inputs()
        parsed = load(config, rows)
        self.assertEqual((len(parsed.train), len(parsed.validation)), (16, 8))
        self.assertFalse({r.family for r in parsed.train} & {r.family for r in parsed.validation})
        self.assertEqual(
            parsed.inferred_final_black_minus_white, {f"game/{i}": 2 for i in range(24)}
        )

    def test_json_duplicate_keys_and_nonfinite_constants_reject(self):
        for text in ['{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}']:
            with self.assertRaises(ValueError):
                pattern.strict_json(text)

    def test_opening_d4_duplicate_and_final_namespace_reject(self):
        config, _ = inputs()
        config["openings"][1]["state"] = config["openings"][0]["state"]
        with self.assertRaisesRegex(ValueError, "deduplicated"):
            data.validate_config(config)
        config, _ = inputs()
        config["trainFamilies"][0] = "final/forbidden"
        with self.assertRaises(ValueError):
            data.validate_config(config)

    def test_duplicate_board_split_leak_and_game_split_reject(self):
        config, rows = inputs()
        rows[16]["state"] = rows[0]["state"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load(config, rows)
        config, rows = inputs()
        rows[16]["gameId"] = rows[0]["gameId"]
        with self.assertRaisesRegex(ValueError, "multiple families"):
            load(config, rows)

    def test_bad_target_schedule_and_missing_family_reject(self):
        for target in [True, 1.5, 200.0, 201, 6500]:
            config, rows = inputs()
            rows[0]["targetCentidiscs"] = target
            with self.assertRaises(ValueError):
                load(config, rows)
        config, rows = inputs()
        with self.assertRaisesRegex(ValueError, "all24"):
            load(config, rows[:-1])
        bad = copy.deepcopy(rows[0])
        bad["gameId"] = "other-game"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load(config, rows + [bad])
        bad = copy.deepcopy(rows[0])
        bad["state"]["board"] = [0] * 64
        with self.assertRaisesRegex(ValueError, "placement"):
            load(config, [bad] + rows[1:])


if __name__ == "__main__":
    unittest.main()
