"""Verify the prepared common environment; imports are explicit, never model execution."""

import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import sysconfig
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def verify(root=None, *, imports=False):
    # ROOT remains the local authored caller; only project metadata belongs to Main.
    common = Path(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            text=True,
            timeout=5,
        ).strip()
    ).parent
    selected = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
    if not selected.is_absolute() or selected != common:
        raise RuntimeError("Canonical Main project metadata binding required")
    if root is not None and Path(root) != selected:
        raise RuntimeError("Foreign project metadata selection refused")
    project = tomllib.loads((selected / "pyproject.toml").read_text())
    layout = json.loads((selected / "research-paths.json").read_text())
    if sys.version_info[:3] != (3, 14, 7) or sysconfig.get_config_var("Py_GIL_DISABLED"):
        raise RuntimeError("Regular Python3.14.7 is required; no system runtime fallback")
    environment = Path(layout["environments"]["project"])
    if not environment.is_absolute() or os.environ["QUORIDOR_PROJECT_ENV"] != str(environment):
        raise RuntimeError("Canonical shared project environment required")
    if Path(sys.prefix).resolve() != environment.resolve() or sys.prefix == sys.base_prefix:
        raise RuntimeError("Current shared project environment is required")
    expected = dict(
        item.split("==", 1) for item in project["tool"]["uv"]["constraint-dependencies"]
    )
    versions, files = {}, {}
    for name, version in expected.items():
        distribution = importlib.metadata.distribution(name)
        if distribution.version != version:
            raise RuntimeError(
                f"Pinned dependency drift: {name} {distribution.version} != {version}"
            )
        location = Path(distribution.locate_file("")).resolve()
        if not location.is_relative_to(environment.resolve()):
            raise RuntimeError(f"Dependency outside the shared environment: {name}")
        versions[name] = version
        files[name] = str(location)
    imported = {}
    if imports:
        os.environ["ORT_DISABLE_TELEMETRY"] = "1"
        os.environ["MPLBACKEND"] = "Agg"
        for name in (
            "websockets",
            "numpy",
            "torch",
            "onnx",
            "onnxruntime",
            "onnxscript",
            "matplotlib",
        ):
            module = importlib.import_module(name)
            location = Path(module.__file__).resolve()
            if not location.is_relative_to(environment.resolve()):
                raise RuntimeError(f"Import outside the shared environment: {name}")
            imported[name] = str(location)
        if sys.modules["torch"].cuda.is_initialized():
            raise RuntimeError("Environment import smoke must not initialise CUDA")
    return {
        "python": platform.python_version(),
        "sys_executable": sys.executable,
        "regular_binary": str(Path(sys.executable).resolve()),
        "environment": str(environment),
        "packages": versions,
        "package_locations": files,
        "explicit_imports": imported,
        "models_fit_Search_games_numerical_qualification": "NOT_RUN",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--imports", action="store_true", help="Explicit no-model import smoke")
    args = parser.parse_args()
    report = verify(imports=args.imports)
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
