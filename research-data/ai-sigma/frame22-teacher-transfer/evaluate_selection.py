"""Once-only new selection-val diagnostic; never an independent test."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from quoridor_training.cache import load, sha
from quoridor_training.route_training import (
    detailed_metrics,
    load_route_cache,
    model_input_key,
    read_input_metadata,
    select_cache_partition,
)
from quoridor_training.train import write


def canonical_keys(rows):
    keys = set()
    for row in rows:
        p = row["side"] - 1
        x = np.zeros((2, 312), dtype=np.float32)
        x[0, row["ids"][p]] = 1
        x[1, row["ids"][1 - p]] = 1
        keys.add(model_input_key(x, np.asarray(row["distance"], dtype=np.float32)))
    return keys


def read_meta(path):
    rows = read_input_metadata(path)
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("duplicate label-free metadata")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registration")
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    for path, expected in reg["input_SHA"].items():
        if sha(path) != expected:
            raise ValueError("frozen input/model binding changed")
    binding, old_rows, old_x, old_d, _ = load_route_cache(reg["old_cache"])
    old_meta = []
    for split in ("train", "validation"):
        with gzip.open(binding["sources"][split]["path"], "rt") as stream:
            old_meta.extend(json.loads(line) for line in stream)
    newtrain = [r for r in read_meta(reg["largest_new_train_metadata"]) if r["split"] == "train"]
    if any(r["split"] != "train" for r in newtrain):
        raise ValueError("largesttrain metadata split")
    newval = [r for r in read_meta(reg["new_validation_metadata"]) if r["split"] == "validation"]
    exposed = old_meta + newtrain
    state = {r["state_key"] for r in exposed}
    history = {r["history_key"] for r in exposed}
    input_keys = {model_input_key(old_x[i], old_d[i, :2]) for i in range(len(old_rows))}
    input_keys |= canonical_keys(newtrain)
    _, rows, x, distance, y = select_cache_partition(
        load(reg["new_validation_cache"]), "validation"
    )
    if any(r["split"] != "validation" for r in rows) or len(rows) > 2400:
        raise ValueError("new selection-val-only cache/count")
    meta = {r["id"]: r for r in newval}
    if set(meta) != {r["id"] for r in rows}:
        raise ValueError("selection metadata coverage")
    if {r["group"] for r in rows} & {r["group"] for r in exposed}:
        raise ValueError("family leakage")
    eligible = []
    matches = {"state": 0, "history_string": 0, "actual_input": 0, "OR": 0}
    for i, row in enumerate(rows):
        m = meta[row["id"]]
        if m["split"] != "validation" or m["group"] != row["group"]:
            raise ValueError("selection metadata split/group")
        hits = {
            "state": m["state_key"] in state,
            "history_string": m["history_key"] in history,
            "actual_input": model_input_key(x[i], distance[i]) in input_keys,
        }
        shared = any(hits.values())
        for kind, hit in hits.items():
            matches[kind] += int(hit)
        matches["OR"] += int(shared)
        eligible.append(bool(row["primary_eligible"] and not shared))
        row.update({"ply": m.get("ply"), "cohort": m.get("cohort", "new-selection")})
    out = Path(reg["output"])
    out.mkdir()
    groups = {}
    for row, ok in zip(rows, eligible):
        g = groups.setdefault(row["group"], {"all": 0, "eligible": 0})
        g["all"] += 1
        g["eligible"] += int(ok)
    mask = {
        "predicate": "state OR history OR actual STM-f32 input against oldtrain+oldval+largestnewtrain",
        "labels_used": False,
        "rows": {r["id"]: bool(ok) for r, ok in zip(rows, eligible)},
        "groups": groups,
        "planned_groups": 12,
        "observed_groups": len(groups),
        "zeroeligible_groups": sum(v["eligible"] == 0 for v in groups.values()),
        "absent_planned_groups": 12 - len(groups),
        "matches_by_rule": matches,
        "history_cross_format_coverage": "UNVERIFIED; literal equality only, no full-history nonexposure guarantee",
    }
    write(out / "mask.json", mask)
    # Record and bind the label-free mask before any model forward.
    mask_sha = sha(out / "mask.json")
    from quoridor_training.residual_model import DistanceResidualModel
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    dense = np.column_stack([distance, np.zeros((len(rows), 4), dtype=np.float32)])
    chosen = np.flatnonzero(eligible)
    unique, results = {}, {}
    common_model_settings = None
    samples = 0
    for tag, item in reg["models"].items():
        folder, checkpoint = Path(item["folder"]), item["checkpoint"]
        cfg = json.loads((folder / "config.json").read_text())
        scale = json.loads((folder / "scale.json").read_text())
        data = json.loads((folder / "data.json").read_text())
        manifest = json.loads((folder / (checkpoint + "-model") / "manifest.json").read_text())
        weights_sha = sha(folder / (checkpoint + "-model") / "weights.f32")
        settings = {
            "config": cfg["model"],
            "scale": scale,
            "route_mu": manifest["route_mu_f32"],
            "route_sigma": manifest["route_sigma_f32"],
            "parameterization": manifest["value_parameterization"],
        }
        if common_model_settings is None:
            common_model_settings = settings
        if settings != common_model_settings:
            raise ValueError("prediction reuse requires identical model settings and buffers")
        if manifest["distance_fit"] != {"a": 0.0, "b": 8.0}:
            raise ValueError("fixed distance coefficients changed")
        if settings["parameterization"] != "fixed-distance-logit-plus-linear-residual-tanh":
            raise ValueError("fixed a0b8 residual evaluator schema")
        if weights_sha != item["weights_SHA"] or manifest["route_mode"] != "zero4":
            raise ValueError("model identity/condition")
        if weights_sha not in unique:
            if samples + len(rows) > reg["sample_upper"] or len(unique) >= 5:
                raise ValueError("evaluation cap")
            model = DistanceResidualModel(
                cfg["model"],
                scale,
                a=0,
                b=8,
                routes=False,
                route_statistics={
                    "mu_f32": manifest["route_mu_f32"],
                    "sigma_f32": manifest["route_sigma_f32"],
                },
            )
            cp = torch.load(folder / (checkpoint + ".pt"), map_location="cpu", weights_only=True)
            model.load_state_dict(cp["model"])
            ordered = [
                model.ft.weight,
                model.ft.bias,
                model.h.weight,
                model.h.bias,
                model.out.weight,
                model.out.bias,
            ]
            vector = np.concatenate(
                [v.detach().cpu().numpy().astype("<f4").reshape(-1) for v in ordered]
            )
            if hashlib.sha256(vector.tobytes()).hexdigest() != weights_sha:
                raise ValueError("checkpoint/native weight bits differ")
            model.eval()
            with torch.inference_mode():
                prediction = model(
                    torch.from_numpy(x),
                    torch.from_numpy(dense),
                    torch.ones(len(rows), dtype=torch.long),
                ).numpy()
            unique[weights_sha] = prediction
            samples += len(rows)
        prediction = unique[weights_sha]
        results[tag] = {
            "weights_SHA": weights_sha,
            "secondary_all_rows": detailed_metrics(rows, prediction, "rootmean", data["constant"]),
            "primary": (
                detailed_metrics(
                    [rows[i] for i in chosen], prediction[chosen], "rootmean", data["constant"]
                )
                if len(chosen)
                else {"status": "NO_ELIGIBLE_ROWS", "rows": 0}
            ),
        }
    distance_prediction = np.tanh(np.float32(8) * (distance[:, 1] - distance[:, 0])).astype(
        np.float32
    )
    distance_metrics = {
        "row_game_phase_metrics": detailed_metrics(rows, distance_prediction, "rootmean", 0.0),
        "formula": "f32(tanh(f32(8 * f32(dopp-dself)))), a0b8 raw STM distance/80 already encoded",
        "NN_samples": 0,
        "constant0_is_not_a_fitted_baseline": True,
    }
    result = {
        "task": "frame22-teacher-transfer-274-selection-v1",
        "schema": "selection-evaluation-v1",
        "status": "PASS",
        "mask_SHA": mask_sha,
        "actual_unique_NN_models": len(unique),
        "actual_NN_samples": samples,
        "mask_denominators": mask,
        "results": results,
        "distance_analytic": distance_metrics,
        "selection_validation_only": True,
        "independent_test": False,
        "candidate_reselection": False,
        "registration_SHA": hashlib.sha256(Path(args.registration).read_bytes()).hexdigest(),
    }
    write(out / "result.json", result)
    with gzip.open(out / "row-predictions.jsonl.gz", "wt") as stream:
        for i, row in enumerate(rows):
            stream.write(
                json.dumps(
                    {
                        "id": row["id"],
                        "group": row["group"],
                        "eligible": bool(eligible[i]),
                        "rootmean": float(y[i, 0]),
                        "z": row["z"],
                        "prediction_by_unique_weightSHA": {
                            key: float(values[i]) for key, values in unique.items()
                        },
                    }
                )
                + "\n"
            )


if __name__ == "__main__":
    main()
