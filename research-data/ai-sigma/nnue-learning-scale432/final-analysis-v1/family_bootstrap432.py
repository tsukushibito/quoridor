"""One original432 saved192-family interval; no engine calls."""

import ast
import hashlib
import json
import math
from pathlib import Path
import platform
import stat
import sys

np = None
SEED = RESAMPLES = PLANNED_FAMILIES = None
MAX_INPUT_BYTES = 131072


def interval_from_complete_family_scores(scores):
    if any(type(score) not in (int, float) for score in scores):
        raise ValueError("family scores must be JSON numbers, not strings or bools")
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or len(values) > PLANNED_FAMILIES:
        raise ValueError("expected at most192 complete two-colour family scores")
    if not np.all(np.isfinite(values)) or not np.all(
        np.isin(values, [0.0, 0.25, 0.5, 0.75, 1.0])
    ):
        raise ValueError("invalid two-colour W/D/L family scores")
    if len(values) == 0:
        return None
    rng = np.random.Generator(np.random.PCG64(SEED))
    sampled = rng.choice(values, size=(RESAMPLES, len(values)), replace=True)
    means = sampled.mean(axis=1, dtype=np.float64)
    return np.quantile(means, [0.025, 0.975], method="linear").tolist()


def read_bound(path):
    with path.open("rb") as stream:
        body = stream.read(MAX_INPUT_BYTES + 1)
    if len(body) > MAX_INPUT_BYTES:
        raise ValueError("small saved metadata input required")
    ref = {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "mode": format(stat.S_IMODE(path.stat().st_mode), "04o"),
    }
    return body, ref


def main():
    global np, SEED, RESAMPLES, PLANNED_FAMILIES

    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: family_bootstrap432.py SETTINGS.json INPUT.json NEW_OUTPUT.json"
        )
    settings_path, input_path, output_path = map(Path, sys.argv[1:])
    source_path = Path(__file__).resolve()
    originals = [read_bound(path) for path in (source_path, settings_path, input_path)]
    source_bytes, source_ref = originals[0]
    settings_bytes, settings_ref = originals[1]
    input_bytes, input_ref = originals[2]
    settings, data = json.loads(settings_bytes), json.loads(input_bytes)
    PLANNED_FAMILIES = settings["planned_family_count"]
    SEED, RESAMPLES = settings["seed"], settings["resamples"]
    if any(type(n) is not int or n <= 0 for n in (PLANNED_FAMILIES, SEED, RESAMPLES)):
        raise ValueError("positive integer family count, seed and resamples required")
    planned_games = settings["planned_game_count"]
    if type(planned_games) is not int or planned_games != 2 * PLANNED_FAMILIES:
        raise ValueError("one two-colour pair per planned family required")
    if (
        settings["rng"] != "PCG64"
        or settings["confidence"] != 0.95
        or settings["quantile_method"] != "linear"
    ):
        raise ValueError("preserve the fixed percentile interval convention")
    contrast = settings["contrasts"][data["contrast"]]
    if contrast["role"] not in ("primary", "secondary"):
        raise ValueError("invalid fixed contrast role")
    if data["planned_family_count"] != PLANNED_FAMILIES:
        raise ValueError("input and fixed family count differ")
    records = data["complete_families"]
    ids = [record["global_family_id"] for record in records]
    if any(
        type(i) is not int or not 0 <= i < PLANNED_FAMILIES for i in ids
    ) or ids != sorted(set(ids)):
        raise ValueError("true global family IDs must be unique and ordered")
    valid, unresolved = data["valid_game_count"], data["unresolved_game_count"]
    if (
        any(type(n) is not int or n < 0 for n in (valid, unresolved))
        or valid + unresolved != planned_games
        or valid < 2 * len(records)
    ):
        raise ValueError("planned, valid and complete-pair denominators disagree")
    complete = data["all_planned_games_complete"]
    expected_complete = valid == planned_games and ids == list(range(PLANNED_FAMILIES))
    if type(complete) is not bool or complete != expected_complete:
        raise ValueError("complete criterion requires every planned game and true pair")
    if unresolved == 0 and not complete:
        raise ValueError("all valid games require every complete family score")
    scores = [record["candidate_score"] for record in records]
    function = next(
        node
        for node in ast.parse(source_bytes).body
        if isinstance(node, ast.FunctionDef)
        and node.name == "interval_from_complete_family_scores"
    )
    function_ast = ast.dump(function, include_attributes=False)
    function_text = ast.get_source_segment(source_bytes.decode(), function)

    # Reserve the actual destination before importing NumPy or drawing resamples.
    # Existing output is an entry refusal, never an invitation to overwrite/retry.
    with output_path.open("x", encoding="utf-8") as output_stream:
        import numpy as np

        interval = interval_from_complete_family_scores(scores)
        mean = math.fsum(scores) / len(scores) if scores else None
        if not complete:
            criterion = "NOT_APPLICABLE_INCOMPLETE"
        elif contrast["role"] == "secondary":
            criterion = "SECONDARY_DESCRIPTIVE_ONLY"
        else:
            criterion = "MET" if interval[0] > 0.5 else "NOT_MET"
        result = {
            "contrast": data["contrast"],
            "contrast_definition": contrast,
            "planned_family_count": PLANNED_FAMILIES,
            "planned_game_count": planned_games,
            "valid_game_count": valid,
            "unresolved_game_count": unresolved,
            "complete_family_count": len(scores),
            "family_mean": mean,
            "percentile_95": interval,
            "criterion_fixed_book_time_only": criterion,
            "partial_scope": "complete-pair conditional; valid-game mean and planned bounds are separate",
            "seed": SEED,
            "requested_resamples": RESAMPLES,
            "executed_resamples": RESAMPLES if scores else 0,
            "rng": "NumPy Generator(PCG64)",
            "quantile_method": "linear",
            "settings": settings_ref,
            "input": input_ref,
            "executed_statistical_source": source_ref,
            "executed_function": function.name,
            "executed_function_AST_sha256": hashlib.sha256(
                function_ast.encode()
            ).hexdigest(),
            "executed_function_text_sha256": hashlib.sha256(
                function_text.encode()
            ).hexdigest(),
            "interpreter": sys.executable,
            "resolved_interpreter": str(Path(sys.executable).resolve()),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "old_intervals_recomputed": False,
        }
        if [
            read_bound(path) for path in (source_path, settings_path, input_path)
        ] != originals:
            raise ValueError("source/settings/input changed during saved calculation")
        output_stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "contrast": data["contrast"],
                "complete_families": len(scores),
            }
        )
    )


if __name__ == "__main__":
    main()
