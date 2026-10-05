#!/usr/bin/env python3
"""Run native numerical/whole-request benchmarks; no Python model forward."""

import argparse
import hashlib
import json
import statistics
import subprocess
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--binary", type=Path, required=True)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--ort-library", type=Path, required=True)
    p.add_argument("--aoti", type=Path, required=True)
    p.add_argument("--tensorrt", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--core", type=int, default=4)
    a = p.parse_args()
    if a.output.exists():
        p.error("output exists")
    a.output.mkdir(parents=True)
    features = json.loads(a.inputs.read_text())
    cases = []
    begin = time.monotonic()
    for batch in [1, 2, 3, 5, 6, 7, 8, 16, 24]:
        sample = a.output / f"input-b{batch}.json"
        sample.write_text(json.dumps(features[:batch]))
        rows = {}
        backends = [("ort", a.model, a.ort_library), ("graph", a.aoti, Path("unused"))]
        if a.tensorrt:
            backends.append(("tensorrt", a.tensorrt, Path("unused")))
        for backend, model, library in backends:
            start = time.monotonic()
            proc = subprocess.run(
                [
                    "taskset",
                    "-c",
                    str(a.core),
                    str(a.binary),
                    backend,
                    str(model),
                    str(library),
                    str(sample),
                ],
                text=True,
                capture_output=True,
                timeout=60,
            )
            (a.output / f"{backend}-b{batch}.stderr").write_text(proc.stderr)
            if proc.returncode:
                raise RuntimeError(
                    f"{backend} B{batch} exit {proc.returncode}: {proc.stderr[-4096:]}"
                )
            result = json.loads(proc.stdout)
            result["process_seconds"] = time.monotonic() - start
            (a.output / f"{backend}-b{batch}.json").write_text(json.dumps(result))
            result["steady_median_seconds"] = statistics.median(result["forward_seconds"][1:])
            rows[backend] = result
        baseline = rows["ort"]["outputs"]
        errors = {}
        for backend, row in rows.items():
            errors[backend] = max(
                abs(x - y)
                for bx, rx in zip(baseline, row["outputs"], strict=True)
                for x, y in zip(bx, rx, strict=True)
            )
            if any(
                abs(x - y) > 1e-4 + 1e-4 * abs(x)
                for bx, rx in zip(baseline, row["outputs"], strict=True)
                for x, y in zip(bx, rx, strict=True)
            ):
                raise ValueError(f"{backend} B{batch} parity failed")
        cases.append(
            {
                "batch": batch,
                "max_abs_error": errors,
                "steady_median_seconds": {k: v["steady_median_seconds"] for k, v in rows.items()},
                "initialization_seconds": {k: v["initialization_seconds"] for k, v in rows.items()},
                "first_forward_seconds": {k: v["forward_seconds"][0] for k, v in rows.items()},
            }
        )
    report = {
        "schema": "quoridor-native-inference-verification-v1",
        "cases": cases,
        "wall_seconds": time.monotonic() - begin,
        "inputs_sha256": hashlib.sha256(a.inputs.read_bytes()).hexdigest(),
        "source_model_sha256": hashlib.sha256(a.model.read_bytes()).hexdigest(),
        "tolerance": {"atol": 1e-4, "rtol": 1e-4},
        "whole_request": "H2D + inference + D2H + owned stream synchronization + Rust output validation; CUDA first forward captures/warm separately",
        "fixed_order": ["ort", "graph", "tensorrt"],
        "limits": "finite legal-prefix fixtures, one hardware host; fixed order and concurrent CPU compilation do not establish causal whole-generation speedup",
    }
    (a.output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
