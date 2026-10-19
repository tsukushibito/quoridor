"""One new boundary: actual sequence/prepare generates the inner job metadata."""

import copy
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
SOURCE = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


lc = module("inner_selected_lc", SOURCE / "scripts/dev/research-lifecycle.py")
fixture = module("inner_selected_fixture", ROOT / "tools/research-session/test_cohort_control.py")
fixture.lc = lc
j = fixture.j


class InnerSelectedOperationTests(fixture.MetadataFixture, unittest.TestCase):
    def test_actual_sequence_generated_inner_joins_settings_and_selected_spec_without_DB(self):
        self.setup_metadata()
        member = self.cohort["members"][0]
        lane_supervisor = dict(pid=200, start_ticks="20", boot_id="boot")
        lane_sequence = dict(pid=201, start_ticks="21", boot_id="boot")
        lane_launcher = dict(pid=202, start_ticks="22", boot_id="boot")
        self.processes.update(
            {
                p["pid"]: {**p, "state": "S", "rss": 1000}
                for p in (lane_supervisor, lane_sequence, lane_launcher)
            }
        )
        patch.object(lc.os, "getpid", return_value=201).start()
        patch.object(j, "lifecycle_module", return_value=lc).start()
        lane_state = dict(
            job_id="actual-lane-job",
            phase="running",
            supervisor=lane_supervisor,
            child=lane_sequence,
            config_sha256=lc.sha(json.dumps(self.children[0], sort_keys=True).encode()),
        )
        lane_state["launch"] = dict(
            owner=self.controller,
            launcher=lane_launcher,
            supervisor=lane_supervisor,
            job_id=lane_state["job_id"],
            config_sha256=lane_state["config_sha256"],
        )
        state_path = Path(member["job_runtime"]) / "state.json"
        fixture.fresh_file(state_path, lane_state)
        experiment = fixture.fresh_file(
            self.root / "synthetic-experiment.json", dict(argv=[sys.executable, "-c", "pass"])
        )
        template = dict(
            kind="run",
            owner=str(self.root),
            cwd=str(self.root),
            writer="synthetic",
            output=str(self.root / "unentered-operation"),
            data_root=str(self.root / "synthetic-data"),
            experiment=experiment,
            env={},
            limits=dict(log_B=4096),
            finalizers=[],
            argv=[],
        )
        settings = dict(
            kind="sequence",
            owner=str(self.root),
            cwd=str(self.root),
            output=member["output"],
            arena_lane=0,
            arena_cohort=self.cohort_ref,
            runs=[template],
        )
        settings_ref = fixture.fresh_file(Path(member["settings_path"]), settings)
        config = copy.deepcopy(self.children[0])
        config["argv"][7] = settings_ref["sha256"]
        # Use the maintained launch table and normal queued config/state generation.
        launch_path = self.control / "launch.json"
        launch = json.loads(launch_path.read_text())
        launch["job_configs"][0] = fixture.fresh_file(
            self.root / "lane-0/selected-job.json", config
        )
        fixture.fresh_file(launch_path, launch)
        lane_state["config_sha256"] = lc.sha(json.dumps(config, sort_keys=True).encode())
        lane_state["launch"]["config_sha256"] = lane_state["config_sha256"]
        fixture.fresh_file(state_path, lane_state)
        origin_config = fixture.fresh_file(Path(member["job_runtime"]) / "config.json", config)
        origin = dict(
            runtime=member["job_runtime"],
            job_id=lane_state["job_id"],
            config=origin_config,
            config_sha256=lane_state["config_sha256"],
            supervisor=lane_supervisor,
            child=lane_sequence,
        )
        db_calls = []

        def forbidden_DB(*args, **kwargs):
            db_calls.append(args)
            raise AssertionError("delegated child must not read DB")

        backend = SimpleNamespace(issues=forbidden_DB)
        evidence = []

        def execute(directory, child, root, backend, **kwargs):
            state = j.read(directory, "state.json")
            state.update(supervisor=lane_sequence, phase="starting")
            j.write(directory, "state.json", state)
            self.assertEqual(child["resource_contract"], settings_ref["path"])
            selected_ref = lc.bound(Path(child["argv"][5]))[0]
            selected = lc.document(selected_ref)
            self.assertEqual(child["argv"][7], selected_ref["sha256"])
            self.assertEqual(selected["settings"], settings_ref)
            self.assertEqual(selected["selection_index"], 0)
            binding = lc.cohort_job_authority(child, directory)
            self.assertEqual(
                j.authority(child, root, backend, horizon=None, delegated=binding),
                {"thread_id": "target"},
            )

            def reject(changed, expression):
                changed_state = dict(
                    state, config_sha256=lc.sha(json.dumps(changed, sort_keys=True).encode())
                )
                j.write(directory, "state.json", changed_state)
                try:
                    with self.assertRaisesRegex(lc.Refused, expression):
                        lc.cohort_job_authority(changed, directory)
                finally:
                    j.write(directory, "state.json", state)

            wrong = copy.deepcopy(child)
            wrong["argv"][7] = "0" * 64
            reject(wrong, "assigned selected RUN")
            wrong = copy.deepcopy(child)
            wrong["resource_contract"] = str(self.root / "other-settings.json")
            reject(wrong, "assigned selected RUN")
            other = dict(selected, selection_index=1)
            other_ref = fixture.fresh_file(directory.parent / "wrong-selection.json", other)
            wrong = copy.deepcopy(child)
            wrong["argv"][5], wrong["argv"][7] = other_ref["path"], other_ref["sha256"]
            reject(wrong, "assigned selected RUN")
            other_ref = fixture.fresh_file(directory.parent / "wrong-location.json", selected)
            wrong["argv"][5], wrong["argv"][7] = other_ref["path"], other_ref["sha256"]
            reject(wrong, "maintained selected operation")
            bad_lane = copy.deepcopy(lane_state)
            bad_lane["launch"]["job_id"] = "another-job"
            fixture.fresh_file(state_path, bad_lane)
            try:
                with self.assertRaisesRegex(lc.Refused, "actual supervisor/job"):
                    lc.cohort_job_authority(child, directory)
            finally:
                fixture.fresh_file(state_path, lane_state)
            bad_inner = dict(state, config_sha256="another-config")
            j.write(directory, "state.json", bad_inner)
            try:
                with self.assertRaisesRegex(lc.Refused, "assigned inner originating job"):
                    lc.cohort_job_authority(child, directory)
            finally:
                j.write(directory, "state.json", state)
            # Fake bounded payload/finalizer only. No lifecycle native/model entry.
            operation = Path(selected["output"])
            operation.mkdir()
            (operation / "INCOMPLETE").write_text("synthetic")
            result = dict(
                outcome="succeeded", direct_child_reaped=True, cleanup_complete=True, remaining=[]
            )
            j.write(directory, "result.json", result)
            evidence.append(
                dict(
                    real_sequence_child_config=True,
                    real_prepare_selected_operation=True,
                    settings_contract=True,
                    spec_argument=True,
                    child_DB_calls=len(db_calls),
                    negative_cases=6,
                )
            )
            return result

        jobs = SimpleNamespace(
            authority=j.authority, validate=j.validate, write=j.write, lock=j.lock, execute=execute
        )
        resources = SimpleNamespace(check=lambda **kwargs: None)

        def complete(operation, job_result):
            result = dict(
                status="PASS", cleanup_complete=True, remaining=[], scientific_claim=False
            )
            fixture.fresh_file(operation / "manifest.json", result)
            return result

        with (
            patch.object(lc, "originating_job", return_value=origin),
            patch.object(lc, "ArenaCohortResources", return_value=resources),
            patch.object(lc, "physical_and_quiet"),
            patch.object(lc, "arena_cohort_progress"),
            patch.object(lc, "arena_cohort_spec", return_value={}),
        ):
            try:
                lc.sequence(settings_ref, job_module=jobs, backend=backend, complete=complete)
            except BaseException:
                terminal = Path(member["output"]) / "result.json"
                if terminal.exists():
                    print(terminal.read_text(), flush=True)
                raise
        result = json.loads((Path(member["output"]) / "result.json").read_text())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completed_operations"], 1)
        self.assertEqual(db_calls, [])
        print(
            json.dumps(
                dict(boundary=evidence, assertions="metadata only; no production stability claim")
            ),
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
