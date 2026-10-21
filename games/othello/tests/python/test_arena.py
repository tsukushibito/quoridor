"""Protocol and outcome tests; fixtures do not implement Othello rules."""

import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from othello_arena import coordinate, move_index
from othello_arena.engines import GTP
from othello_arena.matches import game, paired, summarize
from othello_arena.protocol import EngineError, Native, Process


class ArenaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def process(self, script):
        p = Process([sys.executable, "-u", "-c", script], cwd=self.root, log=self.root / "io.log")
        self.addCleanup(p.close)
        return p

    def test_coordinate_roundtrip(self):
        for i in range(64):
            self.assertEqual(move_index(coordinate(i)), i)
        self.assertEqual(coordinate(0), "a1")
        self.assertEqual(coordinate(63), "h8")
        self.assertIsNone(move_index("PASS"))
        for invalid in (True, -1, 64):
            with self.assertRaises(ValueError):
                coordinate(invalid)

    def test_persistent_jsonl_native(self):
        p = self.process(
            "import sys,json\nfor s in sys.stdin:\n r=json.loads(s);print(json.dumps({'ok':True,'move':r['state']['toMove']}),flush=True)"
        )
        n = Native(p)
        for side in (1, 2):
            self.assertEqual(n.choose({"toMove": side}, deadline=time.monotonic() + 2), side)
        p.close()
        self.assertTrue(p.cleanup["directReaped"])
        self.assertTrue(p.child.stdin.closed and p.child.stdout.closed and p.child.stderr.closed)

    def test_stderr_flood_is_drained_and_log_bounded(self):
        p = self.process(
            "import sys\nsys.stderr.write('x'*200000);sys.stderr.flush();print('ready',flush=True);sys.stdin.readline()"
        )
        self.assertEqual(p.line(time.monotonic() + 3), "ready")
        p.close()
        self.assertGreater(p.bytes_seen, 200000)
        self.assertLessEqual(p.log.stat().st_size, 65536)

    def test_timeout_cancel_eof_crash_malformed_and_frame_bound(self):
        cases = [
            ("import time;time.sleep(10)", "timeout"),
            ("pass", "eof"),
            ("import sys;sys.exit(7)", "crash"),
            ("print('x'*70000,flush=True)", "protocol"),
        ]
        for script, kind in cases:
            with self.subTest(kind=kind):
                p = self.process(script)
                with self.assertRaises(EngineError) as caught:
                    p.line(time.monotonic() + 0.3)
                self.assertEqual(caught.exception.kind, kind)
                p.close()
                self.assertTrue(p.cleanup["directReaped"])
        p = self.process("import time;time.sleep(10)")
        p.cancelled = lambda: True
        with self.assertRaises(EngineError) as caught:
            p.line(time.monotonic() + 2)
        self.assertEqual(caught.exception.kind, "cancelled")
        p.close()
        p = self.process("import sys;sys.stdin.readline();print('bad json',flush=True)")
        with self.assertRaises(EngineError):
            Native(p).request("new", deadline=time.monotonic() + 2)

    def test_gtp_ids_errors_and_coordinates(self):
        script = "import sys\nfor s in sys.stdin:\n tag,cmd=s.strip().split(' ',1);print(('?' if cmd=='bad' else '=')+tag+(' C4' if cmd.startswith('genmove') else ''),end='\\n\\n',flush=True)"
        g = GTP(self.process(script), engine="edax")
        deadline = time.monotonic() + 2
        g.reset(deadline=deadline)
        g.prepare({"toMove": 1}, deadline=deadline)
        self.assertEqual(g.choose({"toMove": 1}, deadline=deadline), 26)
        g.observe(2, None, deadline=deadline)
        with self.assertRaises(EngineError):
            g.command("bad", deadline=deadline)


class RulesFixture:
    def __init__(self, *, pass_first=False):
        self.step = 0
        self.calls = []
        self.pass_first = pass_first

    def request(self, op, **fields):
        self.calls.append(op)
        if op == "status":
            return {
                "status": {
                    "terminal": self.step == 2,
                    "mustPass": self.pass_first and self.step == 0,
                    "legalMoves": [] if self.pass_first and self.step == 0 else [26],
                    "black": 10,
                    "white": 7,
                }
            }
        if op in ("play", "pass"):
            self.step += 1
        if op == "new":
            self.step = 0
        return {
            "state": {"board": [0] * 64, "toMove": 1 if self.step % 2 == 0 else 2, "version": 1}
        }


class PlayerFixture:
    def __init__(self, error=None, move=26):
        self.error = error
        self.move = move
        self.observed = []
        self.choices = 0

    def reset(self, **_):
        pass

    def prepare(self, *_args, **_kwargs):
        pass

    def observe(self, side, move, **_):
        self.observed.append((side, move))

    def choose(self, *_args, **_kwargs):
        self.choices += 1
        if self.error:
            raise EngineError(self.error, "injected failure")
        return self.move


class OutcomeTests(unittest.TestCase):
    def test_forced_pass_terminal_and_actual_disc_difference_use_rust(self):
        rules = RulesFixture(pass_first=True)
        black, white = PlayerFixture(), PlayerFixture()
        result = game(rules, {1: black, 2: white}, [], family="p", candidate_side=2)
        self.assertTrue(result["completed"])
        self.assertEqual(result["blackMinusWhite"], 3)
        self.assertEqual(result["candidateScore"], 0)
        self.assertEqual(black.choices, 0)
        self.assertIn((1, None), white.observed)
        self.assertIn("pass", rules.calls)

    def test_both_colors_same_opening_and_failure_retained_without_refill(self):
        families = [{"id": "p", "moves": []}]
        results = list(paired(RulesFixture(), PlayerFixture(), PlayerFixture(), families))
        self.assertEqual([x["candidateSide"] for x in results], [1, 2])
        for failure in ("timeout", "eof", "crash", "cancelled"):
            results = list(
                paired(RulesFixture(), PlayerFixture(error=failure), PlayerFixture(), families)
            )
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["failure"]["kind"], failure)
            report = summarize(results, 2)
            self.assertEqual(report["unrun"], 1)
            self.assertEqual(report["scoreRateBoundsIncludingUnknown"], [0, 1])
        result = game(
            RulesFixture(),
            {1: PlayerFixture(move=None), 2: PlayerFixture()},
            [],
            family="i",
            candidate_side=1,
        )
        self.assertEqual(result["failure"]["kind"], "illegal")
        self.assertFalse(result["completed"])


class EntryTests(unittest.TestCase):
    def test_full_entry_persistent_fake_protocol_and_denominator(self):
        from othello_arena.__main__ import run
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = Path(sys.executable)
            ref = {
                "bytes": binary.stat().st_size,
                "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            }
            script = """import json,sys
for line in sys.stdin:
 r=json.loads(line);op=r['op'];state=r.get('state',{'version':1,'board':[0]*64,'toMove':1,'step':0})
 if op=='status':out={'status':{'black':10,'white':7,'terminal':state['step']==2,'mustPass':False,'legalMoves':[26]}}
 elif op in ('simple','search'):out={'move':26}
 else:
  if op in ('play','pass'):state=dict(state,step=state['step']+1,toMove=3-state['toMove'])
  out={'state':state}
 print(json.dumps(dict(ok=True,**out)),flush=True)
"""
            native = {"argv": [str(binary), "-u", "-c", script], "cwd": tmp, "binary": ref}
            gtp_script = "import sys\nfor line in sys.stdin:\n tag,cmd=line.strip().split(' ',1);print('= '+tag+(' C4' if cmd.startswith('genmove') else ''),end='\\n\\n',flush=True)"
            opponent = {
                "argv": [str(binary), "-u", "-c", gtp_script],
                "cwd": tmp,
                "binary": ref,
                "protocol": "gtp",
                "engine": "edax",
                "id": "fake",
            }
            config = {
                "families": [
                    {"id": f"fake-{i}", "moves": [], "split": "protocol-smoke-only"}
                    for i in range(4)
                ],
                "purpose": "protocol_cost",
                "superiorityClaim": False,
                "timeMs": 1000,
                "threads": 1,
                "ttMiB": 32,
                "book": False,
                "ponder": False,
                "overheadMs": 100,
                "launchBinding": {"testFixture": True},
                "rules": native,
                "candidate": native,
                "opponents": [opponent],
            }
            self.assertEqual(run(config, root / "result"), 0)
            report = json.loads((root / "result/result.json").read_text())
            self.assertEqual(report["byOpponent"]["fake"]["completed"], 8)
            self.assertEqual(report["byOpponent"]["fake"]["points"], 4)
            self.assertFalse(report["superiorityClaim"])
            self.assertTrue(all(x["directReaped"] for x in report["cleanup"]))


if __name__ == "__main__":
    unittest.main()
