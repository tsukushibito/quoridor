"""R1-only actual bounded metadata reads. Old fixture methods are never run."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

OWN = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fit_view_fixture", OWN / "test_final_fit_view.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
Fixture, common = fixture.Fixture, fixture.common


class ReadSpy:
    def __init__(self, target, mode):
        self.target, self.mode = target, mode
        self.original = target.read_bytes()
        self.real_open, self.real_read, self.real_fstat, self.real_close = (
            os.open,
            os.read,
            os.fstat,
            os.close,
        )
        self.opens, self.requests, self.descriptors, self.closed = 0, [], set(), []
        self.target_fd, self.changed = None, False

    def replace(self, symlink=False):
        saved = self.target.with_suffix(".saved")
        self.target.rename(saved)
        if symlink:
            self.target.symlink_to(saved)
        else:
            self.target.write_bytes(self.original)

    def open(self, path, flags):
        target = Path(path) == self.target
        if target:
            self.opens += 1
            assert flags & os.O_NOFOLLOW and flags & os.O_NONBLOCK and flags & os.O_CLOEXEC
            if self.mode == "replace-before-open":
                self.replace()
            if self.mode == "symlink-before-open":
                self.replace(symlink=True)
        descriptor = self.real_open(path, flags)
        self.descriptors.add(descriptor)
        if target:
            self.target_fd = descriptor
            if self.mode == "replace-after-open":
                self.replace()
        return descriptor

    def fstat(self, descriptor):
        info = self.real_fstat(descriptor)
        if descriptor == self.target_fd and self.mode == "nonregular-opened" and not self.changed:
            self.changed = True
            return SimpleNamespace(
                **{
                    k: getattr(info, k)
                    for k in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
                },
                st_mode=stat.S_IFIFO | 0o600,
            )
        return info

    def read(self, descriptor, count):
        if descriptor == self.target_fd:
            self.requests.append((self.opens, count))
            if (
                not self.changed
                and self.mode in ("grow-initial", "grow-final")
                and self.opens == (1 if self.mode == "grow-initial" else 2)
            ):
                self.changed = True
                with self.target.open("ab") as stream:
                    stream.write(b" " * 131072)
        result = self.real_read(descriptor, count)
        if descriptor == self.target_fd and self.mode == "replace-during-read" and not self.changed:
            self.changed = True
            self.replace()
        return result

    def close(self, descriptor):
        self.closed.append(descriptor)
        if descriptor == self.target_fd:
            self.target_fd = None
        return self.real_close(descriptor)

    def check_closed(self, case):
        for descriptor in self.descriptors:
            case.assertIn(descriptor, self.closed)
            with case.assertRaises(OSError):
                self.real_fstat(descriptor)

    def patches(self):
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(patch.object(os, "open", side_effect=self.open))
        stack.enter_context(patch.object(os, "read", side_effect=self.read))
        stack.enter_context(patch.object(os, "fstat", side_effect=self.fstat))
        stack.enter_context(patch.object(os, "close", side_effect=self.close))
        stack.enter_context(
            patch.object(Path, "read_bytes", side_effect=AssertionError("unbounded metadata read"))
        )
        return stack


class FinalFitViewReadR1NN0(unittest.TestCase):
    def test_cached_schedule_cannot_bypass_stricter_native_config_role(self):
        with tempfile.TemporaryDirectory(dir=OWN) as directory:
            f = Fixture(Path(directory))
            # One real SHA-bound JSON is valid as both roles; the 4MiB schedule
            # role is visited first. Do not assume roles/paths are disjoint.
            combined = f.scheduled(6)
            combined.update(copy.deepcopy(f.native[0]))
            combined["padding"] = "x" * 1100000
            reference = f.put("schedule-and-native", combined)
            f.cfg["schedule"] = reference
            f.rebind_final()
            f.native_refs[0] = reference
            f.m["stream_intake"]["batches"][0]["config"] = reference
            f.m["mcts_native_configs"] = f.put("native-list", f.native_refs)
            f.m["dataset_sha"] = f.m["mcts_native_configs"]["sha256"]
            spy = ReadSpy(Path(reference["path"]), "observe")
            with spy.patches(), self.assertRaisesRegex(ValueError, "cached.*role bound"):
                common.common_cache_config(f.m)
            self.assertEqual(spy.opens, 1)
            self.assertEqual(sum(n for _, n in spy.requests), len(spy.original))
            self.assertTrue(all(0 < n <= 65536 for _, n in spy.requests))
            spy.check_closed(self)

    def test_initial_and_final_growth_read_only_accepted_capacity_then_refuse(self):
        for mode in ("grow-initial", "grow-final"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=OWN) as directory:
                f = Fixture(Path(directory))
                spy = ReadSpy(Path(f.m["input_binding"]["path"]), mode)
                with spy.patches(), self.assertRaisesRegex(ValueError, "SHA/identity drift"):
                    common.common_cache_config(f.m)
                self.assertTrue(spy.changed)
                self.assertEqual(spy.opens, 1 if mode == "grow-initial" else 2)
                for phase in range(1, spy.opens + 1):
                    self.assertEqual(
                        sum(n for p, n in spy.requests if p == phase), len(spy.original)
                    )
                self.assertTrue(all(0 < n <= len(spy.original) for _, n in spy.requests))
                spy.check_closed(self)

    def test_opened_regular_identity_nofollow_and_path_races_close_every_fd(self):
        modes = (
            "replace-before-open",
            "symlink-before-open",
            "replace-after-open",
            "nonregular-opened",
            "replace-during-read",
        )
        for mode in modes:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(dir=OWN) as directory:
                f = Fixture(Path(directory))
                spy = ReadSpy(Path(f.m["input_binding"]["path"]), mode)
                with spy.patches(), self.assertRaises((ValueError, OSError)):
                    common.common_cache_config(f.m)
                if mode != "replace-during-read":
                    self.assertEqual(spy.requests, [])
                else:
                    self.assertEqual(sum(n for _, n in spy.requests), len(spy.original))
                spy.check_closed(self)


if __name__ == "__main__":
    names = sys.argv[1:] or unittest.defaultTestLoader.getTestCaseNames(FinalFitViewReadR1NN0)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(FinalFitViewReadR1NN0(name) for name in names)
    )
    print(
        json.dumps(
            {
                "new_definitions": result.testsRun,
                "passed": result.wasSuccessful(),
                "old_test_methods_run": 0,
                "real_model_forward_rows": 0,
            }
        )
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
