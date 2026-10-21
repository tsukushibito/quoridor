"""Synthetic NN0 regressions for cache integrity, streaming moments and metrics."""

import copy
import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from .cache import load, sha, _JsonStream, _Overlay
from .common import measurements, MeasurementAccumulator
from .train import training_statistics, FROZEN_ARTIFACTS, verify_freeze, test as evaluate_test


def fixture(path, n=7, test=False):
    path.mkdir()
    x = np.zeros((n, 2, 312), dtype="<f4")
    x[:, 0, 4] = 1
    x[:, 1, 9] = 1
    d = np.asarray([[i / 20, (n - i) / 20] for i in range(n)], dtype="<f4")
    y = np.asarray([[np.nan, (i % 3) - 1] for i in range(n)], dtype="<f4")
    x.tofile(path / "x.f32")
    d.tofile(path / "distance.f32")
    y.tofile(path / "labels.f32")
    rows = [
        {
            "id": str(i),
            "group": "g" + str(i % 3),
            "side": 1 if i % 2 else 2,
            "ids": [[4], [9]] if i % 2 else [[9], [4]],
            "ids_order": "P1_then_P2",
            "tensor_view_order": "STM_then_opponent",
            "distance_order": "STM_then_opponent_f32",
            "distance": d[i].tolist(),
            "split": "test" if test else "train",
            "primary_eligible": i % 2 == 0,
            "teacher_type": "fixture",
            "rootmean": None,
            "z": float(y[i, 1]),
        }
        for i in range(n)
    ]
    (path / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    names = ["x.f32", "distance.f32", "labels.f32", "rows.jsonl"]
    manifest = {
        "rows": n,
        "feature_count": 312,
        "allow_test": test,
        "dataset_sha": "fixture",
        "files": {name: name for name in names},
        "sha256": {name: sha(path / name) for name in names},
    }
    (path / "cache.json").write_text(json.dumps(manifest))
    return manifest, rows, x, d, y


class CorpusSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "cache"
        self.manifest, self.rows, self.x, self.d, self.y = fixture(self.path)

    def rewrite(self, name, content):
        (self.path / name).write_bytes(content)
        self.manifest["sha256"][name] = sha(self.path / name)
        (self.path / "cache.json").write_text(json.dumps(self.manifest))

    def test_required_hash_and_exact_lengths_even_when_rehashed(self):
        for name in self.manifest["sha256"]:
            value = copy.deepcopy(self.manifest)
            del value["sha256"][name]
            (self.path / "cache.json").write_text(json.dumps(value))
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "schema"):
                load(self.path)
        (self.path / "cache.json").write_text(json.dumps(self.manifest))
        self.rewrite("distance.f32", self.d.tobytes() + b"1234")
        with self.assertRaisesRegex(ValueError, "byte length"):
            load(self.path)

    def test_finite_nonbinary_and_wrong_finite_distance_rejected(self):
        for name, content in [
            ("x.f32", np.full_like(self.x, 0.25).tobytes()),
            ("distance.f32", (self.d + 0.1).tobytes()),
        ]:
            with self.subTest(name=name):
                self.rewrite(name, content)
                with self.assertRaises(ValueError):
                    load(self.path)
                self.rewrite(name, (self.x if name == "x.f32" else self.d).tobytes())

    def test_p2_order_and_feature_ids_rejected(self):
        self.rows[0]["ids"] = [[4], [9]]
        self.rewrite("rows.jsonl", "".join(json.dumps(r) + "\n" for r in self.rows).encode())
        with self.assertRaisesRegex(ValueError, "IDs/tensor"):
            load(self.path)

    def test_duplicate_metadata_identity_is_rejected(self):
        self.rows[1]["id"] = self.rows[0]["id"]
        self.rewrite("rows.jsonl", "".join(json.dumps(r) + "\n" for r in self.rows).encode())
        with self.assertRaisesRegex(ValueError, "identity duplicated"):
            load(self.path)

    def test_changed_cache_rejected_after_consumption(self):
        corpus = load(self.path)
        corpus.verify_binding()
        (self.path / "x.f32").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "during consumption"):
            corpus.verify_binding()

    def test_lazy_diagnostic_subset_matches_dense_reference(self):
        from .sampling import diagnostic_indices

        corpus = load(self.path)
        indices = np.asarray([0, 2, 3, 6])
        np.testing.assert_array_equal(
            diagnostic_indices(corpus.rows, indices, 3, 19),
            diagnostic_indices(self.rows, indices, 3, 19),
        )

    def test_noncontiguous_duplicate_batch_and_no_dense_concatenation(self):
        with patch(
            "quoridor_training.cache.np.concatenate", side_effect=AssertionError("dense corpus")
        ):
            corpus = load(self.path)
            x, d, y = corpus.batch([6, 0, 3, 6])
        np.testing.assert_array_equal(x, self.x[[6, 0, 3, 6]])
        np.testing.assert_array_equal(d, self.d[[6, 0, 3, 6]])
        np.testing.assert_array_equal(y, self.y[[6, 0, 3, 6]])
        self.assertFalse(isinstance(corpus.rows, list))
        self.assertEqual([r["id"] for r in corpus.rows.iter_indices([6, 0, 6])], ["6", "0", "6"])
        with self.assertRaises(ValueError):
            corpus.batch([-1])

    def test_streamed_statistics_and_baseline_match_dense_reference(self):
        corpus = load(self.path)
        indices = np.array([0, 2, 3, 5, 6])
        stats, fit = training_statistics(corpus, indices, 1, size=2)
        np.testing.assert_array_equal(
            stats["mu_f32"], self.d[indices].mean(axis=0, dtype=np.float64).astype(np.float32)
        )
        np.testing.assert_array_equal(
            stats["sigma_f32"], self.d[indices].std(axis=0, dtype=np.float64).astype(np.float32)
        )
        design = np.column_stack(
            (np.ones(len(indices)), (self.d[indices, 1] - self.d[indices, 0]).astype(np.float64))
        )
        reference = np.linalg.lstsq(design, self.y[indices, 1].astype(np.float64), rcond=None)[
            0
        ].astype(np.float32)
        np.testing.assert_array_equal([fit["a"], fit["b"]], reference)

    def test_metrics_stream_matches_row_and_family_reference(self):
        values = [-0.95, 0.5, 0.25, -0.2, 0.7, 0.99, -0.1]
        accumulator = MeasurementAccumulator("z", 0.1)
        for row, value in zip(self.rows, values):
            accumulator.add(row, value)
        self.assertEqual(accumulator.result(), measurements(self.rows, values, "z", 0.1))
        report = accumulator.result()
        errors = [
            (0.05) ** 2,
            (0.5) ** 2,
            (-0.75) ** 2,
            (0.8) ** 2,
            (0.7) ** 2,
            (-0.01) ** 2,
            (0.9) ** 2,
        ]
        self.assertAlmostEqual(report["target_mse"], sum(errors) / 7)
        self.assertAlmostEqual(
            report["target_game_equal_mse"],
            (
                (errors[0] + errors[3] + errors[6]) / 3
                + (errors[1] + errors[4]) / 2
                + (errors[2] + errors[5]) / 2
            )
            / 3,
        )
        self.assertEqual(report["z_sign_accuracy"], 1)
        self.assertEqual(report["z_sign_rows"], 5)
        self.assertEqual(report["saturation_fraction"], 2 / 7)
        self.assertIsNone(report["rootmean_mse"])

        for group in ("g0", "g1", "g2"):
            pairs = [(r, v) for r, v in zip(self.rows, values) if r["group"] == group]
            self.assertEqual(
                accumulator.result(group),
                measurements([r for r, _ in pairs], [v for _, v in pairs], "z", 0.1),
            )

    def test_overlay_decoder_crosses_read_boundaries_without_retaining_rows(self):
        rows = [
            {"index": i, "id": "日本語" * 5 + str(i), "primary_eligible": i % 2 == 0}
            for i in range(1300)
        ]
        reader = _JsonStream(io.StringIO(json.dumps(rows, ensure_ascii=False)))
        overlay = _Overlay(reader)
        self.assertEqual(len(overlay), len(rows))
        self.assertTrue(overlay.matches(1299, rows[1299]["id"]))
        self.assertEqual(overlay.masks[1299], 0)
        self.assertLessEqual(len(reader.buffer), 65536)


class FreezeSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in FROZEN_ARTIFACTS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        import gzip

        with gzip.open(self.root / "cache-binding.json.gz", "wt") as stream:
            json.dump({"dataset_sha": "input-sha"}, stream)
        (self.root / "data.json").write_text(json.dumps({"binding": {"dataset_sha": "input-sha"}}))
        self.freeze = {
            "schema": "quoridor-candidate-freeze-v2",
            "dataset_sha": "input-sha",
            "artifacts_sha256": {name: sha(self.root / name) for name in FROZEN_ARTIFACTS},
            "model_sha": sha(self.root / "best-model/manifest.json"),
            "weights_sha": sha(self.root / "best-model/weights.f32"),
            "initial_weights_sha": sha(self.root / "initial-model/weights.f32"),
        }
        (self.root / "freeze.json").write_text(json.dumps(self.freeze))

    def test_every_consumed_artifact_change_rejected_before_model(self):
        self.assertEqual(verify_freeze(self.root), self.freeze)
        for name in FROZEN_ARTIFACTS:
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with (
                self.subTest(name=name),
                patch(
                    "quoridor_training.train.build_model",
                    side_effect=AssertionError("model construction"),
                ),
                self.assertRaisesRegex(ValueError, "artifact changed"),
            ):
                evaluate_test("cache-never-opened", self.root, self.root / "result")
            path.write_bytes(original)

    def test_old_or_missing_bindings_rejected(self):
        for value in (
            {"schema": "quoridor-candidate-freeze-v1"},
            {"schema": "quoridor-candidate-freeze-v2", "artifacts_sha256": {}},
        ):
            (self.root / "freeze.json").write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                verify_freeze(self.root)


@unittest.skipUnless(
    os.environ.get("QUORIDOR_OBSERVATION_LIVE_TESTS") == "1", "explicit tiny CPU model fixture only"
)
class LiveFreezeEvaluation(unittest.TestCase):
    def test_freeze_evaluation_native_parameters_and_scale(self):
        import torch
        from .train import train

        with tempfile.TemporaryDirectory(
            dir=os.environ["QUORIDOR_OBSERVATION_TEST_ROOT"]
        ) as temporary:
            root = Path(temporary)
            manifest, rows, _, _, _ = fixture(root / "train-cache", n=6)
            for i, row in enumerate(rows):
                row["split"] = "train" if i < 4 else "validation"
                row["primary_eligible"] = True
            (root / "train-cache/rows.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows)
            )
            manifest["sha256"]["rows.jsonl"] = sha(root / "train-cache/rows.jsonl")
            (root / "train-cache/cache.json").write_text(json.dumps(manifest))
            cfg = {
                "model": {"architecture": "distance_residual"},
                "training": {"target": "z", "steps": 1, "batch_size": 2, "threads": 1},
                "evaluation": {
                    "checkpoints": [0, 1],
                    "batch_size": 1,
                    "diagnostic_rows": 0,
                    "early_stopping_patience": 0,
                },
                "artifacts": {"mode": "native"},
                "limits": {"seconds": 20, "samples": 40},
            }
            (root / "config.json").write_text(json.dumps(cfg))
            emitted = train(root / "train-cache", root / "learning", root / "config.json")
            self.assertEqual(emitted["schema"], "quoridor-candidate-freeze-v2")
            self.assertEqual(verify_freeze(root / "learning"), emitted)
            fixture(root / "test-cache", n=2, test=True)
            result = evaluate_test(root / "test-cache", root / "learning", root / "evaluation")
            self.assertEqual(result["rows"], 2)
            self.assertEqual(
                result["unique_model_forwards"],
                len(
                    {
                        emitted["artifacts_sha256"][name + "-model/weights.f32"]
                        for name in ("initial", "best")
                    }
                ),
            )
            self.assertEqual(
                result["evaluation_cache_binding"]["cache_manifest_SHA"],
                sha(root / "test-cache/cache.json"),
            )
            predictions = np.load(root / "evaluation/predictions.npz")
            corpus = load(root / "test-cache", allow_test=True)
            x, d, _ = corpus.batch([0, 1])
            stats = json.loads((root / "learning/scale.json").read_text())
            for name in ("initial", "best"):
                cp = torch.load(
                    root / "learning" / (name + ".pt"), map_location="cpu", weights_only=True
                )
                exported = np.fromfile(
                    root / "learning" / (name + "-model") / "weights.f32", dtype="<f4"
                )
                ordered = ("ft.weight", "ft.bias", "h.weight", "h.bias", "out.weight", "out.bias")
                vector = np.concatenate([cp["model"][key].numpy().reshape(-1) for key in ordered])
                np.testing.assert_array_equal(exported, vector)
                # Independent NumPy evaluation of the native descriptor, including nonpersistent scale/coefficient.
                ft = np.maximum(
                    0, x @ cp["model"]["ft.weight"].numpy().T + cp["model"]["ft.bias"].numpy()
                )
                hidden_input = np.column_stack(
                    (
                        ft[:, 0],
                        ft[:, 1],
                        (d - np.asarray(stats["mu_f32"], dtype=np.float32))
                        / np.asarray(stats["sigma_f32"], dtype=np.float32),
                        np.zeros((2, 4), dtype=np.float32),
                    )
                )
                hidden = np.maximum(
                    0,
                    hidden_input @ cp["model"]["h.weight"].numpy().T
                    + cp["model"]["h.bias"].numpy(),
                )
                residual = (
                    hidden @ cp["model"]["out.weight"].numpy().T + cp["model"]["out.bias"].numpy()
                )[:, 0]
                expected = np.tanh(np.float32(8) * (d[:, 1] - d[:, 0]) + residual)
                np.testing.assert_allclose(predictions[name], expected, rtol=1e-6, atol=1e-7)
            (root / "learning/scale.json").write_text("{}")
            with (
                patch(
                    "quoridor_training.train.build_model",
                    side_effect=AssertionError("construction"),
                ),
                self.assertRaisesRegex(ValueError, "scale.json"),
            ):
                evaluate_test(root / "test-cache", root / "learning", root / "tampered")


if __name__ == "__main__":
    unittest.main()
