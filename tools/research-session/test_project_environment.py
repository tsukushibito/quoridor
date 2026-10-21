"""New common-entry NN0 contracts; synthetic tools, no package installs or models."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(os.environ.get("QUORIDOR_ENV_TEST_SOURCE", Path(__file__).resolve().parents[2]))
TMP = Path(os.environ.get("QUORIDOR_ENV_TEST_TMP", tempfile.gettempdir()))
ENTRY = SOURCE / "scripts/dev/project-env.sh"


def executable(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


class CommonEnvironmentTests(unittest.TestCase):
    def fixture(self, root):
        project = root / "main"
        project.mkdir()
        (project / ".git").mkdir()
        (project / "pyproject.toml").write_text('[project]\nname="synthetic"\n')
        (project / "uv.lock").write_text("synthetic canonical lock\n")
        for relative in (
            "games/quoridor/python/quoridor_training/__init__.py",
            "shared/python/quoridor_runtime/__init__.py",
            "shared/python/quoridor_runtime/cycle_process.py",
            "shared/python/quoridor_runtime/snapshot.py",
        ):
            source = project / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("# synthetic source marker\n")
        binary = root / "tools"
        executable(
            binary / "git",
            '#!/bin/sh\ncase "$*" in *--show-toplevel*) printf "%s\\n" "$FAKE_MAIN";; '
            '*--git-common-dir*) printf "%s\\n" "$FAKE_MAIN/.git";; *) exit 2;; esac\n',
        )
        executable(
            binary / "uv",
            """#!/bin/bash
printf '%s\n' "$@" > "$UV_ARGS"
printf '%s\n' "$PWD" "$UV_PROJECT_ENVIRONMENT" "$PYTHONPATH" > "$UV_CONTEXT"
if [[ -n "${WAIT_GATE:-}" ]]; then
  touch "$STARTED"
  until [[ -f "$WAIT_GATE" ]]; do sleep .01; done
fi
""",
        )
        environment = root / "environment"
        executable(
            environment / "bin/python",
            """#!/bin/bash
[[ "$1" == -I && "$2" == -c ]] || exit 90
[[ "${INVALID_VERSION:-0}" == 0 ]] || exit 1
""",
        )
        (environment / "pyvenv.cfg").write_text("synthetic venv identity only\n")
        (project / "research-paths.json").write_text(
            json.dumps({"environments": {"project": str(environment)}})
        )
        reports = root / "reports"
        reports.mkdir()
        Path(str(environment) + ".setup.lock").touch()
        env = {
            **os.environ,
            "PATH": str(binary) + ":/usr/bin:/bin",
            "FAKE_MAIN": str(project),
            "UV_ARGS": str(root / "args"),
            "UV_CONTEXT": str(root / "context"),
            "QUORIDOR_PROJECT_ENV": str(environment),
            "QUORIDOR_ENV_REPORT_DIR": str(reports),
        }
        return project, environment, reports, env

    def run_entry(self, root, env, *argv):
        return subprocess.run(
            ["bash", str(ENTRY), *argv],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=5,
        )

    def test_main_worktree_arbitrary_cwd_no_sync_and_argument_boundary(self):
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            project, environment, reports, env = self.fixture(root)
            cwd = root / "other-worktree"
            cwd.mkdir()
            returned = self.run_entry(cwd, env, "python", "-B", "script.py", "--with", "bad")
            self.assertEqual(returned.returncode, 0, returned.stderr)
            args = (root / "args").read_text().splitlines()
            self.assertEqual(args[:3], ["run", "--project", str(project)])
            for flag in ("--locked", "--offline", "--no-sync", "--no-python-downloads"):
                self.assertIn(flag, args)
            separator = args.index("--")
            self.assertEqual(
                args[separator + 1 :],
                [str(environment / "bin/python"), "-B", "script.py", "--with", "bad"],
            )
            self.assertEqual(
                (root / "context").read_text().splitlines(),
                [
                    str(cwd),
                    str(environment),
                    f"{project}/games/quoridor/python:{project}/shared/python",
                ],
            )
            self.assertNotIn("sync", args)
            self.assertNotIn("install", args)

    def test_missing_wrong_or_foreign_python_refuses_before_uv(self):
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            _, environment, _, env = self.fixture(root)
            for altered, command in (
                ({**env, "QUORIDOR_PROJECT_ENV": str(root / "missing")}, "python"),
                ({**env, "INVALID_VERSION": "1"}, "python"),
                (env, "/usr/bin/python3"),
                (env, "python3"),
            ):
                result = self.run_entry(root, altered, command, "-V")
                self.assertEqual(result.returncode, 2)
                self.assertFalse((root / "args").exists())

    def test_actual_reader_lock_refuses_writer_and_releases_after_child(self):
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            _, environment, reports, env = self.fixture(root)
            gate, started = root / "gate", root / "started"
            process = subprocess.Popen(
                ["bash", str(ENTRY), "python", "-B", "synthetic.py"],
                cwd=root,
                env={**env, "WAIT_GATE": str(gate), "STARTED": str(started)},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                end = time.monotonic() + 3
                while not started.exists() and time.monotonic() < end:
                    time.sleep(0.01)
                self.assertTrue(started.exists())
                lock = Path(str(environment) + ".setup.lock")
                writer = subprocess.run(
                    ["flock", "--exclusive", "--nonblock", str(lock), "true"], timeout=3
                )
                self.assertNotEqual(writer.returncode, 0)
                gate.touch()
                stdout, stderr = process.communicate(timeout=3)
                self.assertEqual(process.returncode, 0, stderr.decode())
                self.assertEqual(
                    subprocess.run(
                        ["flock", "--exclusive", "--nonblock", str(lock), "true"], timeout=3
                    ).returncode,
                    0,
                )
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=3)
                for handle in (process.stdout, process.stderr):
                    handle.close()

    def test_active_writer_refuses_before_python_or_uv(self):
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            _, environment, reports, env = self.fixture(root)
            lock = Path(str(environment) + ".setup.lock")
            import fcntl

            with lock.open("r") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = self.run_entry(
                    root,
                    {**env, "QUORIDOR_ENV_REPORT_DIR": str(root / "other-reports")},
                    "python",
                    "-V",
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("writer is active", result.stderr)
                self.assertFalse((root / "args").exists())

    def test_missing_setup_lock_refuses_without_creating_environment(self):
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            _, environment, reports, env = self.fixture(root)
            Path(str(environment) + ".setup.lock").unlink()
            before = set(environment.rglob("*"))
            result = self.run_entry(root, env, "python", "-V")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(before, set(environment.rglob("*")))
            self.assertFalse((root / "args").exists())

    def test_explicit_native_backend_keeps_one_project_env_and_refuses_missing_binding(self):
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            project, environment, _, env = self.fixture(root)
            backend = root / "isolated-native-backend"
            bindings = backend / "python"
            bindings.mkdir(parents=True)
            altered = {**env, "QUORIDOR_TENSORRT_ROOT": str(backend)}
            result = self.run_entry(root, altered, "python", "-B", "export.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            context = (root / "context").read_text().splitlines()
            self.assertEqual(context[1], str(environment))
            self.assertEqual(
                context[2], f"{bindings}:{project}/games/quoridor/python:{project}/shared/python"
            )
            (root / "args").unlink()
            bindings.rmdir()
            result = self.run_entry(root, altered, "python", "-B", "export.py")
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / "args").exists())

    def test_metadata_verifier_is_lazy_and_refuses_version_drift(self):
        spec = importlib.util.spec_from_file_location(
            "verify_project", SOURCE / "scripts/dev/verify-python-environment.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            (root / "pyproject.toml").write_text(
                '[tool.uv]\nconstraint-dependencies=["torch==2.14.0+cu130"]\n'
            )
            environment = root / "environment"
            environment.mkdir()
            (root / "research-paths.json").write_text(
                json.dumps({"environments": {"project": str(environment)}})
            )
            distribution = type(
                "Distribution",
                (),
                {"version": "2.14.0+cu130", "locate_file": lambda self, name: environment},
            )()
            with (
                patch.dict(
                    os.environ,
                    {"QUORIDOR_PROJECT_ENV": str(environment), "QUORIDOR_PROJECT_ROOT": str(root)},
                ),
                patch.object(
                    module.subprocess, "check_output", return_value=str(root / ".git") + "\n"
                ),
                patch.object(module.sys, "version_info", (3, 14, 7)),
                patch.object(module.sys, "prefix", str(environment)),
                patch.object(module.sys, "base_prefix", "/synthetic-base"),
                patch.object(module.sysconfig, "get_config_var", return_value=0),
                patch.object(module.importlib.metadata, "distribution", return_value=distribution),
                patch.object(module.importlib, "import_module") as imports,
            ):
                result = module.verify(root)
                self.assertEqual(result["packages"], {"torch": "2.14.0+cu130"})
                imports.assert_not_called()
                distribution.version = "wrong"
                with self.assertRaisesRegex(RuntimeError, "Pinned dependency drift"):
                    module.verify(root)
                imports.assert_not_called()


if __name__ == "__main__":
    unittest.main()
