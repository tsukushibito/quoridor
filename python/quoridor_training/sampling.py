"""Fixed-row epochs and explicit row/group loss objectives."""

from collections import Counter
import hashlib
import heapq
import itertools
import math

import numpy as np


class EpochSampler:
    def __init__(self, indices, batch_size, seed):
        self.indices = np.asarray(indices, dtype=np.int64)
        if (
            self.indices.ndim != 1
            or not len(self.indices)
            or len(np.unique(self.indices)) != len(self.indices)
            or type(batch_size) is not int
            or batch_size <= 0
        ):
            raise ValueError("nonempty unique training rows and positive batch size required")
        self.batch_size = batch_size
        self.generator = np.random.default_rng(seed)
        self.order = None
        self.cursor = 0
        self.completed_epochs = 0
        self.seen = 0

    def next_batch(self):
        if self.order is None or self.cursor == len(self.indices):
            self.order = self.generator.permutation(self.indices)
            self.cursor = 0
        end = min(self.cursor + self.batch_size, len(self.indices))
        batch = self.order[self.cursor : end]
        self.cursor = end
        self.seen += len(batch)
        if end == len(self.indices):
            self.completed_epochs += 1
        return batch

    @property
    def next_batch_size(self):
        remaining = len(self.indices) - self.cursor
        return min(self.batch_size, remaining or len(self.indices))

    @property
    def partial_epoch_fraction(self):
        return 0.0 if self.cursor == len(self.indices) else self.cursor / len(self.indices)


class FullBatchSampler(EpochSampler):
    """Continue the same shuffled row stream through epoch tails, without refill."""

    def take(self, count):
        if type(count) is not int or count <= 0:
            raise ValueError("positive full-batch row count required")
        blocks = []
        remaining = count
        while remaining:
            self.batch_size = remaining
            part = self.next_batch()
            blocks.append(part)
            remaining -= len(part)
        return np.concatenate(blocks)


def update_steps(limit):
    """A true unbounded update iterator when no scientific horizon is specified."""
    return itertools.count(1) if limit is None else iter(range(1, limit + 1))


class ReflectionBatches:
    """Train-only online reflection, with a generator separate from epoch shuffle."""

    def __init__(self, corpus, probability, seed):
        if not 0 <= probability <= 1 or (probability and not getattr(corpus, "compact", False)):
            raise ValueError("online reflection requires a qualified geometry corpus")
        self.corpus, self.probability = corpus, probability
        self.generator = np.random.default_rng(seed)
        self.training_seen, self.reflected_seen = 0, 0

    def batch(self, indices, *, training=False):
        if not training:
            return self.corpus.batch(indices)
        indices = np.asarray(indices, dtype=np.int64)
        if np.any(self.corpus.splits[indices] != 0):
            raise ValueError("online training reflection must exclude validation/test")
        self.training_seen += len(indices)
        if not self.probability:
            return self.corpus.batch(indices)
        mask = self.generator.random(len(indices)) < self.probability
        self.reflected_seen += int(mask.sum())
        return self.corpus.batch(indices, mask)


def loss_weights(groups, mode):
    if mode not in ("row", "group") or not len(groups):
        raise ValueError("nonempty training groups and explicit row/group objective required")
    if mode == "row":
        return np.ones(len(groups), dtype=np.float32)
    counts = Counter(groups)
    return np.fromiter(
        (len(groups) / (len(counts) * counts[group]) for group in groups),
        dtype=np.float32,
        count=len(groups),
    )


def diagnostic_indices(rows, indices, count, seed):
    """Stable input-ID-only subset; never consumes the optimizer sampler RNG."""
    if count == 0:
        return np.asarray([], dtype=np.int64)
    candidates = (
        zip(indices, rows.iter_indices(indices))
        if hasattr(rows, "iter_indices")
        else ((i, rows[i]) for i in indices)
    )
    ranked = heapq.nsmallest(
        count,
        candidates,
        key=lambda pair: (
            hashlib.sha256(f"{seed}:{pair[1]['id']}".encode()).digest(),
            int(pair[0]),
        ),
    )
    return np.asarray(sorted(int(i) for i, _ in ranked), dtype=np.int64)


def observation_steps(steps, interval, rows, batch, mode, explicit=None):
    if explicit is not None:
        return set(explicit)
    stride = min(interval, max(1, math.ceil(rows / batch / 4)))
    points = {0, 1, 2, 5, 10, 20, steps}
    points.update(range(stride, steps + 1, stride))
    if mode == "epoch":
        points.update(range(math.ceil(rows / batch), steps + 1, math.ceil(rows / batch)))
    return {point for point in points if point <= steps}


def exposure(seen, rows, mode):
    """Exposure of successfully completed updates, not advanced sampler state."""
    return {
        "training_seen": seen,
        "row_epoch": seen / rows,
        "completed_epochs": seen // rows if mode == "epoch" else None,
        "partial_epoch_fraction": (seen % rows) / rows if mode == "epoch" else None,
    }


class ConvergenceObservations:
    """Result-blind, no horizon: full validation per epoch, dense early diagnostics.

    Diagnostics never select or consume patience. Full train is measured on the
    first completed epoch and then at the fixed configured epoch interval.
    """

    def __init__(self, rows, diagnostic_interval=1250, full_train_every_epochs=5):
        if rows <= 0 or diagnostic_interval <= 0 or full_train_every_epochs < 0:
            raise ValueError("positive rows/diagnostic interval and nonnegative train interval")
        self.rows = rows
        self.diagnostic_interval = diagnostic_interval
        self.full_train_every_epochs = full_train_every_epochs

    def at(self, step, seen):
        boundary = seen > 0 and seen % self.rows == 0
        selector = step == 0 or boundary
        dense = step in {0, 1, 2, 5, 10, 20} or (0 < step <= 2000 and step % 25 == 0)
        diagnostic = selector or dense or (step > 2000 and step % self.diagnostic_interval == 0)
        epoch = seen // self.rows
        full_train = boundary and (
            epoch == 1
            or bool(self.full_train_every_epochs and epoch % self.full_train_every_epochs == 0)
        )
        return selector, diagnostic, full_train


class EarlyStopping:
    """Patience counts completed full-selector measurements; zero disables it."""

    def __init__(self, patience, min_delta, relative_delta=0.0):
        self.patience, self.min_delta = patience, min_delta
        self.relative_delta = relative_delta
        self.best, self.stale = math.inf, 0

    def observe(self, value):
        if not math.isfinite(value):
            raise ValueError("nonfinite selector metric")
        threshold = (
            max(self.min_delta, self.relative_delta * abs(self.best))
            if math.isfinite(self.best)
            else self.min_delta
        )
        improved = value < self.best - threshold
        if improved:
            self.best, self.stale = value, 0
        else:
            self.stale += 1
        return improved, bool(self.patience and self.stale >= self.patience)
