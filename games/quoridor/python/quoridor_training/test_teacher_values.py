"""Input-only scalar-sidecar boundaries, no NNUE or teacher forward."""

import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest

import numpy as np

from .teacher_values import TeacherValues
from .public_replay import mixed_batch


class TeacherValueTests(unittest.TestCase):
    def make(self, folder, *, nonfinite=False):
        folder = Path(folder)

        def ref(path):
            raw = path.read_bytes()
            return {
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "mode": f"{path.stat().st_mode & 0o777:04o}",
            }

        def data(name, raw):
            p = folder / name
            p.write_bytes(raw)
            return ref(p)

        train = np.array([0, 2], dtype="<i8")
        val = np.array([3], dtype="<i8")
        ids = np.array([0, 2, 3], dtype="<i8")
        corpus = types.SimpleNamespace(
            manifest_sha="a" * 64,
            row_count=4,
            splits=np.array([0, 0, 0, 1]),
            eligible=np.ones(4, dtype=bool),
            labels=np.array([[0.7, 1], [0.1, -1], [0.8, 1], [0.2, -1]], dtype=np.float32),
            manifest={
                "sampling": {"row_ids": ["a", "b", "c", "d"]},
                "label_columns": ["unused-search-value", "recorded-outcome"],
            },
        )

        def view(canonical, reflected):
            return {
                "source": "sidecar",
                "display_name": "name from supplied manifest",
                "identity": {"model": "input-only-fixture"},
                "value_semantics": "raw-local-stm-single-network-post-tanh",
                "canonical": data(
                    str(canonical[0]) + ".f32",
                    np.asarray(canonical, dtype="<f4").tobytes(),
                ),
                "reflected_train": data(
                    str(reflected[0]) + ".lr.f32",
                    np.asarray(reflected, dtype="<f4").tobytes(),
                ),
            }

        bank = {
            "schema": "quoridor-static-teacher-values-v1",
            "cache_manifest_sha256": corpus.manifest_sha,
            "indices": data("indices.i64", ids.tobytes()),
            "rows": len(ids),
            "row_ids_sha256": hashlib.sha256(
                json.dumps(["a", "c", "d"], separators=(",", ":")).encode()
            ).hexdigest(),
            "train_indices_sha256": hashlib.sha256(train.tobytes()).hexdigest(),
            "validation_indices_sha256": hashlib.sha256(val.tobytes()).hexdigest(),
            "canonical_input_identities": data("can-identities", bytes(len(ids) * 128)),
            "reflected_train_input_identities": data("lr-identities", bytes(len(train) * 128)),
            "source_projection": data("input-only-fixture.json", b'{"fixture":true}'),
            "reflection_semantics": "evaluated-reflected-board-and-fullhistory",
            "outcome_target": "terminal provenance",
            "targets": {
                "terminal provenance": {
                    "source": "cache",
                    "display_name": "original outcome",
                    "column": "recorded-outcome",
                    "value_semantics": "literal-stm-outcome",
                },
                "network A": view(
                    [float("nan") if nonfinite else 0.125, -0.375, 0.625],
                    [0.875, -0.125],
                ),
                "network B": view([-0.2, 0.5, 0], [0.1, -0.4]),
            },
        }
        selection = {
            "manifest": data("bank.json", json.dumps(bank).encode()),
            "objective": "network A",
        }
        return selection, corpus, train, val

    def test_manifest_names_columns_and_actual_reflection(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.make(folder)
            labels = TeacherValues(*args)
            rows = np.array([0, 2, 3])
            np.testing.assert_array_equal(
                labels.take(rows), np.array([0.125, -0.375, 0.625], dtype=np.float32)
            )
            np.testing.assert_array_equal(
                labels.take(rows, np.array([True, False, False])),
                np.array([0.875, -0.375, 0.625], dtype=np.float32),
            )
            np.testing.assert_array_equal(
                labels.take(rows, np.array([True, False, False]), target="terminal provenance"),
                args[1].labels[rows, 1],
            )
            self.assertEqual(labels.outcome_column, 1)
            self.assertEqual(
                labels.metadata["network A"]["display_name"],
                "name from supplied manifest",
            )

    def test_sidecar_identity_finite_membership_and_v_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.make(folder)
            labels = TeacherValues(*args)
            for ids, mask in (
                (np.array([1]), None),
                (np.array([3]), np.array([True])),
                (np.array([0]), np.array([1])),
            ):
                with self.subTest(ids=ids, mask=mask), self.assertRaises(ValueError):
                    labels.take(ids, mask)
            with self.assertRaises(ValueError):
                labels.take(np.array([0]), target="not supplied")
            args[1].manifest_sha = "b" * 64
            with self.assertRaises(ValueError):
                TeacherValues(*args)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                TeacherValues(*self.make(folder, nonfinite=True))

    def test_common_batch_uses_same_mask_without_rng_or_original_target_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.make(folder)
            labels = TeacherValues(*args)
            corpus = args[1]
            before = corpus.labels.copy()

            def batch(ids, mask):
                x = np.zeros((len(ids), 2, 312), dtype=np.float32)
                x[:, 0, 0] = mask
                return x, np.zeros((len(ids), 2), dtype=np.float32), corpus.labels[ids]

            corpus.batch = batch
            ids = np.array([0, 2])
            mask = np.array([True, False])
            np.random.seed(19)
            state = np.random.get_state()
            base = mixed_batch(
                corpus, None, ids, np.array([], dtype=np.int64), mask, target_column=1
            )
            teacher = mixed_batch(
                corpus,
                None,
                ids,
                np.array([], dtype=np.int64),
                mask,
                target_column=1,
                teacher_values=labels,
            )
            np.testing.assert_array_equal(base[0], teacher[0])
            np.testing.assert_array_equal(base[1], teacher[1])
            np.testing.assert_array_equal(teacher[2], np.array([0.875, -0.375], dtype=np.float32))
            np.testing.assert_array_equal(corpus.labels, before)
            after = np.random.get_state()
            self.assertEqual(state[0], after[0])
            np.testing.assert_array_equal(state[1], after[1])
            self.assertEqual(state[2:], after[2:])
