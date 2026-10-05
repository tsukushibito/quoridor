import pathlib,json,datetime,hashlib,os,socket
ROOT=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');RUN=ROOT/'.artifacts/ai-sigma/runs/SIGMA-NN-SEARCH';CACHE=pathlib.Path('/home/vscode/.cache/inference/research/ai-sigma/nn-search');OWN=ROOT/'tools/ai-sigma-nn-search';os.sched_setaffinity(0,{2})
def account(roots,follow=False):
 seen=set();logical=0;allocated=0;count=0
 for root in roots:
  for base,dirs,files in os.walk(root,followlinks=follow):
   for f in files:
    p=pathlib.Path(base)/f
    try:s=p.stat()
    except FileNotFoundError:continue
    logical+=s.st_size;key=(s.st_dev,s.st_ino)
    if key not in seen:seen.add(key);allocated+=s.st_blocks*512;count+=1
 return {'unique_allocated_bytes':allocated,'path_logical_bytes':logical,'unique_files':count}
jobs=[json.loads(p.read_text())for p in RUN.glob('*.process.json')];jobs.sort(key=lambda x:x['start']);live=[];bad=[]
for q in jobs:
 assert q['remaining_pids']==[]
 for child in q['tracked_processes']:
  p=pathlib.Path('/proc')/str(child['pid'])/'stat'
  try:s=p.read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  if int(s[19])==child['start_ticks']and s[0]!='Z':live.append(child['pid'])
 corrections=sum(len(p.get('affinity_corrections',[]))for p in q['tracked_processes'])
 if corrections or q['name']=='native-clock':bad.append({'job':q['name'],'corrections':corrections,'affinity':q['affinity']})
assert not live
ports={}
for port in [5183,5184,5187]:
 s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
 try:s.bind(('127.0.0.1',port));ports[str(port)]='no_listener'
 except OSError:ports[str(port)]='bind_unavailable'
 finally:s.close()
size=account([OWN,RUN,CACHE]);reuse=account([CACHE/'cargo-home/registry/src',CACHE/'cargo-home/registry/cache'],True);total=1772277760+size['unique_allocated_bytes'];assert size['unique_allocated_bytes']<2*1024**3 and total<5*1024**3;overlap=[(a['name'],b['name'])for a,b in zip(jobs,jobs[1:])if b['start']<a['end']];assert not overlap
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'jobs':len(jobs),'failed_jobs':[{'name':q['name'],'exit':q['exit'],'reason':q['stop_reason']}for q in jobs if q['exit']!=0],'CPU_deviations_retained':bad,'CPU_corrected_runtime_jobs_observed_only2':all(all(set(a)=={2}for p in q['tracked_processes']for a in p['affinities'])for q in jobs if q['name']in ['browser-diagnostic-cpu2','native-clock-cpu2','browser-caps','browser-boundary','final-browser-parity']),'job_interval_overlaps':overlap,'peak_RSS_group_plus_runner_conservative_bytes':max(q['peak_group_plus_runner_rss_bytes']for q in jobs),'RSS_note':'200ms sampling; instantaneous peaks and very short descendants may be missed. Runner ru_maxrss is conservative inherited high-water, shared pages summed.','new_storage':size,'reused_registry_source_cache_existing_owner_bytes':reuse,'reused_registry_is_read_only_reference_no_new_copy_count':True,'new_logical_storage_peak_bytes':max(q['peak_storage_bytes']for q in jobs),'prior_experiment_bytes':1772277760,'owned_current_conservative_bytes':total,'additional_reservation_remaining_bytes':2*1024**3-size['unique_allocated_bytes'],'owned_reservation_remaining_bytes':5*1024**3-total,'GPU':0,'training':0,'duels':0,'new_model_downloads':0,'new_crates_downloaded':0,'known_live_children':live,'all_direct_children_waited':True,'ports':ports,'last_job_end':max(q['end']for q in jobs),'other_process_kills':0,'checkpoint':'individual immutable request checkpoints only; failed/stale/late search checkpoint never published','temp_remaining_files':[str(p)for p in(CACHE/'tmp').rglob('*')if p.is_file()],'background_note':'hypothesis CPU0 and coordinator parallel; no formal uncontested performance window','guard_stops':sum(q['stop_reason']is not None for q in jobs)};(RUN/'resource-shutdown-summary.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in ['failed_jobs','temp_remaining_files']}))
