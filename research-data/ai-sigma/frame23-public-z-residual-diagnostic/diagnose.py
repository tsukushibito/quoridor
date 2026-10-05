"""One registered saved-scalar diagnostic; no model or future-label loader."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import struct
import time

import numpy as np

GAMMA = [0.0, 0.125, 0.25, 0.5, 0.75, 1.0]
EPSILON = 1e-6
ROOT = Path("/workspaces/quoridor")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for body in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(body)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n")


def transform(prediction, distance, gamma):
    if not np.isfinite(prediction).all() or not np.isfinite(distance).all():
        raise ValueError("nonfinite saved prediction or input")
    if np.any(np.abs(prediction) > 1):
        raise ValueError("saved tanh output outside [-1,1]")
    # Native rawdistance and logit arithmetic are f32, before f64 tanh.
    difference = np.subtract(distance[:, 1], distance[:, 0], dtype=np.float32)
    logit = np.add(np.float32(0), np.float32(8) * difference, dtype=np.float32)
    bounded = np.clip(prediction.astype(np.float64), -1 + EPSILON, 1 - EPSILON)
    inverted = np.arctanh(bounded)
    restored = logit.astype(np.float64) + gamma * (inverted - logit)
    return np.tanh(restored).astype(np.float32), logit, bounded


def signature(row, distance):
    if (
        row["side"] != 1
        or row["ids_order"] != "P1_then_P2"
        or row["tensor_view_order"] != "STM_then_opponent"
        or row["distance_order"] != "STM_then_opponent_f32"
    ):
        raise ValueError("public canonical STM metadata order")
    ids = row["ids"]
    if len(ids) != 2 or any(
        view != sorted(set(view)) or not view or min(view) < 0 or max(view) >= 312 for view in ids
    ):
        raise ValueError("sparse IDs shape/order/range")
    if np.asarray(row["distance"], dtype="<f4").tobytes() != distance.tobytes():
        raise ValueError("metadata and raw f32 distance bytes differ")
    body = [np.asarray(view, dtype="<u2").tobytes() for view in ids]
    key = b"QF1-f32-STM-v1\0" + struct.pack("<HH", len(body[0]), len(body[1]))
    return hashlib.sha256(key + b"".join(body) + distance.tobytes()).hexdigest()


def references(ref):
    if sha(ref["path"]) != ref["SHA"]:
        raise ValueError("frozen reference compressed SHA")
    rows, digest = {}, hashlib.sha256()
    with gzip.open(ref["path"], "rb") as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            if row["id"] in rows:
                raise ValueError("duplicate frozen reference ID")
            rows[row["id"]] = row["input_signature"]
    if digest.hexdigest() != ref["uncompressed_SHA"] or len(rows) != ref["rows"]:
        raise ValueError("frozen reference uncompressed SHA/denominator")
    return rows


def load_part(item, reference, validation_inputs):
    path = Path(item["path"])
    allowed = ROOT / ".worktree/assets/inputs/sigma-public-fix-z/canonical-v3"
    cycle, split = item["cycle"], item["split"]
    if (cycle, split) not in ((41, "train"), (42, "validation")):
        raise ValueError("only 0041 train and 0042 selection allowed")
    if path != allowed / f"cycle_{cycle:04d}" / "cache":
        raise ValueError("canonical path allowlist")
    manifest = read(path / "cache.json")
    if sha(path / "cache.json") != item["manifest_SHA"] or manifest["allow_test"]:
        raise ValueError("cache manifest changed or test cache")
    n = manifest["rows"]
    for name in ("rows.jsonl", "distance.f32", "labels.f32"):
        if sha(path / name) != manifest["sha256"][name]:
            raise ValueError("cache SHA: " + name)
    # Never read the full dense x tensor: exact input refs are already frozen.
    distance = np.fromfile(path / "distance.f32", dtype="<f4").reshape(n, 2)
    labels = np.fromfile(path / "labels.f32", dtype="<f4").reshape(n, 2)
    if not np.isfinite(distance).all() or not np.isnan(labels[:, 0]).all():
        raise ValueError("finite distance and absent rootmean required")
    chosen, groups, ids, z = [], [], [], []
    seen, raw_groups, raw_to_producer = set(), set(), defaultdict(set)
    counts = {"raw": 0, "zero_reason_unavailable": 0, "decisive": 0, "actual_used": 0}
    counts["raw_actualinput_exposure_to_ALLrawV"] = 0
    counts["decisive_actualinput_exposure_to_ALLrawV"] = 0
    with (path / "rows.jsonl").open() as stream:
        for i, line in enumerate(stream):
            row = json.loads(line)
            if i >= n or row["id"] in seen or row["split"] != split:
                raise ValueError("row length/order/unique/split mismatch")
            seen.add(row["id"])
            if row["rootmean"] is not None or row["teacher_type"] != "external_terminal_outcome":
                raise ValueError("selected public z provenance")
            target = float(labels[i, 1])
            if target not in (-1, 0, 1) or row["z"] != target:
                raise ValueError("recorded z tensor/metadata/decisive predicate")
            key = signature(row, distance[i])
            raw_groups.add(key)
            raw_to_producer[key].add(row["group"])
            counts["raw"] += 1
            counts["zero_reason_unavailable"] += target == 0
            counts["decisive"] += target != 0
            exposed = split == "train" and key in validation_inputs
            counts["raw_actualinput_exposure_to_ALLrawV"] += exposed
            counts["decisive_actualinput_exposure_to_ALLrawV"] += exposed and target != 0
            keep = row["id"] in reference
            if keep and reference[row["id"]] != key:
                raise ValueError("frozen actual-input signature mismatch")
            if split == "validation" and not keep:
                raise ValueError("ALLrawV missing qualified input")
            if keep and target != 0:
                if exposed:
                    raise ValueError("actual fitted input exposed to ALLrawV")
                if not row["primary_eligible"]:
                    raise ValueError("fitted/selected producer-ineligible input")
                chosen.append(i)
                groups.append(key)
                ids.append(row["id"])
                z.append(target)
                counts["actual_used"] += 1
    if len(seen) != n or (split == "train" and not set(reference) <= seen):
        raise ValueError("all raw rows and frozen IDs must be present")
    if any(len(v) != 1 for v in raw_to_producer.values()):
        raise ValueError("one actual input maps to inconsistent producer groups")
    counts["raw_input_groups"] = len(raw_groups)
    counts["actual_input_groups"] = len(set(groups))
    counts["primary_exclusions"] = n - len(chosen)
    return counts, ids, groups, np.asarray(z), distance[chosen]


def describe(z, groups, prediction=None, *, compact=False):
    order = sorted(set(groups))
    index = {g: i for i, g in enumerate(order)}
    inverse = np.asarray([index[g] for g in groups])
    count = np.bincount(inverse)
    means = np.bincount(inverse, weights=z) / count
    result = {
        "rows": len(z),
        "input_groups": len(order),
        "row_z_mean": float(np.mean(z)),
        "group_equal_z_mean": float(np.mean(means)),
        "conflicting_outcome_groups": int(np.sum(np.abs(means) < 1)),
        "empirical_within_input_variance_row": float(np.average(1 - means**2, weights=count)),
        "empirical_within_input_variance_group": float(np.mean(1 - means**2)),
    }
    if compact:
        result["group_count_order"] = (
            "sorted unique frozen Tseen input_signature; referenced, not copied"
        )
        result["group_count_n_positive"] = [
            [int(n), int(round(n * (m + 1) / 2))] for n, m in zip(count, means)
        ]
    else:
        result["group_counts"] = [
            {
                "signature": g,
                "n": int(n),
                "z_mean": float(m),
                "positive": int(round(n * (m + 1) / 2)),
            }
            for g, n, m in zip(order, count, means)
        ]
    if prediction is not None:
        error = prediction.astype(np.float64) - z
        fields = {
            "zMSE": error**2,
            "sign": (np.sign(prediction) == z).astype(np.float64),
            "bias": error,
            "saturation": (np.abs(prediction) >= 0.99).astype(np.float64),
        }
        result["row"] = {k: float(np.mean(v)) for k, v in fields.items()}
        result["inputgroup_equal"] = {
            k: float(np.mean(np.bincount(inverse, weights=v) / count)) for k, v in fields.items()
        }
        pmin = np.full(len(order), np.inf)
        pmax = np.full(len(order), -np.inf)
        np.minimum.at(pmin, inverse, prediction)
        np.maximum.at(pmax, inverse, prediction)
        result["maximum_prediction_range_same_input"] = float(np.max(pmax - pmin))
        result["group_metrics"] = [
            {
                "signature": g,
                "n": int(count[j]),
                **{
                    k: float(np.bincount(inverse, weights=v)[j] / count[j])
                    for k, v in fields.items()
                },
                "prediction_min": float(pmin[j]),
                "prediction_max": float(pmax[j]),
            }
            for j, g in enumerate(order)
        ]
    return result


def check_order(ids, saved_order):
    if ids != saved_order or len(set(ids)) != len(ids):
        raise ValueError("saved scalar row order/unique identity differs")


def fixture():
    distance = np.asarray([[0.1, 0.2], [0.2, 0.1], [0.1, 0.1]], dtype=np.float32)
    saved = np.asarray([0.3, -0.4, 0.1], dtype=np.float32)
    zero, logit, _ = transform(saved, distance, 0)
    one, _, _ = transform(saved, distance, 1)
    assert np.array_equal(zero, np.tanh(logit.astype(np.float64)).astype(np.float32))
    assert np.array_equal(one, saved)
    _, _, clipped = transform(np.asarray([-1, 1, 0], dtype=np.float32), distance, 1)
    assert np.array_equal(clipped, [-1 + EPSILON, 1 - EPSILON, 0])
    d = describe(np.asarray([1, -1, 1]), ["a", "a", "b"], np.asarray([0, 0, 1]))
    assert d["rows"] == 3 and d["input_groups"] == 2
    assert d["row"]["zMSE"] == 2 / 3 and d["inputgroup_equal"]["zMSE"] == 0.5
    assert d["conflicting_outcome_groups"] == 1
    try:
        transform(np.asarray([np.nan] * 3), distance, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("nonfinite not rejected")
    check_order(["row0", "row1"], ["row0", "row1"])
    try:
        check_order(["row0", "row1"], ["row1", "row0"])
    except ValueError:
        pass
    else:
        raise AssertionError("row permutation not rejected")
    return {"schema": "saved-amplitude-fixture-297-v1", "PASS": 6, "NN": 0, "real_data": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration")
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    if args.fixture:
        print(json.dumps(fixture()))
        return
    reg = read(args.registration)
    if reg["task"] != "saved-residual-amplitude-297-v1" or reg["gamma"] != GAMMA:
        raise ValueError("wrong task/gamma")
    start = time.monotonic()
    output = Path(reg["output"])
    if output.exists():
        raise ValueError("result already exists; no automatic rerun")
    for path, digest in reg["input_SHA"].items():
        if sha(path) != digest:
            raise ValueError("registered metadata/source binding changed: " + path)
    freeze = read(reg["freeze"])
    if freeze["baselines"]["D"]["a_f32"] != 0 or freeze["baselines"]["D"]["b_f32"] != 8:
        raise ValueError("frozen raw D coefficients differ")
    tref = references(freeze["references"]["Tseen"]["canonical"])
    vref = references(freeze["references"]["Vraw"]["canonical"])
    validation_inputs = set(vref.values())
    train = load_part(reg["caches"][0], tref, validation_inputs)
    val = load_part(reg["caches"][1], vref, validation_inputs)
    tc, ti, tg, tz, td = train
    vc, vi, vg, vz, vd = val
    with gzip.open(reg["validation_order"], "rt") as stream:
        saved_order = json.load(stream)
    check_order(vi, saved_order)
    if len(vi) != 19846 or len(ti) != 67937:
        raise ValueError("saved scalar actual row order/denominator differs")
    if len(set(vg)) != 20 or len(vref) != 19965:
        raise ValueError("fixed selection input-group/ALLrawV denominator")
    saved = np.fromfile(reg["scalar"]["path"], dtype="<f4")
    if len(saved) != len(vi):
        raise ValueError("scalar length differs")
    values = []
    for gamma in GAMMA:
        pred, logit, bounded = transform(saved, vd, gamma)
        report = describe(vz, vg, pred)
        # Counts are repeated intentionally, but raw/scalar bytes are not copied.
        values.append({"gamma": gamma, **report})
    if abs(values[-1]["row"]["zMSE"] - freeze["candidate"]["selection_mse"]) > 1e-6:
        raise ValueError("saved selected row-MSE source binding differs")
    d, _, _ = transform(saved, vd, 0)
    one, _, bounded = transform(saved, vd, 1)
    initial = np.fromfile(reg["initial_scalar"]["path"], dtype="<f4")
    if len(initial) != len(saved):
        raise ValueError("saved initial scalar order/length")
    error0, error1 = float(np.max(np.abs(d - initial))), float(np.max(np.abs(one - saved)))
    if not np.allclose(d, initial, atol=1e-6, rtol=1e-6):
        raise ValueError("gamma0 native D and saved initial differ")
    if not np.allclose(one, saved, atol=1e-6, rtol=1e-6):
        raise ValueError("gamma1 inversion restoration differs")
    constant = freeze["baselines"]["constant"]["value"]
    if abs(constant - float(np.mean(tz))) > 1e-12:
        raise ValueError("original train-only constant denominator differs")
    result = {
        "schema": "saved-residual-amplitude-diagnostic-v1",
        "task": reg["task"],
        "status": "FINITE_SAVED_ARITHMETIC",
        "UTC": datetime.now(timezone.utc).isoformat(),
        "registration_SHA": sha(args.registration),
        "NN": 0,
        "train": {"denominators": tc, **describe(tz, tg, compact=True)},
        "train_predictions": {"status": "UNAVAILABLE", "forward_to_fill": False},
        "selection": {"denominators": vc, "gamma": values},
        "constant": {
            "value": constant,
            "train_only": True,
            **describe(vz, vg, np.full(len(vz), constant)),
        },
        "restoration": {
            "gamma0_max_abs_vs_saved_initial": error0,
            "gamma1_max_abs_vs_saved_prediction": error1,
            "epsilon": EPSILON,
            "saved_endpoint_count": int(np.sum(np.abs(saved) == 1)),
            "inversion_clipped_count": int(np.sum(saved.astype(np.float64) != bounded)),
            "saved_min": float(np.min(saved)),
            "saved_max": float(np.max(saved)),
            "limits": "tanh inverse cannot recover true logits at rounded/clipped endpoints; a fixed gamma is a new inference condition, not candidate weights",
        },
        "whole_command_wall_before_result_write_s": time.monotonic() - start,
        "scientific_status": "exploratory train/selection diagnostic; no independent test or strength claim",
        "game_history_absolute_side": "UNAVAILABLE; input groups are not independent games; CI not estimated",
        "variance_floor": "empirical label conflict descriptive only; not Bayes truth or trained baseline",
        "dense_x_read": False,
        "old_candidate_or_selection_changed": False,
    }
    write(output, result)
    print(json.dumps({"task": reg["task"], "status": result["status"], "NN": 0}))


if __name__ == "__main__":
    main()
