#!/usr/bin/env python3
"""Isolated, hash-bound TensorRT runtime installation; never modifies training env."""

import argparse
import hashlib
import json
import urllib.request
import zipfile
import sys
from pathlib import Path

VERSION = "11.3.0.99"
LIB_SHA = "cef957e0b48a525f2bcc8849742de06883cedcc6b96185b9cf0b17c9c75a858a"


def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while b := f.read(1024 * 1024):
            h.update(b)
    return h.hexdigest()


def download(url, path, sha):
    if not path.exists():
        with urllib.request.urlopen(url) as response, path.open("wb") as f:
            while b := response.read(1024 * 1024):
                f.write(b)
    if file_sha(path) != sha:
        raise ValueError(f"hash mismatch: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sm", type=int, default=86)
    parser.add_argument("--keep-archive", action="store_true")
    args = parser.parse_args()
    root = args.root
    root.mkdir(parents=True, exist_ok=True)
    downloads = root / "downloads"
    downloads.mkdir(exist_ok=True)
    library = downloads / "libs.whl"
    download(
        f"https://pypi.nvidia.com/tensorrt-cu13-libs/tensorrt_cu13_libs-{VERSION}-py3-none-manylinux_2_28_x86_64.whl",
        library,
        LIB_SHA,
    )
    data = json.load(
        urllib.request.urlopen(f"https://pypi.org/pypi/tensorrt-cu13-bindings/{VERSION}/json")
    )
    entry = next(
        x
        for x in data["urls"]
        if f"cp{sys.version_info.major}{sys.version_info.minor}" in x["filename"]
        and "x86_64" in x["filename"]
    )
    bindings = downloads / "bindings.whl"
    download(entry["url"], bindings, entry["digests"]["sha256"])
    site = root / "python"
    site.mkdir(exist_ok=True)
    for wheel in [library, bindings]:
        with zipfile.ZipFile(wheel) as z:
            for info in z.infolist():
                name = Path(info.filename).name
                if "builder_resource_" in name and not (
                    f"builder_resource_sm{args.sm}." in name or "builder_resource_ptx." in name
                ):
                    continue
                z.extract(info, site)
    headers = root / "include"
    headers.mkdir(exist_ok=True)
    listing = json.load(
        urllib.request.urlopen(
            "https://api.github.com/repos/NVIDIA/TensorRT/contents/include?ref=v11.3"
        )
    )
    checks = {}
    for entry in listing:
        if entry["name"].endswith(".h"):
            content = urllib.request.urlopen(entry["download_url"]).read()
            (headers / entry["name"]).write_bytes(content)
            checks[entry["name"]] = hashlib.sha256(content).hexdigest()
    lib = root / "lib"
    lib.mkdir(exist_ok=True)
    for so in (site / "tensorrt_libs").glob("*.so*"):
        link = lib / so.name
        if not link.exists():
            link.symlink_to(so)
    for name in ["nvinfer", "nvinfer_plugin", "nvonnxparser"]:
        link = lib / f"lib{name}.so"
        actual = next(lib.glob(f"lib{name}.so.*"))
        if not link.exists():
            link.symlink_to(actual)
    manifest = {
        "version": VERSION,
        "library_sha256": LIB_SHA,
        "bindings_sha256": file_sha(bindings),
        "headers_sha256": checks,
        "root": str(root.resolve()),
        "allocated_bytes": sum(
            p.stat().st_blocks * 512 for p in root.rglob("*") if p.is_file() and not p.is_symlink()
        ),
        "shared_environment_modified": False,
        "target_sm": args.sm,
        "archive_kept": args.keep_archive,
    }
    if not args.keep_archive:
        library.unlink()
        bindings.unlink()
    manifest["allocated_bytes"] = sum(
        p.stat().st_blocks * 512 for p in root.rglob("*") if p.is_file() and not p.is_symlink()
    )
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
