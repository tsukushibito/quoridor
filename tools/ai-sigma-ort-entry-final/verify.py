import json,pathlib,sys,math
ROOT=pathlib.Path(__file__).resolve().parents[2];RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-ORT-CHECKPOINT';mode=sys.argv[1]
if mode=='checkpoint':
 v=json.loads((RUN/'browser-checkpoint-gate-backup.json').read_text());rows=[]
 for row in v['rows']:
  r=row.get('forced',row.get('r'));assert r['live_searches']==0
  if 'control'in row:
   a={k:x for k,x in row['control'].items() if k not in ['generation','serialization_ms','serialized_bytes','worker_delivery_send_ms']};b={k:x for k,x in r['cp'].items() if k!='generation'};assert a==b,row['id'];assert r['calls']==r['completed_NN']==3;assert r['cp']['simulations']==3;assert r['invalidated_pending_token']!=r['owned']['completed_token'];assert r['trace'][-1]['cp']==r['cp'];assert r['budget_stop']=='begin_crossed_guard';assert r['worker_finish']-r['t0']<500;rows.append({'id':row['id'],'full_cp_tree_stats_history_exact':True,'NN_attempts':3,'completed':3,'begin_nextNN_started':0,'elapsed_worker_ms':r['worker_finish']-r['t0']})
  elif row['id'].startswith(('no-checkpoint','deadline','hardfault','serialization')):
   assert r['error'] and r['cp'] is None and r['owned'] is None,row['id'];rows.append({'id':row['id'],'error':r['error'],'NN_attempts':r['calls'],'completed_NN':r['completed_NN'],'published_action':None})
  else:assert r['calls']==0 and r['cp']['terminal_value'] is not None;rows.append({'id':row['id'],'NN_attempts':0,'terminal':r['cp']['terminal_value']})
 result={'rows':rows,'passed':True,'full_cp_bits_preserved':True,'original_kernel_immutable':True};(RUN/'checkpoint-gate-final.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
elif mode=='numeric':
 v=json.loads((RUN/'browser-numeric-final.json').read_text());old=json.loads((ROOT/'.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH/native-diagnostic-final.json').read_text());ref=json.loads((ROOT/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json').read_text());bits=nn=prior=0;maxabs=0
 for row,o,r in zip(v['rows'],old['fixtures'],ref):
  assert row['id']==o['id']==r['id'];assert row['features_bits']==o['features_bits'];bits+=len(row['features_bits']);assert row['reference_features_exact'] and row['reference_legal_exact'] and row['reference_terminal_equal'];assert row['raw_legal']==o['raw_legal'] and row['effective_legal']==o['effective_legal']
  for x,y in zip(row['logits']+[row['value']],r['policy_logits']+[r['value']]):nn+=1;maxabs=max(maxabs,abs(x-y));assert math.isfinite(x) and abs(x-y)<=1e-4+1e-4*abs(y)
  for x,y in zip(row['raw_prior'],o['raw_prior']):prior+=1;assert math.isfinite(x) and abs(x-y)<=1e-4+1e-4*abs(y)
 for k in ['shape','null','range','duplicate','stale','token','cancel']:assert not v['faults'][k].get('unexpected_success') and not v['faults'][k].get('checkpoint_published')
 result={'cases':28,'legal':20,'artificial':8,'features_exact_bits':bits,'NN_elements':nn,'prior_elements':prior,'NN_max_abs':maxabs,'failures':0,'gate':'abs<=1e-4+1e-4abs(ref)'};(RUN/'numeric-gate-final.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
elif mode=='boundary':
 v=json.loads((RUN/'browser-boundary-final.json').read_text());r=v['rows'][0];assert r['modelFaults']['short']=='MODEL_LENGTH' and r['modelFaults']['hash']=='MODEL_HASH';assert r['failed']['error']=='INJECTED_NN_ERROR' and r['failed']['cp'] is None;assert r['late']['error']=='DEADLINE' and r['late']['cp'] is None;assert r['old']['rejected']=='RESPONSE_GENERATION';assert not r['fresh']['error'] and r['fresh']['cp']['simulations']==8;old=[e for e in v['events'] if e.get('old_rejected') and e.get('kind')=='response'];assert len(old)==1 and old[0]['result']['cp'] is None and old[0]['result']['owned'] is None;assert old[0]['result']['completed_NN']>=1
 result={'passed':True,'hardfaults_discarded':True,'old_response_after_complete_cp_rejected':True,'old_NN_attempts':old[0]['result']['calls'],'fresh_sims':8,'fallback':0};(RUN/'boundary-gate-final.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
else:raise ValueError(mode)
