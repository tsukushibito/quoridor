"""Trainer observation, interruption and independent sampler contracts."""

import csv
from .sampling import ReflectionBatches, ConvergenceObservations, update_steps
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
    def test_visit_archive_range_and_irregular_indices_preserve_exact_int64_counts(self):
        from .train import write_sampling_counts

        counts = np.asarray([0, 149, 150, 2**40, 149, 0], dtype=np.int64)
        attempted = counts + np.asarray([0, 1, 0, 1, 0, 0], dtype=np.int64)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "counts.npz"
            for indices in [np.asarray([1, 2, 3, 4]), np.asarray([1, 3, 4])]:
                encoding = write_sampling_counts(path, indices, counts, attempted)
                with np.load(path, allow_pickle=False) as archive:
                    self.assertEqual(str(archive["schema"]), "quoridor-visit-counts-v2")
                    restored = (
                        np.arange(*archive["training_index_range"])
                        if encoding == "range"
                        else archive["training_indices"]
                    )
                    np.testing.assert_array_equal(restored, indices)
                    np.testing.assert_array_equal(archive["row_counts"], counts)
                    np.testing.assert_array_equal(archive["attempted_row_counts"], attempted)
                    self.assertEqual(archive["row_counts"].dtype, np.dtype("int64"))
            preserved = path.read_bytes()
            with patch(
                "quoridor_training.train.np.savez_compressed", side_effect=OSError("fixture")
            ):
                with self.assertRaisesRegex(OSError, "fixture"):
                    write_sampling_counts(path, indices, counts, attempted)
            self.assertEqual(path.read_bytes(), preserved)
            self.assertFalse(path.with_suffix(".npz.tmp").exists())

    def test_curve_stream_keeps_every_observation_and_preserves_prefix_on_encoding_failure(self):
        from .train import append_curve_record

        records = [
            {
                "step": step,
                "kind": "fixed_diagnostic",
                "used_for_selection": False,
                "validation": {"target_mse": np.float64(0.4 + step / 10000)},
            }
            for step in range(1000)
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagnostic-curves.jsonl.gz"
            for record in records:
                append_curve_record(path, record)
            with gzip.open(path, "rt") as stream:
                self.assertEqual([json.loads(line) for line in stream], records)
            preserved = path.read_bytes()
            with patch("quoridor_training.train.stream_json", side_effect=OSError("fixture")):
                with self.assertRaisesRegex(OSError, "fixture"):
                    append_curve_record(path, {"step": 1001})
            self.assertEqual(path.read_bytes(), preserved)
            self.assertFalse(path.with_suffix("").exists())

    def test_fixed_initial_weight_binding_rejects_a_different_or_missing_identity(self):
        from .cache import sha
        from .train import verify_initial_binding

        with tempfile.TemporaryDirectory() as temporary:
            weights = Path(temporary) / "weights.f32"
            weights.write_bytes(b"fixed-byte-fixture")
            binding = {"initial_weights_sha": sha(weights)}
            verify_initial_binding(binding, weights)
            weights.write_bytes(b"different-byte-fixture")
            with self.assertRaisesRegex(ValueError, "fixed qualified initialization"):
                verify_initial_binding(binding, weights)
            with self.assertRaisesRegex(ValueError, "fixed qualified initialization"):
                verify_initial_binding({}, weights)

    def test_diagnostic_csv_has_explicit_original_measurement_scopes(self):
        from .train import _curve_csv

        metrics = {"target_mse": 0.4, "target_game_equal_mse": 0.5, "rows": 3}
        point = {
            "step": 1,
            "kind": "fixed_diagnostic",
            "used_for_selection": False,
            "scope": "fixed_target_blind_subset",
            "train": metrics,
            "validation": metrics,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "curves.csv"
            _curve_csv([point], path)
            with path.open() as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["train_scope"], "fixed_diagnostic_subset")
            self.assertEqual(row["validation_scope"], "fixed_diagnostic_subset")
            self.assertEqual(row["used_for_selection"], "False")
            self.assertEqual(row["kind"], "fixed_diagnostic")
            self.assertEqual(row["validation_rows"], "3")
            _curve_csv([{**point, "step": 2}], path, append=True)
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row["step"] for row in rows], ["1", "2"])
            self.assertEqual(rows[0]["validation_scope"], rows[1]["validation_scope"])

    def test_train_only_reflection_keeps_shuffle_and_original_validation(self):
        from types import SimpleNamespace

        masks = []

        def batch(indices, mask=None):
            masks.append(None if mask is None else mask.copy())
            return np.asarray(indices).copy()

        corpus = SimpleNamespace(compact=True, splits=np.array([0] * 12 + [1] * 3), batch=batch)
        supply = ReflectionBatches(corpus, 0.5, 20261007)
        a = np.arange(6)
        np.testing.assert_array_equal(supply.batch(a, training=True), a)
        supply.batch([12, 13])
        supply.batch(np.arange(6, 12), training=True)
        np.testing.assert_array_equal(
            np.concatenate([masks[0], masks[2]]), np.random.default_rng(20261007).random(12) < 0.5
        )
        self.assertIsNone(masks[1])
        self.assertEqual(supply.training_seen, 12)
        with self.assertRaisesRegex(ValueError, "exclude validation"):
            supply.batch([12], training=True)
        from .sampling import EpochSampler

        left, right = (EpochSampler(np.arange(12), 6, 42), EpochSampler(np.arange(12), 6, 42))
        for _ in range(4):
            order = left.next_batch()
            supply.batch(order, training=True)
            np.testing.assert_array_equal(order, right.next_batch())

    def test_unbounded_updates_have_no_hidden_horizon(self):
        iterator = update_steps(None)
        self.assertEqual([next(iterator) for _ in range(5)], [1, 2, 3, 4, 5])
        self.assertEqual(list(update_steps(3)), [1, 2, 3])

    def test_unbounded_config_uses_null_caps_and_scientific_stopping(self):
        base = [
            "training.steps=null",
            "limits.samples=null",
            "limits.seconds=null",
            'evaluation.monitor="row"',
            'evaluation.early_stopping_unit="epoch"',
            "evaluation.full_train=false",
        ]
        resolved = resolve_config(overrides=base)
        self.assertIsNone(resolved["training"]["steps"])
        with self.assertRaisesRegex(ValueError, "scientific epoch"):
            resolve_config(overrides=base + ["evaluation.early_stopping_patience=0"])
        with self.assertRaisesRegex(ValueError, "finite update horizon"):
            resolve_config(overrides=base + ['training.scheduler="cosine"'])
        with self.assertRaisesRegex(ValueError, "separate fixed seed"):
            resolve_config(
                overrides=base
                + ["training.reflection_probability=0.5", "training.reflection_seed=19080311"]
            )

    def test_convergence_plan_does_not_select_dense_diagnostics_or_have_horizon(self):
        plan = ConvergenceObservations(100003, 1250, 5)
        self.assertEqual(plan.at(1, 128), (False, True, False))
        self.assertEqual(plan.at(25, 3200), (False, True, False))
        self.assertEqual(plan.at(782, 100003), (True, True, True))
        self.assertEqual(plan.at(1564, 200006), (True, True, False))
        self.assertEqual(plan.at(1000000, 100003 * 1278), (True, True, False))
        self.assertEqual(plan.at(2500, 319999), (False, True, False))

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
        self.assertLessEqual(max((b - a for a, b in zip(sorted(points), sorted(points)[1:]))), 25)
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
                "group": "t" + str(i % 2) if i < 5 else "v" + str(i % 2),
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
            return (x[indices].copy(), d[indices].copy(), labels[indices].copy())

        def chunks(indices=None, size=4096):
            if indices is None:
                indices = np.arange(len(self.rows))
            for first in range(0, len(indices), size):
                sub = indices[first : first + size]
                yield (sub, batch(sub))

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
            "optimizer": {"lr": 0.0001},
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
        return (p, cfg)

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
        return (output, result)

    def test_live_complete_tail_selected_and_whole_exposure(self):
        out, result = self.run_train("normal")
        sampling = json.loads((out / "sampling.json").read_text())
        self.assertEqual(sampling["seen"], 8)
        self.assertEqual(sampling["completed_epochs"], 1)
        self.assertEqual(sampling["partial_epoch_fraction"], 0.6)
        self.assertEqual(sampling["optimizer_steps"], 3)
        self.assertEqual(sum(sampling["row_counts"][5:]), 0)
        curve = [json.loads(line) for line in gzip.open(out / "curves.jsonl.gz", "rt")]
        chosen = next((p for p in curve if p["step"] == result["best_step"]))
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
        self.assertFalse((out / "curves.svg").exists())

    def test_live_budget_does_not_consume_next_tail(self):
        p, cfg = self.config("budget")
        cfg["evaluation"]["checkpoints"] = [0, 3]
        cfg["evaluation"]["diagnostic_rows"] = 0
        cfg["limits"]["samples"] = 11
        p.write_text(json.dumps(cfg))
        self.run_train("budget", p)
        out = self.root / "budget"
        sampling = json.loads((out / "sampling.json").read_text())
        self.assertEqual(sampling["seen"], 3)
        self.assertEqual(sampling["sampler_advanced_seen"], 3)
        self.assertEqual(sampling["completed_epochs"], 0)
        self.assertEqual(sampling["optimizer_steps"], 1)
        self.assertEqual(self.nn, 11)
        self.assertEqual(
            json.loads((out / "run-status.json").read_text())["status"], "BUDGET_STOPPED"
        )

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
            [json.loads(line) for line in gzip.open(verbose / "diagnostic-curves.jsonl.gz", "rt")][
                0
            ]["used_for_selection"],
            False,
        )


if __name__ == "__main__":
    unittest.main()
