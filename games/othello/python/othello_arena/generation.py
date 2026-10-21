"""Root-controlled weak-simple pilot connector; no search/teacher/fit or job manager.

Two separate run(config_FileRef, new_output_dir) calls are required. ``openings``
selects 24 unlabeled eight-placement development openings (T16/V8, seed20261022,
<=256 attempts). Root freezes that actual openings.json FileRef and its splits
before issuing ``games``. The latter replays each opening with Rust, then uses
only Rust simple/status/play/pass through real terminal status, <=121 total
transitions. A mandatory pass does not advance the placement number. Sample
once per preterminal placement8..60/4, before a mandatory pass when present.

Config: stage, purpose="weak-simple-phase-pattern-pilot", seed=20261022,
namespace="development/<name>", slots=[{gameId,openingFamily,split:"T"|"V"}]*24,
engine=existing checked_spec format, source=FileRef(this module),
canonicalSource=FileRef(same-tree othello_training/pattern.py),
smokeOpenings=FileRef(original four-family smoke config), limits=PILOT_LIMITS,
duplicatePolicy=DUPLICATE_POLICY, launchBinding=Root's concrete resource/source
binding. Stage games additionally requires openings=FileRef(complete output
from stage openings). Config itself is read only after size/mode/SHA matching.
No Main/core-WT source fallback; canonical math has one integrated owner.

Cross-split D4/STM/color sample duplicates are ALL excluded. Within one split,
retain exactly the lexical (gameId, placement) first sample. No copies/refill;
any of24 families without a retained sample is STOP. Five-field training rows
have gameOutcome labels from actual Rust terminal counts, never minimax truth.
Complete terminal/replay evidence is separate from trainer consistency checks.

The existing caller owns CPU/RAM/GPU/deadline/cancellation, execute directwait,
handles and the shared32MiB pilot budget including at most two later checkpoints
and logs. This connector creates no checkpoints and launches one existing
persistent Process only after explicit Root binding. It never calls search.
"""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import time

from .__main__ import checked_spec
from .protocol import Native, Process

MIB = 1024**2
PILOT_LIMITS = {
    "games": 24,
    "openingPlacements": 8,
    "openingAttempts": 256,
    "rows": 4096,
    "inputBytes": 16 * MIB,
    "evidenceBytes": 16 * MIB,
    "retainedBytes": 32 * MIB,
    "checkpoints": 2,
}
DUPLICATE_POLICY = "cross-split-exclude-all;within-split-lexical-gameId-placement-first"
PURPOSE = "weak-simple-phase-pattern-pilot"


class GenerationStop(RuntimeError):
    pass


def _encode(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def _ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "mode": f"{path.stat().st_mode & 0o777:04o}",
        "sha256": digest,
    }


def _matches_ref(path, reference):
    # Optional provenance fields (e.g. accepted commit) remain in the config.
    return all(reference.get(key) == value for key, value in _ref(path).items())


def _read(reference, maximum):
    path = Path(reference["path"])
    if not path.is_absolute() or path.stat().st_size > maximum or not _matches_ref(path, reference):
        raise GenerationStop("FileRef size/mode/SHA mismatch before parse")
    return json.loads(path.read_bytes())


def _validate(config):
    if (
        config["purpose"] != PURPOSE
        or type(config["seed"]) is not int
        or config["seed"] != 20261022
    ):
        raise GenerationStop("explicit weak-simple purpose and seed20261022 required")
    if config["stage"] not in ("openings", "games") or not config.get("launchBinding"):
        raise GenerationStop("Root must bind one stage and its resources before execution")
    if config["limits"] != PILOT_LIMITS or config["duplicatePolicy"] != DUPLICATE_POLICY:
        raise GenerationStop("first-pilot limits/duplicate policy must be fixed before outcomes")
    namespace = config["namespace"]
    if not namespace.startswith("development/") or "final" in namespace.casefold():
        raise GenerationStop("development namespace required; final namespace excluded")
    slots = config["slots"]
    if len(slots) != 24 or Counter(s["split"] for s in slots) != {"T": 16, "V": 8}:
        raise GenerationStop("exactly24 whole-game slots with T16/V8 required")
    if any(set(s) != {"gameId", "openingFamily", "split"} for s in slots):
        raise GenerationStop("unlabeled slot requires only gameId/openingFamily/split")
    for key in ("gameId", "openingFamily"):
        values = [s[key] for s in slots]
        if len(set(values)) != 24 or any(
            not v.startswith(namespace + "/") or "final" in v.casefold() for v in values
        ):
            raise GenerationStop("24 distinct development game/family IDs required")
    if not _matches_ref(__file__, config["source"]):
        raise GenerationStop("generation source differs from Root binding")


def _canonical(config):
    expected = Path(__file__).resolve().parents[1] / "othello_training/pattern.py"
    if not expected.is_file():
        raise GenerationStop("source integration prerequisite: same-tree othello_training.pattern")
    if not _matches_ref(expected, config["canonicalSource"]):
        raise GenerationStop("canonical source FileRef mismatch")
    from othello_training import pattern

    if Path(pattern.__file__).resolve() != expected:
        raise GenerationStop("foreign-tree canonical import refused; no Main fallback")

    def canonical(position):
        return pattern.canonical_board(pattern.state(position))

    return canonical


def _call(native, op, cancelled, **fields):
    if cancelled():
        raise GenerationStop("cancelled before Rust request")
    return native.request(op, deadline=time.monotonic() + 5, **fields)


def _smoke_keys(config, canonical):
    smoke = _read(config["smokeOpenings"], 256 * 1024)
    families = smoke["families"]
    if len(families) != 4:
        raise GenerationStop("exact four original protocol-smoke exclusions required")
    keys = {canonical(f["state"]) for f in families}
    if len(keys) != 4:
        raise GenerationStop("four distinct original smoke canonical exclusions required")
    return keys


def _prepare(native, config, canonical, excluded, result, cancelled):
    rng = random.Random(config["seed"])
    used = set(excluded)
    result["attempts"] = 0
    result["rejections"] = Counter()
    for _ in range(256):
        if len(result["records"]) == 24:
            break
        result["attempts"] += 1
        state = _call(native, "new", cancelled)["state"]
        moves, placements = [], 0
        for _ in range(16):
            status = _call(native, "status", cancelled, state=state)["status"]
            if status["terminal"] or placements == 8:
                break
            move = None if status["mustPass"] else rng.choice(sorted(status["legalMoves"]))
            request = {"state": state} if move is None else {"state": state, "move": move}
            state = _call(native, "pass" if move is None else "play", cancelled, **request)["state"]
            moves.append(move)
            placements += move is not None
        status = _call(native, "status", cancelled, state=state)["status"]
        if placements != 8 or status["terminal"]:
            result["rejections"]["not-eight-preterminal-placements"] += 1
            continue
        key = canonical(state)
        if key in used:
            result["rejections"]["smoke-or-development-equivalent"] += 1
            continue
        used.add(key)
        slot = config["slots"][len(result["records"])]
        result["records"].append(
            {
                **slot,
                "moves": moves,
                "state": state,
                "canonicalSha256": hashlib.sha256(key).hexdigest(),
            }
        )
    if len(result["records"]) != 24:
        raise GenerationStop(
            f"opening candidate deficit: {24 - len(result['records'])}; no labels generated"
        )


def _frozen_openings(config, canonical, excluded):
    frozen = _read(config["openings"], PILOT_LIMITS["inputBytes"])
    records = frozen["records"]
    if (
        frozen.get("complete") is not True
        or frozen.get("stage") != "openings"
        or frozen.get("seed") != config["seed"]
        or frozen.get("outcomeLabels") is not False
        or len(records) != 24
    ):
        raise GenerationStop("Root must freeze24 complete actual states/splits before outcomes")
    for field in (
        "source",
        "engine",
        "canonicalSource",
        "smokeOpenings",
        "duplicatePolicy",
        "namespace",
    ):
        if frozen.get(field) != config[field]:
            raise GenerationStop("frozen opening source/exclusion/policy binding changed")
    used = set(excluded)
    for opening, slot in zip(records, config["slots"], strict=True):
        if any(opening[k] != slot[k] for k in ("gameId", "openingFamily", "split")):
            raise GenerationStop("frozen game/family/split differs from bound config")
        if len(opening["moves"]) > 16 or sum(m is not None for m in opening["moves"]) != 8:
            raise GenerationStop("frozen opening must contain exactly8 placements")
        key = canonical(opening["state"])
        if key in used or hashlib.sha256(key).hexdigest() != opening["canonicalSha256"]:
            raise GenerationStop("frozen opening duplicate/smoke exclusion/identity mismatch")
        used.add(key)
    return records


def _play_game(native, opening, evidence, cancelled):
    state = _call(native, "new", cancelled)["state"]
    placements = 0
    samples = []
    last_sample = None
    for transition in range(122):
        evidence["lastState"] = state
        if transition == len(opening["moves"]) and state != opening["state"]:
            raise GenerationStop("Rust opening replay differs from frozen expectedstate")
        status = _call(native, "status", cancelled, state=state)["status"]
        if status["terminal"]:
            if transition < len(opening["moves"]):
                raise GenerationStop("Rust terminal during opening replay")
            difference = status["black"] - status["white"]
            evidence.update(
                complete=True,
                terminalState=state,
                terminalStatus=status,
                actualBlackMinusWhite=difference,
            )
            return [
                {
                    "placement": p,
                    "split": opening["split"],
                    "row": {
                        "gameId": opening["gameId"],
                        "openingFamily": opening["openingFamily"],
                        "state": s,
                        "labelKind": "gameOutcome",
                        "targetCentidiscs": 100 * difference * (1 if s["toMove"] == 1 else -1),
                    },
                }
                for p, s in samples
            ]
        if transition == 121:
            raise GenerationStop("Rust game exceeded121 legal transitions")
        if (
            transition >= len(opening["moves"])
            and 8 <= placements <= 60
            and placements % 4 == 0
            and placements != last_sample
        ):
            samples.append((placements, state))
            last_sample = placements
        if transition < len(opening["moves"]):
            move = opening["moves"][transition]
        elif status["mustPass"]:
            move = None
        else:
            move = _call(native, "simple", cancelled, state=state)["move"]
        # Legal/pass decisions belong to Rust; this rejects a malformed adapter reply.
        if (move is None and not status["mustPass"]) or (
            move is not None and (type(move) is not int or move not in status["legalMoves"])
        ):
            raise GenerationStop("illegal simple/opening reply; no replacement")
        side = state["toMove"]
        request = {"state": state} if move is None else {"state": state, "move": move}
        state = _call(native, "pass" if move is None else "play", cancelled, **request)["state"]
        placements += move is not None
        evidence["replay"].append({"side": side, "move": move, "placement": placements})
    raise GenerationStop("unreachable transition bound")


def _deduplicate(samples, families, canonical):
    groups = defaultdict(list)
    for sample in samples:
        groups[canonical(sample["row"]["state"])].append(sample)
    kept = []
    cross = within = 0
    for group in groups.values():
        if len({sample["split"] for sample in group}) > 1:
            cross += len(group)
            continue
        ordered = sorted(group, key=lambda s: (s["row"]["gameId"], s["placement"]))
        kept.append(ordered[0])
        within += len(group) - 1
    kept.sort(key=lambda s: (s["row"]["gameId"], s["placement"]))
    counts = Counter(s["row"]["openingFamily"] for s in kept)
    return [s["row"] for s in kept], {
        "crossSplitExcluded": cross,
        "withinSplitExcluded": within,
        "retainedByFamily": {family: counts[family] for family in sorted(families)},
        "zeroSampleFamilies": sorted(f for f in families if counts[f] == 0),
    }


def run(config_ref, output, *, cancelled=lambda: False):
    """Explicitly issued stage only; enclosing standard job owns resource controls."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    config = {}
    report = {
        "stage": config.get("stage"),
        "seed": config.get("seed"),
        "config": config_ref,
        "source": _ref(__file__),
        "status": "STOP",
        "failure": None,
        "gamesPlanned": 0,
        "gamesAttempted": 0,
        "gamesComplete": 0,
        "unrunGames": 0,
        "labels": "UNRUN",
        "cleanup": None,
        "limits": PILOT_LIMITS,
        "duplicatePolicy": DUPLICATE_POLICY,
    }
    openings = {
        "stage": "openings",
        "seed": config.get("seed"),
        "outcomeLabels": False,
        "complete": False,
        "records": [],
        "source": report["source"],
        "config": config_ref,
    }
    games, samples, rows = [], [], []
    process = None
    try:
        config = _read(config_ref, 256 * 1024)
        report.update(stage=config.get("stage"), seed=config.get("seed"))
        openings.update(seed=config.get("seed"))
        for field in ("engine", "canonicalSource", "smokeOpenings", "duplicatePolicy", "namespace"):
            openings[field] = config.get(field)
        _validate(config)
        if config["stage"] == "games":
            report.update(gamesPlanned=24, unrunGames=24)
        canonical = _canonical(config)
        excluded = _smoke_keys(config, canonical)
        frozen = (
            _frozen_openings(config, canonical, excluded) if config["stage"] == "games" else None
        )
        checked_spec(config["engine"])
        report["engine"] = config["engine"]
        report["canonicalSource"] = config["canonicalSource"]
        process = Process(
            config["engine"]["argv"],
            cwd=config["engine"]["cwd"],
            log=output / "protocol.log",
            cancelled=cancelled,
        )
        with process:
            native = Native(process)
            if frozen is None:
                _prepare(native, config, canonical, excluded, openings, cancelled)
                openings["complete"] = True
            else:
                for opening in frozen:
                    evidence = {
                        "gameId": opening["gameId"],
                        "openingFamily": opening["openingFamily"],
                        "split": opening["split"],
                        "openingState": opening["state"],
                        "complete": False,
                        "replay": [],
                    }
                    games.append(evidence)
                    report["gamesAttempted"] += 1
                    report["unrunGames"] -= 1
                    samples.extend(_play_game(native, opening, evidence, cancelled))
                    report["gamesComplete"] += 1
                rows, duplicates = _deduplicate(
                    samples, {s["openingFamily"] for s in frozen}, canonical
                )
                report.update(labels="gameOutcome", duplicates=duplicates)
                if duplicates["zeroSampleFamilies"]:
                    raise GenerationStop(
                        "zero-sample family deficit: " + ",".join(duplicates["zeroSampleFamilies"])
                    )
        if process.cleanup["unexpectedExit"]:
            raise GenerationStop("native crash before cleanup")
        report["status"] = "complete"
    except Exception as error:
        report["failure"] = {
            "kind": getattr(error, "kind", type(error).__name__),
            "message": str(error),
        }
        if error.__context__ is not None:
            report["failure"]["context"] = str(error.__context__)
    finally:
        report["cleanup"] = process.cleanup if process else None
        if games and report["gamesComplete"] != 24:
            report["labels"] = "not-published-incomplete-games"
        blobs = {"config.json": _encode(config)}
        if config.get("stage") == "openings":
            openings["complete"] = report["status"] == "complete"
            blobs["openings.json"] = _encode(openings)
        else:
            blobs["terminal-evidence.json"] = _encode(
                {
                    "config": config_ref,
                    "engine": config.get("engine"),
                    "source": report["source"],
                    "seed": config.get("seed"),
                    "games": games,
                }
            )
            blobs[
                "training.jsonl" if report["status"] == "complete" else "training.partial.jsonl"
            ] = b"".join(_encode(row) for row in rows)
        row_bytes = sum(len(_encode(row)) for row in rows)
        evidence_bytes = len(blobs.get("terminal-evidence.json", b""))
        if len(rows) > 4096 or row_bytes > 16 * MIB or evidence_bytes > 16 * MIB:
            report.update(
                status="STOP",
                failure={"kind": "bounds", "message": "row/input/evidence limit exceeded"},
            )
            blobs = {"config.json": _encode(config)}
        report.update(
            rows=len(rows),
            rowBytes=row_bytes,
            terminalEvidenceBytes=evidence_bytes,
            checkpointLimit=2,
            checkpointsCreated=0,
        )
        # Include the actual closed Process log/receipt and report, with64KiB
        # metadata/allocation margin. Later checkpoints share the caller's cap.
        existing = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        upper = existing + sum(len(data) for data in blobs.values()) + len(_encode(report)) + 65536
        if upper > 32 * MIB:
            report.update(
                status="STOP",
                failure={"kind": "bounds", "message": "retained output limit exceeded"},
            )
            blobs = {}
            upper = existing + len(_encode(report)) + 65536
        report.update(
            retainedUpperBytes=upper,
            remainingRetainedBytesForCheckpointsAndLogs=max(0, 32 * MIB - upper),
        )
        for name, data in blobs.items():
            (output / name).write_bytes(data)
        (output / "result.json").write_bytes(_encode(report))
    return report
