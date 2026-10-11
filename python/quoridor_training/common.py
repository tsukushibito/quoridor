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
    "artifacts": {"mode": "native_onnx", "save_scheduled": False, "checkpoint_steps": []},
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
STEP_MODEL_DEFAULTS = {"distance_bypass": True, "train_transform": "F", "deploy_transform": "F"}


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
        if (section, key) in (("training", "steps"), ("limits", "samples")) and value is None:
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
        result["training"]["sampling"] != "epoch"
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
        validate_warmstart_config(result, incoming, overrides)
    elif result["training"]["target"] == "completed_root_raw":
        raise ValueError("raw completed D6 target requires explicit common warm-start study")
    elif any(k in result["optimizer"] for k in ("betas", "eps")):
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


WARMSTART_STUDY = "common-corpus-warmstart-v1"
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


def validate_warmstart_config(config, incoming, overrides=()):
    """No generic defaults select this study's quantity or fine-tuning method."""
    if config["experiment"]["study"] != WARMSTART_STUDY or overrides:
        raise ValueError("explicit warm-start study; overrides are not selected recipes")
    for section in ("model", "optimizer", "training", "evaluation", "limits", "data", "artifacts"):
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
    if (
        type(e["main_volume_N"]) is not int
        or e["main_volume_N"] <= 0
        or e["teacher_mapping"] not in ("exclude_outside_unit", "divide_by_two")
        or e["draw_policy"] not in ("include_threefold", "exclude_threefold")
        or config["training"]["target"] not in ("z", "completed_root_raw")
    ):
        raise ValueError("human N/teacher mapping/draw policy/selected teacher are required")
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
    if (
        warm["descriptor"]["sha256"] != BEST43_DESCRIPTOR
        or warm["weights"]["sha256"] != BEST43_WEIGHTS
        or warm["evaluator_sha256"] != BEST43_EVALUATOR
        or warm["optimizer"] != "fresh"
        or warm["scale"] != "incumbent"
    ):
        raise ValueError(
            "both fits start from exact BEST43 with fresh optimizer and incumbent scale"
        )


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


def warmstart_inputs(config, *, cache, config_path, input_binding):
    """Join the existing immutable fit input binding; not a second fit permit."""
    if config["experiment"]["study"] != WARMSTART_STUDY:
        return None
    if config_path is None or input_binding is None:
        raise ValueError("warm-start requires selected config and existing guarded input binding")
    from .distance_steps import bound_json, require_completed_stream_cache
    from .scaled_model import validate_statistics

    expected = json.loads(Path(input_binding).read_bytes())
    selected_plan = expected["selected_plan"]
    if Path(selected_plan["path"]).stat().st_size > 65536:
        raise ValueError("selected canonical plan byte bound")
    plan = bound_json(selected_plan["path"], selected_plan["sha256"])
    settings = plan["next_learning_study"]["common_learner_settings"]
    if (
        not isinstance(settings, dict)
        or set(settings) != set(DEFAULTS)
        or not isinstance(settings.get("training"), dict)
        or "target" in settings["training"]
    ):
        raise ValueError("complete selected normalized recipe without teacher target required")
    explicit = copy.deepcopy(settings)
    explicit["training"]["target"] = "z"  # Validation only; the two teachers stay distinct.
    selected_recipe = resolve_config(explicit)
    if selected_recipe != explicit:
        raise ValueError("selected canonical settings cannot use unselected defaults")
    selected_recipe["training"].pop("target")
    pairs = expected["paired_fit_configs"]
    if not isinstance(pairs, list) or len(pairs) != 2:
        raise ValueError("exact two independently bound common fit configs required")
    recipes = []
    selected = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
    targets = set()
    for ref in pairs:
        bound_file_bytes(ref, 65536)
        recipe = resolve_config(ref["path"])
        targets.add(recipe["training"].pop("target"))
        recipes.append(recipe)
    if (
        targets != {"z", "completed_root_raw"}
        or any(recipe != selected_recipe for recipe in recipes)
        or selected not in {ref["sha256"] for ref in pairs}
    ):
        raise ValueError("both teachers must match canonical selected settings except target")
    warm = config["experiment"]["warm_start"]
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
        or (Path(warm["descriptor"]["path"]).parent / descriptor["weights"]).resolve()
        != Path(warm["weights"]["path"]).resolve()
    ):
        raise ValueError("BEST43 architecture/head-scale/output/source convention")
    bound_file_bytes(warm["weights"], 49284)
    manifest = bound_json(Path(cache) / "cache.json", expected["cache_manifest_sha"])
    require_completed_stream_cache(cache, manifest)
    common_cache_config(manifest, config["experiment"], plan=plan)
    if (
        expected.get("fit_config_sha") != hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
        or expected.get("initial_weights_sha") != BEST43_WEIGHTS
        or expected.get("warm_start") != warm
        or manifest["stream_intake"]["human_quantity_n"] != config["experiment"]["main_volume_N"]
        or manifest["schedule_sha256"] != expected["schedule_sha256"]
        or manifest["family_partition_sha256"] != expected["family_partition_sha256"]
        or manifest["source_binding"] != expected["dataset"]
    ):
        raise ValueError(
            "actual common corpus/quantity/schedule/partition/warm-start/config binding"
        )
    return {
        "expected": expected,
        "descriptor": descriptor,
        "statistics": validate_statistics(descriptor),
        "warm_start": warm,
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


def common_cache_config(manifest, experiment=None, selected_plan=None, plan=None):
    """The opt-in cache, selected plan and literal family partition precede arrays."""
    c = manifest["common_corpus"]
    cfg = c["config"]
    if (
        manifest["schema"] != "quoridor-common-corpus-terminal-geometry-v3"
        or set(cfg)
        != {
            "selected_plan",
            "families",
            "prefix_seed",
            "prefix_lengths",
            "split_seed",
            "root_value_policy",
            "draw_policy",
        }
        or set(cfg["selected_plan"]) != {"path", "sha256"}
        or cfg["selected_plan"]["path"]
        != "/workspaces/quoridor/research-data/ai-sigma/teacher-distance-tanh-v1/plan.json"
        or not isinstance(cfg["selected_plan"]["sha256"], str)
        or len(cfg["selected_plan"]["sha256"]) != 64
        or any(v not in "0123456789abcdef" for v in cfg["selected_plan"]["sha256"])
        or type(cfg["families"]) is not int
        or cfg["families"] <= 0
        or any(
            type(cfg[k]) is not int or not 0 <= cfg[k] < 2**64
            for k in ("prefix_seed", "split_seed")
        )
        or not isinstance(cfg["prefix_lengths"], list)
        or not cfg["prefix_lengths"]
        or any(type(v) is not int or not 0 < v < 200 for v in cfg["prefix_lengths"])
        or cfg["prefix_lengths"] != sorted(set(cfg["prefix_lengths"]))
        or cfg["families"] % len(cfg["prefix_lengths"])
        or cfg["root_value_policy"] not in ("exclude_outside_unit", "divide_by_two")
        or cfg["draw_policy"] not in ("include_threefold", "exclude_threefold")
        or c["planned_families"] != cfg["families"]
        or c["raw_file"] != "completed-root-raw.f32"
        or c["common_mask_file"] != "common-eligible.u8"
        or c["sampling_file"] != "sampling.bin"
        or c["teacher_A"] != "actual_final_z"
        or c["teacher_B"] != "explicit_mapping_of_completed_root_raw"
        or c["rootmean_is_raw"] is not False
        or c["same_mask_and_family_partition_for_both"] is not True
        or type(c["common_eligible_rows"]) is not int
        or not 0 <= c["common_eligible_rows"] <= manifest["rows"]
    ):
        raise ValueError("common cache selected config/raw/mask contract")
    authority = manifest["model_scale_authority"]
    if authority != {
        "selected_plan": cfg["selected_plan"],
        "starting_weights_sha256": BEST43_WEIGHTS,
        "descriptor_sha256": BEST43_DESCRIPTOR,
        "evaluator_sha256": BEST43_EVALUATOR,
        "scale_policy": "incumbent_descriptor_T_only",
    }:
        raise ValueError("common cache incumbent model/scale authority")
    intake = manifest["stream_intake"]
    header = intake["provenance"]["header"]
    expected_header_keys = {
        "schema",
        "generator_version",
        "config_sha256",
        "compiled_sources",
        "evaluator",
        "executable_sha256",
        "family_partition_sha256",
        "planned",
        "detailed_schedule_history",
    }
    source = manifest["source_content"]
    if (
        intake["status"] != "complete"
        or intake["scope"] != "common-corpus"
        or intake["publication_protocol"] != "incomplete-marker-last-v1"
        or intake["human_quantity_n"] != cfg["families"]
        or set(header) != expected_header_keys
        or header["schema"] != "quoridor-fixed-d-common-corpus-v1"
        or header["generator_version"] != "fixed-d-common-corpus-warmstart-v1"
        or header["evaluator"] != "original-distance-a0-b8-tanh"
        or header["planned"] != cfg["families"]
        or header["config_sha256"] != intake["config"]["sha256"]
        or header["family_partition_sha256"] != manifest["family_partition_sha256"]
        or intake["provenance"]["requests"] is not None
        or manifest["dataset_sha"] != source["compressed"]["sha256"]
        or manifest["source_binding"]
        != {"path": source["compressed"]["path"], "sha256": source["compressed"]["sha256"]}
        or (selected_plan is not None and selected_plan != cfg["selected_plan"])
        or (
            experiment is not None
            and (
                experiment["main_volume_N"] != cfg["families"]
                or experiment["teacher_mapping"] != cfg["root_value_policy"]
                or experiment["draw_policy"] != cfg["draw_policy"]
            )
        )
    ):
        raise ValueError("completed common scope/header/learner config/selected-plan mismatch")
    if plan is not None:
        study = plan["next_learning_study"]
        if (
            study["issue"] != "quoridor-4lc.362"
            or study["scientific_entry"] is not True
            or study["corpus"]["quantity_families"] != cfg["families"]
            or study["corpus"]["offtrajectory_rows"] != 0
            or study["starting_weights_SHA256"] != BEST43_WEIGHTS
            or study["descriptor_SHA256"] != BEST43_DESCRIPTOR
            or study["typed_evaluator_content_SHA256"] != BEST43_EVALUATOR
            or study["common_learner_settings"] is None
            or study["corpus"]["blind_schedule"]
            != {
                "version": "fixed-d-common-corpus-warmstart-v1",
                "prefix_seed": cfg["prefix_seed"],
                "prefix_lengths": cfg["prefix_lengths"],
                "ordering": "round_robin_lengths",
                "attempts_per_family": 32,
                "old_games_included": False,
            }
            or study["corpus"]["whole_family_T_V_partition"]
            != {
                "algorithm": "canonical_LR_family_SHA256_seed_rank_train_floor_4F_over_5",
                "seed": cfg["split_seed"],
                "before_outcomes": True,
            }
            or study["range_terminal_handling"]
            != {"root_value_policy": cfg["root_value_policy"], "draw_policy": cfg["draw_policy"]}
        ):
            raise ValueError("selected human plan/partition/mapping is unresolved or incompatible")
    return cfg
