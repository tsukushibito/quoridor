"""New config-only static-learning boundaries; no model, head, or optimizer update."""

import ast
import copy
import io
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from quoridor_training.common import DEFAULTS, PARAMETER_SHAPES, resolve_config
from quoridor_training.static_learning import (
    StaticContinuation,
    observation_index_sha,
    read_static_continuation,
    restore_static_exposure,
    static_checkpoint_ref,
    static_settings,
)


def config_for(
    r, v, *, device="cpu", threads=1, optimizer_mode="matching", phase_steps=0, phase_rows=0
):
    """Explicit test run config; it is not a production recipe or admission."""
    if optimizer_mode != "matching":
        raise ValueError("reset is not admitted by this matching-state fixture")
    cfg = copy.deepcopy(DEFAULTS)
    draws = 256 * r
    cfg["model"].update(architecture="distance_residual", distance_a=0, distance_b=0)
    cfg["optimizer"].update(name="adam", lr=1e-4, betas=[0.9, 0.999], eps=1e-8)
    cfg["training"].update(
        steps=math.ceil(draws / 4096),
        batch_size=4096,
        target="static_teacher",
        sampling="row",
        loss_weighting="row",
        scheduler="plateau",
        warmup_steps=0,
        device=device,
        threads=threads,
    )
    cfg["evaluation"].update(
        checkpoints=sorted({0, *[math.ceil(k * r / 4096) for k in range(1, 257)]}),
        monitor="row",
        early_stopping_unit="observation",
        early_stopping_patience=8,
        min_delta=1e-5,
        min_delta_relative=1e-4,
        diagnostic_rows=min(65536, r),
        diagnostic_checkpoints=[],
        full_train=False,
        full_train_checkpoints=[],
    )
    cfg["artifacts"].update(mode="native", save_scheduled=False, checkpoint_steps=[])
    cfg["limits"].update(seconds=None, samples=850000000)
    cfg["static_teacher"].update(
        maximum_training_draws=draws,
        minimum_training_draws=8 * r,
        minimum_floor_training_draws=8 * r,
        overfit_observations=3,
        overfit_validation_absolute=0.002,
        overfit_validation_relative=0.01,
        overfit_training_absolute=1e-5,
        overfit_training_relative=1e-4,
        progress_absolute=1e-4,
        progress_relative=0.01,
        initializer_seed=101,
        panel_seed=102,
        state_checkpoint_steps=sorted({math.ceil(k * 16 * r / 4096) for k in range(1, 17)}),
    )
    return resolve_config(cfg)


def policy_settings(r):
    return static_settings(config_for(r, 2), r, 2)


class ConfiguredStaticBoundaries(unittest.TestCase):
    def test_fresh_pair_preparation_binds_provided_file_and_all_actual_settings(self):
        from quoridor_training import cache
        from quoridor_training.public_static_prepare import file_ref
        import sys

        learning = sys.modules[StaticContinuation.__module__]
        cfg = config_for(12, 3)
        cfg["optimizer"]["lr"] = 0.0007
        cfg["training"].update(
            scheduler="none", batch_size=64, steps=48, warmup_steps=2, seed=77, reflection_seed=78
        )
        cfg["evaluation"]["checkpoints"] = [0, 8, 16, 24, 32, 48]
        cfg["static_teacher"].update(
            state_checkpoint_steps=[16, 48], initializer_seed=79, panel_seed=80
        )
        cfg = resolve_config(cfg)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            inputs = folder / "inputs.json"
            inputs.write_text(
                json.dumps(dict(status="COMPLETE", counts=dict(train=12, validation=3)))
            )
            bank = folder / "bank.json"
            bank.write_text(
                json.dumps(
                    dict(
                        schema="quoridor-public-static-teacher-values-v1",
                        status="COMPLETE",
                        input_classes=file_ref(inputs),
                    )
                )
            )
            source = folder / "provided.json"
            source.write_text(json.dumps(cfg))

            def load(path):
                teacher = json.loads((Path(path) / "cache.json").read_text())["teacher"]
                return SimpleNamespace(
                    input_ref=file_ref(inputs),
                    counts=dict(train=12, validation=3),
                    binding=dict(dataset_sha=("a" if teacher == "S" else "b") * 64),
                    labels=np.full((15, 1), 0.1 if teacher == "S" else -0.2),
                    statistics=lambda: dict(mu_f32=0, sigma_f32=1),
                    verify_binding=lambda: None,
                    close=lambda **kwargs: None,
                )

            def initialize(cache_path, output, config_path):
                actual = resolve_config(config_path)
                self.assertEqual(actual, cfg)
                output.mkdir()
                scale = output / "scale.json"
                scale.write_text(json.dumps(dict(mu_f32=0, sigma_f32=1)))
                weights = output / "NN0-no-model"
                weights.write_bytes(b"metadata-only fixture, no head")
                result = dict(
                    input_classes=file_ref(inputs),
                    initial_weights=file_ref(weights),
                    initial_weights_sha=file_ref(weights)["sha256"],
                    initializer_seed=actual["static_teacher"]["initializer_seed"],
                    scale=dict(path=str(scale), sha256=file_ref(scale)["sha256"]),
                    explicit_NN0=True,
                )
                (output / "result.json").write_text(json.dumps(result))
                return result

            with (
                patch.object(cache, "load", side_effect=load),
                patch.object(learning, "prepare_common", side_effect=initialize),
            ):
                returned = learning.prepare_fits(
                    dict(
                        teacher_values=file_ref(bank),
                        fit_config=file_ref(source),
                        output=str(folder / "prepared"),
                    )
                )
            result = json.loads(Path(returned["result"]["path"]).read_text())
            for teacher in ("S", "C"):
                actual = resolve_config(result["arms"][teacher]["config"]["path"])
                self.assertEqual(actual, cfg)
                binding = json.loads(
                    Path(result["arms"][teacher]["input_binding"]["path"]).read_text()
                )
                self.assertEqual(
                    binding["fit_config_sha"],
                    file_ref(Path(result["arms"][teacher]["config"]["path"]))["sha256"],
                )
            self.assertFalse(returned["fit_entered"])
            self.assertEqual(result["prepare_head_rows"], 0)

    def test_notification_matches_same_resolved_conditions_for_S_and_C(self):
        path = (
            Path(__file__).resolve().parents[4] / "games/quoridor/python/quoridor_training/train.py"
        )
        tree = ast.parse(path.read_text())
        train = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train")
        evaluate = next(
            n for n in train.body if isinstance(n, ast.FunctionDef) and n.name == "evaluate"
        )
        block = next(
            n
            for n in evaluate.body
            if isinstance(n, ast.If)
            and any(
                isinstance(x, ast.Name) and x.id == "first_static_progress_sent"
                for x in ast.walk(n.test)
            )
        )
        function = ast.FunctionDef(
            name="emit",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Global(names=["first_static_progress_sent"]), block],
            decorator_list=[],
        )
        cfg = config_for(33, 2)
        cfg["static_teacher"].update(minimum_floor_training_draws=132, state_checkpoint_steps=[1])
        cfg["evaluation"]["early_stopping_patience"] = 2
        cfg = resolve_config(cfg)
        controls = static_settings(cfg, 33, 2)
        for teacher in ("S", "C"):
            received = []
            position = dict(
                step=1,
                training_seen=4096,
                continuation=dict(phase_steps=1, old_executed=dict(logical_rows=80)),
            )
            namespace = dict(
                static_teacher=True,
                selector=True,
                step=1,
                progress_callback=received.append,
                first_static_progress_sent=False,
                position=lambda: position,
                curve=[dict(wall_seconds=1)],
                phase_seconds={},
                forward_rows={},
                completed_forward_rows={},
                device="cpu",
                batch_size=4096,
                cfg=cfg,
                ix_train=range(33),
                expected={},
                continuation=SimpleNamespace(state=dict(lr=cfg["optimizer"]["lr"])),
                continuation_input=dict(
                    checkpoint=dict(id=teacher + "state"), weights=dict(id=teacher + "weights")
                ),
                corpus=SimpleNamespace(input_ref=dict(id="synthetic")),
                output=Path("synthetic-unwritten"),
                copy=copy,
                math=math,
                static_controls=controls,
            )
            exec(
                compile(
                    ast.fix_missing_locations(
                        ast.Module(body=[copy.deepcopy(function)], type_ignores=[])
                    ),
                    "configured-actual-callback",
                    "exec",
                ),
                namespace,
            )
            namespace["emit"]()
            namespace["emit"]()
            self.assertEqual(len(received), 1)
            packet = received[0]
            self.assertEqual(packet["maximum_phase_updates"], cfg["training"]["steps"])
            self.assertEqual(
                packet["maximum_training_draws"], cfg["static_teacher"]["maximum_training_draws"]
            )
            self.assertEqual(packet["minimum_floor_training_draws"], 132)
            self.assertEqual(packet["required_floor_nonsignificant_observations"], 2)
            self.assertNotIn("initial_weights_sha", packet)

    def test_resume_joins_config_state_RNG_and_remaining_quota_without_heads(self):
        import torch

        cfg = config_for(33, 2)
        settings = static_settings(cfg, 33, 2)
        panel, validation = np.arange(33), np.arange(33, 35)
        corpus = SimpleNamespace(
            counts=dict(train=33, validation=2),
            input_ref=dict(id="new-synthetic-input"),
            binding=dict(teacher="C", teacher_values=dict(id="new-C-bank"), dataset_sha="b" * 64),
            executed_orientations=np.zeros((1, 2), dtype="<u4"),
            pending_training=None,
            executed_rows=0,
        )
        identity = dict(
            input_classes=corpus.input_ref,
            teacher_values=corpus.binding["teacher_values"],
            teacher="C",
            dataset_sha="b" * 64,
            train_panel_sha256=observation_index_sha(panel),
            validation_index_sha256=observation_index_sha(validation),
        )
        baseline = dict(train=dict(target_mse=0.15), validation=dict(target_mse=0.2))
        policy = StaticContinuation(settings, baseline)
        policy.observe(0.19, 0.14, 4096)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            counter = folder / "counter.u32"
            counter.write_bytes(np.array([[4096, 0]], dtype="<u4").tobytes())
            exposure = dict(rows=4096, shape=[1, 2], ref=static_checkpoint_ref(counter))
            parameters = {name: torch.zeros(shape) for name, shape in PARAMETER_SHAPES.items()}
            weights = folder / "weights.f32"
            weights.write_bytes(
                b"".join(value.numpy().astype("<f4").tobytes() for value in parameters.values())
            )
            checkpoint = dict(
                model=parameters,
                model_config=cfg["model"],
                scale=dict(mu_f32=0, sigma_f32=1),
                target="static_teacher",
                dataset_sha="b" * 64,
                position=dict(step=1, training_seen=4096),
                optimizer=dict(
                    state={
                        i: dict(
                            step=torch.tensor(6.0),
                            exp_avg=torch.zeros(shape),
                            exp_avg_sq=torch.zeros(shape),
                        )
                        for i, shape in enumerate(PARAMETER_SHAPES.values())
                    },
                    param_groups=[
                        dict(
                            params=list(range(6)),
                            lr=0.0001,
                            betas=(0.9, 0.999),
                            eps=1e-8,
                            weight_decay=0,
                        )
                    ],
                ),
                static_RNG=dict(
                    index_torch_state=torch.Generator().manual_seed(801).get_state(),
                    reflection_numpy_state=np.random.default_rng(802).bit_generator.state,
                    ordered_index_mask_sha256="a" * 64,
                ),
                static_continuation=dict(
                    identity=identity,
                    resolved_config_sha256=settings["config_sha256"],
                    evaluation_complete_for_position=True,
                    last_observation=dict(
                        step=1,
                        training_seen=4096,
                        train=dict(target_mse=0.14),
                        validation=dict(target_mse=0.19),
                    ),
                    old_executed=dict(logical_rows=80, draws=32, steps=8),
                    phase_draws=4096,
                    phase_steps=1,
                    phase_logical_rows=4166,
                    origin_position=dict(step=5, training_seen=20),
                    policy=policy.state,
                    selected_best=None,
                    optimizer_mode="matching",
                    exposure=exposure,
                ),
            )
            path = folder / "last.pt"
            buffer = io.BytesIO()
            torch.save(checkpoint, buffer)
            path.write_bytes(buffer.getvalue())
            control = dict(
                schema="quoridor-static-continuation-input-v1",
                optimizer_mode="matching",
                **identity,
                checkpoint=static_checkpoint_ref(path),
                weights=static_checkpoint_ref(weights),
                phase_steps=1,
                phase_rows=4166,
            )
            restored = read_static_continuation(
                control, cfg, corpus, checkpoint["scale"], panel, validation
            )
            self.assertEqual(restored["previous_rows"], 4166)
            self.assertEqual(restored["previous_steps"], 1)
            self.assertEqual(restored["settings"]["logical_quota"], 850000000)
            self.assertEqual(restored["checkpoint"]["optimizer"]["state"][0]["step"], 6)
            self.assertTrue(
                torch.equal(
                    restored["checkpoint"]["static_RNG"]["index_torch_state"],
                    checkpoint["static_RNG"]["index_torch_state"],
                )
            )
            self.assertEqual(
                restored["checkpoint"]["static_RNG"]["reflection_numpy_state"],
                checkpoint["static_RNG"]["reflection_numpy_state"],
            )
            restore_static_exposure(corpus, exposure)
            self.assertEqual(corpus.executed_rows, 4096)
            bad = dict(control, phase_rows=0)
            with self.assertRaises(ValueError):
                read_static_continuation(bad, cfg, corpus, checkpoint["scale"], panel, validation)
            changed = copy.deepcopy(cfg)
            changed["optimizer"]["eps"] = 1e-7
            with self.assertRaises(ValueError):
                read_static_continuation(
                    control, resolve_config(changed), corpus, checkpoint["scale"], panel, validation
                )

    def test_two_teachers_consume_changed_LR_stopping_and_save_conditions(self):
        baseline = dict(train=dict(target_mse=0.15), validation=dict(target_mse=0.2))
        cfg = config_for(10, 2)
        cfg["optimizer"]["lr"] = 0.0008
        cfg["training"].update(min_lr=0.0002, lr_decay_factor=0.25, lr_decay_patience=0)
        cfg["evaluation"].update(
            early_stopping_patience=2, min_delta=0.0001, min_delta_relative=0.01
        )
        cfg["static_teacher"].update(
            minimum_floor_training_draws=20,
            overfit_observations=2,
            overfit_validation_absolute=0.01,
            overfit_training_absolute=0.01,
            state_checkpoint_steps=[1],
        )
        cfg = resolve_config(cfg)
        values = []
        for teacher in ("S", "C"):
            settings = static_settings(cfg, 10, 2)
            policy = StaticContinuation(settings, baseline)
            first = policy.observe(0.2, 0.15, 10)
            self.assertEqual(first["update_lr_used"], 0.0008)
            self.assertEqual(first["next_lr"], 0.0002)
            self.assertFalse(policy.observe(0.22, 0.10, 20)["stop"])
            last = policy.observe(0.22, 0.10, 30)
            self.assertEqual(last["verdict"], "OVERFIT_STOP/NEEDED_WORK")
            self.assertEqual(last["floor_draws"], 20)
            self.assertEqual(settings["state_checkpoints"], {1: 1})
            values.append((settings, last))
        self.assertEqual(values[0], values[1])

    def test_config_interactions_and_nonfinite_rejected_before_policy_mutation(self):
        cfg = config_for(10, 2)
        for change in (
            lambda c: c["static_teacher"].update(maximum_training_draws=True),
            lambda c: c["static_teacher"].update(state_checkpoint_steps=[0]),
            lambda c: c["static_teacher"].update(minimum_floor_training_draws=999999),
            lambda c: c["training"].update(steps=2),
            lambda c: c["optimizer"].update(eps=float("nan")),
        ):
            bad = copy.deepcopy(cfg)
            change(bad)
            with self.assertRaises(ValueError):
                resolve_config(bad)
        settings = static_settings(cfg, 10, 2)
        policy = StaticContinuation(
            settings, dict(train=dict(target_mse=0.15), validation=dict(target_mse=0.2))
        )
        previous = copy.deepcopy(policy.state)
        with self.assertRaises(ValueError):
            policy.observe(float("nan"), 0.15, 10)
        self.assertEqual(policy.state, previous)
        changed = copy.deepcopy(cfg)
        changed["optimizer"]["lr"] *= 0.5
        with self.assertRaises(ValueError):
            StaticContinuation(
                static_settings(resolve_config(changed), 10, 2),
                dict(train=dict(target_mse=0.15), validation=dict(target_mse=0.2)),
                state=previous,
            )


if __name__ == "__main__":
    unittest.main()
