"""Synthetic transport checks for the maintained continuous comparison owner."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from othello_arena import continuous


def result():
    return dict(
        move=1,
        rawScore=3,
        score=3,
        scoreUnits="engine-disc",
        proven=False,
        completedDepth=6,
        selectivity=6,
        probability=None,
        isEndSearch=False,
        nodes=100,
        mustPass=False,
        terminal=False,
        interpretation="simd",
        coefficients={},
        ttBytes=1024,
        stopped=None,
    )


class ContinuousFixedBoundary(unittest.TestCase):
    def run_owner(
        self,
        directory,
        *,
        mismatch,
        selected_profiles=("fixed", "timed"),
        timed_options=None,
        search_requests=None,
    ):
        root = Path(directory)
        out = root / "out"
        out.mkdir()
        trace = []
        info = dict(
            engine="console7.8.1-rust-singlethread-source-port",
            upstreamCommit="570d5e0a478c9d720d75de06a5d31995f412704a",
            interpretation="simd",
            identityBinding="callerVerified",
            hashLevel=20,
            hashSeed=20261022,
            workerPool=0,
            midgameId="sha256:mid",
            orderingId="sha256:ordering",
            coefficients={},
        )
        midgame = dict(path="/synthetic/mid", sha256="mid")
        ordering = dict(path="/synthetic/ordering", sha256="ordering")
        families = []
        for family in range(4):
            roots = []
            for index, placement in enumerate((16, 32, 48, 56)):
                roots.append(
                    dict(
                        id=f"f{family}r{index}",
                        placement=placement,
                        rulesStatusBinding="synthetic-port",
                        canonicalSHA256=f"synthetic-{family}-{index}",
                        state=dict(version=1, board=[0] * 64, toMove=1),
                        status=dict(terminal=False, mustPass=False, legalMoves=[1, 2]),
                        fixedDepth=6,
                    )
                )
            families.append(
                dict(
                    id=f"f{family}",
                    seed=2026102301001 + family,
                    exposureComponent=f"synthetic-component-{family}",
                    split="development",
                    generationActions=0,
                    roots=roots,
                )
            )
        roots_path = root / "roots.json"
        roots_path.write_text(json.dumps(dict(admitted=True, H=0, families=families)))
        profiles = {}
        for profile in selected_profiles:
            definition = dict(
                expectedInfo={owner: info for owner in ("baseline", "candidate")},
                qualifiedBuilds={
                    owner: dict(path="/synthetic/build") for owner in ("baseline", "candidate")
                },
                options=dict(timed_options or {}) if profile == "timed" else {},
            )
            for owner in ("baseline", "candidate"):
                definition[owner] = dict(
                    binary=dict(path="/synthetic/" + owner, sha256=owner),
                    argv=["/synthetic/" + owner, profile],
                    cwd=str(root),
                    assets=[midgame, ordering],
                )
            profiles[profile] = definition
        config = dict(
            admitted=True,
            comparisonKind="rust-rust",
            comparator=dict(path=continuous.__file__),
            pruningOffMeaning="statistical-MPC-off;exact-cuts-retained",
            generationQualification=dict(path="/synthetic/generation"),
            exposureQualification=dict(path="/synthetic/exposure"),
            cpuPlan="synthetic",
            resourceBinding="synthetic",
            outputDirectory=str(out),
            projectRoot=str(root),
            cancelFile=str(root / "CANCEL"),
            sourceRequired=[],
            protocolSource=dict(path="/synthetic/protocol"),
            arenaMainSource=dict(path="/synthetic/main"),
            roots=dict(path=str(roots_path)),
            midgame=midgame,
            ordering=ordering,
            coefficients={},
            profiles=profiles,
            limits=dict(
                fixedRequestSeconds=10,
                timedRequestSeconds=1.1,
                setupSeconds=30,
                resetSeconds=5,
                dropSeconds=6,
                commandSeconds=1200,
                parentSeconds=1260,
            ),
        )
        config_path = root / "config.json"
        raw = json.dumps(config).encode()
        config_path.write_bytes(raw)

        class CannedProcess:
            def __init__(self, argv, **kwargs):
                self.owner, self.profile = Path(argv[0]).name, argv[1]
                self.child = SimpleNamespace(pid=-1)
                self.closed = False
                self.cleanup = None
                trace.append(("init", self.owner, self.profile))

            def json_request(self, request, **kwargs):
                op = request["op"]
                trace.append((op, self.owner, self.profile))
                if op == "info":
                    return dict(info)
                if op == "clear":
                    return dict(ok=True)
                if search_requests is not None:
                    search_requests.append((self.owner, self.profile, request))
                row = result()
                if self.owner == "candidate":
                    if self.profile == "fixed" and mismatch:
                        row["nodes"] += 1
                    if self.profile == "timed":
                        row.update(move=2, nodes=200, completedDepth=7)
                return dict(result=row)

            def close(self):
                trace.append(("close", self.owner, self.profile))
                self.closed = True
                self.cleanup = dict(directReaped=True, unexpectedExit=False, errors=[])

        modules = {
            "othello_arena.protocol": SimpleNamespace(Process=CannedProcess),
            "othello_arena.__main__": SimpleNamespace(checked_spec=lambda spec: spec),
        }
        env = dict(
            CUDA_VISIBLE_DEVICES="",
            OMP_NUM_THREADS="1",
            OPENBLAS_NUM_THREADS="1",
            MKL_NUM_THREADS="1",
        )
        argv = ["synthetic", str(config_path), hashlib.sha256(raw).hexdigest()]
        with (
            patch.object(sys, "argv", argv),
            patch.dict(sys.modules, modules),
            patch.dict("os.environ", env),
            patch.object(continuous, "checked", lambda item, maximum=None: Path(item["path"])),
        ):
            if mismatch:
                with self.assertRaises(SystemExit) as caught:
                    continuous.main()
                self.assertEqual(caught.exception.code, 1)
            else:
                continuous.main()
        return (
            trace,
            json.loads((out / "result.json").read_text()),
            json.loads((out / "completion.json").read_text()),
        )

    def test_fixed_fields_refuse_missing_types_and_stop_before_remaining_dispatch(self):
        base = result()
        changes = dict(
            rawScore=4,
            score=4,
            move=2,
            mustPass=True,
            nodes=101,
            completedDepth=5,
            selectivity=5,
            probability=100.0,
            proven=True,
            isEndSearch=True,
        )
        for key, value in changes.items():
            with self.subTest(field=key):
                changed = dict(base, **{key: value})
                self.assertEqual(continuous.fixed_differences(base, changed), [key])
                missing = dict(base)
                del missing[key]
                with self.assertRaises(KeyError):
                    continuous.fixed_differences(base, missing)
        self.assertEqual(continuous.fixed_differences(base, dict(base, proven=0)), ["proven"])
        with tempfile.TemporaryDirectory() as directory:
            trace, saved, completion = self.run_owner(directory, mismatch=True)
        self.assertFalse(completion["complete"])
        self.assertEqual(completion["attempted"], 5)
        self.assertEqual(completion["remainingUNRUN"], 123)
        self.assertEqual(sum(op == "search" for op, _, _ in trace), 5)
        self.assertEqual(sum(op == "close" for op, _, _ in trace), 2)
        self.assertEqual(saved["slots"][4]["status"], "FAILED")
        self.assertEqual(saved["slots"][4]["pairedComparison"]["fixedDifferences"], ["nodes"])
        self.assertIn("nodes", completion["firstError"]["error"])

    def test_matching_fixed_and_different_timed_keep_abba_census_and_close(self):
        with tempfile.TemporaryDirectory() as directory:
            trace, saved, completion = self.run_owner(directory, mismatch=False)
        self.assertTrue(completion["complete"])
        self.assertEqual(completion["attempted"], 128)
        self.assertEqual(completion["remainingUNRUN"], 0)
        self.assertEqual(len(saved["setup"]), 4)
        self.assertEqual(len(saved["resets"]), 32)
        self.assertEqual(len(saved["shutdown"]), 4)
        self.assertEqual(sum(op == "search" for op, _, _ in trace), 128)
        self.assertEqual(sum(op == "close" for op, _, _ in trace), 4)
        paired = [row for row in saved["slots"] if "pairedComparison" in row]
        self.assertEqual(len(paired), 64)
        self.assertTrue(
            all(
                row["pairedComparison"]["fixedDifferences"] == []
                for row in paired
                if row["profile"] == "fixed"
            )
        )
        self.assertTrue(
            all(
                row["pairedComparison"]["policyDifferent"]
                for row in paired
                if row["profile"] == "timed"
            )
        )

    def test_timed_only_preserves_logical_slots_order_wire_and_selected_owners(self):
        requests = []
        with tempfile.TemporaryDirectory() as directory:
            trace, saved, completion = self.run_owner(
                directory,
                mismatch=False,
                selected_profiles=("timed",),
                timed_options=dict(maxDepth=60, timeMs=1000),
                search_requests=requests,
            )
        expected = [
            (family, block, owner, repeat, root)
            for family in range(4)
            for block, owner, repeat in (
                (0, "baseline", 0),
                (1, "candidate", 0),
                (2, "candidate", 1),
                (3, "baseline", 1),
            )
            for root in range(4)
        ]
        self.assertEqual([slot["index"] for slot in saved["slots"]], list(range(64, 128)))
        self.assertEqual(
            [(s["family"], s["block"], s["owner"], s["repeat"], s["root"]) for s in saved["slots"]],
            [(f"f{f}", b, o, r, f"f{f}r{i}") for f, b, o, r, i in expected],
        )
        self.assertTrue(all(profile == "timed" for _, _, profile in trace))
        self.assertEqual(len(requests), 64)
        self.assertTrue(
            all(
                p == "timed" and r["options"] == {"maxDepth": 60, "timeMs": 1000}
                for _, p, r in requests
            )
        )
        self.assertEqual([owner for owner, _, _ in requests], [o for _, _, o, _, _ in expected])
        self.assertEqual(sum(op == "init" for op, _, _ in trace), 2)
        self.assertEqual(sum(op == "clear" for op, _, _ in trace), 16)
        self.assertEqual(sum(op == "close" for op, _, _ in trace), 2)
        self.assertEqual(saved["plannedCalls"], 64)
        self.assertEqual(saved["attemptedCalls"], 64)
        self.assertEqual(saved["completedCalls"], 64)
        self.assertTrue(all(s["status"] == "COMPLETE" for s in saved["slots"]))
        self.assertEqual(sum("pairedComparison" in s for s in saved["slots"]), 32)
        self.assertEqual(completion["planned"], 64)
        self.assertEqual(completion["attempted"], 64)
        self.assertEqual(completion["remainingUNRUN"], 0)
        self.assertIsNone(completion["firstError"])
        self.assertTrue(completion["complete"])


if __name__ == "__main__":
    unittest.main()
