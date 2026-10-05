"""Reuse saved-curve plotting; no Torch/model/forward."""
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path('tools/nnue-training').resolve()))
from plot import plot_runs
D = Path('research-data/ai-sigma/frame14-distance-residual')
R = D / 'runs/frame14-distance-residual-r1'
history = [json.loads(x) for x in (R / 'history.jsonl').read_text().splitlines()]
keys = ['step', 'train_samples_seen', 'train_epochs_equivalent', 'all_samples', 'elapsed_s']
metrics = ['rootmean_game_equal_mse', 'z_game_equal_mse', 'z_sign_accuracy', 'saturation_fraction']
with (D / 'curves.csv').open('w') as file:
    writer = csv.writer(file)
    writer.writerow(keys + [s+'_'+m for s in ['train', 'validation'] for m in metrics])
    for r in history:
        writer.writerow([r[k] for k in keys] + [r[s][m] for s in ['train', 'validation'] for m in metrics])
for metric in ['target', 'rootmean', 'z']:
    plot_runs([R], D / 'curves' / metric, 'train_samples_seen', metric)
assert 'torch' not in sys.modules
print(json.dumps({'rows': len(history), 'plots': 6, 'model_forward': 0, 'samples': 0}))
