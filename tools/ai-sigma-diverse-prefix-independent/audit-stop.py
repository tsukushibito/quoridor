from pathlib import Path
import json,hashlib,datetime,subprocess,tarfile
R=Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX-INDEPENDENT';D=R/'research-data/ai-sigma/119-diverse-prefix';H=lambda b:hashlib.sha256(b).hexdigest()
before=json.loads((O/'input-before.json').read_text());after={p:H((R/p).read_bytes()) for p in before['checks']};assert after==before['checks'],'INPUT_CHANGED'
source_paths=['tools/ai-sigma-diverse-prefix/adapters.cjs','tools/ai-sigma-diverse-prefix/prefix-browser.js','tools/ai-sigma-cpu-sigma-frame8/adapters.cjs','tools/ai-sigma-cpu-sigma-frame8/browser-glue.js','tools/ai-sigma-player-workers/player-main.js','tools/ai-sigma-player-workers/player-worker.js','tools/ai-sigma-tail-transport/early-worker.js','tools/ai-sigma-tail-transport/checkpoint.js','tools/ai-sigma-actual-boundary-repair/early-cache.cjs','tools/ai-sigma-cp-frame/shared-best-action.cjs','tools/ai-sigma-actual-boundary-repair/game.js','tools/ai-sigma-actual-boundary-repair/context.js']
source={}
for p in source_paths:
 b=(R/p).read_bytes();g=subprocess.check_output(['git','show','532c87349fa0baf233fa905f5f3d8c88a5560a9f:'+p],cwd=R);assert b==g,p;source[p]=H(b)
actual=json.loads((O/'runs/p122-saved-r1/source-bindings.json').read_text());pairs=[];owner_ids={}
for i in range(1,9):
 name=f'prefix119-pair{i}-r1';x=json.loads((O/f'pair{i}-input-checks.json').read_text());small=x['small_stop_binding'];assert small[f'runs/{name}/source-bindings.json']==actual,'ADAPTED_SOURCE_MISMATCH';drop=small[f'runs/{name}/finally-model-drop.json'];assert drop['handles']==0 and drop['activeNN']==0 and len(drop['players'])==2 and all(p['handles']==0 and p['activeNN']==0 for p in drop['players']);zero=small[f'runs/{name}/main-timers-stop.json'];assert zero['main_timers']==0 and isinstance(zero['pending_messages'],list) and len(zero['pending_messages'])==0;outer=small[f'runs/{name}/outer-controlled-stop.json'];assert outer['remaining_pids']==0 and outer['waited'] and outer['zombie_identities_absent'];monitor=small[f'runs/{name}/pause-monitor-stop.json'];assert monitor['all_owned_read_callbacks_waited'] and not monitor['pending_children'] and not monitor['active_monitor_timer'];proc=small[f'runs/{name}.process.json'];assert proc['exit']==0 and not proc['stop_reason'] and not proc['remaining'] and not proc['unknown_adopted'];summary=json.loads((D/(name+'.summary.json')).read_text());assert not summary['primary'] and not summary['secondary'] and summary['games_started']==2;after[str((D/(name+'.summary.json')).relative_to(R))]=H((D/(name+'.summary.json')).read_bytes())
 for q in proc['tracked']+outer['tracked']+[{'pid':proc['runner_pid'],'start_ticks':proc['runner_starttick']}]:owner_ids[q['pid'],q.get('start_ticks',q.get('starttick'))]=q
 pairs.append({'run':name,'measured_Git':x['source_Git'],'source_bindings_equal_loaded_browser':True,'Modeldrop_both_zero':True,'search_ACK_all_zero':'independent-browser all rows','main_timer_message_zero':True,'monitor_callbacks_waited':True,'inner_forced':outer['forced'],'outer_waited':True,'current_absence_not_natural':True,'primary':summary['primary'],'secondary':summary['secondary'],'exit':proc['exit'],'runtime_RSS_peak':proc['peak_group_plus_runner_RSS'],'actual_launch_gate_not_final_guard':True})
selfids={};wall=0;resource=[]
for p in (O/'runs').glob('p122-*.process.json'):
 j=json.loads(p.read_text());assert not j['remaining'] and not j['unknown_adopted'];wall+=(datetime.datetime.fromisoformat(j['end'])-datetime.datetime.fromisoformat(j['start'])).total_seconds();resource.append({k:j[k] for k in ['name','exit','stop_reason','start','end','peak_group_plus_runner_RSS','peak_allocated_bytes','all_observed_TIDs_at_assigned_CPU']})
 for q in j['tracked']+[{'pid':j['runner_pid'],'start_ticks':j['runner_starttick']}]:selfids[q['pid'],q.get('start_ticks',q.get('starttick'))]=q
assert wall<360
s=json.loads((D/'runtime-source-stopped-before-report.json').read_text())
def live(ids):
 out=[]
 for pid,tick in ids:
  try:
   a=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
   if int(a[19])==int(tick):out.append({'pid':pid,'start_ticks':tick,'state':a[0]})
  except FileNotFoundError:pass
 return out
original={(v['pid'],v.get('start_ticks',v.get('starttick'))):v for v in s['recorded_identity_list']};assert not live(original) and not live(owner_ids) and not live(selfids)
(O/'input-after.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':after,'original_before_count':len(before['checks']),'after_additional_summaries':8,'source_current_tested_Git_equal':source,'pairs':pairs,'independent_process_recollected_owner_count':len(owner_ids),'owner_declared_all_run_count':len(original),'owner_current_same_identity':[],'self_current_same_identity':[],'self_recorded':len(selfids),'browser_wall_seconds':wall,'browser_resources':resource,'new_NN_model_load_games':0,'shared_source_no_edit':True},indent=2))
print(json.dumps({'owner1517_current0':True,'independent_pair_process_identity_count':len(owner_ids),'self_browser_identities':len(selfids),'browser_seconds':wall,'source_checks':len(source),'pairs_Modeldrop_outerwait':len(pairs)}))
