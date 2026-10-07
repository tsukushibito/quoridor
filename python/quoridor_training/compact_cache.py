"""Lossless native geometry behind the maintained bounded QF1 corpus interface."""

from collections.abc import Sequence
import json
from pathlib import Path

import numpy as np

from .cache import sha
from .public_features import (
    RECORD,
    SCHEMA,
    REVISION_NAME,
    features,
    model_keys,
    phase_proxy,
    validate_geometry,
)


class CompactRows(Sequence):
    def __init__(self, corpus):
        self.corpus = corpus

    def __len__(self):
        return self.corpus.row_count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        index = int(index)
        record = self.corpus.record(index)
        return {
            "id": f"{self.corpus.revision}:{int(record['shard'])}:{int(record['row'])}",
            "group": self.corpus.families[self.corpus.groups[index]],
            "split": ("train", "validation", "test")[self.corpus.splits[index]],
            "primary_eligible": True,
            "teacher_type": "external_outcome",
            "rootmean": None,
            "z": float(record["z"]),
            "source_shard": int(record["shard"]),
            "source_row": int(record["row"]),
            "source_alias": int(record["row"]),
            "phase_proxy": 0
            if int(record["geometry"]["stocks"].sum()) >= 16
            else (1 if int(record["geometry"]["stocks"].sum()) >= 6 else 2),
            "game": "UNAVAILABLE",
            "side": 1,
        }

    def iter_indices(self, indices):
        for index in indices:
            yield self[index]


class CompactCorpus:
    compact = True

    def __init__(self, path, allow_test=False):
        self.path = Path(path)
        manifest_path = self.path / "cache.json"
        self.manifest = json.loads(manifest_path.read_text())
        self.manifest_sha = sha(manifest_path)
        if (
            self.manifest["schema"] != SCHEMA
            or not self.manifest["test_sealed"]
            or self.manifest.get("original_only") is not True
            or self.manifest.get("dataset_revision") != REVISION_NAME
            or self.manifest.get("record_bytes") != RECORD.itemsize
            or len(self.manifest.get("source_shards", [])) != 43
        ):
            raise ValueError("compact cache schema/sealing")
        self.revision = self.manifest["revision"]
        wanted = {"test-sealed"} if allow_test else {"train", "validation"}
        self.descriptors = [x for x in self.manifest["partitions"] if x["name"] in wanted]
        if {x["name"] for x in self.descriptors} != wanted:
            raise ValueError("compact partitions incomplete")
        self.maps, sizes = [], []
        for part in self.descriptors:
            file = self.path / part["file"]
            if (
                part["file"] != part["name"] + ".bin"
                or file.stat().st_size != part["rows"] * RECORD.itemsize
                or sha(file) != part["sha256"]
            ):
                raise ValueError("compact row/hash binding")
            mapped = np.memmap(file, dtype=RECORD, mode="r", shape=(part["rows"],))
            for first in range(0, len(mapped), 4096):
                rows = mapped[first : first + 4096]
                if not np.isfinite(rows["distance"]).all() or not np.isin(rows["z"], (-1, 1)).all():
                    raise ValueError("compact input/target qualification")
                if self.manifest.get("dataset_revision") == REVISION_NAME:
                    headers = self.manifest.get("source_shards", [])
                    if (
                        self.manifest.get("original_only") is not True
                        or len(headers) != 43
                        or np.any(rows["shard"] >= 43)
                    ):
                        raise ValueError("original-only observation provenance")
                    halves = np.asarray([x["rows"] // 2 for x in headers], dtype=np.uint32)
                    if np.any(rows["row"] >= halves[rows["shard"]]):
                        raise ValueError("original-only index must be in first source half")
                validate_geometry(rows["geometry"])
            self.maps.append(mapped)
            sizes.append(len(mapped))
        self.offsets = np.concatenate(([0], np.cumsum(sizes)))
        self.row_count = int(self.offsets[-1])
        self.splits = np.concatenate(
            [
                np.full(
                    len(m),
                    {"train": 0, "validation": 1, "test-sealed": 2}[part["name"]],
                    dtype=np.uint8,
                )
                for m, part in zip(self.maps, self.descriptors)
            ]
        )
        self.eligible = np.ones(self.row_count, dtype=bool)
        self.labels = np.empty((self.row_count, 2), dtype=np.float32)
        self.labels[:, 0] = np.nan
        self.labels[:, 1] = np.concatenate([m["z"] for m in self.maps])
        keys = np.concatenate([model_keys(m) for m in self.maps])
        hashes, self.groups = np.unique(keys, return_inverse=True)
        self.groups = self.groups.astype(np.int32)
        self.families = range(len(hashes))  # dataset-bound input-group IDs, not source game IDs
        del keys, hashes
        self.rows = CompactRows(self)
        self.binding = {
            "schema": self.manifest["schema"],
            "dataset_sha": self.manifest_sha,
            "cache_manifest_SHA": self.manifest_sha,
            "rows": self.row_count,
            "path": str(self.path),
            "partitions": self.descriptors,
            "input_overlap_policy": "report; distinct source observations retained",
            "test_opened": allow_test,
        }

    def record(self, index):
        if not 0 <= index < self.row_count:
            raise IndexError(index)
        part = int(np.searchsorted(self.offsets, index, side="right") - 1)
        return self.maps[part][index - self.offsets[part]]

    def records(self, indices, *, out=None):
        indices = np.asarray(indices, dtype=np.int64)
        if indices.ndim != 1 or np.any(indices < 0) or np.any(indices >= self.row_count):
            raise ValueError("compact batch indices")
        records = np.empty(len(indices), dtype=RECORD) if out is None else out
        if records.dtype != RECORD or records.shape != indices.shape or not records.flags.writeable:
            raise ValueError("record output dtype/shape/writable")
        if any(np.shares_memory(records, m) for m in self.maps):
            raise ValueError("record output must not alias corpus")
        for part, mapped in enumerate(self.maps):
            mask = (indices >= self.offsets[part]) & (indices < self.offsets[part + 1])
            records[mask] = mapped[indices[mask] - self.offsets[part]]
        return records

    def batch(self, indices, reflection_mask=None):
        indices = np.asarray(indices, dtype=np.int64)
        records = self.records(indices)
        return (
            features(records["geometry"], reflection_mask),
            records["distance"].copy(),
            self.labels[indices],
        )

    def batch_into(
        self, indices, reflection_mask, features_out, distances_out, *, records_out, workspace
    ):
        records = self.records(indices, out=records_out)
        if (
            distances_out.dtype != np.float32
            or distances_out.shape != (len(indices), 2)
            or not distances_out.flags.c_contiguous
            or not distances_out.flags.writeable
        ):
            raise ValueError("distance output dtype/shape/contiguity/writable")
        features(records["geometry"], reflection_mask, out=features_out, workspace=workspace)
        distances_out[:] = records["distance"]

    def metadata(self, indices):
        records = self.records(indices)
        return (
            records["distance"],
            self.labels[indices],
            records["shard"],
            phase_proxy(records["geometry"]),
        )

    def chunks(self, indices, size):
        for first in range(0, len(indices), size):
            sub = indices[first : first + size]
            yield sub, self.batch(sub)

    def verify_binding(self):
        if sha(self.path / "cache.json") != self.manifest_sha:
            raise ValueError("compact manifest changed")
        for part in self.descriptors:
            if sha(self.path / part["file"]) != part["sha256"]:
                raise ValueError("compact corpus changed")
