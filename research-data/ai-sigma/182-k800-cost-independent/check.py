import pathlib,json,tarfile,hashlib,statistics,struct,math,datetime,time,resource,os,subprocess,traceback
os.sched_setaffinity(0,{0});start=time.monotonic();D=pathlib.Path('research-data/ai-sigma/182-k800-cost-independent');A=pathlib.Path('research-data/ai-sigma/180-native-k800-time');prefix='.artifacts/ai-sigma/resume-20261003/NATIVE-K800-TIME/runs/';job=prefix+'native180-measure-r1/';wanted={job+'rows.jsonl',job+'status.json',job+'init.json',job+'stop.json',prefix+'native180-measure-r1.process.json',prefix+'native180-mock-r1.process.json'};stored={};refs=[];out={'issue':'quoridor-4lc.182','NN_executed':0,'first_difference':None,'startUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def req(v,m):
 if not v:raise AssertionError(m)
def load(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def f32(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def summary(v):return{'n':len(v),'median':statistics.median(v),'min':min(v),'max':max(v),'values':v}
try:
 with tarfile.open(A/'native180-raw-r1.tar.gz','r|gz')as t:
  for m in t:
   if m.name in wanted:
    b=t.extractfile(m).read();stored[m.name]=b;refs.append({'archive_member':m.name,'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()})
 req(set(stored)==wanted,'required saved members missing');rows=[json.loads(l)for l in stored[job+'rows.jsonl'].splitlines()];status=json.loads(stored[job+'status.json']);init=json.loads(stored[job+'init.json']);stop=json.loads(stored[job+'stop.json']);proc=json.loads(stored[prefix+'native180-measure-r1.process.json']);pr=load(A/'preregister.json');fixtures=load(A/'inputs.json')['fixtures'];req(sha(A/'inputs.json')==pr['input_manifest_SHA256'],'inputsSHA');req(pr['K']==800 and pr['slots']==30 and pr['CPU_pool']==[2],'preregister conditions');req(sha(A/'native180-raw-r1.tar.gz')==load(A/'handoff-manifest.json')['SHA256'],'archiveSHA')
 expected=[]
 for f in fixtures:
  for phase,engines in [('warm',pr['warm_order']),('steady',pr['steady_order'])]:
   for e in engines:expected.append((f['id'],e,phase))
 req(len(rows)==len(status)==len(expected)==30,'all30 slots');req([r['slot']for r in rows]==list(range(30)),'row order');req(all((r['fixture'],r['engine'],r['phase'])==expected[i]and status[i]['slot']==i and status[i]['status']=='COMPLETE'and(status[i]['fixture'],status[i]['engine'],status[i]['phase'])==expected[i] for i,r in enumerate(rows)),'registration/complete');maxfloat=0;rootmeans=0;timing=[]
 for r in rows:
  label='slot'+str(r['slot']);c=r['cp'];root=r['root_state'];n=r['first_NN'];req(c['root_visits']==c['simulations']==800 and sum(e[2]for e in c['root_edges'])==799,label+' K/edge');req(r['NN_actual']==r['returned']==c['nn_calls']==800 and r['terminal_noNN']==r['discarded']==r['cache_hits']==0,label+' counters');req(r['CP_count']==1 and c['generation']==r['slot']+1,label+' CP/generation');req([e[0]for e in c['root_edges']]==root['legal'] and len(set(root['legal']))==len(root['legal']),label+' legal/order');req(all(isinstance(e[2],int)and e[2]>=0 and all(math.isfinite(e[i])for i in [1,3])and e[1]>=0 for e in c['root_edges']),label+' edge arithmetic');req(abs(math.fsum(e[1]for e in c['root_edges'])-1)<1e-12,label+' priormass');req(c['action']==max(c['root_edges'],key=lambda e:e[2])[0],label+' visit argmax');req(abs(c['root_mean']-c['root_valueSum']/800)<1e-14,label+' rootmean');req(abs(c['root_valueSum']-(n['value']-math.fsum(e[3]for e in c['root_edges'])))<1e-9,label+' backup root minus child sign')
  req(len(n['features_bits'])==648 and len(n['NN_bits'])==137,label+' featurebits');req(n['features_bits']==root['features_bits'],label+' root firstfeatures');req(all(math.isfinite(f32(b))for b in n['features_bits']+n['NN_bits']),label+' finite');req([f32(b)for b in n['NN_bits'][:-1]]==n['policy_logits']and f32(n['NN_bits'][-1])==n['value'],label+' bits137');req(abs(n['value'])<=1 and abs(c['root_mean'])<=1,label+' value range')
  req(abs((r['final_CP_validation_end']-r['t0'])-r['elapsed_ms'])<1e-7,label+' controllerclock');req(r['t0']<=r['final_CP_validation_end']<=r['result_receipt_ms'],label+' receive order');req(abs(r['post_CP_cleanup_ms']-(r['result_receipt_ms']-r['final_CP_validation_end']))<1e-7,label+' cleanup');req(r['NN_API_sum_ms']<=r['NN_pipe_sum_ms']+1e-6,label+' NN API within pipe');req(r['zero']=={'activeNN':0,'handles':0,'active':False},label+' zero');timing.append({'slot':r['slot'],'elapsed_ms':r['elapsed_ms'],'cleanup_ms':r['post_CP_cleanup_ms'],'API_ms':r['NN_API_sum_ms'],'pipe_ms':r['NN_pipe_sum_ms'],'bridge':r['bridge'],'primary_clock':'controller single hrtime'});
  if r['engine']=='candidate':req(r['bridge']['count']==sum(r['bridge']['ops'].values())==2404 and r['bridge']['ops']=={'raw':1,'new':1,'begin':800,'resume':800,'checkpoint':800,'cancel':1,'free':1},label+' bridge')
  else:req(r['bridge']['count']==0,label+' reference bridge')
  if r['slot']>0:req(r['t0']>=rows[r['slot']-1]['result_receipt_ms'],label+' next quiescent receipt')
 groups=[]
 for f in fixtures:
  rr=[r for r in rows if r['fixture']==f['id']];base=next(r for r in rr if r['engine']=='reference');checks=[]
  for r in rr:
   req(r['root_state']==base['root_state'] and r['first_NN']==base['first_NN'],f['id']+' root input/NN');req([e[0]for e in r['cp']['root_edges']]==[e[0]for e in base['cp']['root_edges']]and[e[2]for e in r['cp']['root_edges']]==[e[2]for e in base['cp']['root_edges']]and r['cp']['action']==base['cp']['action'],f['id']+' discrete root');diff=max(abs(a[i]-b[i])for a,b in zip(r['cp']['root_edges'],base['cp']['root_edges'])for i in [1,3]);maxfloat=max(maxfloat,diff);rootmeans=max(rootmeans,abs(r['cp']['root_mean']-base['cp']['root_mean']));checks.append({'slot':r['slot'],'root_features_NN137_exact':True,'Action_visits_order_exact':True,'root_edge_f64_maxabs':diff,'rootmean_absdiff':abs(r['cp']['root_mean']-base['cp']['root_mean'])})
  e={}
  for name in ['candidate','reference']:
   steady=[r for r in rr if r['engine']==name and r['phase']=='steady'];e[name]={'primary_ms':summary([r['elapsed_ms']for r in steady]),'warm_ms':[r['elapsed_ms']for r in rr if r['engine']==name and r['phase']=='warm'],'API_ms':summary([r['NN_API_sum_ms']for r in steady]),'pipe_ms':summary([r['NN_pipe_sum_ms']for r in steady]),'cleanup_ms':summary([r['post_CP_cleanup_ms']for r in steady]),'bridge_ms':summary([r['bridge']['wall_ms']for r in steady]),'bridge_response_bytes':summary([r['bridge']['response_bytes']for r in steady])}
  steady=[r for r in rr if r['phase']=='steady'];ratios=[]
  for i in range(0,8,2):
   pair=steady[i:i+2];c=next(r for r in pair if r['engine']=='candidate');r=next(r for r in pair if r['engine']=='reference');ratios.append(c['elapsed_ms']/r['elapsed_ms'])
  groups.append({'fixture':f['id'],'engine':e,'C_over_R_median':e['candidate']['primary_ms']['median']/e['reference']['primary_ms']['median'],'paired_ratios':summary(ratios),'checks':checks})
 req(len(init)==6 and sum(v['init']['startup']['count']for v in init)==6,'startup6');inits=[];identities=[]
 for v in init:
  i=v['init']['info'];req(i['version']=='1.30.0'and i['providers']==['CPUExecutionProvider']and i['intra']==i['inter']==1 and i['sequential']and i['affinity']==[2],'provider');inits.append({'fixture':v['fixture'],'engine':v['engine'],'total_ms':v['total_ms'],'cold_session_ms':i['init_ms'],'startup_API_ms':v['init']['startup']['API_ms'],'startup_wall_ms':v['init']['startup']['wall_ms']});identities.extend(v['init']['identities'])
 req(stop['qualification']is None and stop['monitor_state']=='READY'and stop['NN_actual']==24000 and stop['rows']==30,'science stop');req(len(stop['closings'])==6 and all(z['close']['exit']['code']==0 for z in stop['closings']),'engineclose');req(proc['exit']==0 and not proc['remaining']and not proc['unknown_adopted']and not proc['affinity_violations'],'process stop');req(proc['all_observed_TIDs_at_assigned_CPU'],'finiteCPUaffinity')
 costs=[]
 for run in ['native180-mock-r1','native180-measure-r1']:
  p=json.loads(stored[prefix+run+'.process.json']);sec=(datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds();costs.append({'run':run,'seconds':sec,'exit':p['exit'],'remaining':p['remaining'],'unknown':p['unknown_adopted']})
 identities=[{'pid':v['pid'],'start_ticks':v['start_ticks'],'current_absent':not pathlib.Path('/proc/'+str(v['pid'])).exists()}for v in identities]
 binding=load(A/'binding.json');refs.extend({'path':str(A/n),'SHA256':sha(A/n),'bytes':(A/n).stat().st_size}for n in ['inputs.json','preregister.json','binding.json','science-stop.json','handoff-stop.json','cost-ledger.json']);sources=[]
 for name,h in pr['source'].items():
  if pathlib.Path(name).name in ['measure.cjs','controller.cjs','engine.cjs','common.cjs']:
   b=subprocess.check_output(['git','show','ca7ddb93e21d26196e24db3438a2a2a86b4a7121:'+name]);req(hashlib.sha256(b).hexdigest()==h,'scientificsource '+name);sources.append({'path':name,'Git':'ca7ddb93e21d26196e24db3438a2a2a86b4a7121','SHA256':h})
 out.update({'supported':True,'all30_COMPLETE':True,'warm6':6,'steady24':24,'saved_NN':sum(r['NN_actual']for r in rows),'startup':6,'root_edge_f64_maxabs':maxfloat,'rootmean_maxabs':rootmeans,'groups':groups,'inits':inits,'costs':costs,'all_owned_jobwall':sum(c['seconds']for c in costs),'controller_elapsed_sum_ms':sum(r['elapsed_ms']for r in rows),'cleanup_sum_ms':sum(r['post_CP_cleanup_ms']for r in rows),'saved_stop_and_current_identities':identities,'timing_rows':timing,'references':refs,'source':sources,'preserved_binary_model_binding':binding,'margin_preregistered':False,'kernelCPU_attribution':False,'full_deep_or_allperiod_proof':False})
except BaseException as e:out.update({'supported':False,'first_difference':str(e),'failure_type':type(e).__name__,'trace':traceback.format_exc()})
out.update({'endUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid()});(D/'arithmetic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['groups','inits','costs','saved_stop_and_current_identities','timing_rows','references','source','preserved_binary_model_binding','trace']}));req(out['supported'],'checker not supported; do not convert to original scientific loss')
