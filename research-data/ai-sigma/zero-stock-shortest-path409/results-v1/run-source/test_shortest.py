"""New predicate checks only, not the old WDL/52 fixture suite."""

import unittest

from shortest import dag, distances, predicates


def graph(edges, start):
    vertices = set(edges)
    for children in edges.values():
        vertices.update(children)
    adjacent = {v: tuple(edges.get(v, ())) for v in vertices}
    reverse = {v: [] for v in vertices}
    for vertex, children in adjacent.items():
        for child in children:
            reverse[child].append(vertex)
    goals = [v for v in vertices if not adjacent[v]]
    return dag(adjacent, distances(reverse, goals), start)


class ShortestPredicateTests(unittest.TestCase):
    def test_branch_pair_exists_while_full_unions_overlap(self):
        a = graph({0: [1, 2], 1: [3], 2: [3]}, 0)
        b = graph({4: [1], 1: [6]}, 4)
        one, every, witness, _ = predicates(a, b)
        self.assertTrue(one)
        self.assertFalse(every)
        self.assertEqual(witness, ((0, 2, 3), (4, 1, 6)))
        self.assertEqual(a["path_count"], 2)
        self.assertEqual(a["union"], sum(1 << v for v in [0, 1, 2, 3]))

    def test_disjoint_unions_imply_one_pair(self):
        a = graph({0: [1]}, 0)
        b = graph({2: [3]}, 2)
        one, every, witness, _ = predicates(a, b)
        self.assertTrue(one and every)
        self.assertEqual(witness, ((0, 1), (2, 3)))

    def test_shared_start_or_goal_vertex_is_an_intersection(self):
        a = graph({0: [1], 1: [2]}, 0)
        b = graph({3: [0], 0: [4]}, 3)
        self.assertEqual(predicates(a, b)[:3], (False, False, None))
        a = graph({0: [2]}, 0)
        b = graph({1: [2]}, 1)
        self.assertEqual(predicates(a, b)[:3], (False, False, None))

    def test_shortest_dag_uses_distance_order_and_includes_zero_length(self):
        # Boundary goals at unequal initial graph distances; the longer branch
        # through4 must not enter the complete shortest DAG from0.
        adjacent = {0: [1, 2], 1: [0, 3], 2: [0, 4], 3: [1], 4: [2, 5], 5: [4]}
        distance = distances(adjacent, [3, 5])
        a = dag(adjacent, distance, 0)
        self.assertEqual(a["distance"], 2)
        self.assertEqual(a["edges"], {0: (1,), 1: (3,), 3: ()})
        self.assertEqual(a["union"], (1 << 0) | (1 << 1) | (1 << 3))
        at_goal = dag(adjacent, distance, 3)
        self.assertEqual(at_goal["union"], 1 << 3)
        self.assertEqual(at_goal["distance"], 0)


if __name__ == "__main__":
    unittest.main()
