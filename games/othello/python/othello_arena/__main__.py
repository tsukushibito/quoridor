"""Run a Root-bound finite schedule under the existing resource/job guardian."""

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import time

from .engines import EgaroucidFixedTime, GTP, NativePlayer
from .matches import paired, summarize
from .protocol import EngineError, Native, Process


def checked_spec(spec):
    """Bind the executable selected by Root, without a second source inventory."""
    path = Path(spec["argv"][0])
    expected = spec["binary"]

    def matches(path, expected):
        if not path.is_absolute() or path.stat().st_size != expected["bytes"]:
            return False
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        return actual == expected["sha256"]

    if not matches(path, expected):
        raise ValueError("executable FileRef mismatch")
    if expected.get("mode") and f"{path.stat().st_mode & 0o777:04o}" != expected["mode"]:
        raise ValueError("executable mode mismatch")
    for asset in spec.get("assets", []):
        if not matches(Path(asset["path"]), asset):
            raise ValueError("engine asset FileRef mismatch")
        if (
            asset.get("mode")
            and f"{Path(asset['path']).stat().st_mode & 0o777:04o}" != asset["mode"]
        ):
            raise ValueError("engine asset mode mismatch")
    return spec


def smoke_families(config):
    families = config["families"]
    if len(families) != 4 or len({x["id"] for x in families}) != 4:
        raise ValueError("initial smoke requires four distinct opening families")
    if not 1 <= len(config["opponents"]) <= 2:
        raise ValueError("one or two fixed opponents required")
    if len({o["id"] for o in config["opponents"]}) != len(config["opponents"]):
        raise ValueError("unique opponent IDs required")
    if any(len(f["moves"]) > 60 or f.get("split") != "protocol-smoke-only" for f in families):
        raise ValueError("bounded separate smoke families required")
    if config["purpose"] != "protocol_cost" or config["superiorityClaim"] is not False:
        raise ValueError("this entry supports protocol/cost smoke only")
    if (
        config["timeMs"] != 1000
        or config["threads"] != 1
        or config["ttMiB"] != 32
        or config["book"]
        or config["ponder"]
    ):
        raise ValueError("smoke target must retain the declared initial conditions")
    return families


def run(config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Concrete resource admission/fair lease are owned by the enclosing job.
    # Root must record material external clock/TT differences before launch.
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    results = []
    failure = None
    cleanups = []
    lifecycle = []

    def cancelled():
        return (output / "CANCEL").exists()

    def start(stack, label, spec):
        record = {
            "label": label,
            "launchValidationMs": None,
            "launchWallMs": None,
            "readyWallMs": None,
            "shutdownWallMs": None,
        }
        lifecycle.append(record)
        before = time.monotonic()
        try:
            checked_spec(spec)
        finally:
            record["launchValidationMs"] = (time.monotonic() - before) * 1000
        record["started"] = time.monotonic()
        process = Process(
            spec["argv"], cwd=spec["cwd"], log=output / (label + ".log"), cancelled=cancelled
        )
        record["launchWallMs"] = (time.monotonic() - record["started"]) * 1000

        def close():
            before = time.monotonic()
            try:
                process.close()
            finally:
                record.update(
                    shutdownWallMs=(time.monotonic() - before) * 1000, cleanup=process.cleanup
                )

        stack.callback(close)
        cleanups.append(process)
        return process

    try:
        if not config.get("launchBinding"):
            raise ValueError("Root must bind native images/resources/fair timing before launch")
        families = smoke_families(config)
        for opponent in config["opponents"]:
            with ExitStack() as stack:
                rules = Native(start(stack, "rules-" + opponent["id"], config["rules"]))
                candidate = NativePlayer(
                    Native(start(stack, "candidate-" + opponent["id"], config["candidate"])),
                    simple=config["candidate"].get("simple", False),
                )
                process = start(stack, opponent["id"], opponent)
                engine = (
                    EgaroucidFixedTime(process)
                    if opponent["protocol"] == "fixed_jsonl"
                    else GTP(process, engine=opponent["engine"])
                )
                for result in paired(
                    rules,
                    candidate,
                    engine,
                    families,
                    time_ms=config["timeMs"],
                    overhead_ms=config["overheadMs"],
                ):
                    result["opponent"] = opponent["id"]
                    results.append(result)
                    with (output / "games.jsonl").open("a") as stream:
                        stream.write(json.dumps(result, separators=(",", ":")) + "\n")
                    if result["failure"]:
                        failure = result["failure"]
                        break
                if failure:
                    break
    except (EngineError, OSError, ValueError, KeyError, TypeError) as error:
        fact = {"kind": getattr(error, "kind", type(error).__name__), "message": str(error)}
        if failure:
            failure["secondary"] = fact
        else:
            failure = fact
    finally:
        if not failure and any(p.cleanup and p.cleanup["unexpectedExit"] for p in cleanups):
            failure = {"kind": "crash", "message": "engine exited nonzero before cleanup"}
        report = {
            "purpose": config["purpose"],
            "failure": failure,
            "cleanup": [p.cleanup for p in cleanups],
            "setupShutdown": lifecycle,
            "byOpponent": {
                o["id"]: summarize([r for r in results if r["opponent"] == o["id"]], 8)
                for o in config["opponents"]
            },
            "superiorityClaim": False,
        }
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    return 1 if failure else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.config.stat().st_size > 262144:
        parser.error("config exceeds bound")
    return run(json.loads(args.config.read_text()), args.output)


if __name__ == "__main__":
    sys.exit(main())
