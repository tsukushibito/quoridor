"""One zero-forward synthetic owning setup/close/error-serialization definition."""

import argparse
import ast
import calendar
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest


class IndexedCleanup(unittest.TestCase):
    def test_setup_primary_all_owned_closes_and_training_serialization(self):
        attempts, captured = [], []
        setup = ValueError("synthetic setup E after both owned maps/streams")
        map_error = OSError("synthetic map close C")
        stream_error = OSError("synthetic stream close D")

        class FakeMap:
            def __init__(self, split, error):
                self.split, self.error, self.closed = split, error, False
                self._mmap = self

            def close(self):
                attempts.append("map:" + self.split)
                if self.error is not None:
                    raise self.error
                self.closed = True

        class Stream:
            def __init__(self, real, error):
                self.real, self.error = real, error
                self.split = Path(real.name).stem if isinstance(real.name, str) else ""

            def fileno(self):
                return self.real.fileno()

            def close(self):
                attempts.append("stream:" + self.split)
                self.real.close()
                if self.error is not None:
                    raise self.error

        class SetupMaps(dict):
            def __setitem__(self, split, mapped):
                super().__setitem__(split, mapped)
                if split == "validation":
                    raise setup

        raw = SOURCE.read_bytes()
        node = next(
            n
            for n in ast.parse(raw).body
            if isinstance(n, ast.ClassDef) and n.name == "IndexedPublicCorpus"
        )
        stream_count = 0

        def wrapped_fdopen(fd, mode):
            nonlocal stream_count
            stream = Stream(os.fdopen(fd, mode), stream_error if stream_count == 0 else None)
            stream.split = ("train", "validation")[stream_count]
            stream_count += 1
            captured.append(stream)
            return stream

        def mapped(stream, **kwargs):
            self.assertEqual(kwargs, {"dtype": record, "mode": "r", "shape": (1,)})
            item = FakeMap(stream.split, map_error if stream.split == "train" else None)
            captured.append(item)
            return item

        record = SimpleNamespace(itemsize=66)
        namespace = {
            "__package__": "quoridor_training",
            "Path": Path,
            "json": json,
            "datetime": datetime,
            "calendar": calendar,
            "stat": stat,
            "os": SimpleNamespace(
                open=os.open,
                fdopen=wrapped_fdopen,
                fstat=os.fstat,
                O_RDONLY=os.O_RDONLY,
                O_NOFOLLOW=os.O_NOFOLLOW,
            ),
            "np": SimpleNamespace(memmap=mapped),
            "RECORD": record,
            "SCHEMA": "explicitly-synthetic-public-schema",
            "REVISION_NAME": "explicitly-synthetic-public-revision",
        }
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
        indexed = namespace["IndexedPublicCorpus"]

        class Partial(indexed):
            def __setattr__(self, name, value):
                super().__setattr__(name, SetupMaps(value) if name == "maps" else value)

        with tempfile.TemporaryDirectory(prefix="synthetic-indexed-close-", dir=TMP) as directory:
            root = Path(directory)
            for split in ("train", "validation"):
                (root / (split + ".bin")).write_bytes(b"x" * 66)
            manifest = {
                "schema": namespace["SCHEMA"],
                "dataset_revision": namespace["REVISION_NAME"],
                "original_only": True,
                "test_sealed": True,
                "record_bytes": 66,
                "source_shards": [None] * 43,
                "partitions": [
                    {
                        "name": s,
                        "file": s + ".bin",
                        "bytes": 66,
                        "rows": 1,
                        "sha256": "synthetic-owning-hash",
                    }
                    for s in ("train", "validation")
                ],
            }
            path = root / "cache.json"
            path.write_text(json.dumps(manifest))
            ref = {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "mode": f"{path.stat().st_mode & 511:04o}",
            }
            acceptance = {
                "public_membership": ref,
                "source_env_data_reader_STOP": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "accepted_observations": {
                    "partitions": {
                        s: {"scanned": 1, "stream_SHA256": "synthetic-owning-hash"}
                        for s in ("train", "validation")
                    }
                },
            }
            partial = Partial.__new__(Partial)
            qualified = None
            try:
                Partial.__init__(partial, ref, acceptance)
                qualified = partial
            except BaseExceptionGroup as error:
                setup_group = error
            self.assertIsNone(qualified)
            self.assertEqual(setup_group.exceptions, (setup, map_error, stream_error))
            self.assertIs(setup_group.exceptions[0], setup)
            self.assertEqual(
                attempts, ["map:train", "map:validation", "stream:train", "stream:validation"]
            )
            self.assertTrue(all(s.real.closed for s in captured if isinstance(s, Stream)))
            self.assertTrue(
                next(
                    m for m in captured if isinstance(m, FakeMap) and m.split == "validation"
                ).closed
            )
            states = json.loads(setup_group.__notes__[-1])
            self.assertFalse(states["cleanup_complete"])
            self.assertEqual(states["remaining_maps"], ["train"])
            self.assertEqual(states["remaining_streams"], ["train"])
            self.assertEqual(
                [s["status"] for s in states["stages"]],
                ["FAILED_CLOSE_STATE_UNKNOWN", "CLOSED", "FAILED_CLOSE_STATE_UNKNOWN", "CLOSED"],
            )

            # Run the existing trainer's recursive error/finalizer functions, not its model/training code.
            names = {"_exception_record", "_attempt_finalization", "_finalize_training"}
            nodes = [
                n
                for n in ast.parse(TRAINER.read_bytes()).body
                if isinstance(n, ast.FunctionDef) and n.name in names
            ]
            trainer = {"json": json, "write": lambda p, value: p.write_text(json.dumps(value))}
            exec(compile(ast.Module(body=nodes, type_ignores=[]), str(TRAINER), "exec"), trainer)
            serialized = trainer["_exception_record"](setup_group)
            self.assertEqual(
                [e["message"] for e in serialized["errors"]],
                [str(setup), str(map_error), str(stream_error)],
            )
            self.assertEqual(json.loads(serialized["notes"][-1]), states)

            # The successful-construction close path must attempt all independent actions too.
            attempts.clear()
            normal = indexed.__new__(indexed)
            normal.maps = {
                "train": FakeMap("train", map_error),
                "validation": FakeMap("validation", None),
            }
            normal.streams = {}
            for split, error in (("train", stream_error), ("validation", None)):
                stream = Stream((root / (split + ".bin")).open("rb"), error)
                normal.streams[split] = stream
            later_map, later_stream = normal.maps["validation"], normal.streams["validation"]
            with self.assertRaises(BaseExceptionGroup) as final:
                trainer["_finalize_training"](
                    root,
                    [("public_close", normal.close)],
                    None,
                    lambda: {"fit_updates": 0, "synthetic": True},
                )
            child_group = final.exception.exceptions[0]
            self.assertEqual(child_group.exceptions, (map_error, stream_error))
            self.assertEqual(
                attempts, ["map:train", "map:validation", "stream:train", "stream:validation"]
            )
            self.assertTrue(later_map.closed and later_stream.real.closed)
            receipt = json.loads((root / "finalization-errors.json").read_bytes())
            self.assertIsNone(receipt["primary_exception"])
            self.assertEqual(
                [e["message"] for e in receipt["finalization_errors"][0]["errors"]],
                [str(map_error), str(stream_error)],
            )
            self.assertEqual(receipt["stages"], [{"stage": "public_close", "status": "FAILED"}])
            self.assertFalse(
                json.loads(receipt["finalization_errors"][0]["notes"][0])["cleanup_complete"]
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--trainer", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    SOURCE, TRAINER, TMP = args.source, args.trainer, args.TMP
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IndexedCleanup)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forward_rows": 0,
                "fit_updates": 0,
                "synthetic_handles_and_metadata": True,
                "failures": [s for _, s in result.failures],
                "errors": [s for _, s in result.errors],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
