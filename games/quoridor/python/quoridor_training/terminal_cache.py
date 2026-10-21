"""Published terminal outcomes behind the maintained geometry batch API."""

from array import array
from collections.abc import Sequence
import json
import hashlib
from pathlib import Path

import numpy as np

from .cache import sha
from .distance_steps import require_completed_stream_cache
from .common import common_cache_config
from .compact_cache import CompactCorpus
from .public_features import RECORD, validate_geometry, geometry_from_native

SCHEMA = "quoridor-terminal-geometry-v1"
COMMON_SCHEMA = "quoridor-common-corpus-terminal-geometry-v3"
COMMON_WIDTHS = {
    "geometry.bin": 66,
    "distance-steps.u8": 2,
    "terminal-margin.f32": 4,
    "labels.f32": 8,
    "completed-root-raw.f32": 4,
    "common-eligible.u8": 1,
    "sampling.bin": 6,
}
FILES = {
    "geometry.bin",
    "distance-steps.u8",
    "terminal-margin.f32",
    "labels.f32",
    "rows.jsonl",
}


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
        if self.corpus.common:
            # Only the published binaries and compact sampling table are current
            # training inputs; canonical Game/history JSON stays outside this view.
            group = int(self.corpus.groups[index])
            labels = self.corpus.labels[index]
            record = self.corpus.record(index)

            def label(column):
                value = float(labels[column])
                return None if np.isnan(value) else value

            return {
                "id": self.corpus.row_ids[index],
                "group": self.corpus.families[group],
                "game": self.corpus.game_names[int(self.corpus.row_game_codes[index])],
                "split": ("train", "validation")[int(self.corpus.splits[index])],
                "primary_eligible": bool(self.corpus.primary_eligible[index]),
                "teacher_type": "terminal_outcome",
                "rootmean": label(0),
                "z": label(1),
                "outcome_steps": None if label(1) is None else 80 * label(1),
                "terminal_margin": label(2),
                "completed_root_raw": label(3),
                "distance": record["distance"].tolist(),
                "source_shard": int(record["shard"]),
                "source_row": int(record["row"]),
                "source_alias": int(record["row"]),
                "phase_proxy": 0
                if int(record["geometry"]["stocks"].sum()) >= 16
                else (1 if int(record["geometry"]["stocks"].sum()) >= 6 else 2),
            }
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
        require_completed_stream_cache(self.path, self.manifest)
        self.manifest_sha = sha(self.path / "cache.json")
        m = self.manifest
        if m.get("schema") == COMMON_SCHEMA:
            self._load_common()
            return
        self.common = False
        self.cache_files = FILES
        if "stream_intake" in m and not self.common:
            games = m["stream_intake"]["provenance"]["games_file"]
            if (
                games["file"] != "stream-games.jsonl"
                or sha(self.path / games["file"]) != games["sha256"]
            ):
                raise ValueError("authoritative game/failed search census changed")
        if (
            m.get("schema") != SCHEMA
            or m.get("feature_count") != 312
            or type(m.get("rows")) is not int
            or m["rows"] < 0
            or type(m.get("allow_test")) is not bool
            or (m["allow_test"] and not allow_test)
            or m.get("label_columns") != ["rootmean", "z", "terminal_margin"]
            or set(m.get("sha256", {})) != self.cache_files
            or m.get("files") != {name: name for name in self.cache_files}
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
        for name in self.cache_files:
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

        def row_records():
            with (self.path / "rows.jsonl").open("rb") as stream:
                while True:
                    offset = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    yield offset, json.loads(line)

        for offset, row in row_records():
            i = len(self.row_offsets)
            if i >= self.row_count:
                raise ValueError("terminal row denominator")
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

    def _load_common(self):
        """Read only the once-published binary cache and its compact sampling manifest."""
        m = self.manifest
        cfg = common_cache_config(m)
        widths = COMMON_WIDTHS
        if (
            m["feature_count"] != 312
            or m["allow_test"] is not False
            or type(m["rows"]) is not int
            or not 0 <= m["rows"] <= cfg["batch_count"] * 200
            or m["label_columns"] != ["rootmean", "z", "terminal_margin", "completed_root_raw"]
            or m["files"] != {name: name for name in widths}
            or set(m["sha256"]) != set(widths)
            or m["file_bytes"] != {name: width * m["rows"] for name, width in widths.items()}
        ):
            raise ValueError("compact common schema/columns/length/count")
        self.row_count = m["rows"]
        self.common = True
        self.cache_files = set(widths)
        for name, width in widths.items():
            file = self.path / name
            digest = m["sha256"][name]
            if (
                file.is_symlink()
                or not file.is_file()
                or file.stat().st_size != width * self.row_count
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
                or sha(file) != digest
            ):
                raise ValueError("compact common file identity: " + name)
        sampling = m["sampling"]
        if (
            set(sampling)
            != {
                "schema",
                "file",
                "format",
                "width_B",
                "families",
                "games",
                "row_ids",
                "rows_by_family",
                "common_eligible_by_family",
            }
            or sampling["schema"] != "quoridor-common-corpus-sampling-v1"
            or sampling["file"] != "sampling.bin"
            or sampling["format"] != "<IBB"
            or sampling["width_B"] != 6
            or not isinstance(sampling["families"], list)
            or not isinstance(sampling["row_ids"], list)
            or len(sampling["row_ids"]) != self.row_count
            or len(set(sampling["row_ids"])) != self.row_count
            or any(
                not isinstance(v, str) or not 0 < len(v.encode()) <= 256
                for v in sampling["row_ids"]
            )
        ):
            raise ValueError("compact sampling layout/row identities")
        families = sampling["families"]
        if len(families) > cfg["families"]:
            raise ValueError("compact sampling planned families")
        seen = set()
        for family in families:
            if (
                set(family) != {"family", "game", "split"}
                or not isinstance(family["family"], str)
                or len(family["family"]) != 64
                or any(c not in "0123456789abcdef" for c in family["family"])
                or family["family"] in seen
                or family["split"] not in ("train", "validation")
                or not isinstance(family["game"], str)
                or not 0 < len(family["game"].encode()) <= 256
            ):
                raise ValueError("compact family/game/whole-family split")
            seen.add(family["family"])
        for name in ("rows_by_family", "common_eligible_by_family"):
            counts = sampling[name]
            if (
                not isinstance(counts, list)
                or len(counts) != len(families)
                or any(type(v) is not int or not 0 <= v <= self.row_count for v in counts)
            ):
                raise ValueError("compact family census")

        def mapped(name, dtype, shape):
            return (
                np.memmap(self.path / name, dtype=dtype, mode="r", shape=shape)
                if self.row_count
                else np.empty(shape, dtype=dtype)
            )

        self.maps = [mapped("geometry.bin", RECORD, (self.row_count,))]
        self.offsets = np.array([0, self.row_count])
        self.integer_distances = mapped("distance-steps.u8", np.uint8, (self.row_count, 2))
        original = mapped("labels.f32", "<f4", (self.row_count, 2))
        margin = mapped("terminal-margin.f32", "<f4", (self.row_count,))
        self.raw_root_scores = mapped("completed-root-raw.f32", "<f4", (self.row_count,))
        self.common_mask = mapped("common-eligible.u8", np.uint8, (self.row_count,))
        dtype = np.dtype([("family_code", "<u4"), ("split", "u1"), ("primary_eligible", "u1")])
        self.sampling = mapped("sampling.bin", dtype, (self.row_count,))
        if (
            not np.isfinite(self.raw_root_scores).all()
            or np.any(np.abs(self.raw_root_scores) > 2)
            or not np.isin(self.common_mask, [0, 1]).all()
            or not np.isin(self.sampling["primary_eligible"], [0, 1]).all()
            or not np.isin(self.sampling["split"], [0, 1]).all()
            or np.any(self.sampling["family_code"] >= len(families))
            or np.any(self.common_mask > self.sampling["primary_eligible"])
        ):
            raise ValueError("compact finite raw/mask/family/split bytes")
        self.groups = self.sampling["family_code"]
        self.splits = self.sampling["split"]
        self.primary_eligible = self.sampling["primary_eligible"]
        self.eligible = self.common_mask.astype(bool)
        self.families = [v["family"] for v in families]
        self.group_games = [v["game"] for v in families]
        self.row_ids = sampling["row_ids"]
        blocks = sampling["games"]
        if not isinstance(blocks, list) or len(blocks) > cfg["batch_count"]:
            raise ValueError("compact chronological game blocks")
        self.game_names = []
        self.row_game_codes = np.empty(self.row_count, dtype=np.uint32)
        offset = 0
        for code, block in enumerate(blocks):
            if (
                not isinstance(block, dict)
                or set(block) != {"game", "family_code", "start", "rows"}
                or not isinstance(block["game"], str)
                or not 0 < len(block["game"].encode()) <= 256
                or block["game"] in self.game_names
                or type(block["family_code"]) is not int
                or not 0 <= block["family_code"] < len(families)
                or type(block["start"]) is not int
                or block["start"] != offset
                or type(block["rows"]) is not int
                or not 0 < block["rows"] <= 200
                or offset + block["rows"] > self.row_count
            ):
                raise ValueError("compact game chronology/count/family")
            end = offset + block["rows"]
            if np.any(self.groups[offset:end] != block["family_code"]):
                raise ValueError("compact game family drift")
            self.game_names.append(block["game"])
            self.row_game_codes[offset:end] = code
            offset = end
        if offset != self.row_count:
            raise ValueError("compact game row census")
        for code, family in enumerate(families):
            first = next((b for b in blocks if b["family_code"] == code), None)
            if first is None or first["game"] != family["game"]:
                raise ValueError("compact first-arrival game identity")
        split_codes = np.asarray(
            [0 if v["split"] == "train" else 1 for v in families], dtype=np.uint8
        )
        first_codes = list(dict.fromkeys(int(v) for v in self.groups))
        if (
            first_codes != list(range(len(families)))
            or not np.array_equal(self.splits, split_codes[self.groups])
            or np.bincount(self.groups, minlength=len(families)).tolist()
            != sampling["rows_by_family"]
            or np.bincount(self.groups[self.eligible], minlength=len(families)).tolist()
            != sampling["common_eligible_by_family"]
        ):
            raise ValueError("compact first-arrival/family split/census")
        counts = {
            name: int(np.count_nonzero(self.eligible & (self.splits == code)))
            for name, code in (("train", 0), ("validation", 1))
        }
        if (
            int(self.eligible.sum()) != m["common_corpus"]["common_eligible_rows"]
            or counts != m["common_corpus"]["common_eligible_by_split"]
        ):
            raise ValueError("literal common mask planned/split census")
        self.labels = np.empty((self.row_count, 4), dtype=np.float32)
        self.labels[:, :2] = original
        self.labels[:, 2] = margin
        self.labels[:, 3] = self.raw_root_scores
        expected_mask = self.primary_eligible.astype(bool) & np.isfinite(original[:, 1])
        if (
            not np.array_equal(self.eligible, expected_mask)
            or not np.isfinite(self.labels[self.eligible]).all()
            or np.any(~(np.isnan(original[:, 1]) | np.isin(original[:, 1], [-1, 0, 1])))
            or np.any(np.abs(original[np.isfinite(original[:, 0]), 0]) > 1)
            or np.any(np.abs(margin[np.isfinite(margin)]) > 80)
            or not np.isfinite(self.maps[0]["distance"]).all()
            or np.any(self.integer_distances > 80)
        ):
            raise ValueError("compact binary teacher/distance range")
        normalized = self.integer_distances.astype("<f4") / np.float32(80)
        if not np.array_equal(self.maps[0]["distance"].view("<u4"), normalized.view("<u4")):
            raise ValueError("compact integer distance/D80 bits")
        validate_geometry(self.maps[0]["geometry"])
        self.rows = TerminalRows(self)
        self.binding = {
            **m,
            "dataset_sha": self.manifest_sha,
            "path": str(self.path.resolve()),
            "test_opened": False,
        }

    def verify_binding(self):
        if sha(self.path / "cache.json") != self.manifest_sha or any(
            sha(self.path / name) != self.manifest["sha256"][name] for name in self.cache_files
        ):
            raise ValueError("terminal corpus changed")
