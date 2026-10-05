import json,pathlib,os,time,hashlib,resource,datetime,math
D=pathlib.Path('research-data/ai-sigma/frame16-throughput-independent'); S=pathlib.Path('research-data/ai-sigma/frame16-teacher-throughput')
os.sched_setaffinity(0,{0}); resource.setrlimit(resource.RLIMIT_CPU,(30,30)); resource.setrlimit(resource.RLIMIT_AS,(234881024,234881024))
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def identity(pid):
 try:
  z=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return {'tick':z[19],'rss':int(z[21])*os.sysconf('SC_PAGE_SIZE'),'state':z[0]}
 except FileNotFoundError:return None
record=read(D/'record.json'); started=time.monotonic(); epoch=time.time()
scheduler=read('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json')
loaded=read('.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame16-extension17/running-loaded.json'); monitor=read(pathlib.Path(loaded['run'])/'monitor-observation.json')
assert scheduler['owned'] is None and monitor['owned'] is None, 'natural supervisor currently owned'
assert scheduler['next_at']-epoch>=90 and epoch-datetime.datetime.fromisoformat(monitor['at']).timestamp()<30
m=identity(monitor['process']['pid']);assert m and m['tick']==str(monitor['process']['start_ticks'])
stop=read(S/'science-stop.json'); assert stop['all_child_waited'] and stop['current_exact_absent'] and not stop['remaining_scientific_children']
processes={n:read(S/'jobs'/n/'process.json') for n in ['baseline','candidate','baseline-confirmation','parity-r2']}
observed=[]
for name,p in processes.items():
 assert p['exit']==0 and p['all_child_waited'] and p['current_exact_absent'] and not p['remaining']
 for x in [{'pid':p['runner_pid'],'tick':p['runner_tick']}]+p.get('tracked',[]):
  v=identity(x['pid']);assert v is None or v['tick']!=str(x['tick']), (name,x['pid'])
 observed.append({'run':name,'runner':p['runner_pid'],'tick':p['runner_tick'],'exact_absent':True})
heavy=[]
for q in pathlib.Path('/proc').iterdir():
 if not q.name.isdigit():continue
 try:args=(q/'cmdline').read_bytes().split(b'\0'); exe=pathlib.Path(args[0].decode()).name
 except (FileNotFoundError,PermissionError,IndexError):continue
 if exe.startswith(('python','node')) and any(b'/tools/ai-sigma-' in a or b'/tools/nnue-training/' in a for a in args[1:]):
  if not any(b'save' in a or b'pack' in a for a in args[1:]):heavy.append({'pid':int(q.name),'args':[a.decode(errors='replace') for a in args[:3]]})
assert not heavy,heavy
current=sum(p.stat().st_blocks*512 for p in D.iterdir() if p.is_file())+pathlib.Path('docs/reports/ai-sigma-critic-teacher-throughput.md').stat().st_blocks*512
assert current+53248+4096+16384<=102400
admit={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'identity':identity(os.getpid()),'CPU':[0],'monitor':m,'monitor_run':loaded['run'],'scheduler_owned':None,'next_quiet_s':scheduler['next_at']-epoch,'known_science_exact':observed,'heavy_candidates':heavy,'scope_allocated':current,'forecast_including_Git_temp_metadata':current+53248+4096+16384}
# Only compact saved arithmetic follows admission; no model/session imports.
bind={}
for f,expected in stop['payload_SHA'].items():
 assert sha(S/f)==expected,f;bind[f]=expected
for f,expected in stop['source_SHA'].items():
 if pathlib.Path(f).name in ['provider.py','broker.cjs','worker.cjs','generate.cjs','qualify.cjs','compare.py','runner.py']:
  p=pathlib.Path(f);assert sha(p)==expected,f;bind[f]=expected
for f in ['science-stop.json','preregister-v2.json','cost-target-scenarios.json','archive-manifest.json','storage-final.json','admission-failure-cost-erratum.json']:
 bind[f]=sha(S/f)
pr=read(S/'preregister-v2.json');assert (pr['K'],pr['rootN'],pr['edgeSum'])==(64,64,63)
assert pr['conditions']==[{'name':'baseline','active':24,'maxB':8},{'name':'candidate','active':24,'maxB':24}]
assert datetime.datetime.fromisoformat(pr['amendment_UTC'])<datetime.datetime.fromisoformat(processes['baseline']['startUTC'])
modes={}; slots=None
for name,maxb in [('baseline',8),('candidate',24),('baseline-confirmation',8)]:
 x=read(S/(name+'-summary.json')); p=processes[name]; h=x['batch']['batch_histogram']; n=sum(h); count=sum(i*v for i,v in enumerate(h))
 assert x['planned_games']==48 and x['status_counts']=={'GOAL':48} and len(x['all_slot_plies'])==48
 assert x['Rjoint']==x['Rpolicy']==x['Rz']==sum(g['new_rows']for g in x['all_slot_plies'])==1554
 assert all(g['terminal'] and not g['unknown_z'] and g['status']=='GOAL' for g in x['all_slot_plies'])
 assert x['unknown_z_rows']==x['discarded']==x['startup']==0 and x['qualification_replay_rows']==1554
 assert x['actual_NN']==x['logical_worker_NN']==count==p['sample_equivalent']==81096
 assert x['Rjoint']*64==x['actual_NN']+x['terminal_noNN'] and x['terminal_noNN']==18360
 assert all(x['batch'][k]==81096 for k in ['started','returned','resumed']) and len(h)==maxb+1
 assert not x['mixed_into_learner'] and not x['formal_holdout_read'] and x['providerStop']['modelhash']==pr['model_SHA']
 assert math.isclose(x['allattempt_jobwall_s'],p['jobwall_seconds'])
 sig=[(g['id'],g['total_ply'],g['new_rows'])for g in x['all_slot_plies']]
 if slots is None:slots=sig
 else:assert slots==sig
 modes[name]={'wall_s':p['jobwall_seconds'],'joint':1554,'rate':1554/p['jobwall_seconds'],'actualNN':count,'terminal_noNN':18360,'batch_calls':n,'Bmean':count/n,'full_batches':h[maxb],'partial_batches':n-h[maxb],'queue_mean_ms':x['batch']['queue_ms_sum']/count,'qualify_s':x['qualify_wall_s'],'RSS_sampled_peak':p['peak_aggregate_RSS'],'torch_reserved_peak':x['providerStop']['GPU_peak_reserved_B']}
p=read(S/'jobs/parity-r2/result.json'); checks=p['checks']; assert [c['B']for c in checks]==list(range(1,25))
assert all(c['IDs_pass']and c['f32_finite_pass']and c['max_tol_ratio']<=1 for c in checks)
assert sum(c['CPU_samples']+c['CUDA_samples']for c in checks)==p['NN_samples']==600
receipt=read(S/'parity-receipt.json');assert sha(S/'jobs/parity-r2/result.json')==receipt['SHA'];assert max(c['max_absdiff']for c in checks)==receipt['maxabs']
c=read(S/'comparison.json');assert len(c['roots'])==len(c['paired_prefixes'])==48
assert all(r['visit_vector_equal']and r['action_equal']and r['feature_history_legal_bind']and r['NNmaxtolratio']<=1 for r in c['roots'])
assert all(r['baseline_rows']==r['candidate_rows']==r['same_state_prefix_rows']and r['first_action_divergence_ply']is None for r in c['paired_prefixes'])
assert sum(r['same_state_prefix_rows']for r in c['paired_prefixes'])==1554
wall=sum(p['jobwall_seconds']for p in processes.values()); nn=sum(p['sample_equivalent']for p in processes.values());assert nn==243888 and math.isclose(wall,stop['measured_jobwall_s'])
cost=read(S/'cost-target-scenarios.json');assert math.isclose(wall,cost['measured_allattempt_jobwall_s']);assert cost['unmeasured_failed_admission_wall']['actual_jobwall_s']is None
mean=(modes['baseline']['wall_s']+modes['baseline-confirmation']['wall_s'])/2; cand=modes['candidate']['wall_s']; saving=(mean-cand)/48
scenario={}
for name,m in modes.items():
 k=cost['methods'][name]; total=m['wall_s']+m['qualify_s']+k['sharedpack_per48_s']+k['sharedGit_per48_s']
 value=total/48*1000/60;assert math.isclose(value,k['scenarios']['1000']['projected_qualification_pack_Git_included_minutes'])
 scenario[name]={'1000_linear_job_minutes':m['wall_s']/48*1000/60,'1000_qualified_pack_Git_minutes':value}
known=processes['parity-r2']['jobwall_seconds']+sum(m['qualify_s']for m in modes.values())+3*(cost['methods']['candidate']['sharedpack_per48_s']+cost['methods']['candidate']['sharedGit_per48_s'])
assert math.isclose(known,cost['break_even']['known_validation_qualification_pack_save_cost_s'])
a=read(S/'archive-manifest.json'); assert pathlib.Path(a['archive']).stat().st_size==a['archive_B'];assert sha(a['archive'])==a['archive_SHA']
assert all(sha(S/f)==v for f,v in bind.items()if not f.startswith('tools/'))
result={'admission':admit,'binding':bind,'mode_metrics':modes,'independent_checks':'compact counts/rates/receipt hashes PASS; owner RuleA qualification and root numerical receipts not independent replay/forward','parity_samples':600,'maxabs_saved':receipt['maxabs'],'same_48_prefix_rows':1554,'measured_attempt_s':wall,'failed_admission_actual':'UNKNOWN','failed_admission_budget_s':5,'old_comparison_estimate_s':c['allattempt']['wall_s'],'old_comparison_minus_measured_s':c['allattempt']['wall_s']-wall,'allNN':nn,'baseline_mean_s':mean,'candidate_wall_reduction_fraction':1-cand/mean,'candidate_rate_gain_fraction':mean/cand-1,'density_joint_per_game':1554/48,'required_joint_per_s_60min':1554/48*1000/3600,'required_joint_per_s_30min':1554/48*1000/1800,'scenarios':scenario,'marginal_saved_s_per_game':saving,'measured_validation_helpers_s':known,'helper_only_recovery_game_scenario':known/saving,'incremental_improvement_prep':'UNKNOWN','archive_hash_PASS':True,'scientific_stop':True,'NN':0,'static_charge':60,'cap':60,'calc_actual_wall_s':time.monotonic()-started,'RSS_peak':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'source_SHA':sha(D/'check.py')}
assert result['calc_actual_wall_s']<30 and result['RSS_peak']<234881024
record['result']=result;record['calc_pending']=None;record['remaining_stats_cap']=0;record['science_status']='finite compact PASS; small speed benefit uncertain; no promotion';record['adoption']['effect_observed']=True
(D/'record.json').write_text(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n'); print(json.dumps({k:result[k]for k in ['measured_attempt_s','allNN','candidate_rate_gain_fraction','scenarios','calc_actual_wall_s','RSS_peak']}))
