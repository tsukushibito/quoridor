"""Fixed-row epochs and explicit row/group loss objectives."""

from collections import Counter
import hashlib
import heapq
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


class EarlyStopping:
    """Patience counts completed full-selector measurements; zero disables it."""

    def __init__(self, patience, min_delta):
        self.patience, self.min_delta = patience, min_delta
        self.best, self.stale = math.inf, 0

    def observe(self, value):
        if not math.isfinite(value):
            raise ValueError("nonfinite selector metric")
        improved = value < self.best - self.min_delta
        if improved:
            self.best, self.stale = value, 0
        else:
            self.stale += 1
        return improved, bool(self.patience and self.stale >= self.patience)
