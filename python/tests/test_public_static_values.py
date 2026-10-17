"""NN0 five-route counters and scalar publication; every head/encoder is a test double."""

import hashlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np

import test_static_normal_consumer as fixtures
from quoridor_training import public_static_values as values


def ref(path):
    b = Path(path).read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(b).hexdigest(), bytes=len(b), mode="0644")


class FakeEncoder:
    def __init__(self, *a, **kw):
        pass

    def encode(self, keys, *, include_c20=True):
        sigma = np.zeros((len(keys), 8, 9, 9), dtype=np.float32)
        sigma[:, 0, 0, 0] = (
            np.frombuffer(np.asarray(keys).tobytes(), dtype="u1").reshape(-1, 28)[:, 0] / 100
        )
        return sigma, (np.repeat(sigma[:, :1], 20, axis=1).copy() if include_c20 else None)


class FakeHead:
    mismatch = False

    def __init__(self, *a, **kw):
        self.attempted = 0

    def __call__(self, x):
        self.attempted += len(x)
        return x[:, 0, 0, 0].copy() + np.float32(0.01 if self.mismatch and len(x) > 1 else 0)

    def facts(self):
        return dict(
            test_double=True, logical_rows_attempted=self.attempted, constructor_model_calls=0
        )


class NewStaticValueFlow(unittest.TestCase):
    def setUp(self):
        self.base = fixtures.NormalStaticConsumer()
        self.base.setUp()
        p = self.path = self.base.path
        (p / "lib-core").write_bytes(b"x")
        (p / "lib-c20").write_bytes(b"y")
        (p / "model-S").write_bytes(b"s")
        (p / "model-C").write_bytes(b"c")
        (p / "exclusions.json").write_text(
            json.dumps(
                dict(
                    encoding="SHA256 of canonical STM Sigma8 C-order LE-f32 shape[8,9,9], 2592bytes",
                    sha256=[
                        hashlib.sha256(("old" + str(i)).encode()).hexdigest() for i in range(19)
                    ],
                )
            )
        )
        (p / "old-comparator.py").write_text(
            "class SingleHead:\n"
            "    def __init__(self,*args): self.rows=0\n"
            "    def __call__(self,x): self.rows+=len(x); return x[:,0,0,0].copy()\n"
            "    def facts(self): return {'test_double':True,'attempted_rows':self.rows}\n"
        )
        self.config = dict(
            input_classes=ref(p / "inputs.json"),
            core_library=ref(p / "lib-core"),
            c20_library=ref(p / "lib-c20"),
            models={k: ref(p / ("model-" + k)) for k in ("S", "C")},
            old_input_exclusions=ref(p / "exclusions.json"),
            old_sigma_head_source=ref(p / "old-comparator.py"),
            planned_extra_head_rows=0,
            max_new_base_states=24,
            device="cpu",
            cpu_threads=1,
            output=str(p / "qualification"),
        )
        self.torch = types.ModuleType("torch")
        self.torch.set_num_threads = lambda n: None
        self.torch.get_num_interop_threads = lambda: 1
        FakeHead.mismatch = False

    def tearDown(self):
        FakeHead.mismatch = False
        self.base.tearDown()

    def test_fixed_256_arithmetic_and_complete_5routes_reused_once(self):
        plan = values.qualification_plan(48, 0)
        self.assertEqual(plan["total"], 240)
        self.assertEqual(plan["shared_unissued_margin"], 16)
        for m, extra in [(49, 0), (48, 1), (0, 0), (True, 0)]:
            with self.assertRaises(ValueError):
                values.qualification_plan(m, extra)
        with (
            patch.dict(sys.modules, {"torch": self.torch}),
            patch.object(values, "StaticInputs", FakeEncoder),
            patch.object(values, "StaticHead", FakeHead),
        ):
            result = values.qualify_values(self.config)
            self.assertEqual(result["actual_logical_rows"], 20)
            boundary = json.loads(Path(result["result"]["path"]).read_bytes())
            self.assertEqual(len(boundary["route_rows_attempted"]), 5)
            self.assertEqual(set(boundary["route_rows_attempted"].values()), {4})
            cfg = {
                **self.config,
                "runtime_boundary": result["result"],
                "actual_orientation_rows": 4,
                "inclusive_row_limit": 264,
                "batch_rows": 4,
                "output": str(self.path / "labels"),
            }
            bank = values.label_values(cfg)
        saved = json.loads(Path(bank["manifest"]["path"]).read_bytes())
        self.assertEqual(saved["inclusive_attempted_rows"], 20)
        for kind in ("S", "C"):
            self.assertEqual(saved["teachers"][kind]["reused_boundary_rows"], 4)
            self.assertEqual(saved["teachers"][kind]["new_rows"], 0)
            self.assertIsNone(saved["teachers"][kind]["head"])
            self.assertTrue(
                np.isfinite(
                    np.fromfile(saved["teachers"][kind]["values"]["path"], dtype="<f4")
                ).all()
            )
        self.assertFalse((self.path / "labels/INCOMPLETE").exists())

    def test_actual_mismatch_stops_unentered_routes_without_refill(self):
        FakeHead.mismatch = True
        with (
            patch.dict(sys.modules, {"torch": self.torch}),
            patch.object(values, "StaticInputs", FakeEncoder),
            patch.object(values, "StaticHead", FakeHead),
        ):
            with self.assertRaisesRegex(ValueError, "mismatch"):
                values.qualify_values(self.config)
        failure = json.loads((self.path / "qualification/failure.json").read_bytes())
        self.assertEqual(failure["logical_rows_attempted"], 12)
        self.assertEqual(
            set(failure["route_rows_attempted"]),
            {"S-oldORT-single", "S-Torch-single", "S-Torch-batch"},
        )
        self.assertTrue((self.path / "qualification/INCOMPLETE").exists())
        self.assertFalse((self.path / "qualification/result.json").exists())


if __name__ == "__main__":
    unittest.main()
