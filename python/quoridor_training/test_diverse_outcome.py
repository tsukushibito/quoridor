"""Only changed stock-view/public-only/shared-INITIAL boundaries; real model NN0."""

import copy
from contextlib import ExitStack
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from quoridor_training import common, public_replay as mix, sampling
from quoridor_training import test_mixed_update_observations as related_fixtures
from quoridor_training import test_public_replay as mixture_fixtures

HERE = Path(__file__).resolve().parent

BANDS = [dict(min=a, max=b, rows=8) for a, b in ((16, 20), (8, 15), (1, 7), (0, 0))]
FAKE_ROWS = 0


def config():
    cfg = (
        mixture_fixtures.MixtureBoundaries().settings()
    )  # Metadata fixture only; no old definition run.
    cfg["mixture"].update(train_stock_strata=copy.deepcopy(BANDS), added_sampling_seed=42120261020)
    cfg["mixture"]["selector"]["added_metric"] = "family_mse"
    cfg["evaluation"].update(full_train=False, early_stopping_patience=0)
    return cfg


class DiverseBoundaries(unittest.TestCase):
    def test_stock_view_chronology_games_collision_families_and_V(self):
        # Two games intentionally share one collision family; cap is per game.
        stock = np.array(([20] * 10 + [10] * 10 + [3] * 10 + [0] * 10) * 2 + [20] * 9)
        groups = np.array([0] * 80 + [1] * 9)
        games = np.array([0] * 40 + [1] * 40 + [2] * 9)
        splits = np.array([0] * 80 + [1] * 9)
        eligible = np.ones(89, dtype=bool)
        args = dict(games=games, stock=stock, strata=BANDS)
        view = sampling.family_training_view(groups, splits, eligible, None, **args)
        offsets = [0, 1, 2, 3, 5, 6, 7, 9]
        expected = [base + j for base in range(0, 80, 10) for j in offsets]
        self.assertEqual(view.tolist(), expected)
        self.assertEqual(len(view), 64)
        self.assertTrue(np.array_equal(np.flatnonzero(eligible & (splits == 1)), np.arange(80, 89)))
        # Empty lower-stock strata stay empty; an unknown outcome is never selected.
        small = sampling.family_training_view(
            np.zeros(4, int),
            np.zeros(4, int),
            np.array([True, False, True, True]),
            None,
            games=np.zeros(4, int),
            stock=np.array([20, 20, 20, 20]),
            strata=BANDS,
        )
        self.assertEqual(small.tolist(), [0, 2, 3])
        for bad in (np.array([1] + [0] * 79 + [1] * 9),):
            with self.assertRaises(ValueError):
                sampling.family_training_view(groups, bad, eligible, None, **args)
        with self.assertRaises(ValueError):
            sampling.family_training_view(groups, splits, eligible, 32, **args)
        self.assertEqual(np.flatnonzero(eligible).tolist(), list(range(89)))

    def test_public_only_batch_has_no_added_read_and_preserves_reflection_T(self):
        calls = []
        added = SimpleNamespace(
            row_count=3,
            splits=np.zeros(3, int),
            eligible=np.ones(3, bool),
            batch=lambda *a: self.fail("C must not decode any added training rows"),
        )

        class Public:
            def batch(self, split, indices, mask, training):
                calls.append((split, indices.tolist(), mask.tolist(), training))
                return (
                    np.zeros((len(indices), 2, 312), np.float32),
                    np.zeros((len(indices), 2), np.float32),
                    np.ones(len(indices), np.float32),
                )

        x, d, y = mix.mixed_batch(
            added,
            Public(),
            np.array([], np.int64),
            np.array([1, 1, 2, 0]),
            np.array([True, False, True, False]),
        )
        self.assertEqual((x.shape, d.shape, y.tolist()), ((4, 2, 312), (4, 2), [1] * 4))
        self.assertEqual(calls, [("train", [1, 1, 2, 0], [True, False, True, False], True)])
        with self.assertRaises(ValueError):
            mix.mixed_batch(
                added,
                Public(),
                np.array([], np.int64),
                np.array([], np.int64),
                np.array([], bool),
            )

    def test_configured_C_M_same_updates_scopes_and_complete_work_bound(self):
        cfg = config()
        cfg["training"].update(batch_size=256, threads=2)
        cfg["mixture"].update(added_rows=128, public_rows=128, added_exposures=4)
        cfg["optimizer"]["lr"] = 1e-4
        for R in (1, 32, 1632):
            U = min(64, (4 * R + 127) // 128)
            points = sorted({0, *((k * U + 3) // 4 for k in range(1, 5))})
            cfg["training"].update(steps=U, warmup_steps=min(10, U))
            cfg["evaluation"].update(
                checkpoints=points, diagnostic_checkpoints=points, diagnostic_rows=8192
            )
            common.resolve_config(cfg)
            M = mix.planned_work(
                cfg,
                R,
                123,
                {"train": 8413949, "validation": 419150},
                reuse_initial=True,
            )
            Ccfg = copy.deepcopy(cfg)
            Ccfg["mixture"].update(added_rows=0, public_rows=256)
            common.resolve_config(Ccfg)
            C = mix.planned_work(Ccfg, R, 123, {"train": 8413949, "validation": 419150})
            self.assertEqual((M["updates"], C["updates"]), (U, U))
            self.assertEqual(M["added_rows"], 128 * U)
            self.assertLess(128 * U, 4 * R + 128)
            self.assertEqual((C["added_rows"], C["public_rows"]), (0, 256 * U))
            self.assertEqual(C["observation_steps"], points)
            self.assertEqual(M["measurement_rows_by_step"][0], 0)
            self.assertLess(C["forward_upper"] + M["forward_upper"], 6000000)
            self.assertEqual(Ccfg["experiment"]["warm_start"], cfg["experiment"]["warm_start"])
        bad = copy.deepcopy(cfg)
        bad["mixture"]["train_stock_strata"][0]["min"] = 15
        with self.assertRaises(ValueError):
            common.resolve_config(bad)
        with self.assertRaises(ValueError):
            mix.planned_work(cfg, 0, 1, {"train": 2, "validation": 2})

    def run_fake(self, cfg, out, binding=None, *, stratified=False):
        global FAKE_ROWS
        fixture = related_fixtures.RelatedBoundaries().fixtures()  # Reuse fakes, not any old tests.
        cfg["training"].update(steps=2, batch_size=8, warmup_steps=2)
        cfg["evaluation"].update(
            checkpoints=[0, 1, 2],
            diagnostic_checkpoints=None,
            diagnostic_rows=2,
            full_train=False,
            full_train_checkpoints=[],
            early_stopping_patience=0,
        )
        cfg["mixture"].update(added_exposures=10)
        if not stratified:
            cfg["mixture"]["train_stock_strata"] = None
        cfg["mixture"]["selector"].update(added_metric="family_mse")
        source = out.parent / (out.name + "-config.json")
        source.write_text(json.dumps(cfg))
        with ExitStack() as stack:
            for item in fixture.patches:
                stack.enter_context(item)
            terminal = sys.modules["quoridor_training.terminal_cache"]
            original_ctor = terminal.TerminalCorpus

            def shaped(*args):
                corpus = original_ctor(*args)
                corpus.groups = np.array([0] * 5 + [1, 2, 2])
                corpus.families = ["synthetic-T", "singleton-V", "double-V"]
                corpus.labels = corpus.labels.copy()
                corpus.labels[6:, 1] = 0
                corpus.row_game_codes = np.array([0] * 5 + [1, 2, 2])
                geometry = np.zeros(8, dtype=[("stocks", "u1", (2,))])
                geometry["stocks"] = [
                    [10, 10],
                    [10, 10],
                    [5, 5],
                    [1, 1],
                    [0, 0],
                    [10, 10],
                    [4, 3],
                    [0, 0],
                ]
                corpus.maps = [{"geometry": geometry}]
                return corpus

            stack.enter_context(patch.object(terminal, "TerminalCorpus", shaped))
            value = mix.train_mixture("synthetic", out, source, binding, cfg)
        FAKE_ROWS += sum(c[1] for c in fixture.calls if c[0] == "fake_forward_rows")
        return fixture, value

    def test_C_M_actual_owner_shared_initial_exact_scope_and_counts_NN0(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            tmp = Path(tmp)
            Ccfg = config()
            Ccfg["mixture"].update(added_rows=0, public_rows=8)
            c, C = self.run_fake(Ccfg, tmp / "C")
            initial = tmp / "C/initial-observation.json"
            raw = initial.read_bytes()
            ref = {
                "path": str(initial),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "mode": f"{initial.stat().st_mode & 0o777:04o}",
            }
            binding = tmp / "binding.json"
            binding.write_text(json.dumps({"files": {"initial_observation": ref}}))
            Mcfg = config()
            Mcfg["mixture"].update(added_rows=4, public_rows=4)
            m, M = self.run_fake(Mcfg, tmp / "M", binding)
            self.assertEqual((C["step"], M["step"], C["added_seen"], M["added_seen"]), (2, 2, 0, 8))
            self.assertEqual((C["training_forwards"], M["training_forwards"]), (16, 16))
            self.assertEqual((C["measurement_forwards"], M["measurement_forwards"]), (30, 20))
            self.assertEqual((C["forward_rows"], M["forward_rows"]), (46, 36))
            self.assertEqual(M["curves"][0]["scopes"], C["curves"][0]["scopes"])
            self.assertEqual(M["curves"][0]["reused_initial_observation"], ref)
            self.assertEqual(M["curves"][0]["scopes"]["added_validation"]["family_mse"], 0.5)
            self.assertAlmostEqual(M["curves"][0]["scopes"]["added_validation"]["mse"], 1 / 3)
            self.assertEqual(len(M["curves"][0]["scopes"]["public_validation"]["calibration"]), 10)
            self.assertEqual((C["last_checkpoint_step"], M["last_checkpoint_step"]), (2, 2))
            for name in ("C", "M"):
                data = np.load(tmp / name / "exposure.npz")
                self.assertEqual(int(data["added_visits"].sum()), 0 if name == "C" else 8)
                self.assertFalse((tmp / name / "INCOMPLETE").exists())
            cr = np.random.default_rng(Ccfg["mixture"]["public_sampling_seed"]).integers(7, size=16)
            mr = np.random.default_rng(Mcfg["mixture"]["public_sampling_seed"]).integers(7, size=8)
            self.assertTrue(np.array_equal(cr[:8], mr))
            # A changed INITIAL scope refuses before a fake model call, with marker/cleanup.
            wrong = json.loads(raw)
            wrong["binding"]["evaluation_batch_size"] += 1
            other = tmp / "bad-initial.json"
            other.write_text(json.dumps(wrong))
            b = other.read_bytes()
            badref = {
                "path": str(other),
                "sha256": hashlib.sha256(b).hexdigest(),
                "bytes": len(b),
                "mode": "0644",
            }
            binding.write_text(json.dumps({"files": {"initial_observation": badref}}))
            with self.assertRaisesRegex(ValueError, "shared INITIAL exact"):
                self.run_fake(Mcfg, tmp / "refused", binding)
            partial = json.loads((tmp / "refused/training.json").read_bytes())
            self.assertEqual(partial["forward_rows"], 0)
            self.assertTrue((tmp / "refused/INCOMPLETE").exists())

    def test_stratified_owner_path_saves_view_and_V_stock_metrics_NN0(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            cfg = config()
            cfg["mixture"].update(
                added_rows=4,
                public_rows=4,
                train_stock_strata=[{**b, "rows": 1} for b in BANDS],
            )
            output = Path(tmp) / "stock-entry"
            fixture, result = self.run_fake(cfg, output, stratified=True)
            view = json.loads((output / "training-view.json").read_bytes())
            self.assertEqual(view["indices"], [0, 2, 3, 4])
            self.assertEqual(result["training_view_rows"], 4)
            self.assertEqual(result["validation_rows"], 3)
            banks = result["curves"][0]["scopes"]["added_validation"]["stock_strata"]
            self.assertEqual(
                [banks[f"{b['min']}..{b['max']}"]["rows"] for b in BANDS], [1, 0, 1, 1]
            )
            self.assertIsNone(banks["8..15"]["mse"])
            self.assertEqual(sum(b["rows"] for b in banks.values()), 3)
            self.assertEqual(result["added_seen"], 8)
            visits = np.load(output / "exposure.npz")["added_visits"]
            self.assertEqual(visits.tolist(), [2, 0, 2, 2, 2, 0, 0, 0])
            self.assertEqual(result["selection"]["added_metric"], "family_mse")
            self.assertEqual(result["learning_rates"], [0.0005, 0.001])

    def test_actual_cache_dependent_pair_settings_and_6M_limit_NN0(self):
        spec = importlib.util.spec_from_file_location("prepare421", HERE / "prepare-configs.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        template = json.loads((HERE / "settings.SELECTED.json").read_bytes())
        C_M, plans = helper.resolved_pair(
            template, 2048, 12800, {"train": 8413949, "validation": 419150}
        )
        self.assertEqual((plans["C"]["updates"], plans["M"]["updates"]), (64, 64))
        self.assertEqual(plans["C"]["selector_steps"], [0, 16, 32, 48, 64])
        self.assertEqual(sum(p["forward_upper"] for p in plans.values()) + 1024, 4013502)
        self.assertEqual(C_M["C"]["training"]["warmup_steps"], 10)
        self.assertEqual(C_M["C"]["experiment"]["warm_start"], C_M["M"]["experiment"]["warm_start"])
        self.assertEqual(C_M["M"]["mixture"]["added_sampling_seed"], 42120261020)
        self.assertEqual(C_M["C"]["training"]["seed"], 42120261017)
        self.assertEqual(C_M["M"]["mixture"]["diagnostic_seed"], 42120261022)
        small, _ = helper.resolved_pair(template, 1, 1, {"train": 8413949, "validation": 419150})
        self.assertEqual(
            (small["C"]["training"]["steps"], small["C"]["training"]["warmup_steps"]),
            (1, 1),
        )
        with self.assertRaises(ValueError):
            helper.resolved_pair(template, 0, 1, {"train": 2, "validation": 2})
        with self.assertRaises(ValueError):
            helper.resolved_pair(template, 1, 0, {"train": 2, "validation": 2})

    def test_draw_observation_semantics_from_same_fake_outputs_NN0(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            cfg = config()
            cfg["mixture"].update(added_rows=0, public_rows=8)
            fixture, result = self.run_fake(cfg, Path(tmp) / "draw-observation")
            V = result["curves"][1]["scopes"]["added_validation"]
            self.assertEqual((V["rows"], V["sign_rows"], V["draw_rows"]), (3, 1, 2))
            self.assertEqual(V["draw_mean_absolute_value"], 0.25)
            self.assertEqual(V["sign_accuracy"], 1.0)
            P = result["curves"][1]["scopes"]["public_validation"]
            self.assertEqual(P["draw_rows"], 0)
            self.assertIsNone(P["draw_mean_absolute_value"])
            self.assertEqual(result["forward_rows"], 46)


if __name__ == "__main__":
    result = unittest.main(exit=False).result
    print(
        json.dumps(
            {
                "actual_model_forwards": 0,
                "fake_forward_rows": FAKE_ROWS,
                "real_Torch_imported": "torch" in sys.modules,
            }
        )
    )

    raise SystemExit(not result.wasSuccessful())
