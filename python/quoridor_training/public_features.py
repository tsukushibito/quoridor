"""Lossless QF1 input geometry and native-defined left/right augmentation.

The canonical Sigma adapter fixes STM to player zero. Geometry stores that
checked position, not a new feature layout; decoding returns the maintained
two QF1 views. Reflection preserves goal rows, STM, stocks, distance and z.
"""

import numpy as np

GEOMETRY = np.dtype(
    [
        ("pawns", "u1", (2,)),
        ("stocks", "u1", (2,)),
        ("horizontal", "<u8"),
        ("vertical", "<u8"),
    ]
)
RECORD = np.dtype(
    [
        ("geometry", GEOMETRY),
        ("distance", "<f4", (2,)),
        ("z", "i1"),
        ("shard", "u1"),
        ("row", "<u4"),
        ("input_sha", "u1", (32,)),
    ]
)
SCHEMA = "quoridor-public-geometry-v1"
REVISION_NAME = "original-full-v1"


def wall_bits(values):
    raw = np.ascontiguousarray(values, dtype="<u8").view("u1").reshape(-1, 8)
    return np.unpackbits(raw, axis=1, bitorder="little")


def wall_integers(bits):
    raw = np.packbits(bits, axis=1, bitorder="little")
    return np.ascontiguousarray(raw).view("<u8").reshape(-1)


def validate_geometry(geometry):
    if geometry.dtype != GEOMETRY or geometry.ndim != 1:
        raise ValueError("canonical geometry dtype/shape")
    if np.any(geometry["pawns"] >= 81) or np.any(geometry["stocks"] > 10):
        raise ValueError("canonical geometry pawn/stock bounds")
    if np.any(geometry["pawns"][:, 0] == geometry["pawns"][:, 1]):
        raise ValueError("canonical geometry coincident pawns")


class FeatureWorkspace:
    """Batch-local reusable indices; never shared by simultaneously filling workers."""

    def __init__(self, capacity):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("positive feature workspace capacity")
        self.index = np.arange(capacity, dtype=np.int64)
        self.pawns = np.empty((capacity, 2), dtype=np.int64)


def features(geometry, reflection_mask=None, *, out=None, workspace=None):
    """QF1 in final contiguous storage, decoding each wall once for both views."""
    validate_geometry(geometry)
    n = len(geometry)
    if reflection_mask is not None:
        reflection_mask = np.asarray(reflection_mask)
        if reflection_mask.dtype != np.dtype(bool) or reflection_mask.shape != (n,):
            raise ValueError("reflection mask dtype/shape")
    if out is None:
        out = np.empty((n, 2, 312), dtype=np.float32)
    if out.dtype != np.float32 or out.shape != (n, 2, 312) or not out.flags.c_contiguous:
        raise ValueError("feature output dtype/shape/contiguity")
    if not out.flags.writeable or np.shares_memory(out, geometry):
        raise ValueError("feature output writable and nonaliasing")
    workspace = workspace or FeatureWorkspace(max(1, n))
    if len(workspace.index) < n:
        raise ValueError("feature workspace capacity")
    index, pawns = workspace.index[:n], workspace.pawns[:n]
    pawns[:] = geometry["pawns"]
    if reflection_mask is not None:
        selected = pawns[reflection_mask]
        pawns[reflection_mask] = selected // 9 * 9 + 8 - selected % 9
    out.fill(0)
    for view in range(2):
        own, other = pawns[:, view], pawns[:, view ^ 1]
        if view == 1:
            own, other = 80 - own, 80 - other
        out[index, view, own] = 1
        out[index, view, 81 + other] = 1
        out[index, view, 290 + geometry["stocks"][:, view].astype(np.int64)] = 1
        out[index, view, 301 + geometry["stocks"][:, view ^ 1].astype(np.int64)] = 1
    for name, first in (("horizontal", 162), ("vertical", 226)):
        bits = wall_bits(geometry[name])
        if reflection_mask is not None:
            selected = bits[reflection_mask].reshape(-1, 8, 8)
            bits[reflection_mask] = selected[:, :, ::-1].reshape(-1, 64)
        out[:, 0, first : first + 64] = bits
        out[:, 1, first : first + 64] = bits[:, ::-1]
    return out


def geometry_from_native(bits):
    """Accept only exact two-view QF1 bytes supplied by native qualification."""
    bits = np.asarray(bits)
    if bits.dtype != np.dtype("u1") or bits.ndim != 2 or bits.shape[1] != 78:
        raise ValueError("native bitset shape/dtype")
    x = np.unpackbits(bits, axis=1, bitorder="little").reshape(-1, 2, 312)
    view = x[:, 0]
    out = np.zeros(len(bits), dtype=GEOMETRY)
    for target, parts in (
        ("pawns", ((0, 81), (81, 162))),
        ("stocks", ((290, 301), (301, 312))),
    ):
        for player, (first, end) in enumerate(parts):
            values = view[:, first:end]
            if not np.all(values.sum(axis=1) == 1):
                raise ValueError("native QF1 one-hot qualification")
            out[target][:, player] = values.argmax(axis=1)
    out["horizontal"] = wall_integers(view[:, 162:226])
    out["vertical"] = wall_integers(view[:, 226:290])
    if not np.array_equal(features(out), x):
        raise ValueError("geometry does not reproduce both native QF1 views")
    return out


def reflect(geometry):
    """Native coordinates: pawn x ->8-x; each 8x8 wall anchor x ->7-x."""
    validate_geometry(geometry)
    out = geometry.copy()
    pawns = geometry["pawns"]
    out["pawns"] = pawns // 9 * 9 + (8 - pawns % 9)
    for name in ("horizontal", "vertical"):
        bits = wall_bits(geometry[name]).reshape(-1, 8, 8)
        out[name] = wall_integers(bits[:, :, ::-1].reshape(-1, 64))
    return out


def model_keys(records):
    """Injective geometry+f32 distance identity, equivalent to exact QF1 equality.

    No Python row dictionaries or full dense feature tensor are materialized.
    Original input SHA is separate because qualified float planes need not have
    identical original bytes for an identical native model input.
    """
    raw = records.view("u1").reshape(-1, RECORD.itemsize)
    return np.ascontiguousarray(raw[:, :28]).view("V28").reshape(-1)


def phase_proxy(geometry):
    total = geometry["stocks"].sum(axis=1, dtype=np.uint16)
    return np.where(total >= 16, 0, np.where(total >= 6, 1, 2)).astype(np.uint8)
