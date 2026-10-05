"""QF1 + fixed distance logit + a trainable linear residual head.

Four reserved slots stay zero; QF1 sparse inputs remain active.
This module is imported only in an admitted CPU model job.
"""

import torch
from .scaled_model import validate_statistics
from .model import FEATURE_COUNT

FEATURE_VERSION = "QF1-route4-f32-STM-scaled-residual-v3"
ROUTE_VERSION = "shortest-dag4-f32-STM-v1"


class DistanceResidualModel(torch.nn.Module):
    def __init__(self, config, statistics, *, a=0.0, b=8.0):
        super().__init__()
        statistics = validate_statistics(statistics)
        ft = config["transformer_width"]
        hidden = config["hidden_width"]
        self.ft = torch.nn.Linear(FEATURE_COUNT, ft, dtype=torch.float32)
        self.h = torch.nn.Linear(2 * ft + 6, hidden, dtype=torch.float32)
        self.dropout = torch.nn.Dropout(config["dropout"])
        self.out = torch.nn.Linear(hidden, 1, dtype=torch.float32)
        self.register_buffer(
            "mu", torch.tensor(statistics["mu_f32"], dtype=torch.float32), persistent=False
        )
        self.register_buffer(
            "sigma", torch.tensor(statistics["sigma_f32"], dtype=torch.float32), persistent=False
        )
        self.register_buffer(
            "coefficient", torch.tensor([a, b], dtype=torch.float32), persistent=False
        )
        if not torch.isfinite(self.coefficient).all():
            raise ValueError("fixed distance coefficients must be finite float32")
        with torch.no_grad():
            dw = self.h.weight[:, 2 * ft : 2 * ft + 2].clone()
            self.h.bias.add_(dw @ self.mu)
            self.h.weight[:, 2 * ft : 2 * ft + 2].mul_(self.sigma)
            self.out.weight.zero_()
            self.out.bias.zero_()

    def forward(self, x, d, side):
        if d.ndim != 2 or d.shape[1] != 2:
            raise ValueError("STM/opponent distance2 input shape")
        raw_distance = d[:, :2]
        route = torch.zeros((len(d), 4), dtype=d.dtype, device=d.device)
        a = torch.relu(self.ft(x))
        p = side.long() - 1
        i = torch.arange(len(x), device=x.device)
        h = torch.cat([a[i, p], a[i, 1 - p], (raw_distance - self.mu) / self.sigma, route], dim=1)
        residual = self.out(self.dropout(torch.relu(self.h(h))))[:, 0]
        logit = self.coefficient[0] + self.coefficient[1] * (
            raw_distance[:, 1] - raw_distance[:, 0]
        )
        return torch.tanh(logit + residual)
