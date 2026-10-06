"""Trainer observation, interruption and independent sampler contracts."""

import json
import gzip
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from .common import resolve_config
from .sampling import diagnostic_indices, exposure, observation_steps, EarlyStopping


class ObservationContracts(unittest.TestCase):
    def test_target_blind_stable_subset_does_not_use_numpy_rng(self):
        rows = [{"id": str(i), "z": i % 2} for i in range(12)]
        state = np.random.get_state()
        left = diagnostic_indices(rows, range(12), 4, 42)
        for row in rows:
            row["z"] = None
        right = diagnostic_indices(rows, range(12), 4, 42)
        np.testing.assert_array_equal(left, right)
        now = np.random.get_state()
        np.testing.assert_array_equal(state[1], now[1])
        self.assertEqual(state[2:], now[2:])

    def test_dense_points_epoch_ends_and_explicit_override(self):
        points = observation_steps(400, 25, 14803, 128, "epoch")
        self.assertTrue({0, 1, 2, 5, 10, 20, 116, 232, 348, 400} <= points)
        self.assertLessEqual(max(b - a for a, b in zip(sorted(points), sorted(points)[1:])), 25)
        self.assertEqual(observation_steps(40, 25, 10, 3, "epoch", [0, 40]), {0, 40})

    def test_attempted_tail_is_not_completed_exposure(self):
        self.assertEqual(exposure(3, 5, "epoch")["completed_epochs"], 0)
        self.assertEqual(exposure(3, 5, "epoch")["partial_epoch_fraction"], 0.6)
        self.assertEqual(exposure(5, 5, "epoch")["completed_epochs"], 1)
        self.assertIsNone(exposure(5, 5, "game")["completed_epochs"])

    def test_patience_counts_full_measurements_zero_disabled(self):
        stopper = EarlyStopping(2, 0.01)
        self.assertEqual(stopper.observe(1), (True, False))
        self.assertEqual(stopper.observe(0.995), (False, False))
        self.assertEqual(stopper.observe(0.996), (False, True))
        disabled = EarlyStopping(0, 0)
        self.assertFalse(disabled.observe(1)[1])
        self.assertFalse(disabled.observe(2)[1])

    def test_steps_override_revalidates_checkpoint_ranges(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "config.json"
            p.write_text(
                json.dumps({"training": {"steps": 10}, "evaluation": {"checkpoints": [0, 10]}})
            )
            with self.assertRaisesRegex(ValueError, "checkpoints"):
                resolve_config(p, ["training.steps=5"])

    def test_subset_cannot_export_full_row_scalar_order(self):
        with self.assertRaisesRegex(ValueError, "full-row"):
            resolve_config(
                overrides=["evaluation.full_train=false", "artifacts.save_scheduled=true"]
            )


@unittest.skipUnless(
    os.environ.get("QUORIDOR_OBSERVATION_LIVE_TESTS") == "1", "explicit admitted tiny NN job only"
)
class LiveTrainerObservation(unittest.TestCase):
    """Synthetic input only; every model call contributes to the admitted NN cap."""

    def setUp(self):
        import torch
        from . import train as trainer

        self.torch = torch
        self.trainer = trainer
        self.temp = tempfile.TemporaryDirectory(dir=os.environ["QUORIDOR_OBSERVATION_TEST_ROOT"])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = [
            {
                "id": str(i),
                "group": ("t" + str(i % 2) if i < 5 else "v" + str(i % 2)),
                "split": "train" if i < 5 else "validation",
                "primary_eligible": True,
                "teacher_type": "native_terminal_outcome",
                "rootmean": None,
                "z": float(1 if i % 2 else -1),
            }
            for i in range(8)
        ]
        x = np.zeros((8, 2, 312), dtype=np.float32)
        x[:, :, 0] = 1
        d = np.tile(np.asarray([0.1, 0.15], dtype=np.float32), (8, 1))
        labels = np.asarray([[np.nan, r["z"]] for r in self.rows], dtype=np.float32)
        from types import SimpleNamespace

        class FixtureRows(list):
            def iter_indices(self, indices):
                return (self[int(i)] for i in indices)

        def batch(indices):
            return x[indices].copy(), d[indices].copy(), labels[indices].copy()

        def chunks(indices=None, size=4096):
            if indices is None:
                indices = np.arange(len(self.rows))
            for first in range(0, len(indices), size):
                sub = indices[first : first + size]
                yield sub, batch(sub)

        fixture = SimpleNamespace(
            binding={"dataset_sha": "synthetic-observation-input-v1"},
            rows=FixtureRows(self.rows),
            row_count=8,
            labels=labels,
            groups=np.asarray([0, 1, 0, 1, 0, 2, 3, 2], dtype=np.uint32),
            families=["t0", "t1", "v1", "v0"],
            splits=np.asarray([0] * 5 + [1] * 3),
            eligible=np.ones(8, dtype=bool),
            batch=batch,
            chunks=chunks,
            verify_binding=lambda: None,
        )
        self.load_patch = patch.object(trainer, "load", return_value=fixture)
        self.load_patch.start()
        self.addCleanup(self.load_patch.stop)
        self.nn = 0
        self.original_build = trainer.build_model

    def tearDown(self):
        path = Path(os.environ["QUORIDOR_OBSERVATION_TEST_ROOT"]) / "nn-ledger.jsonl"
        with path.open("a") as stream:
            stream.write(json.dumps({"test": self.id(), "model_rows": self.nn}) + "\n")

    def config(self, name, **evaluation):
        cfg = {
            "model": {
                "architecture": "distance_residual",
                "transformer_width": 32,
                "hidden_width": 32,
            },
            "training": {"steps": 3, "batch_size": 3, "target": "z", "sampling": "epoch"},
            "optimizer": {"lr": 1e-4},
            "evaluation": {
                "checkpoints": [0, 1, 2, 3],
                "diagnostic_rows": 2,
                "diagnostic_checkpoints": [0, 1, 2, 3],
                "early_stopping_patience": 0,
                **evaluation,
            },
            "artifacts": {"mode": "native"},
            "limits": {"samples": 200, "seconds": 20},
        }
        p = self.root / (name + ".json")
        p.write_text(json.dumps(cfg))
        return p, cfg

    def build_counted(self, *args):
        model = self.original_build(*args)

        def charge(module, inputs):
            self.nn += len(inputs[0])
            if self.nn > 250:
                raise AssertionError("per-test NN guard250")

        model.register_forward_pre_hook(charge)
        return model

    def run_train(self, name, config=None):
        if config is None:
            config, _ = self.config(name)
        output = self.root / name
        with patch.object(self.trainer, "build_model", side_effect=self.build_counted):
            result = self.trainer.train("synthetic-only", output, config)
        return output, result

    def test_live_complete_tail_selected_and_whole_exposure(self):
        out, result = self.run_train("normal")
        sampling = json.loads((out / "sampling.json").read_text())
        self.assertEqual(sampling["seen"], 8)
        self.assertEqual(sampling["completed_epochs"], 1)
        self.assertEqual(sampling["partial_epoch_fraction"], 0.6)
        self.assertEqual(sampling["optimizer_steps"], 3)
        self.assertEqual(sum(sampling["row_counts"][5:]), 0)
        curve = json.loads((out / "curves.json").read_text())
        chosen = next(p for p in curve if p["step"] == result["best_step"])
        self.assertEqual(result["selected_exposure"]["training_seen"], chosen["training_seen"])
        self.assertEqual(result["training_seen"], 8)
        records = [
            json.loads(line) for line in gzip.open(out / "batch.jsonl.gz", "rt").read().splitlines()
        ]
        self.assertEqual(
            [p["batch_rows"] for p in records if p["status"] == "COMPLETED"], [3, 2, 3]
        )
        self.assertEqual(self.nn, 40)
        self.assertTrue((out / "curves.csv").exists())
        self.assertTrue((out / "curves.svg").exists())

    def test_live_budget_does_not_consume_next_tail(self):
        p, cfg = self.config("budget")
        cfg["evaluation"]["checkpoints"] = [0, 3]
        cfg["evaluation"]["diagnostic_rows"] = 0
        cfg["limits"]["samples"] = 11  # initial8 + successful batch3; tail cannot enter.
        p.write_text(json.dumps(cfg))
        with self.assertRaisesRegex(RuntimeError, "budget"):
            self.run_train("budget", p)
        out = self.root / "budget"
        sampling = json.loads((out / "sampling.json").read_text())
        self.assertEqual(sampling["seen"], 3)
        self.assertEqual(sampling["sampler_advanced_seen"], 3)
        self.assertEqual(sampling["completed_epochs"], 0)
        self.assertEqual(sampling["optimizer_steps"], 1)
        self.assertEqual(self.nn, 11)
        self.assertEqual(json.loads((out / "run-status.json").read_text())["status"], "INTERRUPTED")

    def test_live_optimizer_fault_preserves_completed_counts(self):
        p, cfg = self.config("fault")
        cfg["evaluation"]["checkpoints"] = [0, 3]
        cfg["evaluation"]["diagnostic_rows"] = 0
        p.write_text(json.dumps(cfg))
        original = self.torch.optim.Adam.step
        calls = 0

        def broken(optimizer, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("synthetic-tail-step-failure")
            return original(optimizer, *args, **kwargs)

        with patch.object(self.torch.optim.Adam, "step", new=broken):
            with self.assertRaisesRegex(RuntimeError, "synthetic-tail"):
                self.run_train("fault", p)
        out = self.root / "fault"
        state = json.loads((out / "run-status.json").read_text())
        sample = json.loads((out / "sampling.json").read_text())
        self.assertEqual(state["training_seen"], 3)
        self.assertEqual(state["step"], 1)
        self.assertEqual(sample["sampler_advanced_seen"], 5)
        self.assertEqual(sum(sample["attempted_row_counts"]), 5)
        self.assertEqual(state["model_state_status"], "UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN")
        self.assertEqual(self.nn, 13)
        self.assertTrue((out / "diagnostic-curves.csv").exists())

    def test_live_diagnostics_preserve_sampling_initial_and_final_parameters(self):
        p, cfg = self.config("quiet")
        cfg["evaluation"]["checkpoints"] = [0, 3]
        cfg["evaluation"]["diagnostic_rows"] = 0
        p.write_text(json.dumps(cfg))
        quiet, _ = self.run_train("quiet", p)
        # Same full selectors, extra fixed diagnostics consume no sampler/model RNG.
        q, cfg = self.config("verbose")
        cfg["evaluation"]["checkpoints"] = [0, 3]
        q.write_text(json.dumps(cfg))
        verbose, _ = self.run_train("verbose", q)
        for name in ["initial-model", "last-model"]:
            self.assertEqual(
                (quiet / name / "weights.f32").read_bytes(),
                (verbose / name / "weights.f32").read_bytes(),
            )
        left = json.loads((quiet / "sampling.json").read_text())
        right = json.loads((verbose / "sampling.json").read_text())
        self.assertEqual(left["row_counts"], right["row_counts"])
        self.assertEqual(self.nn, 24 + 32)
        self.assertEqual(
            json.loads((verbose / "diagnostic-curves.json").read_text())[0]["used_for_selection"],
            False,
        )


if __name__ == "__main__":
    unittest.main()
