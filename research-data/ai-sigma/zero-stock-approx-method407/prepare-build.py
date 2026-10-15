"""Prepare the affected406 software in the existing shared Cargo/build lifecycle."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path("/workspaces/quoridor")
BASE = Path(__file__).resolve().parent
SOURCE = (
    ROOT
    / ".worktree/arena-generalization377/.artifacts/research-team/zero-stock-approx-method407-v1"
)
OUT = BASE / (sys.argv[1] if len(sys.argv) > 1 else "compatible-build-v1")
loader = importlib.util.spec_from_file_location(
    "lc", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
sys.modules["lc"] = lc
loader.loader.exec_module(lc)


def main():
    assert not OUT.exists()
    OUT.mkdir()
    original = (
        ROOT
        / ".artifacts/research-team/integration324/search-cleanup403-v1/compatible-build-v3/intent.json"
    )
    spec = copy.deepcopy(lc.document(lc.artifact_ref(original)))
    composition = lc.document(
        lc.artifact_ref(BASE / "source-composition-v1/result.json")
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    assert composition["all_postimages_match"]
    if commit != composition["commit"]:
        repair = lc.document(lc.artifact_ref(BASE / "fixture-default-repair.json"))
        assert repair["commit"] == commit and not repair["production_changed"]
        assert all(
            lc.artifact_ref(row["path"]) == row for row in composition["subjects"]
        )
    support = dict(
        schema="quoridor.research.phase-support.v1",
        issue="quoridor-4lc.407",
        resources=dict(
            worker_cpu=2,
            guardian_cpu=4,
            native_threads=1,
            GPU=0,
            family_RAM_B=4 * 1024**3,
            controller_included=True,
        ),
        storage_budget=None,
        scope="New407 AI4/runner1/PythonNN0one and affected2; research+diagnostics compile/Clippy, actual optimized measurement image. No prior successful suite replay/new scientific calls; source ready is not scientific/default adoption.",
    )
    lc.new_json(OUT / "resources.json", support)
    spec.update(
        support=lc.artifact_ref(OUT / "resources.json"),
        output=str(OUT / "operation-v1"),
        TMP=str(OUT / "TMP-v1"),
        private=str(
            Path(spec["private"]).with_name("quoridor-runner407-zero-stock-method-v1")
        ),
    )
    spec["env"]["TMPDIR"] = spec["TMP"]
    spec["limits"].update(worker_cpu=2, guardian_cpu=4)
    source = spec["source"]
    source["commit"] = commit
    patch = subprocess.check_output(
        ["git", "diff", "--binary", "--no-ext-diff", "--no-textconv", "HEAD", "--"],
        cwd=ROOT,
    )
    (OUT / "source.patch").write_bytes(patch)
    source["patch"] = lc.artifact_ref(OUT / "source.patch") if patch else None
    source["untracked_inputs"] = []
    for key in ["manifest", "lock"]:
        source[key] = lc.artifact_ref(source[key]["path"])
    for row in source["cargo_configs"]:
        row["file"] = (
            lc.artifact_ref(row["path"]) if Path(row["path"]).exists() else None
        )
    lc.source_check(source)
    lc.new_json(
        OUT / "source-adoption.json",
        dict(
            schema="quoridor.research.source-adoption.v1",
            status="ACCEPTED",
            issue="quoridor-4lc.407",
            scope="Exact stopped407 source and limited review accepted for necessary software; no407 numerical campaign.",
            composition=lc.artifact_ref(BASE / "source-composition-v1/result.json"),
            source=source,
        ),
    )
    spec["source_adoption"] = lc.artifact_ref(OUT / "source-adoption.json")
    handover = lc.document(spec["target_handover"])
    lc.new_json(OUT / "target-handover.json", handover)
    spec["target_handover"] = lc.artifact_ref(OUT / "target-handover.json")
    cargo = spec["tools"]["CARGO"]["file"]["path"]
    common = [
        "--offline",
        "--locked",
        "--manifest-path",
        str(ROOT / "Cargo.toml"),
        "-j1",
        "--message-format=json-render-diagnostics",
    ]
    commands = []
    python_test = OUT / "measurement_config407_tests.py"
    shutil.copy2(SOURCE / "measurement_config407_tests.py", python_test)
    commands.append(
        dict(
            name="measurement-test-compile",
            role="test",
            argv=[
                cargo,
                "test",
                *common,
                "-p",
                "quoridor-runner",
                "--lib",
                "--features",
                "measurement",
                "--no-run",
            ],
        )
    )
    filters = [
        {
            "package": "quoridor-ai",
            "feature": "research-diagnostics",
            "filter": "zero_stock407_",
            "expected": 4,
        },
        {
            "package": "quoridor-runner",
            "feature": "measurement",
            "filter": "measurement407_method_default_refusal_and_resolved_output",
            "expected": 1,
        },
        {
            "package": "quoridor-ai",
            "feature": "research-diagnostics",
            "filter": "zero_stock406_float_cache_wall_key_fallback_and_parent_immutability",
            "expected": 1,
        },
        {
            "package": "quoridor-runner",
            "feature": "measurement",
            "filter": "measurement406_optional_threshold_refusals_and_actual_result_metadata",
            "expected": 1,
        },
    ]
    for row in filters:
        commands.append(
            dict(
                name=row["filter"].replace("_", "-").rstrip("-"),
                role="test",
                argv=[
                    cargo,
                    "test",
                    *common,
                    "-p",
                    row["package"],
                    "--lib",
                    "--features",
                    row["feature"],
                    row["filter"],
                    "--",
                    "--test-threads=1",
                    "--nocapture",
                ],
            )
        )
    for package, feature in [
        ("quoridor-ai", "research"),
        ("quoridor-ai", "research-diagnostics"),
        ("quoridor-runner", "measurement"),
    ]:
        commands.append(
            dict(
                name=feature + "-affected-lint",
                role="lint",
                argv=[
                    cargo,
                    "clippy",
                    *common,
                    "-p",
                    package,
                    "--all-targets",
                    "--features",
                    feature,
                    "--no-deps",
                    "--",
                    "-Dwarnings",
                ],
            )
        )
    commands.append(
        dict(
            name="measurement-build",
            role="build",
            argv=[
                cargo,
                "build",
                *common,
                "--release",
                "-p",
                "quoridor-runner",
                "--bin",
                "quoridor-runner",
                "--features",
                "measurement",
            ],
        )
    )
    spec["commands"] = commands
    for key in ["intent_sha256", "admission"]:
        spec.pop(key, None)
    spec["intent_sha256"] = lc.canonical_sha(spec)
    lc.new_json(
        OUT / "admission.json",
        dict(
            schema="quoridor.research.phase-admission.v1",
            owner=spec["owner"],
            limits=spec["limits"],
            spec_sha256=spec["intent_sha256"],
            support_sha256=spec["support"]["sha256"],
            ready=True,
        ),
    )
    spec["admission"] = lc.artifact_ref(OUT / "admission.json")
    lc.new_json(OUT / "intent.json", spec)
    intent = lc.artifact_ref(OUT / "intent.json")
    with lc.lease():
        lc.physical_and_quiet(spec)
        marker = Path(spec["target"]) / ".research-owner.json"
        before = json.loads(marker.read_text())
        lc.new_json(OUT / "target-owner-before.json", before)
        updated = dict(
            writer=spec["writer"],
            target=spec["target"],
            support_sha256=spec["support"]["sha256"],
        )
        marker.write_text(json.dumps(updated, indent=2) + "\n")
        lc.new_json(
            OUT / "target-owner-transfer.json",
            dict(
                before=before,
                after=updated,
                at=lc.stamp(),
                owned_remaining=[],
                lease_released_at_return=True,
            ),
        )
        lc.build_check(spec)
    job = lc.document(
        lc.artifact_ref(
            ROOT
            / ".artifacts/research-team/integration324/search-cleanup403-v1/compatible-build-v3/job/config.json"
        )
    )
    job.update(
        issue="quoridor-4lc.407",
        argv=[
            str(lc.project_python()),
            "-B",
            str(ROOT / "scripts/dev/research-lifecycle.py"),
            "build",
            "--intent",
            intent["path"],
            "--sha256",
            intent["sha256"],
        ],
        resource_contract=str(OUT / "resources.json"),
    )
    lc.new_json(OUT / "job.json", job)
    lc.new_json(
        OUT / "prepared.json",
        dict(
            intent=intent,
            commands=len(commands),
            test_filters=filters,
            source=source,
            no_job_launched=True,
            storage_budget=None,
        ),
    )
    print(json.dumps(dict(intent=intent, job=str(OUT / "job.json"))))


if __name__ == "__main__":
    main()
