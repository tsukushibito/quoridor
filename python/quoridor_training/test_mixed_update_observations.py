"""R1/R2-only NN0 definitions; all framework/model/cache ports are labelled fake."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class RelatedBoundaries(unittest.TestCase):
    def fixtures(self, mode="complete", cleanup_failure=False):
        import numpy as np
        from quoridor_training import public_replay as mix, train
        from quoridor_training.test_public_replay import MixtureBoundaries

        # Reuse only the old pure metadata helper, never an old test definition.
        cfg = MixtureBoundaries().settings()
        cfg["training"]["steps"] = 2
        cfg["mixture"]["added_exposures"] = 10
        cfg["evaluation"].update(
            checkpoints=[0, 1, 2],
            full_train=False,
            full_train_checkpoints=[],
            diagnostic_checkpoints=None,
            diagnostic_rows=2,
            early_stopping_patience=0,
        )
        calls = []
        original = RuntimeError("synthetic optimizer step2 mutates then throws")
        secondary = OSError("synthetic independent cache identity failure")

        class Tensor:
            def __init__(self, values):
                self.values = np.asarray(values, dtype=np.float32)
                self.grad = None

            @property
            def shape(self):
                return self.values.shape

            @property
            def ndim(self):
                return self.values.ndim

            @property
            def dtype(self):
                return self.values.dtype

            def __len__(self):
                return len(self.values)

            def to(self, device):
                return self

            def reshape(self, *shape):
                return Tensor(self.values.reshape(*shape))

            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.values

            def backward(self):
                calls.append(("fake_backward",))

            def __sub__(self, other):
                return Tensor(self.values - other.values)

            def __pow__(self, power):
                return Tensor(self.values**power)

        class Model:
            def __init__(self):
                self.parameter = Tensor(0.0)

            def to(self, device):
                return self

            def train(self):
                pass

            def eval(self):
                pass

            def __call__(self, *args):
                calls.append(("fake_forward_rows", len(args[0])))
                return Tensor(np.full(len(args[0]), self.parameter.values, dtype=np.float32))

            def parameters(self):
                return [self.parameter]

            def state_dict(self):
                return {"synthetic_parameter": float(self.parameter.values)}

        model = Model()

        class Optimizer:
            def __init__(self, *args, **kw):
                self.param_groups = [{}]
                self.updates = 0

            def zero_grad(self, **kw):
                pass

            def step(self):
                self.updates += 1
                model.parameter.values = np.asarray(self.updates * 0.25, dtype=np.float32)
                calls.append(("mutated_fake_update", self.updates))
                if self.updates == 2 and mode == "throw":
                    raise original
                if self.updates == 2 and mode == "nonfinite":
                    model.parameter.values = np.asarray(float("nan"), dtype=np.float32)

            def state_dict(self):
                return {"synthetic_updates": self.updates}

        class Context:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        def save(data, path):
            calls.append(("checkpoint", Path(path).name, data["step"]))
            Path(path).write_text(json.dumps({"step": data["step"], "model": data["model"]}))

        framework = SimpleNamespace(
            float32=np.dtype("float32"),
            long="fake-long",
            from_numpy=Tensor,
            ones=lambda n, **kw: Tensor(np.ones(n)),
            isfinite=lambda value: np.isfinite(value.values),
            mean=lambda value: Tensor(np.mean(value.values)),
            no_grad=Context,
            optim=SimpleNamespace(Adam=Optimizer),
            save=save,
        )

        class Added:
            row_count = 8
            manifest_sha = "synthetic-cache-only"
            groups = np.array([0] * 5 + [1] * 3)
            splits = np.array([0] * 5 + [1] * 3)
            eligible = np.ones(8, dtype=bool)
            families = ["synthetic-T", "synthetic-V"]
            labels = np.asarray([[0, 1, 0, 2]] * 8, dtype=np.float32)
            rows = [{"id": str(i)} for i in range(8)]

            def batch(self, indices, mask=None):
                count = len(indices)
                calls.append(("added_batch", count, mask is not None))
                return (
                    np.zeros((count, 2, 312), dtype=np.float32),
                    np.ones((count, 2), dtype=np.float32),
                    self.labels[indices],
                )

            def verify_binding(self):
                calls.append(("added_identity_after",))
                if cleanup_failure:
                    raise secondary

        class Public:
            def batch(self, split, indices, mask=None, training=False):
                assert split in ("train", "validation") and (not training or split == "train")
                bound = 7 if split == "train" else 3
                assert all(0 <= int(i) < bound for i in indices)
                count = len(indices)
                calls.append(("public_batch", split, count, training))
                return (
                    np.zeros((count, 2, 312), dtype=np.float32),
                    np.ones((count, 2), dtype=np.float32),
                    np.ones(count, dtype=np.float32),
                )

            def verify_binding(self):
                calls.append(("public_identity_after",))

            def close(self):
                calls.append(("public_close",))

        def exporting(model, config, statistics, fit, path):
            calls.append(("export", path.name, model.state_dict()))
            path.mkdir(exist_ok=True)
            file = path / "manifest.json"
            file.write_text(json.dumps({"synthetic_export": True, "state": model.state_dict()}))
            return file

        warm = {
            "descriptor": {"synthetic_reference": True},
            "weights": {"path": "not-opened"},
        }

        def admitted(*args):
            return (
                {},
                {},
                {"train": 7, "validation": 3},
                {
                    "warm_start": warm,
                    "statistics": {"mu_f32": [0.1, 0.2], "sigma_f32": [0.3, 0.4]},
                },
            )

        patches = [
            patch.dict(
                sys.modules,
                {
                    "torch": framework,
                    "quoridor_training.compact_cache": SimpleNamespace(
                        IndexedPublicCorpus=lambda *a: Public()
                    ),
                    "quoridor_training.terminal_cache": SimpleNamespace(
                        TerminalCorpus=lambda *a: Added()
                    ),
                },
            ),
            patch.object(mix, "admit", admitted),
            patch.object(train, "configure_framework", lambda cfg: "synthetic-cuda"),
            patch.object(train, "build_model", lambda *a: model),
            patch.object(train, "restore_warmstart_parameters", lambda *a: None),
            patch.object(train, "verify_native_parameters", lambda *a: None),
            patch.object(train, "export", exporting),
        ]
        return SimpleNamespace(
            config=cfg,
            calls=calls,
            original=original,
            secondary=secondary,
            patches=patches,
            module=mix,
            model=model,
            warm=warm,
        )

    def test_R1_mutated_throw_and_nonfinite_current_state_unknown_nn0(self):
        for mode in ("throw", "nonfinite"):
            with (
                self.subTest(mode=mode),
                tempfile.TemporaryDirectory(dir=TMP) as directory,
            ):
                fixture = self.fixtures(mode, cleanup_failure=True)
                root = Path(directory)
                config = root / "config.json"
                config.write_text(json.dumps(fixture.config))
                with ExitStack() as stack:
                    for item in fixture.patches:
                        stack.enter_context(item)
                    with self.assertRaises(BaseExceptionGroup) as caught:
                        fixture.module.train_mixture(
                            "synthetic", root / "output", config, None, fixture.config
                        )
                errors = caught.exception.exceptions
                if mode == "throw":
                    self.assertIs(errors[0], fixture.original)
                else:
                    self.assertEqual(str(errors[0]), "nonfinite updated parameters")
                self.assertIs(errors[1], fixture.secondary)
                result = json.loads((root / "output/training.json").read_bytes())
                # Read actual saved output through the maintained streaming writer.
                # Internal step lookup remains numeric; persisted map keys are JSON strings.
                persisted = result["plan"]
                self.assertEqual(
                    persisted["scopes_by_step"],
                    {
                        str(point): [
                            "added_validation",
                            "public_validation",
                            "added_train",
                            "public_train",
                        ]
                        for point in (0, 1, 2)
                    },
                )
                self.assertEqual(persisted["measurement_rows_by_step"], {"0": 10, "1": 10, "2": 10})
                self.assertEqual(persisted["observation_steps"], [0, 1, 2])
                self.assertEqual(
                    (
                        persisted["training_forwards"],
                        persisted["measurement_forwards"],
                        persisted["forward_upper"],
                    ),
                    (14, 30, 44),
                )
                numeric_plan = fixture.module.planned_work(
                    fixture.config, 5, 3, {"train": 7, "validation": 3}
                )
                self.assertEqual(
                    persisted,
                    {
                        **numeric_plan,
                        "scopes_by_step": {
                            str(k): v for k, v in numeric_plan["scopes_by_step"].items()
                        },
                        "measurement_rows_by_step": {
                            str(k): v for k, v in numeric_plan["measurement_rows_by_step"].items()
                        },
                    },
                )
                self.assertEqual((result["step"], result["attempted_update"]), (1, 2))
                self.assertEqual(result["current_update_state"], "UPDATE_IN_PROGRESS_UNKNOWN")
                self.assertEqual(result["last_checkpoint_state"], "UNKNOWN")
                self.assertIsNone(result["last_checkpoint_step"])
                self.assertEqual((result["attempted_added"], result["attempted_public"]), (6, 8))
                self.assertEqual((result["added_seen"], result["public_seen"]), (3, 4))
                self.assertEqual(
                    (
                        result["training_forwards"],
                        result["returned_finite_training_rows"],
                    ),
                    (14, 14),
                )
                self.assertEqual(
                    (
                        result["measurement_forwards"],
                        result["returned_finite_measurement_rows"],
                    ),
                    (20, 20),
                )
                self.assertEqual(result["initial_reference"], fixture.warm)
                self.assertTrue((root / "output/INCOMPLETE").exists())
                self.assertFalse((root / "output/last.pt").exists())
                self.assertFalse((root / "output/last-model").exists())
                self.assertFalse(
                    any(c[0] == "checkpoint" and c[1] == "last.pt" for c in fixture.calls)
                )
                # The earlier verified BEST remains its true update1, not live update2.
                self.assertEqual(
                    json.loads((root / "output/best.pt").read_bytes())["model"],
                    {"synthetic_parameter": 0.25},
                )
                self.assertEqual(sum(c[0] == "added_identity_after" for c in fixture.calls), 1)
                self.assertEqual(sum(c[0] == "public_identity_after" for c in fixture.calls), 1)
                self.assertEqual(sum(c[0] == "public_close" for c in fixture.calls), 1)
                final = json.loads((root / "output/finalization-errors.json").read_bytes())
                self.assertEqual(
                    final["original_stop_and_position"]["current_update_state"],
                    "UPDATE_IN_PROGRESS_UNKNOWN",
                )
                self.assertEqual(final["primary_exception"]["message"], str(errors[0]))

    def test_R2_full_train_and_distinct_diagnostic_points_match_actual_bound_nn0(self):
        from quoridor_training.common import resolve_config

        fixture = self.fixtures()
        fixture.config["evaluation"].update(
            checkpoints=[0, 2],
            full_train=True,
            full_train_checkpoints=[2],
            diagnostic_checkpoints=[1],
        )
        self.assertEqual(resolve_config(fixture.config), fixture.config)
        plan = fixture.module.planned_work(fixture.config, 5, 3, {"train": 7, "validation": 3})
        self.assertEqual(
            plan["scopes_by_step"],
            {
                0: [
                    "added_validation",
                    "public_validation",
                    "added_full_train",
                    "public_full_train",
                ],
                1: ["added_train", "public_train"],
                2: [
                    "added_validation",
                    "public_validation",
                    "added_full_train",
                    "public_full_train",
                ],
            },
        )
        self.assertEqual(plan["measurement_rows_by_step"], {0: 18, 1: 4, 2: 18})
        self.assertEqual(
            (
                plan["training_forwards"],
                plan["measurement_forwards"],
                plan["forward_upper"],
            ),
            (14, 40, 54),
        )
        point_only = {
            **fixture.config,
            "evaluation": {**fixture.config["evaluation"], "full_train": False},
        }
        explicit = fixture.module.planned_work(point_only, 5, 3, {"train": 7, "validation": 3})
        self.assertEqual(explicit["full_train_steps"], [2])
        self.assertNotIn("added_full_train", explicit["scopes_by_step"][0])
        self.assertIn("added_full_train", explicit["scopes_by_step"][2])
        self.assertEqual(explicit["forward_upper"], 42)
        with tempfile.TemporaryDirectory(dir=TMP) as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text(json.dumps(fixture.config))
            with ExitStack() as stack:
                for item in fixture.patches:
                    stack.enter_context(item)
                result = fixture.module.train_mixture(
                    "synthetic", root / "output", config, None, fixture.config
                )
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(
                (
                    result["training_forwards"],
                    result["measurement_forwards"],
                    result["forward_rows"],
                ),
                (14, 40, 54),
            )
            self.assertEqual([p["step"] for p in result["curves"]], [0, 1, 2])
            first, diagnostic, last = result["curves"]
            self.assertEqual(first["scopes"]["added_full_train"]["rows"], 5)
            self.assertEqual(first["scopes"]["public_full_train"]["rows"], 7)
            self.assertEqual(set(diagnostic["scopes"]), {"added_train", "public_train"})
            self.assertEqual(diagnostic["scopes"]["added_train"]["rows"], 2)
            self.assertNotIn("added_validation", diagnostic["scopes"])
            self.assertEqual(last["scopes"]["public_full_train"]["rows"], 7)
            self.assertEqual(result["last_checkpoint_state"], "VERIFIED_COMPLETED_UPDATE")
            self.assertEqual(result["last_checkpoint_step"], 2)
            self.assertEqual(json.loads((root / "output/last.pt").read_bytes())["step"], 2)
            self.assertFalse((root / "output/INCOMPLETE").exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    TMP = args.TMP
    import quoridor_training

    quoridor_training.__path__.insert(0, str(args.source))
    quoridor_training.__path__.insert(1, str(args.source.parents[1] / "source"))
    for name in ("public_replay", "train", "sampling", "common"):
        sys.modules.pop("quoridor_training." + name, None)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(RelatedBoundaries)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forwards": 0,
                "actual_fit_updates": 0,
                "fake_framework_model_and_cache": True,
                "failures": [v for _, v in result.failures],
                "errors": [v for _, v in result.errors],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
