"""New NN0 wire/child fixtures; all model/native assets are synthetic and unopened."""

import ctypes
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

from quoridor_runtime import cycle_process

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "games/quoridor/python/quoridor_training/claustrophobia.py"
)
SPEC = importlib.util.spec_from_file_location("claustrophobia_boundary", MODULE_PATH)
boundary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(boundary)


def request():
    return dict(
        prefix=[81, 163],
        legal=[3, 5, 13],
        simulations=8,
        c_puct=1.5,
        max_head_calls=9,
        library="/synthetic/unopened.so",
        model="/synthetic/unopened.pt",
    )


class ClaustrophobiaArenaTests(unittest.TestCase):
    def test_absolute209_ordered_prefix_and_explicit_finite_limits(self):
        value = request()
        self.assertIs(boundary.validate(value), value)
        for key, invalid in (
            ("prefix", [True]),
            ("prefix", [209]),
            ("legal", [3, 3]),
            ("simulations", True),
            ("simulations", -1),
            ("c_puct", float("nan")),
            ("max_head_calls", False),
            ("model", "relative.pt"),
        ):
            with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                boundary.validate(dict(value, **{key: invalid}))
        with self.assertRaises(ValueError):
            boundary.validate(dict(value, sigma_backend="not-an-alias"))

    def test_result_identity_legal_and_partial_counts_no_fake_move(self):
        value = request()
        args = dict(action=13, simulations=8, calls=9, value=0.25, legal=[13, 5, 3])
        result = boundary.checked_result(value, **args)
        self.assertEqual(result["entry"], "mcts::run_mcts")
        self.assertIsNone(result["search_value"])
        self.assertIsNone(result["nodes"])
        for key, invalid in (
            ("action", 209),
            ("action", True),
            ("simulations", 7),
            ("calls", 10),
            ("calls", 0),
            ("value", float("inf")),
            ("legal", [3, 5]),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                boundary.checked_result(value, **dict(args, **{key: invalid}))

    def test_forward_only_has_one_head_and_no_search_action(self):
        value = dict(request(), simulations=0, max_head_calls=1)
        boundary.validate(value)
        result = boundary.checked_result(
            value, action=None, simulations=0, calls=1, value=-0.5, legal=value["legal"]
        )
        self.assertIsNone(result["action"])
        with self.assertRaises(ValueError):
            boundary.checked_result(
                value, action=13, simulations=0, calls=1, value=-0.5, legal=value["legal"]
            )

    def test_native_abi_layout_declaration(self):
        # Declaration check only; actual Rust sizeof/offset and numerical join
        # remain unbuilt until the pinned upstream library is qualified.
        self.assertEqual(ctypes.sizeof(boundary.Output), 240)
        self.assertEqual(boundary.Output.head_calls.offset, 16)
        self.assertEqual(boundary.Output.root_value.offset, 24)
        self.assertEqual(boundary.Output.legal_absolute.offset, 28)

    def test_real_child_bad_request_rejects_before_ml_native_asset_import(self):
        value = dict(request(), prefix=[209])
        child = subprocess.Popen(
            [sys.executable, "-B", str(MODULE_PATH)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        identity = cycle_process.process_info(child.pid)
        self.assertIsNotNone(identity)
        try:
            out, err = child.communicate(json.dumps(value).encode(), timeout=3)
            self.assertEqual(child.returncode, 1)
            self.assertEqual(out, b"")
            self.assertIn(b"absolute209", err)
            self.assertNotIn(b"No module named", err)
            self.assertNotIn(b"unopened", err)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream:
                    stream.close()
        current = cycle_process.process_info(child.pid)
        self.assertTrue(
            current is None or any(current[k] != identity[k] for k in ("start_ticks", "boot_id"))
        )
        self.assertTrue(all(stream.closed for stream in (child.stdin, child.stdout, child.stderr)))
        print(
            json.dumps(
                dict(
                    synthetic_child=identity,
                    directwait_return=child.returncode,
                    matching_identity_absent=True,
                    three_streams_closed=True,
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
