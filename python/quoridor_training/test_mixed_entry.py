"""New configured fit wiring fixture with fake framework/model; NN0, zero fit."""

import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ConfiguredEntry(unittest.TestCase):
    def test_configured_loop_checkpoints_actual_counters_and_partial_stop_nn0(self):
        import numpy as np
        from quoridor_training import public_replay as mix, train
        from quoridor_training.test_public_replay import MixtureBoundaries

        cfg = MixtureBoundaries().settings()
        cfg["training"]["steps"] = 2
        cfg["evaluation"].update(interval=1, early_stopping_patience=0)
        cfg["mixture"]["added_exposures"] = 10
        cfg["limits"]["samples"] = 1000
        calls = []

        class Tensor:
            def __init__(self, x):
                self.x = np.asarray(x, dtype=np.float32)

            @property
            def shape(self):
                return self.x.shape

            @property
            def ndim(self):
                return self.x.ndim

            @property
            def dtype(self):
                return self.x.dtype

            def __len__(self):
                return len(self.x)

            def to(self, device):
                calls.append(("device", device))
                return self

            def reshape(self, *shape):
                return Tensor(self.x.reshape(*shape))

            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.x

            def backward(self):
                calls.append(("fake_backward",))

            def __sub__(self, other):
                return Tensor(self.x - other.x)

            def __pow__(self, n):
                return Tensor(self.x**n)

        class FakeModel:
            def to(self, device):
                calls.append(("model_device", device))
                return self

            def train(self):
                pass

            def eval(self):
                pass

            def __call__(self, *args):
                calls.append(("synthetic_model_call_rows", len(args[0])))
                return Tensor(np.zeros(len(args[0]), dtype=np.float32))

            def parameters(self):
                return []

            def state_dict(self):
                return {"synthetic_only": True}

        class Optimizer:
            def __init__(self, *args, **kw):
                calls.append(("fresh_fake_optimizer", kw))
                self.param_groups = [{}]

            def zero_grad(self, **kw):
                pass

            def step(self):
                calls.append(("fake_update",))

            def state_dict(self):
                return {"synthetic_only": True}

        class Context:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        def save(data, path):
            calls.append(("checkpoint", Path(path).name, data["step"]))
            Path(path).write_text(json.dumps({"step": data["step"], "synthetic_checkpoint": True}))

        fake = SimpleNamespace(
            float32=np.dtype("float32"),
            long="fake-long",
            from_numpy=lambda v: Tensor(v),
            ones=lambda n, **kw: Tensor(np.ones(n)),
            isfinite=lambda v: np.isfinite(v.x),
            mean=lambda v: Tensor(np.mean(v.x)),
            no_grad=Context,
            optim=SimpleNamespace(Adam=Optimizer),
            save=save,
        )

        class Added:
            row_count = 6
            manifest_sha = "synthetic-cache-only"
            groups = np.array([0, 0, 0, 1, 1, 1])
            splits = np.array([0, 0, 0, 1, 1, 1])
            eligible = np.ones(6, dtype=bool)
            families = ["fake-T", "fake-V"]
            labels = np.array(
                [
                    [0, -1, 0, 2],
                    [0, 0, 0, -2],
                    [0, 1, 0, 2],
                    [0, 1, 0, 2],
                    [0, 0, 0, -2],
                    [0, -1, 0, 2],
                ],
                dtype=np.float32,
            )
            rows = [{"id": str(i)} for i in range(6)]

            def batch(self, indices, mask=None):
                n = len(indices)
                return (
                    np.zeros((n, 2, 312), dtype=np.float32),
                    np.ones((n, 2), dtype=np.float32),
                    self.labels[indices],
                )

            def verify_binding(self):
                calls.append(("added_after",))

        class Public:
            def batch(self, split, indices, mask=None, training=False):
                if training:
                    assert split == "train"
                n = len(indices)
                return (
                    np.zeros((n, 2, 312), dtype=np.float32),
                    np.ones((n, 2), dtype=np.float32),
                    np.ones(n, dtype=np.float32),
                )

            def verify_binding(self):
                calls.append(("public_after",))

            def close(self):
                calls.append(("public_close",))

        def exporting(model, config, statistics, fit, path):
            path.mkdir(exist_ok=True)
            file = path / "manifest.json"
            file.write_text(json.dumps({"synthetic_export": True}))
            return file

        warm = {"descriptor": {"synthetic_only": True}, "weights": {"path": "synthetic-not-opened"}}

        def admitted(*a):
            return (
                {},
                {},
                {"train": 5, "validation": 4},
                {"warm_start": warm, "statistics": {"mu_f32": [0.1, 0.2], "sigma_f32": [0.3, 0.4]}},
            )

        def install():
            return (
                patch.dict(
                    sys.modules,
                    {
                        "torch": fake,
                        "quoridor_training.compact_cache": SimpleNamespace(
                            IndexedPublicCorpus=lambda *a: Public()
                        ),
                        "quoridor_training.terminal_cache": SimpleNamespace(
                            TerminalCorpus=lambda *a: Added()
                        ),
                    },
                ),
                patch.object(mix, "admit", admitted),
                patch.object(train, "configure_framework", lambda c: "cuda"),
                patch.object(train, "build_model", lambda *a: FakeModel()),
                patch.object(
                    train,
                    "restore_warmstart_parameters",
                    lambda *a: calls.append(("initializer_unchanged_port",)),
                ),
                patch.object(train, "verify_native_parameters", lambda *a: None),
                patch.object(train, "export", exporting),
            )

        from contextlib import ExitStack

        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text(json.dumps(cfg))
            with ExitStack() as stack:
                for item in install():
                    stack.enter_context(item)
                result = mix.train_mixture("synthetic", root / "complete", config, None, cfg)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["step"], 2)
            self.assertEqual((result["added_seen"], result["public_seen"]), (6, 8))
            self.assertEqual(result["training_forwards"], 14)
            # Three full observations: addedT3+addedV3+publicT3+publicV4.
            self.assertEqual(result["measurement_forwards"], 39)
            self.assertEqual([p["step"] for p in result["curves"]], [0, 1, 2])
            self.assertEqual(result["initial_reference"], warm)
            self.assertEqual(result["best_step"], 0)
            self.assertIn(("checkpoint", "last.pt", 2), calls)
            self.assertFalse((root / "complete/INCOMPLETE").exists())
            self.assertEqual(
                json.loads((root / "complete/scale.json").read_bytes()),
                {"mu_f32": [0.1, 0.2], "sigma_f32": [0.3, 0.4]},
            )
            self.assertEqual(sum(c[0] == "fresh_fake_optimizer" for c in calls), 1)
            self.assertEqual(sum(c[0] == "public_close" for c in calls), 1)
            # Real mixed finalizer path after an incomplete configured forward ceiling;
            # it retains INITIAL/LAST0 and FAILED/marker, then closes public exactly once.
            calls.clear()
            bad = copy.deepcopy(cfg)
            bad["limits"]["samples"] = 1
            with ExitStack() as stack:
                for item in install():
                    stack.enter_context(item)
                with self.assertRaises(ValueError):
                    mix.train_mixture("synthetic", root / "partial", config, None, bad)
            data = json.loads((root / "partial/training.json").read_bytes())
            self.assertEqual(data["status"], "FAILED")
            self.assertEqual(data["step"], 0)
            self.assertEqual(data["forward_rows"], 0)
            self.assertTrue((root / "partial/INCOMPLETE").exists())
            self.assertEqual(sum(c[0] == "public_close" for c in calls), 1)
            self.assertFalse(any(c[0] == "fake_update" for c in calls))

    def test_attempted_vs_returned_finite_forward_and_refusal_nn0(self):
        import ast
        import numpy as np
        from quoridor_training.public_replay import WorkBudget
        from types import SimpleNamespace

        # Execute the current nested owning forward, not an independently copied
        # evaluator. All callable/model/tensor ports below are explicitly fake.
        code = Path(__file__).with_name("public_replay.py").read_bytes()
        outer = next(
            n
            for n in ast.parse(code).body
            if isinstance(n, ast.FunctionDef) and n.name == "train_mixture"
        )
        node = next(
            n for n in ast.walk(outer) if isinstance(n, ast.FunctionDef) and n.name == "forward"
        )

        class Value:
            shape = (3,)

            def reshape(self, *a):
                return self

        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            budget = WorkBudget(12, None, Path(directory), 1024**2)
            namespace = {
                "budget": budget,
                "torch": SimpleNamespace(isfinite=lambda v: np.array([True])),
                "device": "synthetic-cuda",
                "outcome_inputs": lambda *a: (),
                "model": lambda *a: Value(),
            }
            exec(
                compile(ast.Module(body=[node], type_ignores=[]), "<own-current-forward>", "exec"),
                namespace,
            )
            run = namespace["forward"]
            x, d = np.zeros((3, 2, 312), dtype=np.float32), np.zeros((3, 2), dtype=np.float32)
            run(x, d, training=True)
            self.assertEqual((budget.training, budget.returned_training), (3, 3))

            def refuse(*a):
                raise RuntimeError("synthetic placement refused before model")

            namespace["outcome_inputs"] = refuse
            with self.assertRaises(RuntimeError):
                run(x, d, training=True)
            self.assertEqual((budget.training, budget.returned_training), (6, 3))
            namespace["outcome_inputs"] = lambda *a: ()
            namespace["torch"] = SimpleNamespace(isfinite=lambda v: np.array([False]))
            with self.assertRaises(ValueError):
                run(x, d)
            self.assertEqual((budget.measurement, budget.returned_measurement), (3, 0))
            run_budget = budget.training + budget.measurement
            with self.assertRaises(ValueError):
                run(np.zeros((4, 2, 312), dtype=np.float32), np.zeros((4, 2), dtype=np.float32))
            self.assertEqual(budget.training + budget.measurement, run_budget)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    TMP = args.TMP
    import quoridor_training

    quoridor_training.__path__.insert(0, str(args.source))
    for name in ("common", "public_replay", "train", "sampling"):
        sys.modules.pop("quoridor_training." + name, None)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite([ConfiguredEntry(args.method)])
        if args.method
        else unittest.defaultTestLoader.loadTestsFromTestCase(ConfiguredEntry)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forwards": 0,
                "actual_fit_updates": 0,
                "fake_framework_model_only": True,
                "errors": [s for _, s in result.errors],
                "failures": [s for _, s in result.failures],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
