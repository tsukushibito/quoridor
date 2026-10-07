"""Bounded QF1 expansion and contiguous reusable FP32 batch transfer.

Workers are threads over immutable corpus maps, never model/CUDA processes.
Only the caller owns sampler/reflection RNG, CUDA streams and buffer leases.
"""

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import time

import numpy as np

from .public_features import RECORD, FeatureWorkspace


FLOATS_PER_ROW = 624 + 2 + 1 + 1


def payload_views(storage, rows):
    if rows < 0 or rows * FLOATS_PER_ROW > len(storage):
        raise ValueError("payload capacity")
    first = rows * 624
    return (
        storage[:first].reshape(rows, 2, 312),
        storage[first : first + rows * 2].reshape(rows, 2),
        storage[first + rows * 2 : first + rows * 3],
        storage[first + rows * 3 : first + rows * 4],
    )


class OrderedPrefetch:
    """Bounded whole-batch futures, with exact owner-thread shutdown on all exits."""

    def __init__(self, workers):
        if workers not in (0, 1, 2, 4):
            raise ValueError("supply workers must be 0/1/2/4")
        self.workers = workers
        self.executor = (
            ThreadPoolExecutor(workers, thread_name_prefix="qf1-supply") if workers else None
        )
        self.pending = deque()
        self.closed = False
        self.dispatched_rows = self.expanded_rows = self.consumed_rows = 0

    def submit(self, token, rows, function, *args):
        if self.closed or len(self.pending) >= self.workers + 1:
            raise ValueError("prefetch closed or queue capacity")
        self.dispatched_rows += rows
        if self.executor:
            future = self.executor.submit(function, *args)
        else:
            from concurrent.futures import Future

            future = Future()
            try:
                future.set_result(function(*args))
            except BaseException as error:
                future.set_exception(error)
        self.pending.append((token, rows, future))

    def take(self, token):
        if self.closed or not self.pending or self.pending[0][0] != token:
            raise ValueError("ordered prefetch token mismatch")
        _, rows, future = self.pending.popleft()
        result = future.result()
        self.expanded_rows += rows
        self.consumed_rows += rows
        return result

    def drain(self):
        errors = []
        while self.pending:
            _, rows, future = self.pending.popleft()
            try:
                future.result()
                self.expanded_rows += rows
            except BaseException as caught:
                errors.append(caught)
        if errors:
            raise BaseExceptionGroup("prefetch expansion failures during drain", errors)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.drain()
        finally:
            if self.executor:
                self.executor.shutdown(wait=True, cancel_futures=True)


class PackedSupply:
    """A batch lease survives through its last consumer and every DMA completion.

    Metadata slices are separate contiguous blocks (no interleaved strided rows).
    Lookahead uses cloned RNG state and the current epoch's existing row order;
    neither advances the real sampler/RNG nor crosses the epoch boundary.
    """

    def __init__(self, reflection, capacity, device, weights, column, *, workers=0):
        import torch

        if not getattr(reflection.corpus, "compact", False):
            raise ValueError("packed supply requires qualified compact corpus")
        self.reflection, self.corpus = reflection, reflection.corpus
        self.capacity, self.device, self.weights, self.column = capacity, device, weights, column
        self.torch = torch
        self.queue = OrderedPrefetch(workers)
        self.workers = workers
        self.slots = [self._slot() for _ in range(workers + 1)]
        self.evaluation_slot = self._slot()
        self.free = deque(self.slots)
        self.descriptors = deque()
        self.active = None
        self.transfer_stream = torch.cuda.Stream() if device == "cuda" else None
        self.timing = {
            k: 0.0
            for k in (
                "expansion_worker_seconds",
                "queue_wait_seconds",
                "transfer_enqueue_seconds",
                "lease_wait_seconds",
            )
        }
        self.training_attempted_rows = self.reflected_drawn_rows = 0
        self.closed = False

    def _slot(self):
        torch = self.torch
        host = torch.empty(
            self.capacity * FLOATS_PER_ROW, dtype=torch.float32, pin_memory=self.device == "cuda"
        )
        return {
            "host": host,
            "numpy": host.numpy(),
            "device": torch.empty_like(host, device=self.device) if self.device == "cuda" else host,
            "side": torch.ones(self.capacity, dtype=torch.long, device=self.device),
            "records": np.empty(self.capacity, dtype=RECORD),
            "workspace": FeatureWorkspace(self.capacity),
            "ready": None,
            "consumer": None,
            "rows": 0,
        }

    def _fill(self, slot, index, mask):
        tick = time.perf_counter()
        n = len(index)
        features, distances, target, weights = payload_views(slot["numpy"], n)
        self.corpus.batch_into(
            index,
            mask,
            features,
            distances,
            records_out=slot["records"][:n],
            workspace=slot["workspace"],
        )
        target[:] = self.corpus.labels[index, self.column]
        weights[:] = self.weights[index]
        slot["rows"] = n
        # Each slot belongs to only one future; the owner aggregates its wall later.
        slot["expansion_seconds"] = time.perf_counter() - tick
        return slot

    def _wait(self, slot):
        tick = time.perf_counter()
        failures = []
        for key in ("ready", "consumer"):
            if slot[key] is not None:
                try:
                    slot[key].synchronize()
                    slot[key] = None
                except BaseException as error:
                    failures.append(error)
        self.timing["lease_wait_seconds"] += time.perf_counter() - tick
        if failures:
            raise BaseExceptionGroup("packed supply event waits failed", failures)

    def _upload(self, slot):
        if self.device != "cuda" or slot["ready"] is not None:
            return
        tick = time.perf_counter()
        n = slot["rows"] * FLOATS_PER_ROW
        with self.torch.cuda.stream(self.transfer_stream):
            slot["device"][:n].copy_(slot["host"][:n], non_blocking=True)
            slot["ready"] = self.torch.cuda.Event()
            slot["ready"].record(self.transfer_stream)
        self.timing["transfer_enqueue_seconds"] += time.perf_counter() - tick

    def release(self):
        if self.active is None:
            return
        slot = self.active
        if self.device == "cuda":
            slot["consumer"] = self.torch.cuda.Event()
            slot["consumer"].record(self.torch.cuda.current_stream())
        self.active = None
        if slot is not self.evaluation_slot:
            self.free.append(slot)

    def _draw(self, index):
        reflection = self.reflection
        if np.any(self.corpus.splits[index] != 0):
            raise ValueError("online training reflection must exclude validation/test")
        reflection.training_seen += len(index)
        mask = (
            reflection.generator.random(len(index)) < reflection.probability
            if reflection.probability
            else np.zeros(len(index), dtype=bool)
        )
        reflection.reflected_seen += int(mask.sum())
        self.training_attempted_rows += len(index)
        self.reflected_drawn_rows += int(mask.sum())
        return mask

    def _submit(self, index, mask):
        slot = self.free.popleft()
        self._wait(slot)
        token = (int(index[0]), len(index))
        self.descriptors.append((index.copy(), mask.copy(), slot))
        self.queue.submit(token, len(index), self._fill, slot, index.copy(), mask.copy())

    def batch(self, index, *, training=False, sampler=None):
        if self.closed:
            raise ValueError("packed supply closed")
        index = np.asarray(index, dtype=np.int64)
        if index.ndim != 1 or not 0 < len(index) <= self.capacity:
            raise ValueError("packed batch indices/capacity")
        self.release()
        if not training:
            slot = self.evaluation_slot
            self._wait(slot)
            self._fill(slot, index, None)
        else:
            mask = self._draw(index)
            if not self.descriptors:
                self._submit(index, mask)
            planned_index, planned_mask, _ = self.descriptors[0]
            if not np.array_equal(index, planned_index) or not np.array_equal(mask, planned_mask):
                raise ValueError("prefetch original order/reflection mismatch")
            tick = time.perf_counter()
            slot = self.queue.take((int(index[0]), len(index)))
            self.timing["queue_wait_seconds"] += time.perf_counter() - tick
            self.descriptors.popleft()
            self.timing["expansion_worker_seconds"] += slot["expansion_seconds"]
            # Existing current epoch order only; no next permutation or actual RNG advance.
            if self.workers and sampler is not None:
                cursor = sampler.cursor + sum(len(x[0]) for x in self.descriptors)
                planner = np.random.default_rng()
                planner.bit_generator.state = deepcopy(
                    self.reflection.generator.bit_generator.state
                )
                for _, pending_mask, _ in self.descriptors:
                    drawn = (
                        planner.random(len(pending_mask)) < self.reflection.probability
                        if self.reflection.probability
                        else np.zeros(len(pending_mask), dtype=bool)
                    )
                    if not np.array_equal(drawn, pending_mask):
                        raise ValueError("prefetch planned RNG state mismatch")
                while self.free and cursor < len(sampler.order):
                    sub = sampler.order[cursor : cursor + sampler.batch_size]
                    drawn = (
                        planner.random(len(sub)) < self.reflection.probability
                        if self.reflection.probability
                        else np.zeros(len(sub), dtype=bool)
                    )
                    self._submit(sub, drawn)
                    cursor += len(sub)
        self._upload(slot)
        # Enqueue ready next batches on the same transfer stream; it remains separate
        # from ordered model/finite checks. Every slot has its own device storage.
        for _, _, future in self.queue.pending:
            if future.done() and not future.cancelled() and future.exception() is None:
                self._upload(future.result())
        if self.device == "cuda":
            self.torch.cuda.current_stream().wait_event(slot["ready"])
        self.active = slot
        features, distances, target, weights = payload_views(slot["device"], len(index))
        return (features, distances, slot["side"][: len(index)]), target, weights

    def close(self):
        if self.closed:
            return
        self.closed = True
        failures = []
        actions = [self.release, self.queue.close]
        actions.extend(
            lambda slot=slot: self._wait(slot) for slot in self.slots + [self.evaluation_slot]
        )
        if self.transfer_stream is not None:
            actions.append(self.transfer_stream.synchronize)
        for action in actions:
            try:
                action()
            except BaseException as error:
                failures.append(error)
        if failures:
            raise BaseExceptionGroup("packed supply cleanup failures", failures)
