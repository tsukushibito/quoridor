"""Changed CPU-plan boundaries. Definitions only until integration's actual STOP."""

from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/python"))
from quoridor_runtime import cycle_process as process  # noqa:E402


def lifecycle():
    loader = importlib.util.spec_from_file_location(
        "lc_cpu_plan_tests", Path(__file__).with_name("research-lifecycle.py")
    )
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


class CPUPlanBoundaries(unittest.TestCase):
    def test_runtime_plan_roundtrip_rejects_an_invented_scope_or_count(self):
        record = process.CPUPlan([0, 18], {"run": [0, 12]}).record()
        self.assertEqual(process.CPUPlan.from_record(record).record(), record)
        changed = {**record, "allocation": [0, 12, 14, 18]}
        with self.assertRaisesRegex(ValueError, "differs"):
            process.CPUPlan.from_record(changed)

    def test_unique_roles_library_count_and_physical_smt_refusal(self):
        plan = process.CPUPlan([0], {"run": [0, 12, 14]})
        self.assertEqual(plan.record()["resource_CPUs"], 3)
        self.assertEqual(plan.record()["worker_CPUs"], 2)
        self.assertEqual(plan.record()["library_threads"], 1)
        for cores in ([12, 12], [True], [-1], []):
            with self.subTest(cores=cores), self.assertRaises(ValueError):
                process.CPUPlan([0], {"run": cores})
        with self.assertRaisesRegex(ValueError, "unavailable"):
            plan.check_host({0, 12})
        original = Path.read_text

        def topology(path, *args, **kwargs):
            if str(path).startswith("/sys/devices/system/cpu/"):
                cpu = int(path.parent.parent.name[3:])
                return "0" if path.name == "physical_package_id" else str(cpu // 2)
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", topology):
            plan.check_host({0, 12, 14})
            with self.assertRaisesRegex(ValueError, "physical/SMT"):
                process.CPUPlan([0], {"run": [0, 1]}).check_host({0, 1})

    def test_measurement_plan_runs_actual_typed_team_and_library_predicates(self):
        lc = lifecycle()
        cfg = dict(
            search_threads=2,
            search_cpu_cores=[12, 14],
            management_cpu_core=0,
            native_memory_bytes=256,
        )
        support = dict(
            resources=dict(CPU=3, threads=1, GPU=0, controller_included=True, family_RAM_B=320)
        )
        experiment = dict(phase="compare", argv=["dummy", "measure"], config="config")
        spec = dict(
            kind="run",
            experiment="experiment",
            support="support",
            child_cpu_cores=[0, 12, 14],
            limits=dict(worker_cpu=12, guardian_cpu=0, family_B=320, controller_B=64),
        )
        with (
            patch.object(
                lc,
                "document",
                lambda r: {"experiment": experiment, "config": cfg, "support": support}[r],
            ),
            patch.object(lc, "measurement_config", lambda e: (cfg, None)),
            patch.object(lc, "arena_cohort", lambda s: None),
        ):
            plan = lc.operation_cpu_plan(spec)
            self.assertEqual(plan.commands["run"], (0, 12, 14))
            self.assertEqual(plan.management, (0,))
            self.assertEqual(lc.native_cpu_cores(spec), [0, 12, 14])
            support["resources"]["threads"] = 2
            with self.assertRaisesRegex(lc.Refused, "physical-core family"):
                lc.operation_cpu_plan(spec)
            support["resources"]["threads"] = 1
            cfg["search_cpu_cores"] = [0, 14]
            with self.assertRaisesRegex(lc.Refused, "measurement team"):
                lc.operation_cpu_plan(spec)

    def test_collector_uses_management_not_three_core_test_payload(self):
        lc = lifecycle()
        spec = dict(
            kind="build",
            limits=dict(worker_cpu=12, guardian_cpu=16),
            test_cpu_cores=[12, 14, 16],
            target_handover="target",
        )
        with patch.object(lc, "document", lambda r: dict(test_cpu_cores=[12, 14, 16])):
            plan = lc.operation_cpu_plan(spec)
        self.assertEqual(plan.management, (16,))
        self.assertEqual(plan.commands["run"], (12,))
        self.assertEqual(plan.commands["test"], (12, 14, 16))
        collector = process.CPUPlan(list(plan.management), {"run": list(plan.management)})
        self.assertEqual(collector.all, (16,))
        self.assertNotIn(10, collector.all)

    def test_owner_requires_actual_child_and_config_not_environment_alone(self):
        lc = lifecycle()
        cfg = dict(argv=["bound"], issue="test")
        own = dict(pid=100, start_ticks="10", boot_id="boot")
        parent = dict(pid=99, start_ticks="9", boot_id="boot")
        state = dict(
            child=own,
            phase="running",
            supervisor=parent,
            config_sha256=lc.sha(json.dumps(cfg, sort_keys=True).encode()),
            cpu_plan={"allocation": [0, 12]},
        )

        def document(ref):
            return cfg if ref == "config" else state

        with ExitStack() as stack:
            stack.enter_context(patch.dict(lc.os.environ, {"QUORIDOR_RESEARCH_JOB_DIR": "/actual"}))
            stack.enter_context(
                patch.object(
                    lc,
                    "bound",
                    lambda p: ("config" if p.name == "config.json" else "state", None),
                )
            )
            stack.enter_context(patch.object(lc, "document", document))
            stack.enter_context(patch.object(lc.process, "identity", lambda info: own))
            stack.enter_context(
                patch.object(lc.process, "process_info", lambda pid: {"parent": 99})
            )
            stack.enter_context(patch.object(lc.process, "alive", lambda p: True))
            self.assertEqual(lc.current_cpu_owner(), state["cpu_plan"])
            state["child"] = {**own, "start_ticks": "old"}
            with self.assertRaisesRegex(lc.Refused, "actual running CPU owner"):
                lc.current_cpu_owner()
            state["child"] = own
            state["config_sha256"] = "wrong"
            with self.assertRaises(lc.Refused):
                lc.current_cpu_owner()

    def test_peer_identity_and_thread_scope_are_owned_by_one_job(self):
        # Source functions are exercised with a bounded synthetic /proc view;
        # real two-lane process qualification is a separate required smoke.
        root = dict(pid=10, start_ticks="one", boot_id="boot")
        native = dict(pid=11, start_ticks="two", boot_id="boot")

        class Entry:
            name = "11"

            def __truediv__(self, name):
                return View(name)

        class View:
            def __init__(self, name):
                self.name = name

            def read_bytes(self):
                return b"/image/quoridor-runner\0"

            def iterdir(self):
                return [Entry()]

        original = Path.iterdir

        def entries(p):
            return [Entry()] if str(p) == "/proc" else original(p)

        with (
            patch.object(Path, "iterdir", entries),
            patch.object(process, "members", lambda r, k: [root, native]),
            patch.object(process, "process_info", lambda p: {**native, "state": "R", "parent": 99}),
            patch.object(process.os, "sched_getaffinity", lambda p: {12}),
        ):
            process.compute_peers(root, [0, 12], {"quoridor-runner"})
            with (
                patch.object(process.os, "sched_getaffinity", lambda p: {14}),
                self.assertRaisesRegex(process.CycleStopped, "outside assigned"),
            ):
                process.compute_peers(root, [0, 12], {"quoridor-runner"})
            with (
                patch.object(process, "members", lambda r, k: [root]),
                self.assertRaisesRegex(process.CycleStopped, "external compute peer"),
            ):
                process.compute_peers(root, [0, 12], {"quoridor-runner"})


if __name__ == "__main__":
    unittest.main()
