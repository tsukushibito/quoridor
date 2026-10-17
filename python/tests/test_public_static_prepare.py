"""NN0 publication tests; no real source arrays, codec, library or teacher."""

import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import sys

import numpy as np

from quoridor_training.public_features import MODEL_INPUT, lr_group_keys, model_keys
from quoridor_training.static_public import accumulate_inputs, class_split


class PreparationPublication(unittest.TestCase):
    def setUp(self):
        self.old = {}
        cache = types.ModuleType("quoridor_training.cache")
        cache.sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        common = types.ModuleType("quoridor_training.common")

        def bound(ref, limit):
            data = Path(ref["path"]).read_bytes()
            if (
                len(data) > limit
                or len(data) != ref["bytes"]
                or hashlib.sha256(data).hexdigest() != ref["sha256"]
            ):
                raise ValueError("bound bytes")
            return data

        common.bound_file_bytes = bound
        public = types.ModuleType("quoridor_training.public_sigma")
        public.REVISION = "751186344fc52ad0c29bc65922e62c6fa915f006"
        public.NativeCompact = lambda _: object()
        public.opened_observations = lambda a, s: (
            [np.zeros(0, dtype="<u4") for _ in s["files"]],
            [],
        )
        public.download = lambda *a: None
        compact = types.ModuleType("quoridor_training.compact_cache")
        compact.IndexedPublicCorpus = types.SimpleNamespace(
            identity=lambda st: tuple(
                getattr(st, k)
                for k in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            )
        )
        snapshot = types.ModuleType("quoridor_training.snapshot")

        def write(path, value):
            Path(path).write_text(json.dumps(value) + "\n")

        snapshot.write_json = write
        self.patch = patch.dict(
            sys.modules,
            {m.__name__: m for m in (cache, common, public, compact, snapshot)},
        )
        self.patch.start()
        sys.modules.pop("quoridor_training.public_static_prepare", None)
        self.worker = importlib.import_module("quoridor_training.public_static_prepare")
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        files = [dict(path=f"part-{i}.npz", sha=f"{i:040x}", rows=2, size=1) for i in range(43)]
        source = self.root / "source.json"
        source.write_text(json.dumps(dict(revision=public.REVISION, files=files)))
        library = self.root / "library-not-loaded"
        library.write_bytes(b"x")

        def ref(p):
            b = p.read_bytes()
            return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

        self.config = dict(
            source_manifest=ref(source),
            native_library=ref(library),
            opened_evaluation_receipts=[],
            output=str(self.root / "output"),
            max_sqlite_bytes=65536,
            split_seed=32442026101702,
        )

        originals = np.zeros(81, dtype=MODEL_INPUT)
        originals["geometry"]["pawns"][:, 0] = np.arange(81)
        originals["geometry"]["pawns"][:, 1] = (np.arange(81) + 9) % 81
        originals["geometry"]["stocks"] = 10
        originals["distance"] = (0.25, 0.5)
        keys = lr_group_keys(model_keys(originals))
        self.keys = [
            next(k for k in keys if class_split(bytes(k), self.config["split_seed"]) == s)
            for s in (0, 1)
        ]

    def tearDown(self):
        self.directory.cleanup()
        sys.modules.pop("quoridor_training.public_static_prepare", None)
        self.patch.stop()

    def download(self, item, scratch, attempts, *args):
        f = scratch / Path(item["path"]).name
        f.write_bytes(b"x")
        attempts.append(dict(sha256=hashlib.sha256(b"x").hexdigest()))
        return f

    def accumulate(self, connection, path, item, native, opened):
        i = int(item["path"].split("-")[1].split(".")[0])
        accumulate_inputs(
            connection,
            np.array([self.keys[i % 2]], dtype="V28"),
            np.array([0], dtype="u1"),
        )
        return dict(
            decoded_original_rows=1,
            native_codes=[1, 0, 0, 0, 0, 0, 0],
            old_label_payload_read=False,
        )

    def test_complete_43_source_publication_and_original_multiplicity(self):
        with (
            patch.object(self.worker, "download", self.download),
            patch.object(self.worker, "accumulate_original_shard", self.accumulate),
        ):
            result = self.worker.prepare(self.config)
        root = Path(self.config["output"])
        self.assertFalse((root / "INCOMPLETE").exists())
        self.assertFalse((root / "input-classes.sqlite").exists())
        self.assertFalse((root / "source-scratch").exists())
        saved = json.loads((root / "cache.json").read_bytes())
        self.assertEqual(saved["original_observations"], 43)
        self.assertEqual(result["counts"]["train"] + result["counts"]["validation"], 43)
        self.assertEqual(saved["counts"]["pair_rows"], 2)
        self.assertEqual(len(saved["source_receipts"]), 43)
        self.assertEqual(saved["pair_record_bytes"], 37)
        self.assertFalse(saved["old_label_payload_read"])
        self.assertEqual(saved["split"]["seed"], 32442026101702)

    def test_failure_keeps_original_partial_and_no_complete_publication(self):
        def refuse(*a, **k):
            raise ValueError("original source refusal")

        with (
            patch.object(self.worker, "download", self.download),
            patch.object(self.worker, "accumulate_original_shard", refuse),
        ):
            with self.assertRaisesRegex(ValueError, "original source refusal"):
                self.worker.prepare(self.config)
        root = Path(self.config["output"])
        self.assertTrue((root / "INCOMPLETE").exists())
        self.assertTrue((root / "input-classes.sqlite").exists())
        self.assertTrue((root / "source-scratch" / "part-0.npz").exists())
        self.assertFalse((root / "cache.json").exists())
        self.assertEqual(
            json.loads((root / "failure.json").read_bytes())["message"],
            "original source refusal",
        )


if __name__ == "__main__":
    unittest.main()
