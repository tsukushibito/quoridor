"""Bounded explicit JSONL input and family splits. No Othello rule implementation."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from . import pattern

SEED = 20261022
CONFIG_KEYS = {
    "version",
    "seed",
    "trainFamilies",
    "validationFamilies",
    "holdoutFamilies",
    "familyCounts",
    "maxFamilies",
    "openings",
    "finalEvaluationNamespace",
    "labelSource",
    "labelKind",
    "teacher",
    "samplePlacements",
    "maxObservationsPerFamily",
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
        "maxEpochs": 64,
        "learningRate": 0.1,
        "ridge": 0.001,
        "patience": 8,
    }
    for key, value in fixed.items():
        actual = config[key]
        if type(actual) is not type(value) or actual != value:
            raise ValueError(f"initial fixed training setting differs: {key}")
    samples = config["samplePlacements"]
    if (
        not isinstance(samples, list)
        or not samples
        or any(type(p) is not int or not 0 <= p <= 60 for p in samples)
        or samples != sorted(set(samples))
    ):
        raise ValueError("samplePlacements must be sorted unique integer placements in0..60")
    observations = config["maxObservationsPerFamily"]
    if type(observations) is not int or not 1 <= observations <= len(samples):
        raise ValueError("maxObservationsPerFamily must be1..len(samplePlacements)")
    if config["labelKind"] not in ("gameOutcome", "teacherEstimate"):
        raise ValueError("labelKind must be gameOutcome or teacherEstimate")
    if not isinstance(config["labelSource"], str) or not config["labelSource"]:
        raise ValueError("labelSource requires explicit nonempty provenance")
    teacher = config["teacher"]
    if config["labelKind"] == "gameOutcome":
        if teacher is not None:
            raise ValueError("gameOutcome must not declare a teacher identity")
    else:
        if not isinstance(teacher, dict) or set(teacher) != {
            "id",
            "source",
            "weights",
            "adapter",
            "args",
        }:
            raise ValueError("teacher identity requires id/source/weights/adapter/args in config")
        if not isinstance(teacher["id"], str) or not teacher["id"]:
            raise ValueError("teacher id must be nonempty")
        for key in ("source", "weights", "adapter"):
            if not isinstance(teacher[key], (str, dict)) or not teacher[key]:
                raise ValueError(f"teacher {key} requires explicit fixed identity")
        if not isinstance(teacher["args"], list) or any(
            not isinstance(arg, str) for arg in teacher["args"]
        ):
            raise ValueError("teacher args must be an explicit string argv list")
        json.dumps(teacher, allow_nan=False)
    for key, maximum in [("maxInputBytes", 16 * 1024**2), ("maxRows", 4096)]:
        if type(config[key]) is not int or not 1 <= config[key] <= maximum:
            raise ValueError(f"invalid finite resource limit: {key}")
    seconds = config["maxTrainSeconds"]
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 600:
        raise ValueError("maxTrainSeconds must be finite in (0,600]")
    namespace = config["finalEvaluationNamespace"]
    if not isinstance(namespace, str) or not namespace.endswith("/") or namespace == "/":
        raise ValueError("finalEvaluationNamespace must be a nonempty named prefix ending /")
    maximum = config["maxFamilies"]
    if type(maximum) is not int or not 2 <= maximum <= 512:
        raise ValueError("maxFamilies must be an explicit finite bound in2..512")
    counts = config["familyCounts"]
    if not isinstance(counts, dict) or set(counts) != {"train", "validation", "holdout"}:
        raise ValueError("familyCounts requires train/validation/holdout counts")
    all_families = []
    for split, key in [
        ("train", "trainFamilies"),
        ("validation", "validationFamilies"),
        ("holdout", "holdoutFamilies"),
    ]:
        families, count = config[key], counts[split]
        if (
            type(count) is not int
            or count < (0 if split == "holdout" else 1)
            or count > maximum
            or not isinstance(families, list)
            or len(families) != count
        ):
            raise ValueError(f"declared {split} family count differs or exceeds bounds")
        if any(
            not isinstance(f, str) or not f or (split != "holdout" and f.startswith(namespace))
            for f in families
        ):
            raise ValueError("fit families must be named and outside final namespace")
        all_families.extend(families)
    if len(all_families) > maximum or len(set(all_families)) != len(all_families):
        raise ValueError("T/V/H families must be disjoint unique and within maxFamilies")
    if not isinstance(config["openings"], list) or len(config["openings"]) != len(all_families):
        raise ValueError("config requires each declared T/V/H actual opening for D4 dedup")
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
    target: float
    features: dict
    label_kind: str
    teacher: dict | None


@dataclass(frozen=True)
class Dataset:
    train: tuple
    validation: tuple
    sha256: str
    inferred_final_black_minus_white: dict
    coverage: dict


TEACHER_REQUIRED = {
    "id",
    "rawSTMScore",
    "scorePerspective",
    "scoreUnits",
    "scaleToCentidiscs",
    "bound",
    "proven",
}
TEACHER_OPTIONAL = {
    "completedDepth",
    "reportedProbability",
    "internalElapsedMs",
    "outerWallMs",
    "requestedTimeMs",
}


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_teacher(value, target, config):
    if (
        not isinstance(value, dict)
        or not TEACHER_REQUIRED <= set(value)
        or set(value) - TEACHER_REQUIRED - TEACHER_OPTIONAL
    ):
        raise ValueError("teacher row requires exact declared score/provenance fields")
    if (
        value["id"] != config["teacher"]["id"]
        or value["scorePerspective"] != "state.toMove"
        or value["scoreUnits"] != "engine-disc"
    ):
        raise ValueError("teacher identity/STM perspective/score units mismatch")
    if type(value["scaleToCentidiscs"]) is not int or value["scaleToCentidiscs"] != 100:
        raise ValueError("teacher scaleToCentidiscs must be integer100")
    raw = value["rawSTMScore"]
    if (
        not finite_number(raw)
        or not -64 <= raw <= 64
        or not finite_number(target)
        or not -6400 <= target <= 6400
        or target != raw * 100
    ):
        raise ValueError("teacher target must equal finite rawSTMScore*100 in range")
    if value["bound"] not in ("UNKNOWN", "EXACT", "LOWER", "UPPER") or (
        value["proven"] is not None and type(value["proven"]) is not bool
    ):
        raise ValueError("teacher bound/proven must be actual bound and bool/null")
    normalized = {**value, **{key: value.get(key) for key in TEACHER_OPTIONAL}}
    for key in TEACHER_OPTIONAL:
        metric = normalized[key]
        if metric is None or metric == "UNKNOWN":
            continue
        if not finite_number(metric) or metric < 0:
            raise ValueError(f"invalid teacher metric {key}")
        if key == "completedDepth" and type(metric) is not int:
            raise ValueError("completedDepth must be actual integer or UNKNOWN/null")
        if key == "reportedProbability" and metric > 100:
            raise ValueError("reportedProbability must retain finite reported value in0..100")
    return normalized


def validate_fit_splits(dataset, config):
    """Called before any update/selector; H rows cannot enter through this API."""
    for rows, key in [(dataset.train, "trainFamilies"), (dataset.validation, "validationFamilies")]:
        if not rows:
            raise ValueError("fit requires nonempty actual train and validation rows")
        if any(
            row.family not in config[key] or row.label_kind != config["labelKind"] for row in rows
        ):
            raise ValueError("fit/selector row outside its declared split or labelKind")


def load_dataset(path, config):
    validate_config(config)
    payload = bounded_bytes(path, config["maxInputBytes"])
    rows, boards, games, placements, scores, families = [], set(), {}, set(), {}, {}
    for number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"empty JSONL line {number}")
        if len(rows) >= config["maxRows"]:
            raise ValueError("row limit exceeded")
        row = pattern.strict_json(line)
        fields = {
            "gameId",
            "openingFamily",
            "state",
            "labelKind",
            "targetCentidiscs",
        }
        if config["labelKind"] == "teacherEstimate":
            fields.add("teacher")
        if (
            not isinstance(row, dict)
            or set(row) != fields
            or row["labelKind"] != config["labelKind"]
        ):
            raise ValueError(f"line {number} requires exact fields for configured labelKind")
        game, family = row["gameId"], row["openingFamily"]
        if not isinstance(game, str) or not game or not isinstance(family, str):
            raise ValueError(f"line {number} needs named gameId/openingFamily")
        if (
            family in config["holdoutFamilies"]
            or family not in config["trainFamilies"] + config["validationFamilies"]
        ):
            raise ValueError("H/final/outside rows forbidden from fit/selector")
        if families.get(family, 0) >= config["maxObservationsPerFamily"]:
            raise ValueError("family observation limit exceeded")
        if games.setdefault(game, family) != family:
            raise ValueError("whole game assigned to multiple families/splits")
        position = pattern.state(row["state"])
        placement = sum(cell != 0 for cell in position["board"]) - 4
        if placement not in config["samplePlacements"] or (game, placement) in placements:
            raise ValueError("row placement outside sample schedule or repeated within game")
        target = row["targetCentidiscs"]
        teacher = None
        if config["labelKind"] == "gameOutcome":
            if type(target) is not int or not -6400 <= target <= 6400 or target % 100:
                raise ValueError("outcome labels must be actual STM disc differences times100")
            final_black = target // 100 * (1 if position["toMove"] == 1 else -1)
            if scores.setdefault(game, final_black) != final_black:
                raise ValueError("inconsistent inferred final disc count for same game")
        else:
            teacher = validate_teacher(row["teacher"], target, config)
        key = pattern.canonical_board(position)
        if key in boards:
            raise ValueError("duplicate D4/STM-equivalent sampled board")
        boards.add(key)
        placements.add((game, placement))
        families[family] = families.get(family, 0) + 1
        rows.append(
            Row(
                game,
                family,
                position,
                target,
                pattern.features(position),
                config["labelKind"],
                teacher,
            )
        )
    train = tuple(row for row in rows if row.family in config["trainFamilies"])
    validation = tuple(row for row in rows if row.family in config["validationFamilies"])
    coverage = {
        split: {
            family: dict(
                observed=families.get(family, 0),
                unobservedCapacity=config["maxObservationsPerFamily"] - families.get(family, 0),
            )
            for family in config[key]
        }
        for split, key in [("train", "trainFamilies"), ("validation", "validationFamilies")]
    }
    return Dataset(train, validation, hashlib.sha256(payload).hexdigest(), scores, coverage)
