"""Prospective cost amendment for coordinator's actual 285 allocation."""

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import estimate

ROOT = Path("/workspaces/quoridor")
SCOPE = Path(__file__).parent


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    start = time.monotonic()
    estimate.SCOPE = SCOPE / "revision-285"
    estimate.SCOPE.mkdir(exist_ok=True)
    estimate.admission()
    original = estimate.load(SCOPE / "scenarios-v1.json")
    basis = original["basis"]
    contract = (
        ROOT / "research-data/ai-sigma/frame22-coordinator/nested-independent-teacher-contract.md"
    )
    packing = [
        {"job": 1, "train": 192, "selection": 64, "sealed_eval": 0},
        {"job": 2, "train": 192, "selection": 0, "sealed_eval": 64},
        {"job": 3, "train": 256, "selection": 0, "sealed_eval": 0},
        {"job": 4, "train": 256, "selection": 0, "sealed_eval": 0},
        {"job": 5, "train": 128, "selection": 0, "sealed_eval": 0},
    ]
    assert sum(j["train"] for j in packing) == 1024
    assert sum(j["selection"] for j in packing) == 64
    assert sum(j["sealed_eval"] for j in packing) == 64
    assert all(sum(j[k] for k in ("train", "selection", "sealed_eval")) <= 256 for j in packing)
    scenarios = []
    for name, train in [("stage1", 192), ("stage2_max", 1024)]:
        families = train + 128
        rows = families * basis["eligible_rows_per_family"]
        scenarios.append(
            {
                "name": name,
                "new_train_families": train,
                "new_selection_families": 64,
                "new_future_eval_families": 64,
                "new_unique_families": families,
                "old_plus_new_train_nominal": 5981 + train * basis["train_rows_per_family"],
                "old_plus_new_train_yield20to70": [5981 + train * 20, 5981 + train * 70],
                "needed_mean_yield_for_target": (10000 - 5981) / train
                if name == "stage1"
                else (30000 - 5981) / train,
                "known_generation_opening_cache_center_minutes": families
                * basis["known_opening_cache_s_per_family"]
                / 60,
                "working_generation_minutes": [
                    families * 0.45 / 60 + 2 * 5 / 60,
                    families * 2.5 / 60 + 5 * 20 / 60,
                ],
                "stress_generation_upper_minutes": families * 7.5 / 60 + 5 * 20 / 60,
                "physical_NN_center": families * basis["physical_NN_per_family"],
                "working_NN_20to70rows_40to80NNperrow": [families * 800, families * 5600],
                "Arrow_cache_center_B": math.ceil(rows * basis["Arrow_plus_cache_bytes_per_row"]),
                "retained_Git_temp_forecast_B_70rows_factor2p5": math.ceil(
                    families * 70 * basis["Arrow_plus_cache_bytes_per_row"] * 2.5
                ),
            }
        )
    val = math.ceil(64 * basis["eligible_rows_per_family"])
    oldval = 1248
    learning = [
        {"name": "10k_256k", "train_rows": 10199, "seen": 256000, "evaluations": 10},
        {
            "name": "30k_work_512k_single_trajectory",
            "train_rows": 30199,
            "seen": 512000,
            "evaluations": 15,
        },
    ]
    for job in learning:
        job["eval_row_count"] = job["train_rows"] + oldval + val
        job["total_samples"] = job["seen"] + job["evaluations"] * job["eval_row_count"]
        job["CPU_guardian_center_s_short_extrapolation"] = (
            job["total_samples"] / basis["B_training_eval_samples"] * basis["B_fit_guardian_s"]
        )
    future_rows = math.ceil(64 * basis["eligible_rows_per_family"])
    total = sum(j["total_samples"] for j in learning) + 4 * future_rows + val + 1000
    sigma = original["paired_sigma_reused12"]
    record = {
        "task": "frame22-independent-data-planning-284-amendment285-v2",
        "schema": "data-scale-allocation-comparison-v2",
        "at": datetime.now(timezone.utc).isoformat(),
        "contract_path": str(contract),
        "contract_SHA": hashlib.sha256(contract.read_bytes()).hexdigest(),
        "parent_end": "2026-10-05T23:36:03Z",
        "old284_v1_preserved": True,
        "285_actual_not_hypothesis_approval": True,
        "packing_proposal": packing,
        "qualification_max1_plus_generation5_entry_fit": True,
        "phase1_320families_requires_two_entries_in_this_packing": True,
        "scenarios": scenarios,
        "NN_guard_1152x200x65": 1152 * 200 * 65,
        "allocated_17m_retained": True,
        "learning_proposal": learning,
        "new_fresh_fit_trajectories": 2,
        "fixed_quantity_work_comparison": "5981 savedB / 10k@2000 / largest@2000; largest@4000 work control shares exact first2000 batches",
        "new_eval_rows_nominal": future_rows,
        "max_unique_NN_models_for_future_eval": 4,
        "total_NN_learning_eval_parity_nominal_upper": total,
        "future_CPU_sample_budget_recommendation": 2000000,
        "rebind_actual_rows_before_learning": True,
        "future_eval64_normal_halfwidth_sigma12_reference": 1.96 * sigma / math.sqrt(64),
        "future_eval64_normal_halfwidth_double_sigma_stress": 1.96 * 2 * sigma / math.sqrt(64),
        "future_eval64_sufficient_proof": False,
        "NN": 0,
        "model_import": 0,
        "wall_seconds": time.monotonic() - start,
        "peak_RSS_B": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    (SCOPE / "scenarios-285-v2.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
