import json,gzip,pathlib,hashlib,struct,math,collections,time,datetime,os,resource,zipfile,sys,random
D=pathlib.Path('research-data/ai-sigma/frame14-distance-independent')
H=pathlib.Path('research-data/ai-sigma/frame14-distance-residual')
A=pathlib.Path('research-data/ai-sigma/frame14-teachers/final-qf1-v2')
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def j(p): return json.loads(pathlib.Path(p).read_text())
def rows(p):
 with gzip.open(p,'rt') as h: return [json.loads(x) for x in h]
def write(n,v): (D/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def f(x): return struct.unpack('<f',struct.pack('<f',x))[0]
def avg(v): return math.fsum(v)/len(v)
def admit(phase):
 os.sched_setaffinity(0,{0}); now=datetime.datetime.now(datetime.timezone.utc)
 assert now.hour<2 or (now.hour==2 and now.minute<35), 'newcommand deadline'
 obs=j('.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/live-frame14-ee73f985-00e3-4a1c-960e-1e87143fb693/monitor-observation.json')
 assert obs.get('owned') is None, 'supervisor owned'
 at=datetime.datetime.fromisoformat(obs['at']); assert (now-at).total_seconds()<35, 'stale observer'
 nextslot=now.replace(minute=31,second=55,microsecond=281596)
 while nextslot<now: nextslot+=datetime.timedelta(minutes=20)
 assert (nextslot-now).total_seconds()>150,'supervisor next quiet window'
 heavy=[]
 for p in pathlib.Path('/proc').glob('[0-9]*'):
  try:
   c=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
   if any(t in c for t in ['worker.cjs','provider.py','faithful-native','ort.py','distance-test/generate.cjs','distance-residual/run.py','distance-residual/evaluate.py','nnue-training/train.py']) and int(p.name)!=os.getpid() and 'python3 - <<' not in c:
    heavy.append({'pid':int(p.name),'tick':(p/'stat').read_text().split()[21],'command':c[:400]})
  except (OSError,ValueError): pass
 assert not heavy, ('heavy current',heavy)
 before=sum(p.stat().st_size for p in D.iterdir() if p.is_file())
 forecast=102347236+4194304; assert forecast<117440512 and before<3670016
 write(phase+'-admission.json',{'UTC':now.isoformat(),'PID':os.getpid(),'tick':pathlib.Path('/proc/self/stat').read_text().split()[21],'CPU':[0],'RSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'guard':469762048,'supervisor_owned':None,'observation':obs['at'],'nextslot':nextslot.isoformat(),'current_heavy':heavy,'own_bytes':before,'old_retained':102347236,'new_allin_forecast':4194304,'forecast':forecast,'old_discount':0,'parent_add':0,'charge_this_phase':50 if phase=='mask' else 60})
 return time.monotonic()
def finish(phase,start):
 elapsed=time.monotonic()-start; assert elapsed<60 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<469762048
 write(phase+'-stop.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_s':elapsed,'charge_s':50 if phase=='mask' else 60,'PID':os.getpid(),'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'NN_model_forward_GPU_train':0,'source_children':[]})
def metrics(rs,pred):
 g=collections.defaultdict(list)
 for r in rs:g[r['group']].append(r)
 def one(rr):return {'rows':len(rr),'rootmeanMSE':avg([(pred(r)-r['rootmean'])**2 for r in rr]),'zMSE':avg([(pred(r)-r['z'])**2 for r in rr]),'sign':avg([float((pred(r)>0)-(pred(r)<0)==(r['z']>0)-(r['z']<0)) for r in rr])}
 gm={k:one(v) for k,v in sorted(g.items())};out=one(rs);out['games']=len(gm);out['game_equal']={k:avg([v[k] for v in gm.values()]) for k in ['rootmeanMSE','zMSE','sign']};return out
def early():
 start=admit('early'); meta=rows(A/'all144-metadata.jsonl.gz'); lab={r['id']:r for r in rows(A/'training-labels.jsonl.gz')};mask=j(A/'fixed-exposure-mask.json')
 rs=[dict(r,**{k:v for k,v in lab[r['id']].items() if k!='id'}) for r in meta if r['split'] in ['train','validation']]
 train=[r for r in rs if r['split']=='train'];val=[r for r in rs if r['split']=='validation']; assert len(train)==4653 and len(val)==1248
 counts=collections.Counter(r['group'] for r in train); assert len(counts)==96
 s=lambda r:f(r['distance'][1])-f(r['distance'][0]); w=lambda r:1/(96*counts[r['group']])
 sx=math.fsum(w(r)*s(r) for r in train);sy=math.fsum(w(r)*r['rootmean'] for r in train)
 var=math.fsum(w(r)*(s(r)-sx)**2 for r in train);cov=math.fsum(w(r)*(s(r)-sx)*(r['rootmean']-sy) for r in train);b=cov/var;a=sy-b*sx
 old=j('research-data/ai-sigma/frame14-representation-audit/result.json');pr=j(H/'preregister.json');freeze=j(H/'candidate-freeze-v2.json'); assert sha('research-data/ai-sigma/frame14-representation-audit/result.json')==freeze['coefficient_fit_SHA']
 assert abs(a-freeze['coefficients']['a'])<1e-13 and abs(b-freeze['coefficients']['b'])<1e-12 and abs(sy-freeze['constant'])<1e-13
 pred=lambda r:max(-1,min(1,f(f(a)+f(f(b)*f(s(r))))))
 analytic={'train_distance':metrics(train,pred),'validation_distance':metrics(val,pred),'train_constant':metrics(train,lambda r:sy),'validation_constant':metrics(val,lambda r:sy)}
 curves=[json.loads(x) for x in (H/'runs/frame14-distance-residual-r1/history.jsonl').read_text().splitlines()];assert len(curves)==21 and [x['step'] for x in curves]==list(range(0,2001,100))
 curve=[];maxerr=0
 for x in curves:
  assert x['train_samples_seen']==x['step']*128
  out={'step':x['step'],'samples':x['train_samples_seen']}
  for split,key in [('train','train_games'),('validation','validation_games')]:
   gg=x[key];n=sum(y['rows'] for y in gg.values());assert (n,len(gg))==((4653,96) if split=='train' else (1248,24))
   for k in ['rootmean_mse','z_mse','target_mse','constant_mse']:
    eq=avg([y[k] for y in gg.values()]);rw=math.fsum(y[k]*y['rows'] for y in gg.values())/n
    maxerr=max(maxerr,abs(eq-x[split][k.replace('_mse','_game_equal_mse')]),abs(rw-x[split][k]))
   out[split]={k:x[split][k] for k in ['rootmean_mse','rootmean_game_equal_mse','z_mse','z_game_equal_mse','z_sign_accuracy','saturation_fraction']}
  curve.append(out)
 assert maxerr<1e-12 and min(curves,key=lambda x:x['validation']['target_game_equal_mse'])['step']==0
 assert abs(analytic['validation_distance']['game_equal']['rootmeanMSE']-curves[0]['validation']['rootmean_game_equal_mse'])<1e-7
 bindings={}; tensors={}
 for name,v in freeze['artifacts'].items():
  assert sha(v['path'])==v['checkpoint_SHA'];zf=zipfile.ZipFile(v['path']);members=[n for n in zf.namelist() if '/data/' in n];members.sort(key=lambda n:int(n.rsplit('/',1)[1]));h=hashlib.sha256()
  for n in members:h.update(zf.read(n))
  tensors[name]={'raw_storage_SHA':h.hexdigest(),'receipt_weight_SHA':v['weight_SHA'],'matches':h.hexdigest()==v['weight_SHA']};bindings[v['path']]=sha(v['path'])
 assert all(v['matches'] for v in tensors.values())
 for p,h in freeze['sources'].items():assert sha(p)==h;bindings[p]=h
 for p in [H/'preregister.json',H/'gate-result.json',H/'initial-parity.json',H/'training-stop.json',H/'candidate-freeze.json',H/'candidate-freeze-v2.json',H/'schema-correction-v2.json',A/'all144-metadata.jsonl.gz',A/'training-labels.jsonl.gz',A/'fixed-exposure-mask.json']:bindings[str(p)]=sha(p)
 write('early-result.json',{'coefficient_fit':{'a':a,'b':b,'constant':sy,'mean_s':sx,'variance_s':var,'covariance':cov,'games':96,'rows':4653,'train_only':True},'analytic':analytic,'curves':curve,'all21_aggregation_maxerror':maxerr,'BESTstep':0,'NNUE_residual_validation_benefit':False,'tensor_storage_binding':tensors,'binding':bindings,'limits':['ZIP raw storages/file hashes bind saved weights; no tensor execution or semantic forward certification','initial abs+rtol parity is saved receipt only','outer clip derivative zero strictly outside range; out0 initially constrains lower-layer gradient','reused validation is selection/diagnostic, not fresh test','teacher/rootmean truth and shared RuleA legality not re-certified']})
 finish('early',start)
def signature(r):
 bits=[struct.unpack('<I',struct.pack('<f',v))[0] for v in r['distance']]
 payload=['QF1-f32-STM-v1',sorted(r['ids'][r['side']-1]),sorted(r['ids'][2-r['side']]),bits]
 return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def exposure():
 start=admit('mask'); E=pathlib.Path('research-data/ai-sigma/frame14-distance-test'); C=E/'canonical-export-r1';new=rows(C/'test-metadata.jsonl.gz');old=rows(A/'all144-metadata.jsonl.gz');mask=j(C/'fixed-newtest-mask.json');opening=j(E/'openings.json');families={g['family'] for g in opening['games']};games={g['game_id']:g for g in opening['games']}
 assert len(families)==len(games)==24 and len({r['id'] for r in new})==len(new)
 assert set(mask['games'])==families and mask['new_metadata_SHA']==sha(C/'test-canonical.jsonl.gz') and mask['reference_metadata_SHA']==sha(A/'all144-metadata.jsonl.gz')
 assert not mask['labels_used'] and set(mask['rows'])=={r['id'] for r in new}
 refs={k:{signature(r) if k=='QF1' else r[k] for r in old} for k in ['state_key','history_key','QF1']}
 oldfamilies={r['group'] for r in old};assert not families&oldfamilies
 derived=[];counts=collections.Counter();gg=collections.defaultdict(lambda:{'rows':0,'eligible':0,'excluded':0})
 for r in new:
  assert not any(k in r for k in ['rootmean','rootNN','z','winner','score','target','values']);assert r['split']=='test' and r['group']==games[r['game_id']]['family'];assert r['opening_ply']==games[r['game_id']]['target_ply']
  exp=[k for k in refs if (signature(r) if k=='QF1' else r[k]) in refs[k]];eligible=not exp
  assert eligible==mask['rows'][r['id']]['primary_eligible'];assert sorted({'state_key':'state','history_key':'history','QF1':'QF1'}[k] for k in exp)==mask['rows'][r['id']]['exposure'];g=gg[r['group']];g['rows']+=1;g['eligible']+=eligible;g['excluded']+=not eligible
  for k in exp:counts[k]+=1
  derived.append({'id':r['id'],'group':r['group'],'signature':signature(r),'eligible':eligible,'exposure':exp})
 assert set(gg)==families
 zero=[k for k,v in gg.items() if not v['eligible']];assert sorted(zero)==sorted(mask['zero_eligible_games'])
 freeze=j(H/'candidate-freeze-v2.json');binding={str(p):sha(p) for p in [C/'test-metadata.jsonl.gz',C/'test-canonical.jsonl.gz',C/'fixed-newtest-mask.json',E/'openings.json',A/'all144-metadata.jsonl.gz',H/'candidate-freeze-v2.json']}
 write('mask-result.json',{'planned_games':24,'actual_games':len(gg),'rows':len(new),'eligible_rows':sum(v['eligible'] for v in gg.values()),'Gplus':sum(bool(v['eligible']) for v in gg.values()),'zero_eligible':zero,'excluded_predicates':dict(counts),'groups':dict(gg),'opening_cohorts':dict(collections.Counter(g['target_ply'] for g in opening['games'])),'independent_OR_predicate_match':True,'family_overlap_old144':0,'binding':binding,'candidate_step':freeze['best_step'],'limits':['history_key owner opaque after initial prefix; no new deep RuleA proof','new labels, winners, raw, journals, mixedstatus and old test labels remain unread','metadata signatures are label-free; OS/all-people non-access not guaranteed']})
 finish('mask',start)
def final():
 start=admit('final');freeze=j(H/'test-freeze.json');before=j(H/'candidate-freeze-v2.json');out=H/'test-evaluation-r1';receipt=j(H/'jobs/test-evaluate-r1/process.json');owner=j(out/'result.json');initial=j(out/'started.json')
 assert receipt['exit']==0 and receipt['child_waited'] and receipt['remaining']==[] and receipt['current_exact_identity_absent']
 assert freeze['UTC']<j(H/'jobs/test-bind-r1/process.json')['UTC']<receipt['UTC']
 assert j(H/'jobs/test-bind-r1/process.json')['UTC']<j(H/'jobs/test-evaluate-r1/admission.json')['UTC']<receipt['UTC']
 assert owner['freeze_SHA']==initial['freeze_SHA']==sha(H/'test-freeze.json') and freeze['candidate_freeze_SHA']==sha(H/'candidate-freeze-v2.json')
 for k in ['artifacts','coefficients','constant','train_config','paired_comparisons','bootstrap_seed','bootstrap_replicates']:assert freeze[k]==before[k]
 assert freeze['bootstrap_seed']==20080311 and freeze['bootstrap_replicates']==2000 and freeze['best_step']==0
 assert freeze['test_labels_read'] is False and freeze['labels_read_before_freeze'] is False and freeze['old_test_labels_read'] is False
 parity=j(H/'initial-parity.json');assert parity['rows']==5901 and parity['pass'] and parity['max_residual_abs']==0
 for p,h in freeze['sources'].items():assert sha(p)==h
 for name in ['metadata','mask']:assert sha(freeze[name]['path'])==freeze[name]['SHA']
 assert j(H/'test-open-once.json')['freeze_SHA']==sha(H/'test-freeze.json')
 meta=rows(freeze['metadata']['path']);plain=rows('research-data/ai-sigma/frame14-distance-test/canonical-export-r1/test-metadata.jsonl.gz');assert {r['id']:signature(r) for r in meta}=={r['id']:signature(r) for r in plain}
 mask=j(freeze['mask']['path']);saved=rows(out/'per-row.jsonl.gz');by={r['id']:r for r in saved};assert len(by)==len(saved)==len(meta)==1122 and set(by)=={r['id'] for r in meta}
 names=set(saved[0]['values']);expected=set(freeze['artifacts'])|{'distance_only','constant'};assert names==expected
 allr=[];groups=collections.defaultdict(list);phases=collections.defaultdict(list);cohorts=collections.defaultdict(list)
 diff=0;unknown=collections.Counter()
 for m in meta:
  r=by[m['id']];assert r['game']==m['group'] and r['mask']==mask['rows'][r['id']];assert set(r['values'])==expected
  for k in ['rootmean','z']:
   v=r[k];assert v is None or isinstance(v,(int,float)) and math.isfinite(v) and -1<=v<=1
   if v is None:unknown[k]+=1
  assert all(math.isfinite(v) and -1<=v<=1 for v in r['values'].values())
  assert r['values']['constant']==freeze['constant']
  s=f(f(m['distance'][1])-f(m['distance'][0]));p=max(-1,min(1,f(f(freeze['coefficients']['a'])+f(f(freeze['coefficients']['b'])*s))));diff=max(diff,abs(p-r['values']['distance_only']))
  assert r['values']['candidate']==r['values']['best']==r['values']['distance_initial']==r['values']['distance_only']
  allr.append(r)
  if r['mask']['primary_eligible']:
   groups[r['game']].append(r);phases['early' if m['ply']<40 else 'middle' if m['ply']<100 else 'late'].append(r);cohorts[m['cohort']].append(r)
 assert diff==0 and len(groups)==24 and sum(map(len,groups.values()))==1122 and not mask['zero_eligible_games']
 unique={(x['condition'],x['weight_SHA']) for x in freeze['artifacts'].values()};assert len(unique)==owner['unique_NN_models']==3 and len(unique)*len(meta)==owner['samples']==receipt['samples_charged']==3366<=12000
 def loss(rr,name,target):
  if target=='z_sign':v=[float(r['values'][name]*r['z']>0) for r in rr if r['z'] not in (None,0)]
  else:v=[(r['values'][name]-r[target])**2 for r in rr if r[target] is not None]
  return avg(v) if v else None
 def stat(rr,name):
  g=collections.defaultdict(list)
  for r in rr:g[r['game']].append(r)
  v={'rows':len(rr),'games':len(g)}
  for target in ['rootmean','z']:
   v[target+'_mse']=loss(rr,name,target);ll=[loss(x,name,target) for x in g.values()];ll=[x for x in ll if x is not None];v[target+'_game_equal_mse']=avg(ll) if ll else None;v[target+'_rows']=sum(r[target] is not None for r in rr)
  v['z_sign_rows']=sum(r['z'] not in (None,0) for r in rr);v['z_sign_accuracy']=loss(rr,name,'z_sign');ll=[loss(x,name,'z_sign') for x in g.values()];ll=[x for x in ll if x is not None];v['z_sign_game_equal']=avg(ll) if ll else None
  v['saturation_fraction']=avg([float(abs(r['values'][name])>=.9) for r in rr]) if rr else None;return v
 maxerror=0;models={}
 def compare(calc,supplied):
  nonlocal maxerror
  for k,v in calc.items():
   if k not in supplied:continue
   if v is None:assert supplied[k] is None
   else:maxerror=max(maxerror,abs(v-supplied[k]))
 for name in sorted(names):
  z={'primary':stat(allr,name),'groups':{g:stat(rr,name) for g,rr in sorted(groups.items())},'phase':{k:stat(phases[k],name) for k in ['early','middle','late']},'cohorts':{k:stat(rr,name) for k,rr in sorted(cohorts.items())}}
  compare(z['primary'],owner['models'][name]['primary']);compare(z['primary'],owner['models'][name]['secondary_all'])
  for g,m in z['groups'].items():compare(m,owner['models'][name]['games'][g]['primary'])
  for k,m in z['phase'].items():compare(m,owner['models'][name]['phase'][k])
  for k,m in z['cohorts'].items():compare(m,owner['models'][name]['cohorts'][k])
  models[name]=z
 intervals={};keys=sorted(groups)
 for target in ['rootmean','z','z_sign']:
  intervals[target]={}
  for name,ref in freeze['paired_comparisons']+[['distance_only','constant']]:
   vals=[loss(groups[g],name,target)-loss(groups[g],ref,target) for g in keys];rng=random.Random(20080311);bts=sorted(sum(rng.choice(vals) for _ in vals)/len(vals) for _ in range(2000));v={'groups':24,'delta':sum(vals)/24,'percentile95':[bts[49],bts[1949]],'seed':20080311,'replicates':2000};key=name+'_minus_'+ref;intervals[target][key]=v
   if key in owner['paired_intervals'][target]:
    ov=owner['paired_intervals'][target][key];maxerror=max(maxerror,abs(v['delta']-ov['delta']),*(abs(x-y) for x,y in zip(v['percentile95'],ov['percentile95'])))
 assert maxerror<1e-12
 bindings={str(p):sha(p) for p in [H/'test-freeze.json',H/'candidate-freeze-v2.json',H/'test-open-once.json',out/'result.json',out/'started.json',out/'per-row.jsonl.gz',H/'jobs/test-evaluate-r1/process.json']};costs=[]
 for p in sorted((H/'jobs').glob('*/process.json')):
  v=j(p);costs.append({'id':v['id'],'kind':v['kind'],'wall_s':v['wall_seconds'],'exit':v['exit'],'samples':v['samples_charged'],'wait':v['child_waited'],'remaining':v['remaining']});bindings[str(p)]=sha(p)
 E=pathlib.Path('research-data/ai-sigma/frame14-distance-test');gen=j(E/'science-stop.json');ledger=j(E/'cost-ledger.json');bindings[str(E/'science-stop.json')]=sha(E/'science-stop.json');bindings[str(E/'cost-ledger.json')]=sha(E/'cost-ledger.json')
 classification={'distance_vs_constant':'supported for these fresh games' if intervals['rootmean']['distance_only_minus_constant']['percentile95'][1]<0 else 'insufficient','residual_BEST_vs_distance':'not supported: exact same saved predictions','residual_LAST_vs_distance':'rootmean deterioration supported; z/sign difference uncertain','strength_NI':'not established'}
 write('final-result.json',{'all_planned':24,'actual_games':24,'Gplus':24,'all_rows':1122,'eligible_rows':1122,'excluded_rows':0,'unknown_targets':dict(unknown),'independent_analytic_distance_maxabs':diff,'saved_metric_bootstrap_maxerror':maxerror,'models':models,'paired_intervals':intervals,'actual_NN_unique':3,'actual_NN_samples':3366,'NN_reuse_receipt':owner['prediction_reused'],'freeze_before_first_test_receipt':True,'binding':bindings,'costs':{'200_all_guardian_attempts':costs,'200_guardian_sum_s':sum(v['wall_s'] for v in costs),'200_train_samples':256000,'200_all_training_and_evaluation_samples':379921,'test_receipt_wall_s':receipt['wall_seconds'],'test_owner_internal_s':owner['elapsed_s'],'201_generation_guardian_s':gen['jobwall_s'],'201_workerNN':gen['logical_workerNN'],'201_provider_calls':gen['physical_provider']['result']['calls'],'201_provider_rows':gen['physical_provider']['result']['rows'],'201_terminal_noNN':ledger['terminal_noNN'],'201_discarded_NN':ledger['discarded_NN'],'201_owner_ledger_saved':ledger,'unmeasured_prep_analysis':'unknown','API_pipe_CPU_addition':0},'classification':classification,'limits':['per-row targets and model predictions are saved owner outputs, not new teacher truth or model forward certification','full game legality/deep teacher/backend proof not added','24 independent families only; phase/game row correlation preserved by family bootstrap','shared history/RuleA/source and no global OS-sealing proof','clip/head0 restrictions do not identify unique generalization-failure cause','all guardian wall sums are attempts, not exclusive CPU cycles; prep unknown']})
 finish('final',start)
if __name__=='__main__':
 try: {'early':early,'mask':exposure,'final':final}[sys.argv[1] if len(sys.argv)>1 else 'early']()
 except Exception as e:
  write('checker-failure-'+datetime.datetime.now().strftime('%H%M%S')+'.json',{'type':type(e).__name__,'error':str(e),'science_negative':False});raise
