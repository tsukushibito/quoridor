"""One explicit symmetric-stock prefix, then reachability in an already saved graph."""

from collections import Counter, deque
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys


def ref(path):
    data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "mode": format(path.stat().st_mode & 0o777, "04o"),
    }


def main(root):
    result_path = root / "full-collection-v1/result.json"
    result = json.loads(result_path.read_text())
    candidate = result["globally_first_D"]
    graph_path = Path(candidate["graph"]["path"])
    assert ref(graph_path) == candidate["graph"]
    data = graph_path.read_bytes()
    mask = candidate["first"]["mask"]
    assert mask == 67882 and mask.bit_count() == 6
    rows, offset = {}, 28
    for raw in range(1250):
        status, degree, rank, choice = struct.unpack_from("<BBHH", data, offset)
        offset += 6
        edges = []
        for _ in range(degree):
            action, child = struct.unpack_from("<BH", data, offset)
            offset += 3
            edges.append((action, child))
        rows[raw] = {"status": status, "rank": rank, "choice": choice, "edges": edges}
    assert offset == len(data)
    module_spec = importlib.util.spec_from_file_location(
        "reference405", root / "reference.py"
    )
    rules = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(rules)
    reference_ref = ref(root / "reference.py")
    assert (
        reference_ref["sha256"]
        == "34b04d533501813a4f80bc85500060621aeed862839320babdee500a18afd5d5"
    )
    # This one declared four-pawn-move prelude avoids the trapped final c1 start.
    pawns, turn, stocks, placed = [(0, 2), (4, 2)], 0, [3, 3], 0
    history, actions = [], []

    def record():
        history.append((placed, tuple(pawns), turn, tuple(stocks)))

    def move(destination):
        nonlocal turn
        adjacent = rules.board(5, placed)
        assert destination in rules.actions(adjacent, pawns[turn], pawns[1 - turn])
        assert destination[0] != (4 if turn == 0 else 0), "no terminal before candidate"
        actions.append(
            {
                "kind": "pawn",
                "player": turn,
                "from": pawns[turn],
                "to": destination,
                "wall_mask": placed,
                "stocks_before": list(stocks),
            }
        )
        pawns[turn] = destination
        turn = 1 - turn
        record()

    record()
    for destination in [(1, 2), (3, 2), (1, 3), (2, 2)]:
        move(destination)
    assert pawns == [(1, 3), (2, 2)] and turn == 0
    # Check only these six fixed actual wall placements, not a placement sweep.
    for bit in [1, 3, 5, 8, 11, 16]:
        assert stocks[turn] > 0 and mask & (1 << bit) and not placed & (1 << bit)
        after = placed | (1 << bit)
        adjacent = rules.board(5, after)  # authoritative reference collision/edge rules
        for player, goal_row in [(0, 4), (1, 0)]:
            assert pawns[player] in rules.reachable(
                adjacent, [(goal_row, col) for col in range(5)]
            )
        actions.append(
            {
                "kind": "wall",
                "player": turn,
                "bit": bit,
                "mask_before": placed,
                "mask_after": after,
                "stocks_before": list(stocks),
            }
        )
        placed = after
        stocks[turn] -= 1
        turn = 1 - turn
        record()
    assert placed == mask and stocks == [0, 0] and turn == 0
    start = (
        (pawns[0][0] * 5 + pawns[0][1]) * 50
        + (pawns[1][0] * 5 + pawns[1][1]) * 2
        + turn
    )
    assert start == 424 and rows[start]["status"] != 255
    queue, previous, target = deque([start]), {start: None}, None
    while queue:
        raw = queue.popleft()
        if rows[raw]["status"] == 0:
            target = raw
            break
        for action, child in rows[raw]["edges"]:
            if child != 65535 and child not in previous:
                previous[child] = (raw, action)
                queue.append(child)
    assert target is not None, "no claimed prefix if bounded saved graph cannot reach D"
    path, raw = [], target
    while previous[raw] is not None:
        parent, action = previous[raw]
        path.append({"raw_before": parent, "action": action, "raw_after": raw})
        raw = parent
    path.reverse()
    for step in path:
        assert (
            step["raw_before"]
            == (pawns[0][0] * 5 + pawns[0][1]) * 50
            + (pawns[1][0] * 5 + pawns[1][1]) * 2
            + turn
        )
        move(divmod(step["action"], 5))
        assert (
            step["raw_after"]
            == (pawns[0][0] * 5 + pawns[0][1]) * 50
            + (pawns[1][0] * 5 + pawns[1][1]) * 2
            + turn
        )
    counts = Counter(history)
    assert max(counts.values()) == 1 and rows[target]["status"] == 0
    cycle, seen, raw = [], {}, target
    while raw not in seen:
        seen[raw] = len(cycle)
        row = rows[raw]
        assert row["status"] == 0 and row["rank"] == 0
        outgoing = [
            {"action": action, "child": child, "child_status": rows[child]["status"]}
            for action, child in row["edges"]
        ]
        assert all(child["child_status"] != 2 for child in outgoing)
        assert rows[row["choice"]]["status"] == 0
        cycle.append(
            {
                "raw_state": raw,
                "P0_cell": raw // 50,
                "P1_cell": (raw // 2) % 25,
                "turn": raw % 2,
                "all_legal_edges": outgoing,
                "chosen_child": row["choice"],
            }
        )
        raw = row["choice"]
    output = {
        "status": "EXPLICIT_PREFIX_AND_SAVED_D_STRATEGY_VERIFIED",
        "source_census": ref(result_path),
        "saved_graph": candidate["graph"],
        "reference_rules": reference_ref,
        "wallcount": 6,
        "symmetric_initial_stock_m": 3,
        "initial_pawns": [2, 22],
        "initial_turn": 0,
        "walls_first_from_standard_starts": "NOT_APPLICABLE: final mask traps P0 c1; final raw144 is inactive",
        "initial_fixed_wall_raw144_status": rows[144]["status"],
        "construction": "One explicit four-pawn prelude, six alternating fixed wall placements, then BFS only in saved fullgraph; no newWDL/layout/native campaign",
        "actions": actions,
        "history_keys": history,
        "max_prefix_occurrence": max(counts.values()),
        "saved_graph_nonterminal_path": path,
        "D_raw_state": target,
        "D_pawns": pawns,
        "D_turn": turn,
        "D_strategy_trace": cycle,
        "D_cycle_start": seen[raw],
        "D_cycle_repeat_state": raw,
        "no_new_solver_or_layout_calls": True,
        "scope": "5x5, initial3walls each, goalpriority/standardjump/nonterminal/no prior twice-key trap. Legal prefix not asserted optimal before D; no9x9/20wall embedding theorem.",
    }
    assert (
        ref(graph_path) == candidate["graph"]
        and ref(root / "reference.py") == reference_ref
    )
    (root / "full-collection-v1/candidate-prefix.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": output["status"],
                "D_raw_state": target,
                "D_pawns": pawns,
                "D_turn": turn,
                "prefix_plies": len(actions),
                "nonterminal_path": path,
                "maximum_prior_occurrence": max(counts.values()),
                "cycle": cycle,
            }
        )
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
