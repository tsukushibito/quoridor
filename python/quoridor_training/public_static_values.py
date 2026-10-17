"""Finite static-label streaming into the normal public compact scalarbank.

Existing native encoders and StaticHead own all model and feature mathematics.
No Search/MCTS, sampler, scheduler, teacher selection, replay or restart system.
"""

import argparse
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
from .snapshot import write_json
from .static_public import PAIR, ClassObservations
from .static_teacher_heads import StaticHead
from .static_teacher_inputs import StaticInputs


@contextmanager
def input_pairs(ref):
    manifest = json.loads(bound_file_bytes(ref, 131072))
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


def label_values(config):
    """One fresh original stream; failure retains partials, never automatically resumes."""
    # Real boundary success, same actual inputs/models/libraries and runtime
    # must already be bound. A submitted job or source clear is not that result.
    intended_devices = runtime_devices(config)
    boundary = json.loads(bound_file_bytes(config["runtime_boundary"], 131072))
    if (
        boundary["status"] != "PASS"
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
    keys = np.frombuffer(bound_file_bytes(boundary["keys"], 48 * 28), dtype="V28")
    if not 0 < len(keys) <= 48 or len(np.unique(keys)) != len(keys):
        raise ValueError("bounded actual unique runtime orientation keys")
    reuse = {}
    for kind in ("S", "C"):
        values = np.frombuffer(
            bound_file_bytes(boundary["batch_values"][kind], 48 * 4), dtype="<f4"
        )
        if values.shape != keys.shape or not np.isfinite(values).all() or np.any(abs(values) > 1):
            raise ValueError("finite actual boundary batch outputs for reuse")
        reuse[kind] = {bytes(k): v for k, v in zip(keys, values)}
    output = Path(config["output"])
    output.mkdir(exist_ok=False)
    marker = output / "INCOMPLETE"
    marker.write_text("original finite labels not completely published\n")
    facts = {}
    started = time.monotonic()
    attempted_total = boundary["logical_rows_attempted"]
    try:
        with input_pairs(config["input_classes"]) as (inputs, pairs):
            n = len(pairs)
            m = actual_orientation_count(pairs)
            # Actual source/count plan precedes all new model entry.
            if (
                config["actual_orientation_rows"] != m
                or config["inclusive_row_limit"] != 4 * n + 256
                or not 1 <= m <= 2 * n
            ):
                raise ValueError("actual teacher-row plan differs before model load")
            reuse_keys = set(reuse["S"])
            if reuse_keys != set(reuse["C"]):
                raise ValueError("same actual five-route input set required")
            found = set()
            for _, _, chunk in oriented_keys(pairs, config["batch_rows"]):
                found.update(bytes(k) for k in chunk if bytes(k) in reuse_keys)
            if found != reuse_keys:
                raise ValueError("runtime key not in exact current unsealed label classes")
            missing = m - len(found)
            if attempted_total + 2 * missing > config["inclusive_row_limit"]:
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
            for kind, adapter in (("S", "sigma"), ("C", "claustrophobia")):
                entry = config["models"][kind]
                expected_identity = boundary["model_identities"][kind]
                if list(IndexedPublicCorpus.identity(Path(entry["path"]).lstat())) != list(
                    expected_identity
                ):
                    raise ValueError("model changed since actual boundary hash/reader")
                target_path = output / (kind + ".f32")
                target = np.memmap(target_path, dtype="<f4", mode="w+", shape=(n, 2))
                target[:] = np.nan
                head = None
                tick = time.monotonic()
                newly_returned = 0
                portion_rows = min(16384, missing)
                first_portion = None
                try:
                    if missing:
                        head = StaticHead(
                            adapter,
                            entry["path"],
                            device=config["device"],
                            batch_rows=config["batch_rows"],
                            max_attempted_rows=missing,
                        )
                    for pair, orientation, chunk in oriented_keys(pairs, config["batch_rows"]):
                        values = np.empty(len(chunk), dtype="<f4")
                        present = np.fromiter(
                            (bytes(k) in reuse[kind] for k in chunk), dtype=bool, count=len(chunk)
                        )
                        for i in np.flatnonzero(present):
                            values[i] = reuse[kind][bytes(chunk[i])]
                        locations = np.flatnonzero(~present)
                        at = 0
                        while at < len(locations):
                            take = min(config["batch_rows"], len(locations) - at)
                            if first_portion is None:
                                take = min(take, portion_rows - newly_returned)
                            positions = locations[at : at + take]
                            sigma, c20 = encoder.encode(chunk[positions], include_c20=kind == "C")
                            if attempted_total + len(positions) > config["inclusive_row_limit"]:
                                raise ValueError("inclusive label row budget before dispatch")
                            attempted_total += len(positions)
                            values[positions] = head(sigma if kind == "S" else c20)
                            newly_returned += len(positions)
                            at += len(positions)
                            if first_portion is None and newly_returned == portion_rows:
                                first_portion = dict(
                                    new_logical_rows=newly_returned,
                                    wall_seconds=time.monotonic() - tick,
                                    outputs_retained=True,
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
                        reused_boundary_rows=len(found),
                        new_rows=newly_returned,
                        first_unentered_portion=first_portion,
                        seconds=time.monotonic() - tick,
                    )
                    write_json(
                        output / "progress.json",
                        dict(teachers=facts, inclusive_attempted_rows=attempted_total),
                    )
                except BaseException:
                    facts[kind] = dict(
                        status="FAILED_PARTIAL",
                        model=entry,
                        head=None if head is None else head.facts(),
                        new_finite_rows=newly_returned,
                        intended_new_rows=missing,
                        already_charged_global_attempted_rows=attempted_total,
                        scalar_file_complete=False,
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
                status="COMPLETE",
                input_classes=config["input_classes"],
                teachers=facts,
                runtime_boundary=config["runtime_boundary"],
                actual_orientation_rows=m,
                inclusive_attempted_rows=attempted_total,
                inclusive_row_limit=config["inclusive_row_limit"],
                old_outcome_or_rawsearch_teacher=False,
                history_semantics="board-only static STM",
                logical_rows_are_not_physical_heads=True,
                wall_seconds=time.monotonic() - started,
            )
            write_json(output / "teacher-values.json", bank)
            marker.unlink()
            return dict(
                manifest=file_ref(output / "teacher-values.json"),
                inclusive_attempted_rows=attempted_total,
                teachers=facts,
            )
    except BaseException as primary:
        try:
            write_json(
                output / "failure.json",
                dict(
                    type=type(primary).__name__,
                    message=str(primary),
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
            head_facts["S-oldORT"] = old_head.facts()
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
                head_facts[kind] = head.facts()
                del head
                if config["device"] == "cuda:0":
                    torch.cuda.empty_cache()
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
        marker.unlink()
        return dict(result=file_ref(output / "result.json"), actual_logical_rows=attempted)
    except BaseException as primary:
        try:
            write_json(
                output / "failure.json",
                dict(
                    type=type(primary).__name__,
                    message=str(primary),
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("qualify", "labels"))
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    from .cycle_process import cancellation_signals

    with cancellation_signals():
        config = json.loads(Path(args.config).read_bytes())
        result = (qualify_values if args.mode == "qualify" else label_values)(config)
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
