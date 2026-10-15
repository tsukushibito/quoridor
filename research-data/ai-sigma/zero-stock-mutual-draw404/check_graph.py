"""Finite mathematical check; never calls production Search or a model."""

import collections
import json
import os
from pathlib import Path
import resource
import time

resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))


def vertex(a, b, turn):
    return (a * 81 + b) * 2 + turn


def decode(s):
    pair, turn = divmod(s, 2)
    a, b = divmod(pair, 81)
    return a, b, turn


def adjacency(walls):
    horizontal = {x - 81 for x in walls if 81 <= x < 145}
    vertical = {x - 145 for x in walls if 145 <= x < 209}
    assert len(horizontal) + len(vertical) == len(walls)
    for i in horizontal:
        assert i not in vertical
        assert i % 8 == 7 or i + 1 not in horizontal
    for i in vertical:
        assert i // 8 == 7 or i + 8 not in vertical
    n = [[-1] * 4 for _ in range(81)]
    for a in range(81):
        r, c = divmod(a, 9)
        for direction, (dr, dc) in enumerate(((-1, 0), (1, 0), (0, -1), (0, 1))):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < 9 and 0 <= cc < 9):
                continue
            if dr:
                row = min(r, rr)
                blocked = (c < 8 and row * 8 + c in horizontal) or (
                    c > 0 and row * 8 + c - 1 in horizontal
                )
            else:
                col = min(c, cc)
                blocked = (r < 8 and r * 8 + col in vertical) or (
                    r > 0 and (r - 1) * 8 + col in vertical
                )
            if not blocked:
                n[a][direction] = rr * 9 + cc
    return n


def reachable(n, goals):
    seen = set(goals)
    q = collections.deque(seen)
    while q:
        a = q.popleft()
        for b in n[a]:
            if b >= 0 and b not in seen:
                seen.add(b)
                q.append(b)
    return seen


def pawn_moves(n, own, other):
    dest = set()
    for direction, b in enumerate(n[own]):
        if b < 0:
            continue
        if b != other:
            dest.add(b)
        elif n[b][direction] >= 0:
            dest.add(n[b][direction])
        else:
            for side in (2, 3) if direction < 2 else (0, 1):
                if n[b][side] >= 0:
                    dest.add(n[b][side])
    return sorted(dest)


def analyze(walls, name, out):
    start = time.monotonic()
    n = adjacency(walls)
    reach0 = reachable(n, range(72, 81))
    reach1 = reachable(n, range(9))
    assert 4 in reach0 and 76 in reach1
    size = 81 * 81 * 2
    active = []
    edges = [[] for _ in range(size)]
    predecessors = [[] for _ in range(size)]
    status = [9] * size
    rank = [-1] * size
    remaining = [0] * size
    goal_action = [-1] * size
    q = collections.deque()
    for a in sorted(reach0 - set(range(72, 81))):
        for b in sorted(reach1 - set(range(9))):
            if a == b:
                continue
            for turn in (0, 1):
                s = vertex(a, b, turn)
                status[s] = 0
                active.append(s)
                for action in pawn_moves(
                    n, a if turn == 0 else b, b if turn == 0 else a
                ):
                    if (turn == 0 and action >= 72) or (turn == 1 and action < 9):
                        goal_action[s] = action
                        continue
                    t = vertex(action, b, 1) if turn == 0 else vertex(a, action, 0)
                    edges[s].append(t)
                    predecessors[t].append(s)
                if goal_action[s] >= 0:
                    status[s] = 1
                    rank[s] = 1
                    q.append(s)
                else:
                    assert edges[s], (name, decode(s), "no legal pawn move")
                remaining[s] = len(edges[s])
    while q:
        child = q.popleft()
        for parent in predecessors[child]:
            if status[parent] != 0:
                continue
            if status[child] == -1:
                status[parent] = 1
                rank[parent] = rank[child] + 1
                q.append(parent)
            else:
                remaining[parent] -= 1
                if remaining[parent] == 0:
                    status[parent] = -1
                    rank[parent] = max(rank[x] for x in edges[parent]) + 1
                    q.append(parent)
    # Complete Bellman conditions plus strict rank verify the solved attractor.
    for s in active:
        if status[s] == 1:
            assert goal_action[s] >= 0 or any(
                status[t] == -1 and rank[t] < rank[s] for t in edges[s]
            )
        elif status[s] == -1:
            assert goal_action[s] < 0 and all(
                status[t] == 1 and rank[t] < rank[s] for t in edges[s]
            )
        else:
            assert goal_action[s] < 0
            assert all(status[t] != -1 for t in edges[s])
            assert any(status[t] == 0 for t in edges[s])
    counts = collections.Counter(status[s] for s in active)
    result = dict(
        name=name,
        walls=walls,
        active_nonterminal_states=len(active),
        W=counts[1],
        L=counts[-1],
        D=counts[0],
        elapsed_seconds=time.monotonic() - start,
        Bellman_and_strict_rank=True,
    )
    if counts[0]:
        # Find a simple nonterminal path from genuine initial pawns after walls.
        root = vertex(4, 76, 0)
        parent = {root: None}
        todo = collections.deque([root])
        found = None
        while todo:
            s = todo.popleft()
            if status[s] == 0:
                found = s
                break
            for t in edges[s]:
                if t not in parent:
                    parent[t] = s
                    todo.append(t)
        if found is not None:
            path = [found]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            path.reverse()
            actions = [decode(t)[decode(s)[2]] for s, t in zip(path, path[1:])]
            # Stationary non-losing policy stays D and must eventually repeat.
            cycle_path = [found]
            first = {found: 0}
            while True:
                s = cycle_path[-1]
                t = next(t for t in edges[s] if status[t] == 0)
                cycle_path.append(t)
                if t in first:
                    cycle_start = first[t]
                    break
                first[t] = len(cycle_path) - 1
            result.update(
                draw_root=decode(found),
                nonterminal_prefix_actions=actions,
                draw_path=[decode(x) for x in cycle_path],
                cycle_start=cycle_start,
            )
            certificate = dict(
                walls=walls,
                root=found,
                status=status,
                rank=rank,
                edges=edges,
                goal_action=goal_action,
                active=active,
                scope="Infinite-play draw graph; D-closure proves threefold non-loss for either player",
            )
            (out / "candidate-certificate.json").write_text(json.dumps(certificate))
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    original_walls = [
        145,
        146,
        150,
        151,
        152,
        161,
        162,
        166,
        167,
        168,
        177,
        178,
        182,
        183,
        184,
        193,
        194,
        198,
        199,
        200,
    ]
    cases = [([], "empty-walls-baseline"), (original_walls, "accepted335-walls")]
    result = dict(
        issue="quoridor-4lc.404",
        pid=os.getpid(),
        affinity=sorted(os.sched_getaffinity(0)),
        AS_bytes=512 * 1024**2,
        CPU_seconds=30,
        rule="Fixed walls; infinite-play draws analyzed, not forged historical counts",
        cases=[analyze(w, name, out) for w, name in cases],
    )
    (out / "graph-result-v1.json").write_text(json.dumps(result, indent=2) + "\n")
