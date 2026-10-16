"""Only new configurable sampler/initialization/observation boundaries; real NN0."""

from copy import deepcopy
from contextlib import ExitStack
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from quoridor_training import common, public_replay as mix, sampling
from quoridor_training import test_mixed_update_observations as fixture_module
from quoridor_training import test_cache_scale_binding as scale_fixtures

HERE = Path(__file__).resolve().parent
FAKE_ROWS = 0


def toy_config():
    # Existing selected metadata is a shape fixture, not new scientific settings.
    saved = HERE.parent / "nnue-diverse421-learning-v1/settings.SELECTED.json"
    cfg = deepcopy(json.loads(saved.read_bytes())["C"])
    cfg["training"].update(steps=2, warmup_steps=1, batch_size=4)
    cfg["evaluation"].update(checkpoints=[0, 1, 2], diagnostic_checkpoints=None, diagnostic_rows=2)
    cfg["mixture"].update(
        added_rows=4,
        public_rows=0,
        added_exposures=8,
        public_file_decay=None,
        public_evaluation={"validation": "best", "train_diagnostic": False},
    )
    cfg["limits"]["samples"] = 1000
    return cfg


class ScriptedRng:
    def __init__(self, rows, uniforms=()):
        self.rows = iter(rows)
        self.uniforms = iter(uniforms)
        self.calls = []

    def integers(self, upper, size):
        result = next(self.rows)
        assert len(result) == size
        self.calls.append(("indices", upper, size))
        return result

    def random(self, size):
        result = next(self.uniforms)
        assert len(result) == size
        self.calls.append(("accept", size))
        return result


class TeacherRefreshInputsNN0(unittest.TestCase):
    def test_spec_bound_exact_tail_configs_and_whole_cost_refuse_pilot_only(self):
        location = importlib.util.spec_from_file_location("prepare423", HERE / "prepare-configs.py")
        helper = importlib.util.module_from_spec(location)
        location.loader.exec_module(helper)
        refs = json.loads((HERE / "fixed-spec-refs.json").read_bytes())
        spec = json.loads(common.bound_file_bytes(refs["spec.json"], 65536))
        base = json.loads(
            (HERE.parent / "nnue-diverse421-learning-v1/settings.SELECTED.json").read_bytes()
        )["C"]
        with self.assertRaisesRegex(ValueError, "pilot is not the main study"):
            helper.resolved_four(
                base,
                spec,
                800,
                100,
                {"train": 8413949, "validation": 419150},
                final_scale_fixed=False,
            )
        for rows in (1, 513, 8192):
            configs, plans = helper.resolved_four(
                base,
                spec,
                rows,
                51200,
                {"train": 8413949, "validation": 419150},
                final_scale_fixed=True,
            )
            expected = min(8 * rows, 32768)
            fresh_rows = min(64 * rows, 524288)
            for arm in ("U", "R", "W"):
                self.assertEqual(plans[arm]["training_forwards"], expected)
                self.assertEqual(plans[arm]["updates"], (expected + 255) // 256)
                self.assertEqual(configs[arm]["training"]["seed"], 42320261020)
                self.assertEqual(
                    configs[arm]["training"]["warmup_steps"], min(10, plans[arm]["updates"])
                )
            self.assertEqual(plans["F"]["training_forwards"], fresh_rows)
            self.assertEqual(configs["F"]["training"]["seed"], 42320261021)
            self.assertEqual(configs["F"]["mixture"]["public_rows"], 0)
            self.assertIsNone(configs["F"]["experiment"]["warm_start"]["weights"])
            self.assertEqual(configs["R"]["mixture"]["public_acceptance_seed"], 42320261028)
            self.assertEqual(
                configs["R"]["mixture"]["public_sampling_seed"],
                configs["U"]["mixture"]["public_sampling_seed"],
            )
            self.assertTrue(all(len(p["observation_steps"]) <= 4 for p in plans.values()))
            if rows == 8192:
                self.assertEqual(sum(p["forward_upper"] for p in plans.values()) + 1024, 3381560)
        with self.assertRaises(ValueError):
            helper.resolved_four(
                base, spec, 0, 2, {"train": 2, "validation": 2}, final_scale_fixed=True
            )

    def test_fresh_admit_binds_normalization_but_refuses_any_weight_alias_or_foreign_INITIAL_before_read(
        self,
    ):
        with scale_fixtures.fixture() as (_, _, _, authority, original, admit, _, read):
            warm = {
                "descriptor": original["files"]["descriptor"],
                "weights": None,
                "evaluator_sha256": None,
            }
            inputs = {
                "warm_start": warm,
                "statistics": {"fixture": "frozen"},
                "scale_authority": authority,
            }
            fresh_binding = deepcopy(original)
            del fresh_binding["files"]["weights"]
            with patch.object(mix, "warmstart_model_inputs", return_value=inputs):
                result = admit(fresh_binding)
                self.assertIsNone(result[3]["warm_start"]["weights"])
                self.assertNotIn(original["files"]["weights"], read)
                for key in ("weights", "renamed_weights", "initial_observation"):
                    bad = deepcopy(fresh_binding)
                    bad["files"][key] = original["files"]["weights"]
                    read.clear()
                    with self.assertRaisesRegex(ValueError, "fresh initialization binds only"):
                        admit(bad)
                    self.assertEqual(read, [], "refusal must precede any candidate file body read")
                bad = deepcopy(fresh_binding)
                bad["files"]["descriptor"] = original["files"]["weights"]
                read.clear()
                with self.assertRaises(ValueError):
                    admit(bad)
                self.assertEqual(read, [])

    def test_file_order_weights_indexed_T_only_and_neutral_equivalence(self):
        calls = []

        def records(split, rows, training):
            calls.append((split, rows, training))
            return {"shard": rows}

        corpus = SimpleNamespace(manifest={"source_shards": [{}, {}]}, records=records)
        rng = ScriptedRng([[0, 1], [0]])
        acceptance = ScriptedRng([], [[0.75, 0.99], [0.25]])
        checks = []
        indices, facts = sampling.indexed_public_sample(
            corpus, rng, 2, 2, 0.5, lambda: checks.append(1), acceptance_rng=acceptance
        )
        self.assertEqual(indices, [1, 0])
        self.assertEqual(facts, {"candidate_rows": 3, "accepted_by_file": [1, 1]})
        self.assertEqual(calls, [("train", [0, 1], True), ("train", [0], True)])
        self.assertEqual(len(checks), 2)
        # File index is zero based; first of 43 gets .92**42, last gets 1.
        corpus.manifest = {"source_shards": [{}] * 43}
        rng = ScriptedRng([[0, 42], [0]])
        acceptance = ScriptedRng([], [[0.92**42 + 0.01, 0.99], [0.92**42 / 2]])
        got, facts = sampling.indexed_public_sample(
            corpus, rng, 2, 43, 0.92, lambda: None, acceptance_rng=acceptance
        )
        self.assertEqual(got, [42, 0])
        self.assertEqual(facts["accepted_by_file"][0], 1)
        for decay in (None, 1):
            rng = ScriptedRng([[1, 0]])
            result, facts = sampling.indexed_public_sample(None, rng, 2, 2, decay, lambda: None)
            self.assertEqual(result, [1, 0])
            self.assertEqual(rng.calls, [("indices", 2, 2)])

    def test_weighted_selection_cancel_or_invalid_weights_never_fall_back(self):
        original = RuntimeError("synthetic cancellation before input draw")

        def cancel():
            raise original

        corpus = SimpleNamespace(manifest={"source_shards": [{}, {}]})
        rng = ScriptedRng([])
        with self.assertRaises(RuntimeError) as caught:
            sampling.indexed_public_sample(
                corpus, rng, 1, 2, 0.92, cancel, acceptance_rng=ScriptedRng([])
            )
        self.assertIs(caught.exception, original)
        self.assertEqual(rng.calls, [])
        for bad in (False, 0, -1, float("nan"), 2):
            with self.assertRaises(ValueError):
                sampling.indexed_public_sample(corpus, rng, 1, 2, bad, lambda: None)

    def test_explicit_fresh_config_and_descriptor_only_statistics(self):
        cfg = toy_config()
        warm = cfg["experiment"]["warm_start"]
        warm.update(weights=None, evaluator_sha256=None)
        normalized = common.resolve_config(cfg)
        self.assertIsNone(normalized["experiment"]["warm_start"]["weights"])
        descriptor = {
            "weights_SHA": common.BEST43_WEIGHTS,
            "weights_B": 49284,
            "little_endian_f32": 12321,
            "schema": "quoridor-nnue-distance-residual-v3",
            "feature": "QF1-route4-f32-STM-scaled-residual-v3",
            "dense_feature_version": "shortest-dag4-f32-STM-v1",
            "topology": {"ft_width": 32, "hidden_width": 32},
            "distance_fit": {"a": 0, "b": 0},
            "route_mode": "zero4",
            "route_mu_f32": [0.0] * 4,
            "route_sigma_f32": [1.0] * 4,
            "value_perspective": "side-to-move",
            "value_parameterization": "fixed-distance-logit-plus-linear-residual-tanh",
        }
        statistics = {"fixture": "unchanged frozen descriptor statistics"}
        scale = ModuleType("quoridor_training.scaled_model")
        scale.validate_statistics = lambda value: statistics
        read = []

        def fake_bound(ref, limit):
            read.append(ref)
            self.assertEqual(ref, warm["descriptor"])
            return json.dumps(descriptor).encode()

        with (
            patch.dict(sys.modules, {scale.__name__: scale}),
            patch.object(common, "bound_file_bytes", fake_bound),
        ):
            value = common.warmstart_model_inputs(normalized)
        self.assertEqual(read, [warm["descriptor"]])
        self.assertIs(value["statistics"], statistics)
        self.assertTrue(value["fresh_initialization"])
        self.assertEqual(value["scale_authority"]["starting_weights_sha256"], common.BEST43_WEIGHTS)
        self.assertIsNone(value["warm_start"]["weights"])
        bad = deepcopy(cfg)
        bad["experiment"]["warm_start"]["evaluator_sha256"] = common.BEST43_EVALUATOR
        with self.assertRaises(ValueError):
            common.resolve_config(bad)
        self.assertNotIn("torch", sys.modules)

    def test_best_only_observation_bound_and_earliest_ties_without_public_selector(self):
        cfg = toy_config()
        plan = mix.planned_work(cfg, 5, 3, {"train": 7, "validation": 11})
        self.assertEqual(
            plan["scopes_by_step"],
            {
                0: ["added_validation", "added_train"],
                1: ["added_validation", "added_train"],
                2: ["added_validation", "added_train"],
            },
        )
        self.assertEqual(plan["measurement_forwards"], 3 * (3 + 2) + 11)
        self.assertEqual(plan["forward_upper"], 8 + 15 + 11)
        reused = mix.planned_work(cfg, 5, 3, {"train": 7, "validation": 11}, reuse_initial=True)
        self.assertEqual(reused["forward_upper"], plan["forward_upper"] - 5)
        tail = deepcopy(cfg)
        tail["mixture"]["training_rows"] = 7
        shortened = mix.planned_work(tail, 5, 3, {"train": 7, "validation": 11})
        self.assertEqual(
            (shortened["training_forwards"], shortened["added_rows"], shortened["updates"]),
            (7, 7, 2),
        )
        self.assertEqual(shortened["forward_upper"], plan["forward_upper"] - 1)
        selector = mix.Selector(False, 0, 0.0, 0.0)
        self.assertEqual(selector.observe(0, 1.0, None), (False, False))
        self.assertEqual(selector.observe(1, 0.5, None), (True, False))
        self.assertEqual(selector.observe(2, 0.5, None), (False, False))
        self.assertEqual(selector.best_step, 1)
        cfg["mixture"]["selector"]["public_non_regression"] = True
        with self.assertRaises(ValueError):
            common.resolve_config(cfg)

    def test_shared_initial_subset_requires_same_model_scale_rows_and_needed_constants(self):
        binding = {
            "warm_start": {"fixture": "same model"},
            "statistics": {"scale": "frozen"},
            "cache_manifest_sha256": "a" * 64,
            "public_membership": {"fixture": "same bank"},
            "scopes": {"added_validation": {"rows": 3, "index_sha256": "b" * 64}},
            "constants": {"added": 0.5, "public": None},
        }
        full = deepcopy(binding)
        full["scopes"]["public_train"] = {"rows": 2, "index_sha256": "c" * 64}
        full["constants"]["public"] = 1.0
        saved = {
            "binding": full,
            "scopes": {
                "added_validation": {"rows": 3, "mse": 0.2},
                "public_train": {"rows": 2, "mse": 0.4},
            },
        }
        original = deepcopy(saved)
        reused = mix.initial_observation_scopes(saved, binding)
        self.assertEqual(reused, {"added_validation": saved["scopes"]["added_validation"]})
        for key in ("warm_start", "statistics", "cache_manifest_sha256", "scopes"):
            bad = deepcopy(binding)
            bad[key] = {"drift": True} if key != "cache_manifest_sha256" else "f" * 64
            with self.assertRaises(ValueError):
                mix.initial_observation_scopes(saved, bad)
        self.assertEqual(saved, original)

    def run_fresh_fake(self, output, public_error=None, *, games=False):
        """New owner path using existing fake primitives, never an old test method."""
        global FAKE_ROWS
        import numpy as np
        from quoridor_training import train

        fixture = fixture_module.RelatedBoundaries().fixtures()
        cfg = fixture.config
        cfg["training"].update(steps=2, batch_size=4, warmup_steps=1)
        cfg["evaluation"].update(
            checkpoints=[0, 1, 2],
            diagnostic_checkpoints=None,
            full_train=False,
            full_train_checkpoints=[],
            diagnostic_rows=2,
            early_stopping_patience=0,
        )
        cfg["mixture"].update(
            added_rows=4,
            public_rows=0,
            added_exposures=10,
            train_stock_strata=None,
            public_file_decay=None,
            public_evaluation={"validation": "best", "train_diagnostic": False},
            training_rows=7,
        )
        cfg["mixture"]["selector"].update(public_non_regression=False, added_metric="mse")
        cfg["experiment"]["warm_start"].update(weights=None, evaluator_sha256=None)
        fixture.warm.update(weights=None, evaluator_sha256=None)
        config_path = output.parent / (output.name + "-config.json")
        config_path.write_text(json.dumps(cfg))
        exports, restores, public_reads, models = [], [], [], []
        with ExitStack() as stack:
            for item in fixture.patches:
                stack.enter_context(item)
            terminal = sys.modules["quoridor_training.terminal_cache"]
            compact = sys.modules["quoridor_training.compact_cache"]
            original_added = terminal.TerminalCorpus
            original_public = compact.IndexedPublicCorpus
            fake_torch = sys.modules["torch"]

            def added(*args):
                corpus = original_added(*args)
                corpus.labels = corpus.labels.copy()
                corpus.labels[corpus.splits == 1, 1] = 0
                if games:
                    corpus.row_game_codes = np.array([0] * 5 + [1] * 3)
                return corpus

            class Public:
                def __init__(self, *args):
                    self.inner = original_public(*args)

                def batch(self, split, indices, *args, **kwargs):
                    self_outer.assertEqual(split, "validation", "F must not read public T labels")
                    public_reads.append((split, len(indices)))
                    if public_error is not None:
                        raise public_error
                    return self.inner.batch(split, indices, *args, **kwargs)

                def __getattr__(self, name):
                    return getattr(self.inner, name)

            class FrozenInitial:
                def to(self, device):
                    return self

                def eval(self):
                    return self

                def __call__(self, *inputs):
                    rows = inputs[0].shape[0]
                    fixture.calls.append(("fake_forward_rows", rows))
                    return fake_torch.from_numpy(np.zeros(rows, np.float32))

            def build(*args):
                model = fixture.model if not models else FrozenInitial()
                models.append(model)
                return model

            def restore(model, weights):
                self.assertIs(model, models[1])
                self.assertIn("initial-model", weights["path"])
                restores.append((model, weights))

            def export(model, cfg, statistics, fit, path):
                self.assertIs(model, fixture.model, "LAST must remain the live completed state")
                exports.append(path.name)
                path.mkdir(parents=True)
                payload = np.array([0.0 if path.name == "initial-model" else 0.5], "<f4").tobytes()
                (path / "weights.f32").write_bytes(payload)
                descriptor = path / "manifest.json"
                descriptor.write_text(
                    json.dumps(
                        {
                            "fixture": "one scalar, NOT NNUE weights",
                            "weights": "weights.f32",
                            "weights_SHA": hashlib.sha256(payload).hexdigest(),
                            "weights_B": len(payload),
                        }
                    )
                )
                return descriptor

            self_outer = self
            stack.enter_context(patch.object(terminal, "TerminalCorpus", added))
            stack.enter_context(patch.object(compact, "IndexedPublicCorpus", Public))
            stack.enter_context(patch.object(train, "build_model", build))
            stack.enter_context(patch.object(train, "restore_warmstart_parameters", restore))
            stack.enter_context(
                patch.object(
                    train,
                    "verify_native_parameters",
                    side_effect=AssertionError("fresh F must not verify trained weights"),
                )
            )
            stack.enter_context(patch.object(train, "export", export))
            try:
                result = mix.train_mixture("synthetic", output, config_path, None, cfg)
            except BaseException as error:
                result = json.loads((output / "training.json").read_bytes())
                return fixture, result, exports, restores, public_reads, models, error
            finally:
                FAKE_ROWS += sum(c[1] for c in fixture.calls if c[0] == "fake_forward_rows")
        return fixture, result, exports, restores, public_reads, models, None

    def test_fresh_owner_no_public_T_initial_export_best_once_and_live_LAST_nn0(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            output = Path(directory) / "fresh"
            _, result, exports, restores, public_reads, models, error = self.run_fresh_fake(output)
            if error is not None:
                raise error
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual((result["step"], result["last_checkpoint_step"]), (2, 2))
            self.assertEqual(result["last_checkpoint_state"], "VERIFIED_COMPLETED_UPDATE")
            self.assertEqual(result["best_step"], 0)
            self.assertEqual(exports, ["initial-model", "last-model"])
            self.assertEqual(len(restores), 1)
            self.assertIsNot(models[0], models[1])
            self.assertEqual(public_reads, [("validation", 3)])
            self.assertEqual(result["constants"]["public_T_diagnostic"], None)
            self.assertEqual(result["plan"]["frozen_best_public_validation_rows"], 3)
            self.assertEqual(result["measurement_forwards"], 3 * (3 + 2) + 3)
            self.assertEqual((result["training_forwards"], result["added_seen"]), (7, 7))
            self.assertGreater(result["curves"][2]["scopes"]["added_validation"]["mse"], 0)
            self.assertFalse((output / "INCOMPLETE").exists())

    def test_frozen_best_observation_error_keeps_original_primary_verified_LAST_and_partial_nn0(
        self,
    ):
        original = RuntimeError("new synthetic frozen BEST public monitor failure")
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            output = Path(directory) / "monitor-failure"
            _, result, exports, restores, public_reads, _, error = self.run_fresh_fake(
                output, original
            )
            self.assertIs(error, original)
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual((result["step"], result["last_checkpoint_step"]), (2, 2))
            self.assertEqual(result["last_checkpoint_state"], "VERIFIED_COMPLETED_UPDATE")
            self.assertEqual(exports[-1], "last-model")
            self.assertEqual(len(restores), 1)
            self.assertEqual(public_reads, [("validation", 3)])
            self.assertTrue((output / "INCOMPLETE").exists())
        self.assertNotIn("torch", sys.modules)

    def test_same_prediction_game_code_and_raw_value_calibration_sufficient_for_prefix_join_nn0(
        self,
    ):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            output = Path(directory) / "game-stats"
            _, result, _, _, _, _, error = self.run_fresh_fake(output, games=True)
            if error is not None:
                raise error
            initial = result["curves"][0]["scopes"]["added_validation"]
            last = result["curves"][2]["scopes"]["added_validation"]
            self.assertEqual(initial["game_key_kind"], "TerminalCorpus.row_game_codes")
            self.assertEqual(
                initial["games"]["1"],
                {
                    "rows": 3,
                    "sse": 0.0,
                    "mse": 0.0,
                    "sign_rows": 0,
                    "correct_sign_rows": 0,
                    "prediction_sum": 0.0,
                    "target_sum": 0.0,
                },
            )
            self.assertEqual(last["games"]["1"]["sse"], 0.75)
            occupied = [b for b in last["calibration"] if b["rows"]]
            self.assertEqual(len(occupied), 1)
            self.assertEqual((occupied[0]["mean_value"], occupied[0]["mean_z"]), (0.5, 0.0))
            self.assertEqual((result["training_forwards"], result["measurement_forwards"]), (7, 18))


if __name__ == "__main__":
    unittest.main()
