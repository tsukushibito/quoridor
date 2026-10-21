"""Fixed pattern-v1 schema and STM features, shared contract with Rust pattern.rs."""

from collections import Counter
import json
import math

SHAPES = ((0, 1, 2, 8, 9, 10), (1, 2, 3, 4, 5, 6))
CELL_ORDER = "shape-list-lsb-ternary"
ENCODING = "empty0-stm1-opponent2"
TRANSFORMS = "mirror-then-clockwise-rotations-0-1-2-3"
PHASE = "min(3,clamp(occupied-4,0,60)//15)"
MODEL_MAX_BYTES = 128 * 1024


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)


def from_json(text):
    size = len(text.encode("utf-8")) if isinstance(text, str) else len(text)
    if size > MODEL_MAX_BYTES:
        raise ValueError("pattern JSON exceeds128KiB")
    return validate_model(strict_json(text))


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


def phase(position):
    occupied = sum(cell != 0 for cell in position["board"])
    return min(3, max(0, min(60, occupied - 4)) // 15)


def codes(position):
    board, side = position["board"], position["toMove"]
    digits = [0 if cell == 0 else 1 if cell == side else 2 for cell in board]
    return tuple(
        tuple(
            sum(digits[transform(index, symmetry)] * 3**j for j, index in enumerate(shape))
            for symmetry in range(8)
        )
        for shape in SHAPES
    )


def swap_code(code):
    result, power = 0, 1
    for _ in range(6):
        digit = code % 3
        result += (0 if digit == 0 else 3 - digit) * power
        power *= 3
        code //= 3
    return result


REPRESENTATIVES = tuple(code for code in range(729) if code < swap_code(code))
PAIR_INDEX = {code: index for index, code in enumerate(REPRESENTATIVES)}
PARAMETERS = 4 * 2 * len(REPRESENTATIVES)


def features(position):
    """Sparse count(code)-count(swap(code)) for one representative of each pair."""
    result = Counter()
    offset = phase(position) * 2 * len(REPRESENTATIVES)
    for shape, occurrences in enumerate(codes(position)):
        for code in occurrences:
            swapped = swap_code(code)
            if code != swapped:
                representative = min(code, swapped)
                index = offset + shape * len(REPRESENTATIVES) + PAIR_INDEX[representative]
                result[index] += 1 if code == representative else -1
    return {index: count for index, count in sorted(result.items()) if count}


def canonical_board(position):
    """D4 and simultaneous color/STM equivalents share a key; no rules cloned."""
    side = position["toMove"]
    digits = [0 if cell == 0 else 1 if cell == side else 2 for cell in position["board"]]
    return min(
        bytes(digits[transform(index, symmetry)] for index in range(64)) for symmetry in range(8)
    )


def schema(weights):
    return {
        "version": 1,
        "shapes": [list(shape) for shape in SHAPES],
        "cellOrder": CELL_ORDER,
        "encoding": ENCODING,
        "transforms": TRANSFORMS,
        "phase": PHASE,
        "score": "stm-centidiscs",
        "quantization": {
            "scale": 1,
            "rounding": "nearest-ties-even",
            "minimum": -32767,
            "maximum": 32767,
        },
        "weights": weights,
    }


def validate_model(model):
    if not isinstance(model, dict) or set(model) != set(schema([])):
        raise ValueError("pattern model has missing or unknown fields")
    if type(model["version"]) is not int or model["version"] != 1:
        raise ValueError("pattern model version must be 1")
    expected = schema(model["weights"])
    actual_metadata = {key: value for key, value in model.items() if key != "weights"}
    expected_metadata = {key: value for key, value in expected.items() if key != "weights"}
    if json.dumps(actual_metadata, sort_keys=True, allow_nan=False) != json.dumps(
        expected_metadata, sort_keys=True, allow_nan=False
    ):
        raise ValueError("pattern shape/cell-order/phase/quantization metadata differs")
    weights = model["weights"]
    if not isinstance(weights, list) or len(weights) != 4:
        raise ValueError("pattern weights require 4 phases")
    for shapes in weights:
        if not isinstance(shapes, list) or len(shapes) != 2:
            raise ValueError("pattern phase requires 2 shapes")
        for table in shapes:
            if not isinstance(table, list) or len(table) != 729:
                raise ValueError("pattern table requires 729 cells")
            if any(type(w) is not int or not -32767 <= w <= 32767 for w in table):
                raise ValueError("pattern weights must be finite symmetric-range i16 integers")
            if any(weight != -table[swap_code(code)] for code, weight in enumerate(table)):
                raise ValueError("pattern weights must be color antisymmetric")
    return model


def quantize(parameters):
    if len(parameters) != PARAMETERS:
        raise ValueError("wrong number of unexpanded parameters")
    rounded = []
    for weight in parameters:
        if not math.isfinite(float(weight)):
            raise ValueError("nonfinite parameter STOP")
        value = round(float(weight))
        if not -32767 <= value <= 32767:
            raise ValueError("quantized parameter exceeds symmetric i16 range STOP")
        rounded.append(value)
    weights = [[[0] * 729 for _ in SHAPES] for _ in range(4)]
    for p in range(4):
        for shape in range(2):
            for pair, code in enumerate(REPRESENTATIVES):
                value = rounded[(p * 2 + shape) * len(REPRESENTATIVES) + pair]
                weights[p][shape][code] = value
                weights[p][shape][swap_code(code)] = -value
    return validate_model(schema(weights))


def evaluate(model, position):
    """For an already validated model, exactly match Rust's 16 integer lookups."""
    p = phase(position)
    total = sum(
        model["weights"][p][shape][code]
        for shape, occurrence in enumerate(codes(position))
        for code in occurrence
    )
    return max(-6400, min(6400, total))
