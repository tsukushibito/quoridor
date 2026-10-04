"""200 finite launcher: read-only 195 manager functions, private budget/state/path."""
import argparse
import importlib.util
import json
from pathlib import Path

D=Path('research-data/ai-sigma/frame14-distance-residual')
spec=importlib.util.spec_from_file_location('readonly_manager','tools/nnue-training/manage_frame14.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.D=D
original_state=m.state
m.state=lambda issue:original_state('quoridor-4lc.200' if issue=='quoridor-4lc.195' else issue)
p=argparse.ArgumentParser()
p.add_argument('--id',required=True);p.add_argument('--kind',choices=['static','heavy'],required=True)
p.add_argument('--seconds',type=float,required=True);p.add_argument('--samples',type=int,default=0);p.add_argument('--result')
p.add_argument('--new',default='2026-10-04T02:10:00Z');p.add_argument('--stop',default='2026-10-04T02:20:00Z')
p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
if a.command and a.command[0]=='--':a.command=a.command[1:]
assert a.command and 0<a.seconds<=120
prior=[json.loads(x.read_text()) for x in (D/'jobs').glob('*/process.json')]
assert sum(x['wall_seconds'] for x in prior if x['kind']==a.kind)+a.seconds<=(300 if a.kind=='heavy' else 600)
assert sum(x['samples_charged'] for x in prior)+a.samples<=500000
s=json.loads((D/'storage-admission.json').read_text())
assert s['forecast_B']<s['guard_B']==14680064
assert s['combined_old_current_residual_plus_new_reservation_B']<s['combined_guard_B']==58720256
m.main(a)
