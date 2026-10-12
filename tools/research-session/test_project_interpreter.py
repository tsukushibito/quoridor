"""New admitted-current-interpreter helper boundaries; metadata only, no binary run."""

import ast
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
from unittest.mock import patch
import types
import unittest

SOURCE = Path(os.environ.get("QUORIDOR_ENV_TEST_SOURCE", Path(__file__).resolve().parents[2]))
TMP = Path(os.environ.get("QUORIDOR_ENV_TEST_TMP", tempfile.gettempdir()))
text = (SOURCE / "scripts/dev/research-lifecycle.py").read_text()
tree = ast.parse(text)
names = {"Refused", "require", "project_interpreter", "project_python"}
selected = [
    x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.ClassDef)) and x.name in names
]
PORT = types.ModuleType("project_interpreter_metadata_port")
PORT.__dict__.update(Path=Path, json=json, os=os, subprocess=subprocess)
exec(
    compile(ast.Module(body=selected, type_ignores=[]), "actual-owning-helper-definitions", "exec"),
    PORT.__dict__,
)


class ProjectInterpreterContracts(unittest.TestCase):
    def test_current_venv_regular_input_and_cfg_required_for_all_python_phases(self):
        # Regular binary identity is the unchanged accepted366 input; it is never
        # executed or payload-hashed here. Input hash/mode/size are fixture facts.
        base = Path(
            "/home/vscode/.cache/inference/python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14"
        )
        expected = {
            "path": str(base),
            "sha256": "5a91882290532b2719eaca77c0f3a7448bd73b9214e56df57bc59004560a80c6",
            "bytes": 32418544,
            "mode": "0755",
        }
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            environment = root / "environment"
            (environment / "bin").mkdir(parents=True)
            (environment / "bin/python").symlink_to(base)
            cfg = environment / "pyvenv.cfg"
            cfg.write_text("synthetic metadata\n")
            (root / "research-paths.json").write_text(
                json.dumps({"environments": {"project": str(environment)}})
            )
            PORT.ROOT = root
            self.enterContext(
                patch.dict(
                    os.environ,
                    {"QUORIDOR_PROJECT_ROOT": str(root), "QUORIDOR_PROJECT_ENV": str(environment)},
                )
            )
            self.enterContext(
                patch.object(
                    PORT.subprocess, "check_output", return_value=str(root / ".git") + "\n"
                )
            )
            cfg_ref = {
                "path": str(cfg),
                "sha256": "fixture",
                "bytes": cfg.stat().st_size,
                "mode": "0644",
            }
            for phase in ("analysis", "fit", "software-qualification"):
                experiment = {"phase": phase, "inputs": [expected, cfg_ref]}
                self.assertEqual(PORT.project_interpreter(experiment), expected)
                with self.assertRaisesRegex(PORT.Refused, "separately input-bound"):
                    PORT.project_interpreter({"phase": phase, "inputs": [expected]})
                with self.assertRaisesRegex(PORT.Refused, "bound qualified"):
                    PORT.project_interpreter(
                        {"phase": phase, "inputs": [{**expected, "sha256": "drift"}, cfg_ref]}
                    )
            with self.assertRaisesRegex(PORT.Refused, "project interpreter phase"):
                PORT.project_interpreter({"phase": "arena", "inputs": [expected, cfg_ref]})
            (environment / "bin/python").unlink()
            wrong = root / "foreign-python"
            wrong.write_text("synthetic foreign binary\n")
            (environment / "bin/python").symlink_to(wrong)
            with self.assertRaisesRegex(PORT.Refused, "regular binary correspondence"):
                PORT.project_interpreter({"phase": "analysis", "inputs": [expected, cfg_ref]})

    def test_managed_worktree_defaults_use_main_metadata_and_refuse_foreign_bindings(self):
        # The actual default verifier/main and lifecycle helpers run with a
        # naturally worktree-local __file__. Git and numerical identity are
        # explicit synthetic ports; no package sync, import or binary execution.
        with tempfile.TemporaryDirectory(dir=TMP) as name:
            root = Path(name)
            main, worktree = root / "main", root / "worktree"
            main.mkdir()
            script_dir = worktree / "scripts/dev"
            script_dir.mkdir(parents=True)
            for script in ("verify-python-environment.py", "research-lifecycle.py"):
                (script_dir / script).write_bytes((SOURCE / "scripts/dev" / script).read_bytes())
            environment = root / "shared-env"
            (environment / "bin").mkdir(parents=True)
            base = Path(
                "/home/vscode/.cache/inference/python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14"
            )
            (environment / "bin/python").symlink_to(base)
            cfg = environment / "pyvenv.cfg"
            cfg.write_text("synthetic shared environment identity\n")
            (main / "pyproject.toml").write_text(
                '[tool.uv]\nconstraint-dependencies=["websockets==17.1"]\n'
            )
            (main / "research-paths.json").write_text(
                json.dumps({"environments": {"project": str(environment)}})
            )
            expected = {
                "path": str(base),
                "sha256": "5a91882290532b2719eaca77c0f3a7448bd73b9214e56df57bc59004560a80c6",
                "bytes": 32418544,
                "mode": "0755",
            }
            experiment = {
                "phase": "analysis",
                "inputs": [
                    expected,
                    {
                        "path": str(cfg),
                        "sha256": "fixture",
                        "bytes": cfg.stat().st_size,
                        "mode": "0644",
                    },
                ],
            }
            distribution = type(
                "SyntheticDistribution",
                (),
                {"version": "17.1", "locate_file": lambda self, path: environment},
            )()
            modules = []
            # Only the lifecycle's existing stdlib guardian imports from Main.
            # No worktree metadata/source mirror is supplied for its ROOT.
            with patch.object(sys, "path", [str(Path("/workspaces/quoridor/python")), *sys.path]):
                for script in ("verify-python-environment.py", "research-lifecycle.py"):
                    spec = importlib.util.spec_from_file_location(
                        "synthetic_worktree_" + script, script_dir / script
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    modules.append(module)
            verifier, publisher = modules
            self.assertEqual(verifier.ROOT, worktree)
            self.assertEqual(publisher.ROOT, worktree)
            self.assertEqual(publisher.ORIGIN_CUSTODY, worktree / "research-data")
            with (
                patch.dict(
                    os.environ,
                    {"QUORIDOR_PROJECT_ROOT": str(main), "QUORIDOR_PROJECT_ENV": str(environment)},
                ),
                patch.object(subprocess, "check_output", return_value=str(main / ".git") + "\n"),
                patch.object(verifier.sys, "version_info", (3, 14, 7)),
                patch.object(verifier.sys, "prefix", str(environment)),
                patch.object(verifier.sys, "base_prefix", "/synthetic-base"),
                patch.object(verifier.platform, "python_version", return_value="3.14.7"),
                patch.object(verifier.sysconfig, "get_config_var", return_value=0),
                patch.object(
                    verifier.importlib.metadata, "distribution", return_value=distribution
                ),
                patch.object(verifier.importlib, "import_module") as scientific_imports,
                patch.object(sys, "argv", [str(script_dir / "verify-python-environment.py")]),
            ):
                for stale in (False, True):
                    if stale:
                        (worktree / "pyproject.toml").write_text(
                            '[tool.uv]\nconstraint-dependencies=["websockets==WRONG"]\n'
                        )
                        (worktree / "research-paths.json").write_text(
                            json.dumps({"environments": {"project": str(root / "foreign-env")}})
                        )
                    output = io.StringIO()
                    with redirect_stdout(output):
                        verifier.main()
                    report = json.loads(output.getvalue())
                    self.assertEqual(report["packages"], {"websockets": "17.1"})
                    self.assertEqual(publisher.project_interpreter(experiment), expected)
                with patch.dict(os.environ, {"QUORIDOR_PROJECT_ENV": str(root / "foreign-env")}):
                    with self.assertRaisesRegex(RuntimeError, "Canonical shared"):
                        verifier.verify()
                    with self.assertRaisesRegex(publisher.Refused, "canonical shared"):
                        publisher.project_python()
                with patch.dict(os.environ, {"QUORIDOR_PROJECT_ROOT": str(worktree)}):
                    with self.assertRaisesRegex(RuntimeError, "Canonical Main"):
                        verifier.verify()
                    with self.assertRaisesRegex(publisher.Refused, "canonical Main"):
                        publisher.project_python()
                with self.assertRaisesRegex(RuntimeError, "Foreign project metadata"):
                    verifier.verify(worktree)
                scientific_imports.assert_not_called()


if __name__ == "__main__":
    unittest.main()
