import pathlib,json,gzip,hashlib,math,os,datetime,time,resource,zipfile
D=pathlib.Path('research-data/ai-sigma/frame15-learning-diagnostic-independent');S=pathlib.Path('research-data/ai-sigma/frame15-learning-diagnostic');P=S/'runs/frame15-learning-diagnostic-lr1e-4-seed19080312-r1';start=time.monotonic();os.sched_setaffinity(0,{0})
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def lines(p):
 with gzip.open(p,'rt')as f:return [json.loads(s)for s in f]
def near(a,b,tol=1e-10):assert abs(a-b)<tol,(a,b)
state=read('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');now=datetime.datetime.now(datetime.timezone.utc);assert state['owned'] is None;assert state['next_at']-now.timestamp()>150
current=[]
for p in pathlib.Path('/proc').glob('[0-9]*'):
 try:
  argv=(p/'cmdline').read_bytes().split(b'\0');exe=argv[0].decode();script=next((v.decode()for v in argv[1:]if v.endswith((b'.py',b'.cjs'))),'')
  if ('python'in exe or 'node'in exe) and any(s in script for s in ['ai-sigma-learning-diagnostic/','nnue-training/train.py','ai-sigma-frame14','ai-sigma-qf1']) and not script.endswith(('/save.py','/save_git.py','/summarize.py','/plot_curves.py')):current.append({'pid':int(p.name),'script':script})
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
assert not current,current
process=read(S/'jobs/train-seed19080312-r1/process.json');assert process['exit']==0 and process['child_waited'] and not process['remaining'];p=pathlib.Path('/proc')/str(process['identity']['pid']);assert not p.exists() or p.joinpath('stat').read_text().split(') ')[1].split()[19]!=process['identity']['tick']
tick=pathlib.Path('/proc/self/stat').read_text().split(') ')[1].split()[19]
(D/'fourth-admission.json').write_text(json.dumps({'UTC':now.isoformat(),'PID':os.getpid(),'tick':tick,'CPU':[0],'RSS':int(pathlib.Path('/proc/self/status').read_text().split('VmRSS:')[1].split()[0])*1024,'guard':469762048,'supervisor_owned':None,'next_at':state['next_at'],'current_science':current,'owner_stop_receipt':process,'static_before':120,'remaining':60,'max_job_s':60,'forecast':112832996,'critic_guard':117440512},indent=2)+'\n')
pr=read(S/'fourth-preregister.json');bindings={str(S/'fourth-preregister.json'):sha(S/'fourth-preregister.json'),str(S/'jobs/train-seed19080312-r1/process.json'):sha(S/'jobs/train-seed19080312-r1/process.json')}
for path,h in pr['sources'].items():assert sha(path)==h;bindings[path]=h
cfg=read(P/'config.json');oldcfg=read(S/'runs/frame15-learning-diagnostic-lr1e-4-r1/config.json');assert cfg['training']['seed']==19080312;oldcfg['training']['seed']=19080312
# Sample cap differs solely because evaluation schedule differs.
assert cfg['limits']['samples']==74804;oldcfg['limits']['samples']=74804;assert cfg==oldcfg
hist=lines(P/'history.jsonl.gz');witness=lines(P/'witness.jsonl.gz');obs=read(P/'observer.json');summary=read(P/'summary.json');data=read(P/'dataset.json');old=read(D/'result.json');labels=lines('research-data/ai-sigma/frame14-teachers/final-qf1-v2/training-labels.jsonl.gz');labelmap={r['id']:r for r in labels}
for name in ['config.json','summary.json','history.jsonl.gz','witness.jsonl.gz','observer.json','dataset.json']:bindings[str(P/name)]=sha(P/name)
assert [h['step']for h in hist]==[0,100,200,400]==pr['points']==obs['evaluation_points'];assert [o['step']for o in obs['observations']]==[100,200,400]
assert data['counts']=={'train':4653,'validation':1248} and data['groups']=={'train':96,'validation':24};assert data['train_sha256']=='133ea3f8415f311091741a056034f72ed7f3bedf491fcbb1d5ed9f73ea2572be' and data['validation_sha256']=='d4b5b218fcfaaa548fb9a2ee3056f34b21e4ed63143e67f6e7aa94f7934cd7e3'
assert data['initial_state_sha256']==obs['initial_tensor_SHA']!=old['conditions']['lr1e-4'].get('initial_tensor_SHA','e5d218c9750d581eab7ca6a114acaa8f3cf5bd24474e3f639280705271fc7ddb');assert obs['batch_order_400_SHA']!='83eb87b84b93624cd96ff7fac2b860f8fe38af2b5015a86462377a06ffd17771';assert obs['observer_extra_forward']==obs['observer_extra_backward']==0
curve=[];maxerr=0
for h,w in zip(hist,witness):
 assert h['step']==w['step'];assert h['all_samples']==h['step']*128+(pr['points'].index(h['step'])+1)*5901;assert h['train_samples_seen']==h['step']*128;near(h['train_epochs_equivalent'],h['step']*128/4653)
 for split,games,n in [('train','train_games',96),('validation','validation_games',24)]:
  gs=list(h[games].values());assert len(gs)==n and sum(g['rows']for g in gs)==h[split]['rows']
  for metric in ['rootmean','target','z','constant']:
   avg=sum(g[metric+'_mse']for g in gs)/n;near(avg,h[split][metric+'_game_equal_mse']);maxerr=max(maxerr,abs(avg-h[split][metric+'_game_equal_mse']));near(sum(g[metric+'_mse']*g['rows']for g in gs)/sum(g['rows']for g in gs),h[split][metric+'_mse'])
 assert sorted(w['IDs'])==old['conditions']['lr1e-4']['witness_IDS'];changes=[]
 for r in w['rows']:
  near(r['target_rootmean'],labelmap[r['id']]['rootmean']);near(r['residual'],r['prediction']-r['target_rootmean']);near(math.tanh(r['pre_tanh']),r['prediction'],2e-7);changes.append(r['prediction']-r['prediction_step0'])
 near(w['prediction_step0_RMS_change'],math.sqrt(sum(c*c for c in changes)/12));near(w['prediction_step0_maxabs_change'],max(map(abs,changes)))
 curve.append({'step':h['step'],'train':h['train']['target_game_equal_mse'],'validation':h['validation']['target_game_equal_mse'],'validation_row':h['validation']['target_mse'],'validation_z':h['validation']['z_game_equal_mse'],'validation_sign':h['validation']['z_sign_accuracy'],'val_saturation':h['validation']['saturation_fraction'],'epoch':h['train_epochs_equivalent'],'train_samples':h['train_samples_seen'],'witness_RMS':w['prediction_step0_RMS_change'],'witness_max':w['prediction_step0_maxabs_change']})
primary=hist[2];initial=hist[0];differences={g:primary['validation_games'][g]['target_mse']-initial['validation_games'][g]['target_mse']for g in primary['validation_games']};delta=sum(differences.values())/24;near(delta,primary['validation']['target_game_equal_mse']-initial['validation']['target_game_equal_mse'])
assert summary['all_samples']==process['samples_charged']==74804;assert 330630+74804==pr['all4_actual_science_samples_forecast']==405434
best=min(hist,key=lambda h:h['validation']['target_game_equal_mse']);assert best['step']==summary['best_step'];near(summary['best_validation_mse'],best['validation']['target_game_equal_mse'])
for o in obs['observations']:
 for v in o['layers'].values():assert v['gradient_all_finite'];near(v['update_to_weight_ratio'],v['actual_update_norm']/v['weight_norm_before'])
cp=pathlib.Path(summary['checkpoint_dir'])/'initial.pt'
with zipfile.ZipFile(cp)as z:
 members=sorted((n for n in z.namelist()if '/data/'in n and n.rsplit('/',1)[1].isdigit()),key=lambda n:int(n.rsplit('/',1)[1]));assert len(members)==6;assert hashlib.sha256(b''.join(z.read(n)for n in members)).hexdigest()==data['initial_state_sha256']
bindings[str(cp)]=sha(cp)
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'primary_delta200_own0':delta,'improved_games':sum(d<0 for d in differences.values()),'paired_game_differences':differences,'curve':curve,'initial_tensor_SHA':data['initial_state_sha256'],'batch400_SHA':obs['batch_order_400_SHA'],'initial_and_sampling_both_changed':True,'primary_minus_constant':primary['validation']['target_game_equal_mse']-pr['constant_validation'],'primary_minus_distance':primary['validation']['target_game_equal_mse']-pr['distance_validation'],'max_aggregation_error':maxerr,'observer':obs['observations'],'fourth_actual_samples':74804,'all4_samples':405434,'fourth_guardian_wall':process['wall_seconds'],'all4_heavy_guardian_wall':old['heavy_wall_sum']+process['wall_seconds'],'bindings':bindings,'static_charge':180,'static_cap':180,'new_forward':0,'limits':['same reused validation, two joint seeds only','saved group/12witness and initial ZIP bytes; no new forward/teachertruth','primary200 pre-fixed; best descriptive only']}
(D/'fourth-result.json').write_text(json.dumps(result,indent=2)+'\n');(D/'fourth-stop.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'tick':tick,'CPU':[0],'elapsed_s':time.monotonic()-start,'peak_RSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'children':[],'exit':0,'charge':180,'cap':180},indent=2)+'\n')
print(json.dumps({k:result[k]for k in ['primary_delta200_own0','improved_games','primary_minus_constant','primary_minus_distance','max_aggregation_error','all4_samples','all4_heavy_guardian_wall']}))
