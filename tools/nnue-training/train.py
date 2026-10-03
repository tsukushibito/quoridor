"""Configurable QF1 value trainer. Runs are explicit; no automatic search/sweep."""

import argparse
import hashlib
import json
import re
import subprocess
import time
import traceback
from pathlib import Path

from common import EarlyStopping, load_data, measurements, resolve_config, write_json


class BudgetExceeded(Exception):
    pass


def train(args):
    start = time.monotonic()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("run id must be a simple name")
    cfg = resolve_config(args.config, args.set)
    rows, data_info = load_data(args.data, cfg["data"]["overlap_policy"])
    target_name = cfg["training"]["target"]
    splits = {s: [i for i, r in enumerate(rows) if r["split"] == s] for s in ["train", "validation"]}
    eligible = [i for i in splits["train"] if rows[i].get(target_name) is not None]
    if not eligible or not any(rows[i].get(target_name) is not None for i in splits["validation"]):
        raise ValueError("selected target needs eligible training and validation rows")
    data_info["eligible_train_rows"] = len(eligible)
    constant_groups = {}
    for i in eligible:
        constant_groups.setdefault(rows[i]["group"], []).append(rows[i][target_name])
    constant = (sum(sum(v) / len(v) for v in constant_groups.values()) / len(constant_groups)
                if cfg["evaluation"]["monitor"] == "game" else sum(rows[i][target_name] for i in eligible) / len(eligible))
    if args.dry_run:
        print(json.dumps({"config": cfg, "data": data_info, "eligible_train": len(eligible), "constant": constant}, ensure_ascii=False))
        return
    out = Path(args.output).resolve() / args.run_id
    weights = Path(args.checkpoints).resolve() / args.run_id
    if out.exists() or weights.exists():
        raise ValueError("run already exists: use a new run id/output, never overwrite results")
    out.mkdir(parents=True)
    weights.mkdir(parents=True)
    write_json(out / "config.json", cfg)
    write_json(out / "dataset.json", data_info)
    code = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    write_json(out / "run.json", {"run_id": args.run_id, "git": code.stdout.strip() if code.returncode == 0 else None, "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), Path(__file__).with_name("common.py")]}, "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(), "dataset_sha256": data_info["sha256"], "init_checkpoint": args.init_checkpoint, "checkpoint_dir": str(weights), "status": "created"})
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

        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                h = cfg["model"]["transformer_width"]
                self.ft = torch.nn.Linear(312, h)
                self.h = torch.nn.Linear(2 * h + 2, cfg["model"]["hidden_width"])
                self.dropout = torch.nn.Dropout(cfg["model"]["dropout"])
                self.out = torch.nn.Linear(cfg["model"]["hidden_width"], 1)

            def forward(self, x, d, side):
                a = torch.relu(self.ft(x))
                p = side.long() - 1
                idx = torch.arange(len(x), device=x.device)
                q = torch.cat([a[idx, p], a[idx, 1 - p], d], dim=1)
                return torch.tanh(self.out(self.dropout(torch.relu(self.h(q)))))[:, 0]

        model = Model().to(device)
        if args.init_checkpoint:
            cp = torch.load(args.init_checkpoint, map_location=device, weights_only=True)
            if cp["model_config"] != cfg["model"]:
                raise ValueError("initial checkpoint model configuration mismatch")
            model.load_state_dict(cp["model"])
        def batch(indices):
            selected = [rows[i] for i in indices]
            x = torch.zeros(len(selected), 2, 312)
            for i, row in enumerate(selected):
                for p in (0, 1):
                    x[i, p, row["ids"][p]] = 1
            return x.to(device), torch.tensor([r["distance"] for r in selected], device=device), torch.tensor([r["side"] for r in selected], device=device)
        opt_config = cfg["optimizer"]
        opt_type = {"adam": torch.optim.Adam, "adamw": torch.optim.AdamW, "sgd": torch.optim.SGD}[opt_config["name"]]
        kwargs = {"lr": opt_config["lr"], "weight_decay": opt_config["weight_decay"]}
        if opt_config["name"] == "sgd":
            kwargs["momentum"] = opt_config["momentum"]
        optimizer = opt_type(model.parameters(), **kwargs)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg["training"]["steps"]) if cfg["training"]["scheduler"] == "cosine" else None
        stopper = EarlyStopping(cfg["evaluation"]["early_stopping_patience"], cfg["evaluation"]["min_delta"])
        generator = torch.Generator().manual_seed(cfg["training"]["seed"] + 1)
        grouped = {}
        for i in eligible:
            grouped.setdefault(rows[i]["group"], []).append(i)
        games = list(grouped.values())

        def checkpoint(name):
            torch.save({"model": {k: v.detach().cpu() for k, v in model.state_dict().items()}, "model_config": cfg["model"], "target": target_name, "step": step, "samples": count, "dataset_sha256": data_info["sha256"]}, weights / name)

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
            record = {"step": step, "train_samples_seen": step * cfg["training"]["batch_size"], "train_epochs_equivalent": step * cfg["training"]["batch_size"] / len(eligible), "all_samples": count, "elapsed_s": time.monotonic() - start, "lr": optimizer.param_groups[0]["lr"]}
            for split, ix in splits.items():
                record[split] = measurements([rows[i] for i in ix], [values[i] for i in ix], target_name, constant)
            record["validation_cohorts"] = {}
            for cohort in sorted({rows[i].get("cohort", "all") for i in splits["validation"]}):
                ix = [i for i in splits["validation"] if rows[i].get("cohort", "all") == cohort]
                record["validation_cohorts"][cohort] = measurements([rows[i] for i in ix], [values[i] for i in ix], target_name, constant)
            record["validation_games"] = {}
            for group in sorted({rows[i]["group"] for i in splits["validation"]}):
                ix = [i for i in splits["validation"] if rows[i]["group"] == group]
                record["validation_games"][group] = measurements([rows[i] for i in ix], [values[i] for i in ix], target_name, constant)
            metric = "target_game_equal_mse" if cfg["evaluation"]["monitor"] == "game" else "target_mse"
            score = record["validation"][metric]
            improved, stop = stopper.observe(score)
            record.update({"monitor": metric, "best_checkpoint_updated": improved, "early_stop_bad_evaluations": stopper.bad})
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
                indices = [eligible[i] for i in torch.randint(len(eligible), (cfg["training"]["batch_size"],), generator=generator).tolist()]
            else:
                selected = torch.randint(len(games), (cfg["training"]["batch_size"],), generator=generator).tolist()
                indices = [games[g][int(torch.randint(len(games[g]), (), generator=generator))] for g in selected]
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
        write_json(out / "failure.json", {"error": repr(exc), "traceback": traceback.format_exc(), "step": step, "samples": count})
        write_json(out / "summary.json", {"status": "failed", "step": step, "all_samples": count, "elapsed_s": time.monotonic() - start, "best_step": best_step, "best_validation_mse": stopper.best if "stopper" in locals() and best_step is not None else None, "last_evaluation": last_record, "checkpoint_dir": str(weights), "test_evaluated": False, "strength_claim": False})
        raise
    write_json(out / "summary.json", {"status": reason, "step": step, "all_samples": count, "elapsed_s": time.monotonic() - start, "best_step": best_step, "best_validation_mse": stopper.best if "stopper" in locals() and best_step is not None else None, "last_evaluation": last_record, "checkpoint_dir": str(weights), "test_evaluated": False, "strength_claim": False})
    print(json.dumps({"run": str(out), "status": reason, "best_step": best_step, "samples": count}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="QF1 JSON/JSONL, optionally gzip")
    parser.add_argument("--config")
    parser.add_argument("--set", action="append", default=[], help='JSON override, e.g. optimizer.lr=0.00025')
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", default=".artifacts/ai-sigma/learning")
    parser.add_argument("--checkpoints", default="models/experiments/nnue")
    parser.add_argument("--init-checkpoint", help="weights-only initialization; optimizer/steps start fresh")
    parser.add_argument("--dry-run", action="store_true", help="validate config/split without importing torch or training")
    train(parser.parse_args())
