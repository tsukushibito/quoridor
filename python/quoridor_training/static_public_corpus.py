"""The normal trainer's board-only static-teacher compact corpus.

Original multiplicities are virtual ordinals, not Python row/history objects.
One exact LR pair stores two independently evaluated orientation targets.
The two teachers share the same class manifest, normalizer and split.
"""

import hashlib
import json
import os
from pathlib import Path
import stat

import numpy as np

from .common import bound_file_bytes
from .compact_cache import IndexedPublicCorpus
from .public_features import features, input_records
from .static_public import PAIR, ClassObservations


class _VirtualColumn:
    def __init__(self, corpus, groups=False):
        self.corpus, self.groups = corpus, groups

    def __getitem__(self, item):
        if self.groups:
            return self.corpus.locate(item)[0]
        index, column = item
        if column != 0:
            raise ValueError("static teacher has one scalar, never a z column")
        if isinstance(index, slice):
            index = np.arange(len(self.corpus.rows))[index]
        pair, orientation = self.corpus.locate(index)
        return self.corpus.values[pair, orientation]


class StaticTeacherCorpus:
    compact, static_teacher, terminal = True, True, False

    def __init__(self, path, allow_test=False):
        if allow_test:
            raise ValueError("protected public classes have no test-opening route")
        path = Path(path)
        self.manifest = json.loads((path / "cache.json").read_bytes())
        if self.manifest.get("schema") != "quoridor-public-static-teacher-v1":
            raise ValueError("bound board-only static scalar corpus required")
        self.maps, self.streams, self.identities = {}, {}, {}
        try:
            self.input_ref = self.manifest["input_classes"]
            inputs = json.loads(bound_file_bytes(self.input_ref, 131072))
            bank_ref = self.manifest["teacher_values"]
            bank = json.loads(bound_file_bytes(bank_ref, 131072))
            teacher = self.manifest["teacher"]
            if (
                inputs["schema"] != "quoridor-public-static-input-classes-v1"
                or inputs["status"] != "COMPLETE"
                or bank["status"] != "COMPLETE"
                or bank["schema"] != "quoridor-public-static-teacher-values-v1"
                or bank["input_classes"] != self.input_ref
                or teacher not in ("S", "C")
                or inputs["pair_record_bytes"] != PAIR.itemsize
            ):
                raise ValueError("complete same-input scalarbank binding required")
            if (Path(self.input_ref["path"]).parent / "INCOMPLETE").exists():
                raise ValueError("input publication still incomplete")
            if (Path(bank_ref["path"]).parent / "INCOMPLETE").exists():
                raise ValueError("teacher publication still incomplete")
            n = inputs["counts"]["pair_rows"]
            self.pairs = self._map(
                "pairs",
                inputs["class_pairs"],
                inputs["class_pairs_identity"],
                PAIR,
                (n,),
            )
            entry = bank["teachers"][teacher]
            self.values = self._map(
                "values",
                entry["values"],
                entry["values_identity"],
                np.dtype("<f4"),
                (n, 2),
            )
            self.policy_value = "policy" in entry
            self.joint_batch_targets = None
            if self.policy_value:
                policy = entry["policy"]
                if (
                    teacher != "C"
                    or set(policy)
                    != {
                        "action_order",
                        "value_perspective",
                        "input_coordinates",
                        "orientation_targets",
                        "temperature",
                        "probabilities",
                        "probabilities_identity",
                        "legal_mask",
                        "legal_mask_identity",
                    }
                    or policy["action_order"] != "absolute-core-action-id209"
                    or policy["value_perspective"] != "side-to-move"
                    or policy["input_coordinates"] != "canonical-public-STM0-native-C20"
                    or policy["orientation_targets"]
                    != "independent same-forward actual input orientations"
                    or type(policy["temperature"]) not in (int, float)
                    or not np.isfinite(policy["temperature"])
                    or policy["temperature"] <= 0
                ):
                    raise ValueError("honest bound C joint policy/value metadata")
                self.policy_temperature = policy["temperature"]
                self.policy = self._map(
                    "policy",
                    policy["probabilities"],
                    policy["probabilities_identity"],
                    np.dtype("<f4"),
                    (n, 2, 209),
                )
                self.policy_legal = self._map(
                    "policy_legal",
                    policy["legal_mask"],
                    policy["legal_mask_identity"],
                    np.dtype("u1"),
                    (n, 2, 209),
                )
            self.observations = ClassObservations(self.pairs)
            self.observations.validate_values(self.values)
            self.counts = self.observations.counts
            total = sum(self.counts.values())
            self.rows = range(total)
            self.splits = np.r_[
                np.zeros(self.counts["train"], dtype="u1"),
                np.ones(self.counts["validation"], dtype="u1"),
            ]
            self.eligible = np.ones(total, dtype=bool)
            self.groups = _VirtualColumn(self, groups=True)
            self.labels = _VirtualColumn(self)
            self.families = range(n)  # LR input classes, never independent games.
            self.binding = dict(
                schema=self.manifest["schema"],
                dataset_sha=hashlib.sha256((path / "cache.json").read_bytes()).hexdigest(),
                input_classes=self.input_ref,
                teacher_values=bank_ref,
                teacher=teacher,
                semantic_scope="board-only static STM; game/history UNKNOWN",
            )
            self.executed_orientations = np.zeros((n, 2), dtype="<u4")
            self.training_stream = hashlib.sha256()
            self.pending_training = None
            self.executed_rows = 0
        except BaseException as error:
            self.close(primary_error=error)
            raise

    def _map(self, name, ref, identity, dtype, shape):
        path = Path(ref["path"])
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or list(IndexedPublicCorpus.identity(info)) != list(identity)
            or info.st_size != ref["bytes"]
            or np.prod(shape) * dtype.itemsize != ref["bytes"]
        ):
            raise ValueError("static artifact changed since owning hash scan")
        stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb")
        self.streams[name] = stream
        self.identities[name] = (path, list(identity))
        if list(IndexedPublicCorpus.identity(os.fstat(stream.fileno()))) != list(identity):
            raise ValueError("static artifact identity changed while opening")
        result = np.memmap(stream, dtype=dtype, mode="r", shape=shape)
        self.maps[name] = result
        return result

    def verify_binding(self):
        for name, (path, identity) in self.identities.items():
            if (
                list(IndexedPublicCorpus.identity(path.lstat())) != identity
                or list(IndexedPublicCorpus.identity(os.fstat(self.streams[name].fileno())))
                != identity
            ):
                raise ValueError("static corpus custody changed during reader")

    def close(self, primary_error=None):
        errors = []
        for value in self.maps.values():
            try:
                value._mmap.close()
            except BaseException as error:
                errors.append(error)
        self.maps.clear()
        for stream in self.streams.values():
            try:
                stream.close()
            except BaseException as error:
                errors.append(error)
        self.streams.clear()
        if errors:
            raise BaseExceptionGroup(
                "static corpus close", ([primary_error] if primary_error else []) + errors
            )

    def locate(self, index, mask=None):
        index = np.asarray(index)
        if (
            index.ndim != 1
            or index.dtype.kind not in "iu"
            or np.any(index < 0)
            or np.any(index >= len(self.rows))
        ):
            raise ValueError("virtual original observation IDs out of range")
        pair = np.empty(len(index), dtype=np.int64)
        orientation = np.empty(len(index), dtype="u1")
        training = index < self.counts["train"]
        if mask is not None:
            mask = np.asarray(mask)
            if mask.dtype != np.dtype(bool) or mask.shape != index.shape or not training.all():
                raise ValueError("T-only actual orientation mask")
        for split, selection in [("train", training), ("validation", ~training)]:
            if not selection.any():
                continue
            local = index[selection] - (0 if split == "train" else self.counts["train"])
            pair[selection], orientation[selection] = self.observations.offsets(
                split, local, None if mask is None else mask[selection], training=mask is not None
            )
        return pair, orientation

    def batch_into(self, index, mask, out, distance, *, records_out=None, workspace=None):
        pair, orientation = self.locate(index, mask)
        records = input_records(self.pairs["key"][pair])
        features(records["geometry"], orientation.astype(bool), out=out, workspace=workspace)
        distance[:] = records["distance"]
        target = self.values[pair, orientation]
        if self.policy_value:
            self.joint_batch_targets = self.policy_targets(pair, orientation)
        if not np.isfinite(target).all():
            raise ValueError("missing actual teacher scalar")
        if mask is not None:
            self.pending_training = (
                np.asarray(index, dtype="<u8").copy(),
                np.asarray(mask, dtype=bool).copy(),
                pair.copy(),
                orientation.copy(),
            )
        return target[:, None]

    def batch(self, index, mask=None):
        n = len(index)
        x = np.empty((n, 2, 312), dtype=np.float32)
        distance = np.empty((n, 2), dtype=np.float32)
        target = self.batch_into(index, mask, x, distance)
        return x, distance, target

    def metadata(self, index):
        pair, orientation = self.locate(index)
        records = input_records(self.pairs["key"][pair])
        stock = records["geometry"]["stocks"].sum(axis=1)
        return (
            records["distance"],
            self.values[pair, orientation, None],
            np.full(len(pair), 255, dtype="u1"),
            stock,
        )

    def statistics(self):
        """Common T-only population moments; LR leaves wall distances unchanged."""
        total = self.counts["train"]
        summed = np.zeros(2, dtype=np.float64)
        for first in range(0, len(self.pairs), 65536):
            rows = self.pairs[first : first + 65536]
            weight = np.where(
                rows["split"] == 0, rows["observations"].sum(axis=1, dtype=np.uint64), 0
            )
            distance = input_records(rows["key"])["distance"].astype(np.float64)
            summed += (distance * weight[:, None]).sum(axis=0)
        mean = summed / total
        square = np.zeros(2, dtype=np.float64)
        for first in range(0, len(self.pairs), 65536):
            rows = self.pairs[first : first + 65536]
            weight = np.where(
                rows["split"] == 0, rows["observations"].sum(axis=1, dtype=np.uint64), 0
            )
            distance = input_records(rows["key"])["distance"].astype(np.float64)
            square += (((distance - mean) ** 2) * weight[:, None]).sum(axis=0)
        return dict(
            mu_f32=mean.astype(np.float32).tolist(),
            sigma_f32=np.maximum(
                np.sqrt(square / total).astype(np.float32), np.float32(0.0001)
            ).tolist(),
        )

    def evaluation_weights(self, index):
        pair, _ = self.locate(index)
        return np.bincount(pair, minlength=len(self.pairs)).astype(np.float64)

    def evaluation_chunks(self, index, size):
        if type(size) is not int or size < 2:
            raise ValueError("bounded two-orientation evaluation batch required")
        weights = self.evaluation_weights(index)
        # Each original observation is represented equally in both orientations;
        # duplicates share one actual prediction, not an independence claim.
        pairs = np.flatnonzero(weights)
        for first in range(0, len(pairs), max(1, size // 2)):
            selected = pairs[first : first + max(1, size // 2)]
            ids = np.repeat(selected, 2)
            orientation = np.tile(np.array([0, 1], dtype="u1"), len(selected))
            keys = self.pairs["key"][ids]
            from .public_features import reflected_keys

            symmetric = reflected_keys(self.pairs["key"][selected]) == self.pairs["key"][selected]
            keep = np.ones(len(ids), dtype=bool)
            keep[1::2] = ~symmetric
            w = np.repeat(weights[selected] / 2, 2)
            w[::2][symmetric] *= 2
            ids, orientation, w = ids[keep], orientation[keep], w[keep]
            rows = input_records(keys[keep])
            yield (
                ids,
                orientation,
                w,
                features(rows["geometry"], orientation.astype(bool)),
                rows["distance"],
            )

    def completed_training_forward(self):
        if self.pending_training is None:
            raise ValueError("no actual supplied training orientation")
        index, mask, pair, orientation = self.pending_training
        flat = pair * 2 + orientation
        unique, count = np.unique(flat, return_counts=True)
        before = self.executed_orientations.reshape(-1)[unique].astype(np.uint64)
        if np.any(before + count > np.iinfo(np.uint32).max):
            raise OverflowError("executed orientation counter overflow")
        self.executed_orientations.reshape(-1)[unique] = (before + count).astype("<u4")
        self.training_stream.update(np.asarray([len(index)], dtype="<u4").tobytes())
        self.training_stream.update(index.tobytes())
        self.training_stream.update(mask.tobytes())
        self.executed_rows += len(index)
        self.pending_training = None

    def save_exposure(self, path):
        path = Path(path)
        temporary = path.with_suffix(".partial")
        with temporary.open("wb") as stream:
            self.executed_orientations.tofile(stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        return dict(
            schema="quoridor-static-executed-orientations-u32-v1",
            file=path.name,
            shape=list(self.executed_orientations.shape),
            bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            rows=self.executed_rows,
            ordered_index_mask_sha256=self.training_stream.hexdigest(),
            **(
                {
                    "stream_segments": {
                        "previous": self.training_stream_prefix,
                        "current": self.training_stream.hexdigest(),
                        "semantics": "prefix digest plus current block; not a resumed hashlib digest",
                    }
                }
                if hasattr(self, "training_stream_prefix")
                else {}
            ),
            semantics="successful training forwards, may exceed completed optimizer draws after update failure",
        )

    def policy_targets(self, pair, orientation):
        """Actual same-input orientation output; not assumed teacher LR equivariance."""
        if not self.policy_value:
            raise ValueError("scalar-only bank has no policy targets")
        probability = np.asarray(self.policy[pair, orientation], dtype=np.float32).copy()
        legal = np.asarray(self.policy_legal[pair, orientation]).copy()
        if (
            probability.ndim != 2
            or probability.shape[1] != 209
            or legal.shape != probability.shape
            or np.any(legal > 1)
            or not legal.any(axis=1).all()
            or not np.isfinite(probability).all()
            or np.any(probability < 0)
            or np.any(probability[legal == 0] != 0)
            or not np.allclose(probability.sum(axis=1), 1, atol=1e-6, rtol=0)
        ):
            raise ValueError("finite nonnegative legal full-distribution targets")
        return probability, legal.astype(bool)
