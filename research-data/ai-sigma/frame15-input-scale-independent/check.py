"""NN0: stdlib saved arithmetic, no producer checker/model execution."""
import pathlib,json,gzip,struct,math,hashlib,zipfile,time,os,datetime,resource,collections
D=pathlib.Path('research-data/ai-sigma/frame15-input-scale-independent')
S=pathlib.Path('research-data/ai-sigma/frame15-input-scale-control')
N=S/'runs/frame15-input-scale-control-r1'
O=pathlib.Path('research-data/ai-sigma/frame15-learning-diagnostic/runs/frame15-learning-diagnostic-lr1e-4-r1')
start=time.monotonic()
def j(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(l) for l in f]
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def avg(xs):return math.fsum(xs)/len(xs)
def close(a,b,tol=1e-10):assert abs(a-b)<=tol,(a,b,tol)
os.sched_setaffinity(0,{0})
schedule=j('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json')
assert schedule['owned'] is None
assert schedule['next_at']-time.time()>150
assert not pathlib.Path('/proc/4015517').exists()
live=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  args=(p/'cmdline').read_bytes().split(b'\0')
  exe=pathlib.Path(args[0].decode()).name
  if not (exe.startswith('python') or exe in ['node','nodejs']):continue
  script=next((a.decode() for a in args[1:] if a.endswith((b'.py',b'.cjs'))),None)
  if script and any(s in script for s in ['ai-sigma','nnue-training']):
   if any(s in script for s in ['save.py','save_git.py','scheduler.py','watch.py','summarize','plot']):continue
   live.append({'pid':p.name,'script':script})
 except (FileNotFoundError,PermissionError):pass
assert not live,live
admit={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'tick':pathlib.Path('/proc/self/stat').read_text().split(') ')[1].split()[19],
       'CPU':[0],'owner211_exact_absent':True,'supervisor_owned':None,'next_quiet_seconds':schedule['next_at']-time.time(),'heavy_scan':live,'point_only':True}
(D/'compute-admission.json').write_text(json.dumps(admit,indent=2)+'\n')
reg=j(S/'preregister.json');stop=j(S/'science-stop.json');scale=j(S/'scale.json');parity=j(S/'initial-function-parity.json')
bound={}
for p,h in {**reg['sources'],**reg['private_sources']}.items():
 bound[p]=sha(p);assert bound[p]==h,p
for p,h in stop['source_SHA'].items():assert sha(p)==h,p
for p,h in [(reg['stage_path'],reg['stage_SHA']),(S/'scale.json',reg['scale_SHA']),(reg['raw_initial_path'],reg['raw_initial_checkpoint_SHA']),(S/'config.json',reg['config_SHA'])]:
 bound[str(p)]=sha(p);assert bound[str(p)]==h,p
stage=j(reg['stage_path'])
for k in ['metadata','mask','training_labels']:
 bound[stage[k]]=sha(stage[k]);assert bound[stage[k]]==stage[k+'_sha256']
metadata=rows(stage['metadata']);labels=rows(stage['training_labels'])
assert all(r['split'] in ['train','validation'] for r in labels)
groups=set(stage['train_groups'])
train=[r for r in metadata if r['split']=='train' and r['group'] in groups]
val=[r for r in metadata if r['split']=='validation']
assert len(train)==4653 and len(val)==1248
tg=collections.defaultdict(list)
for r in train:tg[r['group']].append([f32(x) for x in r['distance']])
assert len(tg)==96
mu=[avg([avg([d[k] for d in ds]) for ds in tg.values()]) for k in range(2)]
var=[avg([avg([(d[k]-mu[k])**2 for d in ds]) for ds in tg.values()]) for k in range(2)]
sig=[f32(math.sqrt(v)) for v in var];muf=[f32(v) for v in mu]
assert [bits(v) for v in muf]==scale['mu_bits']
assert [bits(v) for v in sig]==scale['sigma_bits']
for k in range(2):close(mu[k],scale['mu64'][k],1e-14);close(var[k],scale['population_var64'][k],1e-14)
assert j(N/'config.json')==j(O/'config.json')
dataset=j(N/'dataset.json');olddata=j(O/'dataset.json')
for k in ['train_sha256','validation_sha256','counts','groups','constant']:
 assert dataset[k]==olddata[k],k
assert dataset['groups']=={'train':96,'validation':24}
lb={r['id']:r for r in labels}
lt=collections.defaultdict(list)
for r in train:lt[r['group']].append(lb[r['id']]['rootmean'])
constant=avg([avg(v) for v in lt.values()]);close(constant,dataset['constant'])
vg=collections.defaultdict(list)
for r in val:vg[r['group']].append(lb[r['id']]['rootmean'])
constantval=avg([avg([(y-constant)**2 for y in ys]) for ys in vg.values()])
close(constantval,reg['constant_baseline'])
def storage(p):
 z=zipfile.ZipFile(p);keys=sorted([n for n in z.namelist() if '/data/' in n],key=lambda n:int(n.rsplit('/',1)[1]))
 b=[z.read(n) for n in keys];assert [len(x)//4 for x in b]==[9984,32,2112,32,32,1]
 return b,[struct.unpack('<'+'f'*(len(x)//4),x) for x in b]
raw,rv=storage(reg['raw_initial_path']);scaled,sv=storage(pathlib.Path(j(N/'summary.json')['checkpoint_dir'])/'initial.pt')
assert sum(len(v) for v in rv)==12193
assert hashlib.sha256(b''.join(raw)).hexdigest()==reg['raw_initial_tensor_SHA']
assert hashlib.sha256(b''.join(scaled)).hexdigest()==parity['scaled_initial_tensor_SHA']
assert raw[0]==scaled[0] and raw[1]==scaled[1] and raw[4]==scaled[4] and raw[5]==scaled[5]
werr=berr=0
for row in range(32):
 assert rv[2][row*66:row*66+64]==sv[2][row*66:row*66+64]
 for k in range(2):
  expected=f32(rv[2][row*66+64+k]*sig[k]);werr=max(werr,abs(expected-sv[2][row*66+64+k]))
 # Kernel reduction rounding may vary; bounded f32 linear compensation, not model forward.
 expected=rv[3][row]+sum(rv[2][row*66+64+k]*muf[k] for k in range(2))
 berr=max(berr,abs(expected-sv[3][row]))
assert werr==0 and berr<5e-8,(werr,berr)
assert parity['PASS'] and parity['test_rows']==0 and parity['raw_additional_forward_samples']==5901 and parity['no_step_before_parity']
assert parity['maxabs']<=reg['parity_maxabs']
newhist=rows(N/'history.jsonl.gz');oldhist=rows(O/'history.jsonl.gz')
assert [r['step'] for r in newhist]==reg['points']==[r['step'] for r in oldhist]
curves=[];paired={}
for new,old in zip(newhist,oldhist):
 assert new['train_samples_seen']==old['train_samples_seen']==new['step']*128
 close(new['train_epochs_equivalent'],new['step']*128/4653)
 assert new['all_samples']==old['all_samples']
 for spl in ['train','validation']:
  games=new[spl+'_games'];total=sum(g['rows'] for g in games.values())
  assert total==new[spl]['rows'] and len(games)==new[spl]['games']
  for kind in ['rootmean','target','z','constant']:
   close(avg([g[kind+'_mse'] for g in games.values()]),new[spl][kind+'_game_equal_mse'])
   close(math.fsum(g[kind+'_mse']*g['rows'] for g in games.values())/total,new[spl][kind+'_mse'])
  for key in ['z_sign_accuracy','saturation_fraction']:
   close(math.fsum(g[key]*g['rows'] for g in games.values())/total,new[spl][key])
 assert not new['validation_eligible_zero_games']
 diffs={g:new['validation_games'][g]['rootmean_mse']-old['validation_games'][g]['rootmean_mse'] for g in new['validation_games']}
 assert set(diffs)==set(old['validation_games'])
 delta=avg(list(diffs.values()))
 close(delta,new['validation']['rootmean_game_equal_mse']-old['validation']['rootmean_game_equal_mse'])
 curves.append({'step':new['step'],'train_seen':new['train_samples_seen'],'samples':new['all_samples'],
  'old_val':old['validation'],'new_val':new['validation'],'new_train':new['train'],'delta_gameMSE':delta})
 if new['step'] in [200,400]:
  paired[str(new['step'])]={'games':24,'improved_games':sum(d<0 for d in diffs.values()),'mean':delta,'min':min(diffs.values()),'max':max(diffs.values()),'by_game':diffs,
    'phase':new['phase'],'cohorts':new['validation_cohorts']}
primary=next(c for c in curves if c['step']==reg['primary_step'])
close(primary['old_val']['rootmean_game_equal_mse'],reg['primary_baseline'])
best=min(newhist,key=lambda h:h['validation']['rootmean_game_equal_mse'])
assert best['step']==j(N/'summary.json')['best_step']==200
obs=j(N/'observer.json');oldobs=j(O/'observer.json')
assert obs['batch_order_400_SHA']==oldobs['batch_order_400_SHA']==reg['same_batch_order_400_SHA']
assert obs['optimizer_all_parameter_names']==['ft.weight','ft.bias','h.weight','h.bias','out.weight','out.bias']
updates=[]
for a,b in zip(obs['observations'],oldobs['observations']):
 assert a['step']==b['step'] and a['batch_order_prefix_SHA']==b['batch_order_prefix_SHA']
 u=a['distance_coordinate_update'];assert u['extra_forward_backward']==0
 for k,num in [('DeltaWd_standardized',64),('DeltaWd_raw',64),('DeltaBias_standardized',32),('DeltaBias_raw',32)]:
  close(u[k]['norm']/math.sqrt(num),u[k]['RMS'],1e-8)
  assert u[k]['maxabs']<=u[k]['norm']+1e-8
 ratio=u['DeltaWd_raw']['norm']/u['DeltaWd_standardized']['norm']
 assert 1/max(sig)-1e-5<=ratio<=1/min(sig)+1e-5
 updates.append({'step':a['step'],'raw_distance_norm':u['DeltaWd_raw']['norm'],'standardized_distance_norm':u['DeltaWd_standardized']['norm'],
   'ratio':ratio,'raw_bias_norm':u['DeltaBias_raw']['norm'],'standardized_bias_norm':u['DeltaBias_standardized']['norm']})
nw=rows(N/'witness.jsonl.gz');ow=rows(O/'witness.jsonl.gz')
ids=[i for _,i in sorted((hashlib.sha256(('209-witness-v1:'+r['id']).encode()).hexdigest(),r['id']) for r in train)[:12]]
assert set(ids)==set(nw[0]['IDs'])
ids=nw[0]['IDs']
meta={r['id']:r for r in train};wcalc=[]
for a,b in zip(nw,ow):
 assert a['step']==b['step'] and a['IDs']==b['IDs']==ids
 changes=[]
 for r in a['rows']:
  close(r['target_rootmean'],lb[r['id']]['rootmean'])
  close(r['residual'],r['prediction']-r['target_rootmean'])
  close(r['prediction'],math.tanh(r['pre_tanh']),1e-7)
  changes.append(r['prediction']-r['prediction_step0'])
 close(math.sqrt(avg([c*c for c in changes])),a['prediction_step0_RMS_change'],1e-7)
 close(max(abs(c) for c in changes),a['prediction_step0_maxabs_change'],1e-7)
 if a['step']==0:
  maxinitial=max(abs(r['prediction']-s['prediction']) for r,s in zip(a['rows'],b['rows']))
  assert maxinitial<=1e-6
 vals=[f32(f32(f32(meta[i]['distance'][k])-muf[k])/sig[k]) for i in ids for k in range(2)]
 stat=a['input_scale']['distance_standardized']
 close(avg(vals),stat['mean'],1e-6);close(math.sqrt(avg([v*v for v in vals])),stat['rms'],1e-6)
 wcalc.append({'step':a['step'],'prediction_RMS_change':a['prediction_step0_RMS_change'],'prediction_maxabs_change':a['prediction_step0_maxabs_change']})
receipt=j(S/'actual-sample-receipt.json');proc=j(S/'jobs/train-scale-r1/process.json')
assert receipt['samples']==51200+59010+5901==proc['samples_charged']==116111
assert newhist[-1]['all_samples']==51200+10*5901==110210
assert proc['exit']==0 and proc['child_waited'] and proc['remaining']==[] and proc['current_exact_identity_absent']
for p in [S/'preregister.json',S/'science-stop.json',S/'initial-function-parity.json',N/'history.jsonl.gz',O/'history.jsonl.gz',N/'observer.json',N/'witness.jsonl.gz',S/'actual-sample-receipt.json']:
 bound[str(p)]=sha(p)
out={'issue':'quoridor-4lc.212','verdict':'finite reused-validation benefit supported; fresh generalization/cause/strength insufficient',
 'moments':{'rows':4653,'games':96,'mu64':mu,'var64':var,'mu_f32':muf,'sigma_f32':sig,'labels_fit':False},
 'initial_storage':{'parameters':12193,'rawtensorSHA':reg['raw_initial_tensor_SHA'],'scaledtensorSHA':parity['scaled_initial_tensor_SHA'],'distance_weight_maxerror':werr,'bias_linear_maxerror':berr,'unchanged_other_bytes':True,'forward_parity_saved_receipt':parity,'new_forward':0},
 'constant_trainonly':constant,'constant_validation_gameMSE':constantval,'primary':primary,
 'distance_reference':reg['distance_baseline'],'distance_gap':primary['new_val']['rootmean_game_equal_mse']-reg['distance_baseline'],
 'curves':curves,'paired':paired,'coordinate_updates':updates,'witness12':wcalc,'initial_witness_maxabs':maxinitial,
 'sample_accounting':receipt,'owner_job_wall_s':proc['wall_seconds'],'owner_peak_RSS':proc['peak_family_RSS'],
 'observer_exclusive_overhead':'unknown; included in owner wall; API not added as exclusive CPU',
 'independence_limits':['aggregate games checked from saved per-game metrics, not raw prediction regeneration','initial function forward parity is source/receipt binding only','per-step raw bias from aggregate statistics cannot be independently reconstructed','phase/cohort/sign from saved aggregate predictions; teacher truth/history/distribution unresolved','one joint seed, reused validation, center+scale+Adam coordinates combined','old test labels/results/raw/journal/preview and formal173 unread'],
 'budget':{'old210_static':180,'old210_cap':180,'new212_static_charge':120,'new212_cap':120,'source_read_charge':60,'NN0_job_charge':60,'actual_job_seconds':time.monotonic()-start},
 'admission':admit,'bindings':bound,'newNN':0,'PID':os.getpid(),'RSS_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
assert out['RSS_peak_bytes']<448*1048576
(D/'result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'primary_delta':primary['delta_gameMSE'],'improved_games':paired['200']['improved_games'],'first_rawupdate_ratio':updates[0]['ratio'],'job_seconds':time.monotonic()-start,'RSSpeak':out['RSS_peak_bytes']}))
