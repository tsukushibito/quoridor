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

    def encode(self, keys, *, include_c20=True):
        if type(include_c20) is not bool:
            raise ValueError("explicit C20 encoder selection")
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
        if not include_c20:
            return sigma, None
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

    def policy_mask(self, keys):
        """Canonical public keys have native STM=0; C20 policy209 is core order.

        Same canonical C20 closure and core rules own orientation and legality.
        No Python geometry/range-distance classifier or history is reconstructed.
        """
        keys = np.asarray(keys)
        if keys.ndim != 1 or keys.dtype != np.dtype("V28") or not 0 < len(keys) <= self.batch_rows:
            raise ValueError("bounded exact policy input keys")
        packed = np.ascontiguousarray(keys)
        mask = np.zeros((len(keys), 209), dtype="u1")
        status = np.full(len(keys), 255, dtype="u1")
        function = self.core.quoridor_public_policy_masks
        function.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.POINTER(ctypes.c_uint8),
        ]
        function.restype = ctypes.c_int
        code = function(
            packed.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            len(keys),
            mask.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            status.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
        )
        if code != 0 or np.any(status != 0) or np.any(mask > 1) or not mask.any(axis=1).all():
            raise ValueError("canonical core nonterminal policy mask refused")
        return mask.astype(bool)


class PublicPrefixView(ctypes.Structure):
    """Exact repr(C) view; Root qualifies the new library/ABI before use."""

    _fields_ = [
        ("key", ctypes.c_uint8 * 28),
        ("side", ctypes.c_uint8),
        ("qf1", ctypes.c_uint8 * 624),
        ("distance", ctypes.c_float * 2),
        ("action_to_key", ctypes.c_uint16 * 209),
        ("legal_in_key", ctypes.c_uint8 * 209),
        ("prefix", ctypes.c_uint16 * 200),
        ("prefix_len", ctypes.c_uint16),
    ]


def native_prefix_views(histories, library):
    """Sole native replay/trueLR/actual STM/QF1/action-frame owner, no Python geometry."""
    if (
        not isinstance(histories, list)
        or not 1 <= len(histories) <= 16
        or any(
            not isinstance(history, list)
            or len(history) > 200
            or any(type(a) is not int or not 0 <= a < 209 for a in history)
            for history in histories
        )
    ):
        raise ValueError("bounded genuine diagnostic histories")
    actions = [a for history in histories for a in history]
    offsets = [0]
    for history in histories:
        offsets.append(offsets[-1] + len(history))
    packed = (ctypes.c_uint16 * max(1, len(actions)))(*actions)
    starts = (ctypes.c_size_t * len(offsets))(*offsets)
    output = (PublicPrefixView * (2 * len(histories)))()
    status = (ctypes.c_uint8 * len(histories))()
    native = ctypes.CDLL(str(library))
    function = native.quoridor_public_prefix_views
    function.argtypes = [
        ctypes.POINTER(ctypes.c_uint16),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_size_t,
        ctypes.POINTER(PublicPrefixView),
        ctypes.POINTER(ctypes.c_uint8),
    ]
    function.restype = ctypes.c_int
    code = function(packed, len(actions), starts, len(histories), output, status)
    if code != 0 or any(status):
        raise ValueError("native diagnostic frame refused; no replacement")
    # Return owned records, not pointers into the temporary ctypes allocation.
    return [
        {
            "key": bytes(view.key).hex(),
            "side": int(view.side),
            "qf1": list(view.qf1),
            "distance": list(view.distance),
            "action_to_key": list(view.action_to_key),
            "legal_in_key": list(view.legal_in_key),
            "prefix": list(view.prefix[: view.prefix_len]),
        }
        for view in output
    ]
