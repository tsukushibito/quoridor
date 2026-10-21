"""New NN0 finite device, target-distribution and normal-control bindings."""

import json
import sys
import types
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import test_static_normal_consumer as fixtures
from quoridor_training import static_learning as learning
from quoridor_training import cache
from quoridor_training.public_static_prepare import file_ref
from quoridor_training.public_static_values import runtime_devices
from quoridor_training.static_public_corpus import StaticTeacherCorpus
from quoridor_training.static_teacher_inputs import StaticInputs


class FiniteStaticControls(unittest.TestCase):
    def test_sigma_only_devices_and_weighted_target_distribution(self):
        reader = StaticInputs.__new__(StaticInputs)
        reader.batch_rows = 2

        def core(keys, rows, output, status):
            np.ctypeslib.as_array(status, shape=(rows,)).fill(0)
            np.ctypeslib.as_array(output, shape=(rows * 8 * 81,)).fill(0)
            return 0

        def refuse_c20(*args):
            self.fail("Sigma-only source path entered C20")

        reader._core, reader._c20 = core, refuse_c20
        sigma, c20 = reader.encode(np.zeros(2, dtype="V28"), include_c20=False)
        self.assertEqual(sigma.shape, (2, 8, 9, 9))
        self.assertIsNone(c20)
        plan = runtime_devices(dict(device="cuda:0", cpu_threads=1))
        self.assertEqual(plan["S-oldORT-single"]["device"], "cpu")
        self.assertEqual(plan["S-Torch-batch"]["device"], "cuda:0")
        self.assertTrue(all(row["precision"] == "FP32" for row in plan.values()))
        with self.assertRaises(ValueError):
            runtime_devices(dict(device="cpu", cpu_threads=2))
        base = fixtures.NormalStaticConsumer()
        base.setUp()
        try:
            measured = learning.StaticMeasurements(base.corpus.pairs)
            measured.add(
                np.array([0, 1]),
                np.array([0.0, 1.0]),
                np.array([-1.0, 1.0]),
                np.array([2.0, 1.0]),
                np.array([20, 20]),
            )
            result = measured.result()
            self.assertEqual(result["target_mean"], -1 / 3)
            self.assertEqual(result["target_second_moment"], 1)
            self.assertEqual(result["target_histogram10"], [2.0] + [0.0] * 8 + [1.0])
            self.assertEqual(sum(result["target_histogram10"]), result["rows"])
        finally:
            base.tearDown()

    def test_actual_two_caches_share_one_fresh_initial_and_real_count_recipe(self):
        base = fixtures.NormalStaticConsumer()
        base.setUp()
        try:
            root = base.path
            inputs = json.loads((root / "inputs.json").read_bytes())
            inputs["counts"].update(train=4, validation=2)
            (root / "inputs.json").write_text(json.dumps(inputs))
            bank = json.loads((root / "bank.json").read_bytes())
            bank["input_classes"] = file_ref(root / "inputs.json")
            c = np.array([[0.75, -0.25], [-0.5, -0.625]], dtype="<f4")
            c.tofile(root / "C-values")
            bank["teachers"]["C"] = dict(
                values=file_ref(root / "C-values"),
                values_identity=list(
                    fixtures.IndexedPublicCorpus.identity((root / "C-values").stat())
                ),
            )
            (root / "bank.json").write_text(json.dumps(bank))

            def fake_initializer(cache_path, output, config_path):
                output.mkdir()
                corpus = StaticTeacherCorpus(cache_path)
                try:
                    scale = corpus.statistics()
                finally:
                    corpus.close()
                (output / "scale.json").write_text(json.dumps(scale))
                (output / "NN0-not-model-weights").write_bytes(b"NN0")
                weights = file_ref(output / "NN0-not-model-weights")
                result = dict(
                    schema="quoridor-static-common-initial-v1",
                    initial_weights=weights,
                    initial_weights_sha=weights["sha256"],
                    initializer_seed=json.loads(Path(config_path).read_bytes())["static_teacher"][
                        "initializer_seed"
                    ],
                    input_classes=bank["input_classes"],
                    scale=dict(
                        path=str(output / "scale.json"),
                        sha256=file_ref(output / "scale.json")["sha256"],
                    ),
                    model_forwards=0,
                    explicit_test_double=True,
                )
                (output / "result.json").write_text(json.dumps(result))
                return result

            (root / "provided-config.json").write_text(json.dumps(fixtures.config_for(4, 2)))
            with (
                patch.object(
                    learning, "prepare_common", side_effect=fake_initializer
                ) as initialize,
                patch.object(cache, "load", side_effect=StaticTeacherCorpus, create=True),
            ):
                actual = learning.prepare_fits(
                    dict(
                        teacher_values=file_ref(root / "bank.json"),
                        output=str(root / "prepared"),
                        fit_config=file_ref(root / "provided-config.json"),
                    )
                )
            initialize.assert_called_once()
            result = json.loads(Path(actual["result"]["path"]).read_bytes())
            bindings = [
                json.loads(Path(result["arms"][k]["input_binding"]["path"]).read_bytes())
                for k in ("S", "C")
            ]
            self.assertEqual(bindings[0]["initial_weights"], bindings[1]["initial_weights"])
            self.assertEqual(bindings[0]["scale_artifact_sha"], bindings[1]["scale_artifact_sha"])
            self.assertNotEqual(
                bindings[0]["constant_artifact_sha"], bindings[1]["constant_artifact_sha"]
            )
            cfg = json.loads(Path(result["arms"]["S"]["config"]["path"]).read_bytes())
            self.assertEqual(cfg["limits"]["samples"], 850000000)
            self.assertEqual(cfg["training"]["seed"], fixtures.config_for(4, 2)["training"]["seed"])
            self.assertFalse((root / "prepared/INCOMPLETE").exists())
            self.assertFalse(actual["fit_entered"])
        finally:
            base.tearDown()

    def test_fresh_initializer_preserves_constructor_and_close_failures(self):
        work = ValueError("new constructor refusal; no head")
        close = OSError("new close refusal")

        def fail_build(*args, **kwargs):
            raise work

        def fail_close(primary_error=None):
            raise BaseExceptionGroup("close", [primary_error, close])

        corpus = types.SimpleNamespace(
            counts={"train": 4, "validation": 2},
            statistics=lambda: {},
            close=fail_close,
        )
        train = types.ModuleType("quoridor_training.train")
        train.configure_framework = lambda cfg: None
        train.build_model = fail_build
        train.export = train.write = train.sha = lambda *args: None
        with (
            patch.dict(sys.modules, {train.__name__: train}),
            patch.object(cache, "load", return_value=corpus, create=True),
            patch(
                "quoridor_training.common.resolve_config",
                return_value=fixtures.config_for(4, 2, device="cpu", threads=1),
            ),
        ):
            with self.assertRaises(BaseExceptionGroup) as caught:
                learning.prepare_common("NN0", "UNENTERED", "NN0")
        self.assertEqual(list(caught.exception.exceptions), [work, close])


if __name__ == "__main__":
    unittest.main()
