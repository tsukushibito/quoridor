"""Rust-generated, hash-bound tensor cache mapped in bulk."""

import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def load(path, allow_test=False):
    path = Path(path)
    manifest = json.loads((path / "cache.json").read_text())
    if manifest["feature_count"] != 312 or manifest["rows"] <= 0:
        raise ValueError("cache feature/row schema")
    if manifest["allow_test"] and not allow_test:
        raise ValueError("test cache forbidden in learner")
    for name, digest in manifest["sha256"].items():
        file = path / name
        if Path(name).name != name or sha(file) != digest:
            raise ValueError("cache binding changed: " + name)
    rows = [json.loads(line) for line in (path / "rows.jsonl").read_text().splitlines()]
    n = manifest["rows"]
    if len(rows) != n or len({r["id"] for r in rows}) != n:
        raise ValueError("cache row identity")
    if not allow_test and any(r["split"] == "test" for r in rows):
        raise ValueError("test labels in training cache")
    # Copy-on-write mappings are writable to Torch but never alter source bytes.
    x = np.memmap(path / "x.f32", dtype="<f4", mode="c", shape=(n, 2, 312))
    d = np.memmap(path / "distance.f32", dtype="<f4", mode="c", shape=(n, 2))
    y = np.memmap(path / "labels.f32", dtype="<f4", mode="c", shape=(n, 2))
    if not np.isfinite(x).all() or not np.isfinite(d).all():
        raise ValueError("nonfinite input cache")
    return manifest, rows, x, d, y
