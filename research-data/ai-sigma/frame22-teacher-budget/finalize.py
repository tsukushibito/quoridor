"""Preserve the finite stopped teacher-budget diagnosis; no inference or rerun."""

import datetime
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time

BASE = Path(__file__).resolve().parent
ROOT = Path("/workspaces/quoridor")
HELPER = ROOT / ".worktree/frame22-teacher/crates/quoridor-runner/examples/teacher_budget.rs"
BINARY = ROOT / ".artifacts/rust-migration/target/release/examples/teacher_budget"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact(identity):
    try:
        text = Path(f"/proc/{identity['pid']}/stat").read_text()
        tick = text[text.rfind(")") + 2 :].split()[19]
        return str(tick) == str(identity["start_ticks"])
    except (FileNotFoundError, ProcessLookupError):
        return False


def main():
    start = time.monotonic()
    processes = []
    for name in [
        "build-r1",
        "build-r2",
        "prepare-r1",
        "qualification-r1",
        "measurement-r1",
        "salvage-analysis-r1",
    ]:
        p = BASE / name / "process.json"
        d = json.loads(p.read_text())
        identities = [d["identity"], *d.get("recorded_children", [])]
        alive = [i for i in identities if exact(i)]
        assert d["waited"] and not d["current_exact_remaining"] and not alive
        processes.append(
            {
                "run": name,
                "SHA": sha(p),
                "exit": d["exit"],
                "reason": d["reason"],
                "command_wall_s": d["command_wall_s"],
                "management_inclusive_s": d["management_inclusive_wall_s"],
                "waited": True,
                "current_exact": alive,
                "peak_RSS": d["peak_RSS"],
                "GPU_device_sampled_upper": d.get("GPU_peak_sampled_bytes"),
            }
        )
    backgrounds = []
    for name in [
        "background-build-r1",
        "background-build-r2",
        "background-qualification-r1",
        "background-measurement-r1",
    ]:
        p = BASE / name / "result.json"
        d = json.loads(p.read_text())
        assert d["cleanup_complete"] and not d["remaining"]
        backgrounds.append({"run": name, "SHA": sha(p), **d})
    sources = [
        HELPER,
        BASE / "control.py",
        BASE / "build_lint.py",
        BASE / "salvage_analysis.py",
        BASE / "finalize.py",
        BASE / "teacher_budget-qualified-v1.rs",
    ]
    sources += sorted(BASE.glob("*config.json"))
    sources += sorted(BASE.glob("*guardian*.json"))
    sources += sorted(BASE.glob("*background*.json"))
    sources += [
        BASE / "plan-v1.json",
        BASE / "runtime-binding.json",
        BASE / "recording-amendment-v2.json",
        BASE / "contract-reference.md",
    ]
    members = {}
    with tarfile.open(BASE / "necessary-source.tar.xz", "w:xz") as archive:
        for p in sources:
            name = "teacher_budget.rs" if p == HELPER else p.name
            data = p.read_bytes()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
            members[name] = hashlib.sha256(data).hexdigest()
    with tarfile.open(BASE / "necessary-source.tar.xz", "r:xz") as archive:
        for member in archive.getmembers():
            assert (
                hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                == members[member.name]
            )
    result = json.loads((BASE / "salvage-result.json").read_text())
    fees = {
        "compile_lint_command_s": sum(
            p["command_wall_s"] for p in processes if p["run"].startswith("build")
        ),
        "science_command_s": sum(
            p["command_wall_s"]
            for p in processes
            if p["run"] in ["qualification-r1", "measurement-r1"]
        ),
        "NN0_prepare_analysis_command_s": sum(
            p["command_wall_s"]
            for p in processes
            if p["run"] in ["prepare-r1", "salvage-analysis-r1"]
        ),
        "wrappers_overlap_not_added_to_science": True,
        "unmeasured_read_thinking_management": "UNKNOWN",
        "prior_task_fees_unchanged": True,
    }
    current = sum(p.stat().st_size for p in BASE.rglob("*") if p.is_file())
    retained = sum(p.stat().st_size for p in BASE.rglob("*") if p.is_file() and p.suffix != ".xz")
    forecast = current + retained + 262144
    assert forecast <= 3670016, (current, retained, forecast)
    record = {
        "task": "teacher-budget-282-v1",
        "schema": "teacher-budget-stop-v1",
        "stopped_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scientific_source_frozen": True,
        "scientific_slots_used": 2,
        "no_additional_science": True,
        "source": {str(p): sha(p) for p in sources},
        "binary": {"path": str(BINARY), "SHA": sha(BINARY)},
        "payload": {
            n: sha(BASE / n)
            for n in [
                "prepare-result.json",
                "qualify-result.json",
                "measurement-result.partial.json",
                "salvage-result.json",
                "qualification-verified.json",
                "measurement-storage-admission.json",
            ]
        },
        "all_attempts": processes,
        "backgrounds": backgrounds,
        "physical_NN_source_bound": result["total_physical_NN_source_bound"],
        "physical_NN_conservative_upper": result["total_physical_NN_conservative_upper"],
        "original_guard_NN_UNKNOWN_unchanged": True,
        "allocated_source_bound": result["serialized_header_counters"]["allocated_nodes"] + 24914,
        "processed": "UNKNOWN; advance invocations and allocated nodes are separate",
        "fees": fees,
        "archive": {
            "path": "necessary-source.tar.xz",
            "SHA": sha(BASE / "necessary-source.tar.xz"),
            "members": members,
            "stream_restore_PASS": True,
        },
        "storage": {
            "current_B": current,
            "uniqueGit_conservative_forecast_B": retained,
            "remaining_metadata_B": 262144,
            "total_forecast_B": forecast,
            "guard_B": 3670016,
            "reserve_B": 4194304,
            "within": True,
            "unknown_discount": False,
        },
        "finalize_management_seconds": time.monotonic() - start,
        "NN": 0,
        "goal_highest_strength_achieved": False,
    }
    (BASE / "science-stop.json").write_text(json.dumps(record, indent=2) + "\n")
    (BASE / "compact.json").write_text(
        json.dumps(
            {
                "task": record["task"],
                "schema": "teacher-budget-compact-v1",
                "status": "INCONCLUSIVE_HARD_TIMEOUT_RECORDING",
                "complete_conditions": 4,
                "unknown_conditions": 92,
                "missing_conditions": 12,
                "paired_roots": 1,
                "K64_to1024": result["pairs"][-1],
                "physical_NN_source_bound": record["physical_NN_source_bound"],
                "physical_NN_conservative_upper": record["physical_NN_conservative_upper"],
                "allocated_source_bound": record["allocated_source_bound"],
                "fees": fees,
                "all_processes_wait_current_exact_absent": True,
                "all_background_cleanup": True,
                "source_archive_restore": True,
                "independent_review": False,
                "no_seed_variance": True,
                "highK_truth": False,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "fees": fees,
                "storage": record["storage"],
                "source_members": len(members),
                "restore_PASS": True,
                "science_stop_SHA": sha(BASE / "science-stop.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
