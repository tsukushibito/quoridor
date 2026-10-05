"""Summarize explicit runs; flag different targets/validation sets."""

import argparse
import csv
import json
from pathlib import Path

from common import write_json


def compare(paths, output):
    records = []
    for p in map(Path, paths):
        cfg = json.loads((p / "config.json").read_text())
        dataset = json.loads((p / "dataset.json").read_text())
        summary = json.loads((p / "summary.json").read_text())
        eligible_rows = dataset["eligible_train_rows"]
        records.append({"run": p.name, "validation_sha256": dataset["validation_sha256"], "target": cfg["training"]["target"], "monitor": cfg["evaluation"]["monitor"], "optimizer": cfg["optimizer"]["name"], "lr": cfg["optimizer"]["lr"], "weight_decay": cfg["optimizer"]["weight_decay"], "transformer_width": cfg["model"]["transformer_width"], "hidden_width": cfg["model"]["hidden_width"], "train_games": dataset["groups"]["train"], "train_rows": dataset["counts"]["train"], "seed": cfg["training"]["seed"], "batch_size": cfg["training"]["batch_size"], "steps": summary["step"], "train_samples_seen": summary["step"] * cfg["training"]["batch_size"], "train_epochs_equivalent": summary["step"] * cfg["training"]["batch_size"] / eligible_rows, "best_step": summary["best_step"], "best_validation_mse": summary["best_validation_mse"], "samples": summary["all_samples"], "seconds": summary["elapsed_s"], "status": summary["status"]})
    comparable = len({(r["validation_sha256"], r["target"], r["monitor"]) for r in records}) == 1
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out.with_suffix(".json"), {"same_validation_and_target": comparable, "validation_selected_not_final_holdout": True, "runs": records})
    with out.with_suffix(".csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    print(json.dumps({"same_validation_and_target": comparable, "runs": len(records)}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs", required=True, nargs="+")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    compare(a.runs, a.output)
