import json,gzip,pathlib,hashlib,struct,math,collections,time,datetime,os,resource,zipfile,sys
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
 write(phase+'-admission.json',{'UTC':now.isoformat(),'PID':os.getpid(),'tick':pathlib.Path('/proc/self/stat').read_text().split()[21],'CPU':[0],'RSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'guard':469762048,'supervisor_owned':None,'observation':obs['at'],'nextslot':nextslot.isoformat(),'current_heavy':heavy,'own_bytes':before,'old_retained':102347236,'new_allin_forecast':4194304,'forecast':forecast,'old_discount':0,'parent_add':0,'charge_this_phase':60})
 return time.monotonic()
def finish(phase,start):
 elapsed=time.monotonic()-start; assert elapsed<60 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<469762048
 write(phase+'-stop.json',{'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_s':elapsed,'charge_s':60,'PID':os.getpid(),'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'NN_model_forward_GPU_train':0,'source_children':[]})
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
 assert set(mask['games'])==families and mask['new_metadata_SHA']==sha(C/'test-metadata.jsonl.gz') and mask['reference_metadata_SHA']==sha(A/'all144-metadata.jsonl.gz')
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
 freeze=j(H/'candidate-freeze-v2.json');binding={str(p):sha(p) for p in [C/'test-metadata.jsonl.gz',C/'fixed-newtest-mask.json',E/'openings.json',A/'all144-metadata.jsonl.gz',H/'candidate-freeze-v2.json']}
 write('mask-result.json',{'planned_games':24,'actual_games':len(gg),'rows':len(new),'eligible_rows':sum(v['eligible'] for v in gg.values()),'Gplus':sum(bool(v['eligible']) for v in gg.values()),'zero_eligible':zero,'excluded_predicates':dict(counts),'groups':dict(gg),'opening_cohorts':dict(collections.Counter(g['target_ply'] for g in opening['games'])),'independent_OR_predicate_match':True,'family_overlap_old144':0,'binding':binding,'candidate_step':freeze['best_step'],'limits':['history_key owner opaque after initial prefix; no new deep RuleA proof','new labels, winners, raw, journals, mixedstatus and old test labels remain unread','metadata signatures are label-free; OS/all-people non-access not guaranteed']})
 finish('mask',start)
if __name__=='__main__':
 try: {'early':early,'mask':exposure}[sys.argv[1] if len(sys.argv)>1 else 'early']()
 except Exception as e:
  write('checker-failure-'+datetime.datetime.now().strftime('%H%M%S')+'.json',{'type':type(e).__name__,'error':str(e),'science_negative':False});raise
