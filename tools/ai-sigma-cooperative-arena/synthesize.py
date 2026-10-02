"""Aggregate all fixed diagnostic games without replacing failures or prior experiments."""
import json,tarfile,hashlib,datetime,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA'
DATA=ROOT/'research-data/ai-sigma/103-cooperative-arena'
run_names=['initial-pair-r1','asym-pair-r1','jump-pair-r1']
analyses=[];rows=[];games=[];archives=[];api_boundaries=[]
for run in run_names:
 analysis=json.loads((OUT/run/'analysis.json').read_text());analyses.append(analysis)
 summary=json.loads((OUT/run/'summary.json').read_text())
 games.extend({'run':run,**g} for g in summary['games'])
 manifest=json.loads((DATA/(run+'.archive-manifest.json')).read_text())
 archive=ROOT/manifest['archive']
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
 with tarfile.open(archive) as tf:
  restored={m.name:hashlib.sha256(tf.extractfile(m).read()).hexdigest() for m in tf if m.isfile()}
  assert restored==manifest['restored_hashes']
  for line in tf.extractfile(run+'/turns.jsonl').read().splitlines():
   row=json.loads(line);row['run']=run;rows.append(row)
   for span in row['API_spans']:
    if span['start_late_ms']>=row['t0_ms']+402:
     api_boundaries.append({'run':run,'request_id':row['request_id'],'engine':row['engine'],'APIstart_elapsed_early_ms':span['start_early_ms']-row['t0_ms'],'APIstart_elapsed_late_ms':span['start_late_ms']-row['t0_ms'],'class':'definite_after402' if span['start_early_ms']>=row['t0_ms']+402 else 'straddles402'})
 archives.append({'run':run,'path':manifest['archive'],'SHA256':manifest['archive_sha256'],'bytes':manifest['bytes'],'restored_files':manifest['restored_files']})
assert len(games)==6 and sum(a['game_starts'] for a in analyses)==6
processes=[json.loads(p.read_text()) for p in OUT.glob('*.process.json')]
NNprocesses=[p for p in processes if p['name'].startswith('nn-')]
seconds=lambda p:(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds()
engine=[]
for name in ['candidate','reference']:
 own=[r for r in rows if r['engine']==name]
 engine.append({'engine':name,'public':len(own),'accepted':sum(r['accepted'] for r in own),'late':sum(r['error']=='LATE_RESPONSE' for r in own),'public_max_ms':max(r['public_elapsed_ms'] for r in own),'ACK_cause_max_ms':max(r['cause_window_ms'] for r in own),'ACKwall_over500':sum(r['budget_breach'] for r in own),'Worker_stop_class_counts':{c:sum(r['Worker_stop_class']==c for r in own) for c in ['upper_le_D','lower_gt_D','straddles_D','missing']},'Worker_stop_upper_max_ms':max(r['Worker_stop_interval']['late_ms']-r['t0_ms'] for r in own),'wrapper_entry_after402':sum(r['NN_start_after_cutoff_worker'] for r in own),'APIstart_definite_after402':sum(b['engine']==name and b['class']=='definite_after402' for b in api_boundaries),'APIstart_possible_after402':sum(b['engine']==name for b in api_boundaries),'postpublic_APIstart_definite':sum(r['post_public_NN_start_definite'] for r in own),'postpublic_APIstart_possible':sum(r['post_public_NN_start_possible'] for r in own),'last_API_to_Worker_stop_max_ms':max(r['last_API_to_Worker_stop_ms'] for r in own),'stop_to_Node_upper_max_ms':max(r['stop_to_Node_interval']['hi_ms'] for r in own),'Node_receive_to_confirm_max_ms':max(r['Node_received_to_confirm_ms'] for r in own)})
counts={key:sum(a['counts'].get(key,0) for a in analyses) for key in ['public','accepted','late','missing_completed_cp','hand_NN','startup_NN','fixed_golden_root_references','dynamic_root_gates','features_bits','NN_elements','prior_elements','accepted_cache_before_cutoff_caller_marker_after']}
monitors=[]
for run in run_names:
 saved=json.loads((OUT/run/'pause-monitor-stop.json').read_text())
 assert saved['pending_children']==[] and saved['all_owned_read_callbacks_waited']
 monitors.append({'run':run,'state_at_stop':saved['state'],'typed_failure':saved.get('failure'),'pending_children':saved['pending_children'],'all_owned_read_callbacks_waited':True,'active_monitor_timer':saved['active_monitor_timer'],'owned_read_children':sum(r.get('kind')=='owned_observer_child' for r in saved['rows']),'interpretation':'stop-time SIGTERM/read failure retained separately; not user pause or NN mismatch'})
def allocated(base):return sum(p.stat().st_blocks*512 for p in base.rglob('*') if p.is_file())
report={'issue':'quoridor-4lc.103','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'contract':2,'receiptUTC':'2026-10-02T04:13:09Z','dispatchAcceptedUTC':'2026-10-02T04:12:55Z','processingDeadline':'2026-10-02T05:03:09Z','newJobDeadline':'2026-10-02T04:58:09Z','submissionDeadline':'2026-10-02T05:13:09Z','same_arena_source_SHA256':hashlib.sha256((ROOT/'tools/ai-sigma-cooperative-arena/arena.cjs').read_bytes()).hexdigest(),'run_versions':[{k:a[k] for k in ['run','git','game_starts','W','D','L','unfinished','natural_goal_games','responsibility_games']} for a in analyses],'game_starts':6,'W':sum(a['W'] for a in analyses),'D':sum(a['D'] for a in analyses),'L':sum(a['L'] for a in analyses),'unfinished':sum(a['unfinished'] for a in analyses),'goal_games':sum(a['natural_goal_games'] for a in analyses),'responsibility_games':sum(a['responsibility_games'] for a in analyses),'counts':counts,'NN_total':counts['hand_NN']+counts['startup_NN'],'engines':engine,'API_boundary_observations':api_boundaries,'monitors':monitors,'archives':archives,'resources':{'NN_wall_seconds':sum(seconds(p) for p in NNprocesses),'NN_cap_seconds':1800,'each_NN_run_under600':all(seconds(p)<600 for p in NNprocesses),'static_finished_job_wall_seconds':sum(seconds(p) for p in processes if p['name'].startswith('static')),'static_cap_seconds':240,'currentRSS_peak':max(p['peak_group_plus_runner_RSS'] for p in NNprocesses),'NN_RSS_guard':3758096384,'ru_maxrss_launcher_peak_separate':max(p['runner_ru_maxrss_bytes'] for p in NNprocesses),'retained_accounted_monitor_peak':max(p['peak_allocated_bytes'] for p in processes),'storage_guard':58720256,'current_live_and_data_and_source':allocated(OUT)+allocated(DATA)+allocated(ROOT/'tools/ai-sigma-cooperative-arena'),'Git_increment_reserved_bytes':6291456,'no_guard_events':all(not p['stop_reason'] for p in processes),'all_observed_NN_TIDs_CPU2':all(p['all_observed_TIDs_at_assigned_CPU'] for p in NNprocesses),'all_NN_remaining0':all(not p['remaining'] and not p['unknown_adopted'] for p in NNprocesses)},'failed_static_jobs':[{'run':p['name'],'exit':p['exit'],'log':p['name']+'.log'} for p in processes if p['exit']!=0],'games':games,'actual_go':False,'formal_fairness':False,'formal_NI':False,'pool_holdout_sends':0,'older_WDL_pooled':False,'limits':['finite dynamic root connection and games; no all-deep-node equivalence','ACK cause wall is not engine compute time; API await is not kernel time','clock intervals overlap; do not sum lastAPI->stop and stop->Node without checking boundaries','stop-time BEADS_READ_ERROR retained; callbacks and children stopped','same-identity CPU observed lower bound; exited-child final CPU missing','40ms RSS sampling misses instant peak/background; short commands not fully measured','normal budget CP preserved; no synchronous ORT interruption or OS hard realtime claim']}
for base in [OUT,DATA]:(base/'handoff-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['game_starts','W','D','L','goal_games','responsibility_games','counts','NN_total','engines','resources','failed_static_jobs']}))
