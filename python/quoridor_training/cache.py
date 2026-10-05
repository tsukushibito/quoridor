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


def _validate_inputs(rows, x, distance):
    for row, features, d in zip(rows, x, distance):
        if (
            row.get("ids_order") != "P1_then_P2"
            or row.get("distance_order") != "STM_then_opponent_f32"
            or row.get("tensor_view_order") != "STM_then_opponent"
            or row.get("side") not in (1, 2)
        ):
            raise ValueError("sharded input view metadata")
        ids = row["ids"] if row["side"] == 1 else row["ids"][::-1]
        if len(ids) != 2 or any(
            view != np.flatnonzero(tensor).tolist() for view, tensor in zip(ids, features)
        ):
            raise ValueError("sharded STM sparse IDs/tensor differ")
        if not np.isin(features, (0, 1)).all():
            raise ValueError("sharded sparse feature values")
        if np.asarray(row["distance"], dtype="<f4").tobytes() != d.astype("<f4").tobytes():
            raise ValueError("sharded STM distance f32 metadata/tensor differ")


def _load_sharded(path, manifest):
    if set(manifest) != {"schema", "feature_count", "rows", "shards", "references"}:
        raise ValueError("unknown or missing sharded manifest fields")
    if (
        manifest["schema"] != "quoridor-sharded-training-cache-v1"
        or manifest["feature_count"] != 312
    ):
        raise ValueError("sharded cache version/features")
    if not manifest["shards"] or type(manifest["rows"]) is not int or manifest["rows"] <= 0:
        raise ValueError("sharded cache rows")
    for ref in manifest["references"]:
        if set(ref) != {"path", "SHA"} or sha(ref["path"]) != ref["SHA"]:
            raise ValueError("sharded reference binding")
    result_rows, arrays, seen_namespaces, seen_children = [], [], set(), set()
    seen_families = set()
    for shard in manifest["shards"]:
        if set(shard) != {"path", "manifest_SHA", "namespace", "family_map", "rows"}:
            raise ValueError("unknown or missing shard fields")
        child = Path(shard["path"]).resolve()
        namespace = shard["namespace"]
        if not isinstance(namespace, str) or not namespace or namespace in seen_namespaces:
            raise ValueError("shard namespace missing/duplicate")
        if child in seen_children or not child.is_dir():
            raise ValueError("shard duplicate/path")
        seen_namespaces.add(namespace)
        seen_children.add(child)
        if sha(child / "cache.json") != shard["manifest_SHA"]:
            raise ValueError("child cache manifest changed")
        binding, rows, x, d, y = load(child, allow_test=False)
        if binding.get("schema") == "quoridor-sharded-training-cache-v1":
            raise ValueError("nested sharded manifest unsupported")
        if any(row["split"] != "train" for row in rows):
            raise ValueError("only original training shards can be repartitioned")
        _validate_inputs(rows, x, d)
        if len(shard["rows"]) != len(rows):
            raise ValueError("shard row denominator incomplete")
        if set(shard["family_map"]) != {r["group"] for r in rows}:
            raise ValueError("shard family map incomplete")
        for native_family, assignment in shard["family_map"].items():
            if set(assignment) != {"canonical_family", "partition"} or assignment[
                "partition"
            ] not in ("train", "validation"):
                raise ValueError("future/test or invalid family assignment")
            if (
                not isinstance(assignment["canonical_family"], str)
                or not assignment["canonical_family"]
            ):
                raise ValueError("canonical family UID")
            if assignment["canonical_family"] in seen_families:
                raise ValueError("canonical family duplicated across trajectories/shards")
            seen_families.add(assignment["canonical_family"])
        for i, (row, overlay) in enumerate(zip(rows, shard["rows"])):
            if set(overlay) != {"index", "id", "primary_eligible"}:
                raise ValueError("unknown row overlay fields")
            if overlay["index"] != i or overlay["id"] != row["id"]:
                raise ValueError("shard row index/identity/order mismatch")
            if type(overlay["primary_eligible"]) is not bool:
                raise ValueError("row mask must be explicit boolean")
            assignment = shard["family_map"][row["group"]]
            result_rows.append(
                {
                    **row,
                    "source_id": row["id"],
                    "source_group": row["group"],
                    "id": namespace + ":" + row["id"],
                    "split": assignment["partition"],
                    "group": assignment["canonical_family"],
                    "primary_eligible": row["primary_eligible"] and overlay["primary_eligible"],
                }
            )
        arrays.append((x, d, y))
    if len(result_rows) != manifest["rows"] or len({r["id"] for r in result_rows}) != len(
        result_rows
    ):
        raise ValueError("sharded total rows/namespace identity")
    binding = {**manifest, "dataset_sha": sha(path)}
    return binding, result_rows, *(np.concatenate([a[i] for a in arrays]) for i in range(3))


def load(path, allow_test=False):
    """Return (binding, rows, features, STM distances, target columns)."""
    path = Path(path)
    if path.is_file():
        manifest = json.loads(path.read_text())
        return _load_sharded(path, manifest)
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
