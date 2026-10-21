"""NN0 tests of the published outcome codec, with a synthetic config-validation port."""

import hashlib
import json
import tempfile
import struct
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from quoridor_training.terminal_cache import TerminalCorpus, COMMON_WIDTHS
from quoridor_training.public_features import RECORD


class ConfiguredOutcomeCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = {"families": 3, "batch_start": 0, "batch_count": 3}
        self.patch = patch(
            "quoridor_training.terminal_cache.common_cache_config",
            return_value=self.cfg,
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def fixture(self, mask=None):
        # Actual regular files/hash checks/memmaps; metadata, geometry and labels are synthetic.
        records = bytearray()
        for i, z in enumerate([1, -1, 0]):
            body = struct.pack(
                "<4BQQffBBI",
                4,
                76,
                10,
                10,
                0,
                0,
                np.float32(8 / 80),
                np.float32(8 / 80),
                z & 255,
                0,
                i,
            )
            records.extend(body + hashlib.sha256(body[:28]).digest())
        self.assertEqual(len(records), 3 * RECORD.itemsize)
        sampling = np.zeros(
            3,
            dtype=[("family_code", "<u4"), ("split", "u1"), ("primary_eligible", "u1")],
        )
        sampling["primary_eligible"] = [1, 1, 0]
        raw = {
            "geometry.bin": bytes(records),
            "distance-steps.u8": np.array([[8, 8]] * 3, dtype=np.uint8).tobytes(),
            "terminal-margin.f32": np.array([8, -8, np.nan], dtype="<f4").tobytes(),
            "labels.f32": np.array([[1, 1], [-1, -1], [0, np.nan]], dtype="<f4").tobytes(),
            "completed-root-raw.f32": np.array([2, -2, -0.0], dtype="<f4").tobytes(),
            "common-eligible.u8": bytes([1, 1, 0] if mask is None else mask),
            "sampling.bin": sampling.tobytes(),
        }
        for name, data in raw.items():
            (self.root / name).write_bytes(data)
        m = {
            "schema": "quoridor-common-corpus-terminal-geometry-v3",
            "feature_count": 312,
            "rows": 3,
            "allow_test": False,
            "label_columns": ["rootmean", "z", "terminal_margin", "completed_root_raw"],
            "files": {n: n for n in COMMON_WIDTHS},
            "sha256": {n: hashlib.sha256(v).hexdigest() for n, v in raw.items()},
            "file_bytes": {n: len(v) for n, v in raw.items()},
            "stream_intake": {
                "status": "complete",
                "scope": "common-corpus",
                "publication_protocol": "incomplete-marker-last-v1",
            },
            "common_corpus": {
                "common_eligible_rows": 2 if mask is None else sum(mask),
                "common_eligible_by_split": {
                    "train": 2 if mask is None else sum(mask),
                    "validation": 0,
                },
            },
            "sampling": {
                "schema": "quoridor-common-corpus-sampling-v1",
                "file": "sampling.bin",
                "format": "<IBB",
                "width_B": 6,
                "families": [{"family": "a" * 64, "game": "first", "split": "train"}],
                "games": [
                    {"game": g, "family_code": 0, "start": i, "rows": 1}
                    for i, g in enumerate(["first", "second", "unknown"])
                ],
                "row_ids": ["row0", "row1", "row2"],
                "rows_by_family": [3],
                "common_eligible_by_family": [2 if mask is None else sum(mask)],
            },
        }
        self.save(m)
        return m

    def save(self, m):
        (self.root / "cache.json").write_text(json.dumps(m))

    def test_configured_outcomes_include_near_goal_raw_and_preserve_unknown_and_chronology(
        self,
    ):
        self.fixture()
        corpus = TerminalCorpus(self.root)
        self.assertEqual(corpus.eligible.tolist(), [True, True, False])
        self.assertEqual(corpus.labels[:2, 1].tolist(), [1, -1])
        self.assertTrue(np.isnan(corpus.labels[2, 1]))
        self.assertEqual(
            corpus.raw_root_scores.view("<u4").tolist(),
            np.array([2, -2, -0.0], dtype="<f4").view("<u4").tolist(),
        )
        self.assertEqual([corpus.rows[i]["game"] for i in range(3)], ["first", "second", "unknown"])
        self.assertEqual(corpus.groups.tolist(), [0, 0, 0])
        self.assertEqual(corpus.rows[0]["teacher_type"], "terminal_outcome")
        self.assertIsNone(corpus.rows[2]["z"])

    def test_configured_outcome_mask_refuses_old_raw_range_projection(self):
        self.fixture(mask=[0, 0, 0])
        with self.assertRaisesRegex(ValueError, "teacher/distance range"):
            TerminalCorpus(self.root)

    def test_configured_game_blocks_reject_repeat_gap_and_family_split_drift(self):
        for kind in ("repeat", "gap", "split"):
            with self.subTest(kind=kind):
                m = self.fixture()
                if kind == "repeat":
                    m["sampling"]["games"][1]["game"] = "first"
                elif kind == "gap":
                    m["sampling"]["games"][1]["start"] = 2
                else:
                    m["sampling"]["families"][0]["split"] = "validation"
                self.save(m)
                with self.assertRaises(ValueError):
                    TerminalCorpus(self.root)

    def test_configured_publication_refuses_incomplete_byte_drift_and_actual_row_overflow(
        self,
    ):
        m = self.fixture()
        (self.root / "intake-incomplete.json").write_text("synthetic interrupted publication")
        with self.assertRaises(ValueError):
            TerminalCorpus(self.root)
        (self.root / "intake-incomplete.json").unlink()
        (self.root / "common-eligible.u8").write_bytes(bytes([1, 1]))
        with self.assertRaisesRegex(ValueError, "file identity"):
            TerminalCorpus(self.root)
        m = self.fixture()
        m["rows"] = 601
        self.save(m)
        with self.assertRaisesRegex(ValueError, "length/count"):
            TerminalCorpus(self.root)


if __name__ == "__main__":
    unittest.main()
