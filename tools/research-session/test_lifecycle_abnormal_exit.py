"""New owning publication/deadline cases; synthetic Python children, no scientific admission."""

from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

MAIN = Path("/workspaces/quoridor")
SOURCE = Path(os.environ.get("LIFECYCLE_REPAIR_SOURCE", MAIN / "scripts/dev/research-lifecycle.py"))
TMP = Path(
    os.environ.get(
        "LIFECYCLE_REPAIR_TMP", MAIN / ".artifacts/research-lifecycle-maintenance/test-TMP"
    )
)
sys.path.insert(0, str(SOURCE.resolve().parents[2] / "shared/python"))
loader = importlib.util.spec_from_file_location("lc_abnormal", SOURCE)
lc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(lc)
lc.ROOT = MAIN  # Owned derivative location differs; production ROOT remains Main.

NATIVE = """
import json,pathlib,sys,time
p=pathlib.Path(sys.argv[1]);p.mkdir()
(p/'INCOMPLETE').write_text('synthetic open journal\\n')
(p/'planned.json').write_text(json.dumps({'planned':360,'synthetic':True,'Search_calls':0}))
(p/'observations.jsonl').write_text(json.dumps({'synthetic':True,'status':'UNKNOWN','Search_calls':0})+'\\n')
(p/'costs.jsonl').write_text(json.dumps({'synthetic':True,'request_id':0})+'\\n')
while True:time.sleep(1)
"""

WORKER = """
import json,pathlib,sys,subprocess,signal,os,time
sys.path.insert(0,os.environ['QUORIDOR_CODE_ROOT']+'/shared/python')
from quoridor_runtime import cycle_process as proc
p=pathlib.Path(sys.argv[1]);d=json.loads((p/'intent.json').read_text())
while 'originating_job' not in json.loads((pathlib.Path(d['output'])/'INCOMPLETE').read_text()):time.sleep(.01)\nnative=subprocess.Popen(d['argv'],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def stop(sig,frame):
 native.terminate();native.wait(timeout=3)
 signal.signal(sig,signal.SIG_DFL);os.kill(os.getpid(),sig)
signal.signal(signal.SIGTERM,stop)
identity=proc.identity(proc.process_info(native.pid))
(pathlib.Path(d['output'])/'run.process.json').write_text(json.dumps({'command':d['argv'],'status':'running','child':identity,'log_bytes_seen':0}))
(p/'ready').write_text('native-owned')
while True:time.sleep(1)
"""

CONTROLLER = """
import json,pathlib,sys,subprocess,time,hashlib,os
sys.path.insert(0,os.environ['QUORIDOR_CODE_ROOT']+'/shared/python')
from quoridor_runtime import cycle_process as proc
p=pathlib.Path(sys.argv[1]);cfg=json.loads((p/'runtime/config.json').read_text())

# A is a real earlier same-intent child which exits before it claims the operation.
a=p/'runtimeA';a.mkdir();__import__('os').link(p/'runtime/config.json',a/'config.json')
prior=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(.03);raise SystemExit(1)'])
prior_id=proc.identity(proc.process_info(prior.pid));assert prior.wait(timeout=3)==1
prior_state={'job_id':'synthetic-preclaim-A','issue':cfg['issue'],'thread_id':cfg['thread_id'],'config_sha256':hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),'supervisor':proc.identity(proc.process_info(__import__('os').getpid())),'child':prior_id,'started_at':'synthetic earlier A','phase':'finished','outcome':'failed'}
(a/'state.json').write_text(json.dumps(prior_state))
(a/'result.json').write_text(json.dumps({'job_id':prior_state['job_id'],'outcome':'failed','exit_code':1,'finished_at':'synthetic earlier A stopped','direct_child_reaped':True,'cleanup_complete':True,'remaining':[],'cleanup_errors':[]}))

worker=subprocess.Popen([sys.executable,'-B','-c',sys.argv[2],str(p)])
child=proc.identity(proc.process_info(worker.pid))
state={'job_id':'synthetic-abnormal','issue':cfg['issue'],'thread_id':cfg['thread_id'],'config_sha256':hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),'supervisor':proc.identity(proc.process_info(__import__('os').getpid())),'child':child,'started_at':'2026-10-11T00:00:00+00:00'}

op=p/'operation';marker=json.loads((op/'INCOMPLETE').read_text())
config_path=p/'runtime/config.json'
origin={'runtime':str(p/'runtime'),'job_id':state['job_id'],'config':{'path':str(config_path),'sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),'bytes':config_path.stat().st_size,'mode':format(config_path.stat().st_mode&0o7777,'04o')},'config_sha256':state['config_sha256'],'supervisor':state['supervisor'],'child':state['child']}
marker['originating_job']=origin;(op/'INCOMPLETE').write_text(json.dumps(marker))

until=time.monotonic()+5
while not (p/'ready').exists() and time.monotonic()<until:time.sleep(.01)
assert (p/'ready').exists()
until=time.monotonic()+5
while not (p/'data/costs.jsonl').exists() and time.monotonic()<until:time.sleep(.01)
assert (p/'data/costs.jsonl').exists()
worker.terminate();code=worker.wait(timeout=5);assert code==-15
state.update(phase='finished',outcome='timed_out')
(p/'runtime/state.json').write_text(json.dumps(state))
result={'job_id':state['job_id'],'outcome':'timed_out','error':None,'exit_code':code,'finished_at':'2026-10-11T00:00:01+00:00','wall_seconds':1,'direct_child_reaped':True,'cleanup_complete':True,'remaining':[],'cleanup_errors':[]}
(p/'runtime/result.json').write_text(json.dumps(result))
"""


def ref(p):
    return lc.bound(p)[0]


def finalize(*args):
    os.sched_setaffinity(0, {2, 4})
    return lc.finalize(*args)


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(dir=TMP, prefix="abnormal-") as name:
        p = Path(name)
        operation, runtime = p / "operation", p / "runtime"
        operation.mkdir()
        runtime.mkdir()
        support_path = p / "synthetic-support.json"
        lc.new_json(
            support_path,
            {
                "funded_union_B": 524288,
                "global_held_B": 524288,
                "synthetic_fixture_not_resource_issuance": True,
            },
        )
        support = ref(support_path)
        experiment = p / "experiment.json"
        lc.new_json(experiment, {"phase": "compare", "planned_slots": 360, "build_manifest": {}})
        limits = {
            "family_B": 512 * 1024**2,
            "host_reserve_B": 4 * 1024**3,
            "controller_B": 64 * 1024**2,
            "owned_B": 512 * 1024,
            "log_B": 8192,
            "free_B": 4 * 1024**3,
            "worker_cpu": 2,
            "guardian_cpu": 4,
        }
        d = {
            "schema": "quoridor.research.lifecycle-intent.v1",
            "kind": "run",
            "owner": str(p),
            "output": str(operation),
            "data_root": str(p / "data"),
            "owned_outputs": [str(p / "data")],
            "TMP": str(p / "TMP"),
            "cwd": str(MAIN),
            "support": support,
            "approved_plan": ref(experiment),
            "experiment": ref(experiment),
            "argv": [sys.executable, "-B", "-c", NATIVE, str(p / "data")],
            "limits": limits,
            "env": {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            "finalizers": [
                {"kind": "data", "path": str(p / "missing-finalizer.json"), "limit_B": 8192}
            ],
            "data": [
                {"name": n, "path": str(p / "data" / n), "limit_B": 8192}
                for n in ["planned.json", "observations.jsonl", "costs.jsonl", "result.json"]
            ],
        }
        d["intent_sha256"] = hashlib.sha256(
            json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        admission = p / "admission.json"
        lc.new_json(
            admission,
            {
                "schema": "quoridor.research.phase-admission.v1",
                "owner": d["owner"],
                "limits": limits,
                "spec_sha256": d["intent_sha256"],
                "support_sha256": support["sha256"],
                "approved_plan": d["approved_plan"],
                "ready": True,
            },
        )
        d["admission"] = ref(admission)
        intent = p / "intent.json"
        lc.new_json(intent, d)
        os.link(intent, operation / "intent.json")
        lc.new_json(operation / "INCOMPLETE", {"status": "UNKNOWN", "intent": ref(intent)})
        (operation / "run.full.log").write_bytes(b"")
        (operation / "run.log").write_bytes(b"")
        cfg = {
            "argv": [
                sys.executable,
                "-B",
                str(MAIN / "scripts/dev/research-lifecycle.py"),
                "run",
                "--intent",
                str(intent),
                "--sha256",
                ref(intent)["sha256"],
            ],
            "cwd": str(MAIN),
            "resource_contract": support["path"],
            "issue": "synthetic360-abnormal",
            "thread_id": "synthetic-fixture-not-App-session",
        }
        lc.new_json(runtime / "config.json", cfg)
        resources = lc.Limits(d)
        os.sched_setaffinity(0, {2, 4})
        lc.physical_and_quiet(d)
        with lc.lease():
            guardian = lc.process.execute(
                [sys.executable, "-B", "-c", CONTROLLER, str(p), WORKER],
                p / "synthetic-controller.log",
                time.monotonic() + 15,
                resources=resources,
                cwd=str(p),
                cpu_core=2,
            )
        assert guardian["direct_child_reaped"] and guardian["cleanup_complete"]
        assert not (operation / "candidate.json").exists()
        yield p, d, ref(runtime / "result.json")


class AbnormalLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(parents=True, exist_ok=True)

    def test_real_stopped_origin_failure_preserves_partial_and_owed_errors(self):
        with fixture() as (p, d, result):
            o = p / "operation"
            paths = [
                p / "intent.json",
                p / "runtime/result.json",
                o / "run.process.json",
                p / "data/INCOMPLETE",
                p / "data/observations.jsonl",
            ]
            before = [ref(x) for x in paths]
            completed = finalize(o, result)
            self.assertEqual(completed["status"], "FAILED")
            self.assertFalse(completed["cleanup_complete"])
            self.assertEqual(completed["primary"]["original_result"]["exit_code"], -15)
            self.assertEqual(completed["primary"]["original_result"]["outcome"], "timed_out")
            self.assertIsNone(completed["checks"][0]["guardian_return"])
            self.assertEqual(completed["abnormal_origin"]["command_cleanup"], "UNKNOWN")
            self.assertEqual(completed["data"]["status"], "FAILED")
            self.assertIsNone(completed["data"]["numerical_qualification"])
            self.assertEqual(len(completed["data"]["files"]), 3)
            self.assertIn("result.json", [x["stage"] for x in completed["data"]["errors"]])
            self.assertIn("owed_finalizer", [x["stage"] for x in completed["secondary"]])
            self.assertEqual(before, [ref(x) for x in paths])
            self.assertFalse((o / "candidate.json").exists())
            self.assertFalse((o / "INCOMPLETE").exists())
            self.assertTrue((p / "data/INCOMPLETE").exists())
            with self.assertRaisesRegex(lc.Refused, "duplicate"):
                finalize(o, result)

    def test_unrelated_and_active_origins_refuse_before_claim(self):
        with fixture() as (p, d, result):
            o = p / "operation"
            cfg_path = p / "runtime/config.json"
            original = cfg_path.read_bytes()
            state_path = p / "runtime/state.json"
            state_original = state_path.read_bytes()
            marker_path = o / "INCOMPLETE"
            marker_original = marker_path.read_bytes()
            outside = p.parent / (p.name + "-outside-intent.json")
            try:
                outside.write_bytes((p / "intent.json").read_bytes())
                marker = json.loads(marker_original)
                marker["intent"] = ref(outside)
                marker_path.write_text(json.dumps(marker))
                with self.assertRaisesRegex(lc.Refused, "write ownership"):
                    finalize(o, result)
                self.assertFalse((o / "finalizing").exists())
            finally:
                marker_path.write_bytes(marker_original)
                outside.unlink()
            cfg = json.loads(original)
            cfg["argv"][-1] = "0" * 64
            cfg_path.write_text(json.dumps(cfg))
            state = json.loads(state_original)
            state["config_sha256"] = hashlib.sha256(
                json.dumps(cfg, sort_keys=True).encode()
            ).hexdigest()
            state_path.write_text(json.dumps(state))
            with self.assertRaisesRegex(lc.Refused, "closed original"):
                finalize(o, result)
            self.assertFalse((o / "finalizing").exists())
            cfg_path.write_bytes(original)
            state_path.write_bytes(state_original)
            active = subprocess.Popen([sys.executable, "-B", "-c", "import time;time.sleep(10)"])
            try:
                receipt = json.loads((o / "run.process.json").read_bytes())
                receipt["child"] = lc.process.identity(lc.process.process_info(active.pid))
                (o / "run.process.json").write_text(json.dumps(receipt))
                with self.assertRaisesRegex(lc.Refused, "still active"):
                    finalize(o, result)
                self.assertFalse((o / "finalizing").exists())
            finally:
                active.terminate()
                active.wait(timeout=3)

    def test_publication_io_error_retains_original_and_secondary_facts(self):
        with fixture() as (p, d, result):
            ordinary = lc.new_json

            def fail_manifest(path, value):
                if Path(path).name == "manifest.json":
                    raise OSError("synthetic authoritative publication failure")
                return ordinary(path, value)

            with patch.object(lc, "new_json", side_effect=fail_manifest):
                with self.assertRaisesRegex(OSError, "publication failure") as caught:
                    finalize(p / "operation", result)
            facts = json.loads(
                caught.exception.__notes__[-1].split("unpublished completion facts: ", 1)[1]
            )
            self.assertEqual(facts["primary"]["original_result"]["exit_code"], -15)
            self.assertIn("owed_finalizer", [x["stage"] for x in facts["secondary"]])
            self.assertTrue((p / "operation/INCOMPLETE").exists())
            self.assertFalse((p / "operation/manifest.json").exists())
            with self.assertRaisesRegex(lc.Refused, "duplicate"):
                finalize(p / "operation", result)

    def test_actual_command_deadline_cleanup_and_no_deadline_reset(self):
        with tempfile.TemporaryDirectory(dir=TMP, prefix="deadline-") as name:
            p = Path(name)
            limits = {
                "max_memory_bytes": 448 * 1024**2,
                "host_ram_reserve": 4 * 1024**3,
                "max_output_bytes": 49152,
            }
            resources = lc.process.CycleResources(limits, p, None)
            spec = {
                "command_timeout_seconds": 1,
                "limits": {"log_B": 8192, "worker_cpu": 2},
                "cwd": str(p),
                "env": {"PATH": "/usr/bin:/bin"},
            }
            row = {
                "name": "finite",
                "argv": [
                    sys.executable,
                    "-B",
                    "-c",
                    "import time;print('synthetic started',flush=True);time.sleep(20)",
                ],
            }
            ledger = []
            os.sched_setaffinity(0, {2, 4})
            lc.physical_and_quiet(
                {
                    "limits": {
                        "family_B": 512 * 1024**2,
                        "host_reserve_B": 4 * 1024**3,
                        "worker_cpu": 2,
                        "guardian_cpu": 4,
                    }
                }
            )
            with lc.lease(), self.assertRaises(lc.process.CycleStopped):
                lc.command(spec, row, p, resources, ledger=ledger)
            deadline = resources.deadline
            receipt = json.loads((p / "finite.process.json").read_bytes())
            self.assertTrue(receipt["direct_child_reaped"])
            self.assertTrue(receipt["cleanup_complete"])
            self.assertFalse(lc.process.alive(receipt["child"]))
            self.assertIn(b"synthetic started", (p / "finite.full.log").read_bytes())
            self.assertIsNone(ledger[0]["guardian_return"])
            with lc.lease(), self.assertRaises(lc.process.CycleStopped):
                lc.command(spec, {**row, "name": "after-deadline"}, p, resources)
            self.assertEqual(resources.deadline, deadline)
            self.assertFalse((p / "after-deadline.process.json").exists())
            for wrong in [True, 0, -1]:
                with self.assertRaisesRegex(lc.Refused, "positive admitted"):
                    lc.command(
                        {**spec, "command_timeout_seconds": wrong},
                        {**row, "name": "invalid"},
                        p,
                        resources,
                    )

    def test_originating_budget_is_bound_and_reserves_publication_time(self):
        with fixture() as (p, d, result):
            runtime = p / "runtime"
            cfg = json.loads((runtime / "config.json").read_bytes())
            cfg["max_runtime_seconds"] = 900
            state = json.loads((runtime / "state.json").read_bytes())
            state.update(
                phase="running",
                supervisor=lc.process.identity(lc.process.process_info(os.getppid())),
            )

            def admitted(budget):
                current = {**d, "command_timeout_seconds": budget}
                view = {k: v for k, v in current.items() if k not in {"admission", "intent_sha256"}}
                current["intent_sha256"] = hashlib.sha256(
                    json.dumps(view, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                a = json.loads((p / "admission.json").read_bytes())
                a["spec_sha256"] = current["intent_sha256"]
                (p / "admission.json").write_text(json.dumps(a))
                current["admission"] = ref(p / "admission.json")
                (p / "intent.json").write_text(json.dumps(current))
                actual = ref(p / "intent.json")
                cfg["argv"][-1] = actual["sha256"]
                (runtime / "config.json").write_text(json.dumps(cfg))
                state["config_sha256"] = hashlib.sha256(
                    json.dumps(cfg, sort_keys=True).encode()
                ).hexdigest()
                (runtime / "state.json").write_text(json.dumps(state))
                return lc.originating_job(actual, current)

            with patch.dict(os.environ, {"QUORIDOR_RESEARCH_JOB_DIR": str(runtime)}):
                origin = admitted(840)
                self.assertEqual(
                    origin["child"], lc.process.identity(lc.process.process_info(os.getpid()))
                )
                for bad in [True, 0, -1, 841, 900]:
                    with self.assertRaisesRegex(lc.Refused, "cleanup/publication"):
                        admitted(bad)

    def test_entered_preparation_consumes_budget_before_child_launch(self):
        # Trusted scientific input checking is a labelled port here; no accepted
        # engine/model/input is invented. The actual execute/guardian deadline is used.
        with fixture() as (p, d, result):
            current = {**d, "command_timeout_seconds": 1, "output": str(p / "entered-budget-op")}
            view = {k: v for k, v in current.items() if k not in {"admission", "intent_sha256"}}
            current["intent_sha256"] = hashlib.sha256(
                json.dumps(view, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            admission = json.loads((p / "admission.json").read_bytes())
            admission["spec_sha256"] = current["intent_sha256"]
            (p / "admission.json").write_text(json.dumps(admission))
            current["admission"] = ref(p / "admission.json")
            (p / "intent.json").write_text(json.dumps(current))
            actual = ref(p / "intent.json")
            cfg = json.loads((p / "runtime/config.json").read_bytes())
            cfg.update(max_runtime_seconds=61)
            cfg["argv"][-1] = actual["sha256"]
            (p / "runtime/config.json").write_text(json.dumps(cfg))
            state = json.loads((p / "runtime/state.json").read_bytes())
            state.update(
                phase="running",
                supervisor=lc.process.identity(lc.process.process_info(os.getppid())),
                config_sha256=hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
            )
            (p / "runtime/state.json").write_text(json.dumps(state))

            def entered_preparation(_spec):
                time.sleep(1.1)
                return (
                    {"phase": "compare", "planned_slots": 360, "build_manifest": {}},
                    {"source": {"cargo_configs": []}},
                    [],
                )

            os.sched_setaffinity(0, {2, 4})
            with (
                patch.dict(os.environ, {"QUORIDOR_RESEARCH_JOB_DIR": str(p / "runtime")}),
                patch.object(lc, "experiment_check", side_effect=entered_preparation),
            ):
                with self.assertRaises(lc.process.CycleStopped):
                    lc.execute(actual)
            o = Path(current["output"])
            self.assertFalse((o / "run.process.json").exists())
            candidate = json.loads((o / "candidate.json").read_bytes())
            self.assertEqual(candidate["status"], "FAILED")
            self.assertIsNone(candidate["checks"][0]["guardian_return"])

    def assert_unclaimed(self, operation):
        self.assertTrue((operation / "INCOMPLETE").exists())
        self.assertFalse((operation / "finalizing").exists())
        self.assertFalse((operation / "manifest.json").exists())
        self.assertFalse((operation / "candidate.json").exists())

    def test_real_A_preclaim_refuses_B_claim_publishes_failure_only(self):
        with fixture() as (p, spec, result):
            operation = p / "operation"
            raw = {x: x.read_bytes() for x in operation.iterdir()}
            with self.assertRaisesRegex(lc.Refused, "independent operation origin mismatch"):
                finalize(operation, ref(p / "runtimeA/result.json"))
            self.assert_unclaimed(operation)
            self.assertEqual(raw, {x: x.read_bytes() for x in operation.iterdir()})
            completed = finalize(operation, result)
            self.assertEqual(completed["status"], "FAILED")
            self.assertEqual(
                completed["primary"]["original_result"]["job_id"], "synthetic-abnormal"
            )
            self.assertEqual(completed["primary"]["original_result"]["exit_code"], -15)
            self.assertEqual(completed["abnormal_origin"]["command_cleanup"], "UNKNOWN")
            self.assertEqual(completed["data"]["journal_flush_sync_close"], "UNKNOWN")
            self.assertIsNone(completed["data"]["numerical_qualification"])
            self.assertEqual(len(completed["data"]["files"]), 3)
            self.assertIn("owed_finalizer", [x["stage"] for x in completed["secondary"]])
            self.assertTrue((p / "data/INCOMPLETE").exists())
            self.assertFalse((operation / "INCOMPLETE").exists())
            with self.assertRaisesRegex(lc.Refused, "duplicate"):
                finalize(operation, result)

    def test_historical_independent_custody_rejects_A_missing_and_drift(self):
        with fixture() as (p, spec, result):
            operation = p / "operation"
            marker_path = operation / "INCOMPLETE"
            marker = json.loads(marker_path.read_bytes())
            origin = marker.pop("originating_job")
            marker_path.write_text(json.dumps(marker))
            with self.assertRaisesRegex(lc.Refused, "independent operation origin required"):
                finalize(operation, result)
            self.assert_unclaimed(operation)
            custody_path = p / "Root-custody.json"
            custody = {
                "schema": "quoridor.research.operation-origin.v1",
                "status": "ACCEPTED",
                "operation_marker": ref(marker_path),
                "intent": ref(p / "intent.json"),
                "result": result,
                "state": ref(p / "runtime/state.json"),
                "persisted_process": ref(operation / "run.process.json"),
                "originating_job": origin,
            }
            lc.new_json(custody_path, custody)
            # Only the administrative custody location is a fixture port;
            # actual normal admission, ownership, process and publication paths run.
            os.sched_setaffinity(0, {2, 4})
            with self.assertRaisesRegex(lc.Refused, "Root integration custody"):
                lc.finalize(operation, result, origin_ref=ref(custody_path))
            self.assert_unclaimed(operation)
            with patch.object(lc, "ORIGIN_CUSTODY", p):
                os.sched_setaffinity(0, {2, 4})
                with self.assertRaisesRegex(lc.Refused, "independent historical"):
                    lc.finalize(
                        operation,
                        ref(p / "runtimeA/result.json"),
                        origin_ref=ref(custody_path),
                    )
                self.assert_unclaimed(operation)
                saved = custody_path.read_bytes()
                custody_path.write_bytes(saved + b" ")
                os.sched_setaffinity(0, {2, 4})
                with self.assertRaises(lc.Refused):
                    lc.finalize(
                        operation,
                        result,
                        origin_ref={**ref(custody_path), "sha256": lc.sha(saved)},
                    )
                self.assert_unclaimed(operation)
                custody_path.write_bytes(saved)
                os.sched_setaffinity(0, {2, 4})
                completed = lc.finalize(operation, result, origin_ref=ref(custody_path))
            self.assertEqual(completed["status"], "FAILED")
            self.assertEqual(
                completed["abnormal_origin"]["independent_origin_custody"],
                ref(custody_path),
            )
            self.assertIsNone(completed["data"]["numerical_qualification"])
            self.assertEqual(completed["primary"]["original_result"]["exit_code"], -15)


if __name__ == "__main__":
    unittest.main()
