import json,pathlib,hashlib,subprocess,datetime,os,time,tarfile,io,difflib
R=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');O=R/'.artifacts/ai-sigma/resume-20261002/BROWSER-SAB-INDEPENDENT';T=R/'tools/ai-sigma-browser-sab-independent';D=R/'research-data/ai-sigma/109-browser-sab-independent'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text())
def save(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(p,rev='181ea3932d270a9f0e69145b57577b411ecbab62'):return subprocess.check_output(['git','show',rev+':'+p],cwd=R)
def current(pid):
 try:
  t=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return {'pid':pid,'starttick':int(t[19]),'state':t[0],'ppid':int(t[1])}
 except FileNotFoundError:return None
before=read(O/'intake-input-before.json');after={p:sha((R/p).read_bytes()) for p in before['source_model_hashes']};assert after==before['source_model_hashes'],'UPSTREAM_CHANGED'
archivepath='research-data/ai-sigma/107-cp-frame/frame7-run-evidence.tar.gz';ab=git(archivepath);assert sha(ab)=='a65f1194a61ef64907956110e86cf9eaf3d35aef3e11dd560680eaa7fdf6593a'
manifest=read(O/'saved-input-manifest.json');checked={};savedstops=[]
with tarfile.open(fileobj=io.BytesIO(ab),mode='r:gz') as tar:
 for p,expected in manifest['needed_member_checks'].items():
  b=tar.extractfile(p).read();assert sha(b)==expected['sha256'];checked[p]={'sha256':sha(b),'bytes':len(b)}
  if p.endswith('process.json'):savedstops.append(json.loads(b))
fixed={}
for p,expected in [('frame7-handoff.json','8317f94ff8a9e10781dacad87395eaa2356b989c77fdecd321143e5c5f0af3f9'),('frame7-runtime-source-stopped-before-report.json','f36887d66fedba9bc8b1016427670ad5c3995cda4e19501d4dbbb4a7ad2a5887')]:
 b=git('research-data/ai-sigma/107-cp-frame/'+p);assert sha(b)==expected;fixed[p]={'sha256':sha(b),'bytes':len(b)}
procs=[read(p) for p in sorted((O/'runs').glob('*.process.json'))]
def ids(procs):
 out=set()
 for d in procs:
  out.add((d['runner_pid'],d['runner_starttick']));out.add((d['child_pid'],d['child_starttick']))
  for x in d['tracked']:out.add((x['pid'],x['start_ticks']))
 return sorted(out)
def checkids(xs):
 rows=[{'pid':p,'starttick':t,'current':current(p)} for p,t in xs];return {'count':len(rows),'same_identity_live':[x for x in rows if x['current'] and x['current']['starttick']==x['starttick']],'rows':rows}
own=checkids(ids(procs));up=checkids(ids(savedstops));assert not own['same_identity_live'];assert not up['same_identity_live']
for name in ['driver.cjs','runner.py']:
 original='diagnose.cjs' if name=='driver.cjs' else name
 old=git('tools/ai-sigma-cp-frame/'+original,'ec4e92d68b4b4aabd7d45ae6cf8cb1234abae82b').decode().splitlines(True);new=(T/name).read_text().splitlines(True)
 (O/(name+'.adapter.diff')).write_text(''.join(difflib.unified_diff(old,new,fromfile='original107/'+original,tofile='critic109/'+name)))
saved=read(O/'runs/109-functional-r3/independent-saved-browser-analysis.json');runtime=read(O/'runs/109-functional-r3/independent-runtime-browser-analysis.json');rows=read(O/'runs/109-functional-r3/browser-result.json')['rows']
clock=rows[0]['worker_clock'];end=read(O/'runs/109-functional-r3/independent-end-clock.json');inter=[max(clock['lo_ms'],end['lo_ms']),min(clock['hi_ms'],end['hi_ms'])];assert inter[0]<=inter[1]
summary={'issue':'quoridor-4lc.109','UTC':utc(),'decision':'finite_browser_SAB_support; formal_fairness_NI_actual_go_not_certified','actual_go':False,'source_Git':'ec4e92d68b4b4aabd7d45ae6cf8cb1234abae82b','data_Git':'181ea3932d270a9f0e69145b57577b411ecbab62','own_initial_source_Git':'979afe3','upstream_needed_member_checks':len(checked),'fixed':fixed,'saved_browser_adjudication':saved,'independent_browser_adjudication':runtime,'own_attempts':[{'name':p['name'],'start':p['start'],'end':p['end'],'exit':p['exit'],'remaining':p['remaining'],'RSSpeak':p['peak_group_plus_runner_RSS'],'storagepeak':p['peak_allocated_bytes'],'all_observed_TIDs_CPU2':p['all_observed_TIDs_at_assigned_CPU'],'public':7 if p['exit']==0 else 0,'planned_but_unexecuted':0 if p['exit']==0 else 7,'preNN_failure':None if p['exit']==0 else ('Node_heap_OOM' if p['exit']==-6 else 'checker_ACK_order_assumption')} for p in procs], 'heavy_jobwall_seconds':sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in procs),'model_startup_NN':6,'actual_new_public_requests':7,'new_game_starts':0,'holdout_sends':0,'runtime_public_max_ms':max(x['response']['public_elapsed_ms'] for x in rows),'runtime_ACKwall_max_ms':max(x['ACK_wall_ms'] for x in rows),'own_start_end_clock_interval_intersection':inter,'own_end_clock_not_applied_to_original':True,'Node_adjudication':False,'RuleA_common_logic_independence_limit':True,'design_limits':['Original Worker stop lower>D:9; straddles:1 despite 296 timely legal publications. Publication and cause CPU budget are separate.','Original clock only starts; end drift missing; API await is not kernel instruction timing; no hard realtime guarantee.','SAB is trusted per-request Worker with out-of-band key/legal/model identity; not arbitrary malicious shared-memory provenance proof.','SAB FAULT override may supersede browser_late classification if simultaneous; precedence not exercised by these runs.','Stamp follows Judge and necessary UTF8; freezing, cancel dispatch, private JSON serialization and continuation happen later; not a measured OS delivery guarantee.','No general deep/rawview/entropy/training overlap or true legal200/no-legal proof.'],'cleanup':{'drop':read(O/'runs/109-functional-r3/finally-model-drop.json'),'timers':read(O/'runs/109-functional-r3/main-timers-stop.json'),'monitor_callback_stop':{k:v for k,v in read(O/'runs/109-functional-r3/pause-monitor-stop.json').items() if k!='rows'},'controlled_forced':True,'outer_remaining':[],'current_identity_evidence_separate_from_historical_wait':True},'old_failures_preserved':True,'resources_limit':'40ms sampling misses instant peaks; no global idle/full CPU/whole retention proof'}
save('independent-summary.json',summary);save('input-after.json',{'UTC':utc(),'source_model_hashes':after,'needed_member_checks':checked,'archiveSHA256':sha(ab),'fixed':fixed,'upstream_current_identities':up,'independent_current_identities':own})
source={str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()}
allocated=sum(p.stat().st_blocks*512 for root in [O,T,D] if root.exists() for p in root.rglob('*') if p.is_file());assert allocated<14680064
save('runtime-source-stopped-before-report.json',{'UTC':utc(),'monotonic':time.monotonic(),'last_heavy_job_end':procs[-1]['end'],'new_heavy_runs':False,'own_runtime_same_identity_live':own['same_identity_live'],'own_identity_count':own['count'],'upstream_subset_current_identity_count':up['count'],'upstream_subset_same_live':up['same_identity_live'],'all_managed_jobs_waited':all(not p['remaining'] for p in procs),'remaining0':True,'source_hashes':source,'current_own_allocated_bytes':allocated,'new_guard':14680064,'combined_guard':117440512,'past_peaks_not_added_to_current':True,'metadata_helper':{'pid':os.getpid(),'identity':current(os.getpid()),'affinity':list(os.sched_getaffinity(0)),'RSS':int(pathlib.Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE'),'started_source_hash':sha(pathlib.Path(__file__).read_bytes())},'metadata_helper_exit_recorded_separately':True})
print(json.dumps({'ownidentity':own['count'],'upstreamsubset':up['count'],'current0':True,'allocation':allocated,'runtime_public_max':summary['runtime_public_max_ms'],'runtime_ACKmax':summary['runtime_ACKwall_max_ms'],'heavywall':summary['heavy_jobwall_seconds']}))
