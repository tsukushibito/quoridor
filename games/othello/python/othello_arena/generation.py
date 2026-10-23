"""Root-bound opening, trajectory and label stages; shared Rust rules authority.

Config explicitly selects labelKind=gameOutcome or teacherEstimate. Outcome uses
24 T16/V8 terminal simple games. Teacher uses128 T96/V16/H16 actual eight-placement
roots, frozen by Root BEFORE any teacher result, then112 T/V simple trajectories,
then a separately frozen observation FileRef for fixed external estimates. H roots
are held only: no trajectory/teacher/selector. No search/selfplay/trainer framework.
Unlabeled native_evaluator_comparison openings use labelKind:null,16 D families,
seed2026102202, samplePlacements:[], all4+24+128 prior root exclusions (incl H).
Only opening preparation is allowed; Root resolves its finite attempt cap before
any results. Existing Rust preparation/canonical/immutable-input helpers are reused.

Required common config: stage, labelKind, purpose, explicit seed, development
namespace, slots, engine, source, canonicalSource, openingExclusions (list of
{file:FileRef, recordsKey, count}), samplePlacements, limits, duplicatePolicy,
launchBinding. Non-opening stages also bind openings=FileRef. Teacher stage binds
observations=FileRef and teacher={id,engine,adapterSource,upstreamCommit}; engine
spec binds actual binary/weights/argv once. teacher also contains the shared
training identity source/weights/adapter/args; args must equal engine.argv.
All FileRefs verify before parse.
Config/retention/resources are new Root decisions; tiny32MiB is NOT teacher cover.

Cross-split canonical duplicates ALL excluded; within-split lexical gameId/placement
first. Outcome samples once per preterminal placement8..60/4 before a pass. Teacher
samples[8,12,20,24,36,40,48,52] after resolving mandatory passes (same placement),
because the unchanged fixed frontend rejects no-legal input. Missing/duplicate/
early-terminal observations are deficits, never filled or retried. Five-field
outcome rows use actual terminal truth; teacher rows add the shared teacher object.
Arena canonical.py owns shared state shape/D4/STM identity. No tiny model or
training-loader dependency is needed for preparation or producer rows.

Unlabeled continuous-development uses four explicit family seeds, Rust-only legal
trajectories and target placements16/32/48/56, after mandatory passes. Checked
identity-only exposure metadata must declare complete placement8+ coverage; UNKNOWN
refuses admission. Whole-family collisions/terminal/deficits STOP without refill.
No prior state/H/label payload or model is read by this stage. All roots are dev.

run(config_FileRef,new_output,cancelled=current_callback) returns complete/STOP;
caller maps STOP to nonzero and owns current execute resources, termination/reap,
handles, cancellation/deadline and actual retained output guard. No checkpoint or
model payload is created here. Real stages require fresh Root software/admission.
"""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import time

from .__main__ import checked_spec
from .protocol import Native, Process

DUPLICATE_POLICY = "cross-split-exclude-all;within-split-lexical-gameId-placement-first"


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
    if config["stage"] == "continuous-development":
        _validate_continuous(config)
        return
    kind = config["labelKind"]
    comparison = config.get("purpose") == "native_evaluator_comparison"
    if (
        kind not in ((None,) if comparison else ("gameOutcome", "teacherEstimate"))
        or type(config["seed"]) is not int
    ):
        raise GenerationStop("explicit labelKind and seed required")
    stages = (
        ("openings",)
        if comparison
        else ("openings", "games")
        if kind == "gameOutcome"
        else ("openings", "trajectories", "teacher")
    )
    if config["stage"] not in stages or not config.get("launchBinding") or not config["purpose"]:
        raise GenerationStop("Root must bind explicit stage/purpose/resources")
    expected = (
        {"D": 16}
        if comparison
        else {"T": 16, "V": 8}
        if kind == "gameOutcome"
        else {"T": 96, "V": 16, "H": 16}
    )
    slots = config["slots"]
    if len(slots) != sum(expected.values()) or Counter(s["split"] for s in slots) != expected:
        raise GenerationStop("wrong whole-family split count")
    if any(set(s) != {"gameId", "openingFamily", "split"} for s in slots):
        raise GenerationStop("slots must be unlabeled IDs/splits only")
    namespace = config["namespace"]
    if not namespace.startswith("development/") or "final" in namespace.casefold():
        raise GenerationStop("development namespace required; final excluded")
    for key in ("gameId", "openingFamily"):
        values = [s[key] for s in slots]
        if len(set(values)) != len(slots) or any(
            not isinstance(v, str)
            or len(v.encode()) > 192
            or not v.startswith(namespace + "/")
            or "final" in v.casefold()
            for v in values
        ):
            raise GenerationStop("distinct named development slots required")
    if config["duplicatePolicy"] != DUPLICATE_POLICY:
        raise GenerationStop("duplicate policy must be fixed before labels")
    limits = config["limits"]
    required = ("openingAttempts", "inputBytes", "evidenceBytes", "retainedBytes")
    if not comparison:
        required += ("rows",)
    if any(type(limits[k]) is not int or limits[k] <= 0 for k in required):
        raise GenerationStop("fresh concrete positive limits required")
    if limits["inputBytes"] > 16 * 1024**2:
        raise GenerationStop("input cap exceeds shared loader16MiB limit")
    if comparison:
        if (
            config["seed"] != 2026102202
            or config["samplePlacements"] != []
            or limits["openingAttempts"] > 4096
            or sorted(x["count"] for x in config["openingExclusions"]) != [4, 24, 128]
        ):
            raise GenerationStop(
                "native comparison requires16 unlabeled roots and all prior exclusions"
            )
    elif kind == "teacherEstimate":
        if (
            config["samplePlacements"] != [8, 12, 20, 24, 36, 40, 48, 52]
            or config["samplePassPolicy"] != "after-mandatory-pass"
            or type(limits["teacherAttempts"]) is not int
            or not 0 < limits["teacherAttempts"] <= 1024
            or limits["openingAttempts"] > 4096
            or limits["rows"] > 896
            or sorted(x["count"] for x in config["openingExclusions"]) != [4, 24]
        ):
            raise GenerationStop("teacher schedule/exclusions/finite caps differ")
    elif (
        config["samplePlacements"] != list(range(8, 61, 4))
        or limits["rows"] > 4096
        or limits["openingAttempts"] > 256
    ):
        raise GenerationStop("outcome schedule/caps differ")
    if not _matches_ref(__file__, config["source"]):
        raise GenerationStop("generation source differs from Root binding")


def _canonical(config):
    expected = Path(__file__).resolve().parents[1] / "othello_arena/canonical.py"
    if not expected.is_file():
        raise GenerationStop("source integration prerequisite: same-tree othello_arena.canonical")
    if not _matches_ref(expected, config["canonicalSource"]):
        raise GenerationStop("canonical source FileRef mismatch")
    from . import canonical as positions

    if Path(positions.__file__).resolve() != expected:
        raise GenerationStop("foreign-tree canonical import refused; no Main fallback")

    def canonical(position):
        return positions.canonical_board(positions.state(position))

    return canonical


def _call(native, op, cancelled, **fields):
    if cancelled():
        raise GenerationStop("cancelled before Rust request")
    return native.request(op, deadline=time.monotonic() + 5, **fields)


def _excluded_keys(config, canonical):
    keys = set()
    for exclusion in config["openingExclusions"]:
        record = _read(exclusion["file"], config["limits"]["inputBytes"])
        families = record[exclusion["recordsKey"]]
        if len(families) != exclusion["count"]:
            raise GenerationStop("actual prior opening exclusion count differs")
        current = {canonical(f["state"]) for f in families}
        if len(current) != exclusion["count"]:
            raise GenerationStop("prior opening exclusions contain canonical duplicates")
        keys.update(current)
    return keys


CONTINUOUS_DUPLICATE_POLICY = "whole-family-stop-on-canonical-collision-placement8+"


def _validate_continuous(config):
    families, targets, limits = config["families"], config["samplePlacements"], config["limits"]
    if (
        config["labelKind"] is not None
        or config["purpose"] != "development_trajectory_roots"
        or not config.get("launchBinding")
        or config.get("H") != 0
        or config.get("samplePassPolicy") != "after-mandatory-pass"
        or config.get("commonPrefixPlacements") != [0, 7]
        or config["duplicatePolicy"] != CONTINUOUS_DUPLICATE_POLICY
    ):
        raise GenerationStop("explicit unlabeled development trajectory binding required")
    namespace = config["namespace"]
    if not namespace.startswith("development/") or "final" in namespace.casefold():
        raise GenerationStop("development namespace required")
    if len(families) != 4 or targets != [16, 32, 48, 56]:
        raise GenerationStop("four finite families and four placement targets required")
    if any(
        set(f) != {"id", "seed", "split"}
        or not isinstance(f["id"], str)
        or not f["id"].startswith(namespace + "/")
        or len(f["id"].encode()) > 124
        or any(not 33 <= ord(c) <= 126 for c in f["id"])
        or "final" in f["id"].casefold()
        or type(f["seed"]) is not int
        or f["split"] != "development"
        for f in families
    ):
        raise GenerationStop("named development families and explicit seeds required")
    if len({f["id"] for f in families}) != 4 or len({f["seed"] for f in families}) != 4:
        raise GenerationStop("duplicate family or seed; no replacement")
    if (
        type(limits["actionsPerTrajectory"]) is not int
        or not 1 <= limits["actionsPerTrajectory"] <= 128
        or any(
            type(limits[k]) is not int or limits[k] <= 0
            for k in ("inputBytes", "evidenceBytes", "retainedBytes")
        )
        or limits["inputBytes"] > 16 * 1024**2
    ):
        raise GenerationStop("fresh bounded trajectory/input/evidence/retention limits required")
    metadata, scopes = config["exposureMetadata"], config["requiredExposureScopes"]
    if (
        config.get("exposureCoverage") != "complete"
        or not isinstance(metadata, list)
        or not metadata
        or not isinstance(scopes, list)
        or not scopes
        or any(not isinstance(s, str) or not s for s in scopes)
        or len(set(scopes)) != len(scopes)
        or any(set(m) != {"scope", "file", "count"} for m in metadata)
        or sorted(m["scope"] for m in metadata) != sorted(scopes)
        or any(type(m["count"]) is not int or m["count"] < 0 for m in metadata)
    ):
        raise GenerationStop("exposure coverage UNKNOWN/incomplete; refuse admission")
    if sum(m["file"]["bytes"] for m in metadata) > limits["inputBytes"]:
        raise GenerationStop("aggregate exposure metadata exceeds input cap")
    if not _matches_ref(__file__, config["source"]):
        raise GenerationStop("generation source differs from Root binding")


def _continuous_exclusions(config):
    """Checked identity-only metadata, never historical state/label/H payloads."""
    keys = set()
    for binding in config["exposureMetadata"]:
        package = _read(binding["file"], config["limits"]["inputBytes"])
        values = package["canonicalKeys"]
        if (
            package.get("coverageStatus") != "complete"
            or package.get("scope") != binding["scope"]
            or package.get("domain") != "canonical-states-placement8+-pass-inclusive"
            or package.get("canonicalSource") != config["canonicalSource"]
            or not isinstance(values, list)
            or len(values) != binding["count"]
        ):
            raise GenerationStop("checked exposure metadata coverage differs or UNKNOWN")
        current = set()
        for value in values:
            if not isinstance(value, str) or len(value) != 128:
                raise GenerationStop("exposure canonical key must encode64 trits")
            try:
                key = bytes.fromhex(value)
            except ValueError as error:
                raise GenerationStop("invalid exposure canonical key") from error
            if len(key) != 64 or any(cell not in (0, 1, 2) for cell in key) or key in current:
                raise GenerationStop("invalid/duplicate exposure canonical key")
            current.add(key)
        keys.update(current)
    return keys


def _continuous_deficits(config, package):
    reached = {root["id"] for f in package["families"] for root in f["roots"]}
    return [
        f"{family['id']}/p{placement}"
        for family in config["families"]
        for placement in config["samplePlacements"]
        if f"{family['id']}/p{placement}" not in reached
    ]


def _continuous(native, config, canonical, excluded, package, evidence, report, cancelled):
    """One bounded Rust-only trajectory per family; no retry, label or search."""
    seen = {}
    package["families"] = [
        {
            **family,
            "roots": [],
            "status": "UNRUN",
            "exposureComponent": None,
            "generationActions": 0,
        }
        for family in config["families"]
    ]
    for family in package["families"]:
        family["status"] = "ATTEMPTED"
        record = {
            "openingFamily": family["id"],
            "seed": family["seed"],
            "complete": False,
            "replay": [],
            "canonicalHistory": [],
        }
        evidence.append(record)
        state = _call(native, "new", cancelled)["state"]
        rng = random.Random(family["seed"])
        record["initialState"] = state
        placement, actions = 0, 0
        while True:
            record["lastState"] = state
            status = _call(native, "status", cancelled, state=state)["status"]
            record["lastStatus"] = status
            if placement >= 8:
                key = canonical(state)
                record["canonicalHistory"].append(
                    {"placement": placement, "action": actions, "canonicalKey": key.hex()}
                )
                if key in excluded or (key in seen and seen[key] != family["id"]):
                    report["collision"] = {
                        "family": family["id"],
                        "placement": placement,
                        "canonicalKey": key.hex(),
                        "priorFamily": seen.get(key),
                        "priorExposure": key in excluded,
                    }
                    raise GenerationStop("whole-family canonical collision; no refill")
                seen[key] = family["id"]
            if status["terminal"]:
                raise GenerationStop(f"early terminal family {family['id']}; no refill")
            if not status["mustPass"]:
                if placement in config["samplePlacements"]:
                    family["roots"].append(
                        {
                            "id": f"{family['id']}/p{placement}",
                            "placement": placement,
                            "state": state,
                            "status": status,
                            "canonicalSHA256": hashlib.sha256(key).hexdigest(),
                            "fixedDepth": min(6, 64 - status["black"] - status["white"]),
                            "rulesStatusBinding": {
                                "family": family["id"],
                                "action": actions,
                                "engine": config["engine"]["binary"],
                            },
                        }
                    )
                if placement == config["samplePlacements"][-1]:
                    family.update(status="COMPLETE", exposureComponent=family["id"])
                    record["complete"] = True
                    break
            if actions >= config["limits"]["actionsPerTrajectory"]:
                raise GenerationStop(f"legal-action cap family {family['id']}; no refill")
            move = None if status["mustPass"] else rng.choice(sorted(status["legalMoves"]))
            request = {"state": state} if move is None else {"state": state, "move": move}
            state = _call(native, "pass" if move is None else "play", cancelled, **request)["state"]
            placement += move is not None
            actions += 1
            family["generationActions"] = actions
            record["replay"].append({"move": move, "placement": placement, "state": state})


def _prepare(native, config, canonical, excluded, result, cancelled):
    rng = random.Random(config["seed"])
    used = set(excluded)
    result["attempts"] = 0
    result["rejections"] = Counter()
    count = len(config["slots"])
    for _ in range(config["limits"]["openingAttempts"]):
        if len(result["records"]) == count:
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
    if len(result["records"]) != count:
        raise GenerationStop(
            f"opening candidate deficit: {count - len(result['records'])}; no labels generated"
        )


def _frozen_openings(config, canonical, excluded):
    frozen = _read(config["openings"], config["limits"]["inputBytes"])
    records = frozen["records"]
    if (
        frozen.get("complete") is not True
        or frozen.get("stage") != "openings"
        or frozen.get("seed") != config["seed"]
        or frozen.get("outcomeLabels") is not False
        or len(records) != len(config["slots"])
    ):
        raise GenerationStop("Root must freeze all actual states/splits before any labels")
    for field in (
        "source",
        "engine",
        "canonicalSource",
        "openingExclusions",
        "labelKind",
        "samplePlacements",
        "duplicatePolicy",
        "namespace",
    ):
        if frozen.get(field) != config[field]:
            raise GenerationStop("frozen opening source/exclusion/policy binding changed")
    if (
        config.get("purpose") == "native_evaluator_comparison"
        and frozen.get("purpose") != config["purpose"]
    ):
        raise GenerationStop("frozen opening purpose differs")
    if (
        config["labelKind"] == "teacherEstimate"
        and frozen.get("samplePassPolicy") != config["samplePassPolicy"]
    ):
        raise GenerationStop("frozen mandatory-pass policy changed")
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


def _play_game(
    native,
    opening,
    evidence,
    cancelled,
    *,
    label_kind="gameOutcome",
    sample_placements=tuple(range(8, 61, 4)),
):
    state = _call(native, "new", cancelled)["state"]
    placements = 0
    samples = []
    if label_kind == "teacherEstimate":
        evidence["observations"] = samples
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
            if label_kind == "teacherEstimate":
                return samples
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
            and placements in sample_placements
            and placements != last_sample
            and not (label_kind == "teacherEstimate" and status["mustPass"])
        ):
            if label_kind == "gameOutcome":
                samples.append((placements, state))
            else:
                samples.append(
                    {
                        "placement": placements,
                        "split": opening["split"],
                        "legalMoves": status["legalMoves"],
                        "row": {
                            "gameId": opening["gameId"],
                            "openingFamily": opening["openingFamily"],
                            "state": state,
                        },
                    }
                )
            last_sample = placements
        if (
            label_kind == "teacherEstimate"
            and placements >= max(sample_placements)
            and not status["mustPass"]
        ):
            evidence.update(complete=True, stopReason="observation-schedule-complete")
            return samples
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


def _deduplicate(samples, families, canonical, *, full_records=False):
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
    return [s if full_records else s["row"] for s in kept], {
        "crossSplitExcluded": cross,
        "withinSplitExcluded": within,
        "retainedByFamily": {family: counts[family] for family in sorted(families)},
        "zeroSampleFamilies": sorted(f for f in families if counts[f] == 0),
    }


def _trajectory_samples(
    native, config, frozen, evidence, observations, canonical, report, cancelled
):
    records = []
    active = [slot for slot in frozen if slot["split"] != "H"]
    report.update(
        heldoutFamilies=[slot["openingFamily"] for slot in frozen if slot["split"] == "H"],
        trajectoriesPlanned=len(active),
        trajectoriesComplete=0,
    )
    try:
        for opening in active:
            game = {
                "gameId": opening["gameId"],
                "openingFamily": opening["openingFamily"],
                "split": opening["split"],
                "openingState": opening["state"],
                "complete": False,
                "replay": [],
            }
            evidence.append(game)
            try:
                returned = _play_game(
                    native,
                    opening,
                    game,
                    cancelled,
                    label_kind="teacherEstimate",
                    sample_placements=config["samplePlacements"],
                )
            except Exception as error:
                game["failure"] = {
                    "kind": getattr(error, "kind", type(error).__name__),
                    "message": str(error),
                }
                raise
            records.extend(returned)
            observations.extend(returned)
            report["trajectoriesComplete"] += 1
    finally:
        counts = Counter(s["row"]["openingFamily"] for s in records)
        report.update(
            trajectoriesAttempted=len(evidence),
            trajectoriesUnrun=len(active) - len(evidence),
            rawObservations=len(records),
            rawDeficitByFamily={s["openingFamily"]: 8 - counts[s["openingFamily"]] for s in active},
        )
    kept, duplicates = _deduplicate(
        records, {x["openingFamily"] for x in active}, canonical, full_records=True
    )
    observations[:] = kept
    report.update(
        duplicates=duplicates,
        observationsScheduled=len(kept),
        observationDeficit=8 * len(active) - len(kept),
        observationsByFamily=duplicates["retainedByFamily"],
    )


def _frozen_observations(config, frozen, canonical):
    package = _read(config["observations"], config["limits"]["inputBytes"])
    if (
        package.get("complete") is not True
        or package.get("openings") != config["openings"]
        or package.get("outcomeLabels") is not False
        or package.get("source") != config["source"]
        or package.get("duplicatePolicy") != config["duplicatePolicy"]
        or package.get("seed") != config["seed"]
        or package.get("samplePassPolicy") != config["samplePassPolicy"]
        or package.get("samplePlacements") != config["samplePlacements"]
    ):
        raise GenerationStop(
            "Root must freeze complete unlabeled observations before teacher results"
        )
    slots = {slot["gameId"]: slot for slot in frozen}
    records = package["records"]
    if len(records) > 896 or len(records) > config["limits"]["teacherAttempts"]:
        raise GenerationStop("teacher schedule exceeds896 T/V observations or attempt cap")
    used, counts, placements = set(), Counter(), set()
    for record in records:
        row = record["row"]
        if set(row) != {"gameId", "openingFamily", "state"}:
            raise GenerationStop("observation must not contain labels/teacher results")
        slot = slots[row["gameId"]]
        key = canonical(row["state"])
        if (
            slot["split"] == "H"
            or record["split"] != slot["split"]
            or row["openingFamily"] != slot["openingFamily"]
            or type(record["placement"]) is not int
            or record["placement"] not in config["samplePlacements"]
            or key in used
            or sum(cell != 0 for cell in row["state"]["board"]) - 4 != record["placement"]
            or (row["gameId"], record["placement"]) in placements
        ):
            raise GenerationStop("heldout/duplicate/wrong-split observation refused")
        used.add(key)
        placements.add((row["gameId"], record["placement"]))
        counts[row["gameId"]] += 1
        if counts[row["gameId"]] > 8:
            raise GenerationStop("more than8 observations for one family")
    return records


def run(config_ref, output, *, cancelled=lambda: False):
    """Issue exactly one explicit stage; enclosing standard job owns resource controls."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    config = {}
    report = {
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
        "duplicatePolicy": DUPLICATE_POLICY,
    }
    openings = {
        "stage": "openings",
        "complete": False,
        "outcomeLabels": False,
        "records": [],
        "source": report["source"],
        "config": config_ref,
    }
    continuous = {"families": [], "H": 0}
    games, samples, rows, observations, requests = [], [], [], [], []
    session, process = {}, None
    scheduled = None
    validated = False
    try:
        config = _read(config_ref, 256 * 1024)
        if config.get("stage") == "continuous-development":
            report.update(
                rootsPlanned=16,
                rootsComplete=0,
                unrunRoots=16,
                exposureCoverage="UNKNOWN",
                duplicatePolicy=CONTINUOUS_DUPLICATE_POLICY,
            )
        _validate(config)
        validated = True
        report.update(
            stage=config["stage"],
            seed=config["seed"],
            labelKind=config["labelKind"],
            limits=config["limits"],
            engine=config["engine"],
        )
        for field in (
            "seed",
            "engine",
            "canonicalSource",
            "openingExclusions",
            "labelKind",
            "samplePlacements",
            "duplicatePolicy",
            "namespace",
        ):
            openings[field] = config[field]
        if config["labelKind"] == "teacherEstimate":
            openings["samplePassPolicy"] = config["samplePassPolicy"]
        if config["purpose"] == "native_evaluator_comparison":
            openings["purpose"] = config["purpose"]
        canonical = _canonical(config)
        excluded = (
            _continuous_exclusions(config)
            if config["stage"] == "continuous-development"
            else _excluded_keys(config, canonical)
        )
        if config["stage"] == "continuous-development":
            report.update(exposureCoverage="complete", duplicatePolicy=CONTINUOUS_DUPLICATE_POLICY)
        frozen = (
            _frozen_openings(config, canonical, excluded)
            if config["stage"] not in ("openings", "continuous-development")
            else None
        )
        scheduled = (
            _frozen_observations(config, frozen, canonical)
            if config["stage"] == "teacher"
            else None
        )
        if scheduled is not None:
            report.update(
                teacherScheduled=len(scheduled),
                teacherAttemptUpper=config["limits"]["teacherAttempts"],
            )
        checked_spec(config["engine"])
        if config["stage"] == "teacher":
            from .teacher import collect

            if len(scheduled) > config["limits"]["rows"]:
                raise GenerationStop("frozen schedule exceeds fresh row cap before teacher init")
            if not _matches_ref(
                config["teacher"]["adapterSource"]["path"], config["teacher"]["adapterSource"]
            ):
                raise GenerationStop("teacher adapter source identity differs")
            report.update(
                teacher=config["teacher"],
                teacherConnectorSource=_ref(Path(__file__).with_name("teacher.py")),
                teacherResponseSource=_ref(Path(__file__).with_name("engines.py")),
                loaderQualification="UNRUN for actual labels: same-tree loader must qualify generated input",
            )
        process = Process(
            config["engine"]["argv"],
            cwd=config["engine"]["cwd"],
            log=output / "protocol.log",
            cancelled=cancelled,
        )
        with process:
            native = Native(process)
            if config["stage"] == "continuous-development":
                _continuous(
                    native, config, canonical, excluded, continuous, games, report, cancelled
                )
            elif config["stage"] == "openings":
                _prepare(native, config, canonical, excluded, openings, cancelled)
            elif config["stage"] == "trajectories":
                _trajectory_samples(
                    native, config, frozen, games, observations, canonical, report, cancelled
                )
            elif config["stage"] == "teacher":
                collect(
                    native, config, scheduled, output, rows, requests, session, cancelled=cancelled
                )
                report["labels"] = "teacherEstimate"
            else:
                report.update(gamesPlanned=len(frozen), unrunGames=len(frozen))
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
        report.update(
            cleanup=process.cleanup if process else None,
            teacherSession=session,
            teacherAttempted=len(requests),
            teacherComplete=len(rows) if requests else 0,
            teacherSearchIssued=sum(r.get("searchAttempted", False) for r in requests),
            teacherUnrun=None if scheduled is None else len(scheduled) - len(requests),
        )
        blobs = {"config.json": _encode(config)}
        stage = config.get("stage") if validated else None
        if stage == "continuous-development":
            deficits = _continuous_deficits(config, continuous)
            report.update(
                rootsPlanned=16,
                rootsComplete=16 - len(deficits),
                rootDeficits=deficits,
                unrunRoots=len(deficits),
            )
            if report["status"] != "complete":
                for family in continuous["families"]:
                    if family["status"] == "ATTEMPTED":
                        family["status"] = "STOP"
            continuous.update(
                stage=stage,
                complete=report["status"] == "complete",
                outcomeLabels=False,
                config=config_ref,
                source=report["source"],
                canonicalSource=config["canonicalSource"],
                exposureMetadata=config["exposureMetadata"],
                exposureCoverage=report.get("exposureCoverage", "UNKNOWN"),
                duplicatePolicy=CONTINUOUS_DUPLICATE_POLICY,
                commonPrefixPlacements=config["commonPrefixPlacements"],
            )
            blobs["roots.json"] = _encode(continuous)
        elif stage == "openings":
            openings["complete"] = report["status"] == "complete"
            blobs["openings.json"] = _encode(openings)
        elif stage == "trajectories":
            blobs["observations.json"] = _encode(
                {
                    "complete": report["status"] == "complete",
                    "outcomeLabels": False,
                    "openings": config["openings"],
                    "source": report["source"],
                    "duplicatePolicy": DUPLICATE_POLICY,
                    "seed": config["seed"],
                    "samplePassPolicy": config["samplePassPolicy"],
                    "samplePlacements": config["samplePlacements"],
                    "records": observations,
                }
            )
        if stage is not None and stage != "openings":
            blobs["generation-evidence.json"] = _encode(
                {
                    "config": config_ref,
                    "source": report["source"],
                    "engine": config.get("engine"),
                    "seed": config.get("seed"),
                    "games": games,
                    "requests": requests,
                }
            )
        if stage in ("games", "teacher"):
            name = "training.jsonl" if report["status"] == "complete" else "training.partial.jsonl"
            blobs[name] = b"".join(_encode(row) for row in rows)
        limits = config["limits"] if validated else {}
        input_bytes = sum(len(_encode(row)) for row in rows)
        root_bytes = len(blobs.get("roots.json", b""))
        if stage == "continuous-development":
            report["rootBytes"] = root_bytes
        evidence_bytes = len(blobs.get("generation-evidence.json", b""))

        def bound_failure(message):
            fact = {"kind": "bounds", "message": message}
            report["status"] = "STOP"
            if report["failure"] is None:
                report["failure"] = fact
            else:
                report.setdefault("secondaryFailures", []).append(fact)

        if validated and (
            len(rows) > limits.get("rows", 0)
            or input_bytes + root_bytes > limits["inputBytes"]
            or evidence_bytes > limits["evidenceBytes"]
        ):
            bound_failure("row/input/evidence limit; no further work")
        report.update(
            rows=len(rows), rowBytes=input_bytes, evidenceBytes=evidence_bytes, checkpointsCreated=0
        )
        existing = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        upper = existing + sum(len(b) for b in blobs.values()) + len(_encode(report)) + 65536
        if validated and upper > limits["retainedBytes"]:
            bound_failure("fresh retained output limit")
            report["notRetained"] = {}
            # Retain configuration/attempt failure evidence ahead of training rows.
            for name in sorted(
                blobs, key=lambda n: (n in ("config.json", "generation-evidence.json"), n)
            ):
                if upper <= limits["retainedBytes"]:
                    break
                report["notRetained"][name] = {
                    "bytes": len(blobs[name]),
                    "sha256": hashlib.sha256(blobs[name]).hexdigest(),
                }
                del blobs[name]
                upper = existing + sum(map(len, blobs.values())) + len(_encode(report)) + 65536
        if report["status"] != "complete" and "training.jsonl" in blobs:
            blobs["training.partial.jsonl"] = blobs.pop("training.jsonl")
        if report["status"] != "complete":
            for name in ("openings.json", "observations.json", "roots.json"):
                if name in blobs:
                    package = json.loads(blobs[name])
                    package["complete"] = False
                    blobs[name] = _encode(package)
        report.update(
            retainedUpperBytes=upper,
            remainingRetainedBytes=max(0, limits.get("retainedBytes", 0) - upper),
        )
        for name, blob in blobs.items():
            (output / name).write_bytes(blob)
        (output / "result.json").write_bytes(_encode(report))
    return report
