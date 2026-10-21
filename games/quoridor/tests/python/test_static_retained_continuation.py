"""New saved-prefix/no-replay contracts only; every encoder and head is fake."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

import test_static_teacher_scopes as fixtures
import test_public_static_values as doubles
from quoridor_training import public_static_values as values
from quoridor_training.public_static_prepare import file_identity


class RetainedSContinuation(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.TeacherScopedBank()
        self.base.setUp()
        p = self.path = self.base.path
        config = self.base.boundary(both=True)
        boundary = json.loads(Path(config["runtime_boundary"]["path"]).read_bytes())
        keys = self.base.base.keys
        keys[:2].tofile(p / "S-runtime-keys")
        np.zeros(2, dtype="<f4").tofile(p / "S-runtime-values")
        boundary["teacher_keys"]["S"] = doubles.ref(p / "S-runtime-keys")
        boundary["batch_values"]["S"] = doubles.ref(p / "S-runtime-values")
        (p / "scoped-both.json").write_text(json.dumps(boundary))
        config["runtime_boundary"] = doubles.ref(p / "scoped-both.json")
        out = Path(config["output"])
        out.mkdir()
        (out / "INCOMPLETE").write_text("original partial remains incomplete\n")
        np.zeros((2, 2), dtype="<f4").tofile(out / "S.f32")
        keys.tofile(p / "retained-keys")
        np.zeros(4, dtype="<f4").tofile(p / "retained-values")
        failure = dict(
            inclusive_attempted_rows=259,
            teachers=dict(
                S=dict(
                    new_finite_rows=2,
                    head=dict(
                        finite_rows_returned=2, logical_rows_attempted=3, failed_attempted_rows=1
                    ),
                )
            ),
        )
        (out / "failure.json").write_text(json.dumps(failure))
        (out / "first-S-progress.json").write_text(
            json.dumps(dict(status="PARTIAL_RETAINED_NOT_COMPLETE"))
        )
        saved = dict(
            status="SAVED_RETURNED_PREFIX_FROZEN_NOT_RESTARTED",
            original_failure=doubles.ref(out / "failure.json"),
            input_classes=config["input_classes"],
            actual_model=config["models"]["S"],
            original_runtime_boundary=config["runtime_boundary"],
            original_bank=dict(path=str(out / "S.f32"), identity=file_identity(out / "S.f32")),
            already_charged_boundary=256,
            already_charged_global=259,
            new_finite=2,
            failed_attempted_rows=1,
            original_oriented_prefix_rows=4,
            keys=doubles.ref(p / "retained-keys"),
            values=doubles.ref(p / "retained-values"),
        )
        (p / "retained.json").write_text(json.dumps(saved))
        self.config = {
            **config,
            "retained_S_prefix": doubles.ref(p / "retained.json"),
            "retained_S_first_progress": doubles.ref(out / "first-S-progress.json"),
        }
        self.original_failure = (out / "failure.json").read_bytes()
        self.original_first = (out / "first-S-progress.json").read_bytes()
        (p / "human-policy.txt").write_text(
            "Explicit one failed-row repair only; no qualification extras.\n"
        )
        policy = doubles.ref(p / "human-policy.txt")
        repair = dict(
            authority=policy,
            old_qualification_attempts=256,
            prior_production_attempted=3,
            prior_production_returned_finite=2,
            prior_failed_attempts=1,
            prior_total_attempted=259,
            additional_failed_row_repair_max=1,
            old_actual_config_ceiling=264,
            original_plan=260,
            conditional_cumulative_attempted_upper=261,
            difference_from_old_config=-3,
            qualification_extra_rows=0,
            other_fit_or_arena_quota_change=0,
        )
        (p / "repair-envelope.json").write_text(
            json.dumps(dict(authority=policy, logical_repair=repair))
        )
        self.config.update(
            inclusive_row_limit=261, failed_row_repair=doubles.ref(p / "repair-envelope.json")
        )

    def tearDown(self):
        self.base.tearDown()

    def test_preserved_S_inode_values_and_first_event_no_head_replay(self):
        out = Path(self.config["output"])
        original_inode = (out / "S.f32").stat().st_ino
        calls = []

        class Head(doubles.FakeHead):
            def __init__(self, kind, *args, **kwargs):
                if kind != "claustrophobia":
                    raise AssertionError("retained S must not load or evaluate a head")
                super().__init__(kind, *args, **kwargs)

            def __call__(self, inputs):
                calls.append(len(inputs))
                return super().__call__(inputs)

        with (
            patch.dict(sys.modules, {"torch": self.base.base.base.torch}),
            patch.object(values, "StaticInputs", doubles.FakeEncoder),
            patch.object(values, "StaticHead", Head),
        ):
            result = values.label_values(
                self.config,
                progress_callback=lambda ref: self.assertNotEqual(
                    Path(ref["path"]).name, "first-S-progress.json"
                ),
            )
        bank = json.loads(Path(result["manifest"]["path"]).read_bytes())
        self.assertEqual(bank["status"], "COMPLETE")
        self.assertEqual(result["inclusive_attempted_rows"], 261)
        self.assertEqual(calls, [2])
        self.assertEqual(bank["teachers"]["S"]["reused_boundary_rows"], 2)
        self.assertEqual(bank["teachers"]["S"]["reused_saved_production_rows"], 2)
        self.assertEqual(bank["teachers"]["S"]["new_rows"], 0)
        self.assertEqual((out / "S.f32").stat().st_ino, original_inode)
        self.assertEqual((out / "failure.json").read_bytes(), self.original_failure)
        self.assertEqual((out / "first-S-progress.json").read_bytes(), self.original_first)
        self.assertFalse((out / "INCOMPLETE").exists())

    def test_changed_saved_custody_or_past_charge_refused_before_head(self):
        original = json.loads((self.path / "retained.json").read_bytes())
        for field in ("already_charged_global", "new_finite", "original_bank"):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(original))
                if field == "original_bank":
                    changed[field]["identity"][1] += 1
                else:
                    changed[field] += 1
                (self.path / "negative.json").write_text(json.dumps(changed))
                cfg = {**self.config, "retained_S_prefix": doubles.ref(self.path / "negative.json")}
                with patch.object(values, "StaticHead", side_effect=AssertionError("NO HEAD")):
                    with self.assertRaises(ValueError):
                        values.label_values(cfg)
                self.assertEqual(
                    (Path(cfg["output"]) / "failure.json").read_bytes(), self.original_failure
                )

    def test_failed_row_authority_has_exact_cumulative_scope_no_quota_credit(self):
        saved = json.loads((self.path / "retained.json").read_bytes())
        envelope = json.loads((self.path / "repair-envelope.json").read_bytes())
        boundary = dict(logical_rows_attempted=256)
        self.assertEqual(
            values.retained_repair_limit(
                self.config, saved, boundary, planned_total=261, pair_rows=2
            ),
            261,
        )
        for field in (
            "prior_total_attempted",
            "additional_failed_row_repair_max",
            "original_plan",
            "conditional_cumulative_attempted_upper",
            "qualification_extra_rows",
            "other_fit_or_arena_quota_change",
        ):
            changed = json.loads(json.dumps(envelope))
            changed["logical_repair"][field] += 1
            (self.path / "bad-repair.json").write_text(json.dumps(changed))
            cfg = {**self.config, "failed_row_repair": doubles.ref(self.path / "bad-repair.json")}
            with self.subTest(field=field), self.assertRaises(ValueError):
                values.retained_repair_limit(cfg, saved, boundary, planned_total=261, pair_rows=2)
        with self.assertRaises(ValueError):
            values.retained_repair_limit(
                {**self.config, "inclusive_row_limit": 264},
                saved,
                boundary,
                planned_total=261,
                pair_rows=2,
            )


if __name__ == "__main__":
    unittest.main()
