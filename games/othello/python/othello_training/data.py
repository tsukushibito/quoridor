"""Bounded explicit JSONL input and family splits. No Othello rule implementation."""

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path

from . import pattern

SEED = 20261022
SAMPLE_PLACEMENTS = list(range(8, 61, 4))
CONFIG_KEYS = {
    "version",
    "seed",
    "trainFamilies",
    "validationFamilies",
    "openings",
    "finalEvaluationNamespace",
    "labelSource",
    "samplePlacements",
    "maxEpochs",
    "learningRate",
    "ridge",
    "patience",
    "maxInputBytes",
    "maxRows",
    "maxTrainSeconds",
}


def bounded_bytes(path, maximum):
    with Path(path).open("rb") as stream:
        result = stream.read(maximum + 1)
    if len(result) > maximum:
        raise ValueError(f"input exceeds configured byte limit {maximum}")
    return result


def validate_config(config):
    if not isinstance(config, dict) or set(config) != CONFIG_KEYS:
        raise ValueError("training config has missing/unknown fields")
    fixed = {
        "version": 1,
        "seed": SEED,
        "samplePlacements": SAMPLE_PLACEMENTS,
        "labelSource": "weak-simple-policy-game-outcome",
        "maxEpochs": 64,
        "learningRate": 0.1,
        "ridge": 0.001,
        "patience": 8,
    }
    for key, value in fixed.items():
        actual = config[key]
        if type(actual) is not type(value) or actual != value:
            raise ValueError(f"initial fixed training setting differs: {key}")
    if any(type(p) is not int for p in config["samplePlacements"]):
        raise ValueError("sample placements must be integer placements")
    for key, maximum in [("maxInputBytes", 16 * 1024**2), ("maxRows", 4096)]:
        if type(config[key]) is not int or not 1 <= config[key] <= maximum:
            raise ValueError(f"invalid finite resource limit: {key}")
    seconds = config["maxTrainSeconds"]
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 600:
        raise ValueError("maxTrainSeconds must be finite in (0,600]")
    namespace = config["finalEvaluationNamespace"]
    if not isinstance(namespace, str) or not namespace.endswith("/") or namespace == "/":
        raise ValueError("finalEvaluationNamespace must be a nonempty named prefix ending /")
    train, validation = config["trainFamilies"], config["validationFamilies"]
    for families, count in [(train, 16), (validation, 8)]:
        if not isinstance(families, list) or len(families) != count:
            raise ValueError("initial split requires 16 train and 8 validation families")
        if any(not isinstance(f, str) or not f or f.startswith(namespace) for f in families):
            raise ValueError("development families must be named and outside final namespace")
    all_families = train + validation
    if len(set(all_families)) != 24:
        raise ValueError("train/validation families must be disjoint and unique")
    if not isinstance(config["openings"], list) or len(config["openings"]) != 24:
        raise ValueError("config requires the 24 actual opening states for D4 dedup")
    names, keys = set(), set()
    for opening in config["openings"]:
        if not isinstance(opening, dict) or set(opening) != {"openingFamily", "state"}:
            raise ValueError("opening requires openingFamily and state")
        family = opening["openingFamily"]
        if not isinstance(family, str) or family not in all_families or family in names:
            raise ValueError("opening family missing, repeated, or outside development split")
        key = pattern.canonical_board(pattern.state(opening["state"]))
        if key in keys:
            raise ValueError("D4/STM-equivalent opening families must be deduplicated")
        names.add(family)
        keys.add(key)
    return config


@dataclass(frozen=True)
class Row:
    game_id: str
    family: str
    state: dict
    target: int
    features: dict


@dataclass(frozen=True)
class Dataset:
    train: tuple
    validation: tuple
    sha256: str
    inferred_final_black_minus_white: dict


def load_dataset(path, config):
    validate_config(config)
    payload = bounded_bytes(path, config["maxInputBytes"])
    rows, boards, games, placements, scores, families = [], set(), {}, set(), {}, set()
    for number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"empty JSONL line {number}")
        if len(rows) >= config["maxRows"]:
            raise ValueError("row limit exceeded")
        row = pattern.strict_json(line)
        if not isinstance(row, dict) or set(row) != {
            "gameId",
            "openingFamily",
            "state",
            "labelKind",
            "targetCentidiscs",
        }:
            raise ValueError(f"line {number} requires exact outcome row fields")
        game, family = row["gameId"], row["openingFamily"]
        if not isinstance(game, str) or not game or not isinstance(family, str):
            raise ValueError(f"line {number} needs named gameId/openingFamily")
        if family not in config["trainFamilies"] + config["validationFamilies"]:
            raise ValueError("row family outside train/validation (final families forbidden)")
        if games.setdefault(game, family) != family:
            raise ValueError("whole game assigned to multiple families/splits")
        position = pattern.state(row["state"])
        placement = sum(cell != 0 for cell in position["board"]) - 4
        if placement not in config["samplePlacements"] or (game, placement) in placements:
            raise ValueError("row placement outside sample schedule or repeated within game")
        target = row["targetCentidiscs"]
        if (
            row["labelKind"] != "gameOutcome"
            or type(target) is not int
            or not -6400 <= target <= 6400
            or target % 100
        ):
            raise ValueError("outcome labels must be actual STM disc differences times100")
        final_black = target // 100 * (1 if position["toMove"] == 1 else -1)
        if scores.setdefault(game, final_black) != final_black:
            raise ValueError("inconsistent inferred final disc count for same game")
        key = pattern.canonical_board(position)
        if key in boards:
            raise ValueError("duplicate D4/STM-equivalent sampled board")
        boards.add(key)
        placements.add((game, placement))
        families.add(family)
        rows.append(Row(game, family, position, target, pattern.features(position)))
    if families != set(config["trainFamilies"] + config["validationFamilies"]):
        raise ValueError("all24 configured development families need at least one sample")
    train = tuple(row for row in rows if row.family in config["trainFamilies"])
    validation = tuple(row for row in rows if row.family in config["validationFamilies"])
    return Dataset(train, validation, hashlib.sha256(payload).hexdigest(), scores)
