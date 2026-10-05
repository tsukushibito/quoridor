"""Saved-prediction analysis; standard library only, no model or input creation."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import time


ROOT = Path("/workspaces/quoridor")
SCOPE = Path(__file__).parent
TASK = "frame22-transfer-selection-278-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tick(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def write(name, data):
    (SCOPE / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def admit():
    operation = json.loads((ROOT / ".artifacts/research-team/registry.json").read_text())[
        "current_operation"
    ]
    state = json.loads((Path(operation["state_dir"]) / "state.json").read_text())
    expected = json.loads(Path(operation["expectations_path"]).read_text())
    base = Path(operation["config_path"]).parent
    monitor = json.loads((base / "monitor-process.json").read_text())["process"]
    checks = {p: sha(p) == digest for p, digest in expected["input_hashes"].items()}
    foreign = []
    total_rss = 0
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            fields = (p / "stat").read_text().rsplit(")", 1)[1].split()
            total_rss += int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
            argv = (p / "cmdline").read_bytes().split(b"\0")
            argv = [s.decode(errors="replace") for s in argv if s]
            if not argv or int(p.name) == os.getpid():
                continue
            executable = Path(argv[0]).name
            script = (
                next((a for a in argv[1:] if a.endswith(".py")), "")
                if "python" in executable
                else ""
            )
            scientific = (
                executable in ("rustc", "cargo", "teacher-throughput", "quoridor-runner")
                or Path(script).name in ("run_science.py", "run_guard.py", "managed_science.py")
                or "-m" in argv
                and "quoridor_training" in " ".join(argv)
            )
            if scientific:
                foreign.append({"pid": int(p.name), "tick": tick(p.name), "argv": argv})
        except (OSError, ValueError):
            continue
    old = json.loads(
        (
            ROOT / "research-data/ai-sigma/frame22-teacher-throughput/final-caps-storage-v1.json"
        ).read_text()
    )
    current = sum(p.stat().st_blocks * 512 for p in SCOPE.rglob("*") if p.is_file())
    research_pids = {os.getpid(), state["process"]["pid"], monitor["pid"]} | {
        v["pid"] for v in foreign
    }
    # Count owned scientific/runtime processes separately from editor/other host users.
    research_rss = sum(
        int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[21])
        * os.sysconf("SC_PAGE_SIZE")
        for pid in research_pids
    )
    available = (
        int(
            next(
                v
                for v in Path("/proc/meminfo").read_text().splitlines()
                if v.startswith("MemAvailable:")
            ).split()[1]
        )
        * 1024
    )
    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "phase": state["phase"],
        "owned": state.get("owned"),
        "next_at": state["next_at"],
        "scheduler": state["process"],
        "monitor": monitor,
        "input_checks": checks,
        "foreign_science": foreign,
        "current_all_process_RSS_upper": total_rss,
        "research_process_pids": sorted(research_pids),
        "research_current_RSS": research_rss,
        "host_MemAvailable": available,
        "research_RAM_coverage": "current owned scientific/runtime processes; unknown foreign scientific process refuses admission",
        "CPU": 4,
        "logical_count": 1,
        "GPU": 0,
        "RAM_limit": 512 * 1024**2,
        "scope_current": current,
        "scope_forecast": 1024**2,
        "storage_transfer": {
            "old273_reserve": 127 * 1024**2,
            "old273_actual_forecast": old["data_totalforecast"],
            "new278_reserve": 1024**2,
            "aggregate_unchanged": 128 * 1024**2,
            "unknown_discount": 0,
        },
        "point_only": True,
    }
    record["PASS"] = (
        all(checks.values())
        and operation["frame"] == 22
        and state["phase"] == "running"
        and tick(state["process"]["pid"]) == str(state["process"]["start_ticks"])
        and tick(monitor["pid"]) == str(monitor["start_ticks"])
        and not foreign
        and research_rss + 512 * 1024**2 < 8 * 1024**3
        and available > 2 * 1024**3
        and old["data_totalforecast"] < 127 * 1024**2
        and current < 1024**2
    )
    write("admission.json", record)
    if not record["PASS"]:
        raise RuntimeError("CURRENT_ADMISSION_UNAVAILABLE")


def weighted_stats(rows, model):
    mass = sum(r["w"] for r in rows)

    def mean(fn):
        return sum(r["w"] * fn(r) for r in rows) / mass

    e = lambda r: r["rootmean"] - r["D"]
    delta = lambda r: r["predictions"][model] - r["D"]
    ee, rr, cross = (
        mean(lambda r: e(r) ** 2),
        mean(lambda r: delta(r) ** 2),
        mean(lambda r: e(r) * delta(r)),
    )
    em, rm = mean(e), mean(delta)
    variance = (ee - em**2) * (rr - rm**2)
    mse = mean(lambda r: (r["rootmean"] - r["predictions"][model]) ** 2)
    gap = mse - ee
    assert abs(gap - (rr - 2 * cross)) < 1e-12
    return {
        "rows": len(rows),
        "games": len({r["group"] for r in rows}),
        "mass": mass,
        "D_MSE": ee,
        "MSE": mse,
        "gap": gap,
        "signed_contribution": mass * gap,
        "displacement": rr,
        "alignment_twice": 2 * cross,
        "e_mean": em,
        "e_RMS": math.sqrt(ee),
        "r_mean": rm,
        "r_RMS": math.sqrt(rr),
        "corr_e_r": (cross - em * rm) / math.sqrt(variance) if variance > 0 else None,
        "z_MSE": mean(lambda r: (r["z"] - r["predictions"][model]) ** 2),
        "z_sign_accuracy": mean(lambda r: float(r["z"] * r["predictions"][model] > 0)),
        "prediction_abs_ge_099": mean(lambda r: float(abs(r["predictions"][model]) >= 0.99)),
    }


def interval(values, seed):
    rng = random.Random(seed)
    samples = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(2000))
    return [samples[49], samples[1949]]


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    start = time.monotonic()
    admit()
    register = json.loads((SCOPE / "preregister.json").read_text())
    for p, digest in register["input_SHA"].items():
        assert sha(p) == digest, p
    transfer = ROOT / "research-data/ai-sigma/frame22-teacher-transfer"
    source = json.loads((transfer / "newselection-result-r1/result.json").read_text())
    mask = json.loads((transfer / "newselection-result-r1/mask.json").read_text())
    weight_map = {name: item["weights_SHA"] for name, item in source["results"].items()}
    with gzip.open(transfer / "newselection-result-r1/row-predictions.jsonl.gz", "rt") as f:
        rows = [json.loads(line) for line in f]
    assert len(rows) == 392 and len({r["id"] for r in rows}) == 392
    wanted = {r["id"] for r in rows}
    metadata = {}
    with (
        ROOT
        / "research-data/ai-sigma/frame22-teacher-throughput/canonical-active48-cache-v1/rows.jsonl"
    ).open() as f:
        for line in f:
            r = json.loads(line)
            if r["id"] in wanted:
                assert r["split"] == "validation"
                metadata[r["id"]] = r
    assert set(metadata) == wanted
    families = json.loads(
        (
            ROOT / "research-data/ai-sigma/frame22-teacher-throughput/registered-family-map-v1.json"
        ).read_text()
    )["families"]
    cohorts = {f["slot"]: f["cohort"] for f in families}
    counts = Counter(r["group"] for r in rows)
    assert len(counts) == 12 and set(counts) == set(mask["groups"])
    for r in rows:
        m = metadata[r["id"]]
        assert r["group"] == m["group"] and mask["rows"][r["id"]] and r["eligible"]
        assert r["rootmean"] == m["rootmean"] and r["z"] == m["z"]
        r["predictions"] = {
            n: r["prediction_by_unique_weightSHA"][s] for n, s in weight_map.items()
        }
        assert all(math.isfinite(v) for v in r["predictions"].values())
        r["D"] = r["predictions"]["Initial"]
        r["w"] = 1 / (12 * counts[r["group"]])
        r["phase"] = "opening" if m["ply"] < 20 else "middle" if m["ply"] < 60 else "late"
        r["cohort"] = str(cohorts[int(m["game"].split("-")[1])])
        ids = m["ids"][m["side"] - 1]
        a = [v - 290 for v in ids if 290 <= v < 301]
        b = [v - 301 for v in ids if 301 <= v < 312]
        assert len(a) == len(b) == 1
        stock = a[0] + b[0]
        r["remaining_stock"] = "0-5" if stock <= 5 else "6-12" if stock <= 12 else "13-20"
        difference = (m["distance"][1] - m["distance"][0]) * 80
        r["distance_diff"] = (
            "<-1" if difference < -1.00001 else ">1" if difference > 1.00001 else "[-1,1]"
        )
    result = {
        "task": TASK,
        "schema": "transfer-selection-v1",
        "status": "PASS",
        "NN": 0,
        "ML_jobs": 0,
        "rows": len(rows),
        "games": len(counts),
        "weight": "1/(12*n_game), original global weights within bins",
        "models": {},
        "mask": {k: v for k, v in mask.items() if k not in ("rows", "groups")},
        "teacher": {
            "rootmean_z_MSE": sum(r["w"] * (r["rootmean"] - r["z"]) ** 2 for r in rows),
            "rootmean_z_sign_agreement": sum(
                r["w"] * float(r["rootmean"] * r["z"] > 0) for r in rows
            ),
        },
        "metadata_missing": ["full_history", "repetition_count", "all_action_exact_values"],
        "bootstrap": "2000 fixed-prediction game resamples, seed2782201; exploration conditional on selected weights, not selection/teacher uncertainty",
    }
    for model in weight_map:
        overall = weighted_stats(rows, model)
        expected = source["results"][model]["secondary_all_rows"]["rootmean_game_equal_mse"]
        assert abs(overall["MSE"] - expected) < 1e-12
        bins = {}
        for key in ("group", "phase", "cohort", "remaining_stock", "distance_diff"):
            parts = defaultdict(list)
            for r in rows:
                parts[r[key]].append(r)
            bins[key] = {k: weighted_stats(v, model) for k, v in parts.items()}
            assert (
                abs(sum(v["signed_contribution"] for v in bins[key].values()) - overall["gap"])
                < 1e-12
            )
            assert abs(sum(v["mass"] for v in bins[key].values()) - 1) < 1e-12
        differences = [v["gap"] for v in bins["group"].values()]
        result["models"][model] = {
            "overall": overall,
            "bins": bins,
            "game_gain": sum(v < 0 for v in differences),
            "game_loss": sum(v > 0 for v in differences),
            "fixed_game_CI95": interval(differences, 2782201),
        }
    pergame = result["models"]
    ba = [
        pergame["B_BEST200"]["bins"]["group"][g]["MSE"]
        - pergame["A_BEST200"]["bins"]["group"][g]["MSE"]
        for g in counts
    ]
    result["BminusA_BEST"] = {"game_mean": sum(ba) / 12, "CI95": interval(ba, 2782202)}
    result["elapsed_seconds"] = time.monotonic() - start
    result["peak_RSS_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    write("result.json", result)
    print(
        json.dumps(
            {
                "status": "PASS",
                "rows": len(rows),
                "games": len(counts),
                "NN": 0,
                "elapsed": result["elapsed_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
