"""Both teacher errors in explicit raw-step and normalized loss units."""

import math
import numpy as np


def measurements(corpus, indices, values, target, constant, transform):
    if target not in ("outcome_steps", "terminal_margin") or len(indices) != len(values):
        raise ValueError("step measurement target/shape")
    groups, games = {}, {}
    large, sign_right, sign_rows, rows = 0, 0, 0, 0
    totals = {"outcome_steps": [0.0, 0], "terminal_margin": [0.0, 0], "constant": [0.0, 0]}
    bias = 0.0
    for i, prediction in zip(indices, values, strict=True):
        prediction = float(prediction)
        if not math.isfinite(prediction):
            raise ValueError("nonfinite step prediction")
        row = corpus.rows[int(i)]
        values_by_teacher = {
            "outcome_steps": row["outcome_steps"],
            "terminal_margin": row["terminal_margin"],
        }
        if any(v is None for v in values_by_teacher.values()):
            raise ValueError("selected measurement requires both eligible teachers")
        family = groups.setdefault(row["group"], {key: [0.0, 0] for key in totals})
        game = games.setdefault(row["game"], {key: [0.0, 0] for key in totals})
        for key, label in values_by_teacher.items():
            error = (prediction - float(label)) ** 2
            totals[key][0] += error
            totals[key][1] += 1
            family[key][0] += error
            family[key][1] += 1
            game[key][0] += error
            game[key][1] += 1
        label = values_by_teacher[target]
        error = (float(np.float32(constant)) - label) ** 2
        totals["constant"][0] += error
        totals["constant"][1] += 1
        family["constant"][0] += error
        family["constant"][1] += 1
        game["constant"][0] += error
        game["constant"][1] += 1
        bias += prediction - label
        rows += 1
        large += abs(prediction) >= 72
        if row["z"] != 0:
            sign_rows += 1
            sign_right += prediction * row["z"] > 0
    result = {
        "rows": rows,
        "games": len(games),
        "families": len(groups),
        "group_kind": "input-only whole family",
        "score_units": "raw-distance-steps",
        "error_normalizer": 6400,
        "groups": {
            family: {
                "rows": metrics[target][1],
                **{key + "_raw_mse": pair[0] / pair[1] for key, pair in metrics.items()},
                **{key + "_mse": pair[0] / pair[1] / 6400 for key, pair in metrics.items()},
            }
            for family, metrics in groups.items()
        },
    }
    for key, (error, count) in totals.items():
        raw = error / count if count else None
        result[key + "_raw_mse"] = raw
        result[key + "_mse"] = raw / 6400 if raw is not None else None
        result[key + "_game_equal_mse"] = (
            sum(pair[key][0] / pair[key][1] for pair in games.values()) / len(games) / 6400
            if games
            else None
        )
        result[key + "_family_equal_mse"] = (
            sum(pair[key][0] / pair[key][1] for pair in groups.values()) / len(groups) / 6400
            if groups
            else None
        )
    result.update(
        {
            "target_mse": result[target + "_mse"],
            "target_raw_mse": result[target + "_raw_mse"],
            "target_game_equal_mse": result[target + "_game_equal_mse"],
            "z_sign_rows": sign_rows,
            "z_sign_accuracy": sign_right / sign_rows if sign_rows else None,
            "saturation_fraction": large / rows if rows and transform == "F" else None,
            "large_abs_step_score_fraction": large / rows if rows else None,
            "bias": bias / rows if rows else None,
        }
    )
    return result
