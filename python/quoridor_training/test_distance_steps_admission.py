"""New-fit admission ports only: no arrays, models, corpus or optimizer."""

import builtins
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .common import resolve_config
from .distance_steps import recipe, recipe_sha256, require_main_volume, verify_main_statistics


def write_control(path, value):
    path.write_text(json.dumps(value))
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class FitAdmission(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.config_path = self.root / "config.json"
        write_control(self.config_path, recipe("A", 1))
        self.config = resolve_config(self.config_path)
        self.family_sha = "e" * 64
        self.dataset = {"path": str(self.root / "never-opened-rows.jsonl"), "sha256": "d" * 64}
        self.schedule = write_control(
            self.root / "schedule.json",
            {
                "planned_games": 1,
                "family_partition_sha256": self.family_sha,
            },
        )
        self.statistics = {
            "mu_f32": [0.125, 0.125],
            "sigma_f32": [0.0625, 0.0625],
            "fit_partition": "train",
            "fit_rows": 2,
            "target_independent": True,
            "original_before_reflection": True,
            "distance_input_units": "canonical-integer-D/80",
            "zero_variance_coordinates": [False, False],
            "sigma_floor_f32": 0.0001,
        }
        scale = write_control(self.root / "scale.json", self.statistics)
        constant = write_control(self.root / "constant.json", {"row_mean_constant": 0})
        manifest = write_control(
            self.cache / "cache.json",
            {
                "schema": "quoridor-terminal-geometry-v1",
                "source_binding": self.dataset,
                "schedule_sha256": self.schedule["sha256"],
                "family_partition_sha256": self.family_sha,
            },
        )
        self.common = {
            "scope": "full-volume",
            "human_quantity_N": 1,
            "cache_manifest_sha": manifest["sha256"],
            "dataset": self.dataset,
            "schedule": self.schedule,
            "family_partition_sha256": self.family_sha,
            "recipes_sha256": self.recipe_hashes(),
            "initialization": {
                "seed": 19080311,
                "zero_output_head": True,
                "ordered_parameters_sha256": "a" * 64,
            },
            "scale": scale,
            "constants": {c: constant for c in "ABCD"},
        }
        self.expected = {
            "cache_manifest_sha": manifest["sha256"],
            "initial_weights_sha": "a" * 64,
            "scale_artifact": scale["path"],
            "scale_artifact_sha": scale["sha256"],
            "constant_artifact": constant["path"],
            "constant_artifact_sha": constant["sha256"],
        }
        self.binding_path = self.root / "input-binding.json"
        self.refreeze()

    def recipe_hashes(self):
        result = {}
        for c in "ABCD":
            path = self.root / ("recipe-" + c + ".json")
            write_control(path, recipe(c, 1))
            result[c] = recipe_sha256(resolve_config(path))
        return result

    def refreeze(self):
        common = write_control(self.root / "common.json", self.common)
        permit = write_control(
            self.root / "permit.json",
            {
                "scope": "full-volume",
                "human_quantity_N": 1,
                "planned_games": 1,
                "common_input_freeze": common,
            },
        )
        self.config["experiment"].update(
            main_volume_manifest=permit["path"], main_volume_manifest_sha256=permit["sha256"]
        )
        config = write_control(self.config_path, self.config)
        self.expected.update(
            main_volume_manifest_sha256=permit["sha256"],
            common_input_freeze=common,
            fit_config_sha=config["sha256"],
        )
        write_control(self.binding_path, self.expected)

    def admit(self, **overrides):
        return require_main_volume(
            self.config,
            cache=self.cache,
            config_path=self.config_path,
            input_binding=self.binding_path,
            **overrides,
        )

    def test_actual_direct_and_guarded_N_null_close_all_ports(self):
        original_import = builtins.__import__

        def closed(name, *args, **kwargs):
            if name.split(".")[0] in {"numpy", "torch", "onnxruntime", "ctypes"} or name in {
                "cache",
                "cycle_process",
            }:
                raise AssertionError("numerical/data/child port opened before N")
            return original_import(name, *args, **kwargs)

        write_control(self.config_path, recipe("A"))
        guard = self.root / "guard.json"
        write_control(
            guard,
            {
                "fit_config": str(self.config_path),
                "cache": "closed",
                "output": "closed",
                "expected_files_sha256": {"closed": "0" * 64},
            },
        )
        with patch("builtins.__import__", side_effect=closed):
            from . import train

            with (
                patch.object(train, "sha", side_effect=AssertionError("data hash port")),
                patch.object(train, "load", side_effect=AssertionError("corpus port")),
                patch.object(train, "write", side_effect=AssertionError("output port")),
            ):
                for invoke in (
                    lambda: train.train("closed", "closed", self.config_path),
                    lambda: train.guarded_train(guard),
                ):
                    with self.assertRaisesRegex(ValueError, "unset"):
                        invoke()
        self.assertFalse((self.root / "observed-resources.json").exists())

    def test_matching_binding_returns_exact_control_provenance(self):
        admission = self.admit(supply_workers=2)
        self.assertEqual(admission["statistics"], self.statistics)
        self.assertEqual(
            admission["permit_sha256"], self.config["experiment"]["main_volume_manifest_sha256"]
        )
        verify_main_statistics(admission, copy.deepcopy(self.statistics))
        changed = copy.deepcopy(self.statistics)
        changed["fit_partition"] = "validation"
        with self.assertRaises(ValueError):
            verify_main_statistics(admission, changed)

    def test_unrelated_cache_and_mutated_permit_refuse(self):
        other = self.root / "pilot-cache"
        other.mkdir()
        write_control(other / "cache.json", {"scope": "pilot-only"})
        with self.assertRaises(ValueError):
            require_main_volume(
                self.config,
                cache=other,
                config_path=self.config_path,
                input_binding=self.binding_path,
            )
        (self.root / "permit.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            self.admit()

    def test_missing_binding_unbound_scale_and_worker_override_refuse(self):
        with self.assertRaisesRegex(ValueError, "mandatory"):
            require_main_volume(self.config, cache=self.cache, config_path=self.config_path)
        for kwargs in (
            {"scale_path": self.root / "scale.json"},
            {"supply_workers": 0},
            {"supply_workers": True},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, "overrides"):
                self.admit(**kwargs)

    def test_dataset_schedule_recipe_initial_scale_provenance_refuse(self):
        original_common = copy.deepcopy(self.common)
        for change in (
            lambda c: c["dataset"].update(sha256="b" * 64),
            lambda c: c["schedule"].update(sha256="c" * 64),
            lambda c: c["recipes_sha256"].update(A="f" * 64),
            lambda c: c["initialization"].update(seed=0),
            lambda c: c["initialization"].update(ordered_parameters_sha256="f" * 64),
            lambda c: c.update(family_partition_sha256="f" * 64),
        ):
            self.common = copy.deepcopy(original_common)
            change(self.common)
            self.refreeze()
            with self.assertRaises(ValueError):
                self.admit()
        self.common = copy.deepcopy(original_common)
        invalid_scale = copy.deepcopy(self.statistics)
        invalid_scale["fit_partition"] = "validation"
        scale = write_control(self.root / "scale.json", invalid_scale)
        self.common["scale"] = scale
        self.expected["scale_artifact_sha"] = scale["sha256"]
        self.refreeze()
        with self.assertRaisesRegex(ValueError, "T-only"):
            self.admit()

    def test_actual_train_rejects_overrides_before_any_framework(self):
        from . import train

        original = builtins.__import__

        def closed(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "numpy"}:
                raise AssertionError("framework opened")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=closed):
            for kwargs in ({"scale_path": "closed"}, {"supply_workers": 0}):
                with self.assertRaisesRegex(ValueError, "overrides"):
                    train.train(
                        self.cache,
                        "closed",
                        self.config_path,
                        input_binding=self.binding_path,
                        **kwargs,
                    )

    def test_legacy_gate_retains_legacy_controls(self):
        self.assertIsNone(
            require_main_volume(resolve_config(), scale_path="legacy", supply_workers=0)
        )
        verify_main_statistics(None, {"legacy": True})


if __name__ == "__main__":
    unittest.main()
