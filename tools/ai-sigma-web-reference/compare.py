import json,math,hashlib,pathlib,statistics
ROOT=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-WEB-REFERENCE'
fixtures=json.loads((ROOT/'.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json').read_text())['fixtures'];refs=json.loads((ROOT/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json').read_text());actual=json.loads((RUN/'numeric.outputs.json').read_text());byid={x['id']:x for x in actual};failures=[];maxabs=0;elements=0;priors=0
for f,r in zip(fixtures,refs):
 a=byid[f['id']]
 expected_indices=f['canonical_legal_indices']
 if r['canonical_legal_priors'] is None:
  mx=max([r['policy_logits'][i] for i in expected_indices],default=0);ee=[math.exp(r['policy_logits'][i]-mx)for i in expected_indices];sm=sum(ee);expected_priors=[v/sm for v in ee]
 else:expected_priors=[x['prior']for x in r['canonical_legal_priors']]
 if a.get('error'):failures.append({'id':f['id'],'error':a['error']});continue
 for condition,label in [(len(a['features'])==648,'input_shape'),(a['features']==f['raw_features_float32'],'features_exact'),(a['shapes']==[[1,136],[1,1]],'output_shape'),(len(a['policy_logits'])==136,'logits_shape'),(math.isfinite(a['value']) and abs(a['value'])<=1.0001,'value_range'),(a['indices']==expected_indices,'p2_indices')]:
  if not condition:failures.append({'id':f['id'],'gate':label})
 for kind,xs,ys in [('nn',a['policy_logits']+[a['value']],r['policy_logits']+[r['value']]),('prior',a['priors'],expected_priors)]:
  if len(xs)!=len(ys):failures.append({'id':f['id'],'gate':kind+'_length'});continue
  for i,(x,y)in enumerate(zip(xs,ys)):
   err=abs(x-y);maxabs=max(maxabs,err)
   if kind=='nn':elements+=1
   else:priors+=1
   if not math.isfinite(x)or err>1e-4+1e-4*abs(y):failures.append({'id':f['id'],'kind':kind,'index':i,'got':x,'ref':y,'error':err})
def dist(x):
 x=sorted(x)
 return {'n':len(x),'min':x[0],'p50':statistics.median(x),'p95':x[math.ceil(.95*len(x))-1],'max':x[-1]}if x else None
rows=json.loads((RUN/'timing.json').read_text());timing=[]
for id in ['initial-p1','asym-hv-p2','straight-jump-p2']:
 for T in [100,500,1000]:
  rr=[x for x in rows if x['id']==id and x['T_ms']==T and x['phase']=='sample'];timing.append({'id':id,'T_ms':T,'samples':len(rr),'accepted':sum(bool(x['accepted'])for x in rr),'timeouts':sum(bool(x['timeout'])for x in rr),'errors':[x.get('error')for x in rr if x.get('error')],'elapsed_ms':dist([x['elapsed_ms']for x in rr]),'overshoot_ms':dist([x['overshoot_ms']for x in rr]),'finish_ms':dist([x['time']['finish']-x['time']['t0']for x in rr if x.get('time')]),'adapter_queue_ms':dist([x['time']['workerStart']-x['time']['t0']for x in rr if x.get('time')]),'transport_ms':dist([x['transport_ms']for x in rr if x['transport_ms']is not None]),'root_ms':dist([x['time']['rootFinished']-x['time']['t0']for x in rr if x.get('time',{}).get('rootFinished')]),'NN_ms':dist([v['end']-v['start']for x in rr for v in x.get('stats',{}).get('nn',[])]),'step_ms':dist([v for x in rr for v in x.get('stats',{}).get('steps',[])]),'nn_calls':[x.get('stats',{}).get('nnCalls',0)for x in rr],'root_visits':[x.get('stats',{}).get('rootVisits',0)for x in rr]})
terminal=json.loads((RUN/'terminal.json').read_text());cancel=json.loads((RUN/'cancel.json').read_text());fallback=json.loads((RUN/'fallback.json').read_text());gate={'atol':1e-4,'rtol':1e-4,'cases':len(actual),'NN_elements':elements,'prior_elements':priors,'terminal_prior_expectation':'diagnostic raw-mask softmax derived from fixed logits/fixture indices; original ORT reference has null terminal priors','features':len(actual)*648,'max_absolute_error':maxabs,'failures':failures,'numeric_pass':len(actual)==28 and elements==3836 and not failures,'terminal_count':len(terminal),'terminal_NN_zero':all(x['stats']['nnCalls']==0 for x in terminal),'terminal_results':[{'id':x['id'],'terminal':x['terminal'],'nnCalls':x['stats']['nnCalls']}for x in terminal],'fallback_model_not_ready_error':fallback.get('error')=='model_not_ready'and fallback.get('fallback')==0,'cancel_old_rejected':cancel['previous']['rejected'],'cancel_during_NN':cancel['cancelDuringNN'],'new_queue_wait_ms':cancel['newQueueWait_ms'],'new_error':cancel['next'].get('error'),'timing':timing}
(RUN/'gate.json').write_text(json.dumps(gate,indent=2)+'\n');print(json.dumps({k:v for k,v in gate.items()if k!='timing'}));assert gate['numeric_pass'];assert gate['terminal_NN_zero'];assert gate['fallback_model_not_ready_error'];assert gate['cancel_old_rejected']
