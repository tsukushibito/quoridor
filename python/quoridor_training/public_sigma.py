"""Pinned full-original Sigma stream: native qualification and compact geometry.

Labels belong to this producer. Test observations are saved separately and are
never returned by the training cache loader. No game/history identity is inferred.
"""

import argparse
import ctypes
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import zipfile

import numpy as np

from .cache import sha
from .snapshot import write_json as write

from .public_features import (
    RECORD,
    SCHEMA,
    REVISION_NAME,
    geometry_from_native,
    model_keys,
    phase_proxy,
)

REVISION = "751186344fc52ad0c29bc65922e62c6fa915f006"
SEED = 31920261006

EXCLUSION = np.dtype([("shard", "u1"), ("row", "<u4"), ("z", "<f4"), ("reason", "u1")])
PARTITIONS = ("train", "validation", "test-sealed", "evaluation-opened")


def mix64(values):
    """Version-bound unsigned bijection; distinct streams use distinct salt."""
    x = np.asarray(values, dtype=np.uint64).copy()
    with np.errstate(over="ignore"):
        x += np.uint64(0x9E3779B97F4A7C15)
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return x ^ (x >> np.uint64(31))


def selection(blob_sha, half):
    salt = int.from_bytes(hashlib.sha256((blob_sha + str(SEED)).encode()).digest()[:8], "little")
    ids = np.arange(half, dtype=np.uint64) ^ np.uint64(salt)
    candidate = np.ones(half, dtype=bool)
    u = (mix64(ids ^ np.uint64(1)) >> np.uint64(11)).astype(np.float64) / 2**53
    splits = np.where(u < 10 / 11, 0, np.where(u < 10.5 / 11, 1, 2)).astype(np.uint8)
    return candidate, splits, ids


class NativeCompact:
    def __init__(self, library):
        self.library = ctypes.CDLL(str(library))
        self.function = self.library.quoridor_sigma_compact
        self.function.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.function.restype = ctypes.c_int

    def convert(self, planes):
        planes = np.ascontiguousarray(planes, dtype="<f4")
        n = len(planes)
        bits = np.zeros((n, 78), dtype=np.uint8)
        distances = np.zeros((n, 2), dtype="<f4")
        codes = np.zeros(n, dtype=np.uint8)
        if self.function(
            planes.ctypes.data,
            n,
            bits.ctypes.data,
            distances.ctypes.data,
            codes.ctypes.data,
        ):
            raise ValueError("native compact ABI framing")
        return bits, distances, codes


def header(stream):
    version = np.lib.format.read_magic(stream)
    if version == (1, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
    elif version == (2, 0):
        shape, fortran, dtype = np.lib.format.read_array_header_2_0(stream)
    else:
        raise ValueError("unsupported NPY version")
    if fortran or dtype != np.dtype("<f4"):
        raise ValueError("NPY dtype/order")
    return shape


def read_exact(stream, count):
    parts = bytearray()
    while len(parts) < count:
        block = stream.read(count - len(parts))
        if not block:
            raise ValueError("short NPY payload")
        parts.extend(block)
    return bytes(parts)


def download(item, scratch, attempts, remaining_bytes, reuse=None):
    if reuse is not None:
        path = Path(reuse["local_path"])
        started = time.monotonic()
        size = path.stat().st_size
        digest = hashlib.sha1(f"blob {size}\0".encode())
        signature = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                signature.update(block)
        if (
            size != item["size"]
            or digest.hexdigest() != item["sha"]
            or signature.hexdigest() != reuse["sha256"]
        ):
            raise ValueError("read-only reused pinned blob changed")
        attempts.append(
            {
                "path": item["path"],
                "bytes": 0,
                "local_bytes": size,
                "local_path": str(path),
                "status": "REUSED_PASS",
                "sha256": signature.hexdigest(),
                "git_blob": digest.hexdigest(),
                "seconds": time.monotonic() - started,
            }
        )
        return path
    path = scratch / Path(item["path"]).name
    started = time.monotonic()
    git_sha = hashlib.sha1(f"blob {item['size']}\0".encode())
    digest = hashlib.sha256()
    total = 0
    receipt = {"path": item["path"], "started_monotonic": started, "bytes": 0}
    attempts.append(receipt)
    try:
        request = urllib.request.Request(
            f"https://raw.githubusercontent.com/bartolomeo3000/SigmaQuoridor/{REVISION}/{item['path']}",
            headers={"User-Agent": "quoridor-pinned-research"},
        )
        with (
            urllib.request.urlopen(request, timeout=30) as response,
            path.open("xb") as output,
        ):
            while block := response.read(1024 * 1024):
                total += len(block)
                receipt["bytes"] = total
                if total > item["size"] or (
                    remaining_bytes is not None and total > remaining_bytes
                ):
                    raise ValueError("network byte budget")
                git_sha.update(block)
                digest.update(block)
                output.write(block)
        if total != item["size"] or git_sha.hexdigest() != item["sha"]:
            raise ValueError("pinned Git blob bytes differ")
        receipt.update(status="PASS", sha256=digest.hexdigest(), git_blob=git_sha.hexdigest())
        return path
    except BaseException as error:
        receipt.update(status="FAILED", error=str(error))
        raise
    finally:
        receipt["seconds"] = time.monotonic() - started


def opened_observations(descriptors, source):
    """Documented opened evaluation IDs only; old labels/features are not read.

    This one-purpose provenance import reads the completed 319 record format at
    its fixed ID offsets. It is not a legacy training-cache compatibility route.
    Unknown historical exposures remain UNKNOWN, not a claim of unexposed data.
    """
    by_blob = {item["sha"]: i for i, item in enumerate(source["files"])}
    if not descriptors:
        raise ValueError("documented opened evaluation receipt is required")
    opened = [[] for _ in source["files"]]
    refs = []
    for descriptor in descriptors:
        receipt_path = Path(descriptor["evaluation_receipt"])
        receipt = json.loads(receipt_path.read_text())
        result = receipt.get("result", receipt)
        binding = result.get("evaluation_cache_binding", {})
        if (
            sha(receipt_path) != descriptor["receipt_sha256"]
            or binding.get("test_opened") is not True
        ):
            raise ValueError("opened observation receipt/explicit opening")
        cache = Path(binding["path"])
        manifest = json.loads((cache / "cache.json").read_text())
        if (
            sha(cache / "cache.json") != binding["dataset_sha"]
            or manifest.get("revision") != REVISION
            or manifest.get("original_only") is not True
            or manifest.get("schema") != "quoridor-public-compact-v1"
        ):
            raise ValueError("opened original observation corpus attribution")
        part = next(x for x in binding["partitions"] if x["name"] == "test-sealed")
        file = cache / part["file"]
        if sha(file) != part["sha256"] or file.stat().st_size != part["rows"] * 174:
            raise ValueError("opened ID binary binding")
        ids = np.memmap(
            file,
            dtype=np.dtype(
                {
                    "names": ["shard", "row", "alias"],
                    "formats": ["<u2", "<u4", "<u4"],
                    "offsets": [90, 92, 96],
                    "itemsize": 174,
                }
            ),
            mode="r",
            shape=(part["rows"],),
        )
        headers = manifest["source_shards"]
        if np.any(ids["shard"] >= len(headers)) or np.any(ids["row"] != ids["alias"]):
            raise ValueError("opened IDs must be true original observations")
        for old_shard in np.unique(ids["shard"]):
            header = headers[int(old_shard)]
            if header["blob"] not in by_blob:
                raise ValueError("opened observation blob outside pinned source")
            if header["rows"] != source["files"][by_blob[header["blob"]]]["rows"]:
                raise ValueError("opened source row denominator differs from pinned source")
            rows = ids["row"][ids["shard"] == old_shard].copy()
            if np.any(rows >= header["rows"] // 2):
                raise ValueError("opened original row outside source front half")
            opened[by_blob[header["blob"]]].append(rows)
        refs.append(
            {
                "receipt": str(receipt_path),
                "sha256": descriptor["receipt_sha256"],
                "rows": len(ids),
            }
        )
    return [np.unique(np.concatenate(v)) if v else np.zeros(0, dtype="<u4") for v in opened], refs


def original_plane_chunks(path, item, *, with_values):
    """Only the original front half; board-only use never opens old labels."""
    from contextlib import ExitStack

    n = item["rows"]
    if type(n) is not int or n <= 0 or n % 2 or type(with_values) is not bool:
        raise ValueError("positive source halves and explicit old-label policy required")
    with zipfile.ZipFile(path) as archive, ExitStack() as stack:
        states = stack.enter_context(archive.open("states.npy"))
        if header(states) != (n, 8, 9, 9):
            raise ValueError("source states shape")
        values = stack.enter_context(archive.open("values.npy")) if with_values else None
        if values is not None and header(values) != (n,):
            raise ValueError("source values shape")
        for first in range(0, n // 2, 4096):
            count = min(4096, n // 2 - first)
            planes = np.frombuffer(read_exact(states, count * 648 * 4), dtype="<f4").reshape(
                count, 8, 9, 9
            )
            z = (
                np.frombuffer(read_exact(values, count * 4), dtype="<f4")
                if values is not None
                else None
            )
            yield np.arange(first, first + count, dtype="<u4"), planes, z


def process_shard(path, item, shard, native, reject_stream, partition_streams, opened):
    n = item["rows"]
    if n % 2:
        raise ValueError("original/naiveLR source halves")
    half = n // 2
    _, splits, _ = selection(item["sha"], half)
    reasons = np.zeros(7, dtype=np.int64)
    accepted = np.zeros(4, dtype=np.int64)
    label_counts = dict(positive=0, negative=0, zero_unknown_termination=0, invalid_label=0)
    decoded = 0
    for indices, planes, z in original_plane_chunks(path, item, with_values=True):
        count = len(indices)
        assignment = splits[indices].copy()
        assignment[np.isin(indices, opened)] = 3
        bits, distances, codes = native.convert(planes)
        if codes.shape != (count,) or np.any(codes > 6):
            raise ValueError("native status ABI")
        reasons += np.bincount(codes, minlength=7)
        label_counts["positive"] += int(np.count_nonzero(z == 1))
        label_counts["negative"] += int(np.count_nonzero(z == -1))
        label_counts["zero_unknown_termination"] += int(np.count_nonzero(z == 0))
        label_counts["invalid_label"] += int(np.count_nonzero(~np.isin(z, (-1, 0, 1))))
        valid = (codes == 0) & np.isin(z, (-1, 1))
        reject = np.zeros(np.count_nonzero(~valid), dtype=EXCLUSION)
        reject["shard"], reject["row"], reject["z"] = shard, indices[~valid], z[~valid]
        reject["reason"] = np.where(
            codes[~valid] != 0, codes[~valid], np.where(z[~valid] == 0, 7, 8)
        )
        reject_stream.write(reject.tobytes())
        if valid.any():
            rows = np.zeros(np.count_nonzero(valid), dtype=RECORD)
            rows["geometry"] = geometry_from_native(bits[valid])
            rows["distance"] = distances[valid]
            if not np.isfinite(rows["distance"]).all():
                raise ValueError("native distance finite")
            rows["z"], rows["shard"], rows["row"] = z[valid], shard, indices[valid]
            for j, plane in enumerate(planes[valid]):
                rows["input_sha"][j] = np.frombuffer(
                    hashlib.sha256(plane.tobytes()).digest(), dtype="u1"
                )
            for partition, stream in enumerate(partition_streams):
                selected = rows[assignment[valid] == partition]
                stream.write(selected.tobytes())
                accepted[partition] += len(selected)
        decoded += count
    return {
        "stored_rows": n,
        "decoded_original_rows": decoded,
        "original_observations": half,
        "candidate_observations": half,
        "native_codes": reasons.tolist(),
        "labels": label_counts,
        "accepted_per_partition": accepted.tolist(),
        "excluded_observations": half - int(accepted.sum()),
        "naiveLR_half_used": False,
        "qualification_denominator": "all original observations, not distinct states/games",
    }


def publish_progress(output, streams, rejected, progress):
    """Commit OS-visible payload before publishing completed-shard counts.

    This flushes Python buffers; it is not a power-failure/fsync guarantee.
    Partial shards remain partial and are never promoted to complete corpora.
    """
    for stream in streams:
        stream.flush()
    rejected.flush()
    sizes = [os.fstat(stream.fileno()).st_size for stream in streams]
    if sizes != [rows * RECORD.itemsize for rows in progress["counts"]]:
        raise ValueError("completed shard progress differs from flushed partition payload")
    write(output / "progress.json", {**progress, "flushed_partition_bytes": sizes})


def prepare(config):
    from contextlib import ExitStack

    started = time.monotonic()
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    scratch = output / "scratch"
    scratch.mkdir()
    source = json.loads(Path(config["source_manifest"]).read_text())
    if (
        source["revision"] != REVISION
        or len(source["files"]) != 43
        or len({x["sha"] for x in source["files"]}) != 43
        or config.get("original_only") is not True
        or config.get("dataset_revision") != REVISION_NAME
        or config.get("seconds") is not None
    ):
        raise ValueError("pinned all43 original-full-v1/no runtime cap contract")
    opened, references = opened_observations(config["opened_evaluation_receipts"], source)
    plan = {
        "schema": "public-sigma-original-full-plan-v1",
        "dataset_revision": REVISION_NAME,
        "revision": REVISION,
        "original_only": True,
        "seed": SEED,
        "candidate_probability": 1.0,
        "bottom_priority_truncation": False,
        "alias_split": "same319 mix64(original-index XOR sha256(blob+seed) salt XOR1)",
        "split_nominal_fractions": [10 / 11, 0.5 / 11, 0.5 / 11],
        "independent_IID_inclusion_probability": "NOT_PROVEN; deterministic fixed-seed partition",
        "known_opened_rule": "exact sourceblob+originalindex forced into evaluation-opened; no sameinput deletion",
        "known_opened_receipts": references,
        "known_opened_observations": sum(len(v) for v in opened),
        "unknown_historical_exposure": "UNKNOWN, not unexposed or unseen games",
        "native_library_SHA": sha(config["library"]),
        "source_manifest_SHA": sha(config["source_manifest"]),
        "record_bytes": RECORD.itemsize,
        "input_binding": "raw source planes SHA per row; lossless qualified native geometry+distance -> both QF1 views",
        "online_augmentation": "correct native LR in training only; original validation fixed; sourceID/split/z unchanged",
    }
    write(output / "sampling-plan.json", plan)
    attempts, receipts = [], []
    native = NativeCompact(config["library"])
    counts = np.zeros(4, dtype=np.int64)
    try:
        with ExitStack() as stack:
            streams = [
                stack.enter_context((output / (name + ".bin")).open("xb")) for name in PARTITIONS
            ]
            rejected = stack.enter_context(
                gzip.open(output / "exclusions.bin.gz", "wb", compresslevel=1)
            )
            for shard, item in enumerate(source["files"]):
                tick = time.monotonic()
                reuse = next(
                    (
                        r
                        for r in config.get("verified_reuse", [])
                        if r["source_path"] == item["path"]
                    ),
                    None,
                )
                path = download(item, scratch, attempts, None, reuse)
                receipt = process_shard(path, item, shard, native, rejected, streams, opened[shard])
                counts += receipt["accepted_per_partition"]
                receipt.update(
                    shard=shard,
                    file=item["path"],
                    blob=item["sha"],
                    source_SHA256=attempts[-1]["sha256"],
                    seconds=time.monotonic() - tick,
                )
                receipts.append(receipt)
                publish_progress(
                    output,
                    streams,
                    rejected,
                    {
                        "receipts": receipts,
                        "attempts": attempts,
                        "counts": counts.tolist(),
                    },
                )
                if path.parent == scratch:
                    path.unlink()  # Only qualified owned scratch; preserve all source/hash/attempt facts.
                print(
                    json.dumps(
                        {
                            "shard": shard,
                            "counts": counts.tolist(),
                            "seconds": receipt["seconds"],
                        }
                    ),
                    flush=True,
                )
        partitions = []
        for name, count in zip(PARTITIONS, counts):
            file = output / (name + ".bin")
            if file.stat().st_size != count * RECORD.itemsize:
                raise ValueError("streamed compact length mismatch")
            if not count:
                raise ValueError("full original partition unexpectedly empty: " + name)
            rows = np.memmap(file, dtype=RECORD, mode="r", shape=(int(count),))
            model_distinct = len(np.unique(model_keys(rows)))
            source_distinct = len(np.unique(rows["input_sha"].copy().view("V32")))
            partitions.append(
                {
                    "name": name,
                    "file": file.name,
                    "sha256": sha(file),
                    "rows": int(count),
                    "bytes": file.stat().st_size,
                    "original_input_distinct": source_distinct,
                    "model_input_distinct": model_distinct,
                    "model_identity": "injective native canonical geometry+f32 distance, equivalent exact QF1 two-view bytes",
                    "per_shard": np.bincount(rows["shard"], minlength=43).tolist(),
                    "phase_proxy": np.bincount(phase_proxy(rows["geometry"]), minlength=3).tolist(),
                }
            )
            del rows
        write(
            output / "cache.json",
            {
                "schema": SCHEMA,
                "revision": REVISION,
                "dataset_revision": REVISION_NAME,
                "original_only": True,
                "record_bytes": RECORD.itemsize,
                "source_shards": [
                    {"file": x["path"], "blob": x["sha"], "rows": x["rows"]}
                    for x in source["files"]
                ],
                "sampling_plan_sha": sha(output / "sampling-plan.json"),
                "partitions": partitions,
                "qualified_counts": counts.tolist(),
                "input_native": "per original observation checked geometry/full8plane maps/QF1",
                "test_sealed": True,
                "known_opened_evaluation": references,
                "unseen_games": "UNKNOWN",
                "exposure_history": "UNKNOWN except exact documented opened IDs quarantined",
            },
        )
    finally:
        write(
            output / "cost.json",
            {
                "all_attempt_seconds": time.monotonic() - started,
                "time_limit": None,
                "attempts": attempts,
                "network_bytes": sum(x["bytes"] for x in attempts),
                "receipts": receipts,
                "processed_original_rows": sum(x["decoded_original_rows"] for x in receipts),
                "old_allocations_and_UNKNOWN": "historical, not used as new remaining",
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    admission = json.loads(Path(config["storage_admission"]).read_text())
    if (
        admission.get("admission") != "within"
        or admission.get("errors")
        or sha(config["storage_admission"]) != config["storage_admission_sha"]
    ):
        raise ValueError("completed bound storage admission required before compute")
    for path, digest in config["expected_files_sha256"].items():
        if sha(path) != digest:
            raise ValueError("fixed producer/native/source changed before compute")
    os.sched_setaffinity(0, {2, 3})
    if args.worker:
        from .cycle_process import cancellation_signals

        with cancellation_signals():
            prepare(config)
    else:
        import sys
        from .cycle_process import CycleResources, cancellation_signals, execute

        root = Path(config["output"]).parent
        resources = CycleResources(
            {
                "max_memory_bytes": 4 * 1024**3 - 64 * 1024**2,
                "host_ram_reserve": 4 * 1024**3,
                "max_output_bytes": config["max_output_bytes"],
            },
            root,
            None,
        )
        with cancellation_signals():
            execute(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "quoridor_training.public_sigma",
                    "--config",
                    args.config,
                    "--worker",
                ],
                root / "prepare.log",
                None,
                resources=resources,
            )


if __name__ == "__main__":
    main()
