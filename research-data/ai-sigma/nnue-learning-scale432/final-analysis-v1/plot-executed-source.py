"""Static plots of original saved scalar metrics, without model evaluation."""

import csv
import json
from pathlib import Path
import tempfile
import os

_CACHE = tempfile.TemporaryDirectory(prefix="432-plots-")
os.environ["MPLCONFIGDIR"] = _CACHE.name

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402


OWN = Path(__file__).resolve().parent
FINAL = OWN.parent / "final-analysis-v1"


def main():
    with (OWN / "curves.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    fig, axes = plt.subplots(
        1, 2, figsize=(9.0, 3.4), sharex=True, layout="constrained"
    )
    colors = {"A": "#62666a", "B": "#2675b0", "C": "#c65e13", "D": "#258251"}
    styles = {"A": "--", "B": "-.", "C": "-", "D": ":"}
    for name in ("A", "B", "C", "D"):
        for ax, scope, field in (
            (axes[0], "added_validation", "family_z_mse"),
            (axes[1], "public_train", "row_z_mse"),
        ):
            selected = [
                r for r in rows if r["condition"] == name and r["scope"] == scope
            ]
            ax.plot(
                [int(r["training_draws_so_far"]) / 1000 for r in selected],
                [float(r[field]) for r in selected],
                label=name,
                color=colors[name],
                linestyle=styles[name],
                marker="o",
                markersize=3.5,
                linewidth=1.5,
            )
    axes[0].set_title("Common newV: 12,275 rows / 236 families", fontsize=9)
    axes[0].set_ylabel("Canonical-family z-MSE")
    axes[1].set_title("Fixed opened-public T panel: 8,192 rows", fontsize=9)
    axes[1].set_ylabel("Row z-MSE")
    axes[0].legend(title="Fixed condition", fontsize=8, title_fontsize=8)
    for ax in axes:
        ax.set_xlabel("Actual training row draws (thousands)")
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=8)
        ax.axvline(29.88, color="#777777", linestyle="--", linewidth=0.7, alpha=0.6)
    fig.savefig(FINAL / "learning-curves.svg", metadata={"Date": None})
    plt.close(fig)
    examples = json.loads((FINAL / "examples.json").read_text())
    assert len(examples) == 2 and all(row["global_family_id"] == 0 for row in examples)
    fig, (board, notes) = plt.subplots(
        1,
        2,
        figsize=(9.0, 4.7),
        gridspec_kw={"width_ratios": [1.1, 1]},
        layout="constrained",
    )
    for x in range(9):
        for y in range(9):
            board.plot(x, y, ".", color="#c6c9cc", markersize=4)
    # Four walls from the fixed original family0 prefix, using saved action encoding.
    for action in examples[0]["prefix"]:
        if 81 <= action < 145:
            i = action - 81
            x, y = i % 8, i // 8
            board.plot([x - 0.42, x + 1.42], [y + 0.5] * 2, color="#45484c", lw=5)
        elif action >= 145:
            i = action - 145
            x, y = i % 8, i // 8
            board.plot([x + 0.5] * 2, [y - 0.42, y + 1.42], color="#45484c", lw=5)
    board.scatter([4], [0], color="#2675b0", s=140, zorder=4)
    board.scatter([4], [8], color="#b34747", s=140, zorder=4)
    board.annotate(
        "C: pawn to (4,1)",
        xy=(4, 1),
        xytext=(0.1, 3),
        arrowprops={"arrowstyle": "->", "color": "#2675b0"},
        color="#2675b0",
        fontsize=8,
    )
    board.annotate(
        "",
        xy=(4, 1),
        xytext=(4, 0),
        arrowprops={"arrowstyle": "->", "color": "#2675b0", "lw": 2},
    )
    board.plot([6.5, 6.5], [-0.42, 1.42], color="#c65e13", lw=5, linestyle="--")
    board.text(5.1, 2.2, "BEST43: V(6,0)", color="#c65e13", fontsize=8)
    board.set(
        xlim=(-0.7, 8.7),
        ylim=(-0.7, 8.7),
        xticks=range(9),
        yticks=range(9),
        aspect="equal",
        xlabel="x (saved zero-based coordinates)",
        ylabel="y",
    )
    board.set_title("First fixed family0: identical parent / full prefix", fontsize=10)
    notes.axis("off")
    descriptions = []
    for row, label in zip(examples, ("C LAST467", "BEST43"), strict=True):
        first = row["first"]
        descriptions.append(
            f"{label}\n  action {first['action']}, completed D{first['completed_depth']}\n  searched STM value {first['value_stm']:.8f}\n  PV {first['pv']}\n  actual first actions {row['following_actions'][:4]}"
        )
    notes.text(
        0.02,
        0.98,
        "\n\n".join(descriptions)
        + "\n\nSame parent, different timed searches.\nSearched values are not static NNUE labels.\nNeither action is an optimal-WDL oracle.\nFamily0 won by C in both colours;\noverall C score is 48.44%.",
        va="top",
        fontsize=9,
        linespacing=1.45,
    )
    fig.savefig(FINAL / "family0-example.svg", metadata={"Date": None})
    plt.close(fig)
    _CACHE.cleanup()
    print(
        "Saved two original scalar/path figures; new forwards/bootstrap=0; plot TMP removed"
    )


if __name__ == "__main__":
    main()
