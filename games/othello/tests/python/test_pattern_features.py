import copy
import json
import unittest

from othello_training import pattern


def fixture():
    board = [0] * 64
    for index in [0, 1, 2, 8, 10, 18, 31, 37]:
        board[index] = 1
    for index in [3, 9, 27, 36]:
        board[index] = 2
    return dict(version=1, board=board, toMove=1)


def model():
    weights = []
    for phase in range(4):
        tables = []
        for shape in range(2):
            table = []
            for code in range(729):
                swapped = pattern.swap_code(code)
                weight = (min(code, swapped) % 23 - 11) * (phase + 1) * (shape + 1)
                table.append(0 if code == swapped else weight if code < swapped else -weight)
            tables.append(table)
        weights.append(tables)
    return pattern.validate_model(pattern.schema(weights))


class PatternFeatures(unittest.TestCase):
    def test_shape_order_ternary_encoding_and_swap(self):
        board = [0] * 64
        for index, cell in zip(pattern.SHAPES[0], [0, 1, 2, 0, 1, 2], strict=True):
            board[index] = cell
        position = dict(version=1, board=board, toMove=1)
        self.assertEqual(pattern.codes(position)[0][0], 1 * 3 + 2 * 9 + 1 * 81 + 2 * 243)
        self.assertEqual(len(pattern.REPRESENTATIVES), 364)
        self.assertEqual(pattern.PARAMETERS, 2912)
        for code in range(729):
            self.assertEqual(pattern.swap_code(pattern.swap_code(code)), code)

    def test_phase_boundaries(self):
        for occupied, expected in [
            (0, 0),
            (4, 0),
            (18, 0),
            (19, 1),
            (33, 1),
            (34, 2),
            (48, 2),
            (49, 3),
            (64, 3),
        ]:
            self.assertEqual(
                pattern.phase(dict(board=[1] * occupied + [0] * (64 - occupied))), expected
            )

    def test_d4_features_and_score_and_canonical_board_are_invariant(self):
        position, weights = fixture(), model()
        self.assertEqual(pattern.codes(position)[0][0], 445)
        self.assertEqual(pattern.codes(position)[1][0], 22)
        expected = pattern.features(position)
        for symmetry in range(8):
            board = [0] * 64
            for index, cell in enumerate(position["board"]):
                board[pattern.transform(index, symmetry)] = cell
            changed = {**position, "board": board}
            self.assertEqual(pattern.features(changed), expected)
            self.assertEqual(
                pattern.evaluate(weights, changed), pattern.evaluate(weights, position)
            )
            self.assertEqual(pattern.canonical_board(changed), pattern.canonical_board(position))
        switched = {**position, "toMove": 2}
        self.assertEqual(pattern.features(switched), {index: -v for index, v in expected.items()})
        self.assertEqual(pattern.evaluate(weights, switched), -pattern.evaluate(weights, position))

    def test_unexpanded_difference_features_equal_rounded_expanded_lookups(self):
        parameters = [((index * 7) % 31 - 15) * 0.5 for index in range(pattern.PARAMETERS)]
        weights = pattern.quantize(parameters)
        position = fixture()
        expected = sum(round(parameters[i]) * v for i, v in pattern.features(position).items())
        self.assertEqual(pattern.evaluate(weights, position), max(-6400, min(6400, expected)))
        for tables in weights["weights"]:
            for table in tables:
                self.assertEqual(table[0], 0)
                self.assertTrue(all(v == -table[pattern.swap_code(c)] for c, v in enumerate(table)))

    def test_strict_model_rejection(self):
        original = model()
        for key, value in [
            ("version", True),
            ("phase", "occupied//15"),
            ("cellOrder", "big-endian"),
            ("extra", 1),
        ]:
            invalid = copy.deepcopy(original)
            invalid[key] = value
            with self.assertRaises(ValueError):
                pattern.validate_model(invalid)
        for value in [-32768, 32768, 1.5, float("nan"), True]:
            invalid = copy.deepcopy(original)
            invalid["weights"][0][0][1] = value
            with self.assertRaises(ValueError):
                pattern.validate_model(invalid)
        invalid = copy.deepcopy(original)
        invalid["quantization"]["scale"] = True
        with self.assertRaises(ValueError):
            pattern.validate_model(invalid)
        invalid = copy.deepcopy(original)
        invalid["weights"][0][0] = [0]
        with self.assertRaises(ValueError):
            pattern.validate_model(invalid)
        invalid = copy.deepcopy(original)
        invalid["weights"][0][0][0] = 1
        with self.assertRaises(ValueError):
            pattern.validate_model(invalid)

    def test_strict_state_rejection(self):
        for position in [
            {},
            {**fixture(), "version": True},
            {**fixture(), "toMove": False},
            {**fixture(), "board": [0] * 63},
            {**fixture(), "board": [0] * 63 + [True]},
        ]:
            with self.assertRaises(ValueError):
                pattern.state(position)

    def test_json_loader_and_score_saturation(self):
        weights = pattern.from_json(json.dumps(model()))
        self.assertEqual(pattern.evaluate(weights, fixture()), pattern.evaluate(model(), fixture()))
        for text in [
            '{"version":1,"version":1}',
            " " * (pattern.MODEL_MAX_BYTES + 1),
            '{"weights":NaN}',
        ]:
            with self.assertRaises(ValueError):
                pattern.from_json(text)
        saturated = pattern.quantize([32767.0] * pattern.PARAMETERS)
        position = dict(version=1, board=[1] + [0] * 63, toMove=1)
        self.assertEqual(pattern.evaluate(saturated, position), 6400)
        self.assertEqual(pattern.evaluate(saturated, {**position, "toMove": 2}), -6400)


if __name__ == "__main__":
    unittest.main()
