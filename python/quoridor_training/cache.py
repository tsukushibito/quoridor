"""Hash-bound corpus with lazy metadata and bounded shard-aware tensor lookup."""

from array import array
from collections.abc import Sequence
import hashlib
import json
import mmap
import sqlite3
import tempfile
from pathlib import Path
import numpy as np

FILES = {"x.f32", "distance.f32", "labels.f32", "rows.jsonl"}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _validate_input(row, features, distance):
    if (
        row.get("ids_order") != "P1_then_P2"
        or row.get("distance_order") != "STM_then_opponent_f32"
        or row.get("tensor_view_order") != "STM_then_opponent"
        or type(row.get("side")) is not int
        or row["side"] not in (1, 2)
    ):
        raise ValueError("input view metadata")
    ids = row.get("ids")
    if (
        not isinstance(ids, list)
        or len(ids) != 2
        or any(
            not isinstance(view, list) or any(type(v) is not int or not 0 <= v < 312 for v in view)
            for view in ids
        )
    ):
        raise ValueError("invalid sparse feature IDs")
    ids = ids if row["side"] == 1 else ids[::-1]
    if not np.isin(features, (0, 1)).all():
        raise ValueError("sparse feature values must be binary")
    if any(view != np.flatnonzero(tensor).tolist() for view, tensor in zip(ids, features)):
        raise ValueError("STM sparse IDs/tensor differ")
    raw = np.asarray(row.get("distance"), dtype="<f4")
    if raw.shape != (2,) or not np.isfinite(distance).all() or raw.tobytes() != distance.tobytes():
        raise ValueError("STM distance f32 metadata/tensor differ")


class Rows(Sequence):
    def __init__(self, corpus):
        self.corpus = corpus

    def __len__(self):
        return self.corpus.row_count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        index = int(index)
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        shard, local = self.corpus.locate(index)
        return self._overlay(shard, index, shard.row(local))

    def _overlay(self, shard, index, row):
        if shard.namespace is not None:
            row = {
                **row,
                "source_id": row["id"],
                "source_group": row["group"],
                "id": shard.namespace + ":" + row["id"],
                "group": self.corpus.families[self.corpus.groups[index]],
                "split": ("train", "validation", "test")[self.corpus.splits[index]],
                "primary_eligible": bool(self.corpus.eligible[index]),
            }
        return row

    def __iter__(self):
        return self.iter_indices(range(len(self)))

    def iter_indices(self, indices):
        current, stream = None, None
        try:
            for index in indices:
                shard, local = self.corpus.locate(int(index))
                if shard is not current:
                    if stream is not None:
                        stream.close()
                    stream = (shard.path / "rows.jsonl").open("rb")
                    current = shard
                stream.seek(shard.offsets[local])
                yield self._overlay(shard, index, json.loads(stream.readline()))
        finally:
            if stream is not None:
                stream.close()


class _Shard:
    def __init__(self, path, manifest):
        self.path, self.namespace = path, None
        self.manifest, self.manifest_sha = manifest, sha(path / "cache.json")
        self.offsets = array("Q")
        n = manifest["rows"]
        self.x = np.memmap(path / "x.f32", dtype="<f4", mode="r", shape=(n, 2, 312))
        self.distance = np.memmap(path / "distance.f32", dtype="<f4", mode="r", shape=(n, 2))
        self.labels = np.memmap(path / "labels.f32", dtype="<f4", mode="r", shape=(n, 2))

    def release_pages(self):
        # Read-only mappings need no flush; discard their RSS after each bounded read.
        if hasattr(mmap, "MADV_DONTNEED"):
            for values in (self.x, self.distance, self.labels):
                values._mmap.madvise(mmap.MADV_DONTNEED)

    def row(self, index):
        with (self.path / "rows.jsonl").open("rb") as stream:
            stream.seek(self.offsets[index])
            return json.loads(stream.readline())


class Corpus:
    """Compact indices plus file mappings; dense features exist only in batches."""

    def __init__(self, binding, shards, groups, splits, eligible, labels, families):
        self.binding, self.shards, self.families = binding, shards, families
        self.groups = np.asarray(groups, dtype=np.uint32)
        self.splits = np.asarray(splits, dtype=np.uint8)
        self.eligible = np.asarray(eligible, dtype=np.bool_)
        self.labels = np.asarray(labels, dtype="<f4").reshape(-1, 2)
        self.row_count = len(self.groups)
        self.ends = np.cumsum([len(s.offsets) for s in shards])
        self.rows = Rows(self)

    def verify_binding(self):
        if self.binding.get("schema") == "quoridor-sharded-training-cache-v1":
            if sha(self.binding["path"]) != self.binding["dataset_sha"]:
                raise ValueError("sharded manifest changed during consumption")
            for reference in self.binding["references"]:
                if sha(reference["path"]) != reference["SHA"]:
                    raise ValueError("sharded reference changed during consumption")
        for shard in self.shards:
            if sha(shard.path / "cache.json") != shard.manifest_sha:
                raise ValueError("native manifest changed during consumption")
            for name, digest in shard.manifest["sha256"].items():
                if sha(shard.path / name) != digest:
                    raise ValueError("cache binding changed during consumption: " + name)

    def locate(self, index):
        number = int(np.searchsorted(self.ends, index, side="right"))
        start = int(self.ends[number - 1]) if number else 0
        return self.shards[number], index - start

    def batch(self, indices):
        indices = np.asarray(indices, dtype=np.int64)
        if indices.ndim != 1 or np.any(indices < 0) or np.any(indices >= self.row_count):
            raise ValueError("batch indices outside corpus")
        x = np.empty((len(indices), 2, 312), dtype="<f4")
        d = np.empty((len(indices), 2), dtype="<f4")
        y = np.empty((len(indices), 2), dtype="<f4")
        owners = np.searchsorted(self.ends, indices, side="right")
        for number in np.unique(owners):
            selected = np.flatnonzero(owners == number)
            start = self.ends[number - 1] if number else 0
            local = indices[selected] - start
            shard = self.shards[number]
            x[selected], d[selected], y[selected] = (
                shard.x[local],
                shard.distance[local],
                shard.labels[local],
            )
            shard.release_pages()
        return x, d, y

    def chunks(self, indices=None, size=4096):
        if type(size) is not int or size <= 0:
            raise ValueError("positive chunk size required")
        count = self.row_count if indices is None else len(indices)
        for first in range(0, count, size):
            selected = (
                np.arange(first, min(first + size, count), dtype=np.int64)
                if indices is None
                else indices[first : first + size]
            )
            yield selected, self.batch(selected)


def _native(path, allow_test):
    manifest = json.loads((path / "cache.json").read_text())
    if manifest.get("allow_test") is True and not allow_test:
        raise ValueError("test cache forbidden in learner")
    if (
        manifest.get("feature_count") != 312
        or type(manifest.get("rows")) is not int
        or manifest["rows"] <= 0
        or type(manifest.get("allow_test")) is not bool
        or not isinstance(manifest.get("dataset_sha"), str)
        or not manifest["dataset_sha"]
        or set(manifest)
        != {"rows", "feature_count", "allow_test", "dataset_sha", "files", "sha256"}
        or manifest["files"] != {name: name for name in FILES}
        or set(manifest["sha256"]) != FILES
    ):
        raise ValueError("native cache schema/required files and hashes")
    for name in FILES:
        digest = manifest["sha256"][name]
        if not isinstance(digest, str) or len(digest) != 64 or sha(path / name) != digest:
            raise ValueError("cache binding changed: " + name)
    for name, width in [("x.f32", 624), ("distance.f32", 2), ("labels.f32", 2)]:
        if (path / name).stat().st_size != manifest["rows"] * width * 4:
            raise ValueError("cache exact little-endian f32 byte length: " + name)
    return manifest, _Shard(path, manifest)


class _JsonStream:
    """Incremental JSON objects/arrays; shard row overlays never become dict lists."""

    def __init__(self, stream):
        self.stream, self.buffer, self.eof = stream, "", False
        self.decoder = json.JSONDecoder()

    def fill(self):
        part = self.stream.read(65536)
        self.eof = not part
        self.buffer += part

    def peek(self):
        self.buffer = self.buffer.lstrip()
        while not self.buffer and not self.eof:
            self.fill()
            self.buffer = self.buffer.lstrip()
        return self.buffer[:1]

    def take(self, expected):
        if self.peek() != expected:
            raise ValueError("invalid sharded JSON structure")
        self.buffer = self.buffer[1:]

    def value(self):
        self.peek()
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer)
                # A numeric token may cross the current read boundary.
                if end == len(self.buffer) and not self.eof:
                    self.fill()
                    continue
                self.buffer = self.buffer[end:]
                return value
            except json.JSONDecodeError:
                if self.eof:
                    raise ValueError("incomplete sharded JSON") from None
                self.fill()

    def object(self, handler):
        self.take("{")
        result = {}
        if self.peek() != "}":
            while True:
                name = self.value()
                if not isinstance(name, str) or name in result:
                    raise ValueError("duplicate/invalid JSON object key")
                self.take(":")
                result[name] = handler(name)
                if self.peek() != ",":
                    break
                self.take(",")
        self.take("}")
        return result

    def array(self, reader):
        self.take("[")
        if self.peek() != "]":
            while True:
                yield reader()
                if self.peek() != ",":
                    break
                self.take(",")
        self.take("]")


class _Overlay:
    def __init__(self, reader):
        self.identities, self.masks = bytearray(), array("B")
        for i, row in enumerate(reader.array(reader.value)):
            if (
                not isinstance(row, dict)
                or set(row) != {"index", "id", "primary_eligible"}
                or type(row["index"]) is not int
                or row["index"] != i
                or not isinstance(row["id"], str)
                or not row["id"]
                or type(row["primary_eligible"]) is not bool
            ):
                raise ValueError("shard row identity/order/mask")
            self.identities.extend(hashlib.sha256(row["id"].encode()).digest())
            self.masks.append(row["primary_eligible"])

    def __len__(self):
        return len(self.masks)

    def matches(self, index, identity):
        return (
            self.identities[index * 32 : (index + 1) * 32]
            == hashlib.sha256(identity.encode()).digest()
        )


def _sharded_manifest(path):
    with path.open() as stream:
        reader = _JsonStream(stream)

        def shard():
            return reader.object(
                lambda field: _Overlay(reader) if field == "rows" else reader.value()
            )

        manifest = reader.object(
            lambda field: list(reader.array(shard)) if field == "shards" else reader.value()
        )
        if reader.peek():
            raise ValueError("trailing sharded JSON")
        return manifest


def _load(path, allow_test, identities):
    """Validate inputs before returning the sole maintained Corpus interface."""
    path = Path(path)
    sharded = path.is_file()
    if sharded:
        manifest = _sharded_manifest(path)
        if (
            set(manifest) != {"schema", "feature_count", "rows", "shards", "references"}
            or manifest["schema"] != "quoridor-sharded-training-cache-v1"
            or manifest["feature_count"] != 312
            or type(manifest["rows"]) is not int
            or manifest["rows"] <= 0
            or not manifest["shards"]
        ):
            raise ValueError("sharded cache schema")
        for ref in manifest["references"]:
            if set(ref) != {"path", "SHA"} or sha(ref["path"]) != ref["SHA"]:
                raise ValueError("sharded reference binding")
        descriptors = manifest["shards"]
    else:
        descriptors, manifest = [{"path": str(path)}], None
    groups, splits, eligible, labels = array("I"), array("B"), array("B"), array("f")
    shards, families, family_ids = [], [], {}
    seen_children, seen_namespaces, seen_families = set(), set(), set()
    child_bindings = []
    for descriptor in descriptors:
        child = Path(descriptor["path"]).resolve()
        if child in seen_children or not child.is_dir():
            raise ValueError("shard duplicate/path")
        seen_children.add(child)
        namespace = None
        if sharded:
            if set(descriptor) != {"path", "manifest_SHA", "namespace", "family_map", "rows"}:
                raise ValueError("unknown/missing shard fields")
            namespace = descriptor["namespace"]
            if not isinstance(namespace, str) or not namespace or namespace in seen_namespaces:
                raise ValueError("shard namespace missing/duplicate")
            seen_namespaces.add(namespace)
            if sha(child / "cache.json") != descriptor["manifest_SHA"]:
                raise ValueError("child cache manifest changed")
        native, shard = _native(child, allow_test if not sharded else False)
        shard.namespace = namespace
        if sharded and len(descriptor["rows"]) != native["rows"]:
            raise ValueError("shard row denominator incomplete")
        if sharded:
            for assignment in descriptor["family_map"].values():
                if (
                    set(assignment) != {"canonical_family", "partition"}
                    or assignment["partition"] not in ("train", "validation")
                    or not isinstance(assignment["canonical_family"], str)
                    or not assignment["canonical_family"]
                    or assignment["canonical_family"] in seen_families
                ):
                    raise ValueError("invalid/duplicate canonical family assignment")
                seen_families.add(assignment["canonical_family"])
        native_families = set()
        with (child / "rows.jsonl").open("rb") as stream:
            while True:
                offset = stream.tell()
                line = stream.readline()
                if not line:
                    break
                i = len(shard.offsets)
                if i >= native["rows"]:
                    raise ValueError("cache row count")
                row = json.loads(line)
                if (
                    not isinstance(row.get("id"), str)
                    or not row["id"]
                    or not isinstance(row.get("group"), str)
                    or not row["group"]
                    or row.get("split") not in ("train", "validation", "test")
                    or type(row.get("primary_eligible")) is not bool
                ):
                    raise ValueError("cache row identity/partition/eligibility")
                identity = namespace + ":" + row["id"] if namespace is not None else row["id"]
                try:
                    identities.execute("INSERT INTO identities VALUES (?)", (identity,))
                except sqlite3.IntegrityError:
                    raise ValueError("cache row identity duplicated") from None
                if (not allow_test and row["split"] == "test") or (
                    sharded and row["split"] != "train"
                ):
                    raise ValueError("test labels or non-original training shard forbidden")
                _validate_input(row, shard.x[i], shard.distance[i])
                family, partition, mask = row["group"], row["split"], row["primary_eligible"]
                native_families.add(family)
                if sharded:
                    overlay = descriptor["rows"]
                    if not overlay.matches(i, row["id"]):
                        raise ValueError("shard row identity/order/mask")
                    assignment = descriptor["family_map"].get(family)
                    if assignment is None:
                        raise ValueError("shard family map incomplete")
                    family, partition = assignment["canonical_family"], assignment["partition"]
                    mask = mask and bool(overlay.masks[i])
                if family not in family_ids:
                    family_ids[family] = len(families)
                    families.append(family)
                groups.append(family_ids[family])
                splits.append(("train", "validation", "test").index(partition))
                eligible.append(mask)
                labels.extend(shard.labels[i])
                shard.offsets.append(offset)
                if (i + 1) % 4096 == 0:
                    shard.release_pages()
        shard.release_pages()
        if len(shard.offsets) != native["rows"]:
            raise ValueError("cache row count")
        if sharded and set(descriptor["family_map"]) != native_families:
            raise ValueError("shard family map incomplete")
        shards.append(shard)
        child_bindings.append(
            {"path": str(child), "manifest_SHA": sha(child / "cache.json"), "namespace": namespace}
        )
    if sharded:
        if len(groups) != manifest["rows"]:
            raise ValueError("sharded total rows")
        binding = {
            "schema": manifest["schema"],
            "dataset_sha": sha(path),
            "path": str(path.resolve()),
            "rows": len(groups),
            "shards": child_bindings,
            "references": manifest["references"],
        }
    else:
        binding = {**native, "cache_manifest_SHA": sha(child / "cache.json"), "path": str(child)}
    return Corpus(binding, shards, groups, splits, eligible, labels, families)


def load(path, allow_test=False):
    # Exact uniqueness uses a bounded-cache temporary index rather than a corpus-size ID set.
    with tempfile.TemporaryDirectory(prefix="quoridor-corpus-index-") as temporary:
        connection = sqlite3.connect(str(Path(temporary) / "identities.sqlite"))
        try:
            connection.execute("PRAGMA cache_size=-2048")
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("CREATE TABLE identities (identity TEXT PRIMARY KEY) WITHOUT ROWID")
            return _load(path, allow_test, connection)
        finally:
            connection.close()
