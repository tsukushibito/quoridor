"""Synthetic protocol ports only: no Torch, assets, rules, ABI or search."""

import json
import os
import subprocess
import sys
import unittest

CHILD = r"""
import os, sys
from quoridor_training import claustrophobia as owner
initializations = 0
library = object()
class Head:
    def facts(self):
        return {"logical_rows_attempted": 0, "constructor_model_calls": 0}
head = Head()
def initialize(assets):
    global initializations
    initializations += 1
    print("synthetic setup warning", file=sys.stderr, flush=True)
    return library, head
def run(request, *, runtime):
    owner.validate(request)
    assert runtime == (library, head)
    assert "torch" not in sys.modules
    return {"pid": os.getpid(), "initializations": initializations,
            "synthetic": True, "prefix": request["prefix"]}
owner.session_runtime = initialize
owner.run = run
owner.session()
"""


class SessionProtocolTests(unittest.TestCase):
    def test_one_initialization_two_replies_eof_and_wrong_sequence_refusal(self):
        assets = dict(library="/synthetic/library", model="/synthetic/model", max_head_calls=130)
        request = dict(
            prefix=[],
            legal=[13],
            simulations=64,
            c_puct=1.5,
            max_head_calls=65,
            model=assets["model"],
            library=assets["library"],
        )

        def execute(messages):
            wire = "".join(json.dumps(x) + "\n" for x in messages)
            with subprocess.Popen(
                [sys.executable, "-B", "-c", CHILD],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            ) as child:
                try:
                    stdout, stderr = child.communicate(wire, timeout=5)
                except BaseException:
                    child.kill()
                    child.communicate()
                    raise
                self.assertIsNotNone(child.returncode)
                return child.pid, child.returncode, stdout, stderr

        frames = [dict(sequence=n, request=request) for n in (1, 2)]
        pid, status, stdout, stderr = execute([assets, *frames])
        self.assertEqual(status, 0, stderr)
        rows = [json.loads(line) for line in stdout.splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["session"], "ready")
        self.assertEqual(rows[0]["execution"]["pid"], pid)
        self.assertEqual([r["sequence"] for r in rows[1:]], [1, 2])
        self.assertTrue(all(r["result"]["pid"] == pid for r in rows[1:]))
        self.assertTrue(all(r["result"]["initializations"] == 1 for r in rows[1:]))
        self.assertEqual(stderr.count("synthetic setup warning"), 1)
        _, status, stdout, stderr = execute([assets, dict(sequence=2, request=request)])
        self.assertNotEqual(status, 0)
        self.assertEqual(len(stdout.splitlines()), 1)  # Ready, never a wrong reply.
        self.assertIn("matching session sequence and fixed assets", stderr)


if __name__ == "__main__":
    unittest.main()
