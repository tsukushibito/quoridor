"""Saved-cost scenario calculation; no label bodies or numerical frameworks."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time

ROOT = Path("/workspaces/quoridor")
SCOPE = Path(__file__).parent
PRODUCER = ROOT / "research-data/ai-sigma/frame22-teacher-throughput"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(identity):
    if not identity:
        return False
    try:
        tail = Path(f"/proc/{identity['pid']}/stat").read_text().rsplit(")", 1)[1].split()
        return tail[19] == str(identity["start_ticks"])
    except (OSError, KeyError, IndexError):
        return False


def admission():
    registry_path = ROOT / ".artifacts/research-team/registry.json"
    registry = load(registry_path)
    operation = registry["current_operation"]
    base = Path(operation["config_path"]).parent
    state = load(Path(operation["state_dir"]) / "state.json")
    expected = load(base / "expectations.json")
    monitor = load(base / "monitor-process.json")["process"]
    config = load(base / "scheduler.json")
    checks = {p: sha(Path(p)) == digest for p, digest in expected["input_hashes"].items()}
    foreign = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) in (os.getpid(), os.getppid()):
            continue
        try:
            comm = (proc / "comm").read_text().strip()
            if comm in ("bash", "sh", "rg", "timeout"):
                continue
            argv = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            tokens = (
                "teacher-budget",
                "teacher-qualify",
                "quoridor-runner",
                "quoridor_training",
                "route-feature-diagnose",
                "profile-279",
                "rustc ",
                "cargo build",
            )
            if any(token in argv for token in tokens):
                foreign.append(
                    {
                        "pid": int(proc.name),
                        "argv": argv[:400],
                        "affinity": sorted(os.sched_getaffinity(int(proc.name))),
                    }
                )
        except (OSError, ProcessLookupError):
            pass
    available = next(
        int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemAvailable:")
    )
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "state_phase": state["phase"],
        "config_SHA": sha(base / "scheduler.json"),
        "contract_SHA": sha(base / "contract.json"),
        "loaded_config_match": state["config_sha256"] == sha(base / "scheduler.json"),
        "loaded_contract_match": state["contract_sha256"] == sha(base / "contract.json"),
        "current24_hash_checks": checks,
        "scheduler": state["process"],
        "monitor": monitor,
        "scheduler_exact": exact(state["process"]),
        "monitor_exact": exact(monitor),
        "owned": state.get("owned"),
        "natural_next_epoch": state.get("next_at"),
        "foreign_compute": foreign,
        "CPU_affinity": sorted(os.sched_getaffinity(0)),
        "MemAvailable_B": available,
        "parent_end": "2026-10-05T23:36:03Z",
        "fixed_clock_measurement": False,
        "point_only": True,
    }
    record["PASS"] = (
        state["phase"] == "running"
        and all(checks.values())
        and record["loaded_config_match"]
        and record["loaded_contract_match"]
        and record["scheduler_exact"]
        and record["monitor_exact"]
        and not foreign
        and available > 512 * 1024**2
        and record["CPU_affinity"] == [1]
        and config["end_at"] == "2026-10-05T23:31:03Z"
    )
    (SCOPE / "analysis-admission.json").write_text(json.dumps(record, indent=2) + "\n")
    assert record["PASS"], "Current physics/binding refusal; no scenario analysis executed"


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    start = time.monotonic()
    admission()
    refs = [
        PRODUCER / "comparison-v1.json",
        PRODUCER / "cost-scenarios-v1.json",
        PRODUCER / "274-cache-handoff-v1.json",
        PRODUCER / "active48-r1-data/dataset/manifest.json",
        PRODUCER / "canonical-active48-cache-v1/cache.json",
        ROOT / "research-data/ai-sigma/frame22-teacher-transfer/B-summary.json",
        ROOT / "research-data/ai-sigma/frame22-residual-penalty/summary-v1.json",
        ROOT / "research-data/ai-sigma/frame22-residual-penalty/saved-comparison-v1.json",
    ]
    comparison, cost, handoff, manifest, _, b, _, paired = [load(p) for p in refs]
    selected = comparison["conditions"]["48"]
    rows = manifest["rows"]
    density = rows / 48
    train_density = handoff["eligible_train_rows"] / handoff["registered_train_groups"]
    arrow_bytes = sum(
        (PRODUCER / "active48-r1-data/dataset" / shard["path"]).stat().st_size
        for shard in manifest["shards"]
    )
    cache_files = {
        p.name: p.stat().st_size
        for p in (PRODUCER / "canonical-active48-cache-v1").iterdir()
        if p.is_file()
    }
    cache_bytes = sum(cache_files.values())
    basis = {
        "families": 48,
        "eligible_rows": rows,
        "eligible_rows_per_family": density,
        "train_rows_per_family": train_density,
        "observed_family_row_min": min(s["rows"] for s in manifest["shards"]),
        "observed_family_row_max": max(s["rows"] for s in manifest["shards"]),
        "physical_NN_per_family": selected["physical_NN"] / 48,
        "physical_NN_per_row": selected["physical_NN"] / rows,
        "generation_guardian_s": selected["whole_guardian_s"],
        "known_opening_cache_s_per_family": cost[
            "production_including_opening_cache_bytecheck_per_game_s"
        ],
        "B_fit_guardian_s": b["stop"]["wall_seconds"],
        "B_training_eval_samples": 328290,
        "B_peak_RSS_B": b["stop"]["peak_family_RSS"],
        "Arrow_bytes": arrow_bytes,
        "cache_bytes": cache_bytes,
        "cache_file_bytes": cache_files,
        "Arrow_plus_cache_bytes_per_row": (arrow_bytes + cache_bytes) / rows,
        "new_scope_no_label_body_reads": True,
    }
    targets = []
    for n in (6000, 10000, 30000):
        need = max(0, n - 5981)
        targets.append(
            {
                "design_train_positions": n,
                "incremental_rows": need,
                "complete_families_nominal": math.ceil(need / train_density),
                "families_assumed_20_to70_rows": [math.ceil(need / 70), math.ceil(need / 20)],
                "families_observed_15_to80_envelope": [math.ceil(need / 80), math.ceil(need / 15)],
                "same256k_row_epoch": 256000 / n,
                "additional512k_row_epoch": 512000 / n,
            }
        )
    rosters = []
    for label, newtrain in [
        ("stage1_expected_crossing", 144),
        ("stage1_max", 240),
        ("stage2_expected_crossing", 672),
        ("stage2_max", 1248),
    ]:
        families = newtrain + 48 + 96
        batches = math.ceil(families / 48)
        totalrows = families * density
        whole_generation_known_s = (
            families * cost["production_including_opening_cache_bytecheck_per_game_s"]
        )
        rosters.append(
            {
                "name": label,
                "new_train_families": newtrain,
                "new_selection_families": 48,
                "sealed_future_eval_families": 96,
                "total_new_unique_families": families,
                "48_family_jobs": batches,
                "total_train_rows_nominal": 5981 + newtrain * train_density,
                "total_new_rows_nominal": totalrows,
                "NN_nominal": selected["physical_NN"] * families / 48,
                "NN_working_20to70rows_40to80NNperrow": [families * 20 * 40, families * 70 * 80],
                "NN_registered_200ply_K64_guard": batches * (48 * 200 * 64 + 36),
                "known_generation_opening_cache_minutes_nominal": whole_generation_known_s / 60,
                "generation_working_minutes": [
                    families * 0.45 / 60 + batches * 5 / 60,
                    families * 2.5 / 60 + batches * 20 / 60,
                ],
                "generation_stress_upper_minutes_3x": 3 * families * 2.5 / 60 + batches * 20 / 60,
                "preparation_qualification_recording_extra_minutes": [15, 45],
                "new_Arrow_plus_cache_bytes_nominal": math.ceil(
                    totalrows * basis["Arrow_plus_cache_bytes_per_row"]
                ),
                "conservative_data_forecast_bytes": math.ceil(
                    families * 70 * basis["Arrow_plus_cache_bytes_per_row"] * 2.5
                ),
                "projection_not_performance_guarantee": True,
            }
        )
    learning = []
    for n in (6000, 10000, 30000):
        # 48 fixed new selection games, planning density 35.83; oldval remains 1248.
        val = math.ceil(48 * density) + 1248
        for seen, evaluations in ((256000, 10), (512000, 15)):
            samples = seen + evaluations * (n + val)
            learning.append(
                {
                    "train_rows_design": n,
                    "train_seen": seen,
                    "evaluations": evaluations,
                    "same_row_epoch": seen / n,
                    "new_selection_rows_nominal": math.ceil(48 * density),
                    "oldval_rows": 1248,
                    "total_train_eval_sample_upper_nominal": samples,
                    "B_guardian_sample_rate_short_extrapolation_s": samples
                    / 328290
                    * b["stop"]["wall_seconds"],
                    "model_load_fit_export_eval_parity_allowance_s": [15, 120],
                    "RAM_guard_proposed_B": 1879048192,
                }
            )
    sigma = paired["newselection"]["step200"]["groups"]["minus_D"]["sd"]
    precision = [
        {
            "desired_95_halfwidth": h,
            "normal_approx_family_count": math.ceil((1.96 * sigma / h) ** 2),
        }
        for h in (0.01, 0.005)
    ]
    result = {
        "task": "frame22-independent-data-planning-284-v1",
        "schema": "data-scale-scenarios-v1",
        "status": "PASS",
        "basis": basis,
        "design_targets": targets,
        "rosters": rosters,
        "learning": learning,
        "paired_sigma_reused12": sigma,
        "precision_examples_not_power_guarantees": precision,
        "source_SHA": {str(p): sha(p) for p in refs},
        "new_NN": 0,
        "model_import": 0,
        "teacher_or_old_test_label_body_reads": 0,
        "wall_seconds": time.monotonic() - start,
        "peak_RSS_B": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "CPU_affinity": sorted(os.sched_getaffinity(0)),
    }
    assert result["peak_RSS_B"] < 512 * 1024**2
    (SCOPE / "scenarios-v1.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "wall_seconds": result["wall_seconds"],
                "peak_RSS_B": result["peak_RSS_B"],
                "new_NN": 0,
                "basis": basis,
                "targets": targets,
                "precision": precision,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
