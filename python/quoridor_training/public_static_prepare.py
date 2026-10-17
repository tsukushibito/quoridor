"""Full-original board-only public preparation with the maintained native codec.

No teacher/model is loaded here. The normal job guardian owns actual CPU/RAM,
whole holding, cancellation and exact child cleanup. Source shards are serial;
only their verified owning scratch copies are removed after saved receipts.
"""

import argparse
import json
import os
from pathlib import Path
import time

import numpy as np

from .cache import sha
from .common import bound_file_bytes
from .public_sigma import REVISION, NativeCompact, download, opened_observations
from .snapshot import write_json
from .static_public import (
    PAIR,
    ClassObservations,
    accumulate_original_shard,
    create_class_accumulator,
    write_class_table,
)


def file_ref(path):
    path = Path(path).resolve()
    before = path.stat()
    digest = sha(path)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ValueError("artifact changed during owning hash scan")
    return {
        "path": str(path),
        "sha256": digest,
        "bytes": after.st_size,
        "mode": f"{after.st_mode & 0o777:04o}",
    }


def file_identity(path):
    """The owning hash scan binds stable identity; later readers check custody."""
    from .compact_cache import IndexedPublicCorpus

    return IndexedPublicCorpus.identity(Path(path).stat())


def prepare(config):
    source = json.loads(bound_file_bytes(config["source_manifest"], 65536))
    if (
        source.get("revision") != REVISION
        or len(source.get("files", [])) != 43
        or len({row["sha"] for row in source["files"]}) != 43
        or any(
            type(row["rows"]) is not int or row["rows"] <= 0 or row["rows"] % 2
            for row in source["files"]
        )
        or type(config["split_seed"]) is not int
    ):
        raise ValueError("entire pinned original scope and explicit shared class split required")
    # Hash-before-load once. Normal admission also binds this genuine immutable
    # library and its source/software/lifetime; no fake future FileRef is usable.
    bound_file_bytes(config["native_library"], 64 * 1024**2)
    native = NativeCompact(config["native_library"]["path"])
    opened, opened_refs = opened_observations(config["opened_evaluation_receipts"], source)
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("complete full-source census owns publication; failed prefix retained\n")
    scratch = output / "source-scratch"
    scratch.mkdir()
    database = output / "input-classes.sqlite"
    connection = create_class_accumulator(database, max_bytes=config["max_sqlite_bytes"])
    attempts, receipts = [], []
    started = time.monotonic()
    primary = None
    phases = {"source_and_index": 0.0, "table_and_validation": 0.0}
    try:
        tick = time.monotonic()
        for ordinal, item in enumerate(source["files"]):
            reused = [
                r for r in config.get("verified_reuse", []) if r["source_path"] == item["path"]
            ]
            if len(reused) > 1:
                raise ValueError("at most one actual reused source blob per original shard")
            path = download(item, scratch, attempts, item["size"], reused[0] if reused else None)
            before = path.stat()
            receipt = accumulate_original_shard(connection, path, item, native, opened[ordinal])
            after = path.stat()
            if (
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("original source changed during native qualification")
            connection.commit()
            receipts.append(
                {
                    **receipt,
                    "source_ordinal": ordinal,
                    "source_path": item["path"],
                    "source_git_blob": item["sha"],
                    "source_sha256": attempts[-1]["sha256"],
                }
            )
            write_json(output / "progress.json", {"attempts": attempts, "receipts": receipts})
            # External reuse paths are read-only. Only this successful own
            # serial download is reconstructible scratch, never historical RAW.
            if not reused:
                if path.parent != scratch:
                    raise ValueError("source scratch ownership changed")
                path.unlink()
        phases["source_and_index"] = time.monotonic() - tick
        expected = sum(row["rows"] // 2 for row in source["files"])
        if len(receipts) != 43 or sum(r["decoded_original_rows"] for r in receipts) != expected:
            raise ValueError("full original source census incomplete")
        tick = time.monotonic()
        table = output / "class-pairs.bin"
        with table.open("xb") as stream:
            counts = write_class_table(
                connection,
                stream,
                split_seed=config["split_seed"],
            )
            stream.flush()
            os.fsync(stream.fileno())
        native_valid = sum(r["native_codes"][0] for r in receipts)
        if counts["qualified_original_observations"] != native_valid:
            raise ValueError(
                "source-qualified original multiplicity differs from final class census"
            )
        pairs = np.memmap(table, dtype=PAIR, mode="r")
        try:
            observations = ClassObservations(pairs)
            if observations.counts != {k: counts[k] for k in ("train", "validation")}:
                raise ValueError("virtual observation count differs from owning class census")
            del observations
        finally:
            pairs._mmap.close()
        phases["table_and_validation"] = time.monotonic() - tick
        result = {
            "schema": "quoridor-public-static-input-classes-v1",
            "status": "COMPLETE",
            "revision": REVISION,
            "original_only": True,
            "source_manifest": config["source_manifest"],
            "native_library": config["native_library"],
            "class_pairs": file_ref(table),
            "class_pairs_identity": file_identity(table),
            "pair_record_bytes": PAIR.itemsize,
            "original_observations": expected,
            "counts": counts,
            "source_receipts": receipts,
            "source_mapping": "each original valid row -> exact oriented key and trueLR pair; original source order defines within-orientation occurrence ordinal; retain original multiplicity",
            "virtual_order": "within each partition sorted pair, canonical originals then reflected originals",
            "protected_membership": {
                "rule": "old row-split sealed plus known-opened IDs; propagate protection to the complete trueLR pair before teacher access",
                "opened_receipts": opened_refs,
                "protected_payload_use": "opaque exclusion membership only; never teacher/trainer/stopping",
            },
            "split": {
                "seed": config["split_seed"],
                "algorithm": "SHA256(ASCII full-public-teachers-v1|split| + LE-u64 seed + canonical key28); h=BE-u64 first8; 10*h<9*2**64 ->T, elseV",
                "independent_games": "UNKNOWN",
            },
            "value_semantics": "board-only static single evaluation; full history/repetition UNAVAILABLE",
            "old_label_payload_read": False,
            "old_zero_or_missing_termination_filter": False,
            "naive_lr_half_used": False,
            "phases_seconds": phases,
            "whole_seconds": time.monotonic() - started,
        }
        # DB was only a temporary exact-class index. After fully synced output
        # and validated complete census it is reconstructible, not unique data.
        write_json(output / "cache.json", result)
        connection.close()
        connection = None
        database.unlink()
        scratch.rmdir()
        marker.unlink()
        return {"manifest": file_ref(output / "cache.json"), "counts": counts}
    except BaseException as error:
        primary = error
        try:
            write_json(
                output / "failure.json",
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "attempts": attempts,
                    "receipts": receipts,
                    "phases_seconds": phases,
                    "wall_seconds": time.monotonic() - started,
                },
            )
        except BaseException as publication:
            primary = BaseExceptionGroup(
                "original preparation and failure publication", [error, publication]
            )
            raise primary
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except BaseException as error:
                if primary is not None:
                    raise BaseExceptionGroup(
                        "original preparation and SQLite close", [primary, error]
                    )
                raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    # The normal guardian wraps this finite worker; never pin a legacy CPU2/3
    # controller or establish a second scheduler/resource framework here.
    from .cycle_process import cancellation_signals

    with cancellation_signals():
        result = prepare(json.loads(Path(args.config).read_bytes()))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
