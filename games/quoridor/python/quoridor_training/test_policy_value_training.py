"""New zero-head tests for explicit joint settings and same-run restart metadata."""

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from .policy_value_training import (
    settings,
    checkpoint_identity,
    read_restart,
    export_joint,
)


def configuration():
    return {
        "policy_value": {
            "value_weight": 1.0,
            "policy_weight": 1.0,
            "temperature": 1.0,
            "initial_head": "synthetic_untrained",
            "freeze": "none",
            "selector": "joint_loss",
            "checkpoint_bytes": 4 * 1024**2,
        },
        "training": {
            "target": "static_teacher",
            "supply_workers": 0,
            "steps": 2,
            "seed": 187,
        },
        "evaluation": {"diagnostic_checkpoints": []},
        "artifacts": {"checkpoint_steps": []},
        "static_teacher": {"state_checkpoint_steps": [], "initializer_seed": 187},
    }


class _Tensor:
    dtype = "float32"

    def __init__(self, shape, finite=True):
        self.shape, self.finite = shape, finite


class PolicyValueMetadata(unittest.TestCase):
    def test_explicit_weights_temperature_and_unused_options_nn0(self):
        cfg = configuration()
        self.assertEqual(settings(cfg)["freeze"], "none")
        for name, bad in (
            ("value_weight", -1),
            ("value_weight", True),
            ("policy_weight", 0),
            ("temperature", 0),
            ("temperature", float("inf")),
            ("freeze", "value_linear_compat"),
        ):
            changed = copy.deepcopy(cfg)
            changed["policy_value"][name] = bad
            with self.subTest(name=name, bad=bad), self.assertRaises(ValueError):
                settings(changed)
        for section, name, bad in (
            ("training", "target", "z"),
            ("training", "supply_workers", 2),
            ("artifacts", "checkpoint_steps", [1]),
            ("evaluation", "diagnostic_checkpoints", [1]),
        ):
            changed = copy.deepcopy(cfg)
            changed[section][name] = bad
            with self.assertRaises(ValueError):
                settings(changed)

    def fixture(self, directory):
        cfg = configuration()
        corpus = types.SimpleNamespace(binding={"dataset_sha": "synthetic-metadata-only"})
        joint = {
            "settings": cfg["policy_value"],
            "initial_shared_fingerprint": "1" * 64,
            "binding": {
                "initial_model": {"descriptor": "synthetic", "weights": "synthetic"},
                "initial_policy": None,
                "restart": None,
            },
        }
        shapes = {
            "ft.weight": (32, 312),
            "ft.bias": (32,),
            "h.weight": (32, 70),
            "h.bias": (32,),
            "out.weight": (1, 32),
            "out.bias": (1,),
            "policy.weight": (209, 32),
            "policy.bias": (209,),
        }
        state = {
            "identity": checkpoint_identity(cfg, corpus, joint),
            "model_state_status": "LAST_COMPLETED_UPDATE",
            "completed_step": 1,
            "training_seen": 4,
            "samples": 12,
            "forward_rows": {
                "train": 4,
                "full_selector": 8,
                "diagnostic": 0,
                "onnx": 0,
            },
            "completed_forward_rows": {
                "train": 4,
                "full_selector": 8,
                "diagnostic": 0,
                "onnx": 0,
            },
            "observation": {"step": 1, "training_seen": 4},
            "best_state": {name: _Tensor(shape) for name, shape in shapes.items()},
            "initial_state": {name: _Tensor(shape) for name, shape in shapes.items()},
            "policy_evidence": "learned",
        }
        saved = {
            "position": {"step": 1, "training_seen": 4},
            "policy_value": state,
            "model": {name: _Tensor(shape) for name, shape in shapes.items()},
        }
        status = {
            "wall_seconds": 1.5,
            "joint_runtime": {
                "prior_wall_seconds": 0.0,
                "current_wall_seconds": 1.5,
                "cumulative_wall_seconds": 1.5,
            },
            "status": "INTERRUPTED",
            "step": 1,
            "attempted_step": 1,
            "model_state_status": "LAST_COMPLETED_UPDATE",
            "samples": 12,
            "forward_rows_conservative": dict(state["forward_rows"]),
            "forward_rows_completed": dict(state["completed_forward_rows"]),
        }
        checkpoint = directory / "metadata-fake.pt"
        checkpoint.write_bytes(b"synthetic zero-head checkpoint")
        status_path = directory / "run-status.json"

        def ref(path):
            raw = path.read_bytes()
            return {
                "path": str(path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "mode": "0644",
            }

        def bind():
            status_path.write_text(json.dumps(status))
            joint["binding"]["restart"] = {
                "checkpoint": ref(checkpoint),
                "run_status": ref(status_path),
            }

        fake_torch = types.SimpleNamespace(
            load=lambda *a, **kw: saved,
            float32="float32",
            isfinite=lambda t: types.SimpleNamespace(all=lambda: t.finite),
        )
        bind()
        return cfg, corpus, joint, saved, status, bind, fake_torch

    def test_observed_exact_restart_and_finite_head_tuple_nn0(self):
        with tempfile.TemporaryDirectory() as path:
            cfg, corpus, joint, saved, _, _, torch = self.fixture(Path(path))
            with patch.dict("sys.modules", {"torch": torch}):
                self.assertIs(read_restart(cfg, corpus, joint), saved)
                saved["model"]["policy.weight"].finite = False
                with self.assertRaises(ValueError):
                    read_restart(cfg, corpus, joint)

    def test_pending_or_failed_suffix_cannot_reset_actual_work_nn0(self):
        with tempfile.TemporaryDirectory() as path:
            cfg, corpus, joint, _, status, bind, torch = self.fixture(Path(path))
            original = copy.deepcopy(status)
            for changes in (
                {"samples": 13},
                {"attempted_step": 2},
                {"model_state_status": "UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN"},
                {"status": "EARLY_STOPPED"},
                {
                    "forward_rows_conservative": {
                        "train": 5,
                        "full_selector": 8,
                        "diagnostic": 0,
                        "onnx": 0,
                    }
                },
            ):
                status.clear()
                status.update(copy.deepcopy(original))
                status.update(changes)
                bind()
                with (
                    patch.dict("sys.modules", {"torch": torch}),
                    self.assertRaises(ValueError),
                ):
                    read_restart(cfg, corpus, joint)

    def test_restart_binds_data_scale_head_and_temperature_nn0(self):
        with tempfile.TemporaryDirectory() as path:
            cfg, corpus, joint, saved, _, _, torch = self.fixture(Path(path))
            with patch.dict("sys.modules", {"torch": torch}):
                for key in (
                    "dataset",
                    "initializer",
                    "initial_policy",
                    "shared_fingerprint",
                ):
                    identity = saved["policy_value"]["identity"]
                    original = identity[key]
                    identity[key] = "different-synthetic-binding"
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        read_restart(cfg, corpus, joint)
                    identity[key] = original
                cfg["policy_value"]["temperature"] = 0.5
                with self.assertRaises(ValueError):
                    read_restart(cfg, corpus, joint)

    def test_restart_carries_prior_wall_budget_and_refuses_unknown_nn0(self):
        with tempfile.TemporaryDirectory() as path:
            cfg, corpus, joint, saved, status, bind, torch = self.fixture(Path(path))
            status["joint_runtime"] = {
                "prior_wall_seconds": 2.0,
                "current_wall_seconds": 1.5,
                "cumulative_wall_seconds": 3.5,
            }
            bind()
            with patch.dict("sys.modules", {"torch": torch}):
                self.assertEqual(
                    read_restart(cfg, corpus, joint)["_actual_previous_wall_seconds"],
                    3.5,
                )
                for bad in (-1, float("nan"), "UNKNOWN", 1.0):
                    status["joint_runtime"]["cumulative_wall_seconds"] = bad
                    bind()
                    with self.subTest(value=bad), self.assertRaises(ValueError):
                        read_restart(cfg, corpus, joint)

    def test_unsupported_observation_and_state_exports_refuse_before_entry_nn0(self):
        cfg = configuration()
        self.assertEqual(settings(cfg)["selector"], "joint_loss")
        for section, name, bad in (
            ("evaluation", "diagnostic_checkpoints", None),
            ("static_teacher", "state_checkpoint_steps", [1]),
            ("static_teacher", "initializer_seed", 999),
        ):
            changed = copy.deepcopy(cfg)
            changed[section][name] = bad
            with (
                self.subTest(section=section, name=name),
                self.assertRaises(ValueError),
            ):
                settings(changed)

    def test_initial_native_identity_mismatch_refuses_before_policy_publication_nn0(
        self,
    ):
        fake_train = types.SimpleNamespace(
            export=lambda *a: Path("/synthetic-no-model-load/manifest.json"),
            export_policy_head=lambda *a, **kw: self.fail("must not publish a mismatched head"),
        )
        joint = {
            "binding": {"core_library": {"path": "/synthetic-no-library-load"}},
            "native_identity_constructors": 0,
            "initial_shared_fingerprint": "a" * 64,
        }
        with (
            patch.dict("sys.modules", {__package__ + ".train": fake_train}),
            patch(
                __package__ + ".policy_value_training.native_identity",
                return_value={"shared": "b" * 64, "policy": None},
            ),
            self.assertRaises(ValueError),
        ):
            export_joint(object(), {}, {}, {}, Path("/synthetic"), joint, initial=True)


class PolicyValueWallMetadata(unittest.TestCase):
    """R1 only: producer-shaped clock metadata; fake checkpoint, zero heads."""

    def fixture(self, directory):
        return PolicyValueMetadata().fixture(directory)

    def test_producer_wall_prefix_roundtrip_nn0(self):
        for prior, current in ((0.0, 1.5), (10.0, 1.5), (0.1, 0.2), (10, 2), (0, 0)):
            with (
                self.subTest(prior=prior, current=current),
                tempfile.TemporaryDirectory() as path,
            ):
                cfg, corpus, joint, saved, status, bind, torch = self.fixture(Path(path))
                status["wall_seconds"] = current
                status["joint_runtime"] = {
                    "prior_wall_seconds": prior,
                    "current_wall_seconds": current,
                    "cumulative_wall_seconds": prior + current,
                }
                bind()
                with patch.dict("sys.modules", {"torch": torch}):
                    self.assertIs(read_restart(cfg, corpus, joint), saved)
                self.assertEqual(saved["_actual_previous_wall_seconds"], prior + current)
                self.assertEqual(saved["position"], {"step": 1, "training_seen": 4})
                self.assertEqual(saved["policy_value"]["samples"], 12)

    def test_missing_or_inconsistent_wall_prefix_refuses_before_checkpoint_nn0(self):
        with tempfile.TemporaryDirectory() as path:
            cfg, corpus, joint, _, status, bind, torch = self.fixture(Path(path))
            status["joint_runtime"] = {
                "prior_wall_seconds": 10,
                "current_wall_seconds": 1.5,
                "cumulative_wall_seconds": 11.5,
            }
            original = copy.deepcopy(status)
            changes = [
                ("missing-runtime", lambda s: s.pop("joint_runtime")),
                ("missing-wall", lambda s: s.pop("wall_seconds")),
                ("runtime-null", lambda s: s.update(joint_runtime=None)),
                ("runtime-list", lambda s: s.update(joint_runtime=[])),
                (
                    "current-mismatch",
                    lambda s: s["joint_runtime"].update(current_wall_seconds=2.0),
                ),
                (
                    "lost-prefix",
                    lambda s: s["joint_runtime"].update(cumulative_wall_seconds=2.0),
                ),
                (
                    "inflated-prefix",
                    lambda s: s["joint_runtime"].update(cumulative_wall_seconds=12.0),
                ),
                (
                    "changed-prior",
                    lambda s: s["joint_runtime"].update(prior_wall_seconds=9.0),
                ),
            ]
            for key in (
                "prior_wall_seconds",
                "current_wall_seconds",
                "cumulative_wall_seconds",
            ):
                changes.append(("missing-" + key, lambda s, key=key: s["joint_runtime"].pop(key)))
            torch.load = lambda *a, **kw: self.fail(
                "invalid clocks must refuse before checkpoint load"
            )
            for name, change in changes:
                with self.subTest(case=name):
                    status.clear()
                    status.update(copy.deepcopy(original))
                    change(status)
                    bind()
                    with (
                        patch.dict("sys.modules", {"torch": torch}),
                        self.assertRaises(ValueError),
                    ):
                        read_restart(cfg, corpus, joint)

    def test_invalid_wall_numbers_and_overflow_refuse_before_checkpoint_nn0(self):
        with tempfile.TemporaryDirectory() as path:
            cfg, corpus, joint, _, status, bind, torch = self.fixture(Path(path))
            original = copy.deepcopy(status)
            torch.load = lambda *a, **kw: self.fail(
                "invalid clocks must refuse before checkpoint load"
            )
            for key in (
                "wall_seconds",
                "prior_wall_seconds",
                "current_wall_seconds",
                "cumulative_wall_seconds",
            ):
                for bad in (
                    True,
                    False,
                    None,
                    "1.5",
                    -1,
                    float("nan"),
                    float("inf"),
                    -float("inf"),
                    10**400,
                ):
                    with self.subTest(key=key, value=bad):
                        status.clear()
                        status.update(copy.deepcopy(original))
                        if key == "wall_seconds":
                            status[key] = bad
                        else:
                            status["joint_runtime"][key] = bad
                        bind()
                        with (
                            patch.dict("sys.modules", {"torch": torch}),
                            self.assertRaises(ValueError),
                        ):
                            read_restart(cfg, corpus, joint)
            status["wall_seconds"] = 1e308
            status["joint_runtime"] = {
                "prior_wall_seconds": 1e308,
                "current_wall_seconds": 1e308,
                "cumulative_wall_seconds": 1e308,
            }
            bind()
            with (
                patch.dict("sys.modules", {"torch": torch}),
                self.assertRaises(ValueError),
            ):
                read_restart(cfg, corpus, joint)


@unittest.skipUnless(os.environ.get("NNUE_JOINT_SMOKE_PACKET"), "actual bounded smoke input absent")
class PolicyValueFunctional(unittest.TestCase):
    def test_one_joint_stream_two_updates_with_observed_restart(self):
        """ONE planned functional smoke, real <=16 teacher rows and 2 updates.

        Root alone supplies actual library/model/input/resource bindings at a
        compatible STOP window. This test has no model, build or scientific
        authority merely from an environment variable or successful software.
        """
        from .common import bound_file_bytes, resolve_config
        from .public_static_values import label_policy_values
        from .public_static_prepare import file_ref
        from .static_learning import prepare_policy_fit
        from .train import train

        packet_path = Path(os.environ["NNUE_JOINT_SMOKE_PACKET"])
        with packet_path.open("rb") as stream:
            raw = stream.read(131073)
        if len(raw) > 131072:
            raise ValueError("bounded actual smoke packet")
        packet = json.loads(raw)
        self.assertEqual(
            set(packet),
            {
                "teacher_config",
                "fit_config",
                "initial_model",
                "initial_policy",
                "core_library",
                "output",
            },
        )
        teacher_config = json.loads(bound_file_bytes(packet["teacher_config"], 131072))
        cfg = resolve_config(json.loads(bound_file_bytes(packet["fit_config"], 131072)))
        self.assertEqual(cfg["training"]["device"], "cpu")
        self.assertEqual(cfg["training"]["steps"], 2)
        self.assertLessEqual(cfg["training"]["batch_size"], 8)
        self.assertEqual(
            cfg["static_teacher"]["maximum_training_draws"],
            2 * cfg["training"]["batch_size"],
        )
        self.assertEqual(cfg["evaluation"]["checkpoints"], [0, 1, 2])
        self.assertEqual(teacher_config["device"], "cpu")
        self.assertEqual(teacher_config["prior_actual_rows"], 0)
        self.assertLessEqual(teacher_config["inclusive_row_limit"], 16)
        self.assertEqual(teacher_config["core_library"], packet["core_library"])
        output = Path(packet["output"])
        output.mkdir(exist_ok=False)
        teacher_config["output"] = str(output / "teacher")
        labeled = label_policy_values(teacher_config)
        self.assertLessEqual(labeled["head"]["logical_rows_attempted"], 16)
        self.assertEqual(labeled["head"]["failed_attempted_rows"], 0)
        self.assertEqual(
            labeled["head"]["finite_rows_returned"],
            labeled["head"]["logical_rows_attempted"],
        )

        prepare = {
            "cache": labeled["cache"],
            "fit_config": packet["fit_config"],
            "initial_model": packet["initial_model"],
            "initial_policy": packet["initial_policy"],
            "core_library": packet["core_library"],
            "restart": None,
            "output": str(output / "first-inputs"),
        }
        first = prepare_policy_fit(prepare)

        class ObservedBoundary(Exception):
            pass

        def stop_after_first_actual_observation(record):
            self.assertEqual(record["position"]["step"], 1)
            raise ObservedBoundary("planned observed one-update checkpoint, no retry")

        with self.assertRaises(ObservedBoundary):
            train(
                Path(labeled["cache"]["path"]).parent,
                output / "first",
                first["config"]["path"],
                input_binding=first["input_binding"]["path"],
                progress_callback=stop_after_first_actual_observation,
            )
        first_status = json.loads((output / "first/run-status.json").read_text())
        self.assertEqual(first_status["status"], "INTERRUPTED")
        self.assertEqual(first_status["step"], 1)
        self.assertEqual(first_status["attempted_step"], 1)
        self.assertEqual(first_status["model_state_status"], "LAST_COMPLETED_UPDATE")
        # The original interruption/status/cost remains retained and unmodified.
        prepare["restart"] = {
            "checkpoint": file_ref(output / "first/last.pt"),
            "run_status": file_ref(output / "first/run-status.json"),
        }
        prepare["output"] = str(output / "restart-inputs")
        resumed = prepare_policy_fit(prepare)
        final = train(
            Path(labeled["cache"]["path"]).parent,
            output / "resumed",
            resumed["config"]["path"],
            input_binding=resumed["input_binding"]["path"],
        )
        self.assertEqual(final["step"], 2)
        self.assertEqual(final["policy_value"]["prior_logical_rows"], first_status["samples"])
        self.assertEqual(
            final["samples"],
            first_status["samples"] + final["policy_value"]["new_logical_rows"],
        )
        self.assertEqual(final["policy_value"]["native_identity_head_rows"], 0)
        identities = final["policy_value"]["exported_native_identities"]
        self.assertTrue(identities)
        for identity in identities.values():
            self.assertEqual(len(identity["shared"]), 64)
            self.assertEqual(len(identity["policy"]), 64)
        initial = json.loads(
            (output / "resumed/initial-model/policy-head/manifest.json").read_text()
        )
        last = json.loads((output / "resumed/last-model/policy-head/manifest.json").read_text())
        self.assertNotEqual(initial["weights_sha256"], last["weights_sha256"])
        self.assertEqual(last["evidence"], "learned")
        result = {
            "scope": "one joint functional smoke, not a candidate/fit/strength campaign",
            "teacher": labeled,
            "completed_optimizer_updates": 2,
            "first_interruption_unchanged": file_ref(output / "first/run-status.json"),
            "final_freeze": file_ref(output / "resumed/freeze.json"),
            "actual_cumulative_NNUE_row_forwards": final["samples"],
            "actual_constructor_identity_head_rows": 0,
            "normal_native_shared_policy_identities": identities,
            "new_Sigma_Search_MCTS_games": 0,
            "prior18_1_counts_are_separate": True,
        }
        (output / "smoke-result.json").write_text(json.dumps(result, indent=2) + "\n")


class SelectionQueryBoundary(unittest.TestCase):
    def test_native_action_query_boundary_nn0(self):
        from .policy_value_training import _selection_action_queries, policy_diagnostics

        good = {"selected_alpha": [0, 208], "cedar_alpha": [208, 0]}
        saved = copy.deepcopy(good)
        frozen = _selection_action_queries(good, 2)
        self.assertEqual(frozen, {name: tuple(value) for name, value in good.items()})
        self.assertEqual(good, saved)
        good["selected_alpha"][0] = 7
        self.assertEqual(frozen["selected_alpha"][0], 0)
        self.assertEqual(
            len(
                _selection_action_queries(
                    {"selected_alpha": [0] * 32, "cedar_alpha": [208] * 32}, 32
                )["cedar_alpha"]
            ),
            32,
        )
        malformed = [
            ({}, 2),
            ({"selected_alpha": [0, 1], "cedar_alpha": [2, 3], "extra": []}, 2),
            ({"selected_alpha": [0], "cedar_alpha": [0, 1]}, 2),
            ({"selected_alpha": [True, 1], "cedar_alpha": [0, 1]}, 2),
            ({"selected_alpha": [0.0, 1], "cedar_alpha": [0, 1]}, 2),
            ({"selected_alpha": [-1, 1], "cedar_alpha": [0, 1]}, 2),
            ({"selected_alpha": [209, 1], "cedar_alpha": [0, 1]}, 2),
            ({"selected_alpha": [0] * 33, "cedar_alpha": [0] * 33}, 33),
            ({"selected_alpha": [], "cedar_alpha": []}, 0),
            ({"selected_alpha": [0], "cedar_alpha": [0]}, True),
        ]
        for queries, count in malformed:
            with self.subTest(queries=queries, count=count), self.assertRaises(ValueError):
                _selection_action_queries(queries, count)
        fake_logits = types.SimpleNamespace(shape=(2, 209))
        with patch.dict("sys.modules", {"torch": None}), self.assertRaises(ValueError):
            policy_diagnostics(fake_logits, None, None, None, action_queries={"selected_alpha": []})

    def test_compact_action_metrics_use_actual_legal_distributions_nn0(self):
        import torch

        from .policy_value_training import policy_diagnostics

        logits = torch.zeros((2, 209), dtype=torch.float32)
        target = torch.zeros_like(logits)
        legal = torch.zeros_like(logits, dtype=torch.bool)
        legal[:, [0, 1, 208]] = True
        target[0, 0], target[0, 1] = 0.5, 0.5
        target[1, 208] = 1.0
        weights = torch.ones(2)
        plain = policy_diagnostics(logits, target, legal, weights)
        queried = policy_diagnostics(
            logits,
            target,
            legal,
            weights,
            action_queries={"selected_alpha": [0, 0], "cedar_alpha": [208, 0]},
        )
        self.assertEqual({key: queried[key] for key in plain}, plain)
        rows = queried["selection_rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["teacher_top1_in_input_view"], 0)
        self.assertFalse(rows[0]["action_agreement"])
        self.assertTrue(rows[1]["action_agreement"])
        self.assertEqual(rows[0]["queries"]["selected_alpha"]["teacher_legal_rank"], 1)
        self.assertEqual(rows[0]["queries"]["cedar_alpha"]["teacher_legal_rank"], 3)
        self.assertEqual(rows[1]["queries"]["selected_alpha"]["teacher_legal_rank"], 2)
        self.assertEqual(rows[0]["queries"]["selected_alpha"]["teacher_probability"], 0.5)
        self.assertEqual(rows[0]["queries"]["cedar_alpha"]["teacher_probability"], 0.0)
        for row in rows:
            for query in row["queries"].values():
                self.assertAlmostEqual(query["current_probability"], 1.0 / 3.0, places=6)
                self.assertEqual(query["current_legal_rank"], 1)
        with self.assertRaises(ValueError):
            policy_diagnostics(
                logits,
                target,
                legal,
                weights,
                action_queries={"selected_alpha": [2, 0], "cedar_alpha": [0, 0]},
            )


if __name__ == "__main__":
    unittest.main()
