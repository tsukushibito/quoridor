"""Lossless public QF1 bitsets behind the existing bounded corpus interface."""

from collections.abc import Sequence
import hashlib
import json
from pathlib import Path

import numpy as np

from .cache import sha
from .public_sigma import RECORD


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
            "source_alias": int(record["alias"]),
            "phase_proxy": int(record["phase"]),
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
            self.manifest["schema"] != "quoridor-public-compact-v1"
            or not self.manifest["test_sealed"]
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
                if self.manifest.get("dataset_revision") == "original-only-v2":
                    headers = self.manifest.get("source_shards", [])
                    if (
                        self.manifest.get("original_only") is not True
                        or len(headers) != 43
                        or np.any(rows["shard"] >= 43)
                        or np.any(rows["row"] != rows["alias"])
                    ):
                        raise ValueError("original-only observation provenance")
                    halves = np.asarray([x["rows"] // 2 for x in headers], dtype=np.uint32)
                    if np.any(rows["row"] >= halves[rows["shard"]]):
                        raise ValueError("original-only index must be in first source half")
                expected_split = {"train": 0, "validation": 1, "test-sealed": 2}[part["name"]]
                if not np.all(rows["split"] == expected_split):
                    raise ValueError("compact split binding")
                for row in rows:
                    expected = hashlib.sha256(
                        row["bits"].tobytes() + row["distance"].tobytes()
                    ).digest()
                    if expected != row["model_sha"].tobytes():
                        raise ValueError("compact model input signature")
            self.maps.append(mapped)
            sizes.append(len(mapped))
        self.offsets = np.concatenate(([0], np.cumsum(sizes)))
        self.row_count = int(self.offsets[-1])
        self.splits = np.concatenate([m["split"] for m in self.maps])
        self.eligible = np.ones(self.row_count, dtype=bool)
        self.labels = np.empty((self.row_count, 2), dtype=np.float32)
        self.labels[:, 0] = np.nan
        self.labels[:, 1] = np.concatenate([m["z"] for m in self.maps])
        keys = np.concatenate([m["model_sha"] for m in self.maps]).view("V32").reshape(-1)
        hashes, self.groups = np.unique(keys, return_inverse=True)
        self.families = ["public-model-input:" + bytes(h).hex() for h in hashes]
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

    def batch(self, indices):
        indices = np.asarray(indices, dtype=np.int64)
        if indices.ndim != 1 or np.any(indices < 0) or np.any(indices >= self.row_count):
            raise ValueError("compact batch indices")
        bits = np.empty((len(indices), 78), dtype=np.uint8)
        distance = np.empty((len(indices), 2), dtype=np.float32)
        for part, mapped in enumerate(self.maps):
            mask = (indices >= self.offsets[part]) & (indices < self.offsets[part + 1])
            selected = mapped[indices[mask] - self.offsets[part]]
            bits[mask], distance[mask] = selected["bits"], selected["distance"]
        features = (
            np.unpackbits(bits, axis=1, bitorder="little").reshape(-1, 2, 312).astype(np.float32)
        )
        return features, distance, self.labels[indices]

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
