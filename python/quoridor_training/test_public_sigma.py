"""Synthetic qualification, sibling split and streaming reservoir contracts."""

import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from .public_sigma import RECORD, download, header, keep_lowest, main, read_exact, selection


class PublicSigmaContracts(unittest.TestCase):
    def test_verified_blob_reuse_is_read_only_and_network_free(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"fixed fixture blob"
            blob = root / "existing.npz"
            blob.write_bytes(data)
            item = {
                "path": "runs/data_9x9_fix/cycle_0014.npz",
                "size": len(data),
                "sha": hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest(),
            }
            reuse = {"local_path": str(blob), "sha256": hashlib.sha256(data).hexdigest()}
            attempts = []
            with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
                self.assertEqual(download(item, root / "scratch", attempts, 0, reuse), blob)
                self.assertEqual(blob.read_bytes(), data)
                self.assertEqual(attempts[0]["bytes"], 0)
                blob.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "pinned blob changed"):
                    download(item, root / "scratch", [], 0, reuse)

    def test_missing_or_failed_admission_stops_before_child_or_compute(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config.json"
            admission = root / "admission.json"
            for settings in (
                {},
                {"storage_admission": str(admission), "storage_admission_sha": "wrong"},
            ):
                config.write_text(json.dumps(settings))
                admission.write_text(json.dumps({"admission": "within", "errors": []}))
                with (
                    patch("sys.argv", ["public_sigma", "--config", str(config)]),
                    patch("os.sched_setaffinity") as affinity,
                ):
                    with self.assertRaisesRegex(ValueError, "storage admission"):
                        main()
                    affinity.assert_not_called()

    def test_source_identity_splits_are_repeatable_and_cover_tail(self):
        candidates, splits, _ = selection("a" * 40, 10000)
        c2, s2, _ = selection("a" * 40, 10000)
        np.testing.assert_array_equal(candidates, c2)
        np.testing.assert_array_equal(splits, s2)
        self.assertTrue(candidates[:100].any())
        self.assertTrue(candidates[-100:].any())
        self.assertEqual(set(splits[candidates]), {0, 1, 2})
        # Both source halves address exactly the same original alias index.
        rows = np.array([13, 10013])
        np.testing.assert_array_equal(splits[rows % 10000], [splits[13]] * 2)

    def test_reservoir_is_order_independent_and_preserves_outcomes(self):
        rows = np.zeros(7, dtype=RECORD)
        rows["row"] = np.arange(7)
        rows["priority"] = [13, 12, 11, 3, 2, 1, 14]
        rows["z"] = [-1, 1, -1, 1, -1, 1, -1]
        empty = np.zeros(0, dtype=RECORD)
        a = keep_lowest(keep_lowest(empty, rows[:3], 3), rows[3:], 3)
        b = keep_lowest(keep_lowest(empty, rows[3:], 3), rows[:3], 3)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(set(a["row"]), {3, 4, 5})
        self.assertEqual(set(a["z"]), {-1, 1})

    def test_header_and_short_payload_fail_closed(self):
        stream = io.BytesIO()
        np.lib.format.write_array(stream, np.zeros((3, 8, 9, 9), dtype="<f4"))
        stream.seek(0)
        self.assertEqual(header(stream), (3, 8, 9, 9))
        self.assertEqual(len(read_exact(stream, 3 * 648 * 4)), 3 * 648 * 4)
        with self.assertRaises(ValueError):
            read_exact(stream, 1)


if __name__ == "__main__":
    unittest.main()


class CompactBoundary(unittest.TestCase):
    def test_loader_batches_lossless_and_does_not_open_sealed_test(self):
        import hashlib
        import json
        from pathlib import Path
        import tempfile
        from .cache import load, sha

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parts = []
            for split, name in enumerate(("train", "validation")):
                rows = np.zeros(3, dtype=RECORD)
                rows["bits"][:, 0] = [1, 2, 4]
                rows["distance"] = [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4]]
                rows["z"] = [1, -1, 1]
                rows["split"], rows["row"] = split, np.arange(3)
                for row in rows:
                    row["model_sha"] = np.frombuffer(
                        hashlib.sha256(row["bits"].tobytes() + row["distance"].tobytes()).digest(),
                        dtype=np.uint8,
                    )
                rows.tofile(root / (name + ".bin"))
                parts.append(
                    {
                        "name": name,
                        "file": name + ".bin",
                        "rows": 3,
                        "sha256": sha(root / (name + ".bin")),
                    }
                )
            parts.append(
                {
                    "name": "test-sealed",
                    "file": "test-sealed.bin",
                    "rows": 1,
                    "sha256": "deliberately absent sealed labels",
                }
            )
            (root / "cache.json").write_text(
                json.dumps(
                    {
                        "schema": "quoridor-public-compact-v1",
                        "revision": "fixed",
                        "test_sealed": True,
                        "partitions": parts,
                    }
                )
            )
            corpus = load(root)
            x, d, y = corpus.batch([4, 0, 2])
            self.assertEqual(x.shape, (3, 2, 312))
            np.testing.assert_array_equal(np.flatnonzero(x[0].reshape(-1)), [1])
            np.testing.assert_array_equal(y[:, 1], [-1, 1, 1])
            self.assertTrue(np.isnan(y[:, 0]).all())
            np.testing.assert_array_equal(d[0], np.array([0.2, 0.3], dtype=np.float32))
            corpus.verify_binding()
            with self.assertRaises(FileNotFoundError):
                load(root, allow_test=True)


class FinalEvaluationBoundary(unittest.TestCase):
    def test_frozen_corpus_mismatch_rejected_before_loading_labels(self):
        import json
        from pathlib import Path
        import tempfile
        from .cache import sha
        from .train import verify_test_cache_before_open

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "cache.json"
            manifest.write_text(
                json.dumps({"schema": "quoridor-public-compact-v1", "partitions": []})
            )
            freeze = {"cache_schema": "quoridor-public-compact-v1", "dataset_sha": sha(manifest)}
            verify_test_cache_before_open(root, freeze)
            manifest.write_text(
                json.dumps({"schema": "quoridor-public-compact-v1", "partitions": ["other"]})
            )
            with self.assertRaisesRegex(ValueError, "before label opening"):
                verify_test_cache_before_open(root, freeze)
            manifest.write_text(json.dumps({"schema": "native"}))
            with self.assertRaisesRegex(ValueError, "before label opening"):
                verify_test_cache_before_open(root, freeze)
            manifest.unlink()
            with self.assertRaisesRegex(ValueError, "before label opening"):
                verify_test_cache_before_open(root, freeze)
