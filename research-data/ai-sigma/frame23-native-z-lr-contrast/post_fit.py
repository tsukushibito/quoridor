"""Saved-main-trainer collector and counted finite parity; not a learner copy."""

import argparse
import json
import os
from pathlib import Path
import subprocess

os.environ["ORT_DISABLE_TELEMETRY"] = "1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    parser.add_argument("--case", choices=["A", "B"], required=True)
    args = parser.parse_args()
    reg = json.loads(Path(args.registration).read_text())
    case = reg["cases"][args.case]
    output, scope = Path(case["output"]), Path(reg["scope"])
    freeze = json.loads((output / "freeze.json").read_text())
    curve = json.loads((output / "curves.json").read_text())
    if freeze["samples"] != 961328 or freeze["initial_weights_sha"] != reg["initial_SHA"]:
        raise ValueError("common initial/actual sample formula")
    if [p["step"] for p in curve] != reg["points"]:
        raise ValueError("registered dense curve schedule")
    sample = json.loads((output / "sampling.json").read_text())
    if sample["seen"] != 512000 or sum(sample["family_counts"].values()) != 512000:
        raise ValueError("realized game sampling denominator")
    import numpy as np
    import torch
    from quoridor_training.common import resolve_config
    from quoridor_training.train import build_model

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    cfg = resolve_config(case["config"])
    scale = json.loads(Path(reg["scale"]).read_text())
    model = build_model(cfg["model"], scale)
    initial = torch.load(output / "initial.pt", map_location="cpu", weights_only=True)["model"]
    displacement = []
    for point in reg["points"]:
        state = torch.load(output / f"step{point}.pt", map_location="cpu", weights_only=True)[
            "model"
        ]
        squared = sum(
            float((state[key].double() - initial[key].double()).square().sum()) for key in initial
        )
        displacement.append(
            {
                "step": point,
                "parameter_displacement_L2": squared**0.5,
                "seen": point * 128,
                "LR_times_steps_proxy_not_Adam_updates": cfg["optimizer"]["lr"] * point,
            }
        )
    native_cfg = {
        "mode": "diagnose",
        "output": str(scope / f"native-parity-{args.case}.json"),
        "counter": str(scope / f"native-parity-counter-{args.case}.json"),
        "prefixes": [[], [13]],
        "engines": [
            {
                "id": "case-" + args.case,
                "kind": "distance_residual",
                "manifest": str(output / "best-model/manifest.json"),
            }
        ],
        "depths": [],
        "max_nodes": 500,
        "nn_cap": 120,
        "processed_cap": 1000,
        "wall_seconds": 5.0,
        "max_plies": 200,
        "cpu_core": 1,
        "ram_limit": 1879048192,
        "host_ram_reserve": 1073741824,
    }
    config_path = scope / f"native-parity-config-{args.case}.json"
    config_path.write_text(json.dumps(native_cfg, indent=2) + "\n")
    result = subprocess.run(
        [reg["native_binary"], "--config", str(config_path)],
        capture_output=True,
        text=True,
        timeout=7,
    )
    (scope / f"native-parity-stdout-{args.case}.log").write_text(result.stdout)
    (scope / f"native-parity-stderr-{args.case}.log").write_text(result.stderr)
    if result.returncode:
        raise ValueError("newweights native parity failure; no retry")
    native = json.loads(Path(native_cfg["output"]).read_text())
    if (
        native["schema"] != "native-nnue-diagnosis-v1"
        or native["searches"]
        or not native["parent_history_preserved"]
    ):
        raise ValueError("saved native parity purpose schema")
    best = torch.load(output / "best.pt", map_location="cpu", weights_only=True)["model"]
    model.load_state_dict(best)
    model.eval()
    checked, maxabs, sides = 0, 0.0, set()
    for row in native["predictions"]:
        if "values" not in row:
            continue
        feat = row["feature"]
        x = np.zeros((1, 2, 312), dtype=np.float32)
        for side, ids in enumerate(feat["ids"]):
            x[0, side, ids] = 1.0
        sides.add(feat["side"])
        with torch.inference_mode():
            value = float(
                model(
                    torch.from_numpy(x),
                    torch.tensor([feat["distance"]], dtype=torch.float32),
                    torch.tensor([feat["side"] + 1], dtype=torch.long),
                )[0]
            )
        error = abs(value - row["values"][0]["value"])
        if error > 1e-5 + 1e-4 * abs(value):
            raise ValueError("newweights Torch/native value parity")
        maxabs = max(maxabs, error)
        checked += 1
    if checked != 2 or sides != {0, 1}:
        raise ValueError("P1/P2 saved native witness")
    parity = native["NN"] + checked
    if parity > 500:
        raise ValueError("registered parity forward reserve exceeded")
    summary = {
        "task": "native-z-lr-" + args.case + "-302-v1",
        "schema": "native-z-lr-case-result-302-v1",
        "status": "FINITE_FIT_AND_SAVED_PARITY",
        "case": args.case,
        "LR": cfg["optimizer"]["lr"],
        "fit_NN": freeze["samples"],
        "native_parity_NN": native["NN"],
        "Torch_parity_NN": checked,
        "total_NN": freeze["samples"] + parity,
        "processed_reserved": case["processed_upper"],
        "seen": sample["seen"],
        "best_checkpoint_seen": freeze["best_step"] * 128,
        "freeze": freeze,
        "displacement": displacement,
        "native_parity_maxabs": maxabs,
        "native_main_SIMD_field": "NOT_RECORDED; previous unchanged math proof is not newweights SIMD runtime certification",
        "extra_fit_or_validation_forward": 0,
        "future_labels_loaded": False,
    }
    (scope / f"case-{args.case}-result-v1.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {"case": args.case, "status": summary["status"], "total_NN": summary["total_NN"]}
        )
    )


if __name__ == "__main__":
    main()
