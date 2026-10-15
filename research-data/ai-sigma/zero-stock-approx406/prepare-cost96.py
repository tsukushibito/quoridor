"""Bind the authorized finite approximation comparison to one genuine image."""

import copy
import importlib.util
from pathlib import Path
import sys

ROOT = Path("/workspaces/quoridor")
BASE = Path(__file__).resolve().parent
OLD = (
    ROOT
    / ".artifacts/research-team/integration324/shared-signed-ordering402-v1/cost96-v1"
)
OUT = BASE / "cost96-v1"
OWNER = ROOT / ".worktree/assets/perf/zero-stock-approx406-cost96-v1"
loader = importlib.util.spec_from_file_location(
    "lc", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
sys.modules["lc"] = lc
loader.loader.exec_module(lc)


def main():
    assert len(sys.argv) == 2, "actual accepted Build manifest is required"
    build_ref = lc.artifact_ref(sys.argv[1])
    build = lc.accepted_build(build_ref)
    old = lc.document(lc.artifact_ref(OLD / "settings.json"))
    assert not OUT.exists() and not OWNER.exists()
    OUT.mkdir()
    OWNER.mkdir()
    inputs = lc.artifact_ref(BASE / "prefix-inputs-v1/four-prefixes.json")
    correspondence = lc.document(
        lc.artifact_ref(BASE / "prefix-inputs-v1/correspondence.json")
    )
    assert [r["root_walls"] for r in correspondence["roots"]] == [6, 4, 2, 0]
    roots = [
        dict(
            input=0,
            pointer=f"/{i}",
            field="prefix",
            prefix_len=None,
            check_history=False,
            label=f"root-walls-{walls}",
        )
        for i, walls in enumerate([6, 4, 2, 0])
    ]
    request = [
        dict(
            id=f"r{i}-{temperature}",
            session=f"root-{i}",
            root=i,
            depth=8,
            node_cap=4000000,
            time_limit_ms=None,
            diagnostic=False,
            warmup=False,
            observe_completed_depths=False,
        )
        for i in range(4)
        for temperature in ["cold", "warm"]
    ]
    lc.new_json(OUT / "requests.json", request)
    schedule = lc.artifact_ref(OUT / "requests.json")
    support = dict(
        schema="quoridor.research.phase-support.v1",
        issue="quoridor-4lc.406",
        resources=dict(
            worker_cpu=2,
            guardian_cpu=4,
            native_threads=1,
            GPU=0,
            family_RAM_B=4 * 1024**3,
            controller_included=True,
        ),
        storage_budget=None,
        decimal_global_cap_B=50000000000,
        scope="One same-image speed-only null/4/0/0/4/null comparison, NNUE and fixedD strata,4roots cold/warm;96calls48sessions384Mcap. No games/default adoption/sweep/refill/learning.",
        global_actual="UNKNOWN",
    )
    lc.new_json(OUT / "resources.json", support)
    support_ref = lc.artifact_ref(OUT / "resources.json")
    settings = dict(
        schema="quoridor.research.sequence.v1",
        kind="sequence",
        cwd=str(ROOT),
        owner=str(OWNER),
        output=str(OWNER / "execution-v1"),
        arena=None,
        arena_block=1,
        serial_order=["arena", "measure"],
        measurements=[],
    )
    rows = []
    for evaluator, template_index in [("nnue", 0), ("distance", 8)]:
        template = old["measurements"][template_index]
        original_experiment = lc.document(template["experiment"])
        original_config = lc.document(original_experiment["config"])
        for pass_index, threshold in enumerate([None, 4, 0, 0, 4, None]):
            index = len(settings["measurements"])
            mode = "none" if threshold is None else f"min-root-{threshold}"
            config = copy.deepcopy(original_config)
            config.update(
                roots=roots,
                profile="control",
                tt_entries=1048576,
                use_tt=True,
                use_pvs=True,
                lmr=False,
                zero_stock_approx_min_root_walls=threshold,
            )
            config_path = OUT / f"{evaluator}-{mode}-pass{pass_index}.json"
            lc.new_json(config_path, config)
            e = copy.deepcopy(original_experiment)
            e.update(
                build_manifest=build_ref,
                config=lc.artifact_ref(config_path),
                inputs=[inputs],
                schedule=schedule,
                planned_slots=8,
                batch=index,
            )
            e["argv"][0] = build["artifact"]["path"]
            epath = OUT / f"experiment-{index:03}.json"
            lc.new_json(epath, e)
            eref = lc.artifact_ref(epath)
            op = copy.deepcopy(template)
            run_dir = OWNER / f"template-{index:03}"
            op.update(
                owner=str(OWNER),
                output=str(run_dir / "operation"),
                data_root=str(run_dir / "data"),
                owned_outputs=[str(run_dir), str(run_dir / "TMP")],
                TMP=str(run_dir / "TMP"),
                artifact=build["artifact"],
                experiment=eref,
                support=support_ref,
                caller_sources=[
                    lc.artifact_ref(r["path"]) for r in template["caller_sources"]
                ],
            )
            op["env"]["TMPDIR"] = op["TMP"]
            op["data"] = [
                dict(
                    name=name,
                    path=str(run_dir / "data" / filename),
                    limit_B=3 * 1024**2,
                )
                for name, filename in [
                    ("settings", "settings.json"),
                    ("measurements", "measurements.jsonl"),
                    ("result", "result.json"),
                ]
            ]
            op["argv"] = [
                a.replace("@EXPERIMENT@", eref["path"]).replace(
                    "@EXPERIMENT_SHA256@", eref["sha256"]
                )
                for a in e["argv"]
            ]
            op["limits"].update(
                worker_cpu=2,
                guardian_cpu=4,
                family_B=4 * 1024**3,
                controller_B=64 * 1024**2,
                host_reserve_B=4 * 1024**3,
                owned_B=None,
                free_B=None,
            )
            lc.measurement_config(e)
            settings["measurements"].append(op)
            rows.append(
                dict(
                    operation=index,
                    evaluator=evaluator,
                    pass_index=pass_index,
                    zero_stock_approx_min_root_walls=threshold,
                    config=e["config"],
                    schedule=schedule,
                    inputs=[inputs],
                    models=e["models"],
                    namespace_base=config["namespace"],
                )
            )
    assert len(settings["measurements"]) == 12 and len(request) * 12 == 96
    assert sum(r["node_cap"] for r in request) * 12 == 384000000
    assert list(lc.operation_order(settings)) == [("measure", i) for i in range(12)]
    lc.new_json(OUT / "settings.json", settings)
    settings_ref = lc.artifact_ref(OUT / "settings.json")
    job = lc.document(lc.artifact_ref(OLD / "job/config.json"))
    job.update(
        issue="quoridor-4lc.406",
        goal_issue="quoridor-4lc",
        thread_id="01a1376a-bfd3-75d2-bd64-61e9416b3b13",
        argv=[
            str(lc.project_python()),
            "-B",
            str(ROOT / "scripts/dev/research-lifecycle.py"),
            "sequence",
            "--intent",
            settings_ref["path"],
            "--sha256",
            settings_ref["sha256"],
        ],
        resource_contract=str(OUT / "resources.json"),
    )
    lc.new_json(OUT / "job.json", job)
    lc.new_json(
        OUT / "prepared.json",
        dict(
            status="PREPARED_UNLAUNCHED",
            at=lc.stamp(),
            settings=settings_ref,
            build=build_ref,
            artifact=build["artifact"],
            conditions=rows,
            common=dict(
                profile="control",
                lmr=False,
                use_tt=True,
                use_pvs=True,
                tt_entries=1048576,
                depth=8,
                node_cap=4000000,
                time_limit_ms=None,
                diagnostic=False,
                observe_completed_depths=False,
            ),
            calls=96,
            sessions=48,
            node_cap=384000000,
            core_full_history_replay="normal native input admission at actual entry; not inferred from preparation",
            active_approximation="resolved separately at each Search call; positive-depth reachability guard applies",
        ),
    )


if __name__ == "__main__":
    main()
