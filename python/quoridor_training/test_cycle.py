"""NN0 cycle ownership and resource contracts using synthetic short children."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from . import cycle_process as processes
from .cycle import cycle


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


if __name__ == "__main__":
    unittest.main()
