"""New puremock per-operator flag contract; no Torch import/model/head."""

from contextlib import nullcontext
import types
import unittest

from quoridor_training.static_teacher_heads import force_jit_convolution_tf32_off


class Value:
    def __init__(self, value):
        self.value = value

    def toIValue(self):
        return self.value


class Node:
    def __init__(self, flag=True, *, arity=13, children=(), kind="aten::_convolution"):
        self.arguments = [Value(object()) for _ in range(arity)]
        self.arguments[-1] = Value(flag)
        self.children = children
        self.op = kind

    def inputs(self):
        return iter(self.arguments)

    def kind(self):
        return self.op

    def schema(self):
        return "aten::_convolution(... bool allow_tf32) -> Tensor"

    def blocks(self):
        return self.children

    def replaceInput(self, index, value):
        self.arguments[index] = value


class Graph:
    def __init__(self, nodes):
        self.values = nodes
        self.linted = False

    def nodes(self):
        return iter(self.values)

    def insert_point_guard(self, node):
        return nullcontext()

    def insertConstant(self, value):
        return Value(value)

    def lint(self):
        self.linted = True


def model(graph):
    owner = types.SimpleNamespace(
        _method_names=lambda: ["forward"],
        _get_method=lambda name: types.SimpleNamespace(graph=graph),
    )
    return types.SimpleNamespace(modules=lambda: [types.SimpleNamespace(_c=owner)])


class SerializedPrecisionBoundary(unittest.TestCase):
    def test_executed_graph_verification_cannot_repair_or_hide_a_true_flag(self):
        node = Node(False)
        graph = Graph([node])
        result = force_jit_convolution_tf32_off(model(graph), repair=False)
        self.assertEqual(result["explicit_true_flags_replaced"], 0)
        self.assertIs(result["operators"][0]["before"], False)
        self.assertIn("bool allow_tf32", result["operators"][0]["schema"])
        changed = Node(True)
        with self.assertRaisesRegex(ValueError, "executed loaded"):
            force_jit_convolution_tf32_off(model(Graph([changed])), repair=False)
        self.assertIs(list(changed.inputs())[12].toIValue(), True)

    def test_only_explicit_convolution_tf32_flag_changes_and_unknowns_refuse(self):
        child = Node(True)
        parent = Node(False, children=[Graph([child])])
        graph = Graph([parent])
        originals = [(node, list(node.inputs())[:12]) for node in (parent, child)]
        receipt = force_jit_convolution_tf32_off(model(graph))
        self.assertEqual(receipt["explicit_convolution_flag_visits"], 2)
        self.assertEqual(receipt["explicit_true_flags_replaced"], 1)
        self.assertEqual(receipt["head_calls"], 0)
        self.assertTrue(graph.linted)
        for node, before in originals:
            self.assertEqual(list(node.inputs())[:12], before)
            self.assertIs(list(node.inputs())[12].toIValue(), False)
        for nodes in ([], [Node(None)], [Node(True, arity=12)], [Node(True, kind="aten::other")]):
            with self.subTest(nodes=nodes):
                with self.assertRaises(ValueError):
                    force_jit_convolution_tf32_off(model(Graph(nodes)))


if __name__ == "__main__":
    unittest.main()
