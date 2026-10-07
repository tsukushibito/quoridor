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
import time
import tempfile
import os
from pathlib import Path
import numpy as np
from .cache import load, sha

from .common import (
    resolve_config,
    selected_teacher_types,
    validate_target_tensor,
    MeasurementAccumulator,
)


def write(path, value):
    with Path(path).open("w") as stream:
        stream_json(stream, value)
        stream.write("\n")


def stream_json(stream, value):
    """Serialize compact arrays and row iterators without materializing JSON lists."""
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
    if config.get("architecture", "scaled") == "distance_residual":
        from .residual_model import DistanceResidualModel

        return DistanceResidualModel(
            config, statistics, a=config["distance_a"], b=config["distance_b"]
        )
    from .scaled_model import build_model as build_scaled

    return build_scaled(config, statistics)


def export(model, config, statistics, distance_fit, path):
    path = Path(path)
    path.mkdir()
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
    write(path / "training-target.json", {"training_target": config["training"]["target"]})
    write(path / "manifest.json", manifest)
    return path / "manifest.json"


def train(cache, output, config_path=None, steps=None, *, scale_path=None, input_binding=None):
    start = time.monotonic()
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    import torch

    cfg = resolve_config(config_path, (() if steps is None else (f"training.steps={steps}",)))
    if config_path is None:
        cfg["optimizer"]["lr"] = 1e-4
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
    binding, rows, labels = corpus.binding, corpus.rows, corpus.labels
    target = cfg["training"]["target"]
    column = {"rootmean": 0, "z": 1}[target]
    compact = getattr(corpus, "compact", False)
    if compact and (
        target != "z"
        or cfg["training"]["sampling"] != "epoch"
        or cfg["training"]["loss_weighting"] != "row"
        or cfg["evaluation"]["monitor"] != "row"
    ):
        raise ValueError(
            "public compact corpus requires decisive z / row epoch objective and row monitor"
        )
    if compact and (
        corpus.manifest.get("original_only") is not True
        or corpus.manifest.get("dataset_revision") != "original-only-v2"
    ):
        raise ValueError("public fit requires adopted original-only-v2 observations")
    teacher_types = {"external_outcome"} if compact else selected_teacher_types(rows, target)
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
        group_indices, families = [], []
        constant = float(np.mean(labels[ix_train, column], dtype=np.float64))
    else:
        codes = corpus.groups[ix_train]
        family_codes, seen_codes = [], set()
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
    statistics, fitted = training_statistics(corpus, ix_train, column)
    if input_binding is not None:
        expected = json.loads(Path(input_binding).read_text())
        expected_scale = json.loads(Path(expected["scale_artifact"]).read_text())
        constant_path = Path(expected["scale_artifact"]).with_name("train-only-constant-v2.json")
        expected_constant = json.loads(constant_path.read_text())
        if (
            binding["dataset_sha"] != expected["cache_manifest_sha"]
            or statistics["mu_f32"] != expected_scale["mu_f32"]
            or statistics["sigma_f32"] != expected_scale["sigma_f32"]
            or constant != expected_constant["row_mean_constant"]
            or scale_path is not None
        ):
            raise ValueError("fit train-only statistics/constant/input binding mismatch")
    if scale_path is not None:
        from .scaled_model import validate_statistics

        statistics = validate_statistics(json.loads(Path(scale_path).read_text()))
    distance_fit = (
        {"a": cfg["model"]["distance_a"], "b": cfg["model"]["distance_b"]}
        if cfg["model"]["architecture"] == "distance_residual"
        else fitted
    )
    model = build_model(cfg["model"], statistics).to(device)
    initial_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if device == "cuda":
        free, total = torch.cuda.mem_get_info()
        if free <= 2 * 1024**3:
            raise RuntimeError("CUDA host/display reserve leaves no training window")
    generator = torch.Generator().manual_seed(cfg["training"]["seed"] + 1)
    optimizers = {
        "adam": torch.optim.Adam,
        "adamw": torch.optim.AdamW,
        "sgd": torch.optim.SGD,
    }
    opt_kwargs = {
        "lr": cfg["optimizer"]["lr"],
        "weight_decay": cfg["optimizer"]["weight_decay"],
    }
    if cfg["optimizer"]["name"] == "sgd":
        opt_kwargs["momentum"] = cfg["optimizer"]["momentum"]
    optimizer = optimizers[cfg["optimizer"]["name"]](model.parameters(), **opt_kwargs)
    scheduler = (
        torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, cfg["training"]["steps"])
        if cfg["training"]["scheduler"] == "cosine"
        else None
    )
    output = Path(output)
    output.mkdir(parents=True)
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
    samples, best_step, best_loss, best_state = 0, 0, float("inf"), initial_state
    curve, diagnostics, diagnostic_curve = [], [], []
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
    )

    mode = cfg["training"]["sampling"]
    batch_size = cfg["training"]["batch_size"]
    evaluation_steps = observation_steps(
        cfg["training"]["steps"],
        cfg["evaluation"]["interval"],
        len(ix_train),
        batch_size,
        mode,
        cfg["evaluation"]["checkpoints"],
    )
    diagnostic_steps = (
        observation_steps(
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
        # Target-blind fixed subset, independent of the epoch sampler generator.
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
            rows,
            ix_train,
            cfg["evaluation"]["diagnostic_rows"],
            cfg["training"]["seed"],
        )
        diag_val = diagnostic_indices(
            rows,
            ix_validation,
            cfg["evaluation"]["diagnostic_rows"],
            cfg["training"]["seed"],
        )
    train_eval = ix_train if cfg["evaluation"]["full_train"] else diag_train
    if not len(train_eval):
        raise ValueError("full_train=false requires nonempty diagnostic subset")
    epoch_sampler = (
        EpochSampler(ix_train, batch_size, cfg["training"]["seed"]) if mode == "epoch" else None
    )
    stopper = EarlyStopping(
        cfg["evaluation"]["early_stopping_patience"], cfg["evaluation"]["min_delta"]
    )
    sampled_rows = np.zeros(len(rows), dtype=np.int64)
    attempted_rows = np.zeros(len(rows), dtype=np.int64)
    training_seen, completed_step, attempted_step = 0, 0, 0
    best_exposure = None
    row_loss_weights = np.zeros(len(rows), dtype=np.float32)
    row_loss_weights[ix_train] = loss_weights(
        corpus.groups[ix_train],
        cfg["training"]["loss_weighting"],
    )
    objective_weights = torch.as_tensor(row_loss_weights)
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
    forward_rows = {"train": 0, "full_selector": 0, "diagnostic": 0, "onnx": 0}
    completed_forward_rows = dict(forward_rows)
    status, fault, model_state_status = "RUNNING", None, "LAST_COMPLETED_UPDATE"
    last_completed_point = None
    measurement_sets, reference_metrics = {}, {}

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
            samples + n > cfg["limits"]["samples"]
            or time.monotonic() - start > cfg["limits"]["seconds"]
        ):
            raise RuntimeError("training budget exhausted")
        samples += n
        forward_rows[kind] += n

    def batch(index):
        if device == "cuda" and torch.cuda.mem_get_info()[0] < 2 * 1024**3:
            raise RuntimeError("CUDA reserve exhausted")
        tick = time.monotonic()
        features, distances, _ = corpus.batch(index)
        result = (
            torch.from_numpy(features).to(device),
            torch.from_numpy(distances).to(device),
            torch.ones(len(index), dtype=torch.long, device=device),
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
        if compact:
            return compact_measurements(corpus, indices, values, constant, distance_fit, ix_train)
        scope = hashlib.sha256(np.asarray(indices, dtype="<i8")).hexdigest()
        measured = MeasurementAccumulator(target, constant)
        reference = MeasurementAccumulator(target, constant)
        group_distance, group_constant = {}, {}
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
        "algorithm": "sha256(seed:input-row-id), index tie; sorted loaded-index output",
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
            "full_selector_steps": sorted(evaluation_steps),
            "fixed_diagnostic_steps": sorted(diagnostic_steps),
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

    def evaluate(step, selector, diagnostic):
        nonlocal best_step, best_loss, best_state, best_exposure, last_completed_point
        tick = time.monotonic()
        model.eval()
        reused = {}
        stop = False
        with torch.inference_mode():
            if selector:
                current_train_eval = (
                    ix_train if step in cfg["evaluation"]["full_train_checkpoints"] else train_eval
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
                    if cfg["evaluation"]["full_train"]
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
                    if boundary:
                        _, stop = stopper.observe(loss)
                    improved = loss < best_loss
                else:
                    improved, stop = stopper.observe(loss)
                if improved:
                    best_step, best_loss = step, loss
                    best_state = {
                        k: v.detach().cpu().clone() for k, v in model.state_dict().items()
                    }
                    best_exposure = position()
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
                    "used_for_selection": False,
                }
                diagnostic_curve.append(curve_summary(record, "fixed_diagnostic"))
                last_completed_point = {"kind": "fixed_diagnostic", **position()}
                append_record(observation_log, {"kind": "fixed_diagnostic", **record})
                phase_seconds["fixed_diagnostic"] += time.monotonic() - tick
        if step in checkpoint_steps:
            save_checkpoint(step)
        return stop

    def persist():
        tick = time.monotonic()
        write(output / "curves.json", curve)
        write(output / "diagnostic-curves.json", diagnostic_curve)
        write(
            output / "gradients.json",
            {
                "schema": "quoridor-gradient-stream-reference-v1",
                "file": "batch.jsonl.gz",
                "record_status": "COMPLETED",
                "field": "gradient_norm",
                "completed_records": completed_step,
            },
        )
        for name, records in [("curves", curve), ("diagnostic-curves", diagnostic_curve)]:
            _curve_csv(records, output / (name + ".csv"))
        if compact:
            np.savez_compressed(
                output / "sampling-counts.npz",
                training_indices=ix_train,
                row_counts=sampled_rows,
                attempted_row_counts=attempted_rows,
            )
        write(
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
                "family_counts": {
                    family: int(sampled_rows[group].sum())
                    for family, group in zip(families, group_indices)
                },
                "loss_weighting": cfg["training"]["loss_weighting"],
                "sampler_advanced_seen": epoch_sampler.seen if epoch_sampler else None,
            },
        )
        phase_seconds["logging"] += time.monotonic() - tick
        write(
            output / "run-status.json",
            {
                "status": status,
                "fault": fault,
                **position(),
                "attempted_step": attempted_step,
                "model_state_status": model_state_status,
                "selected_exposure": best_exposure,
                "last_completed_point": last_completed_point,
                "samples": samples,
                "forward_rows_conservative": forward_rows,
                "forward_rows_completed": completed_forward_rows,
                "phase_seconds_inclusive": phase_seconds,
                "wall_seconds": time.monotonic() - start,
                "timing_overlap": "inclusive/nested; do not add phases to infer whole wall",
            },
        )

    def curve_summary(record, kind):
        result = dict(record)
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
        try:
            if evaluate(0, True, 0 in diagnostic_steps):
                status = "EARLY_STOPPED"
            else:
                for step in range(1, cfg["training"]["steps"] + 1):
                    attempted_step = step
                    # Budget check before consuming the sampler. charge() runs immediately before forward.
                    n = epoch_sampler.next_batch_size if epoch_sampler else batch_size
                    if (
                        samples + n > cfg["limits"]["samples"]
                        or time.monotonic() - start > cfg["limits"]["seconds"]
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
                    inputs = batch(ix)
                    charge(len(index), "train")
                    tick = time.monotonic()
                    prediction = model(*inputs)
                    sync()
                    phase_seconds["inference"] += time.monotonic() - tick
                    completed_forward_rows["train"] += len(index)
                    per_row_loss = torch.nn.functional.mse_loss(
                        prediction,
                        torch.from_numpy(labels[index, column].copy()).to(device),
                        reduction="none",
                    )
                    loss = (per_row_loss * objective_weights[ix].to(device)).mean()
                    if not torch.isfinite(loss):
                        raise ValueError("nonfinite training loss")
                    tick = time.monotonic()
                    loss.backward()
                    gradients = {
                        k: float(v.grad.detach().norm().cpu())
                        for k, v in model.named_parameters()
                        if v.grad is not None
                    }
                    lr = [group["lr"] for group in optimizer.param_groups]
                    model_state_status = "UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN"
                    optimizer.step()
                    sync()
                    completed_step = step
                    training_seen += len(index)
                    np.add.at(sampled_rows, index, 1)
                    model_state_status = "LAST_COMPLETED_UPDATE"
                    if scheduler is not None:
                        scheduler.step()
                    phase_seconds["update"] += time.monotonic() - tick
                    record = {
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
                    if not compact:
                        diagnostics.append(record)
                    append_record(batch_log, record)
                    if step in evaluation_steps or step in diagnostic_steps:
                        if evaluate(step, step in evaluation_steps, step in diagnostic_steps):
                            status = "EARLY_STOPPED"
                            break
                    elif step in checkpoint_steps:
                        save_checkpoint(step)
                else:
                    status = "COMPLETED"
        except RuntimeError as error:
            if str(error) != "training budget exhausted":
                status, fault = "INTERRUPTED", {"type": type(error).__name__, "message": str(error)}
                raise
            status, fault = "BUDGET_STOPPED", {"type": type(error).__name__, "message": str(error)}
            append_record(
                batch_log,
                {"status": status, "fault": fault, **position(), "attempted_step": attempted_step},
            )
        except BaseException as error:
            status, fault = "INTERRUPTED", {"type": type(error).__name__, "message": str(error)}
            append_record(
                batch_log,
                {"status": status, "fault": fault, **position(), "attempted_step": attempted_step},
            )
            raise
        finally:
            persist()

    tick = time.monotonic()
    last_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    for name, state in [("initial", initial_state), ("best", best_state), ("last", last_state)]:
        torch.save(
            {
                "model": state,
                "model_config": cfg["model"],
                "scale": statistics,
                "target": target,
                "dataset_sha": binding["dataset_sha"],
            },
            output / (name + ".pt"),
        )
        model.load_state_dict(state)
        export(model, cfg, statistics, distance_fit, output / (name + "-model"))
    phase_seconds["export"] += time.monotonic() - tick
    model.load_state_dict(best_state)
    model.eval()
    model = model.cpu()
    if cfg["artifacts"]["mode"] == "native_onnx":
        # Exporter trace count depends on its version; hooks charge each actual call.
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
                tuple(torch.from_numpy(v) for v in corpus.batch([0])[:2])
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
            status, fault = "ARTIFACT_FAILED", {"type": type(error).__name__, "message": str(error)}
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
    write(output / "freeze.json", freeze)
    persist()
    return freeze


def compact_measurements(corpus, indices, values, constant, distance_fit, train_indices):
    """Aggregate row and model-input-group metrics without per-row/group JSON."""
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
        # Metadata is gathered by bounded batches. No dense full-corpus tensor.
        _, distance, labels = corpus.batch(sub)
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
        source = np.fromiter((int(corpus.record(int(i))["shard"]) for i in sub), dtype=np.int16)
        phase = np.fromiter((int(corpus.record(int(i))["phase"]) for i in sub), dtype=np.int8)
        for dimension, codes in [
            ("source", source),
            ("phase", phase),
            ("train_input_known", corpus.train_known_groups[groups].astype(np.int8)),
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


def _curve_csv(curves, path):
    with Path(path).open("w", newline="") as stream:
        writer = csv.writer(stream)
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
                    point.get("train_scope"),
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
        freeze.get("cache_schema") == "quoridor-public-compact-v1"
        or descriptor.get("schema") == "quoridor-public-compact-v1"
    ):
        if (
            not manifest.is_file()
            or descriptor.get("schema") != "quoridor-public-compact-v1"
            or sha(manifest) != freeze["dataset_sha"]
        ):
            raise ValueError("frozen compact test corpus differs before label opening")


def mapped_values(count, dtype="<f4"):
    # Anonymous disk-backed arrays bound prediction RAM even for full selectors.
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
    with Path(path).open("wb") as stream:
        for first in range(0, len(values), size):
            np.asarray(values[first : first + size], dtype="<f4").tofile(stream)


def training_statistics(corpus, indices, column, size=4096):
    total = np.zeros(2, dtype=np.float64)
    for _, (_, d, _) in corpus.chunks(indices, size):
        total += d.sum(axis=0, dtype=np.float64)
    mu64 = total / len(indices)
    squared = np.zeros(2, dtype=np.float64)
    # Incremental QR preserves the least-squares objective without a full design matrix.
    r = np.empty((0, 2), dtype=np.float64)
    projected = np.empty(0, dtype=np.float64)
    for _, (_, d, y) in corpus.chunks(indices, size):
        squared += ((d.astype(np.float64) - mu64) ** 2).sum(axis=0)
        difference = (d[:, 1] - d[:, 0]).astype(np.float64)
        design = np.column_stack((np.ones(len(d)), difference))
        q, r = np.linalg.qr(np.vstack((r, design)), mode="reduced")
        projected = q.T @ np.concatenate((projected, y[:, column].astype(np.float64)))
    fit, *_ = np.linalg.lstsq(r, projected, rcond=np.finfo(np.float64).eps * max(len(indices), 2))
    return (
        {
            "mu_f32": mu64.astype(np.float32).tolist(),
            "sigma_f32": np.maximum(
                np.sqrt(squared / len(indices)).astype(np.float32), np.float32(1e-4)
            ).tolist(),
        },
        {"a": float(np.float32(fit[0])), "b": float(np.float32(fit[1]))},
    )


def verify_native_parameters(path, state):
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
    training = Path(training)
    freeze_path = training / "freeze.json"
    freeze_sha = sha(freeze_path)
    # No model construction or forward may precede complete attribution checks.
    freeze = verify_freeze(training)
    verify_test_cache_before_open(cache, freeze)
    corpus = load(cache, allow_test=True)
    cfg = json.loads((training / "config.json").read_text())
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
    predictions, reports = {}, {}
    primary_count = int(corpus.eligible[test_index].sum())
    # Verify checkpoint/native parameter correspondence before sharing model forwards.
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
            or cp["dataset_sha"] != freeze["dataset_sha"]
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
            (
                "eligible_heldout_observations"
                if getattr(corpus, "compact", False)
                else "unexposed"
            ): unexposed.result() if primary_count else None,
        }
    # numpy's zip writer streams array storage rather than constructing a combined tensor.
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
    from .cycle_process import GPUResources, cancellation_signals, execute

    cfg = json.loads(Path(config_path).read_text())
    for path, digest in cfg["expected_files_sha256"].items():
        if sha(path) != digest:
            raise ValueError("fixed fit input/source/control changed: " + path)
    admission = json.loads(Path(cfg["storage_admission"]).read_text())
    if admission.get("admission") != "within" or admission.get("errors"):
        raise ValueError("fit storage admission before child/GPU")
    os.sched_setaffinity(0, {2, 3})
    root = Path(cfg["output"]).parent
    deadline = time.monotonic() + cfg["seconds"]
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
                "wall_seconds": cfg["seconds"] - max(0, deadline - time.monotonic()),
                "sampling": "guardian checks, not continuous absolute peak",
                "controller_reserve_bytes": resources.controller_reserve,
                "whole_device_VRAM_cap_bytes": resources.vram_limit,
                "co_running_pure_compile_NN0_allowed": True,
                "comparative_speed_claim": False,
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "test"])
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
    args = parser.parse_args()
    if args.command == "train":
        if args.guard_config:
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
                )
            )
        )
    else:
        if not args.training:
            parser.error("test requires --training")
        print(json.dumps(test(args.cache, args.training, args.output)))


if __name__ == "__main__":
    main()
