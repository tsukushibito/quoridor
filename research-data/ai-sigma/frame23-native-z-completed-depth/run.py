"""One admitted, bounded maintained native depth-one caller; no model math."""

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import struct
import subprocess
import time


def validate_output(native, witness):
    if native["schema"] != "native-nnue-diagnosis-v1":
        raise ValueError("native purpose schema")
    if native["NN"] > 2000 or native["processed"] > 5000 or not native["parent_history_preserved"]:
        raise ValueError("counted cap/root parent preservation")
    roots = {p["root"]: p for p in native["predictions"] if "values" in p}
    expected_engines = {"native-z-BEST1000", "D0b8"}
    if set(roots) != set(range(4)) or len(native["searches"]) != 8:
        raise ValueError("four roots/eight fixed searches")
    for ix, row in enumerate(witness["rows"]):
        root = roots[ix]
        feat = root["feature"]
        if root["prefix"] != row["prefix"] or feat["key"] != row["state_key"]:
            raise ValueError("fixed prefix/state identity")
        if sorted(feat["history"]) != sorted(row["history_literal"]):
            raise ValueError("full literal history changed")
        side = feat["side"] + 1
        stm_ids = feat["ids"] if side == 1 else feat["ids"][::-1]
        bits = [struct.unpack("<I", struct.pack("<f", v))[0] for v in feat["distance"]]
        if (
            side != row["side"]
            or stm_ids != row["actualSTM_ids"]
            or bits != row["STM_distance_f32bits"]
        ):
            raise ValueError("P2/STM input bits")
        if {v["engine"] for v in root["values"]} != expected_engines:
            raise ValueError("fixed root evaluators")
        if any(not math.isfinite(v["value"]) for v in root["values"]):
            raise ValueError("nonfinite root leaf value")
    pairs = []
    for ix in range(4):
        rows = [r for r in native["searches"] if r["root"] == ix]
        if len(rows) != 2 or {r["engine"] for r in rows} != expected_engines:
            raise ValueError("fixed same-depth search pair")
        for row in rows:
            if (
                row["requested_depth"] != 1
                or row["completed_depth"] != 1
                or row["stop"] != "DepthComplete"
            ):
                raise ValueError("INCOMPLETE_REQUESTED_DEPTH")
            if not row["completed"] or row["completed"][-1]["depth"] != 1:
                raise ValueError("no completed iteration proof")
            if row["nodes"] > 2048 or not math.isfinite(row["value"]):
                raise ValueError("nodeguard/nonfinite")
            if row["Action"] is None or not row["pv"] or row["pv"][0] != row["Action"]:
                raise ValueError("completed Action/PV identity")
            if row["argmax_all_exact"] != "NOT_RECORDED":
                raise ValueError("unexpected exact vector semantics")
        neural = next(r for r in rows if r["engine"] == "native-z-BEST1000")
        distance = next(r for r in rows if r["engine"] == "D0b8")
        pairs.append(
            {
                "root": ix,
                "input_id": witness["rows"][ix]["id"],
                "canonical_family": witness["rows"][ix]["canonical_family"],
                "side": witness["rows"][ix]["side"],
                "requested_completed_depth": 1,
                "native": neural,
                "D": distance,
                "Action_changed": neural["Action"] != distance["Action"],
                "native_minus_D_value": neural["value"] - distance["value"],
                "full_legal_leaf_vector": "NOT_RECORDED",
            }
        )
    for row in native["predictions"]:
        if "child_action" in row:
            if (
                not row["parent_preserved"]
                or not math.isfinite(row["full"])
                or not math.isfinite(row["delta"])
            ):
                raise ValueError("full/delta/nonfinite/parent")
            if abs(row["full"] - row["delta"]) > 1e-5 + 1e-4 * abs(row["full"]):
                raise ValueError("full/delta tolerance")
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    regpath = Path(parser.parse_args().registration)
    reg = json.loads(regpath.read_text())
    if reg["task"] != "native-z-completed-depth-301-v1":
        raise ValueError("unregistered purpose")
    spec = importlib.util.spec_from_file_location("h", reg["helpers"])
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    os.sched_setaffinity(0, {3})
    scope = Path(reg["scope"])
    if (scope / "science-start-v1.json").exists():
        raise ValueError("MAX1 already consumed; no retry")
    for path, digest in reg["input_SHA"].items():
        if h.sha(path) != digest:
            raise ValueError("registered input/source SHA changed: " + path)
    if reg["argv"] != [reg["native_binary"], "--config", reg["native_config"]]:
        raise ValueError("native CLI argv")
    cfg = h.read(reg["native_config"])
    if (
        cfg["depths"] != [1]
        or cfg["cpu_core"] != 3
        or cfg["nn_cap"] != 2000
        or cfg["processed_cap"] != 5000
    ):
        raise ValueError("fixed depth/resource config")
    if (
        cfg["mode"] != "diagnose"
        or len(cfg["prefixes"]) != 4
        or [e["id"] for e in cfg["engines"]] != ["native-z-BEST1000", "D0b8"]
    ):
        raise ValueError("fixed input/evaluator tuple")
    for issue in ("quoridor-4lc", "quoridor-4lc.301"):
        run = subprocess.run(
            ["bash", "/workspaces/quoridor/scripts/dev/beads.sh", "show", issue, "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        item = json.loads(run.stdout)[0]
        if item["status"] != "in_progress" or any("pause" in v for v in item.get("labels", [])):
            raise ValueError("issue pause/status")
        if issue.endswith(".301") and item["assignee"] != reg["owner"]:
            raise ValueError("owner changed")
    receipt, operation = h.read(reg["loaded"]), h.read(reg["registry"])["current_operation"]
    state = h.read(Path(operation["state_dir"]) / "state.json")
    expectation = h.read(operation["expectations_path"])
    if operation["frame"] != 23 or state["phase"] != "running" or not receipt["PASS"]:
        raise ValueError("wrong current phase/frame")
    if state["process"] != receipt["scheduler"] or not all(
        h.exact(receipt[k]) for k in ("scheduler", "monitor")
    ):
        raise ValueError("current loaded PIDtick")
    if (
        state["config_sha256"] != receipt["loaded_config_sha"]
        or state["contract_sha256"] != receipt["loaded_contract_sha"]
    ):
        raise ValueError("loaded config/contract")
    for path, digest in expectation["input_hashes"].items():
        if h.sha(path) != digest:
            raise ValueError("new current24 mismatch")
    storage = h.read(reg["storage"])
    if (
        not all(storage["conditions"].values())
        or storage["total"] >= storage["cap"]
        or storage["301"]["root"] != str(scope)
        or storage["errors"]
        or h.sha(reg["storage"]) != reg["storage_SHA"]
    ):
        raise ValueError("fresh storage admission")
    current = sum(p.stat().st_blocks * 512 for p in scope.rglob("*") if p.is_file())
    if current + reg["remaining_output_archive_Git_metadata_B"] > 1536 * 1024:
        raise ValueError("inclusive local1.5MiB guard")
    deadline = datetime.fromisoformat(reg["end_at"].replace("Z", "+00:00"))
    if (deadline - datetime.now(timezone.utc)).total_seconds() < 35:
        raise ValueError("hard30 plus reap unavailable")
    ps = h.snapshot()
    own = h.ancestors(os.getpid(), ps)

    def scientific(p):
        if h.science(p):
            return True
        a = p["argv"]
        script = next((s for s in a[1:] if not s.startswith("-")), "") if a else ""
        return bool(
            a
            and (
                "/rust-migration/target/" in a[0]
                or (Path(a[0]).name.startswith("python") and "/research-data/ai-sigma/" in script)
            )
        )

    foreign = [p for p in ps if p["pid"] not in own and scientific(p)]
    gpu = h.gpu_state()
    available = next(
        int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    if foreign or gpu or available < 1024**3:
        h.write(
            scope / "entry-refusal-v1.json",
            {"foreign": foreign, "GPU": gpu, "MemAvailable": available, "MAX1_consumed": False},
        )
        raise ValueError("actual foreign compute/GPU/RAM")
    h.write(
        scope / "admission-v1.json",
        {
            "UTC": datetime.now(timezone.utc).isoformat(),
            "scheduler": receipt["scheduler"],
            "monitor": receipt["monitor"],
            "current24": len(expectation["input_hashes"]),
            "owned": state["owned"],
            "actual_foreign_compute": foreign,
            "GPU": gpu,
            "MemAvailable": available,
            "storage_SHA": reg["storage_SHA"],
            "current_local_B": current,
            "remaining_B": reg["remaining_output_archive_Git_metadata_B"],
            "CPU": [3],
            "hostfuturequiet_guaranteed": False,
        },
    )
    native = None
    started = time.monotonic()
    identities, reason, peak = {}, None, 0
    try:
        with (
            (scope / "native-stdout-v1.log").open("wb") as stdout,
            (scope / "native-stderr-v1.log").open("wb") as stderr,
        ):
            native = subprocess.Popen(
                reg["argv"],
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                env=dict(os.environ, ORT_DISABLE_TELEMETRY="1"),
            )
            identity = h.proc(native.pid)
            h.write(
                scope / "science-start-v1.json",
                {
                    "task": reg["task"],
                    "UTC": datetime.now(timezone.utc).isoformat(),
                    "identity": identity,
                    "argv": reg["argv"],
                    "source_SHA": h.sha(reg["source"]),
                    "registration_SHA": h.sha(regpath),
                    "MAX1_consumed": True,
                    "NN_reserved": 2000,
                    "processed_reserved": 5000,
                },
            )
            while native.poll() is None:
                ps = h.snapshot()
                family = [p for p in ps if p["pgrp"] == native.pid]
                identities.update({(p["pid"], p["start_ticks"]): p for p in family})
                peak = max(peak, h.proc(os.getpid())["rss"] + sum(p["rss"] for p in family))
                if peak > 448 * 1024**2 or any(p["cpus"] != [3] for p in family):
                    reason = "RAM_OR_AFFINITY"
                if any(
                    p["pid"] not in own and p["pgrp"] != native.pid and scientific(p) for p in ps
                ):
                    reason = "FOREIGN_COMPUTE"
                if time.monotonic() - started >= 30:
                    reason = "TIME"
                if reason:
                    break
                time.sleep(0.025)
            if native.poll() is None:
                os.killpg(native.pid, signal.SIGTERM)
            native.wait(timeout=3)
    finally:
        if native is not None:
            if native.poll() is None:
                os.killpg(native.pid, signal.SIGTERM)
                native.wait(timeout=3)
            remaining = [p for p in identities.values() if h.exact(p)]
            group = [p for p in h.snapshot() if p["pgrp"] == native.pid]
            stop = {
                "task": reg["task"],
                "UTC": datetime.now(timezone.utc).isoformat(),
                "exit": native.returncode,
                "reason": reason,
                "command_wall_s": time.monotonic() - started,
                "sampled_manager_family_peak_RSS_B": peak,
                "child_waited": True,
                "recorded_children": list(identities.values()),
                "currentexact": remaining,
                "current_process_group": group,
                "MAX1_consumed": True,
            }
            h.write(scope / "science-stop-v1.json", stop)
            if remaining or group:
                raise ValueError("owned identity not reaped")
    if native.returncode or reason:
        h.write(
            scope / "result-v1.json",
            {
                "task": reg["task"],
                "schema": "native-z-completed-depth-result-301-v1",
                "status": "INCOMPLETE",
                "raw_output_preserved": True,
                "reason": reason,
                "native_exit": native.returncode,
            },
        )
        raise ValueError("incomplete; no retry")
    raw = h.read(reg["native_output"])
    pairs = validate_output(raw, h.read(reg["witness"]))
    result = {
        "task": reg["task"],
        "schema": "native-z-completed-depth-result-301-v1",
        "status": "FINITE_SAME_COMPLETED_DEPTH1",
        "native_output_SHA": h.sha(reg["native_output"]),
        "config_SHA": h.sha(reg["native_config"]),
        "NN": raw["NN"],
        "processed": raw["processed"],
        "command_whole_s": stop["command_wall_s"],
        "native_whole_s": raw["wall_s"],
        "pairs": pairs,
        "parent_history_preserved": True,
        "full_legal_leaf_value_vector": "NOT_RECORDED",
        "no_labels_models_fit_newgames": True,
        "samewall_strength_or_deep_truth": False,
    }
    h.write(scope / "result-v1.json", result)
    print(
        json.dumps(
            {
                "task": reg["task"],
                "status": result["status"],
                "NN": raw["NN"],
                "processed": raw["processed"],
            }
        )
    )


if __name__ == "__main__":
    main()
