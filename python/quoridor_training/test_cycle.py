"""NN0 cycle ownership and resource contracts using synthetic short children."""

import json
import io
from types import SimpleNamespace
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from . import cycle_process as processes
from .cycle import cycle
from . import cycle as cycle_module


class CycleProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.term = patch.object(processes, "TERM_SECONDS", 0.15)
        self.term.start()

    def tearDown(self):
        self.term.stop()
        self.temporary.cleanup()

    def run_child(self, script, resources=None, timeout=2):
        return processes.execute(
            [sys.executable, "-B", "-c", script],
            self.root / "child.log",
            time.monotonic() + timeout,
            resources=resources,
        )

    def record(self):
        return json.loads((self.root / "child.process.json").read_text())

    def policy(self, **kwargs):
        return processes.CycleResources(
            {"host_ram_reserve": 0, **kwargs}, self.root, time.monotonic() + 3
        )

    def assert_clean(self):
        record = self.record()
        self.assertTrue(record["cleanup_complete"])
        self.assertEqual(record["remaining"], [])
        self.assertFalse(processes.alive(record["child"]))

    def test_cleanup_discovery_and_signal_faults_wait_and_close_independently(self):
        for fault in ("members", "signal_members"):
            with self.subTest(fault=fault):
                log = self.root / (fault + ".log")
                with patch.object(processes, fault, side_effect=OSError("cleanup fixture")):
                    with self.assertRaises(BaseExceptionGroup) as error:
                        processes.execute(
                            [sys.executable, "-B", "-c", "import time; time.sleep(10)"],
                            log,
                            time.monotonic() + 0.1,
                        )
                record = json.loads(log.with_suffix(".process.json").read_text())
                self.assertTrue(record["direct_child_reaped"])
                self.assertFalse(record["cleanup_complete"])
                self.assertEqual(record["remaining"], [])
                self.assertEqual(
                    record["handle_closes_attempted"],
                    ["selector_close", "pipe_close", "pidfd_close", "log_close"],
                )
                self.assertFalse(processes.alive(record["child"]))
                self.assertTrue(error.exception.exceptions)

    def test_log_and_receipt_errors_retain_primary_and_all_close_attempts(self):
        real_open = Path.open

        class BrokenLog:
            def __init__(self, stream):
                self.stream = stream

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def write(self, value):
                raise OSError("log write fixture")

        def open_log(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            return BrokenLog(stream) if args and args[0] == "xb" else stream

        log = self.root / "broken-log.log"
        with patch.object(Path, "open", open_log):
            with self.assertRaises(BaseExceptionGroup):
                processes.execute(
                    [sys.executable, "-B", "-c", "import time; time.sleep(10)"],
                    log,
                    time.monotonic() + 0.1,
                )
        record = json.loads(log.with_suffix(".process.json").read_text())
        self.assertTrue(record["direct_child_reaped"])
        self.assertIn("log write fixture", record["primary_error"]["message"])
        self.assertIn("log_close", record["handle_closes_attempted"])
        calls = []
        real_save = processes.save_record

        def broken_receipt(path, record):
            calls.append(dict(record))
            if record.get("final_record_persist") == "attempted":
                raise OSError("receipt fixture")
            return real_save(path, record)

        with patch.object(processes, "save_record", side_effect=broken_receipt):
            with self.assertRaises(BaseExceptionGroup) as error:
                processes.execute(
                    [sys.executable, "-B", "-c", "raise SystemExit(7)"],
                    self.root / "broken-receipt.log",
                    time.monotonic() + 2,
                )
        fallback = json.loads(error.exception.__notes__[-1].split(": ", 1)[1])
        self.assertTrue(fallback["direct_child_reaped"])
        self.assertEqual(fallback["final_record_persist"], "failed_or_partial_UNKNOWN")
        self.assertEqual(fallback["exit_code"], 7)
        self.assertIn("pipe_close", fallback["handle_closes_attempted"])
        self.assertEqual(calls[-1]["final_record_persist"], "attempted")

    def test_dual_signal_failures_preserve_both_receipt_facts_and_direct_wait(self):
        child = SimpleNamespace(
            pid=999999999,
            stdout=io.BytesIO(),
            returncode=None,
            poll=Mock(return_value=None),
            send_signal=Mock(side_effect=OSError("fallback Popen failure")),
        )

        def waited(*args, **kwargs):
            child.returncode = 7
            return 7

        child.wait = Mock(side_effect=waited)
        info = {"pid": child.pid, "start_ticks": "1", "boot_id": "synthetic"}
        fd = processes.os.open("/dev/null", processes.os.O_RDONLY)
        original = processes.save_record

        def save(path, record):
            if record["status"] == "running":
                raise ValueError("primary record failure")
            return original(path, record)

        with (
            patch.object(processes.subprocess, "Popen", return_value=child),
            patch.object(processes.os, "pidfd_open", return_value=fd),
            patch.object(processes, "process_info", return_value=info),
            patch.object(processes, "members", return_value=[]),
            patch.object(
                processes.signal, "pidfd_send_signal", side_effect=OSError("original pidfd failure")
            ),
            patch.object(processes, "TERM_SECONDS", 0),
            patch.object(processes, "save_record", side_effect=save),
        ):
            with self.assertRaises(BaseExceptionGroup):
                processes.execute(["synthetic"], self.root / "dual.log", None)
        child.wait.assert_called_once_with(timeout=3)
        self.assertTrue(child.stdout.closed)
        saved = json.loads((self.root / "dual.process.json").read_text())
        self.assertTrue(saved["direct_child_reaped"])
        self.assertFalse(saved["cleanup_complete"])
        self.assertEqual(saved["primary_error"]["message"], "primary record failure")
        facts = {fact["stage"]: fact["message"] for fact in saved["finalization_errors"]}
        for stage in ("direct_term", "direct_kill"):
            self.assertEqual(facts[stage + "_pidfd"], "original pidfd failure")
            self.assertEqual(facts[stage + "_popen"], "fallback Popen failure")

    def test_pidfd_signal_failure_still_uses_owned_direct_fallback_and_waits(self):
        with patch.object(
            processes.signal, "pidfd_send_signal", side_effect=OSError("pidfd fixture")
        ):
            with self.assertRaises(BaseExceptionGroup):
                self.run_child("import time; time.sleep(10)", timeout=0.1)
        record = self.record()
        self.assertTrue(record["direct_child_reaped"])
        self.assertFalse(record["cleanup_complete"])
        self.assertEqual(record["remaining"], [])

    def test_nullable_finite_default_deadline_and_pre_stage_failures_publish_state(self):
        class Resources:
            def __init__(self, config, output, deadline):
                horizons.append((deadline, time.monotonic()))
                self.deadline = deadline

            def check(self):
                if self.deadline is not None and time.monotonic() >= self.deadline:
                    raise processes.CycleStopped("cycle deadline")

        for name, supplied, expected in (
            ("null", {"wall_seconds": None}, None),
            ("absent", {}, 300),
            ("finite", {"wall_seconds": 4}, 4),
            ("unix", {"wall_seconds": None, "deadline_unix_ms": 1}, "expired"),
        ):
            horizons, launches = [], []
            output = self.root / name
            config = self.root / (name + ".json")
            config.write_text(
                json.dumps({"output": str(output), "cycle": {"python": "unused"}, **supplied})
            )

            def fake_execute(*args):
                launches.append(args)
                raise RuntimeError("mock stage failure")

            with (
                patch.object(cycle_module, "CycleResources", Resources),
                patch.object(cycle_module, "execute", side_effect=fake_execute),
            ):
                with self.assertRaisesRegex(RuntimeError, "deadline|mock stage"):
                    cycle(config, "unused-runner")
            if expected is None:
                self.assertIsNone(horizons[0][0])
            elif expected == "expired":
                self.assertEqual(launches, [])
            else:
                self.assertAlmostEqual(horizons[0][0] - horizons[0][1], expected, delta=0.1)
            state = json.loads((output / "cycle-state.json").read_text())
            self.assertEqual(state["status"], "failed")
            self.assertFalse(state["adopted"])
        config = self.root / "setup.json"
        config.write_text(
            json.dumps({"output": str(self.root / "setup"), "cycle": {"wrong": "python"}})
        )
        with self.assertRaises(KeyError):
            cycle(config, "unused")
        self.assertEqual(
            json.loads((self.root / "setup/cycle-state.json").read_text())["status"], "failed"
        )

    def test_gpu_guard_counts_existing_device_users_and_controller(self):
        with (
            patch.object(processes, "DeviceMemory") as device,
            patch.object(processes, "available_memory", return_value=8192),
            patch.object(processes, "process_info", return_value={"rss": 100}),
        ):
            device.return_value.used.return_value = 200
            resources = processes.GPUResources(
                {
                    "host_ram_reserve": 0,
                    "max_memory_bytes": 4096,
                    "max_vram_bytes": 256,
                    "controller_reserve_bytes": 64,
                },
                self.root,
                time.monotonic() + 3,
            )
            resources.check([{"pid": 1}])
            self.assertEqual(resources.observed["peak_family_RSS_bytes"], 264)
            self.assertEqual(resources.observed["peak_whole_device_used_bytes"], 200)
            resources.memory_limit = 263
            with self.assertRaisesRegex(processes.CycleStopped, "controller reserve"):
                resources.check([{"pid": 1}])
            resources.memory_limit = 4096
            device.return_value.used.return_value = 257
            with self.assertRaisesRegex(processes.CycleStopped, "VRAM cap"):
                resources.check()

    def test_owned_size_ignores_vanished_temporaries_but_refuses_other_errors(self):
        child = self.root / "nested"
        child.mkdir()
        (child / "data").write_bytes(b"data")
        (self.root / "link").symlink_to(child, target_is_directory=True)
        self.assertEqual(processes.directory_bytes(self.root), 4)
        missing = MagicMock()
        missing.stat.side_effect = FileNotFoundError("temporary removed")
        scan = MagicMock()
        scan.__enter__.return_value = iter([missing])
        with patch.object(processes.os, "scandir", return_value=scan):
            self.assertEqual(processes.directory_bytes(self.root), 0)
        missing.stat.assert_called_once_with(follow_symlinks=False)
        denied = MagicMock()
        denied.stat.side_effect = PermissionError("unreadable")
        scan.__enter__.return_value = iter([denied])
        with patch.object(processes.os, "scandir", return_value=scan):
            with self.assertRaises(PermissionError):
                processes.directory_bytes(self.root)

    def test_normal_bounded_tail_and_failure(self):
        record = self.run_child("import sys; sys.stdout.write('x'*3000000+'last')")
        self.assertEqual(record["status"], "complete")
        self.assertEqual(record["log_bytes_seen"], 3000004)
        self.assertEqual((self.root / "child.log").stat().st_size, processes.LOG_MAX_BYTES)
        self.assertTrue((self.root / "child.log").read_bytes().endswith(b"last"))
        self.assert_clean()
        (self.root / "child.log").unlink()
        with self.assertRaisesRegex(processes.CycleStopped, "child failed"):
            self.run_child("raise SystemExit(7)")
        self.assertEqual(self.record()["exit_code"], 7)
        self.assert_clean()

    def test_deadline_kills_term_ignoring_child(self):
        with self.assertRaisesRegex(processes.CycleStopped, "deadline"):
            self.run_child(
                "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)",
                timeout=0.2,
            )
        self.assertEqual(self.record()["exit_code"], -signal.SIGKILL)
        self.assert_clean()

    def test_missing_proc_identity_reaps_direct_child_without_claiming_descendants(self):
        ready = self.root / "ready"
        launched = []
        real_launch = subprocess.Popen

        def track_launch(*args, **kwargs):
            child = real_launch(*args, **kwargs)
            launched.append(child)
            return child

        def unavailable_identity(_pid):
            until = time.monotonic() + 2
            while not ready.exists() and time.monotonic() < until:
                time.sleep(0.01)
            self.assertTrue(ready.exists())
            return None

        source = (
            "import signal,time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            f"Path({str(ready)!r}).touch(); time.sleep(10)"
        )
        with (
            patch.object(processes, "process_info", unavailable_identity),
            patch.object(subprocess, "Popen", track_launch),
        ):
            with self.assertRaisesRegex(processes.CycleStopped, "cannot record child identity"):
                self.run_child(source)
        record = self.record()
        self.assertEqual(record["exit_code"], -signal.SIGKILL)
        self.assertTrue(record["direct_child_reaped"])
        self.assertEqual(record["descendant_visibility"], "unavailable")
        self.assertFalse(record["cleanup_complete"])
        self.assertIsNone(record["child"])
        self.assertEqual(record["error"], "cannot record child identity")
        self.assertEqual(record["cleanup_error"], "cycle cleanup incomplete")
        self.assertIsNotNone(launched[0].returncode)
        self.assertIsNone(processes.process_info(launched[0].pid))

    def test_control_exception_uses_same_cleanup(self):
        class BrokenControl:
            calls = 0

            def check(self, *_args):
                self.calls += 1
                if self.calls == 3:
                    raise ValueError("fake control failure")

        with self.assertRaisesRegex(ValueError, "fake control failure"):
            self.run_child(
                "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)",
                BrokenControl(),
            )
        self.assert_clean()

    def test_pause_and_output_controls(self):
        pause = self.root / "pause"
        policy = self.policy(pause_file=str(pause))
        with self.assertRaisesRegex(processes.CycleStopped, "paused"):
            self.run_child(
                f"from pathlib import Path; import time; Path({str(pause)!r}).touch(); time.sleep(10)",
                policy,
            )
        self.assert_clean()
        (self.root / "child.log").unlink()
        pause.unlink()
        policy = self.policy(max_output_bytes=4096)
        with self.assertRaisesRegex(processes.CycleStopped, "output_limit"):
            self.run_child(
                f"from pathlib import Path; import time; Path({str(self.root / 'data')!r}).write_bytes(b'x'*8192); time.sleep(10)",
                policy,
            )
        self.assert_clean()

    def test_aggregate_memory_control(self):
        baseline = processes.process_info(os.getpid())["rss"]
        policy = self.policy(max_memory_bytes=baseline + 15 * 1024**2)
        with self.assertRaisesRegex(processes.CycleStopped, "memory_limit"):
            self.run_child("import time; data=bytearray(32*1024**2); time.sleep(10)", policy)
        self.assert_clean()

    def test_prelaunch_pause_and_expired_deadline(self):
        pause = self.root / "pause"
        pause.touch()
        with self.assertRaisesRegex(processes.CycleStopped, "paused"):
            self.run_child(
                "raise AssertionError('must not launch')", self.policy(pause_file=str(pause))
            )
        with self.assertRaisesRegex(processes.CycleStopped, "deadline"):
            self.run_child("raise AssertionError('must not launch')", timeout=-1)
        self.assertFalse((self.root / "child.log").exists())

    def test_signal_during_launch_waits_for_identity_and_cleanup(self):
        real_launch = subprocess.Popen

        def interrupt_launch(*args, **kwargs):
            os.kill(os.getpid(), signal.SIGTERM)
            return real_launch(*args, **kwargs)

        with processes.cancellation_signals(), patch.object(subprocess, "Popen", interrupt_launch):
            with self.assertRaisesRegex(processes.CycleStopped, "SIGTERM"):
                self.run_child("import time; time.sleep(10)")
        self.assert_clean()

    def test_identity_mismatch_does_not_signal(self):
        real = processes.identity(processes.process_info(os.getpid()))
        wrong = {**real, "start_ticks": "0"}
        with patch.object(signal, "pidfd_send_signal") as send:
            processes.signal_members([wrong], signal.SIGTERM)
        send.assert_not_called()

    def test_recorded_detached_descendant_is_killed(self):
        descendant_path = self.root / "descendant.json"
        source = (
            "import os,json,signal,time; from pathlib import Path; "
            "from quoridor_training.cycle_process import process_info,identity; "
            "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            f"Path({str(descendant_path)!r}).write_text(json.dumps(identity(process_info(os.getpid())))); "
            "time.sleep(10)"
        )
        parent = (
            "import subprocess,sys,time; "
            f"subprocess.Popen([sys.executable,'-B','-c',{source!r}],start_new_session=True); "
            "time.sleep(10)"
        )
        with self.assertRaisesRegex(processes.CycleStopped, "deadline"):
            self.run_child(parent, timeout=0.35)
        descendant = json.loads(descendant_path.read_text())
        self.assertFalse(processes.alive(descendant))
        self.assert_clean()

    def test_sigterm_and_sigint_write_failed_cycle_and_reap(self):
        for signum in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=signum):
                stage_root = self.root / str(signum)
                stage_root.mkdir()
                runner = stage_root / "fake-runner"
                runner.write_text(
                    f"#!{sys.executable}\nimport time,signal\n"
                    "signal.signal(signal.SIGTERM,signal.SIG_IGN)\ntime.sleep(10)\n"
                )
                runner.chmod(0o700)
                config = stage_root / "config.json"
                config.write_text(
                    json.dumps(
                        {
                            "output": str(stage_root / "output"),
                            "cycle": {"python": sys.executable},
                            "host_ram_reserve": 0,
                            "wall_seconds": 10,
                        }
                    )
                )
                code = (
                    "from quoridor_training import cycle_process; cycle_process.TERM_SECONDS=.15; "
                    "from quoridor_training.cycle import cycle; "
                    f"cycle({str(config)!r},{str(runner)!r})"
                )
                controller = subprocess.Popen(
                    [sys.executable, "-B", "-c", code], stderr=subprocess.PIPE
                )
                try:
                    record_path = stage_root / "output" / "generation.process.json"
                    until = time.monotonic() + 3
                    while not record_path.exists() and time.monotonic() < until:
                        time.sleep(0.01)
                    self.assertTrue(record_path.exists())
                    time.sleep(0.1)
                    controller.send_signal(signum)
                    _stdout, stderr = controller.communicate(timeout=4)
                    self.assertNotEqual(controller.returncode, 0, stderr)
                    state = json.loads((stage_root / "output" / "cycle-state.json").read_text())
                    record = json.loads(record_path.read_text())
                    self.assertEqual(state["status"], "failed")
                    self.assertIn(signal.Signals(signum).name, state["error"])
                    self.assertTrue(record["cleanup_complete"])
                    self.assertFalse(processes.alive(record["child"]))
                finally:
                    if controller.poll() is None:
                        controller.kill()
                        controller.wait()
                    controller.stderr.close()

    def test_synthetic_full_cycle_stages(self):
        runner = self.root / "fake-runner"
        runner.write_text(
            f"#!{sys.executable}\n"
            "import json,sys\nfrom pathlib import Path\n"
            "args=sys.argv\n"
            "if args[1]=='model-check':\n"
            " assert Path(args[args.index('--model')+1]).exists()\n"
            "elif args[1]=='dataset':\n"
            " Path(args[args.index('--output')+1]).mkdir()\n"
            "else:\n"
            " cfg=json.loads(Path(args[args.index('--config')+1]).read_text())\n"
            " out=Path(cfg['output']); out.mkdir()\n"
            " if args[1]=='selfplay':\n"
            "  (out/'dataset').mkdir()\n"
            "  result={'rows':3,'wall_seconds':.1,'outcomes':[{'status':'complete'}]}\n"
            " else:\n"
            "  result={'score':.5,'planned':4,'outcomes':[{'status':'complete'}]*4}\n"
            " (out/'result.json').write_text(json.dumps(result))\n"
        )
        runner.chmod(0o700)
        fake_python = self.root / "fake-python"
        fake_python.write_text(
            f"#!{sys.executable}\n"
            "import json,sys\nfrom pathlib import Path\n"
            "args=sys.argv; out=Path(args[args.index('--output')+1]); out.mkdir()\n"
            "if 'train' in args:\n"
            " (out/'freeze.json').write_text('{}')\n"
            " (out/'data.json').write_text(json.dumps({'distance_fit':{'a':1,'b':8}}))\n"
            " (out/'best-model').mkdir(); (out/'best-model'/'manifest.json').write_text('{}')\n"
            "else:\n"
            " (out/'result.json').write_text('{}')\n"
        )
        fake_python.chmod(0o700)
        config = self.root / "config.json"
        config.write_text(
            json.dumps(
                {
                    "output": str(self.root / "cycle"),
                    "run_id": "synthetic",
                    "cycle": {"python": str(fake_python)},
                    "host_ram_reserve": 0,
                    "wall_seconds": 5,
                }
            )
        )
        state = cycle(config, runner)
        self.assertEqual(state["status"], "complete")
        self.assertFalse(state["adopted"])
        records = list((self.root / "cycle").glob("*.process.json"))
        self.assertEqual(len(records), 7)
        self.assertTrue(all(json.loads(path.read_text())["cleanup_complete"] for path in records))

        for name, horizon in (("null-cycle", None), ("default-cycle", "absent")):
            supplied = json.loads(config.read_text())
            supplied["output"] = str(self.root / name)
            if horizon == "absent":
                supplied.pop("wall_seconds")
            else:
                supplied["wall_seconds"] = horizon
            config.write_text(json.dumps(supplied))
            state = cycle(config, runner)
            self.assertEqual(state["status"], "complete")
            arena = json.loads((self.root / name / "arena-config.json").read_text())
            if horizon is None:
                self.assertIsNone(arena["wall_seconds"])
            else:
                self.assertGreater(arena["wall_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
