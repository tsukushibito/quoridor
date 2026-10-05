"""NN0 input/data regressions; stdlib fixtures, no Torch import or forward."""

import ast
import copy
import gzip
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

from dataset import load_data, load_stage, sha
from exposure import make_exposure_mask
from frame14_data import make_mask
from metadata import canonicalize
from qf1 import canonical_model_input, feature_signature, model_features, validate_input


def row(name, split, *, side=1, distance=None):
    return {
        "id": name,
        "group": "game-" + name,
        "split": split,
        "side": side,
        "ids": [[301, 82, 1, 290], [302, 83, 2, 291]],
        "distance": [0.1, 0.2] if distance is None else distance,
        "state_key": name,
        "history_key": "history-" + name,
    }


class InputContractTests(unittest.TestCase):
    def test_stm_views_and_exact_float32_distance(self):
        first = row("a", "train")
        exchanged = row("b", "validation", side=2, distance=[0.1000000001, 0.2000000001])
        exchanged["ids"].reverse()
        expected = [
            "QF1-f32-STM-v1",
            [1, 82, 290, 301],
            [2, 83, 291, 302],
            [1036831949, 1045220557],
        ]
        self.assertEqual(canonical_model_input(first), expected)
        self.assertEqual(canonical_model_input(exchanged), expected)
        self.assertEqual(feature_signature(first), feature_signature(exchanged))
        views, distance = model_features(exchanged)
        self.assertEqual(views, expected[1:3])
        self.assertEqual(
            distance, [struct.unpack("<f", struct.pack("<I", b))[0] for b in expected[3]]
        )
        exchanged["distance"].reverse()
        self.assertNotEqual(feature_signature(first), feature_signature(exchanged))

    def test_schema_does_not_normalize_accepted_values(self):
        accepted = row("a", "train", distance=[0, 1])
        before = copy.deepcopy(accepted)
        validate_input(accepted)
        self.assertEqual(accepted, before)
        # Conversion has historically served sparse metadata as well as validated
        # training rows. Do not narrow that established conversion boundary.
        accepted["ids"] = [[1], [2]]
        self.assertEqual(model_features(accepted)[0], [[1], [2]])
        with self.assertRaises(ValueError):
            validate_input(accepted)

    def test_schema_rejects_invalid_inputs(self):
        variants = [
            {"side": True},
            {"side": 0},
            {"distance": [float("nan"), 0.2]},
            {"distance": [True, 0.2]},
            {"distance": [-0.1, 0.2]},
            {"distance": [0.1]},
            {"ids": [[1, 1, 82, 301], [2, 83, 291, 302]]},
            {"ids": [[1, 82, 290, 312], [2, 83, 291, 302]]},
        ]
        for difference in variants:
            with self.subTest(difference=difference), self.assertRaises(ValueError):
                validate_input({**row("a", "train"), **difference})

    def test_generic_exposure_has_no_fixed_game_count(self):
        training = row("a", "train")
        validation = row("b", "validation")
        mask = make_exposure_mask([training, validation])
        self.assertFalse(mask["rows"]["b"]["primary_eligible"])
        self.assertEqual(mask["rows"]["b"]["exposure"], ["QF1"])
        legacy = make_mask([training, validation])
        self.assertEqual({**mask, "rule": legacy["rule"]}, legacy)
        self.assertNotIn("96", mask["rule"])
        with self.assertRaises(ValueError):
            make_exposure_mask([{**training, "z": 0}, validation])

    def test_generic_canonicalization_preserves_frozen_command_bytes(self):
        # Existing frame14 CLI remains the independent compatibility caller.
        from frame14 import canonicalize as frozen_canonicalize
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "metadata.json"
            source.write_text(json.dumps([row("a", "train"), row("b", "validation")]))
            generic = directory / "generic.jsonl.gz"
            frozen = directory / "frozen.jsonl.gz"
            receipt = canonicalize(source, generic)
            self.assertEqual(
                {Path(path).name for path in receipt["source_sha256"]},
                {"metadata.py", "dataset.py", "exposure.py", "qf1.py"},
            )
            frozen_canonicalize(SimpleNamespace(metadata=str(source), output=str(frozen)))
            self.assertEqual(generic.read_bytes(), frozen.read_bytes())
            with self.assertRaises(FileExistsError):
                canonicalize(source, generic)
            source.write_text(json.dumps([{**row("a", "train"), "rootmean": 0}]))
            rejected = directory / "rejected.jsonl.gz"
            with self.assertRaises(ValueError):
                canonicalize(source, rejected)
            self.assertFalse(rejected.exists())

    def test_bound_stage_join_and_sealed_test_avoidance(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            rows = [
                row("a", "train"),
                row("b", "validation", distance=[0.3, 0.4]),
                row("c", "test"),
            ]
            files = {
                "metadata": rows,
                "mask": make_exposure_mask(rows),
                "training_labels": [
                    {"id": r["id"], "split": r["split"], "rootmean": 0.25, "z": None}
                    for r in rows[:2]
                ],
            }
            stage = {
                "kind": "QF1-training-stage",
                "train_groups": ["game-a"],
                "test_labels": str(directory / "sealed-NOT-CREATED"),
            }
            for key, content in files.items():
                path = directory / (key + ".json")
                path.write_text(json.dumps(content))
                stage.update({key: str(path), key + "_sha256": sha(path)})
            path = directory / "input.stage.json"
            path.write_text(json.dumps(stage))
            loaded, info = load_data(path)
            self.assertEqual([r["id"] for r in loaded], ["a", "b"])
            self.assertIsNone(loaded[0]["z"])
            self.assertEqual(info["counts"], {"train": 1, "validation": 1})
            labels = Path(stage["training_labels"])
            labels.write_text(
                json.dumps(files["training_labels"] + [{"id": "c", "split": "test", "z": 1}])
            )
            with self.assertRaisesRegex(ValueError, "binding changed"):
                load_stage(path)
            stage["training_labels_sha256"] = sha(labels)
            path.write_text(json.dumps(stage))
            with self.assertRaisesRegex(ValueError, "test labels prohibited"):
                load_stage(path)

    def test_jsonl_gzip_and_overlap_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl.gz"
            rows = [row("a", "train"), row("b", "validation", distance=[0.3, 0.4])]
            rows[1]["state_key"] = rows[0]["state_key"]
            path.write_bytes(gzip.compress("\n".join(map(json.dumps, rows)).encode()))
            with self.assertRaisesRegex(ValueError, "cross split"):
                load_data(path)
            self.assertEqual(load_data(path, "report")[1]["cross_split_keys"]["state_key"], 1)
            rows[1]["group"] = rows[0]["group"]
            path.write_bytes(gzip.compress("\n".join(map(json.dumps, rows)).encode()))
            with self.assertRaisesRegex(ValueError, "group crosses"):
                load_data(path, "report")

    def test_reusable_closure_does_not_import_frame_or_torch(self):
        root = Path(__file__).parent
        for name in ["qf1", "dataset", "exposure", "common"]:
            tree = ast.parse((root / (name + ".py")).read_text())
            imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(
                any(
                    module and (module.startswith("frame") or module.startswith("torch"))
                    for module in imports
                ),
                name,
            )
        model_tree = ast.parse((root / "model.py").read_text())
        self.assertIn(
            "qf1",
            [node.module for node in ast.walk(model_tree) if isinstance(node, ast.ImportFrom)],
        )
        self.assertNotIn("torch", sys.modules)


if __name__ == "__main__":
    unittest.main()
