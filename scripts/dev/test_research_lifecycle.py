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
    def test_measurement_and_callback_arena_caller_membership(self):
        lc = load_lifecycle()
        root = lc.ROOT
        base = [
            dict(path=str(root / name))
            for name in (
                "scripts/dev/research-lifecycle.py",
                "scripts/dev/research-job.py",
                "python/quoridor_training/cycle_process.py",
                "python/quoridor_training/snapshot.py",
            )
        ]
        # Membership fixtures leave production read_ref and byte/hash checks intact.
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            cfg.write_text(json.dumps(dict(profile="control", roots=[])))
            config_ref = lc.bound(cfg)[0]
            measurement = dict(phase="compare", argv=["/fake/native", "measure"], config=config_ref)
            self.assertEqual(lc.caller_source_refs(dict(caller_sources=base), measurement), base)
            callback = base + [
                dict(path=str(root / "python/quoridor_training/claustrophobia.py")),
                dict(path=str(root / "python/quoridor_training/static_teacher_heads.py")),
                dict(path=str(lc.project_python().resolve(strict=True))),
                dict(path=str(lc.project_python().parent.parent / "pyvenv.cfg")),
            ]
            with self.assertRaises(lc.Refused):
                lc.caller_source_refs(dict(caller_sources=callback), measurement)
            cfg.write_text(
                json.dumps(dict(engines=[dict(kind="claustrophobia"), dict(kind="fixed-distance")]))
            )
            config_ref = lc.bound(cfg)[0]
            for phase, command in [("arena", "arena"), ("compare", "decisions")]:
                experiment = dict(phase=phase, argv=["/fake/native", command], config=config_ref)
                self.assertEqual(
                    lc.caller_source_refs(dict(caller_sources=callback), experiment), callback
                )
                with self.assertRaises(lc.Refused):
                    lc.caller_source_refs(dict(caller_sources=base), experiment)
            cfg.write_text(json.dumps(dict(engines=[dict(kind="fixed-distance")] * 2)))
            config_ref = lc.bound(cfg)[0]
            arena = dict(phase="arena", argv=["/fake/native", "arena"], config=config_ref)
            self.assertEqual(lc.caller_source_refs(dict(caller_sources=base), arena), base)
            with self.assertRaises(lc.Refused):
                lc.caller_source_refs(
                    dict(caller_sources=base + [dict(path="/unexpected/extra.py")]), arena
                )

    def test_prior_software_uses_original_receipts_and_rejects_partial_checks(self):
        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source.rs"
            source.write_text("// qualified source\n")
            log = root / "test.log"
            log.write_text("one bounded test passed\n")
            argv = ["cargo", "test", "--offline", "--locked", "-j1"]
            check = dict(
                name="new-boundary",
                role="run",
                argv=argv,
                status="PASS",
                capture_complete=True,
                primary=None,
                secondary=[],
                full_log=lc.artifact_ref(log),
                guardian_return=dict(
                    command=argv,
                    exit_code=0,
                    direct_child_reaped=True,
                    cleanup_complete=True,
                    handle_closes_complete=True,
                    remaining=[],
                ),
            )
            receipt = root / "receipt.json"
            adoption = root / "adoption.json"

            def bind():
                receipt.write_text(json.dumps(dict(checks=[check], primary=None)))
                adoption.write_text(
                    json.dumps(
                        dict(
                            schema="quoridor.research.source-adoption.v1",
                            status="ACCEPTED",
                            prior_software=dict(
                                subjects=[lc.artifact_ref(source)],
                                receipts=[dict(file=lc.artifact_ref(receipt), name=check["name"])],
                            ),
                        )
                    )
                )
                return lc.artifact_ref(adoption)

            ref = bind()
            self.assertEqual(lc.prior_software_roles(ref, current_sources=True), {"test"})
            for key, value in (
                ("capture_complete", False),
                ("status", "FAILED"),
                ("secondary", [{"stage": "publication"}]),
            ):
                previous = check[key]
                check[key] = value
                with self.assertRaises(lc.Refused):
                    lc.prior_software_roles(bind())
                check[key] = previous
            for key in ("direct_child_reaped", "cleanup_complete", "handle_closes_complete"):
                check["guardian_return"][key] = False
                with self.assertRaises(lc.Refused):
                    lc.prior_software_roles(bind())
                check["guardian_return"][key] = True
            ref = bind()
            source.write_text("// changed source\n")
            with self.assertRaises(lc.Refused):
                lc.prior_software_roles(ref, current_sources=True)
            # Historical BUILD consumption uses the frozen source adoption;
            # it does not require current Main to retain those old source bytes.
            self.assertEqual(lc.prior_software_roles(ref), {"test"})
            log.write_text("changed log\n")
            with self.assertRaises(lc.Refused):
                lc.prior_software_roles(ref)

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


class ConfiguredArenaPlanSelection(unittest.TestCase):
    def test_two_configured_arena_plans_keep_exact_authority_and_refuse_cross_selection(self):
        """Metadata only: distinct finite plans use existing RUN custody in both owners."""
        import copy

        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            support = root / "support.json"
            support.write_text(json.dumps(dict(resources=dict(family_RAM_B=1024**3))))
            runs = []
            for i, count in enumerate((128, 32)):
                plan = root / f"plan-{i}.json"
                plan.write_text(json.dumps(dict(planned_slots=count, phase="arena")))
                plan_ref = lc.artifact_ref(plan)
                experiment = root / f"experiment-{i}.json"
                experiment.write_text(
                    json.dumps(
                        dict(
                            phase="arena",
                            argv=["native", "arena"],
                            batch=0,
                            canonical_plan_sha256=plan_ref["sha256"],
                            planned_slots=count,
                        )
                    )
                )
                runs.append(
                    dict(
                        kind="run",
                        owner=str(root),
                        writer="same-owner",
                        cwd=str(root),
                        output=str(root / f"operation-{i}"),
                        data_root=str(root / f"data-{i}"),
                        data=[],
                        finalizers=[],
                        env={},
                        caller_sources=[],
                        artifact=dict(path="/native"),
                        experiment=lc.artifact_ref(experiment),
                        approved_plan=plan_ref,
                        support=lc.artifact_ref(support),
                        limits=dict(
                            family_B=1024**3,
                            controller_B=64 * 1024**2,
                            host_reserve_B=4 * 1024**3,
                            log_B=1024,
                            owned_B=None,
                            free_B=None,
                        ),
                    )
                )
            settings = root / "settings.json"
            settings.write_text(json.dumps(dict(kind="sequence", arena=None, runs=runs)))
            settings_ref = lc.artifact_ref(settings)
            for i in range(2):
                spec = dict(runs[i], settings=settings_ref, selection_index=i)
                experiment = lc.document(spec["experiment"])
                expected = lc.document(spec["approved_plan"])
                self.assertEqual(lc.approved_plan(spec, experiment), expected)
                self.assertIsInstance(lc.Limits(spec), lc.Limits)
                cross = dict(spec, selection_index=1 - i)
                for action in (
                    lambda: lc.approved_plan(cross, experiment),
                    lambda: lc.Limits(cross),
                ):
                    with self.assertRaises(lc.Refused):
                        action()
                drift = copy.deepcopy(spec)
                drift["limits"]["log_B"] += 1
                with self.assertRaises(lc.Refused):
                    lc.Limits(drift)
                wrong_plan = dict(experiment, canonical_plan_sha256="0" * 64)
                with self.assertRaises(lc.Refused):
                    lc.approved_plan(spec, wrong_plan)
                legacy = root / f"legacy-{i}.json"
                legacy.write_text(
                    json.dumps(dict(kind="sequence", arena=dict(range=[0, 0], template=runs[i])))
                )
                legacy_spec = dict(runs[i], settings=lc.artifact_ref(legacy))
                self.assertEqual(lc.approved_plan(legacy_spec, experiment), expected)
                self.assertIsInstance(lc.Limits(legacy_spec), lc.Limits)


if __name__ == "__main__":
    unittest.main()
