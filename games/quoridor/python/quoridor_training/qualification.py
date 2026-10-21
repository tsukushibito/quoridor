"""One bounded supply/math qualification; discards all optimization states.

This uses the maintained model and compact caller. No checkpoint is selected,
no candidate is exported, and no fit is started by this entrypoint.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from .cache import load, sha
from .common import resolve_config
from quoridor_runtime.cycle_process import DeviceMemory
from .train import build_model, export, write


def verify_inputs(config):
    admission = json.loads(Path(config["storage_admission"]).read_text())
    binding = json.loads(Path(config["input_binding"]).read_text())
    scale = json.loads(Path(config["scale"]).read_text())
    source_binding = json.loads(Path(config["source_binding"]).read_text())
    if (
        admission.get("admission") != "within"
        or admission.get("errors")
        or sha(config["storage_admission"]) != config["storage_admission_sha"]
        or sha(Path(config["cache"]) / "cache.json") != binding["cache_manifest_sha"]
        or sha(config["fit_config"]) != binding["fit_config_sha"]
        or sha(config["scale"]) != binding["scale_artifact_sha"]
        or sha(config["source_binding"]) != config["source_binding_sha"]
        or scale.get("binding", {}).get("cache_manifest_sha") != binding["cache_manifest_sha"]
    ):
        raise ValueError("qualification input/admission binding before child/GPU")
    for path, digest in source_binding["source_paths_SHA"].items():
        if sha(path) != digest:
            raise ValueError("qualification science source changed before child/GPU")
    for path, digest in config["control_source_sha"].items():
        if sha(path) != digest:
            raise ValueError("fixed canonical controller changed")
    if sha(config["native_binary"]) != config["native_binary_sha"]:
        raise ValueError("fixed native diagnostic binary changed")


def native_reference(config, model, cfg, statistics, output):
    """Use the existing native diagnostic; no build, teacher or arena."""
    manifest = export(model, cfg, statistics, {"a": 0, "b": 8}, output / "initial-model")
    native_config = {
        "mode": "diagnose",
        "output": str(output / "native.json"),
        "counter": str(output / "native-counter.json"),
        "prefixes": [
            [],
            [13, 67, 81, 66, 14, 65],
            [13, 67, 81, 66, 14, 65, 143, 126, 150, 64, 141, 151],
        ],
        "engines": [{"id": "initial", "kind": "distance_residual", "manifest": str(manifest)}],
        "depths": [],
        "max_nodes": 1,
        "nn_cap": 512,
        "processed_cap": 128,
        "wall_seconds": 3,
        "max_plies": 0,
        "cpu_core": 2,
        "ram_limit": 512 * 1024**2,
        "host_ram_reserve": 4 * 1024**3,
    }
    path = output / "native-config.json"
    write(path, native_config)
    tick = time.monotonic()
    child = subprocess.run(
        [config["native_binary"], "--config", str(path)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    write(
        output / "native-process.json",
        {
            "returncode": child.returncode,
            "wall_seconds": time.monotonic() - tick,
            "direct_child_waited": True,
            "stdout": child.stdout[-4096:],
            "stderr": child.stderr[-4096:],
        },
    )
    child.check_returncode()
    result = json.loads((output / "native.json").read_text())
    features, distances, sides, values = [], [], [], []
    for row in result["predictions"]:
        if row.get("terminal") is not None or row["feature"].get("terminal") is not None:
            continue
        feature = np.zeros((2, 312), dtype=np.float32)
        for view, ids in enumerate(row["feature"]["ids"]):
            feature[view, ids] = 1
        features.append(feature)
        distances.append(row["feature"]["distance"])
        sides.append(row["feature"]["side"] + 1)
        values.append(row["full"] if "full" in row else row["values"][0]["value"])
    if not features:
        raise ValueError("native reference has no nonterminal observations")
    return (
        np.asarray(features),
        np.asarray(distances, dtype=np.float32),
        np.asarray(sides, dtype=np.int64),
        np.asarray(values, dtype=np.float32),
        result["NN"],
    )


def qualify(config):
    started = time.monotonic()
    verify_inputs(config)
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(2)
    torch.manual_seed(31920261006)
    torch.cuda.manual_seed_all(31920261006)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise ValueError("CUDA not available")
    free, total = torch.cuda.mem_get_info()
    if free < 2 * 1024**3:
        raise ValueError("CUDA display/host reserve")
    torch.cuda.set_per_process_memory_fraction(min(5 * 1024**3 / total, 1.0))
    cfg = resolve_config(config["fit_config"])
    corpus = load(config["cache"])
    stats = json.loads(Path(config["scale"]).read_text())
    generator = np.random.default_rng(31920261006)
    indices = np.sort(generator.choice(np.flatnonzero(corpus.splits == 0), 2048, replace=False))
    model = build_model(cfg["model"], stats)
    initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
    x, d, labels = corpus.batch(indices)
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    native_x, native_d, native_side, native_values, native_calls = native_reference(
        config, model, cfg, stats, output
    )
    with torch.inference_mode():
        cpu = model(
            torch.from_numpy(x), torch.from_numpy(d), torch.ones(2048, dtype=torch.long)
        ).numpy()
        native_cpu = model(
            torch.from_numpy(native_x), torch.from_numpy(native_d), torch.from_numpy(native_side)
        ).numpy()
    native_cpu_difference = float(np.max(np.abs(native_cpu - native_values)))
    if native_cpu_difference > 2e-6:
        raise ValueError("initial native/CPU correspondence")
    tick = time.monotonic()
    cpu_optimizer = torch.optim.Adam(model.parameters(), lr=3e-5, weight_decay=0)
    cpu_optimizer.zero_grad(set_to_none=True)
    cpu_loss = torch.nn.functional.mse_loss(
        model(torch.from_numpy(x), torch.from_numpy(d), torch.ones(2048, dtype=torch.long)),
        torch.from_numpy(labels[:, 1].copy()),
    )
    cpu_loss.backward()
    cpu_optimizer.step()
    cpu_state = {name: value.detach().numpy().copy() for name, value in model.state_dict().items()}
    cpu_update_seconds = time.monotonic() - tick
    model.load_state_dict(initial)
    model = model.to("cuda")
    with torch.inference_mode():
        native_cuda = (
            model(
                torch.from_numpy(native_x).to("cuda"),
                torch.from_numpy(native_d).to("cuda"),
                torch.from_numpy(native_side).to("cuda"),
            )
            .cpu()
            .numpy()
        )
    native_cuda_difference = float(np.max(np.abs(native_cuda - native_values)))
    if native_cuda_difference > 2e-6:
        raise ValueError("initial native/CUDA correspondence")
    write(
        output / "progress.json",
        {
            "phase": "native_CPU_CUDA_initial_PASS",
            "native_CPU_difference": native_cpu_difference,
            "native_CUDA_difference": native_cuda_difference,
            "native_calls": native_calls,
            "native_fixture_rows": len(native_x),
            "elapsed_seconds": time.monotonic() - started,
        },
    )
    reports, reference = [], None
    for batch_size in [128, 512, 2048]:
        model.load_state_dict(initial)
        optimizer = torch.optim.Adam(model.parameters(), lr=3e-5, weight_decay=0)
        optimizer.zero_grad(set_to_none=True)
        predictions = np.empty(2048, dtype=np.float32)
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        tick = time.monotonic()
        for first in range(0, 2048, batch_size):
            sub = indices[first : first + batch_size]
            features, distances, local = corpus.batch(sub)
            pred = model(
                torch.from_numpy(features).to("cuda"),
                torch.from_numpy(distances).to("cuda"),
                torch.ones(len(sub), dtype=torch.long, device="cuda"),
            )
            # The same 2048-row objective is accumulated, regardless of supply size.
            loss = (
                torch.nn.functional.mse_loss(
                    pred, torch.from_numpy(local[:, 1].copy()).to("cuda"), reduction="sum"
                )
                / 2048
            )
            loss.backward()
            predictions[first : first + len(sub)] = pred.detach().cpu().numpy()
        optimizer.step()
        torch.cuda.synchronize()
        elapsed = time.monotonic() - tick
        state = {
            name: value.detach().cpu().numpy().copy() for name, value in model.state_dict().items()
        }
        if reference is None:
            reference = state
        parameter_difference = max(float(np.max(np.abs(state[k] - reference[k]))) for k in state)
        cpu_update_difference = max(float(np.max(np.abs(state[k] - cpu_state[k]))) for k in state)
        prediction_difference = float(np.max(np.abs(predictions - cpu)))
        if (
            prediction_difference > 2e-6
            or parameter_difference > 2e-6
            or cpu_update_difference > 2e-6
        ):
            raise ValueError("fixed-objective FP32 supply correspondence")
        reports.append(
            {
                "batch_size": batch_size,
                "rows": 2048,
                "full_supply_forward_backward_one_update_seconds": elapsed,
                "max_cpu_prediction_difference": prediction_difference,
                "max_parameter_difference_vs128": parameter_difference,
                "max_parameter_difference_vs_CPU": cpu_update_difference,
                "allocated_peak_bytes": torch.cuda.max_memory_allocated(),
                "reserved_peak_bytes": torch.cuda.max_memory_reserved(),
                "cold_inclusive": False,
            }
        )
        write(
            output / "progress.json",
            {"reports": reports, "elapsed_seconds": time.monotonic() - started},
        )
        if time.monotonic() - started >= config["seconds"]:
            raise TimeoutError("GPU qualification all-attempt budget")
    write(
        output / "result.json",
        {
            "status": "PASS",
            "cache_manifest_sha": corpus.binding["dataset_sha"],
            "input_indices_sha": sha_array(indices),
            "fit_config_sha": sha(config["fit_config"]),
            "scale_sha": sha(config["scale"]),
            "initial_state_saved": "native qualification export only; no learned/selected checkpoint",
            "candidate_selected": False,
            "GPU_new_all_attempt_seconds": time.monotonic() - started,
            "CPU_forward_rows": 4096 + len(native_x),
            "GPU_forward_rows": 6144 + len(native_x),
            "native_forward_calls": native_calls,
            "native_CPU_max_difference": native_cpu_difference,
            "native_CUDA_max_difference": native_cuda_difference,
            "CPU_equal2048_objective_one_discarded_update_seconds": cpu_update_seconds,
            "native_binary_sha": config["native_binary_sha"],
            "native_scope": "initial H32, maintained diagnostic full/delta/parent preserved/P1/P2; trained weights and explicit ScalarSIMD/undo pending",
            "CUDA_total_bytes": total,
            "CUDA_free_initial_bytes": free,
            "math": "FP32, TF32 off, Adam LR3e-5 wd0; one equal2048-row objective per discarded condition",
            "reports": reports,
        },
    )


def sha_array(array):
    import hashlib

    return hashlib.sha256(np.asarray(array, dtype="<i8").tobytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    verify_inputs(cfg)
    os.sched_setaffinity(0, {2, 3})
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    if args.worker:
        qualify(cfg)
    else:
        import sys
        from quoridor_runtime.cycle_process import (
            CycleResources,
            cancellation_signals,
            execute,
            process_info,
            CycleStopped,
        )

        root = Path(cfg["output"]).parent
        deadline = time.monotonic() + cfg["seconds"]

        class QualificationResources(CycleResources):
            def __init__(self, *args):
                super().__init__(*args)
                self.device = DeviceMemory()
                self.observed = {
                    "peak_family_RSS_including_64MiB_controller_reserve": 0,
                    "peak_whole_device_used_bytes": 0,
                    "VRAM_limit_including_existing_device_users": 6 * 1024**3,
                    "controller_reserve_bytes": 64 * 1024**2,
                }

            def check(self, owned=()):
                super().check(owned)
                infos = [process_info(os.getpid()), *(process_info(x["pid"]) for x in owned)]
                rss = sum(x["rss"] for x in infos if x) + 64 * 1024**2
                used = self.device.used()
                self.observed["peak_family_RSS_including_64MiB_controller_reserve"] = max(
                    self.observed["peak_family_RSS_including_64MiB_controller_reserve"], rss
                )
                self.observed["peak_whole_device_used_bytes"] = max(
                    self.observed["peak_whole_device_used_bytes"], used
                )
                if used > 6 * 1024**3:
                    raise CycleStopped("qualification VRAM cap including existing device usage")

        resources = QualificationResources(
            {
                "max_memory_bytes": 4 * 1024**3 - 64 * 1024**2,
                "host_ram_reserve": 4 * 1024**3,
                "max_output_bytes": 32 * 1024**2,
            },
            root,
            deadline,
        )
        try:
            with cancellation_signals():
                execute(
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "quoridor_training.qualification",
                        "--config",
                        args.config,
                        "--worker",
                    ],
                    root / "supply-qualification.log",
                    deadline,
                    resources=resources,
                )
        finally:
            write(
                root / "observed-resources.json",
                {
                    **resources.observed,
                    "wall_seconds": cfg["seconds"] - max(0, deadline - time.monotonic()),
                    "sampling": "guardian checks, not continuous absolute peak",
                    "memory_scope": "whole device conservative VRAM; worker/guardian RSS plus fixed controller reserve",
                },
            )


if __name__ == "__main__":
    main()
