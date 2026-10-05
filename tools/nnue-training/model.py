"""QF1 float32 model, imported only inside an authorized Torch job."""
import torch
import struct
from frame14_data import canonical_model_input


class Model(torch.nn.Module):
    def __init__(self, config):
        super().__init__()
        h = config['transformer_width']
        self.ft = torch.nn.Linear(312, h)
        self.h = torch.nn.Linear(2 * h + 2, config['hidden_width'])
        self.dropout = torch.nn.Dropout(config['dropout'])
        self.out = torch.nn.Linear(config['hidden_width'], 1)

    def forward(self, x, d, side):
        a = torch.relu(self.ft(x))
        p = side.long() - 1
        i = torch.arange(len(x), device=x.device)
        q = torch.cat([a[i, p], a[i, 1-p], d], dim=1)
        return torch.tanh(self.out(self.dropout(torch.relu(self.h(q)))))[:, 0]


def inputs(rows, device='cpu'):
    x = torch.zeros(len(rows), 2, 312)
    distances = []
    for i, row in enumerate(rows):
        canonical = canonical_model_input(row)
        for p in (0, 1):
            x[i, p, canonical[1+p]] = 1
        distances.append([struct.unpack('<f', struct.pack('<I', b))[0] for b in canonical[3]])
    # Inputs have already been ordered STM/opponent. Model's p=0 selects this order.
    return (x.to(device), torch.tensor(distances, device=device),
            torch.ones(len(rows), device=device, dtype=torch.long))
