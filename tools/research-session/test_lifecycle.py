"""New lifecycle ports: no real Cargo/native/model/Search or old successful suite."""

import copy
from contextlib import contextmanager, nullcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import quoridor_runtime
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get("RESEARCH_TEST_ROOT", Path(__file__).resolve().parents[2]))
if os.environ.get("RESEARCH_CYCLE_SOURCE"):
    quoridor_runtime.__path__.insert(0, str(Path(os.environ["RESEARCH_CYCLE_SOURCE"]).parent))
spec = importlib.util.spec_from_file_location(
    "research_lifecycle",
    os.environ.get("RESEARCH_LIFECYCLE_SOURCE", ROOT / "scripts/dev/research-lifecycle.py"),
)
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)
ORIGINATING_JOB = lc.originating_job


def ref(path):
    return lc.bound(path, 32 * 1024 * 1024)[0]


class LifecycleAllocationTests(unittest.TestCase):
    def test_hardlink_accounting_and_distinct_growth_refusal(self):
        tmp = ROOT / ".artifacts/research-lifecycle-maintenance/test-TMP"
        tmp.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="inode-accounting-", dir=tmp) as name:
            parent = Path(name)
            first, second = parent / "first", parent / "second"
            first.mkdir()
            second.mkdir()
            data = first / "data"
            data.write_bytes(b"bounded filesystem fixture\n" * 2048)
            os.link(data, first / "same-inode")
            os.link(data, second / "same-inode")
            observed = subprocess.check_output(
                ["du", "--summarize", "--block-size=1", "--", str(first), str(second)],
                text=True,
                timeout=10,
            )
            expected = sum(int(line.split()[0]) for line in observed.splitlines())
            seen = set()
            self.assertEqual(
                lc.allocated(first, seen=seen) + lc.allocated(second, seen=seen),
                expected,
            )
            self.assertEqual(lc.allocated(parent / "missing"), 0)
            info = data.stat()
            self.assertEqual(
                lc.allocated(data, seen={(info.st_dev + 1, info.st_ino)}),
                info.st_blocks * 512,
            )

            # Exercise the owning limit check; unrelated process/RAM admission is stubbed.
            resources = object.__new__(lc.Limits)
            resources.spec = {
                "kind": "run",
                "owner": str(parent),
                "limits": {"owned_B": expected, "free_B": 1},
            }
            resources.charged_paths = [first, second]
            with patch.object(lc.process.CycleResources, "check", return_value=None):
                resources.check()
                copy = second / "distinct-inode"
                copy.write_bytes(data.read_bytes())
                self.assertNotEqual(copy.stat().st_ino, info.st_ino)
                with self.assertRaisesRegex(lc.Refused, "owned allocation limit"):
                    resources.check()
                copy.unlink()
                symlink = second / "refused-symlink"
                symlink.symlink_to(data)
                with self.assertRaisesRegex(lc.Refused, "owned namespace symlink"):
                    resources.check()


class NoResources:
    def __init__(self, _spec):
        pass

    def check(self, _children=(), **_kwargs):
        pass


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.gettempdir())
        tmp.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=tmp)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = []
        self.source = self.file("source.rs", b"fn owned_source() {}\n")
        self.tool = self.file("trusted-tool", b"synthetic tool, never executed", 0o755)
        self.source_info = {"commit": "1" * 40, "patch": None, "untracked_inputs": []}
        manifest = self.file("Cargo.toml", b"[workspace]\n")
        lock = self.file("Cargo.lock", b"synthetic lock fixture")
        self.source_info.update(
            workspace=str(self.root),
            manifest=ref(manifest),
            lock=ref(lock),
        )
        # Standard Git is the fixture's only source/delta authority; no map builder.
        for args in (
            ["init", "-q"],
            ["add", "source.rs", "Cargo.toml", "Cargo.lock"],
            [
                "-c",
                "user.name=Synthetic379",
                "-c",
                "user.email=synthetic379@example.invalid",
                "commit",
                "-qm",
                "synthetic source",
            ],
        ):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        self.source_info["commit"] = (
            subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"])
            .decode()
            .strip()
        )
        cargo_home = self.root / "cargo-home"
        configurations = {
            str(p / ".cargo" / n)
            for p in [self.root, *self.root.parents]
            for n in ("config", "config.toml")
        }
        configurations |= {str(cargo_home / n) for n in ("config", "config.toml")}
        self.source_info["cargo_configs"] = [
            {"path": p, "file": ref(p) if Path(p).exists() else None}
            for p in sorted(configurations)
        ]
        origin_port = patch.object(lc, "originating_job", self.origin)
        origin_port.start()
        self.addCleanup(origin_port.stop)
        self.target = self.root / "target"
        self.private = self.root / "private/runner"
        self.spec = {
            "schema": "quoridor.research.lifecycle-intent.v1",
            "kind": "build",
            "caller_sources": [
                ref(ROOT / name)
                for name in (
                    "scripts/dev/research-lifecycle.py",
                    "scripts/dev/research-job.py",
                    "shared/python/quoridor_runtime/__init__.py",
                    "shared/python/quoridor_runtime/cycle_process.py",
                    "shared/python/quoridor_runtime/snapshot.py",
                )
            ],
            "owner": str(self.root),
            "writer": "codex:fixture",
            "cwd": str(self.root),
            "output": str(self.root / "operation"),
            "source": self.source_info,
            "source_adoption": self.json(
                "adoption",
                {
                    "schema": "quoridor.research.source-adoption.v1",
                    "status": "ACCEPTED",
                    "source": self.source_info,
                },
            ),
            "target": str(self.target),
            "private": str(self.private),
            "TMP": str(self.root / "TMP"),
            "target_handover": self.json(
                "handover",
                {
                    "schema": "research.target-handover.v1",
                    "status": "HANDED_OVER",
                    "target": str(self.target),
                    "old_target": str(self.root / "absent-old-target"),
                    "owned_remaining": [],
                    "shared_serial_pool": True,
                    "target_writer": "codex:fixture",
                    "fresh_private_root": str(self.private.parent),
                },
            ),
            "tools": {
                n: {
                    "file": ref(self.tool),
                    "version_args": ["--version"],
                    "version": "fixture1",
                }
                for n in ["CARGO", "RUSTC", "RUSTDOC", "CC", "CXX", "AR", "PYTHON"]
            },
            "env": {
                **{n: str(self.tool) for n in ["RUSTC", "RUSTDOC", "CC", "CXX", "AR"]},
                "CARGO_TARGET_DIR": str(self.target),
                "CARGO_HOME": str(cargo_home),
                "TMPDIR": str(self.root / "TMP"),
                "CARGO_NET_OFFLINE": "true",
                "RUSTUP_AUTO_INSTALL": "0",
                "CARGO_BUILD_JOBS": "1",
                "CARGO_INCREMENTAL": "0",
                "CARGO_PROFILE_RELEASE_OPT_LEVEL": "3",
                "CARGO_PROFILE_RELEASE_DEBUG": "0",
            },
            "commands": [
                {
                    "name": role,
                    "role": role,
                    "argv": [
                        str(self.tool),
                        "clippy" if role == "lint" else role,
                        "--manifest-path",
                        str(manifest),
                        "--offline",
                        "--locked",
                        "-j1",
                        "--message-format=json-render-diagnostics",
                        *(
                            [
                                "--release",
                                "-p",
                                "quoridor-runner",
                                "--bin",
                                "quoridor-runner",
                            ]
                            if role == "build"
                            else []
                        ),
                        *(["--no-deps", "--", "-Dwarnings"] if role == "lint" else []),
                    ],
                }
                for role in ["test", "lint", "build"]
            ],
            "limits": {
                "family_B": 536870912,
                "host_reserve_B": 4 * 1024**3,
                "controller_B": 67108864,
                "owned_B": 1024 * 1024,
                "log_B": 1024 * 1024,
                "free_B": 1024,
                "worker_cpu": 0,
                "guardian_cpu": 2,
            },
            "support": self.json(
                "support", {"funded_union_B": 4294967296, "global_held_B": 49976205312}
            ),
            "admission": None,
            "intent_sha256": "",
            "finalizers": [],
        }

    def file(self, name, data, mode=0o644):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(mode)
        return p

    def json(self, name, value):
        return ref(self.file(name + ".json", json.dumps(value).encode()))

    def intent(self):
        view = {k: v for k, v in self.spec.items() if k not in {"admission", "intent_sha256"}}
        self.spec["intent_sha256"] = hashlib.sha256(
            json.dumps(view, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.spec["admission"] = self.json(
            "admission",
            {
                "schema": "quoridor.research.phase-admission.v1",
                "owner": self.spec["owner"],
                "limits": self.spec["limits"],
                "spec_sha256": self.spec["intent_sha256"],
                "support_sha256": self.spec["support"]["sha256"],
                "ready": True,
            },
        )
        return self.json("intent", self.spec)

    def executor(self, argv, _log, _deadline, **kwargs):
        self.calls.append(argv)
        sink = kwargs["output_sink"]
        if argv[-1] == "--version":
            sink(b"fixture1\n")
        elif len(argv) > 1 and argv[1] in {"test", "clippy", "build"}:
            events = [
                {
                    "reason": "compiler-message",
                    "message": {
                        "level": "warning",
                        "spans": [{"is_primary": True}, {"is_primary": True}],
                    },
                }
            ]
            if argv[1] == "build":
                exe = self.target / "release/quoridor-runner"
                exe.parent.mkdir(exist_ok=True)
                exe.write_bytes(b"synthetic artifact, no model/native call")
                exe.chmod(0o755)
                events += [
                    {
                        "reason": "build-script-executed",
                        "linked_paths": [str(self.target / "generated/lz4")],
                        "out_dir": str(self.target / "generated"),
                    },
                    {
                        "reason": "compiler-artifact",
                        "target": {"name": "quoridor-runner", "kind": ["bin"]},
                        "profile": {"test": False},
                        "executable": str(exe),
                    },
                ]
            events += [{"reason": "build-finished", "success": True}]
            sink(b"\n".join(json.dumps(e).encode() for e in events) + b"\n")
        return {
            "status": "complete",
            "log_bytes_seen": sink.seen,
            "exit_code": 0,
            "direct_child_reaped": True,
            "cleanup_complete": True,
            "remaining": [],
            "finalization_errors": [],
            "signal_mask_restoration": "completed",
            "final_record_persist": "completed",
        }

    def build(self):
        result = lc.execute(
            self.intent(),
            executor=self.executor,
            guard=lambda _: None,
            lock=nullcontext,
            resource_factory=NoResources,
        )
        self.assertEqual(result["status"], "PENDING_FINALIZATION")
        self.assertFalse((Path(self.spec["output"]) / "manifest.json").exists())
        return result

    def finalize(self, directory, job_ref):
        return lc.finalize(
            directory,
            job_ref,
            guard=lambda _: None,
            lock=nullcontext,
            resource_factory=NoResources,
        )

    def origin(self, spec_ref, spec):
        runtime = self.root / "job"
        cfg = {
            "argv": [
                sys.executable,
                "-B",
                str(lc.ROOT / "scripts/dev/research-lifecycle.py"),
                spec["kind"],
                "--intent",
                spec_ref["path"],
                "--sha256",
                spec_ref["sha256"],
            ],
            "cwd": spec["cwd"],
        }
        cfg_ref = self.json("job/config", cfg)
        return {
            "runtime": str(runtime),
            "job_id": spec_ref["sha256"],
            "config": cfg_ref,
            "config_sha256": lc.sha(json.dumps(cfg, sort_keys=True).encode()),
            "supervisor": {"pid": 999990, "start_ticks": "1", "boot_id": "fixture"},
            "child": {"pid": 999991, "start_ticks": "2", "boot_id": "fixture"},
        }

    def job(self, candidate, outcome="succeeded"):
        origin = candidate["originating_job"]
        self.json(
            "job/state",
            {
                "phase": "finished",
                "job_id": origin["job_id"],
                "config_sha256": origin["config_sha256"],
                "supervisor": origin["supervisor"],
                "child": origin["child"],
                "outcome": outcome,
            },
        )
        return self.json(
            "job/result",
            {
                "job_id": origin["job_id"],
                "outcome": outcome,
                "exit_code": 0 if outcome == "succeeded" else 1,
                "finished_at": "fixture-stop",
                "direct_child_reaped": True,
                "cleanup_complete": True,
                "remaining": [],
                "cleanup_errors": [],
            },
        )

    def next_build(self, index):
        self.spec["output"] = str(self.root / f"operation-{index}")
        self.private = self.root / f"private/runner-{index}"
        self.spec["private"] = str(self.private)
        self.spec["commands"][-1]["argv"][0] = str(self.private)
        return self.build()

    def test_whole_storage_unbudgeted_completion_records_current_usage(self):
        self.spec["limits"].update(owned_B=None, free_B=None)
        candidate = self.build()
        active = [False]

        @contextmanager
        def held():
            active[0] = True
            try:
                yield
            finally:
                active[0] = False

        original_allocated = lc.allocated

        def counted(*args, **kwargs):
            self.assertTrue(active[0], "completion observation must retain the owning lease")
            return original_allocated(*args, **kwargs)

        with patch.object(lc, "allocated", counted):
            result = lc.finalize(
                self.spec["output"],
                self.job(candidate),
                guard=lambda _: None,
                lock=held,
                resource_factory=NoResources,
            )
        self.assertFalse(active[0])
        self.assertEqual(result["status"], "PASS")
        usage = json.loads((Path(self.spec["output"]) / "storage-usage.json").read_bytes())
        self.assertIsNone(usage["storage_budget_B"])
        self.assertIsNone(usage["global_actual_B"])
        self.assertGreater(usage["allocated_B"], 0)
        self.assertIn(str(self.target), usage["roots"])
        self.assertIn(str(self.private.parent), usage["roots"])
        self.assertFalse(Path(self.spec["TMP"]).exists())

    def test_whole_storage_final_publication_overflow_preserves_unpublished_candidate(
        self,
    ):
        candidate = self.build()

        def resources(spec):
            value = object.__new__(lc.Limits)
            value.spec = spec
            value.charged_paths = lc.charged_roots(spec)
            seen = set()
            value.spec["limits"]["owned_B"] = sum(
                lc.allocated(p, seen=seen) for p in value.charged_paths
            )
            value.spec["limits"]["free_B"] = None
            return value

        with (
            patch.object(lc.process.CycleResources, "check", return_value=None),
            self.assertRaisesRegex(lc.Refused, "owned allocation limit"),
        ):
            lc.finalize(
                self.spec["output"],
                self.job(candidate),
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=resources,
            )
        self.assertTrue((Path(self.spec["output"]) / "candidate.json").exists())
        self.assertFalse((Path(self.spec["output"]) / "manifest.json").exists())
        self.assertTrue((Path(self.spec["output"]) / "INCOMPLETE").exists())

    def test_whole_storage_usage_fault_keeps_final_marker_and_refuses_completed_claim(
        self,
    ):
        for stage in ("read", "write"):
            with self.subTest(stage=stage):
                other = LifecycleTests("runTest")
                other.setUp()
                try:
                    other.spec["limits"].update(owned_B=None, free_B=None)
                    candidate = other.build()
                    original_write = lc.new_json

                    def fault_write(path, value, **kwargs):
                        if Path(path).name == "storage-usage.json":
                            raise OSError("injected usage write")
                        return original_write(path, value, **kwargs)

                    fault = (
                        patch.object(lc, "allocated", side_effect=OSError("injected usage read"))
                        if stage == "read"
                        else patch.object(lc, "new_json", fault_write)
                    )
                    with (
                        fault,
                        self.assertRaisesRegex(OSError, "injected usage " + stage),
                    ):
                        other.finalize(other.spec["output"], other.job(candidate))
                    directory = Path(other.spec["output"])
                    self.assertTrue((directory / "INCOMPLETE").exists())
                    self.assertFalse((directory / "storage-usage.json").exists())
                    with self.assertRaisesRegex(lc.Refused, "provisional manifest"):
                        lc.accepted_build(lc.bound(directory / "manifest.json")[0])
                finally:
                    other.doCleanups()

    def test_originating_job_entry_and_final_runtime_state_directwait_join(self):
        bound = self.intent()
        origin = self.origin(bound, self.spec)
        state = {
            "phase": "starting",
            "job_id": origin["job_id"],
            "config_sha256": origin["config_sha256"],
            "supervisor": {
                "pid": os.getppid(),
                "start_ticks": "1",
                "boot_id": "fixture",
            },
        }
        self.json("job/state", state)
        with (
            patch.dict(os.environ, QUORIDOR_RESEARCH_JOB_DIR=origin["runtime"]),
            patch.object(lc.process, "alive", return_value=True),
        ):
            actual = ORIGINATING_JOB(bound, self.spec)
            self.assertEqual(actual["job_id"], origin["job_id"])
            self.assertEqual(actual["child"]["pid"], os.getpid())
            state["config_sha256"] = "0" * 64
            self.json("job/state", state)
            with self.assertRaises(lc.Refused):
                ORIGINATING_JOB(bound, self.spec)
        for i, mutation in enumerate(
            ["no-reap", "wrong-state", "wrong-config", "wrong-child", "sibling"]
        ):
            c = self.next_build(i)
            job = self.job(c)
            if mutation == "sibling":
                job = self.json("sibling/result", lc.document(job))
            elif mutation == "no-reap":
                v = lc.document(job)
                v.pop("direct_child_reaped")
                job = self.json("job/result", v)
            else:
                v = json.loads((self.root / "job/state.json").read_bytes())
                if mutation == "wrong-state":
                    v["phase"] = "running"
                if mutation == "wrong-config":
                    v["config_sha256"] = "0" * 64
                if mutation == "wrong-child":
                    v["child"]["start_ticks"] = "unknown"
                self.json("job/state", v)
            final = self.finalize(Path(self.spec["output"]), job)
            self.assertEqual(final["status"], "FAILED", mutation)
            self.assertTrue(any(e["stage"] == "outer_job" for e in final["secondary"]))

    def test_build379_final_cargo_artifact_drift_refuses_after_successful_commands(
        self,
    ):
        c = self.build()
        c["cargo_artifact"]["target"]["name"] = "wrong-target"
        (Path(self.spec["output"]) / "candidate.json").write_text(json.dumps(c))
        final = self.finalize(Path(self.spec["output"]), self.job(c))
        self.assertEqual(final["status"], "FAILED")
        self.assertTrue(any(e["stage"] == "final_artifact_source" for e in final["secondary"]))

    def test_all_command_and_version_logs_rechecked_independently(self):
        c = self.build()
        self.assertEqual(sum(x["role"] == "version" for x in c["checks"]), 7)
        version = next(x for x in c["checks"] if x["role"] == "version")
        Path(version["full_log"]["path"]).unlink()
        build = next(x for x in c["checks"] if x["role"] == "build")
        Path(build["full_log"]["path"]).write_bytes(b"truncated")
        final = self.finalize(Path(self.spec["output"]), self.job(c))
        errors = [x for x in final["secondary"] if x["stage"] == "command_log"]
        self.assertEqual(len(errors), 2)
        self.assertEqual(final["status"], "FAILED")

    def test_failed_return_and_unreturned_persisted_capture_domains_survive(self):
        def returned(argv, log, deadline, **kw):
            r = self.executor(argv, log, deadline, **kw)
            r["exit_code"] = 9
            return r

        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=returned,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        c = json.loads((Path(self.spec["output"]) / "candidate.json").read_bytes())
        entry = c["checks"][0]
        self.assertEqual(entry["guardian_return"]["exit_code"], 9)
        self.assertTrue(entry["capture_complete"])
        self.assertTrue(c["cleanup_complete"])
        self.assertEqual(entry["status"], "FAILED")
        final = self.finalize(Path(self.spec["output"]), self.job(c, "failed"))
        self.assertEqual(final["status"], "FAILED")
        self.assertTrue(final["cleanup_complete"])
        original = OSError("original unreturned failure")
        self.spec["output"] = str(self.root / "unreturned-operation")
        self.private = self.root / "private/unreturned-runner"
        self.spec["private"] = str(self.private)
        self.spec["commands"][-1]["argv"][0] = str(self.private)

        def unreturned(_argv, log, _deadline, **kw):
            kw["output_sink"](b"retained partial")
            receipt = Path(log).with_suffix(".process.json")
            receipt.write_text(
                json.dumps(
                    {
                        "exit_code": 1,
                        "direct_child_reaped": True,
                        "signal_mask_restoration": "pending",
                        "final_record_persist": "attempted",
                    }
                )
            )
            raise original

        with self.assertRaises(OSError) as caught:
            lc.execute(
                self.intent(),
                executor=unreturned,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertIs(caught.exception, original)
        c = json.loads((Path(self.spec["output"]) / "candidate.json").read_bytes())
        entry = c["checks"][0]
        self.assertIsNone(entry["guardian_return"])
        self.assertFalse(entry["capture_complete"])
        self.assertEqual(lc.read_ref(entry["full_log"]), b"retained partial")
        self.assertEqual(
            lc.document(entry["persisted_process_receipt"])["signal_mask_restoration"],
            "pending",
        )
        self.assertFalse(c["cleanup_complete"])

    def test_scientific_root_lifetime_charge_dedup_and_external_declared_refusal(self):
        self.spec.update(
            kind="run",
            data_root=str(self.root / "data"),
            data=[],
            owned_outputs=[str(self.root / "data/nested")],
        )
        roots = lc.charged_roots(self.spec)
        self.assertIn(self.root / "data", roots)
        self.assertNotIn(self.root / "data/nested", roots)
        self.spec["data"] = [
            {"name": "bad", "path": str(self.root / "uncharged/output"), "limit_B": 4}
        ]
        with self.assertRaises(lc.Refused):
            lc.charged_roots(self.spec)
        self.spec["data"] = []
        bound = self.intent()
        resources = lc.Limits(self.spec)
        resources.spec["limits"]["owned_B"] = 4096
        self.file("data/grown", b"x" * 8192)
        with (
            patch.object(lc.process.CycleResources, "check", return_value=None),
            self.assertRaisesRegex(lc.Refused, "owned allocation"),
        ):
            resources.check()
        self.assertIsNotNone(bound)

    def test_adopted_Cargo_workspace_manifest_and_configuration(self):
        self.spec["cwd"] = str(self.root.parent)
        with self.assertRaisesRegex(lc.Refused, "Cargo cwd"):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(self.calls, [])
        self.spec["cwd"] = str(self.root)
        self.spec["commands"][0]["argv"][
            self.spec["commands"][0]["argv"].index("--manifest-path") + 1
        ] = str(self.root / "foreign.toml")
        with self.assertRaisesRegex(lc.Refused, "Cargo manifest"):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(self.calls, [])
        self.spec["commands"][0]["argv"][
            self.spec["commands"][0]["argv"].index("--manifest-path") + 1
        ] = str(self.root / "Cargo.toml")
        self.file("cargo-home/config.toml", b"[build]\n")
        with self.assertRaisesRegex(lc.Refused, "Cargo config appeared"):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        (self.root / "cargo-home/config.toml").unlink()

    def test_e2e_build_manifest_run_finalize_and_exact_source_config_separation(self):
        candidate = self.build()
        manifest = self.finalize(Path(self.spec["output"]), self.job(candidate))
        self.assertEqual(manifest["status"], "PASS")
        accepted = ref(Path(self.spec["output"]) / "manifest.json")
        self.assertEqual(lc.accepted_build(accepted)["artifact"], ref(self.private))
        self.assertTrue(
            all(
                c["cargo"]["warning_count"] == 1
                for c in manifest["checks"]
                if c["role"] in {"test", "lint", "build"}
            )
        )
        self.spec.update(
            kind="run",
            output=str(self.root / "run"),
            artifact=manifest["artifact"],
            argv=[str(self.private), "fixture-run"],
            data_root=str(self.root / "data"),
            data=[
                {
                    "name": "result",
                    "path": str(self.root / "data/result.json"),
                    "limit_B": 1024,
                }
            ],
        )
        config = self.json("scientific-config", {"not_source": True})
        experiment = {
            "schema": lc.EXPERIMENT_SCHEMA,
            "phase": "compare",
            "build_manifest": accepted,
            "config": config,
            "inputs": [],
            "models": [],
            "dynamic_libraries": [],
            "schedule": self.json("schedule", []),
            "numerical_qualification": self.json("numerical", {"fixture_only": True}),
            "planned_slots": 0,
            "argv": self.spec["argv"],
        }
        self.spec["experiment"] = self.json("experiment", experiment)

        def run(argv, log, deadline, **kwargs):
            self.file("data/result.json", b'{"completed":true}')
            return self.executor(argv, log, deadline, **kwargs)

        result = lc.execute(
            self.intent(),
            executor=run,
            guard=lambda _: None,
            lock=nullcontext,
            resource_factory=NoResources,
        )
        self.assertEqual(result["data"]["status"], "PASS")
        final = self.finalize(Path(self.spec["output"]), self.job(result))
        self.assertEqual(final["status"], "PASS")
        self.assertEqual(final["planned_slots"], 0)
        self.assertNotIn("scientific-config", json.dumps(manifest["source"]))

    def test_maintained_guardian_actual_stdlib_child_full_capture_and_returned_cleanup(
        self,
    ):
        self.spec["limits"]["worker_cpu"] = 3
        record, full = lc.command(
            self.spec,
            {
                "name": "stdlib-child",
                "argv": [sys.executable, "-c", "print('no native/model call')"],
            },
            self.root,
            NoResources(self.spec),
        )
        self.assertEqual(full.read_text(), "no native/model call\n")
        self.assertTrue(record["direct_child_reaped"])
        self.assertEqual(record["remaining"], [])
        self.assertEqual(record["signal_mask_restoration"], "completed")
        self.assertEqual(record["final_record_persist"], "completed")

    def test_retained_real_cargo_multiple_primary_warnings_and_native_outputs(self):
        fixture = ROOT / "tools/research-session/fixtures/cargo-native-retained.jsonl"
        report = lc.cargo_report(fixture.read_bytes())
        self.assertEqual(report["warning_count"], 8)
        events = [
            json.loads(line) for line in fixture.read_bytes().splitlines() if line.startswith(b"{")
        ]
        self.assertTrue(
            any(
                sum(s["is_primary"] for s in e.get("message", {}).get("spans", [])) >= 2
                for e in events
            )
        )
        self.assertTrue(any(e.get("reason") == "build-script-executed" for e in events))
        context = json.loads(
            (ROOT / "tools/research-session/fixtures/native-context-retained.json").read_bytes()
        )
        self.assertIn("deps", context)

    def test_no_earlier_success_and_restart_duplicate_refusal(self):
        candidate = self.build()
        with self.assertRaises(FileNotFoundError):
            lc.accepted_build(
                {
                    "path": str(Path(self.spec["output"]) / "manifest.json"),
                    "sha256": "0" * 64,
                    "bytes": 1,
                    "mode": "0644",
                }
            )
        with self.assertRaises(lc.Refused):
            lc.execute(
                candidate["intent"],
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(len(self.calls), 11)

    def test_source_drift_refuses_before_tools_or_target(self):
        self.source.write_text("changed")
        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(self.calls, [])
        self.assertFalse(self.target.exists())

    def test_target_handover_writer_and_parallel_old_refuse(self):
        old = self.file("absent-old-target", b"held")
        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(old.read_bytes(), b"held")
        self.assertFalse(self.target.exists())
        old.unlink()
        h = lc.document(self.spec["target_handover"])
        h["target_writer"] = "codex:foreign"
        self.spec["target_handover"] = self.json("handover", h)
        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(self.calls, [])

    def test_budget_refusal_precedes_output_and_no_foreign_TMP_removal(self):
        tmp = Path(self.spec["TMP"])
        tmp.mkdir()

        def refusal(_):
            raise lc.Refused("budget")

        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=refusal,
            )
        self.assertTrue(tmp.is_dir())
        self.assertFalse(Path(self.spec["output"]).exists())

    def test_original_failure_object_survives_capture_secondary_and_save_failure(self):
        primary = OSError("original engine error")

        def fail(*_a, **_k):
            raise primary

        original = lc.Capture.close

        def close(cap):
            original(cap)
            raise OSError("capture close secondary")

        write = lc.new_json

        def save(path, value):
            if Path(path).name == "candidate.json":
                raise OSError("candidate save secondary")
            return write(path, value)

        with (
            patch.object(lc.Capture, "close", close),
            patch.object(lc, "new_json", save),
        ):
            with self.assertRaises(OSError) as caught:
                lc.execute(
                    self.intent(),
                    executor=fail,
                    guard=lambda _: None,
                    lock=nullcontext,
                    resource_factory=NoResources,
                )
        self.assertIs(caught.exception, primary)
        self.assertIn("capture secondary", str(primary.__notes__))
        self.assertIn("candidate save secondary", str(primary.__notes__))
        self.assertTrue((Path(self.spec["output"]) / "INCOMPLETE").exists())

    def test_build_failure_and_cancellation_never_complete_success(self):
        primary = lc.process.CycleStopped("cycle signal: SIGTERM")

        def fail(*_a, **_k):
            raise primary

        with self.assertRaises(lc.process.CycleStopped):
            lc.execute(
                self.intent(),
                executor=fail,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        c = json.loads((Path(self.spec["output"]) / "candidate.json").read_bytes())
        self.assertEqual(c["status"], "CANCELLED")
        m = self.finalize(Path(self.spec["output"]), self.job(c, "cancelled"))
        self.assertEqual(m["status"], "CANCELLED")
        self.assertFalse(m["cleanup_complete"])

    def test_missing_artifact_and_postbuild_artifact_drift_refuse(self):
        c = self.build()
        self.private.unlink()
        final = self.finalize(Path(self.spec["output"]), self.job(c))
        self.assertEqual(final["status"], "FAILED")
        with self.assertRaises(lc.Refused):
            lc.accepted_build(ref(Path(self.spec["output"]) / "manifest.json"))

    def test_outer_finalizer_cleanup_and_every_owed_error_retained(self):
        c = self.build()
        c["owed_finalizers"] = [
            {"kind": "data", "path": str(self.root / "missing-a"), "limit_B": 1024},
            {"kind": "data", "path": str(self.root / "missing-b"), "limit_B": 1024},
        ]
        Path(self.spec["output"]).joinpath("candidate.json").write_text(json.dumps(c))
        job = self.job(c)
        x = lc.document(job)
        x["cleanup_complete"] = False
        job = self.json("job/result", x)
        m = self.finalize(Path(self.spec["output"]), job)
        self.assertEqual(m["status"], "FAILED")
        self.assertEqual(
            [e["stage"] for e in m["secondary"]],
            ["outer_job", "owed_finalizer", "owed_finalizer"],
        )
        with self.assertRaises(lc.Refused):
            self.finalize(Path(self.spec["output"]), job)

    def test_full_capture_failure_refuses_instead_of_tail_rescue(self):
        c = copy.deepcopy(self.spec)
        c["limits"]["log_B"] = 1
        self.spec = c
        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertFalse(Path(self.spec["output"]).joinpath("manifest.json").exists())

    def test_cargo_false_missing_or_multiple_completion_never_success(self):
        for text in [
            b'{"reason":"build-finished","success":false}',
            b"warning human text only",
            b'{"reason":"build-finished","success":true}\n{"reason":"build-finished","success":true}',
        ]:
            with self.subTest(text=text):
                with self.assertRaises(lc.Refused):
                    lc.cargo_report(text)

    def test_partial_journal_keeps_512_and_original_available_records(self):
        schedule = [
            {
                "slot": s,
                "batch": s // 32,
                "local_game": s % 32,
                "family_id": (s // 32 // 2) * 16 + (s % 32 // 2),
                "candidate_color": s % 2,
            }
            for s in range(512)
        ]
        config = {
            "arena": {
                "book": {
                    "openings": [{"reference": {"settings": {"family_id": f}}} for f in range(16)]
                }
            }
        }
        row = {
            "game": 0,
            "candidate_color": 0,
            "observations": [],
            "moves": [],
            "status": "unknown",
        }
        self.file("data/completed.jsonl", json.dumps(row).encode() + b"\n")
        experiment = {
            "planned_slots": 512,
            "batch": 0,
            "schedule": self.json("schedule", schedule),
            "config": self.json("config", config),
        }
        self.spec["data"] = [
            {
                "name": "journal",
                "path": str(self.root / "data/completed.jsonl"),
                "limit_B": 1024,
            }
        ]
        data = lc.collect_data(self.spec, experiment)
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(data["planned_slots"], 512)
        self.assertEqual(data["observed_local_games"], [0])
        self.assertEqual(data["missing_local_games"], list(range(1, 32)))
        self.assertEqual(len(data["files"]), 1)

    def test_missing_model_and_config_drift_refuse_before_run_factory(self):
        c = self.build()
        self.finalize(Path(self.spec["output"]), self.job(c))
        manifest = ref(Path(self.spec["output"]) / "manifest.json")
        descriptor = self.json("model-descriptor", {"weights_SHA": "0" * 64})
        missing = {
            "path": str(self.root / "missing-weights"),
            "sha256": "0" * 64,
            "bytes": 1,
            "mode": "0600",
        }
        config = self.json("run-config", {"frozen": True})
        e = {
            "schema": lc.EXPERIMENT_SCHEMA,
            "phase": "arena",
            "build_manifest": manifest,
            "config": config,
            "inputs": [],
            "models": [
                {
                    "descriptor": descriptor,
                    "weights": missing,
                    "evaluator_sha256": "0" * 64,
                }
            ],
            "dynamic_libraries": [],
            "schedule": self.json("run-schedule", []),
            "numerical_qualification": self.json("run-qualification", {}),
            "planned_slots": 512,
            "argv": [str(self.private), "strength-arena"],
        }
        self.spec.update(
            kind="run",
            artifact=c["artifact"],
            argv=e["argv"],
            experiment=self.json("run-experiment", e),
            output=str(self.root / "new-run"),
            data_root=str(self.root / "new-data"),
            data=[
                {
                    "name": "journal",
                    "path": str(self.root / "new-data/completed.jsonl"),
                    "limit_B": 1024,
                },
                {
                    "name": "result",
                    "path": str(self.root / "new-data/result.json"),
                    "limit_B": 1024,
                },
            ],
        )
        count = len(self.calls)
        with self.assertRaises(FileNotFoundError):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(len(self.calls), count)
        self.file("missing-weights", b"0", 0o600)
        Path(config["path"]).write_text("changed config")
        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(len(self.calls), count)
        self.assertFalse(Path(self.spec["output"]).exists())

    def test_complete_native_journal_join_and_record_or_tail_drift_refusal(self):
        schedule = [
            {
                "slot": s,
                "batch": s // 32,
                "local_game": s % 32,
                "family_id": (s // 32 // 2) * 16 + s % 32 // 2,
                "candidate_color": s % 2,
            }
            for s in range(512)
        ]
        config = {
            "arena": {
                "book": {
                    "openings": [{"reference": {"settings": {"family_id": f}}} for f in range(16)]
                }
            }
        }
        records = [
            {
                "game": g,
                "candidate_color": g % 2,
                "status": "goal" if g == 0 else "unknown",
                "moves": [],
                "observations": [],
            }
            for g in range(32)
        ]
        journal = self.file(
            "data/completed.jsonl",
            b"".join(json.dumps(r).encode() + b"\n" for r in records),
        )
        result = self.file(
            "data/result.json",
            json.dumps(
                {
                    "planned": 32,
                    "all_workers_joined": True,
                    "stopped": None,
                    "outcomes": list(reversed(records)),
                }
            ).encode(),
        )
        e = {
            "planned_slots": 512,
            "batch": 0,
            "schedule": self.json("schedule", schedule),
            "config": self.json("config", config),
        }
        self.spec["data"] = [
            {"name": "journal", "path": str(journal), "limit_B": 65536},
            {"name": "result", "path": str(result), "limit_B": 65536},
        ]
        data = lc.collect_data(self.spec, e)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["planned_slots"], 512)
        self.assertEqual(data["missing_local_games"], [])
        journal.write_bytes(journal.read_bytes()[:-1])
        data = lc.collect_data(self.spec, e)
        self.assertEqual(data["status"], "FAILED")
        self.assertIn("partial journal tail", str(data["errors"]))

    def test_same_owned_target_rebuild_and_unknown_role_refusal(self):
        self.build()
        self.spec["output"] = str(self.root / "second-operation")
        self.private = self.root / "private/runner-v2"
        self.spec["private"] = str(self.private)
        self.spec["commands"][-1]["argv"][0] = str(self.private)
        second = lc.execute(
            self.intent(),
            executor=self.executor,
            guard=lambda _: None,
            lock=nullcontext,
            resource_factory=NoResources,
        )
        self.assertEqual(second["status"], "PENDING_FINALIZATION")
        self.assertTrue((self.target / ".research-owner.json").is_file())
        self.spec["output"] = str(self.root / "third-operation")
        self.spec["private"] = str(self.root / "private/runner-v3")
        self.spec["commands"][0]["role"] = "run"
        n = len(self.calls)
        with self.assertRaises(lc.Refused):
            lc.execute(
                self.intent(),
                executor=self.executor,
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=NoResources,
            )
        self.assertEqual(len(self.calls), n)

    def test_final_marker_failure_cannot_expose_success(self):
        c = self.build()
        orig = Path.unlink

        def refuse(path, *a, **k):
            if path.name == "INCOMPLETE":
                raise OSError("commit marker failure")
            return orig(path, *a, **k)

        with patch.object(Path, "unlink", refuse):
            with self.assertRaises(OSError):
                self.finalize(Path(self.spec["output"]), self.job(c))
        with self.assertRaises(lc.Refused):
            lc.accepted_build(ref(Path(self.spec["output"]) / "manifest.json"))

    def generation_fixture(self, *, omitted=False):
        # Production-shaped key domains; file contents/outputs remain synthetic NN0 fixtures.
        self.spec["source_adoption"] = self.json(
            "adoption",
            {
                "schema": "quoridor.research.source-adoption.v1",
                "status": "ACCEPTED",
                "source": self.source_info,
            },
        )
        c = self.build()
        m = self.finalize(Path(self.spec["output"]), self.job(c))
        build = ref(Path(self.spec["output"]) / "manifest.json")
        plan = ref(
            Path(
                "/workspaces/quoridor/research-data/ai-sigma/value-search-strength355/plan-v1.json"
            )
        )
        prefixes = [
            [],
            [13, 67],
            [3, 77, 152, 206],
            [3, 75, 196, 182, 187, 66],
            [95, 175, 13, 107, 198, 149, 116, 90],
            [3, 208, 4, 140, 5, 75, 119, 148, 95, 182],
            [3, 67, 4, 151, 192, 199, 141, 183, 179, 68, 105, 82],
            [112, 115, 3, 75, 12, 83, 96, 145, 157, 66, 13, 136, 4, 67],
        ]
        old = self.json("generation-OPEN8", prefixes)
        schedule = []
        for group in range(8):
            for order in range(2):
                for family in range(group * 16, group * 16 + 16):
                    for color in range(2):
                        schedule.append(
                            {
                                "slot": len(schedule),
                                "batch": 2 * group + order,
                                "matchup": (group + order) % 2,
                                "family_id": family,
                                "candidate_color": (family + group + color) % 2,
                                "local_game": 2 * (family % 16) + color,
                            }
                        )
        self.schedule = schedule
        self.request = {
            "plan": {k: plan[k] for k in ("path", "sha256")},
            "old_prefixes": {k: old[k] for k in ("path", "sha256")},
            "output": str(self.root / "generation-data"),
        }
        e = {
            "schema": lc.EXPERIMENT_SCHEMA,
            "phase": "generation",
            "build_manifest": build,
            "config": self.json("generation-request", self.request),
            "inputs": [plan, old],
            "models": [],
            "dynamic_libraries": [],
            "schedule": self.json("generation-schedule", schedule),
            "numerical_qualification": None,
            "canonical_plan_sha256": lc.GENERATION_PLAN,
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "planned_slots": 0,
            "batch": None,
            "argv": [
                str(self.private),
                "strength-book",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        }
        if omitted:
            del e["numerical_qualification"]
        self.spec.update(
            kind="run",
            output=str(self.root / "generation-operation"),
            artifact=m["artifact"],
            data_root=self.request["output"],
            data=[
                {
                    "name": n,
                    "path": str(Path(self.request["output"]) / f),
                    "limit_B": 65536,
                }
                for n, f in lc.GENERATION_FILES.items()
            ],
        )
        self.generation_rebind(e)
        return e

    def generation_rebind(self, e):
        self.spec["experiment"] = self.json("generation-experiment", e)
        self.spec["argv"] = [
            a.replace("@EXPERIMENT@", self.spec["experiment"]["path"]).replace(
                "@EXPERIMENT_SHA256@", self.spec["experiment"]["sha256"]
            )
            for a in e["argv"]
        ]

    def generation_stub(self, argv, log, deadline, **kwargs):
        # Synthetic metadata only: no native geometry/model/Search is executed.
        self.geometry_stub_calls += 1
        sources = {"opaque-historical": ref(self.source)["sha256"]}
        start = {
            "request": self.request,
            "compiled_sources": sources,
            "planned_families": 128,
            "attempt_upper": 1024,
            "transition_upper": 16384,
            "models_loaded": 0,
            "search_calls": 0,
            "games_started": 0,
        }
        book = {
            "schema": "quoridor.value-search-strength.book.v1",
            "plan_sha256": lc.GENERATION_PLAN,
            "old_open8_sha256": self.generation_e["inputs"][1]["sha256"],
            "old_open8_prefixes": lc.document(self.generation_e["inputs"][1]),
            "rules": self.generation_e["rules"],
            "compiled_sources": sources,
            "complete": True,
            "attempted": 128,
            "transitions": 512,
            "attempts": [{} for _ in range(128)],
            "families": [{"family_id": f} for f in range(128)],
        }
        result = {
            "schema": book["schema"],
            "complete": True,
            "families": 128,
            "attempted": 128,
            "transitions": 512,
            "book_sha256": lc.sha(json.dumps(book, separators=(",", ":")).encode()),
            "schedule_sha256": lc.sha(json.dumps(self.schedule, separators=(",", ":")).encode()),
            "models_loaded": 0,
            "search_calls": 0,
            "games_started": 0,
        }
        for name, value in zip(
            lc.GENERATION_FILES, (start, book, self.schedule, result), strict=True
        ):
            self.file(
                "generation-data/" + lc.GENERATION_FILES[name],
                json.dumps(value, separators=(",", ":")).encode(),
            )
        return self.executor(argv, log, deadline, **kwargs)

    def generation_execute(self):
        self.geometry_stub_calls = 0
        return lc.execute(
            self.intent(),
            executor=self.generation_stub,
            guard=lambda _: None,
            lock=nullcontext,
            resource_factory=NoResources,
        )

    def test_generation_bootstrap_null_enters_only_stub_and_normal_finalization(self):
        self.generation_e = self.generation_fixture()
        # Declared library metadata is preserved and verified even without a model.
        self.generation_e["dynamic_libraries"] = [{"file": ref(self.tool), "version": "fixture1"}]
        self.generation_rebind(self.generation_e)
        c = self.generation_execute()
        self.assertEqual(self.geometry_stub_calls, 1)
        self.assertEqual(c["data"]["generation"]["numerical_qualification"], None)
        self.assertTrue((Path(self.spec["output"]) / "INCOMPLETE").exists())
        final = self.finalize(Path(self.spec["output"]), self.job(c))
        self.assertEqual(final["status"], "PASS")
        self.assertEqual(final["planned_slots"], 0)
        self.assertEqual(final["data"]["generation"]["scientific_planned_slots"], 512)
        self.assertNotIn("numerical_qualification", final)

    def test_generation_bootstrap_omitted_and_finalizer_failure_stays_failed(self):
        self.generation_e = self.generation_fixture(omitted=True)
        self.spec["finalizers"] = [
            {
                "kind": "data",
                "path": str(self.root / "missing-finalizer.json"),
                "limit_B": 1024,
            }
        ]
        c = self.generation_execute()
        self.assertEqual(self.geometry_stub_calls, 1)
        final = self.finalize(Path(self.spec["output"]), self.job(c))
        self.assertEqual(final["status"], "FAILED")
        self.assertEqual(final["data"]["generation"]["numerical_qualification"], None)
        self.assertTrue(final["secondary"])

    def test_generation_bootstrap_missing_numerical_refuses_all_other_phases_before_build_io(
        self,
    ):
        e = self.generation_fixture()
        for phase in ("materialize", "compare", "arena", "analysis", "unknown"):
            for omitted in (False, True):
                with self.subTest(phase=phase, omitted=omitted):
                    bad = copy.deepcopy(e)
                    bad["phase"] = phase
                    if omitted:
                        bad.pop("numerical_qualification")
                    self.generation_rebind(bad)
                    count = len(self.calls)
                    with patch.object(
                        lc,
                        "accepted_build",
                        side_effect=AssertionError("build must not open"),
                    ):
                        with self.assertRaises(lc.Refused):
                            self.generation_execute()
                    self.assertEqual(len(self.calls), count)
                    self.assertFalse(Path(self.spec["output"]).exists())

    def test_generation_bootstrap_escalation_and_identity_drift_refuse_before_stub(
        self,
    ):
        e = self.generation_fixture()
        changes = [
            lambda x: x.update(models=[{"descriptor": {}, "weights": {}}]),
            lambda x: x.update(planned_slots=512),
            lambda x: x.update(batch=0),
            lambda x: x["argv"].__setitem__(1, "strength-arena"),
            lambda x: x.update(numerical_qualification={}),
            lambda x: x.update(dynamic_libraries=None),
            lambda x: x.update(inputs=list(reversed(x["inputs"]))),
            lambda x: x.update(canonical_plan_sha256="0" * 64),
            lambda x: x["build_manifest"].update(sha256="0" * 64),
            lambda x: x["config"].update(sha256="0" * 64),
            lambda x: x["schedule"].update(sha256="0" * 64),
            lambda x: x["dynamic_libraries"].append({"file": ref(self.tool), "version": " "}),
        ]
        for change in changes:
            with self.subTest(change=changes.index(change)):
                bad = copy.deepcopy(e)
                change(bad)
                self.generation_rebind(bad)
                count = len(self.calls)
                with self.assertRaises((lc.Refused, KeyError)):
                    self.generation_execute()
                self.assertEqual(self.geometry_stub_calls, 0)
                self.assertEqual(len(self.calls), count)
                self.assertFalse(Path(self.spec["output"]).exists())
        self.generation_rebind(e)
        self.spec["artifact"] = {**self.spec["artifact"], "sha256": "0" * 64}
        with self.assertRaises(lc.Refused):
            self.generation_execute()
        self.assertEqual(self.geometry_stub_calls, 0)

    def test_generation_bootstrap_partial_native_metadata_retains_files_without_pass(
        self,
    ):
        self.generation_e = self.generation_fixture()
        self.generation_execute()
        p = Path(self.request["output"]) / "generation-result.json"
        value = json.loads(p.read_bytes())
        value["search_calls"] = 1
        p.write_text(json.dumps(value))
        data = lc.collect_data(self.spec, self.generation_e)
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(len(data["files"]), 4)
        self.assertEqual(data["generation"]["numerical_qualification"], None)
        self.assertTrue(data["errors"])

    def test_generation_bootstrap_rebound_wrong_inputs_and_missing_build_refuse(self):
        e = self.generation_fixture()
        missing = copy.deepcopy(e)
        missing["build_manifest"]["path"] = str(self.root / "missing-build.json")
        self.generation_rebind(missing)
        with self.assertRaises(FileNotFoundError):
            self.generation_execute()
        self.assertEqual(self.geometry_stub_calls, 0)
        for field in ("plan", "old_prefixes", "schedule", "output"):
            with self.subTest(field=field):
                bad = copy.deepcopy(e)
                request = copy.deepcopy(self.request)
                if field == "schedule":
                    bad["schedule"] = self.json("wrong-schedule", list(reversed(self.schedule)))
                elif field == "output":
                    request["output"] = str(self.root / "uncharged-output")
                else:
                    index = 0 if field == "plan" else 1
                    full = self.json("wrong-" + field, [] if index == 0 else [[1]])
                    bad["inputs"][index] = full
                    request[field] = {k: full[k] for k in ("path", "sha256")}
                bad["config"] = self.json("rebound-request", request)
                self.generation_rebind(bad)
                with self.assertRaises(lc.Refused):
                    self.generation_execute()
                self.assertEqual(self.geometry_stub_calls, 0)
                self.assertFalse(Path(self.spec["output"]).exists())
                self.assertFalse(Path(self.spec["data_root"]).exists())

    def failed_generation_fixture(self):
        self.generation_e = self.generation_fixture()
        c = self.generation_execute()
        c["status"] = "FAILED"
        c["primary"] = {
            "type": "Refused",
            "message": "retained generation source-domain mismatch",
            "notes": [],
        }
        c["data"]["status"] = "FAILED"
        c["data"]["errors"] = [
            {"stage": "generation_metadata", "message": "old exact35 comparison"}
        ]
        p = Path(self.spec["output"]) / "candidate.json"
        p.write_text(json.dumps(c))
        final = self.finalize(Path(self.spec["output"]), self.job(c, outcome="failed"))
        self.assertEqual(final["status"], "FAILED")
        return ref(Path(self.spec["output"]) / "manifest.json"), final

    def test_generation_source_domains_failed_origin_valid_data_keeps_errors_and_no_qualification(
        self,
    ):
        completion, final = self.failed_generation_fixture()
        before = Path(completion["path"]).read_bytes()
        calls = len(self.calls)
        data = lc.generation_input_data(completion)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["origin_status"], "FAILED")
        self.assertEqual(data["origin_primary"], final["primary"])
        self.assertEqual(data["origin_secondary"], final["secondary"])
        self.assertEqual(data["files"], final["data"]["files"])
        self.assertIsNone(data["numerical_qualification"])
        self.assertIsNone(data["generation"]["numerical_qualification"])
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(Path(completion["path"]).read_bytes(), before)

    def test_generation_source_domains_saved_origin_marker_missing_and_drift_refuse(
        self,
    ):
        completion, final = self.failed_generation_fixture()
        p = Path(completion["path"])
        marker = p.with_name("INCOMPLETE")
        marker.write_text("pending")
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(completion)
        marker.unlink()
        for field, value in [("status", "UNKNOWN"), ("cleanup_complete", False)]:
            bad = copy.deepcopy(final)
            bad[field] = value
            alternate = self.json("bad-completion", bad)
            with self.assertRaises(lc.Refused):
                lc.generation_input_data(alternate)
        bad = copy.deepcopy(final)
        bad["data"]["files"] = bad["data"]["files"][:-1]
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(self.json("missing-ref-completion", bad))
        book = Path(self.request["output"]) / "book.json"
        book.write_bytes(book.read_bytes() + b" ")
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(completion)
        self.assertEqual(json.loads(p.read_bytes())["status"], "FAILED")

    def test_generation_source_domains_raw_and_semantic_hashes_are_separate(self):
        self.generation_e = self.generation_fixture()
        self.generation_execute()
        data = lc.collect_data(self.spec, self.generation_e)
        self.assertEqual(data["status"], "PASS")
        g = data["generation"]
        self.assertNotEqual(g["book_sha256"], g["book_semantic_sha256"])
        self.assertNotEqual(g["schedule_sha256"], g["schedule_semantic_sha256"])
        self.assertEqual(g["schedule_semantic_sha256"], lc.GENERATION_SCHEDULE)
        p = Path(self.request["output"]) / "generation-result.json"
        result = json.loads(p.read_bytes())
        result["schedule_sha256"] = g["schedule_semantic_sha256"]
        p.write_text(json.dumps(result))
        data = lc.collect_data(self.spec, self.generation_e)
        self.assertEqual(data["status"], "FAILED")
        self.assertEqual(len(data["files"]), 4)

    def test_generation_source_domains_saved_native_return_and_log_bound_refuse(self):
        completion, final = self.failed_generation_fixture()
        for field, value in [
            ("exit_code", 1),
            ("direct_child_reaped", False),
            ("cleanup_complete", False),
        ]:
            with self.subTest(field=field):
                bad = copy.deepcopy(final)
                bad["checks"][0]["guardian_return"][field] = value
                with self.assertRaises(lc.Refused):
                    lc.generation_input_data(self.json("bad-return", bad))
        bad = copy.deepcopy(final)
        bad["checks"][0]["argv"][1] = "strength-arena"
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(self.json("bad-caller", bad))
        bad = copy.deepcopy(final)
        bad["checks"][0]["full_log"]["bytes"] = lc.CONTROL_BYTES + 1
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(self.json("oversized-log", bad))
        self.assertEqual(lc.document(completion)["status"], "FAILED")

    def current_caller_fixture(self):
        caller = self.file("scripts/dev/research-lifecycle.py", b"current adopted caller v1")
        for name in (
            "scripts/dev/research-job.py",
            "shared/python/quoridor_runtime/__init__.py",
            "shared/python/quoridor_runtime/cycle_process.py",
            "shared/python/quoridor_runtime/snapshot.py",
        ):
            self.file(name, b"current adopted helper")
        self.generation_e = self.generation_fixture()
        # The native image was built with v1; v2 is accepted separately before the run.
        caller.write_bytes(b"current adopted caller v2")
        self.spec["caller_sources"] = [
            ref(self.root / p.relative_to(ROOT))
            for p in map(lambda r: Path(r["path"]), self.spec["caller_sources"])
        ]
        return caller

    def test_current_caller_python_change_reuses_native_and_freezes_current_refs(self):
        caller = self.current_caller_fixture()
        build_ref = self.generation_e["build_manifest"]
        build_bytes = Path(build_ref["path"]).read_bytes()
        count = len(self.calls)
        with patch.object(lc, "ROOT", self.root):
            e, manifest, refs = lc.experiment_check(self.spec)
        self.assertEqual(e["phase"], "generation")
        self.assertEqual(len(self.calls), count)
        self.assertEqual(Path(build_ref["path"]).read_bytes(), build_bytes)
        self.assertIn(ref(caller), refs)

    def test_current_caller_artifact_input_and_config_drift_refuse(self):
        self.current_caller_fixture()
        for p in (
            self.private,
            Path(self.generation_e["config"]["path"]),
            Path(self.generation_e["inputs"][1]["path"]),
        ):
            with self.subTest(path=p.name):
                before = p.read_bytes()
                p.write_bytes(before + b"drift")
                with patch.object(lc, "ROOT", self.root), self.assertRaises(lc.Refused):
                    lc.experiment_check(self.spec)
                p.write_bytes(before)
        self.assertFalse(Path(self.spec["output"]).exists())
        self.assertFalse(Path(self.spec["data_root"]).exists())

    def test_current_analysis_import_membership_and_interpreter_are_bound(self):
        self.current_caller_fixture()
        e = copy.deepcopy(self.generation_e)
        e.update(phase="analysis", numerical_qualification=self.json("numerical", {}))
        script = self.root / "games/quoridor/python/quoridor_training/research355/stream355.py"
        e["argv"] = [str(self.tool), "-B", str(script), "--experiment", "@EXPERIMENT@"]
        for name in (
            "stream355",
            "lifecycle355",
            "io355",
            "observations355",
            "producer355",
            "strength355",
        ):
            p = self.file(
                "games/quoridor/python/quoridor_training/research355/" + name + ".py",
                b"current analysis module",
            )
            self.spec["caller_sources"].append(ref(p))
        self.generation_rebind(e)
        with patch.object(lc, "ROOT", self.root):
            _, _, refs = lc.experiment_check(self.spec)
            self.assertIn(ref(self.tool), refs)
            self.assertIn(ref(script), refs)
            missing = self.spec["caller_sources"].pop()
            with self.assertRaises(lc.Refused):
                lc.experiment_check(self.spec)
            self.spec["caller_sources"].append(missing)
            Path(missing["path"]).write_bytes(b"analysis drift")
            with self.assertRaises(lc.Refused):
                lc.experiment_check(self.spec)
        self.assertFalse(Path(self.spec["output"]).exists())

    def test_saved_generation_candidate_refuses_and_manifest_retains_outer_owed_errors(
        self,
    ):
        self.generation_e = self.generation_fixture()
        self.spec["finalizers"] = [
            {
                "kind": "data",
                "path": str(self.root / "missing-owed.json"),
                "limit_B": 1024,
            }
        ]
        c = self.generation_execute()
        c["status"] = "FAILED"
        c["primary"] = {
            "type": "Refused",
            "message": "original domain mismatch",
            "notes": [],
        }
        candidate = Path(self.spec["output"]) / "candidate.json"
        candidate.write_text(json.dumps(c))
        before = candidate.read_bytes()
        final = self.finalize(Path(self.spec["output"]), self.job(c, outcome="failed"))
        self.assertFalse(candidate.with_name("INCOMPLETE").exists())
        self.assertEqual(candidate.read_bytes(), before)
        self.assertTrue(final["cleanup_complete"])
        self.assertTrue({"outer_job", "owed_finalizer"} <= {x["stage"] for x in final["secondary"]})
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(ref(candidate))
        manifest = ref(candidate.with_name("manifest.json"))
        calls = len(self.calls)
        data = lc.generation_input_data(manifest)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["origin_status"], "FAILED")
        self.assertEqual(data["origin_primary"], final["primary"])
        self.assertEqual(data["origin_secondary"], final["secondary"])
        self.assertEqual(data["origin_completion"], manifest)
        self.assertIsNone(data["numerical_qualification"])
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(candidate.read_bytes(), before)

    def test_saved_generation_individual_allowances_and_actual_aggregate_bound(self):
        self.generation_e = self.generation_fixture()
        caps = [65536, 4194304, 65536, 65536]
        for item, cap in zip(self.spec["data"], caps, strict=True):
            item["limit_B"] = cap
        self.spec["finalizers"] = [
            {
                "kind": "data",
                "path": str(self.root / "missing-owed.json"),
                "limit_B": 1024,
            }
        ]
        c = self.generation_execute()
        c.update(
            status="FAILED",
            primary={
                "type": "Refused",
                "message": "original source-domain mismatch",
                "notes": [],
            },
        )
        candidate = Path(self.spec["output"]) / "candidate.json"
        candidate.write_text(json.dumps(c))
        final = self.finalize(Path(self.spec["output"]), self.job(c, outcome="failed"))
        path = candidate.with_name("manifest.json")
        original = path.read_bytes()
        intent = lc.document(final["intent"])
        self.assertEqual([x["limit_B"] for x in intent["data"]], caps)
        self.assertGreater(sum(caps), 4194304)
        self.assertLess(sum(x["bytes"] for x in final["data"]["files"]), 4194304)
        calls = len(self.calls)
        data = lc.generation_input_data(ref(path))
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["origin_status"], "FAILED")
        self.assertEqual(data["origin_primary"], final["primary"])
        self.assertEqual(data["origin_secondary"], final["secondary"])
        self.assertTrue(
            {"outer_job", "owed_finalizer"} <= {x["stage"] for x in data["origin_secondary"]}
        )
        self.assertIsNone(data["numerical_qualification"])
        self.assertEqual(data["files"], final["data"]["files"])
        self.assertEqual(path.read_bytes(), original)

        def refuses_before_collection(bad):
            path.write_text(json.dumps(bad))
            with (
                patch.object(
                    lc,
                    "collect_data",
                    side_effect=AssertionError("payload collection must not begin"),
                ),
                self.assertRaises(lc.Refused),
            ):
                lc.generation_input_data(ref(path))
            path.write_bytes(original)

        bad = copy.deepcopy(final)
        bad["data"]["files"][1]["bytes"] = 4194304
        refuses_before_collection(bad)  # individually valid, actual aggregate exceeds4MiB
        for value in (True, -1, 4194305):
            with self.subTest(saved_bytes=value):
                bad = copy.deepcopy(final)
                bad["data"]["files"][1]["bytes"] = value
                refuses_before_collection(bad)
        for field, value in (("sha256", "not-a-hash"), ("mode", "invalid")):
            bad = copy.deepcopy(final)
            bad["data"]["files"][1][field] = value
            refuses_before_collection(bad)
        bad = copy.deepcopy(final)
        del bad["data"]["files"][1]["bytes"]
        refuses_before_collection(bad)
        bad = copy.deepcopy(final)
        bad["data"]["files"].pop()
        refuses_before_collection(bad)
        for value in (True, -1, 4194305, 1):
            with self.subTest(individual_allowance=value):
                bad_intent = copy.deepcopy(intent)
                bad_intent["data"][1]["limit_B"] = value
                bad = copy.deepcopy(final)
                bad["intent"] = self.json("bad-individual-intent", bad_intent)
                refuses_before_collection(bad)
        # Current growth must refuse within the saved-size read bound, even though
        # the original per-file allowance would have allowed the larger bytes.
        book = Path(self.request["output"]) / "book.json"
        before = book.read_bytes()
        book.write_bytes(before + b" ")
        with self.assertRaises(lc.Refused):
            lc.generation_input_data(ref(path))
        book.write_bytes(before)
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(lc.document(final["intent"]), intent)


class CommonStudySettingsTests(unittest.TestCase):
    def test_multistream_materialization_uses_ordered_inputs_and_optional_distinct_lineage(self):
        streams = [
            {"path": "/fixture/a.gz", "sha256": "a" * 64},
            {"path": "/fixture/b.gz", "sha256": "b" * 64},
        ]
        binding = {"path": "/fixture/initializer.json", "sha256": "c" * 64}
        request = {
            "schema": "quoridor.common-corpus-cache-materialization.v1",
            "streams": streams,
            "output": "/fixture/cache",
        }
        spec = {
            "data_root": request["output"],
            "data": [
                {"name": name, "path": str(Path(request["output"]) / name)}
                for name in lc.COMPACT_CACHE_WIDTHS
            ]
            + [{"name": "cache_manifest", "path": "/fixture/cache/cache.json"}],
        }
        experiment = {
            "config": {},
            "models": [],
            "planned_slots": 0,
            "batch": None,
            "numerical_qualification": None,
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "inputs": streams.copy(),
            "argv": [
                "converter",
                "--input",
                streams[0]["path"],
                "--input",
                streams[1]["path"],
                "--output",
                request["output"],
            ],
        }
        manifest = {"artifact": {"path": "converter"}}
        with patch.object(lc, "document", return_value=request):
            lc.cache_materialize_check(spec, experiment, manifest)
            request["input_binding"] = binding
            experiment["inputs"].append(binding)
            experiment["argv"] += [
                "--input-binding",
                binding["path"],
                "--binding-sha256",
                binding["sha256"],
            ]
            lc.cache_materialize_check(spec, experiment, manifest)
            request["streams"] = list(reversed(streams))
            with self.assertRaisesRegex(lc.Refused, "ordered argv"):
                lc.cache_materialize_check(spec, experiment, manifest)
            request["streams"] = streams
            experiment["argv"].pop()
            with self.assertRaisesRegex(lc.Refused, "ordered argv"):
                lc.cache_materialize_check(spec, experiment, manifest)

    def test_compact_collection_streams_binary_identity_and_rejects_reordered_or_partial_cache(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            streams = [
                {"path": "/fixture/a.gz", "sha256": "a" * 64, "bytes": 3, "mode": "0644"},
                {"path": "/fixture/b.gz", "sha256": "b" * 64, "bytes": 4, "mode": "0644"},
            ]
            cache = {
                "schema": "quoridor-common-corpus-terminal-geometry-v3",
                "rows": 2,
                "stream_intake": {"status": "complete", "scope": "common-corpus"},
                "source_binding": [{k: r[k] for k in ("path", "sha256")} for r in streams],
                "source_content": [
                    {
                        "encoding": "gzip-single-member-v1",
                        "compressed": r,
                        "raw_sha256": "d" * 64,
                        "raw_bytes": 8,
                    }
                    for r in streams
                ],
                "files": {n: n for n in lc.COMPACT_CACHE_WIDTHS},
                "sha256": {},
                "file_bytes": {},
            }
            data = []
            for name, width in lc.COMPACT_CACHE_WIDTHS.items():
                p = root / name
                p.write_bytes(bytes(2 * width))
                cache["sha256"][name] = lc.sha(p.read_bytes())
                cache["file_bytes"][name] = 2 * width
                data.append({"name": name, "path": str(p), "limit_B": 2 * width})
            metadata = root / "cache.json"
            metadata.write_text(json.dumps(cache))
            data.append({"name": "cache_manifest", "path": str(metadata), "limit_B": 8192})
            spec = {"owner": tmp, "data_root": tmp, "data": data}
            experiment = {
                "phase": "materialize",
                "planned_slots": 0,
                "config": {},
                "build_manifest": {"path": "/fixture/build"},
                "argv": ["converter", "--input"],
            }
            original_bound = lc.bound

            def no_binary_allocation(path, *args, **kwargs):
                self.assertNotIn(Path(path).name, lc.COMPACT_CACHE_WIDTHS)
                return original_bound(path, *args, **kwargs)

            with (
                patch.object(
                    lc,
                    "document",
                    side_effect=lambda ref: {"artifact_target": "terminal-cache"}
                    if ref == experiment["build_manifest"]
                    else {"streams": streams},
                ),
                patch.object(lc, "bound", side_effect=no_binary_allocation),
            ):
                actual = lc.collect_data(spec, experiment)
                self.assertEqual(actual["status"], "PASS")
                self.assertEqual(len(actual["files"]), 8)
                cache["source_content"].reverse()
                metadata.write_text(json.dumps(cache))
                self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED")
                cache["source_content"].reverse()
                metadata.write_text(json.dumps(cache))
                (root / "intake-incomplete.json").write_text("incomplete")
                self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED")
                (root / "intake-incomplete.json").unlink()
                (root / "labels.f32").write_bytes(b"partial")
                self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED")

    def test_decisions_use_finite_settings_and_preserve_scope_and_launch_environment(self):
        plan = {"path": "/fixture/plan", "sha256": "a" * 64}
        experiment = {"phase": "compare", "batch": 2, "argv": ["runner", "decisions"]}
        spec = {
            "settings": {"path": "/fixture/settings"},
            "experiment": {"path": "/fixture/experiment"},
            "owner": "/fixture",
            "writer": "fixture",
            "cwd": "/fixture",
            "limits": {},
            "support": {},
            "approved_plan": plan,
            "artifact": {},
            "caller_sources": [],
            "env": {"BOUND": "same"},
        }
        settings = {"kind": "sequence", "arena": {"range": [0, 3], "template": copy.deepcopy(spec)}}

        def document(ref):
            return settings if ref == spec["settings"] else experiment

        with patch.object(lc, "document", side_effect=document):
            spec["env"].update(QUORIDOR_LIFECYCLE_PARENT_PID="42", TMPDIR="/fixture/own-TMP")
            self.assertEqual(lc.selected_arena(spec), plan)
            spec["env"]["BOUND"] = "changed"
            with self.assertRaisesRegex(lc.Refused, "environment drift"):
                lc.selected_arena(spec)
            spec["env"]["BOUND"] = "same"
            experiment["argv"][1] = "other-operation"
            with self.assertRaisesRegex(lc.Refused, "outside selected"):
                lc.selected_arena(spec)
            experiment["argv"][1] = "decisions"
            experiment["batch"] = 4
            with self.assertRaisesRegex(lc.Refused, "outside selected"):
                lc.selected_arena(spec)

    def test_corpus_quantity_is_configured_and_cpu_scope_is_owned(self):
        config = {
            "common_study": {"root_value_policy": "outcome_only", "batch_count": 3},
            "output": "/tmp/owned-data",
            "planned_games": 3,
            "depth": 6,
            "max_nodes": 100,
            "max_total_nodes": 900,
            "worker_cores": [1, 4],
            "cpu_core": 1,
            "game_workers": 2,
        }
        experiment = {
            "phase": "corpus",
            "config": {},
            "models": [],
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "argv": [
                "runner",
                "teacher-pilot",
                "--experiment",
                "@EXPERIMENT@",
                "--experiment-sha256",
                "@EXPERIMENT_SHA256@",
            ],
        }
        spec = {
            "data_root": config["output"],
            "child_cpu_cores": [1, 4, 6, 8],
            "limits": {"worker_cpu": 1, "guardian_cpu": 6},
        }
        with (
            patch.object(lc, "document", return_value=config),
            patch.object(lc, "numerical_check") as numeric,
        ):
            for count in (3, 12):
                config["planned_games"] = count
                config["common_study"]["batch_count"] = count
                lc.common_study_check(spec, experiment, {}, {})
            self.assertEqual(numeric.call_count, 2)
            bad = copy.deepcopy(spec)
            bad["limits"]["guardian_cpu"] = 4
            with self.assertRaisesRegex(lc.Refused, "workers/guardian"):
                lc.common_study_check(bad, experiment, {}, {})
            experiment["models"] = [{"descriptor": "foreign model"}]
            with self.assertRaisesRegex(lc.Refused, "model-free"):
                lc.common_study_check(spec, experiment, {}, {})

    def test_mixed_inputs_are_shared_and_initializer_and_cache_custody_remain_checked(self):
        warm = {
            "descriptor": {"path": "/models/descriptor"},
            "weights": {"path": "/models/weights"},
            "evaluator_sha256": "a" * 64,
            "optimizer": "fresh",
            "scale": "incumbent",
        }
        public = {"path": "/shared-public/cache.json"}
        acceptance = {"path": "/accepted-public.json"}
        cache_ref = {"path": "/new-data/cache.json", "bytes": 4096}
        cache = {
            "rows": 10,
            "stream_intake": {"status": "complete"},
            "sha256": {},
            "file_bytes": {},
            "common_corpus": {"common_eligible_by_split": {"train": 6, "validation": 4}},
        }
        inputs = [public, acceptance, cache_ref]
        for name, width in lc.COMPACT_CACHE_WIDTHS.items():
            cache["sha256"][name] = "b" * 64
            cache["file_bytes"][name] = 10 * width
            inputs.append({"path": "/new-data/" + name, "sha256": "b" * 64, "bytes": 10 * width})
        config = {
            "training": {"target": "z"},
            "experiment": {"study": "mixed-outcome", "warm_start": warm},
            "mixture": {"public_membership": public, "public_acceptance": acceptance},
        }
        experiment = {
            "phase": "fit",
            "config": {"path": "/settings.json"},
            "planned_slots": 0,
            "rules": "research-standard-2p-threefold-goal-first-v1",
            "distance_units": "wall-distance/80",
            "value_perspective": "side-to-move",
            "inputs": inputs,
            "models": [{k: warm[k] for k in ("descriptor", "weights", "evaluator_sha256")}],
        }
        spec = {
            "data_root": "/tmp/fit-data",
            "argv": [
                sys.executable,
                "-B",
                "-m",
                "quoridor_training.train",
                "train",
                "--cache",
                "/new-data",
                "--output",
                "/tmp/fit-data",
                "--config",
                "/settings.json",
            ],
        }

        def document(ref):
            return cache if ref == cache_ref else config

        with (
            patch.object(lc, "document", side_effect=document),
            patch.object(lc, "read_ref", side_effect=lambda ref, limit: json.dumps(cache).encode()),
            patch.object(lc, "project_python", return_value=Path(sys.executable)),
            patch.object(lc, "project_interpreter"),
            patch.object(lc, "common_training_environment"),
            patch.object(lc, "numerical_check"),
        ):
            lc.common_study_check(spec, experiment, {}, {})
            experiment["inputs"].append({"path": "/shared-public/train.bin"})
            with self.assertRaisesRegex(lc.Refused, "indexed/shared"):
                lc.common_study_check(spec, experiment, {}, {})
            experiment["inputs"].pop()
            warm["scale"] = "new-T-renormalized"
            with self.assertRaisesRegex(lc.Refused, "original scale"):
                lc.common_study_check(spec, experiment, {}, {})
            warm["scale"] = "incumbent"
            inputs[-1]["bytes"] += 1
            with self.assertRaisesRegex(lc.Refused, "binary custody"):
                lc.common_study_check(spec, experiment, {}, {})

    def test_partial_corpus_result_retains_actual_counts_without_plan_census_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = root / "generation.json"
            saved = {
                "scheduled": 5,
                "recorded": 3,
                "goals": 1,
                "draws": 1,
                "unknown": 1,
                "search_nodes": 37,
            }
            result.write_text(json.dumps(saved))
            spec = {
                "owner": tmp,
                "data_root": tmp,
                "data": [{"name": "generation_result", "path": str(result), "limit_B": 4096}],
            }
            experiment = {
                "phase": "corpus",
                "planned_slots": 8,
                "argv": ["runner", "teacher-pilot"],
            }
            actual = lc.collect_data(spec, experiment)
            self.assertEqual(actual["status"], "PASS")
            self.assertEqual(actual["corpus"], saved)
            self.assertEqual(actual["planned_slots"], 8)
            self.assertNotIn("evaluations", actual["corpus"])
            self.assertFalse(actual["global_campaign_complete"])
            saved["recorded"] = 6
            result.write_text(json.dumps(saved))
            refused = lc.collect_data(spec, experiment)
            self.assertEqual(refused["status"], "FAILED")
            self.assertIn("actual generation census", refused["errors"][0]["message"])

    def test_early_stopped_fit_preserves_actual_exposure_and_original_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "training.json"
            state = {
                "status": "EARLY_STOPPED",
                "step": 7,
                "forward_rows": 29,
                "added_seen": 12,
                "public_seen": 12,
            }
            result.write_text(json.dumps(state))
            spec = {
                "owner": tmp,
                "data_root": tmp,
                "data": [{"name": "training", "path": str(result), "limit_B": 4096}],
            }
            experiment = {"phase": "fit", "planned_slots": 0, "argv": ["python", "-B"]}
            actual = lc.collect_data(spec, experiment)
            self.assertEqual(actual["status"], "PASS")
            self.assertEqual(actual["fit"], state)
            self.assertNotIn("aggregate_forward_rows", actual["fit"])
            state["status"] = "FAILED"
            result.write_text(json.dumps(state))
            refused = lc.collect_data(spec, experiment)
            self.assertEqual(refused["status"], "FAILED")
            self.assertIn("did not complete", refused["errors"][0]["message"])


if __name__ == "__main__":
    unittest.main()
