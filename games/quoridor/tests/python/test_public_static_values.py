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


class SelectionDiagnosticPublicationBoundary(unittest.TestCase):
    def test_diagnostic_publication_faults_preserve_partial_rows_and_primary_nn0(self):
        """Actual caller/funnel fault injection; all model/native/decision ports are fake."""
        from contextlib import ExitStack, nullcontext
        import tempfile

        from quoridor_training import policy_value_training, static_teacher_inputs

        class Tensor:
            def reshape(self, *args):
                return self

            def scatter_(self, *args):
                return self

            def all(self):
                return True

            def __getitem__(self, index):
                return 0.0

        class Model:
            def __init__(self, *args, **kwargs):
                pass

            def eval(self):
                pass

            def forward_policy_value(self, *args):
                return Tensor(), Tensor()

        tensor = lambda *args, **kwargs: Tensor()
        torch = types.ModuleType("torch")
        torch.tensor = torch.empty_like = torch.from_numpy = torch.ones = torch.isfinite = tensor
        torch.float32, torch.long = "fake-f32", "fake-long"
        torch.set_num_threads = lambda _: None
        torch.get_num_interop_threads = lambda: 1
        torch.inference_mode = nullcontext
        residual = types.ModuleType("quoridor_training.residual_model")
        residual.DistanceResidualModel = Model
        residual.load_policy_head = lambda *args, **kwargs: None
        train = types.ModuleType("quoridor_training.train")
        train.restore_warmstart_parameters = lambda *args: None
        scaled = types.ModuleType("quoridor_training.scaled_model")
        scaled.validate_statistics = lambda _: {}
        corpus_module = types.ModuleType("quoridor_training.static_public_corpus")

        def leaves(error):
            return (
                [leaf for child in error.exceptions for leaf in leaves(child)]
                if isinstance(error, BaseExceptionGroup)
                else [error]
            )

        for mode in (
            "success",
            "cancel_after_7_rows",
            "cancel_after_metadata",
            "cancel_after_complete",
            "close_failure",
            "close_cancel",
            "cancel_after_7_rows_and_close_failure",
            "custody_failure",
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                authority, views = SelectionDiagnosticJoinBoundary.fixture()
                for view in views:
                    view.update(qf1=[0] * 624, distance=[0.0, 0.0])
                authority.update(
                    inputManifest={"path": "/synthetic/input"},
                    teacherBank={"path": "/synthetic/bank"},
                    cache={"path": "/synthetic/cache/cache.json"},
                )
                reference = lambda path: {"path": path}
                current = dict(
                    descriptor=reference("/synthetic/model/manifest.json"),
                    weights=dict(path="/synthetic/model/weights.f32", sha256="0" * 64),
                    policy=reference("/synthetic/model/policy.json"),
                    shared="s",
                    policy_fingerprint="p",
                )
                book = {"openings": [{"prefix": view["prefix"]} for view in views]}
                config = dict(
                    row_authority=reference("/synthetic/authority"),
                    parents_receipt=reference("/synthetic/parents"),
                    book=reference("/synthetic/book"),
                    core_library=reference("/synthetic/library"),
                    current=current,
                    cache_directory="/synthetic/cache",
                    saved_reader_source={"path": "/synthetic/saved-reader"},
                    output=str(Path(temporary) / "diagnostic"),
                    decisions={},
                )
                descriptor = dict(
                    schema="quoridor-nnue-distance-residual-v3",
                    feature="QF1-route4-f32-STM-scaled-residual-v3",
                    topology=dict(ft_width=32, hidden_width=32),
                    route_mode="zero4",
                    distance_fit=dict(a=0, b=0),
                    value_perspective="side-to-move",
                    weights_SHA="0" * 64,
                    weights_B=49284,
                    weights="weights.f32",
                )
                documents = {
                    "/synthetic/authority": authority,
                    "/synthetic/parents": dict(
                        status="COMPLETE",
                        row_authority=config["row_authority"],
                        core_library=config["core_library"],
                        book=config["book"],
                    ),
                    "/synthetic/book": book,
                    "/synthetic/library": {},
                    "/synthetic/cache/cache.json": {},
                    "/synthetic/model/manifest.json": descriptor,
                    "/synthetic/model/policy.json": {},
                }
                for name in ("selected_alpha", "cedar_alpha"):
                    source = dict(
                        configuration=reference(f"/synthetic/{name}-config"),
                        report=reference(f"/synthetic/{name}/result.json"),
                        evaluator_sha256=name,
                        descriptor=current["descriptor"]
                        if name == "selected_alpha"
                        else reference("/synthetic/cedar/manifest.json"),
                    )
                    config["decisions"][name] = source
                    documents[source["configuration"]["path"]] = dict(
                        output=f"/synthetic/{name}",
                        arena=dict(evaluator_sha256=[name]),
                        engines=[dict(model=source["descriptor"]["path"])],
                    )
                    documents[source["report"]["path"]] = {}
                primary = KeyboardInterrupt("synthetic body cancellation")
                close_error = RuntimeError("synthetic close failure")
                close_cancel = KeyboardInterrupt("synthetic close cancellation")
                custody_error = RuntimeError("synthetic custody failure")
                state = dict(closed=False, verifies=0, fired=False, publications=[])

                class Corpus:
                    def __init__(self, directory):
                        self.input_ref = authority["inputManifest"]
                        self.manifest = dict(teacher_values=authority["teacherBank"])
                        self.policy_value, self.policy_temperature = True, 1
                        self.pairs = np.zeros(16, dtype=[("key", "V28"), ("split", "u1")])
                        for i, row in enumerate(authority["rows"]):
                            self.pairs["key"][i] = bytes.fromhex(row["canonicalKey"])
                        self.pairs["split"] = 1
                        self.values = np.zeros((16, 2), dtype=np.float32)

                    def policy_targets(self, pair, orientation):
                        probability = np.zeros((32, 209), dtype=np.float32)
                        probability[:, 0] = 1
                        return probability, probability.astype(bool)

                    def verify_binding(self):
                        state["verifies"] += 1
                        if mode == "custody_failure" and state["verifies"] == 2:
                            raise custody_error

                    def close(self):
                        state["closed"] = True
                        if mode in ("close_failure", "cancel_after_7_rows_and_close_failure"):
                            raise close_error
                        if mode == "close_cancel":
                            raise close_cancel

                corpus_module.StaticTeacherCorpus = Corpus
                original_write = values.write_json

                def publish(path, result):
                    if result["status"] == "COMPLETE":
                        self.assertTrue(state["closed"])
                        self.assertEqual(state["verifies"], 2)
                    state["publications"].append(result["status"])
                    original_write(path, result)

                def trace(frame, event, arg):
                    if frame.f_code is values.selection_diagnostic.__code__ and event == "line":
                        result = frame.f_locals.get("result")
                        if result is not None and not state["fired"]:
                            partial = (
                                mode
                                in ("cancel_after_7_rows", "cancel_after_7_rows_and_close_failure")
                                and len(result["rows"]) == 7
                            )
                            metadata = (
                                mode == "cancel_after_metadata" and "current_identity" in result
                            )
                            complete = (
                                mode == "cancel_after_complete" and result["status"] == "COMPLETE"
                            )
                            if partial or metadata or complete:
                                state["fired"] = True
                                raise primary
                    return trace

                modules = {
                    "torch": torch,
                    "quoridor_training.residual_model": residual,
                    "quoridor_training.train": train,
                    "quoridor_training.scaled_model": scaled,
                    "quoridor_training.static_public_corpus": corpus_module,
                }
                with ExitStack() as stack:
                    stack.enter_context(patch.dict(sys.modules, modules))
                    stack.enter_context(
                        patch.object(
                            values,
                            "bound_file_bytes",
                            side_effect=lambda ref, maximum: json.dumps(
                                documents[ref["path"]]
                            ).encode(),
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            values,
                            "_selection_saved_decision_report",
                            side_effect=lambda source, book_ref, reader_source: (
                                documents[source["configuration"]["path"]],
                                documents[source["report"]["path"]],
                            ),
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            values,
                            "_selection_decision_join",
                            return_value=[{"action": 0} for _ in range(32)],
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            static_teacher_inputs, "native_prefix_views", return_value=views
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            policy_value_training,
                            "native_identity",
                            return_value=dict(shared="s", policy="p"),
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            policy_value_training,
                            "policy_diagnostics",
                            return_value=dict(selection_rows=[{} for _ in range(32)]),
                        )
                    )
                    stack.enter_context(patch.object(values, "write_json", side_effect=publish))
                    previous_trace = sys.gettrace()
                    sys.settrace(trace)
                    try:
                        if mode == "success":
                            values.selection_diagnostic(config)
                            caught = None
                        else:
                            with self.assertRaises(BaseException) as raised:
                                values.selection_diagnostic(config)
                            caught = raised.exception
                    finally:
                        sys.settrace(previous_trace)
                saved = json.loads((Path(config["output"]) / "result.json").read_bytes())
                k = (
                    7
                    if mode in ("cancel_after_7_rows", "cancel_after_7_rows_and_close_failure")
                    else 32
                )
                self.assertEqual(len(saved["rows"]), k)
                self.assertEqual(saved["remaining_rows"], 32 - k)
                self.assertEqual(saved["work"]["joint_attempted_rows"], 32)
                self.assertEqual(saved["work"]["joint_completed_rows"], 32)
                self.assertEqual(saved["work"]["joint_forward_calls"], 1)
                self.assertTrue(state["closed"])
                marker = Path(config["output"]) / "INCOMPLETE"
                if mode == "success":
                    self.assertEqual(saved["status"], "COMPLETE")
                    self.assertNotIn("error", saved)
                    self.assertFalse(marker.exists())
                    self.assertEqual(state["publications"], ["COMPLETE"])
                else:
                    self.assertEqual(saved["status"], "INCOMPLETE")
                    self.assertIn("error", saved)
                    self.assertTrue(marker.exists())
                    self.assertNotIn("COMPLETE", state["publications"])
                    expected = (
                        [primary, close_error]
                        if mode == "cancel_after_7_rows_and_close_failure"
                        else [close_error]
                        if mode == "close_failure"
                        else [close_cancel]
                        if mode == "close_cancel"
                        else [custody_error]
                        if mode == "custody_failure"
                        else [primary]
                    )
                    self.assertEqual(leaves(caught), expected)

                    def types_in(record):
                        return [record["type"]] + [
                            kind for child in record.get("errors", []) for kind in types_in(child)
                        ]

                    for error in expected:
                        self.assertIn(type(error).__name__, types_in(saved["error"]))


class SelectionSavedPublicationBoundary(unittest.TestCase):
    """Synthetic normal files through the REAL maintained reference-result reader."""

    @staticmethod
    def fixture(root):
        import copy
        import gzip

        root.mkdir()
        authority, views = SelectionDiagnosticJoinBoundary.fixture()
        book = {"openings": [{"prefix": view["prefix"]} for view in views]}
        output = root / "data"
        output.mkdir()

        def store(path, value):
            path.write_text(json.dumps(value, allow_nan=False))
            path.chmod(0o644)
            return ref(path)

        book_ref = store(root / "book.json", book)
        configuration = dict(
            output=str(output),
            run_id="synthetic-saved-decisions",
            games=32,
            max_plies=200,
            ruleset="standard_2p_threefold",
            arena=dict(
                decision_only=True,
                comparison="whole_wall_time",
                clock_policy="strict_unknown",
                return_reserve_ms=5,
                retained_outcome_bytes=32768,
                book=book,
            ),
            engines=[dict(kind="nnue", lmr=False)],
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
        configuration_ref = store(root / "configuration.json", configuration)
        build = store(root / "build.json", dict(artifact=dict(sha256="f" * 64)))
        plan = store(root / "plan.json", dict(phase="compare", book=book_ref))
        experiment = store(
            root / "experiment.json",
            dict(
                config=configuration_ref,
                phase="compare",
                canonical_plan_sha256=plan["sha256"],
                build_manifest=build,
            ),
        )
        intent = store(root / "intent.json", dict(approved_plan=plan, experiment=experiment))
        outcomes = []
        for i, view in enumerate(views):
            outcomes.append(
                dict(
                    game=i,
                    family=f"{configuration['run_id']}-family-{i:06}",
                    moves=view["prefix"],
                    winner=None,
                    status="decision",
                    failure=None,
                    started=True,
                    observations=[
                        dict(
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
                    ],
                )
            )
        raw = b"".join((json.dumps(row) + "\n").encode() for row in outcomes)
        journal = output / "completed.jsonl.gz"
        journal.write_bytes(gzip.compress(raw, mtime=0))
        journal.chmod(0o644)
        journal_ref = ref(journal)
        report = dict(
            schema="quoridor-decisions-v1",
            run_id=configuration["run_id"],
            planned=32,
            outcomes=[],
            stopped=None,
            all_workers_joined=True,
            rows=0,
            dataset=None,
            score=None,
        )
        publication = dict(
            schema="quoridor.arena.reference-result.v1",
            report=report,
            archive=dict(
                encoding="gzip-single-member-v1",
                compressed=journal_ref,
                raw_sha256=hashlib.sha256(raw).hexdigest(),
                raw_bytes=len(raw),
            ),
            outcome_count=32,
            journal_count=32,
            journal_bytes=len(raw),
            journal_sha256=hashlib.sha256(raw).hexdigest(),
            failure_attribution=None,
            archive_wall_seconds=0.0,
            archive_allocated_bytes=0,
        )
        result_ref = store(output / "result.json", publication)
        manifest = dict(
            result=publication,
            binding=dict(config=copy.deepcopy(configuration), executable_sha256="f" * 64),
            cleanup=dict(archive_closed_verified=True, all_workers_joined=True),
            artifacts={
                "result.json": {k: result_ref[k] for k in ("sha256", "bytes", "mode")},
                "completed.jsonl.gz": {k: journal_ref[k] for k in ("sha256", "bytes", "mode")},
            },
        )
        native = store(output / "manifest.json", manifest)
        completion = dict(
            schema="quoridor.research.completion.v1",
            kind="run",
            status="PASS",
            primary=None,
            secondary=[],
            cleanup_complete=True,
            remaining=[],
            experiment=experiment,
            intent=intent,
            data=dict(files=[journal_ref, result_ref, native]),
        )
        completion_path = root / "completion.json"
        source = dict(
            completion=store(completion_path, completion),
            configuration=configuration_ref,
            report=result_ref,
        )
        # Source dependency only. No experiment/model/library/input body is read.
        reader = ref(Path("/workspaces/quoridor/scripts/dev/research-lifecycle.py"))
        return dict(
            source=source,
            book_ref=book_ref,
            book=book,
            views=views,
            reader=reader,
            completion=completion,
            completion_path=completion_path,
            publication=publication,
            manifest=manifest,
            output=output,
            store=store,
        )

    def test_compact_decisions_use_one_real_saved_decode_nn0(self):
        import os
        import tempfile
        import zlib

        with tempfile.TemporaryDirectory() as directory:
            fixture = self.fixture(Path(directory) / "producer")
            source = fixture["source"]
            original = json.loads(Path(source["report"]["path"]).read_bytes())
            self.assertEqual(original["schema"], "quoridor.arena.reference-result.v1")
            self.assertEqual(original["report"]["outcomes"], [])
            before = set(Path(directory).rglob("*"))
            with (
                patch.object(os, "open", wraps=os.open) as opened,
                patch.object(zlib, "decompressobj", wraps=zlib.decompressobj) as decoder,
            ):
                config, report = values._selection_saved_decision_report(
                    source, fixture["book_ref"], fixture["reader"]
                )
            self.assertEqual(decoder.call_count, 1)
            journal = str(fixture["output"] / "completed.jsonl.gz")
            self.assertEqual(sum(str(c.args[0]) == journal for c in opened.call_args_list), 1)
            self.assertEqual(report["schema"], "quoridor-decisions-v1")
            self.assertEqual(len(report["outcomes"]), 32)
            self.assertEqual(
                len(
                    values._selection_decision_join(
                        report, config, fixture["book"], fixture["views"]
                    )
                ),
                32,
            )
            self.assertEqual(set(Path(directory).rglob("*")), before)
            self.assertEqual(json.loads(Path(source["report"]["path"]).read_bytes()), original)

    def test_saved_producer_and_archive_correspondence_refuses_nn0(self):
        import tempfile

        for cause in (
            "missing_journal",
            "changed_journal_sha",
            "changed_producer",
            "wrong_archive_ref",
        ):
            with self.subTest(cause=cause), tempfile.TemporaryDirectory() as directory:
                fixture = self.fixture(Path(directory) / "producer")
                source, completion = fixture["source"], fixture["completion"]
                store = fixture["store"]
                if cause == "missing_journal":
                    completion["data"]["files"].pop(0)
                elif cause == "changed_journal_sha":
                    completion["data"]["files"][0] = {
                        **completion["data"]["files"][0],
                        "sha256": "0" * 64,
                    }
                elif cause == "changed_producer":
                    source["configuration"] = store(
                        Path(directory) / "different-configuration.json", {"synthetic": True}
                    )
                else:
                    publication = fixture["publication"]
                    publication["archive"]["compressed"] = {
                        **publication["archive"]["compressed"],
                        "sha256": "0" * 64,
                    }
                    source["report"] = store(fixture["output"] / "result.json", publication)
                    fixture["manifest"]["result"] = publication
                    fixture["manifest"]["artifacts"]["result.json"] = {
                        k: source["report"][k] for k in ("sha256", "bytes", "mode")
                    }
                    completion["data"]["files"][1] = source["report"]
                    completion["data"]["files"][2] = store(
                        fixture["output"] / "manifest.json", fixture["manifest"]
                    )
                source["completion"] = store(fixture["completion_path"], completion)
                with self.assertRaises(ValueError):
                    values._selection_saved_decision_report(
                        source, fixture["book_ref"], fixture["reader"]
                    )


if __name__ == "__main__":
    unittest.main()
