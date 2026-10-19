"""Optional Config serde defaults, using synthetic closed files without native work."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zlib

ROOT = Path(os.environ.get("QUORIDOR_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
module = importlib.util.spec_from_file_location(
    "arena_optional_defaults_lifecycle", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(module)
module.loader.exec_module(lc)


class ArenaOptionalDefaultsTests(unittest.TestCase):
    def test_omitted_null_defaults_preserve_explicit_and_other_config_mismatches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {
                "output": str(root),
                "run_id": "synthetic-optional-defaults",
                "games": 2,
                "max_plies": 1,
                "engines": [{"kind": "nnue", "time_ms": 100}, {"kind": "mcts"}],
                "arena": {"retained_outcome_bytes": 4096},
            }
            rows = [{"game": game, "started": False, "status": "unknown"} for game in range(2)]
            raw = b"".join(json.dumps(row).encode() + b"\n" for row in rows)
            journal = root / "completed.jsonl.gz"
            journal.write_bytes(zlib.compress(raw, wbits=31))
            journal_ref = lc.bound(journal)[0]
            publication = {
                "schema": lc.ARENA_PUBLICATION,
                "report": {
                    "run_id": config["run_id"],
                    "planned": 2,
                    "outcomes": [],
                    "stopped": None,
                    "all_workers_joined": True,
                },
                "archive": {
                    "encoding": "gzip-single-member-v1",
                    "compressed": journal_ref,
                    "raw_sha256": lc.sha(raw),
                    "raw_bytes": len(raw),
                },
                "outcome_count": 2,
                "journal_count": 2,
                "journal_bytes": len(raw),
                "journal_sha256": lc.sha(raw),
                "failure_attribution": None,
                "archive_wall_seconds": 0,
                "archive_allocated_bytes": 4096,
            }
            result = root / "result.json"
            result.write_text(json.dumps(publication))
            result_ref = lc.bound(result)[0]
            emitted = {
                **copy.deepcopy(config),
                "deadline_unix_ms": 0,
                "mcts_max_bytes": 268435456,
                "mcts_max_nodes": 200000,
                "pause_file": None,
                "simulations": 64,
                "temperature": 1.0,
                "cycle": None,
                "train_games": None,
                "validation_games": None,
            }

            def publish(actual):
                manifest = {
                    "result": publication,
                    "binding": {"config": actual},
                    "cleanup": {"archive_closed_verified": True, "all_workers_joined": True},
                    "artifacts": {
                        "completed.jsonl.gz": {
                            key: journal_ref[key] for key in ("sha256", "bytes", "mode")
                        },
                        "result.json": {
                            key: result_ref[key] for key in ("sha256", "bytes", "mode")
                        },
                    },
                }
                path = root / "manifest.json"
                path.write_text(json.dumps(manifest))
                return {
                    "journal": journal_ref,
                    "result": result_ref,
                    "native_manifest": lc.bound(path)[0],
                }

            self.assertEqual(lc.arena_reference_report(config, publish(emitted))["outcomes"], rows)
            explicit = {**config, "cycle": None, "train_games": None, "validation_games": None}
            self.assertEqual(
                lc.arena_reference_report(explicit, publish(emitted))["outcomes"], rows
            )
            for field, nonnull in (("cycle", {}), ("train_games", 1), ("validation_games", 1)):
                with self.subTest(field=field, side="declared"):
                    with self.assertRaisesRegex(lc.Refused, "manifest/summary/config/cleanup"):
                        lc.arena_reference_report({**config, field: nonnull}, publish(emitted))
                with self.subTest(field=field, side="emitted"):
                    with self.assertRaisesRegex(lc.Refused, "manifest/summary/config/cleanup"):
                        lc.arena_reference_report(config, publish({**emitted, field: nonnull}))
            wrong_clock = copy.deepcopy(emitted)
            wrong_clock["engines"][0]["time_ms"] = 50
            with self.assertRaisesRegex(lc.Refused, "manifest/summary/config/cleanup"):
                lc.arena_reference_report(config, publish(wrong_clock))
            missing = copy.deepcopy(emitted)
            del missing["cycle"]
            with self.assertRaisesRegex(lc.Refused, "manifest/summary/config/cleanup"):
                lc.arena_reference_report(config, publish(missing))
            self.assertEqual(config["engines"][0]["time_ms"], 100)
            self.assertNotIn("cycle", config)


if __name__ == "__main__":
    unittest.main()
