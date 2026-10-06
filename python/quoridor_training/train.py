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
from pathlib import Path
import numpy as np
from .cache import load, sha

from .common import resolve_config, measurements, selected_teacher_types, validate_target_tensor


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def metrics(rows, prediction, target, constant):
    return measurements(rows, prediction.tolist(), target, constant)


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


def train(cache, output, config_path=None, steps=None, *, scale_path=None):
    start = time.monotonic()
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
        torch.cuda.manual_seed_all(cfg["training"]["seed"])
    binding, rows, x, distances, labels = load(cache)
    target = cfg["training"]["target"]
    column = {"rootmean": 0, "z": 1}[target]
    teacher_types = selected_teacher_types(rows, target)
    validate_target_tensor(rows, labels[:, column], target)
    ix_train = np.array(
        [
            i
            for i, r in enumerate(rows)
            if r["split"] == "train" and r["primary_eligible"] and np.isfinite(labels[i, column])
        ],
        dtype=np.int64,
    )
    ix_validation = np.array(
        [
            i
            for i, r in enumerate(rows)
            if r["split"] == "validation"
            and r["primary_eligible"]
            and np.isfinite(labels[i, column])
        ],
        dtype=np.int64,
    )
    ix_validation_raw = np.array(
        [i for i, r in enumerate(rows) if r["split"] == "validation"], dtype=np.int64
    )
    if not len(ix_train) or not len(ix_validation):
        raise ValueError("nonempty eligible train and unexposed validation required")
    families = {}
    for i in ix_train:
        families.setdefault(rows[i]["group"], []).append(float(labels[i, column]))
    constant = float(np.mean([np.mean(values) for values in families.values()]))
    if scale_path is not None:
        from .scaled_model import validate_statistics

        statistics = validate_statistics(json.loads(Path(scale_path).read_text()))
    else:
        mu = distances[ix_train].mean(axis=0, dtype=np.float64).astype(np.float32)
        sigma = distances[ix_train].std(axis=0, dtype=np.float64).astype(np.float32)
        sigma = np.maximum(sigma, np.float32(1e-4))
        statistics = {"mu_f32": mu.tolist(), "sigma_f32": sigma.tolist()}
    if cfg["model"]["architecture"] == "distance_residual":
        distance_fit = {"a": cfg["model"]["distance_a"], "b": cfg["model"]["distance_b"]}
    else:
        difference = (distances[ix_train, 1] - distances[ix_train, 0]).astype(np.float64)
        design = np.column_stack([np.ones(len(ix_train)), difference])
        fit, *_ = np.linalg.lstsq(design, labels[ix_train, column].astype(np.float64), rcond=None)
        distance_fit = {"a": float(np.float32(fit[0])), "b": float(np.float32(fit[1]))}
    model = build_model(cfg["model"], statistics).to(device)
    initial_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    # Keep the corpus mapped on CPU. Only bounded batches enter GPU memory.
    tx = torch.from_numpy(x)
    td = torch.from_numpy(distances)
    if device == "cuda":
        free, total = torch.cuda.mem_get_info()
        if free <= 2 * 1024**3:
            raise RuntimeError("CUDA host/display reserve leaves no training window")
    # Rust has already ordered the two views STM/opponent in the mapped tensor.
    side = torch.ones(len(rows), dtype=torch.long)
    targets = torch.from_numpy(labels[:, column].copy())
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
    group_indices = [
        np.array([i for i in ix_train if rows[i]["group"] == family]) for family in families
    ]
    group_lengths = np.array([len(group) for group in group_indices], dtype=np.int64)
    group_offsets = np.concatenate([[0], np.cumsum(group_lengths)[:-1]])
    group_flat = np.concatenate(group_indices)
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
        [rows[i]["group"] for i in ix_train],
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
        index = torch.as_tensor(index, dtype=torch.long)
        result = tx[index].to(device), td[index].to(device), side[index].to(device)
        sync()
        phase_seconds["transfer"] += time.monotonic() - tick
        return result

    def predict(indices, kind):
        values = []
        for first in range(0, len(indices), cfg["evaluation"]["batch_size"]):
            sub = indices[first : first + cfg["evaluation"]["batch_size"]]
            inputs = batch(sub)
            charge(len(sub), kind)
            tick = time.monotonic()
            result = model(*inputs)
            sync()
            phase_seconds["inference"] += time.monotonic() - tick
            tick = time.monotonic()
            values.append(result.cpu().numpy())
            phase_seconds["transfer"] += time.monotonic() - tick
            completed_forward_rows[kind] += len(sub)
        return np.concatenate(values)

    def summarize(indices, values):
        selected = [rows[i] for i in indices]
        report = metrics(selected, values, target, constant)
        scope = hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest()
        grouped = {}
        for i, row in enumerate(selected):
            grouped.setdefault(row["group"], []).append(i)
        ordered = sorted(grouped.items())
        if scope not in measurement_sets:
            measurement_sets[scope] = {
                "groups": [group for group, _ in ordered],
                "group_rows": [len(local) for _, local in ordered],
                "input_indices_sha256": scope,
                "rows": len(indices),
                "dataset_sha": binding["dataset_sha"],
            }
            raw = distances[indices]
            baseline = np.tanh(
                np.float32(distance_fit["a"])
                + np.float32(distance_fit["b"]) * (raw[:, 1] - raw[:, 0])
            )
            reference_metrics[scope] = {
                "distance": metrics(selected, baseline, target, constant),
                "constant": constant,
                "group_distance_mse_f32": [
                    float(np.mean((baseline[local] - labels[indices[local], column]) ** 2))
                    for _, local in ordered
                ],
                "group_constant_mse_f32": [
                    float(np.mean((constant - labels[indices[local], column]) ** 2))
                    for _, local in ordered
                ],
            }
            write(output / "measurement-sets.json", measurement_sets)
            write(output / "reference-metrics.json", reference_metrics)
        group_reports = [
            metrics([selected[i] for i in local], values[local], target, constant)
            for _, local in ordered
        ]
        vectors = {
            field: [group[field] if group[field] is not None else np.nan for group in group_reports]
            for field in ("target_mse", "z_sign_accuracy", "saturation_fraction")
        }
        vectors["bias"] = [
            float(np.mean(values[local] - labels[indices[local], column])) for _, local in ordered
        ]
        report["groups"] = {
            "encoding": "little-endian-f32-base64; NaN means missing, never zero",
            "order_ref": scope,
            "fields": {
                field: base64.b64encode(np.asarray(vector, dtype="<f4").tobytes()).decode()
                for field, vector in vectors.items()
            },
        }
        report["distance_ref"] = scope
        report["bias"] = float(np.mean(values - labels[indices, column]))
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
                json.dump([rows[i]["id"] for i in indices], stream)

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
                pval = praw[primary_in_raw] if scheduled else praw
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
                reused.update({int(i): float(v) for i, v in zip(current_train_eval, ptrain)})
                reused.update({int(i): float(v) for i, v in zip(ix_validation, pval)})
                if scheduled:
                    ptrain.astype("<f4").tofile(output / f"train-step{step}.f32")
                    praw.astype("<f4").tofile(output / f"validation-step{step}.f32")
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
                "completed_records": len(diagnostics),
            },
        )
        for name, records in [("curves", curve), ("diagnostic-curves", diagnostic_curve)]:
            _curve_csv(records, output / (name + ".csv"))
            _plot(records, output / (name + ".svg"))
        write(
            output / "sampling.json",
            {
                **position(),
                "seen": int(sampled_rows.sum()),
                "mode": mode,
                "row_count_order": "immutable loaded cache order",
                "attempted_step": attempted_step,
                "optimizer_steps": completed_step,
                "training_indices": ix_train.tolist(),
                "training_rows": len(ix_train),
                "row_counts": sampled_rows.tolist(),
                "attempted_row_counts": attempted_rows.tolist(),
                "training_row_min_visits": int(sampled_rows[ix_train].min()),
                "training_row_max_visits": int(sampled_rows[ix_train].max()),
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
                        prediction, targets[ix].to(device), reduction="none"
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
                (tx[:1].cpu(), td[:1].cpu(), side[:1].cpu()),
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
        "schema": "quoridor-candidate-freeze-v1",
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
        "test_opened": False,
        "wall_seconds": time.monotonic() - start,
    }
    write(output / "freeze.json", freeze)
    persist()
    return freeze


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
                ]
            )


def _plot(curves, path):
    # Scientific curve artifact without a plotting dependency in the hot loader.
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="390">',
        '<rect width="720" height="390" fill="white"/>',
    ]
    if not curves:
        Path(path).write_text(
            "\n".join(lines + ['<text x="20" y="30">No completed observation</text>', "</svg>"])
        )
        return
    axis = "row_epoch" if all(c.get("completed_epochs") is not None for c in curves) else "step"
    max_step = max(c[axis] for c in curves) or 1
    max_y = (
        max(c[key]["target_game_equal_mse"] for c in curves for key in ["train", "validation"]) or 1
    )
    for key, color in [("train", "#1261a0"), ("validation", "#c33")]:
        points = " ".join(
            f"{45 + 630 * c[axis] / max_step:.2f},{320 - 270 * c[key]['target_game_equal_mse'] / max_y:.2f}"
            for c in curves
        )
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/><text x="550" y="{20 if key == "train" else 40}" fill="{color}">{key}</text>'
        )
    lines += [
        '<path d="M45 40V320H675" fill="none" stroke="black"/>',
        f'<text x="310" y="360">{"Epochs" if axis == "row_epoch" else "Optimizer steps"}</text>',
        '<text x="8" y="25">Game equal MSE</text>',
        "</svg>",
    ]
    Path(path).write_text("\n".join(lines))


def test(cache, training, output):
    import torch

    training = Path(training)
    freeze_path = training / "freeze.json"
    freeze_sha = sha(freeze_path)
    freeze = json.loads(freeze_path.read_text())
    if (
        sha(training / "best-model" / "manifest.json") != freeze["model_sha"]
        or sha(training / "best-model" / "weights.f32") != freeze["weights_sha"]
    ):
        raise ValueError("frozen candidate changed")
    binding, rows, x, distance, labels = load(cache, allow_test=True)
    test_index = np.array([i for i, r in enumerate(rows) if r["split"] == "test"], dtype=np.int64)
    if not len(test_index):
        raise ValueError("test split empty")
    cfg = json.loads((training / "config.json").read_text())
    data = json.loads((training / "data.json").read_text())
    torch.set_num_threads(cfg["training"]["threads"])
    torch.set_num_interop_threads(cfg["training"]["threads"])
    stats = json.loads((training / "scale.json").read_text())
    model = build_model(cfg["model"], stats)
    tx = torch.from_numpy(x[test_index])
    td = torch.from_numpy(distance[test_index])
    side = torch.ones(len(test_index), dtype=torch.long)
    output = Path(output)
    output.mkdir(parents=True)
    predictions, reports = {}, {}
    selected_rows = [rows[i] for i in test_index]
    primary = np.array([i for i, r in enumerate(selected_rows) if r["primary_eligible"]])
    weight_predictions = {}
    for name in ["initial", "best"]:
        cp = torch.load(training / (name + ".pt"), map_location="cpu", weights_only=True)
        model.load_state_dict(cp["model"])
        weight_digest = sha(training / (name + "-model") / "weights.f32")
        if weight_digest not in weight_predictions:
            model.eval()
            with torch.inference_mode():
                weight_predictions[weight_digest] = model(tx, td, side).numpy()
        predictions[name] = weight_predictions[weight_digest]
    fit = data["distance_fit"]
    predictions["distance"] = np.tanh(
        fit["a"] + fit["b"] * (distance[test_index, 1] - distance[test_index, 0])
    )
    predictions["constant"] = np.full(len(test_index), data["constant"])
    for name, pred in predictions.items():
        reports[name] = {
            "all": metrics(selected_rows, pred, cfg["training"]["target"], data["constant"]),
            "unexposed": metrics(
                [selected_rows[i] for i in primary],
                pred[primary],
                cfg["training"]["target"],
                data["constant"],
            )
            if len(primary)
            else None,
        }
    np.savez(output / "predictions.npz", **predictions)
    result = {
        "freeze_sha": freeze_sha,
        "candidate_sha": freeze["weights_sha"],
        "rows": len(selected_rows),
        "primary_rows": len(primary),
        "metrics": reports,
        "unique_model_forwards": len(weight_predictions),
        "test_reused_for_selection": False,
    }
    write(output / "result.json", result)
    if sha(freeze_path) != freeze_sha:
        raise ValueError("freeze mutated during test")
    return result


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
    args = parser.parse_args()
    if args.command == "train":
        print(
            json.dumps(
                train(args.cache, args.output, args.config, args.steps, scale_path=args.scale)
            )
        )
    else:
        if not args.training:
            parser.error("test requires --training")
        print(json.dumps(test(args.cache, args.training, args.output)))


if __name__ == "__main__":
    main()
