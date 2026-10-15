"""Collect the original twelve completed operations; never execute a search."""

import importlib.util
import math
from pathlib import Path
from statistics import median
import struct
import sys

ROOT = Path("/workspaces/quoridor")
BASE = Path(__file__).resolve().parent
OUT = BASE / "cost96-v1/collection-v1"
loader = importlib.util.spec_from_file_location(
    "lc", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
sys.modules["lc"] = lc
loader.loader.exec_module(lc)


def main():
    OUT.mkdir()
    refs, identities, passes = [], [], []

    def read(ref):
        refs.append(ref)
        return lc.document(ref)

    def absent(original):
        current = lc.process.identity(lc.process.process_info(original["pid"]))
        assert current != original
        identities.append(dict(original=original, current=current))

    settings = read(lc.artifact_ref(BASE / "cost96-v1/settings.json"))
    outer = read(lc.artifact_ref(BASE / "cost96-v1/job/result.json"))
    assert outer["exit_code"] == 0 and outer["direct_child_reaped"]
    assert outer["cleanup_complete"] and not outer["remaining"]
    assert not outer["cleanup_errors"]
    seq_ref = lc.artifact_ref(Path(settings["output"]) / "result.json")
    seq = read(seq_ref)
    assert seq["status"] == "PASS" and seq["completed_operations"] == 12
    assert seq["selected_operations"] == 12 and len(seq["operations"]) == 12
    assert seq["cleanup_complete"] and not seq["remaining"]
    absent(seq["originating_job"]["child"])
    for i, op in enumerate(seq["operations"]):
        assert op["kind"] == "measure" and op["index"] == i and op["completed"]
        job = read(op["job_result"])
        assert job["exit_code"] == 0 and job["direct_child_reaped"]
        assert job["cleanup_complete"] and not job["remaining"]
        assert not job["cleanup_errors"]
        m = read(op["manifest"])
        assert m["status"] == "PASS" and m["cleanup_complete"]
        assert not m["remaining"] and m["data"]["status"] == "PASS"
        intent = read(m["intent"])
        assert not Path(intent["TMP"]).exists()
        absent(m["originating_job"]["child"])
        for check in m["checks"]:
            assert check["status"] == "PASS" and check["capture_complete"]
            receipt = read(check["persisted_process_receipt"])
            assert receipt["direct_child_reaped"]
            assert receipt["process_cleanup_complete"]
            assert receipt["handle_closes_complete"] and not receipt["remaining"]
            absent(receipt["child"])
        for ref in m["data"]["files"]:
            lc.read_ref(ref, ref["bytes"])
            refs.append(ref)
        e = m["data"]["measurement"]
        assert e["journal_result_rows_agree"] and not e["unreturned_tail"]
        assert not e["journal_partial_tail"]
        snap, result = e["settings"], e["result"]
        expected = read(settings["measurements"][i]["experiment"])
        cfg = read(expected["config"])
        assert snap["artifact"] == settings["measurements"][i]["artifact"]
        assert snap["code_build"] == expected["build_manifest"]
        assert snap["execution"]["models"] == expected["models"]
        assert snap["execution"]["inputs"] == expected["inputs"]
        # RootInput serde(default) adds these three fields to the saved snapshot.
        resolved_cfg = {**cfg, "roots": [dict(root) for root in cfg["roots"]]}
        for root in resolved_cfg["roots"]:
            root.setdefault("jsonl_match", None)
            root.setdefault("prefix_len", None)
            root.setdefault("check_history", False)
        assert snap["settings"] == resolved_cfg
        requests = read(expected["schedule"])
        assert snap["requests"] == requests
        assert cfg["tt_entries"] == 1048576 and cfg["use_tt"] and cfg["use_pvs"]
        assert result["calls"] == result["attempted"] == result["planned"] == 8
        assert not result["errors"] and not result["remaining_requests"]
        assert result["extra_calls"] == result["unperformed"] == 0
        assert result["unscheduled"] == 0
        domains = [d for d in result["session_domains"] if d["domain"] == "reset"]
        assert len(domains) == 4
        assert all(d["facts"]["TT_capacity"] == [1048576, 83886128] for d in domains)
        rows = []
        for row, request in zip(result["measurements"], requests, strict=True):
            v = row["measurement"]
            assert row["request"] == request
            assert not request["diagnostic"] and not request["observe_completed_depths"]
            assert not request["warmup"] and request["time_limit_ms"] is None
            assert v["returned"] == "Ok" and v["parent_unchanged"]
            root_walls = [6, 4, 2, 0][request["root"]]
            assert v["root_walls_remaining"] == root_walls
            threshold = cfg["zero_stock_approx_min_root_walls"]
            permitted = threshold is not None and root_walls >= threshold
            assert v["zero_stock_approx_permitted"] == permitted
            assert v["zero_stock_approx_min_root_walls"] == threshold
            if not permitted:
                assert (
                    v["zero_stock_approx_method"] is None
                    and v["work"]["zero_stock_approx_terminations"] == 0
                )
            else:
                assert (
                    v["zero_stock_approx_method"]
                    == "zero-stock406-wall-distance-stm-tie-win-v1"
                )
            assert request["depth"] == 8 and request["node_cap"] == 4000000
            if v["status"] == "UNKNOWN":
                assert (
                    v["stop"] == "NodeLimit"
                    and v["work"]["nodes"] == 4000000
                    and v["completed_depth"] < 8
                )
            else:
                assert v["status"] == "COMPLETE" and v["completed_depth"] == 8

            legal = v["root_legal_action_ids"]
            assert len(legal) == len(set(legal)) and v["action"] in legal
            assert v["PV"] and v["PV"][0] == v["action"]
            assert math.isfinite(v["value"])
            assert (
                struct.unpack("<I", struct.pack("<f", v["value"]))[0] == v["value_bits"]
            )
            assert v["work"]["TT_illegal_moves"] == 0
            assert v["work"]["TT_retained_bytes"] == 83886128
            assert v["work"]["nodes"] <= request["node_cap"]
            if not cfg["lmr"]:
                assert all(v["work"][k] == 0 for k in v["work"] if k.startswith("LMR_"))
            rows.append(row)
        passes.append(
            dict(
                index=i,
                profile=cfg["profile"],
                LMR=cfg["lmr"],
                threshold=cfg["zero_stock_approx_min_root_walls"],
                evaluator="nnue" if i < 6 else "distance",
                manifest=op["manifest"],
                whole_seconds=result["whole_before_result_publication_seconds"],
                setup_seconds=result["setup_seconds"],
                drop_seconds=result["target_drop_seconds"],
                rows=rows,
            )
        )
    conditions = []
    root_summary = []
    for start in (0, 6):
        for threshold, offsets in ((None, (0, 5)), (4, (1, 4)), (0, (2, 3))):
            ps = [passes[start + offset] for offset in offsets]

            def sig(row):
                return {
                    k: row["measurement"][k]
                    for k in (
                        "status",
                        "stop",
                        "completed_depth",
                        "value_bits",
                        "action",
                        "PV",
                        "work",
                        "root_walls_remaining",
                        "zero_stock_approx_permitted",
                    )
                }

            exact = all(
                sig(a) == sig(b)
                and a["root"] == b["root"]
                and a["request"] == b["request"]
                for a, b in zip(ps[0]["rows"], ps[1]["rows"], strict=True)
            )
            assert exact
            conditions.append(
                dict(
                    evaluator=ps[0]["evaluator"],
                    threshold=threshold,
                    whole_seconds=[p["whole_seconds"] for p in ps],
                    whole_median_seconds=median(p["whole_seconds"] for p in ps),
                    setup_seconds=[p["setup_seconds"] for p in ps],
                    drop_seconds=[p["drop_seconds"] for p in ps],
                    COMPLETE=sum(
                        r["measurement"]["status"] == "COMPLETE"
                        for p in ps
                        for r in p["rows"]
                    ),
                    UNKNOWN=sum(
                        r["measurement"]["status"] == "UNKNOWN"
                        for p in ps
                        for r in p["rows"]
                    ),
                    repeat_depth_value_action_PV_allwork_exact=exact,
                )
            )
            for j in range(8):
                rs = [p["rows"][j] for p in ps]
                v = rs[0]["measurement"]
                root_summary.append(
                    dict(
                        evaluator=ps[0]["evaluator"],
                        threshold=threshold,
                        root=j // 2,
                        root_walls=v["root_walls_remaining"],
                        temperature="cold" if j % 2 == 0 else "warm",
                        status=v["status"],
                        stop=v["stop"],
                        depth=v["completed_depth"],
                        value_bits=v["value_bits"],
                        action=v["action"],
                        PV=v["PV"],
                        permitted=v["zero_stock_approx_permitted"],
                        Search_seconds=[
                            r["measurement"]["Search_call_seconds"] for r in rs
                        ],
                        Search_median_seconds=median(
                            r["measurement"]["Search_call_seconds"] for r in rs
                        ),
                        body_seconds=[
                            r["root_body_including_journal_seconds"] for r in rs
                        ],
                        body_median_seconds=median(
                            r["root_body_including_journal_seconds"] for r in rs
                        ),
                        work=v["work"],
                    )
                )
    assert refs == [lc.artifact_ref(ref["path"]) for ref in refs]
    rows = [r for p in passes for r in p["rows"]]
    lc.new_json(
        OUT / "result.json",
        dict(
            at=lc.stamp(),
            calls=len(rows),
            sessions=48,
            node_cap=384000000,
            nodes=sum(r["measurement"]["work"]["nodes"] for r in rows),
            COMPLETE=sum(r["measurement"]["status"] == "COMPLETE" for r in rows),
            UNKNOWN=sum(r["measurement"]["status"] == "UNKNOWN" for r in rows),
            passes=passes,
            conditions=conditions,
            root_summary=root_summary,
            refs=refs,
            actual_TT_capacity=1048576,
            actual_TT_retained_bytes=83886128,
            RSS_peak="UNKNOWN",
            outer_seconds=outer["wall_seconds"],
            new_Search_calls=0,
        ),
    )
    lc.new_json(
        OUT / "STOP.json",
        dict(
            at=lc.stamp(),
            sequence=seq_ref,
            actual_sequence_reader_STOP=seq["reader_STOP"],
            identities=identities,
            TMP_absent=True,
            owned_readers_writers_children_jobs_handles_TMP_leases=[],
        ),
    )
    print(
        {
            "calls": len(rows),
            "nodes": sum(r["measurement"]["work"]["nodes"] for r in rows),
            "conditions": conditions,
        }
    )


if __name__ == "__main__":
    main()
