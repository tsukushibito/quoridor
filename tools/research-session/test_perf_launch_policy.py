"""NN0 child launch policy checks; no perf, model or native research execution."""

import ctypes
import errno
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[2]
MAIN = Path(os.environ["RESEARCH_TEST_ROOT"])
cycle_loader = importlib.util.spec_from_file_location(
    "quoridor_training.perf_policy_subject",
    HERE / "python/quoridor_training/cycle_process.py",
)
cycle = importlib.util.module_from_spec(cycle_loader)
sys.modules[cycle_loader.name] = cycle
cycle_loader.loader.exec_module(cycle)
loader = importlib.util.spec_from_file_location(
    "perf_policy_lifecycle_subject", HERE / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(loader)
sys.modules[loader.name] = lc
loader.loader.exec_module(lc)

STATUS = """
import json,os,pathlib,time
lines=pathlib.Path('/proc/self/status').read_text().splitlines()
print(json.dumps({'nnp':int(next(s.split(':')[1] for s in lines if s.startswith('NoNewPrivs:'))),
                  'pid':os.getpid(),'parent':os.getppid(),'session':os.getsid(0),'group':os.getpgrp()}),flush=True)
time.sleep(.05)
"""


def parent_nnp():
    return int(
        next(
            s.split(":")[1]
            for s in Path("/proc/self/status").read_text().splitlines()
            if s.startswith("NoNewPrivs:")
        )
    )


class PerfLaunchPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def execute(self, name, *, no_new_privs=False, script=STATUS):
        path = self.root / (name + ".log")
        record = cycle.execute(
            [sys.executable, "-B", "-c", script],
            path,
            time.monotonic() + 5,
            no_new_privs=no_new_privs,
        )
        return record, json.loads(path.read_text().splitlines()[0])

    def assert_settled(self, record):
        self.assertTrue(record["direct_child_reaped"])
        self.assertTrue(record["cleanup_complete"])
        self.assertEqual(record["remaining"], [])
        self.assertFalse(cycle.alive(record["child"]))

    def test_selected_policy_survives_exec_ordinary_launch_and_session(self):
        original = parent_nnp()
        selected, observation = self.execute("selected", no_new_privs=True)
        self.assertEqual(observation["nnp"], 1)
        self.assertEqual(observation["parent"], os.getpid())
        self.assertEqual(observation["pid"], observation["session"])
        self.assertEqual(observation["pid"], observation["group"])
        self.assertEqual(selected["child"]["pid"], observation["pid"])
        self.assertEqual(
            selected["launch_policy"],
            {"no_new_privs_requested": True, "verified_before_exec": 1},
        )
        self.assert_settled(selected)
        ordinary, observation = self.execute("ordinary")
        self.assertEqual(observation["nnp"], original)
        self.assertEqual(
            ordinary["launch_policy"],
            {"no_new_privs_requested": False, "verified_before_exec": None},
        )
        self.assert_settled(ordinary)
        self.assertEqual(parent_nnp(), original)

    def test_failed_set_or_check_refuses_command_and_initializes_libc_in_parent(self):
        for failing_option in (38, 39):
            sentinel = self.root / f"executed-{failing_option}"
            loads = []

            class FailedPrctl:
                def __call__(self, option, *_arguments):
                    if option == failing_option:
                        ctypes.set_errno(errno.EPERM)
                        return -1
                    return 0

            def load(*_arguments, **_keywords):
                loads.append(os.getpid())
                return SimpleNamespace(prctl=FailedPrctl())

            log = self.root / f"failed-{failing_option}.log"
            with patch.object(cycle.ctypes, "CDLL", side_effect=load):
                with self.assertRaises(Exception):
                    cycle.execute(
                        [
                            sys.executable,
                            "-B",
                            "-c",
                            f"from pathlib import Path;Path({str(sentinel)!r}).touch()",
                        ],
                        log,
                        time.monotonic() + 5,
                        no_new_privs=True,
                    )
            self.assertEqual(loads, [os.getpid()])
            self.assertFalse(sentinel.exists())
            persisted = json.loads(log.with_suffix(".process.json").read_text())
            self.assertEqual(persisted["status"], "failed")
            self.assertEqual(
                persisted["launch_policy"],
                {"no_new_privs_requested": True, "verified_before_exec": None},
            )
            self.assertIsNone(persisted["child"])
            self.assertTrue(persisted["direct_child_reaped"])
            self.assertTrue(persisted["cleanup_complete"])
            self.assertNotIn("remaining", persisted)

    def test_selected_policy_cancel_directwait_drain_and_cleanup(self):
        script = STATUS.replace(
            "time.sleep(.05)",
            "import signal;os.kill(os.getppid(),signal.SIGTERM);time.sleep(30)",
        )
        log = self.root / "cancel.log"
        with cycle.cancellation_signals():
            with self.assertRaisesRegex(cycle.CycleStopped, "cycle signal: SIGTERM"):
                cycle.execute(
                    [sys.executable, "-B", "-c", script],
                    log,
                    time.monotonic() + 5,
                    no_new_privs=True,
                )
        persisted = json.loads(log.with_suffix(".process.json").read_text())
        observation = json.loads(log.read_text().splitlines()[0])
        self.assertEqual(observation["nnp"], 1)
        self.assertEqual(observation["pid"], observation["session"])
        self.assertEqual(persisted["status"], "failed")
        self.assertEqual(persisted["launch_policy"]["verified_before_exec"], 1)
        self.assert_settled(persisted)
        # On-disk pending/attempted finalizer facts are retained, not relabelled returned facts.
        self.assertEqual(persisted["signal_mask_restoration"], "pending")
        self.assertEqual(persisted["final_record_persist"], "attempted")

    def test_owning_command_selects_policy_only_for_configured_run(self):
        argv = [sys.executable, "-B", "-c", STATUS]
        resources = cycle.CycleResources(
            {
                "host_ram_reserve": 4294967296,
                "max_memory_bytes": 536870912,
                "max_output_bytes": None,
            },
            self.root,
            None,
        )
        spec = {
            "kind": "run",
            "cwd": str(MAIN),
            "env": dict(os.environ),
            "limits": {"worker_cpu": min(os.sched_getaffinity(0)), "log_B": 65536},
            "perf": {"tool": {"path": sys.executable}},
            "argv": argv,
        }
        # Owning command dispatch unit: synthetic Python child, not a perf/Run certificate.
        row = {"name": "dispatch", "role": "run", "argv": argv}
        returned, full = lc.command(
            spec, row, self.root, resources, executor=cycle.execute
        )
        self.assertEqual(returned["launch_policy"]["verified_before_exec"], 1)
        self.assertEqual(json.loads(full.read_text().splitlines()[0])["nnp"], 1)
        self.assert_settled(returned)
        row["name"] = "wrong-dispatch"
        row["argv"] = [
            sys.executable,
            "-B",
            "-c",
            "raise Exception('must not execute')",
        ]
        with self.assertRaisesRegex(lc.Refused, "actual configured profiler launch"):
            lc.command(spec, row, self.root, resources, executor=cycle.execute)
        self.assertFalse((self.root / "wrong-dispatch.process.json").exists())
