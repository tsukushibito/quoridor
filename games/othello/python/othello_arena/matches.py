"""Finite paired games controlled exclusively by the Rust rules service."""

from collections import Counter
import hashlib
import math
import random
import time

from .engines import (
    io_deadline,
    validate_native_search,
    validate_full_search,
    validate_external_search,
)
from .protocol import EngineError


def game(
    rules,
    players,
    opening,
    *,
    family,
    candidate_side,
    time_ms=1000,
    overhead_ms=100,
    expected_opening_state=None,
    retain_setup=False,
):
    result = {
        "family": family,
        "candidateSide": candidate_side,
        "completed": False,
        "moves": [],
        "failure": None,
        "blackMinusWhite": None,
        "candidateScore": None,
    }
    whole_start = time.monotonic()
    if retain_setup:
        result["resetMs"] = {}
    state = None
    actor = "rules"
    try:
        state = rules.request("new", deadline=io_deadline())["state"]
        for color, player in players.items():
            actor = str(color)
            reset_start = time.monotonic()
            try:
                player.reset(deadline=io_deadline())
            finally:
                if retain_setup:
                    result["resetMs"][str(color)] = (time.monotonic() - reset_start) * 1000
        opening_start = time.monotonic()
        for move in opening:
            actor = "rules"
            side = state["toMove"]
            state = rules.request(
                "pass" if move is None else "play",
                deadline=io_deadline(),
                **({"state": state} if move is None else {"state": state, "move": move}),
            )["state"]
            for color, player in players.items():
                actor = str(color)
                player.observe(side, move, deadline=io_deadline())
            result["moves"].append({"side": side, "move": move, "opening": True})
        if retain_setup:
            result["openingReplayWallMs"] = (time.monotonic() - opening_start) * 1000
        if expected_opening_state is not None and state != expected_opening_state:
            actor = "rules"
            raise EngineError("opening", "Rust replay differs from frozen external opening state")
        # Othello has at most 60 placements and a pass between placements.
        for _ in range(121):
            actor = "rules"
            status = rules.request("status", state=state, deadline=io_deadline())["status"]
            result["status"] = status
            if status["terminal"]:
                difference = status["black"] - status["white"]
                candidate_difference = difference * (1 if candidate_side == 1 else -1)
                result.update(
                    completed=True,
                    blackMinusWhite=difference,
                    candidateScore=1
                    if candidate_difference > 0
                    else 0
                    if candidate_difference < 0
                    else 0.5,
                )
                break
            side = state["toMove"]
            actor = str(side)
            if status["mustPass"]:
                move = None
                elapsed = 0
            else:
                prepare_start = time.monotonic()
                players[side].prepare(state, deadline=io_deadline())
                prepare_ms = (time.monotonic() - prepare_start) * 1000
                start = time.monotonic()
                entry = {"side": side, "move": None, "wallMs": None, "opening": False}
                if retain_setup:
                    entry["prepareMs"] = prepare_ms
                result["moves"].append(entry)
                if hasattr(players[side], "last_search"):
                    players[side].last_search = None
                try:
                    move = players[side].choose(
                        state, deadline=start + (time_ms + overhead_ms) / 1000
                    )
                    entry["move"] = move
                finally:
                    elapsed = (time.monotonic() - start) * 1000
                    entry["wallMs"] = elapsed
                    if getattr(players[side], "last_search", None) is not None:
                        entry["search"] = players[side].last_search
                if elapsed > time_ms + overhead_ms:
                    raise EngineError("timeout", f"move wall {elapsed:.3f}ms")
                if type(move) is not int or move not in status["legalMoves"]:
                    raise EngineError("illegal", f"illegal engine move {move!r}")
            actor = "rules"
            state = rules.request(
                "pass" if move is None else "play",
                deadline=io_deadline(),
                **({"state": state} if move is None else {"state": state, "move": move}),
            )["state"]
            if move is None:
                result["moves"].append(
                    {
                        "side": side,
                        "move": None,
                        "wallMs": elapsed,
                        "opening": False,
                        "forcedPass": True,
                    }
                )
            for color, player in players.items():
                # genmove already applied the acting GTP engine's own placement.
                if color != side or move is None:
                    actor = str(color)
                    player.observe(side, move, deadline=io_deadline())
        else:
            raise EngineError("rules", "Rust game exceeded Othello transition bound")
    except (EngineError, OSError, ValueError, KeyError, TypeError) as error:
        result["failure"] = {
            "actor": actor,
            "kind": getattr(error, "kind", type(error).__name__),
            "message": str(error),
        }
    result["state"] = state
    if retain_setup:
        result["wholeWallMs"] = (time.monotonic() - whole_start) * 1000
    return result


def paired(
    rules, candidate, opponent, families, *, time_ms=1000, overhead_ms=100, retain_setup=False
):
    """Yield every attempted result; stop on failure without refilling the schedule."""
    for family in families:
        for side in (1, 2):
            players = {side: candidate, 3 - side: opponent}
            result = game(
                rules,
                players,
                family["moves"],
                family=family["id"],
                candidate_side=side,
                time_ms=time_ms,
                overhead_ms=overhead_ms,
                expected_opening_state=family.get("state"),
                retain_setup=retain_setup,
            )
            yield result
            if result["failure"] is not None:
                return


def summarize(results, planned):
    complete = [
        x
        for x in results
        if x["completed"] is True
        and not x.get("failure")
        and type(x.get("candidateScore")) in (int, float)
        and x["candidateScore"] in (0, 0.5, 1)
    ]
    scores = [x["candidateScore"] for x in complete]
    points = sum(scores)
    unknown = planned - len(complete)
    return {
        "planned": planned,
        "attempted": len(results),
        "completed": len(complete),
        "failures": [x["failure"] for x in results if x["failure"]],
        "unrun": planned - len(results),
        "wins": scores.count(1),
        "draws": scores.count(0.5),
        "losses": scores.count(0),
        "points": points,
        "scoreRateBoundsIncludingUnknown": [points / planned, (points + unknown) / planned],
        "superiorityClaim": False,
    }


def _normal_comparison_game(result, family, evaluations, *, evidence_kind="legacy-native"):
    """Audit retained Rust terminal truth and already-bound native response evidence."""
    try:
        side, difference, status = (
            result["candidateSide"],
            result["blackMinusWhite"],
            result["status"],
        )
        if (
            result["completed"] is not True
            or type(side) is not int
            or side not in (1, 2)
            or result.get("failure") is not None
            or type(difference) is not int
            or not -64 <= difference <= 64
            or status["terminal"] is not True
            or any(
                type(status[k]) is not int or not 0 <= status[k] <= 64 for k in ("black", "white")
            )
            or status["black"] + status["white"] > 64
            or difference != status["black"] - status["white"]
        ):
            return False
        oriented = difference * (1 if side == 1 else -1)
        score = 1 if oriented > 0 else 0 if oriented < 0 else 0.5
        if type(result["candidateScore"]) not in (int, float) or result["candidateScore"] != score:
            return False
        moves, opening = result["moves"], family["moves"]
        if not len(opening) <= len(moves) <= 121:
            return False
        if [m["move"] for m in moves[: len(opening)]] != opening:
            return False
        for index, move in enumerate(moves):
            if type(move["side"]) is not int or move["side"] not in (1, 2):
                return False
            if move["opening"] is not (index < len(opening)):
                return False
            if move["opening"]:
                continue
            wall = move["wallMs"]
            if type(wall) not in (int, float) or not math.isfinite(wall) or not 0 <= wall <= 1100:
                return False
            if move["move"] is not None:
                if type(move["move"]) is not int:
                    return False
                expected = evaluations["candidate" if move["side"] == side else "opponent"]
                if evidence_kind == "fullsearch-external":
                    if move["side"] == side:
                        observed = validate_full_search(move["search"], expected["identity"])[
                            "move"
                        ]
                    else:
                        observed = validate_external_search(move["search"], expected, move["side"])
                elif evidence_kind == "legacy-native":
                    validate_native_search(move["search"], expected)
                    observed = move["search"]["move"]
                else:
                    return False
                if move["move"] != observed:
                    return False
            elif move.get("forcedPass") is not True or wall != 0 or "search" in move:
                return False
        return True
    except (KeyError, TypeError, ValueError, EngineError):
        return False


def comparison_summary(
    results,
    families,
    evaluations,
    *,
    run_qualified,
    opponent_id,
    evidence_kind="legacy-native",
    shared_bootstrap=None,
):
    """CI uses ALL original32 games/16 family means, never a completed-pair subset.

    External development uses one explicitly seeded shared PCG64 table
    and NumPy linear quantiles. Legacy same-native evidence retains its own method:
    Python random.Random (MT19937), seed2026102203;10000 independent resamples
    of16 family means with replacement via randrange(16). Percentiles use linear
    interpolation at sorted index (n-1)*p for p=.025/.975 (R7 convention).
    """
    family_ids = [f["id"] for f in families]
    plan_valid = (
        len(family_ids) == 16
        and len(set(family_ids)) == 16
        and evidence_kind in ("legacy-native", "fullsearch-external")
        and (
            evidence_kind != "fullsearch-external"
            or (
                evaluations.get("candidate", {}).get("protocol") == "fullsearch_jsonl"
                and evaluations.get("opponent", {}).get("protocol") in ("gtp", "fixed_jsonl")
            )
        )
    )
    by_id = {f["id"]: f for f in families}
    slots = [(r.get("family"), r.get("candidateSide")) for r in results]
    counts = Counter(slots)
    known, invalid, known_results = {}, [], []
    for result, slot in zip(results, slots, strict=True):
        family, side = slot
        if (
            not plan_valid
            or opponent_id is None
            or result.get("opponent") != opponent_id
            or family not in by_id
            or type(side) is not int
            or side not in (1, 2)
            or counts[slot] != 1
            or not _normal_comparison_game(
                result, by_id[family], evaluations, evidence_kind=evidence_kind
            )
        ):
            invalid.append(
                {"family": family, "candidateSide": side, "failure": result.get("failure")}
            )
        else:
            known[slot] = result["candidateScore"]
            known_results.append(result)
    points, unknown = sum(known.values()), 32 - len(known)
    eligible = (
        plan_valid
        and run_qualified is True
        and len(results) == 32
        and len(known) == 32
        and not invalid
    )
    summary = summarize(known_results, 32)
    summary.update(
        {
            "planned": 32,
            "plannedPairs": 16,
            "attempted": len(results),
            "knownGames": len(known),
            "unknownGames": unknown,
            "unrun": max(0, 32 - len(results)),
            "knownPoints": points,
            "scoreRateBoundsIncludingUnknown": [points / 32, (points + unknown) / 32],
            "failures": [r["failure"] for r in results if r.get("failure")],
            "invalidResults": invalid,
            "ciEligible": eligible,
            "acceptance": None,
            "conclusion": "unqualified",
            "superiorityClaim": False,
        }
    )
    if evidence_kind == "fullsearch-external":
        summary["gamesQualifiedForCI"] = eligible
        summary["familyBootstrap95"] = None
    if not eligible:
        return summary
    means = [(known[(family, 1)] + known[(family, 2)]) / 2 for family in family_ids]
    if evidence_kind == "fullsearch-external":
        summary["ciEligible"] = False
        if shared_bootstrap is None:
            summary["statisticsStatus"] = "shared-table-unbound"
            return summary
        low, high = _shared_family_interval(means, family_ids, shared_bootstrap)
        conclusion = (
            "supported_in_finite_dev_condition"
            if low > 0.5
            else "unsupported"
            if high < 0.5
            else "unresolved"
        )
        summary.update(
            ciEligible=True,
            statisticsStatus="complete",
            familyMeanScore=sum(means) / 16,
            familyMeans=dict(zip(family_ids, means, strict=True)),
            familyBootstrap95=[low, high],
            bootstrap=shared_bootstrap["metadata"],
            conclusion=conclusion,
            acceptance=True if low > 0.5 else False if high < 0.5 else None,
        )
        return summary
    rng = random.Random(2026102203)
    samples = sorted(sum(means[rng.randrange(16)] for _ in range(16)) / 16 for _ in range(10000))

    def percentile(p):
        index = (len(samples) - 1) * p
        lower = int(index)
        return samples[lower] + (samples[min(lower + 1, len(samples) - 1)] - samples[lower]) * (
            index - lower
        )

    low, high = percentile(0.025), percentile(0.975)
    conclusion = (
        "supported_in_finite_dev_condition"
        if low > 0.5
        else "unsupported"
        if high < 0.5
        else "unresolved"
    )
    summary.update(
        familyMeanScore=sum(means) / 16,
        familyMeans=dict(zip(family_ids, means, strict=True)),
        familyBootstrap95=[low, high],
        bootstrap={
            "seed": 2026102203,
            "resamples": 10000,
            "unit": "16 original family means, both colors per family",
            "rng": "Python random.Random MT19937; randrange(16) with replacement",
            "percentile": "linear sorted index (10000-1)*p, p=0.025/0.975 (R7)",
        },
        conclusion=conclusion,
        acceptance=True if low > 0.5 else False if high < 0.5 else None,
    )
    return summary


def family_bootstrap_table(family_ids, path, *, seed=2026102302064):
    """One future-runtime PCG64 table shared by both external opponents."""
    if type(seed) is not int or seed < 0:
        raise ValueError("shared bootstrap seed must be an explicit nonnegative integer")
    import numpy as np

    if len(family_ids) != 16 or len(set(family_ids)) != 16:
        raise ValueError("shared bootstrap requires the original16 ordered family IDs")
    indices = (
        np.random.Generator(np.random.PCG64(seed))
        .integers(0, 16, size=(10000, 16), dtype=np.int64)
        .astype("<i8", copy=False)
    )
    raw = indices.tobytes(order="C")
    path.write_bytes(raw)
    metadata = {
        "seed": seed,
        "rng": "NumPy Generator(PCG64)",
        "numpyVersion": np.__version__,
        "indexShape": list(indices.shape),
        "indexDtype": indices.dtype.str,
        "indexSHA256": hashlib.sha256(raw).hexdigest(),
        "indexFile": str(path),
        "indexBytes": len(raw),
        "indexOrder": "C",
        "familyOrder": list(family_ids),
        "resamples": 10000,
        "unit": "16 family means, both colors per family",
        "percentile": "numpy.quantile(method='linear'), tails .025/.975",
        "sharedAcrossOpponents": True,
    }
    return {"indices": indices, "metadata": metadata}


def _shared_family_interval(means, family_ids, shared):
    """Consume the same owner-created indices; never create a per-opponent RNG."""
    import numpy as np

    metadata, indices = shared["metadata"], shared["indices"]
    if (
        metadata["familyOrder"] != family_ids
        or type(metadata["seed"]) is not int
        or metadata["seed"] < 0
        or metadata["indexShape"] != [10000, 16]
        or metadata["indexDtype"] != "<i8"
        or tuple(indices.shape) != (10000, 16)
        or indices.dtype.str != "<i8"
        or metadata["sharedAcrossOpponents"] is not True
    ):
        raise ValueError("shared family index contract differs")
    samples = np.asarray(means, dtype=float)[indices].mean(axis=1)
    low, high = np.quantile(samples, [0.025, 0.975], method="linear")
    return float(low), float(high)
