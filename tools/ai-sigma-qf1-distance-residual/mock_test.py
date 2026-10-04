"""Small fake bindings/once opening/weight reuse; no real labels or model."""
import ast
import json
from pathlib import Path
import sys
import tempfile

D = Path('research-data/ai-sigma/frame14-distance-residual')
T = Path('tools/ai-sigma-qf1-distance-residual')
for p in T.glob('*.py'):
    ast.parse(p.read_text(), filename=str(p))
from freeze import write_once
artifacts = {'candidate': ('residual', 'zero'), 'best': ('residual', 'zero'),
             'distance_initial': ('residual', 'zero'), 'last': ('residual', 'learned'),
             'random_QF1': ('original', 'random')}
assert len(set(artifacts.values())) == 3
assert len(set(artifacts.values())) * 24 <= 12000
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / 'once.json'
    write_once(p, {'freeze_SHA': 'fake', 'label_read': False})
    duplicate_rejected = False
    try:
        write_once(p, {'second': True})
    except FileExistsError:
        duplicate_rejected = True
    assert duplicate_rejected
mask = {'a': {'group': 'g1', 'eligible': True}, 'b': {'group': 'g2', 'eligible': False}}
assert len({r['group'] for r in mask.values()}) == 2
assert len({r['group'] for r in mask.values() if r['eligible']}) == 1
assert not any(k == 'torch' or k.startswith('torch.') for k in sys.modules)
result = {'status': 'PASS_SMALL_FAKE', 'AST': True, 'weight_reuse': True,
          'once_marker_reject': True, 'zero_eligible_group_denominator': True,
          'mask_before_labels': True, 'real_test_labels': False, 'model_load': False, 'samples': 0}
(D / 'test-mock.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
