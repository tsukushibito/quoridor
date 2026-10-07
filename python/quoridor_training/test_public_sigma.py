"""Full-original stream, exact exposure IDs, sealed loader and bounded reflection."""

import hashlib
import gzip
import io
import json
import os
import signal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from .cache import load, sha
from .public_features import GEOMETRY, RECORD, SCHEMA, REVISION_NAME, features, reflect
from .public_sigma import (
    REVISION,
    SEED,
    EXCLUSION,
    download,
    header,
    mix64,
    opened_observations,
    publish_progress,
    process_shard,
    read_exact,
    selection,
)


def geometry(count):
    value = np.zeros(count, dtype=GEOMETRY)
    value["pawns"], value["stocks"] = [3, 75], [10, 10]
    return value


def source_headers():
    return [{"file": f"cycle_{i}.npz", "blob": f"{i:040x}", "rows": 100} for i in range(43)]


def fixture_cache(root):
    parts = []
    for split, name in enumerate(("train", "validation")):
        rows = np.zeros(2, dtype=RECORD)
        rows["geometry"] = geometry(2)
        rows["distance"] = [0.1, 0.1]
        rows["z"] = [1, -1]
        rows["row"] = [split * 2, split * 2 + 1]
        rows.tofile(root / (name + ".bin"))
        parts.append(
            {"name": name, "file": name + ".bin", "rows": 2, "sha256": sha(root / (name + ".bin"))}
        )
    parts.append(
        {
            "name": "test-sealed",
            "file": "test-sealed.bin",
            "rows": 1,
            "sha256": "not created: training must not open test",
        }
    )
    parts.append(
        {
            "name": "evaluation-opened",
            "file": "evaluation-opened.bin",
            "rows": 1,
            "sha256": "not created: old evaluation is not train/validation",
        }
    )
    (root / "cache.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "revision": REVISION,
                "dataset_revision": REVISION_NAME,
                "original_only": True,
                "record_bytes": RECORD.itemsize,
                "test_sealed": True,
                "source_shards": source_headers(),
                "partitions": parts,
            }
        )
    )


class PublicSigmaContracts(unittest.TestCase):
    def test_scale_and_constant_use_only_original_train_without_test_or_torch(self):
        from .train import prepare_statistics

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_cache(root)
            result = prepare_statistics(root, root / "moments")
            self.assertFalse(result["test_opened"])
            self.assertEqual(result["model_forward_rows"], 0)
            scale = json.loads((root / "moments/train-only-scale.json").read_text())
            constant = json.loads((root / "moments/train-only-constant.json").read_text())
            validation = np.fromfile(root / "validation.bin", dtype=RECORD)
            validation["distance"] = [0.7, 0.9]
            validation["z"] = 1
            validation.tofile(root / "validation.bin")
            manifest = json.loads((root / "cache.json").read_text())
            manifest["partitions"][1]["sha256"] = sha(root / "validation.bin")
            (root / "cache.json").write_text(json.dumps(manifest))
            prepare_statistics(root, root / "changed-validation")
            other = json.loads((root / "changed-validation/train-only-scale.json").read_text())
            self.assertEqual(scale["mu_f32"], other["mu_f32"])
            self.assertEqual(scale["sigma_f32"], other["sigma_f32"])
            self.assertEqual(constant["row_mean_constant"], 0)
            self.assertEqual(
                constant["row_mean_constant"],
                json.loads((root / "changed-validation/train-only-constant.json").read_text())[
                    "row_mean_constant"
                ],
            )

    def test_progress_flushes_payload_and_rejects_inconsistent_counts(self):
        from contextlib import ExitStack

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with ExitStack() as stack:
                streams = [stack.enter_context((root / f"{i}.bin").open("wb")) for i in range(4)]
                rejected = stack.enter_context(gzip.open(root / "excluded.gz", "wb"))
                for stream in streams:
                    stream.write(bytes(RECORD.itemsize))
                rejected.write(b"original rejection bytes")
                publish_progress(root, streams, rejected, {"counts": [1, 1, 1, 1]})
                self.assertEqual(
                    json.loads((root / "progress.json").read_text())["flushed_partition_bytes"],
                    [66] * 4,
                )
                before = (root / "progress.json").read_bytes()
                self.assertGreater((root / "excluded.gz").stat().st_size, 0)
                with self.assertRaisesRegex(ValueError, "flushed partition payload"):
                    publish_progress(root, streams, rejected, {"counts": [2, 1, 1, 1]})
                self.assertEqual((root / "progress.json").read_bytes(), before)
            self.assertEqual(
                gzip.decompress((root / "excluded.gz").read_bytes()), b"original rejection bytes"
            )

    def test_worker_signal_raises_through_prepare_finally(self):
        from . import public_sigma
        from .cycle_process import CycleStopped

        finalized = []

        def prepare(_config):
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            finally:
                finalized.append("worker finally executed")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "admission.json").write_text(json.dumps({"admission": "within", "errors": []}))
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "storage_admission": str(root / "admission.json"),
                        "storage_admission_sha": sha(root / "admission.json"),
                        "expected_files_sha256": {},
                    }
                )
            )
            with (
                patch.object(public_sigma, "prepare", side_effect=prepare),
                patch("sys.argv", ["producer", "--config", str(root / "config.json"), "--worker"]),
            ):
                with self.assertRaisesRegex(CycleStopped, "SIGTERM"):
                    public_sigma.main()
        self.assertEqual(finalized, ["worker finally executed"])

    def test_verified_blob_reuse_readonly_network_free(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b"fixed fixture blob"
            file = root / "existing.npz"
            file.write_bytes(payload)
            item = {
                "path": "cycle.npz",
                "size": len(payload),
                "sha": hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest(),
            }
            reuse = {"local_path": str(file), "sha256": hashlib.sha256(payload).hexdigest()}
            attempts = []
            with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
                self.assertEqual(download(item, root / "scratch", attempts, 0, reuse), file)
                self.assertEqual(attempts[0]["bytes"], 0)
                file.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "pinned blob changed"):
                    download(item, root / "scratch", [], 0, reuse)

    def test_all_originals_keep_legacy_alias_split_without_candidate_cut(self):
        blob = "a" * 40
        candidates, splits, _ = selection(blob, 10000)
        self.assertTrue(candidates.all())
        salt = int.from_bytes(hashlib.sha256((blob + str(SEED)).encode()).digest()[:8], "little")
        legacy_u = (
            mix64(np.arange(10000, dtype=np.uint64) ^ np.uint64(salt) ^ np.uint64(1))
            >> np.uint64(11)
        ).astype(np.float64) / 2**53
        expected = np.where(legacy_u < 10 / 11, 0, np.where(legacy_u < 10.5 / 11, 1, 2))
        np.testing.assert_array_equal(splits, expected)
        self.assertEqual(set(splits), {0, 1, 2})
        self.assertTrue(candidates[-100:].all())

    def test_stream_front_only_observation_exclusions_and_opened_quarantine(self):
        class QualifiedFixtureNative:
            # Input legality is covered by real Rust fixtures. This unit verifies
            # producer flow, per-row status handling and independently saved z.
            def convert(self, planes):
                if not np.isfinite(planes).all():
                    raise AssertionError("naiveLR half must never enter native qualification")
                n = len(planes)
                bits = np.packbits(
                    features(geometry(n)).astype(np.uint8).reshape(n, 624),
                    axis=1,
                    bitorder="little",
                )
                status = np.zeros(n, dtype=np.uint8)
                status[2] = 2
                return bits, np.full((n, 2), 0.1, dtype=np.float32), status

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            states = np.ones((8, 8, 9, 9), dtype="<f4")
            states[4:] = np.nan
            values = np.array([1, -1, 1, 0, np.nan, np.nan, np.nan, np.nan], dtype="<f4")
            path = root / "shard.npz"
            np.savez_compressed(path, states=states, values=values)
            streams = [io.BytesIO() for _ in range(4)]
            rejected = io.BytesIO()
            info = process_shard(
                path,
                {"rows": 8, "sha": "a" * 40},
                0,
                QualifiedFixtureNative(),
                rejected,
                streams,
                np.array([1], dtype="<u4"),
            )
            saved = [np.frombuffer(s.getvalue(), dtype=RECORD) for s in streams]
            rows = np.concatenate(saved)
            self.assertEqual(set(rows["row"]), {0, 1})
            self.assertEqual(set(rows["z"]), {-1, 1})
            self.assertEqual(len(np.unique(rows["geometry"])), 1)
            self.assertEqual(saved[3]["row"].tolist(), [1])
            self.assertEqual(info["decoded_original_rows"], 4)
            exclusions = np.frombuffer(rejected.getvalue(), dtype=EXCLUSION)
            self.assertEqual(exclusions["row"].tolist(), [2, 3])
            self.assertEqual(exclusions["reason"].tolist(), [2, 7])
            self.assertEqual(info["labels"]["zero_unknown_termination"], 1)

    def test_header_short_payload_fails_closed(self):
        stream = io.BytesIO()
        np.lib.format.write_array(stream, np.zeros((3, 8, 9, 9), dtype="<f4"))
        stream.seek(0)
        self.assertEqual(header(stream), (3, 8, 9, 9))
        self.assertEqual(len(read_exact(stream, 3 * 648 * 4)), 3 * 648 * 4)
        with self.assertRaises(ValueError):
            read_exact(stream, 1)

    def test_legacy_opened_ID_import_is_exact_blob_original_not_input_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            headers = source_headers()
            dtype = np.dtype(
                {
                    "names": ["shard", "row", "alias"],
                    "formats": ["<u2", "<u4", "<u4"],
                    "offsets": [90, 92, 96],
                    "itemsize": 174,
                }
            )
            ids = np.zeros(3, dtype=dtype)
            ids["shard"] = [0, 0, 1]
            ids["row"] = ids["alias"] = [1, 3, 2]
            ids.tofile(root / "test-sealed.bin")
            manifest = {
                "schema": "quoridor-public-compact-v1",
                "revision": REVISION,
                "original_only": True,
                "source_shards": headers,
            }
            (root / "cache.json").write_text(json.dumps(manifest))
            result = {
                "evaluation_cache_binding": {
                    "path": str(root),
                    "test_opened": True,
                    "dataset_sha": sha(root / "cache.json"),
                    "partitions": [
                        {
                            "name": "test-sealed",
                            "file": "test-sealed.bin",
                            "rows": 3,
                            "sha256": sha(root / "test-sealed.bin"),
                        }
                    ],
                }
            }
            (root / "opened.json").write_text(json.dumps(result))
            descriptor = {
                "evaluation_receipt": str(root / "opened.json"),
                "receipt_sha256": sha(root / "opened.json"),
            }
            opened, refs = opened_observations(
                [descriptor], {"files": [{"sha": x["blob"], "rows": x["rows"]} for x in headers]}
            )
            self.assertEqual(opened[0].tolist(), [1, 3])
            self.assertEqual(opened[1].tolist(), [2])
            self.assertEqual(sum(len(x) for x in opened), 3)
            self.assertEqual(refs[0]["rows"], 3)
            with self.assertRaisesRegex(ValueError, "receipt is required"):
                opened_observations([], {"files": []})


class CompactBoundary(unittest.TestCase):
    def test_bounded_loader_and_online_reflection_preserve_target_and_sealing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_cache(root)
            corpus = load(root)
            np.testing.assert_array_equal(corpus.splits, [0, 0, 1, 1])
            x, d, y = corpus.batch([0, 3])
            rx, rd, ry = corpus.batch([0, 3], np.array([True, False]))
            np.testing.assert_array_equal(d, rd)
            np.testing.assert_array_equal(y, ry)
            np.testing.assert_array_equal(rx[0], features(reflect(geometry(1)))[0])
            np.testing.assert_array_equal(rx[1], x[1])
            np.testing.assert_array_equal(corpus.batch([0, 3])[0], x)
            self.assertEqual(len(corpus.families), 1)
            self.assertFalse((root / "test-sealed.bin").exists())
            self.assertFalse((root / "evaluation-opened.bin").exists())
            with self.assertRaises(ValueError):
                corpus.batch([0], np.array([1]))

    def test_frozen_cache_mismatch_rejected_before_missing_test(self):
        from .train import verify_test_cache_before_open

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_cache(root)
            with self.assertRaisesRegex(ValueError, "before label"):
                verify_test_cache_before_open(
                    root, {"cache_schema": SCHEMA, "dataset_sha": "wrong"}
                )
            verify_test_cache_before_open(
                root, {"cache_schema": SCHEMA, "dataset_sha": sha(root / "cache.json")}
            )


if __name__ == "__main__":
    unittest.main()
