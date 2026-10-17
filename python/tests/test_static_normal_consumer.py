"""New NN0 normal-consumer boundaries; no Torch/model/native/old-data entry."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from quoridor_training.common import resolve_config
from quoridor_training.compact_cache import IndexedPublicCorpus
from quoridor_training.public_features import (
    MODEL_INPUT,
    RECORD,
    FeatureWorkspace,
    lr_group_keys,
    model_keys,
)
from quoridor_training.static_public import PAIR
from quoridor_training.static_public_corpus import StaticTeacherCorpus
from quoridor_training.static_learning import (
    StaticMeasurements,
    adequate_learning,
    recipe,
    validate_recipe,
)
from quoridor_training.supply import FLOATS_PER_ROW, PackedSupply, payload_views


def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), mode="0644")


class NormalStaticConsumer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = self.path = Path(self.tmp.name)
        rows = np.zeros(2, dtype=MODEL_INPUT)
        rows["geometry"]["pawns"] = ((3, 75), (12, 65))
        rows["geometry"]["stocks"] = 10
        rows["distance"] = ((0.1, 0.2), (0.3, 0.4))
        pairs = np.zeros(2, dtype=PAIR)
        pairs["key"] = lr_group_keys(model_keys(rows))
        pairs["observations"] = ((3, 1), (2, 0))
        pairs["split"] = (0, 1)
        pairs.tofile(p / "pairs")
        values = np.array([[0.25, -0.75], [0.5, 0.625]], dtype="<f4")
        values.tofile(p / "values")
        inputs = dict(
            schema="quoridor-public-static-input-classes-v1",
            status="COMPLETE",
            pair_record_bytes=37,
            counts=dict(pair_rows=2),
            class_pairs=ref(p / "pairs"),
            class_pairs_identity=list(IndexedPublicCorpus.identity((p / "pairs").stat())),
        )
        (p / "inputs.json").write_text(json.dumps(inputs))
        bank = dict(
            schema="quoridor-public-static-teacher-values-v1",
            status="COMPLETE",
            input_classes=ref(p / "inputs.json"),
            teachers=dict(
                S=dict(
                    values=ref(p / "values"),
                    values_identity=list(IndexedPublicCorpus.identity((p / "values").stat())),
                )
            ),
        )
        (p / "bank.json").write_text(json.dumps(bank))
        (p / "cache.json").write_text(
            json.dumps(
                dict(
                    schema="quoridor-public-static-teacher-v1",
                    input_classes=ref(p / "inputs.json"),
                    teacher_values=ref(p / "bank.json"),
                    teacher="S",
                )
            )
        )
        self.corpus = StaticTeacherCorpus(p)

    def tearDown(self):
        self.corpus.close()
        self.tmp.cleanup()

    def test_normal_supply_keeps_actual_reflection_target_coupled(self):
        corpus = self.corpus
        supply = PackedSupply.__new__(PackedSupply)
        supply.corpus = corpus
        supply.column = 0
        supply.target_scale = 1.0
        supply.weights = np.ones(6, dtype=np.float32)
        slot = dict(
            numpy=np.empty(4 * FLOATS_PER_ROW, dtype=np.float32),
            records=np.empty(4, dtype=RECORD),
            workspace=FeatureWorkspace(4),
            integer_host=None,
        )
        supply._fill(slot, np.arange(4), np.array([True, False, True, False]))
        x, _, target, _ = payload_views(slot["numpy"], 4)
        np.testing.assert_array_equal(target, [-0.75, 0.25, -0.75, -0.75])
        np.testing.assert_array_equal(x[:, 0, :81].argmax(axis=1), [5, 3, 5, 5])
        corpus.completed_training_forward()
        np.testing.assert_array_equal(corpus.executed_orientations, [[1, 3], [0, 0]])
        facts = corpus.save_exposure(self.path / "exposure.u32")
        self.assertEqual(facts["rows"], 4)
        self.assertEqual(facts["bytes"], 16)
        self.assertEqual(len(facts["ordered_index_mask_sha256"]), 64)

    def test_full_v_includes_true_lr_with_original_multiplicity(self):
        chunks = list(self.corpus.evaluation_chunks(np.array([4, 5]), 4096))
        self.assertEqual(len(chunks), 1)
        pair, orientation, weight, _, _ = chunks[0]
        np.testing.assert_array_equal(pair, [1, 1])
        np.testing.assert_array_equal(orientation, [0, 1])
        np.testing.assert_array_equal(weight, [1.0, 1.0])
        measured = StaticMeasurements(self.corpus.pairs)
        measured.add(
            pair,
            np.zeros(2, dtype=np.float32),
            self.corpus.values[pair, orientation],
            weight,
            np.array([20, 20]),
        )
        result = measured.result()
        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["input_classes"], 1)
        self.assertEqual(result["target_mse"], (0.5**2 + 0.625**2) / 2)
        self.assertEqual(result["class_macro_mse"], result["target_mse"])
        self.assertEqual(result["sign_rows"], 2)
        self.assertEqual(result["teacher_zero"], "static scalar zero; never a Draw0 outcome")

    def test_t_only_scale_invariant_between_teacher_labels(self):
        expected = self.corpus.statistics()
        np.testing.assert_array_equal(expected["mu_f32"], np.array([0.1, 0.2], dtype=np.float32))
        np.testing.assert_array_equal(
            expected["sigma_f32"], np.array([0.0001, 0.0001], dtype=np.float32)
        )
        _, labels, _, _ = self.corpus.metadata(np.array([4]))
        np.testing.assert_array_equal(labels, [[0.5]])
        with self.assertRaisesRegex(ValueError, "T-only"):
            self.corpus.locate(np.array([4]), np.array([True]))

    def test_custody_and_incomplete_refusal(self):
        (self.path / "INCOMPLETE").write_text("original partial")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            StaticTeacherCorpus(self.path)
        (self.path / "INCOMPLETE").unlink()
        with (self.path / "values").open("r+b") as stream:
            stream.write(np.float32(0.75).tobytes())
        with self.assertRaisesRegex(ValueError, "custody"):
            self.corpus.verify_binding()

    def test_real_multiplicity_recipe_and_finite_tail(self):
        cfg = recipe(1003, 117, device="cpu", threads=1)
        resolved = resolve_config(cfg)
        validate_recipe(resolved, 1003, 117)
        self.assertEqual(resolved["training"]["steps"], 8)
        self.assertEqual(32 * 1003 - 4096 * 7, 3424)
        self.assertEqual(resolved["training"]["warmup_steps"], 1)
        self.assertEqual(resolved["evaluation"]["early_stopping_patience"], 4)
        self.assertEqual(resolved["limits"]["samples"], 32 * 1003 + 33 * (2 * 117 + 2 * 1003))
        cfg["training"]["steps"] += 1
        with self.assertRaisesRegex(ValueError, "fixed"):
            validate_recipe(cfg, 1003, 117)
        self.assertFalse(adequate_learning(0.5, 0.5, True))
        self.assertFalse(adequate_learning(0.5, 0.1, False))
        self.assertTrue(adequate_learning(0.5, 0.49, True))


if __name__ == "__main__":
    unittest.main()
