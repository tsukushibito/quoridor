"""Aggregate already judged browser records and preserve stop/accounting evidence."""
import collections,datetime,hashlib,json,statistics,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/CPU-SIGMA-COMPARISON';DATA=ROOT/'research-data/ai-sigma/117-cpu-sigma-comparison'
def dist(xs):
 xs=[x for x in xs if x is not None]
 return {'n':len(xs),'min':min(xs) if xs else None,'median':statistics.median(xs) if xs else None,'max':max(xs) if xs else None}
rows=[];games=[];pairs=[];startup=0
for pair in range(1,7):
 run=f'cpu117-pair{pair}-r1';s=json.loads((DATA/(run+'.summary.json')).read_text());pairs.append(s);games+=s['games'];startup+=s['startup_NN']
 with tarfile.open(DATA/(run+'.tar.gz'),'r:gz') as tar:
  raw=json.load(tar.extractfile('runs/'+run+'/browser-result.json'));rows+=raw['rows']
engines={}
for engine in ['candidate','reference']:
 selected=[r for r in rows if r['spec']['engine']==engine]
 cps=[r['diagnostic']['validated_cp'] for r in selected if (r.get('diagnostic')or{}).get('validated_cp')]
 enginegates=[r['gate'] for r in selected if r.get('gate')]
 def first_span(r):
  publications=(r.get('diagnostic')or{}).get('sab_publications',[])
  return publications[0]['validation_end_ms']-r['worker_clock']['mid_ms']-r['identity']['t0_ms'] if publications else None
 first_events=[(r,(r.get('diagnostic')or{}).get('NN_control_events',[])[0]) for r in selected if (r.get('diagnostic')or{}).get('NN_control_events')]
 first_public=[(r,e,(r.get('diagnostic')or{}).get('sab_publications',[])[0]) for r,e in first_events if (r.get('diagnostic')or{}).get('sab_publications')]
 engines[engine]={'first_NN_spans':{'t0_to_first_infer_entry_ms':dist(e['start_ms']-r['worker_clock']['mid_ms']-r['identity']['t0_ms'] for r,e in first_events),'infer_wrapper_ms':dist(e['return_ms']-e['start_ms'] for r,e in first_events),'session_API_await_ms':dist(e['session_run_end_ms']-e['session_run_start_ms'] for r,e in first_events if e.get('session_run_start_ms') is not None),'first_infer_return_to_completed_publication_ms':dist(p['validation_end_ms']-e['return_ms'] for r,e,p in first_public),'start_span_contains_unseparated_input_preparation_rootwork_scheduling':True,'cross_clock_start_span_has_saved_interval_error':True,'APIawait_not_kernel':True}, 'public':len(selected),'classifications':dict(collections.Counter(r['response']['classification'] for r in selected)),
  'public_ms':dist(r['response']['public_elapsed_ms'] for r in selected),'timer_execution_delay_ms':dist(r['response']['timer_ms']-r['response']['planned_ms'] for r in selected),
  'first_completed_publication_ms':dist(first_span(r) for r in selected),'ACK_wall_ms':dist(r.get('ACK_wall_ms') for r in selected),'own_previous_wait_ms':dist(r.get('own_previous_wait',{}).get('wait_ms') for r in selected),
  'worker_stop_classes':dict(collections.Counter(r.get('worker_stop_class','missing') for r in selected)),
  'hand_NN':sum(r.get('hand_NN',0) for r in selected),'postpublic_new_NN_definite':sum(r.get('post_public_NN_definite',0) for r in selected),
  'NN_returned_after_public':sum(r.get('NN_returned_after_public',0) for r in selected),'retired_returns_discarded':sum(sum(bool(x.get('result_discarded')) for x in (r.get('diagnostic')or{}).get('NN_control_events',[])) for r in selected),
  'opposite_input_before_old_ACK':sum(bool(r.get('opposite_previous',{}).get('input_before_old_ACK')) for r in selected),'residual_overlap_ACKwall_ms':dist(r.get('opposite_previous',{}).get('residual_overlap_wall_ms') for r in selected),
  'completed_cp':len(cps),'completed_backup_distribution':dist(c.get('simulations') for c in cps),'completed_cp_NN_distribution':dist(c.get('nn_calls') for c in cps),'candidate_depth':dist(c.get('max_depth') for c in cps),'candidate_cap_true':sum(c.get('cap') is True for c in cps),
  'numeric_gate_rows':len(enginegates),'features_bits':len(enginegates)*648,'NN_values':len(enginegates)*137,'priors':sum(g.get('priors',0) for g in enginegates),'fixed_reference_roots':sum(bool(g.get('fixed_reference')) for g in enginegates),'dynamic_self_roots':sum(not bool(g.get('fixed_reference')) for g in enginegates),'missing_public_cp':sum(bool(g.get('missing_public_cp')) for g in enginegates),'P2_rows':sum(bool(g.get('P2canonical')) for g in enginegates)}
processes=[json.loads(p.read_text()) for p in (OUT/'runs').glob('cpu117-*.process.json')]
identities={}
for process in processes:
 assert not process['remaining'] and not process['unknown_adopted'],'OWNERSHIP_NOT_ZERO'
 identities[(process['runner_pid'],process['runner_starttick'])]={'pid':process['runner_pid'],'start_ticks':process['runner_starttick'],'role':'runner'}
 for x in process.get('tracked',[]):
  identities[(x['pid'],x['start_ticks'])]=x
# tracked is a list in current guardian; keep identity evidence bounded to exact recorded PID/starttick.
live=[]
for pid,tick in identities:
 try:
  stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
  if int(stat[19])==tick:live.append({'pid':pid,'start_ticks':tick})
 except OSError:pass
assert not live,'CURRENT_IDENTITY_LIVE'
source={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'tools/ai-sigma-cpu-sigma-frame8').glob('*') if p.is_file()}
resources={'RSS_peak':max(p['peak_group_plus_runner_RSS'] for p in processes),'storage_peak':max(p['peak_allocated_bytes'] for p in processes),'heavy_seconds':sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in processes if p['phase']!='protocol'),'pure_seconds':sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in processes if p['phase']=='protocol'),'current_RSS_not_ru_maxrss':True,'instantaneous_peak_background_CPU_and_final_exited_child_CPU_unobserved':True}
stop={'issue':'quoridor-4lc.117','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_runtime_stopped':True,'process_runs':len(processes),'recorded_identities':len(identities),'current_same_identity':live,'remaining_unknown_per_run':0,'source_after':source,'resources':resources,'current_absence_not_natural_or_all_period_proof':True}
(OUT/'runtime-source-stopped-before-report.json').write_text(json.dumps(stop,indent=2)+'\n')
result={'admission_helper_gap':'pair4 prelaunch helper falsely matched parent shell and shell continued after failure; runtime guard/stop retained; no retrospective gate success; corrected helper applies to pair5/6', 'issue':'quoridor-4lc.117','registered_games':12,'games_started':len(games),'unstarted':12-len(games),'games':games,'WDL':dict(collections.Counter(g['candidate_result'] for g in games)),'goal_games':sum(g['reason']=='goal' for g in games),'responsibility_loss':sum(g['status']=='responsibility_loss' for g in games),'unfinished':sum(g['status']=='unfinished' for g in games),'game_public':len(rows),'startup_NN_pairs':startup,'hand_NN_games':sum(r.get('hand_NN',0) for r in rows),'postpublic_immutable':sum(bool(r.get('postpublic_immutable')) for r in rows),'engines':engines,'resources':resources,'pair_summaries':[p['run']+'.summary.json' for p in pairs],'actual_go':False,'formal_NI':False,'old_results_integrated':False,'seed_repetitions_not_independent_samples':True,'clock_limits':'Start/end interval calibrations retained per run; intermediate drift unobserved. API await is not kernel time; ACK wall is not CPU time.'}
(DATA/'final-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['WDL','goal_games','unfinished','game_public','startup_NN_pairs','hand_NN_games']}))
