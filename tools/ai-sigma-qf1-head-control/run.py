"""One head-only training run; all frozen tensor bytes and gates are explicit."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys

D = Path('research-data/ai-sigma/frame14-head-control')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg = json.loads((D / 'preregister.json').read_text())
for path, h in {**reg['readonly_sources'], **reg['private_sources']}.items():
    assert sha(path) == h, path
assert sha(reg['stage']) == reg['stage_SHA']
assert sha(reg['parent_settings']) == reg['parent_settings_SHA']
assert sha(reg['initial']['path']) == reg['initial']['checkpoint_SHA']
sys.path.insert(0, str(Path('tools/nnue-training').resolve()))
import model
from head_model import HeadModel
model.Model = HeadModel
from train import train
train(argparse.Namespace(data=reg['stage'], config=str(D/'config.json'), set=[],
                        run_id=reg['run_id'], output=str(D/'runs'),
                        checkpoints='models/experiments/nnue', init_checkpoint=None, dry_run=False))
R = D/'runs'/reg['run_id']
s = json.loads((R/'summary.json').read_text())
data = json.loads((R/'dataset.json').read_text())
assert s['status'] == 'max_steps' and s['step'] == 2000 and s['all_samples'] == 379921
assert data['initial_state_sha256'] == reg['initial']['weight_SHA']
assert data['validation_sha256'] == reg['validation_SHA']
assert data['stage_manifest']['mask_sha256'] == reg['mask_SHA']
history = [json.loads(x) for x in (R/'history.jsonl').read_text().splitlines()]
assert len(history) == 21 and [r['step'] for r in history] == list(range(0, 2001, 100))
parity = HeadModel.instances[0].initial_check
assert parity['rows'] == 5901 and parity['pass'] and parity['max_residual_abs'] == 0
import torch
parent = torch.load(reg['initial']['path'], weights_only=True, map_location='cpu')['model']
checks, frozen = {}, {}
for name in ['initial', 'best', 'last']:
    p = Path(s['checkpoint_dir'])/(name+'.pt')
    cp = torch.load(p, weights_only=True, map_location='cpu')
    assert cp['model_config'] == json.loads((R/'config.json').read_text())['model']
    assert cp['target'] == 'rootmean' and set(cp['model']) == set(parent)
    for key in reg['frozen']:
        assert cp['model'][key].numpy().tobytes() == parent[key].numpy().tobytes(), (name, key)
    if name == 'initial':
        assert all(cp['model'][key].numpy().tobytes() == parent[key].numpy().tobytes() for key in parent)
    checks[name] = {'path': str(p.resolve()), 'checkpoint_SHA': sha(p), 'B': p.stat().st_size,
                    'weight_SHA': hashlib.sha256(b''.join(v.numpy().tobytes() for v in cp['model'].values())).hexdigest(),
                    'step': cp['step'], 'samples': cp['samples'], 'condition': reg['condition']}
    frozen[name] = {key: hashlib.sha256(cp['model'][key].numpy().tobytes()).hexdigest() for key in reg['frozen']}
assert checks['initial']['weight_SHA'] == reg['initial']['weight_SHA']
schema = {'pass': True, 'initial_full_tensor_exact': True, 'frozen_tensor_exact': frozen,
          'trainable_names': ['out.weight', 'out.bias'], 'trainable_parameters': 33,
          'optimizer_head_only': True, 'initial_distance_parity': parity, 'extra_model_forward': 0,
          'outerclip_gradient_constraint': 'same as200; outside clip gradient0',
          'read_train4653_validation1248_only': True, 'old_test_read': False}
(D/'finite-schema.json').write_text(json.dumps(schema, indent=2)+'\n')
settings = {'condition': reg['condition'], 'forward_condition': 'QF1-distance-residual-f32-v1',
            'private_training_model': 'tools/ai-sigma-qf1-head-control/head_model.py',
            'forward_source': 'tools/ai-sigma-qf1-distance-residual/residual_model.py',
            'forward_source_SHA': reg['readonly_sources']['tools/ai-sigma-qf1-distance-residual/residual_model.py'],
            'initial_tensor_SHA': checks['initial']['weight_SHA'], 'checkpoints': checks,
            'coefficients': reg['coefficients'], 'coefficient_fit_SHA': reg['coefficient_fit_SHA'],
            'config': str((R/'config.json').resolve()), 'config_SHA': sha(R/'config.json'),
            'stage_SHA': reg['stage_SHA'], 'validation_SHA': reg['validation_SHA'], 'mask_SHA': reg['mask_SHA'],
            'constant': data['constant'], 'best_step': s['best_step'],
            'best_validation_gameMSE': s['best_validation_mse'], 'schema_SHA': sha(D/'finite-schema.json'),
            'samples': s['all_samples'], 'old_test_read': False, 'strength_claim': False}
(D/'evaluator-settings.json').write_text(json.dumps(settings, indent=2)+'\n')
conditions = {'beststep_positive_and_weight_changed': s['best_step']>0 and checks['best']['weight_SHA']!=checks['initial']['weight_SHA'],
              'below_distanceinitial_by_margin': s['best_validation_mse']<=reg['baseline_validation_gameMSE']-reg['gate_margin'],
              'finite_coeff_input_lowerlayer_schema': True}
provisional = {'issue': 'quoridor-4lc.204', 'UTC': datetime.datetime.now(datetime.UTC).isoformat(),
               'conditions': conditions, 'best_step': s['best_step'], 'best_validation_gameMSE': s['best_validation_mse'],
               'baseline_validation_gameMSE': reg['baseline_validation_gameMSE'], 'margin': reg['gate_margin'],
               'source_child_stop_pending': True, 'generation_authorized': False, 'samples': s['all_samples']}
(D/'gate-provisional.json').write_text(json.dumps(provisional, indent=2)+'\n')
print(json.dumps(provisional))
