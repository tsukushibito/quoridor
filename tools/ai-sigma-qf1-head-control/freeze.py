"""Freeze candidate first, then bind advertised sealed labels without opening."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

D = Path('research-data/ai-sigma/frame14-head-control')
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, value):
    with Path(p).open('x') as file:
        json.dump(value, file, indent=2, allow_nan=False)
        file.write('\n')

p = argparse.ArgumentParser()
p.add_argument('--manifest')
a = p.parse_args()
if not a.manifest:
    s = json.loads((D/'evaluator-settings.json').read_text())
    assert json.loads((D/'gate-result.json').read_text())['status'] == 'GATE_MET'
    config = json.loads(Path(s['config']).read_text())
    paths = ['tools/ai-sigma-qf1-head-control/evaluate.py',
             'tools/ai-sigma-qf1-distance-residual/evaluate.py', s['forward_source'],
             'tools/nnue-training/model.py', 'tools/nnue-training/common.py',
             'tools/nnue-training/frame14_data.py', 'tools/nnue-training/test_contrast.py']
    f = {'kind': 'QF1-frozen-lower-head-only-one-fresh-test',
         'UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'condition': s['condition'], 'artifacts': {'candidate': s['checkpoints']['best'],
          'best': s['checkpoints']['best'], 'last': s['checkpoints']['last']},
         'coefficients': s['coefficients'], 'coefficient_fit_SHA': s['coefficient_fit_SHA'],
         'model_config': config['model'], 'train_config': config, 'train_config_SHA': s['config_SHA'],
         'stage_SHA': s['stage_SHA'], 'validation_SHA': s['validation_SHA'], 'original_mask_SHA': s['mask_SHA'],
         'initial_tensor_SHA': s['initial_tensor_SHA'], 'best_step': s['best_step'],
         'candidate_validation_gameMSE': s['best_validation_gameMSE'], 'constant': s['constant'],
         'selection_rule': 'fixed validation gameequal rootmeanMSE; step0 included',
         'paired_comparisons': [['candidate','distance_only'], ['candidate','constant'], ['last','distance_only']],
         'bootstrap_seed': 20480311, 'bootstrap_replicates': 2000, 'unique_NN_max': 3, 'sample_cap': 12000,
         'sources': {v: sha(v) for v in paths}, 'source_freeze': True,
         'gate_result_SHA': sha(D/'gate-result.json'), 'evaluator_settings_SHA': sha(D/'evaluator-settings.json'),
         'initial_forward_parity_schema_SHA': sha(D/'finite-schema.json'),
         'training_stop_SHA': sha(D/'training-stop.json'), 'test_labels_read': False,
         'old_test_labels_read': False, 'test_reselection': False,
         'analytical_baselines_no_NN_samples': ['distance_only','constant']}
    for artifact in f['artifacts'].values():
        assert sha(artifact['path']) == artifact['checkpoint_SHA']
    write(D/'candidate-freeze.json', f)
else:
    candidate = D/'candidate-freeze.json'
    f = json.loads(candidate.read_text())
    manifest = json.loads(Path(a.manifest).read_text())
    maskpath = manifest['mask']
    assert sha(manifest['metadata']) == manifest['metadata_sha256']
    assert sha(maskpath) == manifest['mask_sha256']
    mask = json.loads(Path(maskpath).read_text())
    f.update({'metadata': {'path': manifest['metadata'], 'SHA': manifest['metadata_sha256']},
              'mask': {'path': maskpath, 'SHA': manifest['mask_sha256']},
              'labels': {'path': manifest['test_labels'], 'SHA': manifest['test_labels_sha256']},
              'candidate_freeze_SHA': sha(candidate), 'fresh_test_manifest': str(Path(a.manifest).resolve()),
              'fresh_test_manifest_SHA': sha(a.manifest), 'reference_metadata_SHA': mask['reference_metadata_SHA'],
              'mask_rule': 'state OR history OR actual STM-f32 QF1; oldtrain96+allval+oldtest24+distance-test24',
              'test_labels_hash_from_owner_only': True, 'labels_read_before_freeze': False})
    write(D/'test-freeze.json', f)
print(json.dumps({'candidate_freeze_SHA': sha(D/'candidate-freeze.json'), 'labels_read': False,
                  'test_freeze_SHA': sha(D/'test-freeze.json') if a.manifest else None}))
