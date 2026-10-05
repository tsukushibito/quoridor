import json,pathlib,hashlib
ROOT=pathlib.Path('../..').resolve();RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH';mode=__import__('sys').argv[1]
if mode=='numeric':
 v=json.loads((RUN/'browser-numeric-frozen-final.json').read_text());old=json.loads((ROOT/'.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH/native-diagnostic-final.json').read_text());native=json.loads((RUN/'native-numeric.json').read_text());ref=json.loads((ROOT/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json').read_text());fail=[];nn=pc=bits=0;maxabs=0
 for row,o,n,r in zip(v['rows'],old['fixtures'],native['fixtures'],ref):
  assert row['id']==o['id']==n['id']==r['id'];bits+=len(row['features_bits']);assert row['features_bits']==o['features_bits']==n['features_bits'];assert row['reference_features_exact'] and row['reference_legal_exact'] and row['reference_terminal_equal'];assert row['raw_legal']==o['raw_legal'] and row['effective_legal']==o['effective_legal']
  for x,y in zip(row['logits']+[row['value']],r['policy_logits']+[r['value']]):
   nn+=1;maxabs=max(maxabs,abs(x-y))
   if abs(x-y)>1e-4+1e-4*abs(y):fail.append([row['id'],'nn',x,y])
  assert len(row['raw_prior'])==len(o['raw_prior'])
  for x,y in zip(row['raw_prior'],o['raw_prior']):
   pc+=1
   if abs(x-y)>1e-4+1e-4*abs(y):fail.append([row['id'],'prior',x,y])
 for k in ['shape','null','range','duplicate','stale','token','cancel']:
  z=v['faults'][k];assert not z.get('unexpected_success') and not z.get('checkpoint_published'),(k,z)
 result={'feature_bits_exact':bits,'NN_elements':nn,'prior_elements':pc,'NN_max_abs':maxabs,'failures':fail,'reference_State_exact_cases':len(v['rows']),'legal_cases':20,'artificial_numeric_diagnostic_cases':8,'faults':{k:v['faults'][k] for k in ['shape','null','range','duplicate','stale','token','cancel']},'gate':'abs<=1e-4+1e-4*abs(ref)'};assert not fail
 (RUN/'numeric-gate-final.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
elif mode=='fixed':
 v=json.loads((RUN/'browser-fixed-frozen-final.json').read_text());rows=[];forks=[]
 for a,b in zip(v['rows'][::2],v['rows'][1::2]):
  assert not a['error'] and not b['error'],(a['id'],a['error'],b['error']);x,y=a['cp'],b['cp'];assert x['terminal_value']==y['terminal_value'];assert x['simulations']==y['simulations'];assert all(x[k]==y[k] for k in ['nodes','arena_bytes','cap','max_depth']);assert x['policy_fallbacks']==y['policy_fallbacks']==x['value_fallbacks']==y['value_fallbacks']==0;assert [e[0] for e in x['root_edges']]==[e[0] for e in y['root_edges']]
  exact=x['action']==y['action'] and [e[2] for e in x['root_edges']]==[e[2] for e in y['root_edges']];r={'id':a['id'],'sims':a['sims'],'max_nodes':a['max_nodes'],'max_depth':a['max_depth'],'actionA':x['action'],'actionB':y['action'],'action_visits_exact':exact,'NN_A':a['calls'],'NN_B':b['calls'],'prior_max_abs':max([abs(e[1]-f[1]) for e,f in zip(x['root_edges'],y['root_edges'])]+[0]),'value_sum_max_abs':max([abs(e[3]-f[3]) for e,f in zip(x['root_edges'],y['root_edges'])]+[0])};rows.append(r)
  if not exact:forks.append(r)
  if x['terminal_value'] is not None:assert a['calls']==b['calls']==0
 (RUN/'fixed-gate-final.json').write_text(json.dumps({'rows':rows,'runs':len(v['rows']),'forks':forks,'errors':0,'fallbacks':0,'structural_stats_exact':True},indent=2));print(json.dumps({'runs':len(v['rows']),'forks':forks,'errors':0,'fallbacks':0}))
elif mode=='boundary':
 v=json.loads((RUN/'browser-boundary-counters-final.json').read_text());r=v['rows'][0];assert r['modelFaults']['short']=='MODEL_LENGTH' and r['modelFaults']['hash']=='MODEL_HASH';assert r['failed']['error']=='INJECTED_NN_ERROR' and r['failed']['cp'] is None;assert r['late']['error']=='DEADLINE' and r['late']['cp'] is None and r['late']['calls']==1;assert r['old']['rejected']=='RESPONSE_GENERATION';assert not r['fresh']['error'] and r['fresh']['cp']['simulations']==8;old=[e for e in v['events'] if e.get('old_rejected') and e.get('kind')=='response'];assert len(old)==1 and old[0]['result']['cp'] is None;result={'passed':True,'late_attempts':r['late']['calls'],'late_completed':0,'late_elapsed_worker_ms':r['late']['worker_finish']-r['late']['t0'],'old_responses_rejected':len(old),'fresh_sims':8,'fallback':0,'one_sync_NN_nonpreemptible':True};(RUN/'boundary-gate-final.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
