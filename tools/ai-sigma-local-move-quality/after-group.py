"""Preserve a completed fixed group after physical heavy recovery; no new search."""
from pathlib import Path
import json,sys,hashlib,tarfile,datetime
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/LOCAL-MOVE-QUALITY';DATA=ROOT/'research-data/ai-sigma/134-local-move-quality'
name=sys.argv[1];run=OUT/'runs'/name
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
process=read(OUT/'runs'/(name+'.process.json'));raw=read(run/'browser-result.json');summary=read(run/'summary.json');assert not process['remaining'] and not process['unknown_adopted']
ids={}
for x in process['tracked']+[{'pid':process['runner_pid'],'start_ticks':process['runner_starttick']}]:ids[(x['pid'],x['start_ticks'])]={'pid':x['pid'],'start_ticks':x['start_ticks']}
live=[]
for key,identity in ids.items():
 try:fields=(Path('/proc')/str(identity['pid'])/'stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(fields[19])==identity['start_ticks']:live.append(identity)
assert not live,'CURRENT_OWNED_IDENTITY'
drop=read(run/'finally-model-drop.json');timers=read(run/'main-timers-stop.json');monitor=read(run/'pause-monitor-stop.json');inner=read(run/'outer-controlled-stop.json')
assert drop['handles']==drop['activeNN']==0 and len(drop['players'])==2
assert timers['main_timers']==0 and not timers['pending_messages'] and monitor['all_owned_read_callbacks_waited'] and not monitor['active_monitor_timer']
assert inner['remaining_pids']==0
stop={'issue':'quoridor-4lc.134','run':name,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_runtime_stopped':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'identities':list(ids.values()),'current_same_identity':live,'remaining_unknown':0,'Model2_drop':drop,'search_zero_all_rows':all(r.get('stop') and not any(r['stop']['stop'].get(k) for k in ['handles','activeNN','active','live_searches']) for r in raw['rows']),'timers_messages':timers,'monitor_callbacks_waited':True,'inner_controlled':inner,'outer_ownedwait':{'remaining':process['remaining'],'unknown':process['unknown_adopted'],'kernel_boundary':process['kernel_boundary']},'currentabsence_not_natural_or_allperiod':True}
save(DATA/(name+'-stop.json'),stop)
metrics=[]
for r in raw['rows']:
 nn=r.get('diagnostic',{}).get('NN_control_events',[]);cp=r.get('adopted_stats');clock=r.get('worker_clock',{});first=r.get('diagnostic',{}).get('sab_publications',[])
 metrics.append({'spec':r['spec'],'request_id':r['identity']['request_id'],'classification':r['response']['classification'],'causes':r['response']['causes'],'Action':r['response']['body']['action'],'adopted_stats':cp,'public_ms':r['response']['public_elapsed_ms'],'planned_ms':r['identity']['seal_ms']-r['identity']['t0_ms'],'timer_ms':r['response']['timer_ms']-r['identity']['t0_ms'],'ACK_wall_ms':r.get('ACK_wall_ms'),'public_before_ACK':r['response']['stamp_ms']<r['stop']['main_received_ms'] if r.get('stop') else None,'opposite_previous':r.get('opposite_previous'),'own_wait':r.get('own_previous_wait'),'first_CP_begin_worker_ms':first[0]['begin_ms'] if first else None,'first_CP_validation_worker_ms':first[0]['validation_end_ms'] if first else None,'first_API':nn[0] if nn else None,'first_API_await_ms':nn[0]['session_run_end_ms']-nn[0]['session_run_start_ms'] if nn else None,'hand_NN':r['hand_NN'],'post_public_newNN_definite':r.get('post_public_NN_definite'),'post_cutoff_newNN_definite':r.get('post_cutoff_NN_definite'),'NN_after_public':r.get('NN_returned_after_public'),'discarded_returns':sum(n['result_discarded'] for n in nn),'worker_stop_class':r.get('worker_stop_class'),'postpublic_immutable':r.get('postpublic_immutable'),'numeric_gate':r.get('gate'),'root_internal_prepare_kernelCPU_exactstore_missing':True})
result={'issue':'quoridor-4lc.134','run':name,'source_Git':read(run/'config.json')['Git'],'planned_games':len(read(run/'config.json')['games']),'started_games':raw['started_games'],'games':raw['games'],'connection':raw.get('connection'),'new_public':sum(g.get('new_public',len(g['actions'])) for g in raw['games']),'functional_public':sum(bool(r['spec'].get('functional')) for r in raw['rows']),'hand_NN':sum(r['hand_NN'] for r in raw['rows']),'startup_NN':read(run/'startup.json')['startup_NN'],'metrics':metrics,'clock_start':read(run/'startup.json')['worker_clocks'],'clock_end':read(run/'clock-end.json'),'resources':{k:process[k] for k in ['start','end','exit','stop_reason','peak_group_plus_runner_RSS','peak_allocated_bytes','assigned_CPU','affinity_violations']},'primary':summary['primary'],'secondary':summary['secondary'],'all_attempts_preserved':True,'score_for_forced_side_not_candidate_AI':True,'formalNI_actualgo':False}
save(DATA/(name+'-results.json'),result)
files=sorted(list(run.rglob('*.json'))+list(run.rglob('*.jsonl'))+list((OUT/'runs').glob(name+'.*')))
files=list(dict.fromkeys(files));members=[{'path':str(p.relative_to(OUT)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in files if p.is_file()]
archive=DATA/(name+'.tar.gz')
with tarfile.open(archive,'w:gz') as t:
 for m in members:t.add(OUT/m['path'],arcname=m['path'],recursive=False)
with tarfile.open(archive) as t:
 for m in members:assert hashlib.sha256(t.extractfile(m['path']).read()).hexdigest()==m['SHA256']
save(DATA/(name+'-archive-manifest.json'),{'issue':'quoridor-4lc.134','source_Git':result['source_Git'],'archive':str(archive.relative_to(ROOT)),'SHA256':sha(archive),'members':members,'stream_restore_all_member_SHA':True,'model_shared_not_copied':True})
print(json.dumps({'run':name,'games':[{k:g.get(k) for k in ['id','status','winner','reason','forced_side_score','new_public','total_ply']} for g in raw['games']],'publics':len(raw['rows']),'NN':result['hand_NN'],'startup':result['startup_NN'],'stopSHA':sha(DATA/(name+'-stop.json')),'identities':len(ids),'archive_bytes':archive.stat().st_size,'archive_SHA':sha(archive)}))
