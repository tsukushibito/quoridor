"""New NN0 owning-loop mid-chunk retention and notification failure boundary."""

from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np

from quoridor_training import public_static_values as values


class RetainedProductionProgress(unittest.TestCase):
    def test_first_both_teachers_are_flushed_midchunk_once_without_tail_or_replay(self):
        m, n = 16420, 8210
        keys = np.zeros(m, dtype="V28")
        raw = keys.view("u1").reshape(m, 28)
        raw[:, :8] = np.arange(m, dtype="<u8").view("u1").reshape(m, 8)
        pairs = np.zeros(n, dtype=[("key", "V28")])
        pairs["key"] = keys[::2]
        head_rows = []

        class Head:
            def __init__(self, *args, **kwargs):
                self.rows = 0
                head_rows.append(self)

            def __call__(self, inputs):
                self.rows += len(inputs)
                return np.full(len(inputs), 0.5, dtype="<f4")

            def facts(self):
                return dict(
                    explicit_test_double=True,
                    head_seconds=0.1,
                    logical_rows_attempted=self.rows,
                    failed_attempted_rows=0,
                )

        class Encoder:
            def __init__(self, *args, **kwargs):
                pass

            def encode(self, selected, **kwargs):
                x = np.zeros((len(selected), 8, 9, 9), dtype="<f4")
                return x, np.zeros((len(selected), 20, 9, 9), dtype="<f4")

        @contextmanager
        def reader(ref):
            yield {}, pairs

        def chunks(rows, capacity):
            for first in range(0, m, capacity):
                ix = np.arange(first, min(m, first + capacity))
                yield ix // 2, (ix % 2).astype("u1"), keys[ix]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys[:1].tofile(root / "keys")
            np.array([0.25], dtype="<f4").tofile(root / "reused")
            for name in ("model-S", "model-C", "core", "c20"):
                (root / name).write_bytes(b"FAKE")
            ref = values.file_ref
            cfg = dict(
                input_classes={"test_double": True},
                core_library=ref(root / "core"),
                c20_library=ref(root / "c20"),
                models={k: ref(root / ("model-" + k)) for k in ("S", "C")},
                device="cpu",
                cpu_threads=1,
                output=str(root / "bank"),
                actual_orientation_rows=m,
                inclusive_row_limit=4 * n + 256,
                batch_rows=256,
                execution_binding={"explicit_test_double": True},
            )
            boundary = dict(
                status="PASS",
                input_classes=cfg["input_classes"],
                core_library=cfg["core_library"],
                c20_library=cfg["c20_library"],
                models=cfg["models"],
                device="cpu",
                route_devices_precision=values.runtime_devices(cfg),
                planned_extra_head_rows=0,
                logical_rows_attempted=5,
                keys=ref(root / "keys"),
                batch_values={k: ref(root / "reused") for k in ("S", "C")},
                model_identities={
                    k: list(values.file_identity(v["path"])) for k, v in cfg["models"].items()
                },
            )
            (root / "boundary.json").write_text(json.dumps(boundary))
            cfg["runtime_boundary"] = ref(root / "boundary.json")
            notices = []

            def notify(packet_ref):
                packet = json.loads(Path(packet_ref["path"]).read_bytes())
                self.assertEqual(packet["new_logical_rows"], 16384)
                self.assertEqual(packet["retained_reused_unique_orientation_inputs"], 1)
                self.assertIsNone(packet["partial_bank"]["final_sha256"])
                mapped = np.memmap(
                    packet["partial_bank"]["path"], mode="r", dtype="<f4", shape=(n, 2)
                )
                indices = np.fromfile(
                    packet["retained_indices"]["path"],
                    dtype=[("pair", "<u8"), ("orientation", "u1"), ("reused", "u1")],
                )
                self.assertEqual(len(indices), 16385)
                expected = np.where(indices["reused"], 0.25, 0.5)
                np.testing.assert_array_equal(
                    mapped[indices["pair"], indices["orientation"]], expected
                )
                self.assertTrue(np.isnan(mapped.reshape(-1)[16385]))
                mapped._mmap.close()
                notices.append(packet["teacher"])
                # Production must continue after this delivery failure.
                raise OSError("explicit fake notification failure")

            torch = types.SimpleNamespace(
                set_num_threads=lambda n: None, get_num_interop_threads=lambda: 1
            )
            with (
                patch.dict(sys.modules, {"torch": torch}),
                patch.object(values, "input_pairs", reader),
                patch.object(values, "actual_orientation_count", return_value=m),
                patch.object(values, "oriented_keys", chunks),
                patch.object(
                    values, "reflected_keys", side_effect=lambda k: np.zeros(len(k), dtype="V28")
                ),
                patch.object(values, "StaticInputs", Encoder),
                patch.object(values, "StaticHead", Head),
                patch.object(
                    values,
                    "ClassObservations",
                    return_value=types.SimpleNamespace(validate_values=lambda t: None),
                ),
            ):
                result = values.label_values(cfg, progress_callback=notify)
            self.assertEqual(notices, ["S", "C"])
            self.assertEqual([head.rows for head in head_rows], [m - 1, m - 1])
            self.assertFalse((root / "bank/INCOMPLETE").exists())
            self.assertTrue(Path(result["manifest"]["path"]).exists())
            for kind in ("S", "C"):
                self.assertTrue((root / f"bank/first-{kind}-notification-failure.json").exists())


if __name__ == "__main__":
    unittest.main()
