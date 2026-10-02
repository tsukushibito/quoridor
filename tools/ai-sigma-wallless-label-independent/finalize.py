import json,pathlib,hashlib,datetime,tarfile,os
R=pathlib.Path(__file__).resolve().parents[2];T=pathlib.Path(__file__).parent;D=R/'research-data/ai-sigma/143-wallless-label-independent';O=R/'.artifacts/ai-sigma/resume-20261002/WALLLESS-LABEL-INDEPENDENT';run=O/'runs/p143-label-r2'
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
pre=load(run/'preflight.json');cases=[load(run/('case-'+str(i)+'.json')) for i in range(2)];served=load(run/'served-source.json');summary=load(run/'summary.json');status=load(run/'browser-status.json');ack=load(O/'runs/p143-label-r2.owned-ack.json');monitor=load(run/'pause-monitor-stop.json')
assert summary['primary'] is None and not ack['registered_live'] and not ack['unknown_adopted'] and ack['kernel_boundary']['sole_explicit_root']
assert monitor['all_owned_read_callbacks_waited'] and not monitor['active_monitor_timer'] and not monitor['pending_children']
assert status['solver_started']==status['solver_completed']==2 and not status['main_active'] and status['NN']==status['Model']==status['Worker_attempts']==0
for p in served['sources']:assert sha((R/p['path']).read_bytes())==p['SHA256']
assert served['browser_echo_SHA256'][1:]==[p['SHA256'] for p in served['sources']]
rows=[]
for i,c in enumerate(cases):
 f=c['independent'];assert c['root_intervals_equal'];p=pre['cases'][i];assert f['nodes']==p['saved_proof']['nodes'] and f['terminal']==p['saved_proof']['terminal'] and f['depthUnknown']==p['saved_proof']['depthUnknown'] and f['nodeUnknown']==f['timeUnknown']==0
 rows.append({'input':c['input'],'saved_proof':p['saved_proof'],'independent':{k:v for k,v in f.items() if k!='proof'},'root_intervals_equal':True,'immediate_goals':p['immediate_goals'],'scientific_solver_attempts':1})
dump(D/'independent-results.json',{'issue':'quoridor-4lc.143','scientific_source_Git':'885eb8e','rows':rows,'mocks':pre['mocks'],'true_state_and_history':True,'shared_RuleA_independence_limit':True,'NN_Model_AIWorker_game_build':0,'label_finite_support':True,'small_modification_sensitivity_unproven':True,'no_general_wall_midgame_or_NI_Sigma':True})
jobs=[load(p) for p in sorted((O/'runs').glob('p143-*.process.json'))];static=[load(p) for p in sorted(O.glob('*.process.json'))];refs={}
for j in jobs:
 for i in j['tracked']+[{'pid':j['runner_pid'],'start_ticks':j['runner_starttick']}]:refs[i['pid'],i['start_ticks']]=i
for j in static:
 for i in j['owned']:refs[i['pid'],i['start_ticks']]=i
for i in load(run/'controlled-stop.json')['tracked']:
 refs[i['pid'],i['starttick']]={'pid':i['pid'],'start_ticks':i['starttick'],'inner_observation':True}
same=[]
for (pid,tick),i in refs.items():
 try:s=pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(s[19])==tick:same.append(i)
assert not same and all(not j['remaining'] and not j['unknown_adopted'] for j in jobs)
inputbefore=load(O/'runs/p143-label-r2.inputs.json');assert all(sha(pathlib.Path(p).read_bytes())==h for p,h in inputbefore['source'].items())
f=load(D/'failures.json');f['attempts']=[a for i,a in enumerate(f['attempts']) if a not in f['attempts'][:i]]
if not any(a['run']=='p143-label-r2' for a in f['attempts']):f['attempts'].append({'run':'p143-label-r2','exit':0,'source_actual_Git':'885eb8e','env_Git_label':'candidate-r2','env_label_is_not_a_Git_ID':True,'actual_source_verified_by_full_launchhash_to_Git_blob':True,'solver_started_completed':2,'scientific_success_repetition':0})
dump(D/'failures.json',f)
stop={'issue':'quoridor-4lc.143','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scientific_runtime_stopped':True,'source_write_stopped':True,'scientific_source_Git':'885eb8e','own_source_hashafter':{str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()},'scientific_source_before_after_exact':True,'jobs':jobs,'static_jobs':static,'observed_identity_count':len(refs),'current_same_identity':same,'read_errors':[],'Model_NN_AIWorker':0,'browser_status':status,'inner_controlled':load(run/'controlled-stop.json'),'monitor_callbacks_waited':True,'main_timer_message':0,'outersole_rootwait_remainingunknown0':True,'browser_wall_s':sum((datetime.datetime.fromisoformat(j['end'])-datetime.datetime.fromisoformat(j['start'])).total_seconds() for j in jobs),'managed_static_wall_s':sum(j['wall_s'] for j in static),'peak_browser_current_RSS':max(j['peak_group_plus_runner_RSS'] for j in jobs),'current_absence_not_natural_fullperiod_allhost':True,'short_unmanaged_management_commands_fullperiod_PID_RSS_missing':True}
stop['closure_helper_at_snapshot']={'pid':os.getpid(),'start_ticks':int(pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),'running_at_snapshot':True,'final_handoff_must_recheck_absence':True}
dump(D/'runtime-source-stopped-before-report.json',stop)
members=[O/'input.json']+[p for p in O.iterdir() if p.is_file() and p.suffix in ['.json','.log']]+[p for p in (O/'runs').rglob('*') if p.is_file() and ('p143-' in p.name or p.parent.name.startswith('p143-'))]
arc=D/'attempts-proof.tar.gz'
with tarfile.open(arc,'w:gz') as a:
 for p in members:a.add(p,arcname=str(p.relative_to(O)),recursive=False)
entries=[]
with tarfile.open(arc) as a:
 for m in a.getmembers():
  b=a.extractfile(m).read();assert b==(O/m.name).read_bytes();entries.append({'path':m.name,'bytes':len(b),'SHA256':sha(b)})
dump(D/'archive-manifest.json',{'archive':str(arc.relative_to(R)),'SHA256':sha(arc.read_bytes()),'bytes':arc.stat().st_size,'members':entries,'restore':str(O.relative_to(R)),'stream_restore_all_equal':True,'original_archive_fullcopy':False})
size=sum(p.stat().st_blocks*512 for folder in [O,D,T] for p in folder.rglob('*') if p.is_file());before=load(D/'input-and-binding.json');assert size<7*1024**2 and before['critic_artifact_current_allocated']+size+2*1024**2<112*1024**2
dump(D/'storage-final.json',{'own_allocated':size,'old_conservative_artifact':before['critic_artifact_current_allocated'],'own_double_count_conservative':True,'Git_report_forecast':2*1024**2,'combined_forecast':before['critic_artifact_current_allocated']+size+2*1024**2,'combined_guard':112*1024**2,'new_guard':7*1024**2,'reservation_new':0,'old_unknown_not_decreased':True})
print(json.dumps({'identity_count':len(refs),'current':same,'heavy_s':stop['browser_wall_s'],'static_s':stop['managed_static_wall_s'],'RSS':stop['peak_browser_current_RSS'],'archive_members':len(entries),'archive_bytes':arc.stat().st_size,'scope_allocated':size}))
