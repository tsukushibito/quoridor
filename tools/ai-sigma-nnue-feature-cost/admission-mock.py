import importlib.util,json
from pathlib import Path
p=Path(__file__).parent/'admission.py';s=importlib.util.spec_from_file_location('private_admission',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
rows=[]
for name,heavy,previous,error in [('false',[{'physicalheavy':True}],[],None),('unknown',[],[{}],None),('readerror',[],[],'READ_ERROR'),('owned_remaining',[],[{'remaining':[1],'unknown_adopted':[]}],None),('true',[],[],None)]:
 spawned=0
 try:
  decision=m.base.base.decide(heavy,previous,error)
  assert decision is True
  if name!='true':raise AssertionError('BAD_ALLOW')
  rows.append({'case':name,'decision':True,'mock_only_not_actual_spawn':True})
 except RuntimeError as e:rows.append({'case':name,'failure':str(e),'spawn_count':spawned})
Path('research-data/ai-sigma/156-nnue-feature-cost/admission-mock.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows))
