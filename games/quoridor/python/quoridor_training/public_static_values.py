"""Finite static-label streaming into the normal public compact scalarbank.

Existing native encoders and StaticHead own all model and feature mathematics.
No Search/MCTS, sampler, scheduler, teacher selection, replay or restart system.
"""

import argparse
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
import sys

import numpy as np

from .common import bound_file_bytes
from .compact_cache import IndexedPublicCorpus
from .public_features import reflected_keys
from .public_static_prepare import file_ref, file_identity
from quoridor_runtime.snapshot import write_json
from .static_public import PAIR, ClassObservations
from .static_teacher_heads import StaticHead
from .static_teacher_inputs import StaticInputs


@contextmanager
def input_pairs(ref):
    manifest = json.loads(bound_file_bytes(ref, 2 * 1024**2))
    if (
        manifest["schema"] != "quoridor-public-static-input-classes-v1"
        or manifest["status"] != "COMPLETE"
        or manifest["pair_record_bytes"] != 37
        or (Path(ref["path"]).parent / "INCOMPLETE").exists()
    ):
        raise ValueError("complete owning input class publication required")
    table = manifest["class_pairs"]
    path = Path(table["path"])
    identity = manifest["class_pairs_identity"]
    n = manifest["counts"]["pair_rows"]
    if (
        list(IndexedPublicCorpus.identity(path.lstat())) != list(identity)
        or table["bytes"] != n * PAIR.itemsize
    ):
        raise ValueError("input table differs from owning hash custody")
    stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb")
    mapped = None
    primary = None
    try:
        if list(IndexedPublicCorpus.identity(os.fstat(stream.fileno()))) != list(identity):
            raise ValueError("input class open identity changed")
        mapped = np.memmap(stream, dtype=PAIR, mode="r", shape=(n,))
        ClassObservations(mapped)
        yield manifest, mapped
        if list(IndexedPublicCorpus.identity(path.lstat())) != list(identity) or list(
            IndexedPublicCorpus.identity(os.fstat(stream.fileno()))
        ) != list(identity):
            raise ValueError("input class identity changed during label reader")
    except BaseException as error:
        primary = error
        raise
    finally:
        failures = []
        for close in ([mapped._mmap.close] if mapped is not None else []) + [stream.close]:
            try:
                close()
            except BaseException as error:
                failures.append(error)
        if failures:
            raise BaseExceptionGroup(
                "class reader original/close errors", ([primary] if primary else []) + failures
            )


def oriented_keys(pairs, capacity):
    """Sorted canonical pairs, actual two orientations; exact symmetric aliases once."""
    if type(capacity) is not int or not 2 <= capacity <= 4096:
        raise ValueError("actual admitted teacher batch capacity2..4096")
    for first in range(0, len(pairs), capacity // 2):
        stop = min(len(pairs), first + capacity // 2)
        key = pairs["key"][first:stop]
        reflected = reflected_keys(key)
        pair = np.repeat(np.arange(first, stop), 2)
        orientation = np.tile(np.array([0, 1], dtype="u1"), len(key))
        keys = np.empty(2 * len(key), dtype="V28")
        keys[::2], keys[1::2] = key, reflected
        keep = np.ones(len(keys), dtype=bool)
        keep[1::2] = key != reflected
        yield pair[keep], orientation[keep], keys[keep]


def actual_orientation_count(pairs):
    n = 0
    for _, _, keys in oriented_keys(pairs, 4096):
        n += len(keys)
    return n


def runtime_devices(config):
    if config["device"] not in ("cpu", "cuda:0") or config["cpu_threads"] != 1:
        raise ValueError("one physical CPU and explicit FP32 teacher device required")
    return {
        name: dict(
            device="cpu" if name == "S-oldORT-single" else config["device"],
            precision="FP32",
            autocast=False,
            tf32=False,
            cpu_intra_threads=1,
            cpu_inter_threads=1,
        )
        for name in ("S-oldORT-single", "S-Torch-single", "S-Torch-batch", "C-single", "C-batch")
    }


def error_details(error):
    """Preserve the original error tree and independent secondary facts."""
    result = dict(type=type(error).__name__, message=str(error))
    if isinstance(error, BaseExceptionGroup):
        result["errors"] = [error_details(item) for item in error.exceptions]
    return result


def retained_repair_limit(config, saved, boundary, *, planned_total, pair_rows):
    """Consume the explicit failed-row repair without changing any original cap."""
    envelope = json.loads(bound_file_bytes(config["failed_row_repair"], 131072))
    repair = envelope["logical_repair"]
    if repair["authority"] != envelope["authority"]:
        raise ValueError("same explicit human failed-row authority required")
    bound_file_bytes(repair["authority"], 32768)
    failed = saved["failed_attempted_rows"]
    if (
        type(failed) is not int
        or failed <= 0
        or repair["old_qualification_attempts"] != boundary["logical_rows_attempted"]
        or repair["prior_total_attempted"] != saved["already_charged_global"]
        or repair["prior_production_returned_finite"] != saved["new_finite"]
        or repair["prior_production_attempted"] != saved["new_finite"] + failed
        or repair["prior_failed_attempts"] != failed
        or repair["additional_failed_row_repair_max"] != failed
        or repair["old_actual_config_ceiling"] != 4 * pair_rows + 256
        or repair["original_plan"] + failed != planned_total
        or repair["conditional_cumulative_attempted_upper"] != planned_total
        or repair["difference_from_old_config"] != planned_total - (4 * pair_rows + 256)
        or repair["qualification_extra_rows"] != 0
        or repair["other_fit_or_arena_quota_change"] != 0
        or config["inclusive_row_limit"] != planned_total
    ):
        raise ValueError("exact past-charge/retained-custody failed-row repair only")
    return planned_total


def label_values(config, *, progress_callback=None):
    """One fresh original stream; failure retains partials, never automatically resumes."""
    # Real boundary success, same actual inputs/models/libraries and runtime
    # must already be bound. A submitted job or source clear is not that result.
    intended_devices = runtime_devices(config)
    boundary = json.loads(bound_file_bytes(config["runtime_boundary"], 131072))
    scoped = boundary["status"] == "PASS_PER_TEACHER_BOUNDARIES"
    teachers = boundary.get("qualified_teachers", ["S", "C"])
    if teachers not in (["S"], ["S", "C"]):
        raise ValueError("original S then C order; no unqualified teacher")
    if (
        boundary["status"] not in ("PASS", "PASS_PER_TEACHER_BOUNDARIES")
        or boundary["input_classes"] != config["input_classes"]
        or boundary["models"] != config["models"]
        or boundary["core_library"] != config["core_library"]
        or boundary["c20_library"] != config["c20_library"]
        or boundary["device"] != config["device"]
        or boundary["route_devices_precision"] != intended_devices
        or boundary["planned_extra_head_rows"] != 0
        or type(boundary["logical_rows_attempted"]) is not int
        or not 0 < boundary["logical_rows_attempted"] <= 256
    ):
        raise ValueError("actual complete same-input/model/runtime boundary required")
    reuse = {}
    for kind in teachers:
        key_ref = boundary["teacher_keys"][kind] if scoped else boundary["keys"]
        keys = np.frombuffer(bound_file_bytes(key_ref, 48 * 28), dtype="V28")
        if not 0 < len(keys) <= 48 or len(np.unique(keys)) != len(keys):
            raise ValueError("bounded actual unique teacher-specific orientation keys")
        values = np.frombuffer(
            bound_file_bytes(boundary["batch_values"][kind], 48 * 4), dtype="<f4"
        )
        if values.shape != keys.shape or not np.isfinite(values).all() or np.any(abs(values) > 1):
            raise ValueError("finite qualified actual teacher batch outputs for reuse")
        reuse[kind] = {bytes(k): v for k, v in zip(keys, values)}
    runtime_coverage = {kind: len(reuse[kind]) for kind in teachers}
    output = Path(config["output"])
    marker = output / "INCOMPLETE"
    saved = None
    saved_new = 0
    saved_first = None
    if config.get("retained_S_prefix") is not None:
        saved = json.loads(bound_file_bytes(config["retained_S_prefix"], 131072))
        old_failure = json.loads(bound_file_bytes(saved["original_failure"], 131072))
        old = old_failure["teachers"]["S"]
        old_head = old["head"]
        if (
            saved["status"] != "SAVED_RETURNED_PREFIX_FROZEN_NOT_RESTARTED"
            or saved["input_classes"] != config["input_classes"]
            or saved["actual_model"] != config["models"]["S"]
            or saved["original_runtime_boundary"] != config["runtime_boundary"]
            or Path(saved["original_bank"]["path"]) != output / "S.f32"
            or not marker.is_file()
            or (output / "C.f32").exists()
            or (output / "teacher-values.json").exists()
            or (output / "remaining-labels-failure.json").exists()
            or saved["already_charged_boundary"] != boundary["logical_rows_attempted"]
            or saved["already_charged_global"] != old_failure["inclusive_attempted_rows"]
            or saved["new_finite"] != old["new_finite_rows"]
            or saved["new_finite"] != old_head["finite_rows_returned"]
            or saved["failed_attempted_rows"] != old_head["failed_attempted_rows"]
            or saved["already_charged_global"]
            != boundary["logical_rows_attempted"] + old_head["logical_rows_attempted"]
            or list(file_identity(output / "S.f32")) != saved["original_bank"]["identity"]
        ):
            raise ValueError("exact original retained S custody/work required; no automatic resume")
        saved_new = saved["new_finite"]
        # The original first event is immutable and must never be repeated.
        if Path(config["retained_S_first_progress"]["path"]) != output / "first-S-progress.json":
            raise ValueError("original first S progress path")
        saved_first = json.loads(bound_file_bytes(config["retained_S_first_progress"], 131072))
    else:
        output.mkdir(exist_ok=False)
        marker.write_text("original finite labels not completely published\n")
    facts = {}
    started = time.monotonic()
    attempted_total = (
        saved["already_charged_global"] if saved is not None else boundary["logical_rows_attempted"]
    )
    try:
        with input_pairs(config["input_classes"]) as (inputs, pairs):
            n = len(pairs)
            m = actual_orientation_count(pairs)
            # Actual source/count plan precedes all new model entry.
            if (
                config["actual_orientation_rows"] != m
                or (saved is None and config["inclusive_row_limit"] != 4 * n + 256)
                or not 1 <= m <= 2 * n
            ):
                raise ValueError("actual teacher-row plan differs before model load")
            if saved is not None:
                count = saved["original_oriented_prefix_rows"]
                if (
                    type(count) is not int
                    or not 0 < count <= m
                    or count != saved_new + runtime_coverage["S"]
                ):
                    raise ValueError("actual retained S row count")
                retained_keys = np.frombuffer(bound_file_bytes(saved["keys"], m * 28), dtype="V28")
                retained_values = np.frombuffer(
                    bound_file_bytes(saved["values"], m * 4), dtype="<f4"
                )
                if (
                    len(retained_keys) != count
                    or len(np.unique(retained_keys)) != count
                    or retained_values.shape != retained_keys.shape
                    or not np.isfinite(retained_values).all()
                    or np.any(abs(retained_values) > 1)
                ):
                    raise ValueError("finite same-input retained production prefix")
                previous = {bytes(k): v for k, v in zip(retained_keys, retained_values)}
                if any(
                    k not in previous or previous[k].tobytes() != v.tobytes()
                    for k, v in reuse["S"].items()
                ):
                    raise ValueError("retained prefix changed qualified S values")
                reuse["S"] = previous
            found_by_teacher = {kind: set() for kind in teachers}
            for _, _, chunk in oriented_keys(pairs, config["batch_rows"]):
                for kind in teachers:
                    found_by_teacher[kind].update(
                        bytes(k) for k in chunk if bytes(k) in reuse[kind]
                    )
            if any(found_by_teacher[kind] != set(reuse[kind]) for kind in teachers):
                raise ValueError("teacher runtime key not in exact current unsealed label classes")
            planned_total = attempted_total + sum(
                m - len(found_by_teacher[kind]) for kind in teachers
            )
            if saved is not None:
                retained_repair_limit(
                    config, saved, boundary, planned_total=planned_total, pair_rows=n
                )
            if planned_total > config["inclusive_row_limit"]:
                raise ValueError("inclusive labels plus prior actual boundary exceed plan")
            # Immutable library payload check once before its actual load.
            bound_file_bytes(config["core_library"], 16 * 1024**2)
            bound_file_bytes(config["c20_library"], 16 * 1024**2)
            encoder = StaticInputs(
                config["core_library"]["path"],
                config["c20_library"]["path"],
                batch_rows=config["batch_rows"],
            )
            import torch

            torch.set_num_threads(config["cpu_threads"])
            if torch.get_num_interop_threads() != 1:
                torch.set_num_interop_threads(1)
            for kind in teachers:
                adapter = "sigma" if kind == "S" else "claustrophobia"
                found = found_by_teacher[kind]
                missing = m - len(found)
                capacity = config.get("teacher_batch_rows", {}).get(kind, config["batch_rows"])
                if type(capacity) is not int or not 2 <= capacity <= config["batch_rows"]:
                    raise ValueError("actual bounded teacher batch capacity")
                if scoped and kind == "C" and capacity != boundary["C_batch_rows"]:
                    raise ValueError(
                        "corrected C production must use qualified batch8/endbatch inlet"
                    )
                entry = config["models"][kind]
                expected_identity = boundary["model_identities"][kind]
                if list(IndexedPublicCorpus.identity(Path(entry["path"]).lstat())) != list(
                    expected_identity
                ):
                    raise ValueError("model changed since actual boundary hash/reader")
                target_path = output / (kind + ".f32")
                keeping_S = saved is not None and kind == "S"
                target = np.memmap(
                    target_path, dtype="<f4", mode="r+" if keeping_S else "w+", shape=(n, 2)
                )
                if not keeping_S:
                    target[:] = np.nan
                head = None
                tick = time.monotonic()
                teacher_start = datetime.now(timezone.utc)
                encoder_seconds = assignment_flush_seconds = 0.0
                retained = np.empty(
                    min(16384, missing) + len(found),
                    dtype=[("pair", "<u8"), ("orientation", "u1"), ("reused", "u1")],
                )
                retained_count = 0
                newly_returned = 0
                portion_rows = min(16384, missing)
                first_portion = saved_first if keeping_S else None
                try:
                    if missing:
                        head = StaticHead(
                            adapter,
                            entry["path"],
                            device=config["device"],
                            batch_rows=capacity,
                            max_attempted_rows=missing,
                        )
                    for pair, orientation, chunk in oriented_keys(pairs, capacity):
                        values = np.empty(len(chunk), dtype="<f4")
                        present = np.fromiter(
                            (bytes(k) in reuse[kind] for k in chunk), dtype=bool, count=len(chunk)
                        )
                        for i in np.flatnonzero(present):
                            values[i] = reuse[kind][bytes(chunk[i])]
                        reused_positions = np.flatnonzero(present)
                        if len(reused_positions):
                            if keeping_S and not np.array_equal(
                                target[pair[reused_positions], orientation[reused_positions]],
                                values[reused_positions],
                            ):
                                raise ValueError(
                                    "existing retained S scalar changed; no overwrite/replay"
                                )
                            save_tick = time.monotonic()
                            target[pair[reused_positions], orientation[reused_positions]] = values[
                                reused_positions
                            ]
                            assignment_flush_seconds += time.monotonic() - save_tick
                            if first_portion is None:
                                stop = retained_count + len(reused_positions)
                                retained["pair"][retained_count:stop] = pair[reused_positions]
                                retained["orientation"][retained_count:stop] = orientation[
                                    reused_positions
                                ]
                                retained["reused"][retained_count:stop] = 1
                                retained_count = stop
                        locations = np.flatnonzero(~present)
                        at = 0
                        while at < len(locations):
                            take = min(capacity, len(locations) - at)
                            if first_portion is None:
                                take = min(take, portion_rows - newly_returned)
                            positions = locations[at : at + take]
                            encode_tick = time.monotonic()
                            sigma, c20 = encoder.encode(chunk[positions], include_c20=kind == "C")
                            encoder_seconds += time.monotonic() - encode_tick
                            if attempted_total + len(positions) > config["inclusive_row_limit"]:
                                raise ValueError("inclusive label row budget before dispatch")
                            attempted_total += len(positions)
                            values[positions] = head(sigma if kind == "S" else c20)
                            newly_returned += len(positions)
                            save_tick = time.monotonic()
                            target[pair[positions], orientation[positions]] = values[positions]
                            symmetric = reflected_keys(chunk[positions]) == chunk[positions]
                            target[pair[positions][symmetric], 1] = values[positions][symmetric]
                            if first_portion is None:
                                stop = retained_count + len(positions)
                                retained["pair"][retained_count:stop] = pair[positions]
                                retained["orientation"][retained_count:stop] = orientation[
                                    positions
                                ]
                                retained["reused"][retained_count:stop] = 0
                                retained_count = stop
                            assignment_flush_seconds += time.monotonic() - save_tick
                            at += len(positions)
                            if first_portion is None and newly_returned == portion_rows:
                                save_tick = time.monotonic()
                                target.flush()
                                assignment_flush_seconds += time.monotonic() - save_tick
                                measured = datetime.now(timezone.utc)
                                wall = time.monotonic() - tick
                                retained_path = output / ("first-" + kind + "-indices.bin")
                                retained[:retained_count].tofile(retained_path)
                                first_portion = dict(
                                    status="PARTIAL_RETAINED_NOT_COMPLETE",
                                    teacher=kind,
                                    actual_orientation_rows=m,
                                    new_logical_rows=newly_returned,
                                    retained_new_unique_orientation_inputs=newly_returned,
                                    retained_reused_unique_orientation_inputs=retained_count
                                    - newly_returned,
                                    failed_attempted_rows=0,
                                    remaining_new_rows=missing - newly_returned,
                                    planned_new_rows=missing,
                                    reused_boundary_rows=runtime_coverage[kind],
                                    reused_saved_production_rows=saved_new if keeping_S else 0,
                                    wall_seconds=wall,
                                    new_inputs_per_second=newly_returned / wall,
                                    estimated_remaining_new_seconds=(missing - newly_returned)
                                    * wall
                                    / newly_returned,
                                    started_UTC=teacher_start.isoformat(),
                                    measured_UTC=measured.isoformat(),
                                    started_JST=teacher_start.astimezone(
                                        timezone(timedelta(hours=9))
                                    ).isoformat(),
                                    measured_JST=measured.astimezone(
                                        timezone(timedelta(hours=9))
                                    ).isoformat(),
                                    encoder_seconds=encoder_seconds,
                                    assignment_flush_seconds=assignment_flush_seconds,
                                    head=head.facts(),
                                    head_span_scope="synchronized return span includes H2D/model/D2H/checks; isolated transfer/kernel UNKNOWN",
                                    wall_scope="teacher constructor through assigned bank prefix flush; nested spans not summed",
                                    retained_indices=file_ref(retained_path),
                                    retained_index_dtype=retained.dtype.descr,
                                    retained_index_count=retained_count,
                                    partial_bank=dict(
                                        path=str(target_path),
                                        identity=file_identity(target_path),
                                        shape=[n, 2],
                                        dtype="<f4",
                                        mutable_partial=True,
                                        final_sha256=None,
                                    ),
                                    input_classes=config["input_classes"],
                                    model=entry,
                                    runtime_boundary=config["runtime_boundary"],
                                    execution_binding=config.get("execution_binding"),
                                    device=config["device"],
                                    batch_rows=capacity,
                                    outputs_retained=True,
                                    C_measured=(kind == "C"),
                                    fit_ETA="UNMEASURED until original fit and first normal V",
                                )
                                first_path = output / ("first-" + kind + "-progress.json")
                                write_json(first_path, first_portion)
                                write_json(
                                    output / "progress.json",
                                    dict(
                                        status="PARTIAL",
                                        teachers=facts,
                                        first_retained=first_portion,
                                        inclusive_attempted_rows=attempted_total,
                                    ),
                                )
                                if progress_callback is not None:
                                    try:
                                        progress_callback(file_ref(first_path))
                                    except BaseException as notification_error:
                                        write_json(
                                            output
                                            / ("first-" + kind + "-notification-failure.json"),
                                            dict(
                                                error=error_details(notification_error),
                                                labels_retained=True,
                                                no_replay=True,
                                            ),
                                        )
                        target[pair, orientation] = values
                        # Exact same encoded self-LR input shares its one scalar.
                        canonical = pairs["key"][pair]
                        symmetric = reflected_keys(canonical) == canonical
                        target[pair[symmetric], 1] = values[symmetric]
                    target.flush()
                    ClassObservations(pairs).validate_values(target)
                    if newly_returned != missing:
                        raise ValueError("original finite scalar census incomplete")
                    facts[kind] = dict(
                        values=file_ref(target_path),
                        values_identity=file_identity(target_path),
                        model=entry,
                        head=None if head is None else head.facts(),
                        reused_boundary_rows=runtime_coverage[kind],
                        reused_saved_production_rows=saved_new if keeping_S else 0,
                        new_rows=newly_returned,
                        first_unentered_portion=first_portion,
                        seconds=time.monotonic() - tick,
                    )
                    write_json(
                        output / "progress.json",
                        dict(teachers=facts, inclusive_attempted_rows=attempted_total),
                    )
                except BaseException as primary:
                    partial = dict(
                        status="FAILED_PARTIAL",
                        model=entry,
                        head="UNKNOWN",
                        new_finite_rows=newly_returned,
                        intended_new_rows=missing,
                        already_charged_global_attempted_rows=attempted_total,
                        scalar_file_complete=False,
                    )
                    facts[kind] = partial
                    try:
                        partial["head"] = None if head is None else head.facts()
                    except BaseException as secondary:
                        partial["facts_error"] = error_details(secondary)
                        raise BaseExceptionGroup(
                            "label original and head facts", [primary, secondary]
                        )
                    raise
                finally:
                    propagating = sys.exception()
                    cleanup = []
                    try:
                        target._mmap.close()
                    except BaseException as error:
                        cleanup.append(error)
                    if head is not None:
                        del head
                        if config["device"] == "cuda:0":
                            try:
                                torch.cuda.empty_cache()
                            except BaseException as error:
                                cleanup.append(error)
                    if cleanup:
                        raise BaseExceptionGroup(
                            "label and scalar/head cleanup",
                            ([propagating] if propagating else []) + cleanup,
                        )
                if list(IndexedPublicCorpus.identity(Path(entry["path"]).lstat())) != list(
                    expected_identity
                ):
                    raise ValueError("model changed during full label reader")
            bank = dict(
                schema="quoridor-public-static-teacher-values-v1",
                status="COMPLETE" if teachers == ["S", "C"] else "PARTIAL_S_COMPLETE_C_UNENTERED",
                input_classes=config["input_classes"],
                teachers=facts,
                runtime_boundary=config["runtime_boundary"],
                actual_orientation_rows=m,
                inclusive_attempted_rows=attempted_total,
                inclusive_row_limit=config["inclusive_row_limit"],
                old_outcome_or_rawsearch_teacher=False,
                history_semantics="board-only static STM",
                logical_rows_are_not_physical_heads=True,
                retained_S_prefix=config.get("retained_S_prefix"),
                wall_seconds=time.monotonic() - started,
            )
        # Final input identity and both reader finalizers have now succeeded.
        manifest_path = output / (
            "teacher-values.json" if teachers == ["S", "C"] else "teacher-values.partial.json"
        )
        write_json(manifest_path, bank)
        result = dict(
            manifest=file_ref(manifest_path),
            inclusive_attempted_rows=attempted_total,
            teachers=facts,
        )
        if teachers == ["S", "C"]:
            marker.unlink()  # Full-bank success only; S-only retains INCOMPLETE.
        return result
    except BaseException as primary:
        try:
            write_json(
                output / ("remaining-labels-failure.json" if saved is not None else "failure.json"),
                dict(
                    **error_details(primary),
                    inclusive_attempted_rows=attempted_total,
                    teachers=facts,
                    partial_model_failed_kernel_rows="UNKNOWN; attempted batch already charged once",
                ),
            )
        except BaseException as publication:
            raise BaseExceptionGroup("original label/publication failure", [primary, publication])
        raise


def qualification_plan(orientation_rows, planned_extra_head_rows):
    """Actual input-count arithmetic, fixed before any model constructor."""
    if (
        type(orientation_rows) is not int
        or not 0 < orientation_rows <= 48
        or type(planned_extra_head_rows) is not int
        or planned_extra_head_rows != 0
    ):
        raise ValueError("actualM1..48 and source-proven integer zero extra head rows required")
    names = ("S-oldORT-single", "S-Torch-single", "S-Torch-batch", "C-single", "C-batch")
    return dict(
        routes={name: orientation_rows for name in names},
        planned_extra_head_rows=planned_extra_head_rows,
        total=5 * orientation_rows + planned_extra_head_rows,
        inclusive_max=256,
        shared_unissued_margin=256 - 5 * orientation_rows,
    )


def qualify_values(config):
    """One new five-route boundary; old19 input hashes exclude their replay."""
    import hashlib
    import importlib.util
    from .public_features import reflected_keys

    if config["planned_extra_head_rows"] != 0 or config["max_new_base_states"] != 24:
        raise ValueError("fixed source-proven zero extras and at-most24 new bases")
    intended_devices = runtime_devices(config)
    exclusion = json.loads(bound_file_bytes(config["old_input_exclusions"], 32768))
    if (
        exclusion["encoding"]
        != "SHA256 of canonical STM Sigma8 C-order LE-f32 shape[8,9,9], 2592bytes"
    ):
        raise ValueError("exact saved old Sigma8 input hash encoding required")
    old_hashes = {bytes.fromhex(k) for k in exclusion["sha256"]}
    if len(old_hashes) != 19 or any(len(k) != 32 for k in old_hashes):
        raise ValueError("actual saved old19 opaque input exclusions required")
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("new five-route runtime not complete\n")
    attempted = 0
    route_counts = {}
    head_facts = {}
    routes = {}
    model_identities = {}
    plan = None
    started = time.monotonic()
    try:
        bound_file_bytes(config["core_library"], 16 * 1024**2)
        bound_file_bytes(config["c20_library"], 16 * 1024**2)
        encoder = StaticInputs(
            config["core_library"]["path"], config["c20_library"]["path"], batch_rows=48
        )
        with input_pairs(config["input_classes"]) as (_, pairs):
            selected = []
            skipped = []
            # At most19 old input classes can exclude an early canonical pair;
            # this finite source-only selection cannot become an outcome refill.
            for ordinal in range(min(len(pairs), 24 + 19)):
                key = np.array([pairs["key"][ordinal]], dtype="V28")
                reflected = reflected_keys(key)
                keys = np.unique(np.r_[key, reflected])
                sigma, _ = encoder.encode(keys, include_c20=False)
                hashes = [
                    hashlib.sha256(np.ascontiguousarray(row, dtype="<f4").tobytes()).digest()
                    for row in sigma
                ]
                if any(h in old_hashes for h in hashes):
                    skipped.append(ordinal)
                    continue
                selected.append((ordinal, keys))
                if len(selected) == 24:
                    break
            if not selected:
                raise ValueError("no new unsealed input outside old19; no replacement pool")
            keys = np.concatenate([entry[1] for entry in selected])
            if len(np.unique(keys)) != len(keys):
                raise ValueError("canonical pairs yielded duplicate actual orientation inputs")
            plan = qualification_plan(len(keys), config["planned_extra_head_rows"])
            sigma, c20 = encoder.encode(keys)
            (output / "keys.bin").write_bytes(keys.tobytes())
            write_json(
                output / "before-model-plan.json",
                dict(
                    **plan,
                    input_classes=config["input_classes"],
                    keys=file_ref(output / "keys.bin"),
                    selected_pair_ordinals=[i for i, _ in selected],
                    skipped_old_pair_ordinals=skipped,
                    old_input_exclusions=config["old_input_exclusions"],
                    selected_base_count=len(selected),
                    actual_orientation_rows=len(keys),
                    route_devices_precision=intended_devices,
                    source_counts="constructors/load/eval/to have no explicit model invocation; physical hidden work UNKNOWN",
                    tolerance=dict(atol=1e-6, rtol=1e-6),
                    new_state_rule="first sorted unsealed canonical input pairs excluding saved old19 Sigma8 input hashes",
                ),
            )
        # The source/prospective counts are now on disk before model entry.
        for kind, ref in config["models"].items():
            bound_file_bytes(ref, 64 * 1024**2)
            model_identities[kind] = file_identity(ref["path"])
        source = config["old_sigma_head_source"]
        bound_file_bytes(source, 32768)
        spec = importlib.util.spec_from_file_location(
            "fixed_old_sigma_single_comparator", source["path"]
        )
        old_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old_module)
        import torch

        torch.set_num_threads(config["cpu_threads"])
        if torch.get_num_interop_threads() != 1:
            torch.set_num_interop_threads(1)

        def call(name, head, x):
            nonlocal attempted
            n = len(x)
            if route_counts.get(name, 0) + n > plan["routes"][name] or attempted + n > 256:
                raise ValueError("inclusive actual comparison budget before model call")
            route_counts[name] = route_counts.get(name, 0) + n
            attempted += n
            return head(x)

        def save_route(name, values):
            f = output / (name + ".f32")
            np.asarray(values, dtype="<f4").tofile(f)
            routes[name] = file_ref(f)

        old_head = old_module.SingleHead("sigma", config["models"]["S"]["path"])
        try:
            reference = np.concatenate(
                [call("S-oldORT-single", old_head, sigma[i : i + 1]) for i in range(len(keys))]
            )
            save_route("S-oldORT-single", reference)
        finally:
            propagating = sys.exception()
            try:
                head_facts["S-oldORT"] = old_head.facts()
            except BaseException as secondary:
                head_facts["S-oldORT"] = dict(facts_error=error_details(secondary))
                if propagating is not None:
                    raise BaseExceptionGroup(
                        "old ORT original and head facts", [propagating, secondary]
                    )
                raise
            finally:
                del old_head
        for kind, adapter, x in [("S", "sigma", sigma), ("C", "claustrophobia", c20)]:
            head = StaticHead(
                adapter,
                config["models"][kind]["path"],
                device=config["device"],
                batch_rows=48,
                max_attempted_rows=2 * len(keys),
            )
            single_name = "S-Torch-single" if kind == "S" else "C-single"
            batch_name = "S-Torch-batch" if kind == "S" else "C-batch"
            try:
                single = np.concatenate(
                    [call(single_name, head, x[i : i + 1]) for i in range(len(keys))]
                )
                save_route(single_name, single)
                batch = call(batch_name, head, x)
                save_route(batch_name, batch)
                if not np.allclose(single, batch, atol=1e-6, rtol=1e-6):
                    raise ValueError(
                        kind + " actual single/batch parity mismatch; no threshold tuning or refill"
                    )
                if kind == "S" and (
                    not np.allclose(reference, single, atol=1e-6, rtol=1e-6)
                    or not np.allclose(reference, batch, atol=1e-6, rtol=1e-6)
                ):
                    raise ValueError(
                        "new Sigma runtime differs from fixed oldORT; no automatic repeat"
                    )
            finally:
                propagating = sys.exception()
                secondary = []
                try:
                    head_facts[kind] = head.facts()
                except BaseException as error:
                    head_facts[kind] = dict(facts_error=error_details(error))
                    secondary.append(error)
                del head
                if config["device"] == "cuda:0":
                    try:
                        torch.cuda.empty_cache()
                    except BaseException as error:
                        secondary.append(error)
                if secondary:
                    raise BaseExceptionGroup(
                        "runtime original and head cleanup",
                        ([propagating] if propagating else []) + secondary,
                    )
        if route_counts != plan["routes"] or attempted != plan["total"]:
            raise ValueError("actual complete five-route census differs from pre-entry plan")
        for kind, ref in config["models"].items():
            if list(file_identity(ref["path"])) != list(model_identities[kind]):
                raise ValueError("teacher model identity changed during runtime reader")
        result = dict(
            status="PASS",
            input_classes=config["input_classes"],
            keys=file_ref(output / "keys.bin"),
            models=config["models"],
            model_identities=model_identities,
            core_library=config["core_library"],
            c20_library=config["c20_library"],
            old_sigma_head_source=config["old_sigma_head_source"],
            device=config["device"],
            route_devices_precision=intended_devices,
            cpu_threads=config["cpu_threads"],
            planned_extra_head_rows=0,
            logical_rows_attempted=attempted,
            route_rows_attempted=route_counts,
            heads=head_facts,
            routes=routes,
            batch_values=dict(S=routes["S-Torch-batch"], C=routes["C-batch"]),
            tolerance=dict(atol=1e-6, rtol=1e-6),
            source_input_rows_not_model_rows=True,
            old_success_replays=0,
            physical_heads="UNKNOWN without profiling",
            wall_seconds=time.monotonic() - started,
        )
        write_json(output / "result.json", result)
        returned = dict(result=file_ref(output / "result.json"), actual_logical_rows=attempted)
        marker.unlink()
        return returned
    except BaseException as primary:
        try:
            write_json(
                output / "failure.json",
                dict(
                    **error_details(primary),
                    pre_model_plan=plan,
                    logical_rows_attempted=attempted,
                    route_rows_attempted=route_counts,
                    heads=head_facts,
                    partial_routes=routes,
                    unentered_routes="UNKNOWN, no refill",
                    failed_rows="already charged when attempted; physical execution UNKNOWN",
                ),
            )
        except BaseException as publication:
            raise BaseExceptionGroup("runtime original/publication failure", [primary, publication])
        raise


def cpu_policy_teacher_boundary(config):
    """Admit saved C-only CPU evidence; this does not qualify new policy/masks."""
    references = config["runtime_boundary"]
    required = {
        "result",
        "execution",
        "completion",
        "stage",
        "teachers",
        "head_source",
        "encoder_library",
        "encoder_build",
        "encoder_closure",
    }
    if not isinstance(references, dict) or set(references) != required:
        raise ValueError("explicit original C-only CPU result/return/source/encoder refs")
    if config["device"] != "cpu" or config["cpu_threads"] != 1:
        raise ValueError("saved C CPU boundary cannot qualify a GPU route")
    metadata = {
        name: json.loads(bound_file_bytes(references[name], 1048576))
        for name in required - {"head_source"}
    }
    bound_file_bytes(references["head_source"], 65536)
    try:
        result = metadata["result"]
        execution = metadata["execution"]
        completed = metadata["completion"]
        stage = metadata["stage"]
        record = result["records"]["C"]
        head = result["heads"]["C"]
        returned = execution["returned"]
        teachers = [t for t in metadata["teachers"]["teachers"] if t["key"] == "C"]
        if len(teachers) != 1:
            raise ValueError("one explicit C teacher required")
        teacher = teachers[0]
        rows = record["input_rows"]
        counts = (
            rows,
            record["finite_rows"],
            record["attempted_rows"],
            head["attempted_rows"],
            head["returned_finite_rows"],
            head["failed_attempt_rows"],
            head["constructor_forward_rows"],
            head["explicit_warmup_rows"],
        )
        if (
            any(type(v) is not int or v < 0 for v in counts)
            or rows == 0
            or result["primary"] is not None
            or result["actual_fixed_encoder_boards"] != rows
            or result["constructor_implicit_input_rows"] != 0
            or type(execution["GPU"]) is not int
            or execution["GPU"] != 0
            or not any(
                ref["sha256"] == result["source_input_comparison_sha256"]
                for ref in stage["fixed_small_refs"]
            )
            or set(result["records"]) != {"C"}
            or set(result["heads"]) != {"C"}
            or record["constructor_entered"] is not True
            or record["constructor_returned"] is not True
            or record["single_batch_pass"] is not True
            or record["finite_rows"] != rows
            or record["attempted_rows"] != 2 * rows
            or head["attempted_rows"] != record["attempted_rows"]
            or head["returned_finite_rows"] != head["attempted_rows"]
            or head["failed_attempt_rows"] != 0
            or head["constructor_forward_rows"] != 0
            or head["explicit_warmup_rows"] != 0
            or head["kind"] != "claustrophobia"
            or head["joint_policy_value_compute"] is not True
            or head["label_semantics"] != "raw-local-stm-single-network-post-tanh"
            or head["extra_tanh_sign_discount_rescaling"] is not False
            or head["runtime"]["device"] != "cpu"
            or head["runtime"]["autocast"] is not False
            or head["runtime"]["original_parameter_dtypes"] != ["torch.float32"]
            or head["runtime"]["inference_dtype"] != "float32"
            or record["teacher_model"] != config["model"]
            or teacher["adapter"] != "claustrophobia"
            or teacher["model"] != config["model"]
            or config["model"] not in stage["model_custody"]
            or config["model"] not in execution["runtime"]["model_custody"]
            or execution["status"] != "RETURNED_COMPLETE"
            or execution["primary"] is not None
            or returned["status"] != "complete"
            or returned["exit_code"] != 0
            or returned["primary_error"] is not None
            or returned["remaining"] != []
            or execution["remaining"] != []
            or returned["cleanup_complete"] is not True
            or returned["direct_child_reaped"] is not True
            or returned["handle_closes_complete"] is not True
            or returned["signal_mask_restoration"] != "completed"
            or returned["final_record_persist"] != "completed"
            or returned["finalization_errors"] != []
            or returned["command"] != stage["argv"]
            or stage["finite_plan"]["teachers_selected"] != ["C"]
            or stage["finite_plan"]["fixed_boards"] != rows
            or stage["finite_plan"]["batch_plus_singles_per_teacher"] != 2 * rows
            or references["teachers"] not in stage["fixed_small_refs"]
            or references["head_source"] not in stage["fixed_small_refs"]
            or references["result"] not in completed["refs"]
            or references["execution"] not in completed["refs"]
            or completed["observed"] != result
            or metadata["encoder_library"]["artifact"] != config["c20_library"]
            or metadata["encoder_build"]["closure"] != references["encoder_closure"]
            or metadata["encoder_closure"]["upstream_commit"]
            != teacher["identity"]["release_commit"]
        ):
            raise ValueError("saved C CPU/model/return/source/encoder correspondence")
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("missing or malformed C-only CPU boundary metadata") from error
    identity = config["model_identity"]
    if (
        not isinstance(identity, list)
        or len(identity) != 6
        or any(type(v) is not int for v in identity)
        or identity[3] != config["model"]["bytes"]
        or list(file_identity(config["model"]["path"])) != identity
    ):
        raise ValueError("actual normal input model custody differs")
    # Existing ordered Experiment inputs bind the model's declared FileRef;
    # this exact stat tuple detects lifetime drift, not a new numerical proof.
    return identity


def exclude_joint_source_inputs(config, pairs):
    """Veto old actual input keys; never read, copy or transform old labels."""
    source = config["excluded_joint_source"]
    if isinstance(source, list):
        if len(source) != 2 or any(not isinstance(s, dict) for s in source):
            raise ValueError("exact two named old joint source authorities required")
        if source[0] == source[1]:
            raise ValueError("duplicate old joint authority is not two sources")
        second_config = json.loads(bound_file_bytes(source[1]["configuration"], 64 * 1024))
        if second_config.get("excluded_joint_source") != source[0]:
            raise ValueError("second old joint source does not bind the first named veto")
        # Reuse each unchanged key/provenance guard exactly once, before either constructor.
        reports = [
            exclude_joint_source_inputs({**config, "excluded_joint_source": authority}, pairs)
            for authority in source
        ]
        if (
            reports[1]["prior_actual_rows"] != reports[0]["inclusive_attempted_rows"]
            or config["prior_actual_rows"] != reports[1]["inclusive_attempted_rows"]
        ):
            raise ValueError("named old joint source actual-row chronology differs")
        return {
            "excluded_joint_sources": source,
            "source_reports": reports,
            "old_actual_orientation_rows": sum(r["old_actual_orientation_rows"] for r in reports),
            "current_actual_orientation_rows": reports[0]["current_actual_orientation_rows"],
            "overlapping_actual_input_keys": 0,
            "labels_read_or_copied": 0,
        }
    if not isinstance(source, dict) or set(source) != {
        "input_classes",
        "teacher_values",
        "configuration",
    }:
        raise ValueError("explicit complete old joint source authority required")
    previous = json.loads(bound_file_bytes(source["configuration"], 64 * 1024))
    bank = json.loads(bound_file_bytes(source["teacher_values"], 64 * 1024))
    if (
        set(previous) - {"excluded_joint_source"} != set(config) - {"excluded_joint_source"}
        or previous["input_classes"] != source["input_classes"]
        or bank["schema"] != "quoridor-public-static-teacher-values-v1"
        or bank["status"] != "COMPLETE"
        or bank["input_classes"] != source["input_classes"]
        or (Path(source["teacher_values"]["path"]).parent / "INCOMPLETE").exists()
        or set(bank["teachers"]) != {"C"}
    ):
        raise ValueError("complete joined old input/configuration/joint bank required")
    for name in (
        "runtime_boundary",
        "model",
        "model_identity",
        "core_library",
        "c20_library",
        "device",
        "cpu_threads",
        "temperature",
    ):
        if previous[name] != config[name]:
            raise ValueError("old joint teacher source differs: " + name)
    if (
        config["temperature"] != 1
        or config["device"] != "cpu"
        or config["cpu_threads"] != 1
        or type(previous["temperature"]) not in (int, float)
        or type(previous["cpu_threads"]) is not int
    ):
        raise ValueError("old joint exclusion requires the matching CPU temperature1 teacher")
    entry = bank["teachers"]["C"]
    for name in ("runtime_boundary", "core_library", "c20_library"):
        if bank[name] != previous[name]:
            raise ValueError("old joint bank source differs: " + name)
    if entry["model"] != previous["model"]:
        raise ValueError("old joint bank teacher model differs")
    policy = entry["policy"]
    if set(policy) != {
        "action_order",
        "value_perspective",
        "input_coordinates",
        "orientation_targets",
        "temperature",
        "probabilities",
        "probabilities_identity",
        "legal_mask",
        "legal_mask_identity",
    } or any(
        policy[name] != value
        for name, value in (
            ("action_order", "absolute-core-action-id209"),
            ("value_perspective", "side-to-move"),
            ("input_coordinates", "canonical-public-STM0-native-C20"),
            ("orientation_targets", "independent same-forward actual input orientations"),
            ("temperature", 1),
        )
    ):
        raise ValueError("old joint raw STM/legal209/orientation/temperature source required")
    import stat

    for name in ("probabilities", "legal_mask"):
        payload = policy[name]
        identity = policy[name + "_identity"]
        if (
            not isinstance(payload, dict)
            or set(payload) != {"path", "sha256", "bytes", "mode"}
            or not isinstance(payload["path"], str)
            or "\x00" in payload["path"]
            or not Path(payload["path"]).is_absolute()
            or not isinstance(payload["sha256"], str)
            or len(payload["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in payload["sha256"])
            or type(payload["bytes"]) is not int
            or payload["bytes"] <= 0
            or not isinstance(payload["mode"], str)
            or not isinstance(identity, (list, tuple))
            or len(identity) != 6
            or any(type(value) is not int for value in identity)
            or identity[0] < 0
            or identity[1] <= 0
            or not stat.S_ISREG(identity[2])
            or identity[2] != stat.S_IFREG | stat.S_IMODE(identity[2])
            or payload["bytes"] != identity[3]
            or payload["mode"] != f"{stat.S_IMODE(identity[2]):04o}"
        ):
            raise ValueError("old joint policy payload FileRef/identity metadata differs")
    head = entry["head"]
    if (
        head["device"] != "cpu"
        or head["fp32"] is not True
        or head["autocast"] is not False
        or head["tf32"] is not False
        or head["value"] != "raw-local-stm-single-network-post-tanh"
        or type(head["failed_attempted_rows"]) is not int
        or head["failed_attempted_rows"] != 0
        or type(head["constructor_model_calls"]) is not int
        or head["constructor_model_calls"] != 0
    ):
        raise ValueError("old joint completed CPU FP32 head source required")
    with input_pairs(source["input_classes"]) as (_, old_pairs):
        blocked = set()
        old_rows = 0
        for _, _, keys in oriented_keys(old_pairs, config["batch_rows"]):
            old_rows += len(keys)
            blocked.update(bytes(key) for key in keys)
        for value in (
            bank["actual_orientation_rows"],
            head["logical_rows_attempted"],
            head["finite_rows_returned"],
        ):
            if type(value) is not int or value != old_rows:
                raise ValueError("old joint actual orientation census differs")
        prior = bank["prior_actual_rows"]
        inclusive = bank["inclusive_attempted_rows"]
        if (
            old_rows == 0
            or len(blocked) != old_rows
            or type(prior) is not int
            or prior < 0
            or type(inclusive) is not int
            or inclusive != prior + old_rows
            or type(previous["prior_actual_rows"]) is not int
            or previous["prior_actual_rows"] != prior
            or type(previous["inclusive_row_limit"]) is not int
            or inclusive > previous["inclusive_row_limit"]
        ):
            raise ValueError("old joint incomplete or inconsistent actual row accounting")
        current_rows = 0
        for _, _, keys in oriented_keys(pairs, config["batch_rows"]):
            current_rows += len(keys)
            if any(bytes(key) in blocked for key in keys):
                raise ValueError("old joint input eligibility collision; no teacher constructor")
    return dict(
        excluded_joint_source=source,
        old_actual_orientation_rows=old_rows,
        prior_actual_rows=prior,
        inclusive_attempted_rows=inclusive,
        current_actual_orientation_rows=current_rows,
        overlapping_actual_input_keys=0,
        labels_read_or_copied=0,
    )


def label_policy_values(config):
    """Chunk the existing C joint head into its two actual orientation targets.

    Old scalar labels cannot supply missing policy. No replay of old label runs:
    this is an explicitly selected NEW joint bank over bound unsealed inputs.
    """
    import math

    required = {
        "input_classes",
        "runtime_boundary",
        "model",
        "model_identity",
        "core_library",
        "c20_library",
        "output",
        "batch_rows",
        "device",
        "cpu_threads",
        "temperature",
        "prior_actual_rows",
        "inclusive_row_limit",
    }
    if set(config) not in (required, required | {"excluded_joint_source"}):
        raise ValueError("explicit bounded joint teacher configuration")
    temperature = config["temperature"]
    if (
        type(temperature) not in (int, float)
        or not math.isfinite(temperature)
        or temperature <= 0
        or config["cpu_threads"] != 1
        or type(config["batch_rows"]) is not int
        or not 2 <= config["batch_rows"] <= 4096
        or config["device"] not in ("cpu", "cuda:0")
        or type(config["prior_actual_rows"]) is not int
        or config["prior_actual_rows"] < 0
        or type(config["inclusive_row_limit"]) is not int
        or config["inclusive_row_limit"] <= 0
    ):
        raise ValueError("joint temperature/thread/actual inclusive row controls")
    expected_identity = cpu_policy_teacher_boundary(config)
    for name in ("core_library", "c20_library"):
        bound_file_bytes(config[name], 16 * 1024**2)
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("joint same-forward teacher bank not published\n")
    maps, head = {}, None
    started = time.monotonic()
    try:
        with input_pairs(config["input_classes"]) as (inputs, pairs):
            if "excluded_joint_source" in config:
                exclusion = exclude_joint_source_inputs(config, pairs)
                write_json(output / "old-input-exclusion.json", exclusion)
            n = len(pairs)
            expected_rows = actual_orientation_count(pairs)
            if config["prior_actual_rows"] + expected_rows > config["inclusive_row_limit"]:
                raise ValueError("joint target plan exceeds remaining actual teacher rows")
            encoder = StaticInputs(
                config["core_library"]["path"],
                config["c20_library"]["path"],
                batch_rows=config["batch_rows"],
            )
            import torch

            torch.set_num_threads(1)
            if torch.get_num_interop_threads() != 1:
                torch.set_num_interop_threads(1)
            for name, dtype, shape in (
                ("values", "<f4", (n, 2)),
                ("policy", "<f4", (n, 2, 209)),
                ("legal_mask", "u1", (n, 2, 209)),
            ):
                maps[name] = np.memmap(
                    output / (name + ".bin"), dtype=dtype, mode="w+", shape=shape
                )
                maps[name][:] = 0 if name == "legal_mask" else np.nan
            head = StaticHead(
                "claustrophobia",
                config["model"]["path"],
                device=config["device"],
                batch_rows=config["batch_rows"],
                max_attempted_rows=config["inclusive_row_limit"] - config["prior_actual_rows"],
            )
            for pair, orientation, keys in oriented_keys(pairs, config["batch_rows"]):
                # Canonical public keys use STM=0. The pinned C20 and original
                # C policy209 use this same action order; no rotation is guessed.
                mask = encoder.policy_mask(keys)
                _, c20 = encoder.encode(keys)
                logits, value = head.policy_value(c20)  # one actual joint call
                legal = np.where(mask, logits.astype(np.float64), -np.inf)
                shifted = legal - np.max(legal, axis=1, keepdims=True)
                with np.errstate(over="ignore", under="ignore"):
                    probability = np.exp(shifted / temperature)
                probability /= probability.sum(axis=1, keepdims=True)
                probability = probability.astype("<f4")
                if (
                    not np.isfinite(probability).all()
                    or np.any(probability < 0)
                    or np.any(probability[~mask] != 0)
                    or not np.allclose(probability.sum(axis=1), 1, atol=1e-6, rtol=0)
                ):
                    raise ValueError("finite legal normalized full teacher distribution")
                maps["values"][pair, orientation] = value
                maps["policy"][pair, orientation] = probability
                maps["legal_mask"][pair, orientation] = mask
                symmetric = reflected_keys(keys) == keys
                # Self-LR SAME input shares the SAME actual output, not an
                # assumed network equivariance or a reflected argmax target.
                for name in maps:
                    maps[name][pair[symmetric], 1] = maps[name][
                        pair[symmetric], orientation[symmetric]
                    ]
            if head.facts()["finite_rows_returned"] != expected_rows:
                raise ValueError("original joint orientation census incomplete")
            ClassObservations(pairs).validate_values(maps["values"])
            for value in maps.values():
                value.flush()
            entry = dict(
                values=file_ref(output / "values.bin"),
                values_identity=file_identity(output / "values.bin"),
                model=config["model"],
                head=head.facts(),
                policy=dict(
                    action_order="absolute-core-action-id209",
                    value_perspective="side-to-move",
                    input_coordinates="canonical-public-STM0-native-C20",
                    orientation_targets="independent same-forward actual input orientations",
                    temperature=temperature,
                    probabilities=file_ref(output / "policy.bin"),
                    probabilities_identity=file_identity(output / "policy.bin"),
                    legal_mask=file_ref(output / "legal_mask.bin"),
                    legal_mask_identity=file_identity(output / "legal_mask.bin"),
                ),
            )
            bank = dict(
                schema="quoridor-public-static-teacher-values-v1",
                status="COMPLETE",
                input_classes=config["input_classes"],
                teachers={"C": entry},
                runtime_boundary=config["runtime_boundary"],
                core_library=config["core_library"],
                c20_library=config["c20_library"],
                actual_orientation_rows=expected_rows,
                prior_actual_rows=config["prior_actual_rows"],
                inclusive_attempted_rows=config["prior_actual_rows"] + head.attempted,
                history_semantics="board-only static STM; histories/WDL UNKNOWN",
                wall_seconds=time.monotonic() - started,
            )
            if list(file_identity(config["model"]["path"])) != list(expected_identity):
                raise ValueError("teacher model changed during joint reader")
        # Close every mapped target before publication; marker stays on failure.
        failures = []
        for value in maps.values():
            try:
                value._mmap.close()
            except BaseException as error:
                failures.append(error)
        maps.clear()
        if failures:
            raise BaseExceptionGroup("joint target final close", failures)
        write_json(output / "teacher-values.json", bank)
        write_json(
            output / "cache.json",
            dict(
                schema="quoridor-public-static-teacher-v1",
                input_classes=config["input_classes"],
                teacher_values=file_ref(output / "teacher-values.json"),
                teacher="C",
            ),
        )
        marker.unlink()
        return dict(
            cache=file_ref(output / "cache.json"),
            bank=file_ref(output / "teacher-values.json"),
            head=bank["teachers"]["C"]["head"],
        )
    except BaseException as error:
        try:
            write_json(
                output / "failure.json",
                dict(
                    primary=error_details(error),
                    head=None if head is None else head.facts(),
                    prior_actual_rows=config["prior_actual_rows"],
                    rows_execution_when_pending="UNKNOWN; no refill/retry",
                ),
            )
        except BaseException as publication:
            raise BaseExceptionGroup("joint teacher primary/publication", [error, publication])
        raise
    finally:
        failures = []
        for value in maps.values():
            try:
                value._mmap.close()
            except BaseException as error:
                failures.append(error)
        if failures:
            propagating = sys.exception()
            raise BaseExceptionGroup(
                "joint teacher primary/cleanup",
                ([propagating] if propagating is not None else []) + failures,
            )


def _selection_identity_rows(authority):
    """Bound identity-only V-first16 authority, never select from values/results."""
    rows = authority["rows"]
    if not isinstance(rows, list) or len(rows) != 16:
        raise ValueError("exact FIRST16 validation components required")
    seen, ranks = set(), []
    for i, row in enumerate(rows):
        if (
            type(row["validationOrdinal0"]) is not int
            or row["validationOrdinal0"] != i
            or type(row["nativeRank0"]) is not int
            or type(row["split"]) is not int
            or row["split"] != 1
            or row["selfLR"] is not False
            or type(row["pairIndex"]) is not int
            or not 0 <= row["pairIndex"] < authority["shape"]["values"][0]
            or row["originalMultiplicity"] != 1
            or row["component"] in seen
            or len(row["views"]) != 2
        ):
            raise ValueError("V wholecomponent/order/multiplicity authority differs")
        seen.add(row["component"])
        ranks.append(row["nativeRank0"])
        keys = [row["originalKey"], row["trueLRKey"]]
        if any(len(bytes.fromhex(key)) != 28 for key in keys) or keys[0] == keys[1]:
            raise ValueError("two distinct exact native input keys required")
        if row["canonicalKey"] != min(keys):
            raise ValueError("saved canonical/native key correspondence")
        for j, view in enumerate(row["views"]):
            orientation = view["bankOrientation"]
            flat = 2 * row["pairIndex"] + orientation
            if (
                view["view"] != ("original", "trueLR")[j]
                or type(orientation) is not int
                or orientation not in (0, 1)
                or (orientation == 0) != (keys[j] == row["canonicalKey"])
                or view["orientedRow0"] != flat
                or view["valueByteOffset"] != 4 * flat
                or view["policyByteOffset"] != 4 * 209 * flat
                or view["maskByteOffset"] != 209 * flat
            ):
                raise ValueError("saved bank orientation/row-offset authority differs")
    if ranks != sorted(set(ranks)) or len({r["pairIndex"] for r in rows}) != 16:
        raise ValueError("native rank/pair identity order differs")
    return rows


def _selection_frame_join(authority, views):
    """Compare native observations to saved identities; no coordinate inference."""
    rows = _selection_identity_rows(authority)
    if not isinstance(views, list) or len(views) != 32:
        raise ValueError("exact32 actual native input views")
    joined = []
    for i, row in enumerate(rows):
        for j, expected in enumerate((row["originalKey"], row["trueLRKey"])):
            view = views[2 * i + j]
            if (
                view["key"] != expected
                or type(view["side"]) is not int
                or view["side"] not in (0, 1)
                or len(view["action_to_key"]) != 209
                or any(type(a) is not int for a in view["action_to_key"])
                or sorted(view["action_to_key"]) != list(range(209))
                or len(view["legal_in_key"]) != 209
                or any(type(a) is not int or a not in (0, 1) for a in view["legal_in_key"])
                or not any(view["legal_in_key"])
            ):
                raise ValueError("actual native STM/key/action frame mismatch")
            joined.append((row, row["views"][j], view))
    return joined


def _selection_native_parents(authority, library):
    from .static_teacher_inputs import native_prefix_views

    rows = _selection_identity_rows(authority)
    # Maintained input manifest is T/V only. Generic JSON transiently parses all
    # source receipts; only these16 histories are used; H source is never opened.
    source = json.loads(bound_file_bytes(authority["inputManifest"], 2 * 1024**2))
    if source["status"] != "COMPLETE" or source["schema"] != (
        "quoridor-public-static-input-classes-v1"
    ):
        raise ValueError("complete adopted T/V source authority required")
    histories = []
    for row in rows:
        parts = row["sourceReceiptPointer"].split("/")
        if len(parts) != 3 or parts[1] != "source_receipts":
            raise ValueError("exact source receipt pointer required")
        receipt = source["source_receipts"][int(parts[2])]
        if (
            receipt["functional_split"] != "V"
            or receipt["family"] != row["publisherSourceSeriesOrdinal"]
            or receipt["fixture"] != int(parts[2])
            or row["fullHistoryByrefPointer"] != row["sourceReceiptPointer"] + "/history"
            or receipt["original_key"] != row["originalKey"]
            or receipt["reflected_key"] != row["trueLRKey"]
            or receipt["canonical_key"] != row["canonicalKey"]
        ):
            raise ValueError("source receipt/key/validation lineage mismatch")
        histories.append(receipt["history"])
    views = native_prefix_views(histories, library)
    _selection_frame_join(authority, views)
    return views


def selection_parents(config):
    """Publish a normal compare Book from native actual original/trueLR contexts."""
    authority = json.loads(bound_file_bytes(config["row_authority"], 65536))
    bound_file_bytes(config["core_library"], 16 * 1024**2)
    views = _selection_native_parents(authority, config["core_library"]["path"])
    openings = []
    for i, (row, saved_view, actual) in enumerate(_selection_frame_join(authority, views)):
        openings.append(
            dict(
                id=f"selection-v16-view-{i:02}",
                cohort="tactical_diagnostic",
                lineage=row["component"],
                siblings=[],
                original_seed=None,
                reference=dict(
                    source_sha256=config["row_authority"]["sha256"],
                    model_sha256=None,
                    settings=dict(
                        family_id=i,
                        component=row["component"],
                        member=row["member"],
                        view=saved_view["view"],
                        actual_native_stm=actual["side"],
                    ),
                    q_definition=None,
                    q_perspective=None,
                    q_aggregation=None,
                    q=None,
                ),
                selection_reason="fixed FIRST16 exposed selectionV original/trueLR, no outcomes",
                candidate_pool_size=16,
                prefix=actual["prefix"],
            )
        )
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    book = output / "book.json"
    write_json(
        book,
        dict(
            id="selection-v16-original-trueLR32",
            usage="functional",
            frozen_before_candidate_results=True,
            independence="16 correlated EXPOSED selectionV components; not IID/holdout",
            openings=openings,
        ),
    )
    result = dict(
        status="COMPLETE",
        row_authority=config["row_authority"],
        core_library=config["core_library"],
        book=file_ref(book),
        components=16,
        views=32,
        new_teacher_forward=0,
        new_joint_forward=0,
        Search=0,
        games=0,
        transient_manifest_scope="whole adopted T/V source-receipts JSON parsed;16 V histories used",
        H_source_opened=False,
    )
    write_json(output / "receipt.json", result)
    return result


def _selection_decision_join(report, configuration, book, views):
    """Join sole normal decisions producer, never call Search or accept a late move."""
    if (
        report["schema"] != "quoridor-decisions-v1"
        or report["run_id"] != configuration["run_id"]
        or report["planned"] != 32
        or len(report["outcomes"]) != 32
        or report["stopped"] is not None
        or report["all_workers_joined"] is not True
        or report["rows"] != 0
        or report["dataset"] is not None
        or report["score"] is not None
        or configuration["games"] != 32
        or configuration["arena"]["decision_only"] is not True
        or configuration["arena"].get("game_selection") is not None
        or configuration["arena"]["comparison"] != "whole_wall_time"
        or configuration["arena"]["clock_policy"] != "strict_unknown"
        or configuration["arena"]["return_reserve_ms"] != 5
        or configuration["ruleset"] != "standard_2p_threefold"
        or configuration["arena"]["book"] != book
        or len(configuration["engines"]) != 1
    ):
        raise ValueError("sole normal decisions/book/no-game census mismatch")
    outcomes = sorted(report["outcomes"], key=lambda row: row["game"])
    observations = []
    for i, outcome in enumerate(outcomes):
        if (
            outcome["game"] != i
            or outcome["family"] != f"{report['run_id']}-family-{i:06}"
            or outcome["moves"] != views[i]["prefix"]
            or outcome["winner"] is not None
            or outcome["status"] != "decision"
            or outcome["failure"] is not None
            or len(outcome["observations"]) != 1
        ):
            raise ValueError("missing/unknown/changed parent; remaining diagnostic rows UNRUN")
        observation = outcome["observations"][0]
        action = observation["action"]
        counters = observation["counters"]
        receipt = counters.get("authority_receipt_ns")
        deadline = observation["deadline_ns"]
        if (
            observation["accepted"] is not True
            or observation["failure"] is not None
            or observation["engine_error"] is not None
            or observation["side"] != views[i]["side"]
            or observation["engine_index"] != 0
            or type(action) is not int
            or not 0 <= action < 209
            or not views[i]["legal_in_key"][views[i]["action_to_key"][action]]
            or type(receipt) is not int
            or type(deadline) is not int
            or deadline - observation["caller_started_ns"] != 100_000_000
            or receipt >= deadline
            or counters.get("inflight_after_drain") != 0
            or counters.get("drain_finished_ns") != observation["returned_ns"]
        ):
            raise ValueError("actual native action/frame/authority receipt mismatch")
        observations.append(observation)
    return observations


def _selection_producer(source, book_ref):
    """Join the normal finalizer's sole producer byrefs; never open its journal."""
    completion = json.loads(bound_file_bytes(source["completion"], 2 * 1024**2))
    if (
        completion["schema"] != "quoridor.research.completion.v1"
        or completion["kind"] != "run"
        or completion["status"] != "PASS"
        or completion["primary"] is not None
        or completion["secondary"]
        or completion["cleanup_complete"] is not True
        or completion["remaining"] != []
        or Path(source["completion"]["path"]).with_name("INCOMPLETE").exists()
    ):
        raise ValueError("settled sole normal decisions completion required")
    experiment = json.loads(bound_file_bytes(completion["experiment"], 2 * 1024**2))
    origin = json.loads(bound_file_bytes(completion["intent"], 2 * 1024**2))
    plan_ref = origin["approved_plan"]
    plan = json.loads(bound_file_bytes(plan_ref, 2 * 1024**2))
    inventory = {ref["path"]: ref for ref in completion["data"]["files"]}
    if (
        len(inventory) != len(completion["data"]["files"])
        or inventory.get(source["report"]["path"]) != source["report"]
        or experiment["config"] != source["configuration"]
        or experiment["phase"] != "compare"
        or experiment["canonical_plan_sha256"] != plan_ref["sha256"]
        or origin["experiment"] != completion["experiment"]
        or plan["phase"] != "compare"
        or plan["book"] != book_ref
    ):
        raise ValueError("normal producer/config/Plan/book/result identity mismatch")
    # The maintained normal entry already owns full Plan/engine/clock validation.
    # This is a byref join, not a substitute normal finalizer or journal qualifier.
    return completion


def selection_diagnostic(config):
    """Saved bank + two normal decisions + one current joint batch; no Search/teacher."""
    from .static_public_corpus import StaticTeacherCorpus
    from .policy_value_training import native_identity, policy_diagnostics
    from .residual_model import DistanceResidualModel, load_policy_head
    from .scaled_model import validate_statistics
    from .train import restore_warmstart_parameters
    import torch

    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("selection diagnostic incomplete; no replacement/retry\n")
    corpus = None
    work = dict(joint_attempted_rows=0, joint_completed_rows=0, new_teacher_rows=0, Search=0)
    result = dict(status="INCOMPLETE", rows=[], work=work, remaining_rows=32)
    started = time.monotonic()
    primary = close_error = None
    try:
        try:
            authority = json.loads(bound_file_bytes(config["row_authority"], 65536))
            parent = json.loads(bound_file_bytes(config["parents_receipt"], 65536))
            if (
                parent["status"] != "COMPLETE"
                or parent["row_authority"] != config["row_authority"]
                or parent["core_library"] != config["core_library"]
                or parent["book"] != config["book"]
            ):
                raise ValueError("native parent producer correspondence differs")
            book = json.loads(bound_file_bytes(config["book"], 262144))
            if len(book["openings"]) != 32:
                raise ValueError("exact32 normal diagnostic parents")
            # Actual native authority is rechecked for the saved normal book, with
            # no teacher/model forward. It does not decode any H or other source.
            from .static_teacher_inputs import native_prefix_views

            bound_file_bytes(config["core_library"], 16 * 1024**2)
            views = native_prefix_views(
                [book["openings"][i]["prefix"] for i in range(0, 32, 2)],
                config["core_library"]["path"],
            )
            joined = _selection_frame_join(authority, views)
            if any(b["prefix"] != v["prefix"] for b, v in zip(book["openings"], views)):
                raise ValueError("normal book original/trueLR chronology differs")
            decisions = {}
            for name in ("selected_alpha", "cedar_alpha"):
                source = config["decisions"][name]
                _selection_producer(source, config["book"])
                cfg = json.loads(bound_file_bytes(source["configuration"], 524288))
                report = json.loads(bound_file_bytes(source["report"], 4 * 1024**2))
                if Path(source["report"]["path"]) != Path(cfg["output"]) / "result.json":
                    raise ValueError("decision result path differs from normal producer")
                if cfg["arena"]["evaluator_sha256"] != [source["evaluator_sha256"]]:
                    raise ValueError("decision evaluator identity differs from normal binding")
                if cfg["engines"][0]["model"] != source["descriptor"]["path"]:
                    raise ValueError("decision value descriptor differs from normal binding")
                decisions[name] = _selection_decision_join(report, cfg, book, views)
            current = config["current"]
            if config["decisions"]["selected_alpha"]["descriptor"] != current["descriptor"]:
                raise ValueError("joint/current Alpha value descriptor differs")
            # Do not rehash the bank arrays. Existing reader retains its normal
            # SAME-input, six-field custody, COMPLETE, finite/shape admission.
            cache = authority["cache"]
            directory = Path(cache["path"]).parent
            if config["cache_directory"] != str(directory):
                raise ValueError("adopted cache DIRECTORY required, not cache.json")
            bound_file_bytes(cache, 65536)
            corpus = StaticTeacherCorpus(directory)
            if (
                corpus.input_ref != authority["inputManifest"]
                or corpus.manifest["teacher_values"] != authority["teacherBank"]
                or not corpus.policy_value
                or corpus.policy_temperature != 1
            ):
                raise ValueError("same adopted rawSTM/temp1 joint bank required")
            pair, orientation = [], []
            for row, saved_view, view in joined:
                index = row["pairIndex"]
                if (
                    bytes(corpus.pairs["key"][index]).hex() != row["canonicalKey"]
                    or int(corpus.pairs["split"][index]) != 1
                ):
                    raise ValueError("V-only sorted pair/row correspondence differs")
                pair.append(index)
                orientation.append(saved_view["bankOrientation"])
            pair, orientation = np.array(pair), np.array(orientation)
            target, legal = corpus.policy_targets(pair, orientation)
            z = np.asarray(corpus.values[pair, orientation]).copy()
            if not np.array_equal(
                legal, np.asarray([v["legal_in_key"] for v in views], dtype=bool)
            ):
                raise ValueError("teacher/native actual public-frame legal masks differ")
            descriptor = json.loads(bound_file_bytes(current["descriptor"], 65536))
            if (
                descriptor["schema"] != "quoridor-nnue-distance-residual-v3"
                or descriptor["feature"] != "QF1-route4-f32-STM-scaled-residual-v3"
                or descriptor["topology"] != {"ft_width": 32, "hidden_width": 32}
                or descriptor["route_mode"] != "zero4"
                or descriptor["distance_fit"] != {"a": 0, "b": 0}
                or descriptor["value_perspective"] != "side-to-move"
                or descriptor["weights_SHA"] != current["weights"]["sha256"]
                or descriptor["weights_B"] != 49284
                or (Path(current["descriptor"]["path"]).parent / descriptor["weights"]).resolve()
                != Path(current["weights"]["path"]).resolve()
            ):
                raise ValueError("same current joint FP32 value descriptor required")
            identity_start = time.monotonic()
            identity = native_identity(
                config["core_library"]["path"],
                current["descriptor"]["path"],
                current["policy"]["path"],
            )
            work["native_identity_seconds"] = time.monotonic() - identity_start
            work["native_identity_pair_calls"] = 1
            work["native_value_loads"] = 1
            work["native_policy_loads"] = 1
            work["native_identity_forward_rows"] = 0
            if identity != {"shared": current["shared"], "policy": current["policy_fingerprint"]}:
                raise ValueError("current native shared/policy identity differs")
            bound_file_bytes(current["policy"], 65536)
            torch.set_num_threads(1)
            if torch.get_num_interop_threads() != 1:
                torch.set_num_interop_threads(1)
            init_start = time.monotonic()
            model = DistanceResidualModel(
                {"transformer_width": 32, "hidden_width": 32, "dropout": 0},
                validate_statistics(descriptor),
                a=0,
                b=0,
            )
            restore_warmstart_parameters(model, current["weights"])
            load_policy_head(
                model, current["policy"]["path"], shared_fingerprint=identity["shared"]
            )
            model.eval()
            work["python_joint_constructors"] = 1
            setup_seconds = time.monotonic() - init_start
            x = torch.tensor([v["qf1"] for v in views], dtype=torch.float32).reshape(32, 2, 312)
            distance = torch.tensor([v["distance"] for v in views], dtype=torch.float32)
            side = torch.tensor([v["side"] + 1 for v in views], dtype=torch.long)
            permutation = torch.tensor([v["action_to_key"] for v in views], dtype=torch.long)
            forward_start = time.monotonic()
            work["joint_attempted_rows"] = 32
            work["joint_forward_calls"] = 1
            with torch.inference_mode():
                value, absolute_logits = model.forward_policy_value(x, distance, side)
                work["joint_forward_seconds"] = time.monotonic() - forward_start
                metrics_start = time.monotonic()
                if not torch.isfinite(value).all() or not torch.isfinite(absolute_logits).all():
                    raise ValueError("current actual-view joint output nonfinite")
                work["joint_completed_rows"] = 32
                # Scatter by the observed native bijection, not a Python geometry rule.
                logits = torch.empty_like(absolute_logits).scatter_(1, permutation, absolute_logits)
                queries = {
                    name: [v["action_to_key"][o["action"]] for v, o in zip(views, observations)]
                    for name, observations in decisions.items()
                }
                metrics = policy_diagnostics(
                    logits,
                    torch.from_numpy(target),
                    torch.from_numpy(legal),
                    torch.ones(32),
                    action_queries=queries,
                )
            work["query_metrics_seconds"] = time.monotonic() - metrics_start
            for i, (row, saved_view, view) in enumerate(joined):
                record = dict(
                    group=i // 2,
                    component=row["component"],
                    view=saved_view["view"],
                    actual_native_stm=view["side"],
                    current_raw_stm_posttanh=float(value[i]),
                    saved_teacher_raw_stm_posttanh=float(z[i]),
                    **metrics["selection_rows"][i],
                    normal_decisions={},
                )
                for name, observations in decisions.items():
                    o = observations[i]
                    record["normal_decisions"][name] = {
                        k: o.get(k)
                        for k in (
                            "action",
                            "accepted",
                            "failure",
                            "stop",
                            "completed_depth",
                            "value_stm",
                            "caller_started_ns",
                            "deadline_ns",
                            "returned_ns",
                            "admission_checked_ns",
                            "accepted_ns",
                            "caller_seconds",
                            "thinking_seconds",
                            "last_completed_iteration_ns",
                            "completed_iteration_counters",
                            "counters",
                        )
                    }
                result["rows"].append(record)
            corpus.verify_binding()
            result.update(
                components=16,
                current_identity=identity,
                joint_setup_seconds=setup_seconds,
                decisions_byref=config["decisions"],
                row_authority=config["row_authority"],
                book=config["book"],
                reader_scope=dict(
                    adopted_bank_openings=1,
                    transient_TV_maps_and_validation_rows=len(corpus.pairs) * 2,
                    scientific_V_rows=32,
                    scientific_T_rows=0,
                    H_source_or_labels_opened=False,
                ),
                units="raw STM posttanh values; Alpha value_stm is LEGACY search score, not a label",
                frame="actual joint view -> native Sigma public-key frame; no learned LR invariance",
                condition="EXPOSED selectionV descriptive queries, no causal/strength/calibration claim",
            )
            del model
        finally:
            primary = sys.exception()
            failures = []
            if corpus is not None:
                for close in (corpus.verify_binding, corpus.close):
                    try:
                        close()
                    except BaseException as error:
                        failures.append(error)
            if failures:
                close_error = BaseExceptionGroup(
                    "selection diagnostic original/custody/close failures",
                    ([primary] if primary else []) + failures,
                )
                result["close_error"] = error_details(close_error)
                raise close_error
        # Required custody/close calls have settled before success publication.
        result["remaining_rows"] = 32 - len(result["rows"])
        result["wall_seconds"] = time.monotonic() - started
        result["status"] = "COMPLETE"
        write_json(output / "result.json", result)
        marker.unlink()
        return dict(result=file_ref(output / "result.json"), status=result["status"])
    except BaseException as error:
        result["status"] = "INCOMPLETE"
        result["remaining_rows"] = 32 - len(result["rows"])
        # Also covers cancellation during cleanup or after provisional success.
        # Preserve an interrupted pending primary/close group, not just its context.
        original = close_error if close_error is not None else primary
        if original is not None and error is not original:
            error = BaseExceptionGroup(
                "selection diagnostic pending failure and interruption", [original, error]
            )
        result["error"] = error_details(error)
        result["wall_seconds"] = time.monotonic() - started
        try:
            # A failure after unlink/file_ref must restore the refusal marker.
            marker.write_text("selection diagnostic incomplete; original error retained\n")
            write_json(output / "result.json", result)
        except BaseException as publication_error:
            raise BaseExceptionGroup(
                "selection diagnostic original and failure-publication errors",
                [error, publication_error],
            ) from None
        raise error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=("qualify", "labels", "policy-values", "selection-parents", "selection-diagnostic"),
    )
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    from quoridor_runtime.cycle_process import cancellation_signals

    with cancellation_signals():
        config = json.loads(Path(args.config).read_bytes())
        result = {
            "qualify": qualify_values,
            "labels": label_values,
            "policy-values": label_policy_values,
            "selection-parents": selection_parents,
            "selection-diagnostic": selection_diagnostic,
        }[args.mode](config)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
