"""One preregistered CPU toy training attempt. Existing five diagnostic roots only."""
import argparse
import hashlib
import importlib.util
import json
import os
import struct
import time
import traceback
from pathlib import Path

D = Path('research-data/ai-sigma/162-pv-cpu-smoke')
FIX = Path('research-data/ai-sigma/160-pv-pipeline-bootstrap/fixtures.jsonl')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(name, value):
    (D / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['train', 'export'])
    args = parser.parse_args()
    start = time.time()
    prereg_bytes = (D / 'preregister.json').read_bytes()
    prereg = json.loads(prereg_bytes)
    assert os.environ['CUDA_VISIBLE_DEVICES'] == ''
    assert os.sched_getaffinity(0) == {0}
    assert all(os.environ[k] == '1' for k in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'))
    fixture_bytes = FIX.read_bytes()
    assert sha(fixture_bytes) == prereg['source_fixture_sha256']
    rows = [json.loads(line) for line in fixture_bytes.splitlines()]
    spec = importlib.util.spec_from_file_location('saved_pv_validator', 'tools/ai-sigma-pv-pipeline-bootstrap/bootstrap.py')
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    assert validator.validate(rows) == {'rows': 5, 'groups': 5, 'train': 4, 'validation': 1}
    assert [{'fixture': r['fixture'], 'group': r['group'], 'split': r['split'], 'side': r['state']['side'], 'K': r['teacher']['K']} for r in rows] == prereg['rows']
    # Heavy imports are reached only through the owner admission wrapper.
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    # Seed only the CPU generator: torch.manual_seed would call deferred CUDA seeding.
    torch.random.default_generator.manual_seed(80311)

    class ToyPV(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.hidden = torch.nn.Linear(648, 16, device='cpu', dtype=torch.float32)
            self.policy = torch.nn.Linear(16, 136, device='cpu', dtype=torch.float32)
            self.value = torch.nn.Linear(16, 1, device='cpu', dtype=torch.float32)

        def forward(self, x):
            h = torch.relu(self.hidden(x))
            return self.policy(h), torch.tanh(self.value(h))

    x = torch.tensor([validator.floats(r['features_bits']) for r in rows], dtype=torch.float32, device='cpu')
    pi = torch.tensor([r['pi136'] for r in rows], dtype=torch.float32, device='cpu')
    target = torch.tensor([[r['teacher']['rootmean_stm']] for r in rows], dtype=torch.float32, device='cpu')
    mask = torch.zeros((5, 136), dtype=torch.bool, device='cpu')
    for i, r in enumerate(rows):
        for action, canonical in r['mapping136']:
            mask[i, canonical] = True
    assert x.shape == (5, 648) and pi.shape == (5, 136) and target.shape == (5, 1)
    assert torch.isfinite(x).all() and torch.isfinite(pi).all() and torch.isfinite(target).all()
    assert torch.all(pi[~mask] == 0)
    train = torch.tensor([i for i, r in enumerate(rows) if r['split'] == 'train'], device='cpu')
    val = torch.tensor([i for i, r in enumerate(rows) if r['split'] == 'validation'], device='cpu')
    model = ToyPV()
    checkpoint = D / 'toy-checkpoint.pt'

    def loss(indices):
        logits, value = model(x[indices])
        assert logits.shape == (len(indices), 136) and value.shape == (len(indices), 1)
        assert torch.isfinite(logits).all() and torch.isfinite(value).all()
        masked = logits.masked_fill(~mask[indices], -1e9)
        policy = -(pi[indices] * torch.log_softmax(masked, dim=1)).sum(dim=1).mean()
        mse = torch.mean((value - target[indices]) ** 2)
        total = policy + mse
        assert torch.isfinite(total)
        return total, policy, mse

    result = {'issue': 'quoridor-4lc.162', 'run': 'cpu-toy162-r1', 'mode': args.mode,
              'start_epoch': start, 'preregister_sha256': sha(prereg_bytes),
              'fixture_sha256': sha(fixture_bytes), 'device': 'cpu', 'dtype': 'float32',
              'torch_version': str(torch.__version__), 'torch_intra_op': torch.get_num_threads(),
              'torch_inter_op': torch.get_num_interop_threads(), 'CUDA_API_calls_in_own_source': 0,
              'parameter_count': sum(p.numel() for p in model.parameters()), 'new_teacher': 0,
              'new_game': 0, 'independent_holdout': False, 'game_z': None}
    if args.mode == 'train':
        assert not checkpoint.exists(), 'existing checkpoint forbids training replacement'
        initial = {k: v.detach().clone() for k, v in model.state_dict().items()}
        initial_hash = sha(b''.join(v.numpy().tobytes() for v in initial.values()))
        with torch.no_grad():
            before_train = [v.item() for v in loss(train)]
            before_val = [v.item() for v in loss(val)]
        # Exact zero-momentum/zero-decay SGD update. Avoid optimizer CUDA graph hooks.
        ledger = []
        for step in range(20):
            model.zero_grad(set_to_none=True)
            total, policy, mse = loss(train)
            total.backward()
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
            grad_max = max(p.grad.abs().max().item() for p in model.parameters())
            ledger.append({'step': step + 1, 'loss': total.item(), 'policy_CE': policy.item(), 'value_MSE': mse.item(), 'grad_max_abs': grad_max, 'grad_finite': True})
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.add_(parameter.grad, alpha=-.01)
            assert all(torch.isfinite(p).all() for p in model.parameters())
        updated = [k for k, v in model.state_dict().items() if not torch.equal(v, initial[k])]
        assert updated, 'no parameter update'
        with torch.no_grad():
            after_train = [v.item() for v in loss(train)]
            after_val = [v.item() for v in loss(val)]
            original_forward = tuple(v.clone() for v in model(x))
        torch.save(model.state_dict(), checkpoint)
        result.update(training_steps=20, initial_weights_sha256=initial_hash, updated_parameter_tensors=updated,
                      loss_before={'train': before_train, 'validation': before_val}, loss_after={'train': after_train, 'validation': after_val}, ledger=ledger,
                      training_finish_epoch=time.time(), checkpoint_sha256=sha(checkpoint.read_bytes()), checkpoint_bytes=checkpoint.stat().st_size)
        write('training-results.json', result)
    else:
        assert checkpoint.exists(), 'export repair requires existing checkpoint'
        original_forward = None

    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    loaded = ToyPV()
    loaded.load_state_dict(state, strict=True)
    assert all(torch.equal(v, loaded.state_dict()[k]) for k, v in state.items())
    loaded.eval()
    with torch.no_grad():
        loaded_forward = loaded(x)
    if original_forward is not None:
        assert all(torch.equal(a, b) for a, b in zip(original_forward, loaded_forward))
    result.update(checkpoint_weights_only_reload=True, reload_weights_bit_equal=True,
                  reload_forward_bit_equal=True if original_forward is not None else None,
                  checkpoint_sha256=sha(checkpoint.read_bytes()))
    write('checkpoint-reload.json', {k: v for k, v in result.items() if k != 'ledger'})
    try:
        import onnx
        import onnxruntime as ort
        onnx_path = D / 'toy.onnx'
        torch.onnx.export(loaded, (x,), str(onnx_path), input_names=['features'], output_names=['policy_logits', 'value'], opset_version=17, dynamo=False)
        onnx.checker.check_model(str(onnx_path))
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        session = ort.InferenceSession(str(onnx_path), sess_options=options, providers=['CPUExecutionProvider'])
        assert session.get_providers() == ['CPUExecutionProvider']
        outputs = session.run(['policy_logits', 'value'], {'features': x.numpy()})
        parity = []
        for name, reference, actual in zip(['policy_logits', 'value'], loaded_forward, outputs):
            reference = reference.numpy()
            assert actual.shape == reference.shape
            import numpy as np
            assert np.isfinite(actual).all()
            diff = np.abs(actual-reference)
            tolerance = 1e-5 + 1e-4*np.abs(reference)
            accepted = bool(np.all(diff <= tolerance))
            parity.append({'output': name, 'shape': list(actual.shape), 'max_abs_error': float(diff.max()), 'max_error_over_tolerance': float((diff/tolerance).max()), 'accepted': accepted})
            assert accepted, name+' CPU ONNX parity outside fixed tolerance'
        result.update(onnx_status='supported_on_five_fixed_rows', onnx_sha256=sha(onnx_path.read_bytes()), onnx_bytes=onnx_path.stat().st_size,
                      onnx_version=str(onnx.__version__), ORT_version=str(ort.__version__), providers=session.get_providers(), parity=parity, status='pipeline_smoke_supported')
        del session
    except Exception as exc:
        result.update(onnx_status='typed_export_or_dependency_or_parity_failure', status='checkpoint_supported_export_unresolved', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    result['end_epoch'] = time.time()
    write('results.json' if args.mode == 'train' else 'export-repair-results.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('ledger', 'traceback')}, allow_nan=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        write('fatal-'+str(time.time_ns())+'.json', {'type': type(exc).__name__, 'error': str(exc), 'traceback': traceback.format_exc(), 'epoch': time.time()})
        raise
