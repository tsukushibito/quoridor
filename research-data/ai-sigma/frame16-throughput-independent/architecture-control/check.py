import pathlib,json,os,time,hashlib,resource,datetime,math
D=pathlib.Path('research-data/ai-sigma/frame16-throughput-independent/architecture-control');S=pathlib.Path('research-data/ai-sigma/frame16-teacher-throughput/architecture-control');R=pathlib.Path('docs/reports/ai-sigma-critic-teacher-throughput.md')
os.sched_setaffinity(0,{0});resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_AS,(234881024,234881024))
def load(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def ident(pid):
 try:
  z=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return {'tick':z[19],'rss':int(z[21])*os.sysconf('SC_PAGE_SIZE')}
 except FileNotFoundError:return None
r=load(D/'record.json');t=time.monotonic();now=time.time();scheduler=load('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');loaded=load('.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame16-extension17/running-loaded.json');mon=load(pathlib.Path(loaded['run'])/'monitor-observation.json')
assert scheduler['owned']is None and mon['owned']is None and scheduler['next_at']-now>=90
assert now-datetime.datetime.fromisoformat(mon['at']).timestamp()<30
mi=ident(mon['process']['pid']);assert mi and mi['tick']==str(mon['process']['start_ticks'])
stop=load(S/'science-stop.json');assert stop['phase2_science_stopped']and stop['science_sources_write_stopped']and stop['all_jobs_waited']and not stop['current_owned_science']
process={n:load(S/'jobs'/n/'process.json')for n in ['graph-r1','graph-confirmation','parity-r1']};absent=[]
for n,p in process.items():
 assert p['exit']==0 and p['all_child_waited']and p['current_exact_absent']and not p['remaining']
 for x in [{'pid':p['runner_pid'],'tick':p['runner_tick']}]+p.get('tracked',[]):
  v=ident(x['pid']);assert v is None or v['tick']!=str(x['tick']), (n,x['pid'])
 absent.append({'run':n,'PID':p['runner_pid'],'tick':p['runner_tick'],'exact_absent':True})
heavy=[]
for q in pathlib.Path('/proc').iterdir():
 if not q.name.isdigit():continue
 try:a=(q/'cmdline').read_bytes().split(b'\0');exe=pathlib.Path(a[0].decode()).name
 except (FileNotFoundError,PermissionError,IndexError):continue
 if exe.startswith(('python','node'))and any(b'/tools/ai-sigma-'in x or b'/tools/nnue-training/'in x for x in a[1:])and not any(b'save'in x or b'pack'in x for x in a[1:]):heavy.append(int(q.name))
assert not heavy,heavy
scope=sum(p.stat().st_blocks*512 for p in D.iterdir()if p.is_file())+max(0,len(R.read_bytes())-r['previous_report_bytes'])
assert scope+53248+12288<102400
admission={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'identity':ident(os.getpid()),'CPU':[0],'monitor':mi,'monitor_run':loaded['run'],'owned':None,'quiet_s':scheduler['next_at']-now,'scientific_identities':absent,'heavy_candidates':heavy,'scope_current_plus_report_delta':scope,'scope_forecast':scope+53248+12288}
bind={'science-stop.json':sha(S/'science-stop.json')}
for f,h in stop['payload_SHA'].items():assert sha(f)==h,f;bind[f]=h
for f,h in stop['source_SHA'].items():
 if pathlib.Path(f).name in ['provider.py','runner.py','generate.cjs','parity.cjs','compare.py','qualify.cjs']:assert sha(f)==h,f;bind[f]=h
pr=load(S/'preregister.json');assert pr['maxB']==8 and pr['active']==24 and (pr['K'],pr['rootN'],pr['edgeSum'])==(64,64,63)
assert datetime.datetime.fromisoformat(pr['UTC'])<datetime.datetime.fromisoformat(process['parity-r1']['startUTC'])
metrics={};signature=None
for n in ['graph-r1','graph-confirmation']:
 x=load(S/(n+'-summary.json'));p=process[n];b=x['batch'];h=b['batch_histogram'];logical=sum(i*v for i,v in enumerate(h));cap=x['providerStop']['graph_startup_samples']
 assert x['planned_games']==len(x['all_slot_plies'])==48 and x['status_counts']=={'GOAL':48}
 assert x['Rjoint']==x['Rpolicy']==x['Rz']==sum(g['new_rows']for g in x['all_slot_plies'])==1554
 assert all(g['status']=='GOAL'and g['terminal']and not g['unknown_z']for g in x['all_slot_plies'])
 assert x['unknown_z_rows']==x['discarded']==0 and x['qualification_replay_rows']==1554
 assert cap==3*sum(range(1,9))==108 and logical==x['logical_worker_NN']==81096
 assert all(b[k]==logical for k in ['started','returned','resumed']) and len(h)==9
 assert x['actual_NN']==p['sample_equivalent']==logical+cap==81204
 assert x['Rjoint']*64==logical+x['terminal_noNN'] and x['terminal_noNN']==18360
 assert x['providerStop']['captured_B']==list(range(1,9))and x['providerStop']['modelhash']=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'
 assert not x['mixed_into_learner']and not x['formal_holdout_read']
 sig=[(g['id'],g['total_ply'],g['new_rows'])for g in x['all_slot_plies']]
 if signature is None:signature=sig
 else:assert signature==sig
 c=load(S/'comparison.json')['conditions'][n];assert c['logical_NN']==logical and math.isclose(c['jobwall_s'],p['jobwall_seconds'])
 metrics[n]={'job_s':p['jobwall_seconds'],'joint_rate':1554/p['jobwall_seconds'],'logicalNN':logical,'physicalNN':logical+cap,'graph_cold_samples':cap,'legacy_startup_field':x['startup'],'capture_warm_s':x['providerStop']['graph_capture_warm_seconds'],'Bmean':logical/sum(h),'calls':sum(h),'full_batches':h[8],'partial_batches':sum(h)-h[8],'qualify_s':x['qualify_wall_s'],'forward_sync_s':c['stages_s']['forward_sync_ms'],'pipe_s':c['provider_pipe_s'],'tail_s':c['last8_completion_tail_s'],'cold_s':c['coldinit_until_first_game_s'],'RSS_sampled_peak':p['peak_aggregate_RSS'],'torch_reserved_peak':x['providerStop']['GPU_peak_reserved_B'],'wire_request_B':c['provider_pipe']['requestBytes'],'wire_response_B':c['provider_pipe']['responseBytes']}
p=load(S/'jobs/parity-r1/result.json');check=p['checks'];assert sorted((c['B'],c['fixture'])for c in check)==[(b,f)for b in range(1,9)for f in range(2)]
assert all(c['IDs_pass']and c['f32_finite_pass']and c['max_tol_ratio']<=1 and c['graph_eager_maxabs']==0 for c in check)
measured=sum(c['CPU_samples']+c['eager_samples']+c['replay_samples']for c in check);cold=p['stop']['result']['graph_startup_samples'];assert measured==216 and cold==108 and measured+cold==p['NN_samples']==process['parity-r1']['sample_equivalent']==324
assert sha(S/'parity-pass.json')==stop['payload_SHA'][str(S/'parity-pass.json')]
c=load(S/'comparison.json');assert len(c['roots'])==len(c['paired_prefixes'])==48
assert all(x['visit_vector_equal']and x['action_equal']and x['feature_history_legal_bind']and x['NNmaxtolratio']<=1 for x in c['roots'])
assert all(x['baseline_rows']==x['candidate_rows']==x['same_state_prefix_rows']and x['first_action_divergence_ply']is None for x in c['paired_prefixes'])
assert sum(x['same_state_prefix_rows']for x in c['paired_prefixes'])==1554
for x in c['whole_qualified_row_correspondence']:
 assert all(x[k]==1554 for k in ['baseline_rows','candidate_rows','same_state_history_rows','same_action_count','same_visit_count'])and x['rootNNmaxtolratio']<=1
old=load(D.parent/'record.json')['result'];base=old['baseline_mean_s'] # prior independent result reuse, no phase1 rerun
mean=sum(x['job_s']for x in metrics.values())/2;phaseNN=sum(p['sample_equivalent']for p in process.values());wall=sum(p['jobwall_seconds']for p in process.values())
assert phaseNN==162732==stop['phase2_NN']and phaseNN+old['allNN']==stop['totalNN']==406620
assert math.isclose(wall,stop['phase2_jobwall'])and phaseNN<=pr['limits']['phase2_NN']and wall<=pr['limits']['phase2_heavy_s']
archive=load(S/'archive-manifest.json');assert pathlib.Path(archive['archive']).stat().st_size==archive['archive_B'];assert sha(archive['archive'])==archive['archive_SHA'];bind['archive-manifest.json']=sha(S/'archive-manifest.json')
# Qualify and pack measured; Git and improvement-only preparation remain unknown if unpublished.
known=process['parity-r1']['jobwall_seconds']+sum(x['qualify_s']for x in metrics.values())+archive['wall_s']
scenario={n:{'job_1000_minutes':x['job_s']/48*1000/60,'qualification_only_1000_minutes':(x['job_s']+x['qualify_s'])/48*1000/60}for n,x in metrics.items()}
for f,h in bind.items():
 path=pathlib.Path(f)if f.startswith(('tools/','research-data/'))else S/f
 assert sha(path)==h, f
out={'admission':admission,'binding':bind,'metrics':metrics,'parity_samples':324,'parity_input_samples':216,'parity_capture_samples':108,'parity_maxabs_saved':max(x['max_absdiff']for x in check),'parity_graph_eager_maxabs_saved':0,'all_root_correspondence_rows':1554,'phase2_NN':phaseNN,'all_phase_NN':phaseNN+old['allNN'],'phase2_measured_s':wall,'all_phase_measured_s':wall+old['measured_attempt_s'],'old_failed_wall':'UNKNOWN; 5s accounting separate','old_static_charge':60,'new_static_charge':90,'graph_mean_s':mean,'old_B8_mean_reused_s':base,'wall_reduction_fraction':1-mean/base,'rate_gain_fraction':base/mean-1,'saving_s_per_game':(base-mean)/48,'known_parity_qualification_pack_s':known,'known_helper_recovery_game_scenario':known/((base-mean)/48),'Git_cost':'UNKNOWN at snapshot; not zero','improvement_only_preparation':'UNKNOWN','scenarios':scenario,'actual1000':False,'teacher_truth':'owner RuleA/compact root correspondence reference; no raw/replay/forward recert','comparison_history_limitation':'owner whole-correspondence comparator checks sorted history keys, not all multiset counts independently; source/rule and matched actions limited support','NN':0,'calc_actual_wall_s':time.monotonic()-t,'RSS_peak':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'source_SHA':sha(D/'check.py')}
assert out['calc_actual_wall_s']<60 and out['RSS_peak']<234881024
r['result']=out;r['calc_pending']=None;r['remaining_calc']=0;(D/'record.json').write_text(json.dumps(r,separators=(',',':'))+'\n');print(json.dumps({k:out[k]for k in ['phase2_NN','phase2_measured_s','graph_mean_s','wall_reduction_fraction','rate_gain_fraction','scenarios','calc_actual_wall_s','RSS_peak']}))
