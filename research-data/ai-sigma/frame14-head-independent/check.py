import pathlib,json,gzip,struct,hashlib,collections,math,random,os,time,datetime,resource,zipfile,pickletools
D=pathlib.Path('research-data/ai-sigma/frame14-head-independent')
H=pathlib.Path('research-data/ai-sigma/frame14-head-control')
E=pathlib.Path('research-data/ai-sigma/frame14-head-test')
A=pathlib.Path('research-data/ai-sigma/frame14-teachers/final-qf1-v2')
def j(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def rows(p):
 with gzip.open(p,'rt') as h:return [json.loads(v) for v in h]
def write(n,v):(D/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def avg(v):return math.fsum(v)/len(v) if v else None
def f(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def sig(r):
 bits=[struct.unpack('<I',struct.pack('<f',v))[0] for v in r['distance']]
 return hashlib.sha256(json.dumps(['QF1-f32-STM-v1',sorted(r['ids'][r['side']-1]),sorted(r['ids'][2-r['side']]),bits],sort_keys=True,separators=(',',':')).encode()).hexdigest()
def admit():
 os.sched_setaffinity(0,{0});now=datetime.datetime.now(datetime.timezone.utc);assert now<datetime.datetime(2026,10,4,3,tzinfo=datetime.timezone.utc)
 obs=j('.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/live-frame14-ee73f985-00e3-4a1c-960e-1e87143fb693/monitor-observation.json');assert obs['owned'] is None
 assert (now-datetime.datetime.fromisoformat(obs['at'])).total_seconds()<35
 nextslot=now.replace(minute=31,second=55,microsecond=281596)
 while nextslot<now:nextslot+=datetime.timedelta(minutes=20)
 assert (nextslot-now).total_seconds()>150
 heavy=[];management=[]
 for p in pathlib.Path('/proc').glob('[0-9]*'):
  try:
   args=[v.decode() for v in (p/'cmdline').read_bytes().split(b'\0') if v];c=' '.join(args);entry=next((v for v in args if v.endswith(('.py','.cjs'))),args[0] if args else '')
   if any(v in entry for v in ['worker.cjs','provider.py','faithful-native','ort.py','head-test/generate.cjs','head-control/run.py','head-control/evaluate.py','nnue-training/train.py']) and int(p.name)!=os.getpid() and 'python3 - <<' not in c:heavy.append({'PID':int(p.name),'tick':(p/'stat').read_text().split()[21],'cmd':c[:200]})
   elif '/tools/' in entry and ('save' in entry or 'pack' in entry):management.append({'PID':int(p.name),'tick':(p/'stat').read_text().split()[21],'affinity':sorted(os.sched_getaffinity(int(p.name))),'cmd':c[:200]})
  except (ValueError,OSError):pass
 assert not heavy,heavy
 for p in [H/'jobs/train-r1/process.json',H/'jobs/test-r1/process.json']:
  q=j(p);assert q['exit']==0 and q['child_waited'] and q['remaining']==[] and q['current_exact_identity_absent']
 assert j(H/'training-stop.json')['scientific_source_stopped'] and j(E/'science-stop-safe.json')['all_child_waited'] and j(E/'science-stop-safe.json')['scientific_source_stopped']
 own=sum(p.stat().st_size for p in D.rglob('*') if p.is_file());assert own<1572864 and 106541540+2097152<117440512
 write('admission.json',{'UTC':now.isoformat(),'PID':os.getpid(),'tick':pathlib.Path('/proc/self/stat').read_text().split()[21],'CPU':[0],'RSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'guard':469762048,'supervisor_owned':None,'observation':obs['at'],'nextslot':nextslot.isoformat(),'heavy_current':heavy,'management_current':management,'old_retained':106541540,'scope_current':own,'newscope_forecast':2097152,'metadata_temp_Git_forecast':1572864,'total':108638692,'old_discount':0,'parent_add':0,'max_job_s':60})
 return time.monotonic()
def storage(v):
 assert sha(v['path'])==v['checkpoint_SHA'];z=zipfile.ZipFile(v['path']);ops=list(pickletools.genops(z.read(next(n for n in z.namelist() if n.endswith('data.pkl')))));names={'distance_a','distance_b','ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias'};mapping={};key=None
 for op,a,_ in ops:
  if op.name in ['BINUNICODE','SHORT_BINUNICODE']:
   if a=='model_config':break
   if a in names:key=a
   elif key and isinstance(a,str) and a.isdigit():mapping[key]=a;key=None
 assert set(mapping)==names
 blobs={k:z.read(next(n for n in z.namelist() if n.endswith('/data/'+ix))) for k,ix in mapping.items()}
 h=hashlib.sha256(b''.join(blobs[k] for k in mapping)).hexdigest();assert h==v['weight_SHA'];return blobs,mapping
def run():
 start=admit();pr=j(H/'preregister.json');settings=j(H/'evaluator-settings.json');gate=j(H/'gate-result.json');schema=j(H/'finite-schema.json');freeze=j(H/'candidate-freeze.json');bindings={}
 assert sha(H/'gate-result.json')=='19e1ec83d63a703d2d2a2d36917875f97c651b9dd30ff805e806ffb460a3929b'
 def bind(p):bindings[str(p)]=sha(p)
 assert pr['head_parameters']==33 and pr['optimizer_parameters']==['out.weight','out.bias'] and pr['training_samples']==256000 and pr['science_samples']==379921
 assert settings['config_SHA']==sha(settings['config'])
 assert settings['initial_tensor_SHA']==pr['initial']['weight_SHA']=='52bfc75272f7cfe8ae6ce57eb14b8a9e7848bfba99613c221f77498a8e897576'
 assert sha('research-data/ai-sigma/frame14-representation-audit/result.json')==pr['coefficient_fit_SHA']=='77ce9e79495038b25a4f4a9ffd95dc9f66700aff2c1f96cf08b65fff3c79733c'
 assert settings['coefficients']==pr['coefficients'] and settings['mask_SHA']==pr['mask_SHA']==sha(A/'fixed-exposure-mask.json')
 assert settings['validation_SHA']==pr['validation_SHA'] and settings['config_SHA']==sha(settings['config'])
 parent,_=storage(pr['initial']);assert struct.unpack('<f',parent['distance_a'])[0]==f(pr['coefficients']['a']) and struct.unpack('<f',parent['distance_b'])[0]==f(pr['coefficients']['b']);tensor={}
 assert all(v==0 for k in pr['optimizer_parameters'] for v in struct.unpack('<'+'f'*(len(parent[k])//4),parent[k]))
 for name,v in settings['checkpoints'].items():
  b,m=storage(v);assert sum(len(b[k]) for k in pr['optimizer_parameters'])==33*4
  for k in pr['frozen']:assert b[k]==parent[k] and hashlib.sha256(b[k]).hexdigest()==schema['frozen_tensor_exact'][name][k]
  if name=='initial':assert b==parent
  tensor[name]={'storage_map':m,'frozen_bytes_equal':True,'head_float32_parameters':33,'weight_SHA':v['weight_SHA'],'file_SHA':v['checkpoint_SHA'],'head_changed':any(b[k]!=parent[k] for k in pr['optimizer_parameters'])};bind(v['path'])
 assert tensor['best']['head_changed'] and tensor['last']['head_changed']
 curve=[json.loads(x) for x in (H/'runs/frame14-head-control-r1/history.jsonl').read_text().splitlines()];assert len(curve)==21 and [r['step'] for r in curve]==list(range(0,2001,100))
 cur=[];curve_error=0
 for r in curve:
  assert r['train_samples_seen']==r['step']*128 and abs(r['train_epochs_equivalent']-r['train_samples_seen']/4653)<1e-12
  v={'step':r['step'],'samples':r['train_samples_seen'],'epochs':r['train_epochs_equivalent']}
  for part in ['train','validation']:
   gg=r[part+'_games'];n=sum(x['rows'] for x in gg.values());assert (n,len(gg))==((4653,96) if part=='train' else (1248,24))
   for k in ['rootmean_mse','z_mse','target_mse','constant_mse']:
    curve_error=max(curve_error,abs(avg([x[k] for x in gg.values()])-r[part][k.replace('_mse','_game_equal_mse')]),abs(math.fsum(x[k]*x['rows'] for x in gg.values())/n-r[part][k]))
   v[part]={k:r[part][k] for k in ['rootmean_mse','rootmean_game_equal_mse','z_mse','z_game_equal_mse','z_sign_accuracy','saturation_fraction']}
  cur.append(v)
 best=min(curve,key=lambda r:r['validation']['target_game_equal_mse']);assert best['step']==settings['best_step']==gate['best_step']==600
 improvement=curve[0]['validation']['target_game_equal_mse']-best['validation']['target_game_equal_mse'];assert improvement>=pr['gate_margin']==.0001 and curve_error<1e-12 and gate['status']=='GATE_MET'
 cfg=j(settings['config']);assert cfg['training']['steps']==2000 and cfg['training']['batch_size']==128 and cfg['training']['target']=='rootmean'
 assert sha(H/'finite-schema.json')==settings['schema_SHA'];assert schema['initial_distance_parity']['pass'] and schema['initial_distance_parity']['rows']==5901
 for p in [H/'preregister.json',H/'evaluator-settings.json',H/'gate-result.json',H/'finite-schema.json',H/'training-stop.json',H/'candidate-freeze.json',H/'runs/frame14-head-control-r1/history.jsonl']:bind(p)
 for p,h in freeze['sources'].items():assert sha(p)==h;bind(p)
 meta=rows(E/'canonical-export-r1/test-canonical.jsonl.gz');mask=j(E/'canonical-export-r1/fixed-newtest-mask.json');reference=j(E/'reference-binding.json');opening=j(E/'openings.json');prior=[]
 assert sha(E/'canonical-export-r1/test-canonical.jsonl.gz')=='707604264807ac59be11576ad7322f20dbbd484ff79bf69f41dbc17eebc41caf'
 assert sha(E/'canonical-export-r1/fixed-newtest-mask.json')=='80b2898a60d4afc5f274ac31b0ed476f6f6e1370f947ec2725ee733e81b0abff'
 for v in reference['references']:assert sha(v['path'])==v['SHA'];prior+=rows(v['path']);bind(v['path'])
 assert len(prior)==6996+1122 and mask['reference_metadata_SHA']==sha(E/'reference-binding.json') and mask['new_metadata_SHA']==sha(E/'canonical-export-r1/test-canonical.jsonl.gz')
 refs={k:{sig(r) if k=='QF1' else r[k] for r in prior} for k in ['state_key','history_key','QF1']};families={g['family'] for g in opening['games']};bygame={g['game_id']:g for g in opening['games']};assert len(families)==24 and not families&{r['group'] for r in prior}
 eg=collections.defaultdict(lambda:{'rows':0,'eligible':0});excluded=collections.Counter()
 for r in meta:
  assert not any(k in r for k in ['rootmean','z','winner','rootNN','loss','values']);assert r['split']=='test' and r['group']==bygame[r['game_id']]['family']
  exp=[{'state_key':'state','history_key':'history','QF1':'QF1'}[k] for k in refs if (sig(r) if k=='QF1' else r[k]) in refs[k]];mr=mask['rows'][r['id']];assert mr['primary_eligible']==(not exp) and mr['exposure']==sorted(exp) and mr['group']==r['group'];eg[r['group']]['rows']+=1;eg[r['group']]['eligible']+=not exp
  excluded.update(exp)
 assert set(eg)==set(mask['games'])==families and set(mask['rows'])=={r['id'] for r in meta};zero=sorted(k for k,v in eg.items() if not v['eligible']);assert zero==mask['zero_eligible_games']
 for p in [E/'reference-binding.json',E/'canonical-export-r1/test-canonical.jsonl.gz',E/'canonical-export-r1/fixed-newtest-mask.json',E/'openings.json',E/'science-stop-safe.json']:bind(p)
 write('source-curve-mask-result.json',{'head_source_subset':'out.weight/out.bias only; ft/h requires_grad False; optimizer uses overridden parameters()','tensor_bindings':tensor,'initial_coefficients':settings['coefficients'],'all21_curves':cur,'curve_aggregation_maxerror':curve_error,'BESTstep':600,'validation_improvement':improvement,'shared_validation_selection_limit':True,'planned':24,'metadata_rows':len(meta),'eligible_rows':sum(v['eligible'] for v in eg.values()),'Gplus':sum(bool(v['eligible']) for v in eg.values()),'zero_eligible_games':zero,'excluded_predicates':dict(excluded),'games':dict(eg),'independent_OR_matches':True,'reference_label_free_rows':len(prior),'bindings':bindings,'limits':['ZIP bytes identify frozen storages; not fresh model execution','history opaque; sharedRuleA teacher truth not recertified','no old test results or labels read']})
 final(start,meta,mask,freeze,bindings)
def final(start,meta,mask,before,bindings):
 fr=j(H/'test-freeze.json');owner=j(H/'test-evaluation-r1/result.json');receipt=j(H/'jobs/test-r1/process.json');started=j(H/'test-evaluation-r1/started.json')
 assert sha(H/'test-evaluation-r1/result.json')=='f8248c21afdacf48605c8960419906d78ad85f1a36e153cb9b91878c1bc58d27' and sha(H/'test-freeze.json')=='cd04dcc912bd5e5006a0fb843ec26b96697a62690565d0dcff7f1f6b1e48c584'
 assert sha(H/'test-freeze.json')==owner['freeze_SHA']==started['freeze_SHA'] and fr['candidate_freeze_SHA']==sha(H/'candidate-freeze.json')
 assert fr['UTC']<j(H/'jobs/test-freeze-r1/process.json')['UTC']<j(H/'jobs/test-r1/admission.json')['UTC']<receipt['UTC']
 for k in ['artifacts','coefficients','constant','train_config','bootstrap_seed','bootstrap_replicates','paired_comparisons']:assert fr[k]==before[k]
 assert fr['bootstrap_seed']==20480311 and fr['bootstrap_replicates']==2000 and fr['best_step']==600
 assert not fr['test_labels_read'] and not fr['old_test_labels_read'] and not fr['labels_read_before_freeze']
 assert sha(fr['metadata']['path'])==fr['metadata']['SHA'] and sha(fr['mask']['path'])==fr['mask']['SHA']
 for p,h in fr['sources'].items():assert sha(p)==h
 assert j(H/'test-open-once.json')['freeze_SHA']==owner['freeze_SHA']
 saved=rows(H/'test-evaluation-r1/per-row.jsonl.gz');by={r['id']:r for r in saved};assert len(by)==len(saved)==len(meta) and set(by)=={r['id'] for r in meta}
 names={'candidate','best','last','distance_only','constant'};gs=collections.defaultdict(list);phase=collections.defaultdict(list);cohort=collections.defaultdict(list);unknown=collections.Counter();diff=0
 for m in meta:
  r=by[m['id']];assert r['game']==m['group'] and r['mask']==mask['rows'][m['id']] and set(r['values'])==names
  for k in ['rootmean','z']:
   v=r[k];assert v is None or isinstance(v,(int,float)) and math.isfinite(v) and -1<=v<=1
   if v is None:unknown[k]+=1
  assert all(math.isfinite(v) and -1<=v<=1 for v in r['values'].values());assert r['values']['candidate']==r['values']['best'] and r['values']['constant']==fr['constant']
  s=f(f(m['distance'][1])-f(m['distance'][0]));p=max(-1,min(1,f(f(fr['coefficients']['a'])+f(f(fr['coefficients']['b'])*s))));diff=max(diff,abs(p-r['values']['distance_only']))
  if r['mask']['primary_eligible']:gs[r['game']].append(r);phase['early' if m['ply']<40 else 'middle' if m['ply']<100 else 'late'].append(r);cohort[m['cohort']].append(r)
 assert diff==0
 unique={(v['condition'],v['weight_SHA']) for v in fr['artifacts'].values()};assert len(unique)==owner['unique_NN_models']==2 and len(unique)*len(meta)==owner['samples']==receipt['samples_charged']<=12000
 def loss(rr,name,target):
  v=[float(r['values'][name]*r['z']>0) for r in rr if r['z'] not in (None,0)] if target=='z_sign' else [(r['values'][name]-r[target])**2 for r in rr if r[target] is not None]
  return avg(v)
 def stats(rr,name):
  gg=collections.defaultdict(list)
  for r in rr:gg[r['game']].append(r)
  z={'rows':len(rr),'games':len(gg)}
  for target in ['rootmean','z']:
   z[target+'_mse']=loss(rr,name,target);g=[loss(v,name,target) for v in gg.values()];z[target+'_game_equal_mse']=avg([x for x in g if x is not None]);z[target+'_rows']=sum(r[target] is not None for r in rr)
  z['z_sign_rows']=sum(r['z'] not in (None,0) for r in rr);z['z_sign_accuracy']=loss(rr,name,'z_sign');g=[loss(v,name,'z_sign') for v in gg.values()];z['z_sign_game_equal']=avg([x for x in g if x is not None]);z['saturation_fraction']=avg([float(abs(r['values'][name])>=.9) for r in rr]);return z
 err=0
 def compare(z,o):
  nonlocal err
  for k,v in z.items():
   if k not in o:continue
   if v is None:assert o[k] is None
   else:err=max(err,abs(v-o[k]))
 eligible=[r for rr in gs.values() for r in rr];models={}
 for name in sorted(names):
  z={'primary':stats(eligible,name),'secondary_all':stats(saved,name),'groups':{g:stats(rr,name) for g,rr in sorted(gs.items())},'phase':{k:stats(phase[k],name) for k in ['early','middle','late']},'cohorts':{k:stats(rr,name) for k,rr in sorted(cohort.items())}}
  compare(z['primary'],owner['models'][name]['primary']);compare(z['secondary_all'],owner['models'][name]['secondary_all'])
  for g,v in z['groups'].items():compare(v,owner['models'][name]['games'][g]['primary'])
  for k,v in z['phase'].items():compare(v,owner['models'][name]['phase'][k])
  for k,v in z['cohorts'].items():compare(v,owner['models'][name]['cohorts'][k])
  models[name]=z
 intervals={};keys=sorted(gs)
 for target in ['rootmean','z','z_sign']:
  intervals[target]={}
  for name,ref in fr['paired_comparisons']+[['distance_only','constant']]:
   vals=[loss(gs[g],name,target)-loss(gs[g],ref,target) for g in keys];rng=random.Random(20480311);bt=sorted(sum(rng.choice(vals) for _ in vals)/len(vals) for _ in range(2000));z={'groups':len(keys),'delta':sum(vals)/len(vals),'percentile95':[bt[49],bt[1949]],'replicates':2000,'seed':20480311};k=name+'_minus_'+ref;intervals[target][k]=z
   if k in owner['paired_intervals'][target]:
    o=owner['paired_intervals'][target][k];err=max(err,abs(z['delta']-o['delta']),*(abs(a-b) for a,b in zip(z['percentile95'],o['percentile95'])))
 assert err<1e-12
 costs=[]
 for p in sorted((H/'jobs').glob('*/process.json')):
  v=j(p);costs.append({'id':v['id'],'kind':v['kind'],'wall_s':v['wall_seconds'],'exit':v['exit'],'samples':v['samples_charged'],'wait':v['child_waited'],'remaining':v['remaining']});bindings[str(p)]=sha(p)
 for p in [H/'test-freeze.json',H/'test-evaluation-r1/result.json',H/'test-evaluation-r1/started.json',H/'test-evaluation-r1/per-row.jsonl.gz',H/'test-open-once.json']:bindings[str(p)]=sha(p)
 write('final-result.json',{'all_planned_games':24,'all_rows':len(saved),'eligible_rows':len(eligible),'Gplus':len(gs),'zero_eligible':mask['zero_eligible_games'],'excluded_rows':len(saved)-len(eligible),'unknown_targets':dict(unknown),'distance_analytic_maxabs':diff,'saved_arithmetic_maxerror':err,'models':models,'paired_intervals':intervals,'actual_unique':2,'actual_NN_samples':owner['samples'],'reuse':owner['prediction_reused'],'freeze_before_test_receipt':True,'bindings':bindings,'costs':{'204_guardian_attempts':costs,'204_allattempt_guardian_sum_s':sum(v['wall_s'] for v in costs),'training_guardian_s':j(H/'jobs/train-r1/process.json')['wall_seconds'],'training_samples':256000,'train_and_curve_samples':379921,'test_guardian_s':receipt['wall_seconds'],'test_internal_s':owner['elapsed_s'],'205_saved_safe_stop':j(E/'science-stop-safe.json'),'API_pipe_exclusive_CPU_add':0,'unmeasured_prep_analysis':'unknown'},'limits':['saved owner targets/predictions and sharedRuleA; no NN/teachertruth/legalitydeep recertification','24family bootstrap: within-game rows correlated; reused validation selected condition and checkpoint','OS physical isolation/all-human non-access not proved','test not used to reselect/fill/impute failures']})
 elapsed=time.monotonic()-start;assert elapsed<60 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<469762048
 write('stop.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'tick':pathlib.Path('/proc/self/stat').read_text().split()[21],'elapsed_s':elapsed,'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'arithmetic_charge_s':60,'source_read_charge_s':30,'static_total_conservative_s':90,'static_cap_s':120,'scientific_children':[],'NN_forward_model_GPU_train_game':0})
if __name__=='__main__':
 try:run()
 except BaseException as e:write('failure-'+datetime.datetime.now().strftime('%H%M%S')+'.json',{'type':type(e).__name__,'error':repr(e),'science_negative':False});raise
