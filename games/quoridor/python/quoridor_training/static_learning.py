"""Finite static-teacher recipe and weighted metrics for the maintained trainer.

This module does not contain another optimizer/fit loop or source classifier.
"""

import copy
import gzip
import hashlib
import io
import json
import math
import sys

import numpy as np


def observation_index_sha(indices):
    return hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest()


def read_initial_observation(ref, corpus, expected, train_indices, validation_indices):
    """Reuse only an actually completed, same-identity zero-update observation."""
    from .common import bound_file_bytes

    saved = json.loads(bound_file_bytes(ref, 131072))
    same = {
        "input_classes": corpus.input_ref,
        "teacher_values": corpus.binding["teacher_values"],
        "teacher": corpus.binding["teacher"],
        "common_initial": expected["common_initial"],
        "initial_weights_sha": expected["initial_weights_sha"],
        "scale_artifact_sha": expected["scale_artifact_sha"],
        "fit_config_sha": expected["fit_config_sha"],
        "train_index_sha": observation_index_sha(train_indices),
        "validation_index_sha": observation_index_sha(validation_indices),
    }
    if saved.get("schema") != "quoridor-static-initial-observation-v1" or any(
        saved.get(key) != value for key, value in same.items()
    ):
        raise ValueError("same INITIAL weights/scale/config/teacher/input/ordered-panel binding")
    status = json.loads(bound_file_bytes(saved["original_run_status"], 65536))
    common = json.loads(bound_file_bytes(saved["common_initial"], 65536))
    original_config = json.loads(bound_file_bytes(saved["original_fit_config"], 65536))
    source = json.loads(bound_file_bytes(saved["original_source"], 131072))
    bank = json.loads(bound_file_bytes(saved["teacher_values"], 131072))
    panel = json.loads(bound_file_bytes(saved["original_diagnostic_subsets"], 2097152))
    if (
        common["input_classes"] != corpus.input_ref
        or common["initial_weights_sha"] != expected["initial_weights_sha"]
        or common["scale"]["sha256"] != expected["scale_artifact_sha"]
        or common["initializer_seed"] != common["initializer"]["training"]["seed"]
        or saved["original_fit_config"]["sha256"] != expected["fit_config_sha"]
        or original_config["training"]["device"] != "cuda"
        or original_config["training"]["target"] != "static_teacher"
        or original_config["model"]["distance_a"] != 0
        or original_config["model"]["distance_b"] != 0
        or not source.get("files")
        or bank["status"] != "COMPLETE"
        or bank["teachers"][saved["teacher"]]["model"] != saved["teacher_model"]
        or panel["dataset_sha"] != corpus.binding["dataset_sha"]
        or observation_index_sha(panel["train"]) != same["train_index_sha"]
    ):
        raise ValueError("original successful INITIAL source/model/FP32 recipe binding")
    weights = bound_file_bytes(saved["original_initial_weights"], 49284)
    if hashlib.sha256(weights).hexdigest() != expected["initial_weights_sha"]:
        raise ValueError("original measured weights differ from common fresh INITIAL")
    with gzip.GzipFile(
        fileobj=io.BytesIO(bound_file_bytes(saved["original_curves"], 131072))
    ) as archive:
        raw = archive.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("bounded original INITIAL control rows")
    records = [json.loads(line) for line in raw.splitlines()]
    point = saved["observation"]
    if not records or any(record != point for record in records):
        raise ValueError("one original INITIAL observation; duplicate publications only")
    if (
        any(status.get(field) != 0 for field in ("step", "training_seen", "attempted_step"))
        or status.get("model_state_status") != "LAST_COMPLETED_UPDATE"
    ):
        raise ValueError("reuse is INITIAL only, never resume a completed/partial optimizer")
    if (
        point.get("step") != 0
        or point.get("training_seen") != 0
        or point.get("kind") != "full_selector"
    ):
        raise ValueError("original full-selector INITIAL only")
    metrics = {scope: copy.deepcopy(point[scope]) for scope in ("train", "validation")}
    for scope, indices in (("train", train_indices), ("validation", validation_indices)):
        result = metrics[scope]
        if (
            result.get("group_kind") != "exact trueLR input class"
            or result.get("rows") != len(indices)
            or not isinstance(result.get("actual_logical_rows"), int)
            or result["actual_logical_rows"] <= 0
            or not math.isfinite(result["target_mse"])
            or result["target_mse"] < 0
        ):
            raise ValueError("actual original weighted row/class scope and completed rows")
    prior = sum(result["actual_logical_rows"] for result in metrics.values())
    counters = dict(train=0, full_selector=prior, diagnostic=0, onnx=0)
    if (
        status["samples"] != prior
        or status["forward_rows_completed"] != counters
        or status["forward_rows_conservative"] != counters
        or point["samples"] != prior
        or point["validation_forward_rows"] != metrics["validation"]["actual_logical_rows"]
    ):
        raise ValueError("original INITIAL actual successful row ledger differs")
    return dict(
        metrics=metrics,
        index_sha={scope: same[scope + "_index_sha"] for scope in metrics},
        prior_logical_rows=prior,
        used_scopes=set(),
        receipt=ref,
    )


def reused_initial_measurement(saved, indices, kind):
    """Return the retained aggregate; no new forward or old-work re-charge."""
    digest = observation_index_sha(indices)
    matches = [scope for scope, value in saved["index_sha"].items() if value == digest]
    if kind != "full_selector" or len(matches) != 1 or matches[0] in saved["used_scopes"]:
        raise ValueError("retained INITIAL scope must match once before any new update")
    scope = matches[0]
    saved["used_scopes"].add(scope)
    result = copy.deepcopy(saved["metrics"][scope])
    result["reused_successful_logical_rows"] = result["actual_logical_rows"]
    result["actual_logical_rows"] = 0
    result["retained_INITIAL_receipt"] = saved["receipt"]
    return result


def static_settings(cfg, train_rows=None, validation_rows=None):
    """Resolve the implemented static fit conditions from one normal run config."""
    static = cfg["static_teacher"]
    training, evaluation = cfg["training"], cfg["evaluation"]
    positive = ("maximum_training_draws",)
    nonnegative = (
        "minimum_training_draws",
        "minimum_floor_training_draws",
        "overfit_observations",
        "initializer_seed",
        "panel_seed",
    )
    for name in positive + nonnegative:
        value = static[name]
        if type(value) is not int or value < (1 if name in positive else 0):
            raise ValueError("invalid static integer: " + name)
    for name in (
        "overfit_validation_absolute",
        "overfit_validation_relative",
        "overfit_training_absolute",
        "overfit_training_relative",
        "progress_absolute",
        "progress_relative",
    ):
        value = static[name]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid static finite threshold: " + name)
    if any(type(n) is not int or n <= 0 for n in (train_rows, validation_rows) if n is not None):
        raise ValueError("nonempty actual retained T/V required")
    maximum_steps = math.ceil(static["maximum_training_draws"] / training["batch_size"])
    if training["steps"] != maximum_steps:
        raise ValueError("static steps must match the configured sole final draw tail")
    if (
        static["minimum_training_draws"] > static["maximum_training_draws"]
        or static["minimum_floor_training_draws"] > static["maximum_training_draws"]
    ):
        raise ValueError("static minimum exposure exceeds maximum draws")
    points = evaluation["checkpoints"]
    state_points = static["state_checkpoint_steps"]
    if (
        not isinstance(points, list)
        or not points
        or points != sorted(set(points))
        or points[0] != 0
        or points[-1] != maximum_steps
        or any(type(p) is not int or not 0 <= p <= maximum_steps for p in points)
        or not isinstance(state_points, list)
        or state_points != sorted(set(state_points))
        or any(type(p) is not int or p <= 0 or p not in points for p in state_points)
    ):
        raise ValueError("static observation/state checkpoints must be explicit matching steps")
    optimizer = cfg["optimizer"]
    betas = optimizer.get("betas")
    if (
        optimizer["name"] != "adam"
        or not isinstance(betas, (list, tuple))
        or len(betas) != 2
        or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v < 1 for v in betas)
        or type(optimizer.get("eps")) not in (int, float)
        or not math.isfinite(optimizer["eps"])
        or optimizer["eps"] <= 0
        or training["sampling"] != "row"
        or training["loss_weighting"] != "row"
        or training["target"] != "static_teacher"
        or training["supply_workers"] != 0
        or training["scheduler"] not in ("none", "plateau")
        or evaluation["monitor"] != "row"
        or evaluation["early_stopping_unit"] != "observation"
        or evaluation["early_stopping_patience"] <= 0
        or evaluation["full_train"]
        or evaluation["diagnostic_rows"] <= 0
        or cfg["artifacts"]["save_scheduled"]
        or cfg["artifacts"]["mode"] != "native"
        or type(cfg["limits"]["samples"]) is not int
        or cfg["limits"]["samples"] <= 0
    ):
        raise ValueError("implemented static Adam/row/full-V/native conditions required")
    # This changes training conditions, not the selected native model/feature math.
    model = cfg["model"]
    if (
        model["architecture"] != "distance_residual"
        or model["distance_a"] != 0
        or model["distance_b"] != 0
        or model["transformer_width"] != 32
        or model["hidden_width"] != 32
        or model["dropout"] != 0
    ):
        raise ValueError("static FT32/H32/FP32 output-bypassOFF model is unchanged")
    result = dict(
        maximum_updates=maximum_steps,
        maximum_training_draws=static["maximum_training_draws"],
        minimum_training_draws=static["minimum_training_draws"],
        minimum_floor_training_draws=static["minimum_floor_training_draws"],
        floor_stale_observations=evaluation["early_stopping_patience"],
        initial_lr=optimizer["lr"],
        decay_factor=training["lr_decay_factor"],
        decay_patience=training["lr_decay_patience"],
        floor=training["min_lr"],
        delta_absolute=evaluation["min_delta"],
        delta_relative=evaluation["min_delta_relative"],
        overfit_observations=static["overfit_observations"],
        overfit_validation_absolute=static["overfit_validation_absolute"],
        overfit_validation_relative=static["overfit_validation_relative"],
        overfit_training_absolute=static["overfit_training_absolute"],
        overfit_training_relative=static["overfit_training_relative"],
        progress_absolute=static["progress_absolute"],
        progress_relative=static["progress_relative"],
        state_checkpoints={step: index for index, step in enumerate(state_points, 1)},
        panel_rows=min(evaluation["diagnostic_rows"], train_rows)
        if train_rows is not None
        else evaluation["diagnostic_rows"],
        panel_seed=static["panel_seed"],
        initializer_seed=static["initializer_seed"],
        logical_quota=cfg["limits"]["samples"],
    )
    result["config_sha256"] = hashlib.sha256(
        json.dumps(cfg, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    return result


def adequate_learning(initial_panel, observed_panel, parameter_changed, settings):
    return bool(
        parameter_changed
        and initial_panel - observed_panel
        >= max(settings["progress_absolute"], settings["progress_relative"] * initial_panel)
    )


def static_checkpoint_ref(path):
    """Bind a completed small continuation checkpoint/export for its next block."""
    from pathlib import Path
    import stat

    path = Path(path).resolve()
    data = path.read_bytes()
    return dict(
        path=str(path),
        sha256=hashlib.sha256(data).hexdigest(),
        bytes=len(data),
        mode=format(stat.S_IMODE(path.stat().st_mode), "04o"),
    )


def restore_static_exposure(corpus, entry):
    """Restore only the bound latest rolling new-phase counter, not the historical BEST array."""
    from .common import bound_file_bytes

    count = corpus.executed_orientations
    data = bound_file_bytes(entry["ref"], count.nbytes)
    values = np.frombuffer(data, dtype="<u4")
    if (
        len(data) != count.nbytes
        or entry["shape"] != list(count.shape)
        or int(values.sum(dtype=np.uint64)) != entry["rows"]
    ):
        raise ValueError("matching latest rolling orientation counter required")
    if corpus.pending_training is not None or corpus.executed_rows:
        raise ValueError("restore exposure before any new training supply")
    count[:] = values.reshape(count.shape)
    corpus.executed_rows = entry["rows"]
    return copy.deepcopy(entry)


class StaticContinuation:
    """The concrete lowered-LR state at completed teacher-own full-V boundaries."""

    def __init__(self, settings, baseline, *, state=None):
        self.settings = copy.deepcopy(settings)
        if any(
            not math.isfinite(float(baseline[scope]["target_mse"]))
            or baseline[scope]["target_mse"] < 0
            for scope in ("train", "validation")
        ):
            raise ValueError("finite nonnegative selected full-V/Tpanel baseline required")
        self.state = (
            copy.deepcopy(state)
            if state is not None
            else dict(
                lr=settings["initial_lr"],
                settings_sha256=settings["config_sha256"],
                significant_best=float(baseline["validation"]["target_mse"]),
                strict_best=float(baseline["validation"]["target_mse"]),
                strict_best_panel=float(baseline["train"]["target_mse"]),
                stale_at_lr=0,
                floor_entry_draws=None,
                floor_first_update=None,
                floor_draws=0,
                floor_stale=0,
                phase_draws=0,
                observations=0,
                overfit_stale=0,
                verdict="NOT_CONVERGED/NEEDED_WORK",
            )
        )
        if (
            self.state.get("settings_sha256") != settings["config_sha256"]
            or not settings["floor"] <= self.state["lr"] <= settings["initial_lr"]
        ):
            raise ValueError("continuation LR state outside fixed range")

    def observe(self, loss, panel, draws):
        """Called once after a genuinely new full-V evaluation, never for a reused baseline."""
        s = self.state
        if not all(math.isfinite(value) for value in (loss, panel)) or min(loss, panel) < 0:
            raise ValueError("nonfinite/negative continuation full-V or Tpanel")
        if draws <= s["phase_draws"]:
            raise ValueError("one new completed full-V observation, never repeat prior draws")
        used_lr = s["lr"]
        if used_lr == self.settings["floor"]:
            if s["floor_entry_draws"] is None:
                s["floor_entry_draws"] = s["phase_draws"]
            s["floor_draws"] += draws - s["phase_draws"]
        delta = max(
            self.settings["delta_absolute"], self.settings["delta_relative"] * s["significant_best"]
        )
        significant = loss < s["significant_best"] - delta
        strict = loss < s["strict_best"]
        if strict:
            s["strict_best"] = loss
            s["strict_best_panel"] = panel
        if significant:
            s["significant_best"] = loss
            s["stale_at_lr"] = s["floor_stale"] = 0
        else:
            s["stale_at_lr"] += 1
            if used_lr == self.settings["floor"]:
                s["floor_stale"] += 1
        if used_lr > self.settings["floor"] and s["stale_at_lr"] > self.settings["decay_patience"]:
            s["lr"] = max(self.settings["floor"], used_lr * self.settings["decay_factor"])
            s["stale_at_lr"] = 0
        divergence = (
            used_lr == self.settings["floor"]
            and loss
            >= s["strict_best"]
            + max(
                self.settings["overfit_validation_absolute"],
                self.settings["overfit_validation_relative"] * s["strict_best"],
            )
            and panel
            <= s["strict_best_panel"]
            - max(
                self.settings["overfit_training_absolute"],
                self.settings["overfit_training_relative"] * s["strict_best_panel"],
            )
        )
        s["overfit_stale"] = s["overfit_stale"] + 1 if divergence else 0
        if (
            s["floor_draws"] >= self.settings["minimum_floor_training_draws"]
            and self.settings["overfit_observations"] > 0
            and s["overfit_stale"] >= self.settings["overfit_observations"]
        ):
            s["verdict"] = "OVERFIT_STOP/NEEDED_WORK"
        if (
            s["verdict"] == "NOT_CONVERGED/NEEDED_WORK"
            and s["floor_draws"] >= self.settings["minimum_floor_training_draws"]
            and s["floor_stale"] >= self.settings["floor_stale_observations"]
        ):
            s["verdict"] = "PRACTICAL_V_PLATEAU"
        s["phase_draws"] = draws
        s["observations"] += 1
        return dict(
            strict_improved=strict,
            significant_improved=significant,
            significant_delta=delta,
            update_lr_used=used_lr,
            next_lr=s["lr"],
            stop=s["verdict"] != "NOT_CONVERGED/NEEDED_WORK",
            **copy.deepcopy(s),
        )


def read_static_continuation(control, cfg, corpus, statistics, train_panel, validation):
    """Load a bound selected checkpoint on CPU, never construct or evaluate a model."""
    from .common import bound_file_bytes, PARAMETER_SHAPES

    import torch

    if control.get("schema") != "quoridor-static-continuation-input-v1":
        raise ValueError("explicit static continuation input schema")
    mode = control["optimizer_mode"]
    settings = static_settings(cfg, corpus.counts["train"], corpus.counts["validation"])
    if (
        mode != "matching"
        or cfg["training"]["scheduler"] != "plateau"
        or cfg["training"]["warmup_steps"]
    ):
        raise ValueError("matching continuation requires plateau and no reset/warmup")
    identity = dict(
        input_classes=corpus.input_ref,
        teacher_values=corpus.binding["teacher_values"],
        teacher=corpus.binding["teacher"],
        dataset_sha=corpus.binding["dataset_sha"],
        train_panel_sha256=observation_index_sha(train_panel),
        validation_index_sha256=observation_index_sha(validation),
    )
    if len(train_panel) != settings["panel_rows"] or len(validation) != corpus.counts["validation"]:
        raise ValueError("fixed Tpanel and whole weighted V are required")
    if any(control.get(key) != value for key, value in identity.items()):
        raise ValueError("continuation teacher/input/fullV/panel identity differs")
    data = bound_file_bytes(control["checkpoint"], 1048576)
    checkpoint = torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)
    if (
        checkpoint["model_config"] != cfg["model"]
        or checkpoint["scale"] != statistics
        or checkpoint["target"] != "static_teacher"
        or checkpoint["dataset_sha"] != corpus.binding["dataset_sha"]
        or set(checkpoint["model"]) != set(PARAMETER_SHAPES)
    ):
        raise ValueError("selected checkpoint model/scale/teacher differs")
    digest = hashlib.sha256()
    for name, shape in PARAMETER_SHAPES.items():
        value = checkpoint["model"][name]
        if (
            tuple(value.shape) != shape
            or value.dtype != torch.float32
            or not torch.isfinite(value).all()
        ):
            raise ValueError("selected continuation tensor shape/dtype/finite")
        digest.update(value.numpy().astype("<f4").tobytes())
    weights = bound_file_bytes(control["weights"], 49284)
    if digest.hexdigest() != hashlib.sha256(weights).hexdigest():
        raise ValueError("selected checkpoint differs from its exact native export")
    prior = checkpoint.get("static_continuation")
    if prior is not None:
        if (
            prior["identity"] != identity
            or not prior["evaluation_complete_for_position"]
            or prior["resolved_config_sha256"] != settings["config_sha256"]
        ):
            raise ValueError("next block requires a same-identity completed fullV checkpoint")
        baseline = prior["last_observation"]
        if (
            baseline["step"] != checkpoint["position"]["step"]
            or baseline["training_seen"] != checkpoint["position"]["training_seen"]
            or prior["policy"]["phase_draws"] != prior["phase_draws"]
            or prior["policy"]["verdict"] != "NOT_CONVERGED/NEEDED_WORK"
        ):
            raise ValueError("next block must not repeat an evaluation or resume a terminal policy")
        old_executed = prior["old_executed"]
        previous_draws, previous_steps, previous_rows = (
            prior[key] for key in ("phase_draws", "phase_steps", "phase_logical_rows")
        )
        origin = prior["origin_position"]
        policy_state = prior["policy"]
        selected_best = prior["selected_best"] or dict(
            checkpoint=control["checkpoint"],
            weights=control["weights"],
            loss=baseline["validation"]["target_mse"],
            position=checkpoint["position"],
        )
        if prior["optimizer_mode"] != mode:
            raise ValueError("optimizer mode changed across blocks")
        if prior.get("exposure") is None or prior["exposure"]["rows"] != prior["phase_draws"]:
            raise ValueError("matching rolling orientation counter required for next block")
    else:
        source = control["baseline"]
        producer = json.loads(bound_file_bytes(source["producer_result"], 1048576))
        arm = producer["arms"][corpus.binding["teacher"]]
        frozen = json.loads(bound_file_bytes(source["freeze"], 65536))
        with gzip.GzipFile(
            fileobj=io.BytesIO(bound_file_bytes(source["cache_binding"], 65536))
        ) as archive:
            original_binding_bytes = archive.read(131073)
        if len(original_binding_bytes) > 131072:
            raise ValueError("bounded original teacher/cache binding")
        original_binding = json.loads(original_binding_bytes)
        if (
            producer["status"] != "TWO_ORIGINAL_FITS_COMPLETE_FIXED_HORIZON_NOT_CONVERGED"
            or arm["curves"] != source["curves"]
            or arm["status"] != source["run_status"]
            or arm["freeze"] != source["freeze"]
            or arm["models"]["best"]["weights"] != control["weights"]
            or frozen["artifacts_sha256"]["best.pt"] != control["checkpoint"]["sha256"]
            or frozen["artifacts_sha256"]["cache-binding.json.gz"]
            != source["cache_binding"]["sha256"]
            or frozen["weights_sha"] != control["weights"]["sha256"]
            or frozen["dataset_sha"] != checkpoint["dataset_sha"]
            or frozen["best_step"] != checkpoint["position"]["step"]
            or frozen["selected_exposure"]["training_seen"]
            != checkpoint["position"]["training_seen"]
            or original_binding != corpus.binding
        ):
            raise ValueError(
                "selected BEST/producer/teacher-bank/dataset/metric custody tuple differs"
            )
        old_status = json.loads(bound_file_bytes(source["run_status"], 65536))
        panel = json.loads(bound_file_bytes(source["diagnostic_subsets"], 2097152))
        if (
            observation_index_sha(panel["train"]) != identity["train_panel_sha256"]
            or panel["dataset_sha"] != corpus.binding["dataset_sha"]
        ):
            raise ValueError("selected old diagnostic panel differs")
        with gzip.GzipFile(
            fileobj=io.BytesIO(bound_file_bytes(source["curves"], 262144))
        ) as archive:
            raw = archive.read(4194305)
        if len(raw) > 4194304:
            raise ValueError("bounded old selected curve metadata")
        matches = [json.loads(line) for line in raw.splitlines() if line]
        matches = [row for row in matches if row["step"] == checkpoint["position"]["step"]]
        if len(matches) != 1:
            raise ValueError("one exact selected checkpoint fullV observation required")
        baseline = matches[0]
        if (
            baseline["training_seen"] != checkpoint["position"]["training_seen"]
            or baseline["validation"]["rows"] != corpus.counts["validation"]
            or baseline["train"]["rows"] != len(train_panel)
            or baseline["validation"].get("group_kind") != "exact trueLR input class"
            or baseline["validation"].get("actual_logical_rows", 0) <= 0
            or baseline["validation"]["target_mse"] != frozen["best_validation_mse"]
            or old_status["status"] != "COMPLETED"
            or old_status["model_state_status"] != "LAST_COMPLETED_UPDATE"
        ):
            raise ValueError("actual selected fullV/panel scope and historical status required")
        old_executed = dict(
            logical_rows=old_status["samples"],
            draws=old_status["training_seen"],
            steps=old_status["step"],
        )
        previous_draws = previous_steps = previous_rows = 0
        origin = checkpoint["position"]
        policy_state = None
        selected_best = dict(
            checkpoint=control["checkpoint"],
            weights=control["weights"],
            loss=baseline["validation"]["target_mse"],
            position=origin,
        )
    if (
        previous_steps >= settings["maximum_updates"]
        or previous_draws >= settings["maximum_training_draws"]
        or previous_rows >= settings["logical_quota"]
    ):
        raise ValueError("completed or exhausted continuation phase must not be resumed")
    if (previous_steps, previous_rows) != (
        control.get("phase_steps", 0),
        control.get("phase_rows", 0),
    ):
        raise ValueError("declared remaining phase/quota differs from actual saved state")
    matching = "optimizer" in checkpoint and "static_RNG" in checkpoint
    if mode == "matching":
        if not matching:
            raise ValueError(
                "matching Adam/index/reflection RNG missing; no implicit fresh fallback"
            )
        states = checkpoint["optimizer"]["state"]
        branch_steps = origin["step"] + previous_steps
        groups = checkpoint["optimizer"]["param_groups"]
        if (
            len(states) != 6
            or len(groups) != 1
            or groups[0]["params"] != list(range(6))
            or set(states) != set(range(6))
            or any(float(state["step"]) != branch_steps for state in states.values())
            or tuple(groups[0]["betas"]) != tuple(cfg["optimizer"]["betas"])
            or groups[0]["eps"] != cfg["optimizer"]["eps"]
            or groups[0]["weight_decay"] != cfg["optimizer"]["weight_decay"]
            or set(checkpoint["static_RNG"])
            != {"index_torch_state", "reflection_numpy_state", "ordered_index_mask_sha256"}
        ):
            raise ValueError("matching Adam/RNG/selected branch position required")
        for state, shape in zip(
            (states[index] for index in range(6)), PARAMETER_SHAPES.values(), strict=True
        ):
            for name in ("exp_avg", "exp_avg_sq"):
                value = state[name]
                if (
                    tuple(value.shape) != shape
                    or value.dtype != torch.float32
                    or not torch.isfinite(value).all()
                ):
                    raise ValueError("matching finite FP32 Adam moments required")
    best_data = (
        checkpoint
        if selected_best["checkpoint"] == control["checkpoint"]
        else torch.load(
            io.BytesIO(bound_file_bytes(selected_best["checkpoint"], 1048576)),
            map_location="cpu",
            weights_only=True,
        )
    )
    best_digest = hashlib.sha256(
        b"".join(
            best_data["model"][name].numpy().astype("<f4").tobytes() for name in PARAMETER_SHAPES
        )
    ).hexdigest()
    if (
        best_data["dataset_sha"] != corpus.binding["dataset_sha"]
        or best_data["model_config"] != cfg["model"]
        or best_data["scale"] != statistics
        or best_digest
        != hashlib.sha256(bound_file_bytes(selected_best["weights"], 49284)).hexdigest()
    ):
        raise ValueError("selected BEST checkpoint/export differs from its owning state")
    return dict(
        checkpoint=checkpoint,
        baseline=baseline,
        identity=identity,
        optimizer_mode=mode,
        old_executed=old_executed,
        origin_position=origin,
        previous_draws=previous_draws,
        previous_steps=previous_steps,
        previous_rows=previous_rows,
        selected_best=selected_best,
        selected_best_checkpoint=best_data,
        policy_state=policy_state,
        settings=settings,
    )


class StaticMeasurements:
    """Same predictions produce row/class/stock/sign/zero/saturation statistics."""

    def __init__(self, pairs):
        self.pairs = pairs
        self.group_error = np.zeros(len(pairs), dtype=np.float64)
        self.group_weight = np.zeros(len(pairs), dtype=np.float64)
        self.stats = {}

    def add(self, pair, prediction, target, weight, stock):
        prediction = np.asarray(prediction, dtype=np.float32)
        target = np.asarray(target, dtype=np.float32)
        weight = np.asarray(weight, dtype=np.float64)
        if (
            prediction.shape != target.shape
            or weight.shape != target.shape
            or not np.isfinite(prediction).all()
            or not np.isfinite(target).all()
            or not np.isfinite(weight).all()
            or np.any(weight <= 0)
        ):
            raise ValueError("finite actual static prediction/target and positive weights")
        error = prediction.astype(np.float64) - target.astype(np.float64)
        np.add.at(self.group_error, pair, weight * error**2)
        np.add.at(self.group_weight, pair, weight)
        for name, mask in [
            ("all", np.ones(len(pair), dtype=bool)),
            ("stock16..20", (stock >= 16) & (stock <= 20)),
            ("stock8..15", (stock >= 8) & (stock <= 15)),
            ("stock1..7", (stock >= 1) & (stock <= 7)),
            ("stock0", stock == 0),
        ]:
            w = weight[mask]
            y = target[mask]
            p = prediction[mask]
            e = error[mask]
            s = self.stats.setdefault(
                name,
                dict(
                    rows=0.0,
                    sse=0.0,
                    absolute=0.0,
                    bias=0.0,
                    target_sum=0.0,
                    target_square_sum=0.0,
                    target_histogram10=[0.0] * 10,
                    sign_rows=0.0,
                    sign_correct=0.0,
                    target_zero_rows=0.0,
                    target_zero_abs=0.0,
                    target_saturated90=0.0,
                    target_saturated99=0.0,
                    predicted_saturated90=0.0,
                    predicted_saturated99=0.0,
                ),
            )
            for field, value in dict(
                rows=w.sum(),
                sse=np.dot(w, e**2),
                absolute=np.dot(w, abs(e)),
                bias=np.dot(w, e),
                target_sum=np.dot(w, y),
                target_square_sum=np.dot(w, y.astype(np.float64) ** 2),
                sign_rows=w[y != 0].sum(),
                sign_correct=w[p * y > 0].sum(),
                target_zero_rows=w[y == 0].sum(),
                target_zero_abs=np.dot(w[y == 0], abs(p[y == 0])),
                target_saturated90=w[abs(y) >= 0.9].sum(),
                target_saturated99=w[abs(y) >= 0.99].sum(),
                predicted_saturated90=w[abs(p) >= 0.9].sum(),
                predicted_saturated99=w[abs(p) >= 0.99].sum(),
            ).items():
                s[field] += float(value)
            histogram, _ = np.histogram(y, bins=np.linspace(-1.0, 1.0, 11), weights=w)
            s["target_histogram10"] = [
                previous + float(value)
                for previous, value in zip(s["target_histogram10"], histogram)
            ]

    def result(self):
        from .public_features import input_records

        stock = input_records(self.pairs["key"])["geometry"]["stocks"].sum(axis=1)
        out = {}
        for name, s in self.stats.items():
            n = s["rows"]
            selected = self.group_weight > 0
            if name != "all":
                lo, hi = {
                    "stock16..20": (16, 20),
                    "stock8..15": (8, 15),
                    "stock1..7": (1, 7),
                    "stock0": (0, 0),
                }[name]
                selected &= (stock >= lo) & (stock <= hi)
            report = {
                **s,
                "target_mse": s["sse"] / n if n else None,
                "target_mae": s["absolute"] / n if n else None,
                "target_mean": s["target_sum"] / n if n else None,
                "target_second_moment": s["target_square_sum"] / n if n else None,
                "target_histogram_edges": np.linspace(-1.0, 1.0, 11).tolist(),
                "input_classes": int(selected.sum()),
                "class_macro_mse": float(
                    np.mean(self.group_error[selected] / self.group_weight[selected])
                )
                if selected.any()
                else None,
                "decisive_sign_accuracy": s["sign_correct"] / s["sign_rows"]
                if s["sign_rows"]
                else None,
                "target_zero_mean_absolute_prediction": s["target_zero_abs"] / s["target_zero_rows"]
                if s["target_zero_rows"]
                else None,
            }
            for key in [
                "target_saturated90",
                "target_saturated99",
                "predicted_saturated90",
                "predicted_saturated99",
            ]:
                report[key + "_fraction"] = s[key] / n if n else None
            out[name] = report
        result = out.pop("all")
        result.update(
            stock_strata=out,
            weighting="original observation multiplicity, equal actual canonical/trueLR orientations",
            teacher_zero="static scalar zero; never a Draw0 outcome",
            independent_games="UNKNOWN",
            group_kind="exact trueLR input class",
        )
        return result


def prepare_common(cache, output, config_path):
    """One actual constructor/export, no forward; caller owns normal resources."""
    from pathlib import Path
    from .train import configure_framework, build_model, export, write, sha
    from .cache import load
    from .common import resolve_config

    cfg = resolve_config(config_path)
    corpus = load(cache)
    try:
        settings = static_settings(cfg, corpus.counts["train"], corpus.counts["validation"])
        statistics = corpus.statistics()
        init = copy.deepcopy(cfg)
        init["training"].update(seed=settings["initializer_seed"], device="cpu")
        configure_framework(init)
        model = build_model(init["model"], statistics)
        output = Path(output)
        output.mkdir(exist_ok=False)
        export(model, init, statistics, {"a": 0.0, "b": 0.0}, output / "initial-model")
        write(output / "scale.json", statistics)
        corpus.verify_binding()
        from .public_static_prepare import file_ref

        result = dict(
            schema="quoridor-static-common-initial-v1",
            initial_weights=file_ref(output / "initial-model/weights.f32"),
            input_classes=corpus.input_ref,
            initial_weights_sha=sha(output / "initial-model/weights.f32"),
            initializer_seed=settings["initializer_seed"],
            model_forwards=0,
            scale=dict(
                path=str((output / "scale.json").resolve()), sha256=sha(output / "scale.json")
            ),
            initializer=init,
            normalizer="T-only original multiplicity, correctLR distance invariant",
        )
        write(output / "result.json", result)
        return result
    finally:
        corpus.close(primary_error=sys.exception())


def prepare_fits(config):
    """Bind actual completed labels and one fresh initializer to normal train."""
    import json
    from pathlib import Path
    from .common import bound_file_bytes
    from .cache import load
    from .public_static_prepare import file_ref
    from quoridor_runtime.snapshot import write_json

    bank_ref = config["teacher_values"]
    bank = json.loads(bound_file_bytes(bank_ref, 131072))
    if bank["schema"] != "quoridor-public-static-teacher-values-v1" or bank["status"] != "COMPLETE":
        raise ValueError("actual completed two-teacher bank required")
    input_ref = bank["input_classes"]
    inputs = json.loads(bound_file_bytes(input_ref, 131072))
    if inputs["status"] != "COMPLETE":
        raise ValueError("actual complete same input bank required")
    r, v = inputs["counts"]["train"], inputs["counts"]["validation"]
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("fit preparation owns partial controls; no implicit retry\n")
    from .common import resolve_config

    cfg = resolve_config(json.loads(bound_file_bytes(config["fit_config"], 65536)))
    static_settings(cfg, r, v)
    fit_config = output / "fit-config.json"
    write_json(fit_config, cfg)
    caches = {}
    for teacher in ("S", "C"):
        cache = output / ("cache-" + teacher)
        cache.mkdir()
        write_json(
            cache / "cache.json",
            dict(
                schema="quoridor-public-static-teacher-v1",
                input_classes=input_ref,
                teacher_values=bank_ref,
                teacher=teacher,
            ),
        )
        caches[teacher] = cache
    common_directory = output / "common-initial"
    common = prepare_common(caches["S"], common_directory, fit_config)
    common_ref = file_ref(common_directory / "result.json")
    arms = {}
    for teacher in ("S", "C"):
        corpus = load(caches[teacher])
        try:
            if corpus.input_ref != input_ref or corpus.counts != {"train": r, "validation": v}:
                raise ValueError("same retained multiplicity and shared partition")
            # This is a descriptive T-only constant. It is not a target transform.
            indices = np.arange(r, dtype=np.int64)
            constant = float(np.mean(corpus.labels[indices, 0], dtype=np.float64))
            statistics = corpus.statistics()
            scale = json.loads(bound_file_bytes(file_ref(common["scale"]["path"]), 65536))
            if statistics != scale:
                raise ValueError("teacher-independent T-only scale differs")
            constant_path = output / ("constant-" + teacher + ".json")
            write_json(
                constant_path,
                dict(
                    row_mean_constant=constant,
                    partition="train",
                    teacher=teacher,
                    original_observations=r,
                ),
            )
            binding = dict(
                cache_manifest_sha=corpus.binding["dataset_sha"],
                scale_artifact=common["scale"]["path"],
                scale_artifact_sha=common["scale"]["sha256"],
                constant_artifact=str(constant_path),
                constant_artifact_sha=file_ref(constant_path)["sha256"],
                fit_config_sha=file_ref(fit_config)["sha256"],
                common_initial=common_ref,
                initial_weights=common["initial_weights"],
                initial_weights_sha=common["initial_weights_sha"],
            )
            path = output / ("input-binding-" + teacher + ".json")
            write_json(path, binding)
            corpus.verify_binding()
            arms[teacher] = dict(
                cache=str(caches[teacher]),
                input_binding=file_ref(path),
                config=file_ref(fit_config),
                original_train=r,
                original_validation=v,
                fit_not_entered=True,
            )
        finally:
            corpus.close(primary_error=sys.exception())
    bound_file_bytes(bank_ref, 131072)
    bound_file_bytes(input_ref, 131072)
    result = dict(
        schema="quoridor-static-paired-fit-controls-v1",
        input_classes=input_ref,
        teacher_values=bank_ref,
        common_initial=common_ref,
        arms=arms,
        prepare_head_rows=0,
        initial_model_reused=True,
        scope="normal train controls only; no fit/numerical success inferred",
    )
    write_json(output / "result.json", result)
    marker.unlink()
    return dict(result=file_ref(output / "result.json"), fit_entered=False)


def prepare_policy_fit(config):
    """Materialize normal train inputs only after an actual joint bank exists."""
    from pathlib import Path
    from .common import bound_file_bytes, resolve_config
    from .scaled_model import validate_statistics
    from .static_public_corpus import StaticTeacherCorpus
    from .public_static_prepare import file_ref
    from quoridor_runtime.snapshot import write_json
    from .policy_value_training import settings

    if set(config) != {
        "cache",
        "fit_config",
        "initial_model",
        "initial_policy",
        "core_library",
        "restart",
        "output",
    }:
        raise ValueError("actual joint cache/config/initializer and normal output required")
    manifest = json.loads(bound_file_bytes(config["cache"], 131072))
    if manifest["schema"] != "quoridor-public-static-teacher-v1":
        raise ValueError("actual published static joint cache")
    cfg = resolve_config(json.loads(bound_file_bytes(config["fit_config"], 131072)))
    settings(cfg)
    descriptor = json.loads(bound_file_bytes(config["initial_model"]["descriptor"], 65536))
    statistics = validate_statistics(descriptor)
    if descriptor["weights_SHA"] != config["initial_model"]["weights"]["sha256"]:
        raise ValueError("actual initializer descriptor/weights differ")
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("actual joint fit inputs not completely prepared\n")
    corpus = StaticTeacherCorpus(Path(config["cache"]["path"]).parent)
    primary = None
    try:
        if (
            corpus.binding["dataset_sha"] != config["cache"]["sha256"]
            or not corpus.policy_value
            or corpus.policy_temperature != cfg["policy_value"]["temperature"]
        ):
            raise ValueError("same actual joint cache/value/policy configuration required")
        static_settings(cfg, corpus.counts["train"], corpus.counts["validation"])
        train_indices = np.flatnonzero(corpus.splits == 0)
        if not len(train_indices) or not corpus.counts["validation"]:
            raise ValueError("nonempty unsealed original T/V classes required")
        constant = float(np.mean(corpus.labels[train_indices, 0], dtype=np.float64))
        write_json(output / "config.json", cfg)
        write_json(output / "scale.json", statistics)
        write_json(
            output / "constant.json",
            {
                "row_mean_constant": constant,
                "binding": {
                    "dataset_sha": corpus.binding["dataset_sha"],
                    "partition": "train",
                    "teacher": "same-forward C STM value, not outcome z",
                },
            },
        )
        binding = {
            "cache_manifest_sha": corpus.binding["dataset_sha"],
            "fit_config_sha": file_ref(output / "config.json")["sha256"],
            "scale_artifact": str((output / "scale.json").resolve()),
            "scale_artifact_sha": file_ref(output / "scale.json")["sha256"],
            "constant_artifact": str((output / "constant.json").resolve()),
            "constant_artifact_sha": file_ref(output / "constant.json")["sha256"],
            "initial_weights": config["initial_model"]["weights"],
            "initial_weights_sha": config["initial_model"]["weights"]["sha256"],
            "policy_value": {
                name: config[name]
                for name in (
                    "initial_model",
                    "initial_policy",
                    "core_library",
                    "restart",
                )
            },
        }
        write_json(output / "input-binding.json", binding)
        corpus.verify_binding()
    except BaseException as error:
        primary = error
        raise
    finally:
        corpus.close(primary_error=primary)
    marker.unlink()
    return {
        "cache": config["cache"],
        "config": file_ref(output / "config.json"),
        "input_binding": file_ref(output / "input-binding.json"),
        "scale": file_ref(output / "scale.json"),
        "constant": file_ref(output / "constant.json"),
        "scope": "actual source/config preparation only; no fit/forward or runtime permission",
    }


def main():
    import argparse
    import json
    from pathlib import Path
    from quoridor_runtime.cycle_process import cancellation_signals

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=("fits", "policy-value"), default="fits")
    args = parser.parse_args()
    with cancellation_signals():
        prepare = prepare_policy_fit if args.mode == "policy-value" else prepare_fits
        result = prepare(json.loads(Path(args.config).read_bytes()))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
