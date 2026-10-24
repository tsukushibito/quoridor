"""Run a Root-bound finite schedule under the existing resource/job guardian."""

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
import time

from .engines import EgaroucidFixedTime, GTP, NativePlayer, FullSearchPlayer, io_deadline
from .matches import paired, summarize, comparison_summary, family_bootstrap_table
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


def development_families(config):
    """Frozen single-target development trajectories, not an unseen strength book."""
    from .generation import _read

    if (
        config["purpose"] != "native_external_development"
        or config.get("superiorityClaim") is not False
        or config.get("comparisonScope") != "development-contest"
        or config.get("independentStrengthQualification") is not None
        or config["timeMs"] != 1000
        or config["overheadMs"] != 100
        or config["threads"] != 1
        or config["ttMiB"] != 32
        or config["book"]
        or config["ponder"]
        or config["candidate"]["protocol"] != "fullsearch_jsonl"
        or len(config["opponents"]) != 2
        or {o["protocol"] for o in config["opponents"]} != {"gtp", "fixed_jsonl"}
        or len({o["id"] for o in config["opponents"]}) != 2
        or any(o["protocol"] == "gtp" and o.get("engine") != "edax" for o in config["opponents"])
    ):
        raise ValueError("explicit normal external development condition required")
    statistics = config["statisticsContract"]
    if type(statistics["seed"]) is not int or statistics["seed"] < 0:
        raise ValueError("explicit nonnegative shared bootstrap seed required")
    spec = config["candidate"]
    argv = spec["argv"]
    flags = [
        "--midgame",
        "--ordering",
        "--midgame-id",
        "--ordering-id",
        "--interpretation",
        "--hash-level",
        "--coefficients",
    ]
    if len(argv) != 15 or argv[1::2] != flags or len(spec["assets"]) != 2:
        raise ValueError("bound ordinary CLI weights/profile argv required")
    assets = {asset["path"]: asset for asset in spec["assets"]}
    identity = spec["identity"]
    if (
        argv[2] not in assets
        or argv[4] not in assets
        or argv[6] != identity["midgameId"]
        or argv[8] != identity["orderingId"]
        or identity["midgameId"] != "sha256:" + assets[argv[2]]["sha256"]
        or identity["orderingId"] != "sha256:" + assets[argv[4]]["sha256"]
        or argv[10] != identity["interpretation"]
        or argv[12] != "20"
        or json.loads(argv[14]) != identity["coefficients"]
    ):
        raise ValueError("callerVerified IDs must bind the checked argv assets/profile")
    try:
        package = _read(config["openings"], 1024 * 1024)
    except RuntimeError as error:
        raise ValueError(str(error)) from error
    if (
        package.get("complete") is not True
        or package.get("H") != 0
        or package.get("trajectoryProfile") != "development-contest-openings"
        or package.get("comparisonScope") != "development-contest"
        or package.get("endpointMetadataChecked") is not True
        or package.get("freshHistoryComplete") is not True
        or package.get("historicalPassInclusiveHistoryCoverage") != "UNKNOWN"
    ):
        raise ValueError("frozen development opening package qualification differs")
    families = package["families"]
    if (
        len(families) != 16
        or len({f["id"] for f in families}) != 16
        or [f["id"] for f in families] != config["familyIds"]
        or len({f["seed"] for f in families}) != 16
        or any(
            f["split"] != "development" or f["status"] != "COMPLETE" or len(f["roots"]) != 1
            for f in families
        )
    ):
        raise ValueError("16 complete original development families required")
    result = []
    for family in families:
        root = family["roots"][0]
        if (
            root["placement"] != 16
            or root["id"] != family["id"] + "/p16"
            or not 16 <= len(root["moves"]) <= 128
            or sum(move is not None for move in root["moves"]) != 16
            or root["status"]["terminal"]
            or root["status"]["mustPass"]
        ):
            raise ValueError("single placement16 root after mandatory pass required")
        result.append({"id": family["id"], "moves": root["moves"], "state": root["state"]})
    return result


def run(config, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Concrete resource admission/fair lease are owned by the enclosing job.
    # Root must record material external clock/TT differences before launch.
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    results = []
    failure = None
    cleanups = []
    cohort_processes = {}
    lifecycle = []
    sessions = []
    families = []
    external = config.get("purpose") == "native_external_development"

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
        if external:
            cohort_processes[opponent["id"]].append(process)
        return process

    try:
        if not config.get("launchBinding"):
            raise ValueError("Root must bind native images/resources/fair timing before launch")
        families = development_families(config) if external else smoke_families(config)
        for opponent in config["opponents"]:
            if external:
                cohort_processes[opponent["id"]] = []
            with ExitStack() as stack:
                rules = Native(start(stack, "rules-" + opponent["id"], config["rules"]))
                candidate_process = start(stack, "candidate-" + opponent["id"], config["candidate"])
                if external:
                    candidate = FullSearchPlayer(
                        candidate_process,
                        identity=config["candidate"]["identity"],
                        options=config["candidate"]["options"],
                    )
                    ready = time.monotonic()
                    info = candidate.initialize(deadline=io_deadline())
                    sessions.append(
                        {
                            "opponent": opponent["id"],
                            "candidateInfo": info,
                            "candidateReadyMs": (time.monotonic() - ready) * 1000,
                        }
                    )
                else:
                    candidate = NativePlayer(
                        Native(candidate_process), simple=config["candidate"].get("simple", False)
                    )
                process = start(stack, opponent["id"], opponent)
                engine = (
                    EgaroucidFixedTime(process, evidence=opponent if external else None)
                    if opponent["protocol"] == "fixed_jsonl"
                    else GTP(process, engine=opponent["engine"])
                )
                if external and opponent["protocol"] == "fixed_jsonl":
                    ready = time.monotonic()
                    info = process.json_request({"op": "info"}, deadline=io_deadline())
                    required = {
                        "label",
                        "engineCommit",
                        "searchThreads",
                        "workerPool",
                        "hashLevel",
                        "hashSeed",
                        "activeTTBytes",
                        "book",
                        "ponder",
                    }
                    expected = opponent["identity"]
                    if (
                        not required <= expected.keys()
                        or expected["label"] != "Console7.8.1-engine + fixed-time adapter"
                        or expected["engineCommit"] != "570d5e0a478c9d720d75de06a5d31995f412704a"
                        or expected["hashLevel"] != 20
                        or expected["hashSeed"] != 20261022
                        or expected["searchThreads"] != 1
                        or expected["workerPool"] != 0
                        or expected["book"] is not False
                        or expected["ponder"] is not False
                        or not 0 < expected["activeTTBytes"] <= 32 * 1024**2
                        or any(info.get(k) != v for k, v in expected.items())
                    ):
                        raise EngineError("identity", "fixed Console startup identity differs")
                    sessions[-1].update(
                        externalInfo=info, externalReadyMs=(time.monotonic() - ready) * 1000
                    )
                for result in paired(
                    rules,
                    candidate,
                    engine,
                    families,
                    time_ms=config["timeMs"],
                    overhead_ms=config["overheadMs"],
                    retain_setup=external,
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
        cohort_qualified = {
            key: len(members) == 3
            and all(
                p.cleanup
                and p.cleanup.get("directReaped") is True
                and not p.cleanup.get("unexpectedExit")
                and not p.cleanup.get("errors")
                for p in members
            )
            for key, members in cohort_processes.items()
        }
        report = {
            "purpose": config["purpose"],
            "failure": failure,
            "cleanup": [p.cleanup for p in cleanups],
            "setupShutdown": lifecycle,
            "byOpponent": {
                o["id"]: summarize(
                    [r for r in results if r["opponent"] == o["id"]], 32 if external else 8
                )
                for o in config["opponents"]
            },
            "superiorityClaim": False,
        }
        if external:

            def summarize_external(opponent, shared=None):
                return comparison_summary(
                    [r for r in results if r["opponent"] == opponent["id"]],
                    families,
                    {"candidate": config["candidate"], "opponent": opponent},
                    run_qualified=cohort_qualified.get(opponent["id"], False),
                    opponent_id=opponent["id"],
                    evidence_kind="fullsearch-external",
                    shared_bootstrap=shared,
                )

            comparisons = {o["id"]: summarize_external(o) for o in config["opponents"]}
            shared = None
            statistics_failure = None
            if any(item["gamesQualifiedForCI"] for item in comparisons.values()):
                try:
                    shared = family_bootstrap_table(
                        [f["id"] for f in families],
                        output / "bootstrap-indices.i64le",
                        seed=config["statisticsContract"]["seed"],
                    )
                    comparisons = {
                        o["id"]: summarize_external(o, shared) for o in config["opponents"]
                    }
                except (ImportError, ValueError, TypeError, OSError) as error:
                    statistics_failure = {"kind": "statistics", "message": str(error)}
                    if failure is None:
                        failure = statistics_failure
                    else:
                        failure["statistics"] = statistics_failure
            report.update(
                failure=failure,
                engineSessions=sessions,
                independentStrengthQualification=None,
                comparisonScope="development-contest",
                cohortCleanupQualified=cohort_qualified,
                familyBootstrapShared=shared["metadata"] if shared is not None else None,
                statisticsFailure=statistics_failure,
                comparison=comparisons,
            )
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
