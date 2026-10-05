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


def lineage_key(prefix):
    def transform(action, lr, rotate):
        assert 0 <= action <= 208
        base, width = (0, 9) if action < 81 else ((81, 8) if action < 145 else (145, 8))
        y, x = divmod(action - base, width)
        if lr:
            x = width - 1 - x
        if rotate:
            y, x = width - 1 - y, width - 1 - x
        return base + y * width + x

    return min(
        tuple(transform(a, lr, rotate) for a in prefix)
        for lr in (False, True)
        for rotate in (False, True)
    )


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
    assert len(plans) == 96
    old = set()
    old_seeds = set()
    for path in cfg["old_label_free_family_maps"]:
        for row in read(path)["families"]:
            old.add(lineage_key(row["prefix"]))
            old_seeds.add(row["actionseed"])
    rows = []
    seen = set()
    for i, plan in enumerate(plans):
        prefix = tuple(plan["prefix"])
        assert (
            len(prefix) == plan["cohort"]
            and lineage_key(prefix) not in old
            and lineage_key(prefix) not in seen
        )
        seen.add(lineage_key(prefix))
        actionseed = prereg["block_seeds"][i // 48] ^ (
            (((i % 48) + 1) * 0x9E3779B97F4A7C15) % (1 << 64)
        )
        assert actionseed not in old_seeds
        rows.append(
            dict(
                plan,
                canonical_family=f"frame23-299-family-{i:06d}",
                local_id=i % 48,
                block=i // 48,
                cohort_pair=prereg["cohorts"].index(plan["cohort"]) // 2,
                native_family=f"{prereg['run_ids'][i // 48]}-family-{i % 48:06d}",
                native_run_id=prereg["run_ids"][i // 48],
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
    assert sum(r["opening_side"] == 1 for r in rows) == 48
    assert len({r["actionseed"] for r in rows}) == 96
    native_paths = []
    for block in range(2):
        subset = rows[block * 48 : (block + 1) * 48]
        assert len(subset) == 48 and sum(r["opening_side"] == 1 for r in subset) == 24
        native = read(cfg["native_template"])
        native.update(
            run_id=prereg["run_ids"][block],
            output=cfg["native_outputs"][block],
            games=48,
            train_games=0,
            validation_games=0,
            seed=prereg["block_seeds"][block],
            openings=[r["prefix"] for r in subset],
            wall_seconds=270.0,
            max_output_bytes=8 * 1024**2,
            deadline_unix_ms=int(
                datetime.fromisoformat(prereg["science_stop"]).timestamp() * 1000
            ),
        )
        assert native["simulations"] == 64 and native["max_plies"] == 200
        assert native["active_games"] == 48 and native["temperature"] == 1.0
        assert native["cpu_cores"] == [2] and native["inference_cpu_core"] == 4
        assert native["max_memory_bytes"] <= 1879048192
        write(cfg["native_configs"][block], native)
        native_paths.append(cfg["native_configs"][block])
    write(
        cfg["family_map"],
        {
            "task": "native-z-fresh-evaluation-299-v1",
            "schema": "native-z-fresh-evaluation-family-map-v1",
            "families": rows,
            "planned": 96,
            "starting_side_counts": {"P1": 48, "P2": 48},
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
            "task": cfg["task"],
            "schema": "native-z-fresh-evaluation-preparation-v1",
            "UTC": datetime.now(timezone.utc).isoformat(),
            "NN": 0,
            "model_science_entries": 0,
            "native_configs_SHA": {p: sha(p) for p in native_paths},
            "family_map_SHA": sha(cfg["family_map"]),
            "source_hashes": cfg["source_hashes"],
            "whole_command_wall_s": time.monotonic() - began,
            "typed_prefix_attempt_failures": raw["typedfailures"],
        },
    )


if __name__ == "__main__":
    main()
