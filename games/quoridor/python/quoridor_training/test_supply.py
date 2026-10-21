"""Independent geometry oracle and bounded deterministic worker/lease contracts."""

from copy import deepcopy
import ast
import json
from pathlib import Path
import tempfile
import time
import sys
import threading
import unittest
from unittest.mock import patch

import numpy as np

from .compact_cache import CompactCorpus
from .public_features import RECORD, FeatureWorkspace, features
from .sampling import EpochSampler, ReflectionBatches
from .supply import FLOATS_PER_ROW, OrderedPrefetch, PackedSupply, payload_views
from .test_public_features import scalar_reference, scalar_reflection


class Host(np.ndarray):
    def numpy(self):
        return self


class FakeTorch:
    float32, long = np.float32, np.int64

    @staticmethod
    def empty(size, **kwargs):
        return np.empty(size, dtype=kwargs["dtype"]).view(Host)

    @staticmethod
    def ones(size, **kwargs):
        return np.ones(size, dtype=kwargs["dtype"])


def corpus(rows=4861):
    value = object.__new__(CompactCorpus)
    rng = np.random.default_rng(71)
    records = np.zeros(rows + 2, dtype=RECORD)
    records["geometry"]["pawns"] = [[0, 80]]
    records["geometry"]["stocks"] = rng.integers(0, 11, size=(rows + 2, 2))
    records["geometry"]["horizontal"] = rng.integers(0, 2**64, size=rows + 2, dtype=np.uint64)
    records["geometry"]["vertical"] = rng.integers(0, 2**64, size=rows + 2, dtype=np.uint64)
    records["distance"] = rng.random((rows + 2, 2), dtype=np.float32)
    records["z"] = rng.choice([-1, 1], rows + 2)
    records.flags.writeable = False
    value.maps, value.offsets, value.row_count = [records], np.array([0, rows + 2]), rows + 2
    value.splits = np.concatenate((np.zeros(rows, np.uint8), np.ones(2, np.uint8)))
    value.labels = np.empty((rows + 2, 2), np.float32)
    value.labels[:, 0], value.labels[:, 1] = np.nan, records["z"]
    return value


class FeatureContracts(unittest.TestCase):
    def test_independent_both_views_reflection_all_anchors(self):
        c = corpus(128)
        g = c.records(np.arange(128))["geometry"]
        mask = np.arange(128) % 3 == 0
        reference = np.stack(
            [scalar_reference(scalar_reflection(p) if mask[i] else p) for i, p in enumerate(g)]
        )
        out = np.full((128, 2, 312), 999, np.float32)
        work = FeatureWorkspace(128)
        self.assertIs(features(g, mask, out=out, workspace=work), out)
        np.testing.assert_array_equal(out, reference)
        np.testing.assert_array_equal(
            features(g, out=out, workspace=work), np.stack([scalar_reference(p) for p in g])
        )
        np.testing.assert_array_equal(g, c.maps[0]["geometry"][:128])

    def test_each_wall_decoded_once_and_full_initialization(self):
        from . import public_features

        g = corpus(3).records(np.arange(3))["geometry"]
        with patch.object(public_features, "wall_bits", wraps=public_features.wall_bits) as decode:
            out = features(g, np.ones(3, bool))
        self.assertEqual(decode.call_count, 2)
        self.assertTrue(np.isin(out, [0, 1]).all())
        self.assertEqual(out.dtype, np.float32)
        self.assertTrue(out.flags.c_contiguous)

    def test_malformed_geometry_mask_output_workspace_rejected(self):
        g = corpus(3).records(np.arange(3))["geometry"]
        for mask in (np.zeros(3, np.uint8), np.zeros(4, bool)):
            with self.assertRaises(ValueError):
                features(g, mask)
        for out in (
            np.zeros((3, 2, 312), np.float64),
            np.zeros((3, 312, 2), np.float32),
            np.zeros((3, 2, 624), np.float32)[:, :, ::2],
        ):
            with self.assertRaises(ValueError):
                features(g, out=out)
        with self.assertRaises(ValueError):
            features(g, workspace=FeatureWorkspace(2))
        invalid = g.copy()
        invalid["pawns"][0] = [1, 1]
        with self.assertRaises(ValueError):
            features(invalid)

    def test_payload_blocks_contiguous_same_dtype_no_overlap(self):
        storage = np.zeros(2048 * FLOATS_PER_ROW, np.float32)
        for n in (2048, 765):
            parts = payload_views(storage, n)
            for i, x in enumerate(parts):
                self.assertTrue(x.flags.c_contiguous)
                self.assertEqual(x.dtype, np.float32)
                self.assertTrue(np.shares_memory(storage, x))
                self.assertTrue(all(not np.shares_memory(x, y) for y in parts[:i]))
        with self.assertRaises(ValueError):
            payload_views(storage, 2049)


class WorkerContracts(unittest.TestCase):
    def test_order_capacity_and_failure_cleanup(self):
        q = OrderedPrefetch(2)
        q.submit(0, 1, lambda: 0)
        q.submit(1, 1, lambda: 1)
        q.submit(2, 1, lambda: 2)
        with self.assertRaises(ValueError):
            q.submit(3, 1, lambda: 3)
        with self.assertRaises(ValueError):
            q.take(1)
        self.assertEqual([q.take(i) for i in range(3)], [0, 1, 2])
        q.close()
        q.close()
        self.assertFalse(any(t.name.startswith("qf1-supply") for t in threading.enumerate()))

    def test_pending_failure_shutdown_and_consumed_not_success(self):
        q = OrderedPrefetch(1)
        q.submit(0, 5, lambda: (_ for _ in ()).throw(ValueError("worker failure")))
        q.submit(1, 7, lambda: 1)
        with self.assertRaisesRegex(ValueError, "worker failure"):
            q.take(0)
        q.close()
        self.assertEqual(q.dispatched_rows, 12)
        self.assertEqual(q.consumed_rows, 0)
        self.assertEqual(q.expanded_rows, 7)
        self.assertFalse(any(t.name.startswith("qf1-supply") for t in threading.enumerate()))

    def test_drain_failure_still_joins_worker(self):
        q = OrderedPrefetch(1)
        q.submit(0, 3, lambda: (_ for _ in ()).throw(ValueError("drain failure")))
        with self.assertRaises(BaseExceptionGroup):
            q.close()
        self.assertTrue(q.closed)
        self.assertFalse(any(t.name.startswith("qf1-supply") for t in threading.enumerate()))

    def test_modes_order_masks_tail_targets_rng_and_no_corpus_duplicate(self):
        c = corpus()
        observations = []
        for workers in (0, 1, 2, 4):
            reflected = ReflectionBatches(c, 0.5, 32320261008)
            sampler = EpochSampler(np.arange(4861), 2048, 32320261007)
            reference_rng = np.random.default_rng(32320261008)
            seen, masks, sizes = [], [], []
            with patch.dict(sys.modules, {"torch": FakeTorch}):
                pipe = PackedSupply(
                    reflected, 2048, "cpu", np.ones(c.row_count, np.float32), 1, workers=workers
                )
            self.assertIs(pipe.corpus, c)
            try:
                for _ in range(2):
                    while True:
                        ix = sampler.next_batch()
                        mask = reference_rng.random(len(ix)) < 0.5
                        inputs, targets, weights = pipe.batch(ix, training=True, sampler=sampler)
                        np.testing.assert_array_equal(
                            inputs[0], features(c.records(ix)["geometry"], mask)
                        )
                        np.testing.assert_array_equal(inputs[1], c.records(ix)["distance"])
                        np.testing.assert_array_equal(inputs[2], np.ones(len(ix), np.int64))
                        np.testing.assert_array_equal(targets, c.labels[ix, 1])
                        np.testing.assert_array_equal(weights, np.ones(len(ix), np.float32))
                        self.assertTrue(
                            all(x.flags.c_contiguous for x in (*inputs, targets, weights))
                        )
                        for _, _, pending_slot in pipe.descriptors:
                            self.assertFalse(
                                np.shares_memory(pipe.active["numpy"], pending_slot["numpy"])
                            )
                        state = deepcopy(reflected.generator.bit_generator.state)
                        pipe.batch(np.array([4861, 4862]))
                        self.assertEqual(state, reflected.generator.bit_generator.state)
                        seen.extend(ix.tolist())
                        masks.extend(mask.tolist())
                        sizes.append(len(ix))
                        if sampler.cursor == 4861:
                            break
                self.assertEqual(sizes, [2048, 2048, 765] * 2)
                self.assertEqual(len(set(seen[:4861])), 4861)
                self.assertEqual(reflected.training_seen, 9722)
                self.assertEqual(reflected.reflected_seen, sum(masks))
                self.assertEqual(sampler.seen, 9722)
                observations.append(
                    (seen, masks, deepcopy(reflected.generator.bit_generator.state))
                )
            finally:
                pipe.close()
            self.assertFalse(any(t.name.startswith("qf1-supply") for t in threading.enumerate()))
        self.assertEqual(observations[0], observations[1])
        self.assertEqual(observations[0], observations[2])
        self.assertEqual(observations[0], observations[3])

    def test_bad_training_partition_capacity_and_close(self):
        c = corpus(4)
        with patch.dict(sys.modules, {"torch": FakeTorch}):
            pipe = PackedSupply(
                ReflectionBatches(c, 0.5, 2), 4, "cpu", np.ones(6, np.float32), 1, workers=1
            )
        try:
            for ix in (np.array([4]), np.arange(5), np.array([[0]])):
                with self.assertRaises(ValueError):
                    pipe.batch(ix, training=True)
        finally:
            pipe.close()
        with self.assertRaises(ValueError):
            pipe.batch(np.array([0]))


def exception_leaves(error):
    if isinstance(error, BaseExceptionGroup):
        return [leaf for part in error.exceptions for leaf in exception_leaves(part)]
    return [error]


class FinalizationContracts(unittest.TestCase):
    """Run the actual trainer finalbody/persist AST, without importing Torch/model."""

    def finalizer(
        self,
        root,
        pipe,
        *,
        primary=None,
        state="LAST_COMPLETED_UPDATE",
        checkpoint_error=None,
        persist_error=None,
    ):
        from . import train

        tree = ast.parse(Path(train.__file__).read_text())
        function = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train"
        )
        terminal = next(
            n
            for n in ast.walk(function)
            if isinstance(n, ast.Try)
            and any(
                isinstance(c, ast.Call)
                and isinstance(c.func, ast.Name)
                and c.func.id == "_finalize_training"
                for part in n.finalbody
                for c in ast.walk(part)
            )
        )
        observed = []
        previous = root / "last.pt"
        previous.write_bytes(b"previous exact LAST")

        def checkpoint(name):
            observed.append("checkpoint:" + name)
            if checkpoint_error:
                raise checkpoint_error
            previous.write_bytes(b"completed update LAST")
            env["checkpoint_positions"][name] = {"step": 2, "training_seen": 2}

        def persist():
            observed.append("persist")
            (root / "visits.json").write_text("[1,1]")
            (root / "run-status.json").write_text(
                json.dumps({"successful_step": 2, "successful_rows": 2, "state": state})
            )
            if persist_error:
                raise persist_error

        env = {
            "packed_supply": pipe,
            "measurement": None,
            "model_state_status": state,
            "save_named_checkpoint": checkpoint,
            "persist": persist,
            "output": root,
            "status": "INTERRUPTED" if primary else "DIAGNOSTIC_EPOCH_COMPLETED",
            "fault": None
            if primary is None
            else {"type": type(primary).__name__, "message": str(primary)},
            "position": lambda: {"step": 2, "training_seen": 2},
            "attempted_step": 3,
            "checkpoint_positions": {"last": {"step": 1}},
            "_finalize_training": train._finalize_training,
            "sys": sys,
            "primary": primary,
            "primary_error": None,
            "stop_record_failures": [],
        }
        body = [ast.Raise(exc=ast.Name(id="primary", ctx=ast.Load()))] if primary else [ast.Pass()]
        node = ast.FunctionDef(
            name="actual_finalizer",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=[ast.Try(body=body, handlers=[], orelse=[], finalbody=terminal.finalbody)],
            decorator_list=[],
        )
        module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
        exec(compile(module, train.__file__, "exec"), env)
        caught = None
        try:
            env["actual_finalizer"]()
        except BaseException as error:
            caught = error
        return observed, caught, previous.read_bytes()

    def failed_pipe(self):
        pipe = object.__new__(PackedSupply)
        pipe.closed = False
        pipe.active = None
        pipe.device = "cpu"
        pipe.slots = [{"ready": None, "consumer": None}]
        pipe.evaluation_slot = {"ready": None, "consumer": None}
        pipe.transfer_stream = None
        pipe.timing = {"lease_wait_seconds": 0.0}
        pipe.queue = OrderedPrefetch(1)
        pipe.queue.submit(
            "unconsumed-next-batch",
            765,
            lambda: (_ for _ in ()).throw(ValueError("pending lookahead expansion failure")),
        )
        return pipe

    def test_actual_finalbody_failed_future_still_saves_LAST_visits_status(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pipe = self.failed_pipe()
            observed, caught, last = self.finalizer(root, pipe)
            self.assertEqual(observed, ["checkpoint:last", "persist"])
            self.assertEqual(last, b"completed update LAST")
            self.assertEqual(json.loads((root / "visits.json").read_text()), [1, 1])
            receipt = json.loads((root / "finalization-errors.json").read_text())
            self.assertEqual(receipt["original_stop_and_position"]["training_seen"], 2)
            self.assertEqual(receipt["stages"][0]["status"], "FAILED")
            self.assertEqual(
                receipt["original_stop_and_position"]["checkpoint_positions"]["last"]["step"], 2
            )
            self.assertIn(
                "pending lookahead expansion failure", [str(e) for e in exception_leaves(caught)]
            )
            self.assertTrue(pipe.closed and pipe.queue.closed)
            self.assertFalse(any(t.name.startswith("qf1-supply") for t in threading.enumerate()))

    def test_primary_cancel_cleanup_checkpoint_persist_errors_all_retained(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            primary = KeyboardInterrupt("owner cancel")
            observed, caught, last = self.finalizer(
                root,
                self.failed_pipe(),
                primary=primary,
                checkpoint_error=OSError("checkpoint storage refusal"),
                persist_error=OSError("persist refusal"),
            )
            leaves = exception_leaves(caught)
            self.assertIs(leaves[0], primary)
            self.assertEqual(
                {str(e) for e in leaves},
                {
                    "owner cancel",
                    "pending lookahead expansion failure",
                    "checkpoint storage refusal",
                    "persist refusal",
                },
            )
            self.assertEqual(observed, ["checkpoint:last", "persist"])
            self.assertEqual(last, b"previous exact LAST")
            self.assertTrue((root / "run-status.json").exists())
            self.assertEqual(
                json.loads((root / "finalization-errors.json").read_text())["primary_exception"][
                    "type"
                ],
                "KeyboardInterrupt",
            )

    def test_UNKNOWN_update_keeps_previousLAST_and_persists_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            observed, caught, last = self.finalizer(
                root,
                self.failed_pipe(),
                primary=ValueError("nonfinite after update"),
                state="UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN",
            )
            self.assertEqual(observed, ["persist"])
            self.assertEqual(last, b"previous exact LAST")
            self.assertEqual(str(exception_leaves(caught)[0]), "nonfinite after update")
            self.assertEqual(
                json.loads((root / "run-status.json").read_text())["state"],
                "UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN",
            )

    def test_clean_finalbody_preserves_original_primary_and_calls_all_actions(self):
        class Pipe:
            def close(self):
                pass

        with tempfile.TemporaryDirectory() as d:
            primary = ValueError("original failed forward")
            observed, caught, _ = self.finalizer(Path(d), Pipe(), primary=primary)
            self.assertIs(caught, primary)
            self.assertEqual(observed, ["checkpoint:last", "persist"])
            self.assertFalse((Path(d) / "finalization-errors.json").exists())

    def test_error_receipt_write_failure_still_preserves_facts_in_exception(self):
        from . import train

        with (
            tempfile.TemporaryDirectory() as d,
            patch.object(train, "write", side_effect=OSError("error receipt IO failed")),
        ):
            observed, caught, _ = self.finalizer(
                Path(d), self.failed_pipe(), primary=ValueError("primary")
            )
            self.assertEqual(observed, ["checkpoint:last", "persist"])
            self.assertIn("error receipt IO failed", [str(e) for e in exception_leaves(caught)])
            self.assertIn('"training_seen": 2', caught.__notes__[0])

    def test_real_persist_continues_status_counts_when_other_files_fail(self):
        from . import train

        tree = ast.parse(Path(train.__file__).read_text())
        function = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train"
        )
        persist = next(
            n for n in function.body if isinstance(n, ast.FunctionDef) and n.name == "persist"
        )
        for fail in ("curves", "gradients.json", "sampling-counts.npz", "sampling.json"):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                written = []

                def write(path, value):
                    written.append(path.name)
                    if path.name == fail:
                        raise OSError(fail)
                    train.write(path, value)

                def curves():
                    if fail == "curves":
                        raise OSError("curves")

                def counts(path, indices, values, attempts):
                    written.append(path.name)
                    if path.name == fail:
                        raise OSError(fail)
                    return train.write_sampling_counts(path, indices, values, attempts)

                from types import SimpleNamespace

                env = {
                    "time": time,
                    "persist_curves": curves,
                    "_attempt_finalization": train._attempt_finalization,
                    "write": write,
                    "write_sampling_counts": counts,
                    "output": root,
                    "np": np,
                    "phase_seconds": {"logging": 0.0},
                    "compact": True,
                    "unbounded": True,
                    "batch_records_logged": 1,
                    "position": lambda: {"step": 2, "training_seen": 2},
                    "sampled_rows": np.array([1, 1]),
                    "attempted_rows": np.array([1, 1]),
                    "ix_train": np.array([0, 1]),
                    "mode": "epoch",
                    "attempted_step": 3,
                    "completed_step": 2,
                    "families": [],
                    "group_indices": [],
                    "cfg": {"training": {"loss_weighting": "row"}},
                    "supply": SimpleNamespace(training_seen=2, reflected_seen=1),
                    "epoch_sampler": SimpleNamespace(seen=2),
                    "packed_supply": None,
                    "status": "INTERRUPTED",
                    "fault": {"message": "primary"},
                    "model_state_status": "LAST_COMPLETED_UPDATE",
                    "best_exposure": None,
                    "last_completed_point": None,
                    "checkpoint_positions": {"last": {"step": 1}},
                    "samples": 2,
                    "forward_rows": {},
                    "completed_forward_rows": {},
                    "start": time.monotonic(),
                }
                exec(
                    compile(
                        ast.fix_missing_locations(ast.Module(body=[persist], type_ignores=[])),
                        train.__file__,
                        "exec",
                    ),
                    env,
                )
                with self.assertRaises(BaseExceptionGroup):
                    env["persist"]()
                self.assertIn("run-status.json", written)
                self.assertEqual(
                    json.loads((root / "run-status.json").read_text())["training_seen"], 2
                )
                if fail != "sampling-counts.npz":
                    with np.load(root / "sampling-counts.npz") as visits:
                        np.testing.assert_array_equal(visits["row_counts"], [1, 1])

    def production_handlers(
        self,
        root,
        primary,
        *,
        log_error=None,
        cleanup_error=None,
        checkpoint_error=None,
        persist_error=None,
        state="LAST_COMPLETED_UPDATE",
    ):
        from . import train

        tree = ast.parse(Path(train.__file__).read_text())
        function = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "train"
        )
        terminal = next(
            n
            for n in ast.walk(function)
            if isinstance(n, ast.Try)
            and any(
                isinstance(c, ast.Call)
                and isinstance(c.func, ast.Name)
                and c.func.id == "_finalize_training"
                for part in n.finalbody
                for c in ast.walk(part)
            )
        )
        owner = next(
            n for n in ast.walk(function) if isinstance(n, ast.With) and terminal in n.body
        )
        # Production pre-try captured-primary locals, actual except handlers and finally.
        initialization = owner.body[: owner.body.index(terminal)]
        observed = []
        previous = root / "last.pt"
        previous.write_bytes(b"previous exact LAST")

        class Pipe:
            def close(self):
                observed.append("close")
                if cleanup_error:
                    raise cleanup_error

        def append_record(*args):
            observed.append("stop-record")
            if log_error:
                raise log_error

        def checkpoint(name):
            observed.append("checkpoint:" + name)
            if checkpoint_error:
                raise checkpoint_error
            previous.write_bytes(b"completed update LAST")
            env["checkpoint_positions"][name] = {"step": 2, "training_seen": 2}

        def persist():
            observed.append("persist")
            (root / "visits.json").write_text("[1,1]")
            if persist_error:
                raise persist_error

        env = {
            "sys": sys,
            "primary": primary,
            "packed_supply": Pipe(),
            "measurement": None,
            "model_state_status": state,
            "save_named_checkpoint": checkpoint,
            "persist": persist,
            "output": root,
            "status": "RUNNING",
            "fault": None,
            "position": lambda: {"step": 2, "training_seen": 2},
            "attempted_step": 3,
            "checkpoint_positions": {"last": {"step": 1}},
            "_finalize_training": train._finalize_training,
            "_attempt_finalization": train._attempt_finalization,
            "append_record": append_record,
            "batch_log": root / "batch.jsonl.gz",
        }
        node = ast.FunctionDef(
            name="actual_production_handlers",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=initialization
            + [
                ast.Try(
                    body=[ast.Raise(exc=ast.Name(id="primary", ctx=ast.Load()))],
                    handlers=terminal.handlers,
                    orelse=[],
                    finalbody=terminal.finalbody,
                )
            ],
            decorator_list=[],
        )
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                train.__file__,
                "exec",
            ),
            env,
        )
        caught = None
        try:
            env["actual_production_handlers"]()
        except BaseException as error:
            caught = error
        receipt = (
            json.loads((root / "finalization-errors.json").read_text())
            if (root / "finalization-errors.json").exists()
            else None
        )
        return observed, caught, receipt, previous.read_bytes()

    def test_actual_handlers_capture_cancel_before_failed_stop_IO_and_all_final_errors(self):
        with tempfile.TemporaryDirectory() as d:
            primary = KeyboardInterrupt("owner cancel")
            io = OSError("primary-stop log write refusal")
            cleanup = ValueError("cleanup failure")
            checkpoint = OSError("checkpoint failed")
            persist = OSError("persist failed")
            observed, caught, receipt, last = self.production_handlers(
                Path(d),
                primary,
                log_error=io,
                cleanup_error=cleanup,
                checkpoint_error=checkpoint,
                persist_error=persist,
            )
            leaves = exception_leaves(caught)
            self.assertIs(leaves[0], primary)
            self.assertEqual(
                {id(x) for x in leaves},
                {id(x) for x in (primary, io, cleanup, checkpoint, persist)},
            )
            self.assertEqual(receipt["primary_exception"]["type"], "KeyboardInterrupt")
            self.assertEqual(receipt["primary_exception"]["message"], "owner cancel")
            self.assertEqual(
                receipt["original_stop_and_position"]["fault"]["type"], "KeyboardInterrupt"
            )
            self.assertEqual(
                receipt["stages"][0], {"stage": "primary_stop_record", "status": "FAILED"}
            )
            self.assertEqual(observed, ["stop-record", "close", "checkpoint:last", "persist"])
            self.assertEqual(last, b"previous exact LAST")
            self.assertTrue((Path(d) / "visits.json").exists())

    def test_actual_handlers_log_failure_alone_retains_primary_as_group_leaf(self):
        with tempfile.TemporaryDirectory() as d:
            primary = KeyboardInterrupt("owner cancel")
            io = OSError("stop log refused")
            observed, caught, receipt, last = self.production_handlers(
                Path(d), primary, log_error=io
            )
            self.assertEqual(exception_leaves(caught), [primary, io])
            self.assertEqual(receipt["primary_exception"]["type"], "KeyboardInterrupt")
            self.assertEqual(last, b"completed update LAST")
            self.assertEqual(observed, ["stop-record", "close", "checkpoint:last", "persist"])

    def test_actual_budget_handler_keeps_controlled_stop_and_failed_IO(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as d:
                primary = RuntimeError("training budget exhausted")
                io = OSError("stop log refused") if failed else None
                observed, caught, receipt, last = self.production_handlers(
                    Path(d), primary, log_error=io
                )
                if failed:
                    self.assertEqual(exception_leaves(caught), [primary, io])
                    self.assertEqual(
                        receipt["original_stop_and_position"]["status"], "BUDGET_STOPPED"
                    )
                    self.assertEqual(receipt["primary_exception"]["type"], "RuntimeError")
                else:
                    self.assertIsNone(caught)
                    self.assertIsNone(receipt)
                self.assertEqual(last, b"completed update LAST")
                self.assertEqual(observed, ["stop-record", "close", "checkpoint:last", "persist"])

    def test_actual_handlers_UNKNOWN_update_stop_IO_cleanup_no_LAST_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            primary = KeyboardInterrupt("owner cancel")
            io = OSError("stop log refused")
            observed, caught, receipt, last = self.production_handlers(
                Path(d),
                primary,
                log_error=io,
                cleanup_error=ValueError("cleanup failed"),
                state="UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN",
            )
            self.assertIs(exception_leaves(caught)[0], primary)
            self.assertEqual(
                receipt["original_stop_and_position"]["model_state_status"],
                "UPDATE_IN_PROGRESS_OR_FAILED_UNKNOWN",
            )
            self.assertEqual(last, b"previous exact LAST")
            self.assertEqual(observed, ["stop-record", "close", "persist"])

    def test_model_free_CUDA_event_failures_still_wait_all_join_drain_and_stream(self):
        seen = []

        class Event:
            def __init__(self, name, failed=False):
                self.name, self.failed = name, failed

            def synchronize(self):
                seen.append(self.name)
                if self.failed:
                    raise RuntimeError(self.name)

        pipe = self.failed_pipe()
        pipe.slots = [
            {"ready": Event("DMA failed", True), "consumer": Event("consumer failed", True)},
            {"ready": Event("next DMA"), "consumer": Event("next consumer")},
        ]
        pipe.evaluation_slot = {"ready": Event("eval DMA"), "consumer": Event("eval consumer")}
        pipe.transfer_stream = Event("transfer stream")
        with self.assertRaises(BaseExceptionGroup) as caught:
            pipe.close()
        self.assertEqual(
            seen,
            [
                "DMA failed",
                "consumer failed",
                "next DMA",
                "next consumer",
                "eval DMA",
                "eval consumer",
                "transfer stream",
            ],
        )
        self.assertEqual(
            {str(e) for e in exception_leaves(caught.exception)},
            {"pending lookahead expansion failure", "DMA failed", "consumer failed"},
        )
        self.assertTrue(pipe.queue.closed)
        self.assertFalse(any(t.name.startswith("qf1-supply") for t in threading.enumerate()))


if __name__ == "__main__":
    unittest.main()
