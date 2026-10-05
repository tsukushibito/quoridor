import pathlib,json,gzip,hashlib,math,zipfile,os,datetime,time,resource
D=pathlib.Path('research-data/ai-sigma/frame15-learning-diagnostic-independent');S=pathlib.Path('research-data/ai-sigma/frame15-learning-diagnostic');start=time.monotonic();os.sched_setaffinity(0,{0})
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text())
def lines(p):
 with gzip.open(p,'rt') as f:return [json.loads(s)for s in f]
def near(a,b,tol=1e-10):assert abs(a-b)<tol,(a,b)
statepath=pathlib.Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json');state=read(statepath);now=datetime.datetime.now(datetime.timezone.utc);assert state['owned'] is None;assert state['next_at']-now.timestamp()>150
current=[]
for p in pathlib.Path('/proc').glob('[0-9]*'):
 try:
  argv=(p/'cmdline').read_bytes().split(b'\0');exe=argv[0].decode();script=next((v.decode()for v in argv[1:] if v.endswith((b'.py',b'.cjs'))),'')
  if ('python' in exe or 'node' in exe) and any(t in script for t in ['ai-sigma-learning-diagnostic/','nnue-training/train.py','ai-sigma-frame14','ai-sigma-qf1']) and not script.endswith(('/save.py','/save_git.py')):
   current.append({'pid':int(p.name),'script':script,'tick':(p/'stat').read_text().split(') ')[1].split()[19]})
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
assert not current,current
stop=read(S/'science-stop.json');assert stop['all_children_waited'] and not stop['current_exact_remaining'] and stop['source_science_stopped']
for j in (S/'jobs').glob('train-*/process.json'):
 x=read(j);assert x['exit']==0 and x['child_waited'] and not x['remaining'];p=pathlib.Path('/proc')/str(x['identity']['pid']);assert not p.exists() or p.joinpath('stat').read_text().split(') ')[1].split()[19]!=x['identity']['tick']
mytick=pathlib.Path('/proc/self/stat').read_text().split(') ')[1].split()[19]
(D/'admission.json').write_text(json.dumps({'UTC':now.isoformat(),'PID':os.getpid(),'tick':mytick,'CPU':[0],'RSS':int(pathlib.Path('/proc/self/status').read_text().split('VmRSS:')[1].split()[0])*1024,'RAMguard':469762048,'supervisor_owned':state['owned'],'next_at':state['next_at'],'science_current':current,'owner_stop':'verified saved receipt plus fresh exact PID absence','old_retained':108638692,'new_forecast':4194304,'total':112832996,'guard':117440512,'max_job_s':60},indent=2)+'\n')
pr=read(S/'preregister.json');bindings={}
for path,h in pr['sources'].items():assert sha(path)==h;bindings[path]=h
labels=lines('research-data/ai-sigma/frame14-teachers/final-qf1-v2/training-labels.jsonl.gz');assert len(labels)==5901;assert {r['split']for r in labels}=={'train','validation'}
labelmap={r['id']:r for r in labels};chosen={r['id']for r in sorted((r for r in labels if r['split']=='train'),key=lambda r:hashlib.sha256(('209-witness-v1:'+r['id']).encode()).hexdigest())[:12]}
conditions={};firstcfg=None;firstobs=None;maxerr=0;costs=[]
for lr in ['lr1e-3','lr1e-4','lr1e-5']:
 P=S/'runs'/('frame15-learning-diagnostic-'+lr+'-r1');cfg=read(P/'config.json');dataset=read(P/'dataset.json');hist=lines(P/'history.jsonl.gz');witness=lines(P/'witness.jsonl.gz');obs=read(P/'observer.json');summary=read(P/'summary.json')
 for name in ['history.jsonl.gz','witness.jsonl.gz','observer.json','summary.json','dataset.json','config.json']:bindings[str(P/name)]=sha(P/name)
 cfg_cmp=json.loads(json.dumps(cfg));cfg_cmp['optimizer']['lr']=0
 if firstcfg is None:firstcfg=cfg_cmp
 assert cfg_cmp==firstcfg
 assert cfg['training']['batch_size']==128 and cfg['training']['steps']==400 and cfg['training']['sampling']=='game'
 assert dataset['counts']=={'train':4653,'validation':1248} and dataset['groups']=={'train':96,'validation':24}
 assert dataset['initial_state_sha256']==pr['initial_tensor_SHA']==obs['initial_tensor_SHA']
 assert obs['batch_order_400_SHA']==stop['shared_batch400_SHA'];assert obs['observer_extra_forward']==obs['observer_extra_backward']==0
 assert [h['step']for h in hist]==pr['points']==[w['step']for w in witness]
 assert [h['step']for h in obs['observations']]==pr['points'][1:]
 assert obs['optimizer_all_parameter_names']==['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias']
 if firstobs is None:firstobs=[o['batch_order_prefix_SHA']for o in obs['observations']]
 assert firstobs==[o['batch_order_prefix_SHA']for o in obs['observations']]
 curve=[]
 for h,w in zip(hist,witness):
  st=h['step'];assert h['train_samples_seen']==st*128;near(h['train_epochs_equivalent'],st*128/4653);assert h['all_samples']==st*128+(pr['points'].index(st)+1)*5901
  for split,games,count in [('train','train_games',96),('validation','validation_games',24)]:
   gs=list(h[games].values());assert len(gs)==count;assert sum(g['rows']for g in gs)==h[split]['rows']
   for metric in ['rootmean','target','z','constant']:
    avg=sum(g[metric+'_mse']for g in gs)/count;v=h[split][metric+'_game_equal_mse'];maxerr=max(maxerr,abs(avg-v));near(avg,v)
    rowavg=sum(g[metric+'_mse']*g['rows']for g in gs)/sum(g['rows']for g in gs);near(rowavg,h[split][metric+'_mse'])
  assert set(w['IDs'])==chosen and len(w['rows'])==12
  changes=[]
  for r in w['rows']:
   near(r['target_rootmean'],labelmap[r['id']]['rootmean']);near(r['residual'],r['prediction']-r['target_rootmean']);near(r['prediction'],math.tanh(r['pre_tanh']),2e-7);changes.append(r['prediction']-r['prediction_step0'])
  near(w['prediction_step0_RMS_change'],math.sqrt(sum(c*c for c in changes)/12));near(w['prediction_step0_maxabs_change'],max(map(abs,changes)))
  curve.append({'step':st,'samples':st*128,'epoch':st*128/4653,'train':h['train']['target_game_equal_mse'],'validation':h['validation']['target_game_equal_mse'],'validation_row':h['validation']['target_mse'],'validation_z':h['validation']['z_game_equal_mse'],'validation_sign':h['validation']['z_sign_accuracy'],'val_saturation':h['validation']['saturation_fraction'],'witness_RMS_change':w['prediction_step0_RMS_change'],'witness_max_change':w['prediction_step0_maxabs_change']})
 best=min(hist,key=lambda h:h['validation']['target_game_equal_mse']);assert best['step']==summary['best_step'];near(best['validation']['target_game_equal_mse'],summary['best_validation_mse'])
 bp=best['validation_games'];ip=hist[0]['validation_games'];diffs={g:bp[g]['target_mse']-ip[g]['target_mse']for g in bp};near(sum(diffs.values())/24,best['validation']['target_game_equal_mse']-hist[0]['validation']['target_game_equal_mse'])
 for o in obs['observations']:
  for name,l in o['layers'].items():
   assert l['gradient_all_finite'];near(l['update_to_weight_ratio'],l['actual_update_norm']/l['weight_norm_before'])
  a=o['ft_active_columns'];near(a['update_to_weight_ratio'],a['actual_weight_update_norm']/a['weight_norm_before'])
 # Saved initial tensor bytes only; no pickle.load, model/session imports or forward.
 cp=pathlib.Path(summary['checkpoint_dir'])/'initial.pt'
 with zipfile.ZipFile(cp) as z:
  members=[n for n in z.namelist()if '/data/' in n and n.rsplit('/',1)[1].isdigit()];members.sort(key=lambda n:int(n.rsplit('/',1)[1]));assert len(members)==6
  raw=b''.join(z.read(n)for n in members);assert hashlib.sha256(raw).hexdigest()==pr['initial_tensor_SHA']
 bindings[str(cp)]=sha(cp)
 conditions[lr]={'curve':curve,'best_step':best['step'],'best_minus_initial':sum(diffs.values())/24,'improved_validation_games':sum(d<0 for d in diffs.values()),'validation_game_differences':diffs,'best_minus_constant':best['validation']['target_game_equal_mse']-best['validation']['constant_game_equal_mse'],'best_minus_fixed_distance':best['validation']['target_game_equal_mse']-pr['fixed_distance_validation_gameMSE'],'observer':obs['observations'],'witness_IDS':sorted(chosen),'all_samples':summary['all_samples']}
for p in (S/'jobs').glob('*/process.json'):
 j=read(p);costs.append({k:j.get(k)for k in ['id','kind','wall_seconds','exit','reason','samples_charged','child_waited','remaining']});bindings[str(p)]=sha(p)
assert sum(c['all_samples']for c in conditions.values())==330630
result={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'conditions':conditions,'max_game_aggregation_error':maxerr,'bindings':bindings,'all_observed_attempts':costs,'heavy_wall_sum':sum(j['wall_seconds']for j in costs if j['kind']=='heavy'),'all_guardian_wall_sum':sum(j['wall_seconds']for j in costs),'observer_extra_forward_backward':0,'limits':['group aggregate and12witness saved arithmetic; no full-row predictions or forward recertification','reused validation/one seed/30 selected observations; not fresh test','norms from saved owner measurements; no independently reconstructed all checkpoint updates','history/teachertruth/source shared limits remain'],'static_charge':120,'static_cap':180,'science_elapsed_s':time.monotonic()-start}
(D/'result.json').write_text(json.dumps(result,indent=2)+'\n')
(D/'compute-stop.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'tick':mytick,'CPU':[0],'elapsed_s':time.monotonic()-start,'peak_RSS':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'children':[],'exit':0,'static_charge':120,'static_cap':180,'newNN':0},indent=2)+'\n')
print(json.dumps({'PASS':True,'conditions':{k:{n:v[n]for n in ['best_step','best_minus_initial','best_minus_constant','best_minus_fixed_distance','improved_validation_games']}for k,v in conditions.items()},'maxerr':maxerr,'heavy_wall':result['heavy_wall_sum'],'elapsed':time.monotonic()-start}))
