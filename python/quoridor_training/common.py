"""Configuration and measurements shared by NNUE training experiments."""

import copy
from array import array
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
    if len(rows) != len(values):
        raise ValueError("invalid predictions")
    accumulator = MeasurementAccumulator(target, constant)
    for row, value in zip(rows, values):
        accumulator.add(row, value)
    return accumulator.result()


class _MeasurementStats:
    fields = (
        "rows",
        "rootmean_sum",
        "rootmean_rows",
        "z_sum",
        "z_rows",
        "constant_sum",
        "constant_rows",
        "sign_correct",
        "sign_rows",
        "saturated",
        "bias_sum",
        "bias_rows",
    )
    positions = {name: i for i, name in enumerate(fields)}
    __slots__ = ("values",)

    def __init__(self):
        self.values = array("d", [0.0]) * len(self.fields)

    def __getitem__(self, name):
        value = self.values[self.positions[name]]
        return value if name.endswith("_sum") else int(value)

    def __setitem__(self, name, value):
        self.values[self.positions[name]] = value


class MeasurementAccumulator:
    """Row-ordered sums and per-family sufficient statistics, without row lists."""

    def __init__(self, target, constant):
        self.target, self.constant = target, constant
        self.rows, self.saturated = 0, 0
        self.groups = {}
        self.totals = self._empty()

    @staticmethod
    def _empty():
        return _MeasurementStats()

    def add(self, row, value):
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("invalid predictions")
        group = self.groups.get(row["group"])
        if group is None:
            group = self.groups[row["group"]] = self._empty()
        for stats in (self.totals, group):
            stats["rows"] += 1
            stats["saturated"] += abs(value) >= 0.9
            for name in ("rootmean", "z"):
                label = row.get(name)
                if label is not None:
                    stats[name + "_sum"] += (value - label) ** 2
                    stats[name + "_rows"] += 1
            label = row.get(self.target)
            if label is not None:
                stats["constant_sum"] += (label - self.constant) ** 2
                stats["constant_rows"] += 1
                stats["bias_sum"] += value - float(np_float32(label))
                stats["bias_rows"] += 1
            if row.get("z") not in (None, 0):
                stats["sign_correct"] += value * row["z"] > 0
                stats["sign_rows"] += 1

    def result(self, family=None):
        stats = self.totals if family is None else self.groups[family]
        groups = list(self.groups.values()) if family is None else [stats]

        def mean(total, count):
            return total / count if count else None

        result = {"rows": stats["rows"], "games": len(groups)}
        for name in ("rootmean", "z", "constant"):
            result[name + "_mse"] = mean(stats[name + "_sum"], stats[name + "_rows"])
            valid = [g for g in groups if g[name + "_rows"]]
            result[name + "_game_equal_mse"] = (
                sum(g[name + "_sum"] / g[name + "_rows"] for g in valid) / len(valid)
                if valid
                else None
            )
            if name != "constant":
                result[name + "_rows"] = stats[name + "_rows"]
        result["target_mse"] = result[self.target + "_mse"]
        result["target_game_equal_mse"] = result[self.target + "_game_equal_mse"]
        result["z_sign_rows"] = stats["sign_rows"]
        result["z_sign_accuracy"] = mean(stats["sign_correct"], stats["sign_rows"])
        result["saturation_fraction"] = mean(stats["saturated"], stats["rows"])
        return result


def np_float32(value):
    # Match the native f32 label used by bias vectors without importing numpy for NN0 callers.
    import struct

    return struct.unpack("<f", struct.pack("<f", value))[0]
