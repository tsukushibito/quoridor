"""One residual training run, reusing the immutable trainer in memory."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

D = Path('research-data/ai-sigma/frame14-distance-residual')
sys.path.insert(0, str(Path('tools/nnue-training').resolve()))
reg = json.loads((D / 'preregister.json').read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
for path, h in reg['readonly_sources'].items():
    assert sha(path) == h, path
for path, h in reg['private_sources'].items():
    assert sha(path) == h, path
assert sha(reg['stage']) == reg['stage_SHA']
assert sha(reg['fit_source']) == reg['fit_SHA']
assert json.loads(Path(reg['fit_source']).read_text())['fit']['a'] == reg['coefficients']['a']
assert json.loads(Path(reg['fit_source']).read_text())['fit']['b'] == reg['coefficients']['b']

import model
from residual_model import ResidualModel, A, B, CONDITION
model.Model = ResidualModel
from train import train
args = argparse.Namespace(data=reg['stage'], config=str(D / 'config.json'), set=[],
                          run_id=reg['run_id'], output=str(D / 'runs'),
                          checkpoints='models/experiments/nnue', init_checkpoint=None, dry_run=False)
train(args)
R = D / 'runs' / reg['run_id']
s = json.loads((R / 'summary.json').read_text())
data = json.loads((R / 'dataset.json').read_text())
assert s['status'] == 'max_steps' and s['step'] == 2000 and s['all_samples'] == 379921
assert s['last_evaluation']['train_samples_seen'] == 256000
check = ResidualModel.instances[0].initial_check
assert check['rows'] == 5901 and check['pass'] and check['max_residual_abs'] == 0
import torch
# Scalar arithmetic autograd checks, no additional NN forward or sample.
t = torch.tensor([-2., -.5, .5, 2.], requires_grad=True)
t.clamp(-1, 1).sum().backward()
assert t.grad.tolist() == [0., 1., 1., 0.]
checks = {}
for name in ['initial', 'best', 'last']:
    p = Path(s['checkpoint_dir']) / (name + '.pt')
    cp = torch.load(p, weights_only=True, map_location='cpu')
    assert cp['target'] == 'rootmean'
    assert cp['model']['distance_a'].item() == torch.tensor(A, dtype=torch.float32).item()
    assert cp['model']['distance_b'].item() == torch.tensor(B, dtype=torch.float32).item()
    checks[name] = {'path': str(p.resolve()), 'checkpoint_SHA': sha(p), 'B': p.stat().st_size,
                    'weight_SHA': hashlib.sha256(b''.join(v.numpy().tobytes() for v in cp['model'].values())).hexdigest(),
                    'step': cp['step'], 'samples': cp['samples'], 'condition': CONDITION}
history = [json.loads(x) for x in (R / 'history.jsonl').read_text().splitlines()]
assert len(history) == 21 and [x['step'] for x in history] == list(range(0, 2001, 100))
finite = dict(check, atol=1e-6, rtol=1e-6, scalar_clip_inputs=t.detach().tolist(),
              scalar_clip_gradients=t.grad.tolist(), extra_NN_forward_samples=0,
              saturated_baseline_gradient='zero outside clip, possible residual learning limitation')
(D / 'initial-parity.json').write_text(json.dumps(finite, indent=2) + '\n')
settings = {'condition': CONDITION, 'private_model': 'tools/ai-sigma-qf1-distance-residual/residual_model.py',
            'private_model_SHA': sha('tools/ai-sigma-qf1-distance-residual/residual_model.py'),
            'coefficients': reg['coefficients'], 'coefficient_fit_SHA': reg['fit_SHA'],
            'constant': data['constant'], 'checkpoints': checks, 'config': str((R / 'config.json').resolve()),
            'config_SHA': sha(R / 'config.json'), 'mask_SHA': data['stage_manifest']['mask_sha256'],
            'validation_SHA': data['validation_sha256'], 'stage_SHA': reg['stage_SHA'],
            'best_step': s['best_step'], 'best_validation_gameMSE': s['best_validation_mse'],
            'initial_validation_gameMSE': history[0]['validation']['target_game_equal_mse'],
            'samples': s['all_samples'], 'old_test_read': False, 'NN_strength_claim': False}
(D / 'evaluator-settings.json').write_text(json.dumps(settings, indent=2) + '\n')
print(json.dumps({'UTC': datetime.datetime.now(datetime.UTC).isoformat(), 'samples': s['all_samples'],
                  'best_step': s['best_step'], 'initial_parity': finite,
                  'best_validation_gameMSE': s['best_validation_mse']}))
