"""One new zero-forward host-transfer boundary; fake CUDA ports, not GPU qualification."""

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class NativeParameterHostTransfer(unittest.TestCase):
    def test_readonly_host_transfer_and_exact_drift_refusal(self):
        from quoridor_training.train import verify_native_parameters

        keys = ("ft.weight", "ft.bias", "h.weight", "h.bias", "out.weight", "out.bias")
        calls = []

        class Values(list):
            def reshape(self, *shape):
                self_shape = shape
                assert self_shape == (-1,)
                return self

        class Tensor:
            def __init__(self, value, device="fake-cuda"):
                self.value, self.device = value, device

            def detach(self):
                return self

            def cpu(self):
                calls.append(("cpu", self.value))
                return Tensor(self.value, "cpu")

            def numpy(self):
                if self.device != "cpu":
                    raise TypeError("fake CUDA cannot convert directly to numpy")
                return Values([self.value])

        state = {key: Tensor(float(i)) for i, key in enumerate(keys)}
        fake = SimpleNamespace(
            memmap=lambda path, **kw: Values(range(6)),
            array_equal=lambda a, b: list(a) == list(b),
        )
        with patch.dict(sys.modules, {"numpy": fake}):
            verify_native_parameters("synthetic-not-opened", state)
            self.assertEqual(calls, [("cpu", float(i)) for i in range(6)])
            self.assertTrue(all(t.device == "fake-cuda" for t in state.values()))
            state["h.bias"] = Tensor(99.0)
            with self.assertRaisesRegex(
                ValueError, "frozen checkpoint/native parameters differ"
            ):
                verify_native_parameters("synthetic-not-opened", state)


if __name__ == "__main__":
    unittest.main()
