"""Current generic QF1 learner; explicit data, run budget and optional scale.

This maintained entry uses the shared dataset/model contracts. The immutable
train.py entry remains for historical SHA-bound experiment adapters. No frame
loader, runtime source patching, or fixed diagnostic schedule is used here.
Import and --dry-run perform no Torch import, model forward, or training.
"""

import argparse
import hashlib
import json
import re
import subprocess
import time
import traceback
from pathlib import Path

from common import EarlyStopping, measurements, resolve_config, write_json
from dataset import load_data
from scaled_model import build_model as build_scaled_model, load_statistics

SOURCE_FILES = (
    "learner.py",
    "common.py",
    "dataset.py",
    "qf1.py",
    "model.py",
    "scaled_model.py",
)


class BudgetExceeded(Exception):
    pass


def train(args, *, model_factory=None, model_sources=()):
    start = time.monotonic()
    scaling_path = getattr(args, "scale_statistics", None)
    statistics, scaling_info = load_statistics(scaling_path) if scaling_path else (None, None)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("run id must be a simple name")
    cfg = resolve_config(args.config, args.set)
    rows, data_info = load_data(args.data, cfg["data"]["overlap_policy"])
    target_name = cfg["training"]["target"]
    splits = {
        s: [i for i, r in enumerate(rows) if r["split"] == s] for s in ["train", "validation"]
    }
    validation_all = list(splits["validation"])
    splits["validation"] = [i for i in validation_all if rows[i].get("primary_eligible", True)]
    eligible = [i for i in splits["train"] if rows[i].get(target_name) is not None]
    if not eligible or not any(rows[i].get(target_name) is not None for i in splits["validation"]):
        raise ValueError("selected target needs eligible training and validation rows")
    data_info["eligible_train_rows"] = len(eligible)
    constant_groups = {}
    for i in eligible:
        constant_groups.setdefault(rows[i]["group"], []).append(rows[i][target_name])
    constant = (
        sum(sum(v) / len(v) for v in constant_groups.values()) / len(constant_groups)
        if cfg["evaluation"]["monitor"] == "game"
        else sum(rows[i][target_name] for i in eligible) / len(eligible)
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "config": cfg,
                    "data": data_info,
                    "eligible_train": len(eligible),
                    "constant": constant,
                    "scaling": scaling_info,
                },
                ensure_ascii=False,
            )
        )
        return
    if model_factory is not None and not model_sources:
        raise ValueError("custom model factory needs explicit source paths for the run binding")
    sources = source_bindings(model_sources)
    out = Path(args.output).resolve() / args.run_id
    weights = Path(args.checkpoints).resolve() / args.run_id
    if out.exists() or weights.exists():
        raise ValueError("run already exists: use a new run id/output, never overwrite results")
    out.mkdir(parents=True)
    weights.mkdir(parents=True)
    write_json(out / "config.json", cfg)
    write_json(out / "dataset.json", data_info)
    code = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    write_json(
        out / "run.json",
        {
            "run_id": args.run_id,
            "git": code.stdout.strip() if code.returncode == 0 else None,
            "source_sha256": sources,
            "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
            "dataset_sha256": data_info["sha256"],
            "init_checkpoint": args.init_checkpoint,
            "checkpoint_dir": str(weights),
            "status": "created",
            "scaling": scaling_info,
        },
    )
    count, step, last_record, best_step = 0, 0, None, None

    def charge(n):
        nonlocal count
        if time.monotonic() - start >= cfg["limits"]["seconds"]:
            raise BudgetExceeded("wall_limit")
        if count + n > cfg["limits"]["samples"]:
            raise BudgetExceeded("sample_limit")
        count += n

    try:
        import torch

        torch.set_num_threads(cfg["training"]["threads"])
        torch.set_num_interop_threads(cfg["training"]["threads"])
        torch.manual_seed(cfg["training"]["seed"])
        torch.use_deterministic_algorithms(True)
        device = torch.device(cfg["training"]["device"])
        if device.type == "cuda":
            torch.cuda.manual_seed_all(cfg["training"]["seed"])

        from model import Model, inputs

        if model_factory is None:
            model = (
                build_scaled_model(cfg["model"], statistics)
                if statistics is not None
                else Model(cfg["model"])
            )
        else:
            model = model_factory(cfg["model"], statistics)
        model = model.to(device)
        if args.init_checkpoint:
            cp = torch.load(args.init_checkpoint, map_location=device, weights_only=True)
            if cp["model_config"] != cfg["model"]:
                raise ValueError("initial checkpoint model configuration mismatch")
            validate_checkpoint_scaling(cp, scaling_info)
            model.load_state_dict(cp["model"])
        all_inputs = inputs(rows, device)
        initial_sha = hashlib.sha256(
            b"".join(v.detach().cpu().numpy().tobytes() for v in model.state_dict().values())
        ).hexdigest()

        def batch(indices):
            ix = torch.tensor(list(indices), device=device, dtype=torch.long)
            return tuple(v[ix] for v in all_inputs)

        opt_config = cfg["optimizer"]
        opt_type = {"adam": torch.optim.Adam, "adamw": torch.optim.AdamW, "sgd": torch.optim.SGD}[
            opt_config["name"]
        ]
        kwargs = {"lr": opt_config["lr"], "weight_decay": opt_config["weight_decay"]}
        if opt_config["name"] == "sgd":
            kwargs["momentum"] = opt_config["momentum"]
        optimizer = opt_type(model.parameters(), **kwargs)
        scheduler = (
            torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["training"]["steps"])
            if cfg["training"]["scheduler"] == "cosine"
            else None
        )
        stopper = EarlyStopping(
            cfg["evaluation"]["early_stopping_patience"], cfg["evaluation"]["min_delta"]
        )
        generator = torch.Generator().manual_seed(cfg["training"]["seed"] + 1)
        grouped = {}
        for i in eligible:
            grouped.setdefault(rows[i]["group"], []).append(i)
        games = list(grouped.values())

        def checkpoint(name):
            torch.save(
                {
                    "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                    "model_config": cfg["model"],
                    "target": target_name,
                    "step": step,
                    "samples": count,
                    "dataset_sha256": data_info["sha256"],
                    "scaling_sha256": scaling_info["sha256"] if scaling_info else None,
                },
                weights / name,
            )

        checkpoint("initial.pt")
        data_info.update(
            {
                "constant": constant,
                "constant_rule": cfg["evaluation"]["monitor"],
                "initial_state_sha256": initial_sha,
                "validation_primary_rows": len(splits["validation"]),
                "validation_all_rows": len(validation_all),
                "validation_zero_eligible_games": sorted(
                    {rows[i]["group"] for i in validation_all}
                    - {rows[i]["group"] for i in splits["validation"]}
                ),
            }
        )
        write_json(out / "dataset.json", data_info)

        def evaluate():
            nonlocal last_record, best_step
            if count + len(rows) > cfg["limits"]["samples"]:
                raise BudgetExceeded("sample_limit")
            model.eval()
            values = []
            with torch.inference_mode():
                for begin in range(0, len(rows), cfg["evaluation"]["batch_size"]):
                    indices = range(begin, min(begin + cfg["evaluation"]["batch_size"], len(rows)))
                    charge(len(indices))
                    values.extend(model(*batch(indices)).cpu().tolist())
            record = {
                "step": step,
                "train_samples_seen": step * cfg["training"]["batch_size"],
                "train_epochs_equivalent": step * cfg["training"]["batch_size"] / len(eligible),
                "all_samples": count,
                "elapsed_s": time.monotonic() - start,
                "lr": optimizer.param_groups[0]["lr"],
            }
            for split, ix in splits.items():
                record[split] = measurements(
                    [rows[i] for i in ix], [values[i] for i in ix], target_name, constant
                )
            record["validation_secondary_all"] = measurements(
                [rows[i] for i in validation_all],
                [values[i] for i in validation_all],
                target_name,
                constant,
            )
            record["validation_eligible_zero_games"] = data_info["validation_zero_eligible_games"]
            record["train_games"] = {}
            for group in sorted({rows[i]["group"] for i in splits["train"]}):
                ix = [i for i in splits["train"] if rows[i]["group"] == group]
                record["train_games"][group] = measurements(
                    [rows[i] for i in ix], [values[i] for i in ix], target_name, constant
                )
            record["phase"] = {}
            for phase in ["early", "middle", "late"]:
                for split, ix0 in splits.items():
                    ix = [
                        i
                        for i in ix0
                        if (
                            "early"
                            if rows[i].get("ply", 0) < 40
                            else "middle"
                            if rows[i].get("ply", 0) < 100
                            else "late"
                        )
                        == phase
                    ]
                    record["phase"][split + "_" + phase] = measurements(
                        [rows[i] for i in ix], [values[i] for i in ix], target_name, constant
                    )
            record["validation_cohorts"] = {}
            for cohort in sorted({rows[i].get("cohort", "all") for i in splits["validation"]}):
                ix = [i for i in splits["validation"] if rows[i].get("cohort", "all") == cohort]
                record["validation_cohorts"][cohort] = measurements(
                    [rows[i] for i in ix], [values[i] for i in ix], target_name, constant
                )
            record["validation_games"] = {}
            for group in sorted({rows[i]["group"] for i in splits["validation"]}):
                ix = [i for i in splits["validation"] if rows[i]["group"] == group]
                record["validation_games"][group] = measurements(
                    [rows[i] for i in ix], [values[i] for i in ix], target_name, constant
                )
            metric = (
                "target_game_equal_mse" if cfg["evaluation"]["monitor"] == "game" else "target_mse"
            )
            score = record["validation"][metric]
            improved, stop = stopper.observe(score)
            record.update(
                {
                    "monitor": metric,
                    "best_checkpoint_updated": improved,
                    "early_stop_bad_evaluations": stopper.bad,
                }
            )
            with (out / "history.jsonl").open("a") as file:
                file.write(json.dumps(record, allow_nan=False) + "\n")
            last_record = record
            if improved:
                best_step = step
                checkpoint("best.pt")
            model.train()
            return stop

        evaluate()
        reason = "max_steps"
        for next_step in range(1, cfg["training"]["steps"] + 1):
            charge(cfg["training"]["batch_size"])
            if cfg["training"]["sampling"] == "row":
                indices = [
                    eligible[i]
                    for i in torch.randint(
                        len(eligible), (cfg["training"]["batch_size"],), generator=generator
                    ).tolist()
                ]
            else:
                selected = torch.randint(
                    len(games), (cfg["training"]["batch_size"],), generator=generator
                ).tolist()
                indices = [
                    games[g][int(torch.randint(len(games[g]), (), generator=generator))]
                    for g in selected
                ]
            targets = torch.tensor([rows[i][target_name] for i in indices], device=device)
            optimizer.zero_grad(set_to_none=True)
            predicted = model(*batch(indices))
            loss = ((predicted - targets) ** 2).mean()
            if not torch.isfinite(loss):
                raise ValueError("nonfinite training loss")
            loss.backward()
            if any(p.grad is None or not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise ValueError("nonfinite/missing gradient")
            optimizer.step()
            step = next_step
            if scheduler:
                scheduler.step()
            if step % cfg["evaluation"]["interval"] == 0 or step == cfg["training"]["steps"]:
                if evaluate():
                    reason = "early_stopping"
                    break
        checkpoint("last.pt")
    except BudgetExceeded as exc:
        reason = str(exc)
        if "model" in locals():
            checkpoint("last.pt")
    except BaseException as exc:
        write_json(
            out / "failure.json",
            {
                "error": repr(exc),
                "traceback": traceback.format_exc(),
                "step": step,
                "samples": count,
            },
        )
        write_json(
            out / "summary.json",
            {
                "status": "failed",
                "step": step,
                "all_samples": count,
                "elapsed_s": time.monotonic() - start,
                "best_step": best_step,
                "best_validation_mse": stopper.best
                if "stopper" in locals() and best_step is not None
                else None,
                "last_evaluation": last_record,
                "checkpoint_dir": str(weights),
                "test_evaluated": False,
                "strength_claim": False,
            },
        )
        raise
    write_json(
        out / "summary.json",
        {
            "status": reason,
            "step": step,
            "all_samples": count,
            "elapsed_s": time.monotonic() - start,
            "best_step": best_step,
            "best_validation_mse": stopper.best
            if "stopper" in locals() and best_step is not None
            else None,
            "last_evaluation": last_record,
            "checkpoint_dir": str(weights),
            "test_evaluated": False,
            "strength_claim": False,
        },
    )
    print(json.dumps({"run": str(out), "status": reason, "best_step": best_step, "samples": count}))


def source_bindings(extra_paths=()):
    paths = [Path(__file__).with_name(name) for name in SOURCE_FILES]
    paths.extend(Path(path) for path in extra_paths)
    # Full paths preserve identity if an external factory has a matching basename.
    return {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def validate_checkpoint_scaling(checkpoint, scaling_info):
    expected = scaling_info["sha256"] if scaling_info else None
    if checkpoint.get("scaling_sha256") != expected:
        raise ValueError("initial checkpoint scaling binding mismatch")


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="QF1 JSON/JSONL/gzip or bound .stage.json")
    parser.add_argument("--config")
    parser.add_argument("--set", action="append", default=[], help="JSON configuration override")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", default=".artifacts/ai-sigma/learning")
    parser.add_argument("--checkpoints", default="models/experiments/nnue")
    parser.add_argument(
        "--init-checkpoint", help="weights-only initialization; optimizer/steps start fresh"
    )
    parser.add_argument(
        "--scale-statistics",
        help="explicit precomputed STM float32 moments; omitted = raw distances",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="NN0 config/input validation; no model import"
    )
    return parser


def main(argv=None):
    train(argument_parser().parse_args(argv))


if __name__ == "__main__":
    main()
