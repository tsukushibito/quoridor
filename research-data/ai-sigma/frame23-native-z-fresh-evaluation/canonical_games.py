"""Sealed outcome sidecar mapping; no change to native raw records or teacher values."""

import argparse
import hashlib
import json
from pathlib import Path

RUNTIME_SHA = "66d06e2332255a01ead0d0033ecaddba0b4b812bbfc8220c4dbb5bc2726e1a29"


def normalize(game):
    outcome = game["outcome"]
    status = outcome["status"]
    winner = outcome["winner"]
    assert status in ("goal", "draw", "unknown"), "UNKNOWN_STATUS_CASING"
    assert winner is None or (type(winner) is int and winner in (0, 1)), "WINNER_ENUM"
    if status == "goal":
        assert winner is not None and outcome["reason"] is None, "GOAL_REASON"
        reason, eligible = "GOAL", True
    elif status == "draw":
        assert winner is None and outcome["reason"] is None, "DRAW_PROOF"
        reason = (
            "RULEA_200_PLY_DRAW"
            if outcome["plies"] >= 200
            else "RULEA_NO_HISTORY_LEGAL_DRAW"
        )
        eligible = True
    else:
        assert isinstance(outcome["reason"], str) and outcome["reason"], (
            "UNKNOWN_REASON"
        )
        reason, eligible = "UNKNOWN:" + outcome["reason"], False
    if status != "unknown":
        assert len(outcome["moves"]) == outcome["plies"], "FULL_PREFIX_LENGTH"
    return {
        "canonical_family": game["canonical_family"],
        "gameUID": game["native_family"],
        "native_family": game["native_family"],
        "opening_side": game["opening_side"],
        "cohort": game["cohort"],
        "cohort_pair": game["cohort_pair"],
        "status": status,
        "terminal_reason": reason,
        "winner_absolute0or1": winner,
        "eligible_terminal_z": eligible,
        "terminal_z_rule": "unknown None; draw0; goal+1 iff row.side==winner_absolute0or1+1 else-1",
        "terminal_full_prefix": outcome["moves"],
        "terminal_prefix_complete": status != "unknown",
        "unknown_moves_scope": "registered opening or partial source moves; do not infer terminal/fullhistory",
        "terminal_total_plies": outcome["plies"],
        "raw_reason": outcome["reason"],
        "source_binding_runtime_SHA": RUNTIME_SHA,
        "proof_scope": "native terminal branch precedes explicit ply_cap_before_terminal UNKNOWN; raw source/result retained",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.input)
    data = json.loads(source.read_text())
    assert data["schema"] == "native-z-fresh-evaluation-sealed-games-v1"
    output = {
        "schema": "native-z-fresh-evaluation-canonical-terminated-games-v1",
        "source": str(source),
        "source_SHA": hashlib.sha256(source.read_bytes()).hexdigest(),
        "block": data["block"],
        "games": [normalize(game) for game in data["games"]],
        "sealed": True,
        "NN": 0,
    }
    with Path(args.output).open("x") as stream:
        stream.write(json.dumps(output, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
