"""Post-group descriptive aggregation; full64 bounds, no stopping based on observed score."""
import json,math,hashlib,tarfile,datetime,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[2];data=root/'research-data/ai-sigma/frame10-baseline-gap';out=root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP';pr=json.loads((data/'preregister.json').read_text());inputs=json.loads((data/'inputs.json').read_text());valid={x['pair']:x for x in inputs['prefixes'] if x['accepted']}
observed={};requests=[];jobs=[];raw_bindings=[]
for man in sorted(data.glob('gap149-group*.manifest.json')):
 m=json.loads(man.read_text());archive=Path(m['archive']);assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['archive_SHA256']
 with tarfile.open(archive) as t:
  names=t.getnames();name=next((n for n in names if n.endswith('/browser-result.json')),None) or next((n for n in names if n.endswith('/partial-browser-result.json')),None)
  if not name:
   fail_name=next((n for n in names if n.endswith('/failure-attempts.json')),None)
   if not fail_name:continue
   f=json.loads(t.extractfile(fail_name).read());r={'games':[dict(g,status='unknown_start_result',reason='outer_Node_OOM',winner=None,initial_prefix=valid[g['pair']]['fixture']['legal_prefix'],actions=[],turn_indices=[]) for g in f['planned_games']],'rows':[],'started_games':None};b=t.extractfile(fail_name).read();name=fail_name
  else:b=t.extractfile(name).read();r=json.loads(b)
  journals=[json.loads(t.extractfile(n).read()) for n in names if '/completed-game-' in n and n.endswith('.json')]
  if journals:r['rows']=[row for j in journals for row in j['rows']]
  sum_name=next((n for n in names if n.endswith('/summary.json')),None);summary=json.loads(t.extractfile(sum_name).read()) if sum_name else {}
  raw_bindings.append({'run':m['run'],'archive_SHA256':m['archive_SHA256'],'member':name,'member_SHA256':hashlib.sha256(b).hexdigest()})
  for g in r.get('games',[]):
   assert g['id'] not in observed,'STARTED_GAME_DUPLICATE'
   observed[g['id']]={'game':g,'run':m['run'],'postgame_helper_primary':summary.get('primary'),'postgame_helper_secondary':summary.get('secondary')}
  for row in r.get('rows',[]):row['_run']=m['run'];requests.append(row)
  jobs.append({'run':m['run'],'startup_NN':summary.get('startup_NN',0) if sum_name else (6 if any(n.endswith('/startup.json') for n in names) else 0),'started_games':r.get('started_games',0),'publics':len(r.get('rows',[])),'primary':summary.get('primary'),'secondary':summary.get('secondary')})
games=[]
for plan in pr['planned_games']:
 ob=observed.get(plan['id']);g=ob['game'] if ob else None;status='unstarted' if plan['pair'] in valid else 'ungenerated';op=[0,1];quality=[0,1];score=None;category=status
 if g:
  status=g['status'];engine=g.get('responsible_engine');
  if status=='unknown_start_result':category='outer_OOM_unknown_start_and_result'
  if status=='terminal':
   score=.5 if g['winner']==0 else int(g['winner']==plan['candidate_color']);op=[score,score];quality=op[:];category='goal' if g['winner'] else 'draw'
  elif status=='responsibility_loss' and engine=='candidate':score=0;op=[0,0];category='candidate_responsibility_faultloss'
  elif status=='responsibility_loss' and engine=='reference':category='reference_responsibility_fault_unknown'
  else:category='outer_OOM_unknown_start_and_result' if status=='unknown_start_result' else 'unfinished_shared_or_reference_NN_unknown'
  # Independent post-game numeric/helper failure is infrastructure, not a strength win/loss.
  if ob['postgame_helper_primary'] or ob['postgame_helper_secondary']:
   op=[0,1];quality=[0,1];score=None;category='postgame_infrastructure_unscored'
  if g['initial_prefix']!=valid[plan['pair']]['fixture']['legal_prefix']:
   op=[0,1];quality=[0,1];score=None;category='input_binding_invalid_unknown'
 game_rows=[r for r in requests if r['spec'].get('game_id')==plan['id']]
 games.append({**plan,'run':ob['run'] if ob else None,'status':status,'category':category,'operational_interval':op,'terminal_quality_interval':quality,'normal_terminal_score':score if category in ['goal','draw'] else None,'winner':g.get('winner') if g else None,'reason':g.get('reason') if g else None,'new_public_plies':len(g['actions']) if g else 0,'initial_prefix_length':len(g['initial_prefix']) if g else None,'total_ply':g.get('total_ply') if g else None,'start_ms':g.get('start_ms') if g else None,'end_ms':g.get('end_ms') if g else None,'public_count':len(game_rows),'hand_API_started':sum((r.get('diagnostic') or {}).get('control_final',{}).get('NN_started',0) for r in game_rows),'hand_API_returned':sum((r.get('diagnostic') or {}).get('control_final',{}).get('NN_returned',0) for r in game_rows),'adopted_completed_backup':sum((r.get('adoptedCP') or {}).get('completed_backup',0) for r in game_rows),'adopted_NN':sum((r.get('adoptedCP') or {}).get('completed_NN',0) for r in game_rows),'typed_flags':[r['response'].get('causes') for r in game_rows if r['response']['classification']!='completed_legal']})
pairs=[]
for pair in range(1,33):
 rows=[g for g in games if g['pair']==pair];assert len(rows)==2
 op=[sum(g['operational_interval'][i] for g in rows)/2 for i in [0,1]];q=[sum(g['terminal_quality_interval'][i] for g in rows)/2 for i in [0,1]]
 scores=[g['normal_terminal_score'] for g in rows];win=[g['winner'] for g in rows]
 pattern='unknown'
 if all(x is not None for x in scores):
  if scores==[1,1]:pattern='candidate_both_colors_win'
  elif scores==[0,0]:pattern='candidate_both_colors_loss'
  elif scores==[.5,.5]:pattern='both_draw'
  elif sorted(scores)==[0,1]:pattern='same_physical_side_winner_one_each_AI'
  else:pattern='draw_plus_decisive'
 pairs.append({'pair':pair,'layer_ply':rows[0]['layer_ply'],'operational_Xi_interval':op,'terminal_quality_Xi_interval':q,'normal_scores':scores,'physical_side_winners':win,'pattern':pattern,'game_ids':[g['id'] for g in rows]})
def bound(rows,key,den):return [sum(x[key][i] for x in rows)/den for i in [0,1]]
op=bound(games,'operational_interval',64);q=bound(games,'terminal_quality_interval',64);eps=math.sqrt(math.log(40)/(2*32));normal=[g['normal_terminal_score'] for g in games if g['normal_terminal_score'] is not None]
roots=[]
for pair in range(1,33):
 rs=[r for r in requests if r['spec'].get('turn')==0 and any(g['id']==r['spec'].get('game_id') and g['pair']==pair for g in games)];rs=sorted(rs,key=lambda r:r['spec']['engine']);row={'pair':pair,'observed':len(rs),'same_input_NN_supported':False}
 if len(rs)==2:
  a,b=rs;na=(a.get('diagnostic') or {}).get('numeric',[]);nb=(b.get('diagnostic') or {}).get('numeric',[]);sameidentity=all(a['identity'][k]==b['identity'][k] for k in ['key','history','legal_prefix','model','schema']);row.update(identity_exact=sameidentity,engines=[r['spec']['engine'] for r in rs],firstCP=[r.get('firstCP') for r in rs],adoptedCP=[r.get('adoptedCP') for r in rs],self_wait=[r.get('own_previous_wait') for r in rs],opposite_previous=[r.get('opposite_previous') for r in rs])
  if na and nb:
   x,y=na[0],nb[0];features=x['features_bits']==y['features_bits'];xx=[*x['policy_logits'],x['value']];yy=[*y['policy_logits'],y['value']];diff=[abs(u-v) for u,v in zip(xx,yy)];tol=len(xx)==len(yy)==137 and all(d<=1e-4+1e-4*abs(v) for d,v in zip(diff,yy));bits=xx==yy
   row.update(features_exact=features,NN_shape=[len(xx),len(yy)],NN_bit_equal=bits,NN_within_tolerance=tol,max_abs_difference=max(diff),same_input_NN_supported=sameidentity and features and tol,new_fixedgolden=False)
 roots.append(row)
def stats(values):
 values=[x for x in values if isinstance(x,(float,int)) and math.isfinite(x)];return {'n':len(values),'min':min(values) if values else None,'median':statistics.median(values) if values else None,'max':max(values) if values else None,'sum':sum(values) if values else None}
engine_cost={}
for engine in ['candidate','reference']:
 rs=[r for r in requests if r['spec']['engine']==engine];pubs=[p for r in rs for p in (r.get('diagnostic') or {}).get('sab_publications',[])];ev=[e for r in rs for e in (r.get('diagnostic') or {}).get('NN_control_events',[])]
 engine_cost[engine]={'requests':len(rs),'hand_API_started':sum((r.get('diagnostic') or {}).get('control_final',{}).get('NN_started',0) for r in rs),'hand_API_returned':sum((r.get('diagnostic') or {}).get('control_final',{}).get('NN_returned',0) for r in rs),'saved_API_events':len(ev),'old_return_discarded':sum(bool(e.get('result_discarded')) for e in ev),'adopted_backup':stats([(r.get('adoptedCP') or {}).get('completed_backup') for r in rs]),'adopted_NN':stats([(r.get('adoptedCP') or {}).get('completed_NN') for r in rs]),'firstCP_backup':stats([(r.get('firstCP') or {}).get('completed_backup') for r in rs]),'public_wall_ms':stats([r['response']['public_elapsed_ms'] for r in rs]),'API_await_ms':stats([e['return_ms']-e['start_ms'] for e in ev]),'self_wait_ms':stats([r['own_previous_wait']['wait_ms'] for r in rs]),'ACK_wall_ms':stats([r.get('ACK_wall_ms') for r in rs]),'residual_overlap_wall_ms':stats([(r.get('opposite_previous') or {}).get('residual_overlap_wall_ms') for r in rs]),'terminal_noNN_direct_count':None,'completed_without_NN_derived':stats([(r.get('adoptedCP') or {}).get('completed_backup',0)-(r.get('adoptedCP') or {}).get('completed_NN',0) for r in rs if r.get('adoptedCP')]),'terminal_caps_deep_states_not_separated':True,'CPU_kernel_NN_time_not_measured':True,'after_public_new_API_definite':sum(r.get('post_public_NN_definite',0) for r in rs),'public_immutable_all':all(r.get('postpublic_immutable') for r in rs)}
categories={k:sum(g['category']==k for g in games) for k in sorted(set(g['category'] for g in games))};reference=[max(0,op[0]-eps),min(1,op[1]+eps)];quality_reference=[max(0,q[0]-eps),min(1,q[1]+eps)]
result={'issue':'quoridor-4lc.149','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'planned_games':64,'planned_pairs':32,'started_games':sum(g['game']['status']!='unknown_start_result' for g in observed.values()),'possibly_started_result_missing':sum(g['game']['status']=='unknown_start_result' for g in observed.values()),'assigned_attempted_games':len(observed),'categories':categories,'operational_mean_interval':op,'terminal_quality_all64_interval':q,'reference_Hoeffding_eps':eps,'operational_assumption_only_95_interval':reference,'terminal_quality_assumption_only_95_interval':quality_reference,'interval_assumptions':'independent bounded32pairs added assumption; fixedPRNG/sharedstates/drift independence and coverage unproved; not64independent games','complete_only_auxiliary':{'m':len(normal),'mean':sum(normal)/len(normal) if normal else None,'selection_limit':'normal terminal subset; never replaces64'},'strata':{str(p):{'planned_games':16,'operational':bound([g for g in games if g['layer_ply']==p],'operational_interval',16),'terminal_quality':bound([g for g in games if g['layer_ply']==p],'terminal_quality_interval',16)} for p in [4,5,12,13]},'games':games,'pairs':pairs,'first_roots_sameinput':roots,'engine_cost':engine_cost,'startup_NN':sum(x['startup_NN'] for x in jobs),'sessions':2*len(jobs),'jobs':jobs,'raw_bindings':raw_bindings,'old_WDL_mixed':False,'policy_changed':False,'NI_or_Sigma_equivalence':False,'interim_not_used_for_stop':True}
(data/'aggregate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['started_games','categories','operational_mean_interval','terminal_quality_all64_interval','startup_NN']}))
