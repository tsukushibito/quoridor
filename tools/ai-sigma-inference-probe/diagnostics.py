import pathlib,json,math,hashlib
r=pathlib.Path('.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE');fixtures=json.loads(pathlib.Path('.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json').read_text())['fixtures'];ref=json.loads((r/'ort-a.outputs.json').read_text());out={}
for candidate in ['native','wasm']:
 vals=json.loads((r/(candidate+'.outputs.json')).read_text());cases=[]
 for f,a,b in zip(fixtures,ref,vals):
  assert f['id']==a['id']==b['id'];actions=f['legal_actions'];perm=f['P2_permutation136'];idx=[perm[x['sigma136']] if f['board']['turn']==1 else x['sigma136'] for x in actions];assert idx==f['canonical_legal_indices'];assert len({x['rust209'] for x in actions})==len(actions)
  mapped=[];prior_error=None
  if f['terminal']['effective_result']=='ongoing':
   def softmax(v):
    z=[v[i] for i in idx];m=max(z);e=[math.exp(x-m) for x in z];s=sum(e);return [x/s for x in e]
   p=softmax(a['policy_logits']);q=softmax(b['policy_logits']);prior_error=max(abs(x-y) for x,y in zip(p,q));assert all(math.isfinite(x) and x>=0 for x in q)
   mapped=[{'sigma136':x['sigma136'],'canonical136':i,'rust209':x['rust209'],'reference_prior':u,'candidate_prior':v} for x,i,u,v in zip(actions,idx,p,q)]
  cases.append({'id':f['id'],'classification':f['classification'],'turn':f['board']['turn'],'effective_result':f['terminal']['effective_result'],'terminal_nn_for_numeric_diagnostic_only':f['terminal']['effective_result']!='ongoing','max_prior_abs':prior_error,'mapped_legal_priors':mapped})
 out[candidate]={'cases':cases,'max_prior_abs':max(x['max_prior_abs'] or 0 for x in cases),'diagnostic_only_no_new_gate':True,'Rust_feature_generation_executed':False}
(r/'prior-action-diagnostics.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v['max_prior_abs'] for k,v in out.items()})
