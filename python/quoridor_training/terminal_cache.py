"""New dual-terminal-teacher cache behind the maintained geometry batch API."""

from array import array
from collections.abc import Sequence
import json
import hashlib
from pathlib import Path

import numpy as np

from .cache import sha
from .compact_cache import CompactCorpus
from .public_features import RECORD, validate_geometry, geometry_from_native

SCHEMA = "quoridor-terminal-geometry-v1"
FILES = {"geometry.bin", "distance-steps.u8", "terminal-margin.f32", "labels.f32", "rows.jsonl"}


def validate_terminal_metadata(row):
    if type(row["primary_eligible"]) is not bool:
        raise ValueError("explicit boolean terminal eligibility")
    targets = row["terminal_targets"]
    provenance = targets["provenance"]
    if provenance["schema"] != "quoridor-terminal-teachers-v1":
        raise ValueError("terminal provenance schema")
    side = row["side"]
    if type(side) is not int or side not in (1, 2):
        raise ValueError("absolute row STM")
    for distances in [
        provenance["final_distance_p1_p2"],
        targets["current_distance_steps_stm_opponent"],
    ]:
        if (
            not isinstance(distances, list)
            or len(distances) != 2
            or any(type(d) is not int or not 0 <= d <= 80 for d in distances)
        ):
            raise ValueError("canonical integer wall distances")
    reason = provenance["reason"]
    if reason not in ("goal", "threefold", "unknown"):
        raise ValueError("termination kind")
    for value in [
        targets["outcome_z"],
        targets["margin_target_steps"],
        targets["terminal_geometric_margin_steps"],
    ]:
        if value is not None and type(value) is not int:
            raise ValueError("integer terminal labels")
    if row["z"] is not None and (type(row["z"]) not in (int, float) or row["z"] not in (-1, 0, 1)):
        raise ValueError("outcome z type/range")
    final = provenance["terminal_distance_p1_p2"]
    if reason == "unknown":
        if (
            any(
                value is not None
                for value in [
                    final,
                    provenance["winner"],
                    targets["outcome_z"],
                    row["z"],
                    targets["margin_target_steps"],
                    targets["terminal_geometric_margin_steps"],
                ]
            )
            or row["primary_eligible"]
        ):
            raise ValueError("UNKNOWN has no terminal labels/eligibility")
    else:
        if final != provenance["final_distance_p1_p2"]:
            raise ValueError("terminal versus final geometry")
        winner = provenance["winner"]
        if reason == "goal" and (
            type(winner) is not int or winner not in (1, 2) or final[winner - 1] != 0
        ):
            raise ValueError("goal winner/distance")
        if reason == "threefold" and winner is not None:
            raise ValueError("draw must have no winner")
        z = 0 if reason == "threefold" else (1 if winner == side else -1)
        margin = final[(side - 1) ^ 1] - final[side - 1]
        if (
            row["z"] != z
            or targets["outcome_z"] != z
            or targets["terminal_geometric_margin_steps"] != margin
            or targets["margin_target_steps"] != (0 if reason == "threefold" else margin)
        ):
            raise ValueError("terminal teacher STM/draw/margin mismatch")
    prefix, final_prefix = row["prefix"], provenance["final_prefix"]
    if (
        not isinstance(prefix, list)
        or not isinstance(final_prefix, list)
        or final_prefix[: len(prefix)] != prefix
        or any(type(v) is not int or not 0 <= v <= 208 for v in final_prefix)
    ):
        raise ValueError("terminal/full row prefix chronology")
    if row["research_ruleset"] != provenance["ruleset"]:
        raise ValueError("row/game rules mismatch")
    return targets


class TerminalRows(Sequence):
    def __init__(self, corpus):
        self.corpus = corpus

    def __len__(self):
        return self.corpus.row_count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if not 0 <= index < len(self):
            raise IndexError(index)
        with (self.corpus.path / "rows.jsonl").open("rb") as stream:
            stream.seek(self.corpus.row_offsets[index])
            row = json.loads(stream.readline())
        row["outcome_steps"] = None if row["z"] is None else 80 * row["z"]
        row["terminal_margin"] = row["terminal_targets"]["margin_target_steps"]
        return row

    def iter_indices(self, indices):
        for index in indices:
            yield self[int(index)]


class TerminalCorpus(CompactCorpus):
    """Reuse qualified fused geometry/reflection/buffer methods, with real families."""

    terminal = True

    def __init__(self, path, allow_test=False):
        self.path = Path(path)
        self.manifest = json.loads((self.path / "cache.json").read_text())
        self.manifest_sha = sha(self.path / "cache.json")
        m = self.manifest
        if (
            m.get("schema") != SCHEMA
            or m.get("feature_count") != 312
            or type(m.get("rows")) is not int
            or m["rows"] < 0
            or type(m.get("allow_test")) is not bool
            or (m["allow_test"] and not allow_test)
            or m.get("label_columns") != ["rootmean", "z", "terminal_margin"]
            or set(m.get("sha256", {})) != FILES
            or m.get("files") != {name: name for name in FILES}
        ):
            raise ValueError("terminal cache schema/files/teacher layout")
        self.row_count = m["rows"]
        for name, width in [
            ("geometry.bin", 66),
            ("distance-steps.u8", 2),
            ("terminal-margin.f32", 4),
            ("labels.f32", 8),
        ]:
            if (self.path / name).stat().st_size != width * self.row_count:
                raise ValueError("terminal exact byte length: " + name)
        for name in FILES:
            if sha(self.path / name) != m["sha256"][name]:
                raise ValueError("terminal cache hash: " + name)

        def mapped(name, dtype, shape):
            return (
                np.memmap(self.path / name, dtype=dtype, mode="r", shape=shape)
                if self.row_count
                else np.empty(shape, dtype=dtype)
            )

        self.maps = [mapped("geometry.bin", RECORD, (self.row_count,))]
        self.integer_distances = mapped("distance-steps.u8", np.uint8, (self.row_count, 2))
        original = mapped("labels.f32", "<f4", (self.row_count, 2))
        margin = mapped("terminal-margin.f32", "<f4", (self.row_count,))
        self.labels = np.empty((self.row_count, 3), dtype=np.float32)
        self.labels[:, :2] = original
        self.labels[:, 2] = margin
        self.offsets = np.array([0, self.row_count])
        self.row_offsets = array("Q")
        groups, splits, eligible, families, family_partition = [], [], [], {}, {}
        identities = set()
        with (self.path / "rows.jsonl").open("rb") as stream:
            while True:
                offset = stream.tell()
                line = stream.readline()
                if not line:
                    break
                i = len(self.row_offsets)
                if i >= self.row_count:
                    raise ValueError("terminal row denominator")
                row = json.loads(line)
                targets = validate_terminal_metadata(row)
                if (
                    row["id"] in identities
                    or not row["id"]
                    or row["teacher_type"] != "terminal_pair"
                    or row["split"] not in ("train", "validation")
                    or type(row["primary_eligible"]) is not bool
                ):
                    raise ValueError("terminal identity/teacher/split")
                identities.add(row["id"])
                family, split = row["group"], row["split"]
                if family in family_partition and family_partition[family] != split:
                    raise ValueError("complete family leaked between T/V")
                family_partition[family] = split
                families.setdefault(family, len(families))
                groups.append(families[family])
                splits.append(0 if split == "train" else 1)
                eligible.append(row["primary_eligible"])
                record = self.maps[0][i]
                ids = row["ids"] if row["side"] == 1 else row["ids"][::-1]
                if len(ids) != 2 or any(
                    not isinstance(view, list)
                    or len(view) > 24
                    or any(type(v) is not int or not 0 <= v < 312 for v in view)
                    or view != sorted(set(view))
                    for view in ids
                ):
                    raise ValueError("native canonical QF1 IDs")
                dense = np.zeros((1, 2, 312), dtype=np.uint8)
                for view in range(2):
                    dense[0, view, ids[view]] = 1
                canonical_geometry = geometry_from_native(
                    np.packbits(dense.reshape(1, 624), axis=1, bitorder="little")
                )
                if canonical_geometry[0].tobytes() != record["geometry"].tobytes():
                    raise ValueError("cache geometry versus native two-view QF1")
                raw_input = record.tobytes()[:28]
                input_sha = hashlib.sha256(raw_input).digest()
                if (
                    input_sha.hex() != row["input_geometry_SHA256"]
                    or input_sha != record["input_sha"].tobytes()
                ):
                    raise ValueError("cache input SHA binding")
                steps = targets["current_distance_steps_stm_opponent"]
                if (
                    not np.array_equal(self.integer_distances[i], steps)
                    or record["distance"].tobytes()
                    != np.asarray([d / 80 for d in steps], dtype="<f4").tobytes()
                ):
                    raise ValueError("integer/raw normalized distance binding")
                for label, actual in [
                    (row["z"], original[i, 1]),
                    (targets["margin_target_steps"], margin[i]),
                ]:
                    if (label is None and not np.isnan(actual)) or (
                        label is not None
                        and np.float32(label).tobytes() != np.float32(actual).tobytes()
                    ):
                        raise ValueError("dual teacher tensor/metadata binding")
                self.row_offsets.append(offset)
        if len(self.row_offsets) != self.row_count:
            raise ValueError("terminal row count")
        validate_geometry(self.maps[0]["geometry"])
        self.groups = np.asarray(groups, dtype=np.uint32)
        self.splits = np.asarray(splits, dtype=np.uint8)
        self.eligible = np.asarray(eligible, dtype=bool)
        self.families = list(families)
        self.rows = TerminalRows(self)
        self.binding = {
            **m,
            "dataset_sha": self.manifest_sha,
            "path": str(self.path.resolve()),
            "test_opened": False,
        }

    def verify_binding(self):
        if sha(self.path / "cache.json") != self.manifest_sha or any(
            sha(self.path / name) != self.manifest["sha256"][name] for name in FILES
        ):
            raise ValueError("terminal corpus changed")
