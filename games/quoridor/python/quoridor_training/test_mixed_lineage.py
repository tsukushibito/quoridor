"""New stdlib owning aggregate outcome manifest boundary; all metadata synthetic."""

import argparse
import copy
import json
from pathlib import Path
import sys
import unittest


class AggregateLineage(unittest.TestCase):
    def test_configured_outcome_aggregate_arrays_interval_and_scale_metadata(self):
        from quoridor_training.common import common_cache_config

        def bound(name):
            return {"path": "/synthetic/never-read/" + name, "sha256": "a" * 64}

        cfg = {
            "families": 10,
            "prefix_seed": 5,
            "prefix_lengths": [4, 8],
            "split_seed": 6,
            "root_value_policy": "outcome_only",
            "schedule": bound("schedule"),
            "partition": bound("partition"),
            "batch_start": 2,
            "batch_count": 5,
            "excluded_books": [bound("books")],
        }

        def source(name):
            return {
                "encoding": "gzip-single-member-v1",
                "compressed": {**bound(name), "bytes": 20, "mode": "0644"},
                "raw_sha256": "b" * 64,
                "raw_bytes": 100,
            }

        c = {
            "config": cfg,
            "planned_families": 10,
            "raw_file": "completed-root-raw.f32",
            "common_mask_file": "common-eligible.u8",
            "sampling_file": "sampling.bin",
            "teacher_A": "actual_final_z",
            "rootmean_is_raw": False,
            "common_eligible_rows": 3,
            "common_eligible_by_split": {"train": 2, "validation": 1},
        }
        m = {
            "schema": "quoridor-common-corpus-terminal-geometry-v3",
            "rows": 4,
            "common_corpus": c,
            "model_scale_authority": {
                "starting_weights_sha256": "c" * 64,
                "descriptor_sha256": "d" * 64,
                "evaluator_sha256": "e" * 64,
                "scale_policy": "incumbent_descriptor_T_only",
            },
            "stream_intake": {
                "status": "complete",
                "scope": "common-corpus",
                "publication_protocol": "incomplete-marker-last-v1",
                "batches": [
                    {"batch_start": 2, "batch_count": 3, "config": bound("config1")},
                    {"batch_start": 5, "batch_count": 2, "config": bound("config2")},
                ],
            },
            "source_content": [source("stream1"), source("stream2")],
            "source_binding": [bound("stream1"), bound("stream2")],
            "dataset_sha": "f" * 64,
            "schedule_sha256": "a" * 64,
            "family_partition_sha256": "a" * 64,
        }
        self.assertEqual(common_cache_config(m), cfg)
        # One stream is still an array; no historical single-object fallback.
        single = copy.deepcopy(m)
        single["common_corpus"]["config"]["batch_count"] = 3
        for name in ("source_content", "source_binding"):
            single[name] = single[name][:1]
        single["stream_intake"]["batches"] = single["stream_intake"]["batches"][:1]
        common_cache_config(single)
        mutations = [
            lambda v: v["common_corpus"]["config"].update(root_value_policy="exclude_outside_unit"),
            lambda v: v["stream_intake"]["batches"][1].update(batch_start=4),
            lambda v: v["source_binding"].reverse(),
            lambda v: v["stream_intake"].update(status="incomplete"),
            lambda v: v.update(schedule_sha256="0" * 64),
            lambda v: v.update(family_partition_sha256="0" * 64),
            lambda v: v["common_corpus"]["common_eligible_by_split"].update(train=3),
            lambda v: v["model_scale_authority"].update(scale_policy="new_T"),
            lambda v: v.update(source_content=v["source_content"][0]),
            lambda v: v.update(dataset_sha="not-an-identity"),
        ]
        for mutation in mutations:
            bad = copy.deepcopy(m)
            mutation(bad)
            with self.assertRaises(ValueError):
                common_cache_config(bad)
        # Changing raw values never enters this metadata boundary; publication
        # owns exact FP32 bits and outcome eligibility, separately verified by381.2.
        self.assertEqual(cfg["root_value_policy"], "outcome_only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--TMP", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    import quoridor_training

    quoridor_training.__path__.insert(0, str(args.source))
    sys.modules.pop("quoridor_training.common", None)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AggregateLineage)
    )
    args.result.write_text(
        json.dumps(
            {
                "status": "PASS" if result.wasSuccessful() else "FAILED",
                "tests_run": result.testsRun,
                "actual_model_forwards": 0,
                "actual_fit_updates": 0,
                "synthetic_metadata_only": True,
                "errors": [s for _, s in result.errors],
                "failures": [s for _, s in result.failures],
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
