"""Critic214 saved-only arithmetic. No model/library import or producer execution."""
import pathlib,json,gzip,hashlib,struct,math,ast,time,os,datetime,resource,zipfile
D=pathlib.Path('research-data/ai-sigma/frame15-distance-update-independent')
S=pathlib.Path('research-data/ai-sigma/frame15-distance-update-control')
B=pathlib.Path('research-data/ai-sigma/frame15-input-scale-control')
N=S/'runs/frame15-distance-update-control-r1';O=B/'runs/frame15-input-scale-control-r1'
start=time.monotonic()
def j(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def rows(p):
 with gzip.open(p,'rt') as f:return [json.loads(l) for l in f]
def avg(x):return math.fsum(x)/len(x)
def close(a,b,t=1e-10):assert abs(a-b)<=t,(a,b,t)
os.sched_setaffinity(0,{0})
stop=j(S/'science-stop.json');proc=j(S/'jobs/train-update-r1/process.json')
schedule=j('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json')
assert schedule['owned'] is None and schedule['next_at']-time.time()>150
identity=proc['identity'];ownerpath=pathlib.Path('/proc',str(identity['pid']))
same=False
if ownerpath.exists():
 try:same=(ownerpath/'stat').read_text().split(') ')[1].split()[19]==str(identity['tick'])
 except FileNotFoundError:pass
assert not same
live=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  args=(p/'cmdline').read_bytes().split(b'\0');exe=pathlib.Path(args[0].decode()).name
  if not (exe.startswith('python') or exe in ['node','nodejs']):continue
  script=next((a.decode() for a in args[1:] if a.endswith((b'.py',b'.cjs'))),None)
  if script and any(x in script for x in ['ai-sigma','nnue-training']) and not any(x in script for x in ['save.py','save_git.py','scheduler.py','watch.py','summarize','plot']):
   live.append({'pid':p.name,'script':script})
 except (PermissionError,FileNotFoundError):pass
assert not live,live
admit={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':os.getpid(),'tick':pathlib.Path('/proc/self/stat').read_text().split(') ')[1].split()[19],
 'CPU':[0],'owner_exact_absent':True,'owner_identity':identity,'supervisor_owned':None,'next_quiet_s':schedule['next_at']-time.time(),'heavy':live,'point_only':True}
(D/'compute-admission.json').write_text(json.dumps(admit,indent=2)+'\n')
reg=j(S/'preregister.json');bindings={}
for p,h in {**reg['sources'],**reg['private_sources']}.items():bindings[p]=sha(p);assert bindings[p]==h,p
assert stop['source_science_stopped'] and stop['allwait'] and not stop['remaining']
for p,h in stop.get('source_SHA',reg['private_sources']).items():assert sha(p)==h,p
assert sha(S/'scale.json')==sha(B/'scale.json')==reg['scale_SHA']
assert j(N/'config.json')==j(O/'config.json')
assert sha(reg['raw_initial_path'])==reg['raw_initial_checkpoint_SHA']
newsource=pathlib.Path('tools/ai-sigma-distance-update-control/run.py').read_text()
oldsource=pathlib.Path('tools/ai-sigma-input-scale-control/run.py').read_text()
def node(s,name):
 return next(n for n in ast.parse(s).body if getattr(n,'name',None)==name)
for name in ['ScaleModel']:
 assert ast.dump(node(newsource,name),include_attributes=False)==ast.dump(node(oldsource,name),include_attributes=False),name
class StripAsserts(ast.NodeTransformer):
 def visit_Assert(self,n):return None
newrecord=StripAsserts().visit(node(newsource,'record'));oldrecord=StripAsserts().visit(node(oldsource,'record'))
assert ast.dump(newrecord,include_attributes=False)==ast.dump(oldrecord,include_attributes=False)
assert "p['scaled_initial_tensor_SHA']==reg['expected_scaled_initial_tensor_SHA']" in newsource
hook=ast.get_source_segment(newsource,node(newsource,'scale_observed_step'))
for text in ['original_step=opt.step','result=original_step(*a,**kw)','copy_(before_w+proposal*mdl.sigma)','applied=mdl.h.weight[:,-2:].detach().clone()-before_w',
 'opt.step=attenuated_step','finally:opt.step=original_step','rawdw=applied/mdl.sigma','rawdb=db-(applied*(mdl.mu/mdl.sigma)).sum(dim=1)']:
 assert text in hook,text
assert 'param_groups' not in hook and '.state.clear' not in hook
dataset=j(N/'dataset.json');olddataset=j(O/'dataset.json')
for k in ['train_sha256','validation_sha256','counts','groups','constant','initial_state_sha256']:assert dataset[k]==olddataset[k],k
assert dataset['groups']=={'train':96,'validation':24} and dataset['counts']=={'train':4653,'validation':1248}
summary=j(N/'summary.json')
cp=pathlib.Path(summary['checkpoint_dir'])/'initial.pt'
oldcp=pathlib.Path(j(O/'summary.json')['checkpoint_dir'])/'initial.pt'
def tensorbytes(p):
 z=zipfile.ZipFile(p);names=sorted([n for n in z.namelist() if '/data/' in n],key=lambda n:int(n.rsplit('/',1)[1]))
 blobs=[z.read(n) for n in names];assert [len(x)//4 for x in blobs]==[9984,32,2112,32,32,1]
 return blobs
t=tensorbytes(cp);ot=tensorbytes(oldcp);assert t==ot
assert hashlib.sha256(b''.join(t)).hexdigest()==reg['expected_scaled_initial_tensor_SHA']==dataset['initial_state_sha256']
parity=j(S/'initial-function-parity.json')
assert parity['PASS'] and parity['maxabs']<=reg['parity_maxabs'] and parity['test_rows']==0 and parity['no_step_before_parity']
assert parity['raw_additional_forward_samples']==5901
first=j(S/'first-proposal-finite.json');assert first['PASS'] and first['nonzero_proposal_count']>0
assert first['proposal_moments_unchanged'] and first['bias_otherparams_unchanged_afterproposal'] and not first['optimizer_group_split_or_reset']
assert first['maxabs_applied_minus_requested']<=first['max_f32_roundoff_bound']
assert sum(r['nonzero'] for r in first['proposal_to_applied_ratio_by_column'])==first['nonzero_proposal_count']
nh=rows(N/'history.jsonl.gz');oh=rows(O/'history.jsonl.gz')
assert [h['step'] for h in nh]==reg['points']==[h['step'] for h in oh]
curves=[];paired={}
for a,b in zip(nh,oh):
 assert a['all_samples']==b['all_samples'] and a['train_samples_seen']==b['train_samples_seen']==a['step']*128
 close(a['train_epochs_equivalent'],a['step']*128/4653)
 assert not a['validation_eligible_zero_games']
 for split in ['train','validation']:
  games=a[split+'_games'];count=sum(g['rows'] for g in games.values())
  assert count==a[split]['rows'] and len(games)==a[split]['games']
  for kind in ['rootmean','z','target','constant']:
   close(avg([g[kind+'_mse'] for g in games.values()]),a[split][kind+'_game_equal_mse'])
   close(math.fsum(g[kind+'_mse']*g['rows'] for g in games.values())/count,a[split][kind+'_mse'])
  for kind in ['z_sign_accuracy','saturation_fraction']:
   close(math.fsum(g[kind]*g['rows'] for g in games.values())/count,a[split][kind])
 assert set(a['validation_games'])==set(b['validation_games'])
 diffs={g:a['validation_games'][g]['rootmean_mse']-b['validation_games'][g]['rootmean_mse'] for g in a['validation_games']}
 curves.append({'step':a['step'],'train_seen':a['train_samples_seen'],'train_epochs':a['train_epochs_equivalent'],'samples':a['all_samples'],
  'new_train':a['train'],'new_val':a['validation'],'old_val':b['validation'],'delta_gameMSE':avg(list(diffs.values()))})
 if a['step'] in [200,400]:paired[str(a['step'])]={'game_count':24,'improved':sum(x<0 for x in diffs.values()),'delta':avg(list(diffs.values())),'min':min(diffs.values()),'max':max(diffs.values()),'by_game':diffs,'phase':a['phase'],'cohorts':a['validation_cohorts']}
primary=next(c for c in curves if c['step']==reg['primary_step'])
close(primary['old_val']['rootmean_game_equal_mse'],reg['primary_baseline'])
close(primary['delta_gameMSE'],primary['new_val']['rootmean_game_equal_mse']-reg['primary_baseline'])
best=min(nh,key=lambda h:h['validation']['rootmean_game_equal_mse'])
assert best['step']==summary['best_step']
obs=j(N/'observer.json');oobs=j(O/'observer.json')
assert obs['batch_order_400_SHA']==oobs['batch_order_400_SHA']==reg['same_batch_order_400_SHA']
assert obs['optimizer_all_parameter_names']==oobs['optimizer_all_parameter_names']
updates=[];sigma=j(S/'scale.json')['sigma_f32']
for a,b in zip(obs['observations'],oobs['observations']):
 assert a['step']==b['step'] and a['batch_order_prefix_SHA']==b['batch_order_prefix_SHA']
 u=a['distance_coordinate_update']
 assert u['proposal_moments_unchanged'] and u['bias_otherparams_afterproposal_unchanged'] and u['extra_forward_backward']==0
 for k,n in [('Adam_proposal_Wd_standardized',64),('Applied_Wd_standardized',64),('Applied_Wd_raw',64),('DeltaBias_standardized',32),('Applied_Bias_raw',32)]:
  close(u[k]['norm']/math.sqrt(n),u[k]['RMS'],1e-8)
  assert u[k]['maxabs']<=u[k]['norm']+1e-8
 ap=u['Applied_Wd_standardized']['norm'];raw=u['Applied_Wd_raw']['norm'];proposal=u['Adam_proposal_Wd_standardized']['norm']
 assert ap/max(sigma)-1e-8<=raw<=ap/min(sigma)+1e-8
 # Aggregate relation bounded by saved per-element max, not recertification of unavailable values.
 assert abs(raw-proposal)<=8*u['proposal_vs_raw_maxabs']+1e-8
 updates.append({'step':a['step'],'proposal_norm':proposal,'ideal_sigma_norm':u['Ideal_sigma_times_proposal_standardized']['norm'],
  'applied_norm':ap,'raw_norm':raw,'raw_to_proposal_ratio':raw/proposal if proposal else None,
  'raw_bias_norm':u['Applied_Bias_raw']['norm'],'bias_standardized_norm':u['DeltaBias_standardized']['norm'],'proposal_vs_raw_maxabs':u['proposal_vs_raw_maxabs']})
nw=rows(N/'witness.jsonl.gz');ow=rows(O/'witness.jsonl.gz');wcalc=[]
for a,b in zip(nw,ow):
 assert a['step']==b['step'] and a['IDs']==b['IDs']
 delta=[]
 for r,s in zip(a['rows'],b['rows']):
  assert r['id']==s['id'] and r['target_rootmean']==s['target_rootmean']
  close(r['residual'],r['prediction']-r['target_rootmean'])
  close(r['prediction'],math.tanh(r['pre_tanh']),1e-7)
  delta.append(r['prediction']-r['prediction_step0'])
  if a['step']==0:close(r['prediction'],s['prediction'],1e-7)
 close(math.sqrt(avg([x*x for x in delta])),a['prediction_step0_RMS_change'],1e-7)
 wcalc.append({'step':a['step'],'RMSchange':a['prediction_step0_RMS_change'],'maxabschange':a['prediction_step0_maxabs_change']})
receipt=j(S/'actual-sample-receipt.json')
assert receipt['samples']==51200+59010+5901==proc['samples_charged']==116111
assert proc['exit']==0 and proc['child_waited'] and not proc['remaining'] and proc['current_exact_identity_absent']
for p in [S/'preregister.json',S/'science-stop.json',S/'first-proposal-finite.json',S/'initial-function-parity.json',N/'history.jsonl.gz',O/'history.jsonl.gz',N/'observer.json',N/'witness.jsonl.gz',cp,oldcp]:
 bindings[str(p)]=sha(p)
out={'issue':'quoridor-4lc.214','primary':primary,'paired':paired,'curves':curves,'updates':updates,'witness':wcalc,
 'first_proposal_finite_saved_receipt':first,'initialparity_saved_receipt':parity,'same_scaled_initial_rawstorage':True,
 'config_data_batch_equal':True,'same_source_class_and_initial_record_except_stronger_assert':True,'best_secondary_step':best['step'],
 'moments':'same train-only scale bound to accepted212; no refit; test metadata arithmetic excluded',
 'sample_accounting':receipt,'owner_wall_seconds':proc['wall_seconds'],'owner_RSSpeak':proc['peak_family_RSS'],
 'unknown_exclusive_observer_prep_management_cost':True,'old209_secondary':reg['old209_secondary_baseline'],
 'distance_reference':reg['distance_baseline'],'constant_reference':reg['constant_baseline'],
 'limits':['one seed/reused validation','attenuation changes subsequent gradients/moments and rawbias coupling; not original209 update reproduction','no individual step deltas saved; arithmetic validates aggregate identities/source/receipt only','initial parity no new forward certification','per-game saved metrics not regenerated predictions/teacher truth','phase/cohort have no new prediction oracle; retained saved counts including zero late','old standalone testlabels/results/raw/journal/mixedstatus/preview/formal173 unread'],
 'admission':admit,'bindings':bindings,'newNN':0,'budget':{'old212':120,'old210':180,'new214cap':120,'source_read_charge':60,'NN0_compute_charge':60,'new214charge':120,'job_actual_seconds':time.monotonic()-start},
 'PID':os.getpid(),'RSS_peak_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
assert out['RSS_peak_bytes']<448*1048576
(D/'result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'primary_delta':primary['delta_gameMSE'],'new_val':primary['new_val']['rootmean_game_equal_mse'],'improved':paired['200']['improved'],'beststep':best['step'],'RSS':out['RSS_peak_bytes'],'job_seconds':time.monotonic()-start}))
