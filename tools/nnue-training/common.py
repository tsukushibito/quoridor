"""Configuration and measurements shared by NNUE training experiments."""

import copy
import json
import math
from pathlib import Path

from dataset import feature_key, load_data

__all__ = [
    "feature_key",
    "load_data",
    "resolve_config",
    "write_json",
    "measurements",
    "EarlyStopping",
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


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


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


class EarlyStopping:
    def __init__(self, patience, min_delta):
        self.patience = patience
        self.min_delta = min_delta
        self.best = math.inf
        self.bad = 0

    def observe(self, value):
        if not math.isfinite(value):
            raise ValueError("nonfinite validation error")
        improved = value < self.best - self.min_delta
        if improved:
            self.best, self.bad = value, 0
        else:
            self.bad += 1
        return improved, bool(self.patience and self.bad >= self.patience)
