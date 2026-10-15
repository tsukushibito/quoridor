"""Saved fixed-run census: packed stream identities, totals and bounded D witness."""

import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

KEYS = ("layouts", "active", "edges", "W", "L", "D", "analysis_ns", "verification_ns")
ROW = struct.Struct("<QIBBBBHHIHHHHQQ")


def ref(path):
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "bytes": stat.st_size,
        "mode": format(stat.st_mode & 0o777, "04o"),
    }


def zero():
    return dict.fromkeys(KEYS, 0)


def add(target, values):
    for key, value in values.items():
        target[key] += value


def main(root):
    output = root / "full-collection-v1"
    enum = json.loads((root / "enumeration-v1/collection-v1/result.json").read_text())
    mask_path = root / "enumeration-v1/masks.bin"
    mask_ref = ref(mask_path)
    assert mask_ref == enum["mask_file"]
    masks = mask_path.read_bytes()
    count = enum["layouts"]
    assert len(masks) == 24 + 4 * count
    total, cold = zero(), zero()
    walls, components, flags = (
        [zero() for _ in range(33)],
        [zero() for _ in range(26)],
        [zero() for _ in range(8)],
    )
    seen = bytearray(count)
    streams, candidates = [], []
    zero_active = draw_layouts = 0
    by_wall_draw_layouts, by_wall_zero_active = [0] * 33, [0] * 33
    paths = [(root / "pilot-v1", None)] + [
        (root / "remaining-v1" / f"worker-{i}", i) for i in range(4)
    ]
    for directory, index in paths:
        summary_ref, records_ref = (
            ref(directory / "summary.json"),
            ref(directory / "records.bin"),
        )
        summary = json.loads((directory / "summary.json").read_text())
        expected = (
            (i for i in range(count) if i < 16 or i % 4096 == 0)
            if index is None
            else (i for i in range(index, count, 4) if not (i < 16 or i % 4096 == 0))
        )
        part, partcold = zero(), zero()
        pw, pc, pf = (
            [zero() for _ in range(33)],
            [zero() for _ in range(26)],
            [zero() for _ in range(8)],
        )
        first_d = None
        with (directory / "records.bin").open("rb") as stream:
            magic, side, phase, workers, worker, input_count, selected, width = (
                struct.unpack("<8sBBBBQQI", stream.read(32))
            )
            assert (magic, side, input_count, width) == (b"Q5REC001", 5, count, 48)
            assert (phase, workers, worker) == (
                (1, 1, 0) if index is None else (2, 4, index)
            )
            assert (
                selected == summary["expected_selected"]
                and records_ref["bytes"] == 32 + selected * 48
            )
            while data := stream.read(48 * 4096):
                assert len(data) % 48 == 0
                for (
                    ordinal,
                    mask,
                    wall,
                    component,
                    flag,
                    reserved,
                    active,
                    rank,
                    edges,
                    w,
                    loss,
                    draw,
                    reserved2,
                    analysis,
                    verification,
                ) in ROW.iter_unpack(data):
                    assert ordinal == next(expected) and not seen[ordinal]
                    seen[ordinal] = 1
                    assert struct.unpack_from("<I", masks, 24 + ordinal * 4)[0] == mask
                    assert (
                        reserved == reserved2 == 0
                        and mask.bit_count() == wall
                        and 1 <= component <= 25
                        and flag < 8
                    )
                    assert active <= 770 and rank <= 1250 and w + loss + draw == active
                    values = dict(
                        zip(
                            KEYS,
                            (1, active, edges, w, loss, draw, analysis, verification),
                        )
                    )
                    for bucket in (
                        part,
                        pw[wall],
                        pc[component],
                        pf[flag],
                        total,
                        walls[wall],
                        components[component],
                        flags[flag],
                    ):
                        add(bucket, values)
                    if ordinal < 16:
                        add(cold, values)
                        add(partcold, values)
                    if active == 0:
                        zero_active += 1
                        by_wall_zero_active[wall] += 1
                    if draw:
                        draw_layouts += 1
                        by_wall_draw_layouts[wall] += 1
                        if first_d is None:
                            first_d = {"ordinal": ordinal, "mask": mask}
            assert next(expected, None) is None
        assert part == summary["total"] and partcold == summary["cold_first16"]
        assert (
            pw == summary["by_wall_count"]
            and pc == summary["by_components"]
            and pf == summary["by_initial_shape_flags"]
        )
        assert (
            ref(directory / "summary.json") == summary_ref
            and ref(directory / "records.bin") == records_ref
        )
        if first_d is None:
            assert (
                summary["first_D"] is None and not (directory / "first-D.bin").exists()
            )
        else:
            assert first_d == {k: summary["first_D"][k] for k in ("ordinal", "mask")}
            candidates.append(
                {"first": summary["first_D"], "graph": ref(directory / "first-D.bin")}
            )
        streams.append(
            {
                "records": records_ref,
                "summary": summary_ref,
                "total": part,
                "native_whole_before_summary_s": summary[
                    "whole_before_summary_seconds"
                ],
                "native_VmHWM_B": summary["peak_rss_B"],
                "output_ns": summary["output_ns"],
            }
        )
    assert (
        all(seen)
        and total["layouts"] == count
        and total["W"] + total["L"] + total["D"] == total["active"]
    )
    assert [v["layouts"] for v in walls] == enum["by_wall_count"] and cold[
        "layouts"
    ] == 16
    assert ref(mask_path) == mask_ref
    first = min(candidates, key=lambda c: c["first"]["ordinal"])
    graph = Path(first["graph"]["path"]).read_bytes()
    magic, side, _, reserved, mask, raw_count, active_count, edge_count = (
        struct.unpack_from("<8sBBHIIII", graph)
    )
    assert (
        magic == b"Q5WDL001"
        and side == 5
        and not reserved
        and mask == first["first"]["mask"]
        and len(graph) <= 37528
    )
    rows, offset = {}, 28
    for raw in range(raw_count):
        status, degree, rank, choice = struct.unpack_from("<BBHH", graph, offset)
        offset += 6
        outgoing = []
        for _ in range(degree):
            action, child = struct.unpack_from("<BH", graph, offset)
            offset += 3
            outgoing.append((action, child))
        rows[raw] = {
            "status": status,
            "rank": rank,
            "choice": choice,
            "outgoing": outgoing,
        }
    assert offset == len(graph)
    raw = first["first"]["raw_state"]
    trace, visited = [], {}
    while raw not in visited:
        visited[raw] = len(trace)
        row = rows[raw]
        assert (
            row["status"] == 0
            and row["rank"] == 0
            and rows[row["choice"]]["status"] == 0
        )
        assert all(
            child != 65535 and rows[child]["status"] != 2
            for _, child in row["outgoing"]
        )
        turn, p1, p0 = raw % 2, (raw // 2) % 25, raw // 50
        chosen = next(
            action for action, child in row["outgoing"] if child == row["choice"]
        )
        trace.append(
            {
                "raw_state": raw,
                "P0_cell": p0,
                "P1_cell": p1,
                "turn": turn,
                "choice_action_cell": chosen,
                "next_raw_state": row["choice"],
                "all_saved_legal_edges": row["outgoing"],
            }
        )
        raw = row["choice"]
    anchors = [
        {
            "orientation": "H" if bit < 16 else "V",
            "row0": (bit % 16) // 4,
            "col0": bit % 4,
            "bit": bit,
        }
        for bit in range(32)
        if mask & (1 << bit)
    ]
    first.update(
        wall_count=mask.bit_count(),
        anchors=anchors,
        active=active_count,
        edges=edge_count,
        saved_strategy_trace=trace,
        cycle_start=visited[raw],
        cycle_state=raw,
        independent_check=ref(output / "independent-first-D.full.log"),
    )
    process_stop = json.loads((output / "process-STOP.json").read_text())
    assert process_stop["all_four_originals_saved_cleaned"]
    pilot_job = json.loads((root / "pilot-v1/runtime-v1/result.json").read_text())
    enum_job = json.loads((root / "enumeration-v1/runtime-v1/result.json").read_text())
    outer = [enum_job, pilot_job, *(v["outer_result"] for v in process_stop["entries"])]
    result = {
        "status": "FULL_FIXED5X5_CENSUS_VALIDATED",
        "total": total,
        "layouts_with_D": draw_layouts,
        "layouts_active0_included": zero_active,
        "by_wall_count": walls,
        "by_components": components,
        "by_initial_shape_flags": flags,
        "D_layouts_by_wall_count": by_wall_draw_layouts,
        "active0_layouts_by_wall_count": by_wall_zero_active,
        "cold_first16": cold,
        "streams": streams,
        "mask_file": mask_ref,
        "enumeration_result": ref(root / "enumeration-v1/collection-v1/result.json"),
        "pilot_result": ref(root / "pilot-v1/collection-v1/result.json"),
        "all_five_record_streams_exact_union_once": True,
        "first_D_per_remaining_shard": candidates,
        "globally_first_D": first,
        "costs": {
            "original_outer_jobs": outer,
            "sum_original_outer_wall_s": sum(v["wall_seconds"] for v in outer),
            "analysis_s": total["analysis_ns"] / 1e9,
            "all_edge_verification_s": total["verification_ns"] / 1e9,
            "native_analysis_whole_sum_s": sum(
                v["native_whole_before_summary_s"] for v in streams
            ),
            "output_nested_s": sum(v["output_ns"] for v in streams) / 1e9,
            "continuous_family_RSS_peak": "UNKNOWN",
            "LLM_source_admin_wall": "not included; UNKNOWN",
        },
        "native_process_STOP": ref(output / "process-STOP.json"),
        "actual_saved_reader_STOP": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "owned_readers_writers_children_jobs_TMP_leases": [],
        "scope": "All collision-free5x5 fixedwall sets; active distinct own-goal-reachable non-goal pawns, both turns. No initial-start/component/even-count filter. Infinite play board-WDL; no actual equal-stock placement/play prefix or9x9 theorem claimed.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "total": total,
                "D_layouts": draw_layouts,
                "active0_layouts": zero_active,
                "first_D": first,
                "D_by_wall": by_wall_draw_layouts,
                "costs": result["costs"],
            }
        )
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
