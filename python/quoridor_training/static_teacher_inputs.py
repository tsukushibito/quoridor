"""Bounded canonical Sigma8/C20 batch inputs for board-only static teachers.

This host adds no encoder mathematics. Core validates every exact key/distance
before its same immutable bytes can enter the pinned C20 encoder closure.
"""

import ctypes

import numpy as np


class StaticInputs:
    def __init__(self, core_library, c20_library, *, batch_rows):
        if type(batch_rows) is not int or not 0 < batch_rows <= 8192:
            raise ValueError("bounded explicit native encoder batch size")
        self.batch_rows = batch_rows
        self.core = ctypes.CDLL(str(core_library))
        self.c20 = ctypes.CDLL(str(c20_library))
        self._core = self.core.quoridor_public_sigma_inputs
        self._c20 = self.c20.quoridor_public_c20_inputs
        for function in (self._core, self._c20):
            function.argtypes = [
                ctypes.POINTER(ctypes.c_uint8),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_uint8),
            ]
            function.restype = ctypes.c_int

    def encode(self, keys):
        keys = np.asarray(keys)
        if keys.ndim != 1 or keys.dtype != np.dtype("V28") or not 0 < len(keys) <= self.batch_rows:
            raise ValueError("bounded exact native input keys")
        packed = np.ascontiguousarray(keys)
        sigma = np.empty((len(keys), 8, 9, 9), dtype=np.float32)
        status = np.full(len(keys), 255, dtype="u1")
        pointer = packed.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
        code = self._core(
            pointer,
            len(keys),
            sigma.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            status.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        )
        if code != 0 or np.any(status != 0) or not np.isfinite(sigma).all():
            raise ValueError("core board/distance input qualification failed before C20")
        c20 = np.empty((len(keys), 20, 9, 9), dtype=np.float32)
        status.fill(255)
        # pointer still names the SAME owned contiguous key bytes; no alternate
        # board, label, inferred history or orientation is supplied here.
        code = self._c20(
            pointer,
            len(keys),
            c20.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
            status.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        )
        if code != 0 or np.any(status != 0) or not np.isfinite(c20).all():
            raise ValueError("pinned canonical C20 input encoding failed")
        return sigma, c20
