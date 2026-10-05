"""One admitted fixed-step penalty fit, native parity, and selection diagnostic."""

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ["ORT_DISABLE_TELEMETRY"] = "1"
import numpy as np

from quoridor_training.cache import load, sha
from quoridor_training.route_training import (
    append_train_inputs,
    detailed_metrics,
    extra_train_inputs,
    load_route_cache,
    read_input_metadata,
    select_cache_partition,
)
from quoridor_training.train import write


def widths(rows, prediction, distance):
    bygroup = {}
    for row, p, d in zip(rows, prediction, distance):
        if row["rootmean"] is None:
            continue
        residual, error = float(p) - float(d), float(row["rootmean"]) - float(d)
        g = bygroup.setdefault(row["group"], {"n": 0, "displacement": 0.0, "alignment": 0.0})
        g["n"] += 1
        g["displacement"] += residual**2
        g["alignment"] += -2 * residual * error
    normalized = {
        k: {
            "rows": v["n"],
            "displacement": v["displacement"] / v["n"],
            "alignment": v["alignment"] / v["n"],
            "teacher_gap": (v["displacement"] + v["alignment"]) / v["n"],
        }
        for k, v in bygroup.items()
    }
    return {
        "groups": normalized,
        "games": len(normalized),
        "displacement": float(np.mean([v["displacement"] for v in normalized.values()])),
        "alignment": float(np.mean([v["alignment"] for v in normalized.values()])),
        "r_rms_game": float(np.sqrt(np.mean([v["displacement"] for v in normalized.values()]))),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("registration")
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    for path, digest in reg["input_SHA"].items():
        if sha(path) != digest:
            raise ValueError("input binding changed: " + path)
    output = Path(reg["output"])
    if output.exists():
        raise ValueError("successful/partial output must not be replaced")
    from quoridor_training.residual_penalty import components, fixture
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    fixture_result = fixture()
    # No random tensors in the fixture. Initial seed is set by the original trainer.
    original = load_route_cache(reg["old_cache"])
    cache_args = argparse.Namespace(
        extra_train_cache=reg["extra_cache"],
        extra_train_metadata=reg["extra_metadata"],
        extra_train_groups=reg["extra_groups"],
    )
    extra, meta = extra_train_inputs(cache_args)
    with gzip.open(original[0]["sources"]["validation"]["path"], "rt") as stream:
        oldvalmeta = [json.loads(line) for line in stream]
    combined = append_train_inputs(original, extra, oldvalmeta, meta)
    binding, rows, _, raw, _ = combined
    if binding["dataset_sha"] != reg["same_dataset_SHA"]:
        raise ValueError("B dataset/mask/order changed")
    # This is analytic tensor arithmetic, not another model forward.
    dvalues = torch.tanh(torch.from_numpy(np.float32(8) * (raw[:, 1] - raw[:, 0]))).numpy()
    reference = {r["id"]: d for r, d in zip(rows, dvalues)}

    def measure(mrows, pred, target, constant):
        d = np.asarray([reference[r["id"]] for r in mrows], dtype=np.float32)
        result = detailed_metrics(mrows, pred, target, constant)
        result["residual_width"] = widths(mrows, pred, d)
        result["objective_teacher_game_equal"] = result["target_game_equal_mse"]
        result["objective_penalty_game_equal"] = result["residual_width"]["displacement"]
        result["objective_total_game_equal"] = (
            result["target_game_equal_mse"] + result["residual_width"]["displacement"]
        )
        return result

    def observer(step, trows, trainpred, vrows, valpred):
        if step == 0:
            for r, p in zip(trows + vrows, np.concatenate([trainpred, valpred])):
                if np.float32(p).view("u4") != np.float32(reference[r["id"]]).view("u4"):
                    raise ValueError("initial D bit parity")
        if step in (200, 2000):
            with gzip.open(output / f"oldval-predictions-step{step}.jsonl.gz", "wt") as stream:
                for r, p in zip(vrows, valpred):
                    stream.write(
                        json.dumps(
                            {**r, "prediction": float(p), "D_initial": float(reference[r["id"]])}
                        )
                        + "\n"
                    )

    from quoridor_training import route_training

    sys.argv = [str(Path(route_training.__file__)), *reg["route_argv"]]
    route_training.main(
        objective=lambda p, t, d: components(p, t, d, 1.0),
        checkpoint_steps=(200,),
        evaluation_observer=observer,
        measure=measure,
        parity_checkpoints=("step200", "last"),
    )
    write(output / "fixture.json", fixture_result)
    write(
        output / "objective.json",
        {
            "lambda": 1,
            "teacher": "rootmean",
            "penalty": "squared(prediction-D_initial)",
            "reduction": "mean in same game-uniform then row-uniform sampled batch",
            "primary": 200,
            "last_secondary": 2000,
            "D": "tanh(f32(8 * (STM_f32_dopp-STM_f32_dself)))",
            "D_input_label_free": True,
            "evaluator_or_output_shrink_changed": False,
        },
    )
    freeze = json.loads((output / "freeze.json").read_text())
    if (
        freeze["initial_weights_sha"] != reg["same_initial_SHA"]
        or freeze["batch_order_sha256"] != reg["same_batch_SHA"]
    ):
        raise ValueError("initial or batch order changed")
    parity = json.loads((output / "parity.json").read_text())
    if parity["all_NN_samples"] != 328434:
        raise ValueError("training/parity sample formula")
    # Reuse the exact old label-free mask, bound to unchanged maximum-train inputs.
    mask = json.loads(Path(reg["selection_mask"]).read_text())
    _, vrows, x, distance, _ = select_cache_partition(load(reg["extra_cache"]), "validation")
    if len(vrows) != 392 or set(mask["rows"]) != {r["id"] for r in vrows}:
        raise ValueError("same selection row/mask binding")
    metadata = {
        r["id"]: r for r in read_input_metadata(reg["extra_metadata"]) if r["split"] == "validation"
    }
    for r in vrows:
        r.update({"ply": metadata[r["id"]].get("ply"), "cohort": "new-selection"})
    if not all(mask["rows"][r["id"]] for r in vrows):
        raise ValueError("expected unchanged all392 eligible; mask must not be exchanged")
    dense = np.column_stack([distance, np.zeros((len(vrows), 4), dtype=np.float32)])
    cfg = json.loads((output / "config.json").read_text())
    scale = json.loads((output / "scale.json").read_text())
    constant = json.loads((output / "data.json").read_text())["constant"]
    from quoridor_training.residual_model import DistanceResidualModel

    saved = {}
    with gzip.open(reg["saved_selection_predictions"], "rt") as stream:
        for line in stream:
            r = json.loads(line)
            saved[r["id"]] = r
    if set(saved) != {r["id"] for r in vrows}:
        raise ValueError("saved baseline rows differ")
    reference_v = np.asarray(
        [saved[r["id"]]["prediction_by_unique_weightSHA"][reg["same_initial_SHA"]] for r in vrows],
        dtype=np.float32,
    )
    results = {}
    unique = {}
    for tag in ("step200", "last"):
        manifest = json.loads((output / (tag + "-model") / "manifest.json").read_text())
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
        cp = torch.load(output / (tag + ".pt"), map_location="cpu", weights_only=True)
        model.load_state_dict(cp["model"])
        model.eval()
        vector = np.concatenate(
            [
                v.detach().cpu().numpy().astype("<f4").reshape(-1)
                for v in (
                    model.ft.weight,
                    model.ft.bias,
                    model.h.weight,
                    model.h.bias,
                    model.out.weight,
                    model.out.bias,
                )
            ]
        )
        weight_sha = hashlib.sha256(vector.tobytes()).hexdigest()
        if weight_sha != sha(output / (tag + "-model") / "weights.f32"):
            raise ValueError("native PT weights mismatch")
        if weight_sha not in unique:
            with torch.inference_mode():
                pred = model(
                    torch.from_numpy(x), torch.from_numpy(dense), torch.ones(392, dtype=torch.long)
                ).numpy()
            unique[weight_sha] = pred
        pred = unique[weight_sha]
        results[tag] = {
            "weight_SHA": weight_sha,
            "metrics": detailed_metrics(vrows, pred, "rootmean", constant),
            "residual_width": widths(vrows, pred, reference_v),
        }
        with gzip.open(output / f"newselection-predictions-{tag}.jsonl.gz", "wt") as stream:
            for r, p, base in zip(vrows, pred, reference_v):
                stream.write(
                    json.dumps({**r, "prediction": float(p), "D_initial": float(base)}) + "\n"
                )
    curves = json.loads((output / "curves.json").read_text())
    write(
        output / "result.json",
        {
            "task": reg["expected_task"],
            "schema": reg["expected_schema"],
            "status": "PASS",
            "lambda": 1,
            "primary_step": 200,
            "primary": next(c for c in curves if c["step"] == 200),
            "last_secondary": curves[-1],
            "newselection": results,
            "unique_selection_models": len(unique),
            "learning_samples": freeze["samples"],
            "parity_samples": 144,
            "selection_samples": 392 * len(unique),
            "fixture_equivalent_upper": 32,
            "total_NN_upper": freeze["samples"] + 144 + 392 * len(unique) + 32,
            "same_initial_SHA": freeze["initial_weights_sha"],
            "same_batch_SHA": freeze["batch_order_sha256"],
            "same_dataset_SHA": freeze["dataset_sha"],
            "history_cross_format": "UNVERIFIED",
            "selection_mask_SHA": sha(reg["selection_mask"]),
            "independent_test": False,
            "candidate_reselection": False,
            "native_root_action_probe": "NOT_RUN; parity only; teacher MSE is not strength",
        },
    )
    print(
        json.dumps(
            {
                "task": reg["expected_task"],
                "samples_upper": freeze["samples"] + 144 + 392 * len(unique) + 32,
                "status": "PASS",
            }
        )
    )


if __name__ == "__main__":
    main()
