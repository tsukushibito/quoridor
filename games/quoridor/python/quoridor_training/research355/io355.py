"""Bounded saved-file helpers and source-only synthetic guard.

The maintained lifecycle owns actual runtime admission, children and publication.
No recursive resource/review certificate admission or packet publisher remains.
"""

import hashlib
import os
from pathlib import Path
import resource
import stat
import re

import strength355 as analysis

LOCK = Path("/workspaces/quoridor/.artifacts/rust-migration/target/arena-software-writer.lock")
MAX_INPUT_TOTAL = 2147483648
MAX_INDEX_BYTES = 1048576
MAX_OUTPUT = 33554432


def identity(path):
    info = path.stat()
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            hasher.update(block)
    return {
        "SHA256": hasher.hexdigest(),
        "bytes": info.st_size,
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
    }


def read_bound(path, expected, maximum):
    analysis.require(
        not path.is_symlink() and expected["bytes"] <= maximum and path.stat().st_size <= maximum,
        "named finite input",
    )
    analysis.require(identity(path) == expected, "input SHA-size-mode drift")
    return analysis.strict_json(path.read_bytes(), maximum)


def read_jsonl(path, expected, row_cap, count_cap, progress):
    analysis.require(
        expected["bytes"] <= MAX_INPUT_TOTAL and path.stat().st_size <= MAX_INPUT_TOTAL,
        "stream total cap",
    )
    analysis.require(not path.is_symlink() and identity(path) == expected, "durable JSONL identity")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for count in range(count_cap + 1):
            raw = stream.readline(row_cap + 1)
            if not raw:
                break
            analysis.require(
                count < count_cap and len(raw) <= row_cap and raw.endswith(b"\n"),
                "partial/truncated/oversize row",
            )
            hasher.update(raw)
            progress["rows_read"] += 1
            yield analysis.strict_json(raw, row_cap)
    analysis.require(hasher.hexdigest() == expected["SHA256"], "JSONL after hash/capture mismatch")


def finite_physical():
    memory = (
        int(
            next(
                x.split()[1]
                for x in Path("/proc/meminfo").read_text().splitlines()
                if x.startswith("MemAvailable:")
            )
        )
        * 1024
    )
    analysis.require(memory >= 536870912 + 4294967296, "family+host reserve")
    pairs = [
        tuple(
            (Path(f"/sys/devices/system/cpu/cpu{c}/topology") / key).read_text().strip()
            for key in ("physical_package_id", "core_id")
        )
        for c in (3, 4)
    ]
    analysis.require(pairs[0] != pairs[1], "distinct physical worker/controller")
    os.sched_setaffinity(0, {3})
    resource.setrlimit(resource.RLIMIT_AS, (536870912, 536870912))


def named_quiet():
    """Fresh finite predicate; no periodic monitor or reservation."""
    pattern = re.compile(
        r"(^|/)(cargo|rustc|perf|quoridor-runner|chromium|chrome)(\s|$)|torchrun|quoridor_training.train|qualify_trained.py|current_gradients.py"
    )
    for path in Path("/proc").iterdir():
        if not path.name.isdigit() or int(path.name) in (os.getpid(), os.getppid()):
            continue
        try:
            argv = path.joinpath("cmdline").read_bytes().split(b"\0")
            if Path(os.fsdecode(argv[0])).name in ("bash", "sh", "timeout"):
                continue
            analysis.require(
                not pattern.search(" ".join(os.fsdecode(a) for a in argv if a)),
                "actual named peer exists",
            )
        except (OSError, IndexError):
            continue
