"""Explicit QF1 distance-scaling factory; importing this module is NN0.

Statistics are supplied by a caller or an explicit path, never an implicit
frame-specific artifact. This module does not estimate statistics, select
data, run parity inference, or change a frozen recipe's normalization rule.
"""

import math
import struct


def validate_statistics(statistics):
    """Return the supplied moments rounded exactly as Torch float32 tensors."""
    result = {}
    for key in ("mu_f32", "sigma_f32"):
        values = statistics.get(key)
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("scaling statistics need two STM/opponent values: " + key)
        rounded = []
        for value in values:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("scaling statistics must be finite: " + key)
            try:
                f32 = struct.unpack("<f", struct.pack("<f", value))[0]
            except OverflowError as error:
                raise ValueError("scaling statistics overflow float32: " + key) from error
            if not math.isfinite(f32) or (key == "sigma_f32" and f32 <= 0):
                raise ValueError("scaling sigma must stay positive in float32")
            rounded.append(f32)
        result[key] = rounded
    return result


def build_model(config, statistics):
    """Construct a scaled model only inside a separately authorized Torch job.

    The initial hidden weights/bias are reparameterized to preserve the raw
    model's function. Statistics are nonpersistent buffers: checkpoints retain
    the established six parameter names and need the separately bound scale.
    This construction does not execute a model forward or a parity pass.
    """
    statistics = validate_statistics(statistics)
    import torch
    from .model import Model

    class ScaledModel(Model):
        def __init__(self, model_config):
            super().__init__(model_config)
            self.register_buffer(
                "mu", torch.tensor(statistics["mu_f32"], dtype=torch.float32), persistent=False
            )
            self.register_buffer(
                "sigma",
                torch.tensor(statistics["sigma_f32"], dtype=torch.float32),
                persistent=False,
            )
            with torch.no_grad():
                distance_weights = self.h.weight[:, -2:].clone()
                self.h.bias.copy_(self.h.bias + distance_weights @ self.mu)
                self.h.weight[:, -2:].copy_(distance_weights * self.sigma)

        def forward(self, x, distance, side):
            return super().forward(x, (distance - self.mu) / self.sigma, side)

    return ScaledModel(config)
