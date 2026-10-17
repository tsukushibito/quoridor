"""New teacher-scoped admission/reuse and truthful partial-bank contracts."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

import test_static_related_repairs as fixtures
import test_public_static_values as doubles
from quoridor_training import public_static_values as values


class TeacherScopedBank(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.RelatedStaticRepairs()
        self.base.setUp()
        self.path = self.base.path

    def tearDown(self):
        self.base.tearDown()

    def boundary(self, *, both):
        boundary = json.loads((self.path / "boundary.json").read_bytes())
        boundary.update(
            status="PASS_PER_TEACHER_BOUNDARIES",
            logical_rows_attempted=256,
            qualified_teachers=["S", "C"] if both else ["S"],
            original_qualification_outcome="FAILED",
            C_batch_rows=8,
            teacher_keys={"S": boundary["keys"]},
        )
        if both:
            self.base.keys[:2].tofile(self.path / "C-keys")
            np.zeros(2, dtype="<f4").tofile(self.path / "C-reused")
            boundary["teacher_keys"]["C"] = doubles.ref(self.path / "C-keys")
            boundary["batch_values"]["C"] = doubles.ref(self.path / "C-reused")
        else:
            del boundary["batch_values"]["C"]
        path = self.path / ("scoped-both.json" if both else "scoped-S.json")
        path.write_text(json.dumps(boundary))
        return {
            **self.base.config,
            "runtime_boundary": doubles.ref(path),
            "batch_rows": 256,
            "teacher_batch_rows": {"S": 256, "C": 8},
        }

    def test_S_ready_does_not_admit_C_or_publish_completed_whole_bank(self):
        config = self.boundary(both=False)
        with (
            patch.dict(sys.modules, {"torch": self.base.base.torch}),
            patch.object(values, "StaticInputs", doubles.FakeEncoder),
            patch.object(values, "StaticHead", side_effect=AssertionError("NO HEAD ENTRY")),
        ):
            result = values.label_values(config)
        bank = json.loads(Path(result["manifest"]["path"]).read_bytes())
        self.assertEqual(bank["status"], "PARTIAL_S_COMPLETE_C_UNENTERED")
        self.assertEqual(set(bank["teachers"]), {"S"})
        self.assertTrue((self.path / "labels/INCOMPLETE").exists())
        self.assertFalse((self.path / "labels/C.f32").exists())
        self.assertFalse((self.path / "labels/teacher-values.json").exists())

    def test_distinct_actual_coverage_reuses_per_teacher_values_and_C8_endbatch(self):
        config = self.boundary(both=True)
        calls = []

        class Head(doubles.FakeHead):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.capacity = kwargs["batch_rows"]

            def __call__(self, inputs):
                calls.append((self.capacity, len(inputs)))
                return super().__call__(inputs)

        with (
            patch.dict(sys.modules, {"torch": self.base.base.torch}),
            patch.object(values, "StaticInputs", doubles.FakeEncoder),
            patch.object(values, "StaticHead", Head),
        ):
            result = values.label_values(config)
        bank = json.loads(Path(result["manifest"]["path"]).read_bytes())
        self.assertEqual(bank["status"], "COMPLETE")
        self.assertEqual(bank["teachers"]["S"]["new_rows"], 0)
        self.assertEqual(bank["teachers"]["S"]["reused_boundary_rows"], 4)
        self.assertEqual(bank["teachers"]["C"]["new_rows"], 2)
        self.assertEqual(bank["teachers"]["C"]["reused_boundary_rows"], 2)
        self.assertEqual(calls, [(8, 2)])
        self.assertEqual(bank["inclusive_attempted_rows"], 258)
        self.assertFalse((self.path / "labels/INCOMPLETE").exists())


if __name__ == "__main__":
    unittest.main()
