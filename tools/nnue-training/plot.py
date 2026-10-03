"""Standalone PNG/SVG training curves, including honest plots of legacy logs."""

import argparse
import gzip
import json
from pathlib import Path


def plot_runs(paths, output, axis="step", metric_name="target"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for path in paths:
        path = Path(path)
        history = [json.loads(line) for line in (path / "history.jsonl").read_text().splitlines() if line]
        if not history:
            raise ValueError(f"empty history: {path}")
        xs = [r[axis] for r in history]
        game_equal = history[0]["monitor"] == "target_game_equal_mse"
        metric = metric_name + ("_game_equal_mse" if game_equal else "_mse")
        constant = "constant_game_equal_mse" if game_equal else "constant_mse"
        for split, style in [("train", "--"), ("validation", "-")]:
            axes[0].plot(xs, [r[split][metric] for r in history], style, marker=".", label=f"{path.name}: {split}")
        if metric_name == "target":
            axes[0].plot(xs, [r["validation"][constant] for r in history], ":", label=f"{path.name}: constant")
        for cohort in sorted(history[0]["validation_cohorts"]):
            axes[1].plot(xs, [r["validation_cohorts"][cohort][metric] for r in history], marker=".", label=f"{path.name}: {cohort}")
        if len(paths) == 1 and metric_name == "target":
            summary = json.loads((path / "summary.json").read_text())
            best = next((r for r in history if r["step"] == summary["best_step"]), None)
            if best:
                axes[0].axvline(best[axis], color="gray", alpha=0.5, label="selected checkpoint")
    for ax, title in zip(axes, ["Training / validation (full-set evaluations)", "Validation cohorts"]):
        ax.set(title=title, xlabel=axis, ylabel=f"{metric_name} MSE (lower is better)")
        ax.grid(alpha=0.25)
        ax.legend(fontsize="small")
    _save(figure, output)


def legacy(path, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    raw = Path(path).read_bytes()
    x = json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    axes[0].plot([r["step"] for r in x["ledger"]], [r["rootmeanMSE"] for r in x["ledger"]], marker="o", label="logged training minibatches (4 points)")
    for key, label in [("train", "full train"), ("validation", "all validation"), ("validation_old", "old validation"), ("validation_new", "new validation")]:
        group = x[key]
        # Mark endpoints only: the intermediate validation trajectory was not recorded.
        axes[1].scatter([0, x["train_steps"]], [group["before"]["rootmeanMSE"], group["after"]["rootmeanMSE"]], label=label)
        if key == "validation_new":
            axes[1].axhline(group["trainmean_constant_rootmeanMSE"], linestyle=":", color="gray", label="new validation: constant baseline")
    axes[0].set(title="190: available training log", xlabel="step", ylabel="minibatch rootmean MSE", yscale="log")
    axes[1].set(title="Validation endpoints only; intermediate values absent", xlabel="step", ylabel="full-set rootmean MSE", xticks=[0, x["train_steps"]])
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(fontsize="small")
    _save(figure, output)


def _save(figure, output):
    import matplotlib.pyplot as plt
    p = Path(output)
    p.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(p.with_suffix(".png"), dpi=160)
    figure.savefig(p.with_suffix(".svg"))
    plt.close(figure)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--runs", nargs="+")
    g.add_argument("--legacy", help="190 learning.json.gz; never invent intermediate validation")
    p.add_argument("--output", required=True, help="basename; writes PNG and SVG")
    p.add_argument("--axis", choices=["step", "train_samples_seen", "train_epochs_equivalent", "elapsed_s"], default="step")
    p.add_argument("--metric", choices=["target", "rootmean", "z"], default="target", help="runs only; reuse saved predictions' errors, no new forward")
    a = p.parse_args()
    legacy(a.legacy, a.output) if a.legacy else plot_runs(a.runs, a.output, a.axis, a.metric)
