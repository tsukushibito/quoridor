"""Static426 figures from the frozen saved analysis; no bootstrap or model calls."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main():
    result = json.loads((ROOT / "result.json").read_text())
    summary = result["sole_actual_192_family_bootstrap"]
    rows = result["B"]["comparisons"]["rows"]
    blue, orange = "#0072B2", "#D55E00"
    fig, axes = plt.subplots(
        1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [0.85, 1.6]}
    )
    mean = summary["family_mean"]
    low, high = summary["percentile_95"]
    axes[0].errorbar(
        [mean],
        [0],
        xerr=[[mean - low], [high - mean]],
        fmt="o",
        color=orange,
        capsize=6,
        markersize=9,
    )
    axes[0].axvline(0.5, color="#666666", linestyle="--")
    axes[0].set_xlim(0.38, 0.6)
    axes[0].set_ylim(-0.6, 0.65)
    axes[0].set_yticks([])
    axes[0].set_xlabel("W family score")
    axes[0].set_title("A: 192 families / 384 goal games")
    axes[0].text(
        0.03,
        0.8,
        "183 W - 201 L\n47.66% [42.97%, 52.34%]\nCriterion lower > 50%: NOT MET",
        transform=axes[0].transAxes,
        fontsize=10,
    )
    axes[0].text(
        0.03,
        0.1,
        "39 both wins / 105 split / 48 both losses\nFixed book and clock only; no Elo claim",
        transform=axes[0].transAxes,
        fontsize=9,
    )
    axes[0].grid(axis="x", alpha=0.2)
    labels = [
        "parent: slot4 ply11",
        "parent: slot4 ply39",
        "parent: slot5 ply12",
        "ply11 H2: 156-91",
        "ply11 H2: 156-196",
        "ply39 H2: 192-43",
        "ply39 H3: 60-53-61",
    ]
    for i, row in enumerate(rows):
        axes[1].plot(
            [row["old_post"], row["W_post"]], [i, i], color="#999999", linewidth=2
        )
        axes[1].scatter(
            row["old_post"], i, color=blue, s=45, label="BEST43" if i == 0 else None
        )
        axes[1].scatter(
            row["W_post"],
            i,
            color=orange,
            marker="x",
            s=65,
            linewidth=2,
            label="W BEST118" if i == 0 else None,
        )
        axes[1].scatter(
            row["Sigma"],
            i,
            color="#999999",
            marker="|",
            s=110,
            label="saved Sigma, not oracle" if i == 0 else None,
        )
        axes[1].text(
            0.02,
            i + 0.31,
            f"{row['old_post']:+.6f} -> {row['W_post']:+.6f}",
            transform=axes[1].get_yaxis_transform(),
            fontsize=8,
        )
    axes[1].axvline(0, color="#bbbbbb", linewidth=1)
    axes[1].set_yticks(range(7), labels)
    axes[1].set_xlim(-1.05, 1.05)
    axes[1].set_ylim(6.7, -0.7)
    axes[1].set_xlabel("Direct static value in each row's LOCAL STM")
    axes[1].set_title("B: 7/7 signs unchanged; 3/7 saturated remain")
    axes[1].grid(axis="x", alpha=0.2)
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, fontsize=8)
    fig.suptitle("Frozen W: independent arena and fixed static examples", fontsize=14)
    fig.text(
        0.02,
        0.015,
        "A: sole NumPy PCG64 bootstrap 10000 / seed42620261016 / 95% linear; "
        "B: same saved inputs, no Search or WDL oracle.",
        fontsize=8,
    )
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    for ext in ("svg", "png"):
        fig.savefig(ROOT / f"evidence426.{ext}", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    for i, item in enumerate(
        result["A_observations"]["work_and_depth_alternative_views"]
    ):
        hist = item["depth_hist"]
        depths = list(range(3, 65))
        values = [hist.get(str(d), 0) / item["accepted_completed"] for d in depths]
        ax.step(
            depths,
            values,
            where="mid",
            color=[orange, blue][i],
            label=f"{item['model']}: n={item['accepted_completed']}, median8",
        )
    ax.set_xlabel("Accepted completed selective nominal depth")
    ax.set_ylabel("Share of each model's accepted completed snapshots")
    ax.set_title("Different trajectories and terminal tails; depth is not strength")
    ax.set_xlim(2, 65)
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    for ext in ("svg", "png"):
        fig.savefig(ROOT / f"accepted-depth426.{ext}", dpi=180)
    plt.close(fig)
    print(json.dumps({"static_figures": 4, "new_model_or_bootstrap_calls": 0}))


if __name__ == "__main__":
    main()
