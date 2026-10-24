"""Synthetic actual sequence control flow; no native searches or job submission."""

from contextlib import ExitStack, nullcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class JobCPUPrimitiveBoundary(unittest.TestCase):
    def test_authenticated_launch_uses_shared_cpu_plan_without_loading_game_lifecycle(self):
        loader = importlib.util.spec_from_file_location(
            "job_cpu_boundary", Path(__file__).with_name("research-job.py")
        )
        job = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(job)
        root = Path(__file__).resolve().parents[2]
        config = {"argv": [sys.executable, "-B", str(root / "scripts/dev/research-lifecycle.py")]}
        owner = dict(pid=123, start_ticks="456", boot_id="synthetic")
        plan = job.process.CPUPlan([18], {"run": [12, 18]}).record()
        for change in (None, "config", "owner", "plan"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                state = {
                    "cpu_launch": {
                        "config_sha256": hashlib.sha256(
                            json.dumps(config, sort_keys=True).encode()
                        ).hexdigest(),
                        "owner": owner,
                        "plan": plan,
                    },
                    "launch": {"owner": owner},
                }
                state = json.loads(json.dumps(state))
                if change == "config":
                    state["cpu_launch"]["config_sha256"] = "0" * 64
                elif change == "owner":
                    state["launch"]["owner"]["pid"] += 1
                elif change == "plan":
                    state["cpu_launch"]["plan"]["resource_CPUs"] += 1
                (Path(tmp) / "state.json").write_text(json.dumps(state))
                with (
                    patch.object(
                        job,
                        "lifecycle_module",
                        side_effect=AssertionError("game lifecycle must not be loaded"),
                    ),
                    patch.dict(job.os.environ, {"QUORIDOR_RESEARCH_JOB_DIR": ""}),
                    patch.object(job.process.CPUPlan, "check_host"),
                    patch.object(job.process.CPUPlan, "apply") as apply,
                ):
                    if change is None:
                        actual, owns_peers = job.configured_cpu_control(Path(tmp), config, root)
                        self.assertEqual(actual.record(), plan)
                        self.assertTrue(owns_peers)
                        apply.assert_called_once_with()
                    else:
                        with self.assertRaises((job.JobError, ValueError)):
                            job.configured_cpu_control(Path(tmp), config, root)
                        apply.assert_not_called()


class CohortControllerAffinity(unittest.TestCase):
    def test_sequence_keeps_declared_management_pool_through_inner_and_finalization(
        self,
    ):
        loader = importlib.util.spec_from_file_location(
            "lc_cohort_affinity", Path(__file__).with_name("research-lifecycle.py")
        )
        lc = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(lc)
        wide = {0, 8, 10, 12, 14, 18}

        for cohort, incoming in ((True, wide), (False, wide), (True, {8, 10, 12, 14})):
            with (
                self.subTest(cohort=cohort, incoming=incoming),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                affinity = set(incoming)
                expected = {0, 18} if cohort else {18}
                observed = []

                def save(path, value):
                    lc.new_json(path, value)
                    return lc.bound(path)[0]

                config = dict(end_at=None, issue="synthetic", thread_id="synthetic")
                config_ref = save(root / "job.json", config)
                origin = dict(config=config_ref)
                settings = dict(
                    kind="sequence",
                    owner=tmp,
                    output=str(root / "execution"),
                    runs=[{}, {}],
                )
                if cohort:
                    settings["arena_cohort"] = {"synthetic": True}
                settings_ref = save(root / "settings.json", settings)

                def check(stage):
                    observed.append(stage)
                    self.assertEqual(affinity, expected, stage)

                def set_affinity(pid, mask):
                    nonlocal affinity
                    affinity = set(mask)

                def prepare(*args):
                    check("prepare")
                    directory = root / (
                        "selected-"
                        + str(len([p for p in root.iterdir() if p.name.startswith("selected-")]))
                    )
                    directory.mkdir()
                    operation = directory / "operation"
                    operation.mkdir()
                    (operation / "INCOMPLETE").touch()
                    return save(
                        directory / "spec.json",
                        dict(
                            cwd=tmp,
                            output=str(operation),
                            TMP=str(directory / "TMP"),
                            limits=dict(log_B=1024),
                        ),
                    )

                def execute(active, child_config, *args, **kwargs):
                    check("inner_execute")
                    result = dict(
                        outcome="succeeded",
                        direct_child_reaped=True,
                        cleanup_complete=True,
                        remaining=[],
                    )
                    save(active / "result.json", result)
                    return result

                def complete(operation, result):
                    check("finalize")
                    value = dict(status="PASS", cleanup_complete=True, remaining=[])
                    save(operation / "manifest.json", value)
                    return value

                def physical(spec):
                    check("physical_entry")
                    # The maintained guard narrows its current controller temporarily.
                    set_affinity(0, {18})
                    return lc.process.CPUPlan([18], {"run": [8, 18]})

                job = SimpleNamespace(
                    authority=lambda *args, **kwargs: check("authority"),
                    validate=lambda value, active: value,
                    write=lambda active, name, value: lc.new_json(active / name, value),
                    lock=lambda *args: nullcontext(),
                    execute=execute,
                )
                resources = SimpleNamespace(check=lambda **kwargs: check("resource"))
                with ExitStack() as stack:
                    for name, value in (
                        ("project_python", lambda: Path(lc.sys.executable)),
                        ("originating_job", lambda *args: origin),
                        ("arena_cohort_spec", lambda *args: {}),
                        (
                            "arena_cohort",
                            lambda *args: (
                                dict(
                                    management_cpu_pool=[0, 18],
                                    global_controller_cpu=18,
                                ),
                                {},
                            ),
                        ),
                        ("ArenaCohortResources", lambda *args: resources),
                        ("arena_cohort_progress", lambda *args: check("progress")),
                        ("physical_and_quiet", physical),
                        (
                            "sequence_cpu_plan",
                            lambda *args: lc.process.CPUPlan(sorted(expected), {"run": [8, 18]}),
                        ),
                        ("current_cpu_owner", lambda: None),
                    ):
                        stack.enter_context(patch.object(lc, name, value))
                    stack.enter_context(
                        patch.object(lc.os, "sched_getaffinity", lambda pid: set(affinity))
                    )
                    stack.enter_context(patch.object(lc.os, "sched_setaffinity", set_affinity))
                    stack.enter_context(
                        patch.object(lc.process.CPUPlan, "check_host", lambda *args: None)
                    )
                    stack.enter_context(
                        patch.object(lc.process, "available_cpus", lambda: set(wide))
                    )
                    stack.enter_context(patch.object(lc.signal, "signal", return_value=None))
                    if cohort and not {0, 18} <= incoming:
                        with self.assertRaisesRegex(lc.Refused, "outside owning launch scope"):
                            lc.sequence(
                                settings_ref,
                                job_module=job,
                                backend=object(),
                                prepare=prepare,
                                complete=complete,
                            )
                        self.assertEqual(observed, [])
                        self.assertEqual(affinity, incoming)
                        continue
                    result = lc.sequence(
                        settings_ref,
                        job_module=job,
                        backend=object(),
                        prepare=prepare,
                        complete=complete,
                    )
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["completed_operations"], 2)
                self.assertTrue(
                    all(r["launch_affinity"] == sorted(expected) for r in result["operations"])
                )
                self.assertEqual(result["launch_affinity_restored"], sorted(expected))
                self.assertEqual(affinity, expected)
                self.assertIn("inner_execute", observed)
                self.assertIn("finalize", observed)
                if cohort:
                    self.assertIn("progress", observed)
                self.assertEqual(
                    json.loads((root / "execution/result.json").read_text())["status"],
                    "PASS",
                )

    def test_progress_retains_identity_with_optional_canonical_and_refuses_ambiguous_lineage(self):
        loader = importlib.util.spec_from_file_location(
            "lc_progress_optional_canonical", Path(__file__).with_name("research-lifecycle.py")
        )
        lc = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(lc)
        returned = dict(
            status="complete",
            exit_code=0,
            direct_child_reaped=True,
            handle_closes_complete=True,
            cleanup_complete=True,
            remaining=[],
            finalization_errors=[],
            signal_mask_restoration="completed",
            final_record_persist="completed",
        )
        for case in ("absent", "recorded", "ambiguous-lineage", "missing-family-id"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                control = root / "control"
                control.mkdir()
                output = root / "sequence"
                operation = output / "run-000" / "operation"
                operation.mkdir(parents=True)
                native = root / "native"
                native.mkdir()

                def save(path, value):
                    lc.new_json(path, value)
                    return lc.bound(path)[0]

                identity = {"family_id": 7}
                if case == "recorded":
                    identity["canonical_family"] = "recorded-native-canonical-identity"
                elif case == "missing-family-id":
                    identity.pop("family_id")
                opening = dict(
                    id="original-request-id",
                    lineage="original-lineage",
                    reference=dict(settings=identity),
                )
                openings = [opening]
                if case == "ambiguous-lineage":
                    openings.append({**opening, "id": "different-request-same-lineage"})
                config = dict(
                    games=2,
                    run_id="synthetic-progress",
                    output=str(native),
                    arena=dict(book=dict(openings=openings)),
                )
                config_ref = save(root / "config.json", config)
                experiment_ref = save(root / "experiment.json", dict(config=config_ref))
                settings_ref = save(
                    root / "settings.json", dict(runs=[dict(experiment=experiment_ref)])
                )
                save(operation / "manifest.json", {})
                publication_ref = save(
                    native / "result.json",
                    dict(
                        outcome_count=2,
                        report=dict(
                            run_id=config["run_id"],
                            planned=2,
                            arena_summary=dict(
                                census=dict(
                                    planned_games=2,
                                    started_games=2,
                                    completed_games=2,
                                    unknown_games=0,
                                    complete_pairs=1,
                                ),
                                pairs=[dict(lineage="original-lineage", family="native-pair-id")],
                            ),
                        ),
                    ),
                )
                member = dict(
                    lane=0,
                    output=str(output),
                    settings_path=settings_ref["path"],
                    job_runtime=str(root / "unentered-outer"),
                )
                cohort = dict(
                    control_root=str(control),
                    members=[member],
                    notify=dict(thread_id="synthetic", issue="synthetic"),
                    global_controller_cpu=18,
                )
                spec = dict(arena_cohort={"synthetic": True}, cwd=tmp)
                with (
                    patch.object(lc, "arena_cohort", return_value=(cohort, member)),
                    patch.object(
                        lc,
                        "arena_cohort_lifetime",
                        return_value=dict(origins={}, clock=lc.time.monotonic() - 1),
                    ),
                    patch.object(lc, "ArenaCohortResources", return_value=object()),
                    patch.object(lc.process, "execute", return_value=returned) as notify,
                ):
                    if case == "ambiguous-lineage":
                        with self.assertRaisesRegex(
                            lc.Refused, "complete pair joins exact family lineage"
                        ):
                            lc.arena_cohort_progress(spec)
                    elif case == "missing-family-id":
                        with self.assertRaisesRegex(KeyError, "family_id"):
                            lc.arena_cohort_progress(spec)
                    else:
                        lc.arena_cohort_progress(spec)
                        notify.assert_called_once()
                if case in ("ambiguous-lineage", "missing-family-id"):
                    notify.assert_not_called()
                    self.assertFalse((control / "first-progress.json").exists())
                    self.assertFalse((control / "first-progress-pairs.json").exists())
                    continue
                pairs = json.loads((control / "first-progress-pairs.json").read_text())
                self.assertEqual(
                    pairs,
                    [
                        dict(
                            lane=0,
                            operation=0,
                            family_id=7,
                            request_id="original-request-id",
                            canonical_family=(
                                "recorded-native-canonical-identity" if case == "recorded" else None
                            ),
                            candidate_colors=[0, 1],
                            native_family="native-pair-id",
                            lineage="original-lineage",
                            publication=publication_ref,
                        )
                    ],
                )
                packet = json.loads((control / "first-progress.json").read_text())
                self.assertEqual(packet["counts"]["planned_games"], 2)
                self.assertEqual(packet["counts"]["completed_games_known"], 2)
                self.assertEqual(packet["counts"]["complete_pairs_known"], 1)
                self.assertEqual(packet["counts"]["scientific_outcome_UNKNOWN_slots"], 0)
                notification = json.loads(
                    (control / "first-progress-notification.json").read_text()
                )
                self.assertEqual(notification["returned"], returned)
                self.assertIsNone(notification["failure"])
                self.assertEqual(notification["secondary"], [])


if __name__ == "__main__":
    unittest.main()
