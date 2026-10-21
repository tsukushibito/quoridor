"""NEW file-transport NN0 fixtures; native/model/run result ports are synthetic."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from quoridor_runtime import cycle_process

MODULE_PATH = (
    Path(__file__).resolve().parents[4]
    / "games/quoridor/python/quoridor_training/claustrophobia.py"
)
SPEC = importlib.util.spec_from_file_location("claustrophobia_file_boundary", MODULE_PATH)
boundary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(boundary)
OWN = Path(__file__).resolve().parents[5]


def request():
    # This legal list is a synthetic transport value, not a replay qualification.
    return dict(
        prefix=[13],
        legal=[67],
        simulations=0,
        c_puct=1.5,
        max_head_calls=1,
        library="/synthetic/unopened.so",
        model="/synthetic/unopened.pt",
    )


class ClaustrophobiaFileRequestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="file-request-NN0-", dir=OWN)
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.file = self.directory / "request.json"

    def arguments(self, raw):
        self.file.write_bytes(raw)
        return ["--request", str(self.file), "--request-sha256", hashlib.sha256(raw).hexdigest()]

    def invoke(self, argv, stdin=b""):
        with (
            mock.patch.object(sys, "argv", [str(MODULE_PATH), *argv]),
            mock.patch.object(sys, "stdin", SimpleNamespace(buffer=io.BytesIO(stdin))),
            contextlib.redirect_stdout(io.StringIO()) as output,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            boundary.main()
        return json.loads(output.getvalue())

    def test_file_and_stdin_dispatch_the_same_run_with_exact_raw_hash(self):
        raw = b"\n" + json.dumps(request(), indent=2).encode() + b"\n"
        argv = self.arguments(raw)
        result = {"synthetic_run_port": True}
        with mock.patch.object(boundary, "run", return_value=result) as run:
            self.assertEqual(self.invoke(argv), result)
            self.assertEqual(self.invoke([], raw), result)
            self.assertEqual(self.invoke(["--stdin"], raw), result)
        self.assertEqual(run.call_args_list, [mock.call(request())] * 3)
        # SHA is over exact file bytes, not parsed/re-encoded JSON.
        argv[-1] = hashlib.sha256(json.dumps(request()).encode()).hexdigest()
        with (
            mock.patch.object(boundary, "run") as run,
            self.assertRaisesRegex(ValueError, "SHA256"),
        ):
            self.invoke(argv)
        run.assert_not_called()

    def test_argument_pairs_and_competing_sources_refuse_before_run(self):
        argv = self.arguments(json.dumps(request()).encode())
        for invalid in (
            ["--request", str(self.file)],
            ["--request-sha256", "a" * 64],
            ["--stdin", *argv],
            ["--request", str(self.file), "--request-sha256", "not-a-sha"],
            ["--unknown"],
        ):
            with self.subTest(argv=invalid), mock.patch.object(boundary, "run") as run:
                with self.assertRaises(SystemExit) as error:
                    self.invoke(invalid)
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()
        with mock.patch.object(boundary, "run") as run:
            with self.assertRaisesRegex(ValueError, "mutually exclusive"):
                self.invoke(argv, b" ")
            run.assert_not_called()

    def test_size_hash_json_and_schema_fail_before_ml_or_native_load(self):
        original_import = __import__

        def no_ml(name, *args, **kwargs):
            if name in {"torch", "numpy"}:
                raise AssertionError("ML import before request refusal")
            return original_import(name, *args, **kwargs)

        cases = [
            (b" " * (boundary.MAX_REQUEST + 1), "bounded", False),
            (b"{not-json", "Expecting", False),
            (json.dumps(dict(request(), legal=[])).encode(), "nonempty", True),
        ]
        for raw, message, enters_run in cases:
            argv = self.arguments(raw)
            with (
                self.subTest(message=message),
                mock.patch("builtins.__import__", side_effect=no_ml),
                mock.patch.object(
                    boundary.C, "CDLL", side_effect=AssertionError("native load")
                ) as dll,
                mock.patch.object(boundary, "run", wraps=boundary.run) as run,
                self.assertRaisesRegex(ValueError, message),
            ):
                self.invoke(argv)
            self.assertEqual(run.call_count, int(enters_run))
            dll.assert_not_called()
        argv = self.arguments(json.dumps(request()).encode())
        argv[-1] = "0" * 64
        with (
            mock.patch.object(boundary, "run") as run,
            self.assertRaisesRegex(ValueError, "SHA256"),
        ):
            self.invoke(argv)
        run.assert_not_called()

    def test_request_file_refuses_relative_missing_symlink_and_fifo(self):
        argv = self.arguments(json.dumps(request()).encode())
        relative = ["--request", "relative.json", "--request-sha256", argv[-1]]
        with mock.patch.object(boundary, "run") as run, self.assertRaises(SystemExit):
            self.invoke(relative)
        run.assert_not_called()
        symlink = self.directory / "symlink.json"
        symlink.symlink_to(self.file)
        fifo = self.directory / "fifo"
        os.mkfifo(fifo)
        for path, error in [
            (self.directory / "missing", OSError),
            (symlink, OSError),
            (fifo, ValueError),
        ]:
            with self.subTest(path=path), mock.patch.object(boundary, "run") as run:
                with self.assertRaises(error):
                    self.invoke(["--request", str(path), "--request-sha256", argv[-1]])
                run.assert_not_called()

    def test_real_file_cli_hash_refusal_directwait_cleanup_before_assets(self):
        argv = self.arguments(json.dumps(request()).encode())
        argv[-1] = "0" * 64
        child = subprocess.Popen(
            [sys.executable, "-B", str(MODULE_PATH), *argv],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            identity = cycle_process.process_info(child.pid)
            self.assertIsNotNone(identity)
            output, errors = child.communicate(b"", timeout=3)
            self.assertEqual(child.returncode, 1)
            self.assertEqual(output, b"")
            self.assertIn(b"request SHA256 mismatch", errors)
            self.assertNotIn(b"unopened", errors)
            self.assertNotIn(b"No module named", errors)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
            for stream in (child.stdin, child.stdout, child.stderr):
                stream.close()
        current = cycle_process.process_info(child.pid)
        self.assertTrue(
            current is None
            or any(current[key] != identity[key] for key in ("start_ticks", "boot_id"))
        )
        self.assertTrue(all(stream.closed for stream in (child.stdin, child.stdout, child.stderr)))
        print(
            json.dumps(
                {
                    "synthetic_child": identity,
                    "directwait_return": child.returncode,
                    "exact_identity_absent": True,
                    "three_handles_closed": True,
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
