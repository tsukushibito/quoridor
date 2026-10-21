"""Affected configurable-mixture NN0 fixtures; no assets/model forwards/fit."""

import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class MixtureBoundaries(unittest.TestCase):
    def settings(self):
        from quoridor_training.common import (
            DEFAULTS,
            BEST43_DESCRIPTOR,
            BEST43_WEIGHTS,
            BEST43_EVALUATOR,
        )

        cfg = copy.deepcopy(DEFAULTS)
        cfg["optimizer"].update(betas=[0.9, 0.999], eps=1e-8)
        cfg["model"].update(architecture="distance_residual", distance_a=0.0, distance_b=0.0)
        cfg["training"].update(
            target="z",
            batch_size=7,
            steps=12,
            reflection_probability=0.0,
            warmup_steps=3,
        )
        cfg["evaluation"].update(
            monitor="row", diagnostic_rows=3, interval=4, early_stopping_patience=2
        )
        cfg["artifacts"]["mode"] = "native"
        cfg["limits"].update(seconds=None, samples=1000)

        def ref(digest):
            return {
                "path": "/synthetic/never-read",
                "sha256": digest,
                "bytes": 1,
                "mode": "0644",
            }

        cfg["experiment"].update(
            study="mixed-outcome",
            warm_start={
                "descriptor": ref(BEST43_DESCRIPTOR),
                "weights": ref(BEST43_WEIGHTS),
                "evaluator_sha256": BEST43_EVALUATOR,
                "optimizer": "fresh",
                "scale": "incumbent",
            },
        )
        cfg["mixture"] = {
            "train_family_row_cap": None,
            "train_stock_strata": None,
            "added_sampling_seed": cfg["training"]["seed"],
            "added_rows": 3,
            "public_rows": 4,
            "added_exposures": 2.0,
            "public_sampling_seed": 21,
            "added_reflection_probability": 0.5,
            "added_reflection_seed": 31,
            "public_reflection_probability": 0.25,
            "public_reflection_seed": 32,
            "diagnostic_seed": 41,
            "public_membership": ref("a" * 64),
            "public_acceptance": ref("b" * 64),
            "selector": {"public_non_regression": False, "added_metric": "mse"},
            "output_limit_bytes": 1024**2,
        }
        return cfg

    def test_explicit_configuration_frozen_initializer_and_scale(self):
        from quoridor_training.common import resolve_config

        cfg = self.settings()
        self.assertEqual(resolve_config(cfg), cfg)
        for section, key, value in (
            ("mixture", "train_family_row_cap", False),
            ("mixture", "added_rows", 4),
            ("mixture", "selector", {}),
            ("mixture", "added_exposures", float("inf")),
            ("training", "steps", None),
            ("training", "target", "completed_root_raw"),
            ("model", "distance_b", 8.0),
            ("experiment", "study", "public-replay-v1"),
        ):
            bad = copy.deepcopy(cfg)
            bad[section][key] = value
            with self.assertRaises(ValueError):
                resolve_config(bad)
        for key in cfg["mixture"]:
            bad = copy.deepcopy(cfg)
            del bad["mixture"][key]
            with self.assertRaises(ValueError):
                resolve_config(bad)
        for key, value in (("scale", "new_T"), ("optimizer", "resume")):
            bad = copy.deepcopy(cfg)
            bad["experiment"]["warm_start"][key] = value
            with self.assertRaises(ValueError):
                resolve_config(bad)
        with self.assertRaises(ValueError):
            resolve_config(cfg, ("training.batch_size=64",))

    def test_family_cap_chronology_endpoints_and_split_isolation(self):
        import numpy as np
        from quoridor_training.sampling import family_training_view

        groups = np.array([0] * 130 + [1] * 4 + [2] * 3)
        splits = np.array([0] * 134 + [1] * 3)
        eligible = np.ones(137, dtype=bool)
        eligible[3] = False
        allrows = family_training_view(groups, splits, eligible, None)
        self.assertEqual(allrows.tolist(), [i for i in range(134) if i != 3])
        view = family_training_view(groups, splits, eligible, 64)
        expected = [i for i in range(130) if i != 3]
        self.assertEqual(
            view[:64].tolist(), [expected[j * (len(expected) - 1) // 63] for j in range(64)]
        )
        self.assertEqual(view[64:].tolist(), list(range(130, 134)))
        self.assertEqual(family_training_view(groups, splits, eligible, 1).tolist(), [0, 130])
        leaked = splits.copy()
        leaked[1] = 1
        with self.assertRaises(ValueError):
            family_training_view(groups, leaked, eligible, None)
        with self.assertRaises(ValueError):
            family_training_view(groups, splits, eligible, 0)

    def test_source_counts_loss_and_independent_reflection_streams(self):
        import numpy as np
        from quoridor_training.public_replay import mixed_batch, mixed_row_loss

        seen = []

        class Added:
            row_count = 5
            splits = np.array([0, 0, 0, 1, 0])
            eligible = np.array([True, True, True, True, False])

            def batch(self, indices, mask=None):
                seen.append(("added", indices.copy(), mask.copy()))
                n = len(indices)
                labels = np.zeros((n, 4), dtype=np.float32)
                labels[:, 1] = [-1, 0, 1][:n]
                labels[:, 3] = 2.0
                return (
                    np.zeros((n, 2, 312), dtype=np.float32),
                    np.ones((n, 2), dtype=np.float32),
                    labels,
                )

        class Public:
            def batch(self, split, indices, mask=None, training=False):
                assert split == "train" and training
                seen.append(("public", indices.copy(), mask.copy()))
                n = len(indices)
                return (
                    np.zeros((n, 2, 312), dtype=np.float32),
                    np.ones((n, 2), dtype=np.float32),
                    np.ones(n, dtype=np.float32),
                )

        a, p = Added(), Public()
        ar = np.random.default_rng(31)
        pr = np.random.default_rng(32)
        am = ar.random(3) < 0.5
        pm = pr.random(4) < 0.25
        x, d, y = mixed_batch(
            a,
            p,
            np.array([0, 1, 2]),
            np.array([2, 1, 0, 1]),
            np.concatenate((am, pm)),
            target_column=1,
        )
        self.assertEqual(x.shape, (7, 2, 312))
        self.assertEqual(y.tolist(), [-1, 0, 1, 1, 1, 1, 1])
        self.assertTrue(np.array_equal(seen[0][2], am))
        self.assertTrue(np.array_equal(seen[1][2], pm))
        # Raw=+2 deliberately does not mask an admitted outcome row.
        for bad in (np.array([3]), np.array([4])):
            with self.assertRaises(ValueError):
                mixed_batch(
                    a,
                    p,
                    bad,
                    np.array([], dtype=np.int64),
                    np.zeros(1, dtype=bool),
                    target_column=1,
                )
        # Real NumPy objective arithmetic, explicit fake framework port, zero forwards.
        fake = SimpleNamespace(float32=np.dtype("float32"), mean=np.mean)
        with patch.dict(sys.modules, {"torch": fake}):
            prediction = np.zeros(7, dtype=np.float32)
            self.assertAlmostEqual(float(mixed_row_loss(prediction, y)), 6 / 7, places=6)
            with self.assertRaises(ValueError):
                mixed_row_loss(prediction, y[:-1])
        # Independent source consumption preserves the same added-mask prefix.
        a1 = np.random.default_rng(31)
        a2 = np.random.default_rng(31)
        self.assertTrue(
            np.array_equal(a1.random(9), np.concatenate([a2.random(3) for _ in range(3)]))
        )

    def test_full_batch_tails_forward_plan_and_empty_splits(self):
        import numpy as np
        from quoridor_training.sampling import FullBatchSampler
        from quoridor_training.public_replay import planned_work

        first = FullBatchSampler(np.arange(5), 3, 6)
        second = FullBatchSampler(np.arange(5), 8, 6)
        self.assertTrue(
            np.array_equal(np.concatenate([first.take(3) for _ in range(4)]), second.take(12))
        )
        self.assertEqual(first.seen, 12)
        self.assertEqual(first.completed_epochs, 2)
        cfg = self.settings()
        plan = planned_work(cfg, 5, 2, {"train": 20, "validation": 8})
        self.assertEqual(
            plan,
            {
                "updates": 4,
                "observation_steps": [0, 4],
                "added_rows": 12,
                "public_rows": 16,
                "training_forwards": 28,
                "measurement_forwards": 32,
                "forward_upper": 60,
                "measurement_rows_per_observation": 16,
            },
        )
        for t, v, public in (
            (0, 2, {"train": 20, "validation": 8}),
            (5, 0, {"train": 20, "validation": 8}),
            (5, 2, {"train": 0, "validation": 8}),
        ):
            with self.assertRaises(ValueError):
                planned_work(cfg, t, v, public)

    def test_device_placement_uses_current_shared_gpu_port_nn0(self):
        import numpy as np
        from quoridor_training.train import outcome_inputs, configure_framework

        calls = []

        class Tensor:
            def to(self, device):
                calls.append(device)
                return self

        fake = SimpleNamespace(
            from_numpy=lambda v: Tensor(),
            ones=lambda n, **kw: (calls.append((n, kw)), Tensor())[1],
            long="fake-long",
        )
        with patch.dict(sys.modules, {"torch": fake}):
            out = outcome_inputs(
                np.zeros((7, 2, 312), dtype=np.float32), np.zeros((7, 2), dtype=np.float32), "cuda"
            )
        self.assertEqual(len(out), 3)
        self.assertEqual(calls, ["cuda", "cuda", (7, {"dtype": "fake-long", "device": "cuda"})])
        setup = []
        cuda = SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True))
        fake = SimpleNamespace(
            set_num_threads=lambda n: setup.append(n),
            get_num_interop_threads=lambda: 1,
            set_num_interop_threads=lambda n: setup.append(n),
            manual_seed=lambda seed: setup.append(seed),
            use_deterministic_algorithms=lambda v: setup.append(v),
            backends=SimpleNamespace(cuda=cuda, cudnn=SimpleNamespace(allow_tf32=True)),
            cuda=SimpleNamespace(
                mem_get_info=lambda: (8 * 1024**3, 8 * 1024**3),
                set_per_process_memory_fraction=lambda v: setup.append(v),
                manual_seed_all=lambda s: setup.append(s),
            ),
        )
        cfg = self.settings()
        cfg["training"]["device"] = "cuda"
        with patch.dict(sys.modules, {"torch": fake}):
            self.assertEqual(configure_framework(cfg), "cuda")
        self.assertFalse(fake.backends.cuda.matmul.allow_tf32)
        self.assertFalse(fake.backends.cudnn.allow_tf32)
        self.assertIn(cfg["training"]["seed"], setup)

    def test_selector_gate_earlystop_and_strict_ties(self):
        from quoridor_training.public_replay import Selector

        gate = Selector(True, 2, 0.00001, 0.0001)
        open_selector = Selector(False, 2, 0.00001, 0.0001)
        for s in (gate, open_selector):
            self.assertEqual(s.observe(0, 1.0, 1.0), (False, False))
        self.assertEqual(gate.observe(2, 0.9, 1.1), (False, False))
        self.assertEqual(open_selector.observe(2, 0.9, 1.1), (True, False))
        self.assertEqual(gate.observe(4, 0.8, 0.99), (True, False))
        self.assertEqual(gate.observe(6, 0.8, 0.98), (False, False))
        self.assertEqual(gate.observe(8, 0.8, 0.98), (False, True))
        self.assertEqual(gate.best_step, 4)
        with self.assertRaises(ValueError):
            gate.observe(9, float("nan"), 1.0)

    def test_all_work_output_cancel_and_partial_finalizer_semantics(self):
        from quoridor_training.public_replay import WorkBudget
        from quoridor_training.train import _finalize_training
        from quoridor_runtime.cycle_process import CycleStopped, cancellation_signals
        import signal

        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            root = Path(directory)
            b = WorkBudget(10, None, root, 1024**2)
            b.charge(7, training=True)
            b.charge(3)
            with self.assertRaises(ValueError):
                b.charge(1)
            self.assertEqual((b.training, b.measurement), (7, 3))
            low = WorkBudget(10, None, root, 1)
            with self.assertRaises(CycleStopped):
                low.check()
            with cancellation_signals():
                with self.assertRaises(CycleStopped):
                    signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            primary = ValueError("synthetic partial stop after last known update")
            save_error = OSError("synthetic LAST save incomplete")
            attempts = []

            def save():
                attempts.append("LAST")
                raise save_error

            def result():
                attempts.append("result")
                (root / "partial.json").write_text(
                    json.dumps(
                        {
                            "status": "FAILED",
                            "step": 3,
                            "INITIAL": "immutable reference",
                            "BEST": 2,
                            "LAST": "UNKNOWN",
                        }
                    )
                )

            def cleanup():
                attempts.append("cleanup")

            with self.assertRaises(BaseExceptionGroup) as error:
                _finalize_training(
                    root,
                    [("LAST", save), ("result", result), ("cleanup", cleanup)],
                    primary,
                    lambda: {"step": 3},
                )
            self.assertIs(error.exception.exceptions[0], primary)
            self.assertIs(error.exception.exceptions[1], save_error)
            self.assertEqual(attempts, ["LAST", "result", "cleanup"])
            self.assertEqual(json.loads((root / "partial.json").read_bytes())["LAST"], "UNKNOWN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    TMP = args.TMP
    import quoridor_training

    quoridor_training.__path__.insert(0, str(args.source))
    for module in ("common", "sampling", "train", "public_replay"):
        sys.modules.pop("quoridor_training." + module, None)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(MixtureBoundaries)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forward_rows": 0,
                "fit_updates": 0,
                "synthetic_arrays_framework_and_metadata": True,
                "failures": [s for _, s in result.failures],
                "errors": [s for _, s in result.errors],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
