import json,hashlib,datetime
from pathlib import Path
ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma');O=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-STREAMING-COMPARISON32-PLAN';p=json.loads((O/'preregister.json').read_text());s=json.loads((O/'preregister-schema.json').read_text());control=json.loads((O/'control-plan.json').read_text());checks=[]
def validate(value,schema):
 if 'const' in schema:assert value==schema['const'];checks.append('const')
 kind=schema.get('type')
 if kind=='object':
  assert isinstance(value,dict)
  for f in schema.get('required',[]):assert f in value
  for f,x in schema.get('properties',{}).items():
   if f in value:validate(value[f],x)
 elif kind=='array':
  assert isinstance(value,list) and len(value)>=schema.get('minItems',0) and len(value)<=schema.get('maxItems',10**9)
  if schema.get('uniqueItems'):assert len({json.dumps(x,sort_keys=True) for x in value})==len(value)
  for x in value:
   if 'items' in schema:validate(x,schema['items'])
 elif kind=='integer':assert isinstance(value,int) and not isinstance(value,bool) and schema.get('minimum',value)<=value<=schema.get('maximum',value)
 elif kind=='null':assert value is None
validate(p,s);assert p['actual_go'] is False and p['source_binding']['accepted'] is False;assert all(x['accepted'] is False for x in p['gates']);assert set(p['ordered_indices'])==set(p['selected_indices']);assert not set(p['selected_indices'])&set(p['excluded_sent8']);d=json.loads((O/'prefix-dictionary.json').read_text());assert hashlib.sha256((O/'prefix-dictionary.json').read_bytes()).hexdigest()==p['prefix_dictionary']['sha256'];assert all(b['prefix_ref'] in d for b in p['pairs']);stop=datetime.datetime.fromisoformat(p['run_budget']['match_stop_UTC'].replace('Z','+00:00'));latest=datetime.datetime.fromisoformat(p['run_budget']['latest_start_UTC'].replace('Z','+00:00'));assert (stop-latest).total_seconds()==8601.5;assert (stop-(latest+datetime.timedelta(milliseconds=1))).total_seconds()<8601.5;assert control['actual_go'] is False and control['same_main_not_executed_here'];assert len(control['bindings'])==9
r={'schema_supported_subset_validation':True,'constant_checks':len(checks),'semantic_checks':True,'exact8601_5_and_plus1ms_nogo':True,'unbound_sources_not_accepted':True,'control_connections':9,'actual_go':False,'NN':0,'engine':0,'games':0};(O/'schema-control-verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
