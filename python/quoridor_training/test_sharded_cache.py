"""NN0 checks for referenced partitions, input order and scheduled config."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from .cache import load, sha
from .common import resolve_config


class ShardedCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.shards = []
        for number, side in enumerate((1, 2)):
            child = self.root / str(number)
            child.mkdir()
            x = np.zeros((1, 2, 312), dtype="<f4")
            x[0, 0, 4] = 1
            x[0, 1, 9] = 1
            d = np.asarray([[0.1, 0.2]], dtype="<f4")
            y = np.asarray([[np.nan, 0 if side == 2 else 1]], dtype="<f4")
            x.tofile(child / "x.f32")
            d.tofile(child / "distance.f32")
            y.tofile(child / "labels.f32")
            row = {
                "id": "same-local-id",
                "group": "native-family",
                "split": "train",
                "primary_eligible": True,
                "side": side,
                "ids": [[4], [9]] if side == 1 else [[9], [4]],
                "ids_order": "P1_then_P2",
                "tensor_view_order": "STM_then_opponent",
                "distance_order": "STM_then_opponent_f32",
                "distance": d[0].tolist(),
                "rootmean": None,
                "z": float(y[0, 1]),
                "teacher_type": "fixture",
            }
            (child / "rows.jsonl").write_text(json.dumps(row) + "\n")
            files = ["x.f32", "distance.f32", "labels.f32", "rows.jsonl"]
            (child / "cache.json").write_text(
                json.dumps(
                    {
                        "rows": 1,
                        "feature_count": 312,
                        "allow_test": False,
                        "dataset_sha": "fixture",
                        "sha256": {name: sha(child / name) for name in files},
                    }
                )
            )
            self.shards.append(
                {
                    "path": str(child),
                    "manifest_SHA": sha(child / "cache.json"),
                    "namespace": f"run{number}",
                    "family_map": {
                        "native-family": {
                            "canonical_family": f"family{number}",
                            "partition": "train" if number == 0 else "validation",
                        }
                    },
                    "rows": [{"index": 0, "id": "same-local-id", "primary_eligible": True}],
                }
            )
        self.manifest = {
            "schema": "quoridor-sharded-training-cache-v1",
            "feature_count": 312,
            "rows": 2,
            "shards": self.shards,
            "references": [],
        }

    def run_manifest(self, value):
        path = self.root / "shards.json"
        path.write_text(json.dumps(value))
        return load(path)

    def test_namespace_p2_draw_and_original_bytes(self):
        before = [sha(Path(s["path"]) / "labels.f32") for s in self.shards]
        binding, rows, x, d, y = self.run_manifest(self.manifest)
        self.assertIsInstance(binding, dict)
        self.assertIsInstance(rows, list)
        self.assertTrue(all(isinstance(row, dict) for row in rows))
        self.assertEqual((len(rows), x.shape[0], d.shape[0], y.shape[0]), (2, 2, 2, 2))
        self.assertEqual([r["id"] for r in rows], ["run0:same-local-id", "run1:same-local-id"])
        self.assertEqual([r["split"] for r in rows], ["train", "validation"])
        self.assertEqual(x.shape, (2, 2, 312))
        self.assertEqual(d[1].tobytes(), np.asarray([0.1, 0.2], dtype="<f4").tobytes())
        self.assertTrue(np.isnan(y[:, 0]).all())
        self.assertEqual(y[1, 1], 0)
        self.assertEqual(before, [sha(Path(s["path"]) / "labels.f32") for s in self.shards])
        self.assertEqual(binding["dataset_sha"], sha(self.root / "shards.json"))

    def test_unknown_future_missing_rows_bad_uid_and_mask_rejected(self):
        variants = []
        value = copy.deepcopy(self.manifest)
        value["unknown"] = True
        variants.append(value)
        value = copy.deepcopy(self.manifest)
        value["shards"][1]["family_map"]["native-family"]["partition"] = "test"
        variants.append(value)
        value = copy.deepcopy(self.manifest)
        value["shards"][0]["rows"] = []
        variants.append(value)
        value = copy.deepcopy(self.manifest)
        value["shards"][1]["namespace"] = "run0"
        variants.append(value)
        value = copy.deepcopy(self.manifest)
        value["shards"][1]["family_map"]["native-family"]["canonical_family"] = "family0"
        variants.append(value)
        value = copy.deepcopy(self.manifest)
        value["shards"][0]["rows"][0]["primary_eligible"] = 1
        variants.append(value)
        value = copy.deepcopy(self.manifest)
        value["shards"][0]["rows"][0]["index"] = 1
        variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_manifest(value)

    def test_child_hash_and_distance_corruption_rejected(self):
        child = Path(self.shards[0]["path"])
        with (child / "distance.f32").open("ab") as stream:
            stream.write(b"bad")
        with self.assertRaises(ValueError):
            self.run_manifest(self.manifest)

    def test_explicit_schedule_and_native_only_defaults(self):
        defaults = resolve_config()
        self.assertEqual(defaults["artifacts"]["mode"], "native_onnx")
        self.assertIsNone(defaults["evaluation"]["checkpoints"])
        good = resolve_config(
            overrides=(
                "training.steps=7813",
                "evaluation.checkpoints=[0,1,5,20,50,100,200,1000,4000,7813]",
                'artifacts.mode="native"',
                "artifacts.save_scheduled=true",
            )
        )
        self.assertEqual(len(good["evaluation"]["checkpoints"]), 10)
        self.assertTrue(good["artifacts"]["save_scheduled"])
        for wrong in ("[0,1,1,200]", "[1,200]", "[0,5]", "[0,true,200]"):
            with self.assertRaises(ValueError):
                resolve_config(overrides=("evaluation.checkpoints=" + wrong,))


if __name__ == "__main__":
    unittest.main()
