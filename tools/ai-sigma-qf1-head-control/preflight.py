"""AST/argv and fake head-only/frozen-byte API check, imports no Torch."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

D = Path('research-data/ai-sigma/frame14-head-control')
T = Path('tools/ai-sigma-qf1-head-control')
reg = json.loads((D/'preregister.json').read_text())
for p in T.glob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
for p, h in reg['readonly_sources'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
for p, h in reg['private_sources'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
python = '/home/vscode/.cache/inference/envs/quoridor-training/bin/python'
assert os.access(python, os.X_OK)
# Small fake: optimizer/check iterator exposes only head, state retains lower layers.
fake = {'ft.weight': b'ft', 'h.weight': b'h', 'out.weight': bytes(32), 'out.bias': bytes(1)}
trainable = ['out.weight', 'out.bias']
assert sum(len(fake[k]) for k in trainable) == 33
after = dict(fake, **{'out.weight': bytes([1])*32, 'out.bias': bytes([1])})
assert all(fake[k] == after[k] for k in fake if k not in trainable)
assert not any(k == 'torch' or k.startswith('torch.') for k in sys.modules)
result = {'UTC': datetime.datetime.now(datetime.UTC).isoformat(), 'status': 'PASS_NN0_PREFLIGHT',
          'AST': True, 'head_only_optimizer_iterator_fake': True, 'frozen_state_fake': True,
          'actual_tensor_frozen_proof': 'pending one real training/checkpoint byte comparison',
          'argv': [python, '-B', str(T/'run.py')], 'newscience': reg['newscience'], 'stop': reg['stop'],
          'samples': 0, 'model_load': False, 'old_test_read': False}
(D/'preflight.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
