#!/usr/bin/env python3
"""Export deployable CPU ONNX / CUDA AOTI / TensorRT artifacts, never a forward service."""

from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=["aoti", "tensorrt", "onnx"], default="aoti")
    parser.add_argument("--max-batch", type=int, default=24)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    if not 2 <= args.max_batch <= 4096:
        parser.error("max-batch must be 2..4096")
    if args.output.exists():
        parser.error("output already exists; preserve previous exports")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    import torch
    from folded_sigma import load, MODEL_SHA

    if sha(args.model) != MODEL_SHA:
        raise ValueError("teacher model SHA mismatch")
    torch.set_num_threads(1)
    torch._inductor.config.compile_threads = 1
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.set_float32_matmul_precision("highest")
    start = time.monotonic()
    model = load(args.model).to(args.device).eval()
    example = torch.zeros((2, 8, 9, 9), device=args.device, dtype=torch.float32)
    dynamic = {"raw": {0: torch.export.Dim("batch", min=1, max=args.max_batch)}}
    with torch.inference_mode():
        exported = torch.export.export(model, (example,), dynamic_shapes=dynamic)
        if args.backend == "aoti":
            torch._inductor.aoti_compile_and_package(
                exported,
                package_path=str(args.output),
                inductor_configs={"max_autotune": False, "triton.cudagraphs": False},
            )
        elif args.backend == "onnx":
            torch.onnx.export(exported, (), str(args.output), external_data=False)
        else:
            try:
                import tensorrt as trt
            except ImportError:
                import tensorrt_bindings as trt
            # Build from exported dynamic ONNX, retaining FP32 and forbidding TF32.
            temporary = args.output.with_suffix(".onnx")
            torch.onnx.export(exported, (), str(temporary), external_data=False)
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            network = builder.create_network(0)
            onnx = trt.OnnxParser(network, logger)
            if not onnx.parse(temporary.read_bytes()):
                raise RuntimeError(
                    "\n".join(str(onnx.get_error(i)) for i in range(onnx.num_errors))
                )
            config = builder.create_builder_config()
            config.clear_flag(trt.BuilderFlag.TF32)
            profile = builder.create_optimization_profile()
            profile.set_shape(
                network.get_input(0).name,
                (1, 8, 9, 9),
                (min(8, args.max_batch), 8, 9, 9),
                (args.max_batch, 8, 9, 9),
            )
            config.add_optimization_profile(profile)
            serialized = builder.build_serialized_network(network, config)
            if serialized is None:
                raise RuntimeError("TensorRT build failed")
            args.output.write_bytes(serialized)
            temporary.unlink()
    manifest = {
        "schema": "quoridor-native-inference-v1",
        "backend": args.backend,
        "source_model_sha256": MODEL_SHA,
        "artifact_sha256": sha(args.output),
        "artifact": args.output.name,
        "input_shape": ["batch", 8, 9, 9],
        "output_shapes": [["batch", 136], ["batch", 1]],
        "dtype": "float32",
        "max_batch": args.max_batch,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "device": args.device,
        "runtime_version": trt.__version__ if args.backend == "tensorrt" else torch.__version__,
        "tf32": False,
        "amp": False,
        "export_seconds": time.monotonic() - start,
        "source_sha256": sha(__file__),
        "folded_model_source_sha256": sha(Path(__file__).with_name("folded_sigma.py")),
    }
    args.output.with_suffix(args.output.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
