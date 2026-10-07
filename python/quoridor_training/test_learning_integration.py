"""Maintained entry/glue contracts; no model, native library, fit or sealed labels."""

import ast
from contextlib import nullcontext, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from . import cache, cycle_process, train
from .common import resolve_config
from .compact_cache import CompactCorpus
from .public_features import RECORD, SCHEMA
from .test_public_sigma import fixture_cache


class IntegrationContracts(unittest.TestCase):
    def test_workers_are_explicit_zero_default_two_supported(self):
        self.assertEqual(resolve_config()["training"]["supply_workers"], 0)
        self.assertEqual(
            resolve_config(overrides=["training.supply_workers=2"])["training"]["supply_workers"], 2
        )
        for value in ("1", "4", "-1", "false", "true"):
            with self.assertRaises(ValueError):
                resolve_config(overrides=["training.supply_workers=" + value])

    def test_actual_CLI_routes_workers_without_loading_any_model(self):
        with (
            patch.object(train, "train", return_value={}) as fit,
            patch(
                "sys.argv",
                [
                    "train",
                    "train",
                    "--cache",
                    "unused",
                    "--output",
                    "unused",
                    "--supply-workers",
                    "2",
                ],
            ),
        ):
            train.main()
            self.assertEqual(fit.call_args.kwargs["supply_workers"], 2)
        with (
            patch.object(train, "guarded_train") as guarded,
            patch(
                "sys.argv",
                [
                    "train",
                    "train",
                    "--cache",
                    "unused",
                    "--output",
                    "unused",
                    "--guard-config",
                    "unused",
                    "--supply-workers",
                    "2",
                ],
            ),
            redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit):
                train.main()
            guarded.assert_not_called()
        with (
            patch.object(train, "prepare_statistics", return_value={}) as statistics,
            patch("sys.argv", ["train", "statistics", "--cache", "unused", "--output", "unused"]),
        ):
            train.main()
            statistics.assert_called_once_with("unused", "unused")

    def test_bound_worker_override_fails_before_corpus_or_model(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = Path(directory) / "config.json"
            cfg.write_text(json.dumps({"training": {"supply_workers": 2}}))
            with (
                patch.dict(sys.modules, {"torch": SimpleNamespace()}),
                patch.object(train, "load", side_effect=AssertionError("corpus must stay closed")),
                patch.object(train, "build_model", side_effect=AssertionError("no model")),
            ):
                with self.assertRaisesRegex(ValueError, "configured supply worker"):
                    train.train("unused", "unused", cfg, input_binding="unused", supply_workers=0)

    def test_cache_dispatch_uses_geometry_and_keeps_sealed_paths_unopened(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_cache(root)
            corpus = cache.load(root)
            self.assertIsInstance(corpus, CompactCorpus)
            self.assertEqual(corpus.manifest["schema"], SCHEMA)
            self.assertEqual(RECORD.itemsize, 66)
            self.assertEqual([p["name"] for p in corpus.descriptors], ["train", "validation"])
            x, distance, labels = corpus.batch([3, 0, 2])
            self.assertEqual((x.shape, x.dtype), ((3, 2, 312), np.dtype("float32")))
            self.assertEqual((distance.shape, distance.dtype), ((3, 2), np.dtype("float32")))
            np.testing.assert_array_equal(labels[:, 1], [-1, 1, 1])
            self.assertFalse((root / "test-sealed.bin").exists())
            self.assertFalse((root / "evaluation-opened.bin").exists())
            manifest = json.loads((root / "cache.json").read_text())
            manifest["schema"] = "quoridor-public-compact-v1"
            (root / "cache.json").write_text(json.dumps(manifest))
            with self.assertRaises((ValueError, KeyError)):
                cache.load(root)

    def test_core_entry_has_no_measurement_or_automatic_image_route(self):
        tree = ast.parse(Path(train.__file__).read_text())
        body = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train")
        self.assertNotIn("measurement", [a.arg for a in body.args.kwonlyargs])
        self.assertFalse(
            any(
                isinstance(n, ast.Name)
                and n.id
                in {"measurement", "measure", "render_learning_png", "render_learning_curves"}
                for n in ast.walk(body)
            )
        )
        for name in ("epoch_measurement", "sigma_reference", "guarded_statistics"):
            self.assertNotIn(name, {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})

    def test_null_deadline_keeps_actual_owned_resource_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            resource = cycle_process.CycleResources(
                {"max_memory_bytes": 1024**3, "max_output_bytes": 4096, "host_ram_reserve": 0},
                directory,
                None,
            )
            resource.check()
            resource.output_limit = 1
            (Path(directory) / "owned.txt").write_text("not empty")
            with self.assertRaisesRegex(cycle_process.CycleStopped, "output_limit"):
                resource.check()

    def test_guarded_caller_binds_null_deadline_and_fixed_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            admission = root / "storage.json"
            admission.write_text(json.dumps({"admission": "within", "errors": []}))
            cfg = root / "guard.json"
            cfg.write_text(
                json.dumps(
                    {
                        "expected_files_sha256": {},
                        "storage_admission": str(admission),
                        "output": str(root / "run"),
                        "seconds": None,
                        "resources": {},
                        "cache": "fixed-cache",
                        "fit_config": "fixed-config",
                        "input_binding": "fixed-binding",
                    }
                )
            )
            resources = SimpleNamespace(
                observed={}, controller_reserve=67108864, vram_limit=6442450944
            )
            with (
                patch.object(cycle_process, "GPUResources", return_value=resources),
                patch.object(cycle_process, "cancellation_signals", return_value=nullcontext()),
                patch.object(cycle_process, "execute", return_value={}) as execute,
                patch.object(train.os, "sched_setaffinity"),
            ):
                train.guarded_train(cfg)
            args = execute.call_args.args
            self.assertIsNone(args[2])
            self.assertEqual(
                args[0][-4:], ["--config", "fixed-config", "--input-binding", "fixed-binding"]
            )
            self.assertEqual(args[0][args[0].index("-m") + 1], "quoridor_training.train")


if __name__ == "__main__":
    unittest.main()
