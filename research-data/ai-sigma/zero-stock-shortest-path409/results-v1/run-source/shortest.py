"""One-off coloured ordinary-geodesic predicates; no pawn move/Search solver."""

from collections import deque
from functools import lru_cache


def distances(adjacent, goals):
    distance = {v: 0 for v in goals}
    queue = deque(goals)
    while queue:
        vertex = queue.popleft()
        for other in adjacent[vertex]:
            if other not in distance:
                distance[other] = distance[vertex] + 1
                queue.append(other)
    return distance


def dag(adjacent, distance, start):
    assert start in distance
    edges = {}
    todo = [start]
    union = 0
    while todo:
        vertex = todo.pop()
        if vertex in edges:
            continue
        union |= 1 << vertex
        children = tuple(
            sorted(
                v for v in adjacent[vertex] if distance.get(v) == distance[vertex] - 1
            )
        )
        assert distance[vertex] == 0 or children
        edges[vertex] = children
        todo.extend(children)

    @lru_cache(None)
    def count(vertex):
        return sum(count(v) for v in edges[vertex]) if edges[vertex] else 1

    return dict(
        start=start,
        edges=edges,
        union=union,
        path_count=count(start),
        distance=distance[start],
    )


def avoid_path(graph, forbidden):
    @lru_cache(None)
    def visit(vertex):
        if forbidden & (1 << vertex):
            return None
        if not graph["edges"][vertex]:
            return (vertex,)
        for child in graph["edges"][vertex]:
            result = visit(child)
            if result is not None:
                return (vertex, *result)
        return None

    return visit(graph["start"])


def paths(graph, vertex=None, prefix=()):
    vertex = graph["start"] if vertex is None else vertex
    prefix = (*prefix, vertex)
    if not graph["edges"][vertex]:
        yield prefix
    else:
        for child in graph["edges"][vertex]:
            yield from paths(graph, child, prefix)


def predicates(first, second):
    """Exact finite enumeration in one colour, reachability in the other.

    Each path contains its start and goal. Strictly descending distance makes
    every path finite. No branch cap or identity-losing shared-flow relaxation.
    """
    all_union = first["union"] & second["union"] == 0
    if all_union:
        witness = (avoid_path(first, 0), avoid_path(second, 0))
        assert all(witness)
        return True, True, witness, 0
    swap = second["path_count"] < first["path_count"]
    enumerated, other = (second, first) if swap else (first, second)
    leaves = 0
    for path in paths(enumerated):
        leaves += 1
        forbidden = sum(1 << vertex for vertex in path)
        alternative = avoid_path(other, forbidden)
        if alternative is not None:
            witness = (alternative, path) if swap else (path, alternative)
            assert set(witness[0]).isdisjoint(witness[1])
            return True, False, witness, leaves
    assert leaves == enumerated["path_count"]
    return False, False, None, leaves
