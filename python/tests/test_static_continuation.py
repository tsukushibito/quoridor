"""New continuation metadata/plateau boundaries; no model, forward, or optimizer step."""

import copy
import gzip
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

from quoridor_training.common import PARAMETER_SHAPES
from quoridor_training.static_learning import (
    StaticContinuation,
    continuation_recipe,
    observation_index_sha,
    read_static_continuation,
    restore_static_exposure,
    static_checkpoint_ref,
)


BASELINE = dict(train=dict(target_mse=0.15), validation=dict(target_mse=0.2))


class StaticContinuationTests(unittest.TestCase):
    def test_fixed256R_ceil_boundaries_preserve_full_batches_and_only_final_tail(self):
        r = 2809595
        cfg = continuation_recipe(r, 312247, device="cpu", threads=1, optimizer_mode="matching")
        self.assertEqual(cfg["training"]["steps"], 175600)
        self.assertEqual(cfg["training"]["warmup_steps"], 0)
        self.assertEqual(cfg["evaluation"]["checkpoints"][16], 10975)
        self.assertEqual(10975 * 4096, 16 * r + 80)
        self.assertEqual(256 * r - (175600 - 1) * 4096, 2816)
        next_cfg = continuation_recipe(
            r,
            312247,
            device="cpu",
            threads=1,
            optimizer_mode="matching",
            phase_steps=10975,
            phase_rows=52000000,
        )
        self.assertEqual(next_cfg["training"]["steps"], 175600 - 10975)
        self.assertEqual(next_cfg["limits"]["samples"], 850000000 - 52000000)
        self.assertEqual(
            next_cfg["evaluation"]["checkpoints"][1], cfg["evaluation"]["checkpoints"][17] - 10975
        )
        with self.assertRaisesRegex(ValueError, "reset is not admitted"):
            continuation_recipe(r, 312247, device="cpu", threads=1, optimizer_mode="fresh")

    def test_rounded_floor_actual_draws_and_divergence_priority(self):
        r = 4097
        plateau = StaticContinuation(r, BASELINE)
        overfit = StaticContinuation(r, BASELINE)
        for k in range(1, 31):
            draws = ((k * r + 4095) // 4096) * 4096
            a = plateau.observe(0.2, 0.15, draws)
            b = overfit.observe(0.25 if k >= 28 else 0.2, 0.1 if k >= 28 else 0.15, draws)
            if k == 29:
                self.assertEqual(a["floor_stale"], 8)
                self.assertLess(a["floor_draws"], 8 * r)
                self.assertFalse(a["stop"])
                self.assertFalse(b["stop"])
        self.assertEqual(a["verdict"], "PRACTICAL_V_PLATEAU")
        self.assertEqual(b["verdict"], "OVERFIT_STOP/NEEDED_WORK")
        self.assertEqual(b["overfit_stale"], 3)
        self.assertEqual(b["floor_stale"], 9)

    def test_latest_rolling_counter_restoration_has_no_embedded_counter_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orientations.u32"
            counts = np.array([[2, 3], [4, 5]], dtype="<u4")
            path.write_bytes(counts.tobytes())
            entry = dict(ref=static_checkpoint_ref(path), shape=[2, 2], rows=14)
            corpus = SimpleNamespace(
                executed_orientations=np.zeros((2, 2), dtype="<u4"),
                pending_training=None,
                executed_rows=0,
            )
            restored = restore_static_exposure(corpus, entry)
            self.assertTrue(np.array_equal(corpus.executed_orientations, counts))
            self.assertEqual(corpus.executed_rows, 14)
            self.assertEqual(restored, entry)
            self.assertLess(len(json.dumps(restored)), 512)
            bad = dict(entry, rows=15)
            empty = SimpleNamespace(
                executed_orientations=np.zeros((2, 2), dtype="<u4"),
                pending_training=None,
                executed_rows=0,
            )
            with self.assertRaisesRegex(ValueError, "matching latest rolling"):
                restore_static_exposure(empty, bad)

    def test_fixed_phase_next_block_offsets_and_rolling_custody(self):
        import torch

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            r = 4097
            panel = np.arange(r)
            validation = np.arange(r, r + 2)
            cfg = continuation_recipe(
                r,
                2,
                device="cpu",
                threads=1,
                optimizer_mode="matching",
                phase_steps=2,
                phase_rows=8200,
            )
            corpus = SimpleNamespace(
                counts=dict(train=r, validation=2),
                input_ref=dict(id="synthetic-input"),
                binding=dict(
                    teacher_values=dict(id="synthetic-bank"), teacher="S", dataset_sha="a" * 64
                ),
            )
            identity = dict(
                input_classes=corpus.input_ref,
                teacher_values=corpus.binding["teacher_values"],
                teacher="S",
                dataset_sha="a" * 64,
                train_panel_sha256=observation_index_sha(panel),
                validation_index_sha256=observation_index_sha(validation),
            )
            policy = StaticContinuation(r, BASELINE)
            policy.observe(0.19, 0.14, 8192)
            point = dict(
                step=2,
                training_seen=8192,
                train=dict(rows=r, target_mse=0.14, actual_logical_rows=8),
                validation=dict(rows=2, target_mse=0.19, actual_logical_rows=4),
            )
            model = {name: torch.zeros(shape) for name, shape in PARAMETER_SHAPES.items()}
            counter = np.array([[8192, 0]], dtype="<u4")
            (folder / "counter.u32").write_bytes(counter.tobytes())
            checkpoint = dict(
                model=model,
                model_config=cfg["model"],
                scale=dict(mu_f32=0, sigma_f32=1),
                target="static_teacher",
                dataset_sha="a" * 64,
                position=dict(step=2, training_seen=8192),
                optimizer=dict(
                    state={
                        i: dict(
                            step=torch.tensor(7.0),
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
                    index_torch_state=torch.Generator().manual_seed(99).get_state(),
                    reflection_numpy_state=np.random.default_rng(98).bit_generator.state,
                    ordered_index_mask_sha256="c" * 64,
                ),
                static_continuation=dict(
                    identity=identity,
                    evaluation_complete_for_position=True,
                    last_observation=point,
                    old_executed=dict(logical_rows=80, draws=32, steps=8),
                    phase_draws=8192,
                    phase_steps=2,
                    phase_logical_rows=8200,
                    origin_position=dict(step=5, training_seen=20),
                    policy=policy.state,
                    selected_best=None,
                    optimizer_mode="matching",
                    exposure=dict(
                        rows=8192, shape=[1, 2], ref=static_checkpoint_ref(folder / "counter.u32")
                    ),
                ),
            )
            (folder / "weights.f32").write_bytes(
                b"".join(value.numpy().astype("<f4").tobytes() for value in model.values())
            )

            def bind(name):
                stream = io.BytesIO()
                torch.save(checkpoint, stream)
                (folder / name).write_bytes(stream.getvalue())
                self.assertLess(len(stream.getvalue()), 512 * 1024)
                return dict(
                    schema="quoridor-static-continuation-input-v1",
                    optimizer_mode="matching",
                    **identity,
                    checkpoint=static_checkpoint_ref(folder / name),
                    weights=static_checkpoint_ref(folder / "weights.f32"),
                    phase_steps=2,
                    phase_rows=8200,
                )

            actual = read_static_continuation(
                bind("block.pt"), cfg, corpus, checkpoint["scale"], panel, validation
            )
            self.assertEqual(
                (actual["previous_steps"], actual["previous_draws"], actual["previous_rows"]),
                (2, 8192, 8200),
            )
            self.assertEqual(actual["old_executed"]["logical_rows"], 80)
            checkpoint["static_continuation"]["evaluation_complete_for_position"] = False
            with self.assertRaisesRegex(ValueError, "completed fullV"):
                read_static_continuation(
                    bind("pending.pt"), cfg, corpus, checkpoint["scale"], panel, validation
                )
            checkpoint["static_continuation"]["evaluation_complete_for_position"] = True
            checkpoint["static_continuation"]["policy"]["verdict"] = "PRACTICAL_V_PLATEAU"
            with self.assertRaisesRegex(ValueError, "terminal policy"):
                read_static_continuation(
                    bind("terminal.pt"), cfg, corpus, checkpoint["scale"], panel, validation
                )

    def test_third_nonsignificant_decays_despite_tiny_strict_bests(self):
        policy = StaticContinuation(10, BASELINE)
        for index in range(1, 4):
            result = policy.observe(0.2 - index * 0.000001, 0.15, 10 * index)
            self.assertTrue(result["strict_improved"])
            self.assertFalse(result["significant_improved"])
            self.assertFalse(result["stop"])
            self.assertEqual(result["update_lr_used"], 0.0001)
        self.assertEqual(result["next_lr"], 0.00005)
        self.assertEqual(result["stale_at_lr"], 0)

    def test_floor_requires_both_eight_R_and_eight_consecutive_observations(self):
        policy = StaticContinuation(10, BASELINE)
        for index in range(1, 29):
            result = policy.observe(0.2, 0.15, 10 * index)
            self.assertFalse(result["stop"])
        result = policy.observe(0.2, 0.15, 290)
        self.assertEqual(result["verdict"], "PRACTICAL_V_PLATEAU")
        self.assertEqual(result["floor_entry_draws"], 210)
        self.assertEqual(result["floor_stale"], 8)

    def test_policy_round_trip_crosses_block_without_reset_or_duplicate_observation(self):
        first = StaticContinuation(10, BASELINE)
        for index in range(1, 17):
            first.observe(0.2, 0.15, index * 10)
        saved = json.loads(json.dumps(first.state))
        second = StaticContinuation(10, BASELINE, state=saved)
        expected = first.observe(0.2, 0.15, 170)
        self.assertEqual(second.observe(0.2, 0.15, 170), expected)
        with self.assertRaisesRegex(ValueError, "never repeat prior draws"):
            second.observe(0.2, 0.15, 170)

    def test_complete_original_custody_tuple_and_mixed_state_refusal(self):
        import torch

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            cfg = continuation_recipe(4, 2, device="cpu", threads=1, optimizer_mode="matching")
            model = {
                name: torch.zeros(shape, dtype=torch.float32)
                for name, shape in PARAMETER_SHAPES.items()
            }
            states = {
                index: dict(
                    step=torch.tensor(5.0),
                    exp_avg=torch.zeros(shape),
                    exp_avg_sq=torch.zeros(shape),
                )
                for index, shape in enumerate(PARAMETER_SHAPES.values())
            }
            checkpoint = dict(
                model=model,
                model_config=cfg["model"],
                scale=dict(mu_f32=0, sigma_f32=1),
                target="static_teacher",
                dataset_sha="a" * 64,
                position=dict(step=5, training_seen=20),
                optimizer=dict(
                    state=states,
                    param_groups=[
                        dict(
                            params=list(range(6)),
                            lr=0.0003,
                            betas=(0.9, 0.999),
                            eps=1e-8,
                            weight_decay=0,
                        )
                    ],
                ),
                static_RNG=dict(
                    index_torch_state=torch.Generator().manual_seed(77).get_state(),
                    reflection_numpy_state=np.random.default_rng(78).bit_generator.state,
                    ordered_index_mask_sha256="b" * 64,
                ),
            )
            stream = io.BytesIO()
            torch.save(checkpoint, stream)
            (folder / "best.pt").write_bytes(stream.getvalue())
            (folder / "weights.f32").write_bytes(
                b"".join(value.numpy().astype("<f4").tobytes() for value in model.values())
            )
            point = dict(
                step=5,
                training_seen=20,
                train=dict(rows=4, target_mse=0.15, actual_logical_rows=8),
                validation=dict(
                    rows=2,
                    target_mse=0.2,
                    actual_logical_rows=4,
                    group_kind="exact trueLR input class",
                ),
            )
            (folder / "curves.gz").write_bytes(gzip.compress((json.dumps(point) + "\n").encode()))
            (folder / "status.json").write_text(
                json.dumps(
                    dict(
                        status="COMPLETED",
                        model_state_status="LAST_COMPLETED_UPDATE",
                        samples=80,
                        training_seen=32,
                        step=8,
                    )
                )
            )
            (folder / "panel.json").write_text(
                json.dumps(dict(train=list(range(4)), dataset_sha="a" * 64))
            )
            corpus = SimpleNamespace(
                counts=dict(train=4, validation=2),
                input_ref=dict(id="synthetic-input"),
                binding=dict(
                    teacher_values=dict(id="synthetic-bank"), teacher="S", dataset_sha="a" * 64
                ),
            )
            (folder / "cache.gz").write_bytes(gzip.compress(json.dumps(corpus.binding).encode()))
            frozen = dict(
                artifacts_sha256={
                    "best.pt": static_checkpoint_ref(folder / "best.pt")["sha256"],
                    "cache-binding.json.gz": static_checkpoint_ref(folder / "cache.gz")["sha256"],
                },
                weights_sha=static_checkpoint_ref(folder / "weights.f32")["sha256"],
                dataset_sha="a" * 64,
                best_step=5,
                selected_exposure=dict(training_seen=20),
                best_validation_mse=0.2,
            )
            (folder / "freeze.json").write_text(json.dumps(frozen))
            producer = dict(
                status="TWO_ORIGINAL_FITS_COMPLETE_FIXED_HORIZON_NOT_CONVERGED",
                arms=dict(
                    S=dict(
                        curves=static_checkpoint_ref(folder / "curves.gz"),
                        status=static_checkpoint_ref(folder / "status.json"),
                        freeze=static_checkpoint_ref(folder / "freeze.json"),
                        models=dict(
                            best=dict(weights=static_checkpoint_ref(folder / "weights.f32"))
                        ),
                    )
                ),
            )
            (folder / "producer.json").write_text(json.dumps(producer))
            control = dict(
                schema="quoridor-static-continuation-input-v1",
                optimizer_mode="matching",
                input_classes=corpus.input_ref,
                teacher_values=corpus.binding["teacher_values"],
                teacher="S",
                dataset_sha="a" * 64,
                train_panel_sha256=observation_index_sha(np.arange(4)),
                validation_index_sha256=observation_index_sha(np.arange(4, 6)),
                checkpoint=static_checkpoint_ref(folder / "best.pt"),
                weights=static_checkpoint_ref(folder / "weights.f32"),
                baseline=dict(
                    producer_result=static_checkpoint_ref(folder / "producer.json"),
                    freeze=static_checkpoint_ref(folder / "freeze.json"),
                    cache_binding=static_checkpoint_ref(folder / "cache.gz"),
                    curves=static_checkpoint_ref(folder / "curves.gz"),
                    run_status=static_checkpoint_ref(folder / "status.json"),
                    diagnostic_subsets=static_checkpoint_ref(folder / "panel.json"),
                ),
            )
            result = read_static_continuation(
                control, cfg, corpus, checkpoint["scale"], np.arange(4), np.arange(4, 6)
            )
            self.assertEqual(result["origin_position"], dict(step=5, training_seen=20))
            self.assertEqual(result["old_executed"]["draws"], 32)
            self.assertEqual(result["previous_rows"], 0)
            wrong = copy.deepcopy(control)
            wrong["teacher"] = "C"
            with self.assertRaisesRegex(ValueError, "teacher/input/fullV/panel"):
                read_static_continuation(
                    wrong, cfg, corpus, checkpoint["scale"], np.arange(4), np.arange(4, 6)
                )
            # A foreign curve can carry plausible metrics, but is not the producer's
            # actual selected observation. A foreign bank can carry the same shape.
            (folder / "foreign.gz").write_bytes((folder / "curves.gz").read_bytes())
            wrong = copy.deepcopy(control)
            wrong["baseline"]["curves"] = static_checkpoint_ref(folder / "foreign.gz")
            with self.assertRaisesRegex(ValueError, "custody tuple"):
                read_static_continuation(
                    wrong, cfg, corpus, checkpoint["scale"], np.arange(4), np.arange(4, 6)
                )
            foreign = copy.deepcopy(corpus)
            foreign.binding["teacher_values"] = dict(id="foreign-bank")
            wrong = dict(control, teacher_values=foreign.binding["teacher_values"])
            with self.assertRaisesRegex(ValueError, "custody tuple"):
                read_static_continuation(
                    wrong, cfg, foreign, checkpoint["scale"], np.arange(4), np.arange(4, 6)
                )
            with self.assertRaisesRegex(ValueError, "model/scale/teacher"):
                read_static_continuation(
                    control, cfg, corpus, dict(mu_f32=1, sigma_f32=1), np.arange(4), np.arange(4, 6)
                )
            checkpoint["optimizer"]["state"][0]["step"] = torch.tensor(8.0)
            stream = io.BytesIO()
            torch.save(checkpoint, stream)
            (folder / "wrong.pt").write_bytes(stream.getvalue())
            wrong = dict(control, checkpoint=static_checkpoint_ref(folder / "wrong.pt"))
            # Keep the producer's binding coherent with this synthetic negative so
            # the rejection reaches the actual mismatched Adam state owner.
            frozen["artifacts_sha256"]["best.pt"] = wrong["checkpoint"]["sha256"]
            (folder / "freeze.json").write_text(json.dumps(frozen))
            producer["arms"]["S"]["freeze"] = static_checkpoint_ref(folder / "freeze.json")
            (folder / "producer.json").write_text(json.dumps(producer))
            wrong["baseline"] = dict(
                control["baseline"],
                freeze=static_checkpoint_ref(folder / "freeze.json"),
                producer_result=static_checkpoint_ref(folder / "producer.json"),
            )
            with self.assertRaisesRegex(ValueError, "matching Adam/RNG/selected"):
                read_static_continuation(
                    wrong, cfg, corpus, checkpoint["scale"], np.arange(4), np.arange(4, 6)
                )


if __name__ == "__main__":
    unittest.main()
