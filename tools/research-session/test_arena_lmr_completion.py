"""Native omitted-lmr completion boundary; synthetic files, no engine or model."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "lmr_completion_lc", ROOT / "scripts/dev/research-lifecycle.py"
)
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


class ArenaLmrCompletionTests(unittest.TestCase):
    def fixture(self, root):
        config = dict(
            output=str(root),
            run_id="lmr-completion",
            games=2,
            max_plies=1,
            engines=[dict(kind="nnue_mcts", time_ms=100), dict(kind="nnue", lmr=True)],
            arena=dict(retained_outcome_bytes=4096),
        )
        rows = [dict(game=i, started=False, status="unknown") for i in range(2)]
        raw = b"".join(json.dumps(row).encode() + b"\n" for row in rows)
        journal = root / "completed.jsonl.gz"
        journal.write_bytes(zlib.compress(raw, wbits=31))
        jr = lc.bound(journal)[0]
        publication = dict(
            schema=lc.ARENA_PUBLICATION,
            report=dict(
                run_id=config["run_id"],
                planned=2,
                outcomes=[],
                stopped=None,
                all_workers_joined=True,
            ),
            archive=dict(
                encoding="gzip-single-member-v1",
                compressed=jr,
                raw_sha256=lc.sha(raw),
                raw_bytes=len(raw),
            ),
            outcome_count=2,
            journal_count=2,
            journal_bytes=len(raw),
            journal_sha256=lc.sha(raw),
            failure_attribution=None,
            archive_wall_seconds=0,
            archive_allocated_bytes=4096,
        )
        result = root / "result.json"
        result.write_text(json.dumps(publication))
        rr = lc.bound(result)[0]
        emitted = copy.deepcopy(config)
        emitted.update(
            cycle=None,
            deadline_unix_ms=0,
            train_games=None,
            validation_games=None,
            mcts_max_bytes=268435456,
            mcts_max_nodes=200000,
            pause_file=None,
            simulations=64,
            temperature=1.0,
        )
        emitted["engines"][0]["lmr"] = False

        def publish(actual, cleanup=True):
            manifest = dict(
                result=publication,
                binding=dict(config=actual),
                cleanup=dict(archive_closed_verified=cleanup, all_workers_joined=True),
                artifacts={
                    "completed.jsonl.gz": {k: jr[k] for k in ("sha256", "bytes", "mode")},
                    "result.json": {k: rr[k] for k in ("sha256", "bytes", "mode")},
                },
            )
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest))
            return dict(journal=jr, result=rr, native_manifest=lc.bound(path)[0])

        return config, emitted, rows, publish

    def test_omitted_false_and_explicit_true_complete_without_mutating_declaration(self):
        with tempfile.TemporaryDirectory() as directory:
            config, emitted, rows, publish = self.fixture(Path(directory))
            self.assertEqual(lc.arena_reference_report(config, publish(emitted))["outcomes"], rows)
            self.assertNotIn("lmr", config["engines"][0])
            explicit = copy.deepcopy(config)
            explicit["engines"][0]["lmr"] = False
            self.assertEqual(
                lc.arena_reference_report(explicit, publish(emitted))["outcomes"], rows
            )
            explicit["engines"][0]["lmr"] = emitted["engines"][0]["lmr"] = True
            self.assertEqual(
                lc.arena_reference_report(explicit, publish(emitted))["outcomes"], rows
            )

    def test_real_config_artifact_and_cleanup_differences_still_refuse_with_location(self):
        with tempfile.TemporaryDirectory() as directory:
            config, emitted, _, publish = self.fixture(Path(directory))
            for value in (True, None, 0, 1, "false"):
                with self.subTest(value=value):
                    bad = copy.deepcopy(emitted)
                    bad["engines"][0]["lmr"] = value
                    with self.assertRaisesRegex(lc.Refused, "/config/engines/0/lmr"):
                        lc.arena_reference_report(config, publish(bad))
            for value in (None, 0, "false"):
                bad = copy.deepcopy(config)
                bad["engines"][0]["lmr"] = value
                with self.assertRaisesRegex(lc.Refused, "/config/engines/0/lmr"):
                    lc.arena_reference_report(bad, publish(emitted))
            for field, value in (
                ("time_ms", 50),
                ("model", "different"),
                ("value", "different"),
                ("policy", "different"),
                ("unknown_field", False),
            ):
                bad = copy.deepcopy(emitted)
                bad["engines"][0][field] = value
                with (
                    self.subTest(field=field),
                    self.assertRaisesRegex(lc.Refused, "/config/engines/0/" + field),
                ):
                    lc.arena_reference_report(config, publish(bad))
            with self.assertRaisesRegex(lc.Refused, "/cleanup/archive_closed_verified"):
                lc.arena_reference_report(config, publish(emitted, cleanup=False))
            files = publish(emitted)
            Path(files["journal"]["path"]).unlink()
            with self.assertRaises((lc.Refused, FileNotFoundError)):
                lc.arena_reference_report(config, files)


if __name__ == "__main__":
    unittest.main()
