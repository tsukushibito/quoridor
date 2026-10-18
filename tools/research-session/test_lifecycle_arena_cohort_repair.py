"""New rejected-v2 reaching conditions only; no actual child, model or game."""

import ast
from contextlib import contextmanager
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

_loader = importlib.util.spec_from_file_location(
    "cohort_existing_fixture", Path(__file__).with_name("test_lifecycle_arena_cohort.py")
)
existing = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(existing)
lc = existing.lc
MiB = 1024**2


class CohortRepairBoundary(unittest.TestCase):
    def setUp(self):
        fixture = existing.ArenaCohortBoundary()
        fixture.setUp()  # Fixture construction only; none of its old assertions execute.
        self.addCleanup(fixture.doCleanups)
        for key in ("root", "shared", "cohort", "settings", "specs"):
            setattr(self, key, getattr(fixture, key))
        self.save = fixture.save
        for member in self.cohort["members"]:
            member["job_runtime"] = str(self.root / f"lane-{member['lane']}/outer-runtime")
        self.cohort_ref = self.save(self.shared / "cohort.json", self.cohort)
        self.infos = {}
        self.origins = {}
        self.settings_refs = []
        self.job_refs = []
        self.current = 300
        for lane, (member, settings, spec) in enumerate(
            zip(self.cohort["members"], self.settings, self.specs, strict=True)
        ):
            settings["arena_cohort"] = self.cohort_ref
            reference = self.save(Path(member["settings_path"]), settings)
            spec.update(settings=reference, arena_cohort=self.cohort_ref)
            self.settings_refs.append(reference)
            runtime = Path(member["job_runtime"])
            config = dict(
                argv=[
                    sys.executable,
                    "-B",
                    str(lc.ROOT / "scripts/dev/research-lifecycle.py"),
                    "sequence",
                    "--intent",
                    reference["path"],
                    "--sha256",
                    reference["sha256"],
                ],
                resource_contract=reference["path"],
                issue="unit-issue",
                thread_id="unit-thread",
                cwd=str(lc.ROOT),
            )
            self.job_refs.append(self.save(self.shared / f"job-{lane}.json", config))
            config_ref = self.save(runtime / "config.json", config)
            supervisor = self.identity(100 + lane, 1, 10 * MiB)
            child = self.identity(200 + lane, 100 + lane, 10 * MiB)
            fingerprint = lc.sha(json.dumps(config, sort_keys=True).encode())
            state = dict(
                job_id=f"unit-outer-{lane}",
                issue="unit-issue",
                thread_id="unit-thread",
                config_sha256=fingerprint,
                phase="running",
                supervisor=supervisor,
                child=child,
            )
            self.save(runtime / "state.json", state)
            origin = dict(
                runtime=str(runtime),
                job_id=state["job_id"],
                config=config_ref,
                config_sha256=fingerprint,
                supervisor=supervisor,
                child=child,
            )
            self.origins[lane] = origin
            self.save(
                Path(member["output"]) / "lane-origin.json",
                dict(
                    settings=reference,
                    originating_job=origin,
                ),
            )
        self.save(
            self.shared / "launch.json",
            dict(
                cohort=self.cohort_ref,
                monotonic=10.0,
                job_configs=self.job_refs,
                job_runtimes=[m["job_runtime"] for m in self.cohort["members"]],
            ),
        )

    def identity(self, pid, parent, rss):
        value = dict(pid=pid, start_ticks=str(pid + 10000), boot_id="unit-boot")
        self.infos[pid] = {**value, "parent": parent, "rss": rss, "state": "S"}
        return value

    def add_inner(self, lane):
        member = self.cohort["members"][lane]
        phase = Path(member["output"]) / "run-000"
        intent = self.save(phase / "intent.json", self.specs[lane])
        config = dict(
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
            issue="unit-issue",
            thread_id="unit-thread",
            cwd=str(lc.ROOT),
        )
        config_ref = self.save(phase / "runtime/config.json", config)
        child = self.identity(300 + lane, 200 + lane, 20 * MiB)
        self.identity(400 + lane, 300 + lane, 40 * MiB)
        state = dict(
            job_id=f"unit-inner-{lane}",
            phase="running",
            child=child,
            supervisor=self.origins[lane]["child"],
            config_sha256=lc.sha(json.dumps(config, sort_keys=True).encode()),
        )
        self.save(phase / "runtime/state.json", state)
        origin = dict(
            runtime=str(phase / "runtime"),
            job_id=state["job_id"],
            config=config_ref,
            supervisor=state["supervisor"],
            child=child,
        )
        self.save(phase / "operation/INCOMPLETE", dict(intent=intent, originating_job=origin))

    @contextmanager
    def kernel(self):
        def members(root, known):
            found = {root["pid"]}
            previous = set()
            while previous != found:
                previous = set(found)
                found.update(pid for pid, info in self.infos.items() if info["parent"] in found)
            return [lc.process.identity(self.infos[p]) for p in sorted(found)]

        with (
            patch.object(lc.process, "process_info", side_effect=lambda pid: self.infos.get(pid)),
            patch.object(lc.process, "members", side_effect=members),
            patch.object(
                lc.process,
                "alive",
                side_effect=lambda v: lc.process.identity(self.infos.get(v["pid"])) == v,
            ),
            patch.object(lc.process, "available_memory", return_value=20 * 1024**3),
            patch.object(lc.os, "getpid", side_effect=lambda: self.current),
            patch.object(lc.time, "monotonic", return_value=20.0),
        ):
            yield

    def test_R1_live_common_total_and_remaining_demand_use_maintained_RSS(self):
        for lane in range(3):
            self.add_inner(lane)
        with self.kernel():
            guard = lc.ArenaCohortResources(self.specs[0])
            facts = guard.check()
            self.assertEqual(len(facts["all_members"]), 12)
            self.assertEqual(len(facts["common_members"]), 6)
            self.assertEqual(sum(len(v) for v in facts["inner_members"].values()), 6)
            live = sum(info["rss"] for info in self.infos.values())
            threshold = guard.total_B - live + guard.reserve
            with patch.object(lc.process, "available_memory", return_value=threshold):
                guard.check(admit=True)
            with patch.object(lc.process, "available_memory", return_value=threshold - 1):
                with self.assertRaisesRegex(lc.Refused, "live plus remaining"):
                    guard.check(admit=True)
            for pid in range(100, 103):
                self.infos[pid]["rss"] = 100 * MiB
            with self.assertRaisesRegex(lc.process.CycleStopped, "memory_limit"):
                guard.check()  # Actual common >256MiB while each inner lane is small.
            for pid in range(100, 103):
                self.infos[pid]["rss"] = 10 * MiB
            for pid in range(400, 403):
                self.infos[pid]["rss"] = 4 * 1024**3
            with self.assertRaisesRegex(lc.process.CycleStopped, "memory_limit"):
                guard.check()

    def test_R2_full_retained_lane_and_prospective_bytes_are_not_spent_again(self):
        self.add_inner(0)
        with self.kernel():
            guard = lc.ArenaCohortResources(self.specs[0])
            prior = self.root / "lane-1/prior-archive.gz"
            prior.write_bytes(b"x" * (2 * MiB))
            with self.assertRaisesRegex(lc.Refused, "full canonical lane lifetime"):
                guard.check()
            prior.unlink()
            limits = lc.Limits.__new__(lc.Limits)
            limits.spec = self.specs[0]
            limits.charged_paths = [Path(self.specs[0]["output"])]
            limits.arena_cohort = (self.cohort, self.cohort["members"][0])
            limits.cohort_resources = guard
            limits.deadline = limits.pause_file = limits.output_limit = None
            limits.reserve = 4 * 1024**3
            limits.memory_limit = 3 * 1024**3
            prior = self.root / "lane-0/prior-archive.gz"
            prior.write_bytes(b"p" * (2 * MiB))
            with self.assertRaisesRegex(lc.Refused, "full canonical lane lifetime"):
                limits.check()
            prior.unlink()
            used = lc.allocated(self.root / "lane-0")
            limits.cohort_resources = SimpleNamespace(check=lambda: None)
            limits.spec["limits"]["owned_B"] = used
            limits.check()
            with self.assertRaisesRegex(lc.Refused, "owned allocation limit"):
                limits.check(extra_B=1)
            limits.arena_cohort = None
            limits.charged_paths = [self.root / "lane-0"]
            limits.check()  # The noncohort/prospective path still uses its declared roots.

    def test_R4_exact_outer_runtime_job_and_native_ancestry_are_joined(self):
        for lane in range(3):
            self.add_inner(lane)
        with self.kernel():
            facts = lc.arena_cohort_lifetime(self.specs[0])
            self.assertEqual(facts["origins"], self.origins)
            with patch.object(lc, "LEASE", self.root / "lease.lock"):
                with lc.operation_lease(self.specs[0], lc.lease):
                    self.assertTrue((self.shared / "start.json").exists())
            custody = Path(self.cohort["members"][1]["output"]) / "lane-origin.json"
            wrong = copy.deepcopy(self.origins[1])
            wrong["runtime"] = str(self.root / "lane-1/another-submission")
            self.save(custody, dict(settings=self.settings_refs[1], originating_job=wrong))
            with self.assertRaisesRegex(lc.Refused, "actual lane origin"):
                lc.arena_cohort_lifetime(self.specs[0])
            self.save(
                custody, dict(settings=self.settings_refs[1], originating_job=self.origins[1])
            )
            state_path = Path(self.cohort["members"][1]["job_runtime"]) / "state.json"
            state = json.loads(state_path.read_text())
            state["job_id"] = "another-real-submission-with-same-actor-settings-argv"
            self.save(state_path, state)
            with self.assertRaisesRegex(lc.Refused, "actual lane origin"):
                lc.arena_cohort_lifetime(self.specs[0])

    def test_R3_pre_inner_refusal_settles_pairs_retained_unknown_and_unentered(self):
        self.current = 200
        member = self.cohort["members"][0]
        self.save(
            Path(member["output"]) / "result.json",
            dict(
                settings=self.settings_refs[0],
                originating_job=self.origins[0],
                status="FAILED",
                completed_operations=0,
                operations=[],
            ),
        )
        for lane in range(3):
            member = self.cohort["members"][lane]
            config_ref = lc.document(self.specs[lane]["experiment"])["config"]
            config = lc.document(config_ref)
            config.update(run_id=f"unit-lane-{lane}", output=str(self.root / f"lane-{lane}/data"))
            config["arena"]["book"] = dict(
                openings=[
                    dict(
                        id=f"request-{2 * i + 7}",
                        lineage=f"lineage-{2 * i + 7}",
                        reference=dict(
                            settings=dict(family_id=2 * i + 7, canonical_family=f"canonical-{i}")
                        ),
                    )
                    for i in range(16)
                ]
            )
            self.save(Path(config_ref["path"]), config)
            experiment_path = Path(self.specs[lane]["experiment"]["path"])
            experiment = lc.document(self.specs[lane]["experiment"])
            experiment["config"] = lc.bound(config_ref["path"])[0]
            self.save(experiment_path, experiment)
            # Rebind this changed unit fixture before any mocked observation.
            for template in self.settings[lane]["runs"]:
                template["experiment"] = lc.bound(experiment_path)[0]
            self.specs[lane]["experiment"] = lc.bound(experiment_path)[0]
        self.rebind_settings()
        for lane in (1, 2):
            member = self.cohort["members"][lane]
            config = lc.document(lc.document(self.specs[lane]["experiment"])["config"])
            publication = self.save(
                Path(config["output"]) / "result.json",
                dict(
                    outcome_count=32,
                    report=dict(
                        run_id=config["run_id"],
                        planned=32,
                        arena_summary=dict(
                            census=dict(
                                planned_games=32,
                                started_games=32,
                                completed_games=31,
                                unknown_games=1,
                                complete_pairs=15,
                            ),
                            pairs=[
                                dict(family=f"native-{i}", lineage=f"lineage-{2 * i + 7}")
                                for i in range(15)
                            ],
                        ),
                    ),
                ),
            )
            self.save(
                Path(member["output"]) / "run-000/operation/manifest.json",
                dict(
                    status="PASS",
                    cleanup_complete=True,
                    data=dict(files=[publication]),
                ),
            )
        with (
            self.kernel(),
            patch.object(
                lc.process, "execute", side_effect=RuntimeError("one send failure")
            ) as send,
        ):
            lc.arena_cohort_progress(self.specs[0])
            packet = json.loads((self.shared / "first-progress.json").read_text())
            counts = packet["counts"]
            self.assertEqual(counts["completed_games_known"], 62)
            self.assertEqual(counts["retained_games_known"], 64)
            self.assertEqual(counts["unknown_games_known"], 2)
            self.assertEqual(counts["complete_pairs_known"], 30)
            self.assertEqual(counts["unentered_slots"], 3008)
            self.assertEqual(counts["terminal_planned_games"], 64)
            self.assertEqual(counts["inflight_slots"], 0)
            self.assertIsNone(packet["conditional_remaining_seconds"])
            self.assertEqual(packet["launch_to_pre_publication_snapshot_seconds"], 10.0)
            self.assertNotIn("inclusive_elapsed_seconds", packet)
            self.assertEqual(len(lc.document(packet["complete_pair_identities"])), 30)
            lc.arena_cohort_progress(self.specs[1])
            self.assertEqual(send.call_count, 1)

    def rebind_settings(self):
        for lane, member in enumerate(self.cohort["members"]):
            member["settings_body_sha256"] = lc.canonical_sha(
                {k: v for k, v in self.settings[lane].items() if k != "arena_cohort"}
            )
        self.cohort_ref = self.save(self.shared / "cohort.json", self.cohort)
        for lane, member in enumerate(self.cohort["members"]):
            self.settings[lane]["arena_cohort"] = self.cohort_ref
            reference = self.save(Path(member["settings_path"]), self.settings[lane])
            self.settings_refs[lane] = reference
            self.specs[lane].update(settings=reference, arena_cohort=self.cohort_ref)
            config = lc.document(self.job_refs[lane])
            config["argv"][-1] = reference["sha256"]
            self.job_refs[lane] = self.save(Path(self.job_refs[lane]["path"]), config)
            runtime = Path(member["job_runtime"])
            self.save(runtime / "config.json", config)
            state = json.loads((runtime / "state.json").read_text())
            state["config_sha256"] = lc.sha(json.dumps(config, sort_keys=True).encode())
            self.save(runtime / "state.json", state)
            self.origins[lane].update(
                config=lc.bound(runtime / "config.json")[0], config_sha256=state["config_sha256"]
            )
            self.save(
                Path(member["output"]) / "lane-origin.json",
                dict(settings=reference, originating_job=self.origins[lane]),
            )
        self.save(
            self.shared / "launch.json",
            dict(
                cohort=self.cohort_ref,
                monotonic=10.0,
                job_configs=self.job_refs,
                job_runtimes=[m["job_runtime"] for m in self.cohort["members"]],
            ),
        )
        terminal = Path(self.cohort["members"][0]["output"]) / "result.json"
        if terminal.exists():
            result = json.loads(terminal.read_text())
            result.update(settings=self.settings_refs[0], originating_job=self.origins[0])
            self.save(terminal, result)

    def test_job_supervisor_resource_callback_covers_pre_spawn_and_wait(self):
        from contextlib import ExitStack
        import signal
        import subprocess

        source = Path(__file__).resolve().parents[2] / "scripts/dev/research-job.py"
        tree = ast.parse(source.read_text())
        execute = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute"
        )
        for refusal_at in (1, 3):
            directory = self.root / f"job-case-{refusal_at}"
            directory.mkdir()
            state = dict(phase="queued", job_id="unit-new-job", thread_id="unit-thread")
            events = []
            process = SimpleNamespace(returncode=None)
            process.poll = lambda: process.returncode
            process.wait = lambda timeout: setattr(process, "returncode", -15)
            process.stdout = SimpleNamespace(close=lambda: events.append("pipe-close"))
            process.pid = 770077  # Inert metadata; no actual PID or fd is opened/signalled.

            class Resource:
                count = 0

                def check(self):
                    self.count += 1
                    events.append("resource-check")
                    if self.count == refusal_at:
                        raise RuntimeError("actual common RSS envelope refusal")

            guard = Resource()

            @contextmanager
            def configured(directory, config, root, resource):
                yield resource

            def publish(directory, name, value):
                if name == "state.json":
                    state.update(value)
                self.save(directory / name, value)

            def popen(*args, **kwargs):
                events.append("Popen")
                return process

            def stop(fd, sig):
                events.append("exact-pidfd-stop")
                process.returncode = -15

            tail = SimpleNamespace(
                thread=SimpleNamespace(
                    start=lambda: None, join=lambda timeout: None, is_alive=lambda: False
                ),
                bytes_seen=0,
                data=b"",
            )
            namespace = dict(
                read=lambda directory, name: state,
                write=publish,
                stamp=lambda: "unit-time",
                authority=lambda *args, **kwargs: dict(thread_id="unit-thread"),
                deadline_reached=lambda value: False,
                runtime=SimpleNamespace(
                    process_identity=lambda pid: dict(pid=pid, start_ticks="fixed", boot_id="unit"),
                    alive=lambda member: process.returncode is None,
                ),
                os=SimpleNamespace(
                    environ={},
                    getpid=lambda: 880088,
                    pidfd_open=lambda pid: 55,
                    close=lambda fd: events.append("pidfd-close"),
                ),
                subprocess=SimpleNamespace(
                    Popen=popen,
                    DEVNULL=subprocess.DEVNULL,
                    PIPE=subprocess.PIPE,
                    STDOUT=subprocess.STDOUT,
                    TimeoutExpired=subprocess.TimeoutExpired,
                ),
                signal=SimpleNamespace(
                    SIGTERM=signal.SIGTERM, SIGKILL=signal.SIGKILL, pidfd_send_signal=stop
                ),
                TailLog=lambda *args: tail,
                track_descendants=lambda child, known: [child],
                descendants_in_group=lambda pid, child: [],
                signal_members=lambda *args: None,
                time=SimpleNamespace(monotonic=lambda: 0.0, sleep=lambda seconds: None),
                ExitStack=ExitStack,
                configured_arena_resources=configured,
                sys=sys,
                json=json,
                JobError=ValueError,
            )
            exec(
                compile(ast.Module(body=[execute], type_ignores=[]), str(source), "exec"), namespace
            )
            config = dict(
                argv=["UNIT-NOT-EXECUTED"],
                cwd=str(self.root),
                end_at=None,
                max_runtime_seconds=None,
                log_max_bytes=1024,
                thread_id="unit-thread",
                control_interval_seconds=30,
            )
            result = namespace["execute"](directory, config, self.root, None, resources=guard)
            self.assertEqual(guard.count, refusal_at)
            self.assertTrue(result["cleanup_complete"])
            if refusal_at == 1:
                self.assertEqual(result["outcome"], "not_started")
                self.assertNotIn("Popen", events)
            else:
                self.assertEqual(result["outcome"], "control_error")
                self.assertTrue(result["direct_child_reaped"])
                self.assertIn("exact-pidfd-stop", events)
                self.assertIn("pipe-close", events)
                self.assertIn("pidfd-close", events)

    def test_outer_startup_factory_and_peer_need_the_original_live_chain(self):
        source = Path(__file__).resolve().parents[2] / "scripts/dev/research-job.py"
        node = next(
            n
            for n in ast.parse(source.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "configured_arena_resources"
        )
        module_spec = SimpleNamespace(
            name="unit_configured_cohort", loader=SimpleNamespace(exec_module=lambda module: None)
        )
        namespace = dict(
            contextmanager=contextmanager,
            Path=Path,
            json=json,
            hashlib=hashlib,
            sys=sys,
            importlib=SimpleNamespace(
                util=SimpleNamespace(
                    spec_from_file_location=lambda *args: module_spec,
                    module_from_spec=lambda spec: lc,
                )
            ),
            JobError=ValueError,
        )
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
        member = self.cohort["members"][0]
        runtime = Path(member["job_runtime"])
        state = json.loads((runtime / "state.json").read_text())
        state.pop("child")
        state["phase"] = "starting"
        self.save(runtime / "state.json", state)
        (Path(member["output"]) / "lane-origin.json").unlink()
        del self.infos[200]
        self.current = 100
        with self.kernel(), patch.object(lc, "LEASE", self.root / "source.lock"):
            config = lc.document(self.job_refs[0])
            with namespace["configured_arena_resources"](runtime, config, lc.ROOT, None) as guard:
                self.assertIsInstance(guard, lc.ArenaCohortResources)
                self.assertNotIn(0, guard.check()["origins"])
                self.assertEqual(len(guard.check()["all_members"]), 5)
            self.identity(200, 100, 10 * MiB)
            state.update(child=self.origins[0]["child"], phase="running")
            self.save(runtime / "state.json", state)
            self.save(
                Path(member["output"]) / "lane-origin.json",
                dict(settings=self.settings_refs[0], originating_job=self.origins[0]),
            )
            for lane in range(3):
                self.add_inner(lane)
            self.current = 300
            proc = self.root / "proc"
            native = proc / "401"
            native.mkdir(parents=True)
            (native / "cmdline").write_bytes(
                b"\0".join(x.encode() for x in self.specs[1]["argv"]) + b"\0"
            )
            (native / "task/401").mkdir(parents=True)

            def path(value):
                actual = Path(value)
                return (
                    proc / actual.relative_to("/proc") if actual.is_relative_to("/proc") else actual
                )

            def affinity(pid):
                return {12} if pid == 301 else {0} if pid == 201 else {8}

            with (
                patch.object(lc, "Path", side_effect=path),
                patch.object(lc.os, "sched_getaffinity", side_effect=affinity),
            ):
                self.assertTrue(lc.arena_cohort_peer(self.specs[0], 401))
                peer_state_path = Path(self.cohort["members"][1]["job_runtime"]) / "state.json"
                peer_state = json.loads(peer_state_path.read_text())
                peer_state["job_id"] = "same-actor-settings-another-original-job"
                self.save(peer_state_path, peer_state)
                with self.assertRaisesRegex(lc.Refused, "actual lane origin"):
                    lc.arena_cohort_peer(self.specs[0], 401)

    def test_sequence_publishes_pre_inner_terminal_before_notice_and_keeps_pause(self):
        self.current = 200
        for settings in self.settings:
            settings.update(owner=str(self.root), cwd=str(lc.ROOT))
        for lane, reference in enumerate(self.job_refs):
            config = lc.document(reference)
            config["end_at"] = None
            self.job_refs[lane] = self.save(Path(reference["path"]), config)
        self.rebind_settings()
        output = Path(self.cohort["members"][0]["output"])
        shutil.rmtree(output)
        calls = []

        def prepare(settings_ref, kind, index):
            projected = lc.arena_cohort_spec(settings_ref)
            phase = Path(projected["output"]).parent
            phase.mkdir(parents=True)
            return self.save(phase / "intent.json", projected)

        def notice(spec):
            saved = json.loads((output / "result.json").read_text())
            self.assertEqual(saved["status"], "FAILED")
            self.assertEqual(saved["completed_operations"], 0)
            self.assertEqual(saved["operations"], [])
            self.assertIn("unit before inner", saved["primary"]["message"])
            calls.append("terminal-already-published")
            raise lc.process.CycleStopped("cycle paused")

        job = SimpleNamespace(authority=lambda *args, **kwargs: None)
        with (
            self.kernel(),
            patch.object(lc, "project_python", return_value=Path(sys.executable)),
            patch.object(lc, "originating_job", return_value=self.origins[0]),
            patch.object(lc, "physical_and_quiet", side_effect=lc.Refused("unit before inner")),
            patch.object(lc, "arena_cohort_progress", side_effect=notice),
        ):
            with self.assertRaisesRegex(lc.Refused, "cancelled at terminal"):
                lc.sequence(
                    self.settings_refs[0], job_module=job, backend=object(), prepare=prepare
                )
        self.assertEqual(calls, ["terminal-already-published"])
        self.assertFalse((output / "run-000/runtime").exists())
        fact = json.loads((output / "terminal-progress-errors.json").read_text())
        self.assertEqual(fact["errors"][0]["type"], "CycleStopped")


if __name__ == "__main__":
    unittest.main()
