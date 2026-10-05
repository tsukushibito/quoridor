"""Private fixed-distance plus QF1 tanh residual; shared trainer stays read-only."""
import torch
from model import Model as QF1Model

A = 0.06294242415104226
B = 8.276425107422213
CONDITION = 'QF1-distance-residual-f32-v1'


class ResidualModel(QF1Model):
    instances = []

    def __init__(self, config):
        super().__init__(config)
        with torch.no_grad():
            self.out.weight.zero_()
            self.out.bias.zero_()
        self.register_buffer('distance_a', torch.tensor(A, dtype=torch.float32))
        self.register_buffer('distance_b', torch.tensor(B, dtype=torch.float32))
        self.initial_check = {'rows': 0, 'max_abs': 0., 'max_residual_abs': 0., 'pass': True}
        self._initial = True
        self.instances.append(self)

    def forward(self, x, d, side):
        if self.training:
            self._initial = False
        residual = super().forward(x, d, side)
        distance = (self.distance_a + self.distance_b * (d[:, 1] - d[:, 0])).clamp(-1, 1)
        prediction = (distance + residual).clamp(-1, 1)
        if self._initial:
            # Reuse the already charged step-0 evaluation; no extra model forward.
            with torch.no_grad():
                reference = (A + B * (d[:, 1].double() - d[:, 0].double())).clamp(-1, 1)
                difference = (prediction.double() - reference).abs()
                c = self.initial_check
                c['rows'] += len(d)
                c['max_abs'] = max(c['max_abs'], difference.max().item())
                c['max_residual_abs'] = max(c['max_residual_abs'], residual.abs().max().item())
                c['pass'] &= bool(torch.isfinite(prediction).all() and
                                  (difference <= 1e-6 + 1e-6 * reference.abs()).all() and
                                  (residual == 0).all())
        return prediction
