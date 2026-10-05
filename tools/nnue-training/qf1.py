"""Pure QF1 input contract; independent of experiments, partitions and Torch.

The sparse views remain absolute-player ordered in stored rows. Model inputs
are ordered side-to-move/opponent, while distance is already in STM order and
must not be exchanged again. Canonical identity uses float32 distance bits.
"""

import hashlib
import json
import math
import struct


FEATURE_COUNT = 312
INPUT_VERSION = "QF1-f32-STM-v1"


def validate_input(row):
    """Validate the accepted training-row schema without changing its values."""
    if (
        type(row.get("side")) is not int
        or row["side"] not in (1, 2)
        or len(row.get("ids", [])) != 2
        or len(row.get("distance", [])) != 2
    ):
        raise ValueError("invalid QF1 input")
    for view in row["ids"]:
        if (
            not isinstance(view, list)
            or len(view) != len(set(view))
            or not 4 <= len(view) <= 24
            or any(type(i) is not int or not 0 <= i < FEATURE_COUNT for i in view)
        ):
            raise ValueError("invalid sparse QF1 indices")
    if any(
        type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1
        for v in row["distance"]
    ):
        raise ValueError("invalid normalized distance")


def canonical_model_input(row):
    """Preserve the established STM identity and exact float32 distance bits.

    Training-row validation is a separate boundary. Frozen metadata callers
    historically also use this conversion on small sparse synthetic views;
    converting them must not silently introduce training-schema rejection.
    """
    player = row["side"] - 1
    if player not in (0, 1) or len(row["distance"]) != 2:
        raise ValueError("invalid canonical model input")
    bits = [struct.unpack("<I", struct.pack("<f", v))[0] for v in row["distance"]]
    return [
        INPUT_VERSION,
        sorted(row["ids"][player]),
        sorted(row["ids"][1 - player]),
        bits,
    ]


def feature_signature(row):
    encoded = json.dumps(
        canonical_model_input(row), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def model_features(row):
    """Return STM sparse views and rounded distances before tensor construction."""
    canonical = canonical_model_input(row)
    distance = [struct.unpack("<f", struct.pack("<I", bits))[0] for bits in canonical[3]]
    return canonical[1:3], distance
