"""Shared opening identity only; no game, model, teacher, fit or RNG execution."""

import unittest

from othello_arena import canonical


class CanonicalTests(unittest.TestCase):
    def test_d4_and_simultaneous_color_stm_preserve_opening_identity(self):
        board = [0] * 64
        for cell in (0, 9):
            board[cell] = 1
        for cell in (1, 18, 43):
            board[cell] = 2
        state = {"version": 1, "board": board, "toMove": 1}
        expected = canonical.canonical_board(canonical.state(state))
        for symmetry in range(8):
            transformed = [board[canonical.transform(i, symmetry)] for i in range(64)]
            for swap in (False, True):
                cells = [3 - cell if swap and cell else cell for cell in transformed]
                equivalent = {"version": 1, "board": cells, "toMove": 2 if swap else 1}
                self.assertEqual(canonical.canonical_board(canonical.state(equivalent)), expected)
        self.assertNotEqual(canonical.canonical_board(dict(state, toMove=2)), expected)
        self.assertEqual(state["board"], board)

    def test_state_shape_is_strict_without_inventing_rule_validation(self):
        state = {"version": 1, "board": [0] * 64, "toMove": 1}
        self.assertIs(canonical.state(state), state)
        for bad in (
            dict(state, version=True),
            dict(state, version=2),
            dict(state, toMove=True),
            dict(state, toMove=3),
            dict(state, board=[0] * 63),
            dict(state, board=[False] + [0] * 63),
            dict(state, board=[3] + [0] * 63),
            dict(state, extra=1),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                canonical.state(bad)


if __name__ == "__main__":
    unittest.main()
