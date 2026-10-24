"""Publish full-original public classes or configured genuine prefix fixtures.

No teacher/model is loaded here. The normal job guardian owns actual CPU/RAM,
whole holding, cancellation and exact child cleanup. Source shards are serial;
only their verified owning scratch copies are removed after saved receipts.
"""

import argparse
import json
import os
from pathlib import Path
import time

import numpy as np

from .cache import sha
from .common import bound_file_bytes
from .public_sigma import REVISION, NativeCompact, download, opened_observations
from quoridor_runtime.snapshot import write_json
from .static_public import (
    PAIR,
    ClassObservations,
    accumulate_original_shard,
    create_class_accumulator,
    write_class_table,
)


def file_ref(path):
    path = Path(path).resolve()
    before = path.stat()
    digest = sha(path)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise ValueError("artifact changed during owning hash scan")
    return {
        "path": str(path),
        "sha256": digest,
        "bytes": after.st_size,
        "mode": f"{after.st_mode & 0o777:04o}",
    }


def file_identity(path):
    """The owning hash scan binds stable identity; later readers check custody."""
    from .compact_cache import IndexedPublicCorpus

    return IndexedPublicCorpus.identity(Path(path).stat())


def prefix_fixture_rows(source, *, maximum_families=512):
    """Validate explicit isolated fixture histories without generating new states."""
    if type(maximum_families) is not int or not (
        1 <= maximum_families <= 1408 or maximum_families == 5120
    ):
        raise ValueError("bounded native publication family count")
    rows = source.get("fixed_prefixes")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32768:
        raise ValueError("bounded fixed prefix fixture required")
    # Explicit family IDs bind related prefixes before native replay/model load.
    # Their presence is not proof of independent games: the bound source owns
    # that lineage, and the publication keeps independent_validation false.
    family_mode = any(isinstance(row, dict) and "family" in row for row in rows)
    fields = {"fixture", "history", "functional_split"} | ({"family"} if family_mode else set())
    if len(rows) > 64 and not family_mode:
        raise ValueError("more than64 prefixes requires actual bounded family lineage")
    family_splits = {}
    family_histories = {}
    seen = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != fields
            or type(row["fixture"]) is not int
            or row["fixture"] < 0
            or row["fixture"] in seen
            or not isinstance(row["history"], list)
            or len(row["history"]) > 200
            or any(type(a) is not int or not 0 <= a < 209 for a in row["history"])
            or row["functional_split"] not in ("T", "V")
        ):
            raise ValueError("unique fixture IDs, actual core action histories and explicit T/V")
        if family_mode:
            family = row["family"]
            if type(family) is not int or family < 0:
                raise ValueError("recorded nonnegative integer prefix family required")
            if family in family_splits and family_splits[family] != row["functional_split"]:
                raise ValueError("prefix family crosses explicit T/V")
            family_splits[family] = row["functional_split"]
            histories = family_histories.setdefault(family, set())
            history = tuple(row["history"])
            if (
                history in histories
                or len(histories) >= 64
                or len(family_splits) > maximum_families
            ):
                raise ValueError("at most512 families/64 unique prefixes each; no duplicate refill")
            histories.add(history)
        seen.add(row["fixture"])
    if {r["functional_split"] for r in rows} != {"T", "V"}:
        raise ValueError("both functional partitions are required")
    return rows


def prefix_fixture_partition(rows, pairs):
    """Join native original/LR keys; no Python board/key/reflection formula."""
    if len(rows) != len(pairs):
        raise ValueError("one native pair per fixed prefix")
    assignments, observations, provenance = {}, [], []
    for row, keys in zip(rows, pairs):
        if len(keys) != 2 or any(type(k) is not bytes or len(k) != 28 for k in keys):
            raise ValueError("two exact native key28 orientations required")
        original, reflected = keys
        canonical = min(keys)
        code = 0 if row["functional_split"] == "T" else 1
        if canonical in assignments and assignments[canonical] != code:
            raise ValueError("same or true-LR class crosses explicit fixture T/V")
        assignments[canonical] = code
        # One actual source prefix contributes one original weight. The teacher
        # separately evaluates both distinct keys, including zero-weight views.
        observations.append(original)
        provenance.append(
            {
                **row,
                "original_key": original.hex(),
                "reflected_key": reflected.hex(),
                "canonical_key": canonical.hex(),
                "self_lr": original == reflected,
                "original_observations": 1,
                "teacher_orientations": 1 if original == reflected else 2,
            }
        )
    return assignments, observations, provenance


def native_prefix_keys(rows, library):
    """Call the sole native legal replay/STM/true-LR/packed-key owner."""
    import ctypes

    if len(rows) > 64:
        # Preserve the existing native ABI's 64-history bound, with no new replay owner.
        return [
            pair
            for first in range(0, len(rows), 64)
            for pair in native_prefix_keys(rows[first : first + 64], library)
        ]
    actions = [a for row in rows for a in row["history"]]
    offsets = [0]
    for row in rows:
        offsets.append(offsets[-1] + len(row["history"]))
    packed = (ctypes.c_uint16 * max(1, len(actions)))(*actions)
    starts = (ctypes.c_size_t * len(offsets))(*offsets)
    keys = (ctypes.c_uint8 * (len(rows) * 56))()
    status = (ctypes.c_uint8 * len(rows))()
    native = ctypes.CDLL(library)
    function = native.quoridor_public_prefix_keys
    function.argtypes = [
        ctypes.POINTER(ctypes.c_uint16),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_uint8),
    ]
    function.restype = ctypes.c_int
    code = function(packed, len(actions), starts, len(rows), keys, status)
    if code != 0 or any(status):
        raise ValueError(f"native prefix replay rejected: call={code}, rows={list(status)}")
    return [
        (bytes(keys[i * 56 : i * 56 + 28]), bytes(keys[i * 56 + 28 : (i + 1) * 56]))
        for i in range(len(rows))
    ]


def repartition_fixture_authority(source, holdout, partition, original):
    """Validate the new split against the bound original native component census."""
    import hashlib

    authority = partition["repartition"]
    if (
        original is None
        or set(authority)
        != {
            "schema",
            "source_partition",
            "source_schedule",
            "source_observations",
            "max_fit_observations",
            "max_holdout_observations",
            "actual_observations",
        }
        or authority["schema"] != "quoridor-prefix-series-repartition-v1"
        or source["source_observations"] != authority["source_observations"]
        or holdout["source_observations"] != authority["source_observations"]
        or partition["source_series"] != original["source_series"]
        or partition["partition"]["schema"] != original["partition"]["schema"]
        or partition["partition"]["rounding"] != original["partition"]["rounding"]
        or partition["partition"]["seed"] != original["partition"]["seed"]
    ):
        raise ValueError("bound original source/component split authority differs")
    old = original["partition"]["assignments"]
    new = partition["partition"]["assignments"]
    if len(old) != len(new) or not old:
        raise ValueError("repartition must preserve every original member")
    original_splits, new_splits = {}, {}
    identities = set()
    for before, after in zip(old, new, strict=True):
        if (
            set(before) != {"game", "prefix", "family", "split"}
            or set(after) != set(before)
            or {k: v for k, v in before.items() if k != "split"}
            != {k: v for k, v in after.items() if k != "split"}
            or before["game"] in identities
        ):
            raise ValueError("original member/order/prefix/component changed")
        identities.add(before["game"])
        for row, splits in ((before, original_splits), (after, new_splits)):
            family, split = row["family"], row["split"]
            if split not in ("train", "validation", "test") or (
                family in splits and splits[family] != split
            ):
                raise ValueError("repartition cuts an original native component")
            splits[family] = split
    if set(original["source_series"]) != identities:
        raise ValueError("original native source membership differs")
    for record, splits in ((original, original_splits), (partition, new_splits)):
        actual = {
            name: sum(v == name for v in splits.values())
            for name in ("train", "validation", "test")
        }
        if actual != record["actual"] or any(
            type(record["requested"][k]) is not int
            or record["requested"][k] < actual[k]
            or record["deficits"][k] != record["requested"][k] - actual[k]
            for k in actual
        ):
            raise ValueError("native original/new component census differs")
    counts = partition["requested"]
    if (
        any(type(n) is not int or n <= 0 for n in counts.values())
        or set(counts) != {"train", "validation", "test"}
        or sum(counts.values()) != len(original_splits)
        or any(partition["deficits"].values())
    ):
        raise ValueError("complete nonempty whole-component allocation required")
    seed = original["partition"]["seed"]
    ranked = sorted(
        original_splits, key=lambda f: (hashlib.sha256(f"{seed}:{f}".encode()).hexdigest(), f)
    )
    for index, family in enumerate(ranked):
        expected = (
            "train"
            if index < counts["train"]
            else "validation"
            if index < counts["train"] + counts["validation"]
            else "test"
        )
        if new_splits[family] != expected:
            raise ValueError("same-seed native component ranking changed")
    actual_rows = {
        name: sum(a["split"] == name for a in new) for name in ("train", "validation", "test")
    }
    fit_max, holdout_max = authority["max_fit_observations"], authority["max_holdout_observations"]
    if (
        type(fit_max) is not int
        or not 0 < fit_max <= 1792
        or type(holdout_max) is not int
        or not 0 < holdout_max <= 256
        or actual_rows != authority["actual_observations"]
        or any(n <= 0 for n in actual_rows.values())
        or actual_rows["train"] + actual_rows["validation"] > fit_max
        or actual_rows["test"] > holdout_max
    ):
        raise ValueError("saved repartition fit/H row bounds differ")
    return authority


def saved_subset_fixture_authority(source, holdout, partition, original, census, source_config):
    """Verify the bound native subset against every original component, before labels."""
    import hashlib

    authority = partition["selection"]
    expanded = authority.get("schema") == "quoridor-prefix-series-saved-subset-v3"
    coverage = expanded or authority.get("schema") == "quoridor-prefix-series-saved-subset-v2"
    fields = {
        "schema",
        "source_schedule",
        "source_partition",
        "source_observations",
        "source_config",
        "census",
        "exposure_parent",
        "excluded_prefix_components",
        "split_counts",
        "actual_observations",
    }
    if (
        original is None
        or census is None
        or source_config is None
        or set(authority) != fields
        or "repartition" in partition
        or authority["schema"]
        not in (
            "quoridor-prefix-series-saved-subset-v1",
            "quoridor-prefix-series-saved-subset-v2",
            "quoridor-prefix-series-saved-subset-v3",
        )
        or census.get("schema")
        != (
            "research.identity-only-component-census.v2"
            if coverage
            else "research.identity-only-component-census.v1"
        )
        or census["columns"]
        != [
            "rank0",
            "component",
            "member_ids",
            "source_series_ids",
            "disposition",
            "prospective_split",
        ]
        or authority["exposure_parent"] != census["exposureParent" if coverage else "selected64"]
        or authority["source_partition"] != census["partition"]
        or authority["source_schedule"] != census["publishedScheduleByRef"]
        or authority["source_config"] != census["nativeInputConfig"]
        or source["source_observations"] != authority["source_observations"]
        or holdout["source_observations"] != authority["source_observations"]
        or original["partition"]["seed"] != census["componentRankSeed"]
        or source_config["split_seed"] != census["componentRankSeed"]
        or source_config["trajectory"]["split_counts"] != original["requested"]
    ):
        raise ValueError("bound native subset parent/census/config authority differs")
    excluded_authority = census["sourceExclusionAuthority"]

    def bound(ref):
        return {key: ref[key] for key in ("path", "sha256")}

    if coverage:
        if (
            source_config["families"] != (32768 if expanded else 8192)
            or source_config["trajectory"]["wall_layer_observations"] != [0, 1, 0]
            or source_config["excluded_books"] != excluded_authority["excluded_books"]
            or not excluded_authority["excluded_books"]
            or source_config["excluded_static_inputs"]
            != excluded_authority["excluded_static_inputs"]
            or excluded_authority["excluded_static_inputs"] is None
            or (
                expanded
                and (
                    not isinstance(source_config.get("excluded_parent"), dict)
                    or source_config["excluded_parent"] != excluded_authority.get("excluded_parent")
                )
            )
        ):
            raise ValueError("coverage source/exclusion authority differs")
    elif source_config["excluded_books"] != [
        bound(excluded_authority["prefixProjection"]),
        bound(excluded_authority["clockBook"]),
    ] or source_config["excluded_static_inputs"] != bound(
        excluded_authority["staticExclusionManifest"]
    ):
        raise ValueError("inherited T/V/H/dev/clock exclusions differ")
    old = original["partition"]["assignments"]
    old_by_id = {a["game"]: a for a in old}
    if len(old_by_id) != len(old) or set(original["source_series"]) != set(old_by_id):
        raise ValueError("complete unique parent member/source census required")
    members, source_ids = {}, {}
    old_splits = {}
    for a in old:
        if set(a) != {"game", "prefix", "family", "split"}:
            raise ValueError("original native assignment shape differs")
        family = a["family"]
        if family in old_splits and old_splits[family] != a["split"]:
            raise ValueError("original component crosses splits")
        old_splits[family] = a["split"]
        members.setdefault(family, set()).add(a["game"])
        source_ids.setdefault(family, set()).add(original["source_series"][a["game"]])
    old_actual = {
        name: sum(v == name for v in old_splits.values())
        for name in ("train", "validation", "test")
    }
    if original["actual"] != old_actual or any(
        type(original["requested"][name]) is not int
        or original["requested"][name] < count
        or original["deficits"][name] != original["requested"][name] - count
        for name, count in old_actual.items()
    ):
        raise ValueError("original component deficit/count differs")
    seed = census["componentRankSeed"]
    ranked = sorted(members, key=lambda f: (hashlib.sha256(f"{seed}:{f}".encode()).hexdigest(), f))
    excluded, counts = authority["excluded_prefix_components"], authority["split_counts"]
    if (
        type(excluded) is not int
        or not 0 <= excluded <= len(ranked)
        or set(counts) != {"train", "validation", "test"}
        or any(type(v) is not int for v in counts.values())
        or counts["train"] <= 0
        or counts["validation"] <= 0
        or (counts["test"] <= 0 if coverage and not expanded else counts["test"] != 0)
        or not 0 < sum(counts.values()) <= (5120 if expanded else 1408 if coverage else 128)
        or (expanded and counts != {"train": 4096, "validation": 1024, "test": 0})
        or (coverage and excluded != 0)
        or len(ranked) - excluded < sum(counts.values())
    ):
        raise ValueError("bounded nonempty T/V whole-component subset or deficit")
    total = sum(counts.values())
    if (
        census["counts"]
        != {
            "originalSurvivors": len(ranked),
            "originalDeficit": sum(original["deficits"].values()),
            ("excludedComponents" if coverage else "excludedDev64"): excluded,
            "eligibleNamedScope": len(ranked) - excluded,
        }
        or census["prospective"]
        != {
            "selected": total,
            "train": counts["train"],
            "validation": counts["validation"],
            "holdout": counts["test"],
            "deficitWithinNamedScope": 0,
        }
        or len(census["records"]) != len(ranked)
    ):
        raise ValueError("subset census component counts/request differs")
    chosen = {}
    for rank, (family, record) in enumerate(zip(ranked, census["records"], strict=True)):
        selected = excluded <= rank < excluded + total
        split = (
            (
                "train"
                if rank < excluded + counts["train"]
                else "validation"
                if rank < excluded + counts["train"] + counts["validation"]
                else "test"
            )
            if selected
            else None
        )
        if (
            not isinstance(record, list)
            or len(record) != 6
            or type(record[0]) is not int
            or record[:2] != [rank, family]
            or len(record[2]) != len(members[family])
            or set(record[2]) != members[family]
            or len(record[3]) != len(source_ids[family])
            or set(record[3]) != source_ids[family]
            or record[4] != ("excluded_dev64" if rank < excluded else "eligible_named_scope")
            or record[5] != split
        ):
            raise ValueError("native rank/member/source/exposed/split census differs")
        if selected:
            if expanded and len(members[family]) != 1:
                raise ValueError("selected coverage component must be a whole singleton")
            chosen[family] = split
    expected = [{**a, "split": chosen[a["family"]]} for a in old if a["family"] in chosen]
    expected_sources = {a["game"]: original["source_series"][a["game"]] for a in expected}
    if (
        partition["partition"] != {**original["partition"], "assignments": expected}
        or partition["source_series"] != expected_sources
        or len(expected) != total
        or partition["requested"] != counts
        or partition["actual"] != counts
        or partition["deficits"] != {"train": 0, "validation": 0, "test": 0}
        or authority["actual_observations"] != counts
        or len(holdout["observations"]) != counts["test"]
    ):
        raise ValueError(
            "subset cuts/changes parent members, exposes excluded components or changes split"
        )
    return authority


def series_fixture_rows(
    source, holdout, partition, original_partition=None, selection_census=None, source_config=None
):
    """Project a bound native component partition; H remains exclusion-only."""
    schema = "quoridor-prefix-series-observations-v1"
    if (
        source.get("schema") != schema
        or holdout.get("schema") != schema
        or source.get("teacher_labels") is not False
        or holdout.get("teacher_labels") is not False
        or source.get("partition") != holdout.get("partition")
        or not isinstance(source.get("source_observations"), dict)
        or source.get("source_observations") != holdout.get("source_observations")
    ):
        raise ValueError("matching unlabelled native fit/holdout partition required")
    if "selection" in partition:
        saved_subset_fixture_authority(
            source, holdout, partition, original_partition, selection_census, source_config
        )
    elif selection_census is not None or source_config is not None:
        raise ValueError("unexpected saved selection census/config")
    elif "repartition" in partition:
        repartition_fixture_authority(source, holdout, partition, original_partition)
    elif original_partition is not None:
        raise ValueError("unexpected replacement split authority")
    assignments = partition["partition"]["assignments"]
    sources = partition["source_series"]
    by_id = {a["game"]: a for a in assignments}
    if len(by_id) != len(assignments) or set(sources) != set(by_id):
        raise ValueError("complete unique native component/source assignments required")
    series = sorted(set(sources.values()))
    expanded = (
        partition.get("selection", {}).get("schema") == "quoridor-prefix-series-saved-subset-v3"
    )
    coverage = expanded or (
        partition.get("selection", {}).get("schema") == "quoridor-prefix-series-saved-subset-v2"
    )
    if not 1 <= len(series) <= (32768 if expanded else 8192 if coverage else 512):
        raise ValueError("bounded native source series required")
    series_ids = {value: i for i, value in enumerate(series)}
    family_splits, source_families, seen = {}, {}, set()
    projected = [[], []]
    for group, manifest in enumerate((source, holdout)):
        for row in manifest["observations"]:
            identity = row["id"]
            a = by_id.get(identity)
            if (
                identity in seen
                or a is None
                or row["prefix"] != a["prefix"]
                or row["family"] != a["family"]
                or row["split"] != a["split"]
                or row["source_series"] != sources[identity]
                or row["split"] not in (("train", "validation") if group == 0 else ("test",))
            ):
                raise ValueError("fit/H observation differs from native component assignment")
            if (
                not row["prefix"]
                or len(row["prefix"]) > 200
                or any(type(action) is not int or not 0 <= action < 209 for action in row["prefix"])
            ):
                raise ValueError("noninitial complete native prefix required")
            family, split = row["family"], row["split"]
            if family in family_splits and family_splits[family] != split:
                raise ValueError("native component crosses fit/holdout partition")
            family_splits[family] = split
            source_id = row["source_series"]
            if source_id in source_families and source_families[source_id] != family:
                raise ValueError("one source series cannot cross native components")
            source_families[source_id] = family
            seen.add(identity)
            projected[group].append(
                {
                    "fixture": len(seen) - 1,
                    "history": row["prefix"],
                    "family": series_ids[source_id],
                    "functional_split": "T" if split == "train" else "V",
                }
            )
    if seen != set(by_id):
        raise ValueError("native fit/H observation census incomplete")
    actual = {
        name: sum(split == name for split in family_splits.values())
        for name in ("train", "validation", "test")
    }
    if actual != partition["actual"] or any(
        partition["requested"][name] - actual[name] != partition["deficits"][name]
        or partition["deficits"][name] < 0
        for name in actual
    ):
        raise ValueError("native component counts/deficits differ")
    # Only T/V is passed to the existing class publisher. H has no labels/classes.
    rows = prefix_fixture_rows(
        {"fixed_prefixes": projected[0]},
        maximum_families=5120 if expanded else 1408 if coverage else 512,
    )
    return (
        rows,
        projected[1],
        {
            "native_partition": source["partition"],
            "native_full_history_source": source["source_observations"],
            "holdout_observations": len(projected[1]),
            "native_component_counts": actual,
            "native_component_deficits": partition["deficits"],
            "H_teacher_labels": False,
        },
    )


def reject_holdout_keys(assignments, pairs):
    """Native true-LR keys only; no Python board/reflection formula."""
    blocked = set()
    for pair in pairs:
        if len(pair) != 2 or any(type(key) is not bytes or len(key) != 28 for key in pair):
            raise ValueError("native holdout original/LR keys required")
        blocked.add(min(pair))
    if blocked.intersection(assignments):
        raise ValueError("fit class collides with native holdout exact/true-LR key")


def prepare_prefix_fixture(config):
    """Small configured source ingress into the existing PAIR37 publisher.

    This route has explicit isolated functional T/V, not the public hash split;
    no public shards, protected observations, labels or model bodies are read.
    """
    from .static_public import accumulate_inputs

    expected = {"prefix_fixture", "native_library", "output", "max_sqlite_bytes"}
    if "holdout_exclusion" in config:
        expected.add("holdout_exclusion")
    if "selection_census" in config:
        expected.add("selection_census")
        if "holdout_exclusion" not in config:
            raise ValueError("native saved subset requires explicit empty H publication")
    if set(config) != expected:
        raise ValueError("prefix fixture and full-public settings cannot be mixed")
    source_raw = bound_file_bytes(config["prefix_fixture"], 64 * 1024**2)
    source = json.loads(source_raw)
    lineage = None
    extra_sources = []
    holdout_rows = []
    if "holdout_exclusion" in config:
        holdout_raw = bound_file_bytes(config["holdout_exclusion"], 64 * 1024**2)
        partition_raw = bound_file_bytes(source["partition"], 64 * 1024**2)
        partition = json.loads(partition_raw)
        original_partition = None
        parent_sources = []
        selection_census = source_config = None
        if "selection" in partition:
            selection = partition["selection"]
            if config.get("selection_census") != selection["census"]:
                raise ValueError("explicit saved-selection census FileRef differs")
            census_raw = bound_file_bytes(
                config["selection_census"],
                16 * 1024**2
                if selection["schema"] == "quoridor-prefix-series-saved-subset-v3"
                else 4 * 1024**2
                if selection["schema"] == "quoridor-prefix-series-saved-subset-v2"
                else 65536,
            )
            source_config_raw = bound_file_bytes(selection["source_config"], 65536)
            selection_census = json.loads(census_raw)
            source_config = json.loads(source_config_raw)
            parent_sources.extend(
                [
                    (config["selection_census"], census_raw),
                    (selection["source_config"], source_config_raw),
                ]
            )
            parent_ref = selection["source_partition"]
            parent_raw = bound_file_bytes(
                parent_ref,
                512 * 1024**2
                if selection["schema"] == "quoridor-prefix-series-saved-subset-v3"
                else 64 * 1024**2,
            )
            original_partition = json.loads(parent_raw)
            parent_sources.append((parent_ref, parent_raw))
        elif "selection_census" in config:
            raise ValueError("unexpected saved-selection census")
        if "repartition" in partition:
            parent_ref = partition["repartition"]["source_partition"]
            parent_raw = bound_file_bytes(parent_ref, 64 * 1024**2)
            original_partition = json.loads(parent_raw)
            parent_sources.append((parent_ref, parent_raw))
        rows, holdout_rows, lineage = series_fixture_rows(
            source,
            json.loads(holdout_raw),
            partition,
            original_partition,
            selection_census,
            source_config,
        )
        if "selection" in partition:
            lineage["selection"] = partition["selection"]
        elif original_partition is not None:
            lineage["repartition"] = partition["repartition"]
        extra_sources = [
            (config["holdout_exclusion"], holdout_raw),
            (source["partition"], partition_raw),
            *parent_sources,
        ]
    else:
        rows = prefix_fixture_rows(source)
    bound_file_bytes(config["native_library"], 64 * 1024**2)
    pairs = native_prefix_keys(rows, config["native_library"]["path"])
    assignments, observations, provenance = prefix_fixture_partition(rows, pairs)
    if lineage is not None:
        reject_holdout_keys(
            assignments,
            native_prefix_keys(holdout_rows, config["native_library"]["path"])
            if holdout_rows
            else [],
        )
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("prefix fixture publication incomplete; original failure retained\n")
    connection = None
    primary = None
    try:
        database = output / "input-classes.sqlite"
        connection = create_class_accumulator(database, max_bytes=config["max_sqlite_bytes"])
        accumulate_inputs(
            connection,
            np.asarray(observations, dtype="V28"),
            np.zeros(len(observations), dtype="u1"),
        )
        connection.commit()
        table = output / "class-pairs.bin"
        with table.open("xb") as stream:
            counts = write_class_table(connection, stream, split_assignments=assignments)
            stream.flush()
            os.fsync(stream.fileno())
        if len(observations) != len(rows) or counts["qualified_original_observations"] != len(rows):
            raise ValueError("fixture original source multiplicity census differs")
        mapped = np.memmap(table, dtype=PAIR, mode="r")
        try:
            if ClassObservations(mapped).counts != {k: counts[k] for k in ("train", "validation")}:
                raise ValueError("fixture virtual observations differ")
        finally:
            mapped._mmap.close()
        if bound_file_bytes(config["prefix_fixture"], 64 * 1024**2) != source_raw:
            raise ValueError("fixture source changed during publication")
        for reference, original in extra_sources:
            if bound_file_bytes(reference, 64 * 1024**2) != original:
                raise ValueError("native partition/holdout source changed during publication")
        result = {
            "schema": "quoridor-public-static-input-classes-v1",
            "status": "COMPLETE",
            "source_mode": "prefix-fixture",
            "source_manifest": config["prefix_fixture"],
            "native_library": config["native_library"],
            "class_pairs": file_ref(table),
            "class_pairs_identity": file_identity(table),
            "pair_record_bytes": PAIR.itemsize,
            "counts": counts,
            "original_observations": len(rows),
            "source_receipts": provenance,
            "split": {
                "algorithm": "explicit configured functional T/V; reject same/trueLR pair across partitions",
                "independent_validation": False,
                **(
                    {
                        "declared_family_partition": {
                            str(row["family"]): row["functional_split"] for row in rows
                        }
                    }
                    if "family" in rows[0]
                    else {}
                ),
            },
            "value_semantics": "native canonical local STM; no outcome/teacher labels created",
            "full_history": "genuine prefix replay; class key remains board-only",
            "old_label_payload_read": False,
            **(
                {
                    "source_lineage": lineage,
                    "holdout_exclusion": config["holdout_exclusion"],
                }
                if lineage is not None
                else {}
            ),
        }
        write_json(output / "cache.json", result)
        connection.close()
        connection = None
        database.unlink()
        marker.unlink()
        return {"manifest": file_ref(output / "cache.json"), "counts": counts}
    except BaseException as error:
        primary = error
        try:
            write_json(
                output / "failure.json",
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "prefix_fixture": config["prefix_fixture"],
                    "native_library": config["native_library"],
                },
            )
        except BaseException as publication:
            raise BaseExceptionGroup("fixture preparation/publication", [error, publication])
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except BaseException as error:
                raise BaseExceptionGroup(
                    "fixture preparation/SQLite close",
                    ([primary] if primary is not None else []) + [error],
                )


def prepare(config):
    if "prefix_fixture" in config:
        return prepare_prefix_fixture(config)
    source = json.loads(bound_file_bytes(config["source_manifest"], 65536))
    if (
        source.get("revision") != REVISION
        or len(source.get("files", [])) != 43
        or len({row["sha"] for row in source["files"]}) != 43
        or any(
            type(row["rows"]) is not int or row["rows"] <= 0 or row["rows"] % 2
            for row in source["files"]
        )
        or type(config["split_seed"]) is not int
    ):
        raise ValueError("entire pinned original scope and explicit shared class split required")
    # Hash-before-load once. Normal admission also binds this genuine immutable
    # library and its source/software/lifetime; no fake future FileRef is usable.
    bound_file_bytes(config["native_library"], 64 * 1024**2)
    native = NativeCompact(config["native_library"]["path"])
    opened, opened_refs = opened_observations(config["opened_evaluation_receipts"], source)
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("complete full-source census owns publication; failed prefix retained\n")
    scratch = output / "source-scratch"
    scratch.mkdir()
    database = output / "input-classes.sqlite"
    connection = create_class_accumulator(database, max_bytes=config["max_sqlite_bytes"])
    attempts, receipts = [], []
    started = time.monotonic()
    primary = None
    phases = {"source_and_index": 0.0, "table_and_validation": 0.0}
    try:
        tick = time.monotonic()
        for ordinal, item in enumerate(source["files"]):
            reused = [
                r for r in config.get("verified_reuse", []) if r["source_path"] == item["path"]
            ]
            if len(reused) > 1:
                raise ValueError("at most one actual reused source blob per original shard")
            path = download(item, scratch, attempts, item["size"], reused[0] if reused else None)
            before = path.stat()
            receipt = accumulate_original_shard(connection, path, item, native, opened[ordinal])
            after = path.stat()
            if (
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("original source changed during native qualification")
            connection.commit()
            receipts.append(
                {
                    **receipt,
                    "source_ordinal": ordinal,
                    "source_path": item["path"],
                    "source_git_blob": item["sha"],
                    "source_sha256": attempts[-1]["sha256"],
                }
            )
            write_json(output / "progress.json", {"attempts": attempts, "receipts": receipts})
            # External reuse paths are read-only. Only this successful own
            # serial download is reconstructible scratch, never historical RAW.
            if not reused:
                if path.parent != scratch:
                    raise ValueError("source scratch ownership changed")
                path.unlink()
        phases["source_and_index"] = time.monotonic() - tick
        expected = sum(row["rows"] // 2 for row in source["files"])
        if len(receipts) != 43 or sum(r["decoded_original_rows"] for r in receipts) != expected:
            raise ValueError("full original source census incomplete")
        tick = time.monotonic()
        table = output / "class-pairs.bin"
        with table.open("xb") as stream:
            counts = write_class_table(
                connection,
                stream,
                split_seed=config["split_seed"],
            )
            stream.flush()
            os.fsync(stream.fileno())
        native_valid = sum(r["native_codes"][0] for r in receipts)
        if counts["qualified_original_observations"] != native_valid:
            raise ValueError(
                "source-qualified original multiplicity differs from final class census"
            )
        pairs = np.memmap(table, dtype=PAIR, mode="r")
        try:
            observations = ClassObservations(pairs)
            if observations.counts != {k: counts[k] for k in ("train", "validation")}:
                raise ValueError("virtual observation count differs from owning class census")
            del observations
        finally:
            pairs._mmap.close()
        phases["table_and_validation"] = time.monotonic() - tick
        result = {
            "schema": "quoridor-public-static-input-classes-v1",
            "status": "COMPLETE",
            "revision": REVISION,
            "original_only": True,
            "source_manifest": config["source_manifest"],
            "native_library": config["native_library"],
            "class_pairs": file_ref(table),
            "class_pairs_identity": file_identity(table),
            "pair_record_bytes": PAIR.itemsize,
            "original_observations": expected,
            "counts": counts,
            "source_receipts": receipts,
            "source_mapping": "each original valid row -> exact oriented key and trueLR pair; original source order defines within-orientation occurrence ordinal; retain original multiplicity",
            "virtual_order": "within each partition sorted pair, canonical originals then reflected originals",
            "protected_membership": {
                "rule": "old row-split sealed plus known-opened IDs; propagate protection to the complete trueLR pair before teacher access",
                "opened_receipts": opened_refs,
                "protected_payload_use": "opaque exclusion membership only; never teacher/trainer/stopping",
            },
            "split": {
                "seed": config["split_seed"],
                "algorithm": "SHA256(ASCII full-public-teachers-v1|split| + LE-u64 seed + canonical key28); h=BE-u64 first8; 10*h<9*2**64 ->T, elseV",
                "independent_games": "UNKNOWN",
            },
            "value_semantics": "board-only static single evaluation; full history/repetition UNAVAILABLE",
            "old_label_payload_read": False,
            "old_zero_or_missing_termination_filter": False,
            "naive_lr_half_used": False,
            "phases_seconds": phases,
            "whole_seconds": time.monotonic() - started,
        }
        # DB was only a temporary exact-class index. After fully synced output
        # and validated complete census it is reconstructible, not unique data.
        write_json(output / "cache.json", result)
        connection.close()
        connection = None
        database.unlink()
        scratch.rmdir()
        marker.unlink()
        return {"manifest": file_ref(output / "cache.json"), "counts": counts}
    except BaseException as error:
        primary = error
        try:
            write_json(
                output / "failure.json",
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "attempts": attempts,
                    "receipts": receipts,
                    "phases_seconds": phases,
                    "wall_seconds": time.monotonic() - started,
                },
            )
        except BaseException as publication:
            primary = BaseExceptionGroup(
                "original preparation and failure publication", [error, publication]
            )
            raise primary
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except BaseException as error:
                if primary is not None:
                    raise BaseExceptionGroup(
                        "original preparation and SQLite close", [primary, error]
                    )
                raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    # The normal guardian wraps this finite worker; never pin a legacy CPU2/3
    # controller or establish a second scheduler/resource framework here.
    from quoridor_runtime.cycle_process import cancellation_signals

    with cancellation_signals():
        result = prepare(json.loads(Path(args.config).read_bytes()))
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
