"""Model-free normal native input admission/publication correspondence."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_research_lifecycle import load_lifecycle


class NativeInputPublication(unittest.TestCase):
    def fixture(self, directory, *, saved=False):
        lc = load_lifecycle()
        root = Path(directory)
        data = root / "data"
        operation = root / "operation"
        data.mkdir()
        operation.mkdir()
        config = dict(
            families=32768,
            prefix_seed=4352026102421,
            split_seed=4352026102423,
            excluded_books=[dict(path="/NEVER_OPEN_OLD_H_PREFIX", sha256="a" * 64)],
            excluded_static_inputs=None,
            excluded_parent=dict(path="/NEVER_OPEN_OLD_PARENT_PAYLOAD"),
            output=str(data),
        )
        counts = dict(train=4096 if saved else 32768, validation=1024 if saved else 0, test=0)
        if saved:
            config["saved_subset"] = dict(split_counts=counts)
        else:
            config["trajectory"] = dict(max_plies=200, split_counts=counts)
        cfg = root / "config.json"
        cfg.write_text(json.dumps(config))
        config_ref = lc.bound(cfg)[0]
        plan = root / "plan.json"
        plan.write_text(
            json.dumps(
                dict(
                    input_request=config_ref,
                    native_exclusions={
                        k: config.get(k)
                        for k in ("excluded_books", "excluded_static_inputs", "excluded_parent")
                    },
                )
            )
        )
        # Independent actual native publication contract; never derive producer files
        # from the consumer helper under test (the previous fixture hid this mismatch).
        files = {
            "partition": "partition.json",
            "fit_observations": "fit-observations.json",
            "holdout_observations": "holdout-observations.json",
        }
        if saved:
            files["selection"] = "selection.json"
        else:
            files.update(source_observations="observations.json", schedule="schedule.json")
        result = dict(
            requested_components=counts,
            actual_components=counts,
            component_deficits=dict(train=0, validation=0, test=0),
            generated_transitions=0 if saved else 10,
            search_calls=0,
            teacher_calls=0,
            outcomes_selected=False,
        )
        for name, filename in files.items():
            if name == "selection":
                continue
            path = data / filename
            path.write_bytes(b"NOT_JSON_SYNTHETIC_PAYLOAD_MUST_ONLY_STREAM_HASH")
            result[name] = lc.bound(path)[0]
        if saved:
            result["source_observations"] = dict(
                path="/NEVER_OPEN_PARENT_SOURCE/observations.json",
                bytes=123,
                sha256="c" * 64,
                mode="0644",
            )
            (data / "selection.json").write_text(json.dumps(result))
        (operation / "run.full.log").write_text(
            json.dumps(dict(config={k: config_ref[k] for k in ("path", "sha256")}, result=result))
            + "\n"
        )
        experiment = dict(
            phase="generation",
            config=config_ref,
            planned_slots=0,
            batch=None,
            models=[],
            numerical_qualification=None,
            argv=[
                "/synthetic/native",
                "teacher-pilot",
                "--prepare-inputs",
                str(cfg),
                "--input-sha256",
                config_ref["sha256"],
            ],
            rules="research-standard-2p-threefold-goal-first-v1",
            distance_units="wall-distance/80",
            value_perspective="side-to-move",
        )
        experiment_path = root / "experiment.json"
        experiment_path.write_text(json.dumps(experiment))
        spec = dict(
            kind="run",
            finalizers=[],
            limits=dict(log_B=16384, worker_cpu=12, guardian_cpu=18),
            child_cpu_cores=[12],
            owner=str(root),
            output=str(operation),
            data_root=str(data),
            approved_plan=lc.bound(plan)[0],
            experiment=lc.bound(experiment_path)[0],
            data=[dict(name=n, path=str(data / f), limit_B=4096) for n, f in files.items()],
        )
        return lc, spec, experiment, config, result

    def test_exact_normal_argv_plan_output_and_no_old_payload_read(self):
        for saved in (False, True):
            with self.subTest(saved=saved), tempfile.TemporaryDirectory() as directory:
                lc, spec, experiment, config, _ = self.fixture(directory, saved=saved)
                original_read = lc.read_ref
                reads = []

                def read(ref, *args, **kwargs):
                    reads.append(ref["path"])
                    self.assertNotIn("NEVER_OPEN", ref["path"])
                    return original_read(ref, *args, **kwargs)

                with patch.object(lc, "read_ref", side_effect=read):
                    lc.experiment_phase_check(experiment)
                    lc.generation_check(spec, experiment)
                    self.assertTrue(lc.charged_roots(spec))
                    self.assertEqual(lc.operation_cpu_plan(spec).record()["allocation"], [12, 18])
                    with self.assertRaises(lc.Refused):
                        lc.operation_cpu_plan(dict(spec, child_cpu_cores=[12, 18]))
                    for key, value in (
                        ("models", [dict(fake=True)]),
                        ("planned_slots", 1),
                        ("argv", [*experiment["argv"][:-1], "f" * 64]),
                    ):
                        bad = dict(experiment, **{key: value})
                        with self.assertRaises(lc.Refused):
                            lc.experiment_phase_check(bad)
                    bad = dict(spec, data_root=str(Path(directory) / "other"))
                    with self.assertRaises(lc.Refused):
                        lc.generation_check(bad, experiment)
                    bad = dict(spec, data=spec["data"][:-1])
                    with self.assertRaises(lc.Refused):
                        lc.generation_check(bad, experiment)
                    with self.assertRaises(lc.Refused):
                        lc.native_input_files(dict(config, trajectory={}, saved_subset={}))
                    if saved:
                        extra = dict(
                            name="source_observations",
                            path=str(Path(spec["data_root"]) / "observations.json"),
                            limit_B=4096,
                        )
                        with self.assertRaises(lc.Refused):
                            lc.generation_check(dict(spec, data=[*spec["data"], extra]), experiment)
                self.assertTrue(reads)

    def test_actual_saved_refs_stream_without_payload_decode_and_refuse_partial_drift(self):
        for saved in (False, True):
            with self.subTest(saved=saved), tempfile.TemporaryDirectory() as directory:
                lc, spec, experiment, config, result = self.fixture(directory, saved=saved)
                good = lc.collect_data(spec, experiment)
                self.assertEqual(good["errors"], [])
                self.assertEqual(good["status"], "PASS")
                self.assertEqual(good["generation"]["actual"], result)
                self.assertEqual(good["generation"]["saved_subset_only"], saved)
                self.assertEqual(good["generation"]["scientific_planned_slots"], 0)
                self.assertIsNone(good["generation"]["model_constructor_count"])
                if saved:
                    self.assertFalse((Path(spec["data_root"]) / "observations.json").exists())
                    self.assertEqual(
                        good["generation"]["inherited_source_observations"],
                        result["source_observations"],
                    )
                    self.assertEqual(len(spec["data"]), 4)
                else:
                    self.assertEqual(len(spec["data"]), 5)
                marker = Path(spec["data_root"]) / "INCOMPLETE"
                marker.write_text("partial")
                self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED")
                marker.unlink()
                response = Path(spec["output"]) / "run.full.log"
                for kind in ("config_type", "ref", "teacher", "transition", "missing"):
                    bad = dict(
                        config={k: experiment["config"][k] for k in ("path", "sha256")},
                        result=copy.deepcopy(result),
                    )
                    if kind == "config_type":
                        bad["config"]["path"] = 17
                    elif kind == "ref":
                        bad["result"]["partition"]["sha256"] = "f" * 64
                    elif kind == "teacher":
                        bad["result"]["teacher_calls"] = 1
                    elif kind == "transition":
                        bad["result"]["generated_transitions"] = 1 if saved else 6553601
                    else:
                        del bad["result"]["holdout_observations"]
                    response.write_text(json.dumps(bad) + "\n")
                    self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED", kind)
                response.write_text(
                    json.dumps(
                        dict(
                            config={k: experiment["config"][k] for k in ("path", "sha256")},
                            result=result,
                        )
                    )
                    + "\n"
                )
                (Path(spec["data_root"]) / "partition.json").unlink()
                self.assertEqual(lc.collect_data(spec, experiment)["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
