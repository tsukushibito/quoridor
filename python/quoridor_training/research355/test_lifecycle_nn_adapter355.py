"""One new integration definition; real metadata, synthetic UNKNOWN game only."""

import copy
from pathlib import Path
import unittest

import lifecycle355 as life
import strength355 as s


def synthetic_book():
    families = []
    for fid in range(128):
        length = (4, 8, 12, 16)[fid // 32]
        prefix = [fid] * (length - 1) + [208 - fid]
        history = [["synthetic-common-initial", 1]] + [
            [f"synthetic-{fid}-{n}", 1] for n in range(length)
        ]
        families.append(
            dict(
                family_id=fid,
                attempt_id=0,
                root_key=history[-1][0],
                prefix=prefix,
                prefix_SHA256=s.digest(prefix),
                counted_history=history,
                history_SHA256=s.digest(history),
                terminal=False,
                current_rules="standard_2p_threefold_goal_first",
                lineage=dict(
                    shared_root="SYNTHETIC-common-initial", family_seed=35520261009 + 8 * fid
                ),
            )
        )
    return dict(
        schema="quoridor.strength355.full-history-book.v1",
        plan_SHA256=s.PLAN_SHA,
        provenance="SYNTHETIC",
        source_book_SHA256="9" * 64,
        families=families,
    )


def synthetic_schedule(book):
    return dict(
        schema="quoridor.strength355.schedule.v1",
        plan_SHA256=s.PLAN_SHA,
        book_SHA256=s.check_book(book),
        source_book_SHA256=book["source_book_SHA256"],
        source_schedule_SHA256="8" * 64,
        slots=s.planned_slots(),
    )


class SavedNNAdapterGuard(unittest.TestCase):
    def test_saved_best43_metadata_through_admission_and_game_adapter(self):
        root = Path(
            "/workspaces/quoridor/.worktree/value-search-strength-arena355/.artifacts/"
            "value-search-strength355/maintained-build-v1"
        )
        config_ref = {
            "path": str(root / "campaign-materialization-v1/data/batch-01.json"),
            "sha256": "e32e31e7670d59ed5273c7898b484e0b50eb08144daf51f5b34d27d088b29e6f",
            "bytes": 14419,
            "mode": "0644",
        }
        experiment_ref = {
            "path": str(root / "campaign-arena-v1/batch-01/controls-v1/experiment.json"),
            "sha256": "c53338fe4760832cd6f9df4f3db534c42c5852964721c0d5cecc6246592d10dd",
            "bytes": 4664,
            "mode": "0644",
        }
        metadata = life.Metadata()
        config = metadata.read(config_ref)
        experiment = metadata.read(experiment_ref)
        self.assertEqual(experiment["config"], config_ref)
        self.assertEqual(config["engines"][0]["distance_b"], 8)
        self.assertEqual(experiment["models"][0]["descriptor"]["sha256"], life.MODELS[1][0])
        self.assertEqual(experiment["models"][0]["weights"]["sha256"], life.MODELS[1][1])
        self.assertEqual(experiment["models"][0]["evaluator_sha256"], life.MODELS[1][2])

        # Tiny self-contained synthetic lineage, never actual book or geometry.
        book = synthetic_book()
        family = book["families"][0]
        family["prefix"] = copy.deepcopy(config["arena"]["book"]["openings"][0]["prefix"])
        family["prefix_SHA256"] = s.digest(family["prefix"])
        schedule = synthetic_schedule(book)
        slot = schedule["slots"][32]
        self.assertEqual((slot["batch_id"], slot["family_id"], slot["local_game"]), (1, 0, 0))
        raw = {
            "game": 0,
            "family": f"{config['run_id']}-family-000000",
            "candidate_color": slot["candidate_colour"],
            "started": False,
            "status": "unknown",
            "winner": None,
            "reason": "SYNTHETIC_UNENTERED",
            "failure": "SYNTHETIC_UNENTERED",
            "plies": len(family["prefix"]),
            "moves": copy.deepcopy(family["prefix"]),
            "observations": [],
        }

        def boundary(cfg, phase, row, plan):
            life.models(phase)
            life.arena_clock(cfg)
            life.arena_conditions(cfg, phase)
            s.check_schedule(plan, book)
            planned = plan["slots"][32]
            expected = {
                "game": planned["local_game"],
                "family": f"{cfg['run_id']}-family-000000",
                "candidate_color": planned["candidate_colour"],
                "opening": cfg["arena"]["book"]["openings"][0]["prefix"],
            }
            return s.adapt_native_game(row, expected, cfg, planned, book, plan)

        result = boundary(config, experiment, raw, schedule)
        self.assertEqual(result["outcome"]["status"], "unknown")
        self.assertEqual(result["outcome"]["reason"], "SYNTHETIC_UNENTERED")
        self.assertEqual(result["provenance"], "SYNTHETIC")
        for a, b in ((0, 0), (-2, 8), (1.5, -0.25)):
            with self.subTest(case="unused_raw_NN_knobs", a=a, b=b):
                variant = copy.deepcopy(config)
                variant["engines"][0].update(distance_a=a, distance_b=b)
                self.assertEqual(boundary(variant, experiment, raw, schedule), result)
        # Variants test guards only, not hash-bound admission or a new phase.
        config_changes = (
            ("NN_kind", ("engines", 0, "kind"), "distance"),
            ("NN_path", ("engines", 0, "model"), "/synthetic/wrong-model.json"),
            ("D_kind", ("engines", 1, "kind"), "nnue"),
            ("D_a", ("engines", 1, "distance_a"), 1),
            ("D_b", ("engines", 1, "distance_b"), 0),
            ("D_model", ("engines", 1, "model"), "/synthetic/forbidden.json"),
            (
                "global_family",
                ("arena", "book", "openings", 0, "reference", "settings", "family_id"),
                1,
            ),
            ("prefix", ("arena", "book", "openings", 0, "prefix"), [208] * 4),
            ("run_id", ("run_id",), "wrong-run"),
            ("clock", ("engines", 0, "time_ms"), 101),
            ("reserve", ("arena", "return_reserve_ms"), 4),
            ("clock_policy", ("arena", "clock_policy"), "wrong-clock"),
        )
        for name, keys, value in config_changes:
            with self.subTest(case=name):
                variant = copy.deepcopy(config)
                target = variant
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.assertRaises(ValueError):
                    boundary(variant, experiment, raw, schedule)
        for key in ("descriptor", "weights", "evaluator_sha256"):
            with self.subTest(case="ordered_current_model", key=key):
                phase = copy.deepcopy(experiment)
                if key == "evaluator_sha256":
                    phase["models"][0][key] = "f" * 64
                else:
                    phase["models"][0][key]["sha256"] = "f" * 64
                with self.assertRaises(ValueError):
                    boundary(config, phase, raw, schedule)
        for key, value in (("family", "wrong-family"), ("candidate_color", 1), ("game", 1)):
            with self.subTest(case="native_context", key=key):
                row = copy.deepcopy(raw)
                row[key] = value
                with self.assertRaises(ValueError):
                    boundary(config, experiment, row, schedule)
        with self.subTest(case="immutable_schedule_context"):
            plan = copy.deepcopy(schedule)
            plan["slots"][32]["candidate_colour"] ^= 1
            with self.assertRaises(ValueError):
                boundary(config, experiment, raw, plan)
        with self.subTest(case="raw_metadata_hash_drift"):
            ref = copy.deepcopy(config_ref)
            ref["sha256"] = "f" * 64
            with self.assertRaises(ValueError):
                life.Metadata().read(ref)
        metadata.after()
        self.assertEqual(set(metadata.seen), {config_ref["path"], experiment_ref["path"]})


if __name__ == "__main__":
    unittest.main()
