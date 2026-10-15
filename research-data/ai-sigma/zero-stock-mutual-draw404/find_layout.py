"""Bounded candidate search for a mathematical example, not an arena trial."""

import json
from pathlib import Path
import random

from check_graph import adjacency, analyze, reachable


def initial_routes_exist(walls):
    try:
        n = adjacency(walls)
    except AssertionError:
        return False
    return 4 in reachable(n, range(72, 81)) and 76 in reachable(n, range(9))


def layouts():
    rows = ([0, 1, 2, 3, 4], [0, 2, 4, 6, 7], [1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
    for ri, rs in enumerate(rows):
        for reflected in (0, 1):
            walls = [
                81 + 8 * r + c
                for j, r in enumerate(rs)
                for c in ([0, 2, 4, 6] if (j + reflected) % 2 == 0 else [1, 3, 5, 7])
            ]
            assert initial_routes_exist(walls)
            yield f"serpentine-{ri}-{reflected}", walls
    for seed in range(54):
        rng = random.Random(202610150000 + seed)
        order = list(range(81, 209))
        rng.shuffle(order)
        walls = []
        for action in order:
            if initial_routes_exist(walls + [action]):
                walls.append(action)
                if len(walls) == 20:
                    break
        assert len(walls) == 20
        yield f"seed-{202610150000 + seed}", walls


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    inputs = list(layouts())
    assert len(inputs) == 62
    (out / "layout-inputs-v1.json").write_text(json.dumps(inputs, indent=2) + "\n")
    results = []
    for name, walls in inputs:
        result = analyze(walls, name, out)
        results.append(result)
        if "draw_root" in result:
            break
    (out / "layout-results-v1.json").write_text(json.dumps(results, indent=2) + "\n")
