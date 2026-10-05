"""QF1 dataset I/O and bound train/validation joins, with no frame dependency.

Stage manifests select explicit train groups and carry a precomputed exposure
mask. This module does not choose a split, maximum dataset size, labels, or
masking policy; frozen experiment adapters own those choices.
"""

import gzip
import hashlib
import json
import math
from pathlib import Path

from qf1 import validate_input


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(obj):
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def read_rows(path):
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    if str(path).removesuffix(".gz").endswith(".jsonl"):
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    obj = json.loads(raw)
    return obj["samples"] if isinstance(obj, dict) else obj


def bound_path(manifest, key):
    path = Path(manifest[key]).resolve()
    if sha(path) != manifest[key + "_sha256"]:
        raise ValueError("manifest binding changed: " + key)
    return path


def load_stage(path):
    manifest = json.loads(Path(path).read_text())
    if manifest.get("kind") != "QF1-training-stage":
        raise ValueError("training manifest kind")
    metadata = read_rows(bound_path(manifest, "metadata"))
    mask = json.loads(bound_path(manifest, "mask").read_text())
    labels = read_rows(bound_path(manifest, "training_labels"))
    # The manifest's sealed test-label reference is intentionally never opened.
    if any(row.get("split") not in ("train", "validation") for row in labels):
        raise ValueError("test labels prohibited in training artifact")
    by_id = {row["id"]: row for row in labels}
    if len(by_id) != len(labels):
        raise ValueError("duplicate training label ID")
    selected = []
    for row in metadata:
        if row["split"] == "test" or (
            row["split"] == "train" and row["group"] not in manifest["train_groups"]
        ):
            continue
        label = by_id.get(row["id"])
        if label is None:
            raise ValueError("missing train/validation label")
        if label["split"] != row["split"]:
            raise ValueError("label partition mismatch")
        row_mask = mask["rows"][row["id"]]
        if row_mask["split"] != row["split"] or row_mask["group"] != row["group"]:
            raise ValueError("mask identity mismatch")
        selected.append(
            {
                **row,
                "rootmean": label.get("rootmean"),
                "z": label.get("z"),
                "primary_eligible": row_mask["primary_eligible"],
            }
        )
    return selected, manifest


def feature_key(row):
    # Preserve the established loader overlap rule (absolute-player views and
    # JSON distances). STM/float32 identity used by exposure masks is separately
    # versioned in qf1.py; silently substituting it would change old datasets.
    encoded = json.dumps(
        [sorted(row["ids"][0]), sorted(row["ids"][1]), row["distance"], row["side"]],
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def load_data(path, overlap_policy="error"):
    data = Path(path).read_bytes()
    stage = None
    if str(path).endswith(".stage.json"):
        rows, stage = load_stage(path)
    else:
        rows = read_rows(path)
    if not isinstance(rows, list) or not rows:
        raise ValueError("no samples")
    ids = set()
    exposures = {
        key: {} for key in ("group", "exposure_group", "state_key", "history_key", "features")
    }
    counts = {"train": 0, "validation": 0}
    for row in rows:
        if not isinstance(row.get("id"), str) or row["id"] in ids:
            raise ValueError("missing/duplicate row id")
        ids.add(row["id"])
        split = row.get("split")
        if split not in counts:
            raise ValueError("only train/validation allowed; keep final test data outside training")
        counts[split] += 1
        if not isinstance(row.get("group"), str) or not row["group"]:
            raise ValueError("each row needs its game/family group")
        validate_input(row)
        for target in ("rootmean", "z"):
            value = row.get(target)
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value) or not -1 <= value <= 1
            ):
                raise ValueError(f"invalid target: {target}")
        for key in exposures:
            value = feature_key(row) if key == "features" else row.get(key)
            if value is not None:
                exposures[key].setdefault(value, set()).add(split)
    if not all(counts.values()):
        raise ValueError("train and validation must both be nonempty")
    overlap = {
        key: sum(len(splits) > 1 for splits in seen.values()) for key, seen in exposures.items()
    }
    if overlap["group"] or overlap["exposure_group"]:
        raise ValueError("game/exposure group crosses train-validation split")
    if overlap_policy == "error" and any(overlap.values()):
        raise ValueError(f"state/history/features cross split: {overlap}")
    split_hashes = {}
    for split in counts:
        split_rows = sorted(
            [row for row in rows if row["split"] == split], key=lambda row: row["id"]
        )
        encoded = json.dumps(split_rows, sort_keys=True, separators=(",", ":"))
        split_hashes[split + "_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    return rows, {
        "path": str(Path(path).resolve()),
        "sha256": hashlib.sha256(data).hexdigest(),
        **split_hashes,
        "rows": len(rows),
        "counts": counts,
        "groups": {
            split: len({row["group"] for row in rows if row["split"] == split}) for split in counts
        },
        "cross_split_keys": overlap,
        "stage_manifest": stage,
        "independent_test": False,
    }
