"""Launch-local ownership and failed completion; artificial payloads only."""

import asyncio
from contextlib import contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ["QUORIDOR_PROJECT_ROOT"])


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


j = module("entry_job", SOURCE / "scripts/dev/research-job.py")
lc = module("entry_lifecycle", SOURCE / "scripts/dev/research-lifecycle.py")


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    j.runtime.atomic_json(path, value)
    return lc.bound(path)[0]


def config(root, argv, contract):
    return dict(
        issue="work",
        goal_issue="goal",
        thread_id="target",
        cwd=str(root),
        argv=argv,
        end_at=None,
        notify_until=None,
        max_runtime_seconds=25,
        control_interval_seconds=1,
        notify_interval_seconds=1,
        request_timeout_seconds=1,
        log_max_bytes=8192,
        resource_contract=str(contract),
    )


class Backend:
    def __init__(self, root):
        self.root = root

    def issues(self, ids, *, timeout, check=None):
        # Only the top normal supervisor may reach this fake DB inlet.
        with (self.root / "DB-calls.jsonl").open("a") as stream:
            stream.write(json.dumps(dict(pid=os.getpid(), ids=ids)) + "\n")
        if check:
            check()
        return [dict(id=i, status="in_progress", labels=[], assignee="codex:target") for i in ids]


def install(root):
    lc.ROOT = root
    j.__file__ = str(root / "scripts/dev/research-job.py")
    j._lifecycle_modules[root] = lc

    @contextmanager
    def resources(*args, **kwargs):
        # The actual external CycleResources owns NN0 CPU/RAM. No engine admission
        # or scientific resource qualification is exercised by fake payloads.
        yield None

    j.configured_arena_resources = resources


def fixture_main():
    root = Path(sys.argv[0]).resolve().parents[2]
    install(root)
    backend = Backend(root)
    if sys.argv[1] == "run":
        directory = Path(sys.argv[3])
        actual_watch = j.watch_notification
        j.watch_notification = lambda directory, cfg, *args: (
            actual_watch(directory, cfg, *args)
            if cfg.get("authority_parent") is not None
            else {"status": "fixture_no_wake"}
        )
        j.run(directory, root, backend)
        return
    intent_ref = lc.bound(Path(sys.argv[3]))[0]
    intent = lc.document(intent_ref)
    if sys.argv[1] == "cohort":
        lc.cohort_sequence(intent_ref, job_module=j, backend=backend)
        return
    lane = intent["arena_lane"]
    directory = Path(os.environ["QUORIDOR_RESEARCH_JOB_DIR"])
    outer_cfg = j.read(directory, "config.json")
    binding = lc.cohort_job_authority(outer_cfg, directory)
    # Reach the same local authority gate as an inner operation, with a real
    # bounded Python process in place of the native engine.
    member = lc.document(intent["arena_cohort"])["members"][lane]
    inner = Path(member["output"]) / "run-000/runtime"
    inner.mkdir(parents=True)
    inner_intent = dict(
        arena_cohort=intent["arena_cohort"],
        settings=lc.bound(Path(member["settings_path"]))[0],
        selection_index=0,
    )
    contract = inner.parent / "intent.json"
    put(contract, inner_intent)
    mode = (root / "mode").read_text()
    payload = (
        "import os,time;from pathlib import Path;Path("
        + repr(str(root / f"payload-{lane}"))
        + ").write_text(str(os.getpid()));time.sleep("
        + (".7" if mode == "child_failure" and lane == 0 else "2")
        + ");raise SystemExit("
        + ("1" if mode == "child_failure" and lane == 0 else "0")
        + ")"
    )
    cfg = {
        **outer_cfg,
        "argv": [sys.executable, "-B", "-c", payload],
        "resource_contract": str(contract),
    }
    put(inner / "config.json", cfg)
    put(
        inner / "state.json",
        dict(
            phase="queued",
            job_id=f"inner-{lane}",
            thread_id="target",
            config_sha256=lc.sha(json.dumps(cfg, sort_keys=True).encode()),
        ),
    )
    previous = {
        sig: signal.signal(
            sig, lambda signum, frame: j.write(inner, "cancel.json", {"signal": signum})
        )
        for sig in (signal.SIGTERM, signal.SIGINT)
    }
    try:
        j.authority(outer_cfg, root, backend, horizon=None, delegated=binding)
        result = j.execute(inner, cfg, root, backend)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    if result["outcome"] != "succeeded":
        raise RuntimeError("synthetic inner failed: " + str(result["error"]))


class StandardParentEntryTests(unittest.TestCase):
    def test_standalone_standard_launch_reader_and_explicit_cancel_publication_priority(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts/dev"
            scripts.mkdir(parents=True)
            entry = (
                "import importlib.util\n"
                f"s=importlib.util.spec_from_file_location('fixture',{str(Path(__file__).resolve())!r})\n"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.fixture_main()\n"
            )
            (scripts / "research-job.py").write_text(entry)
            (scripts / "project-env.sh").symlink_to(MAIN / "scripts/dev/project-env.sh")
            contract = root / "contract.json"
            put(contract, {})
            cfg = config(
                root,
                [
                    sys.executable,
                    "-B",
                    "-c",
                    "import os,sys,time;assert sys.prefix==os.environ['QUORIDOR_PROJECT_ENV'];time.sleep(1)",
                ],
                contract,
            )
            cfg_ref = put(root / "job.json", cfg)
            install(root)
            handles = []
            state = j.submit(
                Path(cfg_ref["path"]),
                root / "runtime",
                root,
                Backend(root),
                supervisor_handles=handles,
            )
            try:
                launcher = state["launch"]["launcher"]
                lock = Path(os.environ["QUORIDOR_PROJECT_ENV"] + ".setup.lock").stat()
                readers = []
                proc = Path(f"/proc/{launcher['pid']}")
                for fd in proc.joinpath("fd").iterdir():
                    try:
                        info = fd.stat()
                        if (info.st_dev, info.st_ino) == (lock.st_dev, lock.st_ino):
                            if (
                                "FLOCK" in (text := proc.joinpath("fdinfo", fd.name).read_text())
                                and " READ " in text
                            ):
                                readers.append(fd.name)
                    except FileNotFoundError:
                        pass
                self.assertTrue(
                    readers,
                    "Actual owned wrapper must hold the selected environment's shared reader lock",
                )
                handles[0].wait(timeout=6)
                result = j.read(root / "runtime", "result.json")
                self.assertEqual(result["outcome"], "succeeded")
                self.assertTrue(result["direct_child_reaped"] and result["cleanup_complete"])
                calls = [
                    json.loads(line) for line in (root / "DB-calls.jsonl").read_text().splitlines()
                ]
                self.assertEqual(
                    {row["pid"] for row in calls}, {os.getpid(), state["supervisor"]["pid"]}
                )
                path = root / "cancel-test.json"
                self.assertTrue(
                    j.runtime.atomic_json(path, {"kind": "cohort_failure"}, replace=False)
                )
                j.runtime.atomic_json(path, {"requested_at": "explicit human cancel"})
                saved = path.read_bytes()
                self.assertFalse(
                    j.runtime.atomic_json(path, {"kind": "cohort_failure"}, replace=False)
                )
                self.assertEqual(path.read_bytes(), saved)
                self.assertFalse(j.runtime.alive(launcher))
                print(
                    json.dumps(
                        dict(
                            standalone_DB_calls=len(calls),
                            actual_reader_fds=readers,
                            selected_environment=True,
                            atomic_internal_cannot_overwrite_explicit=True,
                        )
                    ),
                    flush=True,
                )
            finally:
                if handles[0].poll() is None:
                    j.write(root / "runtime", "cancel.json", {})
                    handles[0].wait(timeout=6)

    def exercise(self, mode):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts/dev"
            scripts.mkdir(parents=True)
            # These are fake-backend entrypoints, not fake environment wrappers:
            # production submit -> actual project-env/flock/uv -> these Python
            # supervisors executes the candidate's unchanged production functions.
            entry = (
                "import importlib.util,sys\nfrom pathlib import Path\n"
                f"s=importlib.util.spec_from_file_location('entry_fixture',{str(Path(__file__).resolve())!r})\n"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
                "m.fixture_main()\n"
            )
            for name in ("research-job.py", "research-lifecycle.py"):
                (scripts / name).write_text(entry)
            (scripts / "project-env.sh").symlink_to(MAIN / "scripts/dev/project-env.sh")
            (root / "mode").write_text(mode)
            parent = dict(
                runtime=str(root / "shared/runtime"),
                output=str(root / "shared/execution"),
                intent_path=str(root / "shared/intent.json"),
                config_path=str(root / "shared/job.json"),
            )
            members = [
                dict(
                    lane=i,
                    job_runtime=str(root / f"lane-{i}/runtime"),
                    output=str(root / f"lane-{i}/sequence"),
                    settings_path=str(root / f"lane-{i}/settings.json"),
                )
                for i in range(8)
            ]
            control = root / "control"
            cohort_ref = put(
                control / "cohort.json",
                dict(
                    owner=str(root),
                    issue="work",
                    thread_id="target",
                    members=members,
                    control_root=str(control),
                    authority_parent=parent,
                ),
            )
            intent_ref = put(
                Path(parent["intent_path"]),
                dict(
                    kind="cohort", cwd=str(root), output=parent["output"], arena_cohort=cohort_ref
                ),
            )
            argv = [
                sys.executable,
                "-B",
                str(scripts / "research-lifecycle.py"),
                "cohort",
                "--intent",
                intent_ref["path"],
                "--sha256",
                intent_ref["sha256"],
            ]
            parent_cfg = config(root, argv, parent["intent_path"])
            parent_ref = put(Path(parent["config_path"]), parent_cfg)
            jobs = []
            for member in members:
                settings = put(
                    Path(member["settings_path"]),
                    dict(
                        kind="sequence",
                        arena_lane=member["lane"],
                        output=member["output"],
                        arena_cohort=cohort_ref,
                    ),
                )
                args = [
                    sys.executable,
                    "-B",
                    str(scripts / "research-lifecycle.py"),
                    "sequence",
                    "--intent",
                    settings["path"],
                    "--sha256",
                    settings["sha256"],
                ]
                jobs.append(
                    put(
                        root / f"lane-{member['lane']}/job.json",
                        {
                            **config(root, args, settings["path"]),
                            "authority_parent": dict(cohort=cohort_ref, lane=member["lane"]),
                        },
                    )
                )
            put(
                control / "launch.json",
                dict(cohort=cohort_ref, parent_config=parent_ref, job_configs=jobs),
            )
            install(root)
            handles = []
            started = time.monotonic()
            state = j.submit(
                Path(parent_ref["path"]),
                Path(parent["runtime"]),
                root,
                Backend(root),
                supervisor_handles=handles,
            )
            self.assertIn(state["phase"], ("starting", "running"))
            try:
                until = time.monotonic() + 12
                while sum((root / f"payload-{i}").exists() for i in range(8)) != 8:
                    if (
                        Path(parent["runtime"]) / "result.json"
                    ).exists() or time.monotonic() >= until:
                        logs = {
                            str(p.relative_to(root)): p.read_text()[-3000:]
                            for p in root.rglob("*.log")
                        }
                        logs.update(
                            {
                                str(p.relative_to(root)): p.read_text()[-3000:]
                                for p in root.rglob("result.json")
                            }
                        )
                        self.fail(json.dumps(logs))
                    time.sleep(0.02)
                actual = j.read(Path(parent["runtime"]), "state.json")
                binding = lc.cohort_parent_binding(cohort_ref)
                wrong = {**binding, "origin": {**binding["origin"], "job_id": "foreign-job"}}
                with self.assertRaisesRegex(lc.Refused, "parent job changed"):
                    lc.cohort_parent_check(wrong)
                reused = {
                    **binding,
                    "origin": {
                        **binding["origin"],
                        "child": {**binding["origin"]["child"], "start_ticks": "0"},
                    },
                }
                with self.assertRaises(lc.Refused):
                    lc.cohort_parent_check(reused)
                with self.assertRaises(lc.Refused):
                    lc.cohort_job_authority(lc.document(jobs[0]), Path(members[0]["job_runtime"]))
                if mode == "cancel":
                    j.write(Path(parent["runtime"]), "cancel.json", dict(requested_at=j.stamp()))
                elif mode == "parent_death":
                    os.kill(actual["child"]["pid"], signal.SIGKILL)
                # Actual setup.lock reader protection while all eight are alive.
                with open(os.environ["QUORIDOR_PROJECT_ENV"] + ".setup.lock") as lock:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handles[0].wait(timeout=14)
                result = j.read(Path(parent["runtime"]), "result.json")
                lane_results, identities = (
                    [],
                    [actual["supervisor"], actual["child"], actual["launch"]["launcher"]],
                )
                for member in members:
                    directory = Path(member["job_runtime"])
                    lane_state = j.read(directory, "state.json")
                    lane_result = j.read(directory, "result.json")
                    lane_results.append(lane_result)
                    self.assertTrue(lane_result["cleanup_complete"], lane_result)
                    inner = Path(member["output"]) / "run-000/runtime"
                    inner_result = j.read(inner, "result.json")
                    self.assertTrue(inner_result["cleanup_complete"], inner_result)
                    identities += [
                        lane_state["supervisor"],
                        lane_state["child"],
                        lane_state["launch"]["launcher"],
                        j.read(inner, "state.json")["child"],
                    ]
                    self.assertEqual(
                        j.read(directory, "notification.json")["status"], "delegated_to_parent"
                    )
                self.assertTrue(result["cleanup_complete"], result)
                self.assertEqual(result["remaining"], [])
                self.assertTrue(all(not j.runtime.alive(i) for i in identities), identities)
                calls = [
                    json.loads(line) for line in (root / "DB-calls.jsonl").read_text().splitlines()
                ]
                self.assertEqual({row["pid"] for row in calls}, {actual["supervisor"]["pid"]})
                self.assertGreaterEqual(len(calls), 1)
                self.assertEqual(
                    result["outcome"],
                    "succeeded"
                    if mode == "normal"
                    else "cancelled"
                    if mode == "cancel"
                    else "failed",
                )
                if mode == "child_failure":
                    self.assertIn("declared lane failed", result["error"])
                    self.assertFalse(
                        j.notification_stopped(Path(parent["runtime"]), parent_cfg, root)
                    )
                    exercise_notifications(self, Path(parent["runtime"]), parent_cfg, root)
                if mode == "cancel":
                    self.assertTrue(
                        j.notification_stopped(Path(parent["runtime"]), parent_cfg, root)
                    )
                print(
                    json.dumps(
                        dict(
                            mode=mode,
                            seconds=time.monotonic() - started,
                            DB_calls=len(calls),
                            DB_pids=sorted({r["pid"] for r in calls}),
                            payloads=8,
                            owned_exact_identities=identities,
                            all_absent=True,
                            actual_wrapper=True,
                            environment_reader_protected=True,
                        )
                    ),
                    flush=True,
                )
            finally:
                if handles[0].poll() is None:
                    j.write(Path(parent["runtime"]), "cancel.json", {})
                    try:
                        handles[0].wait(timeout=12)
                    except subprocess.TimeoutExpired:
                        handles[0].kill()
                        handles[0].wait(timeout=3)

    def test_standard_wrapper_eight_start_parent_only_DB_and_all_reap(self):
        self.exercise("normal")

    def test_standard_wrapper_cancel_parent_death_and_child_failure(self):
        for mode in ("cancel", "parent_death", "child_failure"):
            with self.subTest(mode=mode):
                self.exercise(mode)


def exercise_notifications(test, directory, cfg, root):
    original_stop = j.read(directory, "cancel.json")

    class Server:
        def __init__(self):
            self.wakes = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def read_thread(self, target):
            return dict(id=target, status=dict(type="idle"))

        async def request(self, method, params):
            test.assertEqual(method, "turn/start")
            self.wakes.append(params)
            return dict(turn=dict(id="one-normal-failed-completion"))

    class NotifyBackend:
        def __init__(self, fault):
            self.calls, self.fault, self.server = 0, fault, Server()

        async def connect(self, timeout):
            return self.server

        def issues(self, ids, *, timeout, check=None):
            self.calls += 1
            rows = [
                dict(id=i, status="in_progress", labels=[], assignee="codex:target") for i in ids
            ]
            if self.fault == "DBfailure":
                raise j.JobError("bounded fake unreadable authority")
            if self.fault == "pause":
                rows[0]["labels"] = ["paused-by-user"]
            if self.fault == "owner":
                rows[-1]["assignee"] = "codex:other"
            if self.fault == "closed":
                rows[-1]["status"] = "closed"
            if self.fault == "cancel_at_final_check" and self.calls == 2:
                j.write(directory, "cancel.json", {})
            return rows

    for fault in (
        "internal",
        "explicit_cancel",
        "pause",
        "owner",
        "closed",
        "DBfailure",
        "cancel_at_final_check",
    ):
        with test.subTest(notification=fault):
            j.write(directory, "cancel.json", {} if fault == "explicit_cancel" else original_stop)
            j.write(directory, "notification.json", dict(status="pending"))
            backend = NotifyBackend(fault)
            # Use an ordinary task-local dispatch lock; no real App Server or DB.
            with patch.object(j.client, "dispatch_lock", lambda _: lock_context()):
                first = asyncio.run(j.notify_once(directory, cfg, root, backend))
                second = asyncio.run(j.notify_once(directory, cfg, root, backend))
            test.assertEqual(len(backend.server.wakes), 1 if fault == "internal" else 0)
            test.assertEqual(second["status"], "delivered" if fault == "internal" else "cancelled")
            if fault == "internal":
                test.assertEqual(first["status"], "delivered")
                test.assertEqual(backend.calls, 2)
    j.write(directory, "cancel.json", original_stop)


@contextmanager
def lock_context():
    yield


if __name__ == "__main__":
    unittest.main()
