"""Only new related NN0 completion/config/error contracts; every head is a fake."""

import ast
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

import test_public_static_values as fixtures
from quoridor_training import public_static_values as values
from quoridor_training import static_learning as learning
from quoridor_training.public_features import reflected_keys


class RelatedStaticRepairs(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.NewStaticValueFlow()
        self.base.setUp()
        self.path = self.base.path
        pairs = self.base.base.corpus.pairs
        self.keys = np.concatenate(
            [np.unique(np.r_[k.reshape(1), reflected_keys(k.reshape(1))]) for k in pairs["key"]]
        )
        (self.path / "boundary-keys").write_bytes(self.keys.tobytes())
        for kind in ("S", "C"):
            np.zeros(len(self.keys), dtype="<f4").tofile(self.path / ("boundary-" + kind))
        config = self.base.config
        boundary = dict(
            status="PASS",
            input_classes=config["input_classes"],
            models=config["models"],
            core_library=config["core_library"],
            c20_library=config["c20_library"],
            device="cpu",
            route_devices_precision=values.runtime_devices(config),
            planned_extra_head_rows=0,
            logical_rows_attempted=5 * len(self.keys),
            keys=fixtures.ref(self.path / "boundary-keys"),
            batch_values={k: fixtures.ref(self.path / ("boundary-" + k)) for k in ("S", "C")},
            model_identities={
                k: list(values.file_identity(ref["path"])) for k, ref in config["models"].items()
            },
        )
        (self.path / "boundary.json").write_text(json.dumps(boundary))
        self.config = {
            **config,
            "runtime_boundary": fixtures.ref(self.path / "boundary.json"),
            "actual_orientation_rows": len(self.keys),
            "inclusive_row_limit": 264,
            "batch_rows": 4,
            "output": str(self.path / "labels"),
        }

    def tearDown(self):
        self.base.tearDown()

    def test_off_recipe_constructor_export_and_nonstatic_guard(self):
        cfg = learning.recipe(2809595, 312247, device="cpu", threads=1)
        self.assertEqual((cfg["model"]["distance_a"], cfg["model"]["distance_b"]), (0, 0))
        source = Path(learning.__file__).read_text()
        common = next(
            n for n in ast.parse(source).body if getattr(n, "name", "") == "prepare_common"
        )
        export = next(
            n
            for n in ast.walk(common)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "export"
        )
        self.assertEqual(ast.literal_eval(export.args[3]), {"a": 0.0, "b": 0.0})
        train = ast.parse(Path(learning.__file__).with_name("train.py").read_text())
        guard = next(
            n
            for n in ast.walk(train)
            if isinstance(n, ast.If) and "static_teacher else 8" in ast.unparse(n.test)
        )
        expr = compile(ast.Expression(guard.test), "actual-public-model-guard", "eval")
        for static, b, rejected in (
            (True, 0, False),
            (True, 8, True),
            (False, 8, False),
            (False, 0, True),
        ):
            cfg["model"]["distance_b"] = b
            self.assertEqual(
                eval(expr, dict(cfg=cfg, public_compact=True, static_teacher=static)), rejected
            )

    def test_label_marker_survives_exit_and_return_ref_failures(self):
        original = values.input_pairs
        original_ref = values.file_ref
        for stage in ("custody", "close", "return-ref", "success"):
            with self.subTest(stage=stage):
                cfg = {**self.config, "output": str(self.path / stage)}

                @contextmanager
                def reader(ref):
                    with original(ref) as data:
                        yield data
                        if stage == "custody":
                            raise OSError("final custody")
                    if stage == "close":
                        raise OSError("final reader close")

                def file_ref(path):
                    if stage == "return-ref" and Path(path).name == "teacher-values.json":
                        raise OSError("required return ref")
                    return original_ref(path)

                with (
                    patch.dict(sys.modules, {"torch": self.base.torch}),
                    patch.object(values, "StaticInputs", fixtures.FakeEncoder),
                    patch.object(values, "StaticHead", side_effect=AssertionError("NO HEAD ENTRY")),
                    patch.object(values, "input_pairs", reader),
                    patch.object(values, "file_ref", file_ref),
                ):
                    if stage == "success":
                        result = values.label_values(cfg)
                        self.assertTrue(Path(result["manifest"]["path"]).exists())
                    else:
                        with self.assertRaises(OSError):
                            values.label_values(cfg)
                root = Path(cfg["output"])
                self.assertEqual((root / "INCOMPLETE").exists(), stage != "success")
                if stage in ("custody", "close"):
                    self.assertFalse((root / "teacher-values.json").exists())
                if stage != "success":
                    self.assertTrue((root / "failure.json").exists())

    def test_work_facts_and_cuda_cleanup_preserve_structured_causes(self):
        class FailedHead:
            def __init__(self, *args, **kwargs):
                pass

            def __call__(self, inputs):
                raise ValueError("original work W")

            def facts(self):
                raise OSError("independent facts F")

        def cache_failure():
            raise OSError("independent CUDA C")

        import types

        self.base.torch.cuda = types.SimpleNamespace(empty_cache=cache_failure)
        cfg = {**self.base.config, "device": "cuda:0"}
        with (
            patch.dict(sys.modules, {"torch": self.base.torch}),
            patch.object(values, "StaticInputs", fixtures.FakeEncoder),
            patch.object(values, "StaticHead", FailedHead),
        ):
            with self.assertRaises(BaseExceptionGroup):
                values.qualify_values(cfg)
        failure = json.loads((self.path / "qualification/failure.json").read_bytes())
        self.assertEqual(
            [e["message"] for e in failure["errors"]],
            ["original work W", "independent facts F", "independent CUDA C"],
        )
        self.assertEqual(failure["logical_rows_attempted"], len(self.keys) + 1)
        # A separate fake partial bank checks label's actual except path without
        # executing any real head or repeating the successful old mock case.
        boundary = json.loads((self.path / "boundary.json").read_bytes())
        (self.path / "partial-keys").write_bytes(self.keys[:2].tobytes())
        boundary["keys"] = fixtures.ref(self.path / "partial-keys")
        for kind in ("S", "C"):
            np.zeros(2, dtype="<f4").tofile(self.path / ("partial-" + kind))
            boundary["batch_values"][kind] = fixtures.ref(self.path / ("partial-" + kind))
        (self.path / "partial-boundary.json").write_text(json.dumps(boundary))
        cfg = {**self.config, "runtime_boundary": fixtures.ref(self.path / "partial-boundary.json")}
        with (
            patch.dict(sys.modules, {"torch": self.base.torch}),
            patch.object(values, "StaticInputs", fixtures.FakeEncoder),
            patch.object(values, "StaticHead", FailedHead),
        ):
            with self.assertRaises(BaseExceptionGroup):
                values.label_values(cfg)
        failure = json.loads((self.path / "labels/failure.json").read_bytes())
        self.assertEqual(
            [e["message"] for e in failure["errors"]], ["original work W", "independent facts F"]
        )
        self.assertTrue((self.path / "labels/INCOMPLETE").exists())

    def test_validation_work_field_is_actual_rows_not_weighted_denominator(self):
        tree = ast.parse(Path(learning.__file__).with_name("train.py").read_text())
        expressions = [
            value
            for n in ast.walk(tree)
            if isinstance(n, ast.Dict)
            for key, value in zip(n.keys, n.values)
            if isinstance(key, ast.Constant) and key.value == "validation_forward_rows"
        ]
        self.assertEqual(len(expressions), 1)
        expr = compile(ast.Expression(expressions[0]), "actual-validation-work-field", "eval")
        for static, expected in ((True, 2), (False, 3)):
            self.assertEqual(
                eval(
                    expr,
                    dict(
                        static_teacher=static,
                        praw={"actual_logical_rows": 2},
                        evaluation_validation=[0, 0, 0],
                    ),
                ),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
