import pathlib,json,struct,math,hashlib,os
ROOT=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH';ref=json.loads((ROOT/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json').read_text());gold=json.loads((ROOT/'.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json').read_text())['fixtures'];TAG=os.environ.get('NN_OUT_TAG','');summary={}
for platform in ['native','wasm']:
 actual=json.loads((RUN/(platform+'-diagnostic'+TAG+'.json')).read_text());assert len(actual['fixtures'])==28;maxabs=0.;maxprior=0.;bad=[];cases=[];nodes=0;edges=0;backups=0
 for f,o,a in zip(gold,ref,actual['fixtures']):
  assert f['id']==o['id']==a['id'];bits=[struct.unpack('<I',struct.pack('<f',x))[0]for x in f['raw_features_float32']];assert bits==a['features_bits'];assert hashlib.sha256(struct.pack('<648I',*bits)).hexdigest()==o['input_float32_sha256'];out=a['policy_logits']+[a['value']];expected=o['policy_logits']+[o['value']];assert len(out)==137
  for i,(x,y)in enumerate(zip(out,expected)):
   error=abs(x-y);maxabs=max(maxabs,error)
   if not math.isfinite(x)or error>1e-4+1e-4*abs(y):bad.append([f['id'],i,x,y])
  priors=o['canonical_legal_priors'];localmax=0
  if priors is not None:
   mapping={action['rust209']:z['prior'] for action,z in zip(f['legal_actions'],priors)};assert set(mapping)==set(a['raw_legal'])
   assert all(math.isfinite(x)and x>=0 for x in a['raw_prior']);assert abs(sum(a['raw_prior'])-1)<1e-5
   for id,x in zip(a['raw_legal'],a['raw_prior']):
    y=mapping[id];error=abs(x-y);maxprior=max(maxprior,error);localmax=max(localmax,error)
    if error>1e-4+1e-4*abs(y):bad.append([f['id'],'prior',id,x,y])
  for search in a['search']:
   cp=search['checkpoint'];assert cp['policy_fallbacks']==cp['value_fallbacks']==0
   if f['terminal']['effective_result']!='ongoing':assert cp['nn_calls']==0 and cp['action']is None
   else:assert cp['action']in a['effective_legal']
   table={n['index']:n for n in search['nodes']};ev={x['board_key']:x['value'] for x in search['evaluations']};memo={}
   def node_value(i):
    nonlocal_dummy=None
    if i in memo:return memo[i]
    n=table[i];child_visits=sum(e[2]for e in n['edges']);base=n['visits']-child_visits;assert base>=0
    if n['terminal']is not None:assert not n['edges'];v=n['terminal']*base
    else:v=(ev.get(n['key'],0))*base
    for e,c in zip(n['edges'],n['children']):
     assert e[0]in n['legal'];assert math.isfinite(e[1])and e[1]>=0 and math.isfinite(e[3])
     if c is None:assert e[2]==0;continue
     assert e[2]==table[c]['visits'];child=node_value(c);assert abs(e[3]+child)<=2e-5+2e-5*abs(child),(f['id'],i,e,child);v-=child
    memo[i]=v;return v
   node_value(0);nodes+=len(table);edges+=sum(len(n['edges'])for n in table.values());backups+=sum(c is not None for n in table.values()for c in n['children'])
  cases.append({'id':a['id'],'classification':a['classification'],'feature_bits':True,'numeric_gate':True,'max_prior_abs':localmax,'searches':len(a['search'])})
 assert not bad,bad[:5]
 summary[platform]={'model_output_elements':28*137,'feature_bits':28*648,'gate_failures':bad,'max_nn_abs':maxabs,'max_prior_abs':maxprior,'cases':cases,'nodes_checked':nodes,'edges_checked':edges,'backup_edges_checked':backups}
n=json.loads((RUN/('native-diagnostic'+TAG+'.json')).read_text());w=json.loads((RUN/('wasm-diagnostic'+TAG+'.json')).read_text());differences=[];decisions=[]
def diff(a,b,p=''):
 if isinstance(a,dict):
  assert a.keys()==b.keys(),p
  for k in a:
   if k not in ['arena_bytes','root_ms','spans']:diff(a[k],b[k],p+'/'+k)
 elif isinstance(a,list):
  assert len(a)==len(b),p
  for i,(x,y)in enumerate(zip(a,b)):diff(x,y,p+'/'+str(i))
 elif isinstance(a,float)or isinstance(b,float):
  if a!=b:differences.append({'path':p,'native':a,'wasm':b,'abs':abs(a-b)})
 else:
  if a!=b:decisions.append({'path':p,'native':a,'wasm':b})
diff(n,w);summary['native_wasm']={'float_differences':len(differences),'max_float_abs':max((x['abs']for x in differences),default=0),'decision_context_differences':decisions,'strict_bit_equal':not differences and not decisions,'difference_samples':differences[:30],'timing_arena_excluded':True};(RUN/('numeric-search-summary'+TAG+'.json')).write_text(json.dumps(summary,indent=2));print(json.dumps({k:{x:y for x,y in v.items()if x not in ['cases','difference_samples']}for k,v in summary.items()},indent=2))
