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
import random
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))
from quoridor_training import cycle_process as process  # noqa: E402

LEASE = Path(
    "/workspaces/quoridor/.artifacts/rust-migration/target/arena-software-writer.lock"
)
BUILD_SCHEMA = "quoridor.research.build-manifest.v1"
EXPERIMENT_SCHEMA = "quoridor.research.experiment.v1"
COMPLETION_SCHEMA = "quoridor.research.completion.v1"
ORIGIN_CUSTODY = ROOT / "research-data"
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
        require(
            stat.S_ISREG(info.st_mode) and info.st_size <= limit, "reference size/type"
        )
        data = f.read(limit + 1)
        require(
            len(data) == info.st_size and len(data) <= limit,
            "reference changed/oversize",
        )
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


def allocated(path, *, seen=None):
    # The storage policy charges shared device/inode allocation once.
    seen = set() if seen is None else seen
    total = 0
    pending = [Path(path)]
    while pending:
        base = pending.pop()
        try:
            info = base.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode), "owned namespace symlink")
        identity = (info.st_dev, info.st_ino)
        if identity in seen:
            continue
        seen.add(identity)
        total += info.st_blocks * 512
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(base) as entries:
                pending.extend(Path(e.path) for e in entries)
    return total


def owned(path, owner):
    path, owner = Path(path), Path(owner)
    require(
        path.is_absolute() and owner.is_absolute() and path.is_relative_to(owner),
        "write ownership",
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
            require(
                path.is_relative_to(data_root),
                "declared data outside charged data root",
            )
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


def issued_family_upper(spec, support):
    if spec["kind"] == "build":
        return 6 * 1024**3
    upper = 2 * 1024**3
    # A larger RUN envelope needs the actual Root-issued selected support,
    # independently bound again by the normal owner/spec/support admission.
    if support.get("issue") == "quoridor-4lc.374":
        resources = support.get("resources", {})
        require(
            support["schema"] == "quoridor.research.phase-support.v1"
            and resources.get("CPU") == resources.get("threads") == 1
            and resources.get("GPU") == 0
            and resources.get("controller_included") is True
            and resources.get("family_RAM_B") == 3 * 1024**3,
            "selected actual single-CPU whole family support",
        )
        upper = resources["family_RAM_B"]
    return upper


class Limits(process.CycleResources):
    """Reuse guardian RSS/deadline/pause; add owned positive allocation bounds."""

    def __init__(self, spec):
        self.spec = spec
        cfg = spec["limits"]
        for name in ("family_B", "host_reserve_B", "owned_B", "log_B", "free_B"):
            require(
                type(cfg[name]) is int and cfg[name] > 0,
                "positive priced limit: " + name,
            )
        support = document(spec["support"])
        require(
            cfg["family_B"] <= issued_family_upper(spec, support)
            and cfg["host_reserve_B"] >= 4 * 1024**3,
            "issued family/host envelope",
        )
        require(
            type(support["funded_union_B"]) is int
            and 0 < cfg["owned_B"] <= support["funded_union_B"] <= 50000000000,
            "issued inclusive whole support",
        )
        require(support["global_held_B"] <= 50000000000, "global holding")
        # Admission is issued phase-specific support, not a default scientific horizon.
        admission = document(spec["admission"])
        require(
            admission["schema"] == "quoridor.research.phase-admission.v1",
            "phase admission",
        )
        require(
            admission["owner"] == spec["owner"] and admission["limits"] == cfg,
            "issued owner/limits",
        )
        require(
            admission["spec_sha256"] == spec["intent_sha256"], "actual intent admission"
        )
        require(
            admission["support_sha256"] == spec["support"]["sha256"], "same support"
        )
        require(admission["ready"] is True, "phase not admitted")
        if spec["kind"] == "run":
            require(
                admission["approved_plan"] == spec["approved_plan"],
                "issued approved plan",
            )
        require(
            cfg["controller_B"] == 64 * 1024 * 1024, "whole family includes controller"
        )
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
        seen = set()
        require(
            sum(allocated(p, seen=seen) for p in self.charged_paths)
            <= self.spec["limits"]["owned_B"],
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
                and private + h["old_private_retained_allocated_B"]
                <= h["private_pool_B"],
                "retained private pool cap",
            )
            require(allocated(self.spec["TMP"]) <= 64 * 1024 * 1024, "TMP cap")
        if self.spec["support"]["sha256"] == PERF349_SUPPORT:
            require(allocated(self.spec["TMP"]) <= 4 * 1048576, "349 serial TMP cap")
            if self.spec.get("perf") is not None:
                path = Path(self.spec["perf"]["output"])
                if path.exists():
                    info = path.lstat()
                    require(
                        stat.S_ISREG(info.st_mode) and info.st_size < 12 * 1048576,
                        "349 perf cap; remaining samples/work UNKNOWN",
                    )


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
        identities.append(
            ((p / "physical_package_id").read_text(), (p / "core_id").read_text())
        )
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
        for fn in (
            self.file.flush,
            lambda: os.fsync(self.file.fileno()),
            self.file.close,
        ):
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
        if (
            reason == "compiler-message"
            and item.get("message", {}).get("level") == "warning"
        ):
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
        record.get("direct_child_reaped") is True
        and record.get("cleanup_complete") is True,
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
        budget = spec.get("command_timeout_seconds")
        if budget is not None:
            require(
                type(budget) is int and budget > 0, "positive admitted command timeout"
            )
            if getattr(resources, "deadline", None) is None:
                # Start at the first actual command, never during source preparation.
                # All commands in this operation share this deadline and cleanup reserve.
                resources.deadline = time.monotonic() + budget
        capture = Capture(
            directory / (row["name"] + ".full.log"), spec["limits"]["log_B"]
        )
        cpu_args = {"cpu_core": spec["limits"]["worker_cpu"]}
        if "child_cpu_cores" in spec:
            require(
                spec["kind"] == "run"
                and document(spec["experiment"])["phase"] == "corpus",
                "multi-core launch is only the qualified corpus",
            )
            cpu_args = {"cpu_core": None, "cpu_cores": spec["child_cpu_cores"]}
        record = executor(
            row["argv"],
            directory / (row["name"] + ".log"),
            getattr(resources, "deadline", None),
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
                require(
                    check["capture_complete"], "full returned capture missing/partial"
                )
        except BaseException as error:
            check["secondary"].append(
                {"stage": "capture_identity", **error_fact(error)}
            )
            if primary is not None:
                primary.add_note("capture identity secondary: " + repr(error))
            else:
                primary = error
    persisted = (directory / (row["name"] + ".log")).with_suffix(".process.json")
    if persisted.exists():
        try:
            check["persisted_process_receipt"] = bound(persisted)[0]
        except BaseException as error:
            check["secondary"].append(
                {"stage": "persisted_process_identity", **error_fact(error)}
            )
            if primary is not None:
                primary.add_note("persisted process secondary: " + repr(error))
            else:
                primary = error
    check["status"] = "FAILED" if primary is not None else "PASS"
    check["primary"] = error_fact(primary) if primary is not None else None
    if primary is not None:
        raise primary
    return record, capture.path


def source_metadata_check(source):
    """Git/Cargo provenance, not an independently maintained Rust dependency graph."""
    require(
        set(source)
        == {
            "workspace",
            "commit",
            "patch",
            "untracked_inputs",
            "manifest",
            "lock",
            "cargo_configs",
        },
        "Git/Cargo source record",
    )
    require(
        len(source["commit"]) == 40
        and all(c in "0123456789abcdef" for c in source["commit"]),
        "Git revision",
    )
    workspace = Path(source["workspace"])
    require(workspace.is_absolute(), "adopted workspace")
    for name, filename in (("manifest", "Cargo.toml"), ("lock", "Cargo.lock")):
        require(
            source[name]["path"] == str(workspace / filename), "adopted Cargo " + name
        )
    untracked = source["untracked_inputs"]
    require(
        type(untracked) is list
        and len({r["path"] for r in untracked}) == len(untracked),
        "unique used untracked inputs",
    )
    require(
        all(Path(r["path"]).is_relative_to(workspace) for r in untracked),
        "untracked input outside workspace",
    )
    for item in source["cargo_configs"]:
        if item["file"] is not None:
            require(item["file"]["path"] == item["path"], "Cargo config identity")


def source_check(source):
    """BUILD owns a standard Git revision/delta and actual Cargo inputs.

    Cargo/rustc own source dependency discovery. RUN does not inspect current Rust.
    """
    source_metadata_check(source)
    workspace = Path(source["workspace"])
    require(workspace.resolve() == workspace, "adopted workspace")

    def git(*args):
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(workspace), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=True,
        )
        require(len(completed.stdout) <= CONTROL_BYTES, "bounded Git provenance")
        return completed.stdout

    require(
        git("rev-parse", "HEAD").decode().strip() == source["commit"],
        "Git revision drift",
    )
    patch = b"" if source["patch"] is None else read_ref(source["patch"])
    require(
        git("diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", "--")
        == patch,
        "actual uncommitted Git delta drift",
    )
    untracked = git(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        "Cargo.toml",
        "Cargo.lock",
        ".cargo",
        "crates",
    )
    paths = {str(workspace / os.fsdecode(p)) for p in untracked.split(b"\0") if p}
    require(
        paths == {r["path"] for r in source["untracked_inputs"]},
        "used untracked Cargo inputs drift",
    )
    for ref in [source["manifest"], source["lock"], *source["untracked_inputs"]]:
        read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
    for item in source["cargo_configs"]:
        path = Path(item["path"])
        if item["file"] is None:
            require(
                not path.exists() and not path.is_symlink(), "Cargo config appeared"
            )
        else:
            read_ref(item["file"])


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


def numerical_fields(experiment, manifest):
    return {
        "schema": "quoridor.research.numerical-qualification.v1",
        "status": "PASS",
        "phase": experiment["phase"],
        "artifact_sha256": manifest["artifact"]["sha256"],
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


def ordering_qualification_shape(experiment):
    require(
        experiment["phase"] == "ordering-qualification"
        and experiment.get("numerical_qualification") is None
        and type(experiment["planned_slots"]) is int
        and experiment["planned_slots"] == 20
        and experiment.get("batch") is None,
        "only finite360 pre-Search qualification",
    )
    require(
        experiment["config"]["sha256"]
        == "4a1bb65baea495a99501a087aa59c8391fadbc9fa0719ad9c8350563388c2aa0"
        and experiment["schedule"]["sha256"]
        == "6671bbf8d04ed31fedbfeccdbfaf28dcf5c713e02866544f0d9c8de2110b8671"
        and experiment["canonical_plan_sha256"]
        == "ddb46782feb000f77f5e45d99ffde19d27bce9eaae0e7999afed97bb0a54948e",
        "360 frozen config/schedule/plan",
    )
    require(
        len(experiment["argv"]) == 6
        and experiment["argv"][1:]
        == [
            "ordering-qualify",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        and len(experiment["models"]) == 1
        and len(experiment["dynamic_libraries"]) == 5,
        "360 bounded caller/model/library scope",
    )
    model = experiment["models"][0]
    require(
        model["descriptor"]["sha256"]
        == "46ec2c4708f96dcf9fad579c2fb0d1299c6663df27412f0faac98267467715e1"
        and model["descriptor"]["bytes"] == 677
        and model["descriptor"]["mode"] == "0600"
        and model["weights"]["sha256"]
        == "046fe926e56b955b0fb7de8f147a74ec33eace9cbc00a55c307f9b6541ab9841"
        and model["weights"]["bytes"] == 49284
        and model["weights"]["mode"] == "0644"
        and model["evaluator_sha256"]
        == "96a5f41f875022d1752b9c999595ad58bfb2d42687a8f06de08d42b1c4215875",
        "360 exact BEST43 required",
    )


def ordering_qualification_evidence(experiment, manifest, values):
    report = json.loads(values["result.json"])
    rows = [json.loads(line) for line in values["observations.jsonl"].splitlines()]
    require(
        values["observations.jsonl"].endswith(b"\n")
        and report["schema"] == "quoridor.continuation360.input-qualification.v1"
        and report["status"] == "COMPLETE"
        and report["planned"] == report["qualified"] == 20
        and report["Search_calls"] == 0
        and len(rows) == 20
        and report["roots"] == rows,
        "360 full20 qualification/journal required",
    )
    for i, row in enumerate(rows):
        require(
            row["id"] == i
            and row["status"] == "QUALIFIED"
            and row["Search_calls"] == 0
            and row["model_evaluations_attempted"]
            == row["model_evaluations_returned"]
            == 2
            and row["parent_unchanged"] is True
            and row["plain_bits"] == row["scratch_bits"]
            and type(row["plain_value"]) in (int, float)
            and math.isfinite(row["plain_value"])
            and abs(row["plain_value"]) <= 1
            and row["scratch_value"] == row["plain_value"],
            "360 partial/nonfinite/precision/root refusal",
        )
    expected = numerical_fields({**experiment, "phase": "compare"}, manifest)
    expected["status"] = None
    claim = report["numerical_qualification"]
    require(claim == expected, "360 actual numerical subject drift")
    return claim


def finalize_numerical_claim(candidate):
    if candidate.get("kind") != "run":
        return
    try:
        if document(candidate["experiment"])["phase"] != "ordering-qualification":
            return
        claim = candidate.get("data", {}).get("numerical_qualification")
        if claim is not None:
            claim["status"] = (
                "PASS"
                if candidate["status"] == "PASS"
                and candidate["cleanup_complete"] is True
                and candidate["remaining"] == []
                else "UNKNOWN"
            )
    except BaseException as error:
        candidate["secondary"].append(
            {"stage": "numerical_claim_finalization", **error_fact(error)}
        )
        if candidate["status"] != "CANCELLED":
            candidate["status"] = "FAILED"
        candidate["cleanup_complete"] = False
        claim = candidate.get("data", {}).get("numerical_qualification")
        if isinstance(claim, dict):
            claim["status"] = "UNKNOWN"


PERF349_SCHEMA = "quoridor.current-search-perf349.process.v1"
PERF349_SUPPORT = "22e2138fe41ddbe142aa05f01ea1e30367219b2465195f4db5b4878e7dd1bf6b"
PERF349_SAMPLING = {
    "event": "cpu-clock:u",
    "frequency_Hz": 49,
    "call_graph": "dwarf,8192",
    "ring_pages": 64,
    "data_max_B": 12 * 1048576,
    "no_buildid_cache": True,
}


def perf349_schedule():
    rows = []
    for batch in range(6):
        role = "A" if batch < 3 else "B"
        for local in range(6):
            if local == 0:
                root, family, warm, ply, depth, session = 3, 102, False, None, 4, 0
            elif local == 1:
                root, family, warm, ply, depth, session = 1, 34, False, None, 6, 1
            else:
                root, family, warm, ply, depth, session = (
                    local + 2,
                    0,
                    True,
                    2 * (local - 2),
                    4,
                    2,
                )
            rows.append(
                {
                    "id": len(rows),
                    "process_index": batch,
                    "image_role": role,
                    "sweep": 1,
                    "local_request_id": local,
                    "session": session,
                    "diagnostic": False,
                    "profile": "cheap_control" if role == "A" else "cheap",
                    "depth": depth,
                    "original_root_index": root,
                    "family": family,
                    "warm": warm,
                    "local_ply": ply,
                    "node_cap": 2000000 if depth == 4 else 8000000,
                }
            )
    return rows


def perf349_config(experiment):
    config = document(experiment["config"])
    plan, batch = config["plan"], config["process_index"]
    require(
        set(config) == {"schema", "algorithm", "process_index", "image_role", "plan"}
        and config["schema"] == PERF349_SCHEMA
        and config["algorithm"] == "cheap-static376-integer-parent-v1"
        and type(batch) is int
        and 0 <= batch < 6
        and config["image_role"] == ("A" if batch < 3 else "B")
        and experiment["phase"] == "compare"
        and experiment["planned_slots"] == 6
        and experiment["batch"] == batch
        and experiment["numerical_qualification"] is not None
        and experiment["argv"][1:]
        == [
            "ordering-cheap-assess",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        and plan["schema"] == "quoridor.current-search-perf349.inputs.v1"
        and experiment["canonical_plan_sha256"] == plan["assessment"]["sha256"]
        and plan["resources"]["sha256"] == PERF349_SUPPORT
        and plan["resources"]["bytes"] == 7126
        and plan["resources"]["mode"] == "0644"
        and experiment["inputs"]
        == [
            plan[k]
            for k in (
                "book",
                "warm_origin",
                "warm_config",
                "warm_journal",
                "assessment",
                "resources",
            )
        ]
        and document(experiment["schedule"]) == perf349_schedule(),
        "349 exact six-call role/session/input authority",
    )
    method = document(plan["assessment"])
    require(
        method["schema"] == "quoridor.current-search-perf349.assessment.v1"
        and method["algorithm"] == config["algorithm"]
        and method["planned_Search_calls"] == 36
        and method["D4_calls"] == 30
        and method["D6_calls"] == 6
        and method["planned_sessions"] == 18
        and method["node_liability"] == 108000000
        and method["plain_calls"] == 24
        and method["sampled_calls"] == 12
        and method["calls_per_process"] == 6
        and method["schedule_sha256"] == experiment["schedule"]["sha256"]
        and method["fixed_order"]
        == [
            "A/plain-before",
            "A/perf-sampled",
            "A/plain-after",
            "B/plain-before",
            "B/perf-sampled",
            "B/plain-after",
        ]
        and method["sampling"] == PERF349_SAMPLING,
        "349 fixed method/sampling/denominators",
    )
    support = document(plan["resources"])
    require(
        support["issue"] == "quoridor-4lc.349" and support["whole_B"] == 80 * 1048576,
        "349 whole support",
    )
    return config


def perf349_argv(spec, experiment, native_argv):
    """Only the selected sampled passes introduce one standard perf parent."""
    if (
        experiment["argv"][1] != "ordering-cheap-assess"
        or document(experiment["config"])["schema"] != PERF349_SCHEMA
    ):
        require(spec.get("perf") is None, "perf cannot wrap another scope")
        return native_argv
    config = perf349_config(experiment)
    require(spec["support"] == config["plan"]["resources"], "349 actual phase support")
    require(
        spec.get("command_timeout_seconds") is None,
        "349 finite work, no elapsed deadline",
    )
    owned(spec["TMP"], spec["owner"])
    require(
        not os.path.lexists(spec["TMP"])
        and spec["env"].get("TMPDIR") == spec["TMP"]
        and spec["TMP"] in spec.get("owned_outputs", []),
        "349 fresh charged serial TMP",
    )
    native_files = {
        "planned": "planned.json",
        "observations": "observations.jsonl",
        "costs": "costs.jsonl",
        "result": "result.json",
    }
    require(
        {x["name"]: x["path"] for x in spec["data"] if x["name"] != "perf_data"}
        == {
            name: str(Path(spec["data_root"]) / filename)
            for name, filename in native_files.items()
        }
        and len(spec["data"]) == 4 + int(config["process_index"] % 3 == 1)
        and all(
            type(x["limit_B"]) is int and 0 < x["limit_B"] <= 512 * 1024
            for x in spec["data"]
            if x["name"] != "perf_data"
        ),
        "349 complete bounded native header/journals/footer",
    )
    sampled = config["process_index"] % 3 == 1
    if not sampled:
        require(spec.get("perf") is None, "349 plain pass cannot be profiled")
        return native_argv
    perf = spec["perf"]
    require(set(perf) == {"tool", "output"}, "one standard perf wrapper")
    require(perf["tool"]["path"] == "/usr/bin/perf", "selected standard perf tool")
    read_ref(perf["tool"], 16 * 1048576)
    output = str(Path(spec["output"]) / "perf.data")
    require(
        perf["output"] == output and not os.path.lexists(output),
        "exclusive perf output",
    )
    owned(output, spec["owner"])
    require(
        [x for x in spec["data"] if x["name"] == "perf_data"]
        == [{"name": "perf_data", "path": output, "limit_B": 12 * 1048576}],
        "complete bounded perf data",
    )
    return [
        perf["tool"]["path"],
        "record",
        "-e",
        "cpu-clock:u",
        "-F",
        "49",
        "--call-graph",
        "dwarf,8192",
        "-m",
        "64",
        "--max-size",
        "12M",
        "--no-buildid-cache",
        "-o",
        output,
        "--",
        *native_argv,
    ]


def perf349_evidence(spec, experiment, values):
    config = perf349_config(experiment)
    batch = config["process_index"]
    planned, result = json.loads(values["planned"]), json.loads(values["result"])
    rows = [json.loads(line) for line in values["observations"].splitlines()]
    costs = [json.loads(line) for line in values["costs"].splitlines()]
    requests = [row for row in perf349_schedule() if row["process_index"] == batch]
    expected = [
        {
            "id": row["local_request_id"],
            "pass": row["session"],
            "diagnostic": False,
            "profile": row["profile"],
            "depth": row["depth"],
            "root": row["original_root_index"],
            "warm": row["warm"],
            "node_cap": row["node_cap"],
        }
        for row in requests
    ]
    sampled = batch % 3 == 1
    require(
        planned["schema"] == "quoridor.current-search-perf349.intent.v1"
        and planned["fixed_projection"] == requests
        and planned["requests"] == expected
        and result["schema"] == "quoridor.current-search-perf349.result.v1"
        and result["experiment_sha256"] == spec["experiment"]["sha256"]
        and result["config_sha256"] == experiment["config"]["sha256"]
        and result["schedule_sha256"] == experiment["schedule"]["sha256"]
        and result["process_index"] == batch
        and result["image_role"] == config["image_role"]
        and result["campaign_planned"] == 36
        and result["planned"] == 6
        and result["planned_sessions"] == 3
        and result["perf_sampled"] is sampled
        and result["attempted"]
        == result["actual_Search_invocations"]
        == result["returned_Ok"]
        == 6
        and result["returned_Err"] == 0
        and result["session_setup_Ok"] == 3
        and result["session_setup_Err"] == 0
        and len(rows) == 6
        and len(costs) == 6
        and [row["request_id"] for row in costs] == list(range(6))
        and [row["requests"] for row in result["passes"]] == [1, 1, 4]
        and len(result["root_whole_intervals"]) == 6
        and [row["request"] for row in rows] == expected
        and all(row["status"] in {"COMPLETE", "UNKNOWN"} for row in rows)
        and result["completed_requested_depth"]
        == sum(row["status"] == "COMPLETE" for row in rows)
        and result["planned_UNKNOWN"] == 6 - result["completed_requested_depth"]
        and result["status"]
        == ("COMPLETE" if result["planned_UNKNOWN"] == 0 else "COMPLETED_WITH_UNKNOWN")
        and 0 <= result["node_liability"] <= 18000000,
        "349 complete six-attempt census; capped calls stay UNKNOWN",
    )
    require(
        not (Path(spec["data_root"]) / "INCOMPLETE").exists(),
        "349 native finalization incomplete",
    )
    origin = result["runtime_launch_origin"]
    require(
        origin == planned["runtime_launch_origin"],
        "349 actual launch receipt correspondence",
    )
    if sampled:
        require(
            values["perf_data"][:8] == b"PERFILE2"
            and len(values["perf_data"]) < 12 * 1048576,
            "perf file missing/unsupported/at cap; profiling UNKNOWN, no refill",
        )
    return {
        "planned": 6,
        "complete_depth": result["completed_requested_depth"],
        "UNKNOWN": result["planned_UNKNOWN"],
        "sampled": sampled,
        "runtime_launch_origin": origin,
        "profiling_sufficiency": "UNKNOWN; saved perf loss/unwind/period/interval analysis still required",
    }


def cheap_ordering_inputs(experiment, qualified):
    """Fixed376 projection is new authority; oldQ remains original input/head only."""
    config = document(experiment["config"])
    if config["schema"] == PERF349_SCHEMA:
        perf349_config(experiment)
        plan = config["plan"]
        original = document(qualified["config"])
        require(
            all(
                plan[k] == original[k]
                for k in ("book", "warm_origin", "warm_config", "warm_journal")
            )
            and all(
                experiment[k] == qualified[k]
                for k in (
                    "rules",
                    "distance_units",
                    "value_perspective",
                    "models",
                    "dynamic_libraries",
                )
            ),
            "349 original input/head model/library scope drift",
        )
        return {
            "algorithm": config["algorithm"],
            "approved_plan": plan["assessment"],
            "schedule": experiment["schedule"],
            "resources": plan["resources"],
        }
    plan = config["plan"]
    process = config["process_index"]
    require(
        set(config) == {"schema", "algorithm", "process_index", "image_role", "plan"}
        and config["schema"] == "quoridor.cheap-static376.process.v1"
        and config["algorithm"] == "cheap-static376-integer-parent-v1"
        and type(process) is int
        and 0 <= process < 4
        and config["image_role"] == ["A", "B", "B", "A"][process]
        and experiment["phase"] == "compare"
        and experiment["planned_slots"] == 20
        and experiment["batch"] == process
        and experiment["argv"][1:]
        == [
            "ordering-cheap-assess",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        and plan["schema"] == "quoridor.cheap-static376.inputs.v1"
        and experiment["canonical_plan_sha256"] == plan["assessment"]["sha256"]
        and plan["resources"]["sha256"]
        == "0cb8599c9c1359c6bf2ca38c371805cdf39f4146f51efc9d35045c884c5e61cb"
        and plan["resources"]["bytes"] == 4372
        and experiment["inputs"]
        == [
            plan[k]
            for k in (
                "book",
                "warm_origin",
                "warm_config",
                "warm_journal",
                "assessment",
                "resources",
            )
        ],
        "376 fixed process/profile/authority drift",
    )
    original = document(qualified["config"])
    require(
        all(
            plan[k] == original[k]
            for k in ("book", "warm_origin", "warm_config", "warm_journal")
        )
        and all(
            experiment[k] == qualified[k]
            for k in (
                "rules",
                "distance_units",
                "value_perspective",
                "models",
                "dynamic_libraries",
            )
        ),
        "376 original20 input/head/model/library scope drift",
    )
    return {
        "algorithm": config["algorithm"],
        "approved_plan": plan["assessment"],
        "schedule": experiment["schedule"],
        "resources": plan["resources"],
    }


def retained_ordering_source(
    current, original, adoption, qualification, original_ref, cheap=None
):
    """One reviewed Source adoption; never rewrite the original numerical subject."""
    reuse = adoption["retained_ordering_numerical"]
    require(
        type(reuse) is dict
        and set(reuse)
        == (
            {"scope", "qualification", "build_manifest"}
            | ({"cheap_static376"} if cheap is not None else set())
        ),
        "single adopted numerical scope; no source graph",
    )
    require(
        adoption["schema"] == "quoridor.research.source-adoption.v1"
        and adoption["status"] == "ACCEPTED"
        and adoption["source"] == current["source"]
        and reuse["scope"] == "ordering20-input-and-head-v1"
        and reuse["qualification"] == qualification
        and reuse["build_manifest"] == original_ref
        and (cheap is None or reuse["cheap_static376"] == cheap)
        and original["schema"] == BUILD_SCHEMA
        and original["status"] == "PASS"
        and original["cleanup_complete"] is True
        and original["remaining"] == []
        and original["source"]["workspace"] == current["source"]["workspace"],
        "ordering retained numerical adoption/subject mismatch",
    )
    require(
        {"test", "lint", "build"}
        <= {
            c["role"]
            for c in original["checks"]
            if c["guardian_return"]["exit_code"] == 0
            and c["guardian_return"]["cleanup_complete"] is True
        },
        "ordering original build software incomplete",
    )
    require(
        [c["argv"] for c in original["checks"] if c["role"] == "build"]
        == [c["argv"] for c in current["checks"] if c["role"] == "build"],
        "ordering actual release compiler flags changed",
    )
    for field in ("manifest", "lock", "cargo_configs"):
        require(
            original["source"][field] == current["source"][field],
            "ordering native build input changed",
        )
    # Reusing the old input/head result keeps its native compiler/codegen
    # subject. Current BUILD and RUN own all other tools and runtime inputs;
    # controller Python and unrelated environment keys are not this subject.
    require(
        isinstance(original["tools"].get("RUSTC"), dict)
        and isinstance(original["tools"]["RUSTC"].get("file"), dict)
        and isinstance(original["tools"]["RUSTC"].get("version"), str)
        and bool(original["tools"]["RUSTC"]["version"].strip())
        and original["tools"]["RUSTC"] == current["tools"].get("RUSTC"),
        "ordering native compiler changed",
    )
    for flag in (
        "RUSTFLAGS",
        "CARGO_PROFILE_RELEASE_OPT_LEVEL",
        "CARGO_PROFILE_RELEASE_DEBUG",
    ):
        require(
            isinstance(original["env"].get(flag), str)
            and original["env"][flag] == current["env"].get(flag),
            "ordering native release flags changed",
        )
    # Compare recorded Cargo/Rust configuration, not the runtime environment.
    # This includes all profiles, target/compiler selectors, flags, wrappers and
    # rustup selection. Even non-codegen Cargo settings must match in this scope;
    # we do not decode options or certify unrecorded effective configuration.
    native_env = []
    for subject in (original, current):
        require(isinstance(subject["env"], dict), "native build environment")
        recorded = {
            key: value
            for key, value in subject["env"].items()
            if key.startswith(("CARGO", "RUST"))
        }
        require(
            all(isinstance(value, str) for value in recorded.values()),
            "recorded native configuration values",
        )
        native_env.append(recorded)
    require(
        native_env[0] == native_env[1], "ordering recorded native configuration changed"
    )


def numerical_check(experiment, manifest, *, refs=None):
    q = document(experiment["numerical_qualification"])
    numerical_manifest = manifest
    claim_experiment = experiment
    cheap = experiment["argv"][1] == "ordering-cheap-assess"
    if cheap or experiment["argv"][1] == "ordering-assess":
        reference = experiment["numerical_qualification"]
        require(
            Path(reference["path"]).name == "manifest.json"
            and not Path(reference["path"]).with_name("INCOMPLETE").exists(),
            "authoritative360 numerical manifest",
        )
        require(
            q["schema"] == COMPLETION_SCHEMA
            and q["status"] == "PASS"
            and q["cleanup_complete"] is True
            and q["remaining"] == []
            and q["primary"] is None
            and q["secondary"] == []
            and q["data"]["status"] == "PASS",
            "360 qualification outer/finalizer incomplete",
        )
        qualified = document(q["experiment"])
        ordering_qualification_shape(qualified)
        correspondence = cheap_ordering_inputs(experiment, qualified) if cheap else None
        require(
            cheap
            or all(
                qualified[k] == experiment[k]
                for k in (
                    "config",
                    "schedule",
                    "inputs",
                    "models",
                    "dynamic_libraries",
                    "canonical_plan_sha256",
                )
            ),
            "360 qualified source/model/input/library drift",
        )
        if qualified["build_manifest"] != experiment["build_manifest"]:
            original_ref = qualified["build_manifest"]
            require(
                Path(original_ref["path"]).name == "manifest.json"
                and not Path(original_ref["path"]).with_name("INCOMPLETE").exists(),
                "ordering original build is provisional",
            )
            original = document(original_ref)
            adoption_ref = manifest["source_adoption"]
            require(
                Path(adoption_ref["path"]).is_relative_to(
                    Path(manifest["source"]["workspace"]) / "research-data"
                ),
                "ordering reuse belongs to normal integration source adoption",
            )
            adoption = document(adoption_ref)
            retained_ordering_source(
                manifest, original, adoption, reference, original_ref, correspondence
            )
            numerical_manifest = original
            if refs is not None:
                refs.extend([q["experiment"], original_ref, adoption_ref])
        if cheap:
            require(
                qualified["build_manifest"] != experiment["build_manifest"],
                "376 old20 artifact cannot be80 caller",
            )
            claim_experiment = {**qualified, "phase": "compare"}
        q = q["data"]["numerical_qualification"]
    expected = numerical_fields(claim_experiment, numerical_manifest)
    require(
        all(q.get(k) == v for k, v in expected.items()),
        "current numerical/source/model/input correspondence",
    )
    return q


def project_interpreter(experiment):
    """Current Python ABI is an admitted input, independent of native BUILD tooling."""
    expected = {
        "path": "/home/vscode/.cache/inference/python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14",
        "sha256": "5a91882290532b2719eaca77c0f3a7448bd73b9214e56df57bc59004560a80c6",
        "bytes": 32418544,
        "mode": "0755",
    }
    require(
        experiment["phase"] in {"analysis", "fit", "software-qualification"},
        "project interpreter phase",
    )
    selected = [r for r in experiment["inputs"] if r["path"] == expected["path"]]
    require(
        len(selected) == 1 and selected[0] == expected,
        "bound qualified training interpreter",
    )
    require(
        str(project_python().resolve(strict=True)) == expected["path"],
        "shared venv/admitted regular binary correspondence",
    )
    cfg_path = str(project_python().parent.parent / "pyvenv.cfg")
    require(
        len([ref for ref in experiment["inputs"] if ref["path"] == cfg_path]) == 1,
        "current environment configuration must be separately input-bound",
    )
    # experiment_check reads all ordered inputs before dispatch and returns them
    # for the ordinary after-command lifetime check; no second authority record.
    return selected[0]


def project_python():
    """One prepared venv; the regular binary stays separately FileRef-bound."""
    # Source/build/owner ROOT stays worktree-local; the existing shell binding
    # selects only canonical Main project metadata, independently checked here.
    common = Path(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(ROOT),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ],
            text=True,
            timeout=5,
        ).strip()
    ).parent
    selected = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
    require(
        selected.is_absolute() and selected == common,
        "canonical Main project metadata binding",
    )
    layout = json.loads((selected / "research-paths.json").read_bytes())
    environment = Path(layout["environments"]["project"])
    require(
        os.environ["QUORIDOR_PROJECT_ENV"] == str(environment),
        "canonical shared project environment",
    )
    python = environment / "bin/python"
    require(
        environment.is_absolute()
        and (environment / "pyvenv.cfg").is_file()
        and python.is_file(),
        "prepared shared project Python required",
    )
    return python


def common_training_environment(spec):
    """Shared current project import/thread predicate for admitted Python fits."""
    require(
        spec["cwd"] == str(ROOT)
        and spec["env"].get("PYTHONDONTWRITEBYTECODE") == "1"
        and spec["env"].get("PYTHONPATH") == str(ROOT / "python")
        and all(
            spec["env"].get(k) == "1"
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        ),
        "pinned framework/import/thread environment",
    )


def public_replay_fit_check(spec, experiment, manifest, approved):
    """Current selected same-z arms through the ordinary fit custody boundary."""
    require(
        experiment["phase"] == "fit"
        and spec["approved_plan"]["path"] == str(PILOT_PLAN),
        "canonical selected fit plan",
    )
    study = approved["public_replay_study"]
    config = document(experiment["config"])
    require(
        study["issue"] == "quoridor-4lc.371"
        and study["scientific_entry"] is True
        and experiment["planned_slots"] == 0
        and experiment.get("batch") is None
        and experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and experiment["distance_units"] == "wall-distance/80"
        and experiment["value_perspective"] == "side-to-move"
        and "child_cpu_cores" not in spec,
        "human-selected nongame public replay rules/units/scope",
    )
    project_interpreter(experiment)
    python = str(project_python())
    common_training_environment(spec)
    require(
        len(spec["argv"]) == 13
        and spec["argv"][:5] == [python, "-B", "-m", "quoridor_training.train", "train"]
        and spec["argv"][5:9]
        == [
            "--cache",
            str(PILOT_DATA / "cache-compact-v3"),
            "--output",
            spec["data_root"],
        ]
        and spec["argv"][9:11] == ["--config", experiment["config"]["path"]]
        and spec["argv"][11] == "--input-binding",
        "selected maintained replay trainer/config/output",
    )
    ref = next((r for r in experiment["inputs"] if r["path"] == spec["argv"][12]), None)
    require(ref is not None, "ordinary guarded replay input binding required")
    binding = document(ref)
    require(
        binding["selected_plan"] == spec["approved_plan"]
        and binding["fit_config_sha"] == experiment["config"]["sha256"]
        and binding["paired_fit_configs"] == study["paired_fit_configs"]
        and experiment["config"] in binding["paired_fit_configs"],
        "trusted current approved plan and same paired config digest",
    )
    require(
        all(r in experiment["inputs"] for r in binding["paired_fit_configs"])
        and all(
            binding[k] in experiment["inputs"]
            for k in (
                "public_membership",
                "public_acceptance",
                "added_membership",
                "diagnostic_indices",
            )
        ),
        "ordered immutable input/config memberships",
    )
    cache = document(binding["added_membership"])
    require(
        binding["added_membership"]["path"]
        == str(PILOT_DATA / "cache-compact-v3/cache.json")
        and not (PILOT_DATA / "cache-compact-v3/intake-incomplete.json").exists()
        and cache["schedule_sha256"] == binding["schedule_sha256"]
        and cache["family_partition_sha256"] == binding["family_partition_sha256"]
        and cache["source_binding"] == binding["dataset"],
        "same published binary common cache lineage",
    )
    for name, width in COMPACT_CACHE_WIDTHS.items():
        path = str(PILOT_DATA / "cache-compact-v3" / name)
        matched = [r for r in experiment["inputs"] if r["path"] == path]
        require(
            len(matched) == 1
            and matched[0]["sha256"] == cache["sha256"][name]
            and matched[0]["bytes"]
            == cache["rows"] * width
            == cache["file_bytes"][name],
            "exact seven compact binary input refs",
        )
    warm = config["experiment"]["warm_start"]
    require(
        experiment["models"]
        == [
            {
                "descriptor": warm["descriptor"],
                "weights": warm["weights"],
                "evaluator_sha256": warm["evaluator_sha256"],
            }
        ],
        "same immutable BEST43 model",
    )
    require(
        Path(spec["data_root"]).is_relative_to(
            Path(spec["owner"]) / ".artifacts/public-replay371-v1"
        )
        and {x["path"] for x in spec["data"]}
        == {
            str(Path(spec["data_root"]) / name)
            for name in (
                "training.json",
                "curves.json",
                "curves.csv",
                "exposure.npz",
                "last.pt",
                "last-model/manifest.json",
                "last-model/weights.f32",
                "last-model/training-target.json",
            )
        }
        and {x["name"] for x in spec["data"]} >= {"training", "curves"},
        "exclusive replay arm output and owed immutable evidence",
    )
    if config["experiment"]["condition"] == "replay":
        require(
            binding["prior_fit_manifest"] in experiment["inputs"]
            and binding["prior_fit_result"] in experiment["inputs"],
            "actual first arm completion/result inputs before second entry",
        )
    # Refuse all public payload inputs before the generic FileRef reader.
    # Only manifest/acceptance and bounded indexed accesses carry this data.
    public_root = Path(binding["public_membership"]["path"]).parent
    require(
        all(
            not Path(r["path"]).resolve().is_relative_to(public_root.resolve())
            or r == binding["public_membership"]
            for r in experiment["inputs"]
        ),
        "no repeated public payload hash or sealed input",
    )
    from quoridor_training.public_replay import admit

    admit(
        str(PILOT_DATA / "cache-compact-v3"),
        experiment["config"]["path"],
        ref["path"],
        config,
    )
    numerical_check(experiment, manifest)


def common_pilot_check(spec, experiment, manifest, approved):
    phase = experiment["phase"]
    if (
        phase == "fit"
        and document(experiment["config"])["experiment"]["study"] == "public-replay-v1"
    ):
        public_replay_fit_check(spec, experiment, manifest, approved)
        return
    require(
        spec["approved_plan"]["path"] == str(PILOT_PLAN), "canonical common pilot plan"
    )
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
        require(
            "child_cpu_cores" not in spec, "multi-core corpus cannot widen other phases"
        )
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
        numerical_check(experiment, manifest)
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
            common["selected_plan"]
            == {k: spec["approved_plan"][k] for k in ("path", "sha256")}
            and experiment["inputs"][0] == spec["approved_plan"]
            and document(experiment["schedule"]) == study["corpus"]["blind_schedule"],
            "blind corpus selected-plan/schedule binding",
        )
        return
    require(
        experiment["planned_slots"] == 0, "fit/qualification is a nongame operation"
    )
    project_interpreter(experiment)
    python = str(project_python())
    common_training_environment(spec)
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
            and spec["argv"]
            == [python, "-B", str(QUALIFIER), "--result", config["result"]],
            "software qualifier exact entry/output",
        )
        require(
            spec["data"]
            == [{"name": "qualification", "path": config["result"], "limit_B": 65536}],
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
        == [
            "--cache",
            str(PILOT_DATA / "cache-compact-v3"),
            "--output",
            spec["data_root"],
        ]
        and spec["argv"][9:11] == ["--config", experiment["config"]["path"]]
        and spec["argv"][11] == "--input-binding",
        "fit exact trainer/cache/output/config inlet",
    )
    binding_ref = next(
        (r for r in experiment["inputs"] if r["path"] == spec["argv"][12]), None
    )
    require(binding_ref is not None, "actual fit input binding")
    binding = document(binding_ref)
    require(
        binding["selected_plan"]
        == {k: spec["approved_plan"][k] for k in ("path", "sha256")}
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
        all(
            type(eligible.get(k)) is int and eligible[k] > 0
            for k in ("train", "validation")
        ),
        "common eligible T and V must both be nonempty before trainer",
    )

    require(
        cache["schema"] == "quoridor-common-corpus-terminal-geometry-v3"
        and cache["files"] == {name: name for name in COMPACT_CACHE_WIDTHS}
        and set(cache["sha256"])
        == set(cache["file_bytes"])
        == set(COMPACT_CACHE_WIDTHS)
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
        paths |= {
            ROOT / "python/quoridor_training" / (name + ".py") for name in FIT_IMPORTS
        }
        if (
            experiment["phase"] == "fit"
            and document(experiment["config"])["experiment"]["study"]
            == "public-replay-v1"
        ):
            paths.add(ROOT / "python/quoridor_training/public_replay.py")
        if experiment["phase"] == "software-qualification":
            config = document(experiment["config"])
            paths |= {
                Path(config["definition"]["path"]),
                *(Path(r["path"]) for r in config["helper_sources"]),
            }
    if experiment["phase"] == "analysis":
        if len(spec["argv"]) > 3 and spec["argv"][2:4] == [
            str(ROOT / "scripts/dev/research-lifecycle.py"),
            "arena-analysis",
        ]:
            require(spec["argv"][1] == "-B", "pinned normal arena analysis")
        else:
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
                and spec["argv"][2]
                == str(ROOT / "python/quoridor_training/research355/stream355.py"),
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


def accepted_build(ref):
    manifest = document(ref)
    require(
        not Path(ref["path"]).with_name("INCOMPLETE").exists(), "provisional manifest"
    )
    require(
        manifest["schema"] == BUILD_SCHEMA and manifest["status"] == "PASS",
        "accepted build required",
    )
    require(
        manifest["cleanup_complete"] is True and manifest["remaining"] == [],
        "build completion required",
    )
    require(
        {r["role"] for r in manifest["checks"]} >= {"test", "lint", "build"},
        "affected test/lint/build required",
    )
    read_ref(manifest["artifact"], 32 * 1024 * 1024)
    source_metadata_check(manifest["source"])
    for tool in manifest["tools"].values():
        require(
            isinstance(tool["version"], str) and bool(tool["version"].strip()),
            "qualified tool version",
        )
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
            "ordering-qualification",
        },
        "phase",
    )
    if phase == "ordering-qualification":
        ordering_qualification_shape(experiment)
        return
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
    require(
        set(request) == {"plan", "old_prefixes", "output"}, "generation request shape"
    )
    require(request["output"] == spec["data_root"], "generation owned output binding")
    require(len(experiment["inputs"]) == 2, "generation exact two inputs")
    for field, full in zip(("plan", "old_prefixes"), experiment["inputs"], strict=True):
        require(
            request[field] == {k: full[k] for k in ("path", "sha256")},
            "generation exact plan/OPEN8 references",
        )
    require(
        experiment["inputs"][0]["sha256"] == GENERATION_PLAN, "generation fixed plan"
    )
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
        set(request)
        == {"schema", "stream", "intake_binding", "previous_cache", "output"}
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
        and binding["schedule"]
        == {k: experiment["schedule"][k] for k in ("path", "sha256")},
        "actual stream/intake/schedule pairing",
    )
    previous = document(request["previous_cache"])
    require(
        not Path(request["previous_cache"]["path"])
        .with_name("intake-incomplete.json")
        .exists()
        and previous["schema"] == "quoridor-common-corpus-terminal-geometry-v2"
        and previous["stream_intake"]["status"] == "complete"
        and previous["source_content"] == binding["stream_content"]
        and previous["schedule_sha256"] == experiment["schedule"]["sha256"]
        and previous["common_corpus"]["config"]["selected_plan"]
        == {k: spec["approved_plan"][k] for k in ("path", "sha256")},
        "original retained cache/source identity; no plan substitution",
    )
    paths = {r["path"]: r for r in experiment["inputs"]}
    expected = {
        request[k]["path"] for k in ("stream", "intake_binding", "previous_cache")
    }
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
        require(
            paths[request[key]["path"]] == request[key],
            "actual converter input FileRef",
        )
    for key in ("config", "sources", "schedule"):
        require(
            binding[key]
            == {k: paths[binding[key]["path"]][k] for k in ("path", "sha256")},
            "intake control lifetime",
        )
    require(
        paths[spec["approved_plan"]["path"]] == spec["approved_plan"],
        "current plan lifetime",
    )
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
    manifest = accepted_build(experiment["build_manifest"])
    require(manifest["artifact"] == spec["artifact"], "same actual executable")
    public_replay = (
        experiment["phase"] == "fit"
        and document(experiment["config"])["experiment"]["study"] == "public-replay-v1"
    )
    if public_replay:
        # Current source hashes precede importing the new metadata-only admission.
        for caller in caller_source_refs(spec, experiment):
            read_ref(caller, max(CONTROL_BYTES, caller["bytes"]))
        public_replay_fit_check(
            spec, experiment, manifest, approved_plan(spec, experiment)
        )
    refs = [
        experiment["config"],
        *experiment["inputs"],
        experiment["schedule"],
    ]
    if experiment.get("numerical_qualification") is not None:
        refs.append(experiment["numerical_qualification"])
    require(
        isinstance(experiment["dynamic_libraries"], list),
        "declared library array required",
    )
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
        type(experiment["planned_slots"]) is int
        and 0 <= experiment["planned_slots"] <= 4096,
        "bounded planned denominator",
    )
    approved = approved_plan(spec, experiment)
    refs.append(spec["approved_plan"])
    if experiment["phase"] == "compare" and experiment["argv"][1] in {
        "ordering-assess",
        "ordering-cheap-assess",
    }:
        numerical_check(experiment, manifest, refs=refs)
        if experiment["argv"][1] == "ordering-cheap-assess":
            require(
                document(experiment["config"])["plan"]["output"] == spec["data_root"],
                "376 owned runtime output",
            )
    if (
        experiment["phase"] in {"corpus", "fit", "software-qualification"}
        and not public_replay
    ):
        common_pilot_check(spec, experiment, manifest, approved)
    if experiment["phase"] == "compare" and experiment["argv"][1] == "decisions":
        arena_decision_plan_check(experiment, approved)
        numerical_check(experiment, manifest, refs=refs)
        require(
            document(experiment["config"])["output"] == spec["data_root"],
            "decision owned runtime output",
        )
    if experiment["phase"] == "arena":
        arena_plan_check(experiment, approved)
        numerical_check(experiment, manifest, refs=refs)
        require(
            document(experiment["config"])["output"] == spec["data_root"],
            "arena owned runtime output",
        )
    if (
        experiment["phase"] == "analysis"
        and len(spec["argv"]) > 3
        and spec["argv"][3] == "arena-analysis"
    ):
        arena_analysis_check(spec, experiment)
        numerical_check(experiment, manifest, refs=refs)
    executable = manifest["artifact"]["path"]
    if experiment["phase"] in {"analysis", "fit", "software-qualification"}:
        python = project_interpreter(experiment)
        read_ref(python, max(CONTROL_BYTES, python["bytes"]))
        executable = str(project_python())
    expected_argv = [
        a.replace("@EXPERIMENT@", spec["experiment"]["path"]).replace(
            "@EXPERIMENT_SHA256@", spec["experiment"]["sha256"]
        )
        for a in experiment["argv"]
    ]
    require(expected_argv[0] == executable, "executable argv drift")
    require(
        spec["argv"] == perf349_argv(spec, experiment, expected_argv),
        "exact experiment/profiler argv",
    )
    if spec.get("perf") is not None:
        refs.append(spec["perf"]["tool"])
    require(bool(spec["data"]), "actual durable data required")
    owned(spec["data_root"], spec["owner"])
    require(
        not Path(spec["data_root"]).exists(),
        "exclusive scientific output; duplicate run refused",
    )
    if experiment["phase"] == "arena" or (
        experiment["phase"] == "compare" and experiment["argv"][1] == "decisions"
    ):
        require(
            {
                x["name"]: x["path"]
                for x in spec["data"]
                if x["name"] in {"journal", "result", "native_manifest"}
            }
            == {
                "journal": str(Path(spec["data_root"]) / "completed.jsonl.gz"),
                "result": str(Path(spec["data_root"]) / "result.json"),
                "native_manifest": str(Path(spec["data_root"]) / "manifest.json"),
            },
            "mandatory canonical archive plus bounded native summary/manifest",
        )
    for finalizer in spec["finalizers"]:
        owned(finalizer["path"], spec["owner"])
    return (
        experiment,
        manifest,
        [*refs, experiment["build_manifest"], manifest["artifact"]],
    )


def build_check(spec):
    artifact_target = spec.get("artifact_target", "quoridor-runner")
    require(
        artifact_target in {"quoridor-runner", "terminal-cache"},
        "maintained build artifact",
    )
    if artifact_target == "terminal-cache":
        for row in spec["commands"]:
            if row["role"] == "build":
                require(
                    row["argv"].count("--bin") == 1
                    and row["argv"][row["argv"].index("--bin") + 1] == artifact_target
                    and row["argv"].count("-p") == 1
                    and row["argv"][row["argv"].index("-p") + 1] == "quoridor-data",
                    "exact maintained converter build",
                )
    builds = [row for row in spec["commands"] if row["role"] == "build"]
    require(len(builds) == 1, "one selected Cargo release command")
    argv = builds[0]["argv"]
    package = (
        "quoridor-data" if artifact_target == "terminal-cache" else "quoridor-runner"
    )
    require(
        "--release" in argv
        and argv.count("--bin") == 1
        and argv[argv.index("--bin") + 1] == artifact_target
        and argv.count("-p") == 1
        and argv[argv.index("-p") + 1] == package,
        "exact selected Cargo release target",
    )
    require(
        Path(spec["target"]).is_relative_to(Path(spec["owner"])),
        "isolated owned target",
    )
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
        handover["schema"] == "research.target-handover.v1"
        and handover["status"] == "HANDED_OVER",
        "serial target handover required",
    )
    require(
        handover["target"] == spec["target"] and handover["owned_remaining"] == [],
        "target handover identity",
    )
    require(
        handover["shared_serial_pool"] is True
        and not Path(handover["old_target"]).exists(),
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
    require(
        spec["cwd"] == source["workspace"], "Cargo cwd differs from adopted workspace"
    )
    source_check(spec["source"])
    require(
        "dependency_refs" not in spec,
        "Cargo owns dependency checks; no parallel dependency inventory",
    )
    env = spec["env"]
    cargo_home = Path(env["CARGO_HOME"])
    require(
        cargo_home.is_absolute() and cargo_home.resolve() == cargo_home,
        "frozen Cargo home",
    )
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
        env["CARGO_TARGET_DIR"] == spec["target"] and env["TMPDIR"] == spec["TMP"],
        "isolated env",
    )
    require(
        env["CARGO_NET_OFFLINE"] == "true" and env["RUSTUP_AUTO_INSTALL"] == "0",
        "offline/no install",
    )
    require(
        env["CARGO_BUILD_JOBS"] == "1" and env["CARGO_INCREMENTAL"] == "0",
        "serial bounded build",
    )
    require(
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] == "3"
        and env["CARGO_PROFILE_RELEASE_DEBUG"] == "0",
        "frozen release flags",
    )
    for key in ("RUSTC", "RUSTDOC", "CC", "CXX", "AR"):
        require(
            env[key] == spec["tools"][key]["file"]["path"], "pinned relevant tool env"
        )
    require(
        {c["role"] for c in spec["commands"]} >= {"test", "lint", "build"},
        "one affected qualification",
    )
    names = [c["name"] for c in spec["commands"]]
    require(
        len(names) == len(set(names))
        and all(n.replace("-", "").isalnum() for n in names),
        "unique safe command names",
    )
    for c in spec["commands"]:
        require(
            c["role"] in {"test", "lint", "build"}, "affected software commands only"
        )
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


def generation_evidence(experiment, values):
    """Metadata correspondence only; legal history/model qualification remains downstream."""
    build = document(experiment["build_manifest"])
    start, book, schedule, result = [json.loads(values[n]) for n in GENERATION_FILES]
    evidence = {
        "schema": "quoridor.research.generation-evidence.v1",
        "phase": "generation",
        "numerical_qualification": None,
        "models_loaded": 0,
        "search_calls": 0,
        "games_started": 0,
        "scientific_planned_slots": 512,
        "artifact": build["artifact"],
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


def arena_model_check(experiment, plan, width):
    used = set()
    for m in plan["matchups"]:
        require(
            set(m) <= {"id", "engines", "evaluator_sha256", "inference"}
            and {"id", "engines", "evaluator_sha256"} <= set(m)
            and len(m["engines"]) == len(m["evaluator_sha256"]) == width,
            "declared engine identities",
        )
        sigma = False
        for i, engine in enumerate(m["engines"]):
            kind = engine["kind"]
            require(kind in {"nnue", "distance", "mcts"}, "supported numerical backend")
            if kind == "nnue":
                model = next(
                    (
                        r
                        for r in plan["models"]
                        if r["descriptor"]["path"] == engine["model"]
                    ),
                    None,
                )
                require(
                    model is not None
                    and model["evaluator_sha256"] == m["evaluator_sha256"][i],
                    "declared model/evaluator",
                )
                used.add(model["descriptor"]["path"])
            elif kind == "distance":
                require(engine.get("model") is None, "pure distance model")
            else:
                inference = m.get("inference")
                require(
                    plan["comparison"] == "whole_wall_time"
                    and engine.get("model") is None
                    and isinstance(inference, dict)
                    and inference["backend"] == "ort"
                    and inference.get("device", 0) == 0
                    and inference.get("cuda_graph", False) is False
                    and inference["model_sha"] == m["evaluator_sha256"][i]
                    and any(
                        r["path"] == inference["model"]
                        and r["sha256"] == inference["model_sha"]
                        for r in plan["inputs"]
                    )
                    and any(
                        l["file"]["path"] == inference["library"]
                        for l in experiment["dynamic_libraries"]
                    ),
                    "closed Sigma model/library/backend correspondence",
                )
                sigma = True
        require(sigma == (m.get("inference") is not None), "unused/missing backend")
    require(len(used) == len(plan["models"]), "duplicate/unused model")


def arena_decision_plan_check(experiment, plan):
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
        and plan["phase"] == experiment["phase"] == "compare"
        and plan["comparison"] == "whole_wall_time"
        and experiment["argv"][1:]
        == [
            "decisions",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        and all(
            plan[k] == experiment[k]
            for k in (
                "rules",
                "distance_units",
                "value_perspective",
                "inputs",
                "models",
                "schedule",
                "planned_slots",
            )
        )
        and plan["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and plan["distance_units"] == "wall-distance/80"
        and plan["value_perspective"] == "side-to-move"
        and plan["book"] in plan["inputs"],
        "approved decision scientific correspondence",
    )
    families = plan["family_ids"]
    matchups = [m["id"] for m in plan["matchups"]]
    count = experiment["planned_slots"]
    require(
        families
        and all(type(f) is int and f >= 0 for f in families)
        and len(set(families)) == len(families)
        and len(families) <= 96
        and matchups
        and all(type(m) is int and m >= 0 for m in matchups)
        and len(set(matchups)) == len(matchups)
        and type(count) is int
        and 0 < count <= 288
        and count == len(families) * len(matchups),
        "decision full denominator",
    )
    schedule = document(experiment["schedule"])
    require(
        isinstance(schedule, list) and len(schedule) == count, "decision full schedule"
    )
    pairs = set()
    for i, slot in enumerate(schedule):
        require(
            set(slot)
            == {
                "slot",
                "batch",
                "matchup",
                "local_game",
                "family_id",
                "candidate_color",
            }
            and all(type(v) is int and v >= 0 for v in slot.values())
            and slot["slot"] == i
            and slot["family_id"] in families
            and slot["matchup"] in matchups
            and slot["candidate_color"] == 0,
            "decision typed parent/engine slot",
        )
        pairs.add((slot["family_id"], slot["matchup"]))
    require(len(pairs) == count, "decision unique complete parent/engine coverage")
    covered = set()
    for i, batch in enumerate(plan["batches"]):
        require(
            set(batch) == {"batch", "matchup", "config", "slots"}
            and batch["batch"] == i
            and type(batch["batch"]) is int
            and batch["matchup"] in matchups
            and isinstance(batch["slots"], list)
            and batch["slots"],
            "decision batch",
        )
        for local, global_slot in enumerate(batch["slots"]):
            require(
                type(global_slot) is int
                and 0 <= global_slot < count
                and global_slot not in covered,
                "decision batch ownership",
            )
            covered.add(global_slot)
            slot = schedule[global_slot]
            require(
                slot["batch"] == i
                and slot["matchup"] == batch["matchup"]
                and slot["local_game"] == local,
                "decision local/global correspondence",
            )
    require(
        len(covered) == count
        and type(experiment.get("batch")) is int
        and 0 <= experiment["batch"] < len(plan["batches"]),
        "decision complete coverage",
    )
    batch = plan["batches"][experiment["batch"]]
    require(experiment["config"] == batch["config"], "approved decision config")
    c = document(experiment["config"])
    a = c["arena"]
    m = next(m for m in plan["matchups"] if m["id"] == batch["matchup"])
    require(
        c["ruleset"] == "standard_2p_threefold"
        and c["games"] == len(batch["slots"])
        and all(
            type(c[k]) is int and c[k] == 1
            for k in ("workers", "active_games", "max_batch")
        )
        and c["engines"] == m["engines"]
        and c.get("inference") == m.get("inference")
        and (c.get("inference") is not None or c.get("inference_cpu_core") is None)
        and all(c.get(k) is None for k in ("cycle", "train_games", "validation_games"))
        and a["comparison"] == "whole_wall_time"
        and a["clock_policy"] == "strict_unknown"
        and a.get("decision_only") is True
        and a.get("disable_continuation_static_ordering") is True
        and a["evaluator_sha256"] == m["evaluator_sha256"]
        and type(a["tt_entries"]) is int
        and 0 < a["tt_entries"] <= 1048576
        and type(a["retained_outcome_bytes"]) is int
        and 0 < a["retained_outcome_bytes"] <= c["max_output_bytes"],
        "decision single engine/receipt/retention contract",
    )
    arena_model_check(experiment, plan, 1)
    engine = c["engines"][0]
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
        "decision finite engine limits",
    )
    require(
        type(engine["time_ms"]) is int
        and engine["time_ms"] > 0
        and type(a["return_reserve_ms"]) is int
        and 0 <= a["return_reserve_ms"] < engine["time_ms"],
        "decision clock",
    )
    book = document(plan["book"])
    require(
        book["frozen_before_candidate_results"] is True
        and len(book["openings"]) == len(families)
        and len(a["book"]["openings"]) == len(batch["slots"]),
        "decision frozen parents",
    )
    for local, global_slot in enumerate(batch["slots"]):
        index = families.index(schedule[global_slot]["family_id"])
        require(
            a["book"]["openings"][local] == book["openings"][index],
            "immutable chronological parent/full history",
        )
    return [schedule[i] for i in batch["slots"]], c


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
        == [
            "arena",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ]
        and plan["comparison"]
        in {"evaluator_fixed_depth", "evaluator_wall_time", "whole_wall_time"}
        and plan["rules"]
        == experiment["rules"]
        == "research-standard-2p-threefold-goal-first-v1"
        and plan["distance_units"] == experiment["distance_units"] == "wall-distance/80"
        and plan["value_perspective"]
        == experiment["value_perspective"]
        == "side-to-move"
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
        and not a.get("decision_only", False)
        and config.get("inference") == matchup.get("inference")
        and (
            config.get("inference") is not None
            or config.get("inference_cpu_core") is None
        )
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
        and (
            plan["comparison"] == "whole_wall_time"
            or a["search_artifact_sha256"][0] == a["search_artifact_sha256"][1]
        ),
        "arena equal runtime/backend/retention conditions",
    )
    arena_model_check(experiment, plan, 2)
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
        plan["comparison"] == "whole_wall_time"
        or all(engines[0][k] == engines[1][k] for k in ("depth", "max_nodes", "simd")),
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
    if plan["comparison"] == "whole_wall_time":
        require(
            a.get("disable_continuation_static_ordering") is True,
            "declared retained alpha ordering OFF",
        )
    book = document(plan["book"])
    require(
        book["complete"] is True and book["rules"] == plan["rules"],
        "complete bound book",
    )
    families = {f["family_id"]: f for f in book["families"]}
    require(
        len(families) == len(book["families"])
        and set(plan["family_ids"]) <= families.keys(),
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
            and all(
                ref["settings"][k] == f[k]
                for k in ("family_id", "root_key", "history_counts")
            )
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
            set(slot)
            == {
                "slot",
                "batch",
                "matchup",
                "local_game",
                "family_id",
                "candidate_color",
            }
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
    require(
        isinstance(plan["batches"], list) and bool(plan["batches"]), "declared batches"
    )
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
        require(
            type(index) is int and 0 <= index < len(config["engines"]),
            "observation engine",
        )
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
            and type(obs["accepted_ns"]) is int
            and type(obs["admission_checked_ns"]) is int
            and type(obs["returned_ns"]) is int
            and obs["accepted_ns"] >= obs["admission_checked_ns"] >= obs["returned_ns"],
            "illegal/incoherent acceptance",
        )
        a = config["arena"]
        if config["engines"][index]["kind"] == "mcts":
            counters = obs["counters"]
            receipt = counters["authority_receipt_ns"]
            require(
                type(receipt) is int
                and type(obs["deadline_ns"]) is int
                and receipt < obs["deadline_ns"]
                and counters["authority_legal"] is True
                and counters["inflight_after_drain"] == 0
                and type(counters["completed_simulations"]) is int
                and (
                    (counters["completed_simulations"] > 0)
                    or (
                        counters["completed_simulations"] == 0
                        and counters.get("selection_reason")
                        == "legal_fallback_no_completed_simulation"
                        and "completed_simulation_counters" in counters
                        and "last_completed_simulation_ns" in counters
                        and counters["completed_simulation_counters"] is None
                        and counters["last_completed_simulation_ns"] is None
                        and obs["value_stm"] is None
                    )
                )
                and counters["clock_contract"] == "authority-action-receipt-v1"
                and counters["clock_contract_sha256"]
                == "04062382f70648cdfd722e59c35be1100719169097a04749b0046ea5a19a280d"
                and obs["returned_ns"] == counters["drain_finished_ns"]
                and obs["returned_ns"] >= receipt
                and obs["completed_depth"] is None
                and obs["pv"] == [],
                "Sigma receipt/drain/completed simulation",
            )
            accepted.append(obs["action"])
            continue
        require(
            obs["pv"]
            and obs["pv"][0] == obs["action"]
            and obs["counters"]["completed_snapshot_validation_failed"] is False,
            "alpha completed PV",
        )
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
                and obs["returned_ns"] < obs["deadline_ns"]
                and obs["counters"]["authority_receipt_ns"] == obs["returned_ns"]
                and obs["counters"]["drain_finished_ns"] == obs["returned_ns"],
                "thinking authority/drain",
            )
        accepted.append(obs["action"])
    if not config["arena"].get("decision_only", False):
        opening = config["arena"]["book"]["openings"][row["game"] // 2]["prefix"]
        require(
            row["moves"][: len(opening)] == opening
            and accepted == row["moves"][len(opening) :],
            "full opening/accepted actions/durable moves",
        )


ARENA_PUBLICATION = "quoridor.arena.reference-result.v1"


def arena_reference_report(config, files, values=None, expected_build=None):
    """One maintained saved-result join for publication and analysis; no Search/model replay."""
    required = {
        "journal": "completed.jsonl.gz",
        "result": "result.json",
        "native_manifest": "manifest.json",
    }
    root = Path(config["output"])
    require(
        all(
            name in files and files[name]["path"] == str(root / filename)
            for name, filename in required.items()
        ),
        "exact canonical detail/summary/manifest paths",
    )
    if values is None:
        values = {
            name: read_ref(files[name], files[name]["bytes"]) for name in required
        }
    for name in required:
        require(
            len(values[name]) == files[name]["bytes"]
            and sha(values[name]) == files[name]["sha256"],
            "actual closed saved-file bytes",
        )

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "ambiguous duplicate JSON key")
            result[key] = value
        return result

    def strict(raw):
        def constant(value):
            raise Refused("nonfinite JSON " + value)

        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

    publication = strict(values["result"])
    require(
        set(publication)
        == {
            "schema",
            "report",
            "archive",
            "outcome_count",
            "journal_count",
            "journal_bytes",
            "journal_sha256",
            "failure_attribution",
            "archive_wall_seconds",
            "archive_allocated_bytes",
        }
        and publication["schema"] == ARENA_PUBLICATION,
        "current bounded reference publication",
    )
    require(
        type(publication["archive_wall_seconds"]) in (int, float)
        and math.isfinite(publication["archive_wall_seconds"])
        and publication["archive_wall_seconds"] >= 0
        and type(publication["archive_allocated_bytes"]) is int
        and publication["archive_allocated_bytes"] >= 0,
        "actual encoding wall/allocation metadata",
    )
    report = publication["report"]
    count = config["games"]
    cap = (
        config["arena"].get("retained_outcome_bytes")
        or config["max_plies"] * 16384 + 16384
    )
    raw_cap = count * (cap + 1)
    require(
        report["outcomes"] == []
        and report["run_id"] == config["run_id"]
        and report["planned"] == count
        and publication["outcome_count"] == count
        and type(publication["journal_count"]) is int
        and 0 <= publication["journal_count"] <= count,
        "summary contains no second detailed copy/full planned census",
    )
    content = publication["archive"]
    require(
        set(content) == {"encoding", "compressed", "raw_sha256", "raw_bytes"}
        and content["encoding"] == "gzip-single-member-v1"
        and content["compressed"] == files["journal"]
        and type(content["raw_bytes"]) is int
        and 0 < content["raw_bytes"] <= raw_cap
        and files["journal"]["bytes"] <= raw_cap + ((raw_cap + 8191) // 8192) * 5 + 64,
        "exact closed archive FileRef/logical envelope",
    )
    # stdlib counterpart of the installed maintained lossless_jsonl::Reader contract.
    decoder = zlib.decompressobj(wbits=31)
    raw = decoder.decompress(values["journal"], content["raw_bytes"] + 1)
    require(
        decoder.eof
        and not decoder.unused_data
        and not decoder.unconsumed_tail
        and len(raw) == content["raw_bytes"]
        and sha(raw) == content["raw_sha256"],
        "truncated/trailing/multiple-member/raw-content mismatch",
    )
    require(raw.endswith(b"\n"), "torn canonical outcome tail")
    lines = raw.splitlines(keepends=True)
    require(
        len(lines) == count
        and all(len(line) <= cap + 1 and line.endswith(b"\n") for line in lines),
        "bounded exact outcome records",
    )
    prefix = b"".join(lines[: publication["journal_count"]])
    require(
        len(prefix) == publication["journal_bytes"]
        and sha(prefix) == publication["journal_sha256"],
        "lossless original journal prefix identity",
    )
    attribution = publication["failure_attribution"]
    require(
        (report["stopped"] is None) == (attribution is None),
        "explicit primary attribution",
    )
    rows = []
    seen = set()
    for index, line in enumerate(lines):
        row = strict(line)
        game = row["game"]
        require(
            type(game) is int and 0 <= game < count and game not in seen,
            "duplicate/unplanned/ambiguous outcome correspondence",
        )
        seen.add(game)
        if index >= publication["journal_count"]:
            require(
                row["started"] is False and row["status"] == "unknown",
                "missing journal record cannot become played completion",
            )
        if attribution is not None and row["failure"] in {"cancelled", "not_started"}:
            row["failure"] = attribution
        rows.append(row)
    manifest = strict(values["native_manifest"])
    require(
        manifest["result"] == publication
        and manifest["binding"]["config"] == config
        and manifest["cleanup"]["archive_closed_verified"] is True
        and manifest["cleanup"]["all_workers_joined"] == report["all_workers_joined"],
        "closed native manifest/summary/config/cleanup correspondence",
    )
    for name, filename in required.items():
        if name == "native_manifest":
            continue
        require(
            manifest["artifacts"][filename]
            == {k: files[name][k] for k in ("sha256", "bytes", "mode")},
            "manifest actual archive/summary SHA-size-mode",
        )
    if expected_build is not None:
        require(
            manifest["binding"]["executable_sha256"]
            == expected_build["artifact"]["sha256"],
            "actual current image publication",
        )
    report["outcomes"] = sorted(rows, key=lambda row: row["game"])
    return report


def arena_analysis_check(spec, experiment):
    config = document(experiment["config"])
    require(
        set(config)
        == {
            "schema",
            "arena_plan",
            "decision_plan",
            "diagnostic_selection",
            "bootstrap_resamples",
            "bootstrap_seed",
            "central_interval",
            "batches",
            "decision_batches",
        },
        "exact saved-analysis config fields",
    )
    require(
        config["schema"] == "quoridor.arena-analysis.v1"
        and config["arena_plan"] == spec["approved_plan"]
        and config["bootstrap_resamples"] == 10000
        and config["bootstrap_seed"] == 37420261012
        and config["central_interval"] == "98.33333333333333%"
        and experiment["planned_slots"] == 768
        and experiment["batch"] is None,
        "fixed selected family analysis settings/authority",
    )
    require(
        experiment["argv"][1:]
        == [
            "-B",
            str(ROOT / "scripts/dev/research-lifecycle.py"),
            "arena-analysis",
            "--experiment",
            "@EXPERIMENT@",
            "--experiment-sha256",
            "@EXPERIMENT_SHA256@",
        ],
        "one maintained reference analysis entry",
    )
    plan = document(config["arena_plan"])
    require(
        plan["family_ids"] == list(range(128))
        and plan["planned_slots"] == 768
        and [m["id"] for m in plan["matchups"]] == [0, 1, 2]
        and [[e["kind"] for e in m["engines"]] for m in plan["matchups"]]
        == [["mcts", "distance"], ["mcts", "nnue"], ["distance", "nnue"]]
        and experiment["schedule"] == plan["schedule"],
        "fixed three-engine/full-family schedule",
    )
    require(
        len(config["batches"]) == len(plan["batches"])
        and {b["batch"] for b in config["batches"]} == set(range(len(plan["batches"])))
        and len(config["decision_batches"]) <= 288,
        "one census descriptor per planned batch",
    )
    if config["decision_plan"] is not None:
        dplan = document(config["decision_plan"])
        require(
            len(config["decision_batches"]) == len(dplan["batches"])
            and {b["batch"] for b in config["decision_batches"]}
            == set(range(len(dplan["batches"]))),
            "full diagnostic batch census",
        )
    else:
        require(config["decision_batches"] == [], "no unapproved diagnostic branch")
    refs = {r["path"]: r for r in experiment["inputs"]}
    require(len(refs) == len(experiment["inputs"]), "unique analysis inputs")

    def selected(ref):
        require(
            ref is None or refs.get(ref["path"]) == ref,
            "actual analysis FileRef outside lifetime inputs",
        )

    selected(config["arena_plan"])
    selected(config["decision_plan"])
    selected(config["diagnostic_selection"])
    for section in (config["batches"], config["decision_batches"]):
        for item in section:
            require(
                set(item) == {"batch", "completion"},
                "no invented per-run secondary authority",
            )
            selected(item["completion"])
            if item["completion"] is not None:
                completed = document(item["completion"])
                require(
                    completed["schema"] == COMPLETION_SCHEMA
                    and completed["kind"] == "run"
                    and not Path(item["completion"]["path"])
                    .with_name("INCOMPLETE")
                    .exists(),
                    "original sole authoritative completion required",
                )
                selected(completed["experiment"])
                selected(completed["intent"])
                producer = document(completed["experiment"])
                selected(producer["config"])
                for ref in completed["data"]["files"]:
                    selected(ref)
    require(
        {item["name"]: item["path"] for item in spec["data"]}
        == {
            "summary": str(Path(spec["data_root"]) / "summary.json"),
            "report": str(Path(spec["data_root"]) / "report.md"),
        },
        "owned bounded analysis outputs",
    )
    return config


def arena_analysis(spec, experiment):
    config = arena_analysis_check(spec, experiment)
    plan = document(config["arena_plan"])
    schedule = document(plan["schedule"])
    require(
        len(schedule) == 768 and [r["slot"] for r in schedule] == list(range(768)),
        "fixed ordered slots",
    )
    selection = document(config["diagnostic_selection"])
    require(
        len(selection["parents"]) <= 96
        and selection["selected_before_outputs"] is True,
        "frozen chronological diagnostic selection",
    )
    decision_plan = (
        document(config["decision_plan"])
        if config["decision_plan"] is not None
        else None
    )
    decisions = document(decision_plan["schedule"]) if decision_plan is not None else []
    if decision_plan is not None:
        require(
            [m["id"] for m in decision_plan["matchups"]] == [0, 1, 2]
            and [m["engines"][0]["kind"] for m in decision_plan["matchups"]]
            == ["mcts", "distance", "nnue"],
            "diagnostic engine identities/metric roles",
        )
    require(
        len(decisions) == 3 * len(selection["parents"]) and len(decisions) <= 288,
        "exact selected parent/three-proposal denominator",
    )
    result = {
        "schema": "quoridor.arena-comparison.summary.v1",
        "planned": 768,
        "bootstrap_resamples": 10000,
        "bootstrap_seed": 37420261012,
        "central_interval": "98.33333333333333%",
        "operation_provenance": [],
        "errors": [],
        "diagnostic_selection": config["diagnostic_selection"],
        "diagnostic_exclusions": selection["exclusions"],
        "diagnostic_planned": len(decisions),
        "limitations": [
            "Conditional exploratory family resampling; no IID/population/Elo coverage guarantee.",
            "Shared book/PRNG and interleaved matchups; incomplete pairs are never numerical wins or cap draws.",
            "Descriptive correlated state occupancy; diverged trajectories do not identify counterfactual superiority.",
            "Historical common-parent disagreement is not error or teacher truth; no forced-child/deeper oracle.",
            "Model improvement, default adoption, new fit/features/teacher and general strength are unproved.",
        ],
    }
    observed = {}
    decision_rows = {}
    strata = {}
    result["native_costs"] = []

    def consume(items, approved, phase, target):
        for item in sorted(items, key=lambda row: row["batch"]):
            if item["completion"] is None:
                continue
            completion = document(item["completion"])
            e = document(completion["experiment"])
            origin = document(completion["intent"])
            result["operation_provenance"].append(
                {
                    "completion": item["completion"],
                    "status": completion["status"],
                    "primary": completion["primary"],
                    "secondary_count": len(completion["secondary"]),
                    "cleanup_complete": completion["cleanup_complete"],
                    "remaining": completion["remaining"],
                    "command_wall_seconds": [
                        c.get("guardian_return", {}).get("wall_seconds")
                        if c.get("guardian_return") is not None
                        else None
                        for c in completion["checks"]
                    ],
                    "cost_scope": "original command walls only; nested/controller/admin/continuous peaks not manufactured",
                }
            )
            try:
                require(
                    origin["approved_plan"] == approved
                    and e["canonical_plan_sha256"] == approved["sha256"]
                    and origin["experiment"] == completion["experiment"]
                    and e["build_manifest"] == experiment["build_manifest"]
                    and e["phase"] == phase
                    and e["batch"] == item["batch"],
                    "original producer/current subject correspondence",
                )
                planned, c = (
                    arena_plan_check(e, document(approved))
                    if phase == "arena"
                    else arena_decision_plan_check(e, document(approved))
                )
                inventory = {r["path"]: r for r in completion["data"]["files"]}
                require(
                    len(inventory) == len(completion["data"]["files"]),
                    "unique producer file inventory",
                )
                files = {
                    name: inventory[str(Path(c["output"]) / filename)]
                    for name, filename in (
                        ("journal", "completed.jsonl.gz"),
                        ("result", "result.json"),
                        ("native_manifest", "manifest.json"),
                    )
                }
                native = arena_reference_report(
                    c, files, expected_build=document(e["build_manifest"])
                )
                pub = json.loads(read_ref(files["result"]))
                result["native_costs"].append(
                    {
                        "completion": item["completion"],
                        "native_wall_seconds": native["wall_seconds"],
                        "encoding_sync_verify_seconds": pub["archive_wall_seconds"],
                        "canonical_compressed_bytes": pub["archive"]["compressed"][
                            "bytes"
                        ],
                        "canonical_raw_bytes": pub["archive"]["raw_bytes"],
                        "canonical_allocated_bytes": pub["archive_allocated_bytes"],
                        "compression_ratio_raw_over_compressed": pub["archive"][
                            "raw_bytes"
                        ]
                        / pub["archive"]["compressed"]["bytes"],
                        "native_peak_rss_observation_bytes": native["peak_rss"],
                        "evaluator_setup_seconds": native["pump"][
                            "evaluator_initialization_seconds"
                        ],
                        "backend_setup_seconds": native["pump"][
                            "backend_initialization_seconds"
                        ],
                        "backend_cleanup_seconds": native["pump"][
                            "backend_cleanup_seconds"
                        ],
                        "thinking_seconds": sum(
                            o["thinking_seconds"] or 0
                            for row in native["outcomes"]
                            for o in row["observations"]
                        ),
                        "classification_seconds": sum(
                            o["counters"]
                            .get("position_traits", {})
                            .get("classification_seconds", 0)
                            for row in native["outcomes"]
                            for o in row["observations"]
                        ),
                        "scope": "nested source spans, not additive all-work fees; continuous working set/worker UTC STOP UNKNOWN",
                    }
                )
                for row in native["outcomes"]:
                    slot = next(
                        slot for slot in planned if slot["local_game"] == row["game"]
                    )
                    require(
                        slot["slot"] not in target
                        and row["candidate_color"] == slot["candidate_color"],
                        "unique global scheduled outcome",
                    )
                    width = 2 if phase == "arena" else 1
                    require(
                        row["family"]
                        == f"{c['run_id']}-family-{row['game'] // width:06}",
                        "native family/local parent",
                    )
                    if phase == "compare":
                        require(
                            row["winner"] is None
                            and row["moves"]
                            == c["arena"]["book"]["openings"][row["game"]]["prefix"]
                            and row["status"] in {"decision", "unknown"}
                            and len(row["observations"]) <= 1,
                            "same parent single proposal/no branch game",
                        )
                    arena_observation(c, row)
                    target[slot["slot"]] = (row, c)
            except BaseException as error:
                result["errors"].append(
                    {"completion": item["completion"], **error_fact(error)}
                )

    consume(config["batches"], config["arena_plan"], "arena", observed)
    if decision_plan is not None:
        consume(
            config["decision_batches"],
            config["decision_plan"],
            "compare",
            decision_rows,
        )
    pair_scores = {}
    tables = []
    for m in plan["matchups"]:
        counts = {
            name: 0
            for name in (
                "planned",
                "started",
                "goal_first",
                "goal_second",
                "true_draw",
                "forfeit",
                "cap",
                "late",
                "illegal",
                "error",
                "unfinished",
                "unknown",
                "missing",
            )
        }
        scores = []
        families = []
        for family in range(128):
            values = []
            for slot in (
                r
                for r in schedule
                if r["matchup"] == m["id"] and r["family_id"] == family
            ):
                counts["planned"] += 1
                row = observed.get(slot["slot"], (None, None))[0]
                if row is None:
                    counts["missing"] += 1
                    counts["unknown"] += 1
                    values.append(None)
                    continue
                counts["started"] += int(row["started"])
                status = row["status"]
                failure = row["failure"]
                if status == "draw" and row["winner"] is None:
                    counts["true_draw"] += 1
                    value = 0.5
                elif status in {"goal", "forfeit"} and row["winner"] in (0, 1):
                    value = float(row["winner"] == slot["candidate_color"])
                    counts[
                        "forfeit"
                        if status == "forfeit"
                        else "goal_first"
                        if value
                        else "goal_second"
                    ] += 1
                else:
                    value = None
                    counts["unknown"] += 1
                    counts["cap"] += int(failure == "ply_cap")
                    counts["late"] += int(failure in {"time_overrun", "deadline"})
                    counts["illegal"] += int(failure == "illegal_move")
                    counts["error"] += int(
                        failure
                        in {
                            "engine_error",
                            "initialization",
                            "output_limit",
                            "memory_limit",
                        }
                    )
                    counts["unfinished"] += int(
                        failure in {"not_started", "worker_missing", "cancelled"}
                    )
                values.append(value)
            require(len(values) == 2, "full original colour pair denominator")
            scores.extend(v for v in values if v is not None)
            families.append(None if any(v is None for v in values) else sum(values) / 2)
        require(counts["planned"] == 256, "full matchup denominator")
        pair_scores[m["id"]] = families
        tables.append(
            {
                "matchup": m["id"],
                "counts": counts,
                "complete_colour_pairs": sum(v is not None for v in families),
                "complete_pair_mean": None
                if all(v is None for v in families)
                else sum(v for v in families if v is not None)
                / sum(v is not None for v in families),
                "planned_game_missingness_bounds": [
                    sum(scores) / 256,
                    (sum(scores) + counts["unknown"]) / 256,
                ],
            }
        )
    samples = {m["id"]: [] for m in plan["matchups"]}
    empty = {key: 0 for key in samples}
    rng = random.Random(37420261012)
    for _ in range(10000):
        indices = [rng.randrange(128) for _ in range(128)]
        for key, values in pair_scores.items():
            known = [values[i] for i in indices if values[i] is not None]
            if known:
                samples[key].append(sum(known) / len(known))
            else:
                empty[key] += 1
    for table in tables:
        values = sorted(samples[table["matchup"]])
        table["empty_family_resamples"] = empty[table["matchup"]]
        table["conditional_complete_pair_interval"] = (
            None
            if len(values) != 10000
            else [
                values[(len(values) - 1) // 120],
                values[(119 * (len(values) - 1) + 119) // 120],
            ]
        )
    result["matchups"] = tables
    # Per-state rows are correlated exposures. Every cell retains game/family/colour denominators.
    for global_slot, (row, c) in observed.items():
        slot = schedule[global_slot]
        for observation in row["observations"]:
            traits = observation.get("counters", {}).get("position_traits")
            if traits is None:
                continue
            for name in (
                "stock_sum_stratum",
                "distance_difference_stratum",
                "either_distance_le_2",
                "pawn_contact",
                "legal_jump_available",
                "current_repetition_count",
                "any_recorded_repetition",
                "phase_stratum",
            ):
                key = (
                    slot["matchup"],
                    observation["engine_index"],
                    name,
                    str(traits[name]),
                )
                cell = strata.setdefault(
                    key,
                    {
                        "states": 0,
                        "games": set(),
                        "families": set(),
                        "colours": set(),
                        "winning_side_states": 0,
                        "unknown_outcome_states": 0,
                        "by_colour": {},
                    },
                )
                cell["states"] += 1
                cell["games"].add(global_slot)
                cell["families"].add(slot["family_id"])
                cell["colours"].add(observation["side"])
                cell["winning_side_states"] += int(row["winner"] == observation["side"])
                cell["unknown_outcome_states"] += int(row["status"] == "unknown")
                colour = cell["by_colour"].setdefault(
                    observation["side"],
                    {"states": 0, "games": set(), "families": set()},
                )
                colour["states"] += 1
                colour["games"].add(global_slot)
                colour["families"].add(slot["family_id"])
    result["state_strata"] = [
        {
            "matchup": key[0],
            "engine_index": key[1],
            "trait": key[2],
            "stratum": key[3],
            **{
                k: len(v) if isinstance(v, set) else v
                for k, v in cell.items()
                if k != "by_colour"
            },
            "by_colour": {
                str(side): {
                    k: len(v) if isinstance(v, set) else v for k, v in counts.items()
                }
                for side, counts in sorted(cell["by_colour"].items())
            },
        }
        for key, cell in sorted(strata.items())
    ]
    by_parent = {}
    diagnostic_counts = {
        "planned": len(decisions),
        "proposed": 0,
        "unknown": 0,
        "missing": 0,
    }
    examples = []
    for slot in decisions:
        item = decision_rows.get(slot["slot"])
        if item is None:
            diagnostic_counts["missing"] += 1
            diagnostic_counts["unknown"] += 1
            continue
        row, c = item
        observation = row["observations"][0] if row["observations"] else None
        if (
            row["status"] != "decision"
            or observation is None
            or not observation["accepted"]
        ):
            diagnostic_counts["unknown"] += 1
            continue
        diagnostic_counts["proposed"] += 1
        by_parent.setdefault(slot["family_id"], []).append((slot, observation))
    disagreements = 0
    complete = 0
    for parent, rows in sorted(by_parent.items()):
        if len(rows) != 3:
            continue
        complete += 1
        if len({obs["action"] for _, obs in rows}) > 1:
            disagreements += 1
            if len(examples) < 12:
                examples.append(
                    {
                        "parent": parent,
                        "selection": config["diagnostic_selection"],
                        "proposals": [
                            {
                                "slot": slot["slot"],
                                "engine": slot["matchup"],
                                "action": obs["action"],
                                "PV": obs["pv"],
                                "accepted_depth": obs["completed_depth"],
                                "stop": obs["stop"],
                                "searched_value_stm": obs["value_stm"]
                                if slot["matchup"] != 0
                                else None,
                                "value_role": "Sigma rootmean"
                                if slot["matchup"] == 0
                                else "alpha searched root; not NNUE static",
                                "Sigma_root_nn": obs["counters"].get("root_nn"),
                                "Sigma_rootmean": obs["counters"].get("root_mean"),
                                "Sigma_selected_child_q": obs["counters"].get(
                                    "selected_child_q"
                                ),
                                "counters": obs["counters"],
                                "NNUE_static_pretanh": None,
                                "NNUE_static_posttanh": None,
                                "NNUE_saturation": None,
                                "missing_metric_reason": "not recorded by admitted same-forward path; searched/terminal values are not NNUE static outputs",
                            }
                            for slot, obs in rows
                        ],
                    }
                )
    diagnostic_strata = {}
    for parent, rows in sorted(by_parent.items()):
        if len(rows) != 3:
            continue
        traits = rows[0][1]["counters"].get("position_traits")
        if traits is None:
            continue
        disagreement = len({obs["action"] for _, obs in rows}) > 1
        for name in (
            "stock_sum_stratum",
            "distance_difference_stratum",
            "either_distance_le_2",
            "pawn_contact",
            "legal_jump_available",
            "current_repetition_count",
            "any_recorded_repetition",
            "phase_stratum",
        ):
            key = (name, str(traits[name]))
            cell = diagnostic_strata.setdefault(key, {"parents": 0, "disagreements": 0})
            cell["parents"] += 1
            cell["disagreements"] += int(disagreement)
    result["diagnostic_strata"] = [
        {"trait": key[0], "stratum": key[1], **cell}
        for key, cell in sorted(diagnostic_strata.items())
    ]
    result["diagnostics"] = {
        **diagnostic_counts,
        "complete_three_engine_parents": complete,
        "action_disagreement_parents": disagreements,
        "linked_examples": examples,
        "NNUE_pretanh_posttanh_saturation": "UNKNOWN_NOT_RECORDED_NO_EXTRA_FORWARD",
    }
    report = [
        "Three-engine fixed comparison",
        "",
        "| Matchup | Goals first/second | True draws | UNKNOWN | Complete pairs | Conditional interval |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for table in tables:
        c = table["counts"]
        report.append(
            f"| {table['matchup']} | {c['goal_first']}/{c['goal_second']} | {c['true_draw']} | {c['unknown']} | {table['complete_colour_pairs']} | {table['conditional_complete_pair_interval']} |"
        )
    report += [
        "",
        f"Common parents with all three proposals: {complete}; action disagreements: {disagreements}.",
        "",
        *result["limitations"],
    ]
    return result, "\n".join(report) + "\n"


def arena_analysis_child(experiment_path, expected_sha):
    path = os.environ["QUORIDOR_LIFECYCLE_INTENT_PATH"]
    ref, _ = bound(path)
    require(
        ref["sha256"] == os.environ["QUORIDOR_LIFECYCLE_INTENT"], "actual parent intent"
    )
    spec = document(ref)
    require(
        os.environ["QUORIDOR_LIFECYCLE_PARENT_PID"] == str(os.getppid())
        and os.getppid() > 1,
        "actual immediate parent; no second lifetime lock",
    )
    require(
        spec["experiment"]["path"] == str(experiment_path)
        and spec["experiment"]["sha256"] == expected_sha,
        "exact analysis Experiment",
    )
    require(
        spec["argv"]
        == [
            os.fsdecode(v)
            for v in Path("/proc/self/cmdline").read_bytes().split(b"\0")
            if v
        ],
        "actual admitted child argv",
    )
    require(
        (Path(spec["output"]) / "INCOMPLETE").is_file()
        and not (Path(spec["output"]) / "manifest.json").exists(),
        "active normal parent operation",
    )
    result, report = arena_analysis(spec, document(spec["experiment"]))
    root = Path(spec["data_root"])
    root.mkdir()
    for name, raw in (
        ("summary.json", json.dumps(result, allow_nan=False, indent=2).encode()),
        ("report.md", report.encode()),
    ):
        item = next(item for item in spec["data"] if item["path"] == str(root / name))
        require(len(raw) <= item["limit_B"], "bounded full analysis output")
        with (root / name).open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    fd = os.open(root, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    print(
        json.dumps(
            {
                "planned": result["planned"],
                "diagnostic_planned": result["diagnostic_planned"],
                "scope": "saved-only conditional/descriptive analysis; no model/Search/game/default claim",
            }
        )
    )


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
    if (
        experiment["argv"][1] == "ordering-cheap-assess"
        and document(experiment["config"])["schema"] == PERF349_SCHEMA
    ):
        try:
            data["ordering_perf349"] = perf349_evidence(spec, experiment, values)
        except BaseException as error:
            data["errors"].append(
                {"stage": "349_native_profiler_evidence", **error_fact(error)}
            )
    if experiment["phase"] == "arena" or (
        experiment["phase"] == "compare" and experiment["argv"][1] == "decisions"
    ):
        failure = Path(spec["data_root"]) / "publication-failure.json"
        if failure.exists():
            try:
                ref, raw = bound(failure)
                data["files"].append(ref)
                metadata = json.loads(raw)
                require(
                    metadata["schema"] == ARENA_PUBLICATION
                    and metadata["closed_archive"] is False,
                    "typed retained publication failure",
                )
                data["publication_failure"] = metadata
                data["errors"].append(
                    {
                        "stage": "native_archive_publication",
                        "type": "NativePublicationFailure",
                        "message": metadata["report"]["stopped"],
                        "secondary": metadata["report"]["pump"].get(
                            "publication_failures", []
                        ),
                    }
                )
            except BaseException as error:
                data["errors"].append(
                    {"stage": "native_archive_failure_metadata", **error_fact(error)}
                )
        live = Path(spec["data_root"]) / "completed.jsonl"
        if live.exists():
            try:
                c = document(experiment["config"])
                cap = (
                    c["arena"].get("retained_outcome_bytes")
                    or c["max_plies"] * 16384 + 16384
                )
                ref, _ = bound(live, c["games"] * (cap + 1))
                data["files"].append(ref)
                data["errors"].append(
                    {
                        "stage": "live_journal_not_retired",
                        "type": "Refused",
                        "message": "raw/partial facts retained; canonical publication not complete",
                    }
                )
            except BaseException as error:
                data["errors"].append(
                    {"stage": "live_journal_failure", **error_fact(error)}
                )
    if (
        experiment["phase"] == "analysis"
        and len(experiment["argv"]) > 3
        and experiment["argv"][3] == "arena-analysis"
    ):
        try:
            summary = json.loads(values["summary"])
            require(
                summary["schema"] == "quoridor.arena-comparison.summary.v1"
                and summary["planned"] == 768
                and len(summary["matchups"]) == 3
                and all(t["counts"]["planned"] == 256 for t in summary["matchups"])
                and summary["diagnostic_planned"] <= 288,
                "full conditional saved-analysis census",
            )
            data["scope"] = (
                "conditional/descriptive fixed analysis; native/model/default scientific scope unchanged"
            )
        except BaseException as error:
            data["errors"].append({"stage": "arena_analysis", **error_fact(error)})
    if experiment["phase"] == "ordering-qualification":
        try:
            data["numerical_qualification"] = ordering_qualification_evidence(
                experiment, document(experiment["build_manifest"]), values
            )
        except BaseException as error:
            data["errors"].append(
                {"stage": "360_input_qualification", **error_fact(error)}
            )
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
            files = {
                item["name"]: next(
                    ref for ref in data["files"] if ref["path"] == item["path"]
                )
                for item in spec["data"]
                if item["name"] in {"journal", "result", "native_manifest"}
            }
            report = arena_reference_report(
                config, files, values, document(experiment["build_manifest"])
            )
            records = []
            for row in report["outcomes"]:
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
                    isinstance(row["observations"], list)
                    and isinstance(row["moves"], list),
                    "full scientific per-game observations required",
                )
                require(
                    row["status"] in {"goal", "forfeit", "draw", "unknown"},
                    "typed outcome",
                )
                arena_observation(config, row)
                records.append(row)
                data["observed_local_games"].append(game)
                data["missing_local_games"] = sorted(
                    set(range(local_count)) - set(data["observed_local_games"])
                )
            data["missing_local_games"] = sorted(
                set(range(local_count)) - set(data["observed_local_games"])
            )
            require(
                not data["missing_local_games"],
                "missing planned games; retained UNKNOWN denominator",
            )
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
    if experiment["phase"] == "compare" and experiment["argv"][1] == "decisions":
        try:
            planned, config = arena_decision_plan_check(
                experiment, approved_plan(spec, experiment)
            )
            data["missing_local_games"] = list(range(len(planned)))
            files = {
                item["name"]: next(
                    ref for ref in data["files"] if ref["path"] == item["path"]
                )
                for item in spec["data"]
                if item["name"] in {"journal", "result", "native_manifest"}
            }
            report = arena_reference_report(
                config, files, values, document(experiment["build_manifest"])
            )
            require(
                report["schema"] == "quoridor-decisions-v1"
                and report["planned"] == len(planned)
                and report["run_id"] == config["run_id"]
                and report["all_workers_joined"] is True
                and report["stopped"] is None
                and report["rows"] == 0
                and report["dataset"] is None
                and report["score"] is None
                and len(report["outcomes"]) == len(planned),
                "decision report/census/no game claim",
            )
            for row in report["outcomes"]:
                game = row["game"]
                require(
                    type(game) is int
                    and 0 <= game < len(planned)
                    and game not in data["observed_local_games"],
                    "decision unique local parent",
                )
                require(
                    row["family"] == f"{config['run_id']}-family-{game:06}"
                    and row["winner"] is None
                    and row["moves"]
                    == config["arena"]["book"]["openings"][game]["prefix"]
                    and row["status"] in {"decision", "unknown"}
                    and len(row["observations"]) <= 1
                    and (
                        row["status"] != "decision"
                        or len(row["observations"]) == 1
                        and row["observations"][0]["accepted"] is True
                    ),
                    "one proposal/no branch/UNKNOWN",
                )
                arena_observation(config, row)
                data["observed_local_games"].append(game)
                data["missing_local_games"] = sorted(
                    set(range(len(planned))) - set(data["observed_local_games"])
                )
            require(
                not data["missing_local_games"],
                "missing planned decisions remain UNKNOWN",
            )
            data["planned_global_slots"] = [x["slot"] for x in planned]
            data["scope"] = (
                "single common-parent decision; no game, teacher truth or strength outcome"
            )
        except BaseException as error:
            data["errors"].append({"stage": "decision_metadata", **error_fact(error)})
    if experiment["phase"] in {"corpus", "fit", "software-qualification"}:
        try:
            if experiment["phase"] == "software-qualification":
                receipt = json.loads(values["qualification"])
                require(
                    receipt["schema"]
                    == "quoridor.common-corpus-framework-qualification.v1"
                    and receipt["status"] == "PASS"
                    and receipt["tests_run"] == 3
                    and receipt["failures"] == receipt["errors"] == []
                    and receipt["actual_model_forwards"] == receipt["fit_updates"] == 0
                    and receipt["scientific_corpus_qualified"] is False,
                    "affected framework qualification failed",
                )
                data["scope"] = "software-only; no corpus or numerical PASS"
            elif (
                experiment["phase"] == "fit"
                and document(experiment["config"])["experiment"]["study"]
                == "public-replay-v1"
            ):
                state = json.loads(values["training"])
                curves = json.loads(values["curves"])
                config = document(experiment["config"])
                arm = config["experiment"]["condition"]
                planned = 1034547 if arm == "added_only" else 615397
                require(
                    state["status"] == "COMPLETE"
                    and state["step"] == 200
                    and state["arm"] == arm
                    and state["forward_rows"] == planned
                    and state["added_seen"] == (12800 if arm == "added_only" else 6400)
                    and state["public_seen"] == (0 if arm == "added_only" else 6400)
                    and state["aggregate_forward_rows"] <= 2000000
                    and [p["step"] for p in curves] == list(range(0, 201, 20))
                    and state["curves"] == curves
                    and all(
                        set(point["scopes"])
                        == {
                            "added_train",
                            "added_validation",
                            "public_train",
                            "public_validation",
                        }
                        and all(
                            value["rows"]
                            == {
                                "added_train": 217,
                                "added_validation": 76,
                                "public_train": 8192,
                                "public_validation": 8192,
                            }[name]
                            and math.isfinite(value["mse"])
                            and value["mse"] >= 0
                            and 0 <= value["sign_accuracy"] <= 1
                            and 0 <= value["saturation_fraction"] <= 1
                            for name, value in point["scopes"].items()
                        )
                        for point in curves
                    )
                    and len(state["learning_rates"]) == 200
                    and state["learning_rates"]
                    == [0.001 * min(1, i / 20) for i in range(1, 201)]
                    and state["full_opened_validation"]["initial"]["rows"] == 419150
                    and state["full_opened_validation"]["last"]["rows"] == 419150
                    and not (Path(spec["data_root"]) / "INCOMPLETE").exists(),
                    "complete preselected public replay arm/evaluation/exposure census",
                )
                data["public_replay"] = {
                    "arm": arm,
                    "forward_rows": state["forward_rows"],
                    "aggregate_forward_rows": state["aggregate_forward_rows"],
                    "scope": "outcome learning LAST200; no strength/default claim",
                }
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
                    report["search_nodes"] <= 1_000_000_000,
                    "actual returned corpus work ceiling",
                )
                cache = json.loads(values["cache_manifest"])
                require(
                    cache["stream_intake"]["status"] == "complete",
                    "atomic shared cache intake",
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
        and document(experiment["build_manifest"]).get("artifact_target")
        == "terminal-cache"
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
                and cache["family_partition_sha256"]
                == previous["family_partition_sha256"]
                and cache["common_corpus"]["common_eligible_by_split"]
                == previous["common_corpus"]["common_eligible_by_split"]
                and cache["common_corpus"]["common_eligible_rows"]
                == previous["common_corpus"]["common_eligible_rows"],
                "complete saved cache migration with original census/lineage",
            )
            require(
                cache["files"] == {n: n for n in COMPACT_CACHE_WIDTHS}
                and set(cache["sha256"])
                == set(cache["file_bytes"])
                == set(COMPACT_CACHE_WIDTHS),
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
            data["scope"] = (
                "saved-only cache conversion; no games/Search/model/numerical PASS"
            )
            data["cache_manifest"] = next(
                r
                for r in data["files"]
                if r["path"] == str(Path(spec["data_root"]) / "cache.json")
            )
        except BaseException as error:
            data["errors"].append(
                {"stage": "cache_materialization", **error_fact(error)}
            )
    if data["errors"]:
        data["status"] = "FAILED"
    return data


def generation_input_data(completion_ref):
    """Recheck original saved generation files; never promote the originating run or qualify models."""
    origin = Path(completion_ref["path"])
    require(
        origin.is_absolute()
        and origin.resolve() == origin
        and origin.name == "manifest.json",
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
    require(
        origin == Path(spec["output"]) / "manifest.json",
        "origin operation manifest identity",
    )
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
    require(
        len(completion["checks"]) == 1, "single original generation command required"
    )
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
    require(
        isinstance(experiment["dynamic_libraries"], list), "declared libraries required"
    )
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
        and not Path(experiment["build_manifest"]["path"])
        .with_name("INCOMPLETE")
        .exists()
        and build["artifact"] == spec["artifact"],
        "origin bound qualified build required",
    )
    require(
        all(
            type(x.get("limit_B")) is int and 0 < x["limit_B"] <= 4 * 1024**2
            for x in spec["data"]
        ),
        "saved generation data bound",
    )
    saved = completion["data"].get("files")
    require(
        isinstance(saved, list) and len(saved) == 4,
        "four saved generation descriptors required",
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
    require(
        sum(ref["bytes"] for ref in saved) <= 4 * 1024**2,
        "saved generation aggregate bound",
    )
    # Individual allowances need not sum to the actual aggregate payload budget.
    # Bound current reads by the saved sizes, so drift cannot consume spare allowances.
    collection_spec = {
        **spec,
        "data": [
            {**item, "limit_B": ref["bytes"]}
            for item, ref in zip(spec["data"], saved, strict=True)
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
    require(
        runtime.is_absolute() and runtime.resolve() == runtime,
        "canonical outer runtime",
    )
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
    budget = spec.get("command_timeout_seconds")
    if budget is not None:
        require(
            type(budget) is int
            and budget > 0
            and type(cfg.get("max_runtime_seconds")) in (int, float)
            and math.isfinite(cfg["max_runtime_seconds"])
            and cfg["max_runtime_seconds"] >= budget + 60,
            "admitted command budget must leave outer cleanup/publication time",
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
    launched_at = time.monotonic()
    spec = document(spec_ref)
    require(
        spec["schema"] == "quoridor.research.lifecycle-intent.v1",
        "lifecycle intent schema",
    )
    # The admitted hash excludes only the admission descriptor, to avoid a self-referential digest.
    admission_view = {
        k: v for k, v in spec.items() if k not in {"admission", "intent_sha256"}
    }
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
            budget = spec.get("command_timeout_seconds")
            if budget is not None:
                # Preparation inside an entered worker also consumes its finite budget.
                # This is an executed-operation clock, never a source-preparation expiry.
                resources.deadline = launched_at + budget
            resources.check()
            try:
                if spec["kind"] == "build":
                    build_check(spec)
                    refs = [
                        spec["source"]["manifest"],
                        spec["source"]["lock"],
                        *spec["source"]["untracked_inputs"],
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
                new_json(
                    directory / "INCOMPLETE",
                    {
                        "intent": spec_ref,
                        "status": "UNKNOWN",
                        "originating_job": result["originating_job"],
                    },
                )
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
                        read_ref(
                            tool["file"], max(CONTROL_BYTES, tool["file"]["bytes"])
                        )
                        row = {
                            "name": "version-" + name.lower(),
                            "role": "version",
                            "argv": [tool["file"]["path"], *tool["version_args"]],
                        }
                        _, full = command(
                            spec,
                            row,
                            directory,
                            resources,
                            executor,
                            ledger=result["checks"],
                        )
                        require(
                            full.read_text().strip() == tool["version"],
                            "trusted tool version drift",
                        )
                    candidate = None
                    for row in spec["commands"]:
                        result["active_command"] = row
                        _, full = command(
                            spec,
                            row,
                            directory,
                            resources,
                            executor,
                            ledger=result["checks"],
                        )
                        check = result["checks"][-1]
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
                                len(matches) == 1,
                                "one selected maintained executable artifact",
                            )
                            src = owned(matches[0]["executable"], spec["target"])
                            private_copy_check(spec, src)
                            result["cargo_artifact"] = matches[0]
                            candidate = copy_artifact(src, spec["private"])
                        result["active_command"] = None
                    require(
                        candidate is not None,
                        "actual Cargo artifact required",
                    )
                    result.update(
                        artifact=candidate,
                        artifact_target=spec.get("artifact_target", "quoridor-runner"),
                        source=spec["source"],
                        source_adoption=spec["source_adoption"],
                        tools=spec["tools"],
                        env=spec["env"],
                    )
                else:
                    spec["env"] = {
                        **spec["env"],
                        "QUORIDOR_LIFECYCLE_INTENT": spec_ref["sha256"],
                        "QUORIDOR_LIFECYCLE_INTENT_PATH": spec_ref["path"],
                        "QUORIDOR_LIFECYCLE_PARENT_PID": str(os.getpid()),
                        "QUORIDOR_LIFECYCLE_PARENT_IDENTITY": json.dumps(
                            process.identity(process.process_info(os.getpid()))
                        ),
                    }
                    if spec["support"]["sha256"] == PERF349_SUPPORT:
                        Path(spec["TMP"]).mkdir()
                        created_TMP = True
                    if experiment["phase"] == "software-qualification":
                        Path(spec["data_root"]).mkdir()
                    row = {"name": "run", "argv": spec["argv"]}
                    run_error = None
                    try:
                        command(
                            spec,
                            row,
                            directory,
                            resources,
                            executor,
                            ledger=result["checks"],
                        )
                    except BaseException as error:
                        run_error = error
                    result["data"] = collect_data(spec, experiment)
                    if (
                        spec["support"]["sha256"] == PERF349_SUPPORT
                        and result["data"].get("ordering_perf349") is not None
                    ):
                        try:
                            origin = result["data"]["ordering_perf349"][
                                "runtime_launch_origin"
                            ]
                            direct = result["checks"][-1]["guardian_return"]["child"]
                            expected = (
                                origin["profiler"]
                                if spec.get("perf") is not None
                                else origin["native"]
                            )
                            require(
                                direct == expected
                                and origin["guardian"]
                                == result["originating_job"]["child"],
                                "349 native origin joins actual guardian directchild identity",
                            )
                        except BaseException as error:
                            if run_error is None:
                                run_error = error
                            else:
                                run_error.add_note(
                                    "349 origin secondary: " + repr(error)
                                )
                    if result["data"]["status"] != "PASS":
                        error = Refused(
                            "durable data finalization incomplete: "
                            + json.dumps(result["data"]["errors"])
                        )
                        if run_error is not None:
                            run_error.add_note(
                                "data finalization secondary: " + str(error)
                            )
                        else:
                            run_error = error
                    if run_error is not None:
                        raise run_error
                for ref in refs:
                    read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
                if spec["kind"] == "build":
                    source_check(spec["source"])
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
                            active_error.add_note(
                                "TMP cleanup secondary: " + repr(cleanup_error)
                            )
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
        primary.add_note(
            "lifecycle partial facts: " + json.dumps(result, allow_nan=False)
        )
        raise primary
    return result


def abnormal_run_failure(directory, job_ref, *, origin_ref=None):
    """Join one stopped original run; return failure facts in memory, never a candidate file."""
    require(
        not (directory / "candidate.json").exists()
        and not (directory / "finalizing").exists()
        and not (directory / "manifest.json").exists(),
        "ambiguous or duplicate abnormal finalization",
    )
    marker_ref, _ = bound(directory / "INCOMPLETE")
    marker = document(marker_ref)
    require(marker.get("status") == "UNKNOWN", "original pending operation marker")
    intent_ref = marker["intent"]
    spec = document(intent_ref)
    owned(intent_ref["path"], spec["owner"])
    require(
        spec["schema"] == "quoridor.research.lifecycle-intent.v1"
        and spec["kind"] == "run"
        and owned(directory, spec["owner"]) == Path(spec["output"]),
        "original owned run intent",
    )
    require(
        bound(directory / "intent.json")[0]["sha256"] == intent_ref["sha256"],
        "original copied intent drift",
    )
    admitted = {
        k: v for k, v in spec.items() if k not in {"admission", "intent_sha256"}
    }
    require(
        sha(json.dumps(admitted, sort_keys=True, separators=(",", ":")).encode())
        == spec["intent_sha256"],
        "original admitted intent digest",
    )
    runtime = Path(job_ref["path"]).parent
    owned(runtime, spec["owner"])
    require(Path(job_ref["path"]).name == "result.json", "canonical original result")
    job = document(job_ref)
    config_ref, raw = bound(runtime / "config.json")
    cfg = json.loads(raw)
    state_ref, raw = bound(runtime / "state.json")
    state = json.loads(raw)
    fingerprint = sha(json.dumps(cfg, sort_keys=True).encode())
    expected = [
        sys.executable,
        "-B",
        str(ROOT / "scripts/dev/research-lifecycle.py"),
        spec["kind"],
        "--intent",
        intent_ref["path"],
        "--sha256",
        intent_ref["sha256"],
    ]
    require(
        cfg["argv"] == expected
        and cfg["cwd"] == spec["cwd"]
        and cfg["resource_contract"] == spec["support"]["path"]
        and state["config_sha256"] == fingerprint
        and state["issue"] == cfg["issue"]
        and state["thread_id"] == cfg["thread_id"]
        and state["job_id"] == job["job_id"]
        and state["phase"] == "finished"
        and state["outcome"] == job["outcome"]
        and job["outcome"] in {"failed", "timed_out", "cancelled"}
        and type(job["exit_code"]) is int
        and job["exit_code"] != 0
        and bool(state.get("started_at"))
        and bool(job.get("finished_at"))
        and job.get("direct_child_reaped") is True
        and job.get("cleanup_complete") is True
        and job.get("remaining") == []
        and job.get("cleanup_errors", []) == [],
        "closed original abnormal job/config/owner/argv/directwait join",
    )
    # The operation independently selects its owner; the offered result cannot.
    # Historical markers need an explicit SHA-bound Root integration decision.
    origin = marker.get("originating_job")
    custody_ref = None
    if origin is None:
        require(origin_ref is not None, "independent operation origin required")
        custody_path = Path(origin_ref["path"])
        require(
            custody_path.is_relative_to(ORIGIN_CUSTODY)
            and custody_path.resolve() == custody_path,
            "historical origin requires Root integration custody",
        )
        custody = document(origin_ref)
        require(
            custody["schema"] == "quoridor.research.operation-origin.v1"
            and custody["status"] == "ACCEPTED"
            and custody["operation_marker"] == marker_ref
            and custody["intent"] == intent_ref
            and custody["result"] == job_ref
            and custody["state"] == state_ref,
            "independent historical operation/result/state binding",
        )
        origin = custody["originating_job"]
        custody_ref = origin_ref
    else:
        require(origin_ref is None, "ambiguous operation origin refused")
    require(
        origin
        == {
            "runtime": str(runtime),
            "job_id": state["job_id"],
            "config": config_ref,
            "config_sha256": fingerprint,
            "supervisor": state["supervisor"],
            "child": state["child"],
        },
        "independent operation origin mismatch",
    )
    process_ref, raw = bound(directory / "run.process.json")
    persisted = json.loads(raw)
    if custody_ref is not None:
        require(
            custody["persisted_process"] == process_ref,
            "historical native receipt binding",
        )
    require(persisted["command"] == spec["argv"], "original native command identity")
    identities = [state["supervisor"], state["child"], persisted["child"]]
    for identity in identities:
        require(
            set(identity) == {"pid", "start_ticks", "boot_id"}
            and type(identity["pid"]) is int
            and identity["pid"] > 0
            and isinstance(identity["start_ticks"], str)
            and identity["start_ticks"].isdigit()
            and isinstance(identity["boot_id"], str)
            and bool(identity["boot_id"]),
            "unambiguous original process identity",
        )
    require(
        len({x["pid"] for x in identities}) == 3
        and len({x["boot_id"] for x in identities}) == 1
        and int(identities[0]["start_ticks"])
        <= int(identities[1]["start_ticks"])
        <= int(identities[2]["start_ticks"]),
        "original supervisor/lifecycle/native identity ordering",
    )
    # The supervisor may still deliver its completion notice. It is not the compute child.
    require(
        not process.alive(state["child"]) and not process.alive(persisted["child"]),
        "original lifecycle/native still active",
    )
    experiment = document(spec["experiment"])
    secondary = []
    try:
        data = collect_data(spec, experiment)
    except BaseException as error:
        secondary.append({"stage": "partial_data_collection", **error_fact(error)})
        data = {"status": "FAILED", "files": [], "errors": secondary.copy()}
    data["status"] = (
        "FAILED"  # Available bytes never imply returned publication or completion.
    )
    data["numerical_qualification"] = None
    data["journal_flush_sync_close"] = "UNKNOWN"
    data["incomplete_marker"] = None
    try:
        if (Path(spec["data_root"]) / "INCOMPLETE").exists():
            data["incomplete_marker"] = bound(Path(spec["data_root"]) / "INCOMPLETE")[0]
    except BaseException as error:
        secondary.append({"stage": "available_data_marker", **error_fact(error)})
    check = {
        "name": "run",
        "role": "run",
        "argv": spec["argv"],
        "status": "UNKNOWN",
        "guardian_return": None,
        "persisted_process_receipt": process_ref,
        "full_log": None,
        "capture_complete": False,
        "primary": None,
        "secondary": [],
    }
    try:
        check["full_log"] = bound(directory / "run.full.log", spec["limits"]["log_B"])[
            0
        ]
    except BaseException as error:
        check["secondary"].append({"stage": "available_log", **error_fact(error)})
    return {
        "schema": COMPLETION_SCHEMA,
        "kind": "run",
        "status": "CANCELLED" if job["outcome"] == "cancelled" else "FAILED",
        "intent": intent_ref,
        "experiment": spec["experiment"],
        "build_manifest": experiment["build_manifest"],
        "planned_slots": experiment["planned_slots"],
        "data": data,
        "checks": [check],
        "primary": {
            "type": "AbnormalOuterExit",
            "message": "original owner exited without candidate",
            "original_result": job,
            "result_ref": job_ref,
        },
        "secondary": secondary,
        "cleanup_complete": False,
        "process_cleanup_complete": False,
        "remaining": [],
        "owed_finalizers": spec["finalizers"],
        "originating_job": {
            "runtime": str(runtime),
            "job_id": state["job_id"],
            "config": config_ref,
            "config_sha256": fingerprint,
            "supervisor": state["supervisor"],
            "child": state["child"],
        },
        "abnormal_origin": {
            "marker": marker_ref,
            "independent_origin_custody": custody_ref,
            "state": state_ref,
            "outer_cleanup_complete": True,
            "command_cleanup": "UNKNOWN",
            "journal_flush_sync_close": "UNKNOWN",
            "native_errors": "UNKNOWN",
            "persisted_process_facts": persisted,
            "candidate_file_created": False,
        },
    }


def _prepare_completion(directory, job_ref, *, failure=None):
    """No child launch. Authoritative publish happens after every independent owed finalizer."""
    directory = Path(directory)
    require(
        directory.is_absolute() and (directory / "INCOMPLETE").is_file(),
        "new pending operation required",
    )
    with (directory / "finalizing").open("xb"):
        pass  # Restart cannot run a scientific command or independent finalizers twice.
    candidate = (
        failure
        if failure is not None
        else json.loads((directory / "candidate.json").read_bytes())
    )
    errors = []
    job = {}
    outer_joined = False
    if (
        candidate["status"] != "PENDING_FINALIZATION"
        or candidate["cleanup_complete"] is not True
    ):
        errors.append({"stage": "candidate", "facts": candidate["primary"]})
    try:
        job = document(job_ref)
        origin = candidate["originating_job"]
        runtime = Path(origin["runtime"])
        require(
            job_ref["path"] == str(runtime / "result.json"),
            "different outer result runtime",
        )
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
        errors.append(
            {"stage": "outer_job", **error_fact(error), "available_result": job}
        )
    for check in candidate["checks"]:
        for field in ("full_log", "persisted_process_receipt"):
            try:
                if field == "full_log":
                    require(
                        check.get(field) is not None,
                        "mandatory full command capture missing",
                    )
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
            require(
                check.get("guardian_return") is not None,
                "returned command facts unavailable",
            )
            settled(check["guardian_return"])
            require(
                check.get("capture_complete") is True
                and check["guardian_return"]["log_bytes_seen"]
                == check["full_log"]["bytes"],
                "full returned command capture not complete",
            )
        except BaseException as error:
            errors.append(
                {
                    "stage": "command_return",
                    "command": check["name"],
                    **error_fact(error),
                }
            )
    if candidate["kind"] == "run":
        try:
            require(
                candidate["data"]["status"] == "PASS",
                "data finalization missing/failed",
            )
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
            require(
                doc["schema"] == "quoridor.research.data-finalizer.v1",
                "data finalizer schema",
            )
            require(
                doc["status"] == "PASS" and doc["remaining"] == [],
                "owed finalizer failed/unknown",
            )
            require(
                doc["intent_sha256"] == candidate["intent"]["sha256"],
                "same finalizer intent",
            )
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
    candidate["status"] = (
        "FAILED" if candidate["primary"] or candidate["secondary"] else "PASS"
    )
    if prior_status == "CANCELLED" or job.get("outcome") == "cancelled":
        candidate["status"] = "CANCELLED"
    candidate["authoritative_finished_at"] = stamp()
    candidate["remaining"] = (
        [] if candidate["status"] == "PASS" else job.get("remaining", [])
    )
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
            spec = document(candidate["intent"])
            require(
                candidate["source"] == spec["source"], "final adopted Git/Cargo record"
            )
            require(
                candidate["tools"] == spec["tools"] and candidate["env"] == spec["env"],
                "final build tool/environment identity",
            )
            builds = [c for c in candidate["checks"] if c["role"] == "build"]
            require(len(builds) == 1, "one actual build command")
            cargo = cargo_report(read_ref(builds[0]["full_log"]))
            artifacts = [
                a
                for a in cargo["artifacts"]
                if a["target"]["name"] == candidate["artifact_target"]
                and a["target"]["kind"] == ["bin"]
                and a["profile"]["test"] is False
            ]
            require(
                artifacts == [candidate["cargo_artifact"]],
                "actual Cargo artifact receipt",
            )
            emitted = owned(artifacts[0]["executable"], spec["target"])
            require(
                bound(emitted, 32 * 1024 * 1024)[0]["sha256"]
                == candidate["artifact"]["sha256"],
                "Cargo/private artifact drift",
            )
            require(
                {"test", "lint", "build"}
                <= {
                    c["role"]
                    for c in candidate["checks"]
                    if c["status"] == "PASS"
                    and c["capture_complete"] is True
                    and c["guardian_return"]["exit_code"] == 0
                    and c["guardian_return"]["cleanup_complete"] is True
                },
                "actual completed software checks",
            )
        except BaseException as error:
            if candidate["status"] != "CANCELLED":
                candidate["status"] = "FAILED"
            candidate["cleanup_complete"] = False
            candidate["secondary"].append(
                {"stage": "final_artifact_source", **error_fact(error)}
            )
    finalize_numerical_claim(candidate)
    try:
        new_json(directory / "manifest.json", candidate)
        fd = os.open(directory, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException as error:
        # No recursive IO reporting: keep the originating failure and every
        # accumulated secondary available if authoritative publication fails.
        error.add_note(
            "unpublished completion facts: " + json.dumps(candidate, allow_nan=False)
        )
        raise
    return candidate


def finalize(
    directory,
    job_ref,
    *,
    origin_ref=None,
    guard=physical_and_quiet,
    lock=lease,
    resource_factory=Limits,
):
    directory = Path(directory)
    require(
        not (directory / "manifest.json").exists()
        and not (directory / "finalizing").exists(),
        "duplicate finalization refused",
    )
    candidate_path = directory / "candidate.json"
    # Missing-owner publication is admitted only after the original origin is joined,
    # under the same lifetime lock. No synthetic candidate is written.
    if candidate_path.exists():
        require(origin_ref is None, "candidate already retains its originating job")
        spec = document(json.loads(candidate_path.read_bytes())["intent"])
    else:
        spec = document(document(bound(directory / "INCOMPLETE")[0])["intent"])
    require(
        owned(directory, spec["owner"]) == Path(spec["output"]),
        "finalization operation ownership",
    )
    guard(spec)
    with lock():
        resources = resource_factory(spec)
        resources.check()
        failure = (
            None
            if candidate_path.exists()
            else abnormal_run_failure(directory, job_ref, origin_ref=origin_ref)
        )
        completion = _prepare_completion(directory, job_ref, failure=failure)
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
    p = commands.add_parser("arena-analysis")
    p.add_argument("--experiment", type=Path, required=True)
    p.add_argument("--experiment-sha256", required=True)
    p = commands.add_parser("finalize")
    p.add_argument("--operation", type=Path, required=True)
    p.add_argument("--job-result", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--origin-record", type=Path)
    p.add_argument("--origin-sha256")
    args = parser.parse_args()
    if args.command == "arena-analysis":
        arena_analysis_child(args.experiment, args.experiment_sha256)
        return 0
    if args.command == "finalize":
        ref, _ = bound(args.job_result)
        require(ref["sha256"] == args.sha256, "actual job result binding")
        require(
            bool(args.origin_record) == bool(args.origin_sha256), "origin path/SHA pair"
        )
        origin_ref = None
        if args.origin_record is not None:
            origin_ref, _ = bound(args.origin_record)
            require(
                origin_ref["sha256"] == args.origin_sha256, "independent origin binding"
            )
        result = finalize(args.operation, ref, origin_ref=origin_ref)
        return 0 if result["status"] == "PASS" else 1
    ref, _ = bound(args.intent)
    require(ref["sha256"] == args.sha256, "intent SHA")
    require(document(ref)["kind"] == args.command, "operation kind")
    execute(ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
