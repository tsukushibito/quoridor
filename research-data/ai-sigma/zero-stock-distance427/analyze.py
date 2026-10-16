"""One bounded saved-geometry analysis; no solver/Search/model execution."""

import ast
from collections import Counter, deque
from datetime import datetime, timezone
import gzip
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import struct
import time

HERE = Path(__file__).resolve().parent
ROOT = Path("/workspaces/quoridor")
INPUT_REFS = []
BFS_LOG = []
GEOMETRIES = {}
PAIR_MAPS = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    item = dict(
        path=str(path),
        sha256=sha(raw),
        bytes=len(raw),
        mode=f"{path.stat().st_mode & 0o777:04o}",
    )
    if expected:
        assert all(item[k] == v for k, v in expected.items() if k in item), (
            path,
            item,
            expected,
        )
    INPUT_REFS.append(item)
    return raw


def ast_function(path, name, namespace):
    raw = read(path)
    tree = ast.parse(raw.decode())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    unit = ast.Module(body=[fn], type_ignores=[])
    exec(compile(unit, str(path) + "::" + name, "exec"), namespace)
    return namespace[name]


BOARD = ast_function(
    ROOT
    / ".artifacts/research-team/integration324/zero-stock-5x5-405-v1/software-v1/source/reference.py",
    "board",
    {"itertools": itertools},
)
DISTANCES = ast_function(
    ROOT
    / "research-data/ai-sigma/zero-stock-shortest-path409/results-v1/run-source/shortest.py",
    "distances",
    {"deque": deque},
)


def bfs(adjacent, goals, purpose):
    assert len(BFS_LOG) < 1024, "whole427 BFS budget exhausted"
    entry = dict(
        index=len(BFS_LOG),
        purpose=purpose,
        vertices=len(adjacent),
        seeds=[list(x) for x in goals],
        status="ENTERED",
    )
    BFS_LOG.append(entry)
    result = DISTANCES(adjacent, goals)
    entry.update(
        status="COMPLETE",
        visited=len(result),
        scanned_directed_edges=sum(len(adjacent[v]) for v in result),
    )
    return result


def geometry(n, mask):
    key = (n, mask)
    if key not in GEOMETRIES:
        adjacent = BOARD(n, mask)
        maps = [
            bfs(
                adjacent,
                [(row, c) for c in range(n)],
                f"goal:n{n}:mask{mask}:p{player}",
            )
            for player, row in enumerate((n - 1, 0))
        ]
        GEOMETRIES[key] = (adjacent, maps)
    return GEOMETRIES[key]


def finite_gap(a, b, size):
    return (
        abs(a - b)
        if a is not None and b is not None and 0 <= a < size and 0 <= b < size
        else None
    )


def metrics(state):
    n, mask = state["n"], state["mask"]
    adjacent, maps = geometry(n, mask)
    a, b = [divmod(cell, n) for cell in state["pawns"]]
    turn = state["turn"]
    ds, other = maps[turn].get((a, b)[turn]), maps[1 - turn].get((a, b)[1 - turn])
    m = abs(a[0] - b[0]) + abs(a[1] - b[1])
    gaps = [finite_gap(table.get(a), table.get(b), n * n) for table in maps]
    lower = max([m] + [g for g in gaps if g is not None])
    threshold = (
        None
        if ds is None or other is None
        else 2 * ds
        if ds <= other
        else 2 * other + 1
    )
    return adjacent, a, b, ds, other, m, gaps, lower, threshold


def history_state(actions, prefixes=False):
    pawns, stock, walls = [4, 76], [10, 10], []
    counts = Counter()
    states = []

    def key(turn):
        return (tuple(pawns), turn, tuple(sorted(walls)), tuple(stock))

    counts[key(0)] += 1
    for index, action in enumerate(actions):
        assert not (pawns[0] // 9 == 8 or pawns[1] // 9 == 0), (
            "saved actions continue after goal"
        )
        turn = index % 2
        assert type(action) is int and 0 <= action <= 208
        if action < 81:
            pawns[turn] = action
        else:
            assert stock[turn] > 0 and action not in walls
            stock[turn] -= 1
            walls.append(action)
        assert pawns[0] != pawns[1]
        new_key = key(1 - turn)
        counts[new_key] += 1
        terminal = pawns[0] // 9 == 8 or pawns[1] // 9 == 0
        if stock == [0, 0] and not terminal:
            mask = sum(1 << (wall - 81) for wall in walls)
            domain_counts = [
                count
                for (_, _, wall_ids, stocks), count in counts.items()
                if wall_ids == tuple(sorted(walls)) and stocks == (0, 0)
            ]
            state = dict(
                n=9,
                mask=mask,
                walls=sorted(walls),
                pawns=list(pawns),
                turn=1 - turn,
                stocks=list(stock),
                prefix_length=index + 1,
                history=dict(
                    complete_saved_action_prefix=True,
                    specified_occurrences=index + 2,
                    weighted_counts_source="unit arrivals from complete moves including initial state; no weighted base discarded",
                    E_geometric_domain_derived_empty=not any(
                        c >= 2 for c in domain_counts
                    ),
                    E_repeated_keys_derived=sum(c >= 2 for c in domain_counts),
                    canonical_history_qualification="UNKNOWN: offline action accounting; no new core replay; geometry is not actualproofleaf census",
                ),
            )
            states.append(state)
    final = dict(pawns=pawns, stocks=stock, walls=sorted(walls), turn=len(actions) % 2)
    return (
        states
        if prefixes
        else (
            states[-1]
            if states and states[-1]["prefix_length"] == len(actions)
            else None,
            final,
        )
    )


def state_key(state):
    return (state["n"], state["mask"], tuple(state["pawns"]), state["turn"])


def select_nine():
    inputs = json.loads(
        read(
            ROOT
            / ".worktree/arena-evaluation/.artifacts/research-team/zero-stock-safe-race411-v1/eight-prefixes.json",
            {
                "sha256": "eec77569104f589b2e6b38c9cd388ad5c51e2ec4a549e34fea3d85a6c9588daa",
                "bytes": 4318,
                "mode": "0644",
            },
        )
    )
    selection = json.loads(
        read(
            ROOT
            / ".worktree/arena-evaluation/.artifacts/research-team/zero-stock-safe-race411-v1/selection-result.json",
            {
                "sha256": "01ceb3e7695f658d685f8b3ee59be9b23b5eb955119063e66fe96559debc6b9d"
            },
        )
    )
    chosen, index_by_key, root_audit, game_audit = [], {}, [], []
    duplicates = 0

    def add(state, origin):
        nonlocal duplicates
        key = state_key(state)
        if key in index_by_key:
            duplicates += 1
            chosen[index_by_key[key]]["origins"].append(origin)
            return "existing"
        if len(chosen) == 128:
            return "global128cap"
        state = dict(state, dataset="nine", origins=[origin], saved_label="UNKNOWN")
        index_by_key[key] = len(chosen)
        chosen.append(state)
        return "added"

    for index, item in enumerate(inputs):
        state, final = history_state(item["prefix"])
        status = "notstock0_or_terminal"
        if state:
            assert len(state["walls"]) == 20
            status = add(
                state,
                dict(
                    kind="original411root",
                    root=index,
                    source_game=item["game"],
                    family=item["family"],
                    prefix_length=len(item["prefix"]),
                ),
            )
        root_audit.append(dict(root=index, final=final, disposition=status))
    sources = selection["new_inputs"]
    assert len(sources) == 4 and [x["source"]["local_game"] for x in sources] == [
        0,
        1,
        2,
        3,
    ]
    source_ref = sources[0]["source"]["journal"]
    assert all(x["source"]["journal"] == source_ref for x in sources)
    stream_path = Path(source_ref["path"])
    before_stat = stream_path.stat()
    compressed = read(
        stream_path, source_ref
    )  # The ONE named RAW read; no second disk read.
    raw_hash, raw_bytes, lines = hashlib.sha256(), 0, 0
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        while line := stream.readline():
            lines += 1
            raw_bytes += len(line)
            raw_hash.update(line)
            if lines > 4:
                continue  # CRC/hash drain only; remaining28 games not parsed.
            source = sources[lines - 1]
            assert sha(line) == source["source"]["line_sha256"]
            row = json.loads(line)
            game = row["game"]
            assert game == lines - 1
            assert row["moves"][: len(source["prefix"])] == source["prefix"]
            states = history_state(row["moves"], prefixes=True)
            assert states and states[0]["prefix_length"] == len(source["prefix"])
            expected = source["saved_action_accounting"]
            assert all(
                states[0][key] == expected[key]
                for key in ("pawns", "stocks", "walls", "turn")
            )
            seen, selected, repeated, capped = set(), 0, 0, 0
            for state in states:
                key = state_key(state)
                if key in seen:
                    repeated += 1
                    continue
                seen.add(key)
                if selected == 32:
                    break
                selected += 1
                outcome = add(
                    state,
                    dict(
                        kind="408game",
                        batch=0,
                        game=game,
                        family=source["original_family"],
                        family_id=source["original_family_id"],
                        journal_line=lines,
                        prefix_length=state["prefix_length"],
                    ),
                )
                capped += outcome == "global128cap"
            game_audit.append(
                dict(
                    game=game,
                    family_id=source["original_family_id"],
                    available_nonterminal_stock0_occurrences=len(states),
                    selected_first_distinct=selected,
                    repeated_before_selection_end=repeated,
                    global_capped=capped,
                )
            )
    after_stat = stream_path.stat()
    assert (
        before_stat.st_dev,
        before_stat.st_ino,
        before_stat.st_size,
        before_stat.st_mtime_ns,
    ) == (
        after_stat.st_dev,
        after_stat.st_ino,
        after_stat.st_size,
        after_stat.st_mtime_ns,
    )
    assert sha(compressed) == source_ref["sha256"] and lines == 32
    old_read = selection["archive_reads"][0]
    assert (
        raw_hash.hexdigest() == old_read["raw_sha256"]
        and raw_bytes == old_read["raw_bytes"]
    )
    return chosen, dict(
        roots=root_audit,
        games=game_audit,
        duplicates_merged_with_all_origins=duplicates,
        stream=dict(
            ref=source_ref,
            physical_reads=1,
            parsed_rows=4,
            CRC_hash_drain_rows=28,
            raw_bytes=raw_bytes,
            raw_sha256=raw_hash.hexdigest(),
            before_after_stat_identity=True,
            compressed_hash_before_after_same_buffer=True,
            second_RAW_disk_hash_read=False,
        ),
    )


def select_small():
    refs = json.loads(
        read(
            ROOT
            / ".worktree/arena-evaluation/.artifacts/research-team/zero-stock-detour414-v1/selected-refs.json",
            {
                "sha256": "cf9eb34680f710f1e00649a36aaabd9cf2767c2849004b44dc615c80484bf3a7"
            },
        )
    )
    binaries = [
        r
        for r in refs
        if Path(r["path"]).name.startswith("fixture-") and r["path"].endswith(".bin")
    ]
    selected, examined, files = [], 0, []
    for fixture_index, expected in enumerate(binaries):
        if len(selected) == 128:
            break
        raw = read(expected["path"], expected)
        magic, n, candidates, reserved, mask, raw_count, active, edges = (
            struct.unpack_from("<8sBBHIIII", raw)
        )
        assert (
            magic == b"Q5WDL001"
            and n in (3, 5)
            and candidates == 2 * (n - 1) ** 2
            and reserved == 0
            and raw_count == 2 * n**4
        )
        files.append(dict(fixture=fixture_index, n=n, mask=mask, ref=expected))
        offset = 28
        for raw_id in range(raw_count):
            status, degree, _, _ = struct.unpack_from("<BBHH", raw, offset)
            offset += (
                6 + 3 * degree
            )  # Skip all saved pawnedges/ranks, never execute or verify them.
            assert offset <= len(raw) and status in (0, 1, 2, 255)
            if status not in (1, 2):
                continue
            examined += 1
            cells = n * n
            pair = raw_id // 2
            state = dict(
                dataset="small",
                n=n,
                mask=mask,
                walls=[i for i in range(candidates) if mask >> i & 1],
                pawns=[pair // cells, pair % cells],
                turn=raw_id % 2,
                stocks=[0, 0],
                saved_label={1: "W", 2: "L"}[status],
                origins=[
                    dict(
                        kind="414saved52",
                        fixture=fixture_index,
                        raw_id=raw_id,
                        file=expected,
                    )
                ],
                history=dict(
                    canonical_history_qualification="UNKNOWN: saved history-free W/L, no real fullhistory"
                ),
            )
            _, _, _, ds, other, _, _, lower, threshold = metrics(state)
            assert ds is not None and other is not None and ds > 0 and other > 0
            if lower < threshold:
                selected.append(state)
                if len(selected) == 128:
                    break
    return selected, dict(
        selected=len(selected),
        scanned_active_WL_for_explicit_Lfail_filter=examined,
        fixture_files_read=files,
        stable_order="fixture index then raw_id; no rho/result-directed replacement",
        edges_ranks_or_solver_replayed=False,
    )


def classify(state):
    adjacent, a, b, ds, other, m, gaps, lower, threshold = metrics(state)
    n = state["n"]
    valid = (
        state["stocks"] == [0, 0]
        and a != b
        and a[0] != n - 1
        and b[0] != 0
        and ds is not None
        and other is not None
        and 0 < ds < n * n
        and 0 < other < n * n
    )
    if not valid:
        return dict(
            state,
            classification="INPUT_UNQUALIFIED",
            ds=ds,
            do=other,
            M=m,
            finite_goal_diffs=gaps,
            L=lower,
            T=threshold,
            rho=None,
        )
    key = (n, state["mask"], a)
    if key not in PAIR_MAPS:
        PAIR_MAPS[key] = bfs(adjacent, [a], f"rho:n{n}:mask{state['mask']}:from{a}")
    rho = PAIR_MAPS[key].get(b)
    if rho is not None:
        assert m <= rho and lower <= rho and all(g is None or g <= rho for g in gaps), (
            "bound/input contradiction"
        )
    category = (
        "DISCONNECTED"
        if rho is None
        else "LOWER_BOUND_PASSES"
        if lower >= threshold
        else "BOUND_TOO_WEAK"
        if threshold <= rho
        else "THRESHOLD_STILL_FAILS"
    )
    return dict(
        state,
        ds=ds,
        do=other,
        M=m,
        finite_goal_diffs=gaps,
        goal_cross_values=[
            [table.get(a), table.get(b)] for table in geometry(n, state["mask"])[1]
        ],
        L=lower,
        rho=rho,
        rho_unreachable=rho is None,
        candidate_winner=state["turn"] if ds <= other else 1 - state["turn"],
        T=threshold,
        T_minus_L=threshold - lower,
        rho_minus_L=None if rho is None else rho - lower,
        M_passes=m >= threshold,
        L_passes=lower >= threshold,
        classification=category,
        actual_new_proof_leaf="UNKNOWN/not measured",
    )


def boundary_checks():
    checks = []
    for name, mask, expected_rho, expected_class in [
        ("ordinary_adjacent_threshold_still_fails", 0, 1, "THRESHOLD_STILL_FAILS"),
        (
            "one_legal_vertical_wall_detour_lost_by_both_goal_gaps",
            64,
            3,
            "BOUND_TOO_WEAK",
        ),
    ]:
        state = dict(n=3, mask=mask, pawns=[3, 4], turn=0, stocks=[0, 0])
        result = classify(state)
        assert (
            result["rho"] == expected_rho
            and result["classification"] == expected_class
            and result["L"] == 1
            and result["T"] == 2
        )
        checks.append(
            dict(
                name=name,
                expected=dict(
                    rho=expected_rho, L=1, T=2, classification=expected_class
                ),
                actual=result,
            )
        )
    equal = classify(dict(n=3, mask=0, pawns=[3, 5], turn=0, stocks=[0, 0]))
    assert (
        equal["rho"] == equal["L"] == equal["T"] == 2
        and equal["classification"] == "LOWER_BOUND_PASSES"
    )
    checks.append(dict(name="equality_boundary_ordinary_grid", actual=equal))
    isolated = {(0, 0): set(), (0, 1): set()}
    missing = bfs(isolated, [(0, 0)], "boundary:synthetic_disconnected_twovertices")
    assert (
        (0, 1) not in missing
        and finite_gap(0, 81, 81) is None
        and finite_gap(80, 1, 81) == 79
    )
    assert max([1] + [x for x in [None, finite_gap(5, 1, 81)] if x is not None]) == 4
    checks.append(
        dict(
            name="unreachable_missing_and_sentinel81_ignore_each_term",
            synthetic_graph_only=True,
            no_Quoridor_counterexample=True,
        )
    )
    return checks


def summarize(rows):
    groups = {}
    for row in rows:
        categories = {
            "dataset": row["dataset"],
            "size": str(row["n"]),
            "geometry": f"{row['n']}:{row['mask']}",
        }
        for origin in row["origins"]:
            if origin["kind"] == "408game":
                categories[f"game{origin['game']}"] = f"408:{origin['game']}"
            if origin["kind"] == "original411root":
                categories[f"root{origin['root']}"] = f"411:{origin['root']}"
        for dimension, group in categories.items():
            key = (row["dataset"], dimension, group)
            item = groups.setdefault(
                key,
                dict(
                    dataset=row["dataset"],
                    dimension=dimension,
                    group=group,
                    total=0,
                    classes=Counter(),
                    saved_labels=Counter(),
                    E_derived=Counter(),
                ),
            )
            item["total"] += 1
            item["classes"][row["classification"]] += 1
            item["saved_labels"][row["saved_label"]] += 1
            item["E_derived"][
                str(row["history"].get("E_geometric_domain_derived_empty", "UNKNOWN"))
            ] += 1
    return list(groups.values())


def main():
    assert os.sched_getaffinity(0) == {3}
    start = time.monotonic()
    try:
        nine, nine_selection = select_nine()
        small, small_selection = select_small()
        assert len(nine) <= 128 and len(small) <= 128
        selection = dict(
            fixed_UTC=datetime.now(timezone.utc).isoformat(),
            nine=nine,
            small=small,
            nine_selection=nine_selection,
            small_selection=small_selection,
            note="Selection frozen before any sample rho traversal; small Lfilter used2goal BFS per needed layout, not rho.",
        )
        (HERE / "selected-states.json").write_text(
            json.dumps(selection, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        rows = [classify(s) for s in nine + small]
        checks = boundary_checks()
        reverse = []
        for dataset in ("nine", "small"):
            for result in [r for r in rows if r["dataset"] == dataset][:2]:
                adjacent, a, b, *_ = metrics(result)
                value = bfs(
                    adjacent, [b], f"reversecheck:{dataset}:{result['mask']}:{b}"
                ).get(a)
                assert value == result["rho"]
                reverse.append(
                    dict(
                        dataset=dataset,
                        source=result["origins"][0],
                        rho=value,
                        exact=True,
                    )
                )
        examples = {}
        for row in rows:
            key = row["dataset"] + ":" + row["classification"]
            if len(examples.setdefault(key, [])) < 2:
                examples[key].append(row)
        result = dict(
            status="BOUNDED_SAVED_GEOMETRY_COMPLETE",
            rows=rows,
            groups=summarize(rows),
            representatives=examples,
            selection=dict(nine=nine_selection, small=small_selection),
            boundary_checks=checks,
            reverse_checks=reverse,
            BFS=dict(
                traversals=len(BFS_LOG),
                max_traversals=1024,
                completed=sum(x["status"] == "COMPLETE" for x in BFS_LOG),
                visited_vertices=sum(x.get("visited", 0) for x in BFS_LOG),
                scanned_directed_edges=sum(
                    x.get("scanned_directed_edges", 0) for x in BFS_LOG
                ),
                ledger=BFS_LOG,
            ),
            input_refs=INPUT_REFS,
            core_validation="not rerun; no native legality/HistoryKey certificate from offline accounting",
            per_state_history="derived Eempty on complete saved actions where present; actual core proofleaf qualification UNKNOWN",
            saved_WL_oracle_changed=False,
            new_solver_Search_NN_games_Perf_fit=0,
            maps_pair_cache_scope="invocation-local bounded analysis only; not production cache",
            source_reuse="AST only old405board and old409distances, no oldcheckfixture/pawnedges/ranks/WDL calls",
            costs=dict(
                child_wall_seconds=time.monotonic() - start,
                continuous_peak_or_LLM_fee="UNKNOWN",
            ),
            reader_STOP=datetime.now(timezone.utc).isoformat(),
        )
        (HERE / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        print(
            json.dumps(
                dict(
                    status=result["status"],
                    nine=len(nine),
                    small=len(small),
                    classes={
                        d: dict(
                            Counter(
                                r["classification"] for r in rows if r["dataset"] == d
                            )
                        )
                        for d in ("nine", "small")
                    },
                    BFS=result["BFS"]["traversals"],
                    child_wall_seconds=result["costs"]["child_wall_seconds"],
                )
            )
        )
    finally:
        (HERE / "BFS-ledger.json").write_text(
            json.dumps(
                dict(traversals=len(BFS_LOG), ledger=BFS_LOG), separators=(",", ":")
            )
            + "\n"
        )
        (HERE / "actual-input-refs.json").write_text(
            json.dumps(INPUT_REFS, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
