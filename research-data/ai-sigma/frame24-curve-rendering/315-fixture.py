"""One canonical synthetic XML/caller fixture, stdlib only and zero inference."""

import ast
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("python").resolve()))
from quoridor_training.plotting import render_learning_curves
from quoridor_training.test_plotting import RenderingContracts

tree = ast.parse(Path("python/quoridor_training/train.py").read_text())
assert not any(isinstance(n, ast.FunctionDef) and n.name == "_plot" for n in tree.body)
calls = [
    n
    for n in ast.walk(tree)
    if isinstance(n, ast.Call)
    and isinstance(n.func, ast.Name)
    and n.func.id == "render_learning_curves"
]
assert len(calls) == 1
assert {k.arg for k in calls[0].keywords} == {"selected_step", "references", "sampling", "title"}
signature = inspect.signature(render_learning_curves)
assert all(k.arg in signature.parameters for k in calls[0].keywords)
assert "torch" not in sys.modules
contract = ast.parse(Path("python/quoridor_training/test_contracts.py").read_text())
method = next(
    n
    for n in ast.walk(contract)
    if isinstance(n, ast.FunctionDef)
    and n.name == "test_curve_artifact_has_multiple_measured_points"
)
synthetic = type("CanonicalCaller", (unittest.TestCase,), {})
code = ast.Module(body=[method], type_ignores=[])
environment = {"tempfile": tempfile, "Path": Path, "render_learning_curves": render_learning_curves}
exec(compile(code, "canonical-curve-contract", "exec"), environment)
setattr(synthetic, method.name, environment[method.name])
suite = unittest.TestSuite(
    [
        unittest.defaultTestLoader.loadTestsFromTestCase(RenderingContracts),
        unittest.defaultTestLoader.loadTestsFromTestCase(synthetic),
    ]
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert "torch" not in sys.modules
sys.exit(not result.wasSuccessful())
