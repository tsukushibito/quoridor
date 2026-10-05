"""Register one target-blind RuleA transfer cohort using the stopped native planner."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x") as output:
        output.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    cfg = read(parser.parse_args().config)
    began = time.monotonic()
    for path, expected in cfg["source_hashes"].items():
        assert sha(path) == expected, "SOURCE_SHA:" + path
    prereg = read(cfg["preregister"])
    native_prep = read(cfg["native_prepare"])
    assert native_prep["seed"] == prereg["prefix_seed"]
    subprocess.run(cfg["argv"], check=True)
    raw = read(native_prep["output"])
    assert raw["NN"] == 0 and not raw["new_game_results_seen"]
    assert raw["schema"] == "teacher-opening-plan-v1"
    order = {n: i for i, n in enumerate(prereg["cohorts"])}
    plans = sorted(raw["plans"], key=lambda p: (p["ordinal"], order[p["cohort"]]))
    assert len(plans) == 48
    old = set()
    old_seeds = set()
    for path in cfg["old_label_free_family_maps"]:
        for row in read(path)["families"]:
            old.add(tuple(row["prefix"]))
            old_seeds.add(row["actionseed"])
    rows = []
    seen = set()
    for i, plan in enumerate(plans):
        prefix = tuple(plan["prefix"])
        assert len(prefix) == plan["cohort"] and prefix not in old and prefix not in seen
        seen.add(prefix)
        actionseed = prereg["game_seed"] ^ (((i + 1) * 0x9E3779B97F4A7C15) % (1 << 64))
        assert actionseed not in old_seeds
        rows.append(
            dict(
                plan,
                canonical_family=f"frame23-292-family-{i:06d}",
                local_id=i,
                native_family=f"{prereg['run_id']}-family-{i:06d}",
                native_run_id=prereg["run_id"],
                split="test",
                split_purpose="sealed_rulea_transfer_observation",
                opening_side=1 + len(prefix) % 2,
                prefix_SHA=hashlib.sha256(
                    json.dumps(list(prefix), separators=(",", ":")).encode()
                ).hexdigest(),
                actionseed=actionseed,
                status="NOT_STARTED",
            )
        )
    assert sum(r["opening_side"] == 1 for r in rows) == 24
    assert len({r["actionseed"] for r in rows}) == 48
    native = read(cfg["native_template"])
    native.update(
        run_id=prereg["run_id"],
        output=cfg["native_output"],
        games=48,
        train_games=0,
        validation_games=0,
        seed=prereg["game_seed"],
        openings=[r["prefix"] for r in rows],
        wall_seconds=560.0,
        max_output_bytes=24 * 1024**2,
        deadline_unix_ms=int(datetime.fromisoformat(prereg["science_stop"]).timestamp() * 1000),
    )
    assert native["simulations"] == 64 and native["max_plies"] == 200
    assert native["active_games"] == 48 and native["temperature"] == 1.0
    assert native["cpu_cores"] == [2] and native["inference_cpu_core"] == 4
    write(cfg["native_config"], native)
    write(
        cfg["family_map"],
        {
            "task": "rulea-z-transfer-292-v1",
            "schema": "rulea-z-transfer-family-map-v1",
            "families": rows,
            "planned": 48,
            "starting_side_counts": {"P1": 24, "P2": 24},
            "preregister_SHA": sha(cfg["preregister"]),
            "firstaccepted_native_plan_SHA": sha(native_prep["output"]),
            "labels_or_outcomes_used": False,
            "independence_scope": "registered lineage; IID or all-state disjointness unproved",
            "history_cross_public": "UNAVAILABLE for public rows; no nonexposure guarantee",
        },
    )
    write(
        cfg["output"],
        {
            "task": "rulea-z-transfer-292-prepare-v1",
            "schema": "rulea-z-transfer-preparation-v1",
            "UTC": datetime.now(timezone.utc).isoformat(),
            "NN": 0,
            "model_science_entries": 0,
            "native_config_SHA": sha(cfg["native_config"]),
            "family_map_SHA": sha(cfg["family_map"]),
            "source_hashes": cfg["source_hashes"],
            "whole_command_wall_s": time.monotonic() - began,
            "typed_prefix_attempt_failures": raw["typedfailures"],
        },
    )


if __name__ == "__main__":
    main()
