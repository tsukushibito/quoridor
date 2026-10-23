"""Retain refusal evidence and reap the real child without widening its CPU mask."""

import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared/python"))
from quoridor_runtime import cycle_process as process  # noqa: E402


class CPUScopeRefusalEvidence(unittest.TestCase):
    def test_first_observed_mask_survives_refusal_disk_write_and_actual_reap(self):
        plan = process.CPUPlan([18], {"run": [4]})
        plan.check_host(process.available_cpus())
        original_affinity = os.sched_getaffinity(0)
        actual_getaffinity = os.sched_getaffinity
        observed = []
        try:
            plan.apply()
            with tempfile.TemporaryDirectory(prefix="cpu-scope-refusal-") as directory:
                log = Path(directory) / "child.log"

                def injected_affinity(tid):
                    actual = actual_getaffinity(tid)
                    if tid == os.getpid():
                        return actual
                    self.assertEqual(actual, {4})
                    self.assertEqual(observed, [])
                    observed.append(tid)
                    return {4, 18}

                with patch.object(process.os, "sched_getaffinity", injected_affinity):
                    with self.assertRaisesRegex(
                        process.CycleStopped,
                        "owned child/thread outside assigned command CPU scope",
                    ) as stopped:
                        process.execute(
                            [sys.executable, "-B", "-c", "import signal; signal.pause()"],
                            log,
                            time.monotonic() + 10,
                            cpu_plan=plan,
                        )

                actual = stopped.exception.cycle_cleanup_outcome["record"]
                disk = json.loads(log.with_suffix(".process.json").read_bytes())
                expected = {
                    "member": actual["child"],
                    "tid": actual["child"]["pid"],
                    "observed_cpus": [4, 18],
                    "allowed_cpus": [4],
                }
                self.assertEqual(observed, [expected["tid"]])
                self.assertEqual(actual["cpu_scope_violation"], expected)
                self.assertEqual(disk["cpu_scope_violation"], expected)
                self.assertEqual(actual["status"], "failed")
                self.assertEqual(actual["remaining"], [])
                for field in (
                    "direct_child_reaped",
                    "process_cleanup_complete",
                    "handle_closes_complete",
                    "cleanup_complete",
                ):
                    self.assertIs(actual[field], True)
                self.assertFalse(process.alive(actual["child"]))
        finally:
            os.sched_setaffinity(0, original_affinity)


if __name__ == "__main__":
    unittest.main()
