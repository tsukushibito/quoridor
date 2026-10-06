"""Model-free export asset preservation fixtures; no framework/GPU is imported."""

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("model_export", Path(__file__).with_name("export.py"))
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="model-export-fixture-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.model = self.root / "model.bin"
        self.model.write_bytes(b"synthetic fixture, never a model")
        self.output = self.root / "sigma.engine"
        self.calls = []
        self.loads = []

    def run_export(self, backend="tensorrt", *, failure=None):
        def onnx_export(_exported, _args, filename, **_kwargs):
            self.calls.append(Path(filename))
            Path(filename).write_bytes(b"mock ONNX")
            if failure == "onnx":
                raise RuntimeError("mock ONNX failure")

        def package(_exported, *, package_path, **_kwargs):
            self.calls.append(Path(package_path))
            Path(package_path).write_bytes(b"mock AOTI")

        fake_model = SimpleNamespace(to=lambda _device: fake_model, eval=lambda: fake_model)
        torch = SimpleNamespace(
            __version__="mock",
            version=SimpleNamespace(cuda="mock"),
            set_num_threads=lambda _: None,
            set_float32_matmul_precision=lambda _: None,
            _inductor=SimpleNamespace(config=SimpleNamespace(), aoti_compile_and_package=package),
            backends=SimpleNamespace(
                cuda=SimpleNamespace(matmul=SimpleNamespace()), cudnn=SimpleNamespace()
            ),
            float32="float32",
            zeros=lambda *_, **__: "example",
            inference_mode=contextlib.nullcontext,
            export=SimpleNamespace(
                Dim=lambda *_, **__: "batch", export=lambda *_, **__: "exported"
            ),
            onnx=SimpleNamespace(export=onnx_export),
        )

        def load(path):
            self.loads.append(path)
            return fake_model

        folded = SimpleNamespace(
            MODEL_SHA=hashlib.sha256(self.model.read_bytes()).hexdigest(),
            load=load,
        )
        profile = SimpleNamespace(set_shape=lambda *args: None)
        config = SimpleNamespace(clear_flag=lambda _: None, add_optimization_profile=lambda _: None)
        builder = SimpleNamespace(
            create_network=lambda _: SimpleNamespace(
                get_input=lambda _: SimpleNamespace(name="raw")
            ),
            create_builder_config=lambda: config,
            create_optimization_profile=lambda: profile,
            build_serialized_network=lambda *_: None if failure == "build" else b"mock engine",
        )
        logger = type("Logger", (), {"WARNING": 1, "__init__": lambda *args: None})
        trt = SimpleNamespace(
            __version__="mock",
            Logger=logger,
            Builder=lambda _: builder,
            BuilderFlag=SimpleNamespace(TF32=1),
            OnnxParser=lambda *_: SimpleNamespace(
                parse=lambda _: failure != "parse",
                num_errors=1,
                get_error=lambda _: "mock parser failure",
            ),
        )
        argv = [
            "export.py",
            "--model",
            str(self.model),
            "--output",
            str(self.output),
            "--backend",
            backend,
        ]
        with (
            patch.object(sys, "argv", argv),
            patch.dict(sys.modules, {"torch": torch, "folded_sigma": folded, "tensorrt": trt}),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            EXPORT.main()

    def test_tensor_rt_preserves_sibling_onnx_and_publishes_bound_manifest(self):
        sibling = self.output.with_suffix(".onnx")
        sibling.write_bytes(b"valuable prior ONNX")
        self.run_export()
        self.assertEqual(sibling.read_bytes(), b"valuable prior ONNX")
        self.assertEqual(self.output.read_bytes(), b"mock engine")
        manifest = json.loads(EXPORT.manifest_path(self.output).read_text())
        self.assertEqual(manifest["artifact_sha256"], EXPORT.sha(self.output))
        self.assertEqual(manifest["artifact"], self.output.name)
        self.assertNotEqual(self.calls[0], sibling)
        self.assertFalse(self.calls[0].exists())
        self.assertEqual(list(self.root.glob(".quoridor-export-*")), [])

    def test_failures_preserve_sibling_and_clean_owned_temporary_files(self):
        sibling = self.output.with_suffix(".onnx")
        sibling.write_bytes(b"valuable prior ONNX")
        for failure in ("onnx", "parse", "build"):
            with self.subTest(failure=failure):
                with self.assertRaises(RuntimeError):
                    self.run_export(failure=failure)
                self.assertEqual(sibling.read_bytes(), b"valuable prior ONNX")
                self.assertFalse(self.output.exists())
                self.assertFalse(EXPORT.manifest_path(self.output).exists())
                self.assertEqual(list(self.root.glob(".quoridor-export-*")), [])

    def test_existing_artifact_manifest_or_dangling_symlink_refuses_before_export(self):
        for path in (self.output, EXPORT.manifest_path(self.output)):
            for symlink in (False, True):
                with self.subTest(path=path.name, symlink=symlink):
                    if symlink:
                        path.symlink_to(self.root / "missing")
                    else:
                        path.write_bytes(b"preserve me")
                    with self.assertRaises(SystemExit):
                        self.run_export()
                    self.assertEqual(self.calls, [])
                    self.assertEqual(self.loads, [])
                    if not symlink:
                        self.assertEqual(path.read_bytes(), b"preserve me")
                    path.unlink()

    def test_tensor_rt_onnx_output_refuses_before_export(self):
        self.output = self.root / "sigma.onnx"
        with self.assertRaises(SystemExit):
            self.run_export()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.loads, [])
        self.assertFalse(self.output.exists())

    def test_every_backend_uses_staging_even_for_manifest_named_artifact(self):
        for backend in ("onnx", "aoti"):
            with self.subTest(backend=backend):
                self.output = self.root / backend / "manifest.json"
                self.run_export(backend)
                self.assertIn(self.output.read_bytes(), (b"mock ONNX", b"mock AOTI"))
                self.assertEqual(
                    json.loads(EXPORT.manifest_path(self.output).read_text())["backend"], backend
                )

    def test_publication_race_preserves_existing_destinations(self):
        artifact = self.root / "staged-artifact"
        manifest = self.root / "staged-manifest"
        artifact.write_bytes(b"new artifact")
        manifest.write_bytes(b"new manifest")
        self.output.write_bytes(b"existing artifact")
        with self.assertRaises(FileExistsError):
            EXPORT.publish_exports(artifact, manifest, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing artifact")
        self.output.unlink()
        EXPORT.manifest_path(self.output).write_bytes(b"existing manifest")
        with self.assertRaises(FileExistsError):
            EXPORT.publish_exports(artifact, manifest, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(EXPORT.manifest_path(self.output).read_bytes(), b"existing manifest")


if __name__ == "__main__":
    unittest.main()
