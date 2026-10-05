"""Stopped game journals only; retain all sixteen scheduled slots and control outcomes."""
import json,math,hashlib,statistics,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/151-sigma-web-port';O=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';reg=json.loads((D/'stageB-preregister.json').read_text());records={};roots={};groups=[];counts={k:{'API_started':0,'API_returned':0,'API_result_discarded':0,'adopted_NN':0,'adopted_backup':0,'last_validated_terminal_noNN':0,'post_public_start_definite':0,'post_cutoff_start_definite':0,'post_cutoff_start_possible':0,'NN_returned_after_public':0,'own_wait_ms':0,'requests':0,'missing_adopted_CP':0,'API_await_ms':[],'adopted_backup_distribution':[],'adopted_NN_distribution':[],'firstCP_ms_from_t0':[],'public_ms_from_t0':[],'ACK_wall_ms':[],'max_nodes':None,'max_depth':None,'guard_refusals':[]} for k in ['candidate','reference']}
for i in range(1,5):
 name=f'port151-stageB-group{i}-r1';v=O/'runs'/name;proc=O/'runs'/(name+'.process.json')
 if not proc.exists():continue # never score a live group
 p=json.loads(proc.read_text());summary=json.loads((v/'summary.json').read_text()) if (v/'summary.json').exists() else {'missing':True}
 control=json.loads((v/'pause-monitor-stop.json').read_text()) if (v/'pause-monitor-stop.json').exists() else {'state':'missing','failure':None}
 groups.append({'run':name,'start':p['start'],'end':p['end'],'exit':p['exit'],'stop_reason':p['stop_reason'],'remaining':p['remaining'],'unknown':p['unknown_adopted'],'summary':summary,'control_state':control['state'],'control_failure':control['failure'],'peak_current_RSS':p['peak_group_plus_runner_RSS']})
 for f in sorted(v.glob('completed-game-*.json')):
  data=json.loads(f.read_text());g=data['game'];plan=next(x for x in reg['games'] if x['id']==g['id']);normal=g['status']=='terminal' and g['winner'] in [0,1,2]
  if normal:score=.5 if g['winner']==0 else int(g['winner']==g['candidate_color']);op=quality=[score,score]
  elif g['status']=='responsibility_loss' and g.get('responsible_engine')=='candidate':op=[0,0];quality=[0,1]
  else:op=quality=[0,1]
  assert g['id'] not in records,'NO_REPLACEMENT';records[g['id']]={**plan,'run':name,'status':g['status'],'winner':g['winner'],'reason':g['reason'],'responsible_engine':g.get('responsible_engine'),'fault':g.get('fault'),'error':g.get('error'),'prefix_length':len(g['initial_prefix']),'public_actions':len(g['actions']),'totalply':g.get('total_ply'),'start_ms':g.get('start_ms'),'end_ms':g.get('end_ms'),'operational':op,'terminal_quality':quality,'normal_terminal':normal,'journal_SHA256':hashlib.sha256(f.read_bytes()).hexdigest()}
  for row in data['rows']:
   engine=row['spec']['engine'];c=counts[engine];diag=row.get('diagnostic') or {};events=diag.get('NN_control_events',[]);c['requests']+=1;c['API_started']+=len(events);c['API_returned']+=sum(e.get('return_ms') is not None for e in events);c['API_result_discarded']+=sum(bool(e.get('result_discarded')) for e in events)
   for e in events:
    if e.get('session_run_start_ms') is not None and e.get('session_run_end_ms') is not None:c['API_await_ms'].append(e['session_run_end_ms']-e['session_run_start_ms'])
   c['own_wait_ms']+=(row.get('own_previous_wait') or {}).get('wait_ms',0)
   for field in ['post_public_NN_definite','post_cutoff_NN_definite','post_cutoff_NN_possible','NN_returned_after_public']:
    target={'post_public_NN_definite':'post_public_start_definite','post_cutoff_NN_definite':'post_cutoff_start_definite','post_cutoff_NN_possible':'post_cutoff_start_possible'}.get(field,field);c[target]+=row.get(field,0)
   c['public_ms_from_t0'].append(row['response'].get('public_elapsed_ms'));c['ACK_wall_ms'].append(row.get('ACK_wall_ms'))
   pub=row.get('adoptedCP');cp=diag.get('validated_cp')
   if pub:
    c['adopted_NN']+=pub['completed_NN'];c['adopted_backup']+=pub['completed_backup'];c['adopted_backup_distribution'].append(pub['completed_backup']);c['adopted_NN_distribution'].append(pub['completed_NN'])
   else:c['missing_adopted_CP']+=1
   if row.get('firstCP'):c['firstCP_ms_from_t0'].append(row['firstCP']['validation_end_ms']-row['worker_clock']['mid_ms']-row['identity']['t0_ms'])
   if cp:
    c['last_validated_terminal_noNN']+=(cp['root_visits'] if engine=='reference' else cp['simulations'])-cp['nn_calls'];c['max_nodes']=max(c['max_nodes'] or 0,cp['nodes']) if 'nodes' in cp else c['max_nodes'];c['max_depth']=max(c['max_depth'] or 0,cp['max_depth']) if 'max_depth' in cp else c['max_depth']
    if cp.get('guard_refusal'):c['guard_refusals'].append(cp['guard_refusal'])
   if row['spec']['turn']==0:
    numeric=diag.get('numeric') or [];n=numeric[0] if numeric else None
    roots[g['id']]={'engine':engine,'side':next(x['fixture']['player'] for x in json.loads((D/'stageB-inputs.json').read_text())['prefixes'] if x.get('accepted') and x['fixture']['id']==g['fixture_id']),'key':row['identity']['key'],'history':row['identity']['history'],'prefix209':row['identity']['prefix'],'legal_prefix':row['identity']['legal_prefix'],'numeric':n,'firstCP':row.get('firstCP'),'adoptedCP':pub,'request_id':row['identity']['request_id']}
slots=[]
for plan in reg['games']:slots.append(records.get(plan['id'],{**plan,'status':'not_started_or_no_journal','winner':None,'reason':'unstarted_or_missing_receipt','operational':[0,1],'terminal_quality':[0,1],'normal_terminal':False}))
bounds=lambda rows,field:[sum(x[field][i] for x in rows)/len(rows) for i in range(2)]
main=bounds(slots,'operational');quality=bounds(slots,'terminal_quality');normal=[x for x in slots if x['normal_terminal']];pairs=[];initial_checks=[]
for i in range(1,9):
 rows=[x for x in slots if x['pair']==i];assert len(rows)==2;pair={'pair':i,'layer':rows[0]['layer_ply'],'colors':rows,'Xi':bounds(rows,'operational'),'terminal_quality_Xi':bounds(rows,'terminal_quality'),'same_side_winner':rows[0]['winner'] if all(x['normal_terminal'] and x['winner'] in [1,2] for x in rows) and rows[0]['winner']==rows[1]['winner'] else None,'both_candidate_win':all(x['operational']==[1,1] and x['normal_terminal'] for x in rows),'both_candidate_loss':all(x['operational']==[0,0] and x['normal_terminal'] for x in rows)};pairs.append(pair)
 if all(x['id'] in roots for x in rows):
  a,b=[roots[x['id']] for x in rows];na,nb=a['numeric'],b['numeric'];checks={k:a[k]==b[k] for k in ['side','key','history','prefix209','legal_prefix']};checks.update(features_exact=bool(na and nb and na['features_bits']==nb['features_bits']),NN_logits_exact=bool(na and nb and na['policy_logits']==nb['policy_logits']),NN_value_exact=bool(na and nb and na['value']==nb['value']));initial_checks.append({'pair':i,'checks':checks,'root_engines':[a['engine'],b['engine']],'all_supported':all(checks.values()),'adopted_CPs':[a['adoptedCP'],b['adoptedCP']],'first_CPs':[a['firstCP'],b['firstCP']]})
for engine,c in counts.items():
 for field in ['API_await_ms','adopted_backup_distribution','adopted_NN_distribution','firstCP_ms_from_t0','public_ms_from_t0','ACK_wall_ms']:
  vs=[x for x in c[field] if x is not None];c[field]={'n':len(vs),'min':min(vs) if vs else None,'median':statistics.median(vs) if vs else None,'mean':statistics.mean(vs) if vs else None,'max':max(vs) if vs else None,'measurement':'API await not kernelCPU; counts not sameCPU/work; missing not zero'}
eps=reg['optional_independent_bounded_pair95_eps'];out={'issue':'quoridor-4lc.151','fixed_denominator':16,'pair_denominator':8,'slots':slots,'pairs':pairs,'operational_identification':main,'terminal_quality_identification':quality,'normal_terminal_complete_only':{'m':len(normal),'mean':sum(x['operational'][0] for x in normal)/len(normal) if normal else None,'selected_auxiliary_not_main':True},'normal_WDL':{'W':sum(x['operational']==[1,1] for x in normal),'D':sum(x['operational']==[.5,.5] for x in normal),'L':sum(x['operational']==[0,0] for x in normal)},'assumption_only_95_reference_interval':[max(0,main[0]-eps),min(1,main[1]+eps)],'eps':eps,'independence_coverage_NOT_proved':True,'layers':{str(ply):bounds([x for x in slots if x['layer_ply']==ply],'operational') for ply in [4,5,12,13]},'groups':groups,'initial_root_checks':initial_checks,'counts':counts,'startup_NN_separate':sum(g['summary'].get('startup_NN',0) for g in groups),'formalNI_or_general_Sigma_equivalence':False,'goal_updated_NNUE_still_active':True,'scientific_results_and_control_success_separate':True}
(D/'stageB-results-current.json').write_text(json.dumps(out,indent=2)+'\n');(D/'stageB-initial-roots-current.json').write_text(json.dumps(roots,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['fixed_denominator','normal_WDL','operational_identification','terminal_quality_identification','startup_NN_separate']}))
