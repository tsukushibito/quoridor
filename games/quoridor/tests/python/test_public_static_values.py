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


class SelectionDiagnosticJoinBoundary(unittest.TestCase):
    """New metadata/frame join only; no native decoder, model, Search or RNG."""

    @staticmethod
    def fixture():
        authority = {"shape": {"values": [1280, 2]}, "rows": []}
        views = []
        for i in range(16):
            a = bytes([2 * i + 1]) * 28
            b = bytes([2 * i + 2]) * 28
            authority["rows"].append(
                dict(
                    validationOrdinal0=i,
                    nativeRank0=1024 + i,
                    split=1,
                    selfLR=False,
                    pairIndex=i,
                    originalMultiplicity=1,
                    component=f"synthetic-component-{i}",
                    member=f"synthetic-member-{i}",
                    publisherSourceSeriesOrdinal=100 + i,
                    sourceReceiptPointer=f"/source_receipts/{i}",
                    fullHistoryByrefPointer=f"/source_receipts/{i}/history",
                    originalKey=a.hex(),
                    trueLRKey=b.hex(),
                    canonicalKey=a.hex(),
                    views=[
                        dict(
                            view=name,
                            bankOrientation=j,
                            orientedRow0=2 * i + j,
                            valueByteOffset=4 * (2 * i + j),
                            policyByteOffset=4 * 209 * (2 * i + j),
                            maskByteOffset=209 * (2 * i + j),
                        )
                        for j, name in enumerate(("original", "trueLR"))
                    ],
                )
            )
            for key in (a, b):
                views.append(
                    dict(
                        key=key.hex(),
                        side=i % 2,
                        action_to_key=list(range(209)),
                        legal_in_key=[1] + [0] * 208,
                        prefix=[i],
                    )
                )
        return authority, views

    def test_saved_v_frame_mismatch_refuses_before_model_or_bank_nn0(self):
        import copy

        authority, views = self.fixture()
        with patch.dict(sys.modules, {"torch": None}):
            self.assertEqual(len(values._selection_frame_join(authority, views)), 32)
            for field, bad in (
                ("key", "ff" * 28),
                ("side", True),
                ("action_to_key", [0] * 209),
                ("legal_in_key", [0] * 209),
            ):
                changed = copy.deepcopy(views)
                changed[0][field] = bad
                with self.assertRaises(ValueError):
                    values._selection_frame_join(authority, changed)
            for field, bad in (
                ("split", 0),
                ("selfLR", True),
                ("nativeRank0", 1025),
            ):
                changed = copy.deepcopy(authority)
                changed["rows"][0][field] = bad
                with self.assertRaises(ValueError):
                    values._selection_frame_join(changed, views)
            changed = copy.deepcopy(authority)
            changed["rows"][0]["views"][0]["valueByteOffset"] = 1
            with self.assertRaises(ValueError):
                values._selection_frame_join(changed, views)

    def test_normal_decisions_join_refuses_changed_parent_side_or_receipt_nn0(self):
        import copy

        _, views = self.fixture()
        book = {"openings": [{"prefix": v["prefix"]} for v in views]}
        configuration = dict(
            run_id="synthetic-decisions",
            games=32,
            arena=dict(
                decision_only=True,
                book=book,
                comparison="whole_wall_time",
                clock_policy="strict_unknown",
                return_reserve_ms=5,
            ),
            ruleset="standard_2p_threefold",
            engines=[{"kind": "nnue"}],
        )
        outcomes = []
        for i, view in enumerate(views):
            observation = dict(
                side=view["side"],
                engine_index=0,
                action=0,
                accepted=True,
                failure=None,
                engine_error=None,
                caller_started_ns=0,
                deadline_ns=100_000_000,
                returned_ns=101_000_000,
                counters=dict(
                    authority_receipt_ns=99_000_000,
                    drain_finished_ns=101_000_000,
                    inflight_after_drain=0,
                ),
            )
            outcomes.append(
                dict(
                    game=i,
                    family=f"synthetic-decisions-family-{i:06}",
                    moves=view["prefix"],
                    winner=None,
                    status="decision",
                    failure=None,
                    observations=[observation],
                )
            )
        report = dict(
            schema="quoridor-decisions-v1",
            run_id=configuration["run_id"],
            planned=32,
            outcomes=outcomes,
            stopped=None,
            all_workers_joined=True,
            rows=0,
            dataset=None,
            score=None,
        )
        # Timely immutable receipt remains separate from late returned/drain time.
        self.assertEqual(
            len(values._selection_decision_join(report, configuration, book, views)), 32
        )
        with patch.object(
            values,
            "bound_file_bytes",
            return_value=json.dumps(
                dict(
                    schema="quoridor.research.completion.v1",
                    kind="run",
                    status="FAILED",
                )
            ).encode(),
        ):
            with self.assertRaises(ValueError):
                values._selection_producer(
                    {"completion": {"path": "/synthetic-never-opened"}}, {"path": "/book"}
                )
        for case in range(5):
            bad = copy.deepcopy(report)
            row = bad["outcomes"][0]
            if case == 0:
                row["moves"] = [208]
            elif case == 1:
                row["observations"][0]["side"] = 1
            elif case == 2:
                row["observations"][0]["counters"]["authority_receipt_ns"] = 100_000_000
            elif case == 3:
                row["observations"][0]["accepted"] = False
            else:
                row["observations"].append(copy.deepcopy(row["observations"][0]))
            with self.assertRaises(ValueError):
                values._selection_decision_join(bad, configuration, book, views)

    def test_parent_source_join_retains_family_and_fixture_distinction_nn0(self):
        import copy
        from quoridor_training import static_teacher_inputs

        authority, views = self.fixture()
        authority["inputManifest"] = {"path": "/synthetic-not-opened"}
        source = dict(
            schema="quoridor-public-static-input-classes-v1",
            status="COMPLETE",
            source_receipts=[
                dict(
                    functional_split="V",
                    fixture=i,
                    family=row["publisherSourceSeriesOrdinal"],
                    original_key=row["originalKey"],
                    reflected_key=row["trueLRKey"],
                    canonical_key=row["canonicalKey"],
                    history=views[2 * i]["prefix"],
                )
                for i, row in enumerate(authority["rows"])
            ],
        )
        with (
            patch.object(values, "bound_file_bytes", return_value=json.dumps(source).encode()),
            patch.object(
                static_teacher_inputs, "native_prefix_views", return_value=views
            ) as native,
        ):
            self.assertEqual(values._selection_native_parents(authority, "fake-library"), views)
            self.assertEqual(native.call_count, 1)
        bad = copy.deepcopy(source)
        bad["source_receipts"][0]["family"] += 1
        with (
            patch.object(values, "bound_file_bytes", return_value=json.dumps(bad).encode()),
            patch.object(static_teacher_inputs, "native_prefix_views") as native,
        ):
            with self.assertRaises(ValueError):
                values._selection_native_parents(authority, "fake-library")
            native.assert_not_called()

    def test_native_prefix_view_abi_matches_existing_public_owners_nn0(self):
        import ctypes
        import os
        from quoridor_training.public_static_prepare import native_prefix_keys
        from quoridor_training.public_features import features, input_records
        from quoridor_training.static_teacher_inputs import StaticInputs, native_prefix_views

        # Root binds the NEW built library explicitly. Missing binding FAILS,
        # never skip/PASS; no model, teacher, forward or numerical payload.
        library = os.environ["QUORIDOR_DIAGNOSTIC_FRAME_LIBRARY"]
        histories = [[3], [3, 67]]
        views = native_prefix_views(histories, library)
        old_keys = native_prefix_keys([{"history": h} for h in histories], library)
        keys = [key for pair in old_keys for key in pair]
        self.assertEqual([v["key"] for v in views], [key.hex() for key in keys])
        self.assertEqual([v["side"] for v in views], [1, 1, 0, 0])
        encoder = StaticInputs.__new__(StaticInputs)
        encoder.batch_rows = 4
        encoder.core = ctypes.CDLL(library)
        legal = encoder.policy_mask(np.asarray(keys, dtype="V28"))
        self.assertTrue(np.array_equal(legal, np.asarray([v["legal_in_key"] for v in views])))
        # At actual STM0 the native public/absolute input frames are identical.
        # This checks cross-language buffer layout without assuming LR invariance.
        x = features(input_records(np.asarray(keys[2:], dtype="V28"))["geometry"])
        self.assertTrue(
            np.array_equal(x, np.asarray([v["qf1"] for v in views[2:]]).reshape(2, 2, 312))
        )


if __name__ == "__main__":
    unittest.main()
