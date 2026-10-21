"""New metadata-only MCTS admission boundaries, with no actual corpus or model."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mcts_admission_common", HERE / "common.py")
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)


def reference(path, letter):
    return {"path": path, "sha256": letter * 64}


def manifest(mcts=True):
    cfg = {
        "families": 8,
        "prefix_seed": 3,
        "prefix_lengths": [4, 8],
        "split_seed": 5,
        "root_value_policy": "outcome_only",
        "schedule": reference("/toy/schedule.json", "a"),
        "partition": reference("/toy/partition.json", "b"),
        "batch_start": 2,
        "batch_count": 3,
        "excluded_books": [],
    }
    sources, bindings, batches, datasets = [], [], [], []
    for i, (start, count, rows) in enumerate(((2, 1, 3), (3, 2, 4))):
        dataset = f"/toy/dataset-{i}"
        ref = reference(dataset + "/manifest.json" if mcts else f"/toy/{i}.jsonl.gz", "cd"[i])
        bindings.append(ref)
        sources.append(
            {"encoding": "native-teacher-dataset-shards-v1", "manifest": copy.deepcopy(ref)}
            if mcts
            else {
                "encoding": "gzip-single-member-v1",
                "compressed": {**ref, "bytes": 100 + i, "mode": "0644"},
                "raw_sha256": "e" * 64,
                "raw_bytes": 200 + i,
            }
        )
        datasets.append({"dataset": dataset, "manifest_sha256": ref["sha256"], "rows": rows})
        batches.append(
            {
                "batch_start": start,
                "batch_count": count,
                "config": reference(f"/toy/config-{i}.json", "ef"[i]),
            }
        )
    result = {
        "schema": "quoridor-common-corpus-terminal-geometry-v3",
        "rows": 7,
        "common_corpus": {
            "config": cfg,
            "planned_families": 8,
            "raw_file": "completed-root-raw.f32",
            "common_mask_file": "common-eligible.u8",
            "sampling_file": "sampling.bin",
            "teacher_A": "actual_final_z",
            "rootmean_is_raw": mcts,
            "common_eligible_rows": 5,
            "common_eligible_by_split": {"train": 3, "validation": 2},
        },
        "source_content": sources,
        "source_binding": bindings,
        "stream_intake": {
            "status": "complete",
            "scope": "common-corpus",
            "publication_protocol": "incomplete-marker-last-v1",
            "batches": batches,
        },
        "schedule_sha256": "a" * 64,
        "family_partition_sha256": "b" * 64,
        "dataset_sha": "9" * 64,
    }
    if mcts:
        result.update(
            mcts_source={"model_sha256": "8" * 64, "completed_simulations": 64},
            mcts_datasets=datasets,
            mcts_native_configs=reference("/toy/ordered-config-list.json", "9"),
        )
    return result


class MctsCacheAdmissionNN0(unittest.TestCase):
    def reject(self, value):
        with self.assertRaises((ValueError, KeyError, TypeError)):
            common.common_cache_config(value)

    def test_mcts_native_metadata_without_body_reads_or_fake_alpha_content(self):
        value = manifest()
        # These are toy hashes, not a future runtime authority. The data-only
        # reader uses published metadata, without opening a dataset/config file.
        with (
            patch.object(Path, "read_bytes", side_effect=AssertionError("source body opened")),
            patch.object(Path, "open", side_effect=AssertionError("source opened")),
        ):
            self.assertIs(common.common_cache_config(value), value["common_corpus"]["config"])
        self.assertNotIn("model_scale_authority", value)
        self.assertNotIn("compressed", value["source_content"][0])
        for simulations in (1, 128):
            value["mcts_source"]["completed_simulations"] = simulations
            common.common_cache_config(value)

    def test_mcts_mode_model_and_native_config_ref_are_mandatory_and_typed(self):
        cases = []
        for key in ("mcts_source", "mcts_datasets", "mcts_native_configs"):
            x = manifest()
            del x[key]
            cases.append(x)
        for bad in (False, 1, None):
            x = manifest()
            x["common_corpus"]["rootmean_is_raw"] = bad
            cases.append(x)
        for bad in (0, True, -1, 2**32, 64.0):
            x = manifest()
            x["mcts_source"]["completed_simulations"] = bad
            cases.append(x)
        for bad in ("A" * 64, "x" * 64, "1" * 63):
            x = manifest()
            x["mcts_source"]["model_sha256"] = bad
            cases.append(x)
        for path in ("relative.json", ""):
            x = manifest()
            x["mcts_native_configs"]["path"] = path
            cases.append(x)
        x = manifest()
        x["mcts_native_configs"]["sha256"] = "0" * 64
        cases.append(x)
        x = manifest()
        x["mcts_source"]["extra"] = True
        cases.append(x)
        x = manifest()
        x["source_content"][0] = manifest(False)["source_content"][0]
        cases.append(x)
        x = manifest(False)
        x["common_corpus"]["rootmean_is_raw"] = True
        cases.append(x)
        for i, value in enumerate(cases):
            with self.subTest(case=i):
                self.reject(value)

    def test_mcts_order_dataset_row_census_and_actual_batch_union(self):
        cases = []
        for field in ("source_content", "source_binding", "mcts_datasets"):
            x = manifest()
            x[field].reverse()
            cases.append(x)
            x = manifest()
            x[field].pop()
            cases.append(x)
        x = manifest()
        x["mcts_datasets"][0]["rows"] += 1
        cases.append(x)
        for bad in (True, -1, 3.0):
            x = manifest()
            x["mcts_datasets"][0]["rows"] = bad
            cases.append(x)
        x = manifest()
        x["mcts_datasets"][0]["dataset"] = "relative"
        cases.append(x)
        x = manifest()
        x["mcts_datasets"][0]["manifest_sha256"] = "0" * 64
        cases.append(x)
        x = manifest()
        x["source_content"][0]["manifest"] = x["source_binding"][1]
        cases.append(x)
        x = manifest()
        x["source_content"][0]["raw_sha256"] = "a" * 64
        cases.append(x)
        x = manifest()
        x["source_content"][1] = copy.deepcopy(x["source_content"][0])
        x["source_binding"][1] = copy.deepcopy(x["source_binding"][0])
        x["mcts_datasets"][1]["dataset"] = x["mcts_datasets"][0]["dataset"]
        x["mcts_datasets"][1]["manifest_sha256"] = x["mcts_datasets"][0]["manifest_sha256"]
        cases.append(x)
        for start in (2, 4):
            x = manifest()
            x["stream_intake"]["batches"][1]["batch_start"] = start
            cases.append(x)
        x = manifest()
        x["stream_intake"]["batches"][1]["batch_count"] = 1
        cases.append(x)
        x = manifest()
        x["stream_intake"]["batches"][0]["config"]["path"] = "relative"
        cases.append(x)
        for i, value in enumerate(cases):
            with self.subTest(case=i):
                self.reject(value)

    def test_alpha_route_and_shared_scale_validation_remain_distinct(self):
        alpha = manifest(False)
        self.assertIs(common.common_cache_config(alpha), alpha["common_corpus"]["config"])
        for mcts in (False, True):
            value = manifest(mcts)
            authority = {
                "starting_weights_sha256": "1" * 64,
                "descriptor_sha256": "2" * 64,
                "evaluator_sha256": "3" * 64,
                "scale_policy": "incumbent_descriptor_T_only",
            }
            value["model_scale_authority"] = authority
            common.common_cache_config(value)
            for key, bad in (("descriptor_sha256", "not-a-sha"), ("scale_policy", "new_scale")):
                x = copy.deepcopy(value)
                x["model_scale_authority"][key] = bad
                self.reject(x)
            x = copy.deepcopy(value)
            x["model_scale_authority"]["extra"] = None
            self.reject(x)
        for edit in ("encoding", "compressed", "outcome", "schedule"):
            x = manifest(False)
            if edit == "encoding":
                x["source_content"][0]["encoding"] = "native-teacher-dataset-shards-v1"
            if edit == "compressed":
                x["source_content"][0]["compressed"]["sha256"] = "0" * 64
            if edit == "outcome":
                x["common_corpus"]["teacher_A"] = "raw"
            if edit == "schedule":
                x["schedule_sha256"] = "0" * 64
            self.reject(x)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(MctsCacheAdmissionNN0)
    )
    print(
        json.dumps(
            {
                "new_definitions": result.testsRun,
                "passed": result.wasSuccessful(),
                "real_forward_rows": 0,
                "real_model_imports": 0,
                "old_test_methods_run": 0,
            }
        )
    )
    raise SystemExit(0 if result.wasSuccessful() else 1)
