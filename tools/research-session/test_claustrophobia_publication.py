"""New C publication boundary only: synthetic assets/events, no model or saved-data replay."""

import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import zlib

ROOT = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
SOURCE = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


# Same maintained namespace/imports; only the candidate owning function replaces
# its current definition. No production admission, source selector or shim.
lc = module("c_publication_lifecycle", ROOT / "scripts/dev/research-lifecycle.py")
candidate = SOURCE / "scripts/dev/research-lifecycle.py"
nodes = [
    n
    for n in ast.parse(candidate.read_text()).body
    if isinstance(n, ast.FunctionDef) and n.name == "arena_reference_report"
]
assert len(nodes) == 1
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(candidate), "exec"), lc.__dict__)


class ClaustrophobiaPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"])
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {
            "output": str(self.root),
            "run_id": "synthetic-C-publication",
            "cycle": None,
            "train_games": None,
            "validation_games": None,
            "games": 2,
            "max_plies": 1,
            "management_cpu_core": 18,
            "cpu_cores": [16, 16],
            "engines": [
                {
                    "kind": "claustrophobia",
                    "claustrophobia": {"simulations": 8, "max_head_calls": 9},
                },
                {"kind": "nnue"},
            ],
            "arena": {
                "retained_outcome_bytes": 65536,
                "book": {"openings": [{"prefix": []}]},
                "comparison": "whole_wall_time",
            },
            "deadline_unix_ms": 0,
            "mcts_max_bytes": 268435456,
            "mcts_max_nodes": 200000,
            "pause_file": None,
            "simulations": 64,
            "temperature": 1.0,
        }
        # All process/core/time/legal/model values below are synthetic ports.
        point = {"pid": 5000, "ppid": 4242, "tid": 5000, "core": 16, "affinity": [16]}
        self.observation = {
            "ply": 0,
            "side": 0,
            "engine_index": 0,
            "action": 13,
            "accepted": True,
            "failure": None,
            "engine_error": None,
            "caller_started_ns": 10,
            "deadline_ns": 100,
            "returned_ns": 70,
            "admission_checked_ns": 75,
            "accepted_ns": 75,
            "caller_seconds": 0.000000065,
            "thinking_seconds": 0.000000060,
            "last_completed_iteration_ns": None,
            "completed_iteration_counters": None,
            "stop": "completed_upstream_call",
            "completed_depth": None,
            "value_stm": 0.0,
            "pv": [],
            "counters": {
                "authority_tid_at_start": 4242,
                "authority_core_at_start": 18,
                "authority_tid": 4242,
                "authority_core": 18,
                "child_parent_pid": 4242,
                "child_pid": 5000,
                "child_execution": {
                    "started": copy.deepcopy(point),
                    "returned": copy.deepcopy(point),
                },
                "child_handle_acquired_ns": 20,
                "child_reaped_ns": 50,
                "child_pipes_drained_ns": 60,
                "child_stdout_eof": True,
                "child_stderr_eof": True,
                "direct_child_reaped": True,
                "exit_code": 0,
                "secondary": [],
                "authority_legal": True,
                "authority_receipt_ns": 70,
                "drain_finished_ns": 70,
                "inflight_after_drain": 0,
                "initialization_in_clock": True,
                "fresh_search_and_model_per_turn": True,
                "completed_simulations": 8,
                "head_calls": 9,
            },
        }

    def publish(self, observation, *, config_drift=False, artifact="a" * 64):
        rows = [
            {
                "game": 0,
                "started": True,
                "status": "unknown",
                "failure": "ply_cap",
                "moves": [13],
                "observations": [observation],
            },
            {
                "game": 1,
                "started": False,
                "status": "unknown",
                "failure": "not_started",
                "moves": [],
                "observations": [],
            },
        ]
        raw = b"".join(json.dumps(row).encode() + b"\n" for row in rows)
        encoder = zlib.compressobj(wbits=31)
        (self.root / "completed.jsonl.gz").write_bytes(encoder.compress(raw) + encoder.flush())
        journal = lc.bound(self.root / "completed.jsonl.gz")[0]
        report = {
            "outcomes": [],
            "run_id": self.config["run_id"],
            "planned": 2,
            "process_id": 4242,
            "all_workers_joined": True,
            "stopped": None,
        }
        publication = {
            "schema": lc.ARENA_PUBLICATION,
            "report": report,
            "archive": {
                "encoding": "gzip-single-member-v1",
                "compressed": journal,
                "raw_sha256": lc.sha(raw),
                "raw_bytes": len(raw),
            },
            "outcome_count": 2,
            "journal_count": 2,
            "journal_bytes": len(raw),
            "journal_sha256": lc.sha(raw),
            "failure_attribution": None,
            "archive_wall_seconds": 0.001,
            "archive_allocated_bytes": 4096,
        }
        (self.root / "result.json").write_text(json.dumps(publication))
        files = {"journal": journal, "result": lc.bound(self.root / "result.json")[0]}
        config = copy.deepcopy(self.config)
        if config_drift:
            config["max_plies"] += 1
        manifest = {
            "result": publication,
            "binding": {
                "config": config,
                "executable_sha256": artifact,
                "execution": {
                    "main_pid": 4242,
                    "main_tid": 4242,
                    "management_core": 18,
                    "management_core_observed": 18,
                    "AI_cores": [16, 16],
                    "AI_workers": 2,
                    "simultaneous_games": 1,
                    "inference_pump": False,
                },
            },
            "cleanup": {"archive_closed_verified": True, "all_workers_joined": True},
            "artifacts": {
                "completed.jsonl.gz": {k: journal[k] for k in ("sha256", "bytes", "mode")},
                "result.json": {k: files["result"][k] for k in ("sha256", "bytes", "mode")},
            },
        }
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        files["native_manifest"] = lc.bound(self.root / "manifest.json")[0]
        return files

    def read(self, observation, **options):
        result = lc.arena_reference_report(
            self.config,
            self.publish(observation, **options),
            expected_build={"artifact": {"sha256": "a" * 64}},
        )
        for row in result["outcomes"]:
            lc.arena_observation(self.config, row)
        return result

    def test_self_observed_point_needs_no_ml_import(self):
        before = {name: sys.modules.get(name) for name in ("torch", "numpy")}
        helper = module(
            "future_C_execution_point", SOURCE / "python/quoridor_training/claustrophobia.py"
        )
        point = helper.execution_point()
        self.assertEqual(point["pid"], os.getpid())
        self.assertEqual(point["ppid"], os.getppid())
        self.assertEqual(point["tid"], threading.get_native_id())
        self.assertEqual(point["affinity"], sorted(os.sched_getaffinity(0)))
        self.assertIn(point["core"], point["affinity"])
        self.assertEqual({name: sys.modules.get(name) for name in before}, before)

    def test_complete_c_uses_child_completion_without_depth_callback(self):
        result = self.read(self.observation)
        observed = result["outcomes"][0]["observations"][0]
        self.assertIsNone(observed["completed_depth"])
        self.assertIsNone(observed["last_completed_iteration_ns"])
        self.assertEqual(observed["stop"], "completed_upstream_call")
        self.assertEqual(result["outcomes"][0]["status"], "unknown")

    def test_missing_legacy_identity_or_event_still_refuses(self):
        for key in (
            "authority_tid_at_start",
            "authority_core_at_start",
            "authority_tid",
            "authority_core",
            "child_parent_pid",
            "child_pid",
            "child_execution",
            "child_handle_acquired_ns",
            "child_reaped_ns",
            "child_pipes_drained_ns",
            "child_stdout_eof",
            "child_stderr_eof",
        ):
            with self.subTest(missing=key):
                bad = copy.deepcopy(self.observation)
                del bad["counters"][key]
                with self.assertRaises(lc.Refused):
                    self.read(bad)

    def test_wrong_observed_identity_core_and_affinity_refuse(self):
        for point_name in ("started", "returned"):
            for key, value in (
                ("pid", 5001),
                ("ppid", 4243),
                ("tid", 5001),
                ("core", 17),
                ("affinity", [16, 17]),
                ("affinity", []),
                ("pid", True),
            ):
                with self.subTest(point=point_name, field=key, value=value):
                    bad = copy.deepcopy(self.observation)
                    bad["counters"]["child_execution"][point_name][key] = value
                    with self.assertRaises(lc.Refused):
                        self.read(bad)
        for key, value in (("authority_tid", 4243), ("authority_core", 16), ("child_pid", 4242)):
            bad = copy.deepcopy(self.observation)
            bad["counters"][key] = value
            with self.assertRaises(lc.Refused):
                self.read(bad)

    def test_partial_reap_drain_late_and_callback_alias_refuse(self):
        for key, value in (
            ("child_handle_acquired_ns", 9),
            ("child_reaped_ns", 71),
            ("child_pipes_drained_ns", 49),
            ("child_reaped_ns", True),
            ("direct_child_reaped", False),
            ("exit_code", False),
            ("child_stdout_eof", False),
            ("inflight_after_drain", None),
            ("secondary", ["synthetic close failure"]),
        ):
            with self.subTest(field=key, value=value):
                bad = copy.deepcopy(self.observation)
                bad["counters"][key] = value
                with self.assertRaises(lc.Refused):
                    self.read(bad)
        for key, value in (
            ("deadline_ns", 75),
            ("stop", "completed_iteration"),
            ("last_completed_iteration_ns", 40),
            ("completed_depth", 1),
        ):
            with self.subTest(observation=key):
                bad = copy.deepcopy(self.observation)
                bad[key] = value
                with self.assertRaises(lc.Refused):
                    self.read(bad)

    def test_alpha_and_sigma_still_require_worker_terminal_fields(self):
        for kind in ("nnue", "mcts"):
            with self.subTest(kind=kind):
                self.config["engines"][0]["kind"] = kind
                with self.assertRaisesRegex(lc.Refused, "actual AI/main CPU ownership"):
                    lc.arena_reference_report(self.config, self.publish(self.observation))
                # Synthetic old worker contract port, not Alpha/Sigma science.
                worker = copy.deepcopy(self.observation)
                worker["counters"].update(
                    AI_worker_core=16,
                    AI_worker_tid=4243,
                    matching_terminal_collected=True,
                    AI_terminal_finished_ns=50,
                    terminal_collected_ns=60,
                )
                lc.arena_reference_report(self.config, self.publish(worker))
                worker["counters"]["AI_worker_core"] = 17
                with self.assertRaisesRegex(lc.Refused, "actual AI/main CPU ownership"):
                    lc.arena_reference_report(self.config, self.publish(worker))

    def test_c_branch_does_not_skip_archive_config_or_build_identity(self):
        with self.assertRaises(lc.Refused):
            self.read(self.observation, config_drift=True)
        with self.assertRaises(lc.Refused):
            self.read(self.observation, artifact="b" * 64)
        files = self.publish(self.observation)
        with (self.root / "completed.jsonl.gz").open("ab") as stream:
            stream.write(b"synthetic drift")
        with self.assertRaises(lc.Refused):
            lc.arena_reference_report(self.config, files)

    def test_c_cannot_disable_ownership_by_removing_management_core(self):
        for present in (False, True):
            with self.subTest(explicit_null=present):
                if present:
                    self.config["management_cpu_core"] = None
                else:
                    self.config.pop("management_cpu_core", None)
                with self.assertRaises(lc.Refused):
                    self.read(self.observation)


if __name__ == "__main__":
    unittest.main()
