"""226: stdlib-only compact metadata arithmetic. No NN or teacher replay."""
from pathlib import Path
import collections,datetime,hashlib,json,os,resource,time
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
D=Path('research-data/ai-sigma/frame18-worker-balance-independent'); S=Path('research-data/ai-sigma/frame18-worker-balance'); started=time.monotonic(); os.sched_setaffinity(0,{0}); hashes={}
def read(p):
 p=Path(p); b=p.read_bytes(); hashes[str(p)]=hashlib.sha256(b).hexdigest(); return json.loads(b)
def fail_if(x,why):
 if not x: raise ValueError(why)
reg=read(S/'preregister.json'); stop=read(S/'science-stop.json')
for key in ['scientific_source_write_stopped','all_model_children_waited','current_exact_absent']: fail_if(stop.get(key),'producer stop '+key)
for p in ['tools/ai-sigma-worker-balance/generate.cjs','tools/ai-sigma-worker-balance/runner.py']: fail_if(hashlib.sha256(Path(p).read_bytes()).hexdigest()==stop['source_files'][p],'stop source SHA '+p)
assignments={k:read(S/(k+'-assignment.json')) for k in ['baseline','balanced']}
config=read(S/'balanced-r2-config.json'); opening=read(config['openings_path']); games=[g for g in opening['games'] if g['job']==config['job']]; ids=[g['game_id'] for g in games]
fail_if(len(ids)==96 and len(set(ids))==96,'96 unique game IDs')
assignment_results={}
for mode,a in assignments.items():
 fail_if(a['original_order']==ids and set(a['core_by_game'])==set(ids),'assignment preserves IDs and order')
 counts=collections.Counter(); cohorts=collections.defaultdict(collections.Counter)
 for g in games:
  core=str(a['core_by_game'][g['game_id']]); counts[core]+=1; cohorts[core][str(g['target_ply'])] += 1
 assignment_results[mode]={'workers':dict(counts),'cohorts':{k:dict(v) for k,v in cohorts.items()}}
 fail_if(sorted(counts.values())==[32,32,32],'equal32 assignment')
fail_if(all(v in (5,6) for c in assignment_results['balanced']['cohorts'].values() for v in c.values()),'cohort balanced5or6')
bindings={}
for p,h in reg.get('readonly',{}).items():
 actual=hashlib.sha256(Path(p).read_bytes()).hexdigest(); bindings[p]={'expected':h,'actual':actual}; fail_if(actual==h,'readonly source changed '+p)
summaries={}; failures=[]
for p in sorted(S.glob('*-summary.json')):
 x=read(p); slots=x['all_slot_plies']; fail_if(len(slots)==96 and {s['id'] for s in slots}==set(ids),'all96 denominator')
 status=dict(collections.Counter(s['status'] for s in slots)); policy=sum(s['new_rows'] for s in slots); joint=sum(s['new_rows'] for s in slots if s['status']=='GOAL' and s['terminal'] and not s['unknown_z']); unknown=policy-joint
 fail_if(status==x['status_counts'],'status arithmetic'); fail_if((policy,joint,joint)==(x['Rpolicy'],x['Rz'],x['Rjoint']),'policy/z/joint arithmetic')
 proc=read(S/'jobs'/p.name.replace('-summary.json','')/'process.json'); wall=proc['jobwall_seconds']
 summaries[p.stem]={'status':status,'policy':policy,'z':joint,'joint':joint,'unknown_z_rows':unknown,'joint_per_job_s':joint/wall,'jobwall':wall,'exit':proc['exit'],'stop_reason':proc.get('stop_reason'),'actualNN':proc.get('sample_equivalent'),'workerNN':x.get('logical_worker_NN'),'startup':x.get('startup'),'batch':x.get('batch'),'worker_spans':x.get('worker_spans'),'owner_quality_reference_only':x.get('qualification_replay_rows')}
 for key in ['all_child_waited','current_exact_absent']: fail_if(proc.get(key), 'producer process stop '+key)
 if Path('/proc',str(proc['runner_pid']),'stat').exists(): fail_if(Path('/proc',str(proc['runner_pid']),'stat').read_text().rsplit(')',1)[1].split()[19]!=str(proc['runner_tick']),'fresh runner identity')
 fail_if(not proc.get('remaining'), 'remaining child')
attempts=[]
for p in sorted((S/'jobs').glob('*/process.json')):
 q=read(p); model=(p.parent/'provider-init.json').exists(); before=(p.parent/'before-model-proof.json').exists(); budget=q.get('sample_equivalent')
 if budget is None and before: proof=read(p.parent/'before-model-proof.json'); fail_if(proof['model_NN_samples']==0 and proof['provider_argument_assert_failed_before_any_model_import'],'beforeimport proof'); budget=0
 elif budget is None and model: budget=q['NN_cap']
 attempts.append({'run':p.parent.name,'model_slot':model,'actualNN':q.get('sample_equivalent'),'budgetNN':budget,'wall':q['jobwall_seconds'],'exit':q['exit']})
management=[]
for p in sorted((S/'jobs').glob('*/management-stop.json')):
 q=read(p); management.append({'run':p.parent.name,'receipt':q})
compact=read(S/'compact-result.json')
for p,h in list(hashes.items()):
 if p in stop.get('payload',{}):fail_if(h==stop['payload'][p],'stop payload '+p)
modelslots=sum(a['model_slot'] for a in attempts); measured=sum(a['wall'] for a in attempts); capNN=sum(a['budgetNN'] for a in attempts if a['budgetNN'] is not None)
fail_if(modelslots<=3 and measured<=1500 and capNN<=1050000,'original caps')
fail_if(abs(measured-compact['all_attempt_guardian_wall_s'])<1e-6,'allattemptwall arithmetic')
fail_if(capNN==compact['NN_upper_charge'],'NN conservative budget sum')
completed=[(k,v) for k,v in summaries.items() if v['status']=={'GOAL':96} and v['exit']==0]
comparison=[]
for kb,b in completed:
 for kc,c in completed:
  if kb.startswith('baseline') and kc.startswith('balanced'):
   xb=read(S/(kb+'.json')); xc=read(S/(kc+'.json')); wb=xb['all_slot_plies']; wc=xc['all_slot_plies']; comparison.append({'baseline':kb,'candidate':kc,'wall_delta':c['jobwall']-b['jobwall'],'wall_shortening':1-c['jobwall']/b['jobwall'],'rate_ratio':c['joint_per_job_s']/b['joint_per_job_s'],'same_slot_plies':{i['id']:i['new_rows'] for i in wb}=={i['id']:i['new_rows'] for i in wc},'same_actualNN':b['actualNN']==c['actualNN'],'eligible_rows':[b['joint'],c['joint']]})
for p,h in hashes.items(): fail_if(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,'mutable input '+p)
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'assignment':assignment_results,'bindings':bindings,'summaries':summaries,'attempts':attempts,'management':management,'model_slots':modelslots,'owner_cost_reference':{k:compact.get(k) for k in ['additional_admission_management_wall_unknown','admission_failure_conservative_s','management_conservative_total_bound_s','heavy_known_s','heavy_upper_with_management_admissions_s','finalize_math_wall_s']},'measured_allattempt_wall':measured,'budget_NN_conservative':capNN,'completed_comparisons':comparison,'inputSHA':hashes,'independence_limits':['compact math independent; owner RuleA replay/teacher truth/deep leaves not reauthenticated','same96 repetitions benchmark siblings; no independent training increment','fixed order/warm/censor and overlapping spans not exclusive CPU costs'],'wall':time.monotonic()-started,'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'newNN':0}
(D/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'PASS':True,'model_slots':modelslots,'owner_cost_reference':{k:compact.get(k) for k in ['additional_admission_management_wall_unknown','admission_failure_conservative_s','management_conservative_total_bound_s','heavy_known_s','heavy_upper_with_management_admissions_s','finalize_math_wall_s']},'measured_wall':measured,'comparison':comparison,'wall':result['wall']}))
