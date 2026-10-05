"""Independent saved-scalar arithmetic, never re-runs a model or selects it."""

import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import time


OUT = Path("/workspaces/quoridor/research-data/ai-sigma/frame23-rootmean-saved-arithmetic")
OLD = Path("/workspaces/quoridor/research-data/ai-sigma/frame23-independent-evaluation")
TASK = "frame23-rootmean-saved-arithmetic-293-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(rows, model, np):
    by_family = {}
    for row in rows:
        by_family.setdefault(row["canonical_family"], []).append(row)
    family_metrics = []
    for family, values in sorted(by_family.items()):
        p = np.array([row["prediction"][model] for row in values], dtype="float64")
        t = np.array([row["rootmean"] for row in values], dtype="float64")
        z = np.array([row["z"] for row in values], dtype="float64")
        family_metrics.append(
            {
                "family": family,
                "n": len(values),
                "rootmeanMSE": float(np.mean((p - t) ** 2)),
                "zMSE": float(np.mean((p - z) ** 2)),
                "zsign": float(np.mean(np.sign(p) == np.sign(z))),
                "rootmeanbias": float(np.mean(p - t)),
                "saturation": float(np.mean(np.abs(p) >= 0.99)),
            }
        )
    p = np.array([row["prediction"][model] for row in rows], dtype="float64")
    t = np.array([row["rootmean"] for row in rows], dtype="float64")
    z = np.array([row["z"] for row in rows], dtype="float64")
    return {
        "rows": len(rows),
        "families": len(by_family),
        "equalfamily": {
            key: float(np.mean([r[key] for r in family_metrics]))
            for key in ("rootmeanMSE", "zMSE", "zsign", "rootmeanbias", "saturation")
        },
        "rowweighted": {
            "rootmeanMSE": float(np.mean((p - t) ** 2)),
            "zMSE": float(np.mean((p - z) ** 2)),
            "zsign": float(np.mean(np.sign(p) == np.sign(z))),
            "zero_prediction": int(np.sum(p == 0)),
        },
        "perfamily": family_metrics,
    }


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    register_path = Path(args.registration)
    registration = json.loads(register_path.read_text())
    assert registration["task"] == TASK and registration["entry_SHA"] == sha(__file__)
    if args.mock:
        import sys

        assert sys.argv.count(str(register_path)) == 1
        sample = {("family-a", "same-id"): 0.25, ("family-b", "same-id"): -0.5}
        assert (
            len(sample) == 2 and sample[("family-a", "same-id")] != sample[("family-b", "same-id")]
        )
        result = {
            "task": TASK,
            "schema": "registration-argument-mock-293-v1",
            "PASS": True,
            "entry_SHA": sha(__file__),
            "registration_path_exactly_once": True,
            "argv": sys.argv,
            "targets_read": False,
            "NN": 0,
        }
        (OUT / "argument-registration-mock-v1.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = "1"
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    import numpy as np

    for path, expected in registration["inputs"].items():
        assert sha(path) == expected
    with gzip.open(OLD / "frozen-future-predictions-v1.jsonl.gz", "rt") as stream:
        predicted = [json.loads(line) for line in stream]
    labels = []
    for label_file in registration["scalar_label_files"]:
        label_path = Path(label_file)
        opener = gzip.open if label_path.suffix == ".gz" else open
        with opener(label_path, "rt") as stream:
            labels.extend(json.loads(line) for line in stream)
    lookup = {(r["canonical_family"], r["id"]): r for r in labels}
    assert len(lookup) == len(labels) == 3453
    rows = []
    for row in predicted:
        label = lookup.pop((row["canonical_family"], row["id"]))
        for field in ("rootmean", "z"):
            value = float(label[field])
            assert np.isfinite(value) and -1 <= value <= 1
            row[field] = value
        rows.append(row)
    assert not lookup and len(rows) == 3453
    assert len({r["canonical_family"] for r in rows}) == 96
    models = ("candidate", "D", "oldB")
    whole = {model: metrics(rows, model, np) for model in models}
    pairs = {}
    for a, b in (("candidate", "D"), ("candidate", "oldB"), ("oldB", "D")):
        for target in ("rootmeanMSE", "zMSE", "zsign"):
            aa, bb = whole[a]["perfamily"], whole[b]["perfamily"]
            assert [r["family"] for r in aa] == [r["family"] for r in bb]
            delta = np.array([x[target] - y[target] for x, y in zip(aa, bb)])
            rng = np.random.default_rng(28780311)
            boot = np.mean(delta[rng.integers(0, len(delta), size=(2000, len(delta)))], axis=1)
            pairs[f"{a}minus{b}:{target}"] = {
                "mean": float(delta.mean()),
                "95percentile": np.quantile(boot, [0.025, 0.975]).tolist(),
                "negative": int((delta < 0).sum()),
                "zero": int((delta == 0).sum()),
                "positive": int((delta > 0).sum()),
                "n_family": len(delta),
                "bootstrap_seed": 28780311,
                "repetitions": 2000,
                "fixed_fits": True,
            }
    groups = {}
    for kind in ("cohort", "side", "phase"):
        subset = {}
        for row in rows:
            key = (
                ("early" if row["ply"] < 20 else "middle" if row["ply"] < 60 else "late")
                if kind == "phase"
                else str(row[kind])
            )
            subset.setdefault(key, []).append(row)
        groups[kind] = {
            key: {model: metrics(items, model, np) for model in models}
            for key, items in sorted(subset.items())
        }
    result = {
        "task": TASK,
        "schema": "rootmean-saved-scalar-evaluation-293-v1",
        "PASS": True,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "planned_family": 96,
        "obtained_family": 96,
        "eligible_family": 96,
        "zeroeligible_family": 0,
        "planned_raw_rows": 3453,
        "eligible_rows": 3453,
        "excluded_rows": 0,
        "NN": 0,
        "model_forward": False,
        "whole": whole,
        "paired": pairs,
        "groups": groups,
        "source_inputs": registration["inputs"],
        "limits": [
            "producer Arrow reader/alias/source and shared RuleA teacher qualification dependency",
            "old history crossformat UNVERIFIED; literal OR0 not complete history independence",
            "96 preassigned families, fixed cohort/tau1 distribution; not universal IID or strength",
            "rootmean is K64 generated target, not deep truth; z one game outcome",
            "fixed candidate selected by validation, no test-result reselection",
            "quantity/epoch/steps/old-data/protocol distribution effects not single causal quantity",
        ],
        "command_body_seconds": time.monotonic() - start,
    }
    with gzip.open(OUT / "result-v1.json.gz", "wt") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("task", "schema", "PASS", "paired", "NN")}))


if __name__ == "__main__":
    main()
