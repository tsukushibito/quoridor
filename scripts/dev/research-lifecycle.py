#!/usr/bin/env python3
"""One trusted build manifest and experiment entry, under research-job/cycle_process."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from quoridor_training import cycle_process as process  # noqa: E402

LEASE = Path("/workspaces/quoridor/.artifacts/rust-migration/target/arena-software-writer.lock")
BUILD_SCHEMA = "quoridor.research.build-manifest.v1"
EXPERIMENT_SCHEMA = "quoridor.research.experiment.v1"
COMPLETION_SCHEMA = "quoridor.research.completion.v1"
CONTROL_BYTES = 1024 * 1024


class Refused(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Refused(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def error_fact(error):
    try:
        message = str(error)
    except BaseException:
        message = "<exception stringification failed>"
    fact = {
        "type": type(error).__name__,
        "message": message[:8192],
        "notes": list(getattr(error, "__notes__", [])),
    }
    if isinstance(error, BaseExceptionGroup):
        fact["errors"] = [error_fact(e) for e in error.exceptions]
    return fact


def bound(path, limit=CONTROL_BYTES):
    """No symlinks or re-open-after-admission; hash precisely the admitted bytes."""
    path = Path(path)
    require(path.is_absolute(), "absolute reference required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        info = os.fstat(f.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "reference size/type")
        data = f.read(limit + 1)
        require(len(data) == info.st_size and len(data) <= limit, "reference changed/oversize")
    return {
        "path": str(path),
        "sha256": sha(data),
        "bytes": len(data),
        "mode": format(stat.S_IMODE(info.st_mode), "04o"),
    }, data


def read_ref(ref, limit=CONTROL_BYTES):
    require(
        isinstance(ref, dict) and set(ref) == {"path", "sha256", "bytes", "mode"},
        "bound descriptor",
    )
    actual, data = bound(ref["path"], limit)
    require(actual == ref, "reference drift: " + ref["path"])
    return data


def document(ref):
    return json.loads(read_ref(ref))


def new_json(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    require(len(data) <= CONTROL_BYTES, "control publication cap")
    with Path(path).open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def allocated(path):
    total = 0
    pending = [Path(path)]
    while pending:
        base = pending.pop()
        try:
            info = base.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode), "owned namespace symlink")
        total += info.st_blocks * 512
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(base) as entries:
                pending.extend(Path(e.path) for e in entries)
    return total


def owned(path, owner):
    path, owner = Path(path), Path(owner)
    require(
        path.is_absolute() and owner.is_absolute() and path.is_relative_to(owner), "write ownership"
    )
    require(path != owner, "exclusive operation must be below owner")
    require(path.resolve() == path, "write path symlink/normalization")
    return path


def charged_roots(spec):
    paths = [spec["output"]]
    if spec["kind"] == "build":
        paths += [spec["target"], str(Path(spec["private"]).parent), spec["TMP"]]
    else:
        paths += [spec["data_root"], *spec.get("owned_outputs", [])]
        if spec.get("TMP"):
            paths.append(spec["TMP"])
        paths += [x["path"] for x in spec["finalizers"]]
        data_root = owned(spec["data_root"], spec["owner"])
        for item in spec["data"]:
            path = owned(item["path"], spec["owner"])
            require(path.is_relative_to(data_root), "declared data outside charged data root")
    roots = sorted({owned(p, spec["owner"]) for p in paths}, key=lambda p: len(p.parts))
    unique = []
    for path in roots:
        if not any(path.is_relative_to(parent) for parent in unique):
            unique.append(path)
    return unique


@contextmanager
def lease():
    with LEASE.open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class Limits(process.CycleResources):
    """Reuse guardian RSS/deadline/pause; add owned positive allocation bounds."""

    def __init__(self, spec):
        self.spec = spec
        cfg = spec["limits"]
        for name in ("family_B", "host_reserve_B", "owned_B", "log_B", "free_B"):
            require(type(cfg[name]) is int and cfg[name] > 0, "positive priced limit: " + name)
        require(
            cfg["family_B"] <= (6 if spec["kind"] == "build" else 2) * 1024**3
            and cfg["host_reserve_B"] >= 4 * 1024**3,
            "issued family/host envelope",
        )
        support = document(spec["support"])
        require(
            type(support["funded_union_B"]) is int
            and 0 < cfg["owned_B"] <= support["funded_union_B"] <= 50000000000,
            "issued inclusive whole support",
        )
        require(support["global_held_B"] <= 50000000000, "global holding")
        # Admission is issued phase-specific support, not a default scientific horizon.
        admission = document(spec["admission"])
        require(admission["schema"] == "quoridor.research.phase-admission.v1", "phase admission")
        require(
            admission["owner"] == spec["owner"] and admission["limits"] == cfg,
            "issued owner/limits",
        )
        require(admission["spec_sha256"] == spec["intent_sha256"], "actual intent admission")
        require(admission["support_sha256"] == spec["support"]["sha256"], "same support")
        require(admission["ready"] is True, "phase not admitted")
        if spec["kind"] == "run":
            require(admission["approved_plan"] == spec["approved_plan"], "issued approved plan")
        require(cfg["controller_B"] == 64 * 1024 * 1024, "whole family includes controller")
        self.charged_paths = charged_roots(spec)
        super().__init__(
            {
                "host_ram_reserve": cfg["host_reserve_B"],
                "max_memory_bytes": cfg["family_B"] - cfg["controller_B"],
                "max_output_bytes": cfg["owned_B"],
                "pause_file": spec.get("pause_file"),
            },
            spec["output"],
            None,
        )

    def check(self, children=()):
        super().check(children)
        require(
            sum(allocated(p) for p in self.charged_paths) <= self.spec["limits"]["owned_B"],
            "owned allocation limit",
        )
        require(
            shutil.disk_usage(self.spec["owner"]).free >= self.spec["limits"]["free_B"],
            "FS reserve",
        )
        if self.spec["kind"] == "build":
            h = document(self.spec["target_handover"])
            require(allocated(self.spec["target"]) <= h["target_max_B"], "target cap")
            private = allocated(Path(self.spec["private"]).parent)
            require(
                private <= h["fresh_private_forward_max_B"]
                and private + h["old_private_retained_allocated_B"] <= h["private_pool_B"],
                "retained private pool cap",
            )
            require(allocated(self.spec["TMP"]) <= 64 * 1024 * 1024, "TMP cap")


def physical_and_quiet(spec):
    cfg = spec["limits"]
    require(
        process.available_memory() >= cfg["family_B"] + cfg["host_reserve_B"],
        "physical RAM admission",
    )
    cores = [cfg["worker_cpu"], cfg["guardian_cpu"]]
    if "child_cpu_cores" in spec:
        cores = spec["child_cpu_cores"]
        require(
            spec["kind"] == "run"
            and isinstance(cores, list)
            and len(cores) == 4
            and all(type(c) is int and c >= 0 for c in cores)
            and len(set(cores)) == 4
            and cfg["worker_cpu"] in cores
            and cfg["guardian_cpu"] in cores,
            "declared two-worker corpus with two physical reserve cores",
        )
    require(set(cores) <= os.sched_getaffinity(0), "CPU affinity admission")
    identities = []
    for core in cores:
        p = Path(f"/sys/devices/system/cpu/cpu{core}/topology")
        identities.append(((p / "physical_package_id").read_text(), (p / "core_id").read_text()))
    require(
        len(set(identities)) == len(identities),
        "worker/guardian/reserves must be distinct physical cores",
    )
    # One instantaneous named scan. Lifetime conflicts serialize through the shared lease.
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            args = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if args and Path(os.fsdecode(args[0])).name in {
            "cargo",
            "rustc",
            "cc1plus",
            "quoridor-runner",
            "terminal-cache",
            "chromium",
            "chrome",
        }:
            raise Refused("named compute peer active: " + entry.name)
    os.sched_setaffinity(0, {cfg["guardian_cpu"]})


class Capture:
    """Full bounded bytes. Console tail is never executable/census evidence."""

    def __init__(self, path, limit):
        self.path, self.limit, self.seen = Path(path), limit, 0
        self.file = self.path.open("xb")

    def __call__(self, data):
        require(self.seen + len(data) <= self.limit, "full command capture limit")
        self.file.write(data)
        self.seen += len(data)

    def close(self):
        errors = []
        for fn in (self.file.flush, lambda: os.fsync(self.file.fileno()), self.file.close):
            try:
                fn()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise BaseExceptionGroup("capture finalizers", errors)


def cargo_report(data):
    artifacts, warnings, finished = [], [], []
    for line in data.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue  # Human diagnostics/test output are preserved verbatim in the full log.
        if not isinstance(item, dict):
            continue
        reason = item.get("reason")
        if reason == "compiler-message" and item.get("message", {}).get("level") == "warning":
            warnings.append(item)
        elif reason == "compiler-artifact" and item.get("executable"):
            artifacts.append(item)
        elif reason == "build-finished":
            finished.append(item.get("success"))
    require(finished == [True], "normal Cargo completion missing/failed")
    return {"artifacts": artifacts, "warning_count": len(warnings)}


def settled(record):
    require(
        record.get("status") == "complete" and record.get("exit_code") == 0,
        "command not successful",
    )
    require(
        record.get("direct_child_reaped") is True and record.get("cleanup_complete") is True,
        "directwait/cleanup incomplete",
    )
    require(
        record.get("remaining") == [] and record.get("finalization_errors", []) == [],
        "remaining/finalizers",
    )
    require(
        record.get("signal_mask_restoration") == "completed"
        and record.get("final_record_persist") == "completed",
        "returned guardian finalization incomplete",
    )


def command(spec, row, directory, resources, executor=process.execute, *, ledger=None):
    check = {
        "name": row["name"],
        "role": row.get("role", "run"),
        "argv": row["argv"],
        "status": "ATTEMPTED",
        "guardian_return": None,
        "full_log": None,
        "persisted_process_receipt": None,
        "capture_complete": False,
        "secondary": [],
    }
    if ledger is not None:
        ledger.append(check)
    primary, record, capture = None, None, None
    try:
        capture = Capture(directory / (row["name"] + ".full.log"), spec["limits"]["log_B"])
        cpu_args = {"cpu_core": spec["limits"]["worker_cpu"]}
        if "child_cpu_cores" in spec:
            require(
                spec["kind"] == "run" and document(spec["experiment"])["phase"] == "corpus",
                "multi-core launch is only the qualified corpus",
            )
            cpu_args = {"cpu_core": None, "cpu_cores": spec["child_cpu_cores"]}
        record = executor(
            row["argv"],
            directory / (row["name"] + ".log"),
            None,
            resources=resources,
            cwd=spec["cwd"],
            env=spec["env"],
            output_sink=capture,
            **cpu_args,
        )
        check["guardian_return"] = record
        settled(record)
    except BaseException as error:
        primary = error
    if capture is not None:
        try:
            capture.close()
        except BaseException as error:
            check["secondary"].append({"stage": "capture_close", **error_fact(error)})
            if primary is not None:
                primary.add_note("capture secondary: " + repr(error))
            else:
                primary = error
        try:
            check["full_log"] = bound(capture.path, spec["limits"]["log_B"])[0]
            check["capture_complete"] = (
                record is not None
                and record.get("log_bytes_seen") == check["full_log"]["bytes"]
                and not check["secondary"]
            )
            if primary is None:
                require(check["capture_complete"], "full returned capture missing/partial")
        except BaseException as error:
            check["secondary"].append({"stage": "capture_identity", **error_fact(error)})
            if primary is not None:
                primary.add_note("capture identity secondary: " + repr(error))
            else:
                primary = error
    persisted = (directory / (row["name"] + ".log")).with_suffix(".process.json")
    if persisted.exists():
        try:
            check["persisted_process_receipt"] = bound(persisted)[0]
        except BaseException as error:
            check["secondary"].append({"stage": "persisted_process_identity", **error_fact(error)})
            if primary is not None:
                primary.add_note("persisted process secondary: " + repr(error))
            else:
                primary = error
    check["status"] = "FAILED" if primary is not None else "PASS"
    check["primary"] = error_fact(primary) if primary is not None else None
    if primary is not None:
        raise primary
    return record, capture.path


def source_check(source, *, native_only=False):
    require("workspace" in source, "adopted workspace witness required")
    require(
        len(source["commit"]) == 40 and all(c in "0123456789abcdef" for c in source["commit"]),
        "frozen source commit",
    )
    if not native_only:
        for ref in source["files"]:
            read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
    if not native_only and source["patch"] is not None:
        read_ref(source["patch"])
    if "workspace" in source:
        workspace = Path(source["workspace"])
        require(workspace.is_absolute() and workspace.resolve() == workspace, "adopted workspace")
        files = {r["path"]: r for r in source["files"]}
        require(
            all(Path(p).is_relative_to(workspace) for p in files),
            "adopted source outside workspace",
        )
        for name in ("manifest", "lock"):
            expected = workspace / ("Cargo.toml" if name == "manifest" else "Cargo.lock")
            require(
                source[name]["path"] == str(expected) and files.get(str(expected)) == source[name],
                "adopted Cargo " + name,
            )
        for ref in [
            *source["compiled_sources"].values(),
            *source.get("generator_compiled_sources", {}).values(),
        ]:
            require(
                files.get(ref["path"]) == ref, "compiled source projection outside adopted files"
            )
        for item in source["cargo_configs"]:
            p = Path(item["path"])
            if item["file"] is None:
                require(not p.exists() and not p.is_symlink(), "Cargo config appeared")
            else:
                require(item["file"]["path"] == item["path"], "Cargo config identity")
                read_ref(item["file"])
        if native_only:
            for ref in native_source_refs(source):
                read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))


def native_source_refs(source):
    # Python/docs/test files in source.files remain immutable build provenance;
    # current caller files have their own run-intent binding.
    workspace = Path(source["workspace"])
    refs = list(source["compiled_sources"].values()) + [source["manifest"], source["lock"]]
    refs += [
        r
        for r in source["files"]
        if Path(r["path"]).is_relative_to(workspace / "crates")
        or Path(r["path"]) == workspace / "rust-toolchain.toml"
    ]
    refs += [x["file"] for x in source["cargo_configs"] if x["file"] is not None]
    return refs


def runtime_dependency_refs(manifest, approved_plan_ref=None):
    """Keep compiler dependencies fixed; the approved run plan is a new input."""
    if approved_plan_ref is None:
        return manifest["dependency_refs"]
    source_paths = {r["path"] for r in manifest["source"]["files"]}
    source_paths |= {t["file"]["path"] for t in manifest["tools"].values()}
    result = []
    for ref in manifest["dependency_refs"]:
        if ref["path"] == approved_plan_ref["path"]:
            require(
                ref["path"] not in source_paths
                and Path(ref["path"]).is_relative_to(ROOT / "research-data")
                and Path(ref["path"]).suffix == ".json",
                "runtime plan cannot replace a native/compiler source input",
            )
            result.append(approved_plan_ref)
        else:
            result.append(ref)
    return result


def build_input_refs(manifest, approved_plan_ref=None):
    return [
        manifest["artifact"],
        *native_source_refs(manifest["source"]),
        *runtime_dependency_refs(manifest, approved_plan_ref),
        *(x["file"] for x in manifest["tools"].values()),
    ]


FIT_IMPORTS = (
    "__init__",
    "train",
    "common",
    "terminal_cache",
    "cache",
    "distance_steps",
    "compact_cache",
    "public_features",
    "scaled_model",
    "residual_model",
    "model",
    "sampling",
    "supply",
    "plotting",
    "snapshot",
    "cycle_process",
)
PILOT_DATA = ROOT / ".worktree/assets/data/common-corpus-warmstart-study/pilot-v1"
PILOT_PLAN = ROOT / "research-data/ai-sigma/teacher-distance-tanh-v1/plan.json"
QUALIFIER = (
    ROOT
    / ".worktree/learning-million/.artifacts/common-corpus-warmstart-study/pilot-v1/test_current_framework.py"
)
QUALIFIER_SHA = "283529837b13ec4d8976662488354d86adf983391449771b94ac45fe5351efcb"
FIT_OUTPUTS = (
    "freeze.json",
    "config.json",
    "scale.json",
    "data.json",
    "cache-binding.json.gz",
    "initial.pt",
    "best.pt",
    "initial-model/manifest.json",
    "initial-model/weights.f32",
    "initial-model/training-target.json",
    "best-model/manifest.json",
    "best-model/weights.f32",
    "best-model/training-target.json",
    "last.pt",
    "last-model/manifest.json",
    "last-model/weights.f32",
    "last-model/training-target.json",
    "warm-start.json",
    "z-curves.svg",
    "completed_root_raw-curves.svg",
    "curves.csv",
    "observations.jsonl.gz",
    "run-status.json",
)


def numerical_check(experiment, manifest):
    q = document(experiment["numerical_qualification"])
    expected = {
        "schema": "quoridor.research.numerical-qualification.v1",
        "status": "PASS",
        "phase": experiment["phase"],
        "artifact_sha256": manifest["artifact"]["sha256"],
        "compiled_sources_sha256": canonical_sha(manifest["compiled_sources"]),
        "config_sha256": experiment["config"]["sha256"],
        "schedule_sha256": experiment["schedule"]["sha256"],
        "input_sha256": [r["sha256"] for r in experiment["inputs"]],
        "descriptor_sha256": [r["descriptor"]["sha256"] for r in experiment["models"]],
        "weights_sha256": [r["weights"]["sha256"] for r in experiment["models"]],
        "evaluator_sha256": [r["evaluator_sha256"] for r in experiment["models"]],
        "rules": experiment["rules"],
        "distance_units": experiment["distance_units"],
        "value_perspective": experiment["value_perspective"],
        "canonical_plan_sha256": experiment["canonical_plan_sha256"],
        "remaining": [],
    }
    require(
        all(q.get(k) == v for k, v in expected.items()),
        "current numerical/source/model/input correspondence",
    )
    return q


def common_pilot_check(spec, experiment, manifest, approved):
    phase = experiment["phase"]
    require(spec["approved_plan"]["path"] == str(PILOT_PLAN), "canonical common pilot plan")
    study = approved["next_learning_study"]
    require(
        study["issue"] == "quoridor-4lc.362"
        and study["scientific_entry"] is True
        and study["corpus"]["quantity_families"] == 8,
        "selected retained eight-game pilot",
    )
    require(
        experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and experiment["distance_units"] == "wall-distance/80"
        and experiment["value_perspective"] == "side-to-move"
        and experiment.get("batch") is None,
        "common pilot rules/units/perspective",
    )
    config = document(experiment["config"])
    if phase != "corpus":
        require("child_cpu_cores" not in spec, "multi-core corpus cannot widen other phases")
    if phase == "corpus":
        cpus = spec.get("child_cpu_cores")
        require(
            isinstance(cpus, list)
            and len(cpus) == 4
            and all(type(c) is int and c >= 0 for c in cpus)
            and cpus == sorted(set(cpus))
            and cpus[:2] == config["worker_cores"]
            and config["cpu_core"] == cpus[0]
            and spec["limits"]["worker_cpu"] in cpus[:2]
            and spec["limits"]["guardian_cpu"] == cpus[2],
            "native two-worker admission preserves two actual host reserve cores",
        )
        q = numerical_check(experiment, manifest)
        require(
            experiment["planned_slots"] == 8
            and experiment["models"] == []
            and experiment["argv"][1:]
            == [
                "teacher-pilot",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
            "qualified corpus native entry",
        )
        require(
            config["phase"] == "common_corpus"
            and config["output"] == spec["data_root"] == str(PILOT_DATA)
            and config["planned_games"] == config["main_volume_n"] == 8
            and config["depth"] == 6
            and config["max_nodes"] == 100_000_000
            and config["max_total_nodes"] == 1_000_000_000
            and config["max_total_plies"] == 200
            and config["per_move_timeout_ms"] is None
            and config["distance_a"] == 0
            and config["distance_b"] == 8,
            "selected corpus limits and owned output",
        )
        common = config["common_study"]
        require(
            common["selected_plan"] == {k: spec["approved_plan"][k] for k in ("path", "sha256")}
            and experiment["inputs"][0] == spec["approved_plan"]
            and document(experiment["schedule"]) == study["corpus"]["blind_schedule"],
            "blind corpus selected-plan/schedule binding",
        )
        require(
            q["generator_compiled_sources_sha256"]
            == canonical_sha(manifest["generator_compiled_sources"]),
            "actual current generator closure",
        )
        return
    require(experiment["planned_slots"] == 0, "fit/qualification is a nongame operation")
    python = manifest["tools"]["PYTHON"]["file"]["path"]
    require(
        spec["cwd"] == str(ROOT)
        and spec["env"].get("PYTHONDONTWRITEBYTECODE") == "1"
        and spec["env"].get("PYTHONPATH")
        == "/home/vscode/.cache/inference/envs/quoridor-training/lib/python3.14/site-packages:"
        + str(ROOT / "python")
        and all(
            spec["env"].get(k) == "1"
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        ),
        "pinned framework/import/thread environment",
    )
    warm = study["common_learner_settings"]["experiment"]["warm_start"]
    require(
        experiment["models"]
        == [
            {
                "descriptor": warm["descriptor"],
                "weights": warm["weights"],
                "evaluator_sha256": warm["evaluator_sha256"],
            }
        ],
        "same selected incumbent for fit or framework qualification",
    )
    if phase == "software-qualification":
        require(
            set(config) == {"definition", "helper_sources", "result"}
            and config["definition"]["path"] == str(QUALIFIER)
            and config["definition"]["sha256"] == QUALIFIER_SHA
            and config["definition"] in experiment["inputs"],
            "fixed affected framework definitions",
        )
        require(
            all(r in experiment["inputs"] for r in config["helper_sources"]),
            "bound qualifier helpers",
        )
        require(
            config["result"] == str(Path(spec["data_root"]) / "qualification.json")
            and spec["argv"] == [python, "-B", str(QUALIFIER), "--result", config["result"]],
            "software qualifier exact entry/output",
        )
        require(
            spec["data"] == [{"name": "qualification", "path": config["result"], "limit_B": 65536}],
            "software qualifier durable receipt",
        )
        return
    numerical_check(experiment, manifest)
    require(
        len(experiment["models"]) == 1
        and experiment["models"][0]
        == {
            "descriptor": config["experiment"]["warm_start"]["descriptor"],
            "weights": config["experiment"]["warm_start"]["weights"],
            "evaluator_sha256": config["experiment"]["warm_start"]["evaluator_sha256"],
        },
        "fit same incumbent model",
    )
    require(
        len(spec["argv"]) == 13
        and spec["argv"][:5] == [python, "-B", "-m", "quoridor_training.train", "train"]
        and spec["argv"][5:9]
        == ["--cache", str(PILOT_DATA / "cache-compact-v3"), "--output", spec["data_root"]]
        and spec["argv"][9:11] == ["--config", experiment["config"]["path"]]
        and spec["argv"][11] == "--input-binding",
        "fit exact trainer/cache/output/config inlet",
    )
    binding_ref = next((r for r in experiment["inputs"] if r["path"] == spec["argv"][12]), None)
    require(binding_ref is not None, "actual fit input binding")
    binding = document(binding_ref)
    require(
        binding["selected_plan"] == {k: spec["approved_plan"][k] for k in ("path", "sha256")}
        and binding["fit_config_sha"] == experiment["config"]["sha256"],
        "same approved fit decision",
    )
    pairs = binding["paired_fit_configs"]
    require(
        len(pairs) == 2
        and experiment["config"] in pairs
        and all(r in experiment["inputs"] for r in pairs),
        "bound selected two-teacher config pair",
    )
    targets = []
    for r in pairs:
        recipe = document(r)
        target = recipe["training"].pop("target")
        require(
            recipe == study["common_learner_settings"],
            "no unselected learner defaults or recipe change",
        )
        targets.append(target)
    require(targets == ["z", "completed_root_raw"], "ordered distinct teacher pair")
    require(
        config["training"]["steps"] == 200 and config["training"]["batch_size"] == 64,
        "selected fit quantity",
    )
    require(
        {r["path"] for r in spec["data"]}
        >= {str(Path(spec["data_root"]) / name) for name in FIT_OUTPUTS},
        "owed actual frozen fit outputs",
    )
    cache_ref = next(
        (
            r
            for r in experiment["inputs"]
            if r["path"] == str(PILOT_DATA / "cache-compact-v3/cache.json")
        ),
        None,
    )
    require(
        cache_ref is not None
        and cache_ref["sha256"] == binding["cache_manifest_sha"]
        and not (PILOT_DATA / "cache-compact-v3/intake-incomplete.json").exists(),
        "authoritative shared cache",
    )
    cache = document(cache_ref)
    for name, width in COMPACT_CACHE_WIDTHS.items():
        path = str(Path(cache_ref["path"]).parent / name)
        ref = next((r for r in experiment["inputs"] if r["path"] == path), None)
        require(
            ref is not None
            and ref["sha256"] == cache["sha256"][name]
            and ref["bytes"] == cache["file_bytes"][name] == cache["rows"] * width,
            "same compact binary lifetime inputs",
        )
    eligible = cache["common_corpus"]["common_eligible_by_split"]
    require(
        all(type(eligible.get(k)) is int and eligible[k] > 0 for k in ("train", "validation")),
        "common eligible T and V must both be nonempty before trainer",
    )

    require(
        cache["schema"] == "quoridor-common-corpus-terminal-geometry-v3"
        and cache["files"] == {name: name for name in COMPACT_CACHE_WIDTHS}
        and set(cache["sha256"]) == set(cache["file_bytes"]) == set(COMPACT_CACHE_WIDTHS)
        and cache["stream_intake"]["status"] == "complete"
        and cache["schedule_sha256"] == binding["schedule_sha256"]
        and cache["family_partition_sha256"] == binding["family_partition_sha256"]
        and cache["source_binding"] == binding["dataset"],
        "same source/schedule/partition/dual cache",
    )


def caller_source_refs(spec, experiment):
    paths = {
        ROOT / "scripts/dev/research-lifecycle.py",
        ROOT / "scripts/dev/research-job.py",
        ROOT / "python/quoridor_training/cycle_process.py",
        ROOT / "python/quoridor_training/snapshot.py",
    }
    if experiment["phase"] in {"fit", "software-qualification"}:
        paths |= {ROOT / "python/quoridor_training" / (name + ".py") for name in FIT_IMPORTS}
        if experiment["phase"] == "software-qualification":
            config = document(experiment["config"])
            paths |= {
                Path(config["definition"]["path"]),
                *(Path(r["path"]) for r in config["helper_sources"]),
            }
    if experiment["phase"] == "analysis":
        paths |= {
            ROOT / "python/quoridor_training/research355" / (name + ".py")
            for name in (
                "stream355",
                "lifecycle355",
                "io355",
                "observations355",
                "producer355",
                "strength355",
            )
        }
        require(
            len(spec["argv"]) > 2
            and spec["argv"][1] == "-B"
            and spec["argv"][2] == str(ROOT / "python/quoridor_training/research355/stream355.py"),
            "current maintained analysis entry",
        )
    refs = spec["caller_sources"]
    require(
        isinstance(refs, list)
        and len(refs) == len(paths)
        and {r["path"] for r in refs} == {str(p) for p in paths},
        "exact current caller/import membership",
    )
    return refs


def accepted_build(ref, approved_plan_ref=None):
    manifest = document(ref)
    require(not Path(ref["path"]).with_name("INCOMPLETE").exists(), "provisional manifest")
    require(
        manifest["schema"] == BUILD_SCHEMA and manifest["status"] == "PASS",
        "accepted build required",
    )
    require(
        manifest["cleanup_complete"] is True and manifest["remaining"] == [],
        "build completion required",
    )
    require(
        {r["role"] for r in manifest["checks"]} >= {"test", "lint", "build", "bindings"},
        "affected test/lint/build/bindings required",
    )
    read_ref(manifest["artifact"], 32 * 1024 * 1024)
    source_check(manifest["source"], native_only=True)
    require(
        manifest["compiled_sources"]
        == {k: r["sha256"] for k, r in manifest["source"]["compiled_sources"].items()},
        "qualified native source projection",
    )
    for r in runtime_dependency_refs(manifest, approved_plan_ref):
        read_ref(r, max(CONTROL_BYTES, r["bytes"]))
    for tool in manifest["tools"].values():
        require(
            isinstance(tool["version"], str) and bool(tool["version"].strip()),
            "qualified tool version",
        )
        read_ref(tool["file"], max(CONTROL_BYTES, tool["file"]["bytes"]))
    return manifest


GENERATION_PLAN = "b3e41602eeed250d120444cf65783012e87f8b5f860bef2862c7aac5fd9c24b2"
GENERATION_OPEN8 = "be50f486ccfdef3ae1c1bddde33d8369398a19c2a6ccd3d3324b64863f322dbc"
GENERATION_SCHEDULE = "9bfb6135506f8d237f92d12d75de5e9131faaf5c8693f12f91f6a1698a487e1e"
GENERATION_FILES = {
    "start": "generation-start.json",
    "book": "book.json",
    "schedule": "schedule.json",
    "result": "generation-result.json",
}


def canonical_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def experiment_phase_check(experiment):
    phase = experiment["phase"]
    require(
        phase
        in {
            "generation",
            "materialize",
            "compare",
            "arena",
            "analysis",
            "corpus",
            "fit",
            "software-qualification",
        },
        "phase",
    )
    if phase == "software-qualification":
        require(
            experiment.get("numerical_qualification") is None
            and experiment["planned_slots"] == 0
            and experiment.get("batch") is None,
            "software-only qualifier cannot claim numerical/game qualification",
        )
        return
    if phase == "materialize" and experiment.get("numerical_qualification") is None:
        require(
            experiment["models"] == []
            and experiment["planned_slots"] == 0
            and experiment.get("batch") is None,
            "saved codec cannot claim model/numerical/game qualification",
        )
        return
    if phase != "generation":
        require(
            isinstance(experiment.get("numerical_qualification"), dict),
            "non-generation numerical qualification required",
        )
        return
    require(
        experiment.get("numerical_qualification") is None
        and experiment["models"] == []
        and type(experiment["planned_slots"]) is int
        and experiment["planned_slots"] == 0
        and experiment.get("batch") is None,
        "generation-only model-free non-game bootstrap",
    )
    require(
        len(experiment["argv"]) == 6
        and experiment["argv"][1:]
        == [
            "strength-book",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ],
        "generation exact strength-book argv",
    )
    require(
        experiment["canonical_plan_sha256"] == GENERATION_PLAN
        and experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and experiment["distance_units"] == "wall-distance/80"
        and experiment["value_perspective"] == "side-to-move",
        "generation scientific identity",
    )


def generation_check(spec, experiment):
    request = document(experiment["config"])
    require(set(request) == {"plan", "old_prefixes", "output"}, "generation request shape")
    require(request["output"] == spec["data_root"], "generation owned output binding")
    require(len(experiment["inputs"]) == 2, "generation exact two inputs")
    for field, full in zip(("plan", "old_prefixes"), experiment["inputs"], strict=True):
        require(
            request[field] == {k: full[k] for k in ("path", "sha256")},
            "generation exact plan/OPEN8 references",
        )
    require(experiment["inputs"][0]["sha256"] == GENERATION_PLAN, "generation fixed plan")
    document(experiment["inputs"][0])
    require(
        canonical_sha(document(experiment["inputs"][1])) == GENERATION_OPEN8,
        "generation fixed OPEN8",
    )
    require(
        canonical_sha(document(experiment["schedule"])) == GENERATION_SCHEDULE,
        "generation fixed512 schedule",
    )
    require(
        {r["name"]: r["path"] for r in spec["data"]}
        == {
            name: str(Path(spec["data_root"]) / filename)
            for name, filename in GENERATION_FILES.items()
        }
        and len(spec["data"]) == 4,
        "generation four durable outputs",
    )


COMPACT_CACHE_WIDTHS = {
    "geometry.bin": 66,
    "distance-steps.u8": 2,
    "terminal-margin.f32": 4,
    "labels.f32": 8,
    "completed-root-raw.f32": 4,
    "common-eligible.u8": 1,
    "sampling.bin": 6,
}


def cache_materialize_check(spec, experiment, manifest):
    """Only the existing saved-stream converter; no generation or empirical model calls."""
    request = document(experiment["config"])
    require(
        set(request) == {"schema", "stream", "intake_binding", "previous_cache", "output"}
        and request["schema"] == "quoridor.common-corpus-cache-materialization.v1"
        and request["output"] == spec["data_root"],
        "saved converter exact config/output",
    )
    require(
        experiment["models"] == []
        and experiment["planned_slots"] == 0
        and experiment.get("batch") is None
        and experiment.get("numerical_qualification") is None
        and spec["approved_plan"]["path"] == str(PILOT_PLAN)
        and experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and experiment["distance_units"] == "wall-distance/80"
        and experiment["value_perspective"] == "side-to-move",
        "saved codec scope/current approved plan",
    )
    binding = document(request["intake_binding"])
    require(
        binding["scope"] == "common-corpus"
        and binding["stream"] == {k: request["stream"][k] for k in ("path", "sha256")}
        and binding["stream_content"]["compressed"] == request["stream"]
        and binding["schedule"] == {k: experiment["schedule"][k] for k in ("path", "sha256")},
        "actual stream/intake/schedule pairing",
    )
    previous = document(request["previous_cache"])
    require(
        not Path(request["previous_cache"]["path"]).with_name("intake-incomplete.json").exists()
        and previous["schema"] == "quoridor-common-corpus-terminal-geometry-v2"
        and previous["stream_intake"]["status"] == "complete"
        and previous["source_content"] == binding["stream_content"]
        and previous["schedule_sha256"] == experiment["schedule"]["sha256"]
        and previous["common_corpus"]["config"]["selected_plan"]
        == {k: spec["approved_plan"][k] for k in ("path", "sha256")},
        "original retained cache/source identity; no plan substitution",
    )
    paths = {r["path"]: r for r in experiment["inputs"]}
    expected = {request[k]["path"] for k in ("stream", "intake_binding", "previous_cache")}
    expected |= {binding[k]["path"] for k in ("config", "sources", "schedule")}
    expected.add(spec["approved_plan"]["path"])
    for name in set(COMPACT_CACHE_WIDTHS) - {"sampling.bin"}:
        path = str(Path(request["previous_cache"]["path"]).parent / name)
        expected.add(path)
        ref = paths.get(path)
        require(
            ref is not None
            and ref["sha256"] == previous["sha256"][name]
            and ref["bytes"] == previous["rows"] * COMPACT_CACHE_WIDTHS[name],
            "original six binary custody",
        )
    require(
        set(paths) == expected and len(paths) == len(experiment["inputs"]),
        "closed saved codec input membership",
    )
    for key in ("stream", "intake_binding", "previous_cache"):
        require(paths[request[key]["path"]] == request[key], "actual converter input FileRef")
    for key in ("config", "sources", "schedule"):
        require(
            binding[key] == {k: paths[binding[key]["path"]][k] for k in ("path", "sha256")},
            "intake control lifetime",
        )
    require(paths[spec["approved_plan"]["path"]] == spec["approved_plan"], "current plan lifetime")
    require(
        experiment["argv"]
        == [
            manifest["artifact"]["path"],
            request["stream"]["path"],
            spec["data_root"],
            request["intake_binding"]["path"],
            request["intake_binding"]["sha256"],
        ],
        "existing terminal-cache exact four positional arguments",
    )
    require(
        len(spec["data"]) == 8
        and {x["name"]: x["path"] for x in spec["data"]}
        == {
            **{n: str(Path(spec["data_root"]) / n) for n in COMPACT_CACHE_WIDTHS},
            "cache_manifest": str(Path(spec["data_root"]) / "cache.json"),
        },
        "compact seven files plus last manifest",
    )


def experiment_check(spec):
    charged_roots(spec)
    experiment = document(spec["experiment"])
    require(experiment["schema"] == EXPERIMENT_SCHEMA, "experiment schema")
    experiment_phase_check(experiment)
    manifest = accepted_build(experiment["build_manifest"], spec["approved_plan"])
    require(manifest["artifact"] == spec["artifact"], "same actual executable")
    refs = [
        experiment["config"],
        *experiment["inputs"],
        experiment["schedule"],
    ]
    if experiment.get("numerical_qualification") is not None:
        refs.append(experiment["numerical_qualification"])
    require(isinstance(experiment["dynamic_libraries"], list), "declared library array required")
    for model in experiment["models"]:
        refs.extend([model["descriptor"], model["weights"]])
    for library in experiment["dynamic_libraries"]:
        require(
            isinstance(library["version"], str) and bool(library["version"].strip()),
            "dynamically loaded library version required",
        )
        refs.append(library["file"])
    refs.extend(caller_source_refs(spec, experiment))
    for ref in refs:
        read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
    if manifest.get("artifact_target", "quoridor-runner") == "terminal-cache":
        require(
            experiment["phase"] in {"materialize", "fit"},
            "converter only serves saved materialization or pinned Python fits",
        )
        if experiment["phase"] == "materialize":
            cache_materialize_check(spec, experiment, manifest)
    else:
        require(
            experiment["phase"] != "materialize"
            or isinstance(experiment.get("numerical_qualification"), dict),
            "ordinary model materialization still requires numerical qualification",
        )
    if experiment["phase"] == "generation":
        generation_check(spec, experiment)
    require(
        type(experiment["planned_slots"]) is int and 0 <= experiment["planned_slots"] <= 4096,
        "bounded planned denominator",
    )
    approved = approved_plan(spec, experiment)
    refs.append(spec["approved_plan"])
    if experiment["phase"] in {"corpus", "fit", "software-qualification"}:
        common_pilot_check(spec, experiment, manifest, approved)
    if experiment["phase"] == "arena":
        arena_plan_check(experiment, approved)
        require(
            document(experiment["config"])["output"] == spec["data_root"],
            "arena owned runtime output",
        )
    executable = manifest["artifact"]["path"]
    if experiment["phase"] in {"analysis", "fit", "software-qualification"}:
        python = manifest["tools"]["PYTHON"]["file"]
        read_ref(python, max(CONTROL_BYTES, python["bytes"]))
        executable = python["path"]
    require(spec["argv"][0] == executable, "executable argv drift")
    expected_argv = [
        a.replace("@EXPERIMENT@", spec["experiment"]["path"]).replace(
            "@EXPERIMENT_SHA256@", spec["experiment"]["sha256"]
        )
        for a in experiment["argv"]
    ]
    require(spec["argv"] == expected_argv, "exact experiment argv")
    require(bool(spec["data"]), "actual durable data required")
    owned(spec["data_root"], spec["owner"])
    require(
        not Path(spec["data_root"]).exists(), "exclusive scientific output; duplicate run refused"
    )
    if experiment["phase"] == "arena":
        require(
            {x["name"] for x in spec["data"]} >= {"journal", "result"},
            "mandatory scientific journal/result",
        )
    for finalizer in spec["finalizers"]:
        owned(finalizer["path"], spec["owner"])
    return (
        experiment,
        manifest,
        [*refs, experiment["build_manifest"], *build_input_refs(manifest, spec["approved_plan"])],
    )


def build_check(spec):
    artifact_target = spec.get("artifact_target", "quoridor-runner")
    require(artifact_target in {"quoridor-runner", "terminal-cache"}, "maintained build artifact")
    if artifact_target == "terminal-cache":
        converter = str(
            Path(spec["source"]["workspace"]) / "crates/quoridor-data/src/bin/terminal-cache.rs"
        )
        require(
            any(r["path"] == converter for r in spec["source"]["compiled_sources"].values())
            and "generator_compiled_sources" not in spec["source"],
            "converter has its own actual compiled projection",
        )
        for row in spec["commands"]:
            if row["role"] == "build":
                require(
                    row["argv"].count("--bin") == 1
                    and row["argv"][row["argv"].index("--bin") + 1] == artifact_target
                    and row["argv"].count("-p") == 1
                    and row["argv"][row["argv"].index("-p") + 1] == "quoridor-data",
                    "exact maintained converter build",
                )
    require(Path(spec["target"]).is_relative_to(Path(spec["owner"])), "isolated owned target")
    for name in ("target", "TMP", "private"):
        owned(spec[name], spec["owner"])
        if name != "target":
            require(not Path(spec[name]).exists(), "exclusive build ownership: " + name)
    if Path(spec["target"]).exists():
        owner = json.loads((Path(spec["target"]) / ".research-owner.json").read_bytes())
        require(
            owner
            == {
                "writer": spec["writer"],
                "target": spec["target"],
                "support_sha256": spec["support"]["sha256"],
            },
            "existing isolated target belongs to another owner",
        )
    handover = document(spec["target_handover"])
    require(
        handover["schema"] == "research.target-handover.v1" and handover["status"] == "HANDED_OVER",
        "serial target handover required",
    )
    require(
        handover["target"] == spec["target"] and handover["owned_remaining"] == [],
        "target handover identity",
    )
    require(
        handover["shared_serial_pool"] is True and not Path(handover["old_target"]).exists(),
        "old/new parallel target unsupported",
    )
    support = document(spec["support"])
    funded = support["funded_union_B"]
    target = handover["target_max_B"]
    private = handover["private_pool_B"]
    require(
        all(type(n) is int and n > 0 for n in (funded, target, private))
        and target + private + 67108864 + 8388608 <= funded <= 50000000000,
        "trusted handover pools inside issued whole support",
    )
    require(
        type(spec["limits"]["owned_B"]) is int
        and 0 < spec["limits"]["owned_B"] <= target + private + 67108864 + 8388608,
        "common build/private pool",
    )
    require(handover["target_writer"] == spec["writer"], "single issued writer/pool")
    private_copy_check(spec)
    adoption = document(spec["source_adoption"])
    require(
        adoption["schema"] == "quoridor.research.source-adoption.v1"
        and adoption["status"] == "ACCEPTED",
        "one source adoption required",
    )
    require(adoption["source"] == spec["source"], "accepted frozen source/patch")
    source = spec["source"]
    require(spec["cwd"] == source["workspace"], "Cargo cwd differs from adopted workspace")
    require(bool(source["compiled_sources"]), "adopted compiled-source projection required")
    source_check(spec["source"])
    require(
        source["lock"] in spec["dependency_refs"],
        "same adopted Cargo.lock required",
    )
    for ref in spec["dependency_refs"]:
        read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
    env = spec["env"]
    cargo_home = Path(env["CARGO_HOME"])
    require(cargo_home.is_absolute() and cargo_home.resolve() == cargo_home, "frozen Cargo home")
    workspace = Path(source["workspace"])
    configs = {
        str(p / ".cargo" / n)
        for p in [workspace, *workspace.parents]
        for n in ("config", "config.toml")
    }
    configs |= {str(cargo_home / n) for n in ("config", "config.toml")}
    require(
        {r["path"] for r in source["cargo_configs"]} == configs,
        "complete directly searched Cargo config witnesses",
    )
    require(
        env["CARGO_TARGET_DIR"] == spec["target"] and env["TMPDIR"] == spec["TMP"], "isolated env"
    )
    require(
        env["CARGO_NET_OFFLINE"] == "true" and env["RUSTUP_AUTO_INSTALL"] == "0",
        "offline/no install",
    )
    require(
        env["CARGO_BUILD_JOBS"] == "1" and env["CARGO_INCREMENTAL"] == "0", "serial bounded build"
    )
    require(
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] == "3" and env["CARGO_PROFILE_RELEASE_DEBUG"] == "0",
        "frozen release flags",
    )
    for key in ("RUSTC", "RUSTDOC", "CC", "CXX", "AR"):
        require(env[key] == spec["tools"][key]["file"]["path"], "pinned relevant tool env")
    require(
        {c["role"] for c in spec["commands"]} >= {"test", "lint", "build", "bindings"},
        "one affected qualification",
    )
    names = [c["name"] for c in spec["commands"]]
    require(
        len(names) == len(set(names)) and all(n.replace("-", "").isalnum() for n in names),
        "unique safe command names",
    )
    for c in spec["commands"]:
        require(
            c["role"] in {"test", "lint", "build", "bindings"}, "affected software commands only"
        )
        if c["role"] != "bindings":
            a = c["argv"]
            require(a[0] == spec["tools"]["CARGO"]["file"]["path"], "trusted Cargo argv")
            require(
                a.count("--manifest-path") == 1
                and ("--" not in a or a.index("--manifest-path") < a.index("--"))
                and a[a.index("--manifest-path") + 1] == source["manifest"]["path"]
                and not any(
                    x.startswith("--manifest-path=")
                    or x in {"--config", "-C"}
                    or x.startswith("--config=")
                    for x in a
                ),
                "one adopted Cargo manifest/config",
            )
            require(
                a[1] == {"test": "test", "lint": "clippy", "build": "build"}[c["role"]],
                "no cargo-run/extra workload in software phase",
            )
            require(
                "--offline" in a
                and "--locked" in a
                and "-j1" in a
                and "--message-format=json-render-diagnostics" in a,
                "Cargo pinned command/JSON",
            )
            require(
                not any(x.startswith("-A") or x.startswith("--allow") for x in a),
                "no compiler/lint allowance workaround",
            )
            if c["role"] == "lint":
                require(
                    "-Dwarnings" in a and "--no-deps" in a,
                    "ordinary scoped Clippy with warnings denied",
                )


def private_copy_check(spec, src=None):
    handover = document(spec["target_handover"])
    root = owned(handover["fresh_private_root"], spec["owner"])
    require(root == Path(spec["private"]).parent, "fresh private root binding")
    fresh = handover["fresh_private_forward_max_B"]
    upper = handover["private_candidate_upper_B"]
    group = handover["private_pool_B"]
    preceding = handover["old_private_retained_allocated_B"]
    require(
        all(type(n) is int for n in (fresh, upper, group, preceding))
        and 0 < upper <= fresh <= group
        and 0 <= preceding <= group,
        "positive private candidate/fresh/group bounds",
    )
    if src is None:
        return
    path = owned(src, spec["target"])
    info = path.lstat()
    require(
        stat.S_ISREG(info.st_mode) and 0 < info.st_size <= upper,
        "private candidate size/type before copy",
    )
    block = os.statvfs(root).f_frsize
    require(0 < block <= 65536, "private allocation unit")
    rounded = ((info.st_size + block - 1) // block) * block
    # Retain allocation already in this domain, plus a bounded custody/directory margin.
    prospective = allocated(root) + rounded + 65536
    require(prospective <= fresh, "fresh private room before copy")
    require(prospective + preceding <= group, "selected private group room before copy")


def copy_artifact(src, dst):
    desc, data = bound(src, 32 * 1024 * 1024)
    with Path(dst).open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    Path(dst).chmod(int(desc["mode"], 8))
    return bound(dst, 32 * 1024 * 1024)[0]


GENERATION_SOURCE_KEYS = frozenset(
    (
        "Cargo.lock",
        "ai/alphabeta.rs",
        "ai/lib.rs",
        "ai/sigma_mcts.rs",
        "core/game.rs",
        "core/lib.rs",
        "core/position.rs",
        "core/research.rs",
        "data/lib.rs",
        "inference/cuda.rs",
        "inference/lib.rs",
        "inference/tensorrt.rs",
        "nnue/features.rs",
        "nnue/lib.rs",
        "nnue/quantized.rs",
        "nnue/residual.rs",
        "nnue/simd.rs",
        "runner/Cargo.toml",
        "runner/arena.rs",
        "runner/arena_book.rs",
        "runner/arena_clock.rs",
        "runner/arena_manifest.rs",
        "runner/arena_statistics.rs",
        "runner/config.rs",
        "runner/lib.rs",
        "runner/main.rs",
        "runner/native_input.rs",
        "runner/nnue-diagnose.rs",
        "runner/research_manifest.rs",
        "runner/resources.rs",
        "runner/runtime.rs",
        "runner/sigma_clock.rs",
        "runner/value_search_compare.rs",
        "runner/value_search_strength.rs",
    )
)
RESEARCH_SOURCE_KEYS = GENERATION_SOURCE_KEYS | {"runner/sigma_qualification.rs"}
ORDERING_SOURCE_KEYS = frozenset(("ai/continuation_history.rs", "ai/static_ordering.rs"))
GENERATION_ORDERING_KEYS = GENERATION_SOURCE_KEYS | ORDERING_SOURCE_KEYS
RESEARCH_ORDERING_KEYS = RESEARCH_SOURCE_KEYS | ORDERING_SOURCE_KEYS
ASSESSMENT_SOURCE_KEYS = frozenset(("runner/ordering_assessment.rs",))
RESEARCH_ASSESSMENT_KEYS = RESEARCH_ORDERING_KEYS | ASSESSMENT_SOURCE_KEYS


def generation_source_correspondence(native, qualified):
    """Exact arena projection: retained34/35, ordering36/37, or assessment36/38; never unknown keys."""
    require(
        isinstance(qualified, dict)
        and set(qualified)
        in (RESEARCH_SOURCE_KEYS, RESEARCH_ORDERING_KEYS, RESEARCH_ASSESSMENT_KEYS),
        "qualified exact maintained source domain",
    )
    keys = set(qualified) - {"runner/sigma_qualification.rs"} - ASSESSMENT_SOURCE_KEYS
    require(
        isinstance(native, dict) and set(native) == keys,
        "generation exact source domain",
    )
    require(
        all(
            isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)
            for h in qualified.values()
        ),
        "qualified source hash shape",
    )
    require(
        native == {key: qualified[key] for key in keys},
        "generation shared source hash drift",
    )


def generation_evidence(experiment, values):
    """Metadata correspondence only; legal history/model qualification remains downstream."""
    build = document(experiment["build_manifest"])
    start, book, schedule, result = [json.loads(values[n]) for n in GENERATION_FILES]
    generation_source_correspondence(start["compiled_sources"], build["compiled_sources"])
    require(
        start["compiled_sources"] == book["compiled_sources"],
        "generation native maps drift",
    )
    evidence = {
        "schema": "quoridor.research.generation-evidence.v1",
        "phase": "generation",
        "numerical_qualification": None,
        "models_loaded": 0,
        "search_calls": 0,
        "games_started": 0,
        "scientific_planned_slots": 512,
        "artifact": build["artifact"],
        "compiled_sources": build["compiled_sources"],
        "compiled_sources_domain": (
            "research-qualified38-assessment360-v1"
            if set(build["compiled_sources"]) == RESEARCH_ASSESSMENT_KEYS
            else "research-qualified37-continuation360-v1"
            if set(build["compiled_sources"]) == RESEARCH_ORDERING_KEYS
            else "research-qualified35-v1"
        ),
        "native_compiled_sources": start["compiled_sources"],
        "native_compiled_sources_domain": (
            "arena-generation36-continuation360-v1"
            if set(start["compiled_sources"]) == GENERATION_ORDERING_KEYS
            else "arena-generation34-v1"
        ),
        "generation_compiled_sources_sha256": canonical_sha(start["compiled_sources"]),
        "book_sha256": sha(values["book"]),
        "book_semantic_sha256": canonical_sha(book),
        "schedule_sha256": sha(values["schedule"]),
        "schedule_semantic_sha256": canonical_sha(schedule),
        "config": experiment["config"],
        "inputs": experiment["inputs"],
        "schedule": experiment["schedule"],
        "rules": experiment["rules"],
        "limitation": "bound generation metadata; no numerical/model/history qualification",
    }
    require(
        start["request"] == document(experiment["config"])
        and start["planned_families"] == 128
        and start["attempt_upper"] == 1024
        and start["transition_upper"] == 16384,
        "generation start/source correspondence",
    )
    require(
        all(
            row[key] == 0
            for row in (start, result)
            for key in ("models_loaded", "search_calls", "games_started")
        ),
        "generation zero model/Search/game calls",
    )
    require(
        book["schema"] == result["schema"] == "quoridor.value-search-strength.book.v1"
        and book["complete"] is True
        and result["complete"] is True
        and len(book["families"]) == result["families"] == 128
        and [f["family_id"] for f in book["families"]] == list(range(128))
        and book["plan_sha256"] == experiment["canonical_plan_sha256"]
        and book["rules"] == experiment["rules"]
        and book["old_open8_sha256"] == experiment["inputs"][1]["sha256"]
        and book["old_open8_prefixes"] == document(experiment["inputs"][1])
        and book["attempted"] == result["attempted"] == len(book["attempts"])
        and 128 <= book["attempted"] <= 1024
        and book["transitions"] == result["transitions"]
        and 0 <= book["transitions"] <= 16384,
        "generation complete fixed128 metadata",
    )
    require(
        schedule == document(experiment["schedule"])
        and result["book_sha256"] == sha(values["book"])
        and result["schedule_sha256"] == sha(values["schedule"]),
        "generation book/schedule/result correspondence",
    )
    return evidence


def approved_plan(spec, experiment):
    """Use the integration-issued admission, not Experiment's self-declared plan."""
    admission = document(spec["admission"])
    require(
        admission["schema"] == "quoridor.research.phase-admission.v1"
        and admission["ready"] is True
        and admission["owner"] == spec["owner"]
        and admission["limits"] == spec["limits"]
        and admission["spec_sha256"] == spec["intent_sha256"]
        and admission["support_sha256"] == spec["support"]["sha256"]
        and admission["approved_plan"] == spec["approved_plan"],
        "integration-issued approved launch plan",
    )
    require(
        experiment["canonical_plan_sha256"] == spec["approved_plan"]["sha256"],
        "experiment substituted approved plan",
    )
    return document(spec["approved_plan"])


def arena_plan_check(experiment, plan):
    """One explicit JSON arena plan; config files own engines and search/clock limits."""
    require(
        set(plan)
        == {
            "schema",
            "phase",
            "comparison",
            "rules",
            "distance_units",
            "value_perspective",
            "book",
            "inputs",
            "models",
            "schedule",
            "family_ids",
            "matchups",
            "batches",
            "planned_slots",
        }
        and plan["schema"] == "quoridor.research.arena-plan.v1"
        and plan["phase"] == experiment["phase"] == "arena"
        and len(experiment["argv"]) == 6
        and experiment["argv"][1:]
        == ["arena", "--experiment", "@EXPERIMENT@", "--experiment-sha256", "@EXPERIMENT_SHA256@"]
        and plan["comparison"] in {"evaluator_fixed_depth", "evaluator_wall_time"}
        and plan["rules"] == experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and plan["distance_units"] == experiment["distance_units"] == "wall-distance/80"
        and plan["value_perspective"] == experiment["value_perspective"] == "side-to-move"
        and plan["inputs"] == experiment["inputs"]
        and plan["book"] in plan["inputs"]
        and plan["models"] == experiment["models"]
        and plan["schedule"] == experiment["schedule"],
        "arena declared scientific correspondence",
    )
    schedule = document(experiment["schedule"])
    planned = planned_game_slice(experiment, schedule, plan)
    config = document(experiment["config"])
    batch = plan["batches"][experiment["batch"]]
    require(experiment["config"] == batch["config"], "approved batch config")
    matchup = next(m for m in plan["matchups"] if m["id"] == batch["matchup"])
    a = config["arena"]
    engines = config["engines"]
    require(
        config["ruleset"] == "standard_2p_threefold"
        and config["games"] == len(planned)
        and all(
            type(config[k]) is int and config[k] == 1
            for k in ("workers", "active_games", "max_batch")
        )
        and config.get("inference") is None
        and config.get("inference_cpu_core") is None
        and config.get("cycle") is None
        and config.get("train_games") is None
        and config.get("validation_games") is None
        and engines == matchup["engines"]
        and len(engines) == 2
        and a["evaluator_sha256"] == matchup["evaluator_sha256"]
        and a["comparison"] == plan["comparison"]
        and a["clock_policy"] == "strict_unknown"
        and type(a["tt_entries"]) is int
        and 0 < a["tt_entries"] <= 1048576
        and type(a["retained_outcome_bytes"]) is int
        and 0 < a["retained_outcome_bytes"] <= config["max_output_bytes"]
        and a["search_source_sha256"][0] == a["search_source_sha256"][1],
        "arena equal runtime/backend/retention conditions",
    )
    used = set()
    for m in plan["matchups"]:
        require(len(m["engines"]) == len(m["evaluator_sha256"]) == 2, "two declared engines")
        for i, engine in enumerate(m["engines"]):
            require(engine["kind"] in {"nnue", "distance"}, "supported numerical backend")
            if engine["kind"] == "nnue":
                model = next(
                    (r for r in plan["models"] if r["descriptor"]["path"] == engine["model"]), None
                )
                require(
                    model is not None and model["evaluator_sha256"] == m["evaluator_sha256"][i],
                    "declared model/evaluator",
                )
                used.add(model["descriptor"]["path"])
            else:
                require(engine.get("model") is None, "pure distance model")
    require(len(used) == len(plan["models"]), "duplicate/unused model")
    for engine in engines:
        require(
            type(engine["depth"]) is int
            and 0 < engine["depth"] <= 200
            and type(engine["max_nodes"]) is int
            and engine["max_nodes"] > 0
            and type(engine["simd"]) is bool
            and all(
                type(engine[k]) in (int, float) and math.isfinite(engine[k])
                for k in ("distance_a", "distance_b")
            ),
            "finite engine limits",
        )
    require(
        all(engines[0][k] == engines[1][k] for k in ("depth", "max_nodes", "simd")),
        "equal search limits",
    )
    if plan["comparison"] == "evaluator_fixed_depth":
        require(
            all(engine.get("time_ms") is None for engine in engines)
            and a["return_reserve_ms"] == 0,
            "completed depth has no move clock",
        )
    else:
        require(
            type(engines[0]["time_ms"]) is int
            and engines[0]["time_ms"] > 0
            and engines[1]["time_ms"] == engines[0]["time_ms"]
            and type(a["return_reserve_ms"]) is int
            and 0 <= a["return_reserve_ms"] < engines[0]["time_ms"],
            "equal thinking clocks and reserve",
        )
    book = document(plan["book"])
    require(book["complete"] is True and book["rules"] == plan["rules"], "complete bound book")
    families = {f["family_id"]: f for f in book["families"]}
    require(
        len(families) == len(book["families"]) and set(plan["family_ids"]) <= families.keys(),
        "book family coverage",
    )
    require(
        len(a["book"]["openings"]) * 2 == len(planned)
        and len(a["first_candidate_colors"]) == len(planned) // 2,
        "local pair book",
    )
    for i, opening in enumerate(a["book"]["openings"]):
        slot = planned[i * 2]
        f = families[slot["family_id"]]
        ref = opening["reference"]
        require(
            opening["id"] == f["id"]
            and opening["prefix"] == f["prefix"]
            and opening["original_seed"] == f["seed"]
            and ref["source_sha256"] == plan["book"]["sha256"]
            and all(ref["settings"][k] == f[k] for k in ("family_id", "root_key", "history_counts"))
            and a["first_candidate_colors"][i] == slot["candidate_color"],
            "immutable book/history/colour",
        )
    return planned, config


def planned_game_slice(experiment, schedule, plan):
    count = experiment["planned_slots"]
    families = plan["family_ids"]
    matchups = [m["id"] for m in plan["matchups"]]
    require(
        type(count) is int
        and 0 < count <= 4096
        and count == plan["planned_slots"]
        and isinstance(families, list)
        and families
        and all(type(i) is int and i >= 0 for i in families)
        and len(set(families)) == len(families)
        and matchups
        and all(type(i) is int and i >= 0 for i in matchups)
        and len(set(matchups)) == len(matchups)
        and count == 2 * len(families) * len(matchups),
        "explicit planned family denominator",
    )
    require(isinstance(schedule, list) and len(schedule) == count, "full schedule")
    colors = set()
    for i, slot in enumerate(schedule):
        require(
            set(slot) == {"slot", "batch", "matchup", "local_game", "family_id", "candidate_color"}
            and all(type(v) is int and v >= 0 for v in slot.values())
            and slot["slot"] == i
            and slot["family_id"] in families
            and slot["matchup"] in matchups
            and slot["candidate_color"] in (0, 1),
            "typed unique planned slot",
        )
        colors.add((slot["matchup"], slot["family_id"], slot["candidate_color"]))
    require(len(colors) == count, "full family/colour coverage")
    covered = set()
    require(isinstance(plan["batches"], list) and bool(plan["batches"]), "declared batches")
    for i, batch in enumerate(plan["batches"]):
        require(
            set(batch) == {"batch", "matchup", "config", "slots"}
            and type(batch["batch"]) is int
            and batch["batch"] == i
            and type(batch["matchup"]) is int
            and batch["matchup"] in matchups
            and isinstance(batch["slots"], list)
            and batch["slots"]
            and len(batch["slots"]) % 2 == 0,
            "whole pair batch",
        )
        for local, global_slot in enumerate(batch["slots"]):
            require(
                type(global_slot) is int
                and 0 <= global_slot < count
                and global_slot not in covered,
                "slot ownership",
            )
            covered.add(global_slot)
            row = schedule[global_slot]
            mate_id = batch["slots"][local ^ 1]
            require(type(mate_id) is int and 0 <= mate_id < count, "pair slot")
            mate = schedule[mate_id]
            require(
                row["batch"] == i
                and row["matchup"] == batch["matchup"]
                and row["local_game"] == local
                and mate["family_id"] == row["family_id"]
                and mate["candidate_color"] != row["candidate_color"],
                "batch pair correspondence",
            )
    require(
        len(covered) == count
        and type(experiment.get("batch")) is int
        and 0 <= experiment["batch"] < len(plan["batches"]),
        "complete batch/planned coverage",
    )
    return [schedule[i] for i in plan["batches"][experiment["batch"]]["slots"]]


def arena_observation(config, row):
    """Audit owned native decisions without replaying geometry or Search."""
    accepted = []
    for obs in row["observations"]:
        index = obs["engine_index"]
        require(type(index) is int and 0 <= index < 2, "observation engine")
        for key in ("caller_seconds", "thinking_seconds", "value_stm"):
            value = obs.get(key)
            require(
                value is None or (type(value) in (int, float) and math.isfinite(value)),
                "nonfinite observation",
            )
        require(type(obs["accepted"]) is bool, "typed acceptance")
        if not obs["accepted"]:
            continue
        require(
            obs["failure"] is None
            and obs["engine_error"] is None
            and type(obs["action"]) is int
            and obs["pv"]
            and obs["pv"][0] == obs["action"]
            and type(obs["accepted_ns"]) is int
            and type(obs["admission_checked_ns"]) is int
            and type(obs["returned_ns"]) is int
            and obs["accepted_ns"] >= obs["admission_checked_ns"] >= obs["returned_ns"]
            and obs["counters"]["completed_snapshot_validation_failed"] is False,
            "illegal/incoherent acceptance",
        )
        a = config["arena"]
        if a["comparison"] == "evaluator_fixed_depth":
            require(
                type(obs["completed_depth"]) is int
                and obs["completed_depth"] == config["engines"][index]["depth"]
                and obs["stop"] == "depth_cap"
                and obs["value_stm"] is not None
                and obs["deadline_ns"] is None,
                "partial depth cannot publish action",
            )
        else:
            require(
                type(obs["deadline_ns"]) is int
                and obs["returned_ns"] <= obs["deadline_ns"]
                and obs["counters"]["authority_receipt_ns"] == obs["returned_ns"]
                and obs["counters"]["drain_finished_ns"] == obs["returned_ns"],
                "thinking authority/drain",
            )
        accepted.append(obs["action"])
    require(accepted == row["moves"], "accepted actions/durable moves")


def collect_data(spec, experiment):
    """Preserve actual durable files and partial facts; never substitute a console tail."""
    data = {
        "status": "PASS",
        "files": [],
        "errors": [],
        "planned_slots": experiment["planned_slots"],
        "observed_local_games": [],
        "missing_local_games": [],
        "batch": experiment.get("batch"),
        "global_campaign_complete": False,
    }
    values = {}
    for item in spec["data"]:
        try:
            owned(item["path"], spec["owner"])
            ref, raw = bound(item["path"], item["limit_B"])
            data["files"].append(ref)
            values[item["name"]] = raw
        except BaseException as error:
            data["errors"].append({"stage": item["name"], **error_fact(error)})
    if experiment.get("phase") == "generation":
        data["generation"] = {
            "schema": "quoridor.research.generation-evidence.v1",
            "phase": "generation",
            "numerical_qualification": None,
            "scientific_planned_slots": 512,
        }
        try:
            data["generation"] = generation_evidence(experiment, values)
            data["generation"]["experiment"] = spec["experiment"]
        except BaseException as error:
            data["errors"].append({"stage": "generation_metadata", **error_fact(error)})
    if experiment["phase"] == "arena":
        try:
            plan = approved_plan(spec, experiment)
            planned, config = arena_plan_check(experiment, plan)
            local_count = len(planned)
            data["missing_local_games"] = list(range(local_count))
            data["planned_global_slots"] = [x["slot"] for x in planned]
            config = document(experiment["config"])
            records = []
            raw = values["journal"]
            for line in raw.split(b"\n")[:-1]:
                require(len(line) <= 630784, "full per-game record cap")
                row = json.loads(line)
                game = row["game"]
                require(
                    type(game) is int
                    and 0 <= game < local_count
                    and game not in data["observed_local_games"],
                    "duplicate/unplanned journal game",
                )
                slot = next(x for x in planned if x["local_game"] == game)
                opening = config["arena"]["book"]["openings"][game // 2]
                require(
                    opening["reference"]["settings"]["family_id"] == slot["family_id"],
                    "global family via native batch config",
                )
                require(
                    row["candidate_color"] == slot["candidate_color"]
                    and row["family"] == f"{config['run_id']}-family-{game // 2:06}",
                    "journal family/colour drift",
                )
                require(
                    isinstance(row["observations"], list) and isinstance(row["moves"], list),
                    "full scientific per-game observations required",
                )
                require(row["status"] in {"goal", "forfeit", "draw", "unknown"}, "typed outcome")
                arena_observation(config, row)
                records.append(row)
                data["observed_local_games"].append(game)
                data["missing_local_games"] = sorted(
                    set(range(local_count)) - set(data["observed_local_games"])
                )
            require(not raw or raw.endswith(b"\n"), "partial journal tail")
            data["missing_local_games"] = sorted(
                set(range(local_count)) - set(data["observed_local_games"])
            )
            require(
                not data["missing_local_games"],
                "missing planned games; retained UNKNOWN denominator",
            )
            report = json.loads(values["result"])
            require(
                report["planned"] == local_count
                and report["run_id"] == config["run_id"]
                and report["all_workers_joined"] is True
                and report["stopped"] is None,
                "native run incomplete",
            )
            require(
                sorted(records, key=lambda x: x["game"])
                == sorted(report["outcomes"], key=lambda x: x["game"]),
                "journal/result correspondence",
            )
        except BaseException as error:
            data["errors"].append({"stage": "scientific_journal", **error_fact(error)})
    if experiment["phase"] in {"corpus", "fit", "software-qualification"}:
        try:
            if experiment["phase"] == "software-qualification":
                receipt = json.loads(values["qualification"])
                require(
                    receipt["schema"] == "quoridor.common-corpus-framework-qualification.v1"
                    and receipt["status"] == "PASS"
                    and receipt["tests_run"] == 3
                    and receipt["failures"] == receipt["errors"] == []
                    and receipt["actual_model_forwards"] == receipt["fit_updates"] == 0
                    and receipt["scientific_corpus_qualified"] is False,
                    "affected framework qualification failed",
                )
                data["scope"] = "software-only; no corpus or numerical PASS"
            elif experiment["phase"] == "fit":
                state = json.loads(values["run_status"])
                require(
                    state["status"] == "COMPLETED"
                    and state["fault"] is None
                    and state["step"] == 200,
                    "actual complete 200-update fit required",
                )
            else:
                report = json.loads(values["generation_result"])
                require(
                    report["scheduled"] == experiment["planned_slots"] == 8
                    and report["recorded"] == 8,
                    "full planned corpus denominator",
                )
                data["known_goals"] = report["goals"]
                data["known_draws"] = report["draws"]
                data["unknown"] = report["unknown"]
                require(
                    report["search_nodes"] <= 1_000_000_000, "actual returned corpus work ceiling"
                )
                cache = json.loads(values["cache_manifest"])
                require(
                    cache["stream_intake"]["status"] == "complete", "atomic shared cache intake"
                )
                content = json.loads(values["stream_content"])
                ref = content["compressed"]
                read_ref(ref, ref["bytes"])
                data["canonical_compressed_source"] = ref
                data["raw_content_sha256"] = content["raw_sha256"]
                data["raw_content_B"] = content["raw_bytes"]
        except BaseException as error:
            data["errors"].append({"stage": "common_pilot_data", **error_fact(error)})
    if (
        experiment["phase"] == "materialize"
        and document(experiment["build_manifest"]).get("artifact_target") == "terminal-cache"
    ):
        try:
            cache = json.loads(values["cache_manifest"])
            request = document(experiment["config"])
            previous = document(request["previous_cache"])
            require(
                not (Path(spec["data_root"]) / "intake-incomplete.json").exists()
                and cache["schema"] == "quoridor-common-corpus-terminal-geometry-v3"
                and cache["stream_intake"]["status"] == "complete"
                and cache["rows"] == previous["rows"]
                and cache["source_content"] == previous["source_content"]
                and cache["schedule_sha256"] == previous["schedule_sha256"]
                and cache["family_partition_sha256"] == previous["family_partition_sha256"]
                and cache["common_corpus"]["common_eligible_by_split"]
                == previous["common_corpus"]["common_eligible_by_split"]
                and cache["common_corpus"]["common_eligible_rows"]
                == previous["common_corpus"]["common_eligible_rows"],
                "complete saved cache migration with original census/lineage",
            )
            require(
                cache["files"] == {n: n for n in COMPACT_CACHE_WIDTHS}
                and set(cache["sha256"]) == set(cache["file_bytes"]) == set(COMPACT_CACHE_WIDTHS),
                "closed compact physical files",
            )
            for name, width in COMPACT_CACHE_WIDTHS.items():
                raw = values[name]
                require(
                    len(raw) == cache["rows"] * width == cache["file_bytes"][name]
                    and sha(raw) == cache["sha256"][name],
                    "actual compact byte/hash/count",
                )
                if name != "sampling.bin":
                    require(
                        cache["sha256"][name] == previous["sha256"][name],
                        "original binary bit identity",
                    )
            data["scope"] = "saved-only cache conversion; no games/Search/model/numerical PASS"
            data["cache_manifest"] = next(
                r for r in data["files"] if r["path"] == str(Path(spec["data_root"]) / "cache.json")
            )
        except BaseException as error:
            data["errors"].append({"stage": "cache_materialization", **error_fact(error)})
    if data["errors"]:
        data["status"] = "FAILED"
    return data


def generation_input_data(completion_ref):
    """Recheck original saved generation files; never promote the originating run or qualify models."""
    origin = Path(completion_ref["path"])
    require(
        origin.is_absolute() and origin.resolve() == origin and origin.name == "manifest.json",
        "canonical authoritative manifest.json required",
    )
    completion = document(completion_ref)
    require(
        completion["schema"] == COMPLETION_SCHEMA
        and completion["kind"] == "run"
        and completion["status"] in {"PASS", "FAILED"}
        and completion["cleanup_complete"] is True
        and completion["remaining"] == []
        and not Path(completion_ref["path"]).with_name("INCOMPLETE").exists(),
        "authoritative stopped generation origin required",
    )
    spec = document(completion["intent"])
    require(origin == Path(spec["output"]) / "manifest.json", "origin operation manifest identity")
    experiment = document(completion["experiment"])
    require(
        spec["kind"] == "run"
        and spec["experiment"] == completion["experiment"]
        and experiment["phase"] == "generation"
        and experiment["build_manifest"] == completion["build_manifest"],
        "same bound generation intent/experiment/build",
    )
    experiment_phase_check(experiment)
    generation_check(spec, experiment)
    require(len(completion["checks"]) == 1, "single original generation command required")
    check = completion["checks"][0]
    expected_argv = [
        a.replace("@EXPERIMENT@", completion["experiment"]["path"]).replace(
            "@EXPERIMENT_SHA256@", completion["experiment"]["sha256"]
        )
        for a in experiment["argv"]
    ]
    require(
        check["role"] == "run"
        and check["argv"] == spec["argv"] == expected_argv
        and check["capture_complete"] is True
        and not check["secondary"],
        "original generation return/caller/capture required",
    )
    settled(check["guardian_return"])
    read_ref(check["full_log"], min(CONTROL_BYTES, spec["limits"]["log_B"]))
    require(
        check["guardian_return"]["log_bytes_seen"] == check["full_log"]["bytes"],
        "original generation full log identity",
    )
    require(isinstance(experiment["dynamic_libraries"], list), "declared libraries required")
    require(
        all(
            isinstance(x["version"], str) and x["version"].strip()
            for x in experiment["dynamic_libraries"]
        ),
        "declared library versions required",
    )
    build = document(experiment["build_manifest"])
    require(
        build["schema"] == BUILD_SCHEMA
        and build["status"] == "PASS"
        and build["cleanup_complete"] is True
        and build["remaining"] == []
        and not Path(experiment["build_manifest"]["path"]).with_name("INCOMPLETE").exists()
        and build["artifact"] == spec["artifact"],
        "origin bound qualified build required",
    )
    require(
        all(
            type(x.get("limit_B")) is int and 0 < x["limit_B"] <= 4 * 1024**2 for x in spec["data"]
        ),
        "saved generation data bound",
    )
    saved = completion["data"].get("files")
    require(
        isinstance(saved, list) and len(saved) == 4, "four saved generation descriptors required"
    )
    for item, ref in zip(spec["data"], saved, strict=True):
        require(
            isinstance(ref, dict)
            and set(ref) == {"path", "sha256", "bytes", "mode"}
            and ref["path"] == item["path"]
            and type(ref["bytes"]) is int
            and 0 < ref["bytes"] <= item["limit_B"]
            and isinstance(ref["sha256"], str)
            and len(ref["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in ref["sha256"])
            and isinstance(ref["mode"], str)
            and len(ref["mode"]) == 4
            and ref["mode"][0] == "0"
            and all(c in "01234567" for c in ref["mode"]),
            "saved generation descriptor/individual bound",
        )
    require(sum(ref["bytes"] for ref in saved) <= 4 * 1024**2, "saved generation aggregate bound")
    # Individual allowances need not sum to the actual aggregate payload budget.
    # Bound current reads by the saved sizes, so drift cannot consume spare allowances.
    collection_spec = {
        **spec,
        "data": [
            {**item, "limit_B": ref["bytes"]} for item, ref in zip(spec["data"], saved, strict=True)
        ],
    }
    data = collect_data(collection_spec, experiment)
    require(
        len(data["files"]) == 4 and data["files"] == completion["data"]["files"],
        "original four durable generation identities required",
    )
    data["origin_completion"] = completion_ref
    data["origin_status"] = completion["status"]
    data["origin_primary"] = completion["primary"]
    data["origin_secondary"] = completion["secondary"]
    data["numerical_qualification"] = None
    # data.status describes correspondence only. The completion and original errors remain immutable.
    return data


def originating_job(spec_ref, spec):
    runtime = Path(os.environ.get("QUORIDOR_RESEARCH_JOB_DIR", ""))
    require(runtime.is_absolute() and runtime.resolve() == runtime, "canonical outer runtime")
    cfg_ref, cfg_raw = bound(runtime / "config.json")
    cfg = json.loads(cfg_raw)
    state = json.loads((runtime / "state.json").read_bytes())
    supervisor = state["supervisor"]
    require(
        supervisor["pid"] == os.getppid() and process.alive(supervisor),
        "actual originating outer supervisor",
    )
    expected = [
        sys.executable,
        "-B",
        str(ROOT / "scripts/dev/research-lifecycle.py"),
        spec["kind"],
        "--intent",
        spec_ref["path"],
        "--sha256",
        spec_ref["sha256"],
    ]
    fingerprint = sha(json.dumps(cfg, sort_keys=True).encode())
    require(
        cfg["argv"] == expected
        and cfg["cwd"] == spec["cwd"]
        and state["config_sha256"] == fingerprint
        and state["phase"] in {"starting", "running"},
        "originating job/config join",
    )
    child = process.identity(process.process_info(os.getpid()))
    require(child is not None, "actual lifecycle process identity")
    return {
        "runtime": str(runtime),
        "job_id": state["job_id"],
        "config": cfg_ref,
        "config_sha256": fingerprint,
        "supervisor": supervisor,
        "child": child,
    }


def execute(
    spec_ref,
    *,
    executor=process.execute,
    guard=physical_and_quiet,
    lock=lease,
    resource_factory=Limits,
):
    spec = document(spec_ref)
    require(spec["schema"] == "quoridor.research.lifecycle-intent.v1", "lifecycle intent schema")
    # The admitted hash excludes only the admission descriptor, to avoid a self-referential digest.
    admission_view = {k: v for k, v in spec.items() if k not in {"admission", "intent_sha256"}}
    require(
        sha(json.dumps(admission_view, sort_keys=True, separators=(",", ":")).encode())
        == spec["intent_sha256"],
        "admitted intent digest",
    )
    require(spec["kind"] in ("build", "run"), "build/run only")
    directory = owned(spec["output"], spec["owner"])
    require(not directory.exists(), "restart/duplicate operation refused")
    require(Path(spec["cwd"]).is_dir(), "owned existing cwd")
    result = {
        "schema": BUILD_SCHEMA if spec["kind"] == "build" else COMPLETION_SCHEMA,
        "kind": spec["kind"],
        "status": "UNKNOWN",
        "intent": spec_ref,
        "started_at": stamp(),
        "checks": [],
        "primary": None,
        "secondary": [],
        "cleanup_complete": False,
        "remaining": [],
        "owed_finalizers": spec["finalizers"],
    }
    primary, resources = None, None
    claimed, created_TMP = False, False
    refs = []
    try:
        result["originating_job"] = originating_job(spec_ref, spec)
        guard(spec)
        with lock():
            resources = resource_factory(spec)
            resources.check()
            try:
                if spec["kind"] == "build":
                    build_check(spec)
                    refs = [
                        *spec["source"]["files"],
                        *spec["dependency_refs"],
                        *[t["file"] for t in spec["tools"].values()],
                    ]
                else:
                    experiment, manifest, refs = experiment_check(spec)
                    result.update(
                        experiment=spec["experiment"],
                        build_manifest=experiment["build_manifest"],
                        planned_slots=experiment["planned_slots"],
                    )
                directory.mkdir()
                claimed = True
                new_json(directory / "INCOMPLETE", {"intent": spec_ref, "status": "UNKNOWN"})
                new_json(directory / "intent.json", spec)
                if spec["kind"] == "build":
                    if not Path(spec["target"]).exists():
                        Path(spec["target"]).mkdir()
                        new_json(
                            Path(spec["target"]) / ".research-owner.json",
                            {
                                "writer": spec["writer"],
                                "target": spec["target"],
                                "support_sha256": spec["support"]["sha256"],
                            },
                        )
                    Path(spec["TMP"]).mkdir()
                    created_TMP = True
                    Path(spec["private"]).parent.mkdir(exist_ok=True)
                    for name, tool in spec["tools"].items():
                        read_ref(tool["file"], max(CONTROL_BYTES, tool["file"]["bytes"]))
                        row = {
                            "name": "version-" + name.lower(),
                            "role": "version",
                            "argv": [tool["file"]["path"], *tool["version_args"]],
                        }
                        _, full = command(
                            spec, row, directory, resources, executor, ledger=result["checks"]
                        )
                        require(
                            full.read_text().strip() == tool["version"],
                            "trusted tool version drift",
                        )
                    candidate = None
                    for row in spec["commands"]:
                        if row["role"] == "bindings":
                            require(
                                candidate is not None
                                and row["argv"] == [spec["private"], "research-bindings"],
                                "same executable bindings",
                            )
                        result["active_command"] = row
                        _, full = command(
                            spec, row, directory, resources, executor, ledger=result["checks"]
                        )
                        check = result["checks"][-1]
                        if row["role"] == "bindings":
                            metadata = json.loads(full.read_bytes())
                            require(
                                metadata["executable_sha256"] == candidate["sha256"]
                                and metadata["model_calls"] == 0,
                                "actual zero-model bindings",
                            )
                            require(
                                metadata.get("artifact_target", "quoridor-runner")
                                == spec.get("artifact_target", "quoridor-runner"),
                                "actual selected executable metadata",
                            )
                            result["compiled_sources"] = metadata["compiled_sources"]
                            if "generator_compiled_sources" in spec["source"]:
                                expected_generator = {
                                    k: r["sha256"]
                                    for k, r in spec["source"]["generator_compiled_sources"].items()
                                }
                                require(
                                    metadata.get("generator_compiled_sources")
                                    == expected_generator,
                                    "current generator source binding",
                                )
                                result["generator_compiled_sources"] = metadata[
                                    "generator_compiled_sources"
                                ]
                            require(
                                metadata["compiled_sources"]
                                == {
                                    k: v["sha256"]
                                    for k, v in spec["source"]["compiled_sources"].items()
                                },
                                "compiled image differs from adopted source projection",
                            )
                        else:
                            cargo = cargo_report(full.read_bytes())
                            check["cargo"] = cargo
                            if row["role"] == "build":
                                matches = [
                                    a
                                    for a in cargo["artifacts"]
                                    if a["target"]["name"]
                                    == spec.get("artifact_target", "quoridor-runner")
                                    and a["target"]["kind"] == ["bin"]
                                    and a["profile"]["test"] is False
                                ]
                                require(
                                    len(matches) == 1, "one selected maintained executable artifact"
                                )
                                src = owned(matches[0]["executable"], spec["target"])
                                private_copy_check(spec, src)
                                candidate = copy_artifact(src, spec["private"])
                        result["active_command"] = None
                    require(
                        candidate is not None and result.get("compiled_sources"),
                        "actual artifact/bindings required",
                    )
                    result.update(
                        artifact=candidate,
                        artifact_target=spec.get("artifact_target", "quoridor-runner"),
                        source=spec["source"],
                        source_adoption=spec["source_adoption"],
                        tools=spec["tools"],
                        env=spec["env"],
                        dependency_refs=spec["dependency_refs"],
                    )
                else:
                    spec["env"] = {
                        **spec["env"],
                        "QUORIDOR_LIFECYCLE_INTENT": spec_ref["sha256"],
                        "QUORIDOR_LIFECYCLE_INTENT_PATH": spec_ref["path"],
                        "QUORIDOR_LIFECYCLE_PARENT_PID": str(os.getpid()),
                    }
                    if experiment["phase"] == "software-qualification":
                        Path(spec["data_root"]).mkdir()
                    row = {"name": "run", "argv": spec["argv"]}
                    run_error = None
                    try:
                        command(spec, row, directory, resources, executor, ledger=result["checks"])
                    except BaseException as error:
                        run_error = error
                    result["data"] = collect_data(spec, experiment)
                    if result["data"]["status"] != "PASS":
                        error = Refused(
                            "durable data finalization incomplete: "
                            + json.dumps(result["data"]["errors"])
                        )
                        if run_error is not None:
                            run_error.add_note("data finalization secondary: " + str(error))
                        else:
                            run_error = error
                    if run_error is not None:
                        raise run_error
                for ref in refs:
                    read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
                if spec["kind"] == "run":
                    for item in manifest["source"]["cargo_configs"]:
                        if item["file"] is None:
                            p = Path(item["path"])
                            require(not p.exists() and not p.is_symlink(), "Cargo config appeared")
                result["status"] = "PENDING_FINALIZATION"
            finally:
                if created_TMP:
                    active_error = sys.exception()
                    try:
                        Path(spec["TMP"]).rmdir()
                    except BaseException as cleanup_error:
                        result["secondary"].append(
                            {"stage": "TMP_cleanup", **error_fact(cleanup_error)}
                        )
                        if active_error is not None:
                            active_error.add_note("TMP cleanup secondary: " + repr(cleanup_error))
                        else:
                            raise
                    finally:
                        created_TMP = False
    except BaseException as error:
        primary = error
        result.update(
            status="CANCELLED"
            if isinstance(error, process.CycleStopped) and "signal" in str(error)
            else "FAILED",
            primary=error_fact(error),
        )
    finally:
        if result["secondary"]:
            result["status"] = "FAILED"
        result["finished_at"] = stamp()
        result["process_cleanup_complete"] = bool(result["checks"]) and all(
            c.get("guardian_return") is not None
            and c["guardian_return"].get("direct_child_reaped") is True
            and c["guardian_return"].get("cleanup_complete") is True
            and c["guardian_return"].get("remaining") == []
            and c["guardian_return"].get("finalization_errors", []) == []
            for c in result["checks"]
        )
        result["cleanup_complete"] = (
            result["process_cleanup_complete"]
            and not any(c.get("secondary") for c in result["checks"])
            and not any(x["stage"] == "TMP_cleanup" for x in result["secondary"])
        )
        # This candidate is not a completion or run-admissible manifest.
        if claimed:
            try:
                new_json(directory / "candidate.json", result)
            except BaseException as error:
                if primary is not None:
                    primary.add_note("candidate save secondary: " + repr(error))
                else:
                    primary = error
    if primary is not None:
        primary.add_note("lifecycle partial facts: " + json.dumps(result, allow_nan=False))
        raise primary
    return result


def _prepare_completion(directory, job_ref):
    """No child launch. Authoritative publish happens after every independent owed finalizer."""
    directory = Path(directory)
    require(
        directory.is_absolute() and (directory / "INCOMPLETE").is_file(),
        "new pending operation required",
    )
    with (directory / "finalizing").open("xb"):
        pass  # Restart cannot run a scientific command or independent finalizers twice.
    candidate = json.loads((directory / "candidate.json").read_bytes())
    errors = []
    job = {}
    outer_joined = False
    if candidate["status"] != "PENDING_FINALIZATION" or candidate["cleanup_complete"] is not True:
        errors.append({"stage": "candidate", "facts": candidate["primary"]})
    try:
        job = document(job_ref)
        origin = candidate["originating_job"]
        runtime = Path(origin["runtime"])
        require(job_ref["path"] == str(runtime / "result.json"), "different outer result runtime")
        cfg = document(origin["config"])
        state_ref, state_raw = bound(runtime / "state.json")
        state = json.loads(state_raw)
        candidate["outer_job_state"] = state_ref
        require(
            state["phase"] == "finished"
            and state["job_id"] == job["job_id"] == origin["job_id"]
            and state["config_sha256"]
            == origin["config_sha256"]
            == sha(json.dumps(cfg, sort_keys=True).encode())
            and state["supervisor"] == origin["supervisor"]
            and state["child"] == origin["child"]
            and state["outcome"] == job["outcome"]
            and bool(job["finished_at"])
            and job.get("direct_child_reaped") is True,
            "originating finished job/state/config/directwait join",
        )
        outer_joined = True
        require(
            job.get("outcome") == "succeeded"
            and job.get("exit_code") == 0
            and job.get("cleanup_complete") is True
            and job.get("remaining") == []
            and job.get("cleanup_errors", []) == [],
            "outer job unsuccessful or not cleaned",
        )
        expected = [
            sys.executable,
            "-B",
            str(ROOT / "scripts/dev/research-lifecycle.py"),
            candidate["kind"],
            "--intent",
            candidate["intent"]["path"],
            "--sha256",
            candidate["intent"]["sha256"],
        ]
        require(cfg["argv"] == expected, "different lifecycle job")
    except BaseException as error:
        errors.append({"stage": "outer_job", **error_fact(error), "available_result": job})
    for check in candidate["checks"]:
        for field in ("full_log", "persisted_process_receipt"):
            try:
                if field == "full_log":
                    require(check.get(field) is not None, "mandatory full command capture missing")
                if check.get(field) is not None:
                    read_ref(check[field], max(CONTROL_BYTES, check[field]["bytes"]))
            except BaseException as error:
                errors.append(
                    {
                        "stage": "command_log",
                        "command": check["name"],
                        "field": field,
                        **error_fact(error),
                    }
                )
        try:
            require(check.get("guardian_return") is not None, "returned command facts unavailable")
            settled(check["guardian_return"])
            require(
                check.get("capture_complete") is True
                and check["guardian_return"]["log_bytes_seen"] == check["full_log"]["bytes"],
                "full returned command capture not complete",
            )
        except BaseException as error:
            errors.append(
                {"stage": "command_return", "command": check["name"], **error_fact(error)}
            )
    if candidate["kind"] == "run":
        try:
            require(candidate["data"]["status"] == "PASS", "data finalization missing/failed")
            for ref in candidate["data"]["files"]:
                read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
        except BaseException as error:
            errors.append({"stage": "data_finalization", **error_fact(error)})
    for obligation in candidate["owed_finalizers"]:
        try:
            actual, raw = bound(obligation["path"], obligation["limit_B"])
            doc = json.loads(raw)
            for ref in doc["files"]:
                read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
            obligation["actual_receipt"] = actual
            require(doc["schema"] == "quoridor.research.data-finalizer.v1", "data finalizer schema")
            require(
                doc["status"] == "PASS" and doc["remaining"] == [], "owed finalizer failed/unknown"
            )
            require(doc["intent_sha256"] == candidate["intent"]["sha256"], "same finalizer intent")
            if obligation["kind"] == "journal":
                require(
                    doc["planned_slots"]
                    == (
                        candidate["planned_slots"]
                        if candidate["kind"] == "run"
                        and document(candidate["experiment"])["phase"] == "arena"
                        else 512
                    )
                    and doc["complete_planned_census"] is True,
                    "full scientific journal denominator",
                )
            elif obligation["kind"] != "data":
                raise Refused("unknown independent finalizer kind")
        except BaseException as error:
            errors.append({"stage": "owed_finalizer", **error_fact(error)})
    candidate["outer_job_result"] = job_ref
    candidate["secondary"].extend(errors)
    prior_status = candidate["status"]
    candidate["status"] = "FAILED" if candidate["primary"] or candidate["secondary"] else "PASS"
    if prior_status == "CANCELLED" or job.get("outcome") == "cancelled":
        candidate["status"] = "CANCELLED"
    candidate["authoritative_finished_at"] = stamp()
    candidate["remaining"] = [] if candidate["status"] == "PASS" else job.get("remaining", [])
    candidate["cleanup_complete"] = (
        outer_joined
        and candidate.get("cleanup_complete") is True
        and job.get("direct_child_reaped") is True
        and job.get("cleanup_complete") is True
        and job.get("remaining") == []
        and job.get("cleanup_errors", []) == []
    )
    if candidate["kind"] == "build" and candidate.get("artifact") is not None:
        try:
            read_ref(candidate["artifact"], 32 * 1024 * 1024)
            source_check(candidate["source"])
            expected = {
                k: ref["sha256"] for k, ref in candidate["source"]["compiled_sources"].items()
            }
            require(candidate["compiled_sources"] == expected, "final adopted source projection")
            if "generator_compiled_sources" in candidate["source"]:
                expected_generator = {
                    k: r["sha256"]
                    for k, r in candidate["source"]["generator_compiled_sources"].items()
                }
                require(
                    candidate.get("generator_compiled_sources") == expected_generator,
                    "final generator source projection",
                )
            bindings = [c for c in candidate["checks"] if c["role"] == "bindings"]
            require(bool(bindings), "actual bindings missing")
            for check in bindings:
                metadata = json.loads(read_ref(check["full_log"]))
                if "generator_compiled_sources" in candidate["source"]:
                    require(
                        metadata.get("generator_compiled_sources")
                        == candidate["generator_compiled_sources"],
                        "final generator bindings log",
                    )
                require(
                    metadata.get("artifact_target", "quoridor-runner")
                    == candidate.get("artifact_target", "quoridor-runner")
                    and metadata["compiled_sources"] == expected
                    and metadata["executable_sha256"] == candidate["artifact"]["sha256"]
                    and metadata["model_calls"] == 0,
                    "final artifact/adopted metadata join",
                )
        except BaseException as error:
            if candidate["status"] != "CANCELLED":
                candidate["status"] = "FAILED"
            candidate["cleanup_complete"] = False
            candidate["secondary"].append({"stage": "final_artifact_source", **error_fact(error)})
    new_json(directory / "manifest.json", candidate)
    fd = os.open(directory, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return candidate


def finalize(directory, job_ref, *, guard=physical_and_quiet, lock=lease, resource_factory=Limits):
    directory = Path(directory)
    candidate = json.loads((directory / "candidate.json").read_bytes())
    spec = document(candidate["intent"])
    require(
        owned(directory, spec["owner"]) == Path(spec["output"]), "finalization operation ownership"
    )
    guard(spec)
    with lock():
        resources = resource_factory(spec)
        resources.check()
        completion = _prepare_completion(directory, job_ref)
    # Critical reads, direct waits, data/log writes, lease/handle closes and
    # independent finalizers precede this last fallible publication operation.
    (directory / "INCOMPLETE").unlink()
    return completion


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "run"):
        p = commands.add_parser(name)
        p.add_argument("--intent", type=Path, required=True)
        p.add_argument("--sha256", required=True)
    p = commands.add_parser("finalize")
    p.add_argument("--operation", type=Path, required=True)
    p.add_argument("--job-result", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    args = parser.parse_args()
    if args.command == "finalize":
        ref, _ = bound(args.job_result)
        require(ref["sha256"] == args.sha256, "actual job result binding")
        result = finalize(args.operation, ref)
        return 0 if result["status"] == "PASS" else 1
    ref, _ = bound(args.intent)
    require(ref["sha256"] == args.sha256, "intent SHA")
    require(document(ref)["kind"] == args.command, "operation kind")
    execute(ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
