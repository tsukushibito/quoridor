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
            "mu",
            torch.tensor(statistics["mu_f32"], dtype=torch.float32),
            persistent=False,
        )
        self.register_buffer(
            "sigma",
            torch.tensor(statistics["sigma_f32"], dtype=torch.float32),
            persistent=False,
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

    def shared_hidden(self, x, d, side):
        if d.ndim != 2 or d.shape[1] != 2:
            raise ValueError("STM/opponent distance2 input shape")
        raw_distance = d[:, :2]
        route = torch.zeros((len(d), 4), dtype=d.dtype, device=d.device)
        a = torch.relu(self.ft(x))
        p = side.long() - 1
        i = torch.arange(len(x), device=x.device)
        h = torch.cat([a[i, p], a[i, 1 - p], (raw_distance - self.mu) / self.sigma, route], dim=1)
        return raw_distance, self.dropout(torch.relu(self.h(h)))

    def residual_components(self, x, d, side):
        raw_distance, hidden = self.shared_hidden(x, d, side)
        return raw_distance, self.out(hidden)[:, 0]

    def enable_policy_head(self, *, evidence):
        # This explicit operation creates a new artifact. The ordinary constructor,
        # value-only forward and old state_dict have no policy parameters/RNG work.
        if evidence != "synthetic_untrained" or hasattr(self, "policy"):
            raise ValueError("new policy head must explicitly start synthetic_untrained")
        self.policy = torch.nn.Linear(self.h.out_features, 209, dtype=torch.float32).to(
            device=self.h.weight.device
        )
        self.policy_evidence = evidence

    def forward_policy_value(self, x, d, side):
        if not hasattr(self, "policy"):
            raise ValueError("explicit policy head required; no uniform fallback")
        if (
            x.dtype != torch.float32
            or d.dtype != torch.float32
            or side.dtype not in (torch.int32, torch.int64)
        ):
            raise ValueError("FP32 policy inputs and integer STM")
        if x.ndim != 3 or tuple(x.shape[1:]) != (2, FEATURE_COUNT) or len(x) == 0:
            raise ValueError("policy QF1 rows")
        if not torch.isfinite(x).all() or not torch.isfinite(d).all():
            raise ValueError("finite policy input")

        if side.ndim != 1 or len(side) != len(x) or not ((side == 1) | (side == 2)).all():
            raise ValueError("policy STM must be 1/2 per row")
        raw_distance, hidden = self.shared_hidden(x, d, side)
        value = self.value_from_residual(raw_distance, self.out(hidden)[:, 0])
        canonical = self.policy(hidden)
        permutation = torch.tensor(policy_permutation(2), device=canonical.device)
        absolute = torch.where((side == 2)[:, None], canonical[:, permutation], canonical)
        return value, absolute

    def forward(self, x, d, side):
        raw_distance, residual = self.residual_components(x, d, side)
        return self.value_from_residual(raw_distance, residual)

    def value_from_residual(self, raw_distance, residual):
        logit = self.coefficient[0] + self.coefficient[1] * (
            raw_distance[:, 1] - raw_distance[:, 0]
        )
        return torch.tanh(logit + residual)


def policy_permutation(side, *, reflected=False):
    """Absolute core ActionID -> head coordinate; no legal projection or sign flip."""
    if type(side) is not int or side not in (1, 2) or type(reflected) is not bool:
        raise ValueError("policy side/reflection")
    result = []
    for action in range(209):
        base, width = (0, 9) if action < 81 else ((81, 8) if action < 145 else (145, 8))
        row, col = divmod(action - base, width)
        if reflected:
            col = width - 1 - col
        if side == 2:
            row, col = width - 1 - row, width - 1 - col
        result.append(base + row * width + col)
    return tuple(result)


def policy_value_loss(value, logits, z, policy_target, legal_mask):
    """Loss boundary for the existing optimizer: outcome MSE + legal policy CE.

    Callers supply one joint forward and reflected targets/mask in absolute core
    coordinates. This is no data loader, teacher selection or new fit permission.
    """
    if logits.dtype != torch.float32 or logits.ndim != 2 or logits.shape[1] != 209:
        raise ValueError("FP32 policy209 logits")
    if legal_mask.dtype != torch.bool or legal_mask.shape != logits.shape:
        raise ValueError("policy legal mask")
    if policy_target.dtype != torch.float32 or policy_target.shape != logits.shape:
        raise ValueError("FP32 policy target209")
    if value.dtype != torch.float32 or z.dtype != torch.float32:
        raise ValueError("FP32 value/outcome")
    if value.shape != z.shape or value.shape != logits.shape[:1]:
        raise ValueError("value/outcome row shape")
    if len(value) == 0 or not legal_mask.any(dim=1).all():
        raise ValueError("empty policy row/nonterminal legal set")
    if not all(torch.isfinite(t).all() for t in (value, logits, z, policy_target)):
        raise ValueError("finite policy/value inputs")
    if not ((z >= -1) & (z <= 1)).all() or not ((value >= -1) & (value <= 1)).all():
        raise ValueError("STM outcome/value range")
    if (policy_target < 0).any() or (policy_target[~legal_mask] != 0).any():
        raise ValueError("policy target illegal mass")
    if not torch.allclose(policy_target.sum(dim=1), torch.ones_like(value), atol=1e-6, rtol=0):
        raise ValueError("policy target normalisation")
    # Select legal log probabilities first: never evaluate zero * negative infinity.
    logp = torch.log_softmax(logits.masked_fill(~legal_mask, -torch.inf), dim=1)
    policy = -(policy_target * logp.masked_fill(~legal_mask, 0)).sum(dim=1).mean()
    outcome = torch.mean((value - z) ** 2)
    return outcome + policy, {"outcome_mse": outcome, "policy_cross_entropy": policy}


def validate_policy_manifest(m, shared_fingerprint, hidden):
    required = {
        "schema",
        "action_order",
        "head_coordinates",
        "value_perspective",
        "reflection",
        "evidence",
        "shared_fingerprint",
        "hidden_width",
        "weights",
        "weights_sha256",
        "weights_bytes",
    }
    if not isinstance(m, dict) or set(m) != required:
        raise ValueError("policy manifest fields")
    if (
        m["schema"] != "quoridor-nnue-policy209-v1"
        or m["action_order"] != "absolute-core-action-id209"
        or m["head_coordinates"] != "QF1-STM-rotate180"
        or m["value_perspective"] != "side-to-move"
        or m["reflection"] != "core-action-id209-left-right-v1"
        or m["evidence"] not in ("synthetic_untrained", "learned")
        or m["shared_fingerprint"] != shared_fingerprint
        or type(m["hidden_width"]) is not int
        or m["hidden_width"] != hidden
        or type(m["weights_bytes"]) is not int
        or m["weights_bytes"] != 209 * (hidden + 1) * 4
    ):
        raise ValueError("policy contract/shared model")
    for key in ("shared_fingerprint", "weights_sha256"):
        value = m[key]
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("policy SHA/fingerprint")
    name = m["weights"]
    if (
        not isinstance(name, str)
        or not name
        or "/" in name
        or chr(92) in name
        or name in (".", "..")
    ):
        raise ValueError("policy weight basename")


def load_policy_head(model, path, *, shared_fingerprint):
    """Read optional head only; actual native shared identity must be supplied."""
    import hashlib
    import json
    from pathlib import Path
    import numpy as np

    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("policy manifest size")
    manifest = json.loads(raw)
    validate_policy_manifest(manifest, shared_fingerprint, model.h.out_features)
    with (path.parent / manifest["weights"]).open("rb") as stream:
        raw = stream.read(manifest["weights_bytes"] + 1)
    if (
        len(raw) != manifest["weights_bytes"]
        or hashlib.sha256(raw).hexdigest() != manifest["weights_sha256"]
    ):
        raise ValueError("policy weights SHA/size")
    vector = np.frombuffer(raw, dtype="<f4")
    if not np.isfinite(vector).all():
        raise ValueError("policy weights finite")
    if hasattr(model, "policy"):
        raise ValueError("policy already attached; no implicit replacement")
    model.enable_policy_head(evidence="synthetic_untrained")
    width = model.h.out_features
    with torch.no_grad():
        model.policy.weight.copy_(
            torch.from_numpy(vector[: 209 * width].copy().reshape(209, width)).to(
                model.h.weight.device
            )
        )
        model.policy.bias.copy_(
            torch.from_numpy(vector[209 * width :].copy()).to(model.h.weight.device)
        )
    model.policy_evidence = manifest["evidence"]
    return manifest
