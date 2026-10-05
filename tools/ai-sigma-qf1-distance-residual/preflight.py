"""Label-free scalar/schema and interpreter/AST checks; imports no torch."""
import ast
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

D = Path('research-data/ai-sigma/frame14-distance-residual')
T = Path('tools/ai-sigma-qf1-distance-residual')
sys.path.insert(0, str(Path('tools/nnue-training').resolve()))
from frame14_data import canonical_model_input
reg = json.loads((D / 'preregister.json').read_text())
for p in T.glob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
python = '/home/vscode/.cache/inference/envs/quoridor-training/bin/python'
assert os.access(python, os.X_OK)
f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
a, b = reg['coefficients'].values()
clip = lambda x: max(-1., min(1., x))
witnesses = []
for own, opp in [(0., 0.), (.1, .2), (.2, .1), (.025, .05), (.05, .025), (.5, .5), (0., 1.), (1., 0.)]:
    own, opp = f32(own), f32(opp)
    oracle = clip(a + b * (opp - own))
    actual = clip(f32(f32(a) + f32(f32(b) * f32(opp - own))))
    assert math.isfinite(actual) and abs(actual-oracle) <= 1e-6+1e-6*abs(oracle)
    witnesses.append({'STM_distance': [own, opp], 'oracle': oracle, 'f32': actual})
# Canonical input is already STM ordered; no second distance/side rotation.
x = {'ids': [[1, 83, 302], [2, 84, 303]], 'distance': [.1, .2], 'side': 1}
y = {'ids': list(reversed(x['ids'])), 'distance': x['distance'], 'side': 2}
assert canonical_model_input(x) == canonical_model_input(y)
assert not any(k == 'torch' or k.startswith('torch.') for k in sys.modules)
result = {'UTC': datetime.datetime.now(datetime.UTC).isoformat(), 'status': 'PASS_NN0_PREFLIGHT',
          'python_executable': python, 'AST': True, 'scalar_witnesses': witnesses,
          'STM_side_swap_same_input': True, 'distance_rotated_twice': False,
          'argv': [python, '-B', str(T / 'run.py')], 'newscience': '2026-10-04T02:10:00Z',
          'stop': '2026-10-04T02:20:00Z', 'model_loaded': False, 'samples': 0}
(D / 'preflight.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
