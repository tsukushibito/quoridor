"""229 final independent saved arithmetic, stdlib only; no model evaluation."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,math,random,resource,struct,time
P=Path('research-data/ai-sigma/frame18-data-learning');D=Path('research-data/ai-sigma/frame18-growth-learning-independent');t=time.monotonic();bindings={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 p=Path(p);bindings[str(p)]=sha(p);return json.loads(p.read_text())
def rows(p):
 p=Path(p);bindings[str(p)]=sha(p)
 with gzip.open(p,'rt')as f:return [json.loads(s)for s in f if s.strip()]
def near(a,b):assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-10),(a,b)
def aggregate(g):
 n=sum(v['rows']for v in g.values());o={'rows':n,'games':len(g)}
 for m in ['rootmean','z']:
  key=m+'_mse';o[key]=sum(v[key]*v['rows']for v in g.values())/n
  o[m+'_game_equal_mse']=sum(v[key]for v in g.values())/len(g)
 for key in ['z_sign_accuracy','saturation_fraction']:
  o[key]=sum(v[key]*v['rows']for v in g.values())/n
 return o
def metrics(rr,values):
 groups=collections.defaultdict(list)
 for r,v in zip(rr,values):groups[r['group']].append((r,v))
 g={}
 for k,q in groups.items():
  n=len(q);g[k]={'rows':n,'rootmean_mse':sum((v-r['rootmean'])**2 for r,v in q)/n,'z_mse':sum((v-r['z'])**2 for r,v in q)/n,'z_sign_accuracy':sum((v>0)==(r['z']>0) for r,v in q)/n,'saturation_fraction':sum(abs(v)>=.999999 for r,v in q)/n}
 return aggregate(g),g
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
freeze=read(P/'candidate-freeze-v1.json');stop=read(P/'scientific-final-stop.json');result=read(P/'test-evaluation-r1/result.json');pg=read(P/'test-evaluation-r1/pergame.json');acc=read(P/'test-evaluation-r1/access-start.json');proc=read(P/'learning-guardian/test-r1/process.json')
assert freeze['UTC']<acc['UTC']<proc['startUTC'] and result['freeze_SHA']==sha(P/'candidate-freeze-v1.json') and not result['test_reselection']
for p,h in freeze['artifacts'].items():assert sha(p)==h;bindings[p]=h
assert freeze['selected_stage']==576 and freeze['best_step']==2000 and result['samples']==2*4847
meta=rows(P/'dataset-v1/adapter/canonical.jsonl.gz');byid={r['id']:r for r in meta};plan=read(P/'dataset-v1/plan.json');labels=rows(plan['training_labels_advertised']['path']);assert sha(plan['training_labels_advertised']['path'])==plan['training_labels_advertised']['sha256'];lab={r['id']:r for r in labels};assert all(byid[k]['split']!='test' for k in lab)
curves={};baselines={};parity={};summaries={}
for G,N in [(192,9025),(576,27463)]:
 run=P/f'learning-runs/frame18-growth228-plan{G}-positive{G}-r1';hp=run/'history.jsonl';bindings[str(hp)]=sha(hp);hist=[json.loads(s)for s in hp.read_text().splitlines()];summaries[G]=read(run/'summary.json');parity[G]=read(run/'initial-function-parity.json');obs=read(run/'observer.json');assert parity[G]['PASS'] and obs['observer_additional_forward']==0 and not obs['test_labels_read']
 assert [v['step']for v in hist]==[0,1,2,5,10,20,50,100,200,400,800,1200,2000]
 curves[G]=[]
 for v in hist:
  assert v['train_samples_seen']==128*v['step'];near(v['train_epochs_equivalent'],128*v['step']/N)
  for phase in ['train','validation']:
   a=aggregate(v[phase+'_games']);assert a['games']==(G if phase=='train'else96)
   for k,x in a.items():near(x,v[phase][k])
  curves[G].append({'step':v['step'],'samples':v['train_samples_seen'],'epoch':v['train_epochs_equivalent'],'train':aggregate(v['train_games']),'validation':aggregate(v['validation_games'])})
 best=min(hist,key=lambda v:(v['validation']['rootmean_game_equal_mse'],v['step']));assert best['step']==summaries[G]['best_step'];near(best['validation']['rootmean_game_equal_mse'],summaries[G]['best_validation_mse'])
 rr=[dict(r,**lab[r['id']])for r in meta if r['split']=='train'and r['train_slot']<=G];assert len(rr)==N
 counts=collections.Counter(r['group']for r in rr);pts=[(1/(G*counts[r['group']]),f32(r['distance'][1]-r['distance'][0]),r['rootmean'])for r in rr]
 mx=sum(w*x for w,x,y in pts);my=sum(w*y for w,x,y in pts);var=sum(w*(x-mx)**2 for w,x,y in pts);b=sum(w*(x-mx)*(y-my)for w,x,y in pts)/var;a=my-b*mx
 base=read(P/f'learning-plan-v1/baseline-{G}.json');near(a,base['fit']['a']);near(b,base['fit']['b']);near(my,base['fit']['constant']);baselines[G]={'a':a,'b':b,'constant':my,'train_only':True,'variance':var,'owner_metrics':base['metrics']}
selection=min(summaries,key=lambda g:(summaries[g]['best_validation_mse'],g,summaries[g]['best_step']));assert selection==freeze['selected_stage'];assert freeze['baseline_fit']==read(P/'learning-plan-v1/baseline-576.json')['fit']
test=rows(P/'test-evaluation-r1/predictions.jsonl.gz');assert len(test)==4847 and len({r['id']for r in test})==4847 and all(byid[r['id']]['split']=='test'and r['primary_eligible']for r in test);assert len({r['group']for r in test})==96
metrics_out={}
fit=freeze['baseline_fit']
for r in test:
 m=byid[r['id']];s=f32(m['distance'][1]-m['distance'][0]);pred=max(-1,min(1,f32(fit['a_f32']+f32(fit['b_f32']*s))));near(pred,r['prediction']['distance']);near(fit['constant'],r['prediction']['constant'])
for name in ['candidate','initial','distance','constant']:
 a,g=metrics(test,[r['prediction'][name]for r in test]);metrics_out[name]=a
 for k,x in a.items():near(x,result['models'][name]['primary'][k])
 for k in g:
  for m,x in g[k].items():near(x,pg[name][k][m])
 assert set(g)==set(pg[name])
boot={};groups=list(pg['candidate'])
for base in ['distance','constant','initial']:
 for target in ['rootmean','z']:
  delta=[pg['candidate'][g][target+'_mse']-pg[base][g][target+'_mse']for g in groups]
  # choices uses floating random(), preserve saved evaluator draw convention.
  rng=random.Random(freeze['bootstrap']['seed']);b=sorted(sum(rng.choices(delta,k=96))/96 for _ in range(2000))
  q={'games':96,'delta':sum(delta)/96,'percentile95':[b[50],b[1950]],'gain_games':sum(d<0 for d in delta)};owner=result['paired_fixedfit_bootstrap'][base+'_'+target]
  near(q['delta'],owner['delta']);assert q['gain_games']==owner['gain_games']
  for x,y in zip(q['percentile95'],owner['percentile95']):near(x,y)
  boot[base+'_'+target]=q
cost={'NN':sum(x['samples_actual']for x in stop['learning_test_processes']),'guardian_s':sum(x['wall_s']for x in stop['learning_test_processes']),'generation_NN':1849212,'generation_guardian_s':2175.6067399219028,'overlap_queuewait_not_added':True,'whole_team_management_UNKNOWN':True};assert cost['NN']==1167290
for p,h in bindings.items():assert sha(p)==h,('MUTATED',p)
secondary={'small400':next(v for v in curves[192]if v['step']==400),'large1200':next(v for v in curves[576]if v['step']==1200),'nonselection':True,'step_per_game_equal':400/192==1200/576}
out={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PASS':True,'source_input_SHA':bindings,'curves':curves,'train_only_baselines':baselines,'selected_stage':selection,'initial_parity_saved_receipts':parity,'test_metrics':metrics_out,'paired_bootstrap':boot,'secondary':secondary,'cost':cost,'newNN':0,'scope_limit':'saved predictions and receipts; no current forward or teachertruth reauthentication; fixed-fit game intervals not all selection/teacher/IID uncertainty','calc_s':time.monotonic()-t,'peakRSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
(D/'final-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['PASS','selected_stage','paired_bootstrap','cost','calc_s','peakRSS']}))
