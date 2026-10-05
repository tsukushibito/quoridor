from pathlib import Path
import json,datetime,hashlib,math
R=Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA-INDEPENDENT';U=R/'.artifacts/ai-sigma/resume-20261002/DIAGNOSTIC-ARENA';hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def rows(p):
 if not p.exists():return []
 b=p.read_bytes();hashes[str(p)]=hashlib.sha256(b).hexdigest();return [json.loads(x) for x in b.splitlines() if x]
def close(a,b):assert math.isfinite(a) and math.isfinite(b) and abs(a-b)<1e-5,(a,b)
def clocks(p):
 d=read(p);res={}
 for k in ['page','worker']:
  c=d[k];ss=c['samples'];lo=max(x['remote']-x['end']-.1 for x in ss);hi=min(x['remote']-x['start']+.1 for x in ss);close(lo,c['lo_ms']);close(hi,c['hi_ms']);close((hi-lo)/2+.1,c['error_ms']);assert len(ss)==12 and lo<=hi;res[k]={'samples':len(ss),'lo':lo,'hi':hi,'error':c['error_ms']}
 return res
results=[];detailed=[];allbases=[p.parent for p in U.glob('*/summary.json') if (p.parent/'config.json').exists()]+[O/'critic95-golden-r1',O/'critic95-four-ply-r1']
for base in sorted(allbases):
 s=read(base/'summary.json');cfg=read(base/'config.json');pub=rows(base/'public.jsonl');tr=rows(base/'turns.jsonl');assert len(pub)==len(tr)==s['turns'];assert cfg['seed']==1979 and cfg['affinity']==[2] and cfg['NNthreads']==1 and cfg['clock']=={'T':500,'reserve':89,'commit':9,'cutoff':402,'seal':411}
 stat={e:{'n':0,'accepted':0,'ACK_breach':0,'worker_stop_upper_le500_and_ACK_late':0,'worker_stop_definite_gt500':0,'postpublic_NN':0,'NN':0,'max_public':0,'max_ACK_cause':0,'max_worker_stop_upper':0,'max_delivery_upper':0,'negative_legacyCPU':[],'max_lastAPI_to_worker_stop_upper':0} for e in ['candidate','reference']};samples=[];previous=None;ackzero=0
 for p,t in zip(pub,tr):
  id=p['identity'];r=p['response'];assert id['request_id']==t['request_id']==r['request_id'];close(id['t0_ms'],t['t0_ms']);close(r['stamp_ms'],t['public_stamp_ms']);close(r['stamp_ms']-t['t0_ms'],t['public_elapsed_ms']);close(t['stop_ACK_ms']-t['t0_ms'],t['cause_window_ms']);close(t['stop_ACK_ms']-r['stamp_ms'],t['residual_after_public_ms']);assert (t['cause_window_ms']>500)==t['budget_breach'];assert type(r['accepted'])==bool and type(r['checkpoint'])==bool
  if previous:assert t['t0_ms']>=previous['stop_ACK_ms'];samples.append({'id':id['request_id'],'new_t0_minus_previous_ACK':t['t0_ms']-previous['stop_ACK_ms'],'previous_inspection':previous['shared_diagnostic_inspection_ms']})
  previous=t;z=t['owned_zero'];assert z['handles']==z['activeNN']==z['live_searches']==0 and z['active']==False and not z.get('ownership_error');ackzero+=1
  w=t['worker_clock'];early=z['at_ms']-w['hi_ms'];late=z['at_ms']-w['lo_ms'];delivery=[t['stop_ACK_ms']-late,t['stop_ACK_ms']-early];elapsed=[early-t['t0_ms'],late-t['t0_ms']];assert delivery[1]>=-.5
  spans=t['API_spans'];assert len(spans)==t['NN_completed'];assert all(a['start_early_ms']<=a['start_late_ms'] and a['end_early_ms']<=a['end_late_ms'] and a['api_await_ms']>=0 for a in spans);post=sum(a['start_early_ms']>r['stamp_ms'] for a in spans);assert post==t['post_public_NN_start_definite'];last=max((a['end_early_ms'] for a in spans),default=None);last_late=max((a['end_late_ms'] for a in spans),default=None)
  e=stat[t['engine']];e['n']+=1;e['accepted']+=r['accepted'];e['ACK_breach']+=t['cause_window_ms']>500;e['worker_stop_upper_le500_and_ACK_late']+=t['cause_window_ms']>500 and elapsed[1]<=500;e['worker_stop_definite_gt500']+=elapsed[0]>500;e['postpublic_NN']+=post;e['NN']+=len(spans);e['max_public']=max(e['max_public'],t['public_elapsed_ms']);e['max_ACK_cause']=max(e['max_ACK_cause'],t['cause_window_ms']);e['max_worker_stop_upper']=max(e['max_worker_stop_upper'],elapsed[1]);e['max_delivery_upper']=max(e['max_delivery_upper'],delivery[1]);
  if last is not None:e['max_lastAPI_to_worker_stop_upper']=max(e['max_lastAPI_to_worker_stop_upper'],late-last)
  for field in ['browser_public_ticks','browser_residual_ticks']:
   if t['cpu'][field]<0:e['negative_legacyCPU'].append({'id':id['request_id'],'field':field,'ticks':t['cpu'][field]})
  for key in ['identity_public','identity_residual']:
   if key in t['cpu']:assert all(v['observed_delta_ticks']>=0 for v in t['cpu'][key]['identities']);assert t['cpu'][key]['observed_delta_ticks']==sum(v['observed_delta_ticks'] for v in t['cpu'][key]['identities'])
  item={'id':id['request_id'],'engine':id['engine'],'public_ms':t['public_elapsed_ms'],'ACK_ms':t['cause_window_ms'],'worker_stop_elapsed_interval':elapsed,'stop_generated_to_arena_ACK_interval':delivery,'lastAPI_to_stop_generated_interval':[early-last_late,late-last] if last is not None else None,'postpublic_NN':post,'owned_zero':True,'shared_spans':{k:t.get(k) for k in ['shared_adapter_before_dispatch_ms','shared_final_Judge_clone_UTF8_ms','shared_public_log_ms','shared_diagnostic_inspection_ms']}}
  session=base/('real-'+base.name+'-session1');ackfile=session/('stopACK-'+id['request_id']+'.json')
  if ackfile.exists():a=read(ackfile);close(a['stop']['at_ms'],z['at_ms']);item['stop_generated_to_backend_receive_interval']=[a['node_received_ms']-late,a['node_received_ms']-early];item['backend_receive_to_arena_ACK']=t['stop_ACK_ms']-a['node_received_ms']
  detailed.append(item)
 assert s['public_accepted']==sum(t['accepted'] for t in tr);assert s['budget_breaches']==sum(t['budget_breach'] for t in tr);assert s['NN_hand']==sum(t['NN_completed'] for t in tr)
 games=[]
 for g in s['games']:
  if 'game' not in g:continue
  res=g['result'];games.append({'game':g['game'],'candidateColor':g['candidateColor'],'complete':res['complete'],'score':res.get('score'),'terminal':res.get('terminal'),'kind':res.get('kind'),'category':res.get('category'),'responsible_engine':res.get('responsible_engine'),'reason':res.get('reason')})
 assert s['game_starts']==len(rows(base/'game-start.jsonl'));assert s['W']==sum(g['complete'] and g['score']==1 for g in games);assert s['D']==sum(g['complete'] and g['score']==.5 for g in games);assert s['L']==sum(g['complete'] and g['score']==0 for g in games)
 session=base/('real-'+base.name+'-session1');cs=clocks(session/'browser/clock-start.json');ce=clocks(session/'browser/clock-end.json');assert all(max(cs[k]['lo'],ce[k]['lo'])<=min(cs[k]['hi'],ce[k]['hi']) for k in cs)
 drop=read(session/'model-drop.json');assert drop['handles']==drop['activeNN']==0;controlled=read(session/'controlled-stop.json');assert controlled['controlledPID0']==True
 results.append({'base':str(base.relative_to(R)),'Git':cfg['git'],'stage':cfg['stage'],'startup':s['startup'],'public':len(pub),'ACKzero':ackzero,'engine':stat,'next_t0_checks':len(samples),'next_t0_min_after_previous_ACK':min((x['new_t0_minus_previous_ACK'] for x in samples),default=None),'games':games,'WDL':[s['W'],s['D'],s['L']],'clock_start_end':{'start':cs,'end':ce},'drop0':True,'controlledPID0':True,'forced':controlled['forced'],'primary':s['primary'],'secondary':s['secondary']})
root_input=Path('/workspaces/quoridor/.artifacts/research-team/review-20261002-96/stop-clock-arithmetic.json');root=read(root_input);initial=next(x for x in results if x['base'].endswith('/initial-pair1-r1'));ours={'rows':initial['public'],'ACK_budget_breaches':sum(x['ACK_breach'] for x in initial['engine'].values()),'ACK_late_worker_stop_within500_upper':sum(x['worker_stop_upper_le500_and_ACK_late'] for x in initial['engine'].values())};assert all(root[k]==ours[k] for k in ours)
for ex in root['examples']:
 t=next(x for x in detailed if x['id']==ex['request_id']);close(t['ACK_ms'],ex['ACK_elapsed_ms']);close(t['worker_stop_elapsed_interval'][1],ex['worker_stop_elapsed_upper_ms']);[close(a,b) for a,b in zip(t['stop_generated_to_arena_ACK_interval'],ex['delivery_ms_bounds'])]
owner=[x for x in results if '/DIAGNOSTIC-ARENA/' in x['base']];totals={'public':sum(x['public'] for x in owner),'accepted':sum(sum(e['accepted'] for e in x['engine'].values()) for x in owner),'cause_ACK_breaches':sum(sum(e['ACK_breach'] for e in x['engine'].values()) for x in owner),'handNN':sum(sum(e['NN'] for e in x['engine'].values()) for x in owner),'startupNN':sum(x['startup']['root_NN'] for x in owner),'game_starts':sum(len(x['games']) for x in owner),'natural_goal':sum(g['terminal'] is not None for x in owner for g in x['games']),'fault_termination':sum(g['kind']=='engine_loss' for x in owner for g in x['games'])}
assert not [p for p,h in hashes.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
(O/'arithmetic-inputs.json').write_text(json.dumps(hashes,indent=2)+'\n');(O/'clock-arithmetic-details.json').write_text(json.dumps(detailed,indent=2)+'\n');out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':results,'upstream_totals_separate_Git_not_WDL_pool':totals,'root96_independent_match':ours,'limitations':['ACK wall is not Worker stop time or engine CPU budget','API await not kernel execution time','source timers and current absence do not prove hard deadlines','old live-process counter differences invalid when negative; retained counters lower bound with exited final samples missing']};(O/'clock-arithmetic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'totals':totals,'initial':initial['engine'],'root96match':ours,'input_hash_count':len(hashes)}))
