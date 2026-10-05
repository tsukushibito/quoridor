"""Fixed d790 inference graph, folded weights retained; no upstream module import."""
from pathlib import Path
import hashlib

MODEL_SHA = 'd790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'

def load(path):
    import onnx
    import numpy as np
    import torch
    import torch.nn.functional as F
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == MODEL_SHA
    graph = onnx.load(str(path), load_external_data=False).graph
    convs = {n.name: n for n in graph.node if n.op_type == 'Conv'}
    bns = {n.name: n for n in graph.node if n.op_type == 'BatchNormalization'}
    assert len(convs) == 24 and len(bns) == 6 and len(graph.initializer) == 83
    assert len(graph.node) == 179
    for n in convs.values():
        a = {x.name: onnx.helper.get_attribute_value(x) for x in n.attribute}
        assert a['group'] == 1 and list(a['strides']) == [1, 1]
        assert list(a['dilations']) == [1, 1]
        assert list(a['pads']) in ([0, 0, 0, 0], [1, 1, 1, 1])
    class Folded(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.names = {}
            self.raw_hashes = {}
            for i, x in enumerate(graph.initializer):
                assert x.data_type == onnx.TensorProto.FLOAT and not x.data_location
                a = onnx.numpy_helper.to_array(x).copy()
                assert a.dtype == np.float32 and np.isfinite(a).all()
                self.raw_hashes[x.name] = hashlib.sha256(x.raw_data).hexdigest()
                assert hashlib.sha256(a.tobytes()).hexdigest() == self.raw_hashes[x.name]
                name = 'weight_' + str(i)
                self.register_buffer(name, torch.from_numpy(a))
                self.names[x.name] = name
            self.eval()
        def w(self, name):
            return getattr(self, self.names[name])
        def conv(self, name, x):
            n = convs[name]
            pads = next(a for a in n.attribute if a.name == 'pads').ints
            return F.conv2d(x, self.w(n.input[1]), self.w(n.input[2]) if len(n.input) == 3 else None, padding=pads[0])
        def bn(self, name, x):
            n = bns[name]
            eps = next(a for a in n.attribute if a.name == 'epsilon').f
            assert next(a for a in n.attribute if a.name == 'training_mode').i == 0
            return F.batch_norm(x, self.w(n.input[3]), self.w(n.input[4]), self.w(n.input[1]), self.w(n.input[2]), training=False, eps=eps)
        def linear(self, name, x):
            return F.linear(x, self.w(name + '.weight'), self.w(name + '.bias'))
        def forward(self, raw):
            assert raw.ndim == 4 and tuple(raw.shape[1:]) == (8, 9, 9) and 1 <= raw.shape[0] <= 8 and raw.dtype == torch.float32
            x = F.relu(self.conv('/conv/Conv', raw))
            for i in range(10):
                prefix = f'/residuals/residuals.{i}'
                y = self.conv(prefix + '/conv1/Conv', x)
                if i in (2, 5, 8):
                    r = self.bn(prefix + '/bn1_reg/BatchNormalization', y[:, :96])
                    p = F.relu(self.bn(prefix + '/bn1_pool/BatchNormalization', y[:, 96:]))
                    pool = torch.cat([p.mean(dim=(2, 3)), p.amax(dim=(2, 3))], dim=1)
                    bias = self.linear(f'residuals.{i}.gpool_fc', pool)
                    y = F.relu(r + bias[:, :, None, None])
                else:
                    y = F.relu(y)
                x = F.relu(x + self.conv(prefix + '/conv2/Conv', y))
            feat = torch.cat([(x * raw[:, 0:1]).sum(dim=(2, 3)), (x * raw[:, 1:2]).sum(dim=(2, 3)), x.mean(dim=(2, 3))], dim=1)
            pawn = self.linear('policy_pawn_fc2', F.relu(self.linear('policy_pawn_fc1', feat)))
            h = F.relu(self.conv('/policy_h_conv/Conv', x))[:, 0, :8, :8].contiguous().view(raw.shape[0], -1)
            v = F.relu(self.conv('/policy_v_conv/Conv', x))[:, 0, :8, :8].contiguous().view(raw.shape[0], -1)
            policy = torch.cat([pawn, h, v], dim=1)
            val = F.relu(self.conv('/value_conv/Conv', x))
            val = torch.cat([val.mean(dim=(2, 3)), val.amax(dim=(2, 3))], dim=1)
            value = torch.tanh(self.linear('value_fc2', F.relu(self.linear('value_pool_fc', val))))
            return policy, value
    return Folded()
