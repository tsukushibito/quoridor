"""NEW changed-boundary fixtures; all corpus/selection/model facts are synthetic.

This definition is not a new science phase. The real maintained NumPy decoder,
sampler and Torch residual model/loss are exercised without existing model or
public payload reads. The single residual batch counts 64 logical forwards.
"""

import argparse
import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest


class ReplayBoundaries(unittest.TestCase):
    def test_parent_trusted_plan_config_input_and_output_boundary(self):
        from unittest.mock import patch
        from quoridor_training import public_replay

        with tempfile.TemporaryDirectory(prefix="fake-parent-fit-", dir=TMP) as temporary:
            root = Path(temporary)
            pilot = root / "pilot"
            compact = pilot / "cache-compact-v3"
            compact.mkdir(parents=True)

            def metadata(name, value):
                path = compact / name
                path.write_text(json.dumps(value))
                return self.ref(path)

            config = json.loads(CONFIG.read_bytes())
            ref = metadata("fit.json", config)
            second = metadata("second.json", config)
            widths = {
                "geometry.bin": 66,
                "distance-steps.u8": 2,
                "terminal-margin.f32": 4,
                "labels.f32": 8,
                "completed-root-raw.f32": 4,
                "common-eligible.u8": 1,
                "sampling.bin": 6,
            }
            binaries = []
            for name, width in widths.items():
                file = compact / name
                file.write_bytes(b"\0" * (341 * width))
                binaries.append(self.ref(file))
            cache = metadata(
                "cache.json",
                {
                    "rows": 341,
                    "schedule_sha256": "fake-schedule",
                    "family_partition_sha256": "fake-partition",
                    "source_binding": {"fake-source": True},
                    "sha256": {Path(r["path"]).name: r["sha256"] for r in binaries},
                    "file_bytes": {Path(r["path"]).name: r["bytes"] for r in binaries},
                },
            )
            public_dir = root / "public"
            public_dir.mkdir()
            public_path = public_dir / "cache.json"
            public_path.write_text(
                json.dumps(
                    {
                        "partitions": [
                            {"file": "train.bin"},
                            {"file": "validation.bin"},
                            {"file": "test-sealed.bin"},
                        ]
                    }
                )
            )
            public = self.ref(public_path)
            acceptance = metadata("accepted.json", {"synthetic": True})
            indices = metadata("indices.json", {"synthetic": True})
            plan = metadata("plan.json", {"synthetic": True})
            binding = {
                "selected_plan": plan,
                "fit_config_sha": ref["sha256"],
                "paired_fit_configs": [ref, second],
                "added_membership": cache,
                "public_membership": public,
                "public_acceptance": acceptance,
                "diagnostic_indices": indices,
                "schedule_sha256": "fake-schedule",
                "family_partition_sha256": "fake-partition",
                "dataset": {"fake-source": True},
            }
            binding_ref = metadata("binding.json", binding)
            interpreter = {
                "path": "/home/vscode/.cache/inference/python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14",
                "sha256": "5a91882290532b2719eaca77c0f3a7448bd73b9214e56df57bc59004560a80c6",
                "bytes": 32418544,
                "mode": "0755",
            }
            shared_python = Path("/home/vscode/.cache/inference/envs/quoridor-training/bin/python")
            pyvenv = self.ref(shared_python.parent.parent / "pyvenv.cfg")
            output = root / ".artifacts/public-replay371-v1/control-output"
            names = (
                "training.json",
                "curves.json",
                "curves.csv",
                "exposure.npz",
                "last.pt",
                "last-model/manifest.json",
                "last-model/weights.f32",
                "last-model/training-target.json",
            )
            argv = [
                str(shared_python),
                "-B",
                "-m",
                "quoridor_training.train",
                "train",
                "--cache",
                str(compact),
                "--output",
                str(output),
                "--config",
                ref["path"],
                "--input-binding",
                binding_ref["path"],
            ]
            spec = {
                "owner": str(root),
                "cwd": str(root),
                "env": {
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": str(root / "python"),
                    "OMP_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                },
                "approved_plan": plan,
                "argv": argv,
                "data_root": str(output),
                "data": [
                    {"name": Path(name).stem, "path": str(output / name), "limit_B": 1048576}
                    for name in names
                ],
            }
            warm = config["experiment"]["warm_start"]
            experiment = {
                "phase": "fit",
                "config": ref,
                "planned_slots": 0,
                "batch": None,
                "rules": "research-standard-2p-threefold-goal-first-v1",
                "distance_units": "wall-distance/80",
                "value_perspective": "side-to-move",
                "inputs": [
                    ref,
                    second,
                    binding_ref,
                    cache,
                    public,
                    acceptance,
                    indices,
                    *binaries,
                    interpreter,
                    pyvenv,
                ],
                "models": [
                    {
                        "descriptor": warm["descriptor"],
                        "weights": warm["weights"],
                        "evaluator_sha256": warm["evaluator_sha256"],
                    }
                ],
            }
            selected = {
                "public_replay_study": {
                    "issue": "quoridor-4lc.371",
                    "scientific_entry": True,
                    "paired_fit_configs": [ref, second],
                }
            }
            nodes = [
                n
                for n in ast.parse(PUBLISHER.read_bytes()).body
                if isinstance(n, ast.FunctionDef)
                and n.name
                in {"public_replay_fit_check", "project_interpreter", "common_training_environment"}
            ]
            namespace = {
                "PILOT_PLAN": Path(plan["path"]),
                "ROOT": root,
                "PILOT_DATA": pilot,
                "Path": Path,
                "COMPACT_CACHE_WIDTHS": widths,
                "require": self.require,
                "document": lambda r: json.loads(Path(r["path"]).read_bytes()),
                "project_python": lambda: shared_python,
                "numerical_check": lambda *_: None,
            }
            # Native/numerical and child admission are explicitly fake here.
            # Actual project interpreter input and environment predicates run unchanged.
            # Actual parent plan/ordered inputs/argv/model/output pins run unchanged.
            exec(
                compile(ast.Module(body=nodes, type_ignores=[]), str(PUBLISHER), "exec"), namespace
            )
            check = namespace["public_replay_fit_check"]
            with patch.object(public_replay, "admit", return_value=None) as child:
                check(spec, experiment, {}, selected)
                self.assertEqual(child.call_count, 1)
                child.reset_mock()
                for mutate in (
                    lambda s, e, p: s.update(approved_plan={**plan, "sha256": "0" * 64}),
                    lambda s, e, p: p["public_replay_study"].update(issue="quoridor-4lc.362"),
                    lambda s, e, p: e["inputs"].remove(indices),
                    lambda s, e, p: e["inputs"].remove(interpreter),
                    lambda s, e, p: e["inputs"].remove(pyvenv),
                    lambda s, e, p: e["inputs"][-2].update(sha256="0" * 64),
                    lambda s, e, p: s["env"].update(PYTHONPATH="/legacy/python"),
                    lambda s, e, p: s["argv"].__setitem__(0, "/wrong/python"),
                    lambda s, e, p: e["models"].clear(),
                    lambda s, e, p: s["data"].pop(),
                    lambda s, e, p: e.update(phase="analysis"),
                    lambda s, e, p: e["inputs"].append(
                        {
                            "path": str(public_dir / "test-sealed.bin"),
                            "sha256": "0" * 64,
                            "bytes": 66,
                            "mode": "0644",
                        }
                    ),
                ):
                    ss, ee, pp = copy.deepcopy((spec, experiment, selected))
                    mutate(ss, ee, pp)
                    with self.assertRaises(ValueError):
                        check(ss, ee, {}, pp)
                child.assert_not_called()

    @staticmethod
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def test_full_batches_and_same_added_prefix(self):
        from quoridor_training.sampling import FullBatchSampler
        import numpy as np

        control = FullBatchSampler(np.arange(217), 64, 36220261011)
        replay = FullBatchSampler(np.arange(217), 64, 36220261011)
        a = np.concatenate([control.take(64) for _ in range(200)])
        b = np.concatenate([replay.take(32) for _ in range(200)])
        self.assertEqual(a.shape, (12800,))
        self.assertEqual(b.shape, (6400,))
        np.testing.assert_array_equal(a[:6400], b)
        for start in range(0, len(a) - 216, 217):
            np.testing.assert_array_equal(np.sort(a[start : start + 217]), np.arange(217))
        self.assertEqual(control.seen, 12800)
        self.assertEqual(replay.seen, 6400)
        a_masks = np.random.default_rng(36220261012).random(12800) < 0.5
        b_masks = np.concatenate([np.random.default_rng(36220261012).random(6400) < 0.5])
        np.testing.assert_array_equal(a_masks[:6400], b_masks)
        public = np.random.default_rng(37120261012)
        draws = np.concatenate([public.integers(8413949, size=32) for _ in range(200)])
        self.assertEqual(draws.shape, (6400,))
        self.assertTrue(np.all((draws >= 0) & (draws < 8413949)))
        with self.assertRaises(ValueError):
            control.take(0)

    def test_real_indexed_codec_mixing_reflection_loss_and_split_isolation(self):
        import numpy as np
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        from quoridor_training.compact_cache import IndexedPublicCorpus, CompactCorpus
        from quoridor_training.public_features import RECORD, SCHEMA, features
        from quoridor_training.public_replay import mixed_batch, mixed_row_loss
        from quoridor_training.train import build_model

        with tempfile.TemporaryDirectory(prefix="synthetic-replay-", dir=TMP) as temporary:
            path = Path(temporary)
            records = np.zeros(66, dtype=RECORD)
            records["geometry"]["pawns"] = [40, 31]
            records["geometry"]["stocks"] = [10, 9]
            records["geometry"]["horizontal"] = np.uint64(1)
            records["distance"] = np.asarray([0.125, 0.25], dtype="<f4")
            records["z"] = 1
            records["row"] = np.arange(66)
            partitions = []
            for split in ("train", "validation"):
                p = path / (split + ".bin")
                records.tofile(p)
                partitions.append(
                    {
                        "name": split,
                        "file": p.name,
                        "rows": len(records),
                        "bytes": p.stat().st_size,
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    }
                )
            manifest = {
                "schema": SCHEMA,
                "dataset_revision": "original-full-v1",
                "original_only": True,
                "test_sealed": True,
                "record_bytes": 66,
                "source_shards": [{"rows": 132}] * 43,
                "partitions": partitions,
            }
            file = path / "cache.json"
            file.write_text(json.dumps(manifest))
            ref = self.ref(file)
            acceptance = {
                "public_membership": ref,
                "source_env_data_reader_STOP": datetime.datetime.now(datetime.UTC).isoformat(),
                "accepted_observations": {
                    "partitions": {
                        p["name"]: {"scanned": p["rows"], "stream_SHA256": p["sha256"]}
                        for p in partitions
                    }
                },
            }
            public = IndexedPublicCorpus(ref, acceptance)
            self.addCleanup(public.close)
            # Fake in-memory added metadata, using real inherited RECORD batch/features.
            added = object.__new__(CompactCorpus)
            added.maps = [records.copy()]
            added.offsets = np.array([0, 66])
            added.row_count = 66
            added.splits = np.zeros(66, dtype=np.uint8)
            added.splits[64] = 1
            added.eligible = np.ones(66, dtype=bool)
            added.eligible[65] = False
            added.labels = np.zeros((66, 2), dtype=np.float32)
            added.labels[:, 1] = -1
            ai, pi = np.arange(32), np.arange(32)
            mask = np.arange(64) % 2 == 0
            x, d, y = mixed_batch(added, public, ai, pi, mask)
            np.testing.assert_array_equal(y[:32], -np.ones(32, dtype=np.float32))
            np.testing.assert_array_equal(y[32:], np.ones(32, dtype=np.float32))
            np.testing.assert_array_equal(
                d.view("<u4"), np.tile(records["distance"][0], (64, 1)).view("<u4")
            )
            np.testing.assert_array_equal(
                x,
                np.concatenate(
                    (
                        features(records["geometry"][:32], mask[:32]),
                        features(records["geometry"][:32], mask[32:]),
                    )
                ),
            )
            config = {
                "architecture": "distance_residual",
                "transformer_width": 32,
                "hidden_width": 32,
                "dropout": 0,
                "distance_a": 0,
                "distance_b": 0,
            }
            torch.manual_seed(123)  # Synthetic weights, NOT BEST43/load/warm-start qualification.
            model = build_model(config, {"mu_f32": [0.0, 0.0], "sigma_f32": [1.0, 1.0]})
            with torch.no_grad():
                model.out.weight.zero_()
                model.out.bias.fill_(0.5)
            ReplayBoundaries.model_forward_rows += 64  # Prospective charge before the owning call.
            prediction = model(
                torch.from_numpy(x), torch.from_numpy(d), torch.ones(64, dtype=torch.int64)
            ).reshape(-1)
            target = torch.from_numpy(y)
            loss = mixed_row_loss(prediction, target)
            expected_loss = ((prediction - target) ** 2).sum() / 64
            self.assertEqual(loss.item(), expected_loss.item())
            loss.backward()
            expected_gradient = (
                2 * (prediction.detach() - target) * (1 - prediction.detach() ** 2)
            ).mean()
            self.assertAlmostEqual(model.out.bias.grad.item(), expected_gradient.item(), places=6)
            for invalid in (64, 65):
                bad = ai.copy()
                bad[0] = invalid
                with self.assertRaises(ValueError):
                    mixed_batch(added, public, bad, pi, mask)
            with self.assertRaises(ValueError):
                public.batch("validation", pi, mask[:32], training=True)
            with self.assertRaises(ValueError):
                public.records("test-sealed", pi)
            with self.assertRaises(ValueError):
                public.batch("validation", pi, mask[:32])
            public.verify_binding()
            with (path / "train.bin").open("ab") as stream:
                stream.write(b"x")
            with self.assertRaises(ValueError):
                public.verify_binding()
            stale = copy.deepcopy(acceptance)
            stale["source_env_data_reader_STOP"] = "2000-01-01T00:00:00+00:00"
            with self.assertRaises(ValueError):
                IndexedPublicCorpus(ref, stale)

    def test_selected_recipe_membership_before_framework_or_model_assets(self):
        from unittest.mock import patch
        from quoridor_training import public_replay
        from quoridor_training.common import resolve_config

        cfg = json.loads(CONFIG.read_bytes())
        cfg = resolve_config(cfg)
        with tempfile.TemporaryDirectory(prefix="fake-selected-replay-", dir=TMP) as temporary:
            root = Path(temporary)
            recipe = copy.deepcopy(cfg)
            recipe["experiment"]["condition"] = None
            study = {
                "issue": "quoridor-4lc.371",
                "scientific_entry": True,
                "common_learner_settings": recipe,
                "public_sampling_seed": 37120261012,
                "logical_forward_upper": 2000000,
                "planned_pair_forwards": 1649944,
                "comparison_checkpoint": "LAST200",
                "full_opened_validation": {"initial": "once_added_only", "last": "each"},
            }

            def metadata(name, value):
                p = root / name
                p.write_text(json.dumps(value))
                return self.ref(p)

            refs = []
            for arm in ("added_only", "replay"):
                c = copy.deepcopy(cfg)
                c["experiment"]["condition"] = arm
                refs.append(metadata(arm + ".json", c))
            study["paired_fit_configs"] = refs
            pub = metadata(
                "public.json",
                {
                    "partitions": [
                        {"name": "train", "rows": 8413949},
                        {"name": "validation", "rows": 419150},
                    ]
                },
            )
            added = metadata(
                "cache.json",
                {
                    "rows": 341,
                    "common_corpus": {"common_eligible_by_split": {"train": 217, "validation": 76}},
                },
            )
            accept = metadata(
                "acceptance.json",
                {
                    "issue": "quoridor-4lc.370",
                    "status": "ACCEPTED_FINITE_SAVED_PUBLIC_CORRESPONDENCE",
                    "accepted_observations": {"sealed_files_opened": []},
                    "public_membership": pub,
                    "query_membership": added,
                },
            )
            diagnostic = metadata("diagnostics.json", public_replay.frozen_diagnostics())
            for k, v in {
                "public_membership": pub,
                "public_acceptance": accept,
                "added_membership": added,
                "diagnostic_indices": diagnostic,
            }.items():
                study[k] = v
            plan = metadata("plan.json", {"public_replay_study": study})
            binding = {
                "selected_plan": plan,
                "paired_fit_configs": refs,
                "qualification_forward_rows": 64,
                **{
                    k: study[k]
                    for k in (
                        "public_membership",
                        "public_acceptance",
                        "added_membership",
                        "diagnostic_indices",
                    )
                },
            }
            inp = root / "input-binding.json"
            inp.write_text(json.dumps(binding))
            # Only unrelated descriptor/assets and completed-cache lineage hooks are fake.
            # Selected actual recipe, pair, indices, membership/ref SHA admission is real.
            with (
                patch.object(
                    public_replay, "warmstart_model_inputs", return_value={"synthetic": True}
                ) as model,
                patch.object(public_replay, "common_cache_config", return_value={}),
            ):
                result = public_replay.admit(root, refs[0]["path"], inp, cfg)
                self.assertEqual(result[3], {"synthetic": True})
                model.reset_mock()
                for section, key, value in (
                    ("optimizer", "lr", 0.002),
                    ("training", "seed", 42),
                    ("training", "target", "completed_root_raw"),
                    ("training", "batch_size", 32),
                    ("experiment", "condition", None),
                ):
                    bad = copy.deepcopy(cfg)
                    bad[section][key] = value
                    with self.assertRaises(ValueError):
                        public_replay.admit(root, refs[0]["path"], inp, bad)
                model.assert_not_called()
                b = copy.deepcopy(binding)
                b["qualification_forward_rows"] = 350057
                inp.write_text(json.dumps(b))
                with self.assertRaises(ValueError):
                    public_replay.admit(root, refs[0]["path"], inp, cfg)
                model.assert_not_called()

    @staticmethod
    def ref(path):
        raw = path.read_bytes()
        return {
            "path": str(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "mode": f"{path.stat().st_mode & 511:04o}",
        }


ReplayBoundaries.model_forward_rows = 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--publisher", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    import quoridor_training

    quoridor_training.__path__.insert(0, str(args.source_root))
    CONFIG, TMP, PUBLISHER = args.config, args.TMP, args.publisher
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReplayBoundaries)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forward_rows": ReplayBoundaries.model_forward_rows,
                "fit_updates": 0,
                "synthetic_weights_and_corpus": True,
                "failures": [text for _, text in result.failures],
                "errors": [text for _, text in result.errors],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
