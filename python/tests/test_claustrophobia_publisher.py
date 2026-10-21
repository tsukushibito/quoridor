"""Actual publisher model/caller branch with explicitly synthetic metadata ports."""

import ast
import math
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve()
POST = HERE.parents[2]
PUBLISHER = POST / "scripts/dev/research-lifecycle.py"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def functions(**ports):
    names = {"arena_model_check", "caller_source_refs"}
    tree = ast.parse(PUBLISHER.read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(selected) == len(names)
    namespace = dict(require=require, Path=Path, math=math, **ports)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(PUBLISHER), "exec"), namespace)
    return namespace


class ClaustrophobiaPublisherTests(unittest.TestCase):
    def setUp(self):
        self.python = Path("/synthetic/common/bin/python")
        self.settings = dict(
            python=str(self.python),
            library="/synthetic/current.so",
            library_sha256="a" * 64,
            model_sha256="b" * 64,
            simulations=8,
            c_puct=1.5,
            max_head_calls=9,
        )
        self.engine = dict(
            kind="claustrophobia", model="/synthetic/champion.pt", claustrophobia=self.settings
        )
        self.plan = dict(
            comparison="whole_wall_time",
            models=[],
            inputs=[dict(path=self.engine["model"], sha256="b" * 64)],
            matchups=[dict(id=0, engines=[self.engine], evaluator_sha256=["c" * 64])],
        )
        self.experiment = dict(
            dynamic_libraries=[dict(file=dict(path="/synthetic/current.so", sha256="a" * 64))]
        )
        self.owner = functions(project_python=lambda: self.python)["arena_model_check"]

    def test_actual_owner_accepts_declared_upstream_tuple_without_sigma_alias(self):
        self.owner(self.experiment, self.plan, 1)
        self.plan["matchups"][0]["inference"] = dict(backend="ort")
        with self.assertRaisesRegex(ValueError, "unused/missing"):
            self.owner(self.experiment, self.plan, 1)

    def test_model_library_interpreter_drift_and_nonaligned_phase_refuse(self):
        for field, wrong in (
            ("model_sha256", "d" * 64),
            ("library_sha256", "d" * 64),
            ("library", "/synthetic/other.so"),
            ("python", "/foreign/python"),
            ("simulations", True),
            ("max_head_calls", 0),
        ):
            original = self.settings[field]
            self.settings[field] = wrong
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.owner(self.experiment, self.plan, 1)
            self.settings[field] = original
        self.plan["comparison"] = "evaluator_fixed_depth"
        with self.assertRaises(ValueError):
            self.owner(self.experiment, self.plan, 1)

    def test_actual_caller_membership_requires_helper_head_interpreter_and_cfg(self):
        # Test fixtures remain inside the delegated namespace, not a shared /tmp.
        with tempfile.TemporaryDirectory(
            prefix="claustrophobia-publisher-", dir=POST.parent
        ) as directory:
            root = Path(directory)
            python = root / "env/bin/python"
            python.parent.mkdir(parents=True)
            python.write_text("synthetic interpreter file, never executed\n")
            owner = functions(
                ROOT=root,
                project_python=lambda: python,
                document=lambda _: dict(engines=[self.engine]),
            )["caller_source_refs"]
            base = {
                root / "scripts/dev/research-lifecycle.py",
                root / "scripts/dev/research-job.py",
                root / "shared/python/quoridor_runtime/__init__.py",
                root / "shared/python/quoridor_runtime/cycle_process.py",
                root / "shared/python/quoridor_runtime/snapshot.py",
            }
            all_paths = base | {
                root / "games/quoridor/python/quoridor_training/claustrophobia.py",
                root / "games/quoridor/python/quoridor_training/static_teacher_heads.py",
                python.resolve(),
                root / "env/pyvenv.cfg",
            }
            refs = [dict(path=str(path)) for path in all_paths]
            spec = dict(caller_sources=refs)
            experiment = dict(phase="arena", config={})
            self.assertEqual(owner(spec, experiment), refs)
            for omitted in all_paths - base:
                with self.subTest(omitted=omitted), self.assertRaises(ValueError):
                    owner(
                        dict(caller_sources=[r for r in refs if r["path"] != str(omitted)]),
                        experiment,
                    )


if __name__ == "__main__":
    unittest.main()
