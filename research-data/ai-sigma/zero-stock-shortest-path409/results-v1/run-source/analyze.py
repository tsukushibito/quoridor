"""Finite409: only original3872 D-positive layouts; no all-layout replay."""

import argparse
import hashlib
import importlib.util
import json
import resource
import struct
import time
from collections import Counter
from pathlib import Path

from shortest import dag, distances, predicates


def file_ref(path):
    path = Path(path)
    b = path.read_bytes()
    return dict(
        path=str(path),
        sha256=hashlib.sha256(b).hexdigest(),
        bytes=len(b),
        mode=f"{path.stat().st_mode & 0o777:04o}",
    )


def read_json(ref):
    assert file_ref(ref["path"]) == ref
    return json.loads(Path(ref["path"]).read_bytes())


def state_from_raw(raw):
    turn = raw % 2
    pair = raw // 2
    return (divmod(pair // 25, 5), divmod(pair % 25, 5), turn)


def raw_from_state(state):
    a, b, turn = state
    return ((a[0] * 5 + a[1]) * 25 + b[0] * 5 + b[1]) * 2 + turn


def saved_graph(ref):
    assert file_ref(ref["path"]) == ref
    body = Path(ref["path"]).read_bytes()
    magic, n, candidates, reserved, mask, raw_count, active_count, edge_count = (
        struct.unpack_from("<8sBBHIIII", body)
    )
    assert (magic, n, candidates, reserved, raw_count) == (b"Q5WDL001", 5, 32, 0, 1250)
    offset = 28
    edges, labels = {}, {}
    for raw in range(raw_count):
        status, degree, _, _ = struct.unpack_from("<BBHH", body, offset)
        offset += 6
        outgoing = []
        for _ in range(degree):
            dest, child = struct.unpack_from("<BH", body, offset)
            offset += 3
            outgoing.append(
                (divmod(dest, 5), None if child == 65535 else state_from_raw(child))
            )
        if status != 255:
            assert status in (0, 1, 2) and degree > 0
            state = state_from_raw(raw)
            labels[state] = status
            edges[state] = outgoing
        else:
            assert degree == 0
    assert offset == len(body) and len(labels) == active_count
    assert sum(len(v) for v in edges.values()) == edge_count
    return mask, edges, labels


def bucket():
    return dict(
        layouts=0,
        D=0,
        one_pair_states=0,
        one_pair_layouts=0,
        all_union_states=0,
        all_union_layouts=0,
        one_only_states=0,
        neither_states=0,
        UNKNOWN_states=0,
    )


def add(target, values):
    for key in target:
        target[key] += values[key]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    assert file_ref(args.settings)["sha256"] == args.sha256
    settings = json.loads(args.settings.read_bytes())
    layouts = read_json(settings["input"])
    assert len(layouts) == settings["expected_layouts"] == 3872
    source_ref = settings["original_reference"]
    assert file_ref(source_ref["path"]) == source_ref
    spec = importlib.util.spec_from_file_location(
        "original405_reference", source_ref["path"]
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    # Merely loading the module does not invoke its CLI or old52 software suite.
    saved = {}
    for item in settings["saved_graphs"]:
        mask = item["first"]["mask"]
        saved[mask] = item["graph"]
    out = Path(settings["output"])
    out.mkdir(exist_ok=False)
    total = bucket()
    by_wall = [bucket() for _ in range(33)]
    parity = {"even": bucket(), "odd": bucket()}
    representatives = {"one_pair": None, "all_union": None}
    restored = reused = leaves = distinct_pairs = 0
    restore_seconds = predicate_seconds = 0.0
    start = time.monotonic()
    known405 = None

    def make_case(layout, state, graphs, witness, edges, labels, source_kind):
        walls = []
        for bit in range(32):
            if layout["mask"] & (1 << bit):
                anchor = bit % 16
                walls.append(
                    dict(
                        direction="H" if bit < 16 else "V",
                        row=anchor // 4,
                        col=anchor % 4,
                        anchor_coordinate=f"{chr(97 + anchor % 4)}{anchor // 4 + 1}",
                    )
                )
        cases = dict(
            layout=layout,
            raw_id=raw_from_state(state),
            pawns=[list(state[0]), list(state[1])],
            turn=state[2],
            board_WDL="D",
            shortest_DAGs=[
                dict(
                    start=g["start"],
                    distance=g["distance"],
                    union_cells=[v for v in range(25) if g["union"] & (1 << v)],
                    edges={
                        str(v): list(children)
                        for v, children in sorted(g["edges"].items())
                    },
                    path_count=g["path_count"],
                )
                for g in graphs
            ],
            vertex_disjoint_paths=[list(path) for path in witness] if witness else None,
            walls=walls,
            wall_count_parity="even" if layout["walls"] % 2 == 0 else "odd",
            equal_initial_stock_m=layout["walls"] // 2
            if layout["walls"] % 2 == 0
            else None,
            actual_nonterminal_prefix="UNKNOWN; no new prefix search",
            WDL_source=source_kind,
            all_active_saved_graph=[
                dict(
                    raw=raw_from_state(s),
                    label=label,
                    edges=[
                        dict(
                            action=q[0] * 5 + q[1],
                            child=None if child is None else raw_from_state(child),
                        )
                        for q, child in edges[s]
                    ],
                )
                for s, label in sorted(
                    labels.items(), key=lambda pair: raw_from_state(pair[0])
                )
            ],
        )
        return cases

    flag_struct = struct.Struct("<QIHBB")
    flags_count = 0
    with (
        (out / "D-flags.bin").open("xb") as flags,
        (out / "layout-results.jsonl").open("x") as journal,
    ):
        for layout in layouts:
            t = time.monotonic()
            mask = layout["mask"]
            if mask in saved:
                saved_mask, edges, labels = saved_graph(saved[mask])
                assert saved_mask == mask
                source_kind = "reused original saved full graph"
                reused += 1
            else:
                edges, labels = original.oracle(5, mask)
                source_kind = (
                    "original reference.oracle(5,mask),409 bounded restoration"
                )
                restored += 1
            counts = Counter(labels.values())
            assert (
                len(labels) == layout["active"]
                and sum(len(v) for v in edges.values()) == layout["edges"]
            )
            assert (counts[1], counts[2], counts[0]) == (
                layout["W"],
                layout["L"],
                layout["D"],
            )
            restore_seconds += time.monotonic() - t
            t = time.monotonic()
            adjacent = original.board(5, mask)
            adjacent = {
                r * 5 + c: tuple(sorted(s * 5 + d for s, d in neighbours))
                for (r, c), neighbours in adjacent.items()
            }
            distance = [
                distances(adjacent, range(20, 25)),
                distances(adjacent, range(5)),
            ]
            cache, pair_cache = {}, {}
            part = bucket()
            part["layouts"] = 1
            draw_states = sorted(
                (state for state, label in labels.items() if label == 0),
                key=raw_from_state,
            )
            for state in draw_states:
                a, b, _turn = state
                pawn_pair = (a, b)
                if pawn_pair not in pair_cache:
                    graphs = []
                    for side, pawn in enumerate([a, b]):
                        cell = pawn[0] * 5 + pawn[1]
                        if (side, cell) not in cache:
                            cache[side, cell] = dag(adjacent, distance[side], cell)
                        graphs.append(cache[side, cell])
                    pair_cache[pawn_pair] = (*predicates(*graphs), graphs)
                    distinct_pairs += 1
                    leaves += pair_cache[pawn_pair][3]
                one, every, witness, _, graphs = pair_cache[pawn_pair]
                assert not every or one
                assert all(
                    child is not None and labels[child] != 2
                    for _, child in edges[state]
                )
                assert any(labels[child] == 0 for _, child in edges[state])
                flags.write(
                    flag_struct.pack(
                        layout["ordinal"], mask, raw_from_state(state), one, every
                    )
                )
                flags_count += 1
                part["D"] += 1
                part["one_pair_states"] += one
                part["all_union_states"] += every
                part["one_only_states"] += one and not every
                part["neither_states"] += not one
                if one and representatives["one_pair"] is None:
                    representatives["one_pair"] = make_case(
                        layout, state, graphs, witness, edges, labels, source_kind
                    )
                if every and representatives["all_union"] is None:
                    representatives["all_union"] = make_case(
                        layout, state, graphs, witness, edges, labels, source_kind
                    )
                if mask == 67882 and raw_from_state(state) == 376:
                    known405 = dict(
                        mask=mask,
                        raw_id=376,
                        one_pair=one,
                        all_union=every,
                        qualification="same already verified405 stock3/prefix target; no new prefix or claim of optimal initial play",
                    )
            part["one_pair_layouts"] = int(part["one_pair_states"] > 0)
            part["all_union_layouts"] = int(part["all_union_states"] > 0)
            assert part["D"] == layout["D"]
            for target in [
                total,
                by_wall[layout["walls"]],
                parity["even" if layout["walls"] % 2 == 0 else "odd"],
            ]:
                add(target, part)
            journal.write(
                json.dumps(
                    dict(
                        ordinal=layout["ordinal"],
                        mask=mask,
                        walls=layout["walls"],
                        WDL_source=source_kind,
                        counts=part,
                    ),
                    separators=(",", ":"),
                )
                + "\n"
            )
            predicate_seconds += time.monotonic() - t
        flags.flush()
        journal.flush()
    assert total["layouts"] == 3872 and total["D"] == flags_count == 39708
    assert [b["layouts"] for b in by_wall] == settings["D_layouts_by_walls"]
    assert flags_count * flag_struct.size == (out / "D-flags.bin").stat().st_size
    if representatives["all_union"] is not None:
        representatives["one_pair"] = representatives["all_union"]
    case_refs = {}
    for condition in ["all_union", "one_pair"]:
        case = representatives[condition]
        if (
            condition == "one_pair"
            and case is not None
            and case is representatives["all_union"]
        ):
            case_refs[condition] = case_refs["all_union"]
            continue
        if case is not None:
            path = out / f"representative-{condition}.json"
            path.write_text(json.dumps(case, indent=2) + "\n")
            case_refs[condition] = file_ref(path)
        else:
            case_refs[condition] = None
    assert (
        file_ref(source_ref["path"]) == source_ref
        and file_ref(settings["input"]["path"]) == settings["input"]
    )
    result = dict(
        status="COMPLETE",
        settings=file_ref(args.settings),
        total=total,
        by_wall_count=by_wall,
        parity=parity,
        restored_layouts=restored,
        reused_saved_graph_layouts=reused,
        converse_not_assumed=True,
        all_union_implies_one_pair_checked=True,
        branch_cap=None,
        distinct_pawn_pairs_checked=distinct_pairs,
        enumerated_path_leaves=leaves,
        representatives=case_refs,
        known405_target=known405,
        outputs=[file_ref(out / "D-flags.bin"), file_ref(out / "layout-results.jsonl")],
        flag_record=dict(
            format="<QIHBB",
            bytes=16,
            fields=[
                "original ordinal",
                "wall mask",
                "raw pawn/turn ID",
                "one_pair 0/1",
                "all_union 0/1",
            ],
            endianness="little",
            header_bytes=0,
            complete_records=flags_count,
        ),
        costs=dict(
            restoration_seconds=restore_seconds,
            predicates_and_evidence_seconds=predicate_seconds,
            whole_until_result_seconds=time.monotonic() - start,
            self_ru_maxrss_B=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            continuous_family_peak="UNKNOWN",
            nested_stage_times_not_added_to_guardian=True,
        ),
        limitations=[
            "5x5 original board-D scope only",
            "no9x9/general-history/initial-optimal-play theorem",
            "even walls/equal-stock count not nonterminal-prefix certification",
            "no Search integration or new sweep/refill",
            "original405 records/source/costs unchanged",
        ],
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                status=result["status"],
                total=total,
                restored=restored,
                reused=reused,
                costs=result["costs"],
                result=file_ref(out / "result.json"),
            )
        )
    )


if __name__ == "__main__":
    main()
