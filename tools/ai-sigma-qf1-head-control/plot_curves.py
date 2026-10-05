"""Render recorded curves only; no model/data/labels/forward."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path('tools/nnue-training').resolve()))
from plot import plot_runs

D = Path('research-data/ai-sigma/frame14-head-control')
paths = [D/'runs/frame14-head-control-r1',
         Path('research-data/ai-sigma/frame14-distance-residual/runs/frame14-distance-residual-r1')]
for metric in ['rootmean', 'z']:
    plot_runs(paths, D/('curves-'+metric), axis='train_samples_seen', metric_name=metric)
