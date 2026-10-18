"""Finite cohort-parent control boundaries; artificial Python payloads, no engines."""

import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


j = module("cohort_control_job", ROOT / "scripts/dev/research-job.py")
lc = module("cohort_control_lifecycle", ROOT / "scripts/dev/research-lifecycle.py")
client = j.client


def normal_config(root, argv):
    contract = root / "contract.json"
    contract.write_text("{}")
    return dict(
        issue="work",
        goal_issue="goal",
        thread_id="target",
        cwd=str(root),
        argv=argv,
        end_at=None,
        notify_until=None,
        max_runtime_seconds=10,
        control_interval_seconds=30,
        notify_interval_seconds=1,
        request_timeout_seconds=1,
        log_max_bytes=4096,
        resource_contract=str(contract),
    )


def identity(pid):
    return j.runtime.process_identity(pid)


def fresh_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return lc.bound(path)[0]


class MetadataFixture:
    def setup_metadata(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.control = self.root / "shared/control"
        self.control.mkdir(parents=True)
        self.parent = dict(
            runtime=str(self.root / "shared/parent-runtime"),
            output=str(self.root / "shared/parent-output"),
            intent_path=str(self.root / "shared/parent-intent.json"),
            config_path=str(self.root / "shared/parent-config.json"),
        )
        members = [
            dict(
                lane=i,
                job_runtime=str(self.root / f"lane-{i}/runtime"),
                output=str(self.root / f"lane-{i}/sequence"),
                settings_path=str(self.root / f"lane-{i}/settings.json"),
            )
            for i in range(8)
        ]
        self.settings_bodies = []
        for member in members:
            member.update(
                roots=[str(self.root / f"lane-{member['lane']}")],
                family_B=960 * 1024**2,
                storage_B=96 * 1024**2,
            )
            body = dict(
                kind="sequence", arena_lane=member["lane"], output=member["output"], runs=[{}]
            )
            member["settings_body_sha256"] = lc.canonical_sha(body)
            self.settings_bodies.append(body)
        support = fresh_file(
            self.root / "shared/support.json",
            dict(
                resources=dict(family_RAM_B=9932111872),
                storage_budget=dict(whole_B=800 * 1024**2, roots=[str(self.root)]),
            ),
        )
        self.cohort = dict(
            support=support,
            global_controller_B=1792 * 1024**2,
            management_cpu_pool=[0, 18],
            shared_storage_B=32 * 1024**2,
            owner=str(self.root),
            issue="work",
            thread_id="target",
            members=members,
            control_root=str(self.control),
            shared_roots=[str(self.root / "shared")],
            authority_parent=self.parent,
        )
        self.cohort_ref = fresh_file(self.control / "cohort.json", self.cohort)
        intent = dict(
            kind="cohort",
            cwd=str(self.root),
            output=self.parent["output"],
            arena_cohort=self.cohort_ref,
        )
        ir = fresh_file(Path(self.parent["intent_path"]), intent)
        self.parent_config = normal_config(
            self.root,
            [
                sys.executable,
                "-B",
                str(lc.ROOT / "scripts/dev/research-lifecycle.py"),
                "cohort",
                "--intent",
                ir["path"],
                "--sha256",
                ir["sha256"],
            ],
        )
        self.parent_config["resource_contract"] = self.parent["intent_path"]
        parent_ref = fresh_file(Path(self.parent["config_path"]), self.parent_config)
        self.children = []
        refs = []
        for m in members:
            settings_ref = fresh_file(
                Path(m["settings_path"]),
                {**self.settings_bodies[m["lane"]], "arena_cohort": self.cohort_ref},
            )
            cfg = {
                **self.parent_config,
                "argv": [
                    sys.executable,
                    "-B",
                    str(lc.ROOT / "scripts/dev/research-lifecycle.py"),
                    "sequence",
                    "--intent",
                    m["settings_path"],
                    "--sha256",
                    settings_ref["sha256"],
                ],
                "resource_contract": m["settings_path"],
                "authority_parent": dict(cohort=self.cohort_ref, lane=m["lane"]),
            }
            refs.append(fresh_file(self.root / f"lane-{m['lane']}/selected-job.json", cfg))
            self.children.append(cfg)
        fresh_file(
            self.control / "launch.json",
            dict(
                cohort=self.cohort_ref,
                parent_config=parent_ref,
                job_configs=refs,
                job_runtimes=[m["job_runtime"] for m in members],
                monotonic=time.monotonic(),
            ),
        )
        self.supervisor = dict(pid=100, start_ticks="10", boot_id="boot")
        self.controller = dict(pid=101, start_ticks="11", boot_id="boot")
        self.state = dict(
            job_id="actual-parent",
            issue="work",
            thread_id="target",
            launch=dict(launcher=self.supervisor),
            config_sha256=hashlib.sha256(
                json.dumps(self.parent_config, sort_keys=True).encode()
            ).hexdigest(),
            supervisor=self.supervisor,
            child=self.controller,
            phase="running",
            authority_valid_until_monotonic=time.monotonic() + 100,
        )
        self.actual_config = fresh_file(
            Path(self.parent["runtime"]) / "config.json", self.parent_config
        )
        self.state_path = Path(self.parent["runtime"]) / "state.json"
        fresh_file(self.state_path, self.state)
        self.origin = dict(
            runtime=self.parent["runtime"],
            job_id=self.state["job_id"],
            config=self.actual_config,
            config_sha256=self.state["config_sha256"],
            supervisor=self.supervisor,
            child=self.controller,
        )
        fresh_file(
            Path(self.parent["output"]) / "parent-origin.json",
            dict(cohort=self.cohort_ref, originating_job=self.origin),
        )
        self.processes = {
            100: {**self.supervisor, "parent": 99, "state": "S", "rss": 1000},
            101: {**self.controller, "parent": 100, "state": "S", "rss": 1000},
        }
        real_bytes = Path.read_bytes

        def read_bytes(path):
            if str(path) == "/proc/101/cmdline":
                return b"\0".join(v.encode() for v in self.parent_config["argv"]) + b"\0"
            return real_bytes(path)

        self.addCleanup(patch.stopall)
        real_iterdir = Path.iterdir
        real_affinity = os.sched_getaffinity

        def thread_paths(path):
            parts = path.parts
            if (
                len(parts) == 4
                and parts[1] == "proc"
                and parts[3] == "task"
                and int(parts[2]) in self.processes
            ):
                item = self.processes[int(parts[2])]
                return iter(
                    path / str(tid)
                    for tid in item.get("thread_affinities", {int(parts[2]): {0, 18}})
                )
            return real_iterdir(path)

        def affinity(tid):
            for pid, item in self.processes.items():
                values = item.get("thread_affinities", {pid: {0, 18}})
                if tid in values:
                    return values[tid]
            return real_affinity(tid)

        patch.object(Path, "iterdir", thread_paths).start()
        patch.object(lc.os, "sched_getaffinity", side_effect=affinity).start()
        patch.object(
            lc.process, "process_info", side_effect=lambda pid: self.processes.get(pid)
        ).start()
        patch.object(lc.os, "getpid", return_value=101).start()
        patch.object(Path, "read_bytes", read_bytes).start()


class ParentOriginTests(MetadataFixture, unittest.TestCase):
    def setUp(self):
        self.setup_metadata()

    def test_standalone_keeps_its_own_pause_owner_and_error_authority(self):
        config = {k: v for k, v in self.children[0].items() if k != "authority_parent"}
        rows = [
            {"id": "goal", "status": "in_progress", "labels": []},
            {"id": "work", "status": "in_progress", "labels": [], "assignee": "codex:target"},
        ]
        calls = []

        def issues(ids, *, timeout):
            calls.append(ids)
            return rows

        backend = SimpleNamespace(issues=issues)
        self.assertEqual(
            j.authority(config, self.root, backend, horizon=None)["thread_id"], "target"
        )
        self.assertEqual(calls, [["goal", "work"]])
        for fault in ("pause", "closed", "owner", "failure"):
            rows[0]["labels"] = ["paused-by-user"] if fault == "pause" else []
            rows[1]["status"] = "closed" if fault == "closed" else "in_progress"
            rows[1]["assignee"] = "codex:other" if fault == "owner" else "codex:target"
            with self.subTest(fault=fault):
                if fault == "failure":
                    backend.issues = lambda *a, **k: (_ for _ in ()).throw(TimeoutError("DB"))
                with self.assertRaises((j.JobError, TimeoutError)):
                    j.authority(config, self.root, backend, horizon=None)


class ParentCommonAccountingTests(MetadataFixture, unittest.TestCase):
    def setUp(self):
        self.setup_metadata()

    def test_parent_DB_and_outer_roots_are_common_and_inner_roots_count_once_in_total(self):
        member = self.cohort["members"][0]
        cfg = self.children[0]
        cfg_ref = fresh_file(Path(member["job_runtime"]) / "config.json", cfg)

        def proc(pid, parent, rss):
            identity = dict(pid=pid, start_ticks=str(pid), boot_id="boot")
            self.processes[pid] = {**identity, "parent": parent, "state": "S", "rss": rss}
            return identity

        db = proc(102, 100, 527757312)
        supervisor, child = proc(110, 101, 10 * 1024**2), proc(111, 110, 10 * 1024**2)
        fingerprint = lc.sha(json.dumps(cfg, sort_keys=True).encode())
        state = dict(
            job_id="lane0",
            issue="work",
            thread_id="target",
            phase="running",
            supervisor=supervisor,
            child=child,
            config_sha256=fingerprint,
        )
        fresh_file(Path(member["job_runtime"]) / "state.json", state)
        origin = dict(
            runtime=member["job_runtime"],
            job_id="lane0",
            config=cfg_ref,
            config_sha256=fingerprint,
            supervisor=supervisor,
            child=child,
        )
        settings_ref = lc.bound(member["settings_path"])[0]
        fresh_file(
            Path(member["output"]) / "lane-origin.json",
            dict(settings=settings_ref, originating_job=origin),
        )
        phase = Path(member["output"]) / "run-000"
        intent = fresh_file(
            phase / "intent.json",
            dict(arena_cohort=self.cohort_ref, settings=settings_ref, selection_index=0),
        )
        inner_cfg = dict(
            argv=[
                sys.executable,
                "-B",
                str(lc.ROOT / "scripts/dev/research-lifecycle.py"),
                "run",
                "--intent",
                intent["path"],
                "--sha256",
                intent["sha256"],
            ],
            resource_contract=member["settings_path"],
            issue="work",
            thread_id="target",
        )
        fresh_file(phase / "runtime/config.json", inner_cfg)
        inner = proc(112, 111, 10 * 1024**2)
        native = proc(113, 112, 210821120)
        fresh_file(
            phase / "runtime/state.json",
            dict(
                child=inner,
                supervisor=child,
                config_sha256=lc.sha(json.dumps(inner_cfg, sort_keys=True).encode()),
            ),
        )
        spec = dict(arena_cohort=self.cohort_ref, limits=dict(host_reserve_B=4 * 1024**3))

        def members(root, known):
            found = {root["pid"]}
            while (
                added := {pid for pid, info in self.processes.items() if info["parent"] in found}
                - found
            ):
                found.update(added)
            return [lc.process.identity(self.processes[pid]) for pid in found]

        with (
            patch.object(lc, "arena_cohort", return_value=(self.cohort, member)),
            patch.object(lc.process, "members", side_effect=members),
            patch.object(lc.process, "available_memory", return_value=20 * 1024**3),
            patch.object(lc.os, "getpid", return_value=100),
        ):
            guard = lc.ArenaCohortResources(spec, outer_runtime=self.parent["runtime"])
            facts = guard.check()
            key = lambda v: tuple(v[k] for k in ("pid", "start_ticks", "boot_id"))
            self.assertIn(key(db), facts["common_members"])
            self.assertIn(key(native), facts["all_members"])
            self.assertNotIn(key(native), facts["common_members"])
            self.assertEqual(len(facts["all_members"]), 7)
            self.processes[102]["rss"] = 1792 * 1024**2
            with self.assertRaisesRegex(lc.process.CycleStopped, "memory_limit"):
                guard.check()
            self.processes[102]["rss"] = 527757312
            self.processes[113]["rss"] = 10 * 1024**3
            with self.assertRaisesRegex(lc.process.CycleStopped, "memory_limit"):
                guard.check()


class ParentFiniteLauncherTests(MetadataFixture, unittest.TestCase):
    def setUp(self):
        self.setup_metadata()

    def test_launcher_owns_all_eight_supervisor_handles_and_failure_refuses_next_entry(self):
        import shutil

        for failed in (False, True):
            with self.subTest(failed=failed):
                output = Path(self.parent["output"])
                shutil.rmtree(output)
                cancel = Path(self.parent["runtime"]) / "cancel.json"
                cancel.unlink(missing_ok=True)
                submitted = []
                binding = dict(parent=self.parent, origin=self.origin)

                def submit(config_path, directory, root, backend, *, supervisor_handles):
                    directory.mkdir(parents=True, exist_ok=True)
                    cfg = lc.document(lc.bound(config_path)[0])
                    j.write(directory, "config.json", cfg)
                    lane = cfg["authority_parent"]["lane"]
                    submitted.append(lane)
                    process = subprocess.Popen(
                        [sys.executable, "-B", "-c", "pass"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    supervisor_handles.append(process)
                    j.write(directory, "state.json", dict(job_id=f"new-{lane}", phase="finished"))
                    j.write(
                        directory,
                        "result.json",
                        dict(
                            outcome="failed" if failed and lane == 0 else "succeeded",
                            cleanup_complete=True,
                        ),
                    )
                    return dict(job_id=f"new-{lane}")

                adapter = SimpleNamespace(submit=submit, write=j.write)
                with (
                    patch.object(lc, "originating_job", return_value=self.origin),
                    patch.object(lc, "cohort_parent_binding", return_value=binding),
                    patch.object(lc, "cohort_parent_check", return_value=binding),
                ):
                    if failed:
                        with self.assertRaisesRegex(lc.Refused, "finite cohort stopped"):
                            lc.cohort_sequence(
                                lc.bound(self.parent["intent_path"])[0],
                                job_module=adapter,
                                backend=object(),
                            )
                    else:
                        lc.cohort_sequence(
                            lc.bound(self.parent["intent_path"])[0],
                            job_module=adapter,
                            backend=object(),
                        )
                self.assertEqual(sorted(submitted), list(range(8)))
                result = lc.document(lc.bound(output / "result.json")[0])
                self.assertEqual(len(result["supervisor_returns"]), 8)
                self.assertTrue(all(r["directwait_reaped"] for r in result["supervisor_returns"]))
                self.assertEqual(result["status"], "FAILED" if failed else "PASS")
                if failed:
                    with self.assertRaisesRegex(lc.Refused, "parent cancelled"):
                        lc.cohort_job_authority(self.children[0])

    def test_native_Limits_checks_lost_parent_before_other_resource_work(self):
        guardian = object.__new__(lc.Limits)
        guardian.arena_cohort = (self.cohort, self.cohort["members"][0])
        guardian.spec = dict(arena_cohort=self.cohort_ref)
        guardian.parent_control = dict(parent=self.parent, origin=self.origin)
        with (
            patch.object(
                lc, "cohort_parent_check", side_effect=lc.Refused("parent exact identity lost")
            ),
            patch.object(lc.process.CycleResources, "check") as resources,
        ):
            with self.assertRaisesRegex(lc.Refused, "identity lost"):
                guardian.check()
            resources.assert_not_called()


class BoundedReadControlTests(unittest.TestCase):
    def owned_read(self, code, check):
        commands = []
        popen = client.subprocess.Popen

        def owned(*args, **kwargs):
            child = popen(*args, **kwargs)
            commands.append(child)
            return child

        try:
            with patch.object(client.subprocess, "Popen", side_effect=owned):
                return client.command_json(
                    [sys.executable, "-u", "-c", code], timeout=3, max_bytes=65536, check=check
                )
        finally:
            for child in commands:
                self.assertIsNotNone(child.returncode)
                self.assertTrue(child.stdout.closed and child.stderr.closed)
                self.assertIsNone(j.runtime.process_identity(child.pid))

    def test_DB_wait_services_local_cancel_and_resources_and_reaps_DB_process(self):
        for cause in ("cancel", "resource"):
            calls = []

            def check():
                calls.append(time.monotonic())
                if len(calls) == 2:
                    raise ValueError(cause)

            start = time.monotonic()
            with self.subTest(cause=cause), self.assertRaisesRegex(ValueError, cause):
                self.owned_read("import time; time.sleep(30)", check)
            self.assertGreaterEqual(len(calls), 2)
            self.assertLess(time.monotonic() - start, 2)

    def test_SIGTERM_and_SIGINT_during_DB_wait_reach_existing_cancel_inlet(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            cancelled = []
            previous = signal.signal(sig, lambda signum, frame: cancelled.append(signum))
            timer = threading.Timer(0.1, os.kill, args=(os.getpid(), sig))
            timer.start()
            try:

                def check():
                    if cancelled:
                        raise ValueError("local signal cancel")

                with (
                    self.subTest(signal=sig),
                    self.assertRaisesRegex(ValueError, "local signal cancel"),
                ):
                    self.owned_read("import time; time.sleep(30)", check)
                self.assertEqual(cancelled, [sig])
            finally:
                timer.join()
                signal.signal(sig, previous)

    def test_nonzero_keeps_bounded_stdout_stderr_and_exit_separate(self):
        with self.assertRaises(client.SessionError) as caught:
            self.owned_read(
                "import sys; print('saved-out'); print('saved-err',file=sys.stderr);sys.exit(7)",
                lambda: None,
            )
        self.assertIn("exit 7", str(caught.exception))
        self.assertIn("saved-out", str(caught.exception))
        self.assertIn("saved-err", str(caught.exception))


def artificial_lane(directory, config, root, binding):
    j._lifecycle_modules[root] = lc

    def verified_binding(*args, **kwargs):
        lc.cohort_parent_check(binding)
        return dict(
            binding,
            cohort=config["authority_parent"]["cohort"],
            delegated_lane=config["authority_parent"]["lane"],
            delegated_config_sha256=lc.canonical_sha(config),
        )

    lc.cohort_job_authority = verified_binding
    forbidden = SimpleNamespace(
        issues=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("child attempted DB"))
    )
    j.execute(directory, config, root, forbidden)


class ActualParentLossTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        parent_argv = [sys.executable, "-B", "-c", "import time;time.sleep(30)"]
        self.parent = subprocess.Popen(parent_argv)
        self.addCleanup(self.finish_parent)
        runtime = self.root / "parent-runtime"
        cfg_ref = fresh_file(runtime / "config.json", {"argv": parent_argv})
        cfg_sha = cfg_ref["sha256"]
        self.origin = dict(
            job_id="actual-NN0-parent",
            config=cfg_ref,
            config_sha256=cfg_sha,
            supervisor=identity(os.getpid()),
            child=identity(self.parent.pid),
        )
        self.state = dict(
            phase="running",
            **{k: self.origin[k] for k in ("job_id", "config_sha256", "supervisor", "child")},
            authority_valid_until_monotonic=time.monotonic() + 100,
        )
        fresh_file(runtime / "state.json", self.state)
        self.binding = dict(
            parent=dict(runtime=str(runtime)),
            origin=self.origin,
            management_cpu_pool=sorted(os.sched_getaffinity(0)),
        )

    def finish_parent(self):
        if self.parent.poll() is None:
            self.parent.terminate()
        self.parent.wait(timeout=3)

    def lanes(self, count, seconds):
        children, directories = [], []
        offset = len(list(self.root.glob("lane-*")))
        for index in range(offset, offset + count):
            directory = self.root / f"lane-{index}"
            directory.mkdir()
            marker = directory / "ready"
            argv = [
                sys.executable,
                "-B",
                "-c",
                "import os,time;from pathlib import Path;Path("
                + repr(str(marker))
                + ").write_text(str(os.getpid()));time.sleep("
                + str(seconds)
                + ")",
            ]
            config = normal_config(self.root, argv)
            config["authority_parent"] = dict(cohort={}, lane=index)
            j.write(directory, "config.json", config)
            j.write(
                directory,
                "state.json",
                dict(phase="queued", job_id=f"lane-{index}", thread_id="target"),
            )
            child = multiprocessing.get_context("fork").Process(
                target=artificial_lane, args=(directory, config, self.root, self.binding)
            )
            child.start()
            children.append(child)
            directories.append(directory)
        return children, directories

    def returned(self, children, directories):
        results = []
        for child, directory in zip(children, directories, strict=True):
            child.join(timeout=8)
            if child.is_alive():
                child.kill()
                child.join(timeout=3)
                self.fail("NN0 guardian did not return within finite cleanup allowance")
            self.assertEqual(child.exitcode, 0)
            result = j.read(directory, "result.json")
            self.assertTrue(result["cleanup_complete"])
            if result["outcome"] != "not_started":
                self.assertTrue(result["direct_child_reaped"])
                self.assertEqual(result["remaining"], [])
            state = j.read(directory, "state.json")
            if state.get("child"):
                self.assertFalse(j.runtime.alive(state["child"]))
            results.append(result)
        return results

    def test_eight_artificial_payloads_finish_with_zero_child_DB_reads_and_exact_reap(self):
        children, directories = self.lanes(8, 0.15)
        results = self.returned(children, directories)
        self.assertEqual([r["outcome"] for r in results], ["succeeded"] * 8)

    def test_parent_SIGKILL_stops_owned_payload_and_refuses_next_operation(self):
        children, directories = self.lanes(1, 30)
        deadline = time.monotonic() + 4
        while not (directories[0] / "ready").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue((directories[0] / "ready").exists())
        start = time.monotonic()
        self.parent.kill()
        self.parent.wait(timeout=3)
        results = self.returned(children, directories)
        self.assertEqual(results[0]["outcome"], "control_error")
        self.assertIn("identity lost", results[0]["error"])
        self.assertLess(time.monotonic() - start, 4)
        # A later operation gets no payload, even though the last authority deadline remains future.
        children, directories = self.lanes(1, 0.1)
        result = self.returned(children, directories)[0]
        self.assertEqual(result["outcome"], "not_started")
        self.assertFalse((directories[0] / "ready").exists())

    def test_parent_cancel_or_resource_control_stops_child_before_any_next_payload(self):
        children, directories = self.lanes(1, 30)
        deadline = time.monotonic() + 4
        while not (directories[0] / "ready").exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue((directories[0] / "ready").exists())
        fresh_file(
            Path(self.binding["parent"]["runtime"]) / "cancel.json",
            {"reason": "parent detected pause/owner/DB failure"},
        )
        results = self.returned(children, directories)
        self.assertEqual(results[0]["outcome"], "control_error")
        self.assertIn("cancelled", results[0]["error"])


def artificial_authority_parent(directory, config, root, fault):
    # The entry/periodic loop and signal handlers are production code. Only the
    # DB port and heavy admission facts are controlled by this artificial fixture.
    from contextlib import contextmanager

    calls = []

    class Backend:
        def issues(self, ids, *, timeout, check=None):
            calls.append(dict(pid=os.getpid(), at=time.monotonic(), ids=ids))
            (root / "authority-calls.json").write_text(json.dumps(calls))
            rows = [
                {"id": "goal", "status": "in_progress", "labels": []},
                {"id": "work", "status": "in_progress", "labels": [], "assignee": "codex:target"},
            ]
            if len(calls) > 1:
                if fault.startswith("wait_"):
                    (root / "DB-waiting").write_text("actual callback wait")
                    until = time.monotonic() + 4
                    while time.monotonic() < until:
                        check()
                        time.sleep(0.03)
                if fault == "pause":
                    rows[0]["labels"] = ["paused-by-user"]
                elif fault == "closed":
                    rows[1]["status"] = "closed"
                elif fault == "owner":
                    rows[1]["assignee"] = "codex:other"
                elif fault == "failure":
                    raise TimeoutError("bounded DB failure")
            return rows

    class Resources:
        def check(self):
            if (root / "resource-refusal").exists():
                raise ValueError("actual local resource refusal")

    @contextmanager
    def resources(*args, **kwargs):
        yield Resources()

    j.cohort_parent_command = lambda config, root: True
    j.configured_arena_resources = resources
    j.watch_notification = lambda *args: None
    j.run(directory, root, Backend())


class ParentReadPropagationTests(unittest.TestCase):
    def exercise(self, fault):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        directory = root / "parent-runtime"
        directory.mkdir()
        ready = root / "parent-payload-ready"
        argv = [
            sys.executable,
            "-B",
            "-c",
            "import time;from pathlib import Path;Path("
            + repr(str(ready))
            + ").write_text('ready');time.sleep(30)",
        ]
        cfg = normal_config(root, argv)
        cfg["control_interval_seconds"] = 1
        j.write(directory, "config.json", cfg)
        j.write(
            directory,
            "state.json",
            dict(
                phase="queued",
                job_id="parent",
                thread_id="target",
                config_sha256=lc.sha(json.dumps(cfg, sort_keys=True).encode()),
            ),
        )
        parent = multiprocessing.get_context("fork").Process(
            target=artificial_authority_parent, args=(directory, cfg, root, fault)
        )
        parent.start()
        deadline = time.monotonic() + 4
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(ready.exists())
        state = j.read(directory, "state.json")
        config_ref = lc.bound(directory / "config.json")[0]
        # The production execute-created state and real OS parent/child pair are used.
        state.setdefault("config_sha256", lc.sha(json.dumps(cfg, sort_keys=True).encode()))
        j.write(directory, "state.json", state)
        binding = dict(
            parent=dict(runtime=str(directory)),
            management_cpu_pool=sorted(os.sched_getaffinity(0)),
            origin=dict(
                job_id=state["job_id"],
                config=config_ref,
                config_sha256=state["config_sha256"],
                supervisor=state["supervisor"],
                child=state["child"],
            ),
        )
        lane = root / "lane-runtime"
        lane.mkdir()
        marker = root / "lane-native-ready"
        lane_cfg = normal_config(
            root,
            [
                sys.executable,
                "-B",
                "-c",
                "import time;from pathlib import Path;Path("
                + repr(str(marker))
                + ").write_text('ready');time.sleep(30)",
            ],
        )
        lane_cfg["authority_parent"] = dict(cohort={}, lane=0)
        j.write(lane, "config.json", lane_cfg)
        j.write(lane, "state.json", dict(phase="queued", job_id="lane", thread_id="target"))
        child = multiprocessing.get_context("fork").Process(
            target=artificial_lane, args=(lane, lane_cfg, root, binding)
        )
        child.start()
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(marker.exists())
        if fault.startswith("wait_"):
            while not (root / "DB-waiting").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue((root / "DB-waiting").exists())
            if fault == "wait_cancel":
                j.write(directory, "cancel.json", {})
            elif fault == "wait_resource":
                (root / "resource-refusal").write_text("refused")
            else:
                os.kill(parent.pid, signal.SIGTERM if fault == "wait_TERM" else signal.SIGINT)
        began = time.monotonic()
        for process in (parent, child):
            process.join(timeout=7)
            if process.is_alive():
                process.kill()
                process.join(timeout=3)
                self.fail("controlled parent/lane failed finite stop")
            self.assertEqual(process.exitcode, 0)
        parent_result = j.read(directory, "result.json")
        child_result = j.read(lane, "result.json")
        self.assertTrue(parent_result["direct_child_reaped"] and parent_result["cleanup_complete"])
        self.assertTrue(child_result["direct_child_reaped"] and child_result["cleanup_complete"])
        self.assertEqual(parent_result["remaining"], [])
        self.assertEqual(child_result["remaining"], [])
        self.assertFalse(j.runtime.alive(j.read(lane, "state.json")["child"]))
        calls = json.loads((root / "authority-calls.json").read_text())
        self.assertEqual(len(calls), 2)
        self.assertEqual({r["pid"] for r in calls}, {parent.pid})
        self.assertNotEqual(child_result["outcome"], "succeeded")
        self.assertLess(time.monotonic() - began, 5)

    def test_parent_pause_close_owner_and_DBfailure_stop_owned_child(self):
        for fault in ("pause", "closed", "owner", "failure"):
            with self.subTest(fault=fault):
                self.exercise(fault)

    def test_parent_DB_wait_still_processes_local_cancel_resource_TERM_and_INT(self):
        for fault in ("wait_cancel", "wait_resource", "wait_TERM", "wait_INT"):
            with self.subTest(fault=fault):
                self.exercise(fault)


class ParentRepairReadTests(unittest.TestCase):
    def test_closed_both_pipes_live_child_still_checks_cancel_resource_and_deadline(self):
        factory = client.selectors.DefaultSelector
        for cause in ("cancel", "resource", "deadline"):
            selectors_seen, observed_EOF = [], []

            def selector():
                value = factory()
                selectors_seen.append(value)
                return value

            def check():
                if selectors_seen and not selectors_seen[0].get_map():
                    observed_EOF.append(time.monotonic())
                    if cause != "deadline":
                        raise ValueError(cause)

            began = time.monotonic()
            with (
                self.subTest(cause=cause),
                patch.object(client.selectors, "DefaultSelector", side_effect=selector),
            ):
                with self.assertRaisesRegex(
                    client.SessionError if cause == "deadline" else ValueError,
                    "timed out" if cause == "deadline" else cause,
                ):
                    BoundedReadControlTests.owned_read(
                        self, "import os,time;os.close(1);os.close(2);time.sleep(30)", check
                    )
            self.assertTrue(observed_EOF)
            self.assertLess(time.monotonic() - began, 4.5)
            self.assertFalse(selectors_seen[0].get_map())

    def test_wait_and_selector_cleanup_faults_keep_primary_and_attempt_both_pipe_closes(self):
        popen, selector_factory = client.subprocess.Popen, client.selectors.DefaultSelector
        children, selectors_seen = [], []

        def owned(*args, **kwargs):
            child = popen(*args, **kwargs)
            child.original_wait = child.wait
            child.wait = unittest.mock.Mock(side_effect=OSError("injected finite wait failure"))
            children.append(child)
            return child

        def selector():
            value = selector_factory()
            original_close = value.close
            value.close = unittest.mock.Mock(side_effect=OSError("injected selector close failure"))
            selectors_seen.append((value, original_close))
            return value

        def primary():
            raise ValueError("original local cancel")

        try:
            with (
                patch.object(client.subprocess, "Popen", side_effect=owned),
                patch.object(client.selectors, "DefaultSelector", side_effect=selector),
            ):
                with self.assertRaises(BaseExceptionGroup) as caught:
                    client.command_json(
                        [sys.executable, "-c", "import time;time.sleep(30)"],
                        timeout=1,
                        max_bytes=65536,
                        check=primary,
                    )
            messages = [str(e) for e in caught.exception.exceptions]
            self.assertEqual(messages[0], "original local cancel")
            self.assertTrue(any("finite wait failure" in m for m in messages))
            self.assertTrue(any("selector close failure" in m for m in messages))
            self.assertTrue(children[0].stdout.closed and children[0].stderr.closed)
            self.assertTrue(
                all(call.kwargs["timeout"] <= 3 for call in children[0].wait.call_args_list)
            )
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.original_wait(timeout=3)
            for _, close in selectors_seen:
                close()


class ParentRepairMetadataTests(MetadataFixture, unittest.TestCase):
    def setUp(self):
        self.setup_metadata()

    def test_cancel_write_and_one_wait_fault_do_not_skip_siblings_handlers_or_result(self):
        import shutil

        shutil.rmtree(self.parent["output"])
        actual_children, submit_lock = [], threading.Lock()
        old_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
        write_failures = []

        def write(directory, name, data, *, replace=True):
            if (
                directory == Path(self.parent["runtime"])
                and name == "cancel.json"
                and not write_failures
            ):
                write_failures.append(name)
                raise OSError("injected parent cancel publication failure")
            j.write(directory, name, data, replace=replace)

        def submit(config_path, directory, root, backend, *, supervisor_handles):
            directory.mkdir(parents=True)
            cfg = lc.document(lc.bound(config_path)[0])
            lane = cfg["authority_parent"]["lane"]
            child = subprocess.Popen(
                [sys.executable, "-c", "pass"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with submit_lock:
                actual_children.append(child)
                if not supervisor_handles:
                    original_wait = child.wait
                    calls = []

                    def wait(*, timeout):
                        calls.append(timeout)
                        if len(calls) == 1:
                            raise OSError("injected first supervisor wait failure")
                        return original_wait(timeout=timeout)

                    child.wait = wait
                supervisor_handles.append(child)
            j.write(directory, "state.json", dict(job_id=f"new-{lane}", phase="finished"))
            j.write(
                directory,
                "result.json",
                dict(outcome="failed" if lane == 0 else "succeeded", cleanup_complete=True),
            )
            return dict(job_id=f"new-{lane}")

        binding = dict(parent=self.parent, origin=self.origin)
        try:
            with (
                patch.object(lc, "originating_job", return_value=self.origin),
                patch.object(lc, "cohort_parent_binding", return_value=binding),
                patch.object(lc, "cohort_parent_check", return_value=binding),
            ):
                with self.assertRaises(BaseExceptionGroup) as caught:
                    lc.cohort_sequence(
                        lc.bound(self.parent["intent_path"])[0],
                        job_module=SimpleNamespace(submit=submit, write=write),
                        backend=object(),
                    )
            self.assertIn("finite cohort stopped", str(caught.exception.exceptions[0]))
            result = lc.document(lc.bound(Path(self.parent["output"]) / "result.json")[0])
            self.assertEqual(result["status"], "FAILED")
            self.assertIsNotNone(result["primary"])
            self.assertEqual(len(result["supervisor_returns"]), 8)
            self.assertTrue(
                all(
                    r["directwait_reaped"] and not r["remaining"]
                    for r in result["supervisor_returns"]
                )
            )
            self.assertTrue(
                any("parent cancel publication failure" in str(r) for r in result["secondary"])
            )
            self.assertTrue(any("supervisor wait failure" in str(r) for r in result["secondary"]))
            self.assertEqual({sig: signal.getsignal(sig) for sig in old_handlers}, old_handlers)
            self.assertTrue(all(child.poll() is not None for child in actual_children))
        finally:
            for child in actual_children:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=3)


class ParentRepairCleanupBudgetTests(MetadataFixture, unittest.TestCase):
    def test_shared_slow_child_cutoffs_overlap_and_leave_parent_finalization_budget(self):
        import shutil

        for variant in ("normal", "cancelled", "normal-stuck"):
            with self.subTest(variant=variant):
                self.setup_metadata()
                shutil.rmtree(self.parent["output"])
                clock = SimpleNamespace(now=1000.0)
                events, handles = [], []
                old_handlers = {
                    sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)
                }

                def sleep(seconds):
                    self.assertGreaterEqual(seconds, 0)
                    clock.now += seconds

                class Handle:
                    stdin = stdout = stderr = None

                    def __init__(handle, lane):
                        handle.pid = 2000 + lane
                        handle.lane = lane
                        handle.exit_at = (
                            1000.3 + lane * 0.01 if variant == "normal" else float("inf")
                        )
                        handle.returncode = None
                        handle.wait_faulted = False

                    def wait(handle, *, timeout):
                        self.assertEqual(
                            timeout, 0, "Never stack a fresh blocking timeout per child"
                        )
                        events.append(("wait", handle.lane, clock.now, timeout))
                        if variant == "cancelled" and handle.lane == 4 and not handle.wait_faulted:
                            handle.wait_faulted = True
                            raise OSError("one overlapping wait fault")
                        if clock.now < handle.exit_at:
                            raise subprocess.TimeoutExpired("slow-supervisor", timeout)
                        handle.returncode = 0
                        return 0

                    def terminate(handle):
                        events.append(("TERM", handle.lane, clock.now))
                        if variant == "cancelled" and handle.lane == 0:
                            raise OSError("one TERM obligation fault")

                    def kill(handle):
                        events.append(("KILL", handle.lane, clock.now))
                        if handle.lane != 7:
                            handle.exit_at = clock.now + 0.1

                    def poll(handle):
                        return 0 if clock.now >= handle.exit_at else None

                def submit(config_path, directory, root, backend, *, supervisor_handles):
                    cfg = lc.document(lc.bound(config_path)[0])
                    lane = cfg["authority_parent"]["lane"]
                    directory.mkdir(parents=True)
                    j.write(directory, "state.json", dict(job_id=f"new-{lane}", phase="finished"))
                    if variant != "cancelled" or lane == 0:
                        j.write(
                            directory,
                            "result.json",
                            dict(
                                outcome="failed" if variant == "cancelled" else "succeeded",
                                cleanup_complete=True,
                            ),
                        )
                    handle = Handle(lane)
                    supervisor_handles.append(handle)
                    handles.append(handle)
                    return dict(job_id=f"new-{lane}")

                class Pool:
                    def __init__(pool, *, max_workers):
                        self.assertEqual(max_workers, 8)

                    def __enter__(pool):
                        return pool

                    def __exit__(pool, *args):
                        return False

                    def submit(pool, function, *args, **kwargs):
                        result = function(*args, **kwargs)
                        return SimpleNamespace(result=lambda timeout: result)

                binding = dict(parent=self.parent, origin=self.origin)
                try:
                    with (
                        patch.object(lc, "originating_job", return_value=self.origin),
                        patch.object(lc, "cohort_parent_binding", return_value=binding),
                        patch.object(lc, "cohort_parent_check", return_value=binding),
                        patch.object(lc.time, "monotonic", side_effect=lambda: clock.now),
                        patch.object(lc.time, "sleep", side_effect=sleep),
                        patch("concurrent.futures.ThreadPoolExecutor", Pool),
                    ):
                        if variant == "normal":
                            lc.cohort_sequence(
                                lc.bound(self.parent["intent_path"])[0],
                                job_module=SimpleNamespace(submit=submit, write=j.write),
                                backend=object(),
                            )
                        else:
                            with self.assertRaises(
                                BaseExceptionGroup if variant == "cancelled" else lc.Refused
                            ):
                                lc.cohort_sequence(
                                    lc.bound(self.parent["intent_path"])[0],
                                    job_module=SimpleNamespace(submit=submit, write=j.write),
                                    backend=object(),
                                )
                    result = lc.document(lc.bound(Path(self.parent["output"]) / "result.json")[0])
                    budget = result["cleanup_budget"]
                    base = budget["base_monotonic"]
                    self.assertLessEqual(clock.now - base, 35.001)
                    self.assertLess(clock.now, budget["parent_grace_until"])
                    self.assertEqual(budget["parent_grace_until"] - budget["directwait_until"], 10)
                    self.assertEqual(len(result["supervisor_returns"]), 8)
                    self.assertEqual(
                        {sig: signal.getsignal(sig) for sig in old_handlers}, old_handlers
                    )
                    if variant == "normal":
                        self.assertEqual(result["status"], "PASS")
                        self.assertFalse(any(e[0] in ("TERM", "KILL") for e in events))
                        self.assertLess(clock.now - base, 1)
                    else:
                        self.assertEqual(result["status"], "FAILED")
                        term = [e for e in events if e[0] == "TERM"]
                        kill = [e for e in events if e[0] == "KILL"]
                        self.assertEqual(len(term), 8)
                        self.assertEqual(len(kill), 8)
                        self.assertGreaterEqual(min(e[2] for e in term) - base, 30)
                        self.assertGreaterEqual(min(e[2] for e in kill) - base, 32)
                        self.assertLessEqual(
                            max(e[2] for e in term) - min(e[2] for e in term), 0.001
                        )
                        self.assertLessEqual(
                            max(e[2] for e in kill) - min(e[2] for e in kill), 0.001
                        )
                        self.assertEqual(
                            sum(r["directwait_reaped"] for r in result["supervisor_returns"]), 7
                        )
                        self.assertEqual(
                            result["supervisor_returns"][7]["remaining_observation"], "LIVE"
                        )
                        self.assertTrue(result["supervisor_returns"][7]["remaining"])
                        self.assertIsNotNone(result["primary"])
                    print(
                        "CLEANUP_BUDGET_PROOF",
                        variant,
                        "virtual_seconds",
                        clock.now - base,
                        "reaped",
                        sum(r["directwait_reaped"] for r in result["supervisor_returns"]),
                        flush=True,
                    )
                finally:
                    patch.stopall()
                    self.temp.cleanup()


if __name__ == "__main__":
    unittest.main()
