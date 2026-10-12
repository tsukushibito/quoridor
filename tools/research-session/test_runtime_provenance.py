"""375 publisher-shaped synthetic boundary tests; no native/model/numerical execution."""

import copy
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
module = importlib.util.spec_from_file_location("lc375", ROOT / "scripts/dev/research-lifecycle.py")
lc = importlib.util.module_from_spec(module)
module.loader.exec_module(lc)


class FixtureResources:
    """Only the outer guarded software-test job supplies physical/ownership admission."""

    def __init__(self, _spec):
        self.deadline = time.monotonic() + 10

    def check(self, _children=()):
        pass


class RuntimeProvenanceTests(unittest.TestCase):
    def setUp(self):
        # Qualification fixtures are explicitly synthetic, not retained real images or Q.
        self.tmp = tempfile.TemporaryDirectory(prefix="provenance375-", dir=os.environ["TMPDIR"])
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.file("crates/fixture/src/lib.rs", b"synthetic native source A\n")
        manifest = self.file("Cargo.toml", b"[workspace]\n")
        lock = self.file("Cargo.lock", b"synthetic immutable lock A\n")
        compiler = self.file("compiler", b"never executed synthetic compiler", 0o755)
        dependency = self.file("build-dependency", b"synthetic build input A")
        self.cargo_config = self.root / ".cargo/config.toml"
        self.source_info = {
            "workspace": str(self.root),
            "commit": "a" * 40,
            "patch": None,
            "untracked_inputs": [],
            "manifest": self.ref(manifest),
            "lock": self.ref(lock),
            "cargo_configs": [{"path": str(self.cargo_config), "file": None}],
        }
        for args in (
            ["init", "-q"],
            ["add", "crates/fixture/src/lib.rs", "Cargo.toml", "Cargo.lock"],
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
        script = (
            f"#!{sys.executable}\n"
            "import json,pathlib,sys\n"
            "c=json.loads(pathlib.Path(sys.argv[2]).read_text())\n"
            "out=pathlib.Path(c['output']); out.mkdir()\n"
            "(out/'result.json').write_text(json.dumps({'fixture':'NOT_SCIENCE','complete':True}))\n"
            "if c.get('mutate_caller'): pathlib.Path(c['mutate_caller']).write_text('caller drift')\n"
            "print('synthetic immutable image A')\n"
        )
        artifact = self.file("private/fixture-image-A", script.encode(), 0o755)
        self.build = {
            "schema": lc.BUILD_SCHEMA,
            "status": "PASS",
            "cleanup_complete": True,
            "remaining": [],
            "checks": [{"role": role} for role in ("test", "lint", "build")],
            "source": copy.deepcopy(self.source_info),
            "artifact": self.ref(artifact),
            "dependency_refs": [self.ref(dependency), self.ref(lock)],
            "tools": {"CARGO": {"file": self.ref(compiler), "version": "synthetic v1"}},
        }
        self.build_ref = self.json("build/manifest.json", self.build)
        self.config = self.json("config.json", {"output": str(self.root / "data")})
        plan = self.json("plan.json", {"fixture_only": "NOT_SCIENTIFIC_APPROVAL"})
        self.library = self.file("runtime-library", b"not loaded; runtime file identity fixture")
        self.descriptor = self.json("model/descriptor.json", {"fixture_only": "NOT_MODEL"})
        self.weights = self.file("model/weights.f32", b"NOT_MODEL_PAYLOAD")
        self.input = self.file("input", b"synthetic ordered input")
        callers = [
            self.file(name, b"synthetic current caller")
            for name in (
                "scripts/dev/research-lifecycle.py",
                "scripts/dev/research-job.py",
                "python/quoridor_training/cycle_process.py",
                "python/quoridor_training/snapshot.py",
            )
        ]
        self.experiment = {
            "schema": lc.EXPERIMENT_SCHEMA,
            "phase": "compare",
            "build_manifest": self.build_ref,
            "config": self.config,
            "inputs": [self.ref(self.input)],
            "models": [{"descriptor": self.descriptor, "weights": self.ref(self.weights)}],
            "dynamic_libraries": [{"file": self.ref(self.library), "version": "synthetic v1"}],
            "schedule": self.json("schedule.json", {"fixture_only": True}),
            "numerical_qualification": self.json("not-numerical.json", {"fixture_only": True}),
            "planned_slots": 0,
            "canonical_plan_sha256": plan["sha256"],
            "argv": [str(artifact), "fixture-only", self.config["path"]],
        }
        self.spec = {
            "schema": "quoridor.research.lifecycle-intent.v1",
            "kind": "run",
            "owner": str(self.root),
            "cwd": str(self.root),
            "output": str(self.root / "operation"),
            "data_root": str(self.root / "data"),
            "data": [
                {"name": "result", "path": str(self.root / "data/result.json"), "limit_B": 1024}
            ],
            "artifact": self.build["artifact"],
            "argv": self.experiment["argv"],
            "experiment": self.json("experiment.json", self.experiment),
            "approved_plan": plan,
            "caller_sources": [self.ref(p) for p in callers],
            "finalizers": [],
            "limits": {"log_B": 8192, "worker_cpu": 1},
            "env": {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            "support": self.json("support.json", {"fixture_only": True}),
        }
        port = patch.object(lc, "ROOT", self.root)
        port.start()
        self.addCleanup(port.stop)

    def file(self, name, data, mode=0o644):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)
        return path

    def ref(self, path):
        return lc.bound(path)[0]

    def json(self, name, value):
        return self.ref(self.file(name, (json.dumps(value) + "\n").encode()))

    def intent(self):
        view = {k: v for k, v in self.spec.items() if k not in {"admission", "intent_sha256"}}
        self.spec["intent_sha256"] = lc.canonical_sha(view)
        self.spec["admission"] = self.json(
            "admission.json",
            {
                "schema": "quoridor.research.phase-admission.v1",
                "ready": True,
                "owner": self.spec["owner"],
                "limits": self.spec["limits"],
                "approved_plan": self.spec["approved_plan"],
                "support_sha256": self.spec["support"]["sha256"],
                "spec_sha256": self.spec["intent_sha256"],
            },
        )
        return self.json("intent.json", self.spec)

    def origin(self, intent, spec):
        # Synthetic outer-origin port; the actual child below uses the real guardian.
        config = {
            "argv": [
                sys.executable,
                "-B",
                str(self.root / "scripts/dev/research-lifecycle.py"),
                "run",
                "--intent",
                intent["path"],
                "--sha256",
                intent["sha256"],
            ],
            "cwd": spec["cwd"],
        }
        return {
            "runtime": str(self.root / "job"),
            "job_id": "synthetic-origin375",
            "config": self.json("job/config.json", config),
            "config_sha256": lc.sha(json.dumps(config, sort_keys=True).encode()),
            "supervisor": {"pid": 999990, "start_ticks": "1", "boot_id": "fixture"},
            "child": {"pid": 999991, "start_ticks": "2", "boot_id": "fixture"},
        }

    def run_child(self):
        with patch.object(lc, "originating_job", self.origin):
            return lc.execute(
                self.intent(),
                guard=lambda _: None,
                lock=nullcontext,
                resource_factory=FixtureResources,
            )

    def test_image_A_runs_and_finalizes_while_current_build_inputs_are_B(self):
        saved = Path(self.build_ref["path"]).read_bytes()
        self.source.write_bytes(b"current native source B")
        for path in (
            self.build["source"]["lock"]["path"],
            self.build["tools"]["CARGO"]["file"]["path"],
            self.build["dependency_refs"][0]["path"],
        ):
            Path(path).unlink()
        self.cargo_config.parent.mkdir()
        self.cargo_config.write_text("[build]\n")
        self.intent()
        _, manifest, refs = lc.experiment_check(self.spec)
        self.assertIn(self.build["artifact"], refs)
        self.assertNotIn(self.source_info["lock"], refs)
        self.assertNotIn(self.build["tools"]["CARGO"]["file"], refs)
        self.assertNotIn(self.ref(self.source), refs)
        candidate = self.run_child()
        returned = candidate["checks"][0]["guardian_return"]
        self.assertTrue(returned["direct_child_reaped"] and returned["cleanup_complete"])
        self.assertEqual(returned["remaining"], [])
        origin = candidate["originating_job"]
        self.json(
            "job/state.json",
            {
                "phase": "finished",
                "outcome": "succeeded",
                **{key: origin[key] for key in ("job_id", "config_sha256", "supervisor", "child")},
            },
        )
        job = self.json(
            "job/result.json",
            {
                "job_id": origin["job_id"],
                "outcome": "succeeded",
                "exit_code": 0,
                "finished_at": "synthetic-only",
                "direct_child_reaped": True,
                "cleanup_complete": True,
                "remaining": [],
                "cleanup_errors": [],
            },
        )
        final = lc.finalize(
            Path(self.spec["output"]),
            job,
            guard=lambda _: None,
            lock=nullcontext,
            resource_factory=FixtureResources,
        )
        self.assertEqual(final["status"], "PASS")
        self.assertFalse((Path(self.spec["output"]) / "INCOMPLETE").exists())
        self.assertEqual(Path(self.build_ref["path"]).read_bytes(), saved)
        self.assertEqual(self.source.read_bytes(), b"current native source B")

    def test_runtime_artifact_caller_library_model_config_input_and_plan_drift_refuse(self):
        self.intent()
        refs = [
            self.build["artifact"],
            self.spec["caller_sources"][0],
            self.ref(self.library),
            self.descriptor,
            self.ref(self.weights),
            self.config,
            self.ref(self.input),
            self.spec["approved_plan"],
        ]
        for ref in refs:
            with self.subTest(path=ref["path"]):
                path = Path(ref["path"])
                before = path.read_bytes()
                path.write_bytes(before + b"drift")
                with self.assertRaises(lc.Refused):
                    lc.experiment_check(self.spec)
                self.assertFalse(Path(self.spec["output"]).exists())
                path.write_bytes(before)

    def test_actual_returned_child_cannot_hide_current_caller_lifetime_drift(self):
        self.config = self.json(
            "config.json",
            {
                "output": self.spec["data_root"],
                "mutate_caller": self.spec["caller_sources"][0]["path"],
            },
        )
        self.experiment["config"] = self.config
        self.spec["experiment"] = self.json("experiment.json", self.experiment)
        with self.assertRaisesRegex(lc.Refused, "Git delta drift"):
            self.run_child()
        candidate = json.loads((Path(self.spec["output"]) / "candidate.json").read_bytes())
        self.assertEqual(candidate["status"], "FAILED")
        self.assertEqual(candidate["checks"][0]["guardian_return"]["exit_code"], 0)
        self.assertTrue(candidate["checks"][0]["guardian_return"]["direct_child_reaped"])
        self.assertEqual(candidate["data"]["status"], "PASS")
        self.assertTrue((Path(self.spec["output"]) / "INCOMPLETE").exists())

    def test_invalid_incomplete_or_misbound_build_manifest_refuses(self):
        self.intent()
        for key, value in (
            ("status", "FAILED"),
            ("cleanup_complete", False),
            ("remaining", ["unknown"]),
            ("schema", "unknown"),
            ("checks", []),
        ):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.build)
                bad[key] = value
                e = dict(self.experiment, build_manifest=self.json("bad/manifest.json", bad))
                self.spec["experiment"] = self.json("experiment.json", e)
                with self.assertRaises(lc.Refused):
                    lc.experiment_check(self.spec)
                self.assertFalse(Path(self.spec["output"]).exists())
        self.spec["experiment"] = self.json("experiment.json", self.experiment)
        marker = Path(self.build_ref["path"]).with_name("INCOMPLETE")
        marker.write_text("provisional")
        with self.assertRaisesRegex(lc.Refused, "provisional"):
            lc.experiment_check(self.spec)

    def test_build_source_checks_retained_files_and_cargo_absence(self):
        lc.source_check(self.source_info)
        self.source.write_bytes(b"native B")
        with self.assertRaisesRegex(lc.Refused, "Git delta drift"):
            lc.source_check(self.source_info)
        self.source.write_bytes(b"synthetic native source A\n")
        self.cargo_config.parent.mkdir()
        self.cargo_config.write_text("[build]\n")
        with self.assertRaisesRegex(lc.Refused, "Cargo config appeared"):
            lc.source_check(self.source_info)


if __name__ == "__main__":
    unittest.main()
