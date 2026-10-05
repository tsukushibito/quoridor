"""Recover only complete JSON objects from a stopped, truncated recording."""

import hashlib
import json
from pathlib import Path
import time

BASE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    raw = BASE / "measurement-result.partial.json"
    text = raw.read_text()
    decoder = json.JSONDecoder()
    marker = '"records":['
    cursor = text.index(marker) + len(marker)
    records = []
    while cursor < len(text):
        try:
            record, after = decoder.raw_decode(text, cursor)
        except json.JSONDecodeError:
            break
        records.append(record)
        cursor = after
        if text[cursor : cursor + 1] != ",":
            break
        cursor += 1
    # Object header counters were serialized before the interrupted record array.
    header = json.loads(text[: text.index(marker)].rstrip(",") + "}")
    config = json.loads((BASE / "measurement-config.json").read_text())
    qualification = json.loads((BASE / "qualify-result.json").read_text())
    observed = {(r["id"], r["result"]["K"]): r for r in records}
    denominator = []
    for i, root in enumerate(config["roots"]):
        for j in range(3):
            k = config["ks"][(i + j) % 3]
            r = observed.get((root["id"], k))
            denominator.append(
                {
                    **root,
                    "K": k,
                    "status": r["result"]["status"] if r else "UNKNOWN_NOT_RECORDED",
                    "unstarted_not_inferred": r is None,
                }
            )
    pairs = []
    for root in config["roots"]:
        for a, b in [(64, 256), (256, 1024), (64, 1024)]:
            ra, rb = observed.get((root["id"], a)), observed.get((root["id"], b))
            if ra is None or rb is None:
                continue
            va, vb = ra["result"], rb["result"]
            assert va["status"] == vb["status"] == "COMPLETE"
            assert va["root_visits"] == a and vb["root_visits"] == b
            assert va["action"] in va["legal"] and vb["action"] in vb["legal"]
            ea = {e["action"]: e["visits"] for e in va["edges"]}
            eb = {e["action"]: e["visits"] for e in vb["edges"]}
            ma, mb = sum(ea.values()), sum(eb.values())
            l1 = sum(abs(ea.get(t, 0) / ma - eb.get(t, 0) / mb) for t in set(ea) | set(eb))
            d = ra["D0_8"]
            pairs.append(
                {
                    "id": root["id"],
                    "phase": root["phase"],
                    "split": root["split"],
                    "K_pair": [a, b],
                    "action": [va["action"], vb["action"]],
                    "action_change": va["action"] != vb["action"],
                    "rootmean": [va["rootmean"], vb["rootmean"]],
                    "delta_rootmean": vb["rootmean"] - va["rootmean"],
                    "D0_8": d,
                    "D_residual": [va["rootmean"] - d, vb["rootmean"] - d],
                    "pi_L1_edge_visit_normalized": l1,
                    "edge_visit_mass": [ma, mb],
                    "search_seconds": [va["seconds"], vb["seconds"]],
                    "terminal_origin": [va["terminal_origin"], vb["terminal_origin"]],
                    "highK_is_truth": False,
                }
            )
    report = {
        "task": "teacher-budget-282-v1",
        "schema": "teacher-budget-salvage-v1",
        "raw_SHA": digest(raw),
        "raw_json": "TRUNCATED_PRESERVED",
        "completed_objects": len(records),
        "records": records,
        "denominator": denominator,
        "planned_root_count": 36,
        "registered_root_count": 32,
        "not_available_root_count": 4,
        "planned_K_conditions": 108,
        "registered_K_conditions": 96,
        "not_available_K_conditions": 12,
        "recorded_complete": len(records),
        "unknown_not_recorded": 96 - len(records),
        "serialized_header_counters": header,
        "main_physical_NN_source_bound": header["logical_NN"] + 36,
        "main_physical_NN_evidence": "header counter before synchronous interrupted serialization; fixed TensorRtBackend B1..8 warm36; no inference progresses during this writer",
        "main_NN_conservative_config_upper": config["nn_cap"],
        "qualification_physical_NN": qualification["physical_NN"],
        "total_physical_NN_source_bound": header["logical_NN"] + 36 + qualification["physical_NN"],
        "total_physical_NN_conservative_upper": config["nn_cap"] + qualification["physical_NN"],
        "pairs": pairs,
        "pair_root_count": len({p["id"] for p in pairs}),
        "phase_population_sensitivity": "NOT_ESTABLISHED",
        "all_main_roots_P1": True,
        "no_seed_variance": True,
        "no_rerun": True,
        "analysis_NN": 0,
        "analysis_seconds": time.monotonic() - start,
    }
    (BASE / "salvage-result.json").write_text(
        json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["records", "denominator"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
