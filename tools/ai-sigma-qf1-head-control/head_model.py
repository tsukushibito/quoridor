"""204 changes only trainable parameter subset; 200 forward is reused unchanged."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path('tools/ai-sigma-qf1-distance-residual').resolve()))
from residual_model import ResidualModel
import torch

D = Path('research-data/ai-sigma/frame14-head-control')


class HeadModel(ResidualModel):
    instances = []

    def __init__(self, config):
        super().__init__(config)
        reg = json.loads((D / 'preregister.json').read_text())
        cp = torch.load(reg['initial']['path'], map_location='cpu', weights_only=True)
        assert cp['model_config'] == config and cp['step'] == 0
        h = hashlib.sha256(b''.join(v.numpy().tobytes() for v in cp['model'].values())).hexdigest()
        assert h == reg['initial']['weight_SHA']
        assert torch.count_nonzero(cp['model']['out.weight']) == 0
        assert torch.count_nonzero(cp['model']['out.bias']) == 0
        self.load_state_dict(cp['model'], strict=True)
        for layer in [self.ft, self.h]:
            layer.requires_grad_(False)
        self.out.requires_grad_(True)
        assert {n for n, p in self.named_parameters() if p.requires_grad} == {'out.weight', 'out.bias'}
        assert sum(p.numel() for p in self.parameters()) == 33

    def parameters(self, recurse=True):
        # The immutable trainer uses this iterator for both optimizer and grad checks.
        # Named parameters/state_dict retain all frozen tensors for checkpoint evidence.
        return self.out.parameters(recurse=recurse)
