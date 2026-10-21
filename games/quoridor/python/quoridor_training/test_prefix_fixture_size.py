"""Publication-size regression; native/class ports are explicitly synthetic."""

import ast
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class PrefixFixturePublicationSize(unittest.TestCase):
    def test_large_history_source_is_rechecked_and_mutation_stays_failed(self):
        source = Path(__file__).with_name("public_static_prepare.py")
        tree = ast.parse(source.read_text())
        names = {
            "prefix_fixture_rows",
            "prefix_fixture_partition",
            "prepare_prefix_fixture",
        }
        definitions = ast.Module(
            body=[
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in names
            ],
            type_ignores=[],
        )
        # Compile the actual publication definitions only. No NumPy, native, model,
        # geometry, teacher or production corpus import occurs in this NN0 case.
        code = compile(definitions, str(source), "exec")
        for mutate in (False, True):
            with (
                self.subTest(mutate=mutate),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                input_path = root / "prefixes.json"
                rows = [
                    {
                        "fixture": i,
                        "history": [1] * 199 + [i],
                        "functional_split": "T" if i < 64 else "V",
                        "family": i // 64,
                    }
                    for i in range(128)
                ]
                input_path.write_text(json.dumps({"fixed_prefixes": rows}))
                self.assertGreater(input_path.stat().st_size, 65536)
                library = root / "synthetic-unused-library"
                library.write_bytes(b"synthetic-not-an-ELF")
                output = root / "output"
                reads, connections = [], []
                counts = {
                    "qualified_original_observations": 256,
                    "train": 128,
                    "validation": 128,
                }

                def read_bound(reference, limit):
                    raw = Path(reference["path"]).read_bytes()
                    if len(raw) > limit:
                        raise ValueError("synthetic bounded file reader: size")
                    reads.append((reference["path"], limit))
                    if reference["path"] == str(input_path) and len(reads) == 1 and mutate:
                        input_path.write_bytes(raw + b" ")
                    return raw

                def connection(path, **_):
                    path.touch()
                    value = SimpleNamespace(
                        closed=False,
                        commit=lambda: None,
                    )
                    value.close = lambda: setattr(value, "closed", True)
                    connections.append(value)
                    return value

                def table(_connection, stream, **_):
                    stream.write(b"synthetic-class-table-not-PAIR37")
                    return counts

                def write_json(path, value):
                    path.write_text(json.dumps(value))

                static = ModuleType("quoridor_training.static_public")
                static.accumulate_inputs = lambda *args: None
                namespace = {
                    "__package__": "quoridor_training",
                    "json": json,
                    "Path": Path,
                    "os": os,
                    "bound_file_bytes": read_bound,
                    "native_prefix_keys": lambda values, _: [
                        (
                            (i + 1).to_bytes(28, "little"),
                            (i + 1000).to_bytes(28, "little"),
                        )
                        for i, _ in enumerate(values)
                    ],
                    "np": SimpleNamespace(
                        asarray=lambda values, **_: values,
                        zeros=lambda length, **_: [0] * length,
                        memmap=lambda *args, **_: SimpleNamespace(_mmap=io.BytesIO()),
                    ),
                    "PAIR": SimpleNamespace(itemsize=37),
                    "ClassObservations": lambda _: SimpleNamespace(
                        counts={"train": 128, "validation": 128}
                    ),
                    "create_class_accumulator": connection,
                    "write_class_table": table,
                    "write_json": write_json,
                    "file_ref": lambda path: {"path": str(path)},
                    "file_identity": lambda path: {"synthetic": True},
                }
                exec(code, namespace)
                config = {
                    "prefix_fixture": {"path": str(input_path)},
                    "native_library": {"path": str(library)},
                    "output": str(output),
                    "max_sqlite_bytes": 1024,
                }
                with patch.dict(sys.modules, {"quoridor_training.static_public": static}):
                    if mutate:
                        with self.assertRaisesRegex(ValueError, "source changed"):
                            namespace["prepare_prefix_fixture"](config)
                        self.assertTrue((output / "INCOMPLETE").exists())
                        failure = json.loads((output / "failure.json").read_text())
                        self.assertEqual(
                            failure["message"],
                            "fixture source changed during publication",
                        )
                        self.assertFalse((output / "cache.json").exists())
                    else:
                        result = namespace["prepare_prefix_fixture"](config)
                        self.assertEqual(result["counts"], counts)
                        saved = json.loads((output / "cache.json").read_text())
                        self.assertEqual(saved["status"], "COMPLETE")
                        self.assertFalse(saved["split"]["independent_validation"])
                        self.assertFalse((output / "INCOMPLETE").exists())
                        self.assertFalse((output / "input-classes.sqlite").exists())
                self.assertTrue(all(value.closed for value in connections))
                self.assertEqual(
                    [limit for path, limit in reads if path == str(input_path)],
                    [64 * 1024**2, 64 * 1024**2],
                )


if __name__ == "__main__":
    unittest.main()
