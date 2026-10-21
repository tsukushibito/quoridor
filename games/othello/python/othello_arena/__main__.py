"""Run a Root-bound finite schedule under the existing resource/job guardian."""

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import sys
import time

from .engines import EgaroucidFixedTime, GTP, NativePlayer
from .matches import _normal_comparison_game, comparison_summary, paired, summarize
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


def comparison_bindings(config):
    """Metadata-only preflight. Actual executable/model hashes use checked_spec at launch."""
    fixed = {
        "purpose": "native_evaluator_comparison",
        "timeMs": 1000,
        "overheadMs": 100,
        "threads": 1,
        "ttMiB": 32,
        "maxDepth": 64,
        "exactEmpties": 12,
        "book": False,
        "ponder": False,
        "superiorityClaim": False,
    }
    if any(type(config.get(k)) is not type(v) or config[k] != v for k, v in fixed.items()):
        raise ValueError("native comparison clock/search profile differs")
    if len(config["opponents"]) != 1 or "families" in config:
        raise ValueError("one native opponent and frozen opening FileRefs required")
    model = config["model"]
    if (
        not Path(model["path"]).is_absolute()
        or type(model["bytes"]) is not int
        or not 0 < model["bytes"] <= 128 * 1024
        or model["mode"] != "0644"
        or re.fullmatch("[0-9a-f]{64}", model["sha256"]) is None
    ):
        raise ValueError("explicit immutable pattern model FileRef required")
    rules, candidate, opponent = config["rules"], config["candidate"], config["opponents"][0]
    if re.fullmatch("[A-Za-z0-9_-]{1,64}", opponent["id"]) is None:
        raise ValueError("bounded native opponent identifier required")
    image = rules["argv"][0]
    image_ref = {
        "sha256": "2678ba8e2ff207a4f1d1f2f1047a345964fafad4375e9abcf5d9d6b34debc71d",
        "bytes": 800888,
        "mode": "0755",
    }
    for spec in (rules, candidate, opponent):
        if (
            spec["argv"][0] != image
            or not Path(image).is_absolute()
            or any(spec["binary"].get(k) != v for k, v in image_ref.items())
            or spec["cwd"] != rules["cwd"]
            or spec.get("simple", False) is not False
            or {"maxNodes", "nodeCap", "nodeLimit"} & spec.keys()
            or any(
                k in spec and (type(spec[k]) is not type(fixed[k]) or spec[k] != fixed[k])
                for k in (
                    "timeMs",
                    "ttMiB",
                    "maxDepth",
                    "exactEmpties",
                    "threads",
                    "book",
                    "ponder",
                )
            )
        ):
            raise ValueError(
                "comparison requires same pinned native image/profile, without node cap"
            )
    if {"maxNodes", "nodeCap", "nodeLimit"} & config.keys():
        raise ValueError("aggregate node cap is not part of this comparison")
    if (
        candidate["protocol"] != "native_jsonl"
        or opponent["protocol"] != "native_jsonl"
        or rules["argv"] != [image]
        or opponent["argv"] != [image]
        or candidate["argv"]
        != [image, "--pattern", model["path"], "--model-id", "sha256:" + model["sha256"]]
        or candidate.get("assets") != [model]
        or rules.get("assets", [])
        or opponent.get("assets", [])
    ):
        raise ValueError("only frozen pattern selection may differ from no-args v1 heuristic")
    return {
        "candidate": {
            "kind": "patternV1",
            "modelId": "sha256:" + model["sha256"],
            "modelBytes": model["bytes"],
            "identityBinding": "callerVerified",
        },
        "opponent": {"kind": "v1Heuristic"},
    }


def comparison_families(config):
    """Reuse Rust-only preparation/canonical/frozen-input guards; no raw family fallback."""
    from . import generation

    prepared = generation._read(config["openingConfig"], 256 * 1024)
    generation._validate(prepared)
    if prepared["purpose"] != "native_evaluator_comparison":
        raise ValueError("foreign opening preparation purpose")
    for key in ("argv", "binary", "cwd"):
        if prepared["engine"][key] != config["rules"][key]:
            raise ValueError("opening preparation used a different native image")
    canonical = generation._canonical(prepared)
    excluded = generation._excluded_keys(prepared, canonical)
    records = generation._frozen_openings(
        dict(prepared, openings=config["openings"]), canonical, excluded
    )
    return [{"id": r["openingFamily"], "moves": r["moves"], "state": r["state"]} for r in records]


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
    comparison = config["purpose"] == "native_evaluator_comparison"
    families, evaluations = [], {}
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

    def ready(native, player=None):
        record = lifecycle[-1]
        try:
            record["initialResponse"] = (
                player.initialize(deadline=time.monotonic() + 30)
                if player
                else native.request("new", deadline=time.monotonic() + 30)
            )
        finally:
            record["readyWallMs"] = (time.monotonic() - record["started"]) * 1000
            record["lastSetupResponse"] = getattr(native, "last_response", None)

    try:
        if not config.get("launchBinding"):
            raise ValueError("Root must bind native images/resources/fair timing before launch")
        if comparison:
            evaluations = comparison_bindings(config)
            families = comparison_families(config)
        else:
            families = smoke_families(config)
        family_index = {f["id"]: f for f in families}
        for opponent in config["opponents"]:
            with ExitStack() as stack:
                rules = Native(start(stack, "rules-" + opponent["id"], config["rules"]))
                if comparison:
                    ready(rules)
                candidate = NativePlayer(
                    Native(start(stack, "candidate-" + opponent["id"], config["candidate"])),
                    simple=config["candidate"].get("simple", False),
                    evaluation=evaluations.get("candidate"),
                )
                if comparison:
                    ready(candidate.native, candidate)
                process = start(stack, opponent["id"], opponent)
                engine = (
                    NativePlayer(Native(process), evaluation=evaluations["opponent"])
                    if comparison
                    else EgaroucidFixedTime(process)
                    if opponent["protocol"] == "fixed_jsonl"
                    else GTP(process, engine=opponent["engine"])
                )
                if comparison:
                    ready(engine.native, engine)
                for result in paired(
                    rules,
                    candidate,
                    engine,
                    families,
                    time_ms=config["timeMs"],
                    overhead_ms=config["overheadMs"],
                ):
                    result["opponent"] = opponent["id"]
                    if comparison and not _normal_comparison_game(
                        result, family_index.get(result.get("family"), {}), evaluations
                    ):
                        result["failure"] = result.get("failure") or {
                            "kind": "qualification",
                            "message": "game terminal/protocol/clock evidence incomplete or inconsistent",
                        }
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
            "byOpponent": {}
            if comparison
            else {
                o["id"]: summarize([r for r in results if r["opponent"] == o["id"]], 8)
                for o in config["opponents"]
            },
            "superiorityClaim": False,
        }
        if comparison:
            cleanup_ok = len(cleanups) == 3 and all(
                p.cleanup
                and p.cleanup.get("directReaped") is True
                and not p.cleanup.get("errors")
                and not p.cleanup.get("unexpectedExit")
                for p in cleanups
            )
            report["comparison"] = comparison_summary(
                results,
                families,
                evaluations,
                run_qualified=failure is None and cleanup_ok,
                opponent_id=config["opponents"][0].get("id")
                if len(config["opponents"]) == 1
                else None,
            )
            if len(config["opponents"]) == 1:
                report["byOpponent"][config["opponents"][0]["id"]] = report["comparison"]
            if not report["comparison"]["ciEligible"] and failure is None:
                failure = report["failure"] = {
                    "kind": "qualification",
                    "message": "original32 games/pairs/setup/cleanup did not all qualify",
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
