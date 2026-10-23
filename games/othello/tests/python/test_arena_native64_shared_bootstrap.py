"""Canned NumPy/index and process boundaries; no real RNG, rules, search or model."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from othello_arena import __main__ as arena
from test_arena_native64_boundaries import identity, response


def fake_numpy():
    tracker = {"tables": 0, "seeds": [], "consumedIndices": [], "quantiles": []}

    class Indices:
        shape = (10000, 16)
        dtype = SimpleNamespace(str="<i8")

        def astype(self, dtype, *, copy):
            assert dtype == "<i8" and copy is False
            return self

        def tobytes(self, *, order):
            assert order == "C"
            return b"\0" * (10000 * 16 * 8)

    class Generator:
        def integers(self, low, high, *, size, dtype):
            assert (low, high, size, dtype) == (0, 16, (10000, 16), "fixture-int64")
            tracker["tables"] += 1
            return Indices()

    class Resamples:
        def mean(self, *, axis):
            assert axis == 1
            return "opaque-canned-draw-means"

    class Means:
        def __getitem__(self, indices):
            tracker["consumedIndices"].append(id(indices))
            return Resamples()

    def pcg(seed):
        tracker["seeds"].append(seed)
        return "opaque-pcg"

    def generator(pcg_owner):
        assert pcg_owner == "opaque-pcg"
        return Generator()

    def asarray(values, *, dtype):
        assert values == [0.5] * 16 and dtype is float
        return Means()

    def quantile(values, tails, *, method):
        assert values == "opaque-canned-draw-means"
        assert tails == [0.025, 0.975] and method == "linear"
        tracker["quantiles"].append(method)
        return (0.5, 0.5)

    return SimpleNamespace(
        __version__="fake-model-free-boundary",
        int64="fixture-int64",
        random=SimpleNamespace(PCG64=pcg, Generator=generator),
        asarray=asarray,
        quantile=quantile,
    ), tracker


def result(family, side, opponent):
    external = (
        {
            "ok": True,
            "move": 19,
            "score": 0,
            "scoreKind": "engine_estimate_stm",
            "completedDepth": 8,
            "probability": 100,
            "nodes": 1,
            "elapsedMs": 999,
            "budgetMs": 1000,
            "proven": False,
        }
        if opponent == "fixed"
        else {"protocol": "gtp", "engine": "edax", "side": 3 - side, "move": 19, "response": "D3"}
    )
    return {
        "family": family["id"],
        "candidateSide": side,
        "completed": True,
        "failure": None,
        "blackMinusWhite": 0,
        "candidateScore": 0.5,
        "status": {"terminal": True, "black": 32, "white": 32},
        "moves": [
            {"side": side, "move": 20, "opening": False, "wallMs": 1001, "search": response()},
            {"side": 3 - side, "move": 19, "opening": False, "wallMs": 1001, "search": external},
        ],
    }


def run_fixture(second_complete):
    np, tracker = fake_numpy()
    families = [{"id": f"development/f{i:02}", "moves": []} for i in range(16)]
    fixed_info = {
        "label": "Console7.8.1-engine + fixed-time adapter",
        "engineCommit": "570d5e0a478c9d720d75de06a5d31995f412704a",
        "searchThreads": 1,
        "workerPool": 0,
        "hashLevel": 20,
        "hashSeed": 20261022,
        "activeTTBytes": 25165872,
        "book": False,
        "ponder": False,
    }
    spec = {"argv": ["/unused"], "cwd": "/unused"}
    config = {
        "purpose": "native_external_development",
        "launchBinding": {"fixture": True},
        "rules": spec,
        "candidate": dict(spec, protocol="fullsearch_jsonl", identity=identity(), options={}),
        "timeMs": 1000,
        "overheadMs": 100,
        "opponents": [
            dict(spec, id="fixed", protocol="fixed_jsonl", identity=fixed_info),
            dict(spec, id="edax", protocol="gtp", engine="edax"),
        ],
    }

    class Process:
        cleanup = None

        def __init__(self, *args, **kwargs):
            pass

        def json_request(self, request, *, deadline):
            assert request == {"op": "info"}
            return {"ok": True, **fixed_info}

        def close(self):
            self.cleanup = {"directReaped": True, "unexpectedExit": False, "errors": []}

    class Player:
        def __init__(self, *args, **kwargs):
            pass

        def initialize(self, *, deadline):
            return {"ok": True, **identity()}

    calls = []

    def paired(rules, candidate, opponent, selected, **kwargs):
        name = "fixed" if not calls else "edax"
        calls.append(name)
        for family in selected:
            for side in (1, 2):
                row = result(family, side, name)
                if name == "edax" and not second_complete and family is selected[-1] and side == 2:
                    row.update(
                        completed=False,
                        candidateScore=None,
                        failure={"kind": "fixture-first-error"},
                    )
                yield row

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "out"
        with (
            patch.dict("sys.modules", {"numpy": np}),
            patch.object(arena, "development_families", return_value=families),
            patch.object(arena, "checked_spec"),
            patch.object(arena, "Process", Process),
            patch.object(arena, "FullSearchPlayer", Player),
            patch.object(arena, "paired", paired),
        ):
            code = arena.run(copy.deepcopy(config), output)
        report = json.loads((output / "result.json").read_text())
        tracker["indexFileBytes"] = (output / "bootstrap-indices.i64le").stat().st_size
    return code, report, tracker


class Native64SharedBootstrapTests(unittest.TestCase):
    def test_one_pcg_table_and_family_order_is_shared_by_both_complete_opponents(self):
        code, report, tracker = run_fixture(True)
        self.assertEqual(code, 0)
        self.assertEqual(tracker["tables"], 1)
        self.assertEqual(tracker["seeds"], [2026102302064])
        self.assertEqual(len(tracker["consumedIndices"]), 2)
        self.assertEqual(len(set(tracker["consumedIndices"])), 1)
        self.assertEqual(tracker["quantiles"], ["linear", "linear"])
        self.assertEqual(tracker["indexFileBytes"], 1280000)
        shared = report["familyBootstrapShared"]
        self.assertEqual(shared["indexShape"], [10000, 16])
        self.assertEqual(shared["indexDtype"], "<i8")
        self.assertEqual(shared["familyOrder"], [f"development/f{i:02}" for i in range(16)])
        self.assertEqual(report["comparison"]["fixed"]["bootstrap"], shared)
        self.assertEqual(report["comparison"]["edax"]["bootstrap"], shared)

    def test_incomplete_opponent_has_no_interval_without_erasing_complete_opponent(self):
        code, report, tracker = run_fixture(False)
        self.assertEqual(code, 1)
        self.assertEqual(tracker["tables"], 1)
        self.assertEqual(len(tracker["consumedIndices"]), 1)
        fixed, edax = report["comparison"]["fixed"], report["comparison"]["edax"]
        self.assertEqual(fixed["familyBootstrap95"], [0.5, 0.5])
        self.assertFalse(edax["ciEligible"])
        self.assertIsNone(edax["familyBootstrap95"])
        self.assertIsNone(edax["acceptance"])
        self.assertEqual(edax["unknownGames"], 1)
        self.assertEqual(edax["scoreRateBoundsIncludingUnknown"], [15.5 / 32, 16.5 / 32])
        self.assertEqual(edax["failures"][0]["kind"], "fixture-first-error")


if __name__ == "__main__":
    unittest.main()
