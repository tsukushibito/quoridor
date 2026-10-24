"""Preserve the existing memory guard's observation in its normal failure receipt."""

import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from quoridor_runtime.cycle_process import CycleResources, CycleStopped, execute


class MemoryObservationNotes(unittest.TestCase):
    def test_memory_refusal_keeps_bounded_notes_in_disk_and_actual_exception_record(self):
        class TinyThreshold(CycleResources):
            failure = None
            refusal_count = 0

            def check(self, owned=(), **kwargs):
                if owned:
                    # Test-only threshold, after ownership exists. No allocation or extra RSS query.
                    self.memory_limit = 1
                try:
                    return super().check(owned, **kwargs)
                except CycleStopped as error:
                    if str(error) == "cycle memory_limit":
                        self.refusal_count += 1
                        self.failure = error
                        error.add_note("x" * 40000)
                        for index in range(9):
                            error.add_note(f"synthetic omitted note {index}")
                    raise

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            budget = TinyThreshold(
                dict(max_memory_bytes=2 * 1024**3, host_ram_reserve=0),
                root,
                time.monotonic() + 10,
            )
            with self.assertRaises(CycleStopped) as caught:
                execute(
                    [sys.executable, "-B", "-c", "import time; time.sleep(30)"],
                    root / "tiny.log",
                    budget.deadline,
                    resources=budget,
                )
            self.assertIs(caught.exception, budget.failure)
            self.assertEqual(budget.refusal_count, 1)
            self.assertEqual(str(caught.exception), "cycle memory_limit")
            outcome = caught.exception.cycle_cleanup_outcome
            self.assertFalse(outcome["normal_return"])
            actual = outcome["record"]
            disk = json.loads((root / "tiny.process.json").read_text())
            self.assertEqual(actual["primary_error"], disk["primary_error"])
            fact = actual["primary_error"]
            self.assertEqual(fact["type"], "CycleStopped")
            self.assertEqual(fact["message"], "cycle memory_limit")
            self.assertTrue(fact["notes_truncated"])
            self.assertGreater(fact["notes_omitted"], 0)
            self.assertEqual(fact["notes_unknown"], 0)
            self.assertLessEqual(len(fact["notes"]), 8)
            self.assertEqual(fact["notes_utf8_bytes"], sum(len(n.encode()) for n in fact["notes"]))
            self.assertLessEqual(fact["notes_utf8_bytes"], 32768)
            prefix = "actual memory-limit observation: "
            self.assertTrue(fact["notes"][0].startswith(prefix))
            observation = json.loads(fact["notes"][0][len(prefix) :])
            self.assertEqual(observation["output"], str(root))
            self.assertEqual(observation["limit_B"], 1)
            self.assertGreater(observation["rss_B"], observation["limit_B"])
            self.assertGreater(observation["member_count"], 0)
            self.assertTrue(observation["members"])
            self.assertTrue(actual["direct_child_reaped"])
            self.assertTrue(actual["process_cleanup_complete"])
            self.assertTrue(actual["handle_closes_complete"])
            self.assertEqual(actual["remaining"], [])
            self.assertTrue(disk["direct_child_reaped"])
            self.assertEqual(disk["remaining"], [])
            self.assertEqual(actual["signal_mask_restoration"], "completed")
            self.assertEqual(actual["final_record_persist"], "completed")


if __name__ == "__main__":
    unittest.main()
