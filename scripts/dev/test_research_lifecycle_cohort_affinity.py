"""Synthetic actual sequence control flow; no native searches or job submission."""

from contextlib import ExitStack, nullcontext
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


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


if __name__ == "__main__":
    unittest.main()
