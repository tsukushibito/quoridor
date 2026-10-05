"""Check CUDA forward/backward and a small ONNX export; this does not train a model."""
import argparse
import datetime
import importlib.metadata
import json
import platform
import tempfile
from pathlib import Path

import os
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

import numpy as np
import onnx
import onnxruntime as ort
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is required for this training environment; no CPU fallback.')
    torch.manual_seed(0)
    model = torch.nn.Sequential(torch.nn.Linear(8, 16), torch.nn.ReLU(), torch.nn.Linear(16, 2)).cuda()
    sample = torch.randn(4, 8, device='cuda')
    loss = model(sample).square().mean()
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all().item() for p in model.parameters())
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    before = model[0].weight.detach().clone()
    optimizer.step()
    assert not torch.equal(before, model[0].weight)
    torch.cuda.synchronize()
    model = model.cpu().eval()
    sample = sample.cpu()
    with tempfile.TemporaryDirectory(prefix='quoridor-onnx-') as directory:
        path = Path(directory) / 'smoke.onnx'
        torch.onnx.export(model, (sample,), str(path), input_names=['features'], output_names=['values'], dynamo=True)
        onnx.checker.check_model(str(path))
        session = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
        actual = session.run(None, {'features': sample.numpy()})[0]
        with torch.no_grad():
            expected = model(sample).numpy()
        np.testing.assert_allclose(actual, expected, rtol=1e-4, atol=1e-5)
    report = {
        'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python': platform.python_version(),
        'packages': {name: importlib.metadata.version(name) for name in ['torch', 'numpy', 'onnx', 'onnxruntime', 'onnxscript']},
        'cuda_runtime': torch.version.cuda,
        'gpu': torch.cuda.get_device_name(0),
        'cuda_forward_backward_optimizer': 'passed',
        'onnx_export_cpu_parity': 'passed',
        'browser_wasm_model_inference': 'not tested',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
