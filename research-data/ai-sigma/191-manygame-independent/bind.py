import pathlib,json,gzip,hashlib,struct,math,statistics,collections,time,datetime,resource,os,subprocess,tarfile,difflib,traceback
os.sched_setaffinity(0,{0});start=time.monotonic();D=pathlib.Path('research-data/ai-sigma/191-manygame-independent');A=pathlib.Path('research-data/ai-sigma/187-manygame-generation');B=pathlib.Path('.artifacts/ai-sigma/resume-20261003/MANYGAME-GENERATION');snap={};out={'NN_executed':0,'first_difference':None}
def rd(p):
 p=pathlib.Path(p);b=p.read_bytes();snap[str(p)]={'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b
def load(p):return json.loads(rd(p))
def need(v,m):
 if not v:raise AssertionError(m)
def f32(b):return struct.unpack('<f',struct.pack('<I',b))[0]
try:
 prior=load(D/'arithmetic.json');manifest=load(A/'archive-manifest.json');archive=pathlib.Path(manifest['archive']);need(hashlib.sha256(rd(archive)).hexdigest()==manifest['archiveSHA256'],'archive SHA')
 unchanged=[];members=[]
 for name,old in prior['snapshots'].items():
  p=pathlib.Path(name);need(hashlib.sha256(rd(p)).hexdigest()==old['SHA256'],'changed source during pack '+name);unchanged.append(name)
  if name.startswith(str(B)+'/'):
   rel=name;need(manifest['members'][rel]['SHA256']==old['SHA256'],'archive member binding '+rel);members.append(rel)
 # Independently decompress only the needed process/parity members; no archive extraction.
 stream=[]
 with tarfile.open(archive,'r|gz')as tf:
  for m in tf:
   rel=m.name.removeprefix('./')
   if rel.endswith('/process.json') or rel.endswith('/native187-parity-r1/result.json'):
    b=tf.extractfile(m).read();need(hashlib.sha256(b).hexdigest()==manifest['members'][rel]['SHA256'],'stream member '+rel);stream.append(rel)
 old=load(A/'binding.json');new=load(A/'binding-gpu-future.json');source_checks=[]
 for role,binding,cid in [('original',old,'2fef995b9e59c4dd8109c18c067f148d91f83083'),('GPUfuture',new,'31a807382621e6b73d8656502e7ea6991bb8ba25')]:
  for name in ['worker.cjs','gamepool.cjs','provider.py','adapter.py','broker.cjs','teacher-interface.cjs','schema.cjs']:
   p='tools/ai-sigma-manygame-generation/'+name;expected=binding['source'][p];b=subprocess.run(['git','show',cid+':'+p],capture_output=True,check=True,timeout=8).stdout;need(hashlib.sha256(b).hexdigest()==expected,'source Git bind '+role+name);source_checks.append({'role':role,'Git':cid,'path':p,'SHA256':expected})
  for p,expected in binding['readonly'].items():need(hashlib.sha256(rd(p)).hexdigest()==expected,'readonly source/binary/model '+p)
 need(hashlib.sha256(rd(A/'openings.json')).hexdigest()==old['openingsSHA']==new['inputSHA'],'same inputs')
 need(hashlib.sha256(rd(A/'preregister.json')).hexdigest()==old['preregisterSHA']==new['original_preregisterSHA'],'unchanged prereg')
 need(hashlib.sha256(rd(A/'preregister-future-GPU-supplement.json')).hexdigest()==new['supplementSHA'],'future supplement')
 before=rd('tools/ai-sigma-manygame-generation/worker-pre-history-repair.cjs').decode();after=rd('tools/ai-sigma-manygame-generation/worker.cjs').decode();diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original-worker',tofile='GPUfuture-worker'));D.joinpath('history-only.diff').write_text(diff)
 changed=[(a,b)for a,b in zip(before.splitlines(),after.splitlines())if a!=b];need(len(changed)==1 and len(before.splitlines())==len(after.splitlines()),'more than history source line changed');need('ROOT_BINDING_HISTORY_MEMBERSHIP_COUNTS' in changed[0][1],'history membership repair')
 # Original actual run/source bindings, not current-source identity alone.
 need(all(a['source_git']==('31a807382621e6b73d8656502e7ea6991bb8ba25' if a['run'].split('-')[1] in ['gpu3','gpu12','gpu24','history'] else '2fef995b9e59c4dd8109c18c067f148d91f83083') for a in prior['allattempts'] if a['kind']=='generate'),'run source versions')
 par=load(B/'native187-parity-r1/result.json');pchecks=[]
 for c in par['checks']:
  n=c['B'];need(len(c['cpu']['items'])==len(c['gpu']['items'])==n,'parity batch count');delta=ratio=0
  for cpu,gpu in zip(c['cpu']['items'],c['gpu']['items']):
   need(cpu['id']==gpu['id'],'parity identity');need(len(cpu['f32bits137'])==len(gpu['f32bits137'])==137,'137 parity')
   for a,b in zip(cpu['f32bits137'],gpu['f32bits137']):
    x,y=f32(a),f32(b);need(math.isfinite(x)and math.isfinite(y),'parity finite');delta=max(delta,abs(x-y));ratio=max(ratio,abs(x-y)/(1e-4+1e-4*abs(x)))
  need(ratio<=1,'parity tolerance');pchecks.append({'B':n,'samples_CPU_plus_GPU':2*n,'maxabs':delta,'max_ratio':ratio})
 need([c['B']for c in pchecks]==list(range(1,9))and sum(c['samples_CPU_plus_GPU']for c in pchecks)==72,'parity scope')
 out.update({'supported':True,'unchanged_read_sources':unchanged,'archive_SHA256':manifest['archiveSHA256'],'archive_member_bindings':members,'stream_restored_members':stream,'source_Git_checks':source_checks,'history_changed_lines':len(changed),'parity':pchecks,'parity_full_deep':False,'stop':load(A/'science-stop.json'),'cost_ledger_snapshot':load(A/'pipeline-cost-ledger.json')})
 # Optional 188: arithmetic over saved scalars only; CE logits/forward absent.
 C=pathlib.Path('research-data/ai-sigma/188-value-lr-control/runs/r2');R=pathlib.Path('research-data/ai-sigma/186-value-game-diagnostic/per-row.jsonl.gz');bb=rd(R);need(hashlib.sha256(bb).hexdigest()=='e3ad152157dfe9d12c8b1b60c7f9500ffcd0a0faea792115e6b1fe02d1e928e0','188 baseline hash');rr={r['row_id']:r for r in map(json.loads,gzip.decompress(bb).decode().splitlines())};rows=list(map(json.loads,gzip.decompress(rd(C/'per-row.jsonl.gz')).decode().splitlines()));need(len(rows)==len(rr)==502,'188 count');triples=[];maxerr=0
 for r in rows:
  b=rr[r['row_id']];need(all(r[k]==b[k]for k in ['game_id','lineage','side','ply','z_stm','value_eligible','cohort','old_value','old_mse','old_ce']),'188 row/side/target baseline');need(r['side'] in [1,2] and r['z_stm'] in [-1,1] and r['value_eligible'],'188 view')
  tr={'row_id':r['row_id'],'game':r['game_id'],'cohort':r['cohort'],'z':r['z_stm'],'side':r['side'],'models':{}}
  for name,src,prefix in [('parent176',r,'old'),('LR01',b,'new'),('LR0025',r,'new')]:
   v=src[prefix+'_value'];m=src[prefix+'_mse'];ce=src[prefix+'_ce'];err=abs(m-(v-r['z_stm'])**2);maxerr=max(maxerr,err);need(err<=1e-6,'188 MSE arithmetic');tr['models'][name]={'value':v,'MSE':m,'CE':ce}
  triples.append(tr)
 def agg(rs):
  o={'rows':len(rs),'games':len(set(r['game']for r in rs))}
  for name in ['parent176','LR01','LR0025']:
   o[name]={'MSE':math.fsum(r['models'][name]['MSE']for r in rs)/len(rs),'CE':math.fsum(r['models'][name]['CE']for r in rs)/len(rs),'sign_correct':sum(r['models'][name]['value']*r['z']>0 for r in rs),'wrong_saturation_abs09':sum(abs(r['models'][name]['value'])>=.9 and r['models'][name]['value']*r['z']<0 for r in rs),'mean_P1':math.fsum(r['models'][name]['value']*(1 if r['side']==1 else-1)for r in rs)/len(rs)}
  return o
 cohorts={c:agg([r for r in triples if r['cohort']==c])for c in ['old','new']};games={g:agg([r for r in triples if r['game']==g])for g in sorted(set(r['game']for r in triples))};need(cohorts['old']['rows']==221 and cohorts['new']['rows']==281 and len(games)==8,'188 cohort/game counts')
 saved=load(C/'comparison.json')
 for c,o in cohorts.items():
  for name,target in [('parent176','parent176'),('LR01','LR01_saved181'),('LR0025','LR0025_r2')]:
   for metric in ['CE','MSE','sign_correct']:need(abs(o[name][metric]-saved['cohorts_row_weighted'][c][target][metric])<1e-12,'188 aggregate '+c+name+metric)
 training=load(C/'training.json');need(hashlib.sha256(rd(C/'student-checkpoint.pt')).hexdigest()==training['checkpoint_SHA256'],'188 binary binding');need(hashlib.sha256(rd('tools/ai-sigma-value-lr-control/learn.py')).hexdigest()=='b24a3c74cdd913770fec7f55b299ae670f670d8205a178b388ee694c3797a441','188 source')
 out['optional188']={'supported_saved_arithmetic':True,'cohorts':cohorts,'games':games,'all':agg(triples),'MSE_maxfloat32_difference':maxerr,'CE_independent_forward':False,'CE_saved_scalar_aggregation_only':True,'training_receipt':training,'stop_receipt':load(C/'process-stop.json'),'management_guard_overrun_B':28086,'guard_account':486838,'guard_B':458752,'unGit_final_stop_metadata':True,'not_new_model_recertification':True}
except BaseException as e:out.update({'supported':False,'first_difference':str(e),'type':type(e).__name__,'trace':traceback.format_exc()})
out.update({'snapshots':snap,'elapsed_seconds':time.monotonic()-start,'RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid(),'end':datetime.datetime.now(datetime.timezone.utc).isoformat()});D.joinpath('binding-arithmetic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ['supported','first_difference','elapsed_seconds','RSS_bytes','PID','end']}));need(out['supported'],'own binding checker failure, not original scientific negative')
