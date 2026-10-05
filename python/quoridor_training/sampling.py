"""Fixed-row epochs and explicit row/group loss objectives."""

from collections import Counter

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
    if mode not in ("row", "group") or not groups:
        raise ValueError("nonempty training groups and explicit row/group objective required")
    if mode == "row":
        return np.ones(len(groups), dtype=np.float32)
    counts = Counter(groups)
    return np.asarray(
        [len(groups) / (len(counts) * counts[group]) for group in groups], dtype=np.float32
    )
