#!/usr/bin/env python3
"""Prepare isolated CUDA compile headers/compatibility paths, preserving shared env."""

import argparse
import hashlib
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

CCCL_VERSION = "13.3.4.3.1"


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--cache",
        type=Path,
        default=Path("/home/vscode/.cache/inference/rust-migration"),
    )
    p.add_argument(
        "--training",
        type=Path,
        default=Path("/home/vscode/.cache/inference/envs/quoridor-training"),
    )
    a = p.parse_args()
    site = Path(
        subprocess.check_output(
            [
                str(a.training / "bin/python"),
                "-c",
                'import sysconfig; print(sysconfig.get_paths()["purelib"])',
            ],
            text=True,
        ).strip()
    )
    cache = a.cache
    cache.mkdir(parents=True, exist_ok=True)
    cccl = cache / "cccl"
    cccl.mkdir(exist_ok=True)
    data = json.load(
        urllib.request.urlopen(f"https://pypi.org/pypi/nvidia-cuda-cccl/{CCCL_VERSION}/json")
    )
    entry = next(x for x in data["urls"] if "x86_64" in x["filename"])
    wheel = cccl / entry["filename"]
    if not wheel.exists():
        wheel.write_bytes(urllib.request.urlopen(entry["url"]).read())
    actual = hashlib.sha256(wheel.read_bytes()).hexdigest()
    if actual != entry["digests"]["sha256"]:
        raise ValueError("CCCL wheel hash mismatch")
    with zipfile.ZipFile(wheel) as z:
        z.extractall(cccl)
    (cccl / "manifest.json").write_text(
        json.dumps(
            {
                "source": entry["url"],
                "sha256": actual,
                "version": CCCL_VERSION,
                "bytes": wheel.stat().st_size,
            },
            indent=2,
        )
        + "\n"
    )
    cuda = cache / "cuda"
    (cuda / "lib64").mkdir(parents=True, exist_ok=True)
    links = {
        cuda / "include": site / "nvidia/cu13/include",
        cuda / "lib64/libcudart.so": site / "nvidia/cu13/lib/libcudart.so.13",
        cuda / "lib64/libcuda.so": Path("/usr/lib/x86_64-linux-gnu/libcuda.so.1"),
    }
    for link, target in links.items():
        if not target.exists():
            raise FileNotFoundError(target)
        if link.is_symlink():
            if link.resolve() != target.resolve():
                raise ValueError(f"existing compatibility path differs: {link}")
        elif link.exists():
            raise ValueError(f"existing non-symlink compatibility path: {link}")
        else:
            link.symlink_to(target)
    manifest = {
        "training_root": str(a.training.resolve()),
        "torch_root": str(site / "torch"),
        "cuda_headers": str(site / "nvidia/cu13/include"),
        "extra_headers": [
            str(site / "triton/backends/nvidia/include"),
            str(cccl / "nvidia/cu13/include"),
        ],
        "compatibility_links": {str(k): str(v) for k, v in links.items()},
        "shared_environment_modified": False,
    }
    (cache / "native-environment.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
