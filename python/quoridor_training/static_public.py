"""Board-only public input classes, preserving original observation multiplicity.

The owning stream qualifies geometry and protects sealed/LR groups before this
reader. Class rows are exact native inputs, not games or full-history states.
No inference, model loading, new feature formula or outcome teacher lives here.
"""

import numpy as np

from .public_features import features, input_records, reflected_keys

CLASS = np.dtype([("key", "V28"), ("observations", "<u4"), ("split", "u1")])


def exact_lookup(sorted_keys, requested):
    """Reject absent classes, including a missing independently labeled LR view."""
    requested = np.asarray(requested)
    if requested.ndim != 1 or requested.dtype != np.dtype("V28"):
        raise ValueError("exact native input keys required")
    offsets = np.searchsorted(sorted_keys, requested)
    if np.any(offsets >= len(sorted_keys)):
        raise ValueError("input outside bound class table")
    if not np.array_equal(sorted_keys[offsets], requested):
        raise ValueError("input outside bound class table")
    return offsets


class ClassObservations:
    """Virtual observations with the same multiplicity as the original corpus.

    A class with n original observations occupies n ordinals. Sampling those
    ordinals uniformly is therefore exactly observation-weighted sampling; it
    does not train uniformly over unique inputs. Zero-count reflected T entries
    provide actual orientation targets, never extra observations.
    """

    def __init__(self, classes, *, chunk_rows=65536):
        if (
            classes.dtype != CLASS
            or classes.ndim != 1
            or not len(classes)
            or type(chunk_rows) is not int
            or not 0 < chunk_rows <= 65536
        ):
            raise ValueError("nonempty bounded exact input class table required")
        self.classes = classes
        self.keys = classes["key"]
        previous = None
        for start in range(0, len(classes), chunk_rows):
            rows = classes[start : start + chunk_rows]
            keys = rows["key"]
            ordered = np.sort(keys)
            if (
                not np.array_equal(ordered, keys)
                or np.any(keys[1:] == keys[:-1])
                or (previous is not None and bytes(keys[0]) <= previous)
                or np.any(rows["split"] > 1)
            ):
                raise ValueError("unique sorted unsealed T/V input classes required")
            input_records(keys)
            previous = bytes(keys[-1])
        # Closure is checked in bounded chunks. V need not have an unused LR
        # label, but every present mate shares its split and every T mate exists.
        for start in range(0, len(classes), chunk_rows):
            rows = classes[start : start + chunk_rows]
            mate = reflected_keys(rows["key"])
            offset = np.searchsorted(self.keys, mate)
            present = offset < len(classes)
            safe = np.minimum(offset, len(classes) - 1)
            present &= self.keys[safe] == mate
            if np.any((rows["split"] == 0) & ~present) or np.any(
                self.classes["split"][safe[present]] != rows["split"][present]
            ):
                raise ValueError("true LR T label closure and shared T/V split required")
            if np.any((rows["observations"] == 0) & (rows["split"] != 0)):
                raise ValueError("zero-count views are T augmentation only")
        self.cumulative = {}
        self.counts = {}
        for split, code in (("train", 0), ("validation", 1)):
            weights = np.where(classes["split"] == code, classes["observations"], 0)
            cumulative = np.cumsum(weights, dtype=np.uint64)
            count = int(cumulative[-1])
            if not count:
                raise ValueError("nonempty original observation T/V required")
            # uint32 counts and an addressable table bound the sum below u64.
            if np.any(cumulative[1:] < cumulative[:-1]):
                raise ValueError("observation multiplicity overflow")
            self.cumulative[split] = cumulative
            self.counts[split] = count

    def offsets(self, split, ordinals, reflection_mask=None, *, training=False):
        if split not in self.cumulative or (training and split != "train"):
            raise ValueError("training uses T; only opened T/V can be indexed")
        index = np.asarray(ordinals)
        if (
            index.ndim != 1
            or index.dtype.kind not in "iu"
            or np.any(index < 0)
            or np.any(index >= self.counts[split])
        ):
            raise ValueError("original observation ordinals outside partition")
        offsets = np.searchsorted(self.cumulative[split], index, side="right")
        if reflection_mask is not None:
            mask = np.asarray(reflection_mask)
            if not training or mask.dtype != np.dtype(bool) or mask.shape != index.shape:
                raise ValueError("actual T-only source reflection mask required")
            offsets[mask] = exact_lookup(self.keys, reflected_keys(self.keys[offsets[mask]]))
        if np.any(self.classes["split"][offsets] != (0 if split == "train" else 1)):
            raise ValueError("lookup crossed bound split")
        return offsets

    def records(self, split, ordinals, reflection_mask=None, *, training=False):
        offsets = self.offsets(split, ordinals, reflection_mask, training=training)
        return input_records(self.keys[offsets])

    def batch(self, split, ordinals, values, reflection_mask=None, *, training=False):
        """Use the SAME LR mask for both native QF1 geometry and scalar target."""
        if values.dtype != np.dtype("<f4") or values.ndim != 1 or len(values) != len(self.classes):
            raise ValueError("one bound FP32 scalar per exact input orientation")
        offsets = self.offsets(split, ordinals, reflection_mask, training=training)
        rows = input_records(self.keys[offsets])
        target = np.asarray(values[offsets])
        if not np.isfinite(target).all() or np.any(np.abs(target) > 1):
            raise ValueError("finite local STM post-tanh scalar required")
        return features(rows["geometry"]), rows["distance"].copy(), target


def accumulate_inputs(connection, keys, protection):
    """One bounded native-qualified batch, including opaque protected inputs.

    protection bits: 1 existing sealed row, 2 documented opened-evaluation row.
    Neither old z nor teacher values are an argument to class membership.
    Both orientations inherit protection before any labels can be requested.
    """
    from .public_features import lr_group_keys

    keys = np.asarray(keys)
    protection = np.asarray(protection)
    if (
        keys.ndim != 1
        or keys.dtype != np.dtype("V28")
        or not 0 < len(keys) <= 8192
        or protection.dtype != np.dtype("u1")
        or protection.shape != keys.shape
        or np.any(protection > 3)
    ):
        raise ValueError("bounded qualified input batch and explicit protection bits")
    # Decode through the same owner used by the reader, not another board codec.
    input_records(keys)
    mates = reflected_keys(keys)
    groups = lr_group_keys(keys)
    sql = (
        "INSERT INTO inputs VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET "
        "observations=observations+excluded.observations,"
        "protection=protection|excluded.protection"
    )
    connection.executemany(sql, ((bytes(k), 1, int(p)) for k, p in zip(keys, protection)))
    connection.executemany(sql, ((bytes(k), 0, int(p)) for k, p in zip(mates, protection)))
    # This streaming digest binds each original qualified observation's actual
    # orientation and LR group in caller source-row order; it is not a set hash.
    mapping = np.empty(len(keys), dtype=[("key", "V28"), ("lr_group", "V28")])
    mapping["key"], mapping["lr_group"] = keys, groups
    return mapping.tobytes()


def write_class_table(connection, stream, *, split_seed, validation_parts, split_parts):
    """Finish one full-source accumulation; split only unprotected LR groups.

    The finite recipe owns seed/fraction. SQL iteration is sorted and bounded;
    this never constructs a corpus-size Python input/row/history list.
    The caller publishes only after its complete source census and output sync.
    """
    import hashlib

    if (
        type(split_seed) is not int
        or not 0 <= split_seed < 2**64
        or type(validation_parts) is not int
        or type(split_parts) is not int
        or not 0 < validation_parts < split_parts <= 2**32
    ):
        raise ValueError("explicit finite result-blind class split recipe required")
    from .public_features import lr_group_keys

    counts = {
        "qualified_original_observations": 0,
        "protected_original_observations": 0,
        "protected_by_bits": {"1": 0, "2": 0, "3": 0},
        "train": 0,
        "validation": 0,
        "class_rows": 0,
    }
    seed = split_seed.to_bytes(8, "little")
    cursor = connection.execute("SELECT key,observations,protection FROM inputs ORDER BY key")
    try:
        while batch := cursor.fetchmany(8192):
            # Python objects exist for at most one bounded batch.
            keys = np.asarray([row[0] for row in batch], dtype="V28")
            groups = lr_group_keys(keys)
            rows = np.zeros(len(batch), dtype=CLASS)
            keep = np.ones(len(batch), dtype=bool)
            for index, ((key, observations, protected), group) in enumerate(zip(batch, groups)):
                if not 0 <= observations <= np.iinfo(np.uint32).max or not 0 <= protected <= 3:
                    raise ValueError("class count/protection overflow or corrupt accumulator")
                counts["qualified_original_observations"] += observations
                if protected:
                    counts["protected_original_observations"] += observations
                    counts["protected_by_bits"][str(protected)] += observations
                    keep[index] = False
                    continue
                digest = hashlib.sha256(seed + bytes(group)).digest()
                # Integer threshold avoids floating partition drift. Finite
                # modulo mapping is deterministic, not an IID/game claim.
                split = int(int.from_bytes(digest[:8], "little") % split_parts < validation_parts)
                if observations == 0 and split == 1:
                    keep[index] = False
                    continue
                rows[index] = key, observations, split
                counts["validation" if split else "train"] += observations
            rows = rows[keep]
            stream.write(rows.tobytes())
            counts["class_rows"] += len(rows)
    finally:
        cursor.close()
    if (
        counts["qualified_original_observations"]
        != counts["protected_original_observations"] + counts["train"] + counts["validation"]
    ):
        raise ValueError("complete original multiplicity/protection census")
    return counts


def create_class_accumulator(path):
    """Use the existing bounded SQLite indexing approach; caller owns its TMP."""
    import sqlite3
    from pathlib import Path

    path = Path(path)
    # SQLite's normal connect would silently reopen a previous partial index.
    # Atomic fresh creation preserves failed prefixes rather than retrying them.
    with path.open("xb"):
        pass
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA cache_size=-2048")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute(
            "CREATE TABLE inputs (key BLOB PRIMARY KEY, observations INTEGER NOT NULL,"
            "protection INTEGER NOT NULL) WITHOUT ROWID"
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
