"""Configuration and measurements shared by NNUE training experiments."""

import copy
from array import array
import json
import math
import hashlib
import struct
import stat
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
        "warmup_steps": 0,
        "lr_decay_factor": 0.5,
        "lr_decay_patience": 2,
        "min_lr": 1e-6,
        "reflection_probability": 0.0,
        "supply_workers": 0,
        "reflection_seed": 19080314,
        "device": "cpu",
        "threads": 1,
    },
    "evaluation": {
        "interval": 10,
        "checkpoints": None,
        "batch_size": 1024,
        "monitor": "game",
        "early_stopping_patience": 5,
        "early_stopping_unit": "observation",
        "min_delta": 0.0,
        "min_delta_relative": 0.0,
        "diagnostic_rows": 256,
        "diagnostic_interval": 25,
        "diagnostic_checkpoints": None,
        "full_train": True,
        "full_train_checkpoints": [],
        "full_train_every_epochs": 5,
    },
    "limits": {"seconds": 60.0, "samples": 500000},
    "data": {"overlap_policy": "error"},
    "artifacts": {
        "mode": "native_onnx",
        "save_scheduled": False,
        "checkpoint_steps": [],
    },
    "experiment": {
        "study": None,
        "teacher_mapping": None,
        "draw_policy": None,
        "warm_start": None,
        "condition": None,
        "main_volume_N": None,
        "main_volume_manifest": None,
        "main_volume_manifest_sha256": None,
    },
}
MIXTURE_FIELDS = (
    "train_family_row_cap",
    "train_stock_strata",
    "added_rows",
    "public_rows",
    "added_exposures",
    "added_sampling_seed",
    "public_sampling_seed",
    "added_reflection_probability",
    "added_reflection_seed",
    "public_reflection_probability",
    "public_reflection_seed",
    "diagnostic_seed",
    "public_membership",
    "public_acceptance",
    "selector",
    "output_limit_bytes",
)
DEFAULTS["mixture"] = dict.fromkeys(MIXTURE_FIELDS)
# These leave the currently planned mixture's existing behaviour intact when absent.
# A recipe using either new option must supply its explicit value.
MIXTURE_OPTIONS = {
    "public_file_decay",
    "public_evaluation",
    "public_acceptance_seed",
    "training_rows",
    "training_view",
    "teacher_values",
}
DEFAULTS["mixture"].update(
    public_file_decay=None,
    public_evaluation=None,
    public_acceptance_seed=None,
    training_rows=None,
    training_view=None,
    teacher_values=None,
)


STEP_MODEL_DEFAULTS = {
    "distance_bypass": True,
    "train_transform": "F",
    "deploy_transform": "F",
}


def resolve_config(path=None, overrides=()):
    result = copy.deepcopy(DEFAULTS)
    incoming = {}
    if path:
        incoming = (
            copy.deepcopy(path) if isinstance(path, dict) else json.loads(Path(path).read_text())
        )
        for section, values in incoming.items():
            if section not in result or not isinstance(values, dict):
                raise ValueError(f"unknown/invalid section: {section}")
            for key, value in values.items():
                if (
                    key not in result[section]
                    and not (section == "model" and key in STEP_MODEL_DEFAULTS)
                    and not (section == "optimizer" and key in ("betas", "eps"))
                ):
                    raise ValueError(f"unknown setting: {section}.{key}")
                result[section][key] = value
    for override in overrides:
        name, value = override.split("=", 1)
        section, key = name.split(".", 1)
        if section not in result or (
            key not in result[section] and not (section == "model" and key in STEP_MODEL_DEFAULTS)
        ):
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
        if (section, key) in (
            ("training", "steps"),
            ("limits", "samples"),
        ) and value is None:
            continue
        if type(value) is not int or value <= 0:
            raise ValueError(f"positive integer required: {section}.{key}")
    for section, key in [
        ("evaluation", "early_stopping_patience"),
        ("evaluation", "diagnostic_rows"),
        ("training", "seed"),
        ("training", "warmup_steps"),
        ("training", "lr_decay_patience"),
        ("training", "reflection_seed"),
        ("training", "supply_workers"),
        ("evaluation", "full_train_every_epochs"),
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
        ("evaluation", "min_delta_relative"),
        ("limits", "seconds"),
        ("training", "lr_decay_factor"),
        ("training", "min_lr"),
        ("training", "reflection_probability"),
    ]:
        value = result[section][key]
        if (section, key) == ("limits", "seconds") and value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"nonnegative finite number required: {section}.{key}")
    if (
        result["optimizer"]["lr"] <= 0
        or (result["limits"]["seconds"] is not None and result["limits"]["seconds"] <= 0)
        or result["model"]["dropout"] >= 1
    ):
        raise ValueError("lr/seconds must be positive; dropout must be below 1")
    for name in ("distance_a", "distance_b"):
        value = result["model"][name]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("finite model coefficient required: " + name)
    allowed = {
        ("model", "feature_version"): ["QF1"],
        ("model", "architecture"): ["scaled", "distance_residual", "distance_steps"],
        ("optimizer", "name"): ["adam", "adamw", "sgd"],
        ("training", "target"): [
            "rootmean",
            "z",
            "outcome_steps",
            "terminal_margin",
            "completed_root_raw",
            "static_teacher",
        ],
        ("training", "sampling"): ["row", "game", "epoch"],
        ("training", "supply_workers"): [0, 2],
        ("training", "loss_weighting"): ["row", "group"],
        ("training", "scheduler"): ["none", "cosine", "plateau"],
        ("training", "device"): ["cpu", "cuda"],
        ("evaluation", "monitor"): ["row", "game"],
        ("evaluation", "early_stopping_unit"): ["observation", "epoch"],
        ("data", "overlap_policy"): ["error", "report"],
        ("artifacts", "mode"): ["native", "native_onnx"],
    }
    for (section, key), choices in allowed.items():
        if result[section][key] not in choices:
            raise ValueError(f"invalid {section}.{key}: {result[section][key]}")
    unbounded = result["training"]["steps"] is None
    if unbounded and (
        result["limits"]["seconds"] is not None
        or result["limits"]["samples"] is not None
        or result["training"]["sampling"] != "epoch"
        or result["evaluation"]["monitor"] != "row"
        or result["evaluation"]["early_stopping_unit"] != "epoch"
        or result["evaluation"]["early_stopping_patience"] <= 0
        or result["evaluation"]["checkpoints"] is not None
        or result["evaluation"]["full_train"]
        or result["artifacts"]["save_scheduled"]
        or result["artifacts"]["checkpoint_steps"]
        or result["evaluation"]["full_train_checkpoints"]
        or result["evaluation"]["diagnostic_checkpoints"] is not None
    ):
        raise ValueError(
            "unbounded fit requires null time/sample limits and scientific epoch row selection"
        )
    if result["training"]["scheduler"] == "cosine" and unbounded:
        raise ValueError("cosine scheduler requires a finite update horizon")
    if (
        result["training"]["scheduler"] == "plateau"
        and result["training"]["min_lr"] > result["optimizer"]["lr"]
    ):
        raise ValueError("plateau LR floor must not exceed initial LR")
    if (
        not 0 < result["training"]["lr_decay_factor"] < 1
        or result["training"]["min_lr"] <= 0
        or not 0 <= result["training"]["reflection_probability"] <= 1
    ):
        raise ValueError("invalid LR decay/floor or reflection probability")
    if result["training"]["reflection_probability"] and (
        (
            result["training"]["sampling"] != "epoch"
            and result["training"]["target"] != "static_teacher"
        )
        or result["training"]["reflection_seed"] == result["training"]["seed"]
    ):
        raise ValueError("online reflection requires epoch sampling and separate fixed seed")
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
            or any(
                type(v) is not int or v < 0 or (not unbounded and v > result["training"]["steps"])
                for v in points
            )
        ):
            raise ValueError("invalid observation/artifact checkpoints: " + section + "." + key)
    if result["evaluation"]["checkpoints"] is not None and not set(
        result["evaluation"]["full_train_checkpoints"]
    ) <= set(result["evaluation"]["checkpoints"]):
        raise ValueError("full_train_checkpoints must belong to explicit selector checkpoints")
    if result["model"]["architecture"] == "distance_steps":
        from .distance_steps import validate_condition

        for key, value in STEP_MODEL_DEFAULTS.items():
            result["model"].setdefault(key, value)
        validate_condition(result)
    elif any(key in result["model"] for key in STEP_MODEL_DEFAULTS):
        raise ValueError("step-score model fields require explicit distance_steps architecture")
    elif result["training"]["target"] in ("outcome_steps", "terminal_margin"):
        raise ValueError("raw-step teachers require explicit distance_steps score version")
    if result["experiment"]["study"] is not None:
        validate_mixed_config(result, incoming, overrides)
    elif result["training"]["target"] == "completed_root_raw":
        raise ValueError("raw completed D6 target requires explicit common warm-start study")
    elif result["training"]["target"] != "static_teacher" and any(
        k in result["optimizer"] for k in ("betas", "eps")
    ):
        raise ValueError("explicit Adam settings currently belong to the warm-start study")
    return result


def target_value(row, target):
    """Validate only the selected target; absent auxiliary labels stay absent."""
    if target not in ("rootmean", "z", "outcome_steps", "terminal_margin"):
        raise ValueError("unsupported training target")
    value = row.get(target)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("selected target must be a number or null")
    maximum = 80 if target in ("outcome_steps", "terminal_margin") else 1
    if not math.isfinite(value) or not -maximum <= value <= maximum:
        raise ValueError(f"selected target must be finite within [-{maximum},{maximum}]")
    if target == "outcome_steps" and value not in (-80, 0, 80):
        raise ValueError("outcome teacher is exactly80*z")
    if target == "terminal_margin" and int(value) != value:
        raise ValueError("terminal margin teacher is raw integer steps")
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


BEST43_WEIGHTS = "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841"
BEST43_DESCRIPTOR = "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1"
BEST43_EVALUATOR = "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875"
PARAMETER_SHAPES = {
    "ft.weight": (32, 312),
    "ft.bias": (32,),
    "h.weight": (32, 70),
    "h.bias": (32,),
    "out.weight": (1, 32),
    "out.bias": (1,),
}


def validate_mixed_config(config, incoming, overrides=()):
    """No generic defaults select this study's quantity or fine-tuning method."""
    if config["experiment"]["study"] != "mixed-outcome" or overrides:
        raise ValueError("explicit warm-start study; overrides are not selected recipes")
    for section in (
        "model",
        "optimizer",
        "training",
        "evaluation",
        "limits",
        "data",
        "artifacts",
    ):
        required = set(DEFAULTS[section]) | ({"betas", "eps"} if section == "optimizer" else set())
        if set(incoming.get(section, {})) != required:
            raise ValueError("warm-start requires explicit complete settings: " + section)
    optimizer = config["optimizer"]
    betas = optimizer["betas"]
    if (
        optimizer["name"] != "adam"
        or not isinstance(betas, list)
        or len(betas) != 2
        or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v < 1 for v in betas)
        or type(optimizer["eps"]) not in (int, float)
        or not math.isfinite(optimizer["eps"])
        or optimizer["eps"] <= 0
    ):
        raise ValueError("explicit selected fresh Adam beta/epsilon settings required")
    e = config["experiment"]
    validate_mixture_config(config, incoming)
    m = config["model"]
    if (
        m
        != {
            **DEFAULTS["model"],
            "architecture": "distance_residual",
            "distance_a": 0.0,
            "distance_b": 0.0,
        }
        or config["training"]["sampling"] != "epoch"
        or config["training"]["loss_weighting"] != "row"
        or config["evaluation"]["monitor"] != "row"
        or config["data"]["overlap_policy"] != "error"
        or config["artifacts"]["mode"] != "native"
        or config["artifacts"]["save_scheduled"]
        or config["artifacts"]["checkpoint_steps"]
    ):
        raise ValueError(
            "fixed BEST43 architecture/head-D/no-output-bypass and row epoch objective"
        )
    warm = e["warm_start"]
    if not isinstance(warm, dict) or set(warm) != {
        "descriptor",
        "weights",
        "evaluator_sha256",
        "optimizer",
        "scale",
    }:
        raise ValueError("explicit immutable warm-start descriptor/weights/evaluator/scale/reset")
    fresh = warm["weights"] is None
    if (
        warm["descriptor"]["sha256"] != BEST43_DESCRIPTOR
        or (fresh and warm["evaluator_sha256"] is not None)
        or (
            not fresh
            and (
                warm["weights"]["sha256"] != BEST43_WEIGHTS
                or warm["evaluator_sha256"] != BEST43_EVALUATOR
            )
        )
        or warm["optimizer"] != "fresh"
        or warm["scale"] != "incumbent"
    ):
        raise ValueError(
            "explicit BEST43 weights or fresh initialization, fresh optimizer and incumbent scale"
        )


def validate_stock_strata(strata):
    """Explicit disjoint total-stock bands; independent of labels and predictions."""
    if not isinstance(strata, list) or not strata:
        raise ValueError("nonempty stock strata required")
    covered = set()
    for band in strata:
        if (
            not isinstance(band, dict)
            or set(band) != {"min", "max", "rows"}
            or any(type(band[k]) is not int for k in band)
            or not 0 <= band["min"] <= band["max"] <= 20
            or band["rows"] <= 0
        ):
            raise ValueError("explicit stock stratum bounds and positive row cap")
        values = set(range(band["min"], band["max"] + 1))
        if covered & values:
            raise ValueError("stock strata must be disjoint")
        covered |= values
    if covered != set(range(21)):
        raise ValueError("stock strata must cover total remaining stock 0..20")


def validate_mixture_config(config, incoming):
    """All scientific mixture choices must be explicit, including null row cap."""
    m, t, e = config["mixture"], config["training"], config["evaluation"]
    keys = set(incoming.get("mixture", {}))
    if not set(MIXTURE_FIELDS) <= keys or keys - set(MIXTURE_FIELDS) - MIXTURE_OPTIONS:
        raise ValueError("complete explicit mixture settings required; no selected defaults")
    decay = m["public_file_decay"]
    if decay is not None and (
        type(decay) not in (int, float) or not math.isfinite(decay) or not 0 < decay <= 1
    ):
        raise ValueError("public file-order decay must be null or finite in (0,1]")
    if decay is not None and (type(m["public_rows"]) is not int or m["public_rows"] <= 0):
        raise ValueError("file-weighted sampling requires a public training portion")
    if decay is not None and (
        type(m["public_acceptance_seed"]) is not int or m["public_acceptance_seed"] < 0
    ):
        raise ValueError("explicit independent public acceptance seed required")
    rows = m["training_rows"]
    if rows is not None and (
        type(rows) is not int
        or rows <= 0
        or math.ceil(rows / t["batch_size"]) != t["steps"]
        or (rows % t["batch_size"] and m["added_rows"] and m["public_rows"])
    ):
        raise ValueError(
            "exact training rows/update count; partial mixed-source ratio is not configured"
        )
    public_evaluation = m["public_evaluation"]
    if public_evaluation is not None and (
        not isinstance(public_evaluation, dict)
        or set(public_evaluation) != {"validation", "train_diagnostic"}
        or public_evaluation["validation"] not in ("checkpoints", "best", "last")
        or type(public_evaluation["train_diagnostic"]) is not bool
        or (
            public_evaluation["validation"] in ("best", "last")
            and (
                not isinstance(m["selector"], dict)
                or m["selector"].get("public_non_regression") is not False
            )
        )
    ):
        raise ValueError("explicit public scopes; frozen BEST monitoring cannot select checkpoints")
    cap = m["train_family_row_cap"]
    if cap is not None and (type(cap) is not int or cap <= 0):
        raise ValueError("train_family_row_cap must be null or positive integer")
    if m["train_stock_strata"] is not None:
        if cap is not None:
            raise ValueError("choose either family cap or game stock strata")
        validate_stock_strata(m["train_stock_strata"])
    for name in ("output_limit_bytes",):
        if type(m[name]) is not int or m[name] <= 0:
            raise ValueError("positive mixture setting: " + name)
    for name in (
        "added_rows",
        "public_rows",
        "public_sampling_seed",
        "added_sampling_seed",
        "added_reflection_seed",
        "public_reflection_seed",
        "diagnostic_seed",
    ):
        if type(m[name]) is not int or m[name] < 0:
            raise ValueError("nonnegative mixture setting: " + name)
    if (
        type(m["added_exposures"]) not in (int, float)
        or not math.isfinite(m["added_exposures"])
        or m["added_exposures"] <= 0
    ):
        raise ValueError("finite positive added exposure limit")
    for name in ("added_reflection_probability", "public_reflection_probability"):
        if type(m[name]) not in (int, float) or not math.isfinite(m[name]) or not 0 <= m[name] <= 1:
            raise ValueError("finite source reflection probability: " + name)
    if (
        not isinstance(m["selector"], dict)
        or set(m["selector"]) != {"public_non_regression", "added_metric"}
        or type(m["selector"]["public_non_regression"]) is not bool
        or m["selector"]["added_metric"] not in ("mse", "family_mse")
    ):
        raise ValueError("explicit optional public nonregression selector required")
    for name in (
        "public_membership",
        "public_acceptance",
        "training_view",
        "teacher_values",
    ):
        ref = m.get(name) if name in ("training_view", "teacher_values") else m[name]
        if name in ("training_view", "teacher_values") and ref is None:
            continue
        if name == "teacher_values":
            if (
                not isinstance(ref, dict)
                or set(ref) != {"manifest", "objective"}
                or not isinstance(ref["objective"], str)
                or not ref["objective"]
            ):
                raise ValueError("bound scalar label manifest and explicit objective key required")
            ref = ref["manifest"]
        if (
            not isinstance(ref, dict)
            or set(ref) != {"path", "sha256", "bytes", "mode"}
            or not isinstance(ref["path"], str)
            or not ref["path"]
            or type(ref["bytes"]) is not int
            or not 0 < ref["bytes"] <= (4 * 1024**2 if name == "training_view" else 1024**2)
            or not isinstance(ref["sha256"], str)
            or len(ref["sha256"]) != 64
            or any(v not in "0123456789abcdef" for v in ref["sha256"])
            or ref["mode"] not in ("0600", "0644")
        ):
            raise ValueError("actual bounded public membership/custody FileRef: " + name)
    if (
        t["target"] != "z"
        or t["batch_size"] != m["added_rows"] + m["public_rows"]
        or type(t["steps"]) is not int
        or t["steps"] <= 0
        or type(config["limits"]["samples"]) is not int
        or config["limits"]["samples"] <= 0
        or e["diagnostic_rows"] <= 0
        or t["scheduler"] != "none"
        or e["early_stopping_unit"] != "observation"
        or t["supply_workers"] != 0
    ):
        raise ValueError(
            "finite full-batch outcome mixture, all-work limit, observation selector and synchronous GPU supply required"
        )
    if m.get("teacher_values") is not None and (m["public_rows"] != 0 or m["added_rows"] <= 0):
        raise ValueError("teacher sidecar belongs only to the existing added-only row stream")
    if t["reflection_probability"] != 0:
        raise ValueError(
            "source reflection configured only in mixture; no duplicate global augmentation"
        )
    if (
        config["experiment"]["teacher_mapping"] is not None
        or config["experiment"]["condition"] is not None
    ):
        raise ValueError("outcome mixture has no raw teacher mapping or paired arm selector")


def bound_file_bytes(ref, limit):
    """Existing input FileRef byte domain, before any framework or model load."""
    if (
        not isinstance(ref, dict)
        or set(ref) != {"path", "sha256", "bytes", "mode"}
        or type(ref["bytes"]) is not int
        or not 0 < ref["bytes"] <= limit
        or not isinstance(ref["path"], str)
        or not Path(ref["path"]).is_absolute()
    ):
        raise ValueError("bounded absolute FileRef required")
    p = Path(ref["path"])
    info = p.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_size != ref["bytes"]
        or f"{stat.S_IMODE(info.st_mode):04o}" != ref["mode"]
    ):
        raise ValueError("input FileRef size/mode/regular file")
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ValueError("input FileRef raw SHA mismatch")
    return raw


def warmstart_model_inputs(config):
    """Frozen normalization, with explicitly restored or newly initialized parameters."""
    from .scaled_model import validate_statistics

    warm = config["experiment"]["warm_start"]
    fresh = warm["weights"] is None
    descriptor = json.loads(bound_file_bytes(warm["descriptor"], 16384))
    if (
        descriptor["weights_SHA"] != BEST43_WEIGHTS
        or descriptor["weights_B"] != 49284
        or descriptor["little_endian_f32"] != 12321
        or descriptor["schema"] != "quoridor-nnue-distance-residual-v3"
        or descriptor["feature"] != "QF1-route4-f32-STM-scaled-residual-v3"
        or descriptor["dense_feature_version"] != "shortest-dag4-f32-STM-v1"
        or descriptor["topology"] != {"ft_width": 32, "hidden_width": 32}
        or descriptor["distance_fit"] != {"a": 0, "b": 0}
        or descriptor["route_mode"] != "zero4"
        or descriptor["route_mu_f32"] != [0.0] * 4
        or descriptor["route_sigma_f32"] != [1.0] * 4
        or descriptor["value_perspective"] != "side-to-move"
        or descriptor["value_parameterization"] != "fixed-distance-logit-plus-linear-residual-tanh"
        or (
            not fresh
            and (Path(warm["descriptor"]["path"]).parent / descriptor["weights"]).resolve()
            != Path(warm["weights"]["path"]).resolve()
        )
    ):
        raise ValueError("BEST43 architecture/head-scale/output/source convention")
    if fresh:
        if warm["evaluator_sha256"] is not None:
            raise ValueError("fresh initialization has no trained evaluator or weights")
    else:
        bound_file_bytes(warm["weights"], 49284)
    return {
        "warm_start": warm,
        "fresh_initialization": fresh,
        "scale_authority": {
            "starting_weights_sha256": descriptor["weights_SHA"],
            "descriptor_sha256": warm["descriptor"]["sha256"],
            "evaluator_sha256": BEST43_EVALUATOR,
            "scale_policy": "incumbent_descriptor_T_only",
        },
        "descriptor": descriptor,
        "statistics": validate_statistics(descriptor),
    }


def ordered_parameter_values(raw):
    """Six native FP32 tensors in the existing export order, no checkpoint optimizer."""
    if len(raw) != 49284:
        raise ValueError("exact FT32/H32 parameter byte length")
    values = struct.unpack("<12321f", raw)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("nonfinite warm-start parameter")
    out = {}
    offset = 0
    for name, shape in PARAMETER_SHAPES.items():
        count = math.prod(shape)
        out[name] = values[offset : offset + count]
        offset += count
    return out


def common_cache_config(manifest):
    """Typed published outcome-cache lineage; no study/plan or raw-range selector."""
    mcts_fields = {"mcts_source", "mcts_datasets", "mcts_native_configs"}
    mcts = bool(mcts_fields.intersection(manifest))
    if mcts and not mcts_fields.issubset(manifest):
        raise ValueError("complete MCTS source metadata required")
    c = manifest["common_corpus"]
    cfg = c["config"]
    fields = {
        "families",
        "prefix_seed",
        "prefix_lengths",
        "split_seed",
        "root_value_policy",
        "schedule",
        "partition",
        "batch_start",
        "batch_count",
        "excluded_books",
    }

    def bound_json_ref(value):
        return (
            isinstance(value, dict)
            and set(value) == {"path", "sha256"}
            and isinstance(value["path"], str)
            and bool(value["path"])
            and isinstance(value["sha256"], str)
            and len(value["sha256"]) == 64
            and all(ch in "0123456789abcdef" for ch in value["sha256"])
        )

    if (
        manifest["schema"] != "quoridor-common-corpus-terminal-geometry-v3"
        or set(cfg) != fields
        or type(cfg["families"]) is not int
        or cfg["families"] <= 0
        or any(
            type(cfg[k]) is not int or not 0 <= cfg[k] < 2**64
            for k in ("prefix_seed", "split_seed")
        )
        or not isinstance(cfg["prefix_lengths"], list)
        or not cfg["prefix_lengths"]
        or any(type(v) is not int or not 0 < v < 200 for v in cfg["prefix_lengths"])
        or len(cfg["prefix_lengths"]) != len(set(cfg["prefix_lengths"]))
        or cfg["root_value_policy"] != "outcome_only"
        or any(not bound_json_ref(cfg[k]) for k in ("schedule", "partition"))
        or not isinstance(cfg["excluded_books"], list)
        or any(not bound_json_ref(ref) for ref in cfg["excluded_books"])
        or any(type(cfg[k]) is not int or cfg[k] < 0 for k in ("batch_start", "batch_count"))
        or cfg["batch_count"] <= 0
        or cfg["batch_start"] + cfg["batch_count"] > cfg["families"]
        or c["planned_families"] != cfg["families"]
        or c["raw_file"] != "completed-root-raw.f32"
        or c["common_mask_file"] != "common-eligible.u8"
        or c["sampling_file"] != "sampling.bin"
        or c["teacher_A"] != "actual_final_z"
        or c["rootmean_is_raw"] is not mcts
        or type(manifest["rows"]) is not int
        or manifest["rows"] < 0
        or type(c["common_eligible_rows"]) is not int
        or not 0 <= c["common_eligible_rows"] <= manifest["rows"]
    ):
        raise ValueError("published configured outcome/raw/sampling contract")
    counts = c["common_eligible_by_split"]
    if (
        set(counts) != {"train", "validation"}
        or any(type(v) is not int or v < 0 for v in counts.values())
        or sum(counts.values()) != c["common_eligible_rows"]
    ):
        raise ValueError("literal outcome T/V eligible census")

    def digest(value):
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(v in "0123456789abcdef" for v in value)
        )

    if "model_scale_authority" in manifest:
        authority = manifest["model_scale_authority"]
        if (
            not isinstance(authority, dict)
            or set(authority)
            != {
                "starting_weights_sha256",
                "descriptor_sha256",
                "evaluator_sha256",
                "scale_policy",
            }
            or any(
                not digest(authority[k])
                for k in (
                    "starting_weights_sha256",
                    "descriptor_sha256",
                    "evaluator_sha256",
                )
            )
            or authority["scale_policy"] != "incumbent_descriptor_T_only"
        ):
            raise ValueError("published initializer/frozen scale authority")
    intake = manifest["stream_intake"]
    sources, bindings = manifest["source_content"], manifest["source_binding"]
    if (
        intake["status"] != "complete"
        or intake["scope"] != "common-corpus"
        or intake["publication_protocol"] != "incomplete-marker-last-v1"
        or manifest["schedule_sha256"] != cfg["schedule"]["sha256"]
        or manifest["family_partition_sha256"] != cfg["partition"]["sha256"]
        or not digest(manifest["dataset_sha"])
        or not isinstance(sources, list)
        or not sources
        or not isinstance(bindings, list)
        or len(bindings) != len(sources)
        or len(intake["batches"]) != len(sources)
    ):
        raise ValueError("published complete ordered source/global schedule/partition lineage")
    if mcts:
        model, datasets, configs = (
            manifest["mcts_source"],
            manifest["mcts_datasets"],
            manifest["mcts_native_configs"],
        )
        if (
            not isinstance(model, dict)
            or set(model) != {"model_sha256", "completed_simulations"}
            or not digest(model["model_sha256"])
            or type(model["completed_simulations"]) is not int
            or not 0 < model["completed_simulations"] < 2**32
            or not bound_json_ref(configs)
            or not Path(configs["path"]).is_absolute()
            or configs["sha256"] != manifest["dataset_sha"]
            or not isinstance(datasets, list)
            or len(datasets) != len(sources)
        ):
            raise ValueError("published MCTS model/simulations/ordered native config lineage")
        if (
            any(
                not isinstance(dataset, dict)
                or set(dataset) != {"dataset", "manifest_sha256", "rows"}
                or not isinstance(dataset["dataset"], str)
                or not Path(dataset["dataset"]).is_absolute()
                or not digest(dataset["manifest_sha256"])
                or type(dataset["rows"]) is not int
                or dataset["rows"] < 0
                for dataset in datasets
            )
            or sum(dataset["rows"] for dataset in datasets) != manifest["rows"]
        ):
            raise ValueError("published MCTS dataset manifest/row census")
    seen, cursor = set(), cfg["batch_start"]
    for source, binding, batch in zip(sources, bindings, intake["batches"]):
        if mcts:
            dataset = datasets[len(seen)]
            if (
                not isinstance(source, dict)
                or set(source) != {"encoding", "manifest"}
                or source["encoding"] != "native-teacher-dataset-shards-v1"
                or not bound_json_ref(binding)
                or not Path(binding["path"]).is_absolute()
                or source["manifest"] != binding
                or binding
                != {
                    "path": str(Path(dataset["dataset"]) / "manifest.json"),
                    "sha256": dataset["manifest_sha256"],
                }
                or binding["path"] in seen
                or set(batch) != {"batch_start", "batch_count", "config"}
                or type(batch["batch_start"]) is not int
                or batch["batch_start"] != cursor
                or type(batch["batch_count"]) is not int
                or batch["batch_count"] <= 0
                or not bound_json_ref(batch["config"])
                or not Path(batch["config"]["path"]).is_absolute()
            ):
                raise ValueError("ordered MCTS source manifest/configured batch interval")
        else:
            compressed = source["compressed"]
            if (
                set(source) != {"encoding", "compressed", "raw_sha256", "raw_bytes"}
                or source["encoding"] != "gzip-single-member-v1"
                or set(compressed) != {"path", "sha256", "bytes", "mode"}
                or not bound_json_ref(binding)
                or not Path(binding["path"]).is_absolute()
                or binding != {"path": compressed["path"], "sha256": compressed["sha256"]}
                or binding["path"] in seen
                or type(compressed["bytes"]) is not int
                or compressed["bytes"] <= 0
                or compressed["mode"] not in ("0600", "0644")
                or not digest(source["raw_sha256"])
                or type(source["raw_bytes"]) is not int
                or source["raw_bytes"] <= 0
                or set(batch) != {"batch_start", "batch_count", "config"}
                or type(batch["batch_start"]) is not int
                or batch["batch_start"] != cursor
                or type(batch["batch_count"]) is not int
                or batch["batch_count"] <= 0
                or not bound_json_ref(batch["config"])
            ):
                raise ValueError("ordered disjoint source Content/configured batch interval")
        seen.add(binding["path"])
        cursor += batch["batch_count"]
    if cursor != cfg["batch_start"] + cfg["batch_count"]:
        raise ValueError("actual batch union does not cover published interval")
    if "input_binding" in manifest or "final_fit_view" in manifest:
        # Only small SHA-bound metadata is opened here, never datasets/rows.
        metadata, metadata_bytes = {}, 0

        def metadata_identity(info):
            return (
                info.st_dev,
                info.st_ino,
                info.st_mode,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
            )

        def read_metadata_bytes(path, info, capacity, sha):
            import os

            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= capacity:
                raise ValueError("bounded regular fit-view metadata required")
            descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or metadata_identity(opened) != metadata_identity(info)
                    or metadata_identity(path.lstat()) != metadata_identity(info)
                ):
                    raise ValueError("fit-view opened metadata identity differs from path")
                chunks, remaining = [], info.st_size
                while remaining:
                    block = os.read(descriptor, min(remaining, 65536))
                    if not block:
                        break
                    chunks.append(block)
                    remaining -= len(block)
                raw = b"".join(chunks)
                if (
                    len(raw) != info.st_size
                    or hashlib.sha256(raw).hexdigest() != sha
                    or metadata_identity(os.fstat(descriptor)) != metadata_identity(info)
                    or metadata_identity(path.lstat()) != metadata_identity(info)
                ):
                    raise ValueError("fit-view metadata SHA/identity drift")
                return raw
            finally:
                os.close(descriptor)

        def read_metadata(reference, limit=1048576):
            nonlocal metadata_bytes
            if not bound_json_ref(reference) or not Path(reference["path"]).is_absolute():
                raise ValueError("absolute SHA-bound fit-view metadata required")
            key = (reference["path"], reference["sha256"])
            if key not in metadata:
                path = Path(reference["path"])
                info = path.lstat()
                if (
                    not stat.S_ISREG(info.st_mode)
                    or not 0 < info.st_size <= limit
                    or metadata_bytes + info.st_size > 16777216
                ):
                    raise ValueError("bounded regular fit-view metadata required")
                raw = read_metadata_bytes(
                    path, info, min(limit, 16777216 - metadata_bytes), reference["sha256"]
                )
                metadata_bytes += len(raw)
                metadata[key] = (json.loads(raw), info, limit)
            else:
                value, info, previous_limit = metadata[key]
                if not 0 < info.st_size <= limit:
                    raise ValueError("cached fit-view metadata exceeds current role bound")
                metadata[key] = (value, info, min(previous_limit, limit))
            return metadata[key][0]

        def exact(left, right):
            return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)

        def prefix(value):
            return isinstance(value, list) and all(
                type(action) is int and 0 <= action < 65536 for action in value
            )

        def input_assignments(config):
            schedule = read_metadata(config["schedule"], 4194304)
            partition = read_metadata(config["partition"], 4194304)
            slots = schedule["scheduled"]
            assigned = partition["assignments"]
            if (
                not isinstance(slots, list)
                or len(slots) != config["families"]
                or not isinstance(assigned, list)
                or len(assigned) != config["families"]
                or partition["schema"] != "quoridor-terminal-family-partition-v1"
                or type(partition["seed"]) is not int
                or partition["seed"] != config["split_seed"]
                or not isinstance(partition["rounding"], str)
                or not partition["rounding"]
            ):
                raise ValueError("fit-view bound schedule/partition denominator or seed")
            family_splits = {}
            for index, (slot, assignment) in enumerate(zip(slots, assigned)):
                request = f"fixed-d-family-{index:06}"
                length = config["prefix_lengths"][index % len(config["prefix_lengths"])]
                if (
                    type(slot["game"]) is not int
                    or slot["game"] != index
                    or slot["request_id"] != request
                    or type(slot["requested_prefix_length"]) is not int
                    or slot["requested_prefix_length"] != length
                    or not prefix(slot["prefix"])
                    or len(slot["prefix"]) != length
                    or slot.get("scheduled_failure") is not None
                    or set(assignment) != {"game", "family", "prefix", "split"}
                    or assignment["game"] != request
                    or not digest(assignment["family"])
                    or not prefix(assignment["prefix"])
                    or assignment["prefix"] != slot["prefix"]
                    or assignment["split"] not in ("train", "validation")
                    or family_splits.setdefault(assignment["family"], assignment["split"])
                    != assignment["split"]
                ):
                    raise ValueError("fit-view canonical request/prefix/family/split metadata")
            return assigned, partition["rounding"]

        inlet = read_metadata(manifest["input_binding"]) if "input_binding" in manifest else {}
        if not isinstance(inlet, dict):
            raise ValueError("fit-view input binding object required")
        has_view = "final_fit_view" in manifest
        if has_view != ("final_fit_view" in inlet):
            raise ValueError("manifest/input binding fit-view omission or conflict")
        if has_view:
            view = manifest["final_fit_view"]
            if (
                not mcts
                or not isinstance(view, dict)
                or set(view)
                != {"config", "scope", "realized_games", "changed_global_ids", "assignments"}
                or view["scope"] != "sampling-only-original-source-validated"
                or view["config"] != inlet["final_fit_view"]
                or "model_scale_authority" not in manifest
                or not exact(inlet.get("model_scale_authority"), manifest["model_scale_authority"])
                or not exact(read_metadata(view["config"]), cfg)
                or cfg["batch_start"] != 0
                or cfg["batch_count"] != cfg["families"]
                or type(view["realized_games"]) is not int
                or view["realized_games"] != cfg["families"]
                or not isinstance(view["assignments"], list)
                or len(view["assignments"]) != cfg["families"]
            ):
                raise ValueError("complete bound MCTS final sampling view/scale required")
            references = read_metadata(configs)
            if not exact(references, [batch["config"] for batch in intake["batches"]]):
                raise ValueError("ordered original native configs differ from source batches")
            final, rounding = input_assignments(cfg)
            expected, changed = [], []
            varying = {"families", "schedule", "partition", "batch_start", "batch_count"}
            for source_index, (reference, batch, dataset) in enumerate(
                zip(references, intake["batches"], datasets)
            ):
                native = read_metadata(reference)
                original = native["common_study"]
                if (
                    not isinstance(original, dict)
                    or set(original) != fields
                    or not exact(
                        {k: v for k, v in original.items() if k not in varying},
                        {k: v for k, v in cfg.items() if k not in varying},
                    )
                    or type(original["families"]) is not int
                    or not 0 < original["families"] <= cfg["families"]
                    or type(original["batch_start"]) is not int
                    or type(original["batch_count"]) is not int
                    or original["batch_start"] != batch["batch_start"]
                    or original["batch_count"] != batch["batch_count"]
                    or original["batch_start"] + original["batch_count"] > original["families"]
                    or type(native["simulations"]) is not int
                    or native["simulations"] != model["completed_simulations"]
                    or native["inference"]["model_sha"] != model["model_sha256"]
                    or not isinstance(native["output"], str)
                    or not Path(native["output"]).is_absolute()
                    or str(Path(native["output"]) / "dataset") != dataset["dataset"]
                ):
                    raise ValueError(
                        "original source config/slice/model/output differs from fit view"
                    )
                original_assignments, original_rounding = input_assignments(original)
                if original_rounding != rounding:
                    raise ValueError("source/final partition convention differs")
                for index in range(
                    original["batch_start"], original["batch_start"] + original["batch_count"]
                ):
                    old, new = original_assignments[index], final[index]
                    if (
                        old["game"] != new["game"]
                        or old["family"] != new["family"]
                        or old["prefix"] != new["prefix"]
                    ):
                        raise ValueError("source/final request/prefix/family differs")
                    expected.append(
                        {
                            "global_id": index,
                            "game": f"game-{index}",
                            "request_id": old["game"],
                            "source_index": source_index,
                            "family": old["family"],
                            "prefix": old["prefix"],
                            "source_split": old["split"],
                            "view_split": new["split"],
                        }
                    )
                    if old["split"] != new["split"]:
                        changed.append(index)
            if not exact(view["assignments"], expected) or not exact(
                view["changed_global_ids"], changed
            ):
                raise ValueError("exact ordered realized fit-view assignment/change correspondence")
            sampling = manifest["sampling"]
            families, codes = [], {}
            for assignment in expected:
                family = assignment["family"]
                if family not in codes:
                    codes[family] = len(families)
                    families.append(
                        {
                            "family": family,
                            "game": assignment["game"],
                            "split": assignment["view_split"],
                        }
                    )
            if not exact(sampling["families"], families) or len(sampling["games"]) != len(expected):
                raise ValueError("final sampling family/realized game census differs")
            rows, split_rows = [0] * len(families), {"train": 0, "validation": 0}
            source_rows = [0] * len(datasets)
            cursor = 0
            for assignment, game in zip(expected, sampling["games"]):
                code = codes[assignment["family"]]
                if (
                    type(game["rows"]) is not int
                    or not 0 < game["rows"] <= 200
                    or not exact(
                        game,
                        {
                            "game": assignment["game"],
                            "family_code": code,
                            "start": cursor,
                            "rows": game["rows"],
                        },
                    )
                ):
                    raise ValueError("final sampling game identity/code/chronological range")
                rows[code] += game["rows"]
                source_rows[assignment["source_index"]] += game["rows"]
                cursor += game["rows"]
            eligible = sampling["common_eligible_by_family"]
            if (
                cursor != manifest["rows"]
                or not exact(source_rows, [d["rows"] for d in datasets])
                or not exact(sampling["rows_by_family"], rows)
                or not isinstance(eligible, list)
                or len(eligible) != len(rows)
            ):
                raise ValueError("final sampling row/family census differs")
            for family, count, total in zip(families, eligible, rows):
                if type(count) is not int or not 0 <= count <= total:
                    raise ValueError("final sampling eligible family count")
                split_rows[family["split"]] += count
            if split_rows != counts:
                raise ValueError("final sampling eligible split census differs")
        # Normal caller inputs protect these metadata identities for its lifetime;
        # check every opened body again before returning this admission result.
        for (path, sha), (_, info, limit) in metadata.items():
            read_metadata_bytes(Path(path), info, min(info.st_size, limit), sha)
    return cfg
