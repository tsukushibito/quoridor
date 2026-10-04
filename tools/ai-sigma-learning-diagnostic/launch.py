"""209 job ownership and bounded family guard, reusing readonly manager."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

D=Path('research-data/ai-sigma/frame15-learning-diagnostic')
spec=importlib.util.spec_from_file_location('readonly_manager','tools/nnue-training/manage_frame14.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.D=D
state=m.state;m.state=lambda issue:state('quoridor-4lc.209'if issue=='quoridor-4lc.195'else issue)
p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--kind',choices=['static','heavy'],required=True)
p.add_argument('--seconds',type=float,required=True);p.add_argument('--samples',type=int,default=0);p.add_argument('--result')
p.add_argument('--new',default='2026-10-04T04:45:00Z');p.add_argument('--stop',default='2026-10-04T04:55:00Z');p.add_argument('command',nargs=argparse.REMAINDER)
a=p.parse_args();a.command=a.command[1:]if a.command and a.command[0]=='--'else a.command
assert a.command and 0<a.seconds<=120
prior=[json.loads(x.read_text())for x in(D/'jobs').glob('*/process.json')]
assert sum(j['wall_seconds']for j in prior if j['kind']==a.kind)+a.seconds <= (600 if a.kind=='heavy'else 1200)
assert sum(j['samples_charged']for j in prior)+a.samples<=800000
s=json.loads((D/'storage-admission.json').read_text());assert s['forecast_B']<s['guard_B']==6291456
assert s['combined_conservative_allocation_B']<s['shared_guard_B']==58720256
for row in m.current():
    if row['pid']==os.getpid() or row['cmd'].startswith('/bin/bash -c '):continue
    script=next((x for x in row['cmd'].split()if x.endswith(('.py','.cjs'))),'')
    if any(x in script for x in ['tools/ai-sigma-learning-diagnostic-independent/',
                                'tools/ai-sigma-learning-diagnostic/', 'tools/ai-sigma-qf1-']):
        if not script.endswith(('/save.py','/save_git.py')):
            raise ValueError('current science/helper owner identity '+str((row['pid'],row['tick'],script)))
m.main(a)
