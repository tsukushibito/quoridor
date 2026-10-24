"""Bound continuous comparison using the normal owned native process transport."""

import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time


def checked(ref, maximum=None):
    path = Path(ref["path"])
    assert path.is_absolute() and path.stat().st_size == ref["bytes"]
    assert f"{path.stat().st_mode & 0o777:04o}" == ref["mode"]
    assert maximum is None or ref["bytes"] <= maximum
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == ref["sha256"]
    return path


def write(path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    assert len(text.encode()) <= 2 * 1024**2
    path.write_text(text)


def cpu(process):
    """Specific owned live child CPU only; unavailable remains NULL."""
    try:
        fields = Path(f"/proc/{process.child.pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError):
        return None


def comparison_owners(config):
    kind = config.get("comparisonKind", "rust-original")
    if kind == "rust-original":
        return ("rust", "original")
    if kind == "rust-rust":
        return ("baseline", "candidate")
    raise ValueError("unsupported continuous comparison kind")


def validate_rust_pair(definition):
    """Two explicit native FullSearch specs; never impersonate original transport."""
    specs = []
    for owner in ("baseline", "candidate"):
        spec = definition[owner]
        assert spec and spec["binary"] and definition["qualifiedBuilds"][owner]
        assert spec["argv"] and spec["argv"][0] == spec["binary"]["path"]
        expected = definition["expectedInfo"][owner]
        assert expected and expected["engine"] == "console7.8.1-rust-singlethread-source-port"
        assert expected["upstreamCommit"] == "570d5e0a478c9d720d75de06a5d31995f412704a"
        assert expected["interpretation"] == "simd"
        assert expected["identityBinding"] == "callerVerified"
        assert expected["hashLevel"] == 20 and expected["hashSeed"] == 20261022
        assert expected["workerPool"] == 0
        specs.append(spec)
    assert specs[0]["binary"]["sha256"] != specs[1]["binary"]["sha256"]
    assert specs[0]["argv"][1:] == specs[1]["argv"][1:]
    assert specs[0]["cwd"] == specs[1]["cwd"] and specs[0]["assets"] == specs[1]["assets"]


def fixed_differences(left, right):
    """Require the declared fixed result fields, keeping nullable probabilities exact."""
    fields = (
        "rawScore",
        "score",
        "move",
        "mustPass",
        "nodes",
        "completedDepth",
        "selectivity",
        "probability",
        "proven",
        "isEndSearch",
    )
    return [
        key for key in fields if type(left[key]) is not type(right[key]) or left[key] != right[key]
    ]


def main():
    raw = Path(sys.argv[1]).read_bytes()
    assert len(raw) <= 128 * 1024 and hashlib.sha256(raw).hexdigest() == sys.argv[2]
    config = json.loads(raw)
    assert config["admitted"] is True
    owners = comparison_owners(config)
    same_rust = owners == ("baseline", "candidate")
    if same_rust:
        assert checked(config["comparator"]).resolve() == Path(__file__).resolve()
        for definition in config["profiles"].values():
            validate_rust_pair(definition)
    assert config["pruningOffMeaning"] == "statistical-MPC-off;exact-cuts-retained"
    assert config["generationQualification"] and config["exposureQualification"]
    assert config["cpuPlan"] and config["resourceBinding"] and config["outputDirectory"]
    assert config["limits"] == {
        "fixedRequestSeconds": 10,
        "timedRequestSeconds": 1.1,
        "setupSeconds": 30,
        "resetSeconds": 5,
        "dropSeconds": 6,
        "commandSeconds": 1200,
        "parentSeconds": 1260,
    }
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert all(
        os.environ.get(k) == "1"
        for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
    )
    for ref in config["sourceRequired"]:
        checked(ref)
    checked(config["protocolSource"])
    checked(config["arenaMainSource"])
    for key in ("generationQualification", "exposureQualification"):
        checked(config[key], 128 * 1024)
    roots = json.loads(checked(config["roots"], 512 * 1024).read_bytes())
    assert roots["admitted"] is True and roots["H"] == 0
    families = roots["families"]
    assert len(families) == 4
    assert [f["seed"] for f in families] == [
        2026102301001,
        2026102301002,
        2026102301003,
        2026102301004,
    ]
    assert len({f["id"] for f in families}) == 4
    components = [f["exposureComponent"] for f in families]
    assert len(set(components)) == 4 and all(components)
    all_roots = [r for f in families for r in f["roots"]]
    assert len(all_roots) == 16 and len({r["id"] for r in all_roots}) == 16
    for family in families:
        assert family["split"] == "development"
        assert [r["placement"] for r in family["roots"]] == [16, 32, 48, 56]
        assert family["generationActions"] <= 128
        for root in family["roots"]:
            assert root["rulesStatusBinding"] and root["canonicalSHA256"]
            assert root["state"]["version"] == 1
            assert root["state"]["toMove"] in (1, 2)
            assert len(root["state"]["board"]) == 64
            assert root["status"]["terminal"] is False
    assert len({r["canonicalSHA256"] for r in all_roots}) == 16
    sys.path.insert(0, str(Path(config["projectRoot"]) / "games/othello/python"))
    from othello_arena.__main__ import checked_spec
    from othello_arena.protocol import Process

    out = Path(config["outputDirectory"])
    assert out.is_dir()
    cancel = Path(config["cancelFile"])
    started = time.monotonic()
    slots = []
    for profile in ("fixed", "timed"):
        for family in families:
            counts = {owner: 0 for owner in owners}
            for block, owner in enumerate((owners[0], owners[1], owners[1], owners[0])):
                repeat = counts[owner]
                counts[owner] += 1
                for root in family["roots"]:
                    slots.append(
                        {
                            "index": len(slots),
                            "profile": profile,
                            "family": family["id"],
                            "block": block,
                            "owner": owner,
                            "repeat": repeat,
                            "root": root["id"],
                            "status": "UNRUN",
                        }
                    )
    assert len(slots) == 128
    setup, resets, shutdown, processes = [], [], [], {}
    seen, primary, current = {}, None, None
    attempted = 0

    def deadline(seconds):
        return min(time.monotonic() + seconds, started + 1200)

    def snapshot():
        write(
            out / "result.json",
            {
                "status": "STOP"
                if primary
                else ("COMPLETE" if all(s["status"] == "COMPLETE" for s in slots) else "PARTIAL"),
                "plannedCalls": 128,
                "attemptedCalls": attempted,
                "completedCalls": sum(s["status"] == "COMPLETE" for s in slots),
                "failed": primary,
                "slots": slots,
                "setup": setup,
                "resets": resets,
                "shutdown": shutdown,
                "wholeSeconds": time.monotonic() - started,
                "configSHA256": sys.argv[2],
                "actualRoots": config["roots"],
                "wholeTTIdentity": "UNKNOWN",
                "comparisonKind": config.get("comparisonKind", "rust-original"),
                "strengthClaim": False,
            },
        )

    try:
        for profile in ("fixed", "timed"):
            definition = config["profiles"][profile]
            if same_rust:
                for owner in owners:
                    checked(definition["qualifiedBuilds"][owner])
            else:
                assert definition["qualifiedBuild"] and definition["original"]["binary"]
                checked(definition["qualifiedBuild"])
            processes = {}
            for owner in owners:
                spec = checked_spec(definition[owner])
                assert config["midgame"] in spec["assets"]
                assert config["ordering"] in spec["assets"]
                start = time.monotonic()
                process = Process(
                    spec["argv"],
                    cwd=spec["cwd"],
                    log=out / f"{profile}-{owner}.log",
                    cancelled=cancel.exists,
                    limit=65536,
                )
                processes[owner] = process  # Ownership before first request.
                info = process.json_request({"op": "info"}, deadline=deadline(30))
                for key, value in definition["expectedInfo"][owner].items():
                    assert info.get(key) == value, (owner, key, info.get(key))
                mid_id = "sha256:" + config["midgame"]["sha256"]
                ordering_id = "sha256:" + config["ordering"]["sha256"]
                if owner != "original":
                    assert info["midgameId"] == mid_id
                    assert info["orderingId"] == ordering_id
                    assert info["coefficients"] == config["coefficients"]
                else:
                    assert info["weightIdentity"]["callerVerified"] is True
                    assert info["weightIdentity"]["midgameId"] == mid_id
                    assert info["weightIdentity"]["orderingId"] == ordering_id
                    assert info["controls"]["compiledMpc"] == (profile == "timed")
                    assert info["controls"]["workerPool"] == 0
                    assert info["controls"]["useMultiThread"] is False
                    assert info["controls"]["book"] is False
                    assert info["controls"]["ponder"] is False
                setup.append(
                    {
                        "profile": profile,
                        "owner": owner,
                        "info": info,
                        "launchAndReadyMs": (time.monotonic() - start) * 1000,
                        "pureModelParseMs": None,
                        "preMainMs": None,
                        "childCPUSecondsAtReady": cpu(process),
                    }
                )
            for slot in (s for s in slots if s["profile"] == profile):
                current = slot
                process = processes[slot["owner"]]
                if slot["root"] == next(
                    f["roots"][0]["id"] for f in families if f["id"] == slot["family"]
                ):
                    start = time.monotonic()
                    before = cpu(process)
                    reply = process.json_request({"op": "clear"}, deadline=deadline(5))
                    if same_rust:
                        assert reply.get("ok") is True
                    resets.append(
                        {
                            "profile": profile,
                            "family": slot["family"],
                            "block": slot["block"],
                            "owner": slot["owner"],
                            "reply": reply,
                            "outerMs": (time.monotonic() - start) * 1000,
                            "cpuBefore": before,
                            "cpuAfter": cpu(process),
                        }
                    )
                root = next(r for r in all_roots if r["id"] == slot["root"])
                options = dict(definition["options"])
                if profile == "fixed":
                    options["fixedDepth"] = root["fixedDepth"]  # Frozen by Rust authority.
                    assert 1 <= options["fixedDepth"] <= 6
                    if same_rust:
                        assert options["fixedDepth"] in (4, 6)
                payload = {"op": "search", "state": root["state"], "options": options}
                if slot["owner"] == "original":
                    payload["caseId"] = root["id"]
                seconds = 10 if profile == "fixed" else 1.1
                slot["status"] = "ATTEMPTED"
                attempted += 1
                snapshot()
                before_cpu = cpu(process)
                start = time.monotonic()
                response = process.json_request(payload, deadline=deadline(seconds))
                wall_ms = (time.monotonic() - start) * 1000
                slot.update(
                    response=response,
                    outerWallMs=wall_ms,
                    cpuBefore=before_cpu,
                    cpuAfter=cpu(process),
                    request=payload,
                )
                assert wall_ms <= seconds * 1000
                result = response["result"]
                if same_rust:
                    # Normal FullSearchResult exposes no restoration flag.
                    slot["restorationObserved"] = None
                move = result["move"]
                status = root["status"]
                assert result["mustPass"] == status["mustPass"]
                assert result["terminal"] == status["terminal"]
                if status["mustPass"] or status["terminal"]:
                    assert move is None
                else:
                    assert type(move) is int and move in status["legalMoves"]
                assert type(result["nodes"]) is int and result["nodes"] >= 0
                assert type(result["completedDepth"]) is int and result["completedDepth"] > 0
                assert result["scoreUnits"] == "engine-disc"
                if slot["owner"] == "original":
                    assert response["protocol"] == "egaroucid-continuous16-v1"
                    assert response["profile"] == definition["expectedInfo"]["original"]["profile"]
                    assert response["caseId"] == root["id"]
                else:
                    assert result["interpretation"] == "simd"
                    assert result["coefficients"] == config["coefficients"]
                assert type(result["proven"]) is bool
                assert type(result["ttBytes"]) is int and 0 < result["ttBytes"] <= 32 * 1024**2
                for key in ("score", "rawScore"):
                    value = result[key]
                    assert value is None or (
                        type(value) is int and math.isfinite(value) and -64 <= value <= 64
                    )
                assert result["score"] is not None
                if profile == "fixed":
                    assert result["rawScore"] is not None
                    assert result["completedDepth"] == options["fixedDepth"]
                    assert result["selectivity"] == 6
                    assert result.get("stopped") is None
                else:
                    assert result.get("stopped") in (None, "timeout")
                pair = (profile, slot["family"], slot["root"], slot["repeat"])
                previous = seen.get(pair)
                if previous:
                    assert previous["owner"] != slot["owner"]
                    a, b = previous["result"], result
                    slot["pairedComparison"] = {
                        "rawEqual": None if profile == "timed" else a["rawScore"] == b["rawScore"],
                        "policyDifferent": a["move"] != b["move"],
                        "sameWorkClaim": False,
                    }
                    if profile == "fixed":
                        differences = (
                            fixed_differences(a, b)
                            if same_rust
                            else (["rawScore"] if a["rawScore"] != b["rawScore"] else [])
                        )
                        slot["pairedComparison"]["fixedDifferences"] = differences
                        if differences:
                            slot["status"] = "FAILED"
                            raise RuntimeError(
                                "first fixed result difference: "
                                + ", ".join(differences)
                                + "; no refill"
                            )
                else:
                    seen[pair] = {"owner": slot["owner"], "result": result}
                slot["status"] = "COMPLETE"
                snapshot()
            # Each profile owns exactly two persistent initialized processes.
            for owner, process in processes.items():
                start = time.monotonic()
                before = cpu(process)
                process.close()
                shutdown.append(
                    {
                        "profile": profile,
                        "owner": owner,
                        "cleanup": process.cleanup,
                        "dropMs": (time.monotonic() - start) * 1000,
                        "childCPUSecondsBeforeDrop": before,
                        "CPUAfterDrop": None,
                    }
                )
                assert process.cleanup["directReaped"]
                assert not process.cleanup["unexpectedExit"] and not process.cleanup["errors"]
            processes = {}
    except BaseException as error:
        primary = {"type": type(error).__name__, "error": str(error)}
        if current and current["status"] == "ATTEMPTED":
            current["status"] = "FAILED"
    finally:
        for owner, process in processes.items():
            if process.closed:
                continue
            start = time.monotonic()
            try:
                process.close()
            except BaseException as error:
                primary = primary or {"type": type(error).__name__, "error": str(error)}
            shutdown.append(
                {
                    "owner": owner,
                    "cleanup": process.cleanup,
                    "dropMs": (time.monotonic() - start) * 1000,
                    "CPUAfterDrop": None,
                }
            )
        snapshot()
    complete = primary is None and all(s["status"] == "COMPLETE" for s in slots)
    write(
        out / "completion.json",
        {
            "complete": complete,
            "planned": 128,
            "attempted": attempted,
            "remainingUNRUN": sum(s["status"] == "UNRUN" for s in slots),
            "firstError": primary,
            "noRefill": True,
            "scope": "finite development practical comparison; no strength/default claim",
        },
    )
    if not complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
