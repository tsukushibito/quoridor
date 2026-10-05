"""Optional native bulk feature binding; no Python board/feature code."""

import ctypes
import numpy as np


def features(library, prefixes):
    if any(
        any(
            not isinstance(action, (int, np.integer)) or not 0 <= int(action) <= 208
            for action in prefix
        )
        for prefix in prefixes
    ):
        raise ValueError("invalid action integer/range")
    arrays = [np.asarray(prefix, dtype=np.uint16) for prefix in prefixes]
    if not arrays:
        raise ValueError("empty feature batch")
    if any(len(prefix) > 200 for prefix in arrays):
        raise ValueError("prefix length")
    flat = np.concatenate(arrays)
    offsets = np.concatenate([[0], np.cumsum([len(prefix) for prefix in arrays])]).astype(np.uintp)
    x = np.empty((len(arrays), 2, 312), dtype=np.float32)
    d = np.empty((len(arrays), 2), dtype=np.float32)
    side = np.empty(len(arrays), dtype=np.uint8)
    lib = ctypes.CDLL(str(library))
    fn = lib.quoridor_qf1_bulk
    fn.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    fn.restype = ctypes.c_int
    code = fn(
        flat.ctypes.data,
        len(flat),
        offsets.ctypes.data,
        len(arrays),
        x.ctypes.data,
        d.ctypes.data,
        side.ctypes.data,
    )
    if code:
        raise ValueError("native QF1 bulk rejected input: " + str(code))
    return x, d, side
