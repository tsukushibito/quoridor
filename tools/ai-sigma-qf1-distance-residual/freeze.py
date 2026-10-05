"""Freeze residual/baselines first, then bind owner label-free fresh-test manifest."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

D = Path('research-data/ai-sigma/frame14-distance-residual')
T = Path('tools/ai-sigma-qf1-distance-residual')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_once(p, value):
    with p.open('x') as file:
        file.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def candidate(path):
    e = json.loads((D / 'evaluator-settings.json').read_text())
    random = json.loads((D / 'random-baseline-binding.json').read_text())
    artifacts = {'candidate': e['checkpoints']['best'], 'best': e['checkpoints']['best'],
                 'last': e['checkpoints']['last'], 'distance_initial': e['checkpoints']['initial'],
                 'random_QF1': random}
    for r in artifacts.values():
        assert sha(r['path']) == r['checkpoint_SHA']
    assert e['checkpoints']['initial']['weight_SHA'] != random['weight_SHA']
    config = json.loads(Path(e['config']).read_text())
    f = {'kind': 'QF1-distance-residual-one-fresh-test', 'UTC': datetime.datetime.now(datetime.UTC).isoformat(),
         'condition': e['condition'], 'artifacts': artifacts, 'coefficients': e['coefficients'],
         'coefficient_fit_SHA': e['coefficient_fit_SHA'], 'model_config': config['model'],
         'train_config': config, 'train_config_SHA': e['config_SHA'], 'stage_SHA': e['stage_SHA'],
         'validation_SHA': e['validation_SHA'], 'original_mask_SHA': e['mask_SHA'],
         'best_step': e['best_step'], 'candidate_validation_gameMSE': e['best_validation_gameMSE'],
         'constant': e['constant'], 'selection_rule': 'fixed validation gameequal rootmeanMSE, step0 included',
         'paired_comparisons': [['candidate', 'distance_only'], ['candidate', 'constant'],
                                ['candidate', 'random_QF1'], ['last', 'distance_only']],
         'bootstrap_seed': 20080311, 'bootstrap_replicates': 2000, 'unique_NN_max': 4,
         'sample_cap': 12000, 'source_freeze': True,
         'sources': {str(p): sha(p) for p in [T / 'evaluate.py', T / 'residual_model.py',
                      Path('tools/nnue-training/model.py'), Path('tools/nnue-training/common.py'),
                      Path('tools/nnue-training/frame14_data.py'), Path('tools/nnue-training/test_contrast.py')]},
         'test_labels_read': False, 'old_test_labels_read': False, 'test_reselection': False,
         'analytical_baselines_no_NN_samples': ['distance_only', 'constant']}
    write_once(path, f)
    print(json.dumps({'freeze_SHA': sha(path), 'test_labels_read': False,
                      'weight_unique': len({(r['condition'], r['weight_SHA']) for r in artifacts.values()})}))


def bind(a):
    candidate_path = Path(a.candidate)
    f = json.loads(candidate_path.read_text())
    descriptor = json.loads(Path(a.manifest).read_text())
    # Explicit owner manifest schema, never glob a test/raw/statejournal directory.
    for name, field in [('metadata', 'metadata'), ('mask', 'mask'), ('labels', 'test_labels')]:
        f[name] = {'path': descriptor[field], 'SHA': descriptor[field+'_sha256']}
        assert isinstance(f[name]['path'], str) and len(f[name]['SHA']) == 64
    for name in ['metadata', 'mask']:
        assert sha(f[name]['path']) == f[name]['SHA']
    mask = json.loads(Path(f['mask']['path']).read_text())
    assert mask['new_metadata_SHA'] == f['metadata']['SHA'] and mask['labels_used'] is False
    reference = Path(mask['reference_metadata_path'])
    assert sha(reference) == mask['reference_metadata_SHA']
    f.update({'candidate_freeze_SHA': sha(candidate_path),
              'fresh_test_manifest': str(Path(a.manifest).resolve()), 'fresh_test_manifest_SHA': sha(a.manifest),
              'reference_metadata_SHA': mask['reference_metadata_SHA'],
              'mask_rule': 'state OR history OR actual QF1; oldtrain96+allval+oldtest label-free reference',
              'test_labels_hash_from_owner_only': True, 'labels_read_before_freeze': False})
    assert len(set(descriptor['all24_families'])) == 24
    assert set(descriptor['all24_families']) == set(mask['games'])
    write_once(D / 'test-freeze.json', f)
    print(json.dumps({'freeze_SHA': sha(D / 'test-freeze.json'), 'labels_read': False}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['candidate', 'bind'])
    p.add_argument('--manifest')
    p.add_argument('--candidate', default=str(D / 'candidate-freeze-v2.json'))
    a = p.parse_args()
    if a.command == 'candidate':
        candidate(Path(a.candidate))
    else:
        assert a.manifest
        bind(a)
