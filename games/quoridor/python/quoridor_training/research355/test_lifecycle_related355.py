"""Only new stopped related-v2 field joins; no actual builds or saved science."""

from pathlib import Path
import tempfile
import unittest
from unittest import mock

import lifecycle355 as life
import stream355
from test_lifecycle355 import ref

HERE = Path(__file__).resolve().parent


class RelatedLifecycle(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="synthetic-related-v10-", dir=HERE)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def compare_views(self):
        book = {"source_book_SHA256": "d" * 64}
        index = {
            "engineering_intent": "header",
            "engineering_plan": "config",
            "engineering_footer": "footer",
        }
        config_ref = ref(self.root / "config", "b" * 64)
        build_ref = ref(self.root / "manifest.json", "c" * 64)
        experiment = {"phase": "compare", "config": config_ref}
        completed = {
            "experiment": ref(self.root / "experiment", "e" * 64),
            "build_manifest": build_ref,
        }
        documents = {
            "header": {
                "schema": "quoridor.value-search-strength.compare-intent.v2",
                "experiment_sha256": "e" * 64,
                "config_sha256": "b" * 64,
                "build_manifest": build_ref,
            },
            "config": {
                "schema": "quoridor.value-search-strength.compare.v2",
                "canonical_plan": {"sha256": stream355.s.PLAN_SHA},
                "book": {"sha256": "d" * 64},
            },
            "footer": {
                "schema": "quoridor.value-search-strength.compare-result.v2",
                "experiment_sha256": "e" * 64,
                "config_sha256": "b" * 64,
                "book_sha256": "d" * 64,
                "fixed_denominator": {
                    "matched_positions": 32,
                    "natural4": 96,
                    "common_trees": 8,
                    "stronger_max_cases": 16,
                },
                "outputs": [],
            },
        }
        inputs = mock.Mock()
        inputs.get.side_effect = documents.__getitem__
        inputs.refs = {
            "config": {
                "path": config_ref["path"],
                "SHA256": config_ref["sha256"],
                "bytes": 1,
                "mode": "0644",
            }
        }
        return index, inputs, {"footer": (completed, experiment)}, book, documents

    def test_explicit_compare_hash_domains_and_retired_ambiguous_field(self):
        index, inputs, available, book, documents = self.compare_views()
        header, footer = stream355.compare_binding(index, inputs, available, book)
        self.assertEqual(header["experiment_sha256"], footer["experiment_sha256"])
        self.assertEqual(header["config_sha256"], footer["config_sha256"])
        for changes in (
            {"experiment_sha256": "b" * 64},
            {"config_sha256": "e" * 64},
            {"schema": "quoridor.value-search-strength.compare-result.v1"},
            {"plan_sha256": "e" * 64},
        ):
            original = documents["footer"]
            documents["footer"] = dict(original, **changes)
            with self.assertRaises(ValueError):
                stream355.compare_binding(index, inputs, available, book)
            documents["footer"] = original

    def test_current_footer_census_reuses_already_available_rows(self):
        index, inputs, available, book, documents = self.compare_views()
        documents["footer"].update(
            matched_census={"SYNTHETIC": True},
            stronger_census={"SYNTHETIC": True},
            whole_phase_until_footer_seconds=0.01,
        )
        matched, stronger = [{"SYNTHETIC": "matched"}], [{"SYNTHETIC": "stronger"}]
        summary = {"matched_available_rows": matched, "stronger_available_rows": stronger}
        with mock.patch.object(
            stream355.producer, "census", return_value={"SYNTHETIC": "count"}
        ) as census:
            stream355.compare_footer(index, inputs, None, available, book, summary)
        self.assertIs(census.call_args_list[0].args[1], matched)
        self.assertIs(census.call_args_list[1].args[1], stronger)
        self.assertEqual(summary["engineering_census"]["experiment_SHA256"], "e" * 64)
        self.assertEqual(summary["engineering_census"]["config_SHA256"], "b" * 64)
        self.assertEqual(
            [call.args[0] for call in inputs.get.call_args_list], ["header", "config", "footer"]
        )

    def test_wrong_result_hash_domains_refuse_before_book_and_outcomes(self):
        index, inputs, available, book, documents = self.compare_views()
        completed, experiment = available["footer"]
        files = dict(inputs.refs)
        for name in ("book", "schedule", "header", "footer"):
            file = ref(self.root / name, "d" * 64 if name == "book" else "a" * 64)
            files[name] = {
                "path": file["path"],
                "SHA256": file["sha256"],
                "bytes": 1,
                "mode": "0644",
            }
        inputs.refs = files
        completed.update(
            status="PASS",
            cleanup_complete=True,
            remaining=[],
            primary=None,
            secondary=[],
            checks=[{"guardian_return": None}],
            owed_finalizers=[],
            data={
                "files": [
                    {
                        "path": files[name]["path"],
                        "sha256": files[name]["SHA256"],
                        "bytes": 1,
                        "mode": "0644",
                    }
                    for name in ("header", "footer")
                ],
                "errors": [],
            },
        )
        analysis = {
            "inputs": [
                {
                    "path": file["path"],
                    "sha256": file["SHA256"],
                    "bytes": file["bytes"],
                    "mode": file["mode"],
                }
                for file in files.values()
            ]
        }
        index.update(
            book="book",
            schedule="schedule",
            build_manifest=completed["build_manifest"],
            producer_completions=[ref(self.root / "completion")],
        )
        documents["header"]["config_sha256"] = "e" * 64
        with (
            mock.patch.object(life, "finalized_input", return_value=(completed, experiment)),
            mock.patch.object(life, "numerical"),
        ):
            with self.assertRaises(ValueError):
                stream355.scientific_inputs(
                    index, inputs, mock.Mock(), completed["build_manifest"], {}, analysis
                )
        self.assertEqual(
            [call.args[0] for call in inputs.get.call_args_list], ["header", "config", "footer"]
        )
        self.assertNotIn("book", [call.args[0] for call in inputs.get.call_args_list])
