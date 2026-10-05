"""Task-local, label-free strict restoration and native/Torch diagnosis (no fit)."""

import os

os.environ["ORT_DISABLE_TELEMETRY"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    cfg = json.loads(Path(ap.parse_args().config).read_text())
    assert cfg["task"] == "model-cause-266-stage-a-v1"
    out = Path(cfg["out"])
    out.mkdir(exist_ok=False, parents=True)
    start = time.monotonic()
    original_affinity = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {2})
    native_command = [
        "/usr/bin/taskset",
        "-c",
        ",".join(map(str, original_affinity)),
        cfg["native"],
    ]
    assert sha(cfg["native"]) == cfg["native_SHA"], "NATIVE_BINARY_SHA"
    bind = json.loads(Path(cfg["binding"]).read_text())
    for path, info in bind["model_refs"].items():
        assert sha(path) == info["SHA"], path
    sys.path.insert(0, cfg["python_root"])
    # Prefix selection runs without framework/model imports, before predictions.
    prepare = dict(
        cfg["native_base"],
        mode="prepare",
        engines=[],
        prefixes=[],
        generate=cfg["selection"],
        output=str(out / "openings.json"),
        counter=str(out / "native-counter.json"),
    )
    write(out / "prepare-config.json", prepare)
    subprocess.run(native_command + ["--config", str(out / "prepare-config.json")], check=True)
    opening = json.loads((out / "openings.json").read_text())
    accepted = [r for r in opening["rows"] if "prefix" in r]
    assert len(accepted) == 16, "OPENING_UNAVAILABLE"
    # First six specified cohorts are fixed for B before loading either model.
    write(
        out / "arena-openings-freeze.json",
        {
            "schema": "native-opening-plan-v1",
            "selected_slots": list(range(6)),
            "rows": accepted[:6],
            "selection_SHA": sha(out / "openings.json"),
            "results_used": False,
            "not_formal_holdout": True,
        },
    )
    import torch
    import numpy as np
    from quoridor_training.scaled_model import build_model
    from quoridor_training.train import export

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    old_cfg = json.loads(Path(bind["original_config"]).read_text())
    scale = {key: bind["L"][key] for key in ("mu_f32", "sigma_f32")}
    model_root = Path(cfg["model_out"])
    model_root.mkdir(parents=True, exist_ok=False)
    models, manifests, tensor_receipts = {}, {}, {}
    names = bind["L"]["names"]
    for mode in ("L", "I"):
        cp = torch.load(bind[mode + "_checkpoint"], map_location="cpu", weights_only=True)
        state = cp["model"]
        assert set(state) == set(names), "TENSOR_NAMES"
        for key, shape in zip(names, bind["L"]["shapes"]):
            assert list(state[key].shape) == shape
            assert state[key].dtype == torch.float32 and torch.isfinite(state[key]).all()
        model = build_model(old_cfg["model"], scale)
        model.load_state_dict(
            state, strict=True
        )  # saved scaled tensor replaces construction compensation
        model.eval()
        models[mode] = model
        manifests[mode] = str(
            export(model, old_cfg, scale, bind["L"]["distance_fit"], model_root / mode)
        )
        vector_sha = sha(model_root / mode / "weights.f32")
        if mode == "L":
            assert vector_sha == bind["L"]["weights_SHA"], "L_EXPORT_BYTES"
        tensor_receipts[mode] = {
            "checkpoint_SHA": sha(bind[mode + "_checkpoint"]),
            "weights_SHA": vector_sha,
            "weights_B": (model_root / mode / "weights.f32").stat().st_size,
            "same_saved_scaled_tensors": True,
            "recompensated_after_load": False,
        }
    engines = [
        {"id": m, "kind": "nnue", "manifest": manifests[m], "a": None, "b": None}
        for m in ("L", "I")
    ]
    fit = cfg["distance_baseline"]
    engines.append({"id": "D", "kind": "distance", "manifest": None, **fit})
    native_cfg = dict(
        cfg["native_base"],
        mode="diagnose",
        engines=engines,
        prefixes=[r["prefix"] for r in accepted] + [opening["goal_probe_prefix"]],
        generate=None,
        output=str(out / "native.json"),
        counter=str(out / "native-counter.json"),
    )
    write(out / "diagnose-config.json", native_cfg)
    subprocess.run(native_command + ["--config", str(out / "diagnose-config.json")], check=True)
    native = json.loads((out / "native.json").read_text())
    assert native["schema"] == "native-nnue-diagnosis-v1"
    write(
        out / "native-counter.json",
        {
            "NN": native["NN"],
            "search_processed": native["processed"],
            "preparation_nodes": opening["preparation_nodes"],
            "processed": native["processed"] + opening["preparation_nodes"],
            "inflight_upper": 0,
        },
    )
    torch_count, checks = 0, []
    with torch.inference_mode():
        for mode, model in models.items():
            rows, expected = [], []
            for row in native["predictions"]:
                if row["feature"]["terminal"] is not None:
                    continue
                if row.get("engine") == mode:
                    rows.append(row["feature"])
                    expected.append(row["full"])
                elif "values" in row:
                    rows.append(row["feature"])
                    expected.append(next(v["value"] for v in row["values"] if v["engine"] == mode))
            x = np.zeros((len(rows), 2, 312), dtype=np.float32)
            for i, row in enumerate(rows):
                for view in range(2):
                    x[i, view, row["ids"][view]] = 1
            d = torch.tensor([r["distance"] for r in rows], dtype=torch.float32)
            side = torch.tensor([r["side"] + 1 for r in rows])
            write(
                out / "torch-counter.json",
                {"completed_NN": torch_count, "inflight_upper": len(rows)},
            )
            pred = model(torch.from_numpy(x), d, side).cpu().numpy()
            torch_count += len(rows)
            write(out / "torch-counter.json", {"completed_NN": torch_count, "inflight_upper": 0})
            ref = np.array(expected, dtype=np.float32)
            diff = np.abs(pred - ref)
            ok = np.isfinite(pred).all() and bool(np.all(diff <= 1e-5 + 1e-4 * np.abs(ref)))
            checks.append(
                {
                    "engine": mode,
                    "samples": len(rows),
                    "maxabs": float(diff.max()),
                    "PASS": bool(ok),
                    "absolute_tolerance": 1e-5,
                    "relative_tolerance": 1e-4,
                }
            )
            assert ok, "TORCH_NATIVE_PARITY"
    total = native["NN"] + torch_count
    assert total <= 100000
    assert native["processed"] + opening["preparation_nodes"] <= 200000
    result = {
        "task": cfg["task"],
        "schema": "model-cause-stage-a-v1",
        "status": "PASS",
        "tensor_receipts": tensor_receipts,
        "parity": checks,
        "Torch_NN": torch_count,
        "native_NN": native["NN"],
        "total_NN": total,
        "search_processed": native["processed"],
        "preparation_nodes": opening["preparation_nodes"],
        "processed": native["processed"] + opening["preparation_nodes"],
        "wall_s": time.monotonic() - start,
        "prefixes": 16,
        "native_SHA": sha(out / "native.json"),
        "opening_SHA": sha(out / "arena-openings-freeze.json"),
        "test_labels_read": False,
        "new_fit": False,
        "terminal_SCORE": 2,
        "target": "learned K64 rootmean; not minimax truth",
        "all_exact_argmax": "NOT_RECORDED",
    }
    write(out / "result.json", result)
    with gzip.open(out / "native.json.gz", "wb") as f:
        f.write((out / "native.json").read_bytes())
    with gzip.open(out / "native.json.gz", "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == result["native_SHA"]
    (out / "native.json").unlink()
    # Only this run's regenerable uncompressed duplicate; compact archive remains bound.
    result["native_gzip_SHA"] = sha(out / "native.json.gz")
    write(out / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
