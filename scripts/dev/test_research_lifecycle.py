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
    def test_native_search_team_cpu_family_is_total_not_per_engine(self):
        lc = load_lifecycle()
        config = dict(
            search_threads=2,
            search_cpu_cores=[12, 14],
            management_cpu_core=0,
            native_memory_bytes=2684354560,
        )
        experiment = dict(phase="compare", argv=["/native", "measure"], config=config)
        resources = dict(CPU=3, threads=1, GPU=0, controller_included=True, family_RAM_B=4294967296)
        spec = dict(
            kind="run",
            experiment=experiment,
            support=dict(resources=resources),
            limits=dict(
                worker_cpu=12,
                guardian_cpu=0,
                family_B=4294967296,
                controller_B=1610612736,
            ),
            child_cpu_cores=[0, 12, 14],
        )
        with (
            patch.object(lc, "document", side_effect=lambda ref: ref),
            patch.object(lc, "measurement_config", return_value=(config, [])),
            patch.object(lc, "arena_cohort", return_value=None),
        ):
            self.assertEqual(lc.native_cpu_cores(spec), [0, 12, 14])
            for key, value in [("CPU", 2), ("family_RAM_B", 5368709120)]:
                old = resources[key]
                resources[key] = value
                with self.assertRaises(lc.Refused):
                    lc.native_cpu_cores(spec)
                resources[key] = old
            config["search_cpu_cores"] = [12, 12]
            with self.assertRaises(lc.Refused):
                lc.native_cpu_cores(spec)
            config["search_cpu_cores"] = [12, 14]
            arena = dict(
                arena=dict(comparison="search_wall_time"),
                workers=1,
                active_games=1,
                max_batch=1,
                cpu_cores=[12, 12],
                management_cpu_core=0,
                engines=[
                    dict(
                        kind="distance",
                        ordering_profile="control",
                        search_threads=2,
                        search_cpu_cores=[12, 14],
                    )
                ]
                * 2,
            )
            experiment.update(phase="arena", argv=["/native", "arena"], config=arena)
            self.assertEqual(lc.native_cpu_cores(spec), [0, 12, 14])
            arena["workers"] = 2
            with self.assertRaises(lc.Refused):
                lc.native_cpu_cores(spec)

    def test_measurement_and_callback_arena_caller_membership(self):
        lc = load_lifecycle()
        root = lc.ROOT
        base = [
            dict(path=str(root / name))
            for name in (
                "scripts/dev/research-lifecycle.py",
                "scripts/dev/research-job.py",
                "shared/python/quoridor_runtime/__init__.py",
                "shared/python/quoridor_runtime/cycle_process.py",
                "shared/python/quoridor_runtime/snapshot.py",
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
                dict(path=str(root / "games/quoridor/python/quoridor_training/claustrophobia.py")),
                dict(
                    path=str(
                        root / "games/quoridor/python/quoridor_training/static_teacher_heads.py"
                    )
                ),
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

    def test_completed_node_sharing_provenance_is_explicit_team_only(self):
        lifecycle = load_lifecycle()
        config = {
            "roots": [
                {"input": 0, "pointer": "/families/0", "field": "prefix", "label": "software-only"}
            ],
            "profile": "control",
            "tt_entries": 17,
            "use_tt": True,
            "use_pvs": True,
            "namespace": {
                "evaluator": "software-only",
                "rules": "research-standard-2p-threefold-goal-first-v1",
                "selectivity": "PVS",
            },
            "output_bytes": 1048576,
            "record_bytes": 32768,
        }
        requests = [
            {"id": "node-publication", "session": "one", "root": 0, "depth": 1, "node_cap": 64}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def experiment():
                cp = root / "config.json"
                cp.write_text(json.dumps(config))
                rp = root / "requests.json"
                rp.write_text(json.dumps(requests))
                return {
                    "config": lifecycle.bound(cp)[0],
                    "schedule": lifecycle.bound(rp)[0],
                    "inputs": [{}],
                    "models": [],
                    "rules": "research-standard-2p-threefold-goal-first-v1",
                }

            lifecycle.measurement_config(experiment())
            config["smp_sharing_provenance"] = False
            lifecycle.measurement_config(experiment())
            config["smp_sharing_provenance"] = True
            with self.assertRaises(lifecycle.Refused):
                lifecycle.measurement_config(experiment())
            config.update(
                search_threads=2,
                search_cpu_cores=[12, 14],
                management_cpu_core=0,
                native_memory_bytes=2684354560,
            )
            lifecycle.measurement_config(experiment())
            for wrong in (None, 1, "on"):
                config["smp_sharing_provenance"] = wrong
                with self.assertRaises(lifecycle.Refused):
                    lifecycle.measurement_config(experiment())


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

    def test_arena_probcut_actual_fp32_namespace_and_off_correspondence(self):
        import copy

        lc = load_lifecycle()
        p = dict(
            shallow_depth=1,
            deep_depth=3,
            slope=1.0,
            intercept=-0.02,
            margin=0.1,
            nonterminal_abs_bound=1.0,
            terminal_utility=2.0,
            calibration_sha256="a" * 64,
        )
        # Literal native FP32 namespace: this expectation does not call the reader helper.
        base = "distance-tanh-f32:sha256:" + "b" * 64 + ":simd=false"
        suffix = ":probcut13-v1:3f800000:bca3d70a:3dcccccd:3f800000:40000000:" + "a" * 64
        typed = dict(p, intercept=-0.019999999552965164, margin=0.10000000149011612)
        report = {
            k: 0
            for k in (
                "eligible_after_TT",
                "matching_nonPV_after_TT",
                "threshold_outside_domain",
                "shallow_probes",
                "shallow_nodes",
                "shallow_evaluations",
                "predicted_cuts_ALL",
                "probe_aborts",
                "terminal_probe_rejects",
                "diagnostic_explicit_child_calls",
                "diagnostic_nodes_in_parent_budget",
                "diagnostic_evaluations",
            )
        }
        report["samples"] = []
        engine = dict(
            kind="distance",
            simd=False,
            depth=3,
            ordering_profile="control",
            lmr=False,
            zero_stock_safe_race=False,
        )
        config = dict(
            engines=[engine],
            arena=dict(
                comparison="evaluator_fixed_depth",
                evaluator_sha256=["b" * 64],
                decision_only=True,
            ),
        )
        counters = dict(
            actual_search_namespace=dict(
                evaluator=base,
                rules="research-standard-2p-threefold-goal-first-v1",
                selectivity="control",
            ),
            requested_lmr_method="depth_rank",
            actual_lmr_method_id=None,
            lmr_reduction_rule=None,
            requested_lmr_parameters=None,
            actual_lmr_parameters=None,
            actual_lmr_enabled=False,
            actual_zero_stock_safe_race_enabled=False,
            requested_zero_stock_safe_race_method="path_tail",
            actual_zero_stock_safe_race_method_id=None,
            completed_snapshot_validation_failed=False,
            whole_search={},
            requested_probcut=None,
            actual_probcut=None,
        )
        obs = dict(
            engine_index=0,
            caller_seconds=0.01,
            thinking_seconds=0.01,
            value_stm=0.0,
            accepted=True,
            failure=None,
            engine_error=None,
            action=1,
            accepted_ns=3,
            admission_checked_ns=2,
            returned_ns=1,
            deadline_ns=None,
            completed_depth=3,
            pv=[1],
            stop="depth_cap",
            counters=counters,
            completed_iteration_counters={},
        )
        row = dict(observations=[obs])
        lc.arena_observation(config, row)
        # Old OFF records may omit both new fields, never actual ProbCut work.
        legacy = copy.deepcopy(row)
        legacy_obs = legacy["observations"][0]
        for key in ("requested_probcut", "actual_probcut"):
            del legacy_obs["counters"][key]
        lc.arena_observation(config, legacy)
        for work in (
            legacy_obs["counters"]["whole_search"],
            legacy_obs["completed_iteration_counters"],
        ):
            for hidden in ({}, None):
                work["probcut"] = hidden
                with self.assertRaises(lc.Refused):
                    lc.arena_observation(config, legacy)
                del work["probcut"]
        lc.arena_observation(config, legacy)
        counters["actual_search_namespace"]["evaluator"] += suffix
        with self.assertRaises(lc.Refused):
            lc.arena_observation(config, row)
        engine["probcut"] = p
        counters.update(requested_probcut=typed, actual_probcut=copy.deepcopy(typed))
        counters["whole_search"]["probcut"] = copy.deepcopy(report)
        obs["completed_iteration_counters"]["probcut"] = copy.deepcopy(report)
        lc.arena_observation(config, row)
        for scope, key, value in (
            (engine["probcut"], "margin", 0.2),
            (engine["probcut"], "deep_depth", 4),
            (engine["probcut"], "nonterminal_abs_bound", 2.0),
            (engine["probcut"], "calibration_sha256", "c" * 64),
            (counters["actual_probcut"], "margin", 0.2),
            (counters, "actual_probcut", None),
            (counters["actual_search_namespace"], "evaluator", base),
            (
                counters["actual_search_namespace"],
                "evaluator",
                base + suffix + ":extra",
            ),
            (counters["actual_search_namespace"], "rules", "other"),
            (counters["whole_search"], "probcut", None),
        ):
            old = scope[key]
            scope[key] = value
            with self.assertRaises(lc.Refused, msg=key):
                lc.arena_observation(config, row)
            scope[key] = old
        del engine["probcut"]
        counters["actual_search_namespace"]["evaluator"] = base
        counters.update(requested_probcut=None, actual_probcut=None)
        with self.assertRaises(lc.Refused):
            lc.arena_observation(config, row)  # OFF cannot hide leftover ON work.
        # Existing legal zero-completion fallback remains truthful in OFF and ON.
        for enabled in (False, True):
            clock_config = copy.deepcopy(config)
            clock_config["management_cpu_core"] = 0
            clock_config["arena"]["comparison"] = "search_wall_time"
            if enabled:
                clock_config["engines"][0]["probcut"] = p
            fallback = copy.deepcopy(obs)
            fallback.update(
                completed_depth=None,
                value_stm=None,
                pv=[],
                stop="node_cap",
                last_completed_iteration_ns=None,
                completed_iteration_counters=None,
                deadline_ns=100,
                returned_ns=10,
                admission_checked_ns=11,
                accepted_ns=12,
            )
            c = fallback["counters"]
            c.update(
                selection_reason="legal_fallback_no_completed_iteration",
                authority_receipt_ns=5,
                drain_finished_ns=10,
                inflight_after_drain=0,
                whole_search={"probcut": copy.deepcopy(report)} if enabled else {},
                requested_probcut=typed if enabled else None,
                actual_probcut=typed if enabled else None,
            )
            c["actual_search_namespace"]["evaluator"] = base + (suffix if enabled else "")
            lc.arena_observation(clock_config, dict(observations=[fallback]))
            if not enabled:
                legacy_fallback = copy.deepcopy(fallback)
                for key in ("requested_probcut", "actual_probcut"):
                    del legacy_fallback["counters"][key]
                lc.arena_observation(clock_config, dict(observations=[legacy_fallback]))
                legacy_fallback["counters"]["whole_search"]["probcut"] = copy.deepcopy(report)
                with self.assertRaises(lc.Refused):
                    lc.arena_observation(clock_config, dict(observations=[legacy_fallback]))

    def test_next5120_evaluation_publication_joins_rank_and_locator_nn0(self):
        lc = load_lifecycle()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "locator.json").write_text("{}")
            locator = lc.artifact_ref(root / "locator.json")
            request = dict(saved_next_evaluation=dict(locator=locator, components=128), output=name)
            (root / "config.json").write_text(json.dumps(request))
            config_ref = lc.artifact_ref(root / "config.json")
            experiment = dict(
                phase="generation",
                planned_slots=0,
                config=config_ref,
                inputs=[locator],
                argv=[
                    "/native",
                    "teacher-pilot",
                    "--prepare-inputs",
                    config_ref["path"],
                    "--input-sha256",
                    config_ref["sha256"],
                ],
            )
            (root / "Experiment.json").write_text(json.dumps(experiment))
            names = dict(
                book="book.json",
                evaluation_census="evaluation-census.json",
                publication="publication.json",
            )
            # This is deliberately not JSON: the collector must never retain/decode it.
            (root / "book.json").write_bytes(b"synthetic book is streamed/hash-only")
            census = dict(
                schema="quoridor-native-saved-evaluation-census-v1",
                producer=dict(locator=locator),
                parent_components=7615,
                excluded_components=5120,
                protected_H_components=0,
                eligible_named_scope=2495,
                selected_components=128,
                deficit=0,
                evaluation_only=True,
                excluded_from_future_fit=True,
                members=[
                    dict(
                        family_id=i,
                        native_rank=5120 + i,
                        component=f"c{i}",
                        observation=f"o{i}",
                        source_series=f"s{i}",
                        source_seed=i,
                    )
                    for i in range(128)
                ],
            )
            (root / "evaluation-census.json").write_text(json.dumps(census))
            files = [
                lc.artifact_ref(root / filename)
                for filename in ("book.json", "evaluation-census.json")
            ]
            result = dict(
                book=files[0],
                evaluation_census=files[1],
                selected_components=128,
                eligible_named_scope=2495,
                excluded_components=5120,
                typed_context_rows=128,
                protected_H_typed_context_or_rules_audits=0,
                opaque_parent_JSON_read_including_protected_bytes=True,
                generated_transitions=0,
                search_calls=0,
                teacher_calls=0,
                fit_calls=0,
            )
            (root / "publication.json").write_text(json.dumps(result))
            files.append(lc.artifact_ref(root / "publication.json"))
            spec = dict(
                data_root=name,
                output=str(root / "operation"),
                owner=name,
                limits=dict(log_B=65536),
                experiment=lc.artifact_ref(root / "Experiment.json"),
                data=[
                    dict(name=key, path=str(root / filename), limit_B=8 * 1024**2)
                    for key, filename in names.items()
                ],
            )
            Path(spec["output"]).mkdir()
            response = dict(config={k: config_ref[k] for k in ("path", "sha256")}, result=result)
            capture = Path(spec["output"]) / "run.full.log"
            capture.write_text(json.dumps(response))
            values = dict(
                evaluation_census=json.dumps(census).encode(),
                publication=json.dumps(result).encode(),
            )
            with (
                patch.object(lc, "owned", side_effect=lambda path, owner: Path(path)),
                patch.object(lc, "bound", wraps=lc.bound) as intake,
            ):
                self.assertEqual(lc.native_input_files(request), names)
                collected = lc.collect_data(spec, experiment)
                self.assertEqual(collected["status"], "PASS")
                self.assertEqual(collected["errors"], [])
                self.assertEqual(collected["files"], files)
                evidence = collected["generation"]
                self.assertTrue(evidence["saved_evaluation_only"])
                self.assertIsNone(evidence["numerical_qualification"])
                retained_limits = {
                    Path(call.args[0]).name: call.args[1]
                    for call in intake.call_args_list
                    if len(call.args) > 1
                }
                self.assertNotIn("book.json", retained_limits)
                self.assertFalse(
                    any(Path(call.args[0]) == root / "book.json" for call in intake.call_args_list)
                )
                self.assertEqual(retained_limits["evaluation-census.json"], 4 * 1024**2)
                self.assertEqual(retained_limits["publication.json"], 65536)
                for mutation in ("locator", "rank", "publication"):
                    with self.subTest(mutation=mutation):
                        bad = json.loads(json.dumps(census))
                        bad_values = dict(values)
                        if mutation == "locator":
                            bad["producer"]["locator"]["sha256"] = "c" * 64
                        elif mutation == "rank":
                            bad["members"][0]["native_rank"] = 5121
                        else:
                            bad_values["publication"] = b"{}"
                        bad_values["evaluation_census"] = json.dumps(bad).encode()
                        # Preserve the original direct refusal assertion, then require
                        # the same refusal through real bounded collection/file ports.
                        with self.assertRaises(lc.Refused):
                            lc.native_input_evidence(spec, experiment, bad_values, files)
                        (root / "evaluation-census.json").write_bytes(
                            bad_values["evaluation_census"]
                        )
                        bad_result = dict(
                            result,
                            evaluation_census=lc.artifact_ref(root / "evaluation-census.json"),
                        )
                        (root / "publication.json").write_bytes(
                            b"{}" if mutation == "publication" else json.dumps(bad_result).encode()
                        )
                        capture.write_text(json.dumps(dict(response, result=bad_result)))
                        refused = lc.collect_data(spec, experiment)
                        self.assertEqual(refused["status"], "FAILED")
                        self.assertTrue(
                            any(
                                error["stage"] == "generation_metadata"
                                for error in refused["errors"]
                            )
                        )
                        (root / "evaluation-census.json").write_bytes(values["evaluation_census"])
                        (root / "publication.json").write_bytes(values["publication"])
                        capture.write_text(json.dumps(response))
            with self.assertRaises(lc.Refused):
                lc.native_input_files({**request, "trajectory": {"max_plies": 200}})


if __name__ == "__main__":
    unittest.main()
