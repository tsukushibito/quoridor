"""Independent literal finite-board oracle; execution belongs to software/analysis owner."""

import argparse
import hashlib
import itertools
import json
import struct
import subprocess
from collections import deque
from pathlib import Path

GOAL = 65535


def legal_masks(n):
    """Tiny reference only: literal pair conflicts, not the native collision masks."""
    anchors = [
        (orientation, row, col)
        for orientation in ("H", "V")
        for row in range(n - 1)
        for col in range(n - 1)
    ]
    assert len(anchors) <= 8, "brute reference only3x3, never2^32"
    result = []
    for mask in range(1 << len(anchors)):
        walls = [a for i, a in enumerate(anchors) if mask & (1 << i)]
        valid = True
        for (o, r, c), (p, s, d) in itertools.combinations(walls, 2):
            if o != p and (r, c) == (s, d):
                valid = False
            if o == p == "H" and r == s and abs(c - d) == 1:
                valid = False
            if o == p == "V" and c == d and abs(r - s) == 1:
                valid = False
        if valid:
            result.append(mask)
    return result


def board(n, mask):
    points = [(r, c) for r in range(n) for c in range(n)]
    adjacent = {p: set() for p in points}
    for r, c in points:
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            q = (r + dr, c + dc)
            if q in adjacent:
                adjacent[r, c].add(q)
    anchors = [
        (o, r, c) for o in ("H", "V") for r in range(n - 1) for c in range(n - 1)
    ]
    chosen = [a for i, a in enumerate(anchors) if mask & (1 << i)]
    assert mask >> len(anchors) == 0
    for (o, r, c), (p, s, d) in itertools.combinations(chosen, 2):
        assert not (o != p and (r, c) == (s, d))
        assert not (o == p == "H" and r == s and abs(c - d) == 1)
        assert not (o == p == "V" and c == d and abs(r - s) == 1)
    for orientation, r, c in chosen:
        edges = (
            [((r, c), (r + 1, c)), ((r, c + 1), (r + 1, c + 1))]
            if orientation == "H"
            else [((r, c), (r, c + 1)), ((r + 1, c), (r + 1, c + 1))]
        )
        for a, b in edges:
            adjacent[a].remove(b)
            adjacent[b].remove(a)
    return adjacent


def reachable(adjacent, goals):
    seen = set(goals)
    queue = deque(goals)
    while queue:
        for q in adjacent[queue.popleft()]:
            if q not in seen:
                seen.add(q)
                queue.append(q)
    return seen


def actions(adjacent, own, other):
    result = set()
    for q in adjacent[own]:
        if q != other:
            result.add(q)
            continue
        dr, dc = q[0] - own[0], q[1] - own[1]
        beyond = q[0] + dr, q[1] + dc
        if beyond in adjacent[q]:
            result.add(beyond)
        else:
            # Definition by perpendicular coordinate, independent of native bit arithmetic.
            candidates = ((q[0] + dc, q[1] + dr), (q[0] - dc, q[1] - dr))
            result.update(z for z in candidates if z in adjacent[q])
    return result


def oracle(n, mask):
    adjacent = board(n, mask)
    allowed = [
        reachable(adjacent, [(n - 1, c) for c in range(n)]),
        reachable(adjacent, [(0, c) for c in range(n)]),
    ]
    states = [
        (a, b, turn)
        for a in sorted(allowed[0])
        if a[0] != n - 1
        for b in sorted(allowed[1])
        if b[0] != 0 and a != b
        for turn in (0, 1)
    ]
    edges = {}
    for a, b, turn in states:
        own, other = (a, b) if turn == 0 else (b, a)
        outgoing = []
        for q in sorted(actions(adjacent, own, other)):
            if q[0] == (n - 1 if turn == 0 else 0):
                outgoing.append((q, None))
            else:
                child = (q, b, 1) if turn == 0 else (a, q, 0)
                outgoing.append((q, child))
        assert outgoing, "no legal move semantics not invented"
        edges[a, b, turn] = outgoing
    state_set = set(states)
    assert all(
        child in state_set
        for row in edges.values()
        for _, child in row
        if child is not None
    )
    label = {}
    # Whole-set synchronous least fixed point: no native reverse queue/rank algorithm.
    while True:
        additions = {}
        for state, outgoing in edges.items():
            if state in label:
                continue
            successors = [v for _, v in outgoing]
            if None in successors or any(label.get(v) == 2 for v in successors):
                additions[state] = 1
            elif all(label.get(v) == 1 for v in successors):
                additions[state] = 2
        if not additions:
            break
        label.update(additions)
    return edges, {s: label.get(s, 0) for s in states}


def raw_id(n, state):
    a, b, turn = state
    aa, bb = a[0] * n + a[1], b[0] * n + b[1]
    return (aa * n * n + bb) * 2 + turn


def check_fixture(path):
    assert path.stat().st_size <= 37528, "bounded fixture before read"
    data = path.read_bytes()
    assert len(data) <= 37528, "bounded full graph fixture"
    magic, n, count, reserved, mask, raw_count, active_count, edge_count = (
        struct.unpack_from("<8sBBHIIII", data)
    )
    assert (
        magic == b"Q5WDL001"
        and n in (3, 5)
        and count == 2 * (n - 1) ** 2
        and reserved == 0
    )
    assert raw_count == 2 * n**4 and raw_count <= 1250
    offset = 28
    rows = {}
    for i in range(raw_count):
        status, degree, rank, choice = struct.unpack_from("<BBHH", data, offset)
        offset += 6
        assert status in (0, 1, 2, 255) and degree <= 8
        outgoing = []
        for _ in range(degree):
            dest, child = struct.unpack_from("<BH", data, offset)
            offset += 3
            outgoing.append((dest, child))
        assert len(set(dest for dest, _ in outgoing)) == degree
        rows[i] = status, rank, choice, outgoing
    assert offset == len(data), "incomplete/trailing fixture"
    edges, labels = oracle(n, mask)
    ids = {raw_id(n, state) for state in edges}
    assert active_count == len(ids) and edge_count == sum(
        len(v) for v in edges.values()
    )
    for i, (status, rank, choice, outgoing) in rows.items():
        if i not in ids:
            assert (status, rank, choice, outgoing) == (255, 0, GOAL, [])
    for state, outgoing in edges.items():
        i = raw_id(n, state)
        expected = sorted(
            (q[0] * n + q[1], GOAL if child is None else raw_id(n, child))
            for q, child in outgoing
        )
        status, rank, choice, actual = rows[i]
        assert actual == expected and status == labels[state], (
            n,
            mask,
            state,
            expected,
            actual,
        )
        children = [c for _, c in actual]
        if status == 1:
            assert rank > 0 and choice in children
            if choice == GOAL:
                assert rank == 1
            else:
                assert rows[choice][0] == 2 and rows[choice][1] < rank
        elif status == 2:
            assert rank > 0 and GOAL not in children
            assert all(rows[c][0] == 1 and rows[c][1] < rank for c in children)
        else:
            assert (
                rank == 0
                and GOAL not in children
                and all(rows[c][0] != 2 for c in children)
            )
            assert choice in children and rows[choice][0] == 0
    return {
        "side": n,
        "mask": mask,
        "active": active_count,
        "edges": edge_count,
        "W": sum(v == 1 for v in labels.values()),
        "L": sum(v == 2 for v in labels.values()),
        "D": sum(v == 0 for v in labels.values()),
        "fixture_sha256": hashlib.sha256(data).hexdigest(),
    }


def run_native(binary, args):
    p = subprocess.Popen(
        [str(binary), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        stat = Path(f"/proc/{p.pid}/stat").read_text().rsplit(")", 1)[1].split()
        identity = {
            "pid": p.pid,
            "start_ticks": stat[19],
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        }
    except FileNotFoundError:
        identity = None
    try:
        stdout, stderr = p.communicate()
        assert len(stdout) + len(stderr) < 128 * 1024
        assert p.returncode == 0, stderr.decode()
        return {
            "argv": args,
            "child": identity,
            "directwait_exit": p.returncode,
            "handles_closed": True,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        }
    finally:
        if p.poll() is None:
            p.terminate()
            p.wait()
        p.stdout.close()
        p.stderr.close()


def software_check(binary, tmp):
    tmp.mkdir(exist_ok=False)
    records = []
    masks, summary = tmp / "tiny-masks.bin", tmp / "tiny-summary.json"
    records.append(
        run_native(
            binary,
            [
                "enumerate",
                "--side",
                "3",
                "--masks",
                str(masks),
                "--summary",
                str(summary),
            ],
        )
    )
    data = masks.read_bytes()
    magic, n, count, layouts = struct.unpack_from("<8sIIQ", data)
    assert (
        magic == b"Q5MASK01" and n == 3 and count == 8 and len(data) == 24 + 4 * layouts
    )
    values = list(struct.unpack_from(f"<{layouts}I", data, 24))
    assert values == legal_masks(3), "independent all-tiny layout census"
    actual = json.loads(summary.read_text())
    assert actual["layouts"] == len(values) and actual["by_wall_count"] == [
        sum(m.bit_count() == i for m in values) for i in range(33)
    ]
    fixtures = []
    fixed = [(3, mask) for mask in values] + [
        (5, 0),
        (5, 1),
        (5, 1 << 28),
        (5, 1 << 16),
        (5, (1 << 0) | (1 << 2) | (1 << 20) | (1 << 22)),
    ]
    for index, (side, mask) in enumerate(fixed):
        path = tmp / f"fixture-{index:03d}.bin"
        records.append(
            run_native(
                binary,
                [
                    "fixture",
                    "--side",
                    str(side),
                    "--mask",
                    str(mask),
                    "--output",
                    str(path),
                ],
            )
        )
        fixtures.append(check_fixture(path))
    result = {
        "status": "PASS",
        "tiny_legal_layouts": len(values),
        "independent_fixture_checks": len(fixtures),
        "fixtures": fixtures,
        "native_children": records,
        "model_Search_games_fit_calls": 0,
        "scope": "new finite software definitions only; not full5x5 or9x9 conclusion",
    }
    (tmp / "check-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"status": "PASS", "tiny_layouts": len(values), "fixtures": len(fixtures)}
        )
    )


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", type=Path)
    mode.add_argument("--native", type=Path)
    parser.add_argument("--tmp", type=Path)
    args = parser.parse_args()
    if args.fixture:
        print(json.dumps(check_fixture(args.fixture)))
    else:
        assert args.tmp is not None
        software_check(args.native, args.tmp)


if __name__ == "__main__":
    main()
