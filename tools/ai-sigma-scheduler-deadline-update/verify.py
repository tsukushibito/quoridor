"""Isolated checks of the live copy's hash guard; never imports/runs its monitor loop."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import resource
import os
import datetime as dt
sys.path.insert(0,str(Path(__file__).parent))
import safe_state
tree=ast.parse((Path(__file__).parent/'watch.py').read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='readstate')
parent=Path(__file__).resolve().parents[2]/'.artifacts/ai-sigma/continuation-20261001/SIGMA-DEADLINE-UPDATE'
checks=[]
with tempfile.TemporaryDirectory(dir=parent,prefix='fixture-') as name:
 p=Path(name);inputfile=p/'config.json';inputfile.write_text('{}');(p/'state.json').write_text('{}')
 class Fake:
  Unavailable=safe_state.Unavailable
  @staticmethod
  def read_bounded(*a,**k):return {'validated_fixture':True}
 space={'EXPECTED':{'input_hashes':{str(inputfile):hashlib.sha256(inputfile.read_bytes()).hexdigest()}},'Path':Path,'hashlib':hashlib,'safe_state':Fake,'STATE':p,'EXPECTED_BINDING':{},'EXPECTED_PROCESS':{},'read_failure':lambda x:None}
 exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-copy-readstate','exec'),space)
 assert space['readstate']()=={'validated_fixture':True};checks.append('matching hashes permit bounded state read')
 inputfile.write_text('{"changed":true}')
 try:space['readstate']()
 except safe_state.Unavailable:checks.append('changed input hash fails closed before state read')
 else:raise AssertionError('changed hash accepted')
 inputfile.unlink()
 try:space['readstate']()
 except OSError:checks.append('missing input fails closed into monitor abnormal-stop handler')
 else:raise AssertionError('missing input accepted')
const=[x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('END','FINAL') for t in x.targets)]
space={'dt':dt,'UTC':dt.timezone.utc};exec(compile(ast.Module(body=const,type_ignores=[]),'actual-copy-deadlines','exec'),space)
assert space['END']==dt.datetime(2026,10,2,0,55,tzinfo=dt.timezone.utc)
assert space['FINAL']==dt.datetime(2026,10,2,0,58,tzinfo=dt.timezone.utc)
checks.append('actual-copy END00:55 FINAL00:58 UTC')
print(json.dumps({'checks':checks,'passed':len(checks),'live_fault_injection':False,'signals':0,'pid':os.getpid(),'self_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},ensure_ascii=False))
