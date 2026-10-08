"""Bulk native tensor loader with the maintained QF1 Model and configuration.

Validation selects a checkpoint; test is opened only by a later frozen invocation.
Model/optimizer definitions live in this package.
"""

import argparse
import gzip
import csv
import hashlib
import base64
import json
import math
import time
import tempfile
import os
from pathlib import Path
from .snapshot import atomic_text
from .common import (
    resolve_config,
    selected_teacher_types,
    validate_target_tensor,
    MeasurementAccumulator,
)
import io, sys


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(*args, **kwargs):
    from .cache import load as load_cache

    return load_cache(*args, **kwargs)


def _exception_record(error):
    result = {"type": type(error).__name__, "message": str(error)}
    if hasattr(error, "__notes__"):
        result["notes"] = error.__notes__
    if isinstance(error, BaseExceptionGroup):
        result["errors"] = [_exception_record(part) for part in error.exceptions]
    return result


def write_sampling_counts(path, indices, row_counts, attempted_row_counts):
    """Store visits exactly; contiguous train indices need only two int64 bounds."""
    import numpy as np

    indices = np.asarray(indices, dtype=np.int64)
    start = int(indices[0]) if len(indices) else 0
    contiguous = all(
        (
            np.array_equal(
                indices[first : first + 4096],
                np.arange(start + first, start + min(first + 4096, len(indices))),
            )
            for first in range(0, len(indices), 4096)
        )
    )
    encoding = "range" if contiguous else "explicit"
    payload = {
        "schema": np.asarray("quoridor-visit-counts-v2"),
        "index_encoding": np.asarray(encoding),
        "row_counts": row_counts,
        "attempted_row_counts": attempted_row_counts,
    }
    payload["training_index_range" if contiguous else "training_indices"] = (
        np.asarray([start, start + len(indices)], dtype=np.int64) if contiguous else indices
    )
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("wb") as stream:
            np.savez_compressed(stream, **payload)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return encoding


def verify_initial_binding(expected, weights_path):
    """Reject a different initialization before any selector or optimizer forward."""
    if sha(weights_path) != expected.get("initial_weights_sha"):
        raise ValueError("initial native weights differ from fixed qualified initialization")


def prepare_statistics(cache, output):
    """Fix original-train distance moments and row constant without Torch or test labels."""
    import numpy as np

    started = time.monotonic()
    corpus = load(cache)
    if (
        not getattr(corpus, "compact", False)
        or corpus.manifest.get("dataset_revision") != "original-full-v1"
    ):
        raise ValueError("statistics requires qualified original-full-v1 compact observations")
    indices = np.flatnonzero((corpus.splits == 0) & corpus.eligible)
    if not len(indices):
        raise ValueError("statistics requires nonempty training observations")
    statistics, fitted = training_statistics(corpus, indices, 1)
    constant = float(np.mean(corpus.labels[indices, 1], dtype=np.float64))
    binding = {
        "cache_manifest_sha": corpus.binding["dataset_sha"],
        "partition": "train",
        "rows": len(indices),
        "target": "decisive STM z",
        "weighting": "row",
        "augmentation": "original only; scale fixed before online reflection",
        "test_opened": False,
    }
    output = Path(output)
    output.mkdir(parents=True)
    corpus.verify_binding()
    write(output / "train-only-scale.json", {**statistics, "binding": binding})
    write(output / "train-only-constant.json", {"row_mean_constant": constant, "binding": binding})
    result = {
        **binding,
        "scale_sha": sha(output / "train-only-scale.json"),
        "constant_sha": sha(output / "train-only-constant.json"),
        "least_squares_distance_diagnostic": fitted,
        "model_distance": {"a": 0, "b": 8},
        "wall_seconds": time.monotonic() - started,
        "model_forward_rows": 0,
    }
    write(output / "result.json", result)
    return result


def _finalize_training(output, actions, primary_error, facts, *, prior_failures=()):
    failures = list(prior_failures)
    stages = [{"stage": "primary_stop_record", "status": "FAILED"} for _ in prior_failures]
    for stage, action in actions:
        before = len(failures)
        _attempt_finalization(stage, action, failures)
        stages.append(
            {"stage": stage, "status": "FAILED" if len(failures) > before else "COMPLETED"}
        )
    if not failures:
        return
    receipt = {
        "primary_exception": None if primary_error is None else _exception_record(primary_error),
        "original_stop_and_position": facts(),
        "stages": stages,
        "finalization_errors": [_exception_record(error) for error in failures],
        "failed_checkpoint_completeness": "UNKNOWN if its stage failed; position is last known successful save",
    }
    _attempt_finalization(
        "finalization_error_receipt",
        lambda: write(output / "finalization-errors.json", receipt),
        failures,
    )
    errors = ([primary_error] if primary_error is not None else []) + failures
    group = BaseExceptionGroup("training primary/finalization failures", errors)
    group.add_note(json.dumps(receipt, allow_nan=False))
    raise group from None


def append_curve_record(path, record):
    """Append one complete gzip member; existing observations are never rewritten."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as archive:
        with io.TextIOWrapper(archive, encoding="utf-8") as stream:
            stream_json(stream, record)
            stream.write("\n")
    with Path(path).open("ab") as stream:
        stream.write(buffer.getbuffer())


def _attempt_finalization(stage, action, failures):
    """Attempt each owed independent action, retaining every stage error."""
    try:
        return action()
    except BaseException as error:
        error.add_note("training finalization stage: " + stage)
        failures.append(error)
        return None


def write(path, value):
    with atomic_text(path) as stream:
        stream_json(stream, value)
        stream.write("\n")


def stream_json(stream, value):
    """Serialize compact arrays and row iterators without materializing JSON lists."""
    import numpy as np

    if isinstance(value, dict):
        stream.write("{")
        for number, (key, part) in enumerate(value.items()):
            if number:
                stream.write(",")
            stream.write(json.dumps(key) + ":")
            stream_json(stream, part)
        stream.write("}")
    elif isinstance(value, (list, tuple, np.ndarray)) or hasattr(value, "__next__"):
        stream.write("[")
        for number, part in enumerate(value):
            if number:
                stream.write(",")
            stream_json(stream, part)
        stream.write("]")
    else:
        if isinstance(value, np.generic):
            value = value.item()
        stream.write(json.dumps(value, allow_nan=False))


def build_model(config, statistics):
    if config.get("architecture") == "distance_steps":
        from .distance_steps import build_model as build_steps

        return build_steps(config, statistics)
    if config.get("architecture", "scaled") == "distance_residual":
        from .residual_model import DistanceResidualModel

        return DistanceResidualModel(
            config, statistics, a=config["distance_a"], b=config["distance_b"]
        )
    from .scaled_model import build_model as build_scaled

    return build_scaled(config, statistics)


def export(model, config, statistics, distance_fit, path):
    import numpy as np

    path = Path(path)
    path.mkdir(exist_ok=True)
    ordered = [
        model.ft.weight,
        model.ft.bias,
        model.h.weight,
        model.h.bias,
        model.out.weight,
        model.out.bias,
    ]
    arrays = [v.detach().cpu().numpy().astype("<f4").reshape(-1) for v in ordered]
    vector = np.concatenate(arrays)
    weights = path / "weights.f32"
    vector.tofile(weights)
    manifest = {
        "feature": "QF1-f32-STM-scaled-v1",
        "weights": weights.name,
        "weights_SHA": sha(weights),
        "weights_B": weights.stat().st_size,
        "little_endian_f32": int(vector.size),
        "transformer_width": config["model"]["transformer_width"],
        "hidden_width": config["model"]["hidden_width"],
        "mu_f32": statistics["mu_f32"],
        "sigma_f32": statistics["sigma_f32"],
        "distance_fit": distance_fit,
        "source_kind": "native-QF1-learning-cycle",
    }
    if config["model"]["transformer_width"] != 32 or config["model"]["hidden_width"] != 32:
        manifest["feature"] = "QF1-f32-STM-scaled-v2"
        manifest["topology"] = {
            "ft_width": config["model"]["transformer_width"],
            "hidden_width": config["model"]["hidden_width"],
        }
        manifest["value_perspective"] = "side-to-move"
    if config["model"].get("architecture", "scaled") == "distance_residual":
        from .residual_model import FEATURE_VERSION, ROUTE_VERSION

        for key in ("transformer_width", "hidden_width", "source_kind"):
            manifest.pop(key, None)
        manifest.update(
            {
                "schema": "quoridor-nnue-distance-residual-v3",
                "feature": FEATURE_VERSION,
                "value_perspective": "side-to-move",
                "value_parameterization": "fixed-distance-logit-plus-linear-residual-tanh",
                "dense_feature_version": ROUTE_VERSION,
                "route_mode": "zero4",
                "route_mu_f32": [0.0] * 4,
                "route_sigma_f32": [1.0] * 4,
                "topology": {
                    "ft_width": config["model"]["transformer_width"],
                    "hidden_width": config["model"]["hidden_width"],
                },
                "distance_fit": {
                    "a": config["model"]["distance_a"],
                    "b": config["model"]["distance_b"],
                },
            }
        )
    elif config["model"].get("architecture") == "distance_steps":
        from .distance_steps import SCORE_SCHEMA, nonterminal_bound
        from .residual_model import FEATURE_VERSION, ROUTE_VERSION

        bound = nonterminal_bound(
            [v.detach().cpu().numpy() for v in ordered],
            statistics,
            config["model"]["distance_bypass"],
        )
        for key in ("transformer_width", "hidden_width", "source_kind", "distance_fit"):
            manifest.pop(key, None)
        manifest.update(
            {
                "schema": SCORE_SCHEMA,
                "feature": FEATURE_VERSION,
                "dense_feature_version": ROUTE_VERSION,
                "route_mode": "zero4",
                "route_mu_f32": [0.0] * 4,
                "route_sigma_f32": [1.0] * 4,
                "topology": {"ft_width": 32, "hidden_width": 32},
                "value_perspective": "side-to-move",
                "score_version": "distance-step-v1",
                "score_units": "raw-distance-steps",
                "distance_bypass": config["model"]["distance_bypass"],
                "train_transform": config["model"]["train_transform"],
                "deploy_transform": config["model"]["deploy_transform"],
                "distance_input_units": "wall-only-D/80-before-T-standardization",
                "integer_bypass_input": "canonical-geometry-opponentD-minus-STM-D; never rounded feature reconstruction",
                "nonterminal_raw_abs_bound": bound,
                "outcome_target_scale": 80,
                "loss_divisor": 6400,
                "condition": config["experiment"]["condition"],
            }
        )
    write(path / "training-target.json", {"training_target": config["training"]["target"]})
    write(path / "manifest.json", manifest)
    return path / "manifest.json"


def train(
    cache,
    output,
    config_path=None,
    steps=None,
    *,
    scale_path=None,
    input_binding=None,
    supply_workers=None,
):
    start = time.monotonic()
    cfg = resolve_config(config_path, () if steps is None else (f"training.steps={steps}",))
    from .distance_steps import require_main_volume

    volume_admission = require_main_volume(
        cfg,
        cache=cache,
        config_path=config_path,
        input_binding=input_binding,
        scale_path=scale_path,
        supply_workers=supply_workers,
    )
    import numpy as np

    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch

    if supply_workers is None:
        supply_workers = cfg["training"]["supply_workers"]
    if type(supply_workers) is not int or supply_workers not in (0, 2):
        raise ValueError("supply workers must be 0 (synchronous) or 2 (qualified prefetch)")
    if input_binding and supply_workers != cfg["training"]["supply_workers"]:
        raise ValueError("bound input requires the configured supply worker mode")
    cfg["training"]["supply_workers"] = supply_workers
    if config_path is None:
        cfg["optimizer"]["lr"] = 0.0001
    torch.set_num_threads(cfg["training"]["threads"])
    if torch.get_num_interop_threads() != cfg["training"]["threads"]:
        torch.set_num_interop_threads(cfg["training"]["threads"])
    torch.manual_seed(cfg["training"]["seed"])
    torch.use_deterministic_algorithms(True)
    device = cfg["training"]["device"]
    if device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        _, device_total = torch.cuda.mem_get_info()
        torch.cuda.set_per_process_memory_fraction(min(5 * 1024**3 / device_total, 1.0))
        torch.cuda.manual_seed_all(cfg["training"]["seed"])
    corpus = load(cache)
    binding, rows, labels = (corpus.binding, corpus.rows, corpus.labels)
    target = cfg["training"]["target"]
    column = {"rootmean": 0, "z": 1, "outcome_steps": 1, "terminal_margin": 2}[target]
    step_score = cfg["model"]["architecture"] == "distance_steps"
    if step_score != getattr(corpus, "terminal", False):
        raise ValueError("distance-step model requires its bound dual-teacher geometry corpus")
    target_scale = 80 if target == "outcome_steps" else 1
    compact = getattr(corpus, "compact", False)
    public_compact = compact and not step_score
    if public_compact and (
        target != "z"
        or cfg["training"]["sampling"] != "epoch"
        or cfg["training"]["loss_weighting"] != "row"
        or (cfg["evaluation"]["monitor"] != "row")
    ):
        raise ValueError(
            "public compact corpus requires decisive z / row epoch objective and row monitor"
        )
    if public_compact and (
        corpus.manifest.get("original_only") is not True
        or corpus.manifest.get("dataset_revision") != "original-full-v1"
    ):
        raise ValueError("public fit requires adopted original-full-v1 observations")
    if public_compact and (
        cfg["model"]["architecture"] != "distance_residual"
        or cfg["model"]["transformer_width"] != 32
        or cfg["model"]["hidden_width"] != 32
        or (cfg["model"]["dropout"] != 0)
        or (cfg["model"]["distance_a"] != 0)
        or (cfg["model"]["distance_b"] != 8)
        or (cfg["optimizer"]["name"] != "adam")
        or (cfg["optimizer"]["weight_decay"] != 0)
    ):
        raise ValueError("public full fit requires fixed QF1+D FT32/H32/dropout0/a0b8 Adam/wd0")
    teacher_types = (
        {"terminal_pair"}
        if step_score
        else ({"external_outcome"} if compact else selected_teacher_types(rows, target))
    )
    if not compact:
        validate_target_tensor(rows, labels[:, column], target)
    valid = corpus.eligible & np.isfinite(labels[:, column])
    ix_train = np.flatnonzero((corpus.splits == 0) & valid)
    ix_validation = np.flatnonzero((corpus.splits == 1) & valid)
    ix_validation_raw = np.flatnonzero(corpus.splits == 1)
    if not len(ix_train) or not len(ix_validation):
        raise ValueError("nonempty eligible train and unexposed validation required")
    if compact:
        family_codes = np.unique(corpus.groups[ix_train])
        group_indices, families = ([], [])
        constant = float(np.mean(labels[ix_train, column], dtype=np.float64))
    else:
        codes = corpus.groups[ix_train]
        family_codes, seen_codes = ([], set())
        for code in codes:
            if int(code) not in seen_codes:
                family_codes.append(int(code))
                seen_codes.add(int(code))
        order = np.argsort(codes, kind="stable")
        sorted_codes = codes[order]
        starts = np.searchsorted(sorted_codes, family_codes, side="left")
        ends = np.searchsorted(sorted_codes, family_codes, side="right")
        group_flat_sorted = ix_train[order]
        group_indices = [group_flat_sorted[first:last] for first, last in zip(starts, ends)]
        families = [corpus.families[code] for code in family_codes]
        sums = np.zeros(len(corpus.families), dtype=np.float64)
        counts = np.zeros(len(corpus.families), dtype=np.int64)
        for first in range(0, len(ix_train), 4096):
            sub = ix_train[first : first + 4096]
            np.add.at(sums, corpus.groups[sub], labels[sub, column].astype(np.float64))
            np.add.at(counts, corpus.groups[sub], 1)
        constant = float(np.mean(sums[family_codes] / counts[family_codes]))
        del codes, order, sorted_codes
    constant *= target_scale
    if step_score:
        cfg["training"]["warmup_steps"] = min(
            257, math.ceil(len(ix_train) / cfg["training"]["batch_size"])
        )
    statistics, fitted = training_statistics(corpus, ix_train, column)
    if input_binding is not None:
        expected = (
            volume_admission["expected"]
            if volume_admission is not None
            else json.loads(Path(input_binding).read_text())
        )
        expected_scale = json.loads(Path(expected["scale_artifact"]).read_text())
        constant_path = Path(expected["constant_artifact"])
        expected_constant = json.loads(constant_path.read_text())
        if (
            binding["dataset_sha"] != expected["cache_manifest_sha"]
            or sha(expected["scale_artifact"]) != expected["scale_artifact_sha"]
            or sha(constant_path) != expected["constant_artifact_sha"]
            or (config_path is not None and sha(config_path) != expected["fit_config_sha"])
            or (statistics["mu_f32"] != expected_scale["mu_f32"])
            or (statistics["sigma_f32"] != expected_scale["sigma_f32"])
            or (constant != expected_constant["row_mean_constant"])
            or (scale_path is not None)
        ):
            raise ValueError("fit train-only statistics/constant/input binding mismatch")
    from .distance_steps import verify_main_statistics

    verify_main_statistics(volume_admission, statistics)
    if scale_path is not None:
        from .scaled_model import validate_statistics

        statistics = validate_statistics(json.loads(Path(scale_path).read_text()))
    distance_fit = (
        {"a": cfg["model"]["distance_a"], "b": cfg["model"]["distance_b"]}
        if cfg["model"]["architecture"] == "distance_residual"
        else fitted
    )
    if step_score:
        distance_fit = {"a": 0, "b": 1, "units": "integer-wall-distance-steps"}
    model = build_model(cfg["model"], statistics).to(device)
    initial_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if volume_admission is not None:
        digest = hashlib.sha256()
        for key in ("ft.weight", "ft.bias", "h.weight", "h.bias", "out.weight", "out.bias"):
            digest.update(initial_state[key].numpy().astype("<f4").tobytes())
        if digest.hexdigest() != volume_admission["expected"]["initial_weights_sha"]:
            raise ValueError("actual common initialization differs before optimizer/forward")
    if device == "cuda":
        free, total = torch.cuda.mem_get_info()
        if free <= 2 * 1024**3:
            raise RuntimeError("CUDA host/display reserve leaves no training window")
    generator = torch.Generator().manual_seed(cfg["training"]["seed"] + 1)
    optimizers = {"adam": torch.optim.Adam, "adamw": torch.optim.AdamW, "sgd": torch.optim.SGD}
    opt_kwargs = {"lr": cfg["optimizer"]["lr"], "weight_decay": cfg["optimizer"]["weight_decay"]}
    if cfg["optimizer"]["name"] == "sgd":
        opt_kwargs["momentum"] = cfg["optimizer"]["momentum"]
    optimizer = optimizers[cfg["optimizer"]["name"]](model.parameters(), **opt_kwargs)
    scheduler = None
    if cfg["training"]["scheduler"] == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, cfg["training"]["steps"])
    elif cfg["training"]["scheduler"] == "plateau":
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=cfg["training"]["lr_decay_factor"],
            patience=cfg["training"]["lr_decay_patience"],
            threshold=cfg["evaluation"]["min_delta"],
            threshold_mode="abs",
            min_lr=cfg["training"]["min_lr"],
        )
    if step_score and scheduler is not None:
        from .distance_steps import significant_improvement

        scheduler.is_better = significant_improvement
    output = Path(output)
    output.mkdir(parents=True)
    if volume_admission is not None:
        write(output / "main-volume-admission.json", volume_admission)
    write(output / "config.json", cfg)
    write(output / "scale.json", statistics)
    with gzip.open(output / "cache-binding.json.gz", "wt") as stream:
        json.dump(binding, stream)
    write(
        output / "data.json",
        {
            "binding": {"dataset_sha": binding["dataset_sha"], "file": "cache-binding.json.gz"},
            "train": len(ix_train),
            "validation": len(ix_validation),
            "constant": constant,
            "distance_fit": distance_fit,
            "teacher_types": sorted(teacher_types),
            "target_alias": "rootmean is bounded search value only for alpha_beta datasets",
            "test_opened": False,
        },
    )
    samples, best_step, best_loss, best_state = (0, 0, float("inf"), initial_state)
    curve, diagnostics, diagnostic_curve = ([], [], [])
    group_lengths = np.array([len(group) for group in group_indices], dtype=np.int64)
    group_offsets = np.concatenate([[0], np.cumsum(group_lengths)[:-1]])
    group_flat = np.concatenate(group_indices) if group_indices else np.empty(0, dtype=np.int64)
    from .sampling import (
        EpochSampler,
        EarlyStopping,
        diagnostic_indices,
        observation_steps,
        exposure,
        loss_weights,
        update_steps,
        ReflectionBatches,
        ConvergenceObservations,
    )

    mode = cfg["training"]["sampling"]
    batch_size = cfg["training"]["batch_size"]
    unbounded = cfg["training"]["steps"] is None
    convergence = (
        ConvergenceObservations(
            len(ix_train),
            cfg["evaluation"]["diagnostic_interval"],
            cfg["evaluation"]["full_train_every_epochs"],
        )
        if unbounded
        else None
    )
    supply = ReflectionBatches(
        corpus, cfg["training"]["reflection_probability"], cfg["training"]["reflection_seed"]
    )
    evaluation_steps = (
        set()
        if unbounded
        else observation_steps(
            cfg["training"]["steps"],
            cfg["evaluation"]["interval"],
            len(ix_train),
            batch_size,
            mode,
            cfg["evaluation"]["checkpoints"],
        )
    )
    diagnostic_steps = (
        set()
        if unbounded
        else observation_steps(
            cfg["training"]["steps"],
            cfg["evaluation"]["diagnostic_interval"],
            len(ix_train),
            batch_size,
            mode,
            cfg["evaluation"]["diagnostic_checkpoints"],
        )
        if cfg["evaluation"]["diagnostic_rows"]
        else set()
    )
    checkpoint_steps = set(cfg["artifacts"]["checkpoint_steps"])
    scheduled = cfg["artifacts"]["save_scheduled"]
    evaluation_validation = ix_validation_raw if scheduled else ix_validation
    primary_in_raw = np.searchsorted(ix_validation_raw, ix_validation)
    if compact:
        rng = np.random.default_rng(cfg["training"]["seed"] + 2)
        diag_train = np.sort(
            rng.choice(
                ix_train, min(len(ix_train), cfg["evaluation"]["diagnostic_rows"]), replace=False
            )
        )
        diag_val = np.sort(
            rng.choice(
                ix_validation,
                min(len(ix_validation), cfg["evaluation"]["diagnostic_rows"]),
                replace=False,
            )
        )
    else:
        diag_train = diagnostic_indices(
            rows, ix_train, cfg["evaluation"]["diagnostic_rows"], cfg["training"]["seed"]
        )
        diag_val = diagnostic_indices(
            rows, ix_validation, cfg["evaluation"]["diagnostic_rows"], cfg["training"]["seed"]
        )
    train_eval = ix_train if cfg["evaluation"]["full_train"] else diag_train
    if not len(train_eval):
        raise ValueError("full_train=false requires nonempty diagnostic subset")
    epoch_sampler = (
        EpochSampler(ix_train, batch_size, cfg["training"]["seed"]) if mode == "epoch" else None
    )
    stopper = EarlyStopping(
        cfg["evaluation"]["early_stopping_patience"],
        cfg["evaluation"]["min_delta"],
        cfg["evaluation"]["min_delta_relative"],
    )
    sampled_rows = np.zeros(len(rows), dtype=np.int64)
    attempted_rows = np.zeros(len(rows), dtype=np.int64)
    training_seen, completed_step, attempted_step = (0, 0, 0)
    best_exposure = None
    row_loss_weights = np.zeros(len(rows), dtype=np.float32)
    row_loss_weights[ix_train] = loss_weights(
        corpus.groups[ix_train], cfg["training"]["loss_weighting"]
    )
    objective_weights = torch.as_tensor(row_loss_weights)
    packed_supply = None
    training_payload = None
    if not compact and supply_workers:
        raise ValueError("prefetch requires compact epoch corpus")
    phase_seconds = {
        name: 0.0
        for name in [
            "initialization",
            "transfer",
            "synchronization",
            "inference",
            "update",
            "logging",
            "full_selector",
            "fixed_diagnostic",
            "export",
        ]
    }
    phase_seconds["initialization"] = time.monotonic() - start
    batch_records_logged = 0
    checkpoint_positions = {}
    forward_rows = {"train": 0, "full_selector": 0, "diagnostic": 0, "onnx": 0}
    completed_forward_rows = dict(forward_rows)
    status, fault, model_state_status = ("RUNNING", None, "LAST_COMPLETED_UPDATE")
    last_completed_point = None
    measurement_sets, reference_metrics = ({}, {})

    def position():
        return {"step": completed_step, **exposure(training_seen, len(ix_train), mode)}

    def sync():
        if device == "cuda":
            tick = time.monotonic()
            torch.cuda.synchronize()
            phase_seconds["synchronization"] += time.monotonic() - tick

    def append_record(stream, record):
        tick = time.monotonic()
        stream.write(json.dumps(record, allow_nan=False) + "\n")
        stream.flush()
        phase_seconds["logging"] += time.monotonic() - tick

    def charge(n, kind):
        nonlocal samples
        if (
            cfg["limits"]["samples"] is not None
            and samples + n > cfg["limits"]["samples"]
            or (
                cfg["limits"]["seconds"] is not None
                and time.monotonic() - start > cfg["limits"]["seconds"]
            )
        ):
            raise RuntimeError("training budget exhausted")
        samples += n
        forward_rows[kind] += n

    def batch(index, *, training=False):
        nonlocal training_payload
        if device == "cuda" and torch.cuda.mem_get_info()[0] < 2 * 1024**3:
            raise RuntimeError("CUDA reserve exhausted")
        tick = time.monotonic()
        if packed_supply is not None:
            result, targets, weights = packed_supply.batch(
                index, training=training, sampler=epoch_sampler if training else None
            )
            if training:
                training_payload = (targets, weights)
            phase_seconds["transfer"] += time.monotonic() - tick
            return result
        features, distances, _ = supply.batch(index, training=training)
        result = (
            torch.from_numpy(features).to(device),
            torch.from_numpy(distances).to(device),
            torch.ones(len(index), dtype=torch.long, device=device),
        )
        if step_score:
            result += (
                torch.from_numpy(corpus.integer_distances[index].astype(np.float32)).to(device),
            )
        sync()
        phase_seconds["transfer"] += time.monotonic() - tick
        return result

    def predict(indices, kind):
        values = mapped_values(len(indices))
        for first in range(0, len(indices), cfg["evaluation"]["batch_size"]):
            sub = indices[first : first + cfg["evaluation"]["batch_size"]]
            inputs = batch(sub)
            charge(len(sub), kind)
            tick = time.monotonic()
            result = model(*inputs)
            sync()
            phase_seconds["inference"] += time.monotonic() - tick
            tick = time.monotonic()
            values[first : first + len(sub)] = result.cpu().numpy()
            phase_seconds["transfer"] += time.monotonic() - tick
            completed_forward_rows[kind] += len(sub)
        return values

    def summarize(indices, values):
        if step_score:
            from .step_measurements import measurements as step_measurements

            return step_measurements(
                corpus, indices, values, target, constant, cfg["model"]["train_transform"]
            )
        if compact:
            return compact_measurements(corpus, indices, values, constant, distance_fit, ix_train)
        scope = hashlib.sha256(np.asarray(indices, dtype="<i8")).hexdigest()
        measured = MeasurementAccumulator(target, constant)
        reference = MeasurementAccumulator(target, constant)
        group_distance, group_constant = ({}, {})
        for first in range(0, len(indices), cfg["evaluation"]["batch_size"]):
            sub = indices[first : first + cfg["evaluation"]["batch_size"]]
            _, raw, local_labels = corpus.batch(sub)
            baseline = np.tanh(
                np.float32(distance_fit["a"])
                + np.float32(distance_fit["b"]) * (raw[:, 1] - raw[:, 0])
            )
            for j, (i, row) in enumerate(zip(sub, rows.iter_indices(sub))):
                measured.add(row, values[first + j])
                reference.add(row, baseline[j])
                for store, error in (
                    (group_distance, (baseline[j] - local_labels[j, column]) ** np.float32(2)),
                    (
                        group_constant,
                        (np.float32(constant) - local_labels[j, column]) ** np.float32(2),
                    ),
                ):
                    pair = store.setdefault(row["group"], [0.0, 0])
                    pair[0] += float(error)
                    pair[1] += 1
        ordered = sorted(measured.groups)
        if scope not in measurement_sets:
            measurement_sets[scope] = {
                "groups": ordered,
                "group_rows": [measured.groups[g]["rows"] for g in ordered],
                "input_indices_sha256": scope,
                "rows": len(indices),
                "dataset_sha": binding["dataset_sha"],
            }
            reference_metrics[scope] = {
                "distance": reference.result(),
                "constant": constant,
                "group_distance_mse_f32": [
                    float(np.float32(group_distance[g][0] / group_distance[g][1])) for g in ordered
                ],
                "group_constant_mse_f32": [
                    float(np.float32(group_constant[g][0] / group_constant[g][1])) for g in ordered
                ],
            }
            write(output / "measurement-sets.json", measurement_sets)
            write(output / "reference-metrics.json", reference_metrics)
        reports = [measured.result(g) for g in ordered]
        vectors = {
            field: [r[field] if r[field] is not None else np.nan for r in reports]
            for field in ("target_mse", "z_sign_accuracy", "saturation_fraction")
        }
        vectors["bias"] = [
            measured.groups[g]["bias_sum"] / measured.groups[g]["bias_rows"]
            if measured.groups[g]["bias_rows"]
            else np.nan
            for g in ordered
        ]
        report = measured.result()
        report["groups"] = {
            "encoding": "little-endian-f32-base64; NaN means missing, never zero",
            "order_ref": scope,
            "fields": {
                field: base64.b64encode(np.asarray(vector, dtype="<f4").tobytes()).decode()
                for field, vector in vectors.items()
            },
        }
        report["distance_ref"] = scope
        report["bias"] = (
            measured.totals["bias_sum"] / measured.totals["bias_rows"]
            if measured.totals["bias_rows"]
            else None
        )
        return report

    subsets = {
        "train": [int(i) for i in diag_train],
        "validation": [int(i) for i in diag_val],
        "algorithm": "independent numpy RNG(seed+2), uniform without replacement, sorted indices"
        if compact
        else "sha256(seed:input-row-id), index tie; sorted loaded-index output",
        "target_blind": True,
    }
    write(
        output / "diagnostic-subsets.json",
        {
            **subsets,
            "index_sha256": hashlib.sha256(
                json.dumps(subsets, sort_keys=True).encode()
            ).hexdigest(),
            "dataset_sha": binding["dataset_sha"],
        },
    )
    write(
        output / "observation-plan.json",
        {
            "full_selector_steps": None if unbounded else sorted(evaluation_steps),
            "unbounded_epoch_plan": {
                "selector": "step0 and each completed epoch, all eligible validation original inputs",
                "diagnostic": "0/1/2/5/10/20; every25 through2000, then configured interval plus epoch ends",
                "full_train": "epoch1 and every configured full_train_every_epochs; fixed diagnostics otherwise",
                "diagnostic_interval": cfg["evaluation"]["diagnostic_interval"],
                "full_train_every_epochs": cfg["evaluation"]["full_train_every_epochs"],
                "scientific_stop": "epoch primary rowMSE patience/min_delta or nonfinite; no fixed horizon",
            }
            if unbounded
            else None,
            "augmentation": {
                "probability": cfg["training"]["reflection_probability"],
                "seed": cfg["training"]["reflection_seed"],
                "train_only": True,
                "validation_original": True,
            },
            "fixed_diagnostic_steps": None if unbounded else sorted(diagnostic_steps),
            "checkpoint_steps": sorted(checkpoint_steps),
            "full_train": cfg["evaluation"]["full_train"],
            "selector_scope": "all eligible validation; scheduled export additionally reads raw validation",
            "fixed_diagnostic_is_selector": False,
            "initialization_seconds": phase_seconds["initialization"],
            "timing_overlap": "inclusive phases; synchronization nested in transfer/inference/update; do not sum",
            "tail_objective": "each tail uses its own mean loss and one optimizer update",
        },
    )
    if scheduled:
        for name, indices in [("train", ix_train), ("validation", ix_validation_raw)]:
            with gzip.open(output / f"{name}-order.json.gz", "wt") as stream:
                stream_json(stream, (row["id"] for row in rows.iter_indices(indices)))

    def save_checkpoint(step):
        tick = time.monotonic()
        torch.save(
            {"model": model.state_dict(), "model_config": cfg["model"], "scale": statistics},
            output / f"step{step}.pt",
        )
        export(model, cfg, statistics, distance_fit, output / f"step{step}-model")
        phase_seconds["export"] += time.monotonic() - tick

    def save_named_checkpoint(name):
        """Overwrite the three maintained names; never save a checkpoint per curve point."""
        tick = time.monotonic()
        state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        torch.save(
            {
                "model": state,
                "model_config": cfg["model"],
                "scale": statistics,
                "target": target,
                "dataset_sha": binding["dataset_sha"],
                "position": position(),
                "optimizer": optimizer.state_dict(),
            },
            output / (name + ".pt"),
        )
        export(model, cfg, statistics, distance_fit, output / (name + "-model"))
        checkpoint_positions[name] = position()
        phase_seconds["export"] += time.monotonic() - tick

    def evaluate(step, selector, diagnostic, full_train=False):
        nonlocal best_step, best_loss, best_state, best_exposure, last_completed_point
        tick = time.monotonic()
        model.eval()
        reused = {}
        stop = False
        with torch.inference_mode():
            if selector:
                current_train_eval = (
                    ix_train
                    if full_train or step in cfg["evaluation"]["full_train_checkpoints"]
                    else train_eval
                )
                ptrain = predict(current_train_eval, "full_selector")
                praw = predict(evaluation_validation, "full_selector")
                pval = (
                    select_values(praw, primary_in_raw, cfg["evaluation"]["batch_size"])
                    if scheduled
                    else praw
                )
                record = {
                    **position(),
                    "samples": samples,
                    "wall_seconds": time.monotonic() - start,
                    "loss_weighting": cfg["training"]["loss_weighting"],
                    "train_scope": "full_train"
                    if full_train
                    or cfg["evaluation"]["full_train"]
                    or step in cfg["evaluation"]["full_train_checkpoints"]
                    else "fixed_diagnostic_subset",
                    "validation_forward_rows": len(evaluation_validation),
                    "train": summarize(current_train_eval, ptrain),
                    "validation": summarize(ix_validation, pval),
                }
                loss = record["validation"][
                    "target_mse"
                    if cfg["evaluation"]["monitor"] == "row"
                    else "target_game_equal_mse"
                ]
                if cfg["evaluation"]["early_stopping_unit"] == "epoch":
                    boundary = training_seen > 0 and training_seen % len(ix_train) == 0
                    if step == 0 or boundary:
                        _, stop = stopper.observe(loss)
                    if (
                        boundary
                        and scheduler is not None
                        and (cfg["training"]["scheduler"] == "plateau")
                        and (completed_step >= cfg["training"]["warmup_steps"])
                    ):
                        scheduler.step(loss)
                    improved = loss < best_loss
                else:
                    improved, stop = stopper.observe(loss)
                if improved:
                    best_step, best_loss = (step, loss)
                    best_state = {
                        k: v.detach().cpu().clone() for k, v in model.state_dict().items()
                    }
                    best_exposure = position()
                    save_named_checkpoint("best")
                save_named_checkpoint("last")
                record["lr"] = [group["lr"] for group in optimizer.param_groups]
                curve.append(curve_summary(record, "full_selector"))
                last_completed_point = {"kind": "full_selector", **position()}
                append_record(observation_log, {"kind": "full_selector", **record})
                for indices, values, diagnostic_indices in (
                    (current_train_eval, ptrain, diag_train),
                    (ix_validation, pval, diag_val),
                ):
                    positions = np.searchsorted(indices, diagnostic_indices)
                    for i, at in zip(diagnostic_indices, positions):
                        if at < len(indices) and indices[at] == i:
                            reused[int(i)] = float(values[at])
                if scheduled:
                    write_values(
                        ptrain, output / f"train-step{step}.f32", cfg["evaluation"]["batch_size"]
                    )
                    write_values(
                        praw, output / f"validation-step{step}.f32", cfg["evaluation"]["batch_size"]
                    )
                phase_seconds["full_selector"] += time.monotonic() - tick
            if diagnostic:
                tick = time.monotonic()
                parts = {}
                for name, indices in [("train", diag_train), ("validation", diag_val)]:
                    missing = np.asarray(
                        [i for i in indices if int(i) not in reused], dtype=np.int64
                    )
                    if len(missing):
                        reused.update(
                            {
                                int(i): float(v)
                                for i, v in zip(missing, predict(missing, "diagnostic"))
                            }
                        )
                    values = np.asarray([reused[int(i)] for i in indices], dtype=np.float32)
                    parts[name] = summarize(indices, values)
                record = {
                    **position(),
                    "wall_seconds": time.monotonic() - start,
                    **parts,
                    "scope": "fixed_target_blind_subset",
                    "train_scope": "fixed_diagnostic_subset",
                    "used_for_selection": False,
                }
                diagnostic_curve.append(curve_summary(record, "fixed_diagnostic"))
                last_completed_point = {"kind": "fixed_diagnostic", **position()}
                append_record(observation_log, {"kind": "fixed_diagnostic", **record})
                phase_seconds["fixed_diagnostic"] += time.monotonic() - tick
        if step in checkpoint_steps:
            save_checkpoint(step)
        persist_curves()
        return stop

    persisted_curve_counts = {"curves": 0, "diagnostic-curves": 0}

    def persist_curves():
        tick = time.monotonic()
        for name, records in [("curves", curve), ("diagnostic-curves", diagnostic_curve)]:
            while persisted_curve_counts[name] < len(records):
                at = persisted_curve_counts[name]
                append_curve_record(output / (name + ".jsonl.gz"), records[at])
                _curve_csv([records[at]], output / (name + ".csv"), append=at > 0)
                persisted_curve_counts[name] += 1
        phase_seconds["logging"] += time.monotonic() - tick

    def persist():
        tick = time.monotonic()
        failures = []
        _attempt_finalization("curves", persist_curves, failures)
        _attempt_finalization(
            "gradients.json",
            lambda: write(
                output / "gradients.json",
                {
                    "schema": "quoridor-gradient-stream-reference-v1",
                    "file": "batch.jsonl.gz",
                    "record_status": "COMPLETED",
                    "field": "gradient_norm",
                    "completed_records": batch_records_logged,
                    "logging": "observed diagnostics/epoch boundaries only"
                    if unbounded
                    else "every update",
                },
            ),
            failures,
        )
        count_encoding = None
        if compact:
            count_encoding = _attempt_finalization(
                "sampling-counts.npz",
                lambda: write_sampling_counts(
                    output / "sampling-counts.npz", ix_train, sampled_rows, attempted_rows
                ),
                failures,
            )
        _attempt_finalization(
            "sampling.json",
            lambda: write(
                output / "sampling.json",
                {
                    **position(),
                    "seen": int(sampled_rows.sum()),
                    "mode": mode,
                    "row_count_order": "immutable loaded cache order",
                    "attempted_step": attempted_step,
                    "optimizer_steps": completed_step,
                    "training_indices": None if compact else ix_train,
                    "training_rows": len(ix_train),
                    "row_counts": None if compact else sampled_rows,
                    "attempted_row_counts": None if compact else attempted_rows,
                    "training_row_min_visits": int(sampled_rows[ix_train].min()),
                    "training_row_max_visits": int(sampled_rows[ix_train].max()),
                    "compact_counts_file": "sampling-counts.npz" if compact else None,
                    "compact_counts_schema": "quoridor-visit-counts-v2" if compact else None,
                    "compact_training_index_encoding": count_encoding if compact else None,
                    "family_counts": {
                        family: int(sampled_rows[group].sum())
                        for family, group in zip(families, group_indices)
                    },
                    "loss_weighting": cfg["training"]["loss_weighting"],
                    "reflection": {
                        "attempted_training_supply_original_rows": supply.training_seen,
                        "reflected_drawn_original_rows": supply.reflected_seen,
                        "counter_scope": "supply attempts/drawn masks before transfer or forward; successful exposure recorded separately",
                        "independent_game_count": "UNKNOWN",
                        "saved_augmentation_rows": 0,
                    },
                    "sampler_advanced_seen": epoch_sampler.seen if epoch_sampler else None,
                    "packed_supply": None
                    if packed_supply is None
                    else {
                        "workers": packed_supply.workers,
                        "dispatched_rows": packed_supply.queue.dispatched_rows,
                        "expanded_rows": packed_supply.queue.expanded_rows,
                        "consumed_supply_rows": packed_supply.queue.consumed_rows,
                        "successful_training_rows": training_seen,
                        "timing_inclusive_not_DMA": packed_supply.timing,
                    },
                },
            ),
            failures,
        )
        phase_seconds["logging"] += time.monotonic() - tick
        _attempt_finalization(
            "run-status.json",
            lambda: write(
                output / "run-status.json",
                {
                    "status": status,
                    "fault": fault,
                    **position(),
                    "attempted_step": attempted_step,
                    "model_state_status": model_state_status,
                    "selected_exposure": best_exposure,
                    "last_completed_point": last_completed_point,
                    "checkpoint_positions": checkpoint_positions,
                    "samples": samples,
                    "forward_rows_conservative": forward_rows,
                    "forward_rows_completed": completed_forward_rows,
                    "phase_seconds_inclusive": phase_seconds,
                    "wall_seconds": time.monotonic() - start,
                    "timing_overlap": "inclusive/nested; do not add phases to infer whole wall",
                },
            ),
            failures,
        )
        if failures:
            raise BaseExceptionGroup("training numerical record persistence failures", failures)

    def curve_summary(record, kind):
        result = dict(record)
        result["kind"] = kind
        result.setdefault("used_for_selection", kind == "full_selector")
        for scope in ("train", "validation"):
            result[scope] = {k: v for k, v in record[scope].items() if k != "groups"}
            result[scope]["groups_ref"] = {
                "file": "observations.jsonl.gz",
                "kind": kind,
                "step": record["step"],
                "scope": scope,
            }
        return result

    with (
        gzip.open(output / "batch.jsonl.gz", "wt", compresslevel=1) as batch_log,
        gzip.open(output / "observations.jsonl.gz", "wt", compresslevel=1) as observation_log,
    ):
        primary_error = None
        stop_record_failures = []
        try:
            supply_started = time.monotonic()
            if compact:
                from .supply import PackedSupply

                packed_supply = PackedSupply(
                    supply,
                    max(batch_size, cfg["evaluation"]["batch_size"]),
                    device,
                    row_loss_weights,
                    column,
                    workers=supply_workers,
                    target_scale=target_scale,
                )
            phase_seconds["initialization"] += time.monotonic() - supply_started
            save_named_checkpoint("initial")
            if compact and input_binding is not None:
                verify_initial_binding(expected, output / "initial-model" / "weights.f32")
            save_named_checkpoint("last")
            if unbounded:
                evaluation_steps.add(0)
                if cfg["evaluation"]["diagnostic_rows"]:
                    diagnostic_steps.add(0)
            if evaluate(0, True, 0 in diagnostic_steps):
                status = "EARLY_STOPPED"
            else:
                for step in update_steps(cfg["training"]["steps"]):
                    attempted_step = step
                    n = epoch_sampler.next_batch_size if epoch_sampler else batch_size
                    if (
                        cfg["limits"]["samples"] is not None
                        and samples + n > cfg["limits"]["samples"]
                        or (
                            cfg["limits"]["seconds"] is not None
                            and time.monotonic() - start > cfg["limits"]["seconds"]
                        )
                    ):
                        raise RuntimeError("training budget exhausted")
                    if epoch_sampler is not None:
                        index = epoch_sampler.next_batch()
                    elif mode == "game":
                        group_ix = torch.randint(
                            len(group_indices), (batch_size,), generator=generator
                        ).numpy()
                        uniform = torch.rand(batch_size, generator=generator).numpy()
                        index = group_flat[
                            group_offsets[group_ix]
                            + (uniform * group_lengths[group_ix]).astype(np.int64)
                        ]
                    else:
                        index = ix_train[
                            torch.randint(len(ix_train), (batch_size,), generator=generator).numpy()
                        ]
                    np.add.at(attempted_rows, index, 1)
                    planned_seen = training_seen + len(index)
                    selector_point, diagnostic_point, full_train_point = (
                        convergence.at(step, planned_seen)
                        if unbounded
                        else (step in evaluation_steps, step in diagnostic_steps, False)
                    )
                    diagnostic_point = diagnostic_point and bool(
                        cfg["evaluation"]["diagnostic_rows"]
                    )
                    record_update = not unbounded or selector_point or diagnostic_point
                    if record_update:
                        append_record(
                            batch_log,
                            {
                                "status": "ATTEMPTED",
                                "attempted_step": step,
                                "batch_rows": len(index),
                                **position(),
                                "wall_seconds": time.monotonic() - start,
                            },
                        )
                    ix = torch.as_tensor(index, dtype=torch.long)
                    model.train()
                    optimizer.zero_grad(set_to_none=True)
                    inputs = batch(index, training=True)
                    charge(len(index), "train")
                    tick = time.monotonic()
                    prediction = model(*inputs)
                    sync()
                    phase_seconds["inference"] += time.monotonic() - tick
                    completed_forward_rows["train"] += len(index)
                    per_row_loss = torch.nn.functional.mse_loss(
                        prediction,
                        training_payload[0]
                        if packed_supply is not None
                        else torch.from_numpy((labels[index, column] * target_scale).copy()).to(
                            device
                        ),
                        reduction="none",
                    )
                    weights = (
                        training_payload[1]
                        if packed_supply is not None
                        else objective_weights[ix].to(device)
                    )
                    loss = (per_row_loss * weights).mean() / (6400 if step_score else 1)
                    if not torch.isfinite(loss):
                        raise ValueError("nonfinite training loss")
                    tick = time.monotonic()
                    loss.backward()
                    if not torch.stack(
                        [
                            torch.isfinite(v.grad).all()
                            for v in model.parameters()
                            if v.grad is not None
                        ]
                    ).all():
                        raise ValueError("nonfinite training gradient")
                    gradients = (
                        {
                            k: float(v.grad.detach().norm().cpu())
                            for k, v in model.named_parameters()
                            if v.grad is not None
                        }
                        if record_update
                        else None
                    )
                    if step <= cfg["training"]["warmup_steps"]:
                        for group in optimizer.param_groups:
                            group["lr"] = (
                                cfg["optimizer"]["lr"] * step / cfg["training"]["warmup_steps"]
                            )
                    lr = [group["lr"] for group in optimizer.param_groups]
                    model_state_status = "UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN"
                    optimizer.step()
                    sync()
                    if not torch.stack([torch.isfinite(v).all() for v in model.parameters()]).all():
                        raise ValueError("nonfinite parameter after update")
                    completed_step = step
                    training_seen += len(index)
                    np.add.at(sampled_rows, index, 1)
                    model_state_status = "LAST_COMPLETED_UPDATE"
                    if scheduler is not None and cfg["training"]["scheduler"] == "cosine":
                        scheduler.step()
                    phase_seconds["update"] += time.monotonic() - tick
                    if packed_supply is not None:
                        packed_supply.release()
                    record = (
                        {
                            **position(),
                            "status": "COMPLETED",
                            "actual_optimizer_step": completed_step,
                            "objective_loss": float(loss.detach().cpu()),
                            "batch_row_mse": float(per_row_loss.detach().mean().cpu()),
                            "batch_rows": len(index),
                            "lr": lr,
                            "gradient_norm": gradients,
                            "samples": samples,
                            "wall_seconds": time.monotonic() - start,
                        }
                        if record_update or not compact
                        else None
                    )
                    if not compact:
                        diagnostics.append(record)
                    if record_update:
                        append_record(batch_log, record)
                        batch_records_logged += 1
                    if selector_point or diagnostic_point:
                        if selector_point:
                            evaluation_steps.add(step)
                        if diagnostic_point:
                            diagnostic_steps.add(step)
                        if evaluate(step, selector_point, diagnostic_point, full_train_point):
                            status = "EARLY_STOPPED"
                            break
                    if not (selector_point or diagnostic_point) and step in checkpoint_steps:
                        save_checkpoint(step)
                else:
                    status = "COMPLETED"
        except RuntimeError as error:
            primary_error = error
            if str(error) != "training budget exhausted":
                status, fault = (
                    "INTERRUPTED",
                    {"type": type(error).__name__, "message": str(error)},
                )
                raise
            status, fault = (
                "BUDGET_STOPPED",
                {"type": type(error).__name__, "message": str(error)},
            )
            _attempt_finalization(
                "primary_stop_record",
                lambda: append_record(
                    batch_log,
                    {
                        "status": status,
                        "fault": fault,
                        **position(),
                        "attempted_step": attempted_step,
                    },
                ),
                stop_record_failures,
            )
        except BaseException as error:
            primary_error = error
            status, fault = ("INTERRUPTED", {"type": type(error).__name__, "message": str(error)})
            _attempt_finalization(
                "primary_stop_record",
                lambda: append_record(
                    batch_log,
                    {
                        "status": status,
                        "fault": fault,
                        **position(),
                        "attempted_step": attempted_step,
                    },
                ),
                stop_record_failures,
            )
            raise
        finally:
            actions = []
            if packed_supply is not None:
                actions.append(("supply_cleanup", packed_supply.close))
            if model_state_status == "LAST_COMPLETED_UPDATE":
                actions.append(("last_checkpoint", lambda: save_named_checkpoint("last")))
            actions.append(("persist", persist))
            _finalize_training(
                output,
                actions,
                primary_error if primary_error is not None else sys.exception(),
                lambda: {
                    "status": status,
                    "fault": fault,
                    **position(),
                    "attempted_step": attempted_step,
                    "model_state_status": model_state_status,
                    "checkpoint_positions": checkpoint_positions,
                },
                prior_failures=stop_record_failures,
            )
    model.load_state_dict(best_state)
    model.eval()
    model = model.cpu()
    if cfg["artifacts"]["mode"] == "native_onnx":

        def trace_charge(module, inputs):
            charge(int(inputs[0].shape[0]), "onnx")

        def trace_completed(module, inputs, result):
            completed_forward_rows["onnx"] += int(inputs[0].shape[0])

        before = model.register_forward_pre_hook(trace_charge)
        after = model.register_forward_hook(trace_completed)
        tick = time.monotonic()
        try:
            torch.onnx.export(
                model,
                tuple((torch.from_numpy(v) for v in corpus.batch([0])[:2]))
                + (torch.ones(1, dtype=torch.long),),
                str(output / "best.onnx"),
                input_names=["features", "distance", "side"],
                output_names=["value"],
                dynamic_axes={
                    "features": {0: "batch"},
                    "distance": {0: "batch"},
                    "side": {0: "batch"},
                    "value": {0: "batch"},
                },
                opset_version=17,
                dynamo=False,
            )
        except BaseException as error:
            status, fault = (
                "ARTIFACT_FAILED",
                {"type": type(error).__name__, "message": str(error)},
            )
            raise
        finally:
            before.remove()
            after.remove()
            phase_seconds["export"] += time.monotonic() - tick
            persist()
    freeze = {
        "schema": "quoridor-candidate-freeze-v2",
        "artifacts_sha256": {name: sha(output / name) for name in FROZEN_ARTIFACTS},
        "best_step": best_step,
        "best_validation_mse": best_loss,
        "selected_exposure": best_exposure,
        "selection_weighting": cfg["evaluation"]["monitor"],
        "evaluation_checkpoints": sorted(evaluation_steps),
        **position(),
        "loss_weighting": cfg["training"]["loss_weighting"],
        "artifact_mode": cfg["artifacts"]["mode"],
        "samples": samples,
        "model_sha": sha(output / "best-model" / "manifest.json"),
        "weights_sha": sha(output / "best-model" / "weights.f32"),
        "initial_weights_sha": sha(output / "initial-model" / "weights.f32"),
        "dataset_sha": binding["dataset_sha"],
        "cache_schema": binding.get("schema"),
        "test_opened": False,
        "wall_seconds": time.monotonic() - start,
    }
    corpus.verify_binding()
    if volume_admission is not None:
        freeze["main_volume_admission"] = {
            "permit_sha256": volume_admission["permit_sha256"],
            "common_input_freeze": volume_admission["common_input_freeze"],
            "input_binding_sha256": volume_admission["input_binding_sha256"],
            "receipt_sha256": sha(output / "main-volume-admission.json"),
        }
    write(output / "freeze.json", freeze)
    persist()
    return freeze


def compact_measurements(corpus, indices, values, constant, distance_fit, train_indices):
    """Aggregate row and model-input-group metrics without per-row/group JSON."""
    import numpy as np

    if not hasattr(corpus, "train_known_groups"):
        corpus.train_known_groups = np.zeros(len(corpus.families), dtype=bool)
        corpus.train_known_groups[corpus.groups[train_indices]] = True
    group_counts = np.zeros(len(corpus.families), dtype=np.int64)
    group_error = np.zeros(len(corpus.families), dtype=np.float64)
    group_distance = np.zeros(len(corpus.families), dtype=np.float64)
    group_constant = np.zeros(len(corpus.families), dtype=np.float64)
    strata = {}
    error_sum = distance_sum = constant_sum = bias = 0.0
    sign_correct = saturated = 0
    for first in range(0, len(indices), 4096):
        sub = indices[first : first + 4096]
        prediction = np.asarray(values[first : first + len(sub)], dtype=np.float32)
        if not np.isfinite(prediction).all():
            raise ValueError("nonfinite compact prediction")
        distance, labels, source, phase = corpus.metadata(sub)
        target = labels[:, 1]
        baseline = np.tanh(
            np.float32(distance_fit["a"])
            + np.float32(distance_fit["b"]) * (distance[:, 1] - distance[:, 0])
        )
        errors = (prediction.astype(np.float64) - target) ** 2
        de = (baseline.astype(np.float64) - target) ** 2
        ce = (np.float32(constant).astype(np.float64) - target) ** 2
        groups = corpus.groups[sub]
        np.add.at(group_counts, groups, 1)
        np.add.at(group_error, groups, errors)
        np.add.at(group_distance, groups, de)
        np.add.at(group_constant, groups, ce)
        error_sum += errors.sum()
        distance_sum += de.sum()
        constant_sum += ce.sum()
        bias += (prediction.astype(np.float64) - target).sum()
        sign_correct += int(np.count_nonzero(prediction * target > 0))
        saturated += int(np.count_nonzero(np.abs(prediction) >= 0.9))
        for dimension, codes in [
            ("source", source),
            ("phase", phase),
            ("original_train_input_known", corpus.train_known_groups[groups].astype(np.int8)),
        ]:
            for code in np.unique(codes):
                mask = codes == code
                pair = strata.setdefault(f"{dimension}:{int(code)}", [0, 0.0])
                pair[0] += int(mask.sum())
                pair[1] += float(errors[mask].sum())
    mask = group_counts > 0
    n = len(indices)
    if not n:
        raise ValueError("empty measurement scope")
    group_mse = float(np.mean(group_error[mask] / group_counts[mask]))
    return {
        "rows": n,
        "input_groups": int(mask.sum()),
        "group_kind": "QF1+distance model input; game/history UNKNOWN",
        "target_mse": float(error_sum / n),
        "z_mse": float(error_sum / n),
        "target_game_equal_mse": group_mse,
        "z_game_equal_mse": group_mse,
        "distance_mse": float(distance_sum / n),
        "constant_mse": float(constant_sum / n),
        "distance_group_equal_mse": float(np.mean(group_distance[mask] / group_counts[mask])),
        "constant_game_equal_mse": float(np.mean(group_constant[mask] / group_counts[mask])),
        "z_sign_accuracy": sign_correct / n,
        "saturation_fraction": saturated / n,
        "bias": float(bias / n),
        "strata": {k: {"rows": v[0], "target_mse": v[1] / v[0]} for k, v in strata.items()},
    }


def _curve_csv(curves, path, *, append=False):
    with Path(path).open("a" if append else "w", newline="") as stream:
        writer = csv.writer(stream)
        if not append:
            writer.writerow(
                [
                    "step",
                    "training_seen",
                    "row_epoch",
                    "completed_epochs",
                    "partial_epoch_fraction",
                    "wall_seconds",
                    "train_group_mse",
                    "validation_group_mse",
                    "train_scope",
                    "train_row_mse",
                    "validation_row_mse",
                    "train_distance_mse",
                    "validation_distance_mse",
                    "train_constant_mse",
                    "validation_constant_mse",
                    "train_sign_accuracy",
                    "validation_sign_accuracy",
                    "train_saturation_fraction",
                    "validation_saturation_fraction",
                    "kind",
                    "used_for_selection",
                    "validation_scope",
                    "train_rows",
                    "validation_rows",
                    *[
                        scope + "_" + metric
                        for metric in (
                            "outcome_steps_raw_mse",
                            "terminal_margin_raw_mse",
                            "outcome_steps_mse",
                            "terminal_margin_mse",
                            "bias",
                            "large_abs_step_score_fraction",
                        )
                        for scope in ("train", "validation")
                    ],
                ]
            )
        for point in curves:
            writer.writerow(
                [
                    point.get(k)
                    for k in [
                        "step",
                        "training_seen",
                        "row_epoch",
                        "completed_epochs",
                        "partial_epoch_fraction",
                        "wall_seconds",
                    ]
                ]
                + [
                    point["train"]["target_game_equal_mse"],
                    point["validation"]["target_game_equal_mse"],
                    point.get(
                        "train_scope",
                        "fixed_diagnostic_subset"
                        if point.get("used_for_selection") is False
                        else None,
                    ),
                    point["train"]["target_mse"],
                    point["validation"]["target_mse"],
                    point["train"].get("distance_mse"),
                    point["validation"].get("distance_mse"),
                    point["train"].get("constant_mse"),
                    point["validation"].get("constant_mse"),
                    point["train"].get("z_sign_accuracy"),
                    point["validation"].get("z_sign_accuracy"),
                    point["train"].get("saturation_fraction"),
                    point["validation"].get("saturation_fraction"),
                    point.get("kind"),
                    point.get("used_for_selection", point.get("kind") == "full_selector"),
                    "fixed_diagnostic_subset"
                    if point.get("used_for_selection") is False
                    else "full_selector",
                    point["train"].get("rows"),
                    point["validation"].get("rows"),
                    *[
                        point[scope].get(metric)
                        for metric in (
                            "outcome_steps_raw_mse",
                            "terminal_margin_raw_mse",
                            "outcome_steps_mse",
                            "terminal_margin_mse",
                            "bias",
                            "large_abs_step_score_fraction",
                        )
                        for scope in ("train", "validation")
                    ],
                ]
            )


FROZEN_ARTIFACTS = (
    "config.json",
    "scale.json",
    "data.json",
    "cache-binding.json.gz",
    "initial.pt",
    "best.pt",
    "initial-model/manifest.json",
    "initial-model/weights.f32",
    "initial-model/training-target.json",
    "best-model/manifest.json",
    "best-model/weights.f32",
    "best-model/training-target.json",
)


def verify_freeze(training):
    training = Path(training)
    freeze = json.loads((training / "freeze.json").read_text())
    if freeze.get("schema") != "quoridor-candidate-freeze-v2":
        raise ValueError("unsupported freeze; historical guarantees cannot be inferred")
    digests = freeze.get("artifacts_sha256")
    if not isinstance(digests, dict) or set(digests) != set(FROZEN_ARTIFACTS):
        raise ValueError("freeze missing required evaluation artifact bindings")
    for name, digest in digests.items():
        if sha(training / name) != digest:
            raise ValueError("frozen evaluation artifact changed: " + name)
    if (
        digests["best-model/manifest.json"] != freeze.get("model_sha")
        or digests["best-model/weights.f32"] != freeze.get("weights_sha")
        or digests["initial-model/weights.f32"] != freeze.get("initial_weights_sha")
    ):
        raise ValueError("freeze native artifact identity differs")
    with gzip.open(training / "cache-binding.json.gz", "rt") as stream:
        binding = json.load(stream)
    data = json.loads((training / "data.json").read_text())
    if (
        binding["dataset_sha"] != freeze.get("dataset_sha")
        or data["binding"]["dataset_sha"] != binding["dataset_sha"]
    ):
        raise ValueError("freeze training input identity differs")
    if freeze.get("cache_schema") != binding.get("schema"):
        raise ValueError("frozen cache schema differs from bound training corpus")
    return freeze


def verify_test_cache_before_open(cache, freeze):
    """Compact train/test share one all-partition manifest; check before labels."""
    manifest = Path(cache) / "cache.json"
    descriptor = json.loads(manifest.read_text()) if manifest.is_file() else {}
    if (
        freeze.get("cache_schema") == "quoridor-public-geometry-v1"
        or descriptor.get("schema") == "quoridor-public-geometry-v1"
    ):
        if (
            not manifest.is_file()
            or descriptor.get("schema") != "quoridor-public-geometry-v1"
            or sha(manifest) != freeze["dataset_sha"]
        ):
            raise ValueError("frozen compact test corpus differs before label opening")


def mapped_values(count, dtype="<f4"):
    import numpy as np

    stream = tempfile.TemporaryFile()
    stream.truncate(count * np.dtype(dtype).itemsize)
    result = np.memmap(stream, dtype=dtype, mode="r+", shape=(count,))
    stream.close()
    return result


def select_values(values, indices, size):
    result = mapped_values(len(indices))
    for first in range(0, len(indices), size):
        result[first : first + size] = values[indices[first : first + size]]
    return result


def write_values(values, path, size):
    import numpy as np

    with Path(path).open("wb") as stream:
        for first in range(0, len(values), size):
            np.asarray(values[first : first + size], dtype="<f4").tofile(stream)


def training_statistics(corpus, indices, column, size=4096):
    import numpy as np

    def metadata_chunks():
        for first in range(0, len(indices), size):
            sub = indices[first : first + size]
            if getattr(corpus, "compact", False):
                distance, labels, _, _ = corpus.metadata(sub)
            else:
                _, distance, labels = corpus.batch(sub)
            yield (distance, labels)

    total = np.zeros(2, dtype=np.float64)
    for d, _ in metadata_chunks():
        total += d.sum(axis=0, dtype=np.float64)
    mu64 = total / len(indices)
    squared = np.zeros(2, dtype=np.float64)
    r = np.empty((0, 2), dtype=np.float64)
    projected = np.empty(0, dtype=np.float64)
    for d, y in metadata_chunks():
        squared += ((d.astype(np.float64) - mu64) ** 2).sum(axis=0)
        if not getattr(corpus, "terminal", False):
            difference = (d[:, 1] - d[:, 0]).astype(np.float64)
            design = np.column_stack((np.ones(len(d)), difference))
            q, r = np.linalg.qr(np.vstack((r, design)), mode="reduced")
            projected = q.T @ np.concatenate((projected, y[:, column].astype(np.float64)))
    if getattr(corpus, "terminal", False):
        return (
            {
                "mu_f32": mu64.astype(np.float32).tolist(),
                "sigma_f32": np.maximum(
                    np.sqrt(squared / len(indices)).astype(np.float32), np.float32(0.0001)
                ).tolist(),
                "distance_input_units": "canonical-integer-D/80",
                "fit_partition": "train",
                "fit_rows": len(indices),
                "sigma_floor_f32": float(np.float32(0.0001)),
                "zero_variance_coordinates": (squared == 0).tolist(),
                "target_independent": True,
                "original_before_reflection": True,
            },
            {"a": 0, "b": 1, "units": "integer-steps"},
        )
    fit, *_ = np.linalg.lstsq(r, projected, rcond=np.finfo(np.float64).eps * max(len(indices), 2))
    return (
        {
            "mu_f32": mu64.astype(np.float32).tolist(),
            "sigma_f32": np.maximum(
                np.sqrt(squared / len(indices)).astype(np.float32), np.float32(0.0001)
            ).tolist(),
        },
        {"a": float(np.float32(fit[0])), "b": float(np.float32(fit[1]))},
    )


def verify_native_parameters(path, state):
    import numpy as np

    native = np.memmap(path, dtype="<f4", mode="r")
    offset = 0
    for key in ("ft.weight", "ft.bias", "h.weight", "h.bias", "out.weight", "out.bias"):
        values = state[key].detach().numpy().reshape(-1)
        for first in range(0, len(values), 4096):
            part = values[first : first + 4096]
            if not np.array_equal(part, native[offset + first : offset + first + len(part)]):
                raise ValueError("frozen checkpoint/native parameters differ")
        offset += len(values)
    if offset != len(native):
        raise ValueError("frozen native parameter count differs")


def test(cache, training, output):
    import numpy as np

    training = Path(training)
    cfg = json.loads((training / "config.json").read_text())
    if cfg["model"].get("architecture") == "distance_steps":
        raise ValueError(
            "new terminal-teacher experiment has T/V only; six-view development is the explicit arena caller, not sealed-label test"
        )
    freeze_path = training / "freeze.json"
    freeze_sha = sha(freeze_path)
    freeze = verify_freeze(training)
    verify_test_cache_before_open(cache, freeze)
    corpus = load(cache, allow_test=True)
    data = json.loads((training / "data.json").read_text())
    stats = json.loads((training / "scale.json").read_text())
    target = cfg["training"]["target"]
    column = {"rootmean": 0, "z": 1}[target]
    validate_target_tensor(corpus.rows, corpus.labels[:, column], target)
    test_index = np.flatnonzero(corpus.splits == 2)
    if not len(test_index):
        raise ValueError("test split empty")
    import torch

    torch.set_num_threads(cfg["training"]["threads"])
    if torch.get_num_interop_threads() != cfg["training"]["threads"]:
        torch.set_num_interop_threads(cfg["training"]["threads"])
    model = build_model(cfg["model"], stats)
    output = Path(output)
    output.mkdir(parents=True)
    predictions, reports = ({}, {})
    primary_count = int(corpus.eligible[test_index].sum())
    checkpoint_predictions = {}
    size = cfg["evaluation"]["batch_size"]
    checkpoint_names = ("best",) if getattr(corpus, "compact", False) else ("initial", "best")
    for name in checkpoint_names:
        digest = freeze["artifacts_sha256"][name + "-model/weights.f32"]
        cp = torch.load(training / (name + ".pt"), map_location="cpu", weights_only=True)
        if (
            cp["model_config"] != cfg["model"]
            or cp["scale"] != stats
            or cp["target"] != target
            or (cp["dataset_sha"] != freeze["dataset_sha"])
        ):
            raise ValueError("checkpoint descriptor differs from frozen evaluation configuration")
        verify_native_parameters(training / (name + "-model/weights.f32"), cp["model"])
        if digest not in checkpoint_predictions:
            model.load_state_dict(cp["model"])
            model.eval()
            values = mapped_values(len(test_index))
            with torch.inference_mode():
                for first in range(0, len(test_index), size):
                    sub = test_index[first : first + size]
                    x, d, _ = corpus.batch(sub)
                    values[first : first + len(sub)] = model(
                        torch.from_numpy(x),
                        torch.from_numpy(d),
                        torch.ones(len(sub), dtype=torch.long),
                    ).numpy()
            checkpoint_predictions[digest] = values
        predictions[name] = checkpoint_predictions[digest]
    predictions["distance"] = mapped_values(len(test_index))
    predictions["constant"] = mapped_values(len(test_index), "<f8")
    fit = data["distance_fit"]
    accumulators = {
        name: (
            MeasurementAccumulator(target, data["constant"]),
            MeasurementAccumulator(target, data["constant"]),
        )
        for name in predictions
    }
    for first in range(0, len(test_index), size):
        sub = test_index[first : first + size]
        _, d, _ = corpus.batch(sub)
        predictions["distance"][first : first + len(sub)] = np.tanh(
            fit["a"] + fit["b"] * (d[:, 1] - d[:, 0])
        )
        predictions["constant"][first : first + len(sub)] = data["constant"]
        for j, row in enumerate(corpus.rows.iter_indices(sub)):
            for name, (all_rows, unexposed) in accumulators.items():
                value = predictions[name][first + j]
                all_rows.add(row, value)
                if row["primary_eligible"]:
                    unexposed.add(row, value)
    for name, (all_rows, unexposed) in accumulators.items():
        reports[name] = {
            "all": all_rows.result(),
            "eligible_heldout_observations"
            if getattr(corpus, "compact", False)
            else "unexposed": unexposed.result() if primary_count else None,
        }
    np.savez(output / "predictions.npz", **predictions)
    result = {
        "freeze_sha": freeze_sha,
        "candidate_sha": freeze["weights_sha"],
        "checkpoint_sha256": {
            name: freeze["artifacts_sha256"][name + ".pt"] for name in checkpoint_names
        },
        "evaluation_cache_binding": corpus.binding,
        "rows": len(test_index),
        "primary_rows": primary_count,
        "metrics": reports,
        "unique_model_forwards": len(checkpoint_predictions),
        "test_reused_for_selection": False,
        "exposure_status": "UNKNOWN; held-out source observations, no unseen-game guarantee"
        if getattr(corpus, "compact", False)
        else "native family exposure protocol",
    }
    if sha(freeze_path) != freeze_sha or verify_freeze(training) != freeze:
        raise ValueError("frozen evaluation inputs mutated during test")
    corpus.verify_binding()
    write(output / "result.json", result)
    return result


def guarded_train(config_path):
    """Launch the maintained trainer once, with exact child ownership and resource caps."""
    import sys

    cfg = json.loads(Path(config_path).read_text())
    from .distance_steps import require_main_volume

    require_main_volume(
        resolve_config(cfg["fit_config"]),
        cache=cfg["cache"],
        config_path=cfg["fit_config"],
        input_binding=cfg.get("input_binding"),
    )
    from .cycle_process import GPUResources, cancellation_signals, execute

    for path, digest in cfg["expected_files_sha256"].items():
        if sha(path) != digest:
            raise ValueError("fixed fit input/source/control changed: " + path)
    admission = json.loads(Path(cfg["storage_admission"]).read_text())
    if admission.get("admission") != "within" or admission.get("errors"):
        raise ValueError("fit storage admission before child/GPU")
    os.sched_setaffinity(0, {2, 3})
    root = Path(cfg["output"]).parent
    started = time.monotonic()
    deadline = None if cfg["seconds"] is None else started + cfg["seconds"]
    resources = GPUResources(cfg["resources"], root, deadline)
    command = [
        sys.executable,
        "-B",
        "-m",
        "quoridor_training.train",
        "train",
        "--cache",
        cfg["cache"],
        "--output",
        cfg["output"],
        "--config",
        cfg["fit_config"],
        "--input-binding",
        cfg["input_binding"],
    ]
    try:
        with cancellation_signals():
            execute(command, root / "fit.log", deadline, resources=resources)
    finally:
        write(
            root / "observed-resources.json",
            {
                **resources.observed,
                "wall_seconds": time.monotonic() - started,
                "sampling": "guardian checks, not continuous absolute peak",
                "controller_reserve_bytes": resources.controller_reserve,
                "whole_device_VRAM_cap_bytes": resources.vram_limit,
                "co_running_pure_compile_NN0_allowed": True,
                "comparative_speed_claim": False,
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "test", "statistics"])
    parser.add_argument("--cache", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config")
    parser.add_argument("--steps", type=int)
    parser.add_argument(
        "--scale", help="explicit distance moments JSON; otherwise train-only moments"
    )
    parser.add_argument("--training")
    parser.add_argument("--input-binding")
    parser.add_argument("--guard-config")
    parser.add_argument(
        "--supply-workers",
        type=int,
        choices=(0, 2),
        help="0: synchronous (default); 2: qualified ordered prefetch",
    )
    args = parser.parse_args()
    if args.command == "statistics":
        if args.guard_config or args.supply_workers is not None:
            parser.error("statistics does not use a fit guard or supply workers")
        print(json.dumps(prepare_statistics(args.cache, args.output)))
        return
    if args.command == "train":
        if args.guard_config:
            if args.supply_workers is not None or args.steps is not None or args.scale is not None:
                parser.error("guarded training uses only its fixed config/input binding")
            guarded_train(args.guard_config)
            return
        print(
            json.dumps(
                train(
                    args.cache,
                    args.output,
                    args.config,
                    args.steps,
                    scale_path=args.scale,
                    input_binding=args.input_binding,
                    supply_workers=args.supply_workers,
                )
            )
        )
    else:
        if not args.training:
            parser.error("test requires --training")
        print(json.dumps(test(args.cache, args.training, args.output)))


if __name__ == "__main__":
    main()
