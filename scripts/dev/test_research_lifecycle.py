"""Owning lifecycle boundaries for bulk data and configured operation paths."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def load_lifecycle():
    path = Path(__file__).with_name("research-lifecycle.py")
    loader = importlib.util.spec_from_file_location("lifecycle_test", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


class LifecycleDataAndPaths(unittest.TestCase):
    def test_corpus_stream_is_hashed_without_control_buffer(self):
        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            stream = root / "terminal.stream"
            stream.write_bytes(b"\xff\x00\x80" * 1024)
            result = root / "generation.json"
            result.write_text(json.dumps({"scheduled": 1, "recorded": 0}))
            spec = {
                "owner": str(root),
                "data": [
                    {"name": "pilot_stream", "path": str(stream), "limit_B": 4096},
                    {"name": "generation_result", "path": str(result), "limit_B": 4096},
                ],
            }
            experiment = {
                "phase": "corpus",
                "argv": ["unused", "teacher-pilot"],
                "planned_slots": 1,
            }
            original_bound = lc.bound

            def bounded_control(path, *args, **kwargs):
                self.assertNotEqual(Path(path), stream, "bulk stream loaded as control")
                return original_bound(path, *args, **kwargs)

            with patch.object(lc, "bound", bounded_control):
                actual = lc.collect_data(spec, experiment)
            self.assertEqual(actual["status"], "PASS")
            self.assertEqual(actual["corpus"], {"scheduled": 1, "recorded": 0})
            self.assertIn(lc.artifact_ref(stream), actual["files"])
            self.assertFalse(actual["errors"])
            spec["data"][0]["limit_B"] = stream.stat().st_size - 1
            rejected = lc.collect_data(spec, experiment)
            self.assertEqual(rejected["status"], "FAILED")
            self.assertEqual(rejected["errors"][0]["stage"], "pilot_stream")

    def test_sequence_operation_stays_in_exact_nested_output(self):
        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            experiment = root / "experiment.json"
            experiment.write_text(
                json.dumps(
                    {
                        "phase": "corpus",
                        "argv": ["unused", "teacher-pilot", "@EXPERIMENT@"],
                    }
                )
            )
            template = {
                "kind": "run",
                "owner": str(root),
                "data_root": str(root / "data"),
                "experiment": lc.artifact_ref(experiment),
                "env": {},
                "finalizers": [],
            }
            selected_output = root / "nested" / "sequence"
            settings = root / "settings.json"
            settings.write_text(
                json.dumps(
                    {
                        "kind": "sequence",
                        "owner": str(root),
                        "output": str(selected_output),
                        "runs": [template],
                    }
                )
            )
            selected_ref = lc.artifact_ref(settings)
            actual_ref = lc.prepare_selected_operation(selected_ref, "run", 0)
            actual = lc.document(actual_ref)
            phase = selected_output / "run-000"
            self.assertEqual(Path(actual_ref["path"]), phase / "intent.json")
            self.assertEqual(actual["output"], str(phase / "operation"))
            self.assertEqual(actual["TMP"], str(phase / "TMP"))
            self.assertEqual(actual["data_root"], template["data_root"])
            self.assertFalse((root / "sequence").exists())
            with self.assertRaises(lc.Refused):
                lc.prepare_selected_operation(selected_ref, "run", 0)
            # An output outside the owner must fail before any operation is created.
            escaped = lc.document(selected_ref)
            escaped["output"] = str(root.parent / (root.name + "-escape"))
            outside = root / "outside-settings.json"
            outside.write_text(json.dumps(escaped))
            with self.assertRaises(lc.Refused):
                lc.prepare_selected_operation(lc.artifact_ref(outside), "run", 0)
            self.assertFalse(Path(escaped["output"]).exists())

    def test_fresh_fit_numerical_identity_binds_descriptor_config_and_seed(self):
        """Metadata-only; no model loader, payload or numerical execution."""
        lc = load_lifecycle()
        descriptor = {"path": "/descriptor", "sha256": "d" * 64, "bytes": 1, "mode": "0644"}
        warm = dict(
            descriptor=descriptor,
            weights=None,
            evaluator_sha256=None,
            optimizer="fresh",
            scale="incumbent",
        )
        config = dict(
            experiment=dict(study="mixed-outcome", warm_start=warm), training=dict(seed=42320261021)
        )
        model = dict(descriptor=descriptor, weights=None, evaluator_sha256=None)
        experiment = dict(
            phase="fit",
            config=dict(sha256="c" * 64),
            schedule=dict(sha256="s" * 64),
            inputs=[],
            models=[model],
            rules="rules",
            distance_units="unit",
            value_perspective="side-to-move",
            canonical_plan_sha256="p" * 64,
        )
        build = dict(artifact=dict(sha256="a" * 64))
        with patch.object(lc, "document", return_value=config):
            value = lc.numerical_fields(experiment, build)
            self.assertEqual(value["weights_sha256"], [None])
            self.assertEqual(value["evaluator_sha256"], [None])
            self.assertEqual(value["descriptor_sha256"], ["d" * 64])
            self.assertEqual(value["config_sha256"], "c" * 64)
            for field, invalid in (
                ("optimizer", "resume"),
                ("scale", "new"),
                ("weights", dict(sha256="w" * 64)),
                ("evaluator_sha256", "e" * 64),
            ):
                with self.subTest(field=field):
                    original = warm[field]
                    warm[field] = invalid
                    with self.assertRaises(lc.Refused):
                        lc.numerical_fields(experiment, build)
                    warm[field] = original
            for invalid in (True, None, "21"):
                config["training"]["seed"] = invalid
                with self.assertRaises(lc.Refused):
                    lc.numerical_fields(experiment, build)
            config["training"]["seed"] = 42320261021
            config["experiment"]["study"] = "other"
            with self.assertRaises(lc.Refused):
                lc.numerical_fields(experiment, build)
            config["experiment"]["study"] = "mixed-outcome"
            experiment["phase"] = "arena"
            with self.assertRaises(lc.Refused):
                lc.numerical_fields(experiment, build)
            experiment["phase"] = "fit"
            model["evaluator_sha256"] = "e" * 64
            with self.assertRaises(lc.Refused):
                lc.numerical_fields(experiment, build)
            model["weights"] = dict(sha256="w" * 64)
            value = lc.numerical_fields(experiment, build)
            self.assertEqual(value["weights_sha256"], ["w" * 64])
            self.assertEqual(value["evaluator_sha256"], ["e" * 64])

    def test_fresh_fit_ref_census_omits_absent_weights_after_normal_admission(self):
        """Isolate ref collection after synthetic prior admission; no actual run."""
        lc = load_lifecycle()
        descriptor = dict(path="/descriptor", sha256="d" * 64, bytes=1, mode="0644")
        config_ref = dict(path="/config", sha256="c" * 64, bytes=1, mode="0644")
        schedule = dict(path="/schedule", sha256="s" * 64, bytes=1, mode="0644")
        experiment = dict(
            schema=lc.EXPERIMENT_SCHEMA,
            phase="fit",
            build_manifest=dict(path="/build"),
            config=config_ref,
            schedule=schedule,
            inputs=[],
            models=[dict(descriptor=descriptor, weights=None, evaluator_sha256=None)],
            dynamic_libraries=[],
            planned_slots=0,
            argv=["python", "train"],
            numerical_qualification=None,
        )
        spec = dict(
            experiment=dict(path="/experiment"),
            artifact=dict(path="/image"),
            argv=["unused"] * 6 + ["/cache"],
        )
        config = dict(experiment=dict(study="mixed-outcome"))
        reads = []

        def document(ref):
            return experiment if ref is spec["experiment"] else config

        class RefsCollected(Exception):
            pass

        with (
            patch.object(lc, "charged_roots"),
            patch.object(lc, "document", side_effect=document),
            patch.object(lc, "experiment_phase_check"),
            patch.object(lc, "accepted_build", return_value=dict(artifact=spec["artifact"])),
            patch.object(lc, "caller_source_refs", return_value=[]),
            patch.object(lc, "common_study_check") as admission,
            patch.object(lc, "approved_plan", side_effect=[None, RefsCollected()]),
            patch.object(lc, "read_ref", side_effect=lambda ref, *_: reads.append(ref)),
        ):
            with self.assertRaises(RefsCollected):
                lc.experiment_check(spec)
        admission.assert_called_once()
        self.assertEqual(reads, [config_ref, schedule, descriptor])
        self.assertNotIn(None, reads)


if __name__ == "__main__":
    unittest.main()
