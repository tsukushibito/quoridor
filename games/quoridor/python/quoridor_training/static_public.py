"""Board-only public input classes with original observation multiplicity.

Each stored row is one exact native input/true-LR pair. The two counts retain
original orientations; independently evaluated orientation scalars are separate.
The owning stream protects old sealed/opened groups before any teacher call.
"""

import hashlib
from pathlib import Path
import sqlite3

import numpy as np

from .public_features import (
    features,
    input_records,
    lr_group_keys,
    reflected_keys,
    reflect,
)

PAIR = np.dtype([("key", "V28"), ("observations", "<u4", (2,)), ("split", "u1")])


class ClassObservations:
    """Virtual observation ordinals, weighted by the exact original counts.

    Within each sorted pair, canonical observations precede reflected ones.
    Uniform ordinal sampling and complete epochs preserve original multiplicity,
    rather than sampling unique inputs uniformly. No game/history is invented.
    """

    def __init__(self, pairs, *, chunk_rows=65536):
        if (
            pairs.dtype != PAIR
            or pairs.ndim != 1
            or not len(pairs)
            or type(chunk_rows) is not int
            or not 0 < chunk_rows <= 65536
        ):
            raise ValueError("nonempty bounded native LR-pair table required")
        self.pairs, self.keys = pairs, pairs["key"]
        previous = None
        for first in range(0, len(pairs), chunk_rows):
            batch = pairs[first : first + chunk_rows]
            keys = batch["key"]
            if (
                not np.array_equal(np.sort(keys), keys)
                or np.any(keys[1:] == keys[:-1])
                or (previous is not None and bytes(keys[0]) <= previous)
                or not np.array_equal(lr_group_keys(keys), keys)
                or np.any(batch["split"] > 1)
                or np.any(batch["observations"].sum(axis=1, dtype=np.uint64) == 0)
            ):
                raise ValueError("unique canonical sorted unsealed T/V LR pairs required")
            # A self-reflected exact input has one original orientation.
            symmetric = reflected_keys(keys) == keys
            if np.any(batch["observations"][symmetric, 1] != 0):
                raise ValueError(
                    "symmetric exact inputs cannot invent a second original orientation"
                )
            previous = bytes(keys[-1])
        self.cumulative, self.counts = {}, {}
        totals = pairs["observations"].sum(axis=1, dtype=np.uint64)
        for split, code in (("train", 0), ("validation", 1)):
            cumulative = np.cumsum(np.where(pairs["split"] == code, totals, 0), dtype=np.uint64)
            if np.any(cumulative[1:] < cumulative[:-1]) or not int(cumulative[-1]):
                raise ValueError("nonempty observation partition without count overflow required")
            self.cumulative[split] = cumulative
            self.counts[split] = int(cumulative[-1])

    def offsets(self, split, ordinals, reflection_mask=None, *, training=False):
        if split not in self.cumulative or (training and split != "train"):
            raise ValueError("training uses T; only unsealed T/V can be indexed")
        index = np.asarray(ordinals)
        if (
            index.ndim != 1
            or index.dtype.kind not in "iu"
            or np.any(index < 0)
            or np.any(index >= self.counts[split])
        ):
            raise ValueError("original observation ordinal outside partition")
        cumulative = self.cumulative[split]
        pairs = np.searchsorted(cumulative, index, side="right")
        before = np.zeros(len(index), dtype=np.uint64)
        nonfirst = pairs != 0
        before[nonfirst] = cumulative[pairs[nonfirst] - 1]
        orientation = index - before >= self.pairs["observations"][pairs, 0]
        if reflection_mask is not None:
            mask = np.asarray(reflection_mask)
            if not training or mask.dtype != np.dtype(bool) or mask.shape != index.shape:
                raise ValueError("actual T-only source reflection mask required")
            orientation ^= mask
        if np.any(self.pairs["split"][pairs] != (0 if split == "train" else 1)):
            raise ValueError("lookup crossed bound split")
        return pairs, orientation.astype(np.uint8)

    def records(self, split, ordinals, reflection_mask=None, *, training=False):
        pairs, orientation = self.offsets(split, ordinals, reflection_mask, training=training)
        rows = input_records(self.keys[pairs]).copy()
        selected = orientation.astype(bool)
        rows["geometry"][selected] = reflect(rows["geometry"][selected])
        return rows

    def validate_values(self, values, *, chunk_rows=65536):
        if values.dtype != np.dtype("<f4") or values.shape != (len(self.pairs), 2):
            raise ValueError("one bound FP32 scalar per exact pair orientation")
        for first in range(0, len(self.pairs), chunk_rows):
            batch = self.pairs[first : first + chunk_rows]
            required = np.ones((len(batch), 2), dtype=bool)
            target = values[first : first + len(batch)][required]
            if not np.isfinite(target).all() or np.any(np.abs(target) > 1):
                raise ValueError("finite actual canonical/reflected teacher values required")

    def batch(self, split, ordinals, values, reflection_mask=None, *, training=False):
        if values.dtype != np.dtype("<f4") or values.shape != (len(self.pairs), 2):
            raise ValueError("one bound FP32 scalar per exact pair orientation")
        pairs, orientation = self.offsets(split, ordinals, reflection_mask, training=training)
        rows = input_records(self.keys[pairs])
        target = values[pairs, orientation]
        if not np.isfinite(target).all() or np.any(np.abs(target) > 1):
            raise ValueError("finite actual orientation scalar required")
        return (
            features(rows["geometry"], orientation.astype(bool)),
            rows["distance"].copy(),
            target,
        )


def accumulate_inputs(connection, keys, protection):
    """One bounded qualified batch; z/termination/teacher values are not inputs.

    Protection bits1=old sealed and2=known opened are ORed per exact trueLR pair.
    Late protected aliases therefore remove earlier apparent training inputs.
    """
    keys, protection = np.asarray(keys), np.asarray(protection)
    if (
        keys.ndim != 1
        or keys.dtype != np.dtype("V28")
        or not 0 < len(keys) <= 8192
        or protection.dtype != np.dtype("u1")
        or protection.shape != keys.shape
        or np.any(protection > 3)
    ):
        raise ValueError("bounded qualified native keys and explicit protection bits")
    groups = lr_group_keys(keys)  # also validates native input-key shape/range
    orientation = keys != groups
    connection.executemany(
        "INSERT INTO inputs VALUES (?,?,?,?) ON CONFLICT(key) DO UPDATE SET "
        "canonical_n=canonical_n+excluded.canonical_n,"
        "reflected_n=reflected_n+excluded.reflected_n,"
        "protection=protection|excluded.protection",
        (
            (bytes(key), int(not side), int(side), int(protected))
            for key, side, protected in zip(groups, orientation, protection)
        ),
    )
    mapping = np.empty(len(keys), dtype=[("key", "V28"), ("lr_group", "V28")])
    mapping["key"], mapping["lr_group"] = keys, groups
    return mapping.tobytes()


def class_split(key, split_seed):
    """Frozen shared90/10 SHA rule; no numerical labels enter the split."""
    if type(split_seed) is not int or not 0 <= split_seed < 2**64 or len(key) != 28:
        raise ValueError("unsigned64 seed and owning exact native key28 required")
    digest = hashlib.sha256(
        b"full-public-teachers-v1|split|" + split_seed.to_bytes(8, "little") + key
    ).digest()
    return int(10 * int.from_bytes(digest[:8], "big") >= 9 * 2**64)


def write_class_table(connection, stream, *, split_seed=None, split_assignments=None):
    """Publish sorted complete-source LR pairs using the frozen shared hash."""
    # Hash splitting remains the full-public default. Explicit fixture splits
    # must cover exactly the same complete unprotected class set, never alias it.
    if split_assignments is None:
        class_split(bytes(28), split_seed)
    else:
        if (
            split_seed is not None
            or not isinstance(split_assignments, dict)
            or not split_assignments
            or any(
                type(key) is not bytes
                or len(key) != 28
                or type(code) is not int
                or code not in (0, 1)
                for key, code in split_assignments.items()
            )
        ):
            raise ValueError("exclusive complete explicit class partition required")
        actual = {row[0] for row in connection.execute("SELECT key FROM inputs")}
        if actual != set(split_assignments):
            raise ValueError("explicit partition differs from complete accumulated classes")
    counts = {
        "qualified_original_observations": 0,
        "protected_original_observations": 0,
        "protected_by_bits": {"1": 0, "2": 0, "3": 0},
        "train": 0,
        "validation": 0,
        "pair_rows": 0,
    }
    cursor = connection.execute(
        "SELECT key,canonical_n,reflected_n,protection FROM inputs ORDER BY key"
    )
    try:
        while batch := cursor.fetchmany(8192):
            rows = np.zeros(len(batch), dtype=PAIR)
            keep = np.ones(len(batch), dtype=bool)
            for i, (key, canonical, reflected, protected) in enumerate(batch):
                if (
                    not 0 <= canonical <= np.iinfo(np.uint32).max
                    or not 0 <= reflected <= np.iinfo(np.uint32).max
                    or canonical + reflected == 0
                    or not 0 <= protected <= 3
                ):
                    raise ValueError("class multiplicity overflow or corrupt accumulator")
                n = canonical + reflected
                counts["qualified_original_observations"] += n
                if protected:
                    if split_assignments is not None:
                        raise ValueError("explicit fixture cannot assign a protected class")
                    counts["protected_original_observations"] += n
                    counts["protected_by_bits"][str(protected)] += n
                    keep[i] = False
                    continue
                split = (
                    class_split(key, split_seed)
                    if split_assignments is None
                    else split_assignments[key]
                )
                rows[i] = key, (canonical, reflected), split
                counts["validation" if split else "train"] += n
            rows = rows[keep]
            stream.write(rows.tobytes())
            counts["pair_rows"] += len(rows)
    finally:
        cursor.close()
    if (
        counts["qualified_original_observations"]
        != counts["protected_original_observations"] + counts["train"] + counts["validation"]
    ):
        raise ValueError("complete original multiplicity/protection census")
    return counts


def create_class_accumulator(path, *, max_bytes):
    """The existing bounded SQLite approach, one key per trueLR pair, no row list."""
    if type(max_bytes) is not int or max_bytes < 16384 or max_bytes % 4096:
        raise ValueError("concrete whole-admitted SQLite page holding bound required")
    path = Path(path)
    with path.open("xb"):
        pass  # refuse reopening any prior failed/partial index
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA page_size=4096")
        connection.execute(f"PRAGMA max_page_count={max_bytes // 4096}")
        connection.execute("PRAGMA cache_size=-2048")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute(
            "CREATE TABLE inputs (key BLOB PRIMARY KEY, canonical_n INTEGER NOT NULL,"
            "reflected_n INTEGER NOT NULL,protection INTEGER NOT NULL) WITHOUT ROWID"
        )
    except BaseException:
        connection.close()
        raise
    return connection


def accumulate_original_shard(connection, path, item, native, opened):
    """Board-only native ingress; old labels never enter eligibility or teacher work.

    Protected native inputs are used solely as opaque exclusion membership. They
    never reach a teacher or a training view, including aliases found earlier.
    Original blob custody/download verification remains with the current caller.
    """
    import hashlib

    from .public_features import MODEL_INPUT, geometry_from_native, model_keys
    from .public_sigma import original_plane_chunks, selection

    count = item["rows"] // 2
    opened = np.asarray(opened)
    if (
        opened.ndim != 1
        or opened.dtype.kind not in "iu"
        or np.any(opened < 0)
        or np.any(opened >= count)
        or len(np.unique(opened)) != len(opened)
    ):
        raise ValueError("bound exact original opened observation IDs")
    _, old_splits, _ = selection(item["sha"], count)
    reasons = np.zeros(7, dtype=np.int64)
    mapping = hashlib.sha256()
    planes_digest = hashlib.sha256()
    decoded = 0
    for indices, planes, old_values in original_plane_chunks(path, item, with_values=False):
        if old_values is not None:
            raise ValueError("board-only source must not expose old labels")
        planes_digest.update(planes.tobytes())
        bits, distances, codes = native.convert(planes)
        if (
            codes.dtype != np.dtype("u1")
            or codes.shape != indices.shape
            or np.any(codes > 6)
            or distances.shape != (len(indices), 2)
            or distances.dtype != np.dtype("<f4")
        ):
            raise ValueError("native qualification status/distance ABI")
        reasons += np.bincount(codes, minlength=7)
        valid = codes == 0
        mapping.update(np.asarray([len(indices)], dtype="<u4").tobytes())
        mapping.update(indices.tobytes())
        mapping.update(codes.tobytes())
        if valid.any():
            rows = np.zeros(np.count_nonzero(valid), dtype=MODEL_INPUT)
            rows["geometry"] = geometry_from_native(bits[valid])
            rows["distance"] = distances[valid]
            protection = (old_splits[indices[valid]] == 2).astype("u1")
            protection[np.isin(indices[valid], opened)] |= 2
            key_mapping = accumulate_inputs(connection, model_keys(rows), protection)
            mapping.update(protection.tobytes())
            mapping.update(key_mapping)
        decoded += len(indices)
    if decoded != count or int(reasons.sum()) != count:
        raise ValueError("entire original half was not qualified exactly once")
    return {
        "stored_rows": item["rows"],
        "original_observations": count,
        "decoded_original_rows": decoded,
        "native_codes": reasons.tolist(),
        "old_label_payload_read": False,
        "old_label_or_termination_eligibility_filter": False,
        "naive_lr_half_used": False,
        "original_planes_sha256": planes_digest.hexdigest(),
        "observation_mapping_sha256": mapping.hexdigest(),
        "mapping_encoding": "per chunk: LE-u32 n, LE-u32 original IDs, u8 native status; valid subsequence u8 protection, packed V28 exact key+V28 trueLR group",
        "threefold_or_fullhistory_qualification": "UNAVAILABLE board-only",
    }
