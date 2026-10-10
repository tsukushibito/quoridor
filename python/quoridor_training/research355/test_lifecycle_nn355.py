"""Actual saved config metadata exercises only the affected NN guard boundary."""

import copy
from pathlib import Path
import unittest

import lifecycle355 as life


class SavedNNConfigGuard(unittest.TestCase):
    def test_saved_best43_config_and_manifest_owned_fit(self):
        root = Path(
            "/workspaces/quoridor/.worktree/value-search-strength-arena355/.artifacts/"
            "value-search-strength355/maintained-build-v1"
        )
        config_ref = {
            "path": str(root / "campaign-materialization-v1/data/batch-01.json"),
            "sha256": "e32e31e7670d59ed5273c7898b484e0b50eb08144daf51f5b34d27d088b29e6f",
            "bytes": 14419,
            "mode": "0644",
        }
        experiment_ref = {
            "path": str(root / "campaign-arena-v1/batch-01/controls-v1/experiment.json"),
            "sha256": "c53338fe4760832cd6f9df4f3db534c42c5852964721c0d5cecc6246592d10dd",
            "bytes": 4664,
            "mode": "0644",
        }
        metadata = life.Metadata()
        config = metadata.read(config_ref)
        experiment = metadata.read(experiment_ref)
        self.assertEqual(experiment["config"], config_ref)
        self.assertEqual(config["engines"][0]["distance_b"], 8)
        self.assertEqual(experiment["models"][0]["descriptor"]["sha256"], life.MODELS[1][0])
        self.assertEqual(experiment["models"][0]["weights"]["sha256"], life.MODELS[1][1])
        self.assertEqual(experiment["models"][0]["evaluator_sha256"], life.MODELS[1][2])

        def guard(value, phase):
            # Current separate canonical protections remain, not a new validator.
            life.models(phase)
            life.arena_clock(value)
            life.arena_conditions(value, phase)

        guard(config, experiment)
        for a, b in ((0, 0), (-2, 8), (1.5, -0.25)):
            with self.subTest(case="ignored_raw_NN_knobs", a=a, b=b):
                variant = copy.deepcopy(config)
                variant["engines"][0].update(distance_a=a, distance_b=b)
                guard(variant, experiment)
        # These variants exercise guard units, never claim hash-bound phase
        # admission or mutate the immutable original config/Experiment.
        changes = (
            ("NN_kind", ("engines", 0, "kind"), "distance"),
            ("NN_path", ("engines", 0, "model"), "/synthetic/wrong-model.json"),
            ("D_kind", ("engines", 1, "kind"), "nnue"),
            ("D_a", ("engines", 1, "distance_a"), 1),
            ("D_b", ("engines", 1, "distance_b"), 0),
            ("D_model", ("engines", 1, "model"), "/synthetic/forbidden-model.json"),
            ("rules", ("ruleset",), "wrong_rules"),
            ("backend", ("inference",), {}),
            ("backend_core", ("inference_cpu_core",), 0),
            ("clock", ("engines", 0, "time_ms"), 101),
            ("reserve", ("arena", "return_reserve_ms"), 4),
            ("clock_policy", ("arena", "clock_policy"), "wrong_policy"),
            ("comparison", ("arena", "comparison"), "wrong_domain"),
            ("depth", ("engines", 0, "depth"), 63),
            ("nodes", ("engines", 1, "max_nodes"), 999999),
            ("TT", ("arena", "tt_entries"), 8192),
        )
        for name, keys, value in changes:
            with self.subTest(case=name):
                variant = copy.deepcopy(config)
                target = variant
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.assertRaises(ValueError):
                    guard(variant, experiment)
        for key in ("descriptor", "weights", "evaluator_sha256"):
            with self.subTest(case="current_model_identity", key=key):
                phase = copy.deepcopy(experiment)
                if key == "evaluator_sha256":
                    phase["models"][0][key] = "f" * 64
                else:
                    phase["models"][0][key]["sha256"] = "f" * 64
                with self.assertRaisesRegex(
                    ValueError, "fixed models, scale and evaluator identities"
                ):
                    guard(config, phase)
        for batch in (0, 16):
            with self.subTest(case="batch_identity", batch=batch):
                phase = copy.deepcopy(experiment)
                phase["batch"] = batch
                with self.assertRaises(ValueError):
                    guard(config, phase)
        metadata.after()
        self.assertEqual(set(metadata.seen), {config_ref["path"], experiment_ref["path"]})


if __name__ == "__main__":
    unittest.main()
