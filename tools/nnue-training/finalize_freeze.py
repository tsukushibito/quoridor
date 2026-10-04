"""Select only by preregistered validation score, bind one sealed test; NN0."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

D = Path('research-data/ai-sigma/frame14-learning')
runs = [D / f'runs/frame14-train{n}-r1' for n in (24, 48, 96)]
scores = []
for n, run in zip((24, 48, 96), runs):
    s = json.loads((run / 'summary.json').read_text())
    assert s['status'] == 'max_steps' and s['step'] == 2000
    scores.append((s['best_validation_mse'], n, s['best_step'], run))
score, stage, step, run = min(scores)
selection = {
    'UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'rule': 'lowest fixed primary validation gameequal MSE; ties stage24/48/96 then earlieststep',
    'candidate_stage': stage, 'best_step': step, 'validation_score': score,
    'all_candidates': [{'stage': n, 'step': t, 'score': v} for v, n, t, _ in scores],
    'note': 'All beststep0 share exact initial tensorSHA. Approximately 1e-11 initial score differences arise with batch context; selected48 is not evidence of superior learned weights.',
    'test_labels_read': False, 'additional_training': False,
}
(D / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
desc = json.loads(Path('research-data/ai-sigma/frame14-teachers/final-qf1-v2/dataset-manifest.json').read_text())
test = {'path': desc['test_labels'], 'sha256': desc['test_labels_sha256']}
candidate = D / 'candidate-freeze.json'
subprocess.run([sys.executable, '-B', 'tools/nnue-training/frame14.py', 'freeze',
                '--run', str(run), '--test-labels', test['path'], '--test-sha', test['sha256'],
                '--output', str(candidate), '--reason', json.dumps(selection, sort_keys=True)], check=True)
final = D / 'test-freeze.json'
subprocess.run([sys.executable, '-B', 'tools/nnue-training/test_contrast.py', 'freeze',
                '--candidate-freeze', str(candidate), '--stage24', str(runs[0]),
                '--stage96', str(runs[2]), '--output', str(final)], check=True)
print(json.dumps({'selected_stage': stage, 'best_step': step, 'test_freeze_sha256': hashlib.sha256(final.read_bytes()).hexdigest(), 'test_labels_read': False}))
