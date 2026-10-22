"""Arena opening identity: JSON shape and D4/STM equivalence, not game rules.

Rust remains the authority for legal moves, passes, replay and terminal scores.
No feature encoding, evaluation weights or training dependency lives here.
"""


def transform(index, symmetry):
    row, col = divmod(index, 8)
    if symmetry >= 4:
        col = 7 - col
    for _ in range(symmetry % 4):
        row, col = col, 7 - row
    return row * 8 + col


def state(value):
    if not isinstance(value, dict) or set(value) != {"version", "board", "toMove"}:
        raise ValueError("state requires exactly version, board, toMove")
    board = value["board"]
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("state version must be 1")
    if type(value["toMove"]) is not int or value["toMove"] not in (1, 2):
        raise ValueError("state toMove must be 1 or 2")
    if not isinstance(board, list) or len(board) != 64:
        raise ValueError("state board must contain 64 cells")
    if any(type(cell) is not int or cell not in (0, 1, 2) for cell in board):
        raise ValueError("state cells must be integers 0..2")
    return value


def canonical_board(position):
    """D4 and simultaneous color/STM equivalents share a key; no rules cloned."""
    side = position["toMove"]
    digits = [0 if cell == 0 else 1 if cell == side else 2 for cell in position["board"]]
    return min(
        bytes(digits[transform(index, symmetry)] for index in range(64)) for symmetry in range(8)
    )
