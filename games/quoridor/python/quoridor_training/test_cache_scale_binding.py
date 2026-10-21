"""New metadata-only admission boundary; all model/public bytes are labelled toys."""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from quoridor_training import common, public_replay as mixed


def write_ref(path, value):
    path.write_text(json.dumps(value) + "\n")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "mode": format(stat.S_IMODE(path.stat().st_mode), "04o"),
    }


def manifest():
    bound = {"path": "/synthetic-only/config.json", "sha256": "a" * 64}
    source = {"path": "/synthetic-only/rows.jsonl.gz", "sha256": "b" * 64}
    return {
        "schema": "quoridor-common-corpus-terminal-geometry-v3",
        "rows": 2,
        "common_corpus": {
            "config": {
                "families": 2,
                "prefix_seed": 17,
                "prefix_lengths": [4, 8],
                "split_seed": 18,
                "root_value_policy": "outcome_only",
                "schedule": bound,
                "partition": bound,
                "batch_start": 0,
                "batch_count": 2,
                "excluded_books": [],
            },
            "planned_families": 2,
            "raw_file": "completed-root-raw.f32",
            "common_mask_file": "common-eligible.u8",
            "sampling_file": "sampling.bin",
            "teacher_A": "actual_final_z",
            "rootmean_is_raw": False,
            "common_eligible_rows": 2,
            "common_eligible_by_split": {"train": 1, "validation": 1},
        },
        "stream_intake": {
            "status": "complete",
            "scope": "common-corpus",
            "publication_protocol": "incomplete-marker-last-v1",
            "batches": [{"batch_start": 0, "batch_count": 2, "config": bound}],
        },
        "source_content": [
            {
                "encoding": "gzip-single-member-v1",
                "compressed": {**source, "bytes": 5, "mode": "0644"},
                "raw_sha256": "c" * 64,
                "raw_bytes": 7,
            }
        ],
        "source_binding": [source],
        "schedule_sha256": "a" * 64,
        "family_partition_sha256": "a" * 64,
        "dataset_sha": "d" * 64,
    }


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix="cache-scale-nn0-", dir=Path(__file__).parent) as d:
        root = Path(d)
        cache = root / "cache"
        cache.mkdir()
        cache_ref = write_ref(cache / "cache.json", manifest())
        descriptor = write_ref(root / "descriptor.json", {"fixture": "not a model descriptor"})
        weights = write_ref(root / "weights.json", {"fixture": "not model weights"})
        warm = {"descriptor": descriptor, "weights": weights, "evaluator_sha256": "e" * 64}
        authority = {
            "starting_weights_sha256": weights["sha256"],
            "descriptor_sha256": descriptor["sha256"],
            "evaluator_sha256": warm["evaluator_sha256"],
            "scale_policy": "incumbent_descriptor_T_only",
        }
        public = write_ref(
            root / "public.json",
            {
                "partitions": [
                    {"name": "train", "rows": 7},
                    {"name": "validation", "rows": 3},
                ]
            },
        )
        acceptance = write_ref(root / "acceptance.json", {"public_membership": public})
        cfg = {"mixture": {"public_membership": public, "public_acceptance": acceptance}}
        config_path = root / "config.json"
        write_ref(config_path, cfg)
        binding = {
            "cache_manifest_sha256": cache_ref["sha256"],
            "model_scale_authority": authority,
            "files": {"cache_manifest": cache_ref, "descriptor": descriptor, "weights": weights},
        }
        binding_path = root / "binding.json"
        calls = []
        checked_files = []
        real_bound = common.bound_file_bytes

        def bound(ref, limit):
            checked_files.append(deepcopy(ref))
            return real_bound(ref, limit)

        def admit(value=binding):
            if value is not None:
                write_ref(binding_path, value)
            return mixed.admit(cache, config_path, binding_path if value is not None else None, cfg)

        stream = ModuleType("quoridor_training.distance_steps")
        stream.require_completed_stream_cache = lambda *args: calls.append("completed-stream")
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules, {stream.__name__: stream}))
            stack.enter_context(patch.object(common, "resolve_config", return_value=cfg))
            stack.enter_context(patch.object(mixed, "bound_file_bytes", side_effect=bound))
            stack.enter_context(
                patch.object(
                    mixed,
                    "warmstart_model_inputs",
                    side_effect=lambda c: {
                        "warm_start": warm,
                        "statistics": {"fixture": "already validated by owner"},
                    },
                )
            )
            yield root, cache, cfg, authority, binding, admit, calls, checked_files


class CacheScaleBindingNN0(unittest.TestCase):
    def test_data_only_read_still_validates_present_authority(self):
        value = manifest()
        self.assertEqual(common.common_cache_config(value), value["common_corpus"]["config"])
        for malformed in (None, [], {}, {"scale_policy": "recomputed"}):
            with self.subTest(malformed=malformed):
                bad = {**value, "model_scale_authority": malformed}
                with self.assertRaisesRegex(ValueError, "published initializer"):
                    common.common_cache_config(bad)
        bad = deepcopy(value)
        bad["common_corpus"]["common_eligible_by_split"]["train"] = 2
        with self.assertRaisesRegex(ValueError, "eligible census"):
            common.common_cache_config(bad)

    def test_fit_requires_exact_cache_or_bound_external_authority(self):
        with fixture() as (_, cache, _, authority, binding, admit, calls, checked):
            with self.assertRaisesRegex(ValueError, "cache/initializer/frozen-scale"):
                admit(None)
            admitted, _, counts, inputs = admit()
            self.assertNotIn("model_scale_authority", admitted)
            self.assertEqual(counts, {"train": 7, "validation": 3})
            self.assertEqual(inputs["warm_start"]["weights"], binding["files"]["weights"])
            self.assertIn(binding["files"]["cache_manifest"], checked)
            value = manifest()
            value["model_scale_authority"] = authority
            write_ref(cache / "cache.json", value)
            self.assertEqual(admit(None)[0]["model_scale_authority"], authority)
            self.assertEqual(len(calls), 3)

    def test_unbound_drifted_conflicting_and_malformed_authority_refuse(self):
        with fixture() as (root, cache, _, authority, original, admit, _, _):
            variants = []
            for key in ("cache_manifest_sha256", "model_scale_authority"):
                bad = deepcopy(original)
                del bad[key]
                variants.append(bad)
            for key in ("cache_manifest", "descriptor", "weights"):
                bad = deepcopy(original)
                del bad["files"][key]
                variants.append(bad)
            bad = deepcopy(original)
            bad["files"]["cache_manifest"] = write_ref(root / "other-cache.json", manifest())
            variants.append(bad)
            for key, value in (("descriptor_sha256", "f" * 64), ("scale_policy", "recomputed")):
                bad = deepcopy(original)
                bad["model_scale_authority"][key] = value
                variants.append(bad)
            for value in (None, {}, []):
                bad = deepcopy(original)
                bad["model_scale_authority"] = value
                variants.append(bad)
            bad = deepcopy(original)
            bad["files"]["weights"]["sha256"] = "f" * 64
            variants.append(bad)
            for i, bad in enumerate(variants):
                with self.subTest(case=i), self.assertRaises(ValueError):
                    admit(bad)
            cached = manifest()
            cached["model_scale_authority"] = {**authority, "evaluator_sha256": "f" * 64}
            updated = deepcopy(original)
            updated["files"]["cache_manifest"] = write_ref(cache / "cache.json", cached)
            updated["cache_manifest_sha256"] = updated["files"]["cache_manifest"]["sha256"]
            with self.assertRaisesRegex(ValueError, "cache/initializer/frozen-scale"):
                admit(updated)

    def test_same_external_authority_keeps_bound_shared_initial_and_zero_remeasurement(self):
        with fixture() as (root, _, cfg, _, binding, admit, _, checked):
            initial = write_ref(
                root / "initial-observation.json",
                {
                    "fixture": "saved initial observation, not real predictions",
                },
            )
            binding["files"]["initial_observation"] = initial
            admit(binding)
            self.assertIn(initial, checked)
            cfg["mixture"].update(added_exposures=1, added_rows=1, public_rows=1)
            cfg["training"] = {"steps": 1, "batch_size": 2}
            cfg["evaluation"] = {
                "checkpoints": [0, 1],
                "diagnostic_checkpoints": None,
                "full_train_checkpoints": [],
                "full_train": False,
                "diagnostic_rows": 1,
            }
            plan = mixed.planned_work(cfg, 1, 1, {"train": 7, "validation": 3}, reuse_initial=True)
            self.assertEqual(plan["measurement_rows_by_step"], {0: 0, 1: 6})
            self.assertEqual(plan["forward_upper"], 8)
            self.assertTrue(plan["reused_initial"])
        self.assertNotIn("torch", sys.modules)


if __name__ == "__main__":
    unittest.main()
