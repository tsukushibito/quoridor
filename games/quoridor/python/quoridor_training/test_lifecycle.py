"""NN0 resource/publication boundaries; execute actual AST with synthetic ports."""

import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from quoridor_runtime.snapshot import atomic_text, write_json

SOURCE = Path(__file__).with_name("train.py")


def helpers():
    tree = ast.parse(SOURCE.read_text())
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {
            "write",
            "stream_json",
            "_exception_record",
            "_attempt_finalization",
            "_finalize_training",
        }
    ]
    env = {
        "Path": Path,
        "json": json,
        "atomic_text": atomic_text,
        "np": SimpleNamespace(ndarray=type("Array", (), {}), generic=type("Scalar", (), {})),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), env)
    return tree, env


class LifecycleTests(unittest.TestCase):
    def test_streaming_snapshots_preserve_last_good_on_serialization_and_replace_failure(self):
        _, env = helpers()
        for writer in (write_json, env["write"]):
            with self.subTest(writer=writer.__name__), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "snapshot.json"
                writer(path, {"old": [1, 2]})
                before = path.read_bytes()
                with self.assertRaises((ValueError, TypeError)):
                    writer(path, {"partial": [1, float("nan")]})
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(Path(directory).glob("*.tmp")), [])
                with patch(
                    "quoridor_runtime.snapshot.os.replace", side_effect=OSError("replace fixture")
                ):
                    with self.assertRaisesRegex(OSError, "replace fixture"):
                        writer(path, {"new": 3})
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(Path(directory).glob("*.tmp")), [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.json"

            def broken():
                yield 1
                raise OSError("mid-serialization fixture")

            env["write"](path, {"old": 1})
            with self.assertRaisesRegex(OSError, "mid-serialization"):
                env["write"](path, {"new": broken()})
            self.assertEqual(json.loads(path.read_text()), {"old": 1})
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_cycle_and_public_progress_use_the_same_owned_snapshot_writer(self):
        for filename in ("cycle.py", "public_sigma.py"):
            tree = ast.parse(SOURCE.with_name(filename).read_text())
            imports = [
                node
                for node in tree.body
                if isinstance(node, ast.ImportFrom) and node.module == "quoridor_runtime.snapshot"
            ]
            self.assertTrue(
                any(
                    alias.name == "write_json" and alias.asname == "write"
                    for node in imports
                    for alias in node.names
                )
            )

    def test_actual_supply_acquisition_scope_handles_log_open_and_body_failures(self):
        tree, env = helpers()
        train = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "train"
        )
        scope = copy.deepcopy(
            next(
                node
                for node in train.body
                if isinstance(node, ast.With)
                and any(isinstance(child, ast.Try) for child in node.body)
            )
        )
        # Retain actual with ports, acquisition and finalizer; replace numerical steps by one failing port.
        attempt = next(node for node in scope.body if isinstance(node, ast.Try))
        acquire = next(
            node
            for node in attempt.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "compact"
        )
        acquire.body = [node for node in acquire.body if not isinstance(node, ast.ImportFrom)]
        attempt.body = [
            acquire,
            ast.Expr(
                value=ast.Call(func=ast.Name(id="body", ctx=ast.Load()), args=[], keywords=[])
            ),
        ]
        attempt.handlers = []
        attempt.orelse = []
        module = ast.fix_missing_locations(ast.Module(body=[scope], type_ignores=[]))
        for fail_open in (1, 2, None):
            opened = []
            supplies = []
            primary = RuntimeError("body fixture")

            def open_log(*args, **kwargs):
                if fail_open == len(opened) + 1:
                    raise OSError("log fixture")
                handle = Mock()
                handle.__enter__ = Mock(return_value=handle)
                handle.__exit__ = Mock(return_value=False)
                opened.append(handle)
                return handle

            def supply(*args, **kwargs):
                value = SimpleNamespace(close=Mock())
                supplies.append(value)
                return value

            local = {
                **env,
                "gzip": SimpleNamespace(open=open_log),
                "output": Path("unused"),
                "compact": True,
                "PackedSupply": supply,
                "packed_supply": None,
                "supply": object(),
                "batch_size": 2,
                "cfg": {"evaluation": {"batch_size": 3}},
                "device": "fake",
                "row_loss_weights": (),
                "column": 1,
                "supply_workers": 0,
                "body": Mock(side_effect=primary),
                "primary_error": None,
                "sys": sys,
                "stop_record_failures": [],
                "model_state_status": "UNKNOWN",
                "persist": Mock(),
                "position": lambda: {},
                "status": "RUNNING",
                "fault": None,
                "attempted_step": 0,
                "checkpoint_positions": {},
            }
            with self.assertRaises(OSError if fail_open else RuntimeError) as error:
                exec(compile(module, str(SOURCE), "exec"), local)
            self.assertEqual(len(supplies), 0 if fail_open else 1)
            if supplies:
                supplies[0].close.assert_called_once_with()
                self.assertIs(error.exception, primary)
                local["persist"].assert_called_once_with()
            for handle in opened:
                handle.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
