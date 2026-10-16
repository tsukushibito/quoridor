"""One 426 saved-family interval, executed only after the original arena returns."""

import hashlib
import json
import math
from pathlib import Path
import platform
import stat
import sys

import numpy as np

SEED = 42620261016
RESAMPLES = 10000
PLANNED_FAMILIES = 192


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


def file_ref(path, body):
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "mode": format(stat.S_IMODE(path.stat().st_mode), "04o"),
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: family_bootstrap426.py INPUT.json NEW_OUTPUT.json")
    input_path, output_path = map(Path, sys.argv[1:])
    if output_path.exists():
        raise FileExistsError("preserve original output")
    source_path = Path(__file__)
    source_bytes = source_path.read_bytes()
    input_bytes = input_path.read_bytes()
    if len(input_bytes) > 131072:
        raise ValueError("small complete-family input required")
    data = json.loads(input_bytes)
    if data["planned_family_count"] != PLANNED_FAMILIES:
        raise ValueError("426 has one fixed192-family design")
    records = data["complete_families"]
    ids = [record["global_family_id"] for record in records]
    if any(
        type(i) is not int or not 0 <= i < PLANNED_FAMILIES for i in ids
    ) or ids != sorted(set(ids)):
        raise ValueError("true global family IDs must be unique and ordered")
    complete = data["all_384_complete"]
    if type(complete) is not bool or (
        complete and ids != list(range(PLANNED_FAMILIES))
    ):
        raise ValueError("all384 complete requires all192 true families")
    scores = [record["candidate_score"] for record in records]
    interval = interval_from_complete_family_scores(scores)
    mean = math.fsum(scores) / len(scores) if scores else None
    criterion = (
        ("MET" if interval[0] > 0.5 else "NOT_MET")
        if complete
        else "NOT_APPLICABLE_INCOMPLETE"
    )
    result = {
        "complete_family_count": len(scores),
        "family_mean": mean,
        "percentile_95": interval,
        "criterion_fixed_book_time_only": criterion,
        "partial_scope": "complete-pair conditional; planned bounds are separate",
        "seed": SEED,
        "requested_resamples": RESAMPLES,
        "executed_resamples": RESAMPLES if scores else 0,
        "rng": "NumPy Generator(PCG64)",
        "quantile_method": "linear",
        "input": file_ref(input_path, input_bytes),
        "executed_statistical_source": file_ref(source_path, source_bytes),
        "executed_function": "interval_from_complete_family_scores",
        "interpreter": sys.executable,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "old423_interval_recomputed": False,
    }
    if (
        input_path.read_bytes() != input_bytes
        or source_path.read_bytes() != source_bytes
    ):
        raise ValueError("input/source changed during saved calculation")
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output_path), "complete_families": len(scores)}))


if __name__ == "__main__":
    main()
