"""Bulk native tensor loader with the maintained QF1 Model and configuration.

Validation selects a checkpoint; test is opened only by a later frozen invocation.
Model/optimizer definitions live in this package.
"""

import argparse
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
    write(path / "manifest.json", manifest)
    return path / "manifest.json"


def train(cache, output, config_path=None, steps=None):
    import torch
    from .scaled_model import build_model

    start = time.monotonic()
    cfg = resolve_config(config_path)
    if config_path is None:
        cfg["optimizer"]["lr"] = 1e-4
    if steps is not None:
        cfg["training"]["steps"] = steps
    torch.set_num_threads(cfg["training"]["threads"])
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
    if not len(ix_train) or not len(ix_validation):
        raise ValueError("nonempty eligible train and unexposed validation required")
    families = {}
    for i in ix_train:
        families.setdefault(rows[i]["group"], []).append(float(labels[i, column]))
    constant = float(np.mean([np.mean(values) for values in families.values()]))
    mu = distances[ix_train].mean(axis=0, dtype=np.float64).astype(np.float32)
    sigma = distances[ix_train].std(axis=0, dtype=np.float64).astype(np.float32)
    sigma = np.maximum(sigma, np.float32(1e-4))
    statistics = {"mu_f32": mu.tolist(), "sigma_f32": sigma.tolist()}
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
    output.mkdir()
    write(output / "config.json", cfg)
    write(output / "scale.json", statistics)
    write(
        output / "data.json",
        {
            "binding": binding,
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
    curve, diagnostics = [], []
    group_indices = [
        np.array([i for i in ix_train if rows[i]["group"] == family]) for family in families
    ]
    group_lengths = np.array([len(group) for group in group_indices], dtype=np.int64)
    group_offsets = np.concatenate([[0], np.cumsum(group_lengths)[:-1]])
    group_flat = np.concatenate(group_indices)
    selection_rows = [rows[i] for i in ix_validation]
    evaluation_steps = {0, 1, 2, 5, 10, 20, 50, 100, cfg["training"]["steps"]}
    evaluation_steps.update(range(0, cfg["training"]["steps"] + 1, cfg["evaluation"]["interval"]))

    def charge(n):
        nonlocal samples
        if (
            samples + n > cfg["limits"]["samples"]
            or time.monotonic() - start > cfg["limits"]["seconds"]
        ):
            raise RuntimeError("training budget exhausted")
        samples += n

    def gpu_guard():
        if device == "cuda" and torch.cuda.mem_get_info()[0] < 2 * 1024**3:
            raise RuntimeError("CUDA reserve exhausted")

    def batch(index):
        gpu_guard()
        index = torch.as_tensor(index, dtype=torch.long)
        return tx[index].to(device), td[index].to(device), side[index].to(device)

    def predict(indices):
        values = []
        for first in range(0, len(indices), cfg["evaluation"]["batch_size"]):
            inputs = batch(indices[first : first + cfg["evaluation"]["batch_size"]])
            values.append(model(*inputs).cpu().numpy())
        return np.concatenate(values)

    def evaluate(step):
        nonlocal best_step, best_loss, best_state
        charge(len(ix_train) + len(ix_validation))
        model.eval()
        with torch.inference_mode():
            ptrain = predict(ix_train)
            pval = predict(ix_validation)
        tr = metrics([rows[i] for i in ix_train], ptrain, target, constant)
        va = metrics(selection_rows, pval, target, constant)
        loss = va["target_game_equal_mse"]
        curve.append(
            {
                "step": step,
                "samples": samples,
                "wall_seconds": time.monotonic() - start,
                "train": tr,
                "validation": va,
            }
        )
        if loss < best_loss - cfg["evaluation"]["min_delta"]:
            best_step, best_loss = step, loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        return ptrain

    evaluate(0)
    for step in range(1, cfg["training"]["steps"] + 1):
        charge(cfg["training"]["batch_size"])
        if cfg["training"]["sampling"] == "game":
            group_ix = torch.randint(
                len(group_indices),
                (cfg["training"]["batch_size"],),
                generator=generator,
            ).numpy()
            uniform = torch.rand(cfg["training"]["batch_size"], generator=generator).numpy()
            within = (uniform * group_lengths[group_ix]).astype(np.int64)
            index = group_flat[group_offsets[group_ix] + within]
        else:
            index = ix_train[
                torch.randint(
                    len(ix_train), (cfg["training"]["batch_size"],), generator=generator
                ).numpy()
            ]
        ix = torch.as_tensor(index, dtype=torch.long)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        prediction = model(*batch(ix))
        loss = torch.nn.functional.mse_loss(prediction, targets[ix].to(device))
        if not torch.isfinite(loss):
            raise ValueError("nonfinite training loss")
        loss.backward()
        gradients = {
            k: float(v.grad.detach().norm().cpu())
            for k, v in model.named_parameters()
            if v.grad is not None
        }
        optimizer.step()
        if scheduler is not None:
            scheduler.step()
        diagnostics.append(
            {
                "step": step,
                "batch_mse": float(loss.detach().cpu()),
                "gradient_norm": gradients,
            }
        )
        if step in evaluation_steps:
            evaluate(step)
    last_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    for name, state in [
        ("initial", initial_state),
        ("best", best_state),
        ("last", last_state),
    ]:
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
    write(output / "curves.json", curve)
    write(output / "gradients.json", diagnostics)
    model.load_state_dict(best_state)
    model.eval()
    # ONNX is a cold interchange artifact. Rust NNUE consumes the compact raw
    # weights above; no Python or ONNX inference is performed in each search node.
    witness = (tx[:1].cpu(), td[:1].cpu(), side[:1].cpu())
    model = model.cpu()
    torch.onnx.export(
        model,
        witness,
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
    freeze = {
        "schema": "quoridor-candidate-freeze-v1",
        "best_step": best_step,
        "best_validation_game_mse": best_loss,
        "samples": samples,
        "model_sha": sha(output / "best-model" / "manifest.json"),
        "weights_sha": sha(output / "best-model" / "weights.f32"),
        "initial_weights_sha": sha(output / "initial-model" / "weights.f32"),
        "dataset_sha": binding["dataset_sha"],
        "test_opened": False,
        "wall_seconds": time.monotonic() - start,
    }
    write(output / "freeze.json", freeze)
    _plot(curve, output / "learning-curves.svg")
    return freeze


def _plot(curves, path):
    # Scientific curve artifact without a plotting dependency in the hot loader.
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="390">',
        '<rect width="720" height="390" fill="white"/>',
    ]
    max_step = max(c["step"] for c in curves) or 1
    max_y = (
        max(c[key]["target_game_equal_mse"] for c in curves for key in ["train", "validation"]) or 1
    )
    for key, color in [("train", "#1261a0"), ("validation", "#c33")]:
        points = " ".join(
            f"{45 + 630 * c['step'] / max_step:.2f},{320 - 270 * c[key]['target_game_equal_mse'] / max_y:.2f}"
            for c in curves
        )
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/><text x="550" y="{20 if key == "train" else 40}" fill="{color}">{key}</text>'
        )
    lines += [
        '<path d="M45 40V320H675" fill="none" stroke="black"/>',
        '<text x="310" y="360">Optimizer steps</text>',
        '<text x="8" y="25">Game equal MSE</text>',
        "</svg>",
    ]
    Path(path).write_text("\n".join(lines))


def test(cache, training, output):
    import torch
    from .scaled_model import build_model

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
    output.mkdir()
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
    parser.add_argument("--training")
    args = parser.parse_args()
    if args.command == "train":
        print(json.dumps(train(args.cache, args.output, args.config, args.steps)))
    else:
        if not args.training:
            parser.error("test requires --training")
        print(json.dumps(test(args.cache, args.training, args.output)))


if __name__ == "__main__":
    main()
