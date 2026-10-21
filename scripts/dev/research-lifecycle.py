"""One trusted build manifest and experiment entry, under research-job/cycle_process."""

from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
import random
from pathlib import Path
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import uuid
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "games/quoridor/python"), str(ROOT / "shared/python")]
from quoridor_runtime import cycle_process as process  # noqa: E402

LEASE = Path("/workspaces/quoridor/.artifacts/rust-migration/target/arena-software-writer.lock")
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
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "reference size/type")
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


def new_json(path, value, *, resources=None):
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    require(len(data) <= CONTROL_BYTES, "control publication cap")
    if resources is not None:
        block = os.statvfs(Path(path).parent).f_frsize
        resources.check(extra_B=((len(data) + block - 1) // block) * block)
    with Path(path).open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    if resources is not None:
        resources.check()


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
    paths = [spec["output"], *spec.get("owned_outputs", [])]
    paths += [x["path"] for x in spec["finalizers"]]
    if spec["kind"] == "build":
        paths += [spec["target"], str(Path(spec["private"]).parent), spec["TMP"]]
    else:
        paths.append(spec["data_root"])
        if spec.get("TMP"):
            paths.append(spec["TMP"])
        data_root = owned(spec["data_root"], spec["owner"])
        perf = spec.get("perf")
        raw = None
        if perf is not None:
            raw = owned(perf["output"], spec["owner"])
            require(
                raw != data_root and raw.parent == data_root.parent,
                "configured perf RAW must be a native output sibling",
            )
            require(
                sum(
                    item["name"] == "perf_RAW"
                    and item["path"] == str(raw)
                    and item["limit_B"] == perf["data_max_bytes"]
                    for item in spec["data"]
                )
                == 1,
                "one full configured perf RAW capture",
            )
            paths.append(raw)
        for item in spec["data"]:
            path = owned(item["path"], spec["owner"])
            require(
                path.is_relative_to(data_root)
                or (
                    path == raw
                    and item["name"] == "perf_RAW"
                    and item["limit_B"] == perf["data_max_bytes"]
                ),
                "declared data outside charged data root/configured perf RAW",
            )
    roots = sorted({owned(p, spec["owner"]) for p in paths}, key=lambda p: len(p.parts))
    unique = []
    for path in roots:
        if not any(path.is_relative_to(parent) for parent in unique):
            unique.append(path)
    return unique


@contextmanager
def lease(*, shared=False):
    with LEASE.open("a") as f:
        fcntl.flock(f, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        yield


def issued_family_upper(spec, support):
    """Read a declared hardware envelope without study identity or storage pricing."""
    upper = support.get("resources", {}).get("family_RAM_B")
    if upper is None:
        return 6 * 1024**3 if spec["kind"] == "build" else 2 * 1024**3
    require(type(upper) is int and upper > 0, "declared family RAM envelope")
    return upper


def resolve_arena_parallel(config):
    """Resolve configuration only; normal jobs still own entry, clocks and cleanup."""
    count = config["parallel_games"]
    pool = config["physical_cpu_pool"]
    operations = config["operation_ids"]
    require(type(count) is int and 1 <= count <= 8, "finite configured parallel games")
    require(
        isinstance(pool, list)
        and len(pool) >= count + 2
        and all(type(c) is int and c >= 0 for c in pool)
        and len(set(pool)) == len(pool),
        "explicit search CPUs and two management CPUs; physical SMT checked at entry",
    )
    require(
        isinstance(operations, list)
        and count <= len(operations) <= 32
        and all(type(n) is int and n >= 0 for n in operations)
        and len(set(operations)) == len(operations),
        "finite unique original operation order, not native family IDs",
    )
    for key in (
        "lane_family_B",
        "lane_storage_B",
        "common_family_B",
        "shared_storage_B",
    ):
        require(
            type(config[key]) is int and config[key] > 0,
            "explicit positive runtime/holding bounds",
        )
    require(
        config["lane_family_B"] > 64 * 1024**2 and config["common_family_B"] >= 64 * 1024**2,
        "controllers included in actual family bounds",
    )
    managers = pool[:2]
    return dict(
        parallel_games=count,
        management_cpu_pool=managers,
        global_controller_cpu=managers[0],
        global_controller_B=config["common_family_B"],
        shared_storage_B=config["shared_storage_B"],
        family_RAM_B=count * config["lane_family_B"] + config["common_family_B"],
        whole_B=count * config["lane_storage_B"] + config["shared_storage_B"],
        CPU=len(process.CPUPlan(managers, {"run": pool[2 : 2 + count]}).all),
        members=[
            dict(
                lane=lane,
                AI_workers=[pool[2 + lane]] * 2,
                main_cpu=managers[lane % 2],
                family_B=config["lane_family_B"],
                controller_B=64 * 1024**2,
                worker_B=config["lane_family_B"] - 64 * 1024**2,
                storage_B=config["lane_storage_B"],
                operation_ids=operations[lane::count],
            )
            for lane in range(count)
        ],
    )


def arena_cohort_cpus(cohort, *, management=False):
    """Only explicit management sharing and identical same-game AI bindings overlap."""
    require(type(management) is bool, "CPU management projection must be boolean")
    members = cohort["members"]
    require(
        isinstance(members, list)
        and 1 <= len(members) <= 8
        and [m["lane"] for m in members] == list(range(len(members))),
        "finite ordered configured cohort lanes",
    )
    pool = cohort.get("management_cpu_pool")
    if pool is None:
        # Distinct owner/main assignments remain a live normal execution mode.
        pool = [cohort["global_controller_cpu"], *[m["main_cpu"] for m in members]]
        require(len(set(pool)) == len(pool), "shared main CPUs need an explicit management pool")
    require(
        isinstance(pool, list)
        and pool
        and all(type(c) is int and c >= 0 for c in pool)
        and len(set(pool)) == len(pool)
        and cohort["global_controller_cpu"] in pool,
        "explicit unique management pool",
    )
    occupied = set(pool)
    for member in members:
        ai = member["AI_workers"]
        require(
            isinstance(ai, list)
            and len(ai) == 2
            and all(type(c) is int and c >= 0 for c in ai)
            and member["main_cpu"] in pool,
            "two actual AI owners and a declared manager",
        )
        require(
            not occupied.intersection(ai),
            "different games/search and management CPUs cannot overlap",
        )
        occupied.update(ai)
    resolved = resolve_arena_parallel(cohort["parallel"]) if "parallel" in cohort else None
    if resolved is not None:
        require(
            pool == resolved["management_cpu_pool"]
            and cohort["global_controller_cpu"] == resolved["global_controller_cpu"]
            and cohort["global_controller_B"] == resolved["global_controller_B"]
            and cohort["shared_storage_B"] == resolved["shared_storage_B"]
            and len(members) == resolved["parallel_games"]
            and all(
                all(member.get(k) == v for k, v in expected.items() if k != "operation_ids")
                for member, expected in zip(members, resolved["members"], strict=True)
            ),
            "bound normal cohort consumes the one resolved parallel config",
        )
    return list(pool) if management else sorted(occupied)


def arena_cohort(spec):
    """Configured normal sequences share only their issued immutable arena cohort."""
    if spec.get("arena_cohort") is None:
        return None
    require(
        spec["kind"] == "run" and spec.get("selection_index") is not None,
        "cohort belongs to selected normal arena RUNs",
    )
    settings = document(spec["settings"])
    require(settings.get("arena_cohort") == spec["arena_cohort"], "same cohort reference")
    cohort = document(spec["arena_cohort"])
    require(
        cohort["schema"] == "quoridor.research.arena-cohort.v1"
        and cohort["owner"] == spec["owner"]
        and cohort["support"] == spec["support"],
        "issued arena cohort owner/support",
    )
    members = cohort["members"]
    require(
        1 <= len(members) <= 8 and [m["lane"] for m in members] == list(range(len(members))),
        "configured distinct ordered cohort lanes",
    )
    lane = settings["arena_lane"]
    require(type(lane) is int and 0 <= lane < len(members), "configured arena lane")
    member = members[lane]
    require(
        spec["settings"]["path"] == member["settings_path"]
        and canonical_sha({k: v for k, v in settings.items() if k != "arena_cohort"})
        == member["settings_body_sha256"],
        "frozen lane settings body",
    )
    require(
        settings["kind"] == "sequence"
        and 0 < len(settings["runs"]) <= 32
        and settings["output"] == member["output"],
        "finite lane of at most 32 operations",
    )
    selected_run(spec, document(spec["experiment"]))
    phase = Path(member["output"]) / f"run-{spec['selection_index']:03d}"
    require(
        spec["output"] == str(phase / "operation") and spec["TMP"] == str(phase / "TMP"),
        "canonical cohort operation namespace",
    )
    experiment = document(spec["experiment"])
    config = document(experiment["config"])
    require(
        experiment["phase"] == "arena"
        and config["arena"]["comparison"] in {"whole_wall_time", "search_wall_time"}
        and config["cpu_cores"] == member["AI_workers"]
        and config["management_cpu_core"] == member["main_cpu"]
        and spec["limits"]["family_B"] == member["family_B"]
        and spec["limits"]["owned_B"] == member["storage_B"]
        and spec["limits"]["controller_B"] == 64 * 1024**2
        and spec["limits"]["worker_cpu"] == member["AI_workers"][0]
        and spec["limits"]["guardian_cpu"] == member["main_cpu"]
        and config["max_memory_bytes"] == member["family_B"] - spec["limits"]["controller_B"]
        and spec["artifact"] == cohort["artifact"],
        "actual lane engine/resource binding",
    )
    if "parallel" in cohort:
        expected = resolve_arena_parallel(cohort["parallel"])["members"][lane]
        require(
            len(settings["runs"]) == len(expected["operation_ids"])
            and experiment["batch"] == expected["operation_ids"][spec["selection_index"]],
            "same resolved operation order and actual original batch binding",
        )
    support = document(cohort["support"])
    resources = support["resources"]
    require(
        resources["CPU"] == len(arena_cohort_cpus(cohort))
        and resources["GPU"] == 0
        and resources["threads"] == 1
        and resources["controller_included"] is True
        and resources["family_RAM_B"]
        == sum(m["family_B"] for m in members) + cohort["global_controller_B"]
        and type(cohort["global_controller_B"]) is int
        and cohort["global_controller_B"] >= 64 * 1024**2
        and resources["host_reserve_B"] >= 4 * 1024**3,
        "issued aggregate configured-lane RAM and global controller envelope",
    )
    roots = []
    for m in members:
        require(
            type(m["family_B"]) is int
            and m["family_B"] > 64 * 1024**2
            and type(m["storage_B"]) is int
            and m["storage_B"] > 0
            and len(m["AI_workers"]) == 2
            and all(type(c) is int and c >= 0 for c in [*m["AI_workers"], m["main_cpu"]]),
            "positive lane bounds including controller",
        )
        roots.extend(m["roots"])
    roots.extend(cohort["shared_roots"])
    if cohort.get("authority_parent") is not None:
        parent = cohort["authority_parent"]
        require(
            set(parent) == {"runtime", "output", "intent_path", "config_path"},
            "exact authority parent fields",
        )
        require(
            all(
                any(
                    owned(value, spec["owner"]).is_relative_to(Path(root))
                    for root in cohort["shared_roots"]
                )
                for value in parent.values()
            ),
            "all parent/DB/controller metadata inside shared lifetime",
        )
    paths = [owned(p, spec["owner"]) for p in roots]
    require(
        all(
            not (a.is_relative_to(b) or b.is_relative_to(a))
            for i, a in enumerate(paths)
            for b in paths[i + 1 :]
        ),
        "disjoint lane/shared holding partitions",
    )
    require(
        sum(m["storage_B"] for m in members) + cohort["shared_storage_B"]
        <= support["storage_budget"]["whole_B"]
        and all(
            any(p.is_relative_to(Path(r)) for r in support["storage_budget"]["roots"])
            for p in paths
        ),
        "all simultaneous lane holdings inside one issued whole",
    )
    require(
        all(any(p.is_relative_to(Path(r)) for r in member["roots"]) for p in charged_roots(spec)),
        "lane writes inside its reserved partition",
    )
    require(
        any(Path(cohort["control_root"]).is_relative_to(Path(r)) for r in cohort["shared_roots"]),
        "cohort control belongs to shared holding",
    )
    for m in members:
        for value in (m["settings_path"], m["output"], m["job_runtime"]):
            path = owned(value, spec["owner"])
            require(
                any(path.is_relative_to(Path(root)) for root in m["roots"]),
                "outer/inner/config/collector/failure paths belong to the full lane lifetime",
            )
    return cohort, member


def cohort_parent_binding(cohort_ref):
    """Assign the actual admitted parent job; admission owns settings/source/resources."""
    cohort = document(cohort_ref)
    parent = cohort["authority_parent"]
    state = json.loads(bound(Path(parent["runtime"]) / "state.json")[1])
    origin = document(bound(Path(parent["output"]) / "parent-origin.json")[0])
    require(origin["cohort"] == cohort_ref, "assigned parent belongs to this cohort")
    binding = dict(
        cohort=cohort_ref,
        parent=parent,
        origin=origin["originating_job"],
        launchers=[state["launch"]["launcher"]],
    )
    require(binding["origin"]["runtime"] == parent["runtime"], "assigned parent job runtime")
    require(
        state["issue"] == cohort["issue"] and state["thread_id"] == cohort["thread_id"],
        "assigned parent job owner",
    )
    cohort_parent_check(binding)
    return binding


def cohort_parent_check(binding):
    """Local job watch only; no repeated DB, source, argv or CPU-role admission."""
    origin = binding["origin"]
    runtime = Path(binding["parent"]["runtime"])
    state = json.loads(bound(runtime / "state.json")[1])
    require(
        state["job_id"] == origin["job_id"]
        and state["config_sha256"] == origin["config_sha256"]
        and state.get("supervisor") == origin["supervisor"]
        and state.get("child") == origin["child"]
        and state["phase"] == "running",
        "assigned running parent job changed",
    )
    require(
        process.alive(origin["supervisor"]) and process.alive(origin["child"]),
        "assigned parent exact identity lost",
    )
    require(
        all(process.alive(item) for item in binding.get("launchers", [])),
        "assigned normal environment-reader launcher lost",
    )
    require(not (runtime / "cancel.json").exists(), "cohort parent cancelled")
    until = state.get("authority_valid_until_monotonic")
    require(
        type(until) in (int, float) and math.isfinite(until) and time.monotonic() < until,
        "parent authority check deadline lost",
    )
    return binding


def cohort_job_authority(config, directory=None):
    """Only registered normal jobs inherit control from their assigned live parent."""
    delegated = config["authority_parent"]
    require(set(delegated) == {"cohort", "lane"}, "exact delegated cohort/member declaration")
    cohort_ref, lane = delegated["cohort"], delegated["lane"]
    binding = cohort_parent_binding(cohort_ref)
    cohort = document(cohort_ref)
    require(type(lane) is int and 0 <= lane < len(cohort["members"]), "declared lane index")
    member = cohort["members"][lane]
    launch = document(bound(Path(cohort["control_root"]) / "launch.json")[0])
    declared = document(launch["job_configs"][lane])
    require(
        launch["cohort"] == cohort_ref
        and declared.get("authority_parent") == delegated
        and config["issue"] == declared["issue"] == cohort["issue"]
        and config["thread_id"] == declared["thread_id"] == cohort["thread_id"]
        and config["goal_issue"] == declared["goal_issue"],
        "assigned member and issue/thread roster",
    )
    own = process.identity(process.process_info(os.getpid()))
    if own == binding["origin"]["child"]:
        require(
            config == declared and (directory is None or str(directory) == member["job_runtime"]),
            "parent submits only its declared normal lane job",
        )
    else:
        runtime = Path(member["job_runtime"])
        state = json.loads(bound(runtime / "state.json")[1])
        registered = state["launch"]
        require(
            registered["owner"] == binding["origin"]["child"]
            and registered["supervisor"] == state["supervisor"]
            and registered["job_id"] == state["job_id"]
            and registered["config_sha256"] == state["config_sha256"],
            "normal submit registered this actual supervisor/job to its owner",
        )
        binding["launchers"].append(registered["launcher"])
        require(
            process.alive(registered["launcher"]), "assigned lane environment-reader launcher lost"
        )
        if own == state["supervisor"]:
            require(
                config == declared and (directory is None or Path(directory) == runtime),
                "registered supervisor executes its own declared lane",
            )
        else:
            sequence = state.get("child")
            require(state["phase"] == "running", "registered running lane sequence required")
            if config == declared:
                require(
                    own == sequence,
                    "inner operation caller is the registered running lane sequence",
                )
            if config != declared:
                # The sequence contract stays settings; the selected RUN spec is
                # the maintained --intent argument, as in sequence's child_config.
                require(
                    isinstance(config["argv"], list)
                    and len(config["argv"]) == 8
                    and config["argv"][:5]
                    == [
                        sys.executable,
                        "-B",
                        str(ROOT / "scripts/dev/research-lifecycle.py"),
                        "run",
                        "--intent",
                    ]
                    and config["argv"][6] == "--sha256",
                    "inner operation uses the canonical registered run caller",
                )
                settings_ref = bound(Path(member["settings_path"]))[0]
                intent_ref = bound(Path(config["argv"][5]))[0]
                intent = document(intent_ref)
                index = intent["selection_index"]
                require(
                    config["resource_contract"] == settings_ref["path"]
                    and intent_ref["sha256"] == config["argv"][7]
                    and intent["kind"] == "run"
                    and intent["arena_cohort"] == cohort_ref
                    and intent["settings"] == settings_ref
                    and type(index) is int
                    and 0 <= index < len(document(settings_ref)["runs"]),
                    "inner normal admission belongs to assigned selected RUN",
                )
                selected = Path(member["output"]) / f"run-{index:03d}"
                require(
                    intent_ref["path"] == str(selected / "intent.json"),
                    "inner intent is the maintained selected operation",
                )
                inner_runtime = selected / "runtime"
                inner = json.loads(bound(inner_runtime / "state.json")[1])
                require(
                    (directory is None or Path(directory) == inner_runtime)
                    and inner["supervisor"] == sequence
                    and inner["config_sha256"] == sha(json.dumps(config, sort_keys=True).encode()),
                    "assigned inner originating job",
                )
                if own != sequence:
                    # The command child is distinct from the sequence that
                    # executes its normal job. Admit only that registered child,
                    # never an arbitrary descendant or an environment claim.
                    require(
                        directory is not None
                        and Path(directory) == inner_runtime
                        and document(bound(runtime / "config.json")[0]) == declared
                        and state["config_sha256"]
                        == sha(json.dumps(declared, sort_keys=True).encode())
                        and document(bound(inner_runtime / "config.json")[0]) == config
                        and inner["issue"] == config["issue"]
                        and inner["thread_id"] == config["thread_id"]
                        and inner["phase"] == "running"
                        and inner.get("child") == own
                        and sequence is not None
                        and process.alive(sequence)
                        and process.alive(state["supervisor"])
                        and process.alive(own)
                        and process.process_info(sequence["pid"])["parent"]
                        == state["supervisor"]["pid"]
                        and process.process_info(own["pid"])["parent"] == sequence["pid"]
                        and not (runtime / "cancel.json").exists()
                        and not (inner_runtime / "cancel.json").exists(),
                        "registered inner child/config/live ancestry and uncancelled lane",
                    )
    binding["delegated_config_sha256"] = canonical_sha(config)
    binding["delegated_lane"] = lane
    return binding


def cohort_sequence(settings_ref, *, job_module=None, backend=None):
    """One finite normal parent, eight maintained sequences; no second scheduler."""
    settings = document(settings_ref)
    cohort_ref = settings["arena_cohort"]
    cohort = document(cohort_ref)
    parent = cohort["authority_parent"]
    require(
        settings["kind"] == "cohort"
        and settings["output"] == parent["output"]
        and settings_ref["path"] == parent["intent_path"],
        "actual configured parent entry",
    )
    origin = originating_job(settings_ref, settings)
    require(origin["runtime"] == parent["runtime"], "original parent runtime")
    cpu_plan = sequence_cpu_plan(settings_ref)
    apply_controller_cpu_plan(cpu_plan)
    output = owned(parent["output"], cohort["owner"])
    output.mkdir(exist_ok=False)
    new_json(output / "parent-origin.json", dict(cohort=cohort_ref, originating_job=origin))
    if job_module is None:
        loader = importlib.util.spec_from_file_location(
            "cohort_job", ROOT / "scripts/dev/research-job.py"
        )
        job_module = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(job_module)
    if backend is None:
        backend = job_module.runtime.AppBackend(ROOT)
    launch = document(bound(Path(cohort["control_root"]) / "launch.json")[0])
    stopped = False
    cancel_started = None
    supervisor_handles = []
    records, submissions = {}, []
    primary = None
    secondary = []
    cleanup_facts = []

    def failed(stage, error):
        error.add_note("cohort controller obligation: " + stage)
        secondary.append(error)
        cleanup_facts.append(dict(stage=stage, error=error_fact(error)))

    def attempt(stage, action, default=None):
        try:
            return action()
        except BaseException as error:
            failed(stage, error)
            return default

    def cancel(signum, frame):
        nonlocal stopped, cancel_started
        stopped = True
        if cancel_started is None:
            cancel_started = time.monotonic()

        def publish_parent_cancel():
            path = Path(parent["runtime"])
            if (path / "cancel.json").exists():
                return  # An explicit user/control stop must never become an internal failure.
            value = dict(requested_at=stamp(), reason="cohort controller stopped", signal=signum)
            if signum is None and primary is not None:
                value.update(
                    kind="cohort_failure",
                    job_id=origin["job_id"],
                    controller=origin["child"],
                    cohort=cohort_ref,
                    primary=error_fact(primary),
                )
            job_module.write(path, "cancel.json", value, replace=False)

        attempt("parent cancel publication", publish_parent_cancel)
        for member in cohort["members"]:
            path = Path(member["job_runtime"])
            if attempt(f"lane-{member['lane']} cancel path", path.is_dir, True):
                attempt(
                    f"lane-{member['lane']} cancel publication",
                    lambda path=path: job_module.write(
                        path, "cancel.json", dict(requested_at=stamp(), signal=signum)
                    ),
                )

    previous = {}
    futures = []
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.signal(sig, cancel)
        binding = cohort_parent_binding(cohort_ref)
        # submit only creates ordinary normal-job supervisors. All payload authority
        # and resources stay in maintained execute; no per-batch LLM/barrier exists.
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=len(cohort["members"])) as pool:
            for member, cfg_ref in zip(cohort["members"], launch["job_configs"], strict=True):
                require(not stopped, "cohort cancelled before lane submission")
                cohort_parent_check(binding)
                futures.append(
                    (
                        member,
                        pool.submit(
                            job_module.submit,
                            Path(cfg_ref["path"]),
                            Path(member["job_runtime"]),
                            ROOT,
                            backend,
                            supervisor_handles=supervisor_handles,
                        ),
                    )
                )
            for member, future in futures:
                try:
                    submissions.append(dict(lane=member["lane"], state=future.result(timeout=8)))
                except BaseException as error:
                    submissions.append(dict(lane=member["lane"], error=error_fact(error)))
                    if primary is None:
                        primary = error
                    cancel(None, None)
        new_json(output / "submission.json", dict(cohort=cohort_ref, submissions=submissions))
        while len(records) < len(submissions):
            if cancel_started is not None and time.monotonic() - cancel_started >= 30:
                break
            try:
                cohort_parent_check(binding)
            except BaseException as error:
                if primary is None:
                    primary = error
                cancel(None, None)
            for row in submissions:
                lane = row["lane"]
                if lane in records:
                    continue
                runtime = Path(cohort["members"][lane]["job_runtime"])
                result_path = runtime / "result.json"
                if result_path.exists():
                    records[lane] = dict(
                        result=bound(result_path)[0],
                        state=bound(runtime / "state.json")[0],
                    )
                    terminal = document(records[lane]["result"])
                    if terminal["outcome"] != "succeeded" or not terminal["cleanup_complete"]:
                        if primary is None:
                            primary = Refused(
                                "finite cohort stopped: declared lane failed; "
                                + json.dumps(records[lane])
                            )
                        cancel(None, None)
                elif "error" in row and not (runtime / "state.json").exists():
                    records[lane] = dict(submission_error=row["error"], native_entry="UNENTERED")
            if len(records) < len(submissions):
                time.sleep(0.2)
    except BaseException as error:
        if primary is None:
            primary = error
        else:
            error.add_note("cohort body failed after primary")
            secondary.append(error)
    finally:
        if stopped or primary is not None:
            cancel(None, None)
        # One cohort-wide budget, anchored at the FIRST cancellation (or normal
        # terminal cleanup). Delegated job grace22 + TERM2 + wait3 + remaining1
        # + log1 + scan allowance1 =30. Shared TERM2/wait3 then end by35, leaving
        # ten seconds for independent final obligations inside parent grace45.
        cleanup_base = cancel_started if cancel_started is not None else time.monotonic()
        cleanup_budget = dict(
            base_monotonic=cleanup_base,
            delegated_grace_seconds=22,
            normal_delegated_finalization_seconds=8,
            child_grace_until=cleanup_base + 30,
            term_until=cleanup_base + 32,
            directwait_until=cleanup_base + 35,
            parent_grace_until=cleanup_base + 45,
            final_obligations_reserved_seconds=10,
            phases=[],
        )
        joins = [dict(child=child, code=None, reaped=False) for child in supervisor_handles]

        def drain(until, phase):
            cleanup_budget["phases"].append(dict(phase=phase, at_monotonic=time.monotonic()))
            wait_errors = set()
            while True:
                for index, item in enumerate(joins):
                    if item["reaped"] or index in wait_errors:
                        continue
                    child = item["child"]
                    try:
                        item["code"] = child.wait(timeout=0)
                        item["reaped"] = True
                    except subprocess.TimeoutExpired:
                        pass
                    except BaseException as error:
                        failed(f"supervisor-{child.pid} {phase} directwait", error)
                        wait_errors.add(index)
                if all(item["reaped"] for item in joins) or time.monotonic() >= until:
                    break
                time.sleep(min(0.05, max(0, until - time.monotonic())))

        drain(cleanup_budget["child_grace_until"], "child-grace")
        if any(not item["reaped"] for item in joins):
            if primary is None:
                primary = Refused(
                    "finite cohort stopped: owned supervisor exceeded normal drain grace"
                )
            cleanup_budget["phases"].append(dict(phase="TERM-all", at_monotonic=time.monotonic()))
            for item in joins:
                if not item["reaped"]:
                    child = item["child"]
                    attempt(f"supervisor-{child.pid} terminate", child.terminate)
            drain(cleanup_budget["term_until"], "after-TERM")
        if any(not item["reaped"] for item in joins):
            cleanup_budget["phases"].append(dict(phase="KILL-all", at_monotonic=time.monotonic()))
            for item in joins:
                if not item["reaped"]:
                    child = item["child"]
                    attempt(f"supervisor-{child.pid} kill", child.kill)
            drain(cleanup_budget["directwait_until"], "after-KILL")
        supervisor_returns = []
        for item in joins:
            child, code, reaped = item["child"], item["code"], item["reaped"]
            handles = []
            for name in ("stdin", "stdout", "stderr"):
                stream = getattr(child, name, None)
                if stream is not None:
                    attempt(f"supervisor-{child.pid} {name} close", stream.close)
                    handles.append(dict(name=name, closed=bool(getattr(stream, "closed", False))))
            running = attempt(
                f"supervisor-{child.pid} final poll", lambda: child.poll() is None, None
            )
            supervisor_returns.append(
                dict(
                    pid=child.pid,
                    exit_code=code,
                    directwait_reaped=reaped,
                    remaining=(
                        [
                            dict(
                                pid=child.pid,
                                identity="owned Popen; live or unresolved",
                            )
                        ]
                        if running is not False
                        else []
                    ),
                    remaining_observation="UNKNOWN"
                    if running is None
                    else "LIVE"
                    if running
                    else "ABSENT",
                    handles=handles,
                    handles_closed=all(h["closed"] for h in handles),
                )
            )
        for sig, handler in previous.items():
            attempt(
                f"restore signal-{sig}",
                lambda sig=sig, handler=handler: signal.signal(sig, handler),
            )
        cleanup_budget["finished_obligations_monotonic"] = time.monotonic()
        cleanup_budget["within_parent_envelope"] = (
            time.monotonic() < cleanup_budget["parent_grace_until"]
        )
        passed = attempt(
            "terminal status assessment",
            lambda: (
                primary is None
                and not secondary
                and not stopped
                and cleanup_budget["within_parent_envelope"]
                and len(records) == len(cohort["members"])
                and all(
                    "result" in r
                    and document(r["result"])["outcome"] == "succeeded"
                    and document(r["result"])["cleanup_complete"]
                    for r in records.values()
                )
                and all(
                    r["directwait_reaped"] and not r["remaining"] and r["handles_closed"]
                    for r in supervisor_returns
                )
            ),
            False,
        )
        attempt(
            "terminal result publication",
            lambda: new_json(
                output / "result.json",
                dict(
                    at=stamp(),
                    cohort=cohort_ref,
                    originating_job=origin,
                    submissions=submissions,
                    results=records,
                    supervisor_returns=supervisor_returns,
                    stopped=stopped,
                    primary=error_fact(primary) if primary is not None else None,
                    secondary=[error_fact(e) for e in secondary],
                    cleanup_obligations=cleanup_facts,
                    cleanup_budget=cleanup_budget,
                    status="PASS" if passed else "FAILED",
                    reader_STOP=stamp(),
                ),
            ),
        )
    if secondary:
        raise BaseExceptionGroup(
            "cohort primary/cleanup failures",
            [*([primary] if primary is not None else []), *secondary],
        )
    if primary is not None:
        raise primary
    require(
        not stopped and document(bound(output / "result.json")[0])["status"] == "PASS",
        "finite cohort stopped or failed; original results retained",
    )


def arena_cohort_lifetime(spec, *, outer_runtime=None):
    """Join only declared normal submissions and their actual live trees."""
    cohort, member = arena_cohort(spec)
    parent = cohort.get("authority_parent")
    parent_runtime = parent["runtime"] if parent is not None else None
    if outer_runtime is not None:
        require(
            outer_runtime in {member["job_runtime"], parent_runtime},
            "actual configured lane or authority-parent runtime",
        )
    control = Path(cohort["control_root"])
    launch_ref = bound(control / "launch.json")[0]
    launch = document(launch_ref)
    require(
        launch["cohort"] == spec["arena_cohort"]
        and len(launch["job_configs"]) == len(cohort["members"])
        and launch["job_runtimes"] == [m["job_runtime"] for m in cohort["members"]]
        and type(launch["monotonic"]) in (int, float)
        and math.isfinite(launch["monotonic"])
        and 0 < launch["monotonic"] <= time.monotonic(),
        "actual pre-submit launch clock/configs and fixed original runtime namespaces",
    )
    all_members, common_members, inner_members, origins = {}, {}, {}, {}

    # The parent owns this whole tree. Observe it once for this accounting call:
    # a native appearing between independent lane and parent scans must not be
    # charged to common solely because its earlier lane scan did not see it.
    # This is no permission cache; local child guards still scan their own live
    # descendants, and the next cohort check takes a new process observation.
    parent_processes = None
    if parent is not None:
        state = json.loads(bound(Path(parent_runtime) / "state.json")[1])
        root = state["supervisor"]
        parent_processes = {}
        if process.alive(root):
            for item in process.members(root, []):
                info = process.process_info(item["pid"])
                if process.identity(info) == item and info["state"] != "Z":
                    parent_processes[info["pid"]] = info

    def discover(root):
        if not process.alive(root):
            return {}
        if parent_processes is None:
            return {
                (v["pid"], v["start_ticks"], v["boot_id"]): v for v in process.members(root, [])
            }
        info = parent_processes.get(root["pid"])
        if process.identity(info) != root:
            return {}
        selected = {root["pid"]}
        selected.update(
            p["pid"] for p in parent_processes.values() if p.get("group") == root["pid"]
        )
        changed = True
        while changed:
            changed = False
            for p in parent_processes.values():
                if p["pid"] not in selected and p["parent"] in selected:
                    selected.add(p["pid"])
                    changed = True
        return {
            tuple(
                parent_processes[pid][k] for k in ("pid", "start_ticks", "boot_id")
            ): process.identity(parent_processes[pid])
            for pid in selected
        }

    for m, declared in zip(cohort["members"], launch["job_configs"], strict=True):
        settings_ref = bound(m["settings_path"])[0]
        settings = document(settings_ref)
        expected = document(declared)
        require(
            settings.get("arena_cohort") == spec["arena_cohort"]
            and settings["arena_lane"] == m["lane"]
            and settings["output"] == m["output"]
            and canonical_sha({k: v for k, v in settings.items() if k != "arena_cohort"})
            == m["settings_body_sha256"]
            and expected["argv"]
            == [
                sys.executable,
                "-B",
                str(ROOT / "scripts/dev/research-lifecycle.py"),
                "sequence",
                "--intent",
                settings_ref["path"],
                "--sha256",
                settings_ref["sha256"],
            ]
            and expected["resource_contract"] == m["settings_path"]
            and expected["issue"] == cohort["issue"]
            and expected["thread_id"] == cohort["thread_id"],
            "all actual immutable settings and declared normal originating configs",
        )
        runtime = Path(m["job_runtime"])
        require(
            runtime.resolve() == runtime
            and any(runtime.is_relative_to(Path(r)) for r in m["roots"]),
            "outer runtime belongs to this lane lifetime partition",
        )
        state_path = runtime / "state.json"
        if not state_path.exists():
            continue  # A later independent submit is not a barrier or a reserved process.
        actual_ref = bound(runtime / "config.json")[0]
        actual = document(actual_ref)
        state = json.loads(bound(state_path)[1])
        require(
            actual == expected
            and state["config_sha256"] == sha(json.dumps(actual, sort_keys=True).encode())
            and state["issue"] == cohort["issue"]
            and state["thread_id"] == cohort["thread_id"],
            "declared launch joins the actual original outer job/config/runtime",
        )
        if state.get("child") is None:
            if state.get("supervisor") is not None:
                tree = discover(state["supervisor"])
                all_members.update(tree)
                common_members.update(tree)
            continue
        origin = dict(
            runtime=str(runtime),
            job_id=state["job_id"],
            config=actual_ref,
            config_sha256=state["config_sha256"],
            supervisor=state["supervisor"],
            child=state["child"],
        )
        origin_path = Path(m["output"]) / "lane-origin.json"
        if origin_path.exists():
            custody = document(bound(origin_path)[0])
            require(
                custody["settings"] == settings_ref and custody["originating_job"] == origin,
                "actual lane origin equals its declared original job_id and PID-start-boot chain",
            )
        elif m["lane"] == member["lane"] and outer_runtime is None:
            raise Refused("own original sequence custody not published")
        origins[m["lane"]] = origin
        tree = discover(origin["supervisor"])
        if process.alive(origin["child"]):
            info = process.process_info(origin["child"]["pid"])
            require(
                info["parent"] == origin["supervisor"]["pid"]
                and process.alive(origin["supervisor"]),
                "live outer sequence belongs to its exact original supervisor",
            )
            tree.update(discover(origin["child"]))
        lane_inner = {}
        for index in range(32):
            phase = Path(m["output"]) / f"run-{index:03d}"
            inner_state_path = phase / "runtime/state.json"
            if not inner_state_path.exists():
                continue
            inner_state = json.loads(bound(inner_state_path)[1])
            child = inner_state.get("child")
            if child is None or not process.alive(child):
                continue
            intent_ref = bound(phase / "intent.json")[0]
            intent = document(intent_ref)
            cfg = document(bound(phase / "runtime/config.json")[0])
            require(
                intent.get("arena_cohort") == spec["arena_cohort"]
                and intent["settings"] == settings_ref
                and intent["selection_index"] == index
                and inner_state["supervisor"] == origin["child"]
                and inner_state["config_sha256"] == sha(json.dumps(cfg, sort_keys=True).encode())
                and cfg["argv"]
                == [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts/dev/research-lifecycle.py"),
                    "run",
                    "--intent",
                    intent_ref["path"],
                    "--sha256",
                    intent_ref["sha256"],
                ]
                and cfg["resource_contract"] == m["settings_path"]
                and cfg["issue"] == cohort["issue"]
                and cfg["thread_id"] == cohort["thread_id"]
                and process.process_info(child["pid"])["parent"] == origin["child"]["pid"],
                "exact inner job roots belong to this declared original outer submission",
            )
            lane_inner.update(discover(child))
        inner_members[m["lane"]] = lane_inner
        all_members.update(tree)
        common_members.update({k: v for k, v in tree.items() if k not in lane_inner})
    if parent is not None:
        parent_cfg_ref = bound(parent["config_path"])[0]
        require(launch.get("parent_config") == parent_cfg_ref, "declared parent launch config")
        parent_cfg = document(parent_cfg_ref)
        intent_ref = bound(parent["intent_path"])[0]
        parent_intent = document(intent_ref)
        require(
            parent_intent["kind"] == "cohort"
            and parent_intent["arena_cohort"] == spec["arena_cohort"]
            and parent_cfg["argv"]
            == [
                sys.executable,
                "-B",
                str(ROOT / "scripts/dev/research-lifecycle.py"),
                "cohort",
                "--intent",
                intent_ref["path"],
                "--sha256",
                intent_ref["sha256"],
            ]
            and parent_cfg["resource_contract"] == parent["intent_path"],
            "actual parent immutable caller/input",
        )
        for declared in launch["job_configs"]:
            cfg = document(declared)
            require(
                all(cfg[k] == parent_cfg[k] for k in ("issue", "goal_issue", "thread_id")),
                "single parent checks complete issue/thread roster",
            )
        runtime = Path(parent_runtime)
        if (runtime / "state.json").exists():
            cfg = document(bound(runtime / "config.json")[0])
            state = json.loads(bound(runtime / "state.json")[1])
            require(
                cfg == parent_cfg
                and state["config_sha256"] == sha(json.dumps(cfg, sort_keys=True).encode()),
                "actual parent runtime/config ownership",
            )
            tree = discover(state["supervisor"])
            all_members.update(tree)
            native_keys = (
                set().union(*(set(m) for m in inner_members.values())) if inner_members else set()
            )
            common_members.update({k: v for k, v in tree.items() if k not in native_keys})
    if parent_processes is not None:
        # A still-owned process may lose its intermediate ancestor after the
        # observation. Never drop that observed identity merely because current
        # PPID/group reachability no longer reconnects it. Residuals conservatively
        # belong to common until the normal owner/guardian finishes cleanup.
        all_members.update(
            {
                tuple(p[k] for k in ("pid", "start_ticks", "boot_id")): process.identity(p)
                for p in parent_processes.values()
            }
        )
        inner_keys = (
            set().union(*(set(m) for m in inner_members.values())) if inner_members else set()
        )
        common_members = {k: v for k, v in all_members.items() if k not in inner_keys}

    if outer_runtime is None:
        require(member["lane"] in origins, "own actual original outer submission required")
    else:
        state = json.loads(bound(Path(outer_runtime) / "state.json")[1])
        require(
            state["supervisor"] == process.identity(process.process_info(os.getpid())),
            "resource owner is the exact declared outer supervisor",
        )
    return dict(
        launch=launch_ref,
        clock=launch["monotonic"],
        origins=origins,
        all_members=all_members,
        common_members=common_members,
        inner_members=inner_members,
    )


def arena_cohort_spec(settings_ref):
    """Project existing frozen settings for accounting only, without native entry."""
    settings = document(settings_ref)
    projected = copy.deepcopy(settings["runs"][0])
    phase = Path(settings["output"]) / "run-000"
    projected.update(
        settings=settings_ref,
        selection_index=0,
        arena_cohort=settings["arena_cohort"],
        output=str(phase / "operation"),
        TMP=str(phase / "TMP"),
    )
    return projected


class ArenaCohortResources(process.CycleResources):
    """Use the maintained RSS/host/pause checks for the exact common and total trees."""

    def __init__(self, spec, *, outer_runtime=None):
        self.spec = spec
        self.outer_runtime = outer_runtime
        self.cohort, _ = arena_cohort(spec)
        support = document(self.cohort["support"])
        self.total_B = support["resources"]["family_RAM_B"]
        self.common_B = self.cohort["global_controller_B"]
        config = dict(
            host_ram_reserve=spec["limits"]["host_reserve_B"],
            max_memory_bytes=self.total_B,
            max_output_bytes=None,
            pause_file=spec.get("pause_file"),
        )
        super().__init__(config, self.cohort["control_root"], None)
        self.common = process.CycleResources(
            {**config, "max_memory_bytes": self.common_B}, self.cohort["control_root"], None
        )
        self.check(admit=True)

    def check(self, owned=(), *, admit=False):
        facts = arena_cohort_lifetime(self.spec, outer_runtime=self.outer_runtime)
        current = process.identity(process.process_info(os.getpid()))
        key = tuple(current[k] for k in ("pid", "start_ticks", "boot_id"))
        require(key in facts["all_members"], "resource checker belongs to its exact cohort tree")

        def rss(members):
            total = 0
            for identity in members.values():
                info = process.process_info(identity["pid"])
                if process.identity(info) == identity:
                    total += info["rss"]
            return total

        if admit:
            common_live = rss(facts["common_members"])
            remaining = max(0, self.common_B - common_live)
            for member in self.cohort["members"]:
                remaining += max(
                    0, member["family_B"] - rss(facts["inner_members"].get(member["lane"], {}))
                )
            require(
                process.available_memory() >= remaining + self.reserve,
                "fresh live plus remaining aggregate RAM demand and host reserve",
            )
            # The ordinary constructor subtracts already-resident RSS from free RAM.
            # Having admitted live+remaining demand, retain the declared RSS caps;
            # the maintained check still enforces current RSS and host reserve.
            self.memory_limit = self.total_B
            self.common.memory_limit = self.common_B
        total = [v for k, v in facts["all_members"].items() if k != key]
        common = [v for k, v in facts["common_members"].items() if k != key]
        process.CycleResources.check(self, total)
        # The checker is already in total/lane accounting. Charge it to common
        # only when the same observation actually classifies it as common.
        self.common.check(common, include_self=key in facts["common_members"])
        # Canonical lifetime roots, including already retained results and all
        # controllers/collectors/FAILED/TMP, are never spent again per operation.
        for member in self.cohort["members"]:
            seen = set()
            require(
                sum(allocated(p, seen=seen) for p in member["roots"]) <= member["storage_B"],
                "full canonical lane lifetime holding partition",
            )
        seen = set()
        require(
            sum(allocated(p, seen=seen) for p in self.cohort["shared_roots"])
            <= self.cohort["shared_storage_B"],
            "full shared holding partition",
        )
        budget = document(self.cohort["support"])["storage_budget"]
        seen = set()
        require(
            sum(allocated(p, seen=seen) for p in budget["roots"]) <= budget["whole_B"],
            "same complete issued five-root whole, including structural directory overhead",
        )
        return facts


@contextmanager
def operation_lease(spec, lock):
    selected = arena_cohort(spec)
    if selected is None:
        with lock():
            yield
        return
    cohort, member = selected
    with lock(shared=True):
        control = Path(cohort["control_root"])
        require(control.is_dir() and control.resolve() == control, "existing cohort control root")
        with (control / f"lane-{member['lane']}.lock").open("a") as lane_lock:
            fcntl.flock(lane_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with (control / "entry.lock").open("a") as entry_lock:
                fcntl.flock(entry_lock, fcntl.LOCK_EX)
                resources = ArenaCohortResources(spec)
                facts = resources.check(admit=True)
                start = control / "start.json"
                if not start.exists():
                    new_json(
                        start,
                        dict(
                            cohort=spec["arena_cohort"],
                            at=stamp(),
                            launch=facts["launch"],
                            monotonic=facts["clock"],
                            actual_live_origins=facts["origins"],
                            available_B=process.available_memory(),
                            family_B=resources.total_B,
                            common_B=resources.common_B,
                            settings=spec["settings"],
                            selection_index=spec["selection_index"],
                            scope="Actual live+remaining admission, not an idle reservation",
                        ),
                    )
                require(document(bound(start)[0])["cohort"] == spec["arena_cohort"], "same cohort")
            yield


def arena_cohort_progress(spec):
    """One natural snapshot, including pre-inner refusals and retained native facts."""
    selected = arena_cohort(spec)
    if selected is None:
        return
    cohort, _ = selected
    control = Path(cohort["control_root"])
    packet_path = control / "first-progress.json"
    if packet_path.exists():
        return
    lifetime = arena_cohort_lifetime(spec)
    lanes = []
    planned_games = 0
    for member in cohort["members"]:
        output = Path(member["output"])
        settings_ref = bound(member["settings_path"])[0]
        settings = document(settings_ref)
        configs = [document(document(run["experiment"])["config"]) for run in settings["runs"]]
        require(
            all(type(config.get("games")) is int and config["games"] > 0 for config in configs),
            "configured positive-int games per operation",
        )
        planned_games += sum(config["games"] for config in configs)
        terminal = None
        if (output / "result.json").exists():
            terminal_ref = bound(output / "result.json")[0]
            terminal = document(terminal_ref)
            require(
                terminal["settings"] == settings_ref
                and terminal["originating_job"] == lifetime["origins"].get(member["lane"]),
                "terminal lane result joins its actual declared original submission",
            )
        first = output / "run-000"
        settled = (first / "operation/manifest.json").exists() and not (
            first / "operation/INCOMPLETE"
        ).exists()
        inner = first / "runtime/result.json"
        inner_failed = False
        if inner.exists():
            result = document(bound(inner)[0])
            settled |= result.get("cleanup_complete") is True
            inner_failed = result["outcome"] != "succeeded"
        outer = Path(member["job_runtime"]) / "result.json"
        outer_failure = None
        if outer.exists():
            original_state = json.loads(bound(Path(member["job_runtime"]) / "state.json")[1])
            outer_result = document(bound(outer)[0])
            require(
                original_state["job_id"] == outer_result["job_id"],
                "outer terminal result joins its original runtime/job_id",
            )
            if outer_result["outcome"] != "succeeded" and outer_result.get("cleanup_complete"):
                outer_failure = bound(outer)[0]
        failed = (
            inner_failed
            or (terminal is not None and terminal["status"] != "PASS")
            or outer_failure is not None
        )
        if not (settled or failed):
            return
        lanes.append(
            dict(
                member=member,
                settings=settings,
                configs=configs,
                terminal=terminal,
                terminal_ref=terminal_ref if terminal is not None else None,
                outer_failure=outer_failure,
                initial_failed=bool(failed),
            )
        )
    with (control / "progress.lock").open("a") as progress_lock:
        fcntl.flock(progress_lock, fcntl.LOCK_EX)
        if packet_path.exists():
            return
        counts = dict(
            planned_games=planned_games,
            terminal_planned_games=0,
            inflight_slots=0,
            unentered_slots=0,
            native_started_games_known=0,
            completed_games_known=0,
            unknown_games_known=0,
            retained_games_known=0,
            retained_count_unknown_slots=0,
            terminal_native_census_unknown_slots=0,
            complete_pairs_known=0,
        )
        evidence, pairs, initial_failures = [], [], []
        for lane in lanes:
            member = lane["member"]
            if lane["initial_failed"]:
                initial_failures.append(
                    dict(
                        lane=member["lane"],
                        terminal=lane["terminal_ref"],
                        outer_failure=lane["outer_failure"],
                    )
                )
            for index, config in enumerate(lane["configs"]):
                games = config["games"]
                phase = Path(member["output"]) / f"run-{index:03d}"
                operation = phase / "operation"
                manifest_path = operation / "manifest.json"
                inner_path = phase / "runtime/result.json"
                manifest = None
                if manifest_path.exists() and not (operation / "INCOMPLETE").exists():
                    manifest = document(bound(manifest_path)[0])
                inner_result = document(bound(inner_path)[0]) if inner_path.exists() else None
                terminal = manifest is not None or (
                    inner_result is not None and inner_result.get("cleanup_complete") is True
                )
                lane_terminal = lane["terminal"] is not None or lane["outer_failure"] is not None
                publication_path = Path(config["output"]) / "result.json"
                native_owned = operation.exists()
                if terminal and not native_owned:
                    counts["unentered_slots"] += games
                elif terminal or (lane_terminal and native_owned):
                    counts["terminal_planned_games"] += games
                    if publication_path.exists():
                        publication_ref = bound(publication_path)[0]
                        publication = document(publication_ref)
                        native = publication["report"]
                        summary = native["arena_summary"]
                        census = summary["census"]
                        require(
                            native["run_id"] == config["run_id"]
                            and native["planned"] == census["planned_games"] == games
                            and 0 <= publication["outcome_count"] <= games,
                            "actual saved local native census/config and retained outcomes",
                        )
                        counts["native_started_games_known"] += census["started_games"]
                        counts["completed_games_known"] += census["completed_games"]
                        counts["unknown_games_known"] += census["unknown_games"]
                        counts["retained_games_known"] += publication["outcome_count"]
                        counts["complete_pairs_known"] += census["complete_pairs"]
                        require(
                            len(summary["pairs"]) == census["complete_pairs"],
                            "actual complete pairs",
                        )
                        openings = config["arena"]["book"]["openings"]
                        for pair in summary["pairs"]:
                            joined = [o for o in openings if o["lineage"] == pair["lineage"]]
                            require(len(joined) == 1, "complete pair joins exact family lineage")
                            source = joined[0]["reference"]["settings"]
                            pairs.append(
                                dict(
                                    lane=member["lane"],
                                    operation=index,
                                    family_id=source["family_id"],
                                    request_id=joined[0]["id"],
                                    canonical_family=source["canonical_family"],
                                    candidate_colors=[0, 1],
                                    native_family=pair["family"],
                                    lineage=pair["lineage"],
                                    publication=publication_ref,
                                )
                            )
                        evidence.append(
                            dict(
                                lane=member["lane"],
                                operation=index,
                                publication=publication_ref,
                                manifest=bound(manifest_path)[0] if manifest is not None else None,
                                inner_result=bound(inner_path)[0]
                                if inner_result is not None
                                else None,
                            )
                        )
                    else:
                        counts["terminal_native_census_unknown_slots"] += games
                        counts["retained_count_unknown_slots"] += games
                elif lane_terminal:
                    # No operation ownership marker and no inner job means no native entry.
                    counts["unentered_slots"] += games
                elif phase.exists():
                    counts["inflight_slots"] += games
                else:
                    counts["unentered_slots"] += games
        require(
            counts["terminal_planned_games"] + counts["inflight_slots"] + counts["unentered_slots"]
            == planned_games,
            "disjoint terminal/inflight/unentered planned slot domains",
        )
        counts["scientific_outcome_UNKNOWN_slots"] = planned_games - counts["completed_games_known"]
        elapsed = time.monotonic() - lifetime["clock"]
        require(elapsed > 0, "actual common launch-to-pre-publication snapshot clock")
        pair_path = control / "first-progress-pairs.json"
        require(
            len(json.dumps(pairs).encode()) <= CONTROL_BYTES, "bounded lossless pair identity facts"
        )
        new_json(pair_path, pairs)
        evidence_path = control / "first-progress-retained.json"
        require(
            len(json.dumps(evidence).encode()) <= CONTROL_BYTES, "bounded lossless retained facts"
        )
        new_json(evidence_path, evidence)
        now = datetime.now(timezone.utc)
        packet = dict(
            cohort=spec["arena_cohort"],
            at=now.isoformat(),
            at_JST=now.astimezone(timezone(timedelta(hours=9))).isoformat(),
            counts=counts,
            overall_target=planned_games,
            launch_to_pre_publication_snapshot_seconds=elapsed,
            clock_endpoint="Snapshot before packet/body/sender publication; no publication-complete clock claimed",
            completed_games_per_second=counts["completed_games_known"] / elapsed,
            conditional_remaining_seconds=(planned_games - counts["terminal_planned_games"])
            * elapsed
            / counts["completed_games_known"]
            if counts["completed_games_known"] > 0 and not initial_failures
            else None,
            initial_lane_failures=initial_failures,
            retained_publications=bound(evidence_path)[0],
            complete_pair_identities=bound(pair_path)[0],
            UNKNOWN_scope="Future/inflight/unentered and missing terminal native facts are separate; retained unknown counts are never fabricated0",
            condition="Same observed composition/contention/holding only; no ideal3x, CI, strength, refill or replay",
            overlapping_lane_native_spans_summed=False,
        )
        require(len(json.dumps(packet).encode()) <= 65536, "small first cohort packet")
        new_json(packet_path, packet)
    body = control / "first-progress.txt"
    body.write_text(
        "First natural configured-lane snapshot: " + json.dumps(bound(packet_path)[0]) + "\n"
    )
    capture = Capture(control / "first-progress-notification.full.log", 65536)
    returned = primary = None
    secondary = []
    try:
        resources = ArenaCohortResources(spec)
        returned = process.execute(
            [
                "bash",
                str(ROOT / "scripts/dev/research-session.sh"),
                "send",
                "--thread",
                cohort["notify"]["thread_id"],
                "--issue",
                cohort["notify"]["issue"],
                "--body-file",
                str(body),
            ],
            control / "first-progress-notification.log",
            time.monotonic() + 30,
            cpu_core=cohort["global_controller_cpu"],
            resources=resources,
            cwd=spec["cwd"],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            output_sink=capture,
            no_new_privs=True,
        )
        settled(returned)
    except BaseException as error:
        primary = error
    finally:
        try:
            capture.close()
        except BaseException as error:
            secondary.append(error)
        try:
            new_json(
                control / "first-progress-notification.json",
                dict(
                    returned=returned,
                    failure=error_fact(primary) if primary is not None else None,
                    secondary=[error_fact(e) for e in secondary],
                    one_shot=True,
                    producer_ack_required=False,
                ),
            )
        except BaseException as error:
            raise BaseExceptionGroup(
                "first progress notification publication",
                [*([primary] if primary is not None else []), *secondary, error],
            )
    if (
        primary is not None
        and isinstance(primary, process.CycleStopped)
        and any(k in str(primary) for k in ("signal", "pause"))
    ):
        raise primary


def selected_arena(spec):
    """The finite settings select the range once; child intents select no authority."""
    settings = document(spec["settings"])
    selection = settings["arena"]
    template = selection["template"]
    experiment = document(spec["experiment"])
    first, last = selection["range"]
    require(
        settings["kind"] == "sequence"
        and type(first) is int
        and type(last) is int
        and 0 <= first <= experiment["batch"] <= last
        and (
            experiment["phase"] == "arena"
            or (experiment["phase"] == "compare" and experiment["argv"][1] == "decisions")
        ),
        "operation outside selected finite arena range",
    )
    for key in (
        "owner",
        "writer",
        "cwd",
        "limits",
        "support",
        "approved_plan",
        "artifact",
        "caller_sources",
    ):
        require(spec[key] == template[key], "selected arena settings drift: " + key)
    launch_fields = {
        "TMPDIR",
        "QUORIDOR_LIFECYCLE_INTENT",
        "QUORIDOR_LIFECYCLE_INTENT_PATH",
        "QUORIDOR_LIFECYCLE_PARENT_PID",
        "QUORIDOR_LIFECYCLE_PARENT_IDENTITY",
    }
    require(
        {k: v for k, v in spec["env"].items() if k not in launch_fields}
        == {k: v for k, v in template["env"].items() if k not in launch_fields},
        "selected arena environment drift",
    )
    return spec["approved_plan"]


def selected_run(spec, experiment):
    """A configured finite RUN keeps its original inputs and logical output."""
    settings = document(spec["settings"])
    index = spec["selection_index"]
    runs = settings.get("runs")
    require(
        settings["kind"] == "sequence"
        and isinstance(runs, list)
        and type(index) is int
        and 0 <= index < len(runs),
        "selected finite RUN index",
    )
    template = runs[index]
    require(
        all("lmr_recipe" not in value for value in (settings, template, spec)),
        "lmr_recipe is retired; use static typed LMR parameters",
    )
    require(
        template.get("finalizers") == [],
        "configured RUN with nonempty finalizers unsupported",
    )
    expected_experiment = document(template["experiment"])
    adaptive = "parameter_tuning" in settings
    if adaptive:
        require(settings.get("arena_cohort") is None, "serial adaptive parameter owner")
        _, state = parameter_trial(settings, index)
        config = document(expected_experiment["config"])
        operation = state["operation"]
        require(
            config["arena"]["max_total_nodes"] == operation["nodes"]
            and arena_game_ids(config) == operation["selected"],
            "selected parameter slots and nonlending cap",
        )
        for engine, parameters in zip(
            config["engines"], [state["LEFT"], state["RIGHT"]], strict=True
        ):
            engine["lmr_parameters"] = parameters
        require(document(experiment["config"]) == config, "only declared typed parameters change")
        phase = Path(settings["output"]) / f"run-{index:03d}"
        require(
            experiment["config"]["path"] == str(phase / "config.json")
            and spec["approved_plan"]["path"] == str(phase / "plan.json")
            and experiment["numerical_qualification"]["path"] == str(phase / "numerical.json"),
            "normal derived parameter metadata paths",
        )
        plan = document(template["approved_plan"])
        batch = plan["batches"][expected_experiment["batch"]]
        batch["config"] = experiment["config"]
        next(m for m in plan["matchups"] if m["id"] == batch["matchup"])["engines"] = config[
            "engines"
        ]
        require(document(spec["approved_plan"]) == plan, "only resolved parameter plan changes")
        expected_experiment["config"] = experiment["config"]
        expected_experiment["canonical_plan_sha256"] = spec["approved_plan"]["sha256"]
        prior = document(expected_experiment["numerical_qualification"])
        numerical = numerical_fields(
            expected_experiment, accepted_build(expected_experiment["build_manifest"])
        )
        for key in ["original_evidence", "correspondence_only", "scope", "new_model_or_head_calls"]:
            if key in prior:
                numerical[key] = prior[key]
        require(
            document(experiment["numerical_qualification"]) == numerical,
            "inherited numerical correspondence",
        )
        expected_experiment["numerical_qualification"] = experiment["numerical_qualification"]
    for key in (
        "owner",
        "cwd",
        "limits",
        "support",
        "artifact",
        "caller_sources",
        "approved_plan",
        "data_root",
        "data",
        "finalizers",
    ):
        if adaptive and key == "approved_plan":
            continue
        require(spec[key] == template[key], "selected RUN settings drift: " + key)
    require(experiment == expected_experiment, "selected RUN experiment drift")
    launch_fields = {
        "TMPDIR",
        "QUORIDOR_LIFECYCLE_INTENT",
        "QUORIDOR_LIFECYCLE_INTENT_PATH",
        "QUORIDOR_LIFECYCLE_PARENT_PID",
        "QUORIDOR_LIFECYCLE_PARENT_IDENTITY",
    }
    require(
        {k: v for k, v in spec["env"].items() if k not in launch_fields}
        == {k: v for k, v in template["env"].items() if k not in launch_fields},
        "selected RUN environment drift",
    )
    return spec["approved_plan"]


class SequenceResources(process.CycleResources):
    """Bound one explicitly declared serial sequence and its management tree."""

    def __init__(self, settings):
        require(
            settings["kind"] == "sequence" and settings.get("arena_cohort") is None,
            "ordinary serial sequence resources",
        )
        cfg = settings["limits"]
        require(
            type(cfg["family_B"]) is int
            and type(cfg["controller_B"]) is int
            and 64 * 1024**2 <= cfg["controller_B"] < cfg["family_B"]
            and type(cfg["host_reserve_B"]) is int
            and cfg["host_reserve_B"] >= 4 * 1024**3,
            "declared management reservation inside family",
        )
        runs = settings["runs"]
        require(isinstance(runs, list) and bool(runs), "serial sequence operations")
        self.native_paths = set()
        for spec in runs:
            require(
                spec["kind"] == "run"
                and all(
                    spec["limits"][k] == cfg[k]
                    for k in ("family_B", "controller_B", "host_reserve_B")
                )
                and cfg["family_B"] <= issued_family_upper(spec, document(spec["support"]))
                and spec["argv"][0] == spec["artifact"]["path"],
                "one issued serial family and actual native command paths",
            )
            self.native_paths.add(spec["artifact"]["path"])
        common = dict(
            host_ram_reserve=cfg["host_reserve_B"],
            max_output_bytes=None,
            pause_file=settings.get("pause_file"),
        )
        super().__init__({**common, "max_memory_bytes": cfg["family_B"]}, settings["output"], None)
        self.management = process.CycleResources(
            {**common, "max_memory_bytes": cfg["controller_B"]}, settings["output"], None
        )
        self.native = process.CycleResources(
            {**common, "max_memory_bytes": cfg["family_B"] - cfg["controller_B"]},
            settings["output"],
            None,
        )
        self.root = process.identity(process.process_info(os.getpid()))
        self.known = []
        self.check()

    def _owned_info(self, member):
        info = process.process_info(member["pid"])
        if info is None:
            try:
                Path(f"/proc/{member['pid']}").stat()
            except FileNotFoundError:
                return None  # Confirmed exit; an unreadable stat alone is not exit.
            except OSError as error:
                raise process.CycleStopped("known owned process existence unknown") from error
            raise process.CycleStopped("known owned process stat/RSS unknown")
        if process.identity(info) != process.identity(member):
            return None  # Confirmed PID reuse: never charge the replacement as this member.
        if type(info.get("rss")) is not int or info["rss"] < 0:
            raise process.CycleStopped("known owned process RSS unknown")
        return info

    def check(self, owned=()):
        require(
            process.identity(process.process_info(os.getpid())) == self.root,
            "same serial sequence resource owner",
        )
        candidates = {
            (member["pid"], member["start_ticks"], member["boot_id"]): member
            for member in [
                *self.known,
                *owned,
                *process.members(self.root, [*self.known, *owned]),
            ]
        }
        self.known = list(candidates.values())
        infos = {}
        native = set()
        for member in self.known:
            info = self._owned_info(member)
            if info is None:
                continue
            infos[info["pid"]] = info
            try:
                with Path(f"/proc/{info['pid']}/cmdline").open("rb") as stream:
                    command = os.fsdecode(stream.read(4096).split(b"\0", 1)[0])
                if command in self.native_paths:
                    native.add(info["pid"])
            except OSError:
                pass  # Unclassified live members remain management, never uncharged.
        self.known = [process.identity(info) for info in infos.values()]
        changed = True
        while changed:
            children = {pid for pid, info in infos.items() if info["parent"] in native}
            changed = not children <= native
            native.update(children)
        root = self.root["pid"]
        require(root not in native, "management supervisor is not a native worker")
        for role, guard, members in [
            ("aggregate", self, infos),
            ("management", self.management, set(infos) - native),
            ("native", self.native, native),
        ]:
            # Reuse host/pause/deadline checks without a second permissive RSS read.
            process.CycleResources.check(guard, include_self=False)
            rss = sum(infos[pid]["rss"] for pid in members)
            if rss > guard.memory_limit:
                error = process.CycleStopped("cycle memory_limit")
                error.add_note(
                    json.dumps(
                        {
                            "snapshot": "same validated sequence check; not a continuous peak",
                            "role": role,
                            "rss_B": rss,
                            "limit_B": guard.memory_limit,
                            "member_count": len(members),
                            "members": [
                                {
                                    **process.identity(infos[pid]),
                                    "rss_B": infos[pid]["rss"],
                                    "role": "native" if pid in native else "management",
                                }
                                for pid in sorted(members)[:32]
                            ],
                            "members_omitted": max(0, len(members) - 32),
                        }
                    )
                )
                raise error


class Limits(process.CycleResources):
    """Reuse guardian RSS/deadline/pause; add owned positive allocation bounds."""

    def __init__(self, spec):
        self.spec = spec
        cfg = spec["limits"]
        for name in ("family_B", "host_reserve_B", "log_B"):
            require(
                type(cfg[name]) is int and cfg[name] > 0,
                "positive priced limit: " + name,
            )
        measurement = spec["kind"] == "run" and document(spec["experiment"])["argv"][1] == "measure"
        support = document(spec["support"]) if spec.get("support") is not None else {}
        require(measurement or bool(support), "owning support for non-measurement operation")
        require(
            cfg["family_B"] <= issued_family_upper(spec, support)
            and cfg["host_reserve_B"] >= 4 * 1024**3,
            "issued family/host envelope",
        )
        # Omitted/None storage is ordinary work, not a default allowance.
        for name in ("owned_B", "free_B"):
            value = cfg.get(name)
            require(
                value is None or (type(value) is int and value > 0),
                "declared storage limit: " + name,
            )
        require(
            cfg.get("owned_B") is None or cfg["owned_B"] <= 50000000000,
            "global storage cap",
        )
        if spec.get("selection_index") is not None:
            selected_run(spec, document(spec["experiment"]))
        elif spec["kind"] == "run" and (
            document(spec["experiment"])["phase"] == "arena"
            or (
                document(spec["experiment"])["phase"] == "compare"
                and document(spec["experiment"])["argv"][1] == "decisions"
            )
        ):
            selected_arena(spec)
        elif not measurement:
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
                admission["spec_sha256"] == spec["intent_sha256"],
                "actual intent admission",
            )
            require(admission["support_sha256"] == spec["support"]["sha256"], "same support")
            require(admission["ready"] is True, "phase not admitted")
            if spec["kind"] == "run":
                require(
                    admission["approved_plan"] == spec["approved_plan"],
                    "issued approved plan",
                )
        require(
            type(cfg["controller_B"]) is int
            and 64 * 1024**2 <= cfg["controller_B"] < cfg["family_B"],
            "whole family includes declared controller reservation",
        )
        self.charged_paths = charged_roots(spec)
        self.arena_cohort = arena_cohort(spec)
        super().__init__(
            {
                "host_ram_reserve": cfg["host_reserve_B"],
                "max_memory_bytes": cfg["family_B"] - cfg["controller_B"],
                "max_output_bytes": None,  # This owner counts actual allocated shared inodes below.
                "pause_file": spec.get("pause_file"),
            },
            spec["output"],
            None,
        )

        self.cohort_resources = (
            ArenaCohortResources(spec) if self.arena_cohort is not None else None
        )

    def check(self, children=(), *, extra_B=0):
        if (
            self.arena_cohort is not None
            and self.arena_cohort[0].get("authority_parent") is not None
        ):
            if not hasattr(self, "parent_control"):
                self.parent_control = cohort_parent_binding(self.spec["arena_cohort"])
            cohort_parent_check(self.parent_control)
        super().check(children)
        if self.arena_cohort is not None:
            self.cohort_resources.check()
            cohort, _ = self.arena_cohort
            seen = set()
            require(
                sum(allocated(p, seen=seen) for p in cohort["shared_roots"])
                <= cohort["shared_storage_B"],
                "shared cohort holding partition",
            )
        budget = self.spec["limits"].get("owned_B")
        require(type(extra_B) is int and extra_B >= 0, "prospective allocation")
        if budget is not None:
            seen = set()
            require(
                sum(
                    allocated(p, seen=seen)
                    for p in (
                        self.arena_cohort[1]["roots"]
                        if self.arena_cohort is not None
                        else self.charged_paths
                    )
                )
                + extra_B
                <= budget,
                "owned allocation limit",
            )
        reserve = self.spec["limits"].get("free_B")
        if reserve is not None:
            require(
                shutil.disk_usage(self.spec["owner"]).free >= reserve + extra_B,
                "FS reserve",
            )
        if self.spec.get("perf") is not None:
            path = Path(self.spec["perf"]["output"])
            if path.exists():
                info = path.lstat()
                require(
                    stat.S_ISREG(info.st_mode)
                    and info.st_size < self.spec["perf"]["data_max_bytes"],
                    "configured perf capture cap; remaining samples/work UNKNOWN",
                )


def _build_test_cpu_cores(spec):
    """The owning BUILD handover can issue the three-core NN0 integration scope."""
    cores = spec.get("test_cpu_cores")
    require(
        spec["kind"] == "build"
        and isinstance(cores, list)
        and len(cores) == 3
        and all(type(c) is int and c >= 0 for c in cores)
        and cores == sorted(set(cores))
        and spec["limits"]["worker_cpu"] == cores[0]
        and spec["limits"]["guardian_cpu"] == cores[2]
        and document(spec["target_handover"]).get("test_cpu_cores") == cores,
        "source-bound Root handover for actual three-core model-free tests",
    )
    return cores


def _native_cpu_cores(spec):
    """Bind native measurement or serial arena to its admitted search/main roles."""
    require(spec["kind"] == "run", "native CPU allocation belongs to RUN")
    experiment = document(spec["experiment"])
    config = document(experiment["config"])
    if experiment["phase"] == "compare" and experiment["argv"][1] == "measure":
        config, _ = measurement_config(experiment)
        workers = config.get("search_cpu_cores")
        threads = config.get("search_threads")
        main = config.get("management_cpu_core")
        require(
            type(threads) is int
            and threads > 0
            and isinstance(workers, list)
            and len(workers) == threads
            and all(type(c) is int and c >= 0 for c in workers)
            and len(set(workers)) == threads
            and type(main) is int
            and main >= 0
            and main not in workers
            and spec["limits"]["worker_cpu"] == workers[0]
            and spec["limits"]["guardian_cpu"] == main
            and config["native_memory_bytes"]
            == spec["limits"]["family_B"] - spec["limits"]["controller_B"]
            and arena_cohort(spec) is None,
            "normal measurement team/management/native family equals declared RUN",
        )
        cores = sorted([*workers, main])
    else:
        require(
            experiment["phase"] == "arena"
            or (experiment["phase"] == "compare" and experiment["argv"][1] == "decisions"),
            "native CPU team belongs to measurement or serial arena/decisions",
        )
        ai = config.get("cpu_cores")
        main = config.get("management_cpu_core")
        require(
            config.get("arena", {}).get("comparison")
            in {"whole_wall_time", "evaluator_fixed_depth", "search_wall_time"}
            and all(config.get(k) == 1 for k in ("workers", "active_games", "max_batch"))
            and config.get("inference_cpu_core") is None
            and isinstance(ai, list)
            and len(ai) == 2
            and all(type(cpu) is int and cpu >= 0 for cpu in ai)
            and type(main) is int
            and main >= 0
            and main not in ai,
            "one game, fixed A/B worker cores and distinct main core",
        )
        workers = set(ai)
        maximum = 1
        for index, engine in enumerate(config["engines"]):
            threads = engine.get("search_threads", 1)
            require(
                type(threads) is int and threads > 0,
                "positive total engine search_threads",
            )
            if "search_cpu_cores" not in engine:
                require(threads == 1, "complete multiworker engine team required")
                continue
            team = engine["search_cpu_cores"]
            require(
                engine["kind"] in {"nnue", "nnue_quantized", "distance"}
                and engine.get("ordering_profile") == "control"
                and isinstance(team, list)
                and len(team) == threads
                and all(type(c) is int and c >= 0 for c in team)
                and len(set(team)) == threads
                and team[0] == ai[index]
                and main not in team
                and arena_cohort(spec) is None,
                "declared managed serial alpha team; no cohort/unused selector",
            )
            maximum = max(maximum, threads)
            workers.update(team)
        require(
            len(workers) >= config["workers"] * maximum,
            "game concurrency times total search workers",
        )
        cores = sorted([*workers, main])
        require(
            spec["limits"]["worker_cpu"] == ai[0] and spec["limits"]["guardian_cpu"] == main,
            "native AI/main RUN allocation",
        )
    require(spec.get("child_cpu_cores") == cores, "exact declared native launch CPU team")
    support = document(spec["support"])
    resources = support.get("resources", {})
    require(
        (arena_cohort(spec) is not None or resources.get("CPU") == len(cores))
        and resources.get("threads") == 1
        and resources.get("GPU") == 0
        and resources.get("controller_included") is True
        and type(resources.get("family_RAM_B")) is int
        and resources["family_RAM_B"] > 0
        and (
            arena_cohort(spec) is not None
            or resources["family_RAM_B"] == spec["limits"]["family_B"]
        ),
        "actual issued native physical-core family, not corpus/source-only authority",
    )
    return cores


def operation_cpu_plan(spec):
    """One typed operation allocation, shared by execute and terminal collection."""
    cfg = spec["limits"]
    require(spec["kind"] in {"build", "run"}, "CPU plan belongs to a normal BUILD/RUN")
    require(
        cfg["worker_cpu"] != cfg["guardian_cpu"],
        "worker and management CPU roles overlap",
    )
    cores = [cfg["worker_cpu"]]
    test = cores
    if spec["kind"] == "build" and "test_cpu_cores" in spec:
        test = _build_test_cpu_cores(spec)
    if spec["kind"] == "run":
        if document(spec["experiment"])["phase"] == "corpus":
            cores = spec["child_cpu_cores"]
            require(
                isinstance(cores, list)
                and len(cores) >= 3
                and cfg["worker_cpu"] in cores
                and cfg["guardian_cpu"] in cores,
                "declared corpus CPU scope",
            )
        else:
            cores = _native_cpu_cores(spec)
    return process.CPUPlan([cfg["guardian_cpu"]], {"run": cores, "test": test})


def native_cpu_cores(spec):
    """Public normal-factory projection of the operation plan, not a second resolver."""
    require(spec["kind"] == "run", "native CPU allocation belongs to RUN")
    return list(operation_cpu_plan(spec).commands["run"])


def sequence_cpu_plan(settings_ref):
    settings = document(settings_ref)
    if settings.get("arena_cohort") is not None:
        cohort = document(settings["arena_cohort"])
        all_cores = arena_cohort_cpus(cohort)
        managers = arena_cohort_cpus(cohort, management=True)
        if settings["kind"] == "cohort":
            commands = {
                str(m["lane"]): sorted({*m["AI_workers"], m["main_cpu"]}) for m in cohort["members"]
            }
        else:
            member = cohort["members"][settings["arena_lane"]]
            commands = {"run": sorted({*member["AI_workers"], member["main_cpu"]})}
        if cohort.get("management_cpu_pool") is None:
            commands["controller"] = [
                cohort["global_controller_cpu"]
                if settings["kind"] == "cohort"
                else member["main_cpu"]
            ]
        plan = process.CPUPlan(managers, commands)
        require(set(plan.all) <= set(all_cores), "resolved cohort role scope")
        return plan
    templates = settings.get("runs", []) or settings.get("measurements", [])
    if settings.get("arena") is not None:
        templates = [*templates, settings["arena"]["template"]]
    require(bool(templates), "finite sequence CPU plan needs operation templates")
    plans = [operation_cpu_plan(t) for t in templates]
    management = {c for p in plans for c in p.management}
    if settings.get("limits") is not None:
        management.add(settings["limits"]["guardian_cpu"])
    workers = {c for p in plans for c in set(p.all) - set(p.management)}
    require(
        not management.intersection(workers),
        "sequence manager overlaps a search/test worker",
    )
    return process.CPUPlan(sorted(management), {str(i): list(p.all) for i, p in enumerate(plans)})


def apply_controller_cpu_plan(plan):
    plan.check_host(process.available_cpus())
    owner = current_cpu_owner()
    available = owner["allocation"] if owner is not None else os.sched_getaffinity(0)
    require(
        set(plan.all) <= set(available),
        "controller CPU plan outside owning launch scope",
    )
    plan.apply()


def configured_job_cpu_plan(config):
    """The standard job resolves only its actual hashed common entry/settings."""
    argv = config["argv"]
    if (
        len(argv) in {10, 14}
        and argv[:5]
        == [
            sys.executable,
            "-B",
            str(ROOT / "scripts/dev/research-lifecycle.py"),
            "finalize",
            "--operation",
        ]
        and argv[6] == "--job-result"
        and argv[8] == "--sha256"
    ):
        directory = Path(argv[5])
        custody = document(
            bound(
                directory
                / ("candidate.json" if (directory / "candidate.json").exists() else "INCOMPLETE")
            )[0]
        )
        require(
            config["resource_contract"] == custody["intent"]["path"],
            "collector resource contract is original operation intent",
        )
        plan = operation_cpu_plan(document(custody["intent"]))
        return process.CPUPlan(list(plan.management), {"run": list(plan.management)})
    if not (
        len(argv) == 8
        and argv[:3] == [sys.executable, "-B", str(ROOT / "scripts/dev/research-lifecycle.py")]
        and argv[3] in {"sequence", "cohort", "run", "build"}
        and argv[4] == "--intent"
        and argv[6] == "--sha256"
    ):
        return None
    reference = bound(Path(argv[5]))[0]
    require(reference["sha256"] == argv[7], "job CPU plan binds actual intent hash")
    if argv[3] in {"sequence", "cohort"}:
        require(config["resource_contract"] == reference["path"], "job CPU settings owner")
        return sequence_cpu_plan(reference)
    return operation_cpu_plan(document(reference))


def current_cpu_owner():
    """Join a running normal owner by config hash, exact child and actual ancestry."""
    runtime = Path(os.environ.get("QUORIDOR_RESEARCH_JOB_DIR", ""))
    if not runtime.is_absolute():
        return None
    config = document(bound(runtime / "config.json")[0])
    state = document(bound(runtime / "state.json")[0])
    own = process.identity(process.process_info(os.getpid()))
    require(
        (state.get("child") == own or (state["phase"] == "starting" and state.get("child") is None))
        and state["phase"] in {"starting", "running"}
        and process.alive(state["supervisor"])
        and process.process_info(own["pid"])["parent"] == state["supervisor"]["pid"]
        and state["config_sha256"] == sha(json.dumps(config, sort_keys=True).encode()),
        "actual running CPU owner/config/child ancestry",
    )
    if config.get("authority_parent") is not None:
        cohort_parent_check(cohort_job_authority(config, runtime))
    require(state.get("cpu_plan") is not None, "owning job has no resolved CPU plan")
    return state["cpu_plan"]


def physical_and_quiet(spec, *, collection=False):
    cfg = spec["limits"]
    plan = operation_cpu_plan(spec)
    if collection:
        plan = process.CPUPlan(list(plan.management), {"run": list(plan.management)})
    plan.check_host(process.available_cpus())
    require(
        process.available_memory() >= cfg["family_B"] + cfg["host_reserve_B"],
        "physical RAM admission",
    )
    owner = current_cpu_owner()
    if owner is not None:
        require(
            set(plan.all) <= set(owner["allocation"]),
            "child operation outside actual owner CPU plan",
        )
    else:
        # A separate terminal collector has its own explicit plan and no live
        # delegated exemption; its owning job performs the conflict check.
        require(
            os.sched_getaffinity(0) <= set(plan.all),
            "collector outside assigned CPU scope",
        )
        process.compute_peers(
            process.identity(process.process_info(os.getpid())),
            plan.all,
            {
                "cargo",
                "rustc",
                "cc1plus",
                "quoridor-runner",
                "terminal-cache",
                "chromium",
                "chrome",
            },
        )
    plan.apply()
    return plan


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
        budget = spec.get("command_timeout_seconds")
        if budget is not None:
            require(type(budget) is int and budget > 0, "positive admitted command timeout")
            if getattr(resources, "deadline", None) is None:
                # Start at the first actual command, never during source preparation.
                # All commands in this operation share this deadline and cleanup reserve.
                resources.deadline = time.monotonic() + budget
        capture = Capture(directory / (row["name"] + ".full.log"), spec["limits"]["log_B"])
        plan = getattr(resources, "cpu_plan", None) or operation_cpu_plan(spec)
        scope = "test" if row.get("role") == "test" else "run"
        cpu_args = {"cpu_plan": plan, "cpu_scope": scope}
        if spec.get("perf") is not None and row.get("role", "run") == "run":
            require(
                spec["kind"] == "run" and row["argv"] == spec["argv"],
                "actual configured profiler launch",
            )
            cpu_args["no_new_privs"] = True
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
        # This is an actual exception after execute's finally, not a normal
        # guardian return or evidence reconstructed from a pre-final disk record.
        outcome = getattr(error, "cycle_cleanup_outcome", None)
        if outcome is not None:
            if (
                isinstance(outcome, dict)
                and outcome.get("normal_return") is False
                and isinstance(outcome.get("record"), dict)
                and outcome["record"].get("command") == [str(arg) for arg in row["argv"]]
            ):
                check["guardian_exception_outcome"] = outcome
            else:
                check["secondary"].append(
                    {
                        "stage": "guardian_exception_outcome",
                        "type": "Refused",
                        "message": "exception cleanup does not join this actual command",
                    }
                )
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
        len(source["commit"]) == 40 and all(c in "0123456789abcdef" for c in source["commit"]),
        "Git revision",
    )
    workspace = Path(source["workspace"])
    require(workspace.is_absolute(), "adopted workspace")
    for name, filename in (("manifest", "Cargo.toml"), ("lock", "Cargo.lock")):
        require(source[name]["path"] == str(workspace / filename), "adopted Cargo " + name)
    untracked = source["untracked_inputs"]
    require(
        type(untracked) is list and len({r["path"] for r in untracked}) == len(untracked),
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
        git("diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", "--") == patch,
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
        "games/quoridor/crates",
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
            require(not path.exists() and not path.is_symlink(), "Cargo config appeared")
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
)


def numerical_fields(experiment, manifest):
    weights = []
    for model in experiment["models"]:
        if model["weights"] is None:
            require(experiment["phase"] == "fit", "fresh weights are fit-only")
            config = document(experiment["config"])
            warm = config["experiment"]["warm_start"]
            require(
                config["experiment"]["study"] == "mixed-outcome"
                and experiment["models"] == [model]
                and model
                == {
                    "descriptor": warm["descriptor"],
                    "weights": None,
                    "evaluator_sha256": None,
                }
                and warm["weights"] is None
                and warm["evaluator_sha256"] is None
                and warm["optimizer"] == "fresh"
                and warm["scale"] == "incumbent"
                and type(config["training"]["seed"]) is int,
                "explicit fresh initializer, descriptor normalization and bound seed",
            )
            weights.append(None)
        else:
            weights.append(model["weights"]["sha256"])
    return {
        "schema": "quoridor.research.numerical-qualification.v1",
        "status": "PASS",
        "phase": experiment["phase"],
        "artifact_sha256": manifest["artifact"]["sha256"],
        "config_sha256": experiment["config"]["sha256"],
        "schedule_sha256": experiment["schedule"]["sha256"],
        "input_sha256": [r["sha256"] for r in experiment["inputs"]],
        "descriptor_sha256": [r["descriptor"]["sha256"] for r in experiment["models"]],
        "weights_sha256": weights,
        "evaluator_sha256": [r["evaluator_sha256"] for r in experiment["models"]],
        "rules": experiment["rules"],
        "distance_units": experiment["distance_units"],
        "value_perspective": experiment["value_perspective"],
        "canonical_plan_sha256": experiment["canonical_plan_sha256"],
        "remaining": [],
    }


def resolved_lmr_parameters(config, profile, *, supported=True):
    """Typed coefficient box shared by preparation and normal data correspondence.

    Native owns table construction and namespace identity. Explicit values are
    validated even while OFF; omission alone resolves the retained baseline.
    """
    baseline = dict(intercept=0.7844, log_divisor=2.4696, min_depth=3, min_rank=4, max_extra=3)
    if "lmr_parameters" not in config:
        return baseline
    value = config["lmr_parameters"]
    require(
        supported
        and profile == "control"
        and config.get("lmr_method", "depth_rank") == "depth_rank",
        "LMR parameters require a supported research Control/depth_rank caller",
    )
    require(type(value) is dict and set(value) == set(baseline), "complete typed LMR parameters")
    for key, low, high in [("intercept", 0.0, 2.0), ("log_divisor", 1.0, 4.0)]:
        require(
            type(value[key]) in (int, float)
            and math.isfinite(value[key])
            and low <= value[key] <= high,
            "finite LMR " + key,
        )
    for key, low, high in [("min_depth", 3, 63), ("min_rank", 4, 63), ("max_extra", 0, 8)]:
        require(type(value[key]) is int and low <= value[key] <= high, "integer LMR " + key)
    return dict(value, intercept=0.0 if value["intercept"] == 0 else value["intercept"])


def measurement_config(experiment):
    """Functional shapes only; settings and input order belong to the run."""
    config = document(experiment["config"])
    requests = document(experiment["schedule"])
    require(
        isinstance(config, dict)
        and set(config)
        <= {
            "inference",
            "probcut",
            "probcut_samples",
            "search_threads",
            "smp_sharing_provenance",
            "search_cpu_cores",
            "management_cpu_core",
            "native_memory_bytes",
            "time_reserve_ms",
            "roots",
            "profile",
            "tt_entries",
            "use_tt",
            "use_pvs",
            "namespace",
            "output_bytes",
            "record_bytes",
            "seed",
            "lmr",
            "lmr_method",
            "lmr_parameters",
            "neighbour_opportunity",
            "root_ordering_quality",
            "history_provenance",
            "zero_stock_approx_min_root_walls",
            "zero_stock_approx_method",
            "zero_stock_safe_race",
            "zero_stock_safe_race_method",
        }
        and {
            "roots",
            "profile",
            "tt_entries",
            "use_tt",
            "use_pvs",
            "namespace",
            "output_bytes",
            "record_bytes",
        }
        <= set(config),
        "measurement settings shape",
    )
    if "probcut" in config or "probcut_samples" in config:
        p = config.get("probcut")
        samples = config.get("probcut_samples", 0)
        require(type(samples) is int and 0 <= samples <= 8, "ProbCut first sample bound")
        require(
            config.get("search_threads", 1) == 1
            and config["profile"] == "control"
            and config["use_pvs"]
            and config["use_tt"]
            and config.get("zero_stock_approx_min_root_walls") is None
            and "neighbour_opportunity" not in config
            and "root_ordering_quality" not in config
            and "history_provenance" not in config,
            "ProbCut is N1 Control/PVS with no other observer or approximation",
        )
        require(
            not (p is not None or samples != 0)
            or all(not r.get("observe_lmr", False) for r in requests),
            "ProbCut or sampling cannot enter the OFF-only LMR observation path",
        )
        if "probcut" in config:
            require(
                isinstance(p, dict)
                and set(p)
                == {
                    "shallow_depth",
                    "deep_depth",
                    "slope",
                    "intercept",
                    "margin",
                    "nonterminal_abs_bound",
                    "terminal_utility",
                    "calibration_sha256",
                },
                "complete calibrated ProbCut object; absence is OFF",
            )
            require(
                samples == 0
                and type(p["shallow_depth"]) is int
                and p["shallow_depth"] == 1
                and type(p["deep_depth"]) is int
                and p["deep_depth"] == 3,
                "exact1/3 only; calibration references are OFF",
            )
            require(
                all(
                    type(p[k]) in (int, float) and math.isfinite(p[k])
                    for k in (
                        "slope",
                        "intercept",
                        "margin",
                        "nonterminal_abs_bound",
                        "terminal_utility",
                    )
                )
                and p["slope"] > 0
                and p["margin"] >= 0
                and p["nonterminal_abs_bound"] > 0
                and p["terminal_utility"] > p["nonterminal_abs_bound"]
                and isinstance(p["calibration_sha256"], str)
                and len(p["calibration_sha256"]) == 64
                and all(c in "0123456789abcdefABCDEF" for c in p["calibration_sha256"]),
                "finite calibrated domain and provenance; actual domain checked by native owner",
            )
    if "search_threads" in config:
        threads = config["search_threads"]
        team = config.get("search_cpu_cores")
        main = config.get("management_cpu_core")
        require(
            type(threads) is int
            and threads > 0
            and isinstance(team, list)
            and len(team) == threads
            and all(type(c) is int and c >= 0 for c in team)
            and len(set(team)) == threads
            and type(main) is int
            and main >= 0
            and main not in team
            and type(config.get("native_memory_bytes")) is int
            and config["native_memory_bytes"] >= 64 * 1024**2
            and config["profile"] == "control"
            and config["use_tt"]
            and config.get("zero_stock_approx_min_root_walls") is None
            and (
                ("neighbour_opportunity" not in config and "root_ordering_quality" not in config)
                or (
                    threads == 1
                    and config.get("root_ordering_quality") is True
                    and config.get("neighbour_opportunity") == "off_shadow"
                )
            )
            and all(
                not any(
                    r.get(k, False)
                    for k in (
                        "diagnostic",
                        "observe_lmr",
                        "observe_completed_depths",
                        "warmup",
                    )
                )
                for r in requests
            ),
            "positive admitted ordinary native search team; no observer/approximation",
        )
    else:
        require(
            not any(
                k in config
                for k in (
                    "search_cpu_cores",
                    "management_cpu_core",
                    "native_memory_bytes",
                )
            ),
            "unused search-team resources",
        )
    if "smp_sharing_provenance" in config:
        require(
            type(config["smp_sharing_provenance"]) is bool
            and (not config["smp_sharing_provenance"] or "search_threads" in config),
            "sharing provenance is an explicit Boolean opt-in for a configured native team",
        )
    if "time_reserve_ms" in config:
        reserve = config["time_reserve_ms"]
        require(
            ("search_threads" in config or config.get("root_ordering_quality") is True)
            and type(reserve) is int
            and reserve >= 0
            and all(
                type(r.get("time_limit_ms")) is int and r["time_limit_ms"] > reserve
                for r in requests
            ),
            "explicit clock requests retain a positive budget after reserve",
        )
    require(
        config["profile"] in {"control", "cheap", "coverage"},
        "configured ordering target",
    )
    for key in ("tt_entries", "output_bytes", "record_bytes"):
        require(type(config[key]) is int and config[key] > 0, "measurement positive " + key)
    require(
        config["record_bytes"] <= config["output_bytes"],
        "measurement record/output limit",
    )
    require(
        all(type(config[key]) is bool for key in ("use_tt", "use_pvs")),
        "measurement Boolean switches",
    )
    require(type(config.get("lmr", False)) is bool, "measurement LMR switch")
    require(
        type(config.get("zero_stock_safe_race", True)) is bool,
        "measurement safe-race switch",
    )
    safe_method = config.get("zero_stock_safe_race_method")
    require(
        safe_method is None
        or (
            type(safe_method) is str
            and safe_method
            in {
                "manhattan",
                "path_tail",
                "path_tail_future",
            }
        ),
        "measurement safe-race method",
    )
    root_quality = config.get("root_ordering_quality", False)
    require(type(root_quality) is bool, "root ordering quality Boolean switch")
    if "history_provenance" in config:
        watch = config["history_provenance"]
        require(
            root_quality and type(watch) is list and 0 < len(watch) <= 8,
            "bounded selected history entries require root quality",
        )
        seen_watch = set()
        for entry in watch:
            require(
                type(entry) is dict and entry.get("kind") in {"main", "continuation"},
                "history entry kind",
            )
            require(
                type(entry.get("colour")) is int
                and entry["colour"] in {0, 1}
                and type(entry.get("action")) is int
                and 0 <= entry["action"] < 209,
                "history entry colour/action",
            )
            if entry["kind"] == "main":
                require(
                    set(entry) == {"kind", "colour", "from_cell", "action"}
                    and (
                        (
                            entry["action"] < 81
                            and type(entry["from_cell"]) is int
                            and 0 <= entry["from_cell"] < 81
                        )
                        or (entry["action"] >= 81 and entry["from_cell"] is None)
                    ),
                    "history main entry key",
                )
            else:
                require(
                    set(entry) == {"kind", "colour", "lag", "previous", "action"}
                    and type(entry["lag"]) is int
                    and entry["lag"] in {1, 2, 3, 4, 6}
                    and type(entry["previous"]) is int
                    and 0 <= entry["previous"] < 209,
                    "history continuation entry key",
                )
            identity = tuple(sorted(entry.items()))
            require(identity not in seen_watch, "duplicate history entry")
            seen_watch.add(identity)
    opportunity = config.get("neighbour_opportunity")
    if "neighbour_opportunity" in config:
        require(
            type(opportunity) is str
            and opportunity in {"off_shadow", "on"}
            and config["profile"] == "control"
            and config["use_tt"]
            and config["use_pvs"]
            and config.get("lmr", False)
            and config.get("lmr_method", "depth_rank") == "depth_rank"
            and config.get("zero_stock_safe_race", True)
            and config.get("zero_stock_safe_race_method") in {None, "path_tail"}
            and config.get("zero_stock_approx_min_root_walls") is None,
            "isolated neighbour opportunity diagnostic",
        )
    lmr_method = config.get("lmr_method", "depth_rank")
    require(
        type(lmr_method) is str
        and lmr_method
        in (
            "fixed_one",
            "depth_rank",
        ),
        "measurement LMR method",
    )
    parameters = resolved_lmr_parameters(config, config["profile"])
    method = config.get("zero_stock_approx_method", "race")
    require(
        type(method) is str and method in {"race", "fixed_d"},
        "measurement zero-stock approximation method",
    )
    threshold = config.get("zero_stock_approx_min_root_walls")
    require(
        threshold is None or (type(threshold) is int and 0 <= threshold <= 20),
        "measurement zero-stock threshold must be an integer0..20 or null",
    )
    require(
        not config.get("lmr", False)
        or (config["use_pvs"] and config["profile"] in {"control", "cheap"}),
        "measurement LMR requires PVS and Control/Cheap",
    )
    require(
        config.get("seed") is None or (type(config["seed"]) is int and 0 <= config["seed"] < 2**64),
        "measurement seed metadata",
    )
    namespace = config["namespace"]
    require(
        isinstance(namespace, dict)
        and set(namespace) == {"evaluator", "rules", "selectivity"}
        and all(isinstance(v, str) and v for v in namespace.values())
        and namespace["rules"] == experiment["rules"],
        "measurement namespace",
    )
    inference = config.get("inference")
    if inference is not None:
        require(
            isinstance(inference, dict)
            and {"backend", "model", "model_sha", "library", "logical_row_limit"} <= set(inference)
            and set(inference)
            <= {
                "backend",
                "model",
                "model_sha",
                "library",
                "logical_row_limit",
                "device",
                "cuda_graph",
            }
            and inference["backend"] == "ort"
            and type(inference["logical_row_limit"]) is int
            and inference["logical_row_limit"] > 0
            and type(inference.get("device", 0)) is int
            and inference.get("device", 0) == 0
            and inference.get("cuda_graph", False) is False
            and all(
                type(inference[k]) is str and inference[k].startswith("/")
                for k in ("model", "library")
            )
            and type(inference["model_sha"]) is str
            and len(inference["model_sha"]) == 64
            and all(c in "0123456789abcdef" for c in inference["model_sha"]),
            "measurement native CPU inference shape/budget",
        )
        require(
            config["profile"] == "control"
            and not config.get("lmr", False)
            and config.get("zero_stock_approx_min_root_walls") is None
            and not config.get("zero_stock_safe_race", True)
            and experiment.get("models") == []
            and any(
                r["path"] == inference["model"] and r["sha256"] == inference["model_sha"]
                for r in experiment["inputs"]
            )
            and any(
                r["file"]["path"] == inference["library"]
                for r in experiment.get("dynamic_libraries", [])
            )
            and namespace["evaluator"].startswith("sigma-value-onnx-cpu:sha256:")
            and len(namespace["evaluator"].rsplit(":", 1)[-1]) == 64
            and all(c in "0123456789abcdef" for c in namespace["evaluator"].rsplit(":", 1)[-1]),
            "measurement closed Sigma inputs and native-owned identity",
        )
    require(isinstance(config["roots"], list) and config["roots"], "measurement roots")
    for root in config["roots"]:
        require(
            isinstance(root, dict)
            and {"input", "pointer", "field", "label"} <= set(root)
            and set(root)
            <= {
                "input",
                "pointer",
                "field",
                "label",
                "prefix_len",
                "jsonl_match",
                "check_history",
            }
            and type(root["input"]) is int
            and 0 <= root["input"] < len(experiment["inputs"])
            and all(isinstance(root[k], str) for k in ("pointer", "field", "label"))
            and (not root["pointer"] or root["pointer"].startswith("/"))
            and bool(root["field"]),
            "measurement root selector",
        )
        require(
            root.get("prefix_len") is None
            or (type(root["prefix_len"]) is int and root["prefix_len"] >= 0),
            "chronological prefix length",
        )
        require(
            root.get("jsonl_match") is None or isinstance(root["jsonl_match"], dict),
            "JSONL selection",
        )
        require(type(root.get("check_history", False)) is bool, "history check switch")
    require(isinstance(requests, list), "measurement request array")
    ids, closed, active = set(), set(), None
    for request in requests:
        require(
            isinstance(request, dict)
            and {"id", "session", "root", "depth", "node_cap"} <= set(request)
            and set(request)
            <= {
                "id",
                "session",
                "root",
                "depth",
                "node_cap",
                "time_limit_ms",
                "diagnostic",
                "warmup",
                "observe_completed_depths",
                "observe_lmr",
            }
            and all(isinstance(request[k], str) and request[k] for k in ("id", "session"))
            and request["id"] not in ids
            and type(request["root"]) is int
            and 0 <= request["root"] < len(config["roots"])
            and type(request["depth"]) is int
            and 0 < request["depth"] < 2**16
            and type(request["node_cap"]) is int
            and 0 < request["node_cap"] < 2**64,
            "measurement request type/range/identity",
        )
        require(
            request.get("time_limit_ms") is None
            or (type(request["time_limit_ms"]) is int and 0 < request["time_limit_ms"] < 2**64),
            "measurement optional deadline",
        )
        require(
            all(
                type(request.get(k, False)) is bool
                for k in (
                    "diagnostic",
                    "warmup",
                    "observe_completed_depths",
                    "observe_lmr",
                )
            ),
            "measurement request switches",
        )
        ids.add(request["id"])
        if active != request["session"]:
            require(request["session"] not in closed, "session reused after teardown")
            if active is not None:
                closed.add(active)
            active = request["session"]
    if opportunity is not None:
        require(
            all(
                not any(
                    r.get(k, False)
                    for k in (
                        "observe_lmr",
                        "diagnostic",
                        "observe_completed_depths",
                        "warmup",
                    )
                )
                for r in requests
            ),
            "opportunity diagnostic has no mixed observers/warmup",
        )
    if any(r.get("observe_lmr", False) for r in requests):
        require(
            len(requests) <= 12
            and len({r["session"] for r in requests}) == len(requests)
            and len({r["root"] for r in requests}) == len(requests)
            and config["profile"] == "control"
            and config["tt_entries"] == 1048576
            and config["use_tt"]
            and config["use_pvs"]
            and config.get("lmr", False)
            and lmr_method == "depth_rank"
            and parameters == resolved_lmr_parameters({}, "control")
            and threshold is None
            and not config.get("zero_stock_safe_race", True)
            and all(
                r.get("observe_lmr", False)
                and r["depth"] == 5
                and r["node_cap"] == 1000000
                and r.get("time_limit_ms") is None
                and not r.get("diagnostic", False)
                and not r.get("warmup", False)
                and not r.get("observe_completed_depths", False)
                for r in requests
            ),
            "bounded LMR observation cold Control/depth_rank D5/1M TT1M scope",
        )
        require(
            all(
                r["field"] == "prefix"
                and r.get("prefix_len") is None
                and r.get("jsonl_match") is None
                and not r.get("check_history", False)
                for r in config["roots"]
            ),
            "LMR observation complete-prefix selectors",
        )
    if root_quality:
        require(
            opportunity == "off_shadow"
            and config["tt_entries"] == 1048576
            and 0 < len(requests) <= 26
            and len({r["root"] for r in requests}) == len(requests)
            and len({r["session"] for r in requests}) <= 6
            and all(
                r["depth"] == 64
                and r["node_cap"] <= 1000000
                and (r.get("time_limit_ms") is None or config.get("time_reserve_ms") is not None)
                for r in requests
            ),
            "bounded root ordering quality OffShadow/TT1M/26roots/6sessions/D64/1M/optional-clock-with-reserve",
        )
    return config, requests


def measurement_argv(spec, experiment, native_argv):
    """Standard configured perf wrapper, checked against the actual launch chain."""
    perf = spec.get("perf")
    if perf is None:
        return native_argv
    require(experiment["argv"][1] == "measure", "profiling belongs to measurement entry")
    require(
        set(perf)
        == {
            "tool",
            "output",
            "event",
            "frequency_hz",
            "call_graph",
            "ring_pages",
            "data_max_bytes",
            "no_buildid_cache",
        },
        "standard perf settings",
    )
    for key in ("frequency_hz", "ring_pages", "data_max_bytes"):
        require(type(perf[key]) is int and 0 < perf[key] < 2**64, "positive perf " + key)
    require(
        perf["ring_pages"] & (perf["ring_pages"] - 1) == 0,
        "perf ring pages power of two",
    )
    require(
        all(
            isinstance(perf[k], str) and perf[k] and "\0" not in perf[k]
            for k in ("event", "call_graph")
        ),
        "perf option strings",
    )
    require(type(perf["no_buildid_cache"]) is bool, "perf cache setting")
    require(
        artifact_ref(perf["tool"]["path"]) == perf["tool"],
        "actual standard perf executable",
    )
    output = owned(perf["output"], spec["owner"])
    require(not os.path.lexists(output), "exclusive perf RAW output")
    require(
        any(
            item["path"] == str(output) and item["limit_B"] == perf["data_max_bytes"]
            for item in spec["data"]
        ),
        "full configured perf RAW capture",
    )
    argv = [
        perf["tool"]["path"],
        "record",
        "-e",
        perf["event"],
        "-F",
        str(perf["frequency_hz"]),
        "--call-graph",
        perf["call_graph"],
        "-m",
        str(perf["ring_pages"]),
        "--max-size",
        str(perf["data_max_bytes"]) + "B",
    ]
    if perf["no_buildid_cache"]:
        argv.append("--no-buildid-cache")
    return [*argv, "-o", str(output), "--", *native_argv]


def measurement_evidence(spec, experiment, values, *, files=()):
    """Read the actual result; partial counts are facts, not a plan-equality gate."""
    snapshot = json.loads(values["settings"]) if "settings" in values else None
    result = json.loads(values["result"]) if "result" in values else None
    journal = values.get("measurements", b"")
    prefix, separator, tail = journal.rpartition(b"\n")
    complete = prefix + separator if separator else b""
    rows = [json.loads(line) for line in complete.splitlines()]
    require(
        snapshot is None or isinstance(snapshot, dict),
        "measurement settings snapshot shape",
    )
    if result is not None:
        require(
            isinstance(result, dict)
            and ("measurements" not in result or isinstance(result["measurements"], list)),
            "measurement result shape",
        )
        for key in ("planned", "calls", "complete", "uncompleted", "unperformed"):
            if key in result:
                require(
                    type(result[key]) is int and result[key] >= 0,
                    "measurement count type: " + key,
                )
        require(isinstance(result.get("errors"), list), "measurement errors array")
    raw_refs = [ref for ref in files if spec.get("perf") and ref["path"] == spec["perf"]["output"]]
    if result is not None and spec.get("perf"):
        result = {**result, "perf_RAW": raw_refs}
    result_rows = result.get("measurements") if result is not None else None
    result_inline = result
    result_file = None
    if result is not None and len(values["result"]) > CONTROL_BYTES // 4:
        result_path = next(item["path"] for item in spec["data"] if item["name"] == "result")
        result_file = next(ref for ref in files if ref["path"] == result_path)
        result_inline = {
            key: result[key]
            for key in (
                "schema",
                "status",
                "planned",
                "calls",
                "complete",
                "uncompleted",
                "unperformed",
                "errors",
                "census",
                "runtime_launch_origin",
            )
            if key in result
        }
        result_inline["records_embedded"] = False
    recorded_prefix = rows if not isinstance(result_rows, list) else None
    recorded_prefix_file = None
    if recorded_prefix is not None and len(journal) > CONTROL_BYTES // 4:
        journal_path = next(item["path"] for item in spec["data"] if item["name"] == "measurements")
        recorded_prefix_file = next(ref for ref in files if ref["path"] == journal_path)
        recorded_prefix = None
    return {
        "settings": snapshot,
        "result": result_inline,
        "result_file": result_file,
        "journal_rows": len(rows),
        "journal_partial_tail": bool(tail),
        "journal_tail_bytes": len(tail),
        "journal_tail_sha256": sha(tail) if tail else None,
        "observed_complete": sum(row.get("status") == "COMPLETE" for row in rows),
        "journal_result_rows_agree": len(rows) == len(result_rows)
        if isinstance(result_rows, list)
        else None,
        "unreturned_tail": result is None,
        "recorded_prefix": recorded_prefix,
        "recorded_prefix_file": recorded_prefix_file,
        "runtime_launch_origin": result.get("runtime_launch_origin")
        if result
        else snapshot.get("runtime_launch_origin")
        if snapshot
        else None,
        "perf_RAW": raw_refs,
        "scope": "Actual settings plus result. Missing counters remain absent; partial/error/UNKNOWN are retained. No scientific adoption or original qualification claim.",
    }


def numerical_check(experiment, manifest, *, refs=None):
    q = document(experiment["numerical_qualification"])
    expected = numerical_fields(experiment, manifest)
    require(
        all(q.get(k) == v for k, v in expected.items()),
        "current numerical/model/input correspondence",
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
        environment.is_absolute() and (environment / "pyvenv.cfg").is_file() and python.is_file(),
        "prepared shared project Python required",
    )
    return python


def common_training_environment(spec):
    """Shared current project import/thread predicate for admitted Python fits."""
    require(
        spec["cwd"] == str(ROOT)
        and spec["env"].get("PYTHONDONTWRITEBYTECODE") == "1"
        and spec["env"].get("PYTHONPATH")
        == os.pathsep.join(str(ROOT / p) for p in ("games/quoridor/python", "shared/python"))
        and spec["env"].get("PYTHONSAFEPATH") == "1"
        and all(
            spec["env"].get(k) == "1"
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        ),
        "pinned framework/import/thread environment",
    )


def common_study_check(spec, experiment, manifest, approved):
    """Functional generation/training inputs; quantities and recipes belong to settings."""
    phase = experiment["phase"]
    config = document(experiment["config"])
    require(
        experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and experiment["distance_units"] == "wall-distance/80"
        and experiment["value_perspective"] == "side-to-move",
        "common study rules/units/perspective",
    )
    if phase == "corpus":
        numerical_check(experiment, manifest)
        require(
            experiment["models"] == []
            and experiment["argv"][1:]
            == [
                "teacher-pilot",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ]
            and config["common_study"]["root_value_policy"] == "outcome_only"
            and config["planned_games"] == config["common_study"]["batch_count"]
            and config["output"] == spec["data_root"]
            and type(config["planned_games"]) is int
            and config["planned_games"] > 0
            and type(config["depth"]) is int
            and config["depth"] > 0
            and type(config["max_nodes"]) is int
            and config["max_nodes"] > 0
            and (
                config["max_total_nodes"] is None
                or type(config["max_total_nodes"]) is int
                and config["max_total_nodes"] > 0
            ),
            "configured model-free corpus entry/output/work",
        )
        cpus = spec.get("child_cpu_cores")
        workers = config["worker_cores"]
        require(
            isinstance(cpus, list)
            and all(type(c) is int and c >= 0 for c in cpus)
            and cpus == sorted(set(cpus))
            and len(workers) == config["game_workers"]
            and workers
            and workers == cpus[: len(workers)]
            and config["cpu_core"] == workers[0]
            and spec["limits"]["worker_cpu"] in workers
            and spec["limits"]["guardian_cpu"] in cpus[len(workers) :]
            and len(cpus) >= len(workers) + 2,
            "configured generator workers/guardian and host reserve cores",
        )
        return
    project_interpreter(experiment)
    common_training_environment(spec)
    python = str(project_python())
    require("child_cpu_cores" not in spec, "nongame software/fit cannot widen child CPUs")
    if phase == "software-qualification":
        definition = config["definition"]
        require(
            definition in experiment["inputs"]
            and all(r in experiment["inputs"] for r in config.get("helper_sources", []))
            and config["result"] == str(Path(spec["data_root"]) / "qualification.json")
            and spec["argv"] == [python, "-B", definition["path"], "--result", config["result"]],
            "configured software definition and actual output",
        )
        return
    require(phase == "fit" and experiment["planned_slots"] == 0, "nongame training scope")
    argv = spec["argv"]
    require(
        len(argv) in {11, 13}
        and argv[:5] == [python, "-B", "-m", "quoridor_training.train", "train"]
        and argv[5] == "--cache"
        and Path(argv[6]).is_absolute()
        and argv[7:11] == ["--output", spec["data_root"], "--config", experiment["config"]["path"]]
        and (
            len(argv) == 11
            or argv[11] == "--input-binding"
            and any(r["path"] == argv[12] for r in experiment["inputs"])
        ),
        "maintained train/cache/output/config and optional distinct binding",
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
        ]
        and warm["optimizer"] == "fresh"
        and warm["scale"] == "incumbent",
        "declared immutable initializer and original scale",
    )
    numerical_check(experiment, manifest)
    if config["experiment"]["study"] == "mixed-outcome":
        mixture = config["mixture"]
        require(config["training"]["target"] == "z", "mixed outcome teacher")
        for key in ("public_membership", "public_acceptance"):
            require(mixture[key] in experiment["inputs"], "actual indexed public " + key)
        public_root = Path(mixture["public_membership"]["path"]).parent.resolve()
        require(
            all(
                not Path(r["path"]).resolve().is_relative_to(public_root)
                or r == mixture["public_membership"]
                for r in experiment["inputs"]
            ),
            "public payload remains indexed/shared; no repeated full payload hashing",
        )
    cache_ref = next(
        (r for r in experiment["inputs"] if r["path"] == str(Path(argv[6]) / "cache.json")),
        None,
    )
    require(
        cache_ref is not None and not Path(argv[6]).joinpath("intake-incomplete.json").exists(),
        "published actual added cache",
    )
    cache = json.loads(read_ref(cache_ref, max(CONTROL_BYTES, cache_ref["bytes"])))
    require(cache["stream_intake"]["status"] == "complete", "atomic cache intake")
    for name, width in COMPACT_CACHE_WIDTHS.items():
        path = str(Path(argv[6]) / name)
        ref = next((r for r in experiment["inputs"] if r["path"] == path), None)
        require(
            ref is not None
            and ref["sha256"] == cache["sha256"][name]
            and ref["bytes"] == cache["file_bytes"][name] == cache["rows"] * width,
            "actual compact binary custody",
        )
    eligible = cache["common_corpus"]["common_eligible_by_split"]
    require(
        all(type(eligible.get(k)) is int and eligible[k] > 0 for k in ("train", "validation")),
        "nonempty actual eligible T/V",
    )


def caller_source_refs(spec, experiment):
    paths = {
        ROOT / "scripts/dev/research-lifecycle.py",
        ROOT / "scripts/dev/research-job.py",
        ROOT / "shared/python/quoridor_runtime/__init__.py",
        ROOT / "shared/python/quoridor_runtime/cycle_process.py",
        ROOT / "shared/python/quoridor_runtime/snapshot.py",
    }
    if experiment["phase"] in {"fit", "software-qualification"}:
        paths |= {
            ROOT / "games/quoridor/python/quoridor_training" / (name + ".py")
            for name in FIT_IMPORTS
        }
        if (
            experiment["phase"] == "fit"
            and document(experiment["config"])["experiment"]["study"] == "mixed-outcome"
        ):
            paths.add(ROOT / "games/quoridor/python/quoridor_training/public_replay.py")
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
                ROOT / "games/quoridor/python/quoridor_training/research355" / (name + ".py")
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
                == str(ROOT / "games/quoridor/python/quoridor_training/research355/stream355.py"),
                "current maintained analysis entry",
            )
    if experiment["phase"] == "arena" or (
        experiment["phase"] == "compare" and experiment["argv"][1] == "decisions"
    ):
        config = document(experiment["config"])
        if any(e["kind"] == "claustrophobia" for e in config["engines"]):
            paths |= {
                ROOT / "games/quoridor/python/quoridor_training/claustrophobia.py",
                ROOT / "games/quoridor/python/quoridor_training/static_teacher_heads.py",
                project_python().resolve(strict=True),
                project_python().parent.parent / "pyvenv.cfg",
            }
    refs = spec["caller_sources"]
    require(
        isinstance(refs, list)
        and len(refs) == len(paths)
        and {r["path"] for r in refs} == {str(p) for p in paths},
        "exact current caller/import membership",
    )
    return refs


def prior_software_roles(adoption_ref, *, current_sources=False):
    """Consume accepted, completed checks without replaying them during BUILD."""
    adoption = document(adoption_ref)
    require(
        adoption["schema"] == "quoridor.research.source-adoption.v1"
        and adoption["status"] == "ACCEPTED",
        "accepted source adoption required",
    )
    qualification = adoption.get("prior_software")
    if qualification is None:
        return set()
    require(bool(qualification["subjects"]), "prior software source scope required")
    if current_sources:
        for ref in qualification["subjects"]:
            require(artifact_ref(ref["path"]) == ref, "prior software source drift")
    roles = set()
    selected_names = set()
    for selected in qualification["receipts"]:
        require(selected["name"] not in selected_names, "duplicate prior software selection")
        selected_names.add(selected["name"])
        receipt = document(selected["file"])
        recorded = receipt["checks"]
        failed = [c for c in recorded if c["status"] == "FAILED"]
        require(len(failed) <= 1, "multiple failed prior software checks")
        if receipt.get("primary") is not None:
            require(
                len(failed) == 1
                and failed[0] is recorded[-1]
                and failed[0].get("primary") == receipt["primary"]
                and failed[0]["name"] != selected["name"],
                "prior parent failure must belong to one different final failed check",
            )
        checks = [c for c in recorded if c["name"] == selected["name"]]
        require(len(checks) == 1, "one original prior software check")
        check = checks[0]
        guardian = check["guardian_return"]
        require(
            check["status"] == "PASS"
            and check["capture_complete"] is True
            and not check.get("primary")
            and not check.get("secondary")
            and guardian["command"] == check["argv"]
            and guardian["exit_code"] == 0
            and guardian["direct_child_reaped"] is True
            and guardian["cleanup_complete"] is True
            and guardian["handle_closes_complete"] is True
            and guardian["remaining"] == [],
            "completed prior software check required",
        )
        argv = check["argv"]
        require(
            len(argv) > 1 and Path(argv[0]).name == "cargo" and argv[1] in {"test", "clippy"},
            "prior Cargo test/lint only",
        )
        require(
            {"--offline", "--locked", "-j1"} <= set(argv)
            and not any(x.startswith("-A") or x.startswith("--allow") for x in argv),
            "bounded prior Cargo qualification",
        )
        if argv[1] == "clippy":
            require(
                "--no-deps" in argv
                and (
                    "-Dwarnings" in argv
                    or any(a == "-D" and b == "warnings" for a, b in zip(argv, argv[1:]))
                ),
                "prior scoped Clippy warnings denied",
            )
        read_ref(check["full_log"])
        roles.add({"test": "test", "clippy": "lint"}[argv[1]])
    return roles


def accepted_build(ref):
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
        document(manifest["source_adoption"])["source"] == manifest["source"],
        "build source adoption correspondence",
    )
    require(
        {r["role"] for r in manifest["checks"]} | prior_software_roles(manifest["source_adoption"])
        >= {"test", "lint", "build"},
        "affected test/lint/build required",
    )
    require(
        artifact_ref(manifest["artifact"]["path"]) == manifest["artifact"],
        "artifact identity drift",
    )
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
        },
        "phase",
    )
    if phase == "compare" and experiment["argv"][1] == "measure":
        config = document(experiment["config"])
        fixed_d = config["namespace"]["evaluator"] == "original-distance-a0-b8-tanh"
        sigma_value = config.get("inference") is not None
        require(
            (sigma_value and experiment["models"] == [] and config["profile"] == "control")
            or (
                not sigma_value
                and fixed_d
                and experiment["models"] == []
                and config["profile"] in {"control", "coverage", "cheap"}
            )
            or (
                not sigma_value
                and not fixed_d
                and len(experiment["models"]) == 1
                and config["profile"] in {"control", "cheap"}
            ),
            "measurement evaluator/model/profile binding",
        )
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
    """Ordered saved streams enter the maintained converter; no previous-cache migration."""
    request = document(experiment["config"])
    require(
        {"schema", "streams", "output"} <= set(request)
        and set(request) <= {"schema", "streams", "output", "input_binding", "mcts_configs"}
        and request["schema"] == "quoridor.common-corpus-cache-materialization.v1"
        and request["output"] == spec["data_root"],
        "saved converter config/output",
    )
    require(
        experiment["models"] == []
        and experiment["planned_slots"] == 0
        and experiment.get("batch") is None
        and experiment.get("numerical_qualification") is None
        and experiment["rules"] == "research-standard-2p-threefold-goal-first-v1"
        and experiment["distance_units"] == "wall-distance/80"
        and experiment["value_perspective"] == "side-to-move",
        "saved codec scope",
    )
    streams = request["streams"]
    require(isinstance(streams, list) and streams, "nonempty ordered stream inputs")
    require(len({r["path"] for r in streams}) == len(streams), "distinct stream inputs")
    require(all(r in experiment["inputs"] for r in streams), "actual converter stream refs")
    mcts = request.get("mcts_configs")
    if mcts is not None:
        require(mcts in experiment["inputs"] and mcts not in streams, "bound MCTS config-list file")
        configs = document(mcts)
        require(
            isinstance(configs, list)
            and len(configs) == len(streams)
            and all(isinstance(r, dict) and set(r) == {"path", "sha256"} for r in configs)
            and len({r["path"] for r in configs}) == len(configs)
            and all(
                any(
                    {k: ref[k] for k in ("path", "sha256")} == r
                    for ref in experiment["inputs"]
                    if ref not in streams and ref != mcts
                )
                for r in configs
            ),
            "actual ordered native config references",
        )
    argv = [manifest["artifact"]["path"]]
    for ref in streams:
        path = Path(ref["path"])
        require(path.is_absolute(), "absolute stream input")
        if mcts is not None:
            require(path.name == "manifest.json", "MCTS input is the actual dataset manifest")
        argv.extend(["--input", str(path.parent) if mcts is not None else ref["path"]])
    argv.extend(["--output", spec["data_root"]])
    if mcts is not None:
        argv.extend(["--mcts-configs", mcts["path"], "--mcts-configs-sha256", mcts["sha256"]])
    binding = request.get("input_binding")
    if binding is not None:
        require(
            binding in experiment["inputs"] and binding not in streams,
            "distinct optional lineage input",
        )
        argv.extend(["--input-binding", binding["path"], "--binding-sha256", binding["sha256"]])
    require(experiment["argv"] == argv, "maintained converter ordered argv")
    require(
        len(spec["data"]) == 8
        and {x["name"]: x["path"] for x in spec["data"]}
        == {
            **{n: str(Path(spec["data_root"]) / n) for n in COMPACT_CACHE_WIDTHS},
            "cache_manifest": str(Path(spec["data_root"]) / "cache.json"),
        },
        "compact seven files plus final manifest",
    )


def experiment_check(spec):
    charged_roots(spec)
    experiment = document(spec["experiment"])
    require(experiment["schema"] == EXPERIMENT_SCHEMA, "experiment schema")
    experiment_phase_check(experiment)
    manifest = accepted_build(experiment["build_manifest"])
    require(manifest["artifact"] == spec["artifact"], "same actual executable")
    mixed_outcome = (
        experiment["phase"] == "fit"
        and document(experiment["config"])["experiment"]["study"] == "mixed-outcome"
    )
    if mixed_outcome:
        # Current source hashes precede importing the new metadata-only admission.
        for caller in caller_source_refs(spec, experiment):
            read_ref(caller, max(CONTROL_BYTES, caller["bytes"]))
        common_study_check(spec, experiment, manifest, approved_plan(spec, experiment))
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
        refs.append(model["descriptor"])
        if model["weights"] is None:
            # common_study_check already checked the fresh config/seed correspondence.
            require(
                mixed_outcome and model["evaluator_sha256"] is None,
                "only an admitted fresh fit omits trained weights",
            )
        else:
            refs.append(model["weights"])
    for library in experiment["dynamic_libraries"]:
        require(
            isinstance(library["version"], str) and bool(library["version"].strip()),
            "dynamically loaded library version required",
        )
        refs.append(library["file"])
    refs.extend(caller_source_refs(spec, experiment))
    streamed_inputs = set()
    if experiment["phase"] == "materialize" and manifest.get("artifact_target") == "terminal-cache":
        streamed_inputs = {r["path"] for r in document(experiment["config"])["streams"]}
    elif mixed_outcome:
        cache_root = Path(spec["argv"][6])
        streamed_inputs = {str(cache_root / name) for name in COMPACT_CACHE_WIDTHS}
    for ref in refs:
        if ref["path"] in streamed_inputs:
            require(artifact_ref(ref["path"]) == ref, "actual streamed input identity")
        else:
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
    measurement = experiment["phase"] == "compare" and experiment["argv"][1] == "measure"
    if measurement:
        config, _ = measurement_config(experiment)
        if "search_threads" in config:
            native_cpu_cores(spec)
        approved = None
    else:
        approved = approved_plan(spec, experiment)
        refs.append(spec["approved_plan"])
    if experiment["phase"] in {"corpus", "fit", "software-qualification"} and not mixed_outcome:
        common_study_check(spec, experiment, manifest, approved)
    if experiment["phase"] == "compare" and experiment["argv"][1] == "decisions":
        arena_decision_plan_check(experiment, approved)
        if document(experiment["config"])["arena"]["comparison"] == "whole_wall_time":
            native_cpu_cores(spec)
        numerical_check(experiment, manifest, refs=refs)
        require(
            document(experiment["config"])["output"] == spec["data_root"],
            "decision owned runtime output",
        )
    if experiment["phase"] == "arena":
        arena_plan_check(experiment, approved)
        arena_config = document(experiment["config"])
        if arena_config["arena"]["comparison"] == "whole_wall_time" or (
            arena_config["arena"]["comparison"] in {"evaluator_fixed_depth", "search_wall_time"}
            and arena_config.get("management_cpu_core") is not None
        ):
            native_cpu_cores(spec)
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
        spec["argv"] == measurement_argv(spec, experiment, expected_argv),
        "exact experiment/profiler argv",
    )
    if spec.get("perf") is not None:
        refs.append(spec["perf"]["tool"])
    require(bool(spec["data"]), "actual durable data required")
    owned(spec["data_root"], spec["owner"])
    if (
        measurement
        or experiment["phase"] == "arena"
        or (experiment["phase"] == "compare" and experiment["argv"][1] == "decisions")
    ) and spec.get("TMP") is not None:
        owned(spec["TMP"], spec["owner"])
        require(
            not os.path.lexists(spec["TMP"])
            and spec["env"].get("TMPDIR") == spec["TMP"]
            and spec["TMP"] in spec.get("owned_outputs", []),
            "fresh owned execution TMP",
        )
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
    package = "quoridor-data" if artifact_target == "terminal-cache" else "quoridor-runner"
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
        env["CARGO_PROFILE_RELEASE_OPT_LEVEL"] == "3" and env["CARGO_PROFILE_RELEASE_DEBUG"] == "0",
        "frozen release flags",
    )
    for key in ("RUSTC", "RUSTDOC", "CC", "CXX", "AR"):
        require(env[key] == spec["tools"][key]["file"]["path"], "pinned relevant tool env")
    require(
        {c["role"] for c in spec["commands"]}
        | prior_software_roles(spec["source_adoption"], current_sources=True)
        >= {"test", "lint", "build"},
        "one affected qualification",
    )
    names = [c["name"] for c in spec["commands"]]
    require(
        len(names) == len(set(names)) and all(n.replace("-", "").isalnum() for n in names),
        "unique safe command names",
    )
    for c in spec["commands"]:
        require(c["role"] in {"test", "lint", "build"}, "affected software commands only")
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


def private_copy_check(spec, src=None, *, resources=None):
    handover = document(spec["target_handover"])
    root = owned(handover["fresh_private_root"], spec["owner"])
    require(root == Path(spec["private"]).parent, "fresh private root binding")
    if src is None:
        return
    path = owned(src, spec["target"])
    info = path.lstat()
    require(
        stat.S_ISREG(info.st_mode) and info.st_size > 0,
        "private candidate type before copy",
    )
    if resources is not None:
        block = os.statvfs(root).f_frsize
        rounded = ((info.st_size + block - 1) // block) * block
        resources.check(extra_B=rounded)  # Source inode already belongs to the whole union.


def artifact_ref(path, *, resources=None):
    """Stream regular artifact identity, with fixed memory and no executable-size budget."""
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path, "absolute artifact path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode), "regular artifact required")
    except BaseException:
        os.close(fd)
        raise
    with os.fdopen(fd, "rb") as file:
        digest, total = hashlib.sha256(), 0
        while True:
            if resources is not None:
                resources.check()
            block = file.read(min(65536, info.st_size - total + 1))
            if not block:
                break
            total += len(block)
            require(total <= info.st_size, "artifact grew during read")
            digest.update(block)
        after = os.fstat(file.fileno())
        named = path.lstat()
        require(
            total == info.st_size
            and all(
                getattr(info, k) == getattr(after, k)
                for k in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            )
            and (named.st_dev, named.st_ino) == (info.st_dev, info.st_ino),
            "artifact changed during read",
        )
    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "bytes": total,
        "mode": format(stat.S_IMODE(info.st_mode), "04o"),
    }


def copy_artifact(src, dst, *, resources=None):
    dst = Path(dst)
    require(dst.is_absolute() and dst.resolve() == dst, "absolute copy destination")
    expected = artifact_ref(src, resources=resources)
    fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(
            stat.S_ISREG(info.st_mode) and info.st_size == expected["bytes"],
            "copy source type/length",
        )
    except BaseException:
        os.close(fd)
        raise
    with os.fdopen(fd, "rb") as source, Path(dst).open("xb") as destination:
        digest, total = hashlib.sha256(), 0
        while True:
            if resources is not None:
                resources.check()
            block = source.read(min(65536, expected["bytes"] - total + 1))
            if not block:
                break
            total += len(block)
            require(total <= expected["bytes"], "copy source grew")
            digest.update(block)
            destination.write(block)
        named = Path(src).lstat()
        require(
            (named.st_dev, named.st_ino) == (info.st_dev, info.st_ino),
            "copy source path drift",
        )
        destination.flush()
        os.fchmod(destination.fileno(), int(expected["mode"], 8))
        os.fsync(destination.fileno())
        require(
            total == expected["bytes"]
            and digest.hexdigest() == expected["sha256"]
            and all(
                getattr(info, k) == getattr(os.fstat(source.fileno()), k)
                for k in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            ),
            "copy source drift",
        )
    actual = artifact_ref(dst, resources=resources)
    require({**actual, "path": str(src)} == expected, "copied artifact drift")
    if resources is not None:
        resources.check()
    return actual


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
    """Use selected settings for arena; preserve other owning phase admissions."""
    if spec.get("selection_index") is not None:
        expected = selected_run(spec, experiment)
        require(
            experiment["canonical_plan_sha256"] == expected["sha256"],
            "selected RUN plan identity",
        )
        return document(expected)
    if experiment["phase"] == "arena" or (
        experiment["phase"] == "compare" and experiment["argv"][1] == "decisions"
    ):
        expected = selected_arena(spec)
        require(
            experiment["canonical_plan_sha256"] == expected["sha256"],
            "experiment substituted selected plan",
        )
        return document(expected)
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
            require(
                kind
                in {
                    "nnue",
                    "nnue_mcts",
                    "distance",
                    "mcts",
                    "sigma_value",
                    "claustrophobia",
                },
                "supported numerical backend",
            )
            if kind == "nnue":
                model = next(
                    (r for r in plan["models"] if r["descriptor"]["path"] == engine["model"]),
                    None,
                )
                require(
                    model is not None and model["evaluator_sha256"] == m["evaluator_sha256"][i],
                    "declared model/evaluator",
                )
                used.add(model["descriptor"]["path"])
            elif kind == "nnue_mcts":
                settings = engine.get("nnue_mcts")
                require(
                    plan["comparison"] == "whole_wall_time"
                    and isinstance(settings, dict)
                    and set(settings) == {"prior", "logical_row_limit"}
                    and type(settings["logical_row_limit"]) is int
                    and 0 < settings["logical_row_limit"] < 2**64
                    and isinstance(settings["prior"], dict)
                    and len(m["evaluator_sha256"][i]) == 64
                    and all(c in "0123456789abcdef" for c in m["evaluator_sha256"][i]),
                    "explicit NNUE MCTS prior/cumulative rows/native typed identity",
                )
                model = next(
                    (r for r in plan["models"] if r["descriptor"]["path"] == engine.get("model")),
                    None,
                )
                require(model is not None, "NNUE MCTS bound value descriptor")
                used.add(model["descriptor"]["path"])
                prior = settings["prior"]
                if prior.get("kind") == "uniform":
                    require(set(prior) == {"kind"}, "explicit uniform has no head")
                else:
                    require(
                        set(prior) == {"kind", "manifest", "evidence"}
                        and prior["kind"] == "head"
                        and prior["evidence"] in {"synthetic_untrained", "learned"},
                        "explicit policy head/evidence",
                    )
                    head = next(
                        (r for r in plan["inputs"] if r["path"] == prior["manifest"]),
                        None,
                    )
                    require(head is not None, "bound NNUE policy descriptor input")
                    policy = document(head)
                    require(
                        set(policy)
                        == {
                            "schema",
                            "action_order",
                            "head_coordinates",
                            "value_perspective",
                            "reflection",
                            "evidence",
                            "shared_fingerprint",
                            "hidden_width",
                            "weights",
                            "weights_sha256",
                            "weights_bytes",
                        }
                        and policy["schema"] == "quoridor-nnue-policy209-v1"
                        and policy["action_order"] == "absolute-core-action-id209"
                        and policy["head_coordinates"] == "QF1-STM-rotate180"
                        and policy["reflection"] == "core-action-id209-left-right-v1"
                        and policy["value_perspective"] == "side-to-move"
                        and policy["evidence"] == prior["evidence"]
                        and type(policy["hidden_width"]) is int
                        and 0 < policy["hidden_width"] <= 2048
                        and type(policy["weights_bytes"]) is int
                        and policy["weights_bytes"] == 4 * 209 * (policy["hidden_width"] + 1)
                        and isinstance(policy["weights"], str)
                        and policy["weights"] not in {"", ".", ".."}
                        and Path(policy["weights"]).name == policy["weights"]
                        and chr(92) not in policy["weights"]
                        and all(
                            isinstance(policy[k], str)
                            and len(policy[k]) == 64
                            and all(c in "0123456789abcdef" for c in policy[k])
                            for k in ("shared_fingerprint", "weights_sha256")
                        ),
                        "policy209 typed layout/evidence/shared-fingerprint shape",
                    )
                    weights = str(Path(prior["manifest"]).parent / policy["weights"])
                    require(
                        any(
                            r["path"] == weights
                            and r["sha256"] == policy["weights_sha256"]
                            and r["bytes"] == policy["weights_bytes"]
                            for r in plan["inputs"]
                        ),
                        "bound NNUE policy weights",
                    )
                # Actual shared fingerprint and provider identity are recomputed
                # by the native model/provider, then checked by normal arena
                # initialization; this metadata route is no numeric certificate.
            elif kind == "distance":
                require(engine.get("model") is None, "pure distance model")
            elif kind == "claustrophobia":
                settings = engine.get("claustrophobia")
                require(
                    plan["comparison"] == "whole_wall_time"
                    and isinstance(settings, dict)
                    and set(settings)
                    == {
                        "python",
                        "library",
                        "library_sha256",
                        "model_sha256",
                        "simulations",
                        "c_puct",
                        "max_head_calls",
                    }
                    and settings["python"] == str(project_python())
                    and type(settings["simulations"]) is int
                    and 0 < settings["simulations"] < 2**32
                    and type(settings["max_head_calls"]) is int
                    and 0 < settings["max_head_calls"] < 2**64
                    and type(settings["c_puct"]) in (int, float)
                    and math.isfinite(settings["c_puct"])
                    and settings["c_puct"] > 0
                    and any(
                        r["path"] == engine.get("model") and r["sha256"] == settings["model_sha256"]
                        for r in plan["inputs"]
                    )
                    and any(
                        r["file"]["path"] == settings["library"]
                        and r["file"]["sha256"] == settings["library_sha256"]
                        for r in experiment["dynamic_libraries"]
                    )
                    and len(m["evaluator_sha256"][i]) == 64,
                    "closed original Claustrophobia model/library/current interpreter; native typed identity is recomputed",
                )
            elif kind == "sigma_value":
                inference = m.get("inference")
                require(
                    plan["comparison"] == "evaluator_fixed_depth"
                    and engine.get("model") is None
                    and isinstance(inference, dict)
                    and inference["backend"] == "ort"
                    and inference.get("device", 0) == 0
                    and inference.get("cuda_graph", False) is False
                    and type(inference.get("logical_row_limit")) is int
                    and inference["logical_row_limit"] > 0
                    and len(m["evaluator_sha256"][i]) == 64
                    and all(c in "0123456789abcdef" for c in m["evaluator_sha256"][i])
                    and any(
                        r["path"] == inference["model"] and r["sha256"] == inference["model_sha"]
                        for r in plan["inputs"]
                    )
                    and any(
                        r["file"]["path"] == inference["library"]
                        for r in experiment["dynamic_libraries"]
                    ),
                    "closed Sigma static value model/library/native-owned identity",
                )
                # The native owner recomputes the typed identity from actual library SHA.
                sigma = True
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
                        r["path"] == inference["model"] and r["sha256"] == inference["model_sha"]
                        for r in plan["inputs"]
                    )
                    and any(
                        library["file"]["path"] == inference["library"]
                        for library in experiment["dynamic_libraries"]
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
        and plan["comparison"]
        in {"whole_wall_time", "evaluator_fixed_depth", "evaluator_wall_time"}
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
    schedule = document(experiment["schedule"])
    planned = planned_game_slice(experiment, schedule, plan, width=1)
    batch = plan["batches"][experiment["batch"]]
    require(experiment["config"] == batch["config"], "approved decision config")
    c = document(experiment["config"])
    a = c["arena"]
    m = next(m for m in plan["matchups"] if m["id"] == batch["matchup"])
    require(
        c["ruleset"] == "standard_2p_threefold"
        and c["games"] == len(batch["slots"])
        and all(type(c[k]) is int and c[k] == 1 for k in ("workers", "active_games", "max_batch"))
        and c["engines"] == m["engines"]
        and c.get("inference") == m.get("inference")
        and (c.get("inference") is not None or c.get("inference_cpu_core") is None)
        and all(c.get(k) is None for k in ("cycle", "train_games", "validation_games"))
        and a["comparison"] == plan["comparison"]
        and a["clock_policy"] == "strict_unknown"
        and a.get("decision_only") is True
        and type(a.get("disable_continuation_static_ordering", False)) is bool
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
    if plan["comparison"] == "evaluator_fixed_depth":
        require(
            engine.get("time_ms") is None and a["return_reserve_ms"] == 0,
            "completed-depth decision has no move clock/reserve",
        )
    else:
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
    return planned, c


def arena_game_ids(config):
    """Original local IDs; selected and excluded are one fixed approved partition."""
    count = config["games"]
    selection = config["arena"].get("game_selection")
    if selection is None:
        return list(range(count))
    require(type(count) is int and count > 0, "positive original arena game count")
    require(
        isinstance(selection, dict) and set(selection) == {"selected", "excluded"},
        "typed game selection",
    )
    selected, excluded = selection["selected"], selection["excluded"]
    require(
        all(
            isinstance(ids, list)
            and all(type(i) is int and 0 <= i < count for i in ids)
            and ids == sorted(set(ids))
            for ids in (selected, excluded)
        )
        and selected
        and not set(selected) & set(excluded)
        and sorted(selected + excluded) == list(range(count)),
        "selected/excluded original game partition",
    )
    require(not config["arena"].get("decision_only", False), "selection belongs to playing arena")
    return selected


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
        in {
            "evaluator_fixed_depth",
            "evaluator_wall_time",
            "whole_wall_time",
            "search_wall_time",
        }
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
    selected_ids = arena_game_ids(config)
    require(
        a.get("game_selection") == batch.get("game_selection"),
        "approved selected/excluded mask",
    )
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
        and (config.get("inference") is not None or config.get("inference_cpu_core") is None)
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
    if plan["comparison"] == "search_wall_time":
        require(
            a["evaluator_sha256"][0] == a["evaluator_sha256"][1]
            and engines[0]["kind"] == engines[1]["kind"]
            and engines[0]["simd"] == engines[1]["simd"],
            "search comparison requires the same frozen evaluator/implementation mode",
        )
    arena_model_check(experiment, plan, 2)
    for engine in engines:
        require("history_tie_break" not in engine, "retired engine ordering field")
        require(
            engine["kind"] == "nnue_mcts" or engine.get("nnue_mcts") is None,
            "unused NNUE MCTS settings",
        )
        if engine["kind"] == "claustrophobia":
            require(
                a["comparison"] == "whole_wall_time"
                and a.get("max_total_nodes") is None
                and config["temperature"] == 0
                and engine.get("lmr", False) is False
                and engine.get("lmr_method") is None
                and engine.get("lmr_parameters") is None
                and engine.get("ordering_profile") is None
                and engine.get("zero_stock_safe_race") is not True
                and engine.get("zero_stock_safe_race_method") is None,
                "Claustrophobia uses its own search limits, not alpha settings",
            )
        else:
            require(engine.get("claustrophobia") is None, "unused Claustrophobia settings")
        require("shallow_main_history" not in engine, "retired arena setting")
        resolved_lmr_parameters(
            engine,
            engine.get("ordering_profile"),
            supported=engine["kind"] not in {"mcts", "nnue_mcts", "claustrophobia"}
            and a["comparison"] != "functional",
        )
        require(
            type(engine["depth"]) is int
            and 0 < engine["depth"] <= 200
            and type(engine["max_nodes"]) is int
            and engine["max_nodes"] > 0
            and type(engine["simd"]) is bool
            and type(engine.get("lmr", False)) is bool
            and (
                engine.get("zero_stock_safe_race") is None
                or type(engine["zero_stock_safe_race"]) is bool
            )
            and engine.get("zero_stock_safe_race_method")
            in {
                None,
                "manhattan",
                "path_tail",
                "path_tail_future",
            }
            and (
                "lmr_method" not in engine
                or engine["lmr_method"]
                in (
                    "fixed_one",
                    "depth_rank",
                )
            )
            and engine.get("ordering_profile") in {None, "control", "cheap"}
            and (not engine.get("lmr", False) or engine.get("ordering_profile") is not None)
            and (
                engine.get("ordering_profile") is None
                or (
                    engine["kind"] in {"nnue", "distance", "sigma_value"}
                    and not a.get("disable_continuation_static_ordering", False)
                )
            )
            and all(
                type(engine[k]) in (int, float) and math.isfinite(engine[k])
                for k in ("distance_a", "distance_b")
            ),
            "finite engine limits",
        )
    if plan["comparison"] in {"evaluator_fixed_depth", "evaluator_wall_time"}:
        require(
            engines[0].get("lmr", False) == engines[1].get("lmr", False)
            and (
                not engines[0].get("lmr", False)
                or (
                    engines[0].get("lmr_method", "depth_rank")
                    == engines[1].get("lmr_method", "depth_rank")
                    and resolved_lmr_parameters(engines[0], engines[0].get("ordering_profile"))
                    == resolved_lmr_parameters(engines[1], engines[1].get("ordering_profile"))
                )
            ),
            "evaluator comparison keeps effective LMR settings equal",
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
    require(
        type(a.get("disable_continuation_static_ordering", False)) is bool,
        "explicit alpha ordering selector",
    )
    book = document(plan["book"])
    require(
        book["complete"] is True and book["rules"] == plan["rules"],
        "complete bound book",
    )
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
    return [slot for slot in planned if slot["local_game"] in selected_ids], config


def planned_game_slice(experiment, schedule, plan, width=2):
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
        and count == width * len(families) * len(matchups),
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
            and slot["candidate_color"] in range(width),
            "typed unique planned slot",
        )
        colors.add((slot["matchup"], slot["family_id"], slot["candidate_color"]))
    require(len(colors) == count, "full family/colour coverage")
    covered = set()
    require(isinstance(plan["batches"], list) and bool(plan["batches"]), "declared batches")
    for i, batch in enumerate(plan["batches"]):
        require(
            set(batch)
            in (
                {"batch", "matchup", "config", "slots"},
                {"batch", "matchup", "config", "slots", "game_selection"},
            )
            and type(batch["batch"]) is int
            and batch["batch"] == i
            and type(batch["matchup"]) is int
            and batch["matchup"] in matchups
            and isinstance(batch["slots"], list)
            and batch["slots"]
            and len(batch["slots"]) % width == 0,
            "whole pair batch",
        )
        if batch.get("game_selection") is not None:
            require(width == 2, "selected playing batch")
            arena_game_ids(
                dict(games=len(batch["slots"]), arena=dict(game_selection=batch["game_selection"]))
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
            mate_id = batch["slots"][local ^ 1] if width == 2 else global_slot
            require(type(mate_id) is int and 0 <= mate_id < count, "pair slot")
            mate = schedule[mate_id]
            require(
                row["batch"] == i
                and row["matchup"] == batch["matchup"]
                and row["local_game"] == local
                and mate["family_id"] == row["family_id"]
                and (width == 1 or mate["candidate_color"] != row["candidate_color"]),
                "batch pair correspondence",
            )
    require(
        len(covered) == count
        and type(experiment.get("batch")) is int
        and 0 <= experiment["batch"] < len(plan["batches"]),
        "complete batch/planned coverage",
    )
    return [schedule[i] for i in plan["batches"][experiment["batch"]]["slots"]]


def arena_probcut_suffix(engine, counters, completed):
    """Match the configured FP32 pair to the worker's actual session, not its label."""
    keys = {
        "shallow_depth",
        "deep_depth",
        "slope",
        "intercept",
        "margin",
        "nonterminal_abs_bound",
        "terminal_utility",
        "calibration_sha256",
    }
    floats = (
        "slope",
        "intercept",
        "margin",
        "nonterminal_abs_bound",
        "terminal_utility",
    )

    def typed(p):
        require(isinstance(p, dict) and set(p) == keys, "complete arena ProbCut parameters")
        require(
            type(p["shallow_depth"]) is int
            and p["shallow_depth"] == 1
            and type(p["deep_depth"]) is int
            and p["deep_depth"] == 3,
            "arena ProbCut exact1/3",
        )
        q = dict(p)
        for k in floats:
            require(
                type(p[k]) in (int, float) and math.isfinite(p[k]),
                "finite arena ProbCut",
            )
            try:
                q[k] = struct.unpack(">f", struct.pack(">f", p[k]))[0]
            except (OverflowError, struct.error) as error:
                raise Refused("arena ProbCut FP32 range") from error
            require(math.isfinite(q[k]), "finite typed arena ProbCut")
        require(
            q["slope"] > 0
            and q["margin"] >= 0
            and struct.pack(">f", q["nonterminal_abs_bound"]) == struct.pack(">f", 1.0)
            and struct.pack(">f", q["terminal_utility"]) == struct.pack(">f", 2.0)
            and isinstance(q["calibration_sha256"], str)
            and len(q["calibration_sha256"]) == 64
            and all(c in "0123456789abcdefABCDEF" for c in q["calibration_sha256"]),
            "arena ProbCut actual legacy domain and calibration hash",
        )
        return q

    configured = engine.get("probcut")
    require(
        "probcut" not in engine or configured is not None,
        "absence alone is arena ProbCut OFF",
    )
    require(
        "requested_probcut" in counters and "actual_probcut" in counters,
        "native requested/effective arena ProbCut record",
    )
    if configured is None:
        require(
            counters["requested_probcut"] is None and counters["actual_probcut"] is None,
            "arena ProbCut OFF requested/effective",
        )
        suffix = ""
    else:
        expected = typed(configured)
        for name in ("requested_probcut", "actual_probcut"):
            actual = typed(counters[name])
            require(
                actual == expected
                and all(
                    struct.pack(">f", actual[k]) == struct.pack(">f", expected[k]) for k in floats
                ),
                "configured/actual arena ProbCut FP32 correspondence",
            )
        suffix = (
            ":probcut13-v1:"
            + ":".join(struct.pack(">f", expected[k]).hex() for k in floats)
            + ":"
            + expected["calibration_sha256"]
        )
    for index, work in enumerate((counters.get("whole_search"), completed)):
        # An absent completed snapshot is truthful only on the existing fallback route.
        if work is None and (
            configured is None
            or (
                index == 1
                and counters.get("selection_reason") == "legal_fallback_no_completed_iteration"
            )
        ):
            continue
        require(isinstance(work, dict), "actual completed/terminal arena work")
        if configured is None:
            require("probcut" not in work, "OFF arena cannot publish ProbCut work")
        else:
            report = work.get("probcut")
            require(isinstance(report, dict), "ON arena must report actual ProbCut work")
            names = (
                "eligible_after_TT",
                "matching_nonPV_after_TT",
                "threshold_outside_domain",
                "shallow_probes",
                "shallow_nodes",
                "shallow_evaluations",
                "predicted_cuts_ALL",
                "probe_aborts",
                "terminal_probe_rejects",
                "diagnostic_explicit_child_calls",
                "diagnostic_nodes_in_parent_budget",
                "diagnostic_evaluations",
            )
            require(
                all(type(report.get(k)) is int and report[k] >= 0 for k in names)
                and report.get("samples") == []
                and report["diagnostic_explicit_child_calls"] == 0
                and report["diagnostic_nodes_in_parent_budget"] == 0
                and report["diagnostic_evaluations"] == 0,
                "arena ProbCut counters without calibration references",
            )
    return suffix


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
        if config["engines"][index]["kind"] == "claustrophobia":
            settings = config["engines"][index]["claustrophobia"]
            counters = obs["counters"]
            require(
                type(obs["deadline_ns"]) is int
                and obs["admission_checked_ns"] < obs["deadline_ns"]
                and obs["completed_depth"] is None
                and obs["pv"] == []
                and counters["direct_child_reaped"] is True
                and counters["secondary"] == []
                and counters["authority_legal"] is True
                and type(counters["completed_simulations"]) is int
                and counters["completed_simulations"] == settings["simulations"]
                and type(counters["head_calls"]) is int
                and 0 < counters["head_calls"] <= settings["max_head_calls"],
                "original Claustrophobia completed call/clock/direct cleanup",
            )
            accepted.append(obs["action"])
            continue
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
        counters = obs["counters"]
        engine = config["engines"][index]
        probcut_suffix = (
            arena_probcut_suffix(engine, counters, obs.get("completed_iteration_counters"))
            if "probcut" in engine
            or "requested_probcut" in counters
            or "actual_probcut" in counters
            or any(
                isinstance(work, dict) and "probcut" in work
                for work in (
                    counters.get("whole_search"),
                    obs.get("completed_iteration_counters"),
                )
            )
            else ""
        )
        if engine.get("ordering_profile") is not None:
            method = counters.get("actual_search_namespace")
            require(
                isinstance(method, dict)
                and set(method) == {"evaluator", "rules", "selectivity"}
                and all(isinstance(v, str) and v for v in method.values())
                and method["rules"] == "research-standard-2p-threefold-goal-first-v1"
                and method["evaluator"]
                in {
                    kind
                    + ":sha256:"
                    + a["evaluator_sha256"][index]
                    + ":simd="
                    + str(engine["simd"]).lower()
                    + probcut_suffix
                    for kind in {
                        "distance": ("distance-tanh-f32",),
                        "nnue": ("nnue-f32", "nnue-residual-f32"),
                        "nnue_quantized": ("nnue-i16",),
                        "sigma_value": ("sigma-value-onnx-cpu",),
                    }.get(engine["kind"], ())
                }
                # The native typed factory and report validator own exact namespace/ID
                # correspondence. Do not duplicate AI method suffixes in this reader.
                and counters.get("requested_lmr_method")
                == (
                    engine.get("lmr_method")
                    if engine.get("lmr_method") is not None
                    else "depth_rank"
                )
                and (
                    all(
                        isinstance(counters.get(k), str) and counters[k]
                        for k in ("actual_lmr_method_id", "lmr_reduction_rule")
                    )
                    if engine.get("lmr", False)
                    else all(
                        k in counters and counters[k] is None
                        for k in ("actual_lmr_method_id", "lmr_reduction_rule")
                    )
                )
                and counters.get("requested_lmr_parameters") == engine.get("lmr_parameters")
                and "actual_lmr_parameters" in counters
                and counters["actual_lmr_parameters"]
                == (
                    resolved_lmr_parameters(engine, engine.get("ordering_profile"))
                    if engine.get("lmr", False)
                    and engine.get("lmr_method", "depth_rank") == "depth_rank"
                    else None
                )
                and type(counters.get("actual_lmr_enabled")) is bool
                and counters["actual_lmr_enabled"] == engine.get("lmr", False),
                "configured/actual arena ordering-LMR method correspondence",
            )
        if engine["kind"] != "mcts":
            enabled = (a["comparison"] != "functional") and engine.get(
                "zero_stock_safe_race"
            ) is not False
            require(
                counters.get("actual_zero_stock_safe_race_enabled") is enabled
                and counters.get("requested_zero_stock_safe_race_method")
                == (
                    engine.get("zero_stock_safe_race_method")
                    or ("manhattan" if a["comparison"] == "functional" else "path_tail")
                )
                and (
                    isinstance(counters.get("actual_zero_stock_safe_race_method_id"), str)
                    and bool(counters["actual_zero_stock_safe_race_method_id"])
                    if enabled
                    else counters.get("actual_zero_stock_safe_race_method_id") is None
                ),
                "configured/actual safe-race method correspondence",
            )
        fallback = (
            a["comparison"] == "whole_wall_time"
            or (
                a["comparison"] == "search_wall_time"
                and config.get("management_cpu_core") is not None
            )
        ) and counters.get("selection_reason") == "legal_fallback_no_completed_iteration"
        require(
            counters["completed_snapshot_validation_failed"] is False
            and (
                (
                    obs["completed_depth"] is None
                    and obs["value_stm"] is None
                    and obs["pv"] == []
                    and obs["last_completed_iteration_ns"] is None
                    and obs["completed_iteration_counters"] is None
                )
                if fallback
                else (
                    obs["pv"]
                    and obs["pv"][0] == obs["action"]
                    and type(obs["completed_depth"]) is int
                    and obs["completed_depth"] > 0
                    and obs["value_stm"] is not None
                )
            ),
            "alpha completion/PV or truthful zero-work fallback",
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
            receipt = counters["authority_receipt_ns"]
            require(
                type(receipt) is int
                and type(obs["deadline_ns"]) is int
                and receipt < obs["deadline_ns"]
                and counters["drain_finished_ns"] == obs["returned_ns"]
                and (
                    (obs["returned_ns"] >= receipt and counters["inflight_after_drain"] == 0)
                    if (
                        a["comparison"] == "whole_wall_time"
                        or (
                            a["comparison"] == "search_wall_time"
                            and config.get("management_cpu_core") is not None
                        )
                    )
                    else obs["returned_ns"] == receipt
                ),
                "main receipt/terminal drain",
            )
        accepted.append(obs["action"])
    if not config["arena"].get("decision_only", False):
        opening = config["arena"]["book"]["openings"][row["game"] // 2]["prefix"]
        require(
            row["moves"][: len(opening)] == opening and accepted == row["moves"][len(opening) :],
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
        values = {name: read_ref(files[name], files[name]["bytes"]) for name in required}
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
    selected_ids = arena_game_ids(config)
    count = len(selected_ids)
    cap = config["arena"].get("retained_outcome_bytes") or config["max_plies"] * 16384 + 16384
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
            type(game) is int and game in selected_ids and game not in seen,
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
    if any(engine["kind"] == "claustrophobia" for engine in config["engines"]):
        require(
            type(config.get("management_cpu_core")) is int and config["management_cpu_core"] >= 0,
            "explicit Claustrophobia main CPU owner required",
        )
    if config.get("management_cpu_core") is not None:
        execution = manifest["binding"].get("execution", {})
        require(
            execution.get("main_pid") == execution.get("main_tid") == report["process_id"]
            and execution.get("management_core")
            == execution.get("management_core_observed")
            == config["management_cpu_core"]
            and execution.get("AI_cores") == config["cpu_cores"]
            and execution.get("AI_workers") == len(config["engines"])
            and execution.get("simultaneous_games") == 1
            and execution.get("inference_pump") is False,
            "actual process main and fixed AI owners, from the emitted runtime record",
        )
        for row in rows:
            for observation in row["observations"]:
                if not observation["accepted"]:
                    continue
                counters = observation["counters"]
                if config["engines"][observation["engine_index"]]["kind"] == "claustrophobia":
                    child = counters.get("child_pid")
                    execution = counters.get("child_execution")
                    require(
                        type(report["process_id"]) is int
                        and report["process_id"] > 0
                        and type(child) is int
                        and child > 0
                        and child != report["process_id"]
                        and type(counters.get("child_parent_pid")) is int
                        and counters["child_parent_pid"] == report["process_id"]
                        and type(counters.get("authority_tid_at_start")) is int
                        and counters["authority_tid_at_start"] == report["process_id"]
                        and type(counters.get("authority_tid")) is int
                        and counters["authority_tid"] == report["process_id"]
                        and type(counters.get("authority_core_at_start")) is int
                        and counters["authority_core_at_start"] == config["management_cpu_core"]
                        and type(counters.get("authority_core")) is int
                        and counters["authority_core"] == config["management_cpu_core"]
                        and isinstance(execution, dict)
                        and set(execution) == {"started", "returned"},
                        "actual Claustrophobia main/direct-child ownership required",
                    )
                    core = config["cpu_cores"][observation["engine_index"]]
                    for point in (execution["started"], execution["returned"]):
                        require(
                            isinstance(point, dict)
                            and set(point) == {"pid", "ppid", "tid", "core", "affinity"}
                            and all(type(point[k]) is int for k in ("pid", "ppid", "tid", "core"))
                            and point["pid"] == point["tid"] == child
                            and point["ppid"] == report["process_id"]
                            and point["core"] == core
                            and isinstance(point["affinity"], list)
                            and len(point["affinity"]) == 1
                            and type(point["affinity"][0]) is int
                            and point["affinity"] == [core],
                            "self-observed Claustrophobia child identity/core points",
                        )
                    times = [
                        observation["caller_started_ns"],
                        counters.get("child_handle_acquired_ns"),
                        counters.get("child_reaped_ns"),
                        counters.get("child_pipes_drained_ns"),
                        observation["returned_ns"],
                    ]
                    require(
                        all(type(t) is int and t >= 0 for t in times)
                        and times == sorted(times)
                        and counters.get("direct_child_reaped") is True
                        and type(counters.get("exit_code")) is int
                        and counters["exit_code"] == 0
                        and counters.get("secondary") == []
                        and counters.get("child_stdout_eof") is True
                        and counters.get("child_stderr_eof") is True
                        and type(counters.get("inflight_after_drain")) is int
                        and counters["inflight_after_drain"] == 0
                        and type(counters.get("authority_receipt_ns")) is int
                        and counters["authority_receipt_ns"] == observation["returned_ns"]
                        and type(counters.get("drain_finished_ns")) is int
                        and counters["drain_finished_ns"] == observation["returned_ns"]
                        and counters.get("initialization_in_clock") is True
                        and counters.get("fresh_search_and_model_per_turn") is True
                        and observation["stop"] == "completed_upstream_call"
                        and observation["completed_depth"] is None
                        and "last_completed_iteration_ns" in observation
                        and observation["last_completed_iteration_ns"] is None
                        and "completed_iteration_counters" in observation
                        and observation["completed_iteration_counters"] is None,
                        "Claustrophobia whole-caller completion/reap/drain, not depth callbacks",
                    )
                    continue
                require(
                    counters.get("authority_tid") == report["process_id"]
                    and counters.get("authority_core") == config["management_cpu_core"]
                    and counters.get("AI_worker_core")
                    == config["cpu_cores"][observation["engine_index"]]
                    and type(counters.get("AI_worker_tid")) is int
                    and counters["AI_worker_tid"] != report["process_id"]
                    and counters.get("matching_terminal_collected") is True
                    and type(counters.get("AI_terminal_finished_ns")) is int
                    and counters["AI_terminal_finished_ns"]
                    <= counters["terminal_collected_ns"]
                    <= observation["returned_ns"],
                    "actual AI/main CPU ownership and matching terminal chronology",
                )
    # Match ArenaConfig's two default=false/skip_serializing_if=false_flag fields.
    # All true values and every other declared field remain exact.
    serialized_config = copy.deepcopy(config)
    # Config serde emits these defaults even when the declared field is omitted.
    # Explicit values (including null/conflicts) remain subject to full equality.
    for field, default in {
        "cycle": None,
        "deadline_unix_ms": 0,
        "train_games": None,
        "validation_games": None,
        "mcts_max_bytes": 268435456,
        "mcts_max_nodes": 200000,
        "pause_file": None,
        "simulations": 64,
        "temperature": 1.0,
    }.items():
        serialized_config.setdefault(field, default)
    for flag in ("disable_continuation_static_ordering", "decision_only"):
        if serialized_config["arena"].get(flag) is False:
            del serialized_config["arena"][flag]
    require(
        manifest["result"] == publication
        and manifest["binding"]["config"] == serialized_config
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
            manifest["binding"]["executable_sha256"] == expected_build["artifact"]["sha256"],
            "actual current image publication",
        )
    report["outcomes"] = sorted(rows, key=lambda row: row["game"])
    return report


def diagnostic_proposal(slot, obs, engine):
    """Metric role follows the declared engine, never an arbitrary matchup ID."""
    sigma = engine["kind"] == "mcts"
    return {
        "slot": slot["slot"],
        "engine": slot["matchup"],
        "kind": engine["kind"],
        "action": obs["action"],
        "PV": obs["pv"],
        "accepted_depth": obs["completed_depth"],
        "stop": obs["stop"],
        "searched_value_stm": None if sigma else obs["value_stm"],
        "value_role": "Sigma rootmean" if sigma else "alpha searched root; not NNUE static",
        "Sigma_root_nn": obs["counters"].get("root_nn"),
        "Sigma_rootmean": obs["counters"].get("root_mean"),
        "Sigma_selected_child_q": obs["counters"].get("selected_child_q"),
        "counters": obs["counters"],
        "NNUE_static_pretanh": None,
        "NNUE_static_posttanh": None,
        "NNUE_saturation": None,
        "missing_metric_reason": "not recorded by admitted same-forward path; searched/terminal values are not NNUE static outputs",
    }


def interval_tail(interval):
    require(
        isinstance(interval, str) and interval.endswith("%"),
        "central interval percentage",
    )
    try:
        central = Fraction(interval[:-1]) / 100
    except (ValueError, ZeroDivisionError) as error:
        raise Refused("finite central interval percentage") from error
    require(0 < central < 1, "central interval strictly between0 and100 percent")
    return (1 - central) / 2


def arena_analysis_check(spec, experiment):
    config = document(experiment["config"])
    require(
        set(config) - {"linked_examples_limit"}
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
        and type(config["bootstrap_resamples"]) is int
        and config["bootstrap_resamples"] > 0
        and type(config["bootstrap_seed"]) is int
        and 0 <= config["bootstrap_seed"] < 2**64
        and experiment["batch"] is None,
        "selected family analysis settings/authority",
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
    interval_tail(config["central_interval"])
    require(
        type(config.get("linked_examples_limit", 12)) is int
        and config.get("linked_examples_limit", 12) >= 0,
        "linked example retention count",
    )
    plan = approved_plan(spec, experiment)
    require(
        plan == document(config["arena_plan"])
        and plan["phase"] == "arena"
        and experiment["planned_slots"] == plan["planned_slots"]
        and experiment["schedule"] == plan["schedule"],
        "selected arena analysis correspondence",
    )
    planned_game_slice(
        {"planned_slots": plan["planned_slots"], "batch": 0},
        document(plan["schedule"]),
        plan,
    )

    def census(items, selected):
        require(
            isinstance(items, list)
            and len(items) == len(selected["batches"])
            and all(type(i.get("batch")) is int for i in items)
            and {i["batch"] for i in items} == set(range(len(selected["batches"]))),
            "one census descriptor per planned batch",
        )

    census(config["batches"], plan)
    if config["decision_plan"] is not None:
        dplan = document(config["decision_plan"])
        require(
            dplan["phase"] == "compare" and config["diagnostic_selection"] is not None,
            "declared diagnostic plan/selection",
        )
        planned_game_slice(
            {"planned_slots": dplan["planned_slots"], "batch": 0},
            document(dplan["schedule"]),
            dplan,
            width=1,
        )
        census(config["decision_batches"], dplan)
        selection = document(config["diagnostic_selection"])
        require(
            selection["selected_before_outputs"] is True
            and len(selection["parents"]) == len(dplan["family_ids"]),
            "declared diagnostic selection flag/count; parent correspondence unverified",
        )
    else:
        require(
            config["decision_batches"] == [] and config["diagnostic_selection"] is None,
            "no unapproved diagnostic branch",
        )
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
                    and not Path(item["completion"]["path"]).with_name("INCOMPLETE").exists(),
                    "original sole authoritative completion required",
                )
                selected(completed["experiment"])
                selected(completed["intent"])
                producer = document(completed["experiment"])
                selected(producer["config"])
                if producer["build_manifest"] != experiment["build_manifest"]:
                    selected(producer["build_manifest"])
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


def arena_score_tables(plan, schedule, observed, config):
    """Colour-pair counts and selected conditional family resampling, NN0."""
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
        for family in plan["family_ids"]:
            values = []
            for slot in (
                r for r in schedule if r["matchup"] == m["id"] and r["family_id"] == family
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
        require(counts["planned"] == 2 * len(plan["family_ids"]), "full matchup denominator")
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
                    sum(scores) / counts["planned"],
                    (sum(scores) + counts["unknown"]) / counts["planned"],
                ],
            }
        )
    samples = {m["id"]: [] for m in plan["matchups"]}
    empty = {key: 0 for key in samples}
    rng = random.Random(config["bootstrap_seed"])
    for _ in range(config["bootstrap_resamples"]):
        indices = [rng.randrange(len(plan["family_ids"])) for _ in plan["family_ids"]]
        for key, values in pair_scores.items():
            known = [values[i] for i in indices if values[i] is not None]
            if known:
                samples[key].append(sum(known) / len(known))
            else:
                empty[key] += 1
    for table in tables:
        values = sorted(samples[table["matchup"]])
        table["empty_family_resamples"] = empty[table["matchup"]]
        unavailable = (
            "fewer_than_two_complete_colour_pairs"
            if table["complete_colour_pairs"] < 2
            else "empty_family_resample"
            if len(values) != config["bootstrap_resamples"]
            else None
        )
        table["conditional_interval_unavailable_reason"] = unavailable
        table["conditional_complete_pair_interval"] = (
            None
            if unavailable is not None
            else [
                values[math.floor((len(values) - 1) * interval_tail(config["central_interval"]))],
                values[
                    math.ceil((len(values) - 1) * (1 - interval_tail(config["central_interval"])))
                ],
            ]
        )
    return tables


def arena_analysis(spec, experiment):
    config = arena_analysis_check(spec, experiment)
    plan = document(config["arena_plan"])
    schedule = document(plan["schedule"])
    selection = (
        document(config["diagnostic_selection"])
        if config["diagnostic_selection"] is not None
        else {"exclusions": []}
    )
    decision_plan = (
        document(config["decision_plan"]) if config["decision_plan"] is not None else None
    )
    decisions = document(decision_plan["schedule"]) if decision_plan is not None else []
    diagnostic_engines = (
        {m["id"]: m["engines"][0] for m in decision_plan["matchups"]}
        if decision_plan is not None
        else {}
    )
    result = {
        "schema": "quoridor.arena-comparison.summary.v1",
        "planned": plan["planned_slots"],
        "bootstrap_resamples": config["bootstrap_resamples"],
        "bootstrap_seed": config["bootstrap_seed"],
        "central_interval": config["central_interval"],
        "operation_provenance": [],
        "errors": [],
        "diagnostic_selection": config["diagnostic_selection"],
        "diagnostic_selection_relation": "OPAQUE_UNVERIFIED"
        if config["diagnostic_selection"] is not None
        else None,
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
    if config["diagnostic_selection"] is not None:
        result["limitations"].append(
            "Diagnostic selection reference has pre-output flag/count checks only; "
            "its parent correspondence is opaque/unverified. Actual proposals retain "
            "the admitted decision book/config full-history authority."
        )
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
                    "producer_build": e["build_manifest"],
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
                    and approved_plan(origin, e) == document(approved)
                    and e["canonical_plan_sha256"] == approved["sha256"]
                    and origin["experiment"] == completion["experiment"]
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
                        "canonical_compressed_bytes": pub["archive"]["compressed"]["bytes"],
                        "canonical_raw_bytes": pub["archive"]["raw_bytes"],
                        "canonical_allocated_bytes": pub["archive_allocated_bytes"],
                        "compression_ratio_raw_over_compressed": pub["archive"]["raw_bytes"]
                        / pub["archive"]["compressed"]["bytes"],
                        "native_peak_rss_observation_bytes": native["peak_rss"],
                        "evaluator_setup_seconds": native["pump"][
                            "evaluator_initialization_seconds"
                        ],
                        "backend_setup_seconds": native["pump"]["backend_initialization_seconds"],
                        "backend_cleanup_seconds": native["pump"]["backend_cleanup_seconds"],
                        "thinking_seconds": sum(
                            o["thinking_seconds"] or 0
                            for row in native["outcomes"]
                            for o in row["observations"]
                        ),
                        "classification_seconds": sum(
                            o["counters"].get("parent_traits", {}).get("classification_seconds", 0)
                            for row in native["outcomes"]
                            for o in row["observations"]
                        ),
                        "scope": "nested source spans, not additive all-work fees; continuous working set/worker UTC STOP UNKNOWN",
                    }
                )
                for row in native["outcomes"]:
                    slot = next(slot for slot in planned if slot["local_game"] == row["game"])
                    require(
                        slot["slot"] not in target
                        and row["candidate_color"] == slot["candidate_color"],
                        "unique global scheduled outcome",
                    )
                    width = 2 if phase == "arena" else 1
                    require(
                        row["family"] == f"{c['run_id']}-family-{row['game'] // width:06}",
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
                result["errors"].append({"completion": item["completion"], **error_fact(error)})

    consume(config["batches"], config["arena_plan"], "arena", observed)
    if decision_plan is not None:
        consume(
            config["decision_batches"],
            config["decision_plan"],
            "compare",
            decision_rows,
        )
    tables = arena_score_tables(plan, schedule, observed, config)
    result["matchups"] = tables
    # Per-state rows are correlated exposures. Every cell retains game/family/colour denominators.
    for global_slot, (row, c) in observed.items():
        slot = schedule[global_slot]
        for observation in row["observations"]:
            traits = observation.get("counters", {}).get("parent_traits")
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
            **{k: len(v) if isinstance(v, set) else v for k, v in cell.items() if k != "by_colour"},
            "by_colour": {
                str(side): {k: len(v) if isinstance(v, set) else v for k, v in counts.items()}
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
        if row["status"] != "decision" or observation is None or not observation["accepted"]:
            diagnostic_counts["unknown"] += 1
            continue
        diagnostic_counts["proposed"] += 1
        by_parent.setdefault(slot["family_id"], []).append((slot, observation))
    disagreements = 0
    complete = 0
    for parent, rows in sorted(by_parent.items()):
        if {slot["matchup"] for slot, _ in rows} != set(diagnostic_engines):
            continue
        complete += 1
        if len({obs["action"] for _, obs in rows}) > 1:
            disagreements += 1
            if len(examples) < config.get("linked_examples_limit", 12):
                examples.append(
                    {
                        "parent": parent,
                        "selection": config["diagnostic_selection"],
                        "selection_relation": result["diagnostic_selection_relation"],
                        "proposals": [
                            diagnostic_proposal(slot, obs, diagnostic_engines[slot["matchup"]])
                            for slot, obs in rows
                        ],
                    }
                )
    diagnostic_strata = {}
    for parent, rows in sorted(by_parent.items()):
        if {slot["matchup"] for slot, _ in rows} != set(diagnostic_engines):
            continue
        traits = rows[0][1]["counters"].get("parent_traits")
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
        "complete_all_engine_parents": complete,
        "engine_ids": list(diagnostic_engines),
        "action_disagreement_parents": disagreements,
        "linked_examples": examples,
        "NNUE_pretanh_posttanh_saturation": "UNKNOWN_NOT_RECORDED_NO_EXTRA_FORWARD",
    }
    report = [
        "Configured arena comparison",
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
        f"Common parents with all configured proposals: {complete}; action disagreements: {disagreements}.",
        "",
        *result["limitations"],
    ]
    return result, "\n".join(report) + "\n"


def arena_analysis_child(experiment_path, expected_sha):
    path = os.environ["QUORIDOR_LIFECYCLE_INTENT_PATH"]
    ref, _ = bound(path)
    require(ref["sha256"] == os.environ["QUORIDOR_LIFECYCLE_INTENT"], "actual parent intent")
    spec = document(ref)
    require(
        os.environ["QUORIDOR_LIFECYCLE_PARENT_PID"] == str(os.getppid()) and os.getppid() > 1,
        "actual immediate parent; no second lifetime lock",
    )
    require(
        spec["experiment"]["path"] == str(experiment_path)
        and spec["experiment"]["sha256"] == expected_sha,
        "exact analysis Experiment",
    )
    require(
        spec["argv"]
        == [os.fsdecode(v) for v in Path("/proc/self/cmdline").read_bytes().split(b"\0") if v],
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
            if (experiment["phase"] == "materialize" and item["name"] in COMPACT_CACHE_WIDTHS) or (
                experiment["phase"] == "corpus" and item["name"] == "pilot_stream"
            ):
                ref = artifact_ref(item["path"])
                require(ref["bytes"] <= item["limit_B"], "declared streamed output size")
                data["files"].append(ref)
            else:
                ref, raw = bound(item["path"], item["limit_B"])
                data["files"].append(ref)
                values[item["name"]] = raw
        except BaseException as error:
            data["errors"].append({"stage": item["name"], **error_fact(error)})
    if experiment["argv"][1] == "measure":
        try:
            data["measurement"] = measurement_evidence(
                spec, experiment, values, files=data["files"]
            )
        except BaseException as error:
            data["errors"].append({"stage": "measurement_records", **error_fact(error)})
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
                    metadata["schema"] == ARENA_PUBLICATION and metadata["closed_archive"] is False,
                    "typed retained publication failure",
                )
                data["publication_failure"] = metadata
                data["errors"].append(
                    {
                        "stage": "native_archive_publication",
                        "type": "NativePublicationFailure",
                        "message": metadata["report"]["stopped"],
                        "secondary": metadata["report"]["pump"].get("publication_failures", []),
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
                cap = c["arena"].get("retained_outcome_bytes") or c["max_plies"] * 16384 + 16384
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
                data["errors"].append({"stage": "live_journal_failure", **error_fact(error)})
    if (
        experiment["phase"] == "analysis"
        and len(experiment["argv"]) > 3
        and experiment["argv"][3] == "arena-analysis"
    ):
        try:
            summary = json.loads(values["summary"])
            selected = arena_analysis_check(spec, experiment)
            plan = document(selected["arena_plan"])
            decisions = (
                document(selected["decision_plan"])
                if selected["decision_plan"] is not None
                else None
            )
            require(
                summary["schema"] == "quoridor.arena-comparison.summary.v1"
                and summary["planned"] == plan["planned_slots"]
                and len(summary["matchups"]) == len(plan["matchups"])
                and {t["matchup"] for t in summary["matchups"]}
                == {m["id"] for m in plan["matchups"]}
                and all(
                    t["counts"]["planned"] == 2 * len(plan["family_ids"])
                    for t in summary["matchups"]
                )
                and summary["diagnostic_planned"]
                == (decisions["planned_slots"] if decisions else 0)
                and all(
                    summary[k] == selected[k]
                    for k in (
                        "bootstrap_seed",
                        "bootstrap_resamples",
                        "central_interval",
                    )
                ),
                "full conditional saved-analysis census",
            )
            data["scope"] = (
                "conditional/descriptive fixed analysis; native/model/default scientific scope unchanged"
            )
        except BaseException as error:
            data["errors"].append({"stage": "arena_analysis", **error_fact(error)})
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
            selected_ids = [x["local_game"] for x in planned]
            data["missing_local_games"] = selected_ids.copy()
            data["planned_global_slots"] = [x["slot"] for x in planned]
            config = document(experiment["config"])
            files = {
                item["name"]: next(ref for ref in data["files"] if ref["path"] == item["path"])
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
                    and game in selected_ids
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
                require(
                    row["status"] in {"goal", "forfeit", "draw", "unknown"},
                    "typed outcome",
                )
                arena_observation(config, row)
                records.append(row)
                data["observed_local_games"].append(game)
                data["missing_local_games"] = sorted(
                    set(selected_ids) - set(data["observed_local_games"])
                )
            data["missing_local_games"] = sorted(
                set(selected_ids) - set(data["observed_local_games"])
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
            planned, config = arena_decision_plan_check(experiment, approved_plan(spec, experiment))
            data["missing_local_games"] = list(range(len(planned)))
            files = {
                item["name"]: next(ref for ref in data["files"] if ref["path"] == item["path"])
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
                    and row["moves"] == config["arena"]["book"]["openings"][game]["prefix"]
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
                    receipt["status"] == "PASS"
                    and not receipt.get("failures")
                    and not receipt.get("errors"),
                    "affected software failed",
                )
                data["scope"] = "software-only; no corpus or numerical PASS"
            elif experiment["phase"] == "fit":
                state = json.loads(
                    values["run_status"] if "run_status" in values else values["training"]
                )
                require(
                    state["status"] in {"COMPLETE", "COMPLETED", "EARLY_STOPPED"}
                    and state.get("fault") is None,
                    "actual training did not complete",
                )
                data["fit"] = {
                    key: state[key]
                    for key in (
                        "status",
                        "step",
                        "forward_rows",
                        "aggregate_forward_rows",
                        "added_seen",
                        "public_seen",
                        "best_step",
                        "last_step",
                    )
                    if key in state
                }
                for key in (
                    "step",
                    "forward_rows",
                    "aggregate_forward_rows",
                    "added_seen",
                    "public_seen",
                ):
                    if key in data["fit"]:
                        require(
                            type(data["fit"][key]) is int and data["fit"][key] >= 0,
                            "actual nonnegative training counter " + key,
                        )
                data["scope"] = (
                    "actual configured training; absent counters remain unknown; no strength/default claim"
                )
            else:
                report = json.loads(values["generation_result"])
                require(
                    type(report["scheduled"]) is int
                    and type(report["recorded"]) is int
                    and 0 <= report["recorded"] <= report["scheduled"],
                    "actual generation census",
                )
                data["corpus"] = {
                    key: report[key]
                    for key in (
                        "scheduled",
                        "recorded",
                        "goals",
                        "draws",
                        "unknown",
                        "search_nodes",
                    )
                    if key in report
                }
                data["planned_slots"] = experiment["planned_slots"]
                data["scope"] = (
                    "actual completed-depth generation; partial/UNKNOWN retained without refill"
                )
                if "cache_manifest" in values:
                    cache = json.loads(values["cache_manifest"])
                    require(
                        cache["stream_intake"]["status"] == "complete",
                        "atomic cache intake",
                    )
                if "stream_content" in values:
                    content = json.loads(values["stream_content"])
                    ref = content["compressed"]
                    require(
                        artifact_ref(ref["path"]) == ref,
                        "canonical corpus stream identity drift",
                    )
                    data["canonical_compressed_source"] = ref
                    data["raw_content_sha256"] = content["raw_sha256"]
                    data["raw_content_B"] = content["raw_bytes"]
        except BaseException as error:
            data["errors"].append({"stage": "common_study_data", **error_fact(error)})

    if (
        experiment["phase"] == "materialize"
        and document(experiment["build_manifest"]).get("artifact_target") == "terminal-cache"
    ):
        try:
            cache = json.loads(values["cache_manifest"])
            request = document(experiment["config"])
            streams = request["streams"]
            lineage = [{k: ref[k] for k in ("path", "sha256")} for ref in streams]
            require(
                not (Path(spec["data_root"]) / "intake-incomplete.json").exists()
                and cache["schema"] == "quoridor-common-corpus-terminal-geometry-v3"
                and cache["stream_intake"]["status"] == "complete"
                and cache["stream_intake"]["scope"] == "common-corpus"
                and cache["source_binding"] == lineage
                and isinstance(cache["source_content"], list)
                and len(cache["source_content"]) == len(streams)
                and all(
                    (
                        content.get("encoding") == "native-teacher-dataset-shards-v1"
                        and content.get("manifest") == {k: ref[k] for k in ("path", "sha256")}
                    )
                    if request.get("mcts_configs") is not None
                    else (
                        content["compressed"] == ref
                        and content["encoding"] == "gzip-single-member-v1"
                    )
                    for content, ref in zip(cache["source_content"], streams, strict=True)
                )
                and type(cache["rows"]) is int
                and cache["rows"] >= 0,
                "complete saved cache with actual ordered stream lineage",
            )
            mcts = request.get("mcts_configs")
            if mcts is not None:
                datasets = cache["mcts_datasets"]
                require(
                    cache["mcts_native_configs"] == {k: mcts[k] for k in ("path", "sha256")}
                    and cache["dataset_sha"] == mcts["sha256"]
                    and cache["common_corpus"]["rootmean_is_raw"] is True
                    and isinstance(datasets, list)
                    and len(datasets) == len(streams)
                    and all(
                        d["dataset"] == str(Path(ref["path"]).parent)
                        and d["manifest_sha256"] == ref["sha256"]
                        and type(d["rows"]) is int
                        and d["rows"] >= 0
                        for d, ref in zip(datasets, streams, strict=True)
                    )
                    and sum(d["rows"] for d in datasets) == cache["rows"],
                    "honest native MCTS list-file and dataset manifest lineage",
                )
            require(
                cache["files"] == {n: n for n in COMPACT_CACHE_WIDTHS}
                and set(cache["sha256"]) == set(cache["file_bytes"]) == set(COMPACT_CACHE_WIDTHS),
                "closed compact physical files",
            )
            refs = {Path(ref["path"]).name: ref for ref in data["files"]}
            for name, width in COMPACT_CACHE_WIDTHS.items():
                ref = refs[name]
                require(
                    ref["bytes"] == cache["rows"] * width == cache["file_bytes"][name]
                    and ref["sha256"] == cache["sha256"][name],
                    "actual compact byte/hash/count",
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


def remove_empty_owned_tmp(path, owner, guardian_return, *, exception_outcome=None):
    """Remove only empty owned directories after the actual child and handles closed."""
    path = owned(path, owner)
    if guardian_return is None:
        require(
            isinstance(exception_outcome, dict) and exception_outcome.get("normal_return") is False,
            "owned TMP cleanup requires actual exception cleanup transport",
        )
        guardian_return = exception_outcome.get("record")
        require(
            isinstance(guardian_return, dict)
            and guardian_return.get("signal_mask_restoration") == "completed"
            and guardian_return.get("final_record_persist") == "completed"
            and guardian_return.get("finalization_errors", []) == [],
            "exception guardian finalization incomplete",
        )
    require(
        isinstance(guardian_return, dict)
        and guardian_return.get("direct_child_reaped") is True
        and guardian_return.get("process_cleanup_complete") is True
        and guardian_return.get("handle_closes_complete") is True
        and guardian_return.get("remaining") == [],
        "owned TMP cleanup requires returned child/handle closure",
    )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

    def drain(directory):
        for name in os.listdir(directory):
            child = os.open(name, flags, dir_fd=directory)
            try:
                drain(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=directory)

    parent = os.open(path.parent, flags)
    try:
        directory = os.open(path.name, flags, dir_fd=parent)
        try:
            drain(directory)
        finally:
            os.close(directory)
        os.rmdir(path.name, dir_fd=parent)
    finally:
        os.close(parent)


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
        plan = guard(spec)
        with operation_lease(spec, lock):
            resources = resource_factory(spec)
            resources.cpu_plan = plan
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
                        read_ref(tool["file"], max(CONTROL_BYTES, tool["file"]["bytes"]))
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
                            private_copy_check(spec, src, resources=resources)
                            result["cargo_artifact"] = matches[0]
                            candidate = copy_artifact(src, spec["private"], resources=resources)
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
                    if (
                        experiment["phase"] == "arena"
                        or (
                            experiment["phase"] == "compare"
                            and experiment["argv"][1] == "decisions"
                        )
                        or experiment["argv"][1] == "measure"
                    ) and spec.get("TMP") is not None:
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
                    if result["data"].get("measurement") is not None:
                        try:
                            origin = result["data"]["measurement"]["runtime_launch_origin"]
                            direct = result["checks"][-1]["guardian_return"]["child"]
                            expected = (
                                origin["profiler"]
                                if spec.get("perf") is not None
                                else origin["native"]
                            )
                            require(
                                direct == expected
                                and origin["guardian"] == result["originating_job"]["child"],
                                "measurement native origin joins actual guardian directchild identity",
                            )
                        except BaseException as error:
                            if run_error is None:
                                run_error = error
                            else:
                                run_error.add_note("measurement origin secondary: " + repr(error))
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
                    if spec["kind"] == "run" and ref == manifest["artifact"]:
                        require(
                            artifact_ref(ref["path"], resources=resources) == ref,
                            "artifact identity drift",
                        )
                    else:
                        read_ref(ref, max(CONTROL_BYTES, ref["bytes"]))
                if spec["kind"] == "build":
                    source_check(spec["source"])
                result["status"] = "PENDING_FINALIZATION"
            finally:
                if created_TMP:
                    active_error = sys.exception()
                    try:
                        remove_empty_owned_tmp(
                            spec["TMP"],
                            spec["owner"],
                            result["checks"][-1].get("guardian_return")
                            if result["checks"]
                            else None,
                            exception_outcome=result["checks"][-1].get("guardian_exception_outcome")
                            if result["checks"]
                            else None,
                        )
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
                new_json(directory / "candidate.json", result, resources=resources)
            except BaseException as error:
                if primary is not None:
                    primary.add_note("candidate save secondary: " + repr(error))
                else:
                    primary = error
    if primary is not None:
        primary.add_note("lifecycle partial facts: " + json.dumps(result, allow_nan=False))
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
    admitted = {k: v for k, v in spec.items() if k not in {"admission", "intent_sha256"}}
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
    # A selected RUN is launched under its admitted sequence settings contract.
    # Direct RUN jobs keep their original support contract. Read the exact bound
    # bytes; the independent operation origin still selects the original config.
    resource_contract = spec.get("settings", spec["support"])
    read_ref(resource_contract)
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
        and cfg["resource_contract"] == resource_contract["path"]
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
            custody_path.is_relative_to(ORIGIN_CUSTODY) and custody_path.resolve() == custody_path,
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
    data["status"] = "FAILED"  # Available bytes never imply returned publication or completion.
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
        check["full_log"] = bound(directory / "run.full.log", spec["limits"]["log_B"])[0]
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


def _prepare_completion(directory, job_ref, *, failure=None, resources=None):
    """No child launch. Authoritative publish happens after every independent owed finalizer."""
    directory = Path(directory)
    require(
        directory.is_absolute() and (directory / "INCOMPLETE").is_file(),
        "new pending operation required",
    )
    with (directory / "finalizing").open("xb"):
        pass  # Restart cannot run a scientific command or independent finalizers twice.
    candidate = (
        failure if failure is not None else json.loads((directory / "candidate.json").read_bytes())
    )
    errors = []
    job = {}
    outer_joined = False
    if candidate["status"] != "PENDING_FINALIZATION" or candidate["cleanup_complete"] is not True:
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
        errors.append({"stage": "outer_job", **error_fact(error), "available_result": job})
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
                and check["guardian_return"]["log_bytes_seen"] == check["full_log"]["bytes"],
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
            require(
                artifact_ref(candidate["artifact"]["path"]) == candidate["artifact"],
                "artifact identity drift",
            )
            source_check(candidate["source"])
            spec = document(candidate["intent"])
            require(candidate["source"] == spec["source"], "final adopted Git/Cargo record")
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
                artifact_ref(emitted)["sha256"] == candidate["artifact"]["sha256"],
                "Cargo/private artifact drift",
            )
            require(
                {"test", "lint", "build"}
                <= prior_software_roles(candidate["source_adoption"])
                | {
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
            candidate["secondary"].append({"stage": "final_artifact_source", **error_fact(error)})
    try:
        new_json(directory / "manifest.json", candidate, resources=resources)
        fd = os.open(directory, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except BaseException as error:
        # No recursive IO reporting: keep the originating failure and every
        # accumulated secondary available if authoritative publication fails.
        error.add_note("unpublished completion facts: " + json.dumps(candidate, allow_nan=False))
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
        not (directory / "manifest.json").exists() and not (directory / "finalizing").exists(),
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
    plan = guard(spec, collection=True) if guard is physical_and_quiet else guard(spec)
    with operation_lease(spec, lock):
        resources = resource_factory(spec)
        resources.cpu_plan = plan
        resources.check()
        failure = (
            None
            if candidate_path.exists()
            else abnormal_run_failure(directory, job_ref, origin_ref=origin_ref)
        )
        completion = _prepare_completion(directory, job_ref, failure=failure, resources=resources)
        # Critical reads, direct waits, data/log writes, lease/handle closes and
        # independent finalizers precede this last fallible publication operation.
        seen = set()
        roots = charged_roots(spec)
        usage = {
            "observed_at": stamp(),
            "roots": [str(p) for p in roots],
            "allocated_B": sum(allocated(p, seen=seen) for p in roots),
            "storage_budget_B": spec["limits"].get("owned_B"),
            "FS_free_B": shutil.disk_usage(spec["owner"]).free,
            "global_actual_B": None,
            "scope": "Current directed retention after manifest publication/cleanup, before final INCOMPLETE removal; not historical peak, forecast support, or a whole-global inventory. Serial TMP is counted only if retained now. This receipt is published after the observation.",
        }
        new_json(directory / "storage-usage.json", usage, resources=resources)
        # All fallible observation/publication/check/sync work precedes this final marker.
        (directory / "INCOMPLETE").unlink()
    return completion


def operation_order(settings):
    """Serial selected blocks preserve each method's order and arena priority."""
    arena = settings.get("arena")
    measurements = settings.get("measurements", [])
    runs = settings.get("runs", [])
    require(isinstance(runs, list), "finite configured RUN list")
    if runs:
        require(arena is None and not measurements, "configured RUNs have one serial order")
        for index in range(len(runs)):
            yield "run", index
        return
    require(isinstance(measurements, list), "finite measurement settings")
    block = settings["arena_block"]
    require(type(block) is int and block > 0, "positive serial arena block")
    serial_order = settings.get("serial_order", ["arena", "measure"])
    require(
        isinstance(serial_order, list)
        and len(serial_order) == 2
        and set(serial_order) == {"arena", "measure"},
        "serial arena/measurement order",
    )
    require(
        arena is None or not measurements or serial_order[0] == "arena",
        "arena precedes measurement when both are selected",
    )
    if arena is None:
        first, last = 0, -1
    else:
        first, last = arena["range"]
        require(
            type(first) is int and type(last) is int and 0 <= first <= last,
            "finite selected arena range",
        )
        plan = document(arena["template"]["approved_plan"])
        require(last < len(plan["batches"]), "selected arena range exceeds plan")
    batch = first
    measurement = 0
    while batch <= last or measurement < len(measurements):
        for kind in serial_order:
            if kind == "arena":
                end = min(last + 1, batch + block)
                for selected in range(batch, end):
                    yield kind, selected
                batch = end
            elif measurement < len(measurements):
                yield kind, measurement
                measurement += 1


def comparison_conditions(common):
    """Normal research uses ON/depth_rank; explicit controls stay explicit.

    This preparation owner resolves settings, never session namespace IDs.
    Product/generator and direct raw config enable defaults remain OFF.
    """
    require(
        not {"history_tie_breaks", "shallow_main_history"}.intersection(common),
        "retired comparison setting",
    )
    variants = [
        dict(
            evaluator=evaluator,
            profile=profile,
            lmr=lmr,
            lmr_method=common.get("lmr_method", "depth_rank"),
            zero_stock_safe_race=common.get("zero_stock_safe_race", True),
            zero_stock_safe_race_method=common.get("zero_stock_safe_race_method", "path_tail"),
        )
        for evaluator in common["evaluators"]
        for profile in common["profiles"]
        for lmr in common.get("lmr_values", (True,))
    ]
    for variant in variants:
        if "lmr_parameters" in common:
            variant["lmr_parameters"] = copy.deepcopy(common["lmr_parameters"])
        resolved_lmr_parameters(variant, variant["profile"])
    return variants


def apply_comparison_cost(config, common, variant):
    require(
        not {"history_tie_break", "shallow_main_history"}.intersection(variant),
        "retired comparison variant",
    )
    config["tt_entries"] = common["tt_entries"]
    config["use_tt"] = common["use_tt"]
    config["use_pvs"] = common["use_pvs"]
    config["namespace"]["rules"] = common["rules"]
    config["profile"] = variant["profile"]
    config["lmr"] = variant["lmr"]
    config["lmr_method"] = variant["lmr_method"]
    if "lmr_parameters" in variant:
        config["lmr_parameters"] = copy.deepcopy(variant["lmr_parameters"])
    else:
        config.pop("lmr_parameters", None)

    config["zero_stock_safe_race"] = variant["zero_stock_safe_race"]
    config["zero_stock_safe_race_method"] = variant["zero_stock_safe_race_method"]


def apply_comparison_arena(config, common, pair):
    arena = common["arena"]
    # The existing arena entry fixes these flags true; it has no override fields.
    assert common["use_tt"] is True and common["use_pvs"] is True
    config["ruleset"] = common["ruleset"]
    config["arena"]["tt_entries"] = common["tt_entries"]
    config["arena"]["return_reserve_ms"] = arena["return_reserve_ms"]
    config["management_cpu_core"] = arena["management_guardian"]
    config["cpu_cores"] = list(arena["AI_workers"])
    config["host_ram_reserve"] = common["host_reserve_B"]
    config["max_plies"] = arena["max_plies"]
    config["max_memory_bytes"] = common["family_B"] - common["controller_B"]
    for engine, variant in zip(config["engines"], pair, strict=True):
        require(
            not {"history_tie_break", "shallow_main_history"}.intersection(variant),
            "retired comparison variant",
        )
        assert engine["kind"] == variant["evaluator"]
        engine["ordering_profile"] = variant["profile"]
        engine["lmr"] = variant["lmr"]
        engine["lmr_method"] = variant["lmr_method"]
        if "lmr_parameters" in variant:
            engine["lmr_parameters"] = copy.deepcopy(variant["lmr_parameters"])
        else:
            engine.pop("lmr_parameters", None)
        engine["zero_stock_safe_race"] = variant["zero_stock_safe_race"]
        engine["zero_stock_safe_race_method"] = variant["zero_stock_safe_race_method"]
        for key in ("depth", "max_nodes", "time_ms"):
            engine[key] = arena[key]


def parameter_schedule(recipe):
    """Compile bounded typed coordinate/SPSA configuration, without experiment IDs."""
    require(recipe["schema"] == "quoridor.parameter-tuning.v1", "typed parameter recipe")
    baseline = recipe["baseline"]
    resolved_lmr_parameters(dict(lmr_parameters=baseline), "control")
    continuous = recipe["continuous"]
    keys = continuous["coordinates"]
    scales = continuous["scale"]
    require(
        keys == ["intercept", "log_divisor"]
        and len(scales) == 2
        and all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in scales)
        and all(
            type(continuous[k]) in (int, float) and math.isfinite(continuous[k])
            for k in ("center_box", "trial_box", "step_clip")
        )
        and 0 < continuous["step_clip"] <= continuous["center_box"]
        and continuous["center_box"] < continuous["trial_box"]
        and continuous["initial_center"] == [0.0, 0.0]
        and all(type(v) in (int, float) for v in continuous["initial_center"]),
        "finite normalized coordinate bounds",
    )
    for sign in [-1, 1]:
        edge = dict(baseline)
        for key, scale in zip(keys, scales, strict=True):
            edge[key] += sign * continuous["trial_box"] * scale
        resolved_lmr_parameters(dict(lmr_parameters=edge), "control")
    split = document(recipe["book_split"])
    tuning = {r["global_family_id"] for r in split["tuning"]}
    confirmation = {r["global_family_id"] for r in split["confirmation"]}
    require(
        len(tuning) == len(split["tuning"])
        and len(confirmation) == len(split["confirmation"])
        and not tuning & confirmation
        and len({row["canonical_family"] for row in split["tuning"] + split["confirmation"]})
        == len(tuning) + len(confirmation),
        "disjoint canonical recipe families",
    )
    stages = recipe["integer_stages"]
    require(
        [stage["coordinate"] for stage in stages] == ["min_depth", "min_rank", "max_extra"],
        "declared integer coordinate order",
    )
    operations = []
    for index, stage in enumerate(stages):
        ids = stage["family_ids"]
        values = stage["candidates"]
        require(
            len(ids) == len(set(ids)) == 32
            and set(ids) <= tuning
            and stage["games_per_candidate"] == 2 * len(ids)
            and isinstance(values, list)
            and len(values) == len(set(values)) == 2
            and all(type(v) is int for v in values),
            "bounded paired integer candidates",
        )
        for value in values:
            trial = dict(baseline, **{stage["coordinate"]: value})
            resolved_lmr_parameters(dict(lmr_parameters=trial), "control")
            for chunk in range(2):
                operations.append(
                    dict(
                        kind="coordinate",
                        stage=index,
                        candidate=value,
                        chunk=chunk,
                        families=ids[chunk * 16 : chunk * 16 + 16],
                        selected=list(range(32)),
                        games=32,
                        nodes=recipe["limits"]["operation32_nodes"],
                    )
                )
    updates = recipe["updates"]
    require(isinstance(updates, list) and 0 < len(updates) <= 128, "finite SPSA updates")
    for index, update in enumerate(updates):
        require(
            update["index"] == index
            and len(update["family_ids"]) == len(set(update["family_ids"])) == 8
            and set(update["family_ids"]) <= tuning
            and len(update["selected_local_games"])
            == len(set(update["selected_local_games"]))
            == 16
            and sorted(update["selected_local_games"]) in [list(range(16)), list(range(16, 32))]
            and update["games"] == 16
            and update["nodes_nonlending"] == recipe["limits"]["operation16_nodes"]
            and len(update["delta"]) == 2
            and all(type(v) is int and v in {-1, 1} for v in update["delta"])
            and all(
                type(update[k]) in (int, float) and math.isfinite(update[k]) and update[k] > 0
                for k in ("a", "c")
            ),
            "typed complete SPSA trial",
        )
        operations.append(
            dict(
                kind="spsa",
                stage=index,
                families=update["family_ids"],
                selected=update["selected_local_games"],
                games=16,
                nodes=update["nodes_nonlending"],
            )
        )
    limits = recipe["limits"]
    require(
        all(
            type(limits[k]) is int and limits[k] > 0
            for k in (
                "games",
                "nodes",
                "operation32_nodes",
                "operation16_nodes",
                "confirmation_games",
                "confirmation_nodes",
            )
        )
        and sum(op["games"] for op in operations) + limits["confirmation_games"] == limits["games"]
        and sum(op["nodes"] for op in operations) + limits["confirmation_nodes"] == limits["nodes"],
        "nonlending finite parameter campaign",
    )
    return operations


def parameter_coordinate_seed(control, recipe):
    """Resolve configured accepted integer decisions without fabricating normal feedback."""
    if "coordinate_seed" not in control:
        return None
    decisions = control["coordinate_seed"]
    stages = recipe["integer_stages"]
    require(
        type(decisions) is list and len(decisions) == len(stages),
        "complete accepted coordinate seed",
    )
    integers = {}
    for stage, declared in zip(stages, decisions, strict=True):
        coordinate = stage["coordinate"]
        require(
            type(declared) is dict
            and set(declared) == {"coordinate", "value", "selection", "acceptance"}
            and declared["coordinate"] == coordinate
            and type(declared["value"]) is int
            and declared["value"] in [recipe["baseline"][coordinate], *stage["candidates"]],
            "ordered configured coordinate decision",
        )
        selection = document(declared["selection"])
        acceptance = document(declared["acceptance"])
        require(
            type(selection) is dict
            and type(acceptance) is dict
            and selection["selected_" + coordinate] == declared["value"]
            and acceptance.get("selection", acceptance.get("result")) == declared["selection"]
            and acceptance.get(
                "selected_" + coordinate, acceptance.get("selected", {}).get(coordinate)
            )
            == declared["value"],
            "accepted immutable coordinate selection correspondence",
        )
        require(
            all(selection.get("selected_" + key) == value for key, value in integers.items()),
            "coordinate choices keep preceding accepted integers",
        )
        integers[coordinate] = declared["value"]
    return integers


def parameter_continuation(control, recipe):
    """Bind accepted prefix/choice inputs; no old PASS or local feedback is fabricated."""
    if "continuation" not in control:
        return None
    declared = control["continuation"]
    require(
        "coordinate_seed" not in control
        and type(declared) is dict
        and set(declared)
        == {
            "center",
            "acceptance",
            "selection",
            "selection_acceptance",
            "update_range",
            "operation_offset",
        },
        "typed accepted continuation inputs",
    )
    center = document(declared["center"])
    acceptance = document(declared["acceptance"])
    evidence = acceptance["evidence"]
    require(
        evidence["post_update32_center"] == declared["center"],
        "accepted exact prefix center",
    )
    result = document(evidence["result"])
    stop = document(evidence["STOP"])
    prefix = center["normal_operations"]
    update_range = declared["update_range"]
    offset = declared["operation_offset"]
    require(
        type(prefix) is int
        and type(update_range) is list
        and len(update_range) == 2
        and all(type(v) is int for v in update_range)
        and 0 < prefix == update_range[0] < update_range[1] <= len(recipe["updates"])
        and type(offset) is int
        and offset >= 4 * len(recipe["integer_stages"]) + prefix,
        "bounded configured update and operation offsets",
    )
    require(
        result["normal_operations"] == prefix
        and len(result["operations"]) == prefix
        and all(
            row["normal_data_status"] == "PASS" and row["UNKNOWN"] == 0
            for row in result["operations"]
        )
        and result["UNKNOWN"] == center["UNKNOWN"] == 0
        and result["center"] == declared["center"]
        and result["normal_feedback"] == center["feedback"]
        and result["normal_feedback_selections"] == center["selections"]
        and result["qualified_games"] == center["physical_games"] == 16 * prefix
        and result["qualified_pairs"] == center["complete_pairs"] == 8 * prefix
        and stop["result"] == evidence["result"]
        and stop["center"] == declared["center"]
        and stop["directwait_reaped"] is True
        and stop["handles_closed"] is True
        and stop["remaining"] == stop["TMP_remaining"] == stop["standing_source_leases"] == [],
        "accepted complete normal prefix and actual collection STOP",
    )
    prefix_settings = document(center["exact_settings"])
    require(
        prefix_settings["kind"] == "sequence"
        and len(prefix_settings["runs"]) == prefix
        and prefix_settings["parameter_tuning"]["recipe"] == control["recipe"]
        and prefix_settings["parameter_tuning"]["prior"] == []
        and "continuation" not in prefix_settings["parameter_tuning"]
        and center["base"] == recipe["baseline"]
        and center["scales"] == recipe["continuous"]["scale"]
        and center["old64_terminal"] is False
        and center["best_interim_selection"] is False,
        "same original normalization and complete original prefix, not a restarted trial",
    )
    vector = center["center"]
    require(
        type(vector) is list
        and len(vector) == len(recipe["continuous"]["coordinates"])
        and all(
            type(value) in (int, float)
            and math.isfinite(value)
            and abs(value) <= recipe["continuous"]["center_box"]
            for value in vector
        ),
        "finite accepted center in original box",
    )
    choice = document(declared["selection"])
    choice_acceptance = document(declared["selection_acceptance"])
    selected = choice["selected"]
    require(
        choice["status"] == "PASS"
        and choice["UNKNOWN"] == 0
        and choice["center"] == declared["center"]
        and choice_acceptance["selection"] == declared["selection"]
        and choice_acceptance["selected"] == selected
        and resolved_lmr_parameters(dict(lmr_parameters=selected), "control") == selected
        and selected["max_extra"] == center["integers"]["max_extra"],
        "accepted complete wide choice with fixed cap",
    )
    for key, scale, value in zip(
        recipe["continuous"]["coordinates"],
        recipe["continuous"]["scale"],
        vector,
        strict=True,
    ):
        expected = recipe["baseline"][key] + scale * value
        require(
            selected[key] == center["physical_parameters"][key] == expected,
            "wide choice keeps exact original prefix coefficients without rebase",
        )
    return dict(
        center=list(vector),
        integers={key: selected[key] for key in ("min_depth", "min_rank", "max_extra")},
        update_range=list(update_range),
        operation_offset=offset,
    )


def parameter_state(recipe, feedback, coordinate_seed=None, continuation=None):
    """Resolve a complete stage prefix; accepted integer seeds never stand in for feedback."""
    operations = parameter_schedule(recipe)
    offset = 0
    if continuation is not None:
        require(coordinate_seed is None, "one configured continuation seed")
        begin, end = continuation["update_range"]
        start = 4 * len(recipe["integer_stages"])
        operations = operations[start + begin : start + end]
        offset = continuation["operation_offset"]
    elif coordinate_seed is not None:
        keys = [stage["coordinate"] for stage in recipe["integer_stages"]]
        require(
            type(coordinate_seed) is dict
            and set(coordinate_seed) == set(keys)
            and all(
                type(coordinate_seed[k]) is int
                and coordinate_seed[k] in [recipe["baseline"][k], *stage["candidates"]]
                for k, stage in zip(keys, recipe["integer_stages"], strict=True)
            ),
            "accepted integer values only; coefficient center stays original",
        )
        offset = 4 * len(recipe["integer_stages"])
        operations = operations[offset:]
        require(
            all(op["kind"] == "spsa" for op in operations),
            "coefficient-only continuation",
        )
    require(
        isinstance(feedback, list) and len(feedback) <= len(operations),
        "feedback prefix",
    )
    baseline = recipe["baseline"]
    integers = {k: baseline[k] for k in ["min_depth", "min_rank", "max_extra"]}
    if coordinate_seed is not None:
        integers.update(coordinate_seed)
    control = recipe["continuous"]
    center = list(control["initial_center"])
    if continuation is not None:
        integers.update(continuation["integers"])
        center = list(continuation["center"])
    trace = []

    def physical(vector):
        values = dict(baseline, **integers)
        for key, scale, coordinate in zip(
            control["coordinates"], control["scale"], vector, strict=True
        ):
            values[key] = baseline[key] + scale * coordinate
        resolved_lmr_parameters(dict(lmr_parameters=values), "control")
        return values

    def arms(operation):
        if operation["kind"] == "coordinate":
            stage = recipe["integer_stages"][operation["stage"]]
            current = physical([0.0, 0.0])
            return [
                dict(current, **{stage["coordinate"]: operation["candidate"]}),
                current,
            ]
        update = recipe["updates"][operation["stage"]]
        return [
            physical(
                [
                    max(
                        -control["trial_box"],
                        min(control["trial_box"], x + sign * update["c"] * delta),
                    )
                    for x, delta in zip(center, update["delta"], strict=True)
                ]
            )
            for sign in [1, -1]
        ]

    for index, entry in enumerate(feedback):
        operation = operations[index]
        expected = arms(operation)
        require(
            entry["operation"] == offset + index
            and entry["games"] == operation["games"]
            and entry["families"] == operation["families"]
            and entry["UNKNOWN"] == 0
            and type(entry["point"]) in (int, float)
            and math.isfinite(entry["point"])
            and 0 <= entry["point"] <= 1
            and entry["point"] * entry["games"] * 2 % 1 == 0
            and [entry["LEFT"], entry["RIGHT"]] == expected,
            "complete frozen feedback/parameter correspondence; UNKNOWN stops dependency",
        )
        if operation["kind"] == "coordinate":
            if index % 4 == 3:
                stage = recipe["integer_stages"][operation["stage"]]
                coordinate = stage["coordinate"]
                scored = [
                    (
                        sum(
                            feedback[j]["point"]
                            for j in [
                                index - 3 + 2 * candidate,
                                index - 2 + 2 * candidate,
                            ]
                        )
                        / 2,
                        value,
                    )
                    for candidate, value in enumerate(stage["candidates"])
                ]
                eligible = [(point, value) for point, value in scored if point > 0.5]
                before = integers[coordinate]
                if eligible:
                    integers[coordinate] = min(
                        eligible,
                        key=lambda pair: (-pair[0], abs(pair[1] - before), pair[1]),
                    )[1]
                trace.append(
                    dict(
                        kind="coordinate",
                        coordinate=coordinate,
                        before=before,
                        after=integers[coordinate],
                        exploratory_points=scored,
                    )
                )
        else:
            update = recipe["updates"][operation["stage"]]
            gradient = [(entry["point"] - 0.5) / (update["c"] * delta) for delta in update["delta"]]
            raw = [update["a"] * g for g in gradient]
            step = [max(-control["step_clip"], min(control["step_clip"], value)) for value in raw]
            after = [
                max(-control["center_box"], min(control["center_box"], x + change))
                for x, change in zip(center, step, strict=True)
            ]
            trace.append(
                dict(
                    kind="spsa",
                    update=operation["stage"],
                    before=center,
                    gradient=gradient,
                    raw_step=raw,
                    clipped_step=step,
                    after=after,
                    step_clips=sum(a != b for a, b in zip(raw, step, strict=True)),
                    center_clips=sum(
                        x + change != new
                        for x, change, new in zip(center, step, after, strict=True)
                    ),
                )
            )
            center = after
    if len(feedback) == len(operations):
        return dict(
            kind="terminal",
            operation_offset=offset,
            LEFT=physical(center),
            RIGHT=baseline,
            center=center,
            integers=integers,
            trace=trace,
        )
    operation = operations[len(feedback)]
    left, right = arms(operation)
    return dict(
        kind="trial",
        operation_index=offset + len(feedback),
        operation_offset=offset,
        operation=operation,
        LEFT=left,
        RIGHT=right,
        center=center,
        integers=integers,
        trace=trace,
    )


def parameter_history(settings, index):
    """Read only bounded normal PASS manifests and their compact result summaries."""
    control = settings["parameter_tuning"]
    require(
        type(control) is dict
        and set(control)
        in (
            {"recipe", "prior"},
            {"recipe", "prior", "coordinate_seed"},
            {"recipe", "prior", "continuation"},
        ),
        "typed parameter control",
    )
    recipe = document(control["recipe"])
    operations = parameter_schedule(recipe)
    seed = parameter_coordinate_seed(control, recipe)
    offset = 4 * len(recipe["integer_stages"]) if seed is not None else 0
    continuation = parameter_continuation(control, recipe)
    available = len(operations) - offset
    if continuation is not None:
        begin, end = continuation["update_range"]
        start = 4 * len(recipe["integer_stages"])
        operations = operations[start + begin : start + end]
        available = len(operations)
        offset = continuation["operation_offset"]
    prior = control["prior"]
    require(
        isinstance(prior, list)
        and type(index) is int
        and 0 <= index <= len(settings["runs"])
        and len(prior) + len(settings["runs"]) <= available,
        "bounded normal parameter sequence",
    )
    references, selections = [], []
    for position, declared in enumerate(prior):
        require(
            type(declared) is dict
            and set(declared) == {"operation", "manifest", "settings", "selection_index"}
            and type(declared["operation"]) is int
            and declared["operation"] == offset + position,
            "declared original feedback operation",
        )
        references.append(declared["manifest"])
        selections.append((declared["settings"], declared["selection_index"]))
    for local in range(index):
        references.append(
            bound(Path(settings["output"]) / f"run-{local:03d}/operation/manifest.json")[0]
        )
        selections.append((None, local))
    require(
        len({ref["sha256"] for ref in references}) == len(references),
        "no reused normal feedback operation",
    )
    result = []
    configs = set()
    for position, reference in enumerate(references):
        manifest = document(reference)
        require(
            manifest["status"] == "PASS"
            and manifest["cleanup_complete"] is True
            and manifest["remaining"] == manifest["owed_finalizers"] == []
            and manifest["primary"] is None
            and manifest["secondary"] == [],
            "normal completed parameter feedback",
        )
        data = manifest["data"]
        operation = operations[position if continuation is not None else offset + position]
        require(
            data["status"] == "PASS"
            and data["errors"] == []
            and data["missing_local_games"] == []
            and sorted(data["observed_local_games"]) == operation["selected"],
            "complete original selected parameter slots",
        )
        # A normal PASS is necessary, but it must be the declared original RUN.
        expected_settings_ref, selected_index = selections[position]
        expected_settings = (
            settings if expected_settings_ref is None else document(expected_settings_ref)
        )
        require(
            type(selected_index) is int
            and expected_settings["kind"] == "sequence"
            and 0 <= selected_index < len(expected_settings["runs"]),
            "original feedback selection index",
        )
        intent = document(manifest["intent"])
        require(
            intent["selection_index"] == selected_index
            and (expected_settings_ref is None or intent["settings"] == expected_settings_ref)
            and document(intent["settings"]) == expected_settings
            and manifest["experiment"] == intent["experiment"]
            and reference["path"]
            == str(
                Path(expected_settings["output"])
                / f"run-{selected_index:03d}/operation/manifest.json"
            ),
            "normal feedback is the original settings/RUN/operation custody",
        )
        template = expected_settings["runs"][selected_index]
        original_experiment = document(template["experiment"])
        experiment = document(manifest["experiment"])
        config = document(experiment["config"])
        expected_config = document(original_experiment["config"])
        require(
            len(config["engines"]) == len(expected_config["engines"]) == 2,
            "two original feedback engines",
        )
        for original, actual in zip(expected_config["engines"], config["engines"], strict=True):
            original["lmr_parameters"] = actual["lmr_parameters"]
        require(
            config == expected_config,
            "feedback preserves original clock/seed/model/book/history/colour; only five parameters may derive",
        )
        plan = document(template["approved_plan"])
        batch = plan["batches"][original_experiment["batch"]]
        batch["config"] = experiment["config"]
        next(m for m in plan["matchups"] if m["id"] == batch["matchup"])["engines"] = config[
            "engines"
        ]
        require(
            document(intent["approved_plan"]) == plan,
            "feedback preserves original Plan and selected batch",
        )
        expected_experiment = dict(original_experiment)
        for field in ["config", "canonical_plan_sha256", "numerical_qualification"]:
            expected_experiment[field] = experiment[field]
        require(
            experiment == expected_experiment
            and experiment["canonical_plan_sha256"] == intent["approved_plan"]["sha256"],
            "feedback preserves original Experiment outside normal typed derivation",
        )
        if "parameter_tuning" not in expected_settings:
            selected_run(intent, experiment)
        # Adaptive PASS already went through the unchanged normal selected_run
        # owner. Re-reading its feedback here would recursively qualify prefixes;
        # bind that immutable selection and its parameter-only science above.
        require(
            experiment["config"]["sha256"] not in configs,
            "feedback config cannot be replayed",
        )
        configs.add(experiment["config"]["sha256"])
        files = [ref for ref in data["files"] if Path(ref["path"]).name == "result.json"]
        require(len(files) == 1, "one compact normal native result")
        native = document(files[0])["report"]
        summary = native["arena_summary"]
        census = summary["census"]
        require(
            native["run_id"] == config["run_id"]
            and native["all_workers_joined"] is True
            and native["stopped"] is None
            and census["planned_games"]
            == census["started_games"]
            == census["completed_games"]
            == operation["games"]
            and census["unknown_games"] == census["incomplete_pairs"] == 0
            and census["complete_pairs"] * 2 == operation["games"],
            "qualified feedback census, no refill",
        )
        selected = operation["selected"]
        actual_families = [
            config["arena"]["book"]["openings"][i // 2]["reference"]["settings"]["family_id"]
            for i in selected[::2]
        ]
        require(
            actual_families == operation["families"]
            and config["arena"]["max_total_nodes"] == operation["nodes"]
            and config["arena"]["game_selection"]["selected"] == selected
            and config["arena"]["game_selection"]["excluded"]
            == sorted(set(range(config["games"])) - set(selected)),
            "recipe family/mask/nonlending budget",
        )
        point = summary["complete_pair_mean"]
        require(
            point == native["score"]
            and len(summary["pairs"]) == len(actual_families)
            and point == sum(p["score"] for p in summary["pairs"]) / len(actual_families),
            "normal complete-family point",
        )
        budget = native["pump"]["arena_node_budget"]
        require(
            budget["cap"] == operation["nodes"]
            and type(budget["charged_nodes_including_opaque_reservations"]) is int
            and type(budget["remaining"]) is int
            and 0 <= budget["charged_nodes_including_opaque_reservations"] <= budget["cap"]
            and budget["charged_nodes_including_opaque_reservations"] + budget["remaining"]
            == budget["cap"],
            "actual parameter node debit",
        )
        result.append(
            dict(
                operation=offset + position,
                games=operation["games"],
                families=actual_families,
                UNKNOWN=0,
                point=point,
                LEFT=config["engines"][0]["lmr_parameters"],
                RIGHT=config["engines"][1]["lmr_parameters"],
                manifest=reference,
                original_selection=dict(
                    settings=intent["settings"],
                    selection_index=selected_index,
                    intent=manifest["intent"],
                    original_RUN_experiment=template["experiment"],
                    original_Plan=template["approved_plan"],
                ),
                charged_nodes=budget["charged_nodes_including_opaque_reservations"],
            )
        )
    return recipe, result


def parameter_trial(settings, index):
    recipe, feedback = parameter_history(settings, index)
    seed = parameter_coordinate_seed(settings["parameter_tuning"], recipe)
    continuation = parameter_continuation(settings["parameter_tuning"], recipe)
    state = parameter_state(recipe, feedback, coordinate_seed=seed, continuation=continuation)
    require(state["kind"] == "trial", "no operation after terminal parameter center")
    return recipe, state


def prepare_parameter_run(settings, index, phase, spec, experiment):
    """Materialize coefficients only into the existing ordinary RUN/Plan/numerical owners."""
    _, state = parameter_trial(settings, index)
    operation = state["operation"]
    config = document(experiment["config"])
    planned = document(experiment["schedule"])
    selected = operation["selected"]
    require(
        config["arena"]["max_total_nodes"] == operation["nodes"]
        and arena_game_ids(config) == selected
        and [row["family_id"] for row in planned if row["local_game"] in selected[::2]]
        == operation["families"],
        "fixed parameter RUN family/mask/cap",
    )
    for engine, parameters in zip(config["engines"], [state["LEFT"], state["RIGHT"]], strict=True):
        engine["lmr_parameters"] = parameters
    new_json(phase / "config.json", config)
    experiment["config"] = bound(phase / "config.json")[0]
    plan = document(spec["approved_plan"])
    plan["batches"][experiment["batch"]]["config"] = experiment["config"]
    matchup = next(
        m for m in plan["matchups"] if m["id"] == plan["batches"][experiment["batch"]]["matchup"]
    )
    matchup["engines"] = config["engines"]
    new_json(phase / "plan.json", plan)
    spec["approved_plan"] = bound(phase / "plan.json")[0]
    experiment["canonical_plan_sha256"] = spec["approved_plan"]["sha256"]
    prior = document(experiment["numerical_qualification"])
    numerical = numerical_fields(experiment, accepted_build(experiment["build_manifest"]))
    for key in ["original_evidence", "correspondence_only", "scope", "new_model_or_head_calls"]:
        if key in prior:
            numerical[key] = prior[key]
    new_json(phase / "numerical.json", numerical)
    experiment["numerical_qualification"] = bound(phase / "numerical.json")[0]
    new_json(phase / "parameter-state.json", state)
    arena_plan_check(experiment, plan)


def prepare_selected_operation(settings_ref, kind, index):
    """Derive ordinary lifecycle parameters; never issue a per-operation admission."""
    settings = document(settings_ref)
    if kind == "arena":
        template = settings["arena"]["template"]
    else:
        require(kind in {"measure", "run"}, "selected finite operation kind")
        template = settings["runs" if kind == "run" else "measurements"][index]
    require(
        "lmr_recipe" not in settings and "lmr_recipe" not in template,
        "lmr_recipe is retired; use static typed LMR parameters",
    )
    if "parameter_tuning" in settings:
        require(
            kind == "run" and settings.get("arena_cohort") is None,
            "adaptive parameters use the existing serial RUN owner",
        )
        parameter_trial(settings, index)
    spec = copy.deepcopy(template)
    if settings.get("arena_cohort") is not None:
        require(kind == "run", "cohort selects normal RUN sequences only")
        spec["arena_cohort"] = settings["arena_cohort"]
    require(spec["kind"] == "run", "finite execution composes RUN operations only")
    if kind == "run":
        require(
            template.get("finalizers") == [],
            "configured RUN with nonempty finalizers unsupported before ownership",
        )
    phase = owned(
        Path(settings["output"]) / f"{kind}-{index:03d}",
        spec["owner"],
    )
    require(not phase.exists(), "selected operation already exists; never replay")
    experiment = document(template["experiment"])
    original_experiment = copy.deepcopy(experiment)
    spec.pop("admission", None)
    spec.pop("intent_sha256", None)
    spec.update(output=str(phase / "operation"), TMP=str(phase / "TMP"), finalizers=[])
    spec["env"]["TMPDIR"] = spec["TMP"]
    if "PERF_BUILDID_DIR" in spec["env"]:
        spec["env"]["PERF_BUILDID_DIR"] = str(phase / "buildid-cache")
    if kind == "arena":
        spec["settings"] = settings_ref
        plan = document(spec["approved_plan"])
        batch = plan["batches"][index]
        require(batch["batch"] == index, "selected plan batch index")
        experiment.update(
            batch=index,
            config=batch["config"],
            inputs=plan["inputs"],
            models=plan["models"],
            schedule=plan["schedule"],
            canonical_plan_sha256=spec["approved_plan"]["sha256"],
        )
        spec["data_root"] = document(experiment["config"])["output"]
    elif kind == "run":
        spec.update(settings=settings_ref, selection_index=index)
        require(
            not Path(spec["data_root"]).exists(),
            "configured output already entered; never replay",
        )
    else:
        require(experiment["argv"][1] == "measure", "selected common measurement only")
        old_root = Path(spec["data_root"])
        spec["data_root"] = str(phase / "data")
        for item in spec["data"]:
            if item["name"] == "perf_RAW":
                item["path"] = str(phase / "perf.data")
            else:
                item["path"] = str(
                    Path(spec["data_root"]) / Path(item["path"]).relative_to(old_root)
                )
        if spec.get("perf") is not None:
            spec["perf"]["output"] = str(phase / "perf.data")
    if kind == "arena":
        for item in spec["data"]:
            item["path"] = str(Path(spec["data_root"]) / Path(item["path"]).name)
    spec["owned_outputs"] = list(
        dict.fromkeys([*spec.get("owned_outputs", []), str(phase), spec["TMP"]])
    )
    phase.mkdir(parents=True)
    if "parameter_tuning" in settings:
        prepare_parameter_run(settings, index, phase, spec, experiment)
    if kind != "run" and experiment.get("numerical_qualification") is not None:
        prior = document(original_experiment["numerical_qualification"])
        numerical = numerical_fields(experiment, accepted_build(experiment["build_manifest"]))
        # Retain the original evidence's scope; these are current loader bindings only.
        for key in (
            "original_evidence",
            "correspondence_only",
            "scope",
            "new_model_or_head_calls",
        ):
            if key in prior:
                numerical[key] = prior[key]
        new_json(phase / "numerical.json", numerical)
        experiment["numerical_qualification"] = bound(phase / "numerical.json")[0]
    new_json(phase / "experiment.json", experiment)
    spec["experiment"] = bound(phase / "experiment.json")[0]
    native = [
        a.replace("@EXPERIMENT@", spec["experiment"]["path"]).replace(
            "@EXPERIMENT_SHA256@", spec["experiment"]["sha256"]
        )
        for a in experiment["argv"]
    ]
    spec["argv"] = measurement_argv(spec, experiment, native)
    spec["intent_sha256"] = canonical_sha(spec)
    new_json(phase / "intent.json", spec)
    return bound(phase / "intent.json")[0]


def sequence(
    settings_ref,
    *,
    job_module=None,
    backend=None,
    prepare=prepare_selected_operation,
    complete=finalize,
):
    """One finite controller; inner execute/directwait/finalize never dispatch a turn."""
    settings = document(settings_ref)
    require(settings["kind"] == "sequence", "selected finite settings")
    require(sys.executable == str(project_python()), "current common-entry interpreter")
    origin = originating_job(settings_ref, settings)
    config = document(origin["config"])
    order = list(operation_order(settings))
    output = owned(settings["output"], settings["owner"])
    require(not output.exists(), "finite controller already entered; no automatic restart")
    if job_module is None:
        loader = importlib.util.spec_from_file_location(
            "sequence_job", ROOT / "scripts/dev/research-job.py"
        )
        job_module = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(job_module)
    if backend is None:
        backend = job_module.runtime.AppBackend(ROOT)
    output.mkdir(parents=True)
    if settings.get("arena_cohort") is not None:
        new_json(
            output / "lane-origin.json",
            dict(settings=settings_ref, originating_job=origin),
        )
    cpu_plan = sequence_cpu_plan(settings_ref)
    apply_controller_cpu_plan(cpu_plan)
    active = None
    active_spec = None
    stopped = False
    result = {
        "settings": settings_ref,
        "originating_job": origin,
        "operations": [],
        "cpu_plan": cpu_plan.record(),
        "primary": None,
        "secondary": [],
    }

    def cancel(signum, frame):
        nonlocal stopped
        stopped = True
        if active is not None:
            job_module.write(active, "cancel.json", {"requested_at": stamp(), "signal": signum})

    def cohort_spec():
        if active_spec is not None:
            return active_spec
        if settings.get("arena_cohort") is None:
            return None
        return arena_cohort_spec(settings_ref)

    def progress():
        nonlocal stopped
        projected = cohort_spec()
        if projected is None:
            return
        try:
            arena_cohort_progress(projected)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as error:
            result.setdefault("progress_errors", []).append(error_fact(error))
            cancellation = (
                error.subgroup(process.CycleStopped)
                if isinstance(error, BaseExceptionGroup)
                else error
                if isinstance(error, process.CycleStopped)
                else None
            )
            if cancellation is not None and any(
                k in json.dumps(error_fact(cancellation)) for k in ("signal", "pause")
            ):
                stopped = True

    previous = {sig: signal.signal(sig, cancel) for sig in (signal.SIGTERM, signal.SIGINT)}
    cohort_resources = None
    try:
        if settings.get("arena_cohort") is not None:
            cohort_resources = ArenaCohortResources(cohort_spec())
        for kind, index in order:
            if cohort_resources is not None:
                cohort_resources.check(admit=True)
            require(not stopped, "finite controller cancelled; remaining work UNKNOWN")
            job_module.authority(config, ROOT, backend, horizon=config["end_at"])
            read_ref(settings_ref)
            cpu_plan.apply()
            spec_ref = prepare(settings_ref, kind, index)
            spec = document(spec_ref)
            active_spec = spec
            operation_plan = physical_and_quiet(spec)
            require(
                set(operation_plan.all) <= set(cpu_plan.all),
                "selected operation outside sequence CPU plan",
            )
            cpu_plan.apply()
            active = Path(spec_ref["path"]).parent / "runtime"
            active.mkdir()
            child_config = job_module.validate(
                {
                    **config,
                    "cwd": spec["cwd"],
                    "resource_contract": settings_ref["path"],
                    "log_max_bytes": spec["limits"]["log_B"],
                    "argv": [
                        sys.executable,
                        "-B",
                        str(ROOT / "scripts/dev/research-lifecycle.py"),
                        "run",
                        "--intent",
                        spec_ref["path"],
                        "--sha256",
                        spec_ref["sha256"],
                    ],
                },
                active,
            )
            job_module.write(active, "config.json", child_config)
            job_module.write(
                active,
                "state.json",
                {
                    "schema_version": 1,
                    "job_id": str(uuid.uuid4()),
                    "issue": child_config["issue"],
                    "thread_id": child_config["thread_id"],
                    "phase": "queued",
                    "created_at": stamp(),
                    "config_sha256": sha(json.dumps(child_config, sort_keys=True).encode()),
                },
            )
            entry = {
                "kind": kind,
                "index": index,
                "launch_affinity": sorted(os.sched_getaffinity(0)),
            }
            result["operations"].append(entry)
            require(not stopped, "finite controller cancelled before child entry")
            with job_module.lock(active, "process.lock"):
                if cohort_resources is None:
                    returned = job_module.execute(active, child_config, ROOT, backend)
                else:
                    returned = job_module.execute(
                        active, child_config, ROOT, backend, resources=cohort_resources
                    )
            entry["job_result"] = bound(active / "result.json")[0]
            operation = Path(spec["output"])
            if (operation / "INCOMPLETE").exists():
                cpu_plan.apply()
                completion = complete(operation, entry["job_result"])
                entry["manifest"] = bound(operation / "manifest.json")[0]
                require(
                    completion["status"] == "PASS"
                    and completion["cleanup_complete"] is True
                    and completion["remaining"] == [],
                    "owning operation failed or not cleaned",
                )
            else:
                raise Refused("operation refused before ownership; remaining work UNKNOWN")
            require(
                returned["outcome"] == "succeeded"
                and returned.get("direct_child_reaped") is True
                and returned.get("cleanup_complete") is True
                and returned.get("remaining") == [],
                "original child failed or not cleaned",
            )
            require(not Path(spec["TMP"]).exists(), "owned child TMP remains")
            read_ref(settings_ref)
            entry["completed"] = True
            entry["reader_STOP"] = stamp()
            active = None
            cpu_plan.apply()
            progress()
        require(not stopped, "finite controller cancelled after terminal collection")
    except BaseException as error:
        result["primary"] = error_fact(error)
    finally:
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except BaseException as error:
                result["secondary"].append({"stage": "signal_restore", **error_fact(error)})
        try:
            cpu_plan.apply()
        except BaseException as error:
            result["secondary"].append({"stage": "affinity_restore", **error_fact(error)})
        child_results = []
        for entry in result["operations"]:
            try:
                child_results.append(document(entry["job_result"]))
            except BaseException as error:
                child_results.append(None)
                result["secondary"].append({"stage": "job_result", **error_fact(error)})
        result.update(
            status="CANCELLED"
            if stopped
            else ("FAILED" if result["primary"] or result["secondary"] else "PASS"),
            completed_operations=sum(x.get("completed") is True for x in result["operations"]),
            selected_operations=len(order),
            reader_STOP=stamp(),
            launch_affinity_restored=sorted(os.sched_getaffinity(0)),
            cleanup_complete=all(
                child is not None and child.get("cleanup_complete") is True
                for child in child_results
            ),
            remaining=None
            if any(child is None or child.get("remaining") is None for child in child_results)
            else [member for child in child_results for member in child["remaining"]],
        )
        new_json(output / "result.json", result)
        previous_errors = len(result.get("progress_errors", []))
        progress()  # Other lanes can now observe a genuine pre-inner terminal refusal.
        if len(result.get("progress_errors", [])) > previous_errors:
            try:
                new_json(
                    output / "terminal-progress-errors.json",
                    dict(
                        result=bound(output / "result.json")[0],
                        errors=result["progress_errors"][previous_errors:],
                    ),
                )
            except BaseException as error:
                print(
                    json.dumps(dict(terminal_notice_publication_error=error_fact(error))),
                    file=sys.stderr,
                )
    if settings.get("arena_cohort") is not None:
        require(
            not stopped,
            "cancelled at terminal notification; saved execution result retained",
        )
    require(result["status"] == "PASS", "finite execution stopped; see its original result")
    return result


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
    p = commands.add_parser("cohort")
    p.add_argument("--intent", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p = commands.add_parser("sequence")
    p.add_argument(
        "--intent",
        type=Path,
        required=True,
        help="One selected finite settings snapshot",
    )
    p.add_argument("--sha256", required=True)
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
        require(bool(args.origin_record) == bool(args.origin_sha256), "origin path/SHA pair")
        origin_ref = None
        if args.origin_record is not None:
            origin_ref, _ = bound(args.origin_record)
            require(origin_ref["sha256"] == args.origin_sha256, "independent origin binding")
        result = finalize(args.operation, ref, origin_ref=origin_ref)
        return 0 if result["status"] == "PASS" else 1
    ref, _ = bound(args.intent)
    require(ref["sha256"] == args.sha256, "intent SHA")
    require(document(ref)["kind"] == args.command, "operation kind")
    if args.command == "cohort":
        cohort_sequence(ref)
        return 0
    if args.command == "sequence":
        sequence(ref)
        return 0
    execute(ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
