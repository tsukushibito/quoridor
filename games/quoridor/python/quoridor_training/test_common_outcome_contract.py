"""Owning metadata correspondence with the configured outcome producer; NN0."""

import copy
import unittest

from quoridor_training.common import common_cache_config


class CommonCacheContract(unittest.TestCase):
    def test_outcome_prefix_order_and_excluded_book_list_are_preserved(self):
        def ref(name):
            return {"path": "/synthetic/never-opened/" + name, "sha256": "a" * 64}

        cfg = {
            "families": 3,
            "prefix_seed": 1,
            "prefix_lengths": [12, 4, 8],
            "split_seed": 2,
            "root_value_policy": "outcome_only",
            "schedule": ref("schedule"),
            "partition": ref("partition"),
            "batch_start": 0,
            "batch_count": 3,
            "excluded_books": [ref("evaluation-book-1"), ref("evaluation-book-2")],
        }
        manifest = {
            "schema": "quoridor-common-corpus-terminal-geometry-v3",
            "rows": 2,
            "common_corpus": {
                "config": cfg,
                "planned_families": 3,
                "raw_file": "completed-root-raw.f32",
                "common_mask_file": "common-eligible.u8",
                "sampling_file": "sampling.bin",
                "teacher_A": "actual_final_z",
                "rootmean_is_raw": False,
                "common_eligible_rows": 2,
                "common_eligible_by_split": {"train": 1, "validation": 1},
            },
            "model_scale_authority": {
                "starting_weights_sha256": "b" * 64,
                "descriptor_sha256": "c" * 64,
                "evaluator_sha256": "d" * 64,
                "scale_policy": "incumbent_descriptor_T_only",
            },
            "stream_intake": {
                "status": "complete",
                "scope": "common-corpus",
                "publication_protocol": "incomplete-marker-last-v1",
                "batches": [{"batch_start": 0, "batch_count": 3, "config": ref("config")}],
            },
            "source_binding": [ref("stream")],
            "source_content": [
                {
                    "encoding": "gzip-single-member-v1",
                    "compressed": {**ref("stream"), "bytes": 32, "mode": "0644"},
                    "raw_sha256": "e" * 64,
                    "raw_bytes": 128,
                }
            ],
            "dataset_sha": "f" * 64,
            "schedule_sha256": "a" * 64,
            "family_partition_sha256": "a" * 64,
        }
        for books in ([], cfg["excluded_books"]):
            candidate = copy.deepcopy(manifest)
            candidate["common_corpus"]["config"]["excluded_books"] = books
            actual = common_cache_config(candidate)
            self.assertEqual(actual["prefix_lengths"], [12, 4, 8])
            self.assertEqual(actual["excluded_books"], books)
        for mutation in (
            {"prefix_lengths": [4, 4]},
            {"prefix_lengths": [True]},
            {"prefix_lengths": [None]},
            {"prefix_lengths": [{}]},
            {"excluded_books": ref("old-object-form")},
            {"excluded_books": ["not-a-bound-reference"]},
            {"excluded_books": [{"path": "missing-sha"}]},
        ):
            candidate = copy.deepcopy(manifest)
            candidate["common_corpus"]["config"].update(mutation)
            with self.assertRaises(ValueError):
                common_cache_config(candidate)
