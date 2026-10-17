"""New batch-host NN0 boundaries; no native library or model is loaded."""

import ctypes
import types
import unittest
from unittest.mock import patch

import numpy as np

from quoridor_training.static_teacher_heads import StaticHead
from quoridor_training.static_teacher_inputs import StaticInputs


class StaticBatchHostTests(unittest.TestCase):
    def test_core_refusal_never_enters_c20(self):
        reader = StaticInputs.__new__(StaticInputs)
        reader.batch_rows = 4
        calls = []

        def core(keys, rows, output, status):
            calls.append("core")
            np.ctypeslib.as_array(status, shape=(rows,)).fill(1)
            return 0

        def c20(*args):
            self.fail("unqualified key entered C20")

        reader._core, reader._c20 = core, c20
        with self.assertRaisesRegex(ValueError, "before C20"):
            reader.encode(np.zeros(2, dtype="V28"))
        self.assertEqual(calls, ["core"])

    def test_same_owned_key_bytes_cross_both_encoder_calls(self):
        reader = StaticInputs.__new__(StaticInputs)
        reader.batch_rows = 4
        calls = []
        original = np.array([bytes(range(28)), bytes(range(28, 56))], dtype="V28")

        def encode(channels):
            def invoke(keys, rows, output, status):
                address = ctypes.cast(keys, ctypes.c_void_p).value
                raw = np.ctypeslib.as_array(keys, shape=(rows * 28,)).copy()
                calls.append((address, raw.tobytes()))
                np.ctypeslib.as_array(status, shape=(rows,)).fill(0)
                np.ctypeslib.as_array(output, shape=(rows * channels * 81,)).fill(channels)
                return 0

            return invoke

        reader._core, reader._c20 = encode(8), encode(20)
        sigma, c20 = reader.encode(original)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(calls[0][1], original.tobytes())
        self.assertEqual(sigma.shape, (2, 8, 9, 9))
        self.assertEqual(c20.shape, (2, 20, 9, 9))

    def test_head_budget_refuses_before_backend_and_failure_is_charged(self):
        head = StaticHead.__new__(StaticHead)
        head.kind, head.device = "sigma", "cpu"
        head.batch_rows, head.row_limit = 4, 2
        head.attempted = head.returned = head.failed_attempted_rows = head.calls = 0
        head.seconds = 0.0
        head.runtime = {}

        def must_not_infer():
            raise RuntimeError("new actual failed-entry fixture")

        dummy = types.SimpleNamespace(inference_mode=must_not_infer)
        inputs = np.zeros((2, 8, 9, 9), dtype=np.float32)
        with patch.dict("sys.modules", {"torch": dummy}):
            with self.assertRaisesRegex(RuntimeError, "failed-entry"):
                head(inputs)
            self.assertEqual(head.attempted, 2)
            self.assertEqual(head.failed_attempted_rows, 2)
            self.assertEqual(head.returned, 0)
            with self.assertRaisesRegex(ValueError, "budget"):
                head(inputs)
        self.assertEqual(head.calls, 1)
        self.assertEqual(
            head.facts()["failed_kernel_execution_rows"],
            "UNKNOWN without actual profiling",
        )


if __name__ == "__main__":
    unittest.main()
