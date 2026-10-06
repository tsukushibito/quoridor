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
        "architecture": "scaled",
        "distance_a": 0.0,
        "distance_b": 8.0,
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
        "sampling": "epoch",
        "loss_weighting": "row",
        "scheduler": "none",
        "device": "cpu",
        "threads": 1,
    },
    "evaluation": {
        "interval": 10,
        "checkpoints": None,
        "batch_size": 1024,
        "monitor": "game",
        "early_stopping_patience": 5,
        "min_delta": 0.0,
        "diagnostic_rows": 256,
        "diagnostic_interval": 25,
        "diagnostic_checkpoints": None,
        "full_train": True,
        "full_train_checkpoints": [],
    },
    "limits": {"seconds": 60.0, "samples": 500000},
    "data": {"overlap_policy": "error"},
    "artifacts": {"mode": "native_onnx", "save_scheduled": False, "checkpoint_steps": []},
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
        ("evaluation", "diagnostic_interval"),
        ("limits", "samples"),
    ]:
        value = result[section][key]
        if type(value) is not int or value <= 0:
            raise ValueError(f"positive integer required: {section}.{key}")
    for section, key in [
        ("evaluation", "early_stopping_patience"),
        ("evaluation", "diagnostic_rows"),
        ("training", "seed"),
    ]:
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
    for name in ("distance_a", "distance_b"):
        value = result["model"][name]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("finite model coefficient required: " + name)
    allowed = {
        ("model", "feature_version"): ["QF1"],
        ("model", "architecture"): ["scaled", "distance_residual"],
        ("optimizer", "name"): ["adam", "adamw", "sgd"],
        ("training", "target"): ["rootmean", "z"],
        ("training", "sampling"): ["row", "game", "epoch"],
        ("training", "loss_weighting"): ["row", "group"],
        ("training", "scheduler"): ["none", "cosine"],
        ("training", "device"): ["cpu", "cuda"],
        ("evaluation", "monitor"): ["row", "game"],
        ("data", "overlap_policy"): ["error", "report"],
        ("artifacts", "mode"): ["native", "native_onnx"],
    }
    for (section, key), choices in allowed.items():
        if result[section][key] not in choices:
            raise ValueError(f"invalid {section}.{key}: {result[section][key]}")
    if result["training"]["sampling"] == "game" and result["training"]["loss_weighting"] != "row":
        raise ValueError("game sampling already balances groups; do not weight groups twice")
    points = result["evaluation"]["checkpoints"]
    if points is not None and (
        not isinstance(points, list)
        or not points
        or any(type(v) is not int or v < 0 or v > result["training"]["steps"] for v in points)
        or points != sorted(set(points))
        or points[0] != 0
        or points[-1] != result["training"]["steps"]
    ):
        raise ValueError(
            "explicit evaluation checkpoints must be unique sorted initial-to-last steps"
        )
    if type(result["artifacts"]["save_scheduled"]) is not bool:
        raise ValueError("artifacts.save_scheduled must be boolean")
    if type(result["evaluation"]["full_train"]) is not bool:
        raise ValueError("evaluation.full_train must be boolean")
    if result["artifacts"]["save_scheduled"] and not result["evaluation"]["full_train"]:
        raise ValueError("scheduled full-row scalars require evaluation.full_train=true")
    for section, key in [
        ("evaluation", "diagnostic_checkpoints"),
        ("artifacts", "checkpoint_steps"),
        ("evaluation", "full_train_checkpoints"),
    ]:
        points = result[section][key]
        if points is not None and (
            not isinstance(points, list)
            or points != sorted(set(points))
            or any(type(v) is not int or not 0 <= v <= result["training"]["steps"] for v in points)
        ):
            raise ValueError("invalid observation/artifact checkpoints: " + section + "." + key)
    if result["evaluation"]["checkpoints"] is not None and not set(
        result["evaluation"]["full_train_checkpoints"]
    ) <= set(result["evaluation"]["checkpoints"]):
        raise ValueError("full_train_checkpoints must belong to explicit selector checkpoints")
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
