"""Configuration and measurements shared by NNUE training experiments."""

import copy
import json
import math
from pathlib import Path

__all__ = [
    "resolve_config",
    "measurements",
]


DEFAULTS = {
    "model": {
        "feature_version": "QF1",
        "transformer_width": 32,
        "hidden_width": 32,
        "dropout": 0.0,
    },
    "optimizer": {"name": "adam", "lr": 0.001, "weight_decay": 0.0, "momentum": 0.0},
    "training": {
        "steps": 200,
        "batch_size": 128,
        "seed": 19080311,
        "target": "rootmean",
        "sampling": "row",
        "scheduler": "none",
        "device": "cpu",
        "threads": 1,
    },
    "evaluation": {
        "interval": 10,
        "batch_size": 1024,
        "monitor": "game",
        "early_stopping_patience": 5,
        "min_delta": 0.0,
    },
    "limits": {"seconds": 60.0, "samples": 500000},
    "data": {"overlap_policy": "error"},
}


def resolve_config(path=None, overrides=()):
    result = copy.deepcopy(DEFAULTS)
    if path:
        incoming = json.loads(Path(path).read_text())
        for section, values in incoming.items():
            if section not in result or not isinstance(values, dict):
                raise ValueError(f"unknown/invalid section: {section}")
            for key, value in values.items():
                if key not in result[section]:
                    raise ValueError(f"unknown setting: {section}.{key}")
                result[section][key] = value
    for override in overrides:
        name, value = override.split("=", 1)
        section, key = name.split(".", 1)
        if section not in result or key not in result[section]:
            raise ValueError(f"unknown setting: {name}")
        result[section][key] = json.loads(value)
    for section, key in [
        ("model", "transformer_width"),
        ("model", "hidden_width"),
        ("training", "steps"),
        ("training", "batch_size"),
        ("training", "threads"),
        ("evaluation", "interval"),
        ("evaluation", "batch_size"),
        ("limits", "samples"),
    ]:
        value = result[section][key]
        if type(value) is not int or value <= 0:
            raise ValueError(f"positive integer required: {section}.{key}")
    for section, key in [("evaluation", "early_stopping_patience"), ("training", "seed")]:
        value = result[section][key]
        if type(value) is not int or value < 0:
            raise ValueError(f"nonnegative integer required: {section}.{key}")
    for section, key in [
        ("model", "dropout"),
        ("optimizer", "lr"),
        ("optimizer", "weight_decay"),
        ("optimizer", "momentum"),
        ("evaluation", "min_delta"),
        ("limits", "seconds"),
    ]:
        value = result[section][key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"nonnegative finite number required: {section}.{key}")
    if (
        result["optimizer"]["lr"] <= 0
        or result["limits"]["seconds"] <= 0
        or result["model"]["dropout"] >= 1
    ):
        raise ValueError("lr/seconds must be positive; dropout must be below 1")
    allowed = {
        ("model", "feature_version"): ["QF1"],
        ("optimizer", "name"): ["adam", "adamw", "sgd"],
        ("training", "target"): ["rootmean", "z"],
        ("training", "sampling"): ["row", "game"],
        ("training", "scheduler"): ["none", "cosine"],
        ("training", "device"): ["cpu", "cuda"],
        ("evaluation", "monitor"): ["row", "game"],
        ("data", "overlap_policy"): ["error", "report"],
    }
    for (section, key), choices in allowed.items():
        if result[section][key] not in choices:
            raise ValueError(f"invalid {section}.{key}: {result[section][key]}")
    return result


def target_value(row, target):
    """Validate only the selected target; absent auxiliary labels stay absent."""
    if target not in ("rootmean", "z"):
        raise ValueError("unsupported training target")
    value = row.get(target)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("selected target must be a number or null")
    if not math.isfinite(value) or not -1 <= value <= 1:
        raise ValueError("selected target must be finite within [-1,1]")
    return float(value)


def selected_teacher_types(rows, target):
    """Teacher provenance follows eligible selected labels, never rootmean alone."""
    types = set()
    for row in rows:
        if row["split"] not in ("train", "validation"):
            raise ValueError("training labels must exclude test/unknown partitions")
        value = target_value(row, target)
        if not row["primary_eligible"] or value is None:
            continue
        kind = row.get("teacher_type")
        if not isinstance(kind, str) or not kind:
            raise ValueError("eligible selected target needs teacher provenance")
        types.add(kind)
    if len(types) != 1:
        raise ValueError("teacher types must not be mixed implicitly: " + str(types))
    return types


def validate_target_tensor(rows, values, target):
    """Bind metadata to the chosen f32 column; missing labels are NaN, not zero."""
    import struct

    if len(rows) != len(values):
        raise ValueError("target tensor row count differs")
    for row, tensor in zip(rows, values):
        value = target_value(row, target)
        tensor = float(tensor)
        if value is None:
            if not math.isnan(tensor):
                raise ValueError("missing selected target must have NaN tensor")
        elif not math.isfinite(tensor) or struct.pack("<f", value) != struct.pack("<f", tensor):
            raise ValueError("selected target metadata/tensor f32 mismatch")


def measurements(rows, values, target, constant):
    if len(rows) != len(values) or any(not math.isfinite(v) for v in values):
        raise ValueError("invalid predictions")
    result = {"rows": len(rows), "games": len({r["group"] for r in rows})}
    for name in ["rootmean", "z"]:
        valid = [(r, v) for r, v in zip(rows, values) if r.get(name) is not None]
        errors = [(v - r[name]) ** 2 for r, v in valid]
        grouped = {}
        for (row, _), error in zip(valid, errors):
            grouped.setdefault(row["group"], []).append(error)
        result[name + "_mse"] = sum(errors) / len(errors) if errors else None
        result[name + "_game_equal_mse"] = (
            sum(sum(e) / len(e) for e in grouped.values()) / len(grouped) if grouped else None
        )
        result[name + "_rows"] = len(valid)
    valid = [(r, v) for r, v in zip(rows, values) if r.get(target) is not None]
    result["target_mse"] = result[target + "_mse"]
    result["target_game_equal_mse"] = result[target + "_game_equal_mse"]
    result["constant_mse"] = (
        sum((r[target] - constant) ** 2 for r, _ in valid) / len(valid) if valid else None
    )
    constant_groups = {}
    for r, _ in valid:
        constant_groups.setdefault(r["group"], []).append((r[target] - constant) ** 2)
    result["constant_game_equal_mse"] = (
        sum(sum(e) / len(e) for e in constant_groups.values()) / len(constant_groups)
        if constant_groups
        else None
    )
    eligible = [(r, v) for r, v in zip(rows, values) if r.get("z") not in (None, 0)]
    result["z_sign_rows"] = len(eligible)
    result["z_sign_accuracy"] = (
        sum(v * r["z"] > 0 for r, v in eligible) / len(eligible) if eligible else None
    )
    result["saturation_fraction"] = (
        sum(abs(v) >= 0.9 for v in values) / len(values) if values else None
    )
    return result
