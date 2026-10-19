"""New sparse/odd selection metadata boundaries only; no native, model or old tests."""

import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(os.environ["QUORIDOR_PROJECT_ROOT"])
SOURCE = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


# Load normal imports from the maintained root, then replace only reviewed private
# function definitions in the same namespace. No environment/caller bypass is added.
lc = module("selected_slot_metadata_lc", ROOT / "scripts/dev/research-lifecycle.py")
target = SOURCE / "scripts/dev/research-lifecycle.py"
tree = ast.parse(target.read_text())
names = {
    "arena_game_ids",
    "arena_plan_check",
    "planned_game_slice",
    "arena_reference_report",
    "collect_data",
}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(nodes) == len(names)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(target), "exec"), lc.__dict__)
fixture_module = module(
    "selected_slot_existing_fixture", ROOT / "tools/research-session/test_arena_plan.py"
)
fixture_module.lc = lc


class SelectedOriginalGamesTests(unittest.TestCase):
    def fixture(self, directory):
        fixture = fixture_module.ArenaPlanTests(methodName="runTest")
        fixture.tmp = type("TMP", (), {"name": directory})()
        spec, e, plan, config, slots = fixture.fixture(4, 3)
        return fixture, spec, e, plan, config, slots

    def select(self, fixture, e, plan, config):
        config["arena"]["game_selection"] = {"selected": [1, 4, 7], "excluded": [0, 2, 3, 5, 6]}
        e["config"] = fixture.json_file("selected-config.json", config)
        plan["batches"][0]["config"] = e["config"]
        plan["batches"][0]["game_selection"] = copy.deepcopy(config["arena"]["game_selection"])

    def test_sparse_odd_original_domain_and_approved_exclusion_mask(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture, _, e, plan, config, full = self.fixture(directory)
            baseline, _ = lc.arena_plan_check(e, plan)
            self.assertEqual(baseline, full)
            self.select(fixture, e, plan, config)
            rows, checked = lc.arena_plan_check(e, plan)
            self.assertEqual([row["local_game"] for row in rows], [1, 4, 7])
            self.assertEqual(rows, [full[i] for i in [1, 4, 7]])
            self.assertEqual(checked["games"], 8)
            self.assertEqual(plan["planned_slots"], 8)
            for selected, excluded in [
                ([1, 1, 7], [0, 2, 3, 5, 6]),
                ([1, 4, 8], [0, 2, 3, 5, 6]),
                ([0, 4, 7], [0, 2, 3, 5, 6]),
                ([7, 4, 1], [0, 2, 3, 5, 6]),
            ]:
                bad = copy.deepcopy(config)
                bad["arena"]["game_selection"] = dict(selected=selected, excluded=excluded)
                with self.assertRaises(lc.Refused):
                    lc.arena_game_ids(bad)
            drift = copy.deepcopy(plan)
            drift["batches"][0]["game_selection"] = {
                "selected": [0, 4, 7],
                "excluded": [1, 2, 3, 5, 6],
            }
            with self.assertRaisesRegex(lc.Refused, "approved selected/excluded"):
                lc.arena_plan_check(e, drift)

    def test_normal_publication_and_collector_use_sparse_ids_and_physical_count(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture, spec, e, plan, config, full = self.fixture(directory)
            self.select(fixture, e, plan, config)
            root = Path(config["output"])
            root.mkdir()
            rows = [
                dict(
                    game=game,
                    family=f"{config['run_id']}-family-{game // 2:06}",
                    candidate_color=full[game]["candidate_color"],
                    status="unknown",
                    started=False,
                    failure="not_started",
                    winner=None,
                    observations=[],
                    moves=config["arena"]["book"]["openings"][game // 2]["prefix"],
                )
                for game in [1, 4, 7]
            ]

            def publish(outcomes, stopped=None):
                raw = b"".join(json.dumps(row).encode() + b"\n" for row in outcomes)
                encoder = zlib.compressobj(wbits=31)
                (root / "completed.jsonl.gz").write_bytes(encoder.compress(raw) + encoder.flush())
                journal = lc.bound(root / "completed.jsonl.gz")[0]
                report = dict(
                    run_id=config["run_id"],
                    planned=3,
                    all_workers_joined=True,
                    stopped=stopped,
                    outcomes=[],
                    pump=dict(
                        arena_node_budget=dict(
                            cap=17, charged_nodes_including_opaque_reservations=3, remaining=14
                        )
                    ),
                )
                publication = dict(
                    schema=lc.ARENA_PUBLICATION,
                    report=report,
                    outcome_count=3,
                    journal_count=3,
                    journal_bytes=len(raw),
                    journal_sha256=lc.sha(raw),
                    failure_attribution=stopped,
                    archive_wall_seconds=0.01,
                    archive_allocated_bytes=4096,
                    archive=dict(
                        encoding="gzip-single-member-v1",
                        compressed=journal,
                        raw_sha256=lc.sha(raw),
                        raw_bytes=len(raw),
                    ),
                )
                (root / "result.json").write_text(json.dumps(publication))
                files = dict(journal=journal, result=lc.bound(root / "result.json")[0])
                manifest = dict(
                    result=publication,
                    binding=dict(config=config, executable_sha256=spec["artifact"]["sha256"]),
                    cleanup=dict(archive_closed_verified=True, all_workers_joined=True),
                    artifacts={
                        "completed.jsonl.gz": {k: journal[k] for k in ("sha256", "bytes", "mode")},
                        "result.json": {k: files["result"][k] for k in ("sha256", "bytes", "mode")},
                    },
                )
                (root / "manifest.json").write_text(json.dumps(manifest))
                files["native_manifest"] = lc.bound(root / "manifest.json")[0]
                return files

            files = publish(rows)
            report = lc.arena_reference_report(config, files)
            self.assertEqual([row["game"] for row in report["outcomes"]], [1, 4, 7])
            self.assertEqual(report["planned"], 3)
            with patch.object(lc, "approved_plan", return_value=plan):
                data = lc.collect_data(spec, e)
            self.assertEqual(data["status"], "PASS", data["errors"])
            self.assertEqual(data["observed_local_games"], [1, 4, 7])
            self.assertEqual(data["planned_global_slots"], [1, 4, 7])
            self.assertEqual(data["planned_slots"], 8)
            self.assertEqual(data["missing_local_games"], [])
            self.assertEqual(report["pump"]["arena_node_budget"]["cap"], 17)
            foreign = copy.deepcopy(rows)
            foreign[0]["game"] = 0
            files = publish(foreign)
            with self.assertRaisesRegex(lc.Refused, "duplicate/unplanned"):
                lc.arena_reference_report(config, files)
            files = publish(rows, "cancelled")
            with patch.object(lc, "approved_plan", return_value=plan):
                cancelled = lc.collect_data(spec, e)
            self.assertEqual(cancelled["status"], "FAILED")
            self.assertTrue(
                any(error["stage"] == "scientific_journal" for error in cancelled["errors"])
            )
            self.assertTrue(all(row["status"] == "unknown" for row in rows))


if __name__ == "__main__":
    unittest.main()
