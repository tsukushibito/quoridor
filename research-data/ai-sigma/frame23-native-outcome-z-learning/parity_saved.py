"""Finite saved-model native parity; no fit, future input, or new arena."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

os.environ["ORT_DISABLE_TELEMETRY"] = "1"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    reg = read(parser.parse_args().registration)
    if reg["task"] != "native-z-saved-parity-298-v1":
        raise ValueError("purpose mismatch")
    for path, digest in reg["input_SHA"].items():
        if sha(path) != digest:
            raise ValueError("parity input/source changed: " + path)
    import numpy as np
    import torch
    from quoridor_training.common import resolve_config
    from quoridor_training.train import build_model

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    out = Path(reg["scope"])
    witness = read(reg["witness"])
    rows = witness["rows"]
    native_run = subprocess.run(
        [reg["native_binary"], "--config", reg["native_config"]],
        capture_output=True,
        text=True,
        timeout=20,
    )
    (out / "native-parity-stdout.log").write_text(native_run.stdout)
    (out / "native-parity-stderr.log").write_text(native_run.stderr)
    if native_run.returncode:
        raise ValueError("maintained native CLI failure; no retry")
    native = read(reg["native_output"])
    if native["schema"] != "native-nnue-diagnosis-v1" or native["searches"]:
        raise ValueError("native task schema/horizon mismatch")
    if not native["parent_history_preserved"] or native["NN"] > 800:
        raise ValueError("native parent preservation/counter")
    cfg = resolve_config(reg["config"])
    scale = read(reg["scale"])
    root_predictions = {p["root"]: p for p in native["predictions"] if "values" in p}
    maxima = {"Torch_scalar": 0.0, "ScalarSIMD": 0.0, "full_delta": 0.0}
    torch_count, private_count = 0, 0
    checked_sides = set()
    for engine in reg["engines"]:
        model = build_model(cfg["model"], scale)
        model.load_state_dict(
            torch.load(engine["checkpoint"], map_location="cpu", weights_only=True)["model"]
        )
        model.eval()
        x = np.zeros((len(rows), 2, 312), dtype=np.float32)
        ds = np.empty((len(rows), 2), dtype=np.float32)
        sides = []
        stream_rows = []
        for ix, row in enumerate(rows):
            pred = root_predictions[ix]
            feat = pred["feature"]
            side = int(feat["side"]) + 1
            if side != row["side"]:
                raise ValueError("native STM side mismatch")
            stm_ids = feat["ids"] if side == 1 else feat["ids"][::-1]
            if stm_ids != row["actualSTM_ids"]:
                raise ValueError("native P1P2 to STM sparse IDs mismatch")
            distance = np.asarray(feat["distance"], dtype="<f4")
            if distance.view("<u4").tolist() != row["STM_distance_f32bits"]:
                raise ValueError("native raw STM f32distance bits mismatch")
            for pside, ids in enumerate(feat["ids"]):
                x[ix, pside, ids] = 1.0
            ds[ix] = distance
            sides.append(side)
            checked_sides.add(side)
            stream_rows.append(
                {"id": row["id"], "ids": feat["ids"], "distance": distance.tolist(), "side": side}
            )
        with torch.inference_mode():
            pv = model(
                torch.from_numpy(x), torch.from_numpy(ds), torch.tensor(sides, dtype=torch.long)
            ).numpy()
        torch_count += len(rows)
        for ix, expected in enumerate(pv):
            actual = next(
                v["value"] for v in root_predictions[ix]["values"] if v["engine"] == engine["id"]
            )
            error = abs(float(expected) - actual)
            maxima["Torch_scalar"] = max(maxima["Torch_scalar"], error)
            if error > 1e-5 + 1e-4 * abs(float(expected)):
                raise ValueError("native/Torch fixed model parity")
        # Existing stopped private binary is comparison-only for the missing
        # maintained CLI SIMD field. No new alternate runtime or math is added.
        replay = stream_rows + stream_rows[:6]
        simd = subprocess.run(
            [reg["comparison_simd_binary"], "model", engine["manifest"]],
            input="\n".join(json.dumps(r) for r in replay) + "\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        (out / (engine["id"] + "-SIMD-stdout.log")).write_text(simd.stdout)
        (out / (engine["id"] + "-SIMD-stderr.log")).write_text(simd.stderr)
        if simd.returncode:
            raise ValueError("comparison-only SIMD CLI failure; no retry")
        sv = [json.loads(line) for line in simd.stdout.splitlines()]
        if len(sv) != len(replay):
            raise ValueError("comparison SIMD row denominator")
        private_count += 3 * len(sv)
        for ix, value in enumerate(sv):
            original_ix = ix if ix < len(rows) else ix - len(rows)
            if value["id"] != replay[ix]["id"]:
                raise ValueError("SIMD row ID order")
            expected = float(pv[original_ix])
            for field in ("value", "delta_value", "simd_value"):
                error = abs(value[field] - expected)
                maxima["ScalarSIMD" if field == "simd_value" else "full_delta"] = max(
                    maxima["ScalarSIMD" if field == "simd_value" else "full_delta"], error
                )
                if error > 1e-5 + 1e-4 * abs(expected):
                    raise ValueError("comparison scalar/SIMD/delta/parent return")
    draw_root = root_predictions[len(rows)]
    if draw_root["feature"]["terminal"] != 0.0 or any(
        v["value"] != 0.0 for v in draw_root["values"]
    ):
        raise ValueError("genuine RuleA terminal draw priority")
    if checked_sides != {1, 2}:
        raise ValueError("P1/P2 witness coverage")
    total = native["NN"] + torch_count + private_count
    if total > reg["sample_upper"]:
        raise ValueError("parity all native/Torch forward charge exceeded")
    result = {
        "task": reg["task"],
        "schema": reg["expected_schema"],
        "status": "FINITE_PARITY_PASS",
        "total_NN": total,
        "processed": native["processed"] + torch_count + private_count,
        "maintained_native_NN": native["NN"],
        "Torch_NN": torch_count,
        "comparison_SIMD_NN": private_count,
        "maxabs": maxima,
        "P2_STM_f32bits": "PASS",
        "terminal_draw_priority": "PASS",
        "full_delta_parent_return": "PASS",
        "witness_rows": len(rows),
        "native_model_engines": len(reg["engines"]),
        "SIMD_scope": "existing stopped comparison-only binary; maintained CLI SIMD field unavailable",
        "no_new_fit_game_future_labels": True,
    }
    Path(reg["expected_output"]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
