"""Pinned public Sigma producer: streamed planes, native qualification, row reservoirs.

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

REVISION = "751186344fc52ad0c29bc65922e62c6fa915f006"
SEED = 31920261006
CANDIDATE_PROBABILITY = 0.30
COUNTS = (1_000_000, 50_000, 50_000)
RECORD = np.dtype(
    [
        ("bits", "u1", (78,)),
        ("distance", "<f4", (2,)),
        ("z", "<f4"),
        ("shard", "<u2"),
        ("row", "<u4"),
        ("alias", "<u4"),
        ("input_sha", "u1", (32,)),
        ("model_sha", "u1", (32,)),
        ("priority", "<u8"),
        ("split", "u1"),
        ("phase", "u1"),
    ]
)


def write(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


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
    candidate = mix64(ids) < int(CANDIDATE_PROBABILITY * 2**64)
    u = (mix64(ids ^ np.uint64(1)) >> np.uint64(11)).astype(np.float64) / 2**53
    splits = np.where(u < 10 / 11, 0, np.where(u < 10.5 / 11, 1, 2)).astype(np.uint8)
    return candidate, splits, ids


def keep_lowest(existing, incoming, count):
    combined = np.concatenate((existing, incoming))
    if len(combined) > count:
        # Stable secondary key is the unique source shard/row, never the label.
        order = np.lexsort((combined["row"], combined["shard"], combined["priority"]))[:count]
        combined = combined[order].copy()
    return combined


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
            planes.ctypes.data, n, bits.ctypes.data, distances.ctypes.data, codes.ctypes.data
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
        with urllib.request.urlopen(request, timeout=30) as response, path.open("xb") as output:
            while block := response.read(1024 * 1024):
                total += len(block)
                receipt["bytes"] = total
                if total > item["size"] or total > remaining_bytes:
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


def process_shard(path, item, shard, native, reject_stream, deadline):
    n = item["rows"]
    if n % 2:
        raise ValueError("augmentation halves")
    half = n // 2
    candidate, split, tokens = selection(item["sha"], half)
    chunks = []
    reasons = np.zeros(7, dtype=np.int64)
    decoded = 0
    with zipfile.ZipFile(path) as archive:
        with archive.open("states.npy") as stream:
            if header(stream) != (n, 8, 9, 9):
                raise ValueError("states shape")
            stop = half
            for first in range(0, stop, 4096):
                if time.monotonic() >= deadline:
                    raise TimeoutError("data all-attempt deadline")
                count = min(4096, stop - first)
                planes = np.frombuffer(read_exact(stream, count * 648 * 4), dtype="<f4").reshape(
                    count, 8, 9, 9
                )
                indices = np.arange(first, first + count, dtype=np.uint32)
                mask = candidate[indices % half]
                indices = indices[mask]
                selected = planes[mask]
                if len(indices):
                    bits, distance, codes = native.convert(selected)
                    reasons += np.bincount(codes, minlength=7)
                    rows = np.zeros(len(indices), dtype=RECORD)
                    rows["bits"], rows["distance"] = bits, distance
                    rows["shard"], rows["row"], rows["alias"] = shard, indices, indices % half
                    rows["split"] = split[indices % half]
                    rows["priority"] = mix64(
                        tokens[indices % half]
                        ^ np.uint64(2)
                        ^ (indices >= half).astype(np.uint64) * np.uint64(4)
                    )
                    stocks = np.rint(selected[:, 4:6, 0, 0] * 10).sum(axis=1)
                    rows["phase"] = np.where(stocks >= 16, 0, np.where(stocks >= 6, 1, 2))
                    for j, plane in enumerate(selected):
                        rows["input_sha"][j] = np.frombuffer(
                            hashlib.sha256(plane.tobytes()).digest(), dtype=np.uint8
                        )
                        rows["model_sha"][j] = np.frombuffer(
                            hashlib.sha256(bits[j].tobytes() + distance[j].tobytes()).digest(),
                            dtype=np.uint8,
                        )
                    chunks.append((rows, codes))
                decoded += count
        # Original native inputs are checked before recorded label qualification.
        with archive.open("values.npy") as stream:
            if header(stream) != (n,):
                raise ValueError("values shape")
            label_rows = half
            labels = np.frombuffer(read_exact(stream, label_rows * 4), dtype="<f4")
        accepted = []
        label_counts = {
            "positive": 0,
            "negative": 0,
            "zero_unknown_termination": 0,
            "invalid_label": 0,
        }
        for rows, codes in chunks:
            z = labels[rows["row"]]
            rows["z"] = z
            decisive = np.isin(z, (-1, 1))
            label_counts["positive"] += int(np.count_nonzero(z == 1))
            label_counts["negative"] += int(np.count_nonzero(z == -1))
            label_counts["zero_unknown_termination"] += int(np.count_nonzero(z == 0))
            label_counts["invalid_label"] += int(np.count_nonzero(~np.isin(z, (-1, 0, 1))))
            excluded = (codes != 0) | ~decisive
            # Binary exclusions retain original value and per-observation reason, no full row JSON.
            records = np.zeros(
                np.count_nonzero(excluded),
                dtype=[("shard", "<u2"), ("row", "<u4"), ("z", "<f4"), ("reason", "u1")],
            )
            records["shard"], records["row"], records["z"] = (
                shard,
                rows["row"][excluded],
                z[excluded],
            )
            records["reason"] = np.where(
                codes[excluded] != 0, codes[excluded], np.where(z[excluded] == 0, 7, 8)
            )
            reject_stream.write(records.tobytes())
            accepted.append(rows[~excluded])
    return np.concatenate(accepted), {
        "stored_rows": n,
        "decoded_rows": decoded,
        "original_observations": half,
        "candidate_observations": int(candidate.sum()),
        "candidate_stored_rows": int(candidate.sum()),
        "native_codes": reasons.tolist(),
        "labels": label_counts,
        "full_LR_input_and_label_bytes": "NOT_APPLICABLE_ORIGINAL_ONLY",
        "original_only": True,
    }


def prepare(config):
    started = time.monotonic()
    deadline = started + config["seconds"]
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    scratch = output / "scratch"
    scratch.mkdir()
    source = json.loads(Path(config["source_manifest"]).read_text())
    if source["revision"] != REVISION or len(source["files"]) != 43:
        raise ValueError("source revision/file count")
    if (
        config.get("original_only") is not True
        or config.get("dataset_revision") != "original-only-v2"
    ):
        raise ValueError("active producer requires original-only-v2 contract")
    plan = {
        "schema": "public-sigma-row-sampling-v2",
        "dataset_revision": config["dataset_revision"],
        "network_series": config["network_series"],
        "original_only": True,
        "revision": REVISION,
        "seed": SEED,
        "candidate_probability": CANDIDATE_PROBABILITY,
        "split_probabilities": [10 / 11, 0.5 / 11, 0.5 / 11],
        "counts": COUNTS,
        "priority": "mix64(original-index XOR blob+seed salt XOR2); deterministic fixed rank, ties shard/row; stream independence unproved",
        "sampling": "bottom priority eligible rows per split over all43; tie shard/row",
        "aliases": "pinned same-blob original-index; original-only observations, no LR targets",
        "input_overlap": "allowed independent observations; game/history UNKNOWN",
        "eligibility_denominator": "candidate rows only; unsampled eligibility UNKNOWN",
        "final_inclusion_probability": "NOT_PROVEN; thresholds are nominal design fractions, N/qualified_candidates is realized retention, not independent inclusion probability",
        "sealed_test": True,
        "native_sha": sha(config["library"]),
        "source_manifest_sha": sha(config["source_manifest"]),
        "record_bytes": RECORD.itemsize,
    }
    write(output / "sampling-plan.json", plan)
    native = NativeCompact(config["library"])
    reservoirs = [np.zeros(0, dtype=RECORD) for _ in COUNTS]
    qualified_counts = [0, 0, 0]
    if len({x["sha"] for x in source["files"]}) != 43:
        raise ValueError("source duplicate blob aliases need explicit admission")
    attempts, receipts = [], []
    try:
        with gzip.open(output / "exclusions.bin.gz", "wb", compresslevel=1) as rejected:
            for shard, item in enumerate(source["files"]):
                begin = time.monotonic()
                if begin >= deadline:
                    raise TimeoutError("data deadline before download")
                reuse = next(
                    (
                        r
                        for r in config.get("verified_reuse", [])
                        if r["source_path"] == item["path"]
                    ),
                    None,
                )
                path = download(
                    item,
                    scratch,
                    attempts,
                    config["network_max_bytes"]
                    - config.get("prior_series_bytes", 0)
                    - sum(a["bytes"] for a in attempts),
                    reuse=reuse,
                )
                incoming, receipt = process_shard(path, item, shard, native, rejected, deadline)
                for split, count in enumerate(COUNTS):
                    selected = incoming[incoming["split"] == split]
                    qualified_counts[split] += len(selected)
                    reservoirs[split] = keep_lowest(reservoirs[split], selected, count)
                receipt.update(
                    shard=shard,
                    path=item["path"],
                    blob=item["sha"],
                    sha256=attempts[-1]["sha256"],
                    seconds=time.monotonic() - begin,
                    retained=[len(x) for x in reservoirs],
                    qualified_counts=list(qualified_counts),
                )
                receipts.append(receipt)
                write(
                    output / "progress.json",
                    {
                        "receipts": receipts,
                        "attempts": attempts,
                        "seconds": time.monotonic() - started,
                    },
                )
                if path.parent == scratch:
                    path.unlink()  # Owned scratch only; hashes/provenance retained.

                print(
                    json.dumps(
                        {
                            "shard": shard,
                            "retained": receipt["retained"],
                            "seconds": receipt["seconds"],
                        }
                    ),
                    flush=True,
                )
        if any(len(r) != count for r, count in zip(reservoirs, COUNTS)):
            raise ValueError("INSUFFICIENT_QUALIFIED_ROWS: " + str([len(r) for r in reservoirs]))
        manifests = []
        for split, rows in enumerate(reservoirs):
            name = ("train", "validation", "test-sealed")[split]
            rows = rows[np.lexsort((rows["row"], rows["shard"]))]
            filename = name + ".bin"
            rows.tofile(output / filename)
            source_distinct = len(np.unique(rows["input_sha"].copy().view("V32")))
            model_distinct = len(np.unique(rows["model_sha"].copy().view("V32")))
            manifests.append(
                {
                    "name": name,
                    "file": filename,
                    "sha256": sha(output / filename),
                    "rows": len(rows),
                    "bytes": rows.nbytes,
                    "original_input_distinct": source_distinct,
                    "model_input_distinct": model_distinct,
                    "per_shard": np.bincount(rows["shard"], minlength=43).tolist(),
                    "phase_proxy": np.bincount(rows["phase"], minlength=3).tolist(),
                }
            )
        write(
            output / "cache.json",
            {
                "schema": "quoridor-public-compact-v1",
                "revision": REVISION,
                "dataset_revision": config["dataset_revision"],
                "original_only": True,
                "source_shards": [
                    {"file": x["path"], "blob": x["sha"], "rows": x["rows"]}
                    for x in source["files"]
                ],
                "sampling_plan_sha": sha(output / "sampling-plan.json"),
                "partitions": manifests,
                "qualified_counts": qualified_counts,
                "input_native": "per observation checked geometry/full8plane maps and QF1",
                "test_sealed": True,
                "unseen_games": "UNKNOWN",
                "exposure_history": "UNKNOWN; prior public observations not relabeled unseen",
            },
        )
    finally:
        write(
            output / "cost.json",
            {
                "network_series": config["network_series"],
                "network_series_cap_bytes": config["network_max_bytes"],
                "prior_series_bytes": config.get("prior_series_bytes", 0),
                "all_attempt_seconds": time.monotonic() - started,
                "attempts": attempts,
                "network_bytes": sum(a["bytes"] for a in attempts),
                "receipts": receipts,
                "processed_rows": sum(r["decoded_rows"] for r in receipts),
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    admission_path = config.get("storage_admission")
    if not admission_path:
        raise ValueError("completed fresh storage admission required before child/compute")
    admission = json.loads(Path(admission_path).read_text())
    if (
        admission.get("admission") != "within"
        or admission.get("errors")
        or sha(admission_path) != config.get("storage_admission_sha")
    ):
        raise ValueError("storage admission failed or changed before child/compute")
    os.sched_setaffinity(0, {2, 3})
    if args.worker:
        prepare(config)
    else:
        import sys
        from .cycle_process import CycleResources, cancellation_signals, execute

        root = Path(config["output"]).parent
        root.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + config["seconds"]
        resources = CycleResources(
            {
                "max_memory_bytes": 4 * 1024**3,
                "max_output_bytes": config.get("max_output_bytes", 320 * 1024**2),
                "host_ram_reserve": 4 * 1024**3,
            },
            root,
            deadline,
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
                deadline,
                resources=resources,
            )


if __name__ == "__main__":
    main()
