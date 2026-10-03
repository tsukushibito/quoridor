"""Configuration and measurements shared by NNUE training experiments."""

import copy
import gzip
import hashlib
import json
import math
from pathlib import Path


DEFAULTS = {
    "model": {"feature_version": "QF1", "transformer_width": 32, "hidden_width": 32, "dropout": 0.0},
    "optimizer": {"name": "adam", "lr": 0.001, "weight_decay": 0.0, "momentum": 0.0},
    "training": {"steps": 200, "batch_size": 128, "seed": 19080311, "target": "rootmean", "sampling": "row", "scheduler": "none", "device": "cpu", "threads": 1},
    "evaluation": {"interval": 10, "batch_size": 1024, "monitor": "game", "early_stopping_patience": 5, "min_delta": 0.0},
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
    for section, key in [("model", "transformer_width"), ("model", "hidden_width"), ("training", "steps"), ("training", "batch_size"), ("training", "threads"), ("evaluation", "interval"), ("evaluation", "batch_size"), ("limits", "samples")]:
        value = result[section][key]
        if type(value) is not int or value <= 0:
            raise ValueError(f"positive integer required: {section}.{key}")
    for section, key in [("evaluation", "early_stopping_patience"), ("training", "seed")]:
        value = result[section][key]
        if type(value) is not int or value < 0:
            raise ValueError(f"nonnegative integer required: {section}.{key}")
    for section, key in [("model", "dropout"), ("optimizer", "lr"), ("optimizer", "weight_decay"), ("optimizer", "momentum"), ("evaluation", "min_delta"), ("limits", "seconds")]:
        value = result[section][key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"nonnegative finite number required: {section}.{key}")
    if result["optimizer"]["lr"] <= 0 or result["limits"]["seconds"] <= 0 or result["model"]["dropout"] >= 1:
        raise ValueError("lr/seconds must be positive; dropout must be below 1")
    allowed = {("model", "feature_version"): ["QF1"], ("optimizer", "name"): ["adam", "adamw", "sgd"], ("training", "target"): ["rootmean", "z"], ("training", "sampling"): ["row", "game"], ("training", "scheduler"): ["none", "cosine"], ("training", "device"): ["cpu", "cuda"], ("evaluation", "monitor"): ["row", "game"], ("data", "overlap_policy"): ["error", "report"]}
    for (section, key), choices in allowed.items():
        if result[section][key] not in choices:
            raise ValueError(f"invalid {section}.{key}: {result[section][key]}")
    return result


def feature_key(row):
    encoded = json.dumps([sorted(row["ids"][0]), sorted(row["ids"][1]), row["distance"], row["side"]], separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def load_data(path, overlap_policy="error"):
    data = Path(path).read_bytes()
    stage = None
    if str(path).endswith('.stage.json'):
        from frame14_data import load_stage
        rows, stage = load_stage(path)
    else:
        raw = gzip.decompress(data) if str(path).endswith(".gz") else data
    if stage is not None:
        pass
    elif str(path).removesuffix(".gz").endswith(".jsonl"):
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        obj = json.loads(raw)
        rows = obj["samples"] if isinstance(obj, dict) else obj
    if not isinstance(rows, list) or not rows:
        raise ValueError("no samples")
    ids = set()
    exposures = {key: {} for key in ["group", "exposure_group", "state_key", "history_key", "features"]}
    counts = {"train": 0, "validation": 0}
    for row in rows:
        if not isinstance(row.get("id"), str) or row["id"] in ids:
            raise ValueError("missing/duplicate row id")
        ids.add(row["id"])
        split = row.get("split")
        if split not in counts:
            raise ValueError("only train/validation allowed; keep final test data outside training")
        counts[split] += 1
        if not isinstance(row.get("group"), str) or not row["group"]:
            raise ValueError("each row needs its game/family group")
        if type(row.get("side")) is not int or row["side"] not in (1, 2) or len(row.get("ids", [])) != 2 or len(row.get("distance", [])) != 2:
            raise ValueError("invalid QF1 input")
        for view in row["ids"]:
            if not isinstance(view, list) or len(view) != len(set(view)) or not 4 <= len(view) <= 24 or any(type(i) is not int or not 0 <= i < 312 for i in view):
                raise ValueError("invalid sparse QF1 indices")
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in row["distance"]):
            raise ValueError("invalid normalized distance")
        for target in ("rootmean", "z"):
            value = row.get(target)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not -1 <= value <= 1):
                raise ValueError(f"invalid target: {target}")
        for key in exposures:
            value = feature_key(row) if key == "features" else row.get(key)
            if value is not None:
                exposures[key].setdefault(value, set()).add(split)
    if not all(counts.values()):
        raise ValueError("train and validation must both be nonempty")
    overlap = {key: sum(len(splits) > 1 for splits in seen.values()) for key, seen in exposures.items()}
    if overlap["group"] or overlap["exposure_group"]:
        raise ValueError("game/exposure group crosses train-validation split")
    if overlap_policy == "error" and any(overlap.values()):
        raise ValueError(f"state/history/features cross split: {overlap}")
    split_hashes = {s + "_sha256": hashlib.sha256(json.dumps(sorted([r for r in rows if r["split"] == s], key=lambda r: r["id"]), sort_keys=True, separators=(",", ":")).encode()).hexdigest() for s in counts}
    return rows, {"path": str(Path(path).resolve()), "sha256": hashlib.sha256(data).hexdigest(), **split_hashes, "rows": len(rows), "counts": counts, "groups": {s: len({r["group"] for r in rows if r["split"] == s}) for s in counts}, "cross_split_keys": overlap, "stage_manifest": stage, "independent_test": False}


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
        result[name + "_game_equal_mse"] = sum(sum(e) / len(e) for e in grouped.values()) / len(grouped) if grouped else None
        result[name + "_rows"] = len(valid)
    valid = [(r, v) for r, v in zip(rows, values) if r.get(target) is not None]
    result["target_mse"] = result[target + "_mse"]
    result["target_game_equal_mse"] = result[target + "_game_equal_mse"]
    result["constant_mse"] = sum((r[target] - constant) ** 2 for r, _ in valid) / len(valid) if valid else None
    constant_groups = {}
    for r, _ in valid:
        constant_groups.setdefault(r["group"], []).append((r[target] - constant) ** 2)
    result["constant_game_equal_mse"] = sum(sum(e) / len(e) for e in constant_groups.values()) / len(constant_groups) if constant_groups else None
    eligible = [(r, v) for r, v in zip(rows, values) if r.get("z") not in (None, 0)]
    result["z_sign_rows"] = len(eligible)
    result["z_sign_accuracy"] = sum(v * r["z"] > 0 for r, v in eligible) / len(eligible) if eligible else None
    result["saturation_fraction"] = sum(abs(v) >= 0.9 for v in values) / len(values) if values else None
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
