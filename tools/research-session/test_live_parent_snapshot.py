"""One new deterministic replacement boundary; no engines or archived data."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
SOURCE = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


lc = module("live_snapshot_lc", SOURCE / "scripts/dev/research-lifecycle.py")
fixture = module("live_snapshot_fixture", ROOT / "tools/research-session/test_cohort_control.py")
fixture.lc = lc


class LiveParentSnapshotTests(fixture.MetadataFixture, unittest.TestCase):
    def test_atomic_replacement_is_coherent_and_next_bad_snapshot_fails_closed(self):
        self.setup_metadata()
        binding = lc.cohort_parent_binding(self.cohort_ref)
        actual_bound = lc.bound
        reads = []
        runtime = Path(self.parent["runtime"])

        def replace_after_read(path, *args, **kwargs):
            value = actual_bound(path, *args, **kwargs)
            if Path(path) == self.state_path:
                before = json.loads(value[1])
                reads.append(before)
                refreshed = dict(
                    before,
                    updated_at=f"atomic-refresh-{len(reads)}",
                    authority_valid_until_monotonic=time.monotonic() + 90,
                )
                fixture.j.write(runtime, "state.json", refreshed)
            return value

        with patch.object(lc, "bound", side_effect=replace_after_read):
            for _ in range(2):
                start = len(reads)
                self.assertIs(lc.cohort_parent_check(binding), binding)
                self.assertEqual(len(reads) - start, 1)
            self.assertNotEqual(reads[0].get("updated_at"), reads[1]["updated_at"])
            self.assertEqual(reads[0]["job_id"], reads[1]["job_id"])

        def put(value):
            fixture.j.write(runtime, "state.json", value)

        put(dict(self.state, job_id="wrong-job"))
        with self.assertRaisesRegex(lc.Refused, "running parent job changed"):
            lc.cohort_parent_check(binding)
        put(self.state)
        malformed = runtime / "malformed.tmp"
        malformed.write_text("{")
        malformed.replace(self.state_path)
        with self.assertRaises(json.JSONDecodeError):
            lc.cohort_parent_check(binding)
        put(self.state)
        self.state_path.unlink()
        with self.assertRaises(OSError):
            lc.cohort_parent_check(binding)
        put(self.state)
        with patch.object(lc, "bound", side_effect=PermissionError("synthetic unreadable state")):
            with self.assertRaises(PermissionError):
                lc.cohort_parent_check(binding)
        fixture.j.write(runtime, "cancel.json", dict(signal=15))
        with self.assertRaisesRegex(lc.Refused, "parent cancelled"):
            lc.cohort_parent_check(binding)
        (runtime / "cancel.json").unlink()
        old = self.processes.pop(101)
        try:
            with self.assertRaisesRegex(lc.Refused, "exact identity lost"):
                lc.cohort_parent_check(binding)
        finally:
            self.processes[101] = old
        put(dict(self.state, authority_valid_until_monotonic=time.monotonic() - 1))
        with self.assertRaisesRegex(lc.Refused, "deadline lost"):
            lc.cohort_parent_check(binding)
        print(
            json.dumps(
                dict(
                    healthy_atomic_replacements=2,
                    bounded_state_reads_per_watch=1,
                    fail_closed=[
                        "wrong-job",
                        "malformed",
                        "missing",
                        "unreadable",
                        "cancel",
                        "identity-loss",
                        "stale-deadline",
                    ],
                    archived_game_or_native_or_DB_calls=0,
                )
            ),
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
