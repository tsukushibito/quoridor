"""Finite paired games controlled exclusively by the Rust rules service."""

import time

from .engines import io_deadline
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
    state = None
    actor = "rules"
    try:
        state = rules.request("new", deadline=io_deadline())["state"]
        for color, player in players.items():
            actor = str(color)
            player.reset(deadline=io_deadline())
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
                players[side].prepare(state, deadline=io_deadline())
                start = time.monotonic()
                move = players[side].choose(state, deadline=start + (time_ms + overhead_ms) / 1000)
                elapsed = (time.monotonic() - start) * 1000
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
            result["moves"].append(
                {"side": side, "move": move, "wallMs": elapsed, "opening": False}
            )
            if move is not None and hasattr(players[side], "last_search"):
                result["moves"][-1]["search"] = players[side].last_search
            for color, player in players.items():
                # genmove already applied the acting GTP engine's own placement.
                if color != side or move is None:
                    actor = str(color)
                    player.observe(side, move, deadline=io_deadline())
        else:
            raise EngineError("rules", "Rust game exceeded Othello transition bound")
    except EngineError as error:
        result["failure"] = {"actor": actor, "kind": error.kind, "message": str(error)}
    result["state"] = state
    return result


def paired(rules, candidate, opponent, families, *, time_ms=1000, overhead_ms=100):
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
            )
            yield result
            if result["failure"] is not None:
                return


def summarize(results, planned):
    complete = [x for x in results if x["completed"]]
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
