"""Reaggregate already saved selection scalars and freeze one observational model."""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path):
    p = Path(path)
    return {"path": str(p), "SHA": sha(p), "B": p.stat().st_size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    reg = read(parser.parse_args().registration)
    for path, digest in reg["input_SHA"].items():
        if sha(path) != digest:
            raise ValueError("freeze bound input/source changed: " + path)
    import numpy as np
    from quoridor_training.cache import load

    binding, x, distances, labels, rows = load(reg["cache"])
    output, scope = Path(reg["checkpoint_output"]), Path(reg["scope"])
    ix_t = np.array(
        [i for i, r in enumerate(rows) if r["split"] == "train" and r["primary_eligible"]]
    )
    ix_v = np.array([i for i, r in enumerate(rows) if r["split"] == "validation"])
    if (len(rows), len(ix_t), len(ix_v)) != (19536, 14803, 4733):
        raise ValueError("immutable denominator")
    with gzip.open(output / "validation-order.json.gz", "rt") as stream:
        if json.load(stream) != [rows[i]["id"] for i in ix_v]:
            raise ValueError("saved scalar/row ID order")
    with gzip.open(output / "train-order.json.gz", "rt") as stream:
        if json.load(stream) != [rows[i]["id"] for i in ix_t]:
            raise ValueError("saved train row order")
    y = labels[ix_v, 1].astype(np.float64)
    groups = {}
    for local, index in enumerate(ix_v):
        groups.setdefault(rows[index]["group"], []).append(local)
    if len(groups) != 144 or not np.isfinite(y).all():
        raise ValueError("finite actual family selection")

    def mse(values):
        error = (values.astype(np.float64) - y) ** 2
        return float(np.mean([error[index].mean() for index in groups.values()]))

    constant = read(output / "data.json")["constant"]
    train_stats = read(scope / "actual-sharded-qualification-v1.json")
    if abs(constant - train_stats["family_constant"]) > 1e-12:
        raise ValueError("train-only family constant")
    summaries = []
    curve = read(output / "curves.json")
    p0 = np.fromfile(output / "validation-step0.f32", dtype="<f4")
    rawlogit = np.float32(8.0) * (distances[ix_v, 1] - distances[ix_v, 0])
    analytic_D = np.tanh(rawlogit.astype(np.float64)).astype(np.float32)
    d_max = float(np.max(np.abs(analytic_D - p0)))
    if not np.all(np.abs(analytic_D - p0) <= 1e-7 + 1e-7 * np.abs(p0)):
        raise ValueError("initial zerohead/D f32 formula")
    for c in curve:
        point = c["step"]
        p = np.fromfile(output / f"validation-step{point}.f32", dtype="<f4")
        if len(p) != len(y) or not np.isfinite(p).all():
            raise ValueError("saved scalar cardinality/finite")
        observed = mse(p)
        if abs(observed - c["validation"]["target_game_equal_mse"]) > 1e-12:
            raise ValueError("saved scalar independent reaggregation/curve")
        summaries.append(
            {
                "step": point,
                "selection_family_zMSE": observed,
                "selection_row_zMSE": float(np.mean((p.astype(np.float64) - y) ** 2)),
                "sign_accuracy": float(np.mean(np.sign(p) == np.sign(y))),
                "bias": float(np.mean(p - y)),
                "saturation": float(np.mean(np.abs(p) >= 0.999)),
                "D_gap": observed - mse(p0),
            }
        )
    selected = min(summaries, key=lambda c: (c["selection_family_zMSE"], c["step"]))
    f = read(output / "freeze.json")
    if (
        selected["step"] != f["best_step"]
        or abs(selected["selection_family_zMSE"] - f["best_validation_mse"]) > 1e-12
    ):
        raise ValueError("candidate selection source consistency")
    chosen = selected["step"]
    if sha(output / "best-model/weights.f32") != sha(output / f"step{chosen}-model/weights.f32"):
        raise ValueError("scheduled/best native weights mismatch")
    sampling = read(output / "sampling.json")
    if sampling["seen"] != 1000064 or sum(sampling["family_counts"].values()) != 1000064:
        raise ValueError("actual used training sampling")
    freeze = {
        "schema": "native-outcome-z-candidate-freeze-298-v1",
        "UTC": datetime.now(timezone.utc).isoformat(),
        "selection_rule": "minimum preregistered 144-family equal zMSE; tie earliest step; observed NNUE even when D not beaten",
        "candidate": {
            "condition": "native-z-1m",
            "step": chosen,
            "training_seen": chosen * 128,
            "full_run_seen": sampling["seen"],
            "selection_mse": selected["selection_family_zMSE"],
            "checkpoint": ref(output / f"step{chosen}.pt"),
            "native_manifest": ref(output / "best-model/manifest.json"),
            "native_weights": ref(output / "best-model/weights.f32"),
            "config": ref(reg["config"]),
            "target_metadata": ref(output / "best-model/training-target.json"),
        },
        "initial": {
            "checkpoint": ref(output / "initial.pt"),
            "native_manifest": ref(output / "initial-model/manifest.json"),
            "weights": ref(output / "initial-model/weights.f32"),
            "equal_D_zerohead": True,
            "D_f32maxabs": d_max,
        },
        "baselines": {
            "D": {
                "a_f32": 0.0,
                "b_f32": 8.0,
                "formula": "tanh(f32(0+8*f32(rawSTM_opponent-self))); native f64 tanh cast f32",
                "selection_zMSE": mse(p0),
            },
            "constant": {
                "value": constant,
                "fittrain_only_family_equal": True,
                "train_family_summary": ref(scope / "actual-sharded-qualification-v1.json"),
                "selection_zMSE": mse(np.full(len(y), constant)),
            },
            "public_frozen_baseline": ref(reg["public_baseline_freeze"]),
        },
        "model_settings": {
            "feature": "QF1 sparse312 bothviews plus Zero4",
            "schema": "quoridor-nnue-distance-residual-v3",
            "route_mode": "zero4",
            "value_perspective": "actual side-to-move",
            "scale": ref(reg["scale"]),
            "native_binary": ref(reg["native_binary"]),
            "native_SIMD_comparison_only_binary": ref(reg["comparison_simd_binary"]),
            "sample_semantics": "game uniform then row uniform; seed19080311, generator seed19080312 as maintained trainer",
        },
        "references": {
            "Tseen": ref(scope / "Tseen-input-references.jsonl.gz"),
            "Vraw": ref(scope / "Vraw-input-references.jsonl.gz"),
            "Tseen_rows": 14803,
            "ALLrawV_rows": 4733,
            "Tseen_union": "all eligible train rows conservative across all saved scheduled/best/last weights; actual sample counts in sampling.json",
            "history_literal": "exact private prefix witness with hash+path retained; publichistory unavailable not nonexposure guarantee",
            "dataset": ref(reg["cache"]),
            "split": ref(scope / "registered-family-split-v1.json"),
            "sampling": ref(output / "sampling.json"),
        },
        "source_stop": ref(scope / "source-reader-stop-pre-freeze-v1.json"),
        "science_stops": [
            ref(scope / (t + "-stop.json"))
            for t in ["native-outcome-z-fit-298-v1", "native-z-saved-parity-298-v1"]
        ],
        "parity": ref(scope / "saved-parity-result-v1.json"),
        "summary": summaries,
        "all_planned_families": 576,
        "train_families": 432,
        "selection_families": 144,
        "zeroeligible": 0,
        "new_future_labels_opened": False,
        "known_old_corpus_newselection_not_blind": True,
        "samewall_strength_certified": False,
        "native_teacher_expectation_truth_certified": False,
        "no_candidate_reselect_after_future_eval": True,
    }
    (scope / "candidate-freeze-v1.json").write_text(json.dumps(freeze, indent=2) + "\n")
    result = {
        "task": reg["task"],
        "schema": reg["expected_schema"],
        "status": "FINITE_SCALAR_REAGGREGATION_AND_FREEZE",
        "total_NN": 0,
        "processed": len(rows) * 2,
        "candidate_freeze": ref(scope / "candidate-freeze-v1.json"),
        "sampled_family_min": min(sampling["family_counts"].values()),
        "sampled_family_max": max(sampling["family_counts"].values()),
        "curve_points": len(summaries),
        "candidate_step": chosen,
        "D_zMSE": mse(p0),
        "best_zMSE": selected["selection_family_zMSE"],
        "last_zMSE": summaries[-1]["selection_family_zMSE"],
        "constant_zMSE": mse(np.full(len(y), constant)),
        "scalar_order_finite_curve_reaggregation": "PASS",
        "model_or_forward_imported": False,
    }
    Path(reg["expected_output"]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
