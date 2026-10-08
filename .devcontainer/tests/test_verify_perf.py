"""NN0 parser/control checks; no perf process, syscall, or container is started."""

import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "verify_perf", Path(__file__).resolve().parents[1] / "verify-perf.py"
)
perf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perf)


class PerfCheckTests(unittest.TestCase):
    def test_numeric_zero_is_a_counter_but_unsupported_and_missing_are_not(self):
        for value, expected in (
            ("0", True),
            ("1.25", True),
            ("<not supported>", False),
            ("<not counted>", False),
            ("nan", False),
        ):
            with self.subTest(value=value):
                result = {"returncode": 0, "stderr": f"{value}\t\tcycles:u\t100\n"}
                self.assertEqual(perf.usable_counter(result, "cycles:u"), expected)
        self.assertFalse(
            perf.usable_counter({"returncode": 0, "stderr": ""}, "cycles:u")
        )

    def test_failed_command_cannot_be_rescued_by_a_counter_or_another_event(self):
        self.assertFalse(
            perf.usable_counter(
                {"returncode": 255, "stderr": "1\t\tcycles:u\n"}, "cycles:u"
            )
        )
        self.assertFalse(
            perf.usable_counter(
                {"returncode": 0, "stderr": "1\t\tcycles:u\n"}, "cpu-clock:u"
            )
        )

    def test_command_preserves_refusal_and_uses_owned_timeout_and_user_locale(self):
        result = subprocess.CompletedProcess(["perf"], 255, "", "permission denied")
        with patch.object(perf.subprocess, "run", return_value=result) as run:
            actual = perf.command(["perf", "--version"])
        self.assertEqual(actual["returncode"], 255)
        self.assertEqual(actual["stderr"], "permission denied")
        self.assertTrue(actual["direct_child_waited"])
        self.assertEqual(run.call_args.kwargs["timeout"], 5)
        self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")

    def test_missing_or_timed_out_command_remains_an_error(self):
        for error in (
            FileNotFoundError("missing"),
            subprocess.TimeoutExpired(["perf"], 5),
        ):
            with self.subTest(error=error):
                with patch.object(perf.subprocess, "run", side_effect=error):
                    actual = perf.command(["perf", "--version"])
                self.assertIn("error", actual)
                self.assertFalse(perf.usable_counter(actual, "cycles:u"))


if __name__ == "__main__":
    unittest.main()
