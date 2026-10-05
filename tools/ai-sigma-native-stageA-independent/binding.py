"""Minimal saved source/phase binding and crossbackend root arithmetic; inference execution0."""
import os,json,pathlib,hashlib,subprocess,struct,datetime
os.sched_setaffinity(0,{0});R=pathlib.Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/168-native-stageA-independent';B=R/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE/runs';refs=[]
def read(p):
 p=pathlib.Path(p);p=p if p.is_absolute() else R/p;b=p.read_bytes();refs.append({'path':str(p.relative_to(R)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return json.loads(b)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(262144):h.update(b)
 return h.hexdigest()
def gitbytes(commit,p):return subprocess.check_output(['git','show',commit+':'+p],cwd=R,timeout=60)
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
raw=read(B/'native165-mechanism-r1/result.json');assert refs[-1]['sha256']=='dee3d3b52839b3c8ba50c082abba835be6f0784c61617a37ccfa550811113286'
inputs=read(B/'native165-mechanism-r1.inputs.json');source=inputs['git_commit'];assert source.startswith('a09279c')
sb=read('research-data/ai-sigma/165-native-baseline/source-binding.json');binary=sb['build']['binary'];binarysha=sha(binary['path']);assert binarysha==binary['SHA256']=='166dd0c4f5eef9cd02a189e9e8bb4811bd307f6545db83a07e7180ea410e96f8'
paths=['engine.cjs','ort.py','reference-core-native.js','reference-core-browser-adapter.js','reference.cjs','trace-reference.js','common.cjs','controller.cjs','diagnose.cjs','private/src/lib.rs','private/src/main.rs','private/Cargo.lock']
sources=[];text={}
for n in paths:
 p='tools/ai-sigma-native-baseline/'+n;b=gitbytes(source,p);sh=hashlib.sha256(b).hexdigest();expected=inputs['source'].get(str(R/p),sb['bound_sources'].get(p));assert expected==sh,(p,expected,sh)
 sources.append({'path':p,'source_Git':source,'Git_sha256_equal':True,'sha256':sh,'current_sha256':sha(R/p),'current_equal_to_StageA':sha(R/p)==sh});text[n]=b.decode()
assert 'intra_op_num_threads=1' in text['ort.py'] and 'ORT_SEQUENTIAL' in text['ort.py']
new=text['reference-core-native.js'];old=text['reference-core-browser-adapter.js'];oldtimer='await new Promise(r=>setTimeout(r,0));';comment='/* native: no browser artificial timer; dedicated process + NN IPC */'
assert old.count(oldtimer)==2 and old.replace(oldtimer,comment)==new
pr=gitbytes(source,'research-data/ai-sigma/165-native-baseline/preregister-stageA.json');fi=gitbytes(source,'research-data/ai-sigma/165-native-baseline/stageA-inputs.json');assert fi==(R/'research-data/ai-sigma/165-native-baseline/stageA-inputs.json').read_bytes()
model=R/'models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx';modelsha=sha(model);assert modelsha=='d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d'
oldraw=read('.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT/runs/port151-stageA-r2/browser-result.json');assert refs[-1]['sha256']=='d37215cbc7914519ca24ab254c5e413d21e780389094faed537280a059c234d2'
cross=[]
for r in raw['rows']:
 assert len(r['CP_receipts'])==32 and [x['K'] for x in r['CP_receipts']]==list(range(1,33))
 assert all(a['receive_ms']<=b['receive_ms'] for a,b in zip(r['CP_receipts'],r['CP_receipts'][1:]));assert all(cp['generation']==r['cp']['generation'] for cp in r['CPs'])
 assert r['NN_calls']==r['completed']==32 and r['discardedNN']==r['terminal_noNN']==0 and len(r['spans'])==32
 assert r['zero']=={'activeNN':0,'handles':0,'active':False}
 if r['engine']!='candidate':continue
 n=r['numeric'][0];m=next(x for x in oldraw['rows'] if x['fixture_id']==r['fixture_id'] and x['engine']=='candidate')['numeric'][0];assert n['features_bits']==m['features_bits']
 vals=n['policy_logits']+[n['value']];prev=m['policy_logits']+[m['value']];deltas=[abs(a-b) for a,b in zip(vals,prev)];assert len(vals)==len(prev)==137
 assert all(abs(a-b)<=1e-4+1e-4*abs(b) for a,b in zip(vals,prev))
 cross.append({'fixture':r['fixture_id'],'features_bits_exact':True,'outputs':137,'different_f32_bits':sum(bits(a)!=bits(b) for a,b in zip(vals,prev)),'max_abs':max(deltas),'abs1e4_rel1e4':True,'backend_different':True,'no_crossbackend_path_claim':True})
proc=read(B/'native165-mechanism-r1.process.json');stop=read('research-data/ai-sigma/165-native-baseline/stageA-stop.json');control=read(B/'native165-mechanism-r1/control-summary.json');monitor=read(B/'native165-mechanism-r1/pause-monitor-stop.json');started=read(B/'native165-mechanism-r1.started.json')
assert proc['exit']==0 and proc['stop_reason'] is None and proc['remaining']==proc['unknown_adopted']==[]
assert stop['source_Git']=='a09279c' and stop['last_heavy_end']==proc['end'];assert stop['Model_engine_exit']==raw['closed']
assert monitor['state']=='READY' and monitor['failure'] is None and monitor['pending_children']==[] and monitor['active_monitor_timer'] is False and monitor['all_owned_read_callbacks_waited'] is True
assert control['primary'] is None and control['control'] is None and control['monitor_state']=='READY'
readerrows=[z for z in monitor['rows'] if 'exitCode' in z];assert len(readerrows)==4 and all(z['exitCode']==0 and z['error'] is None for z in readerrows)
assert datetime.datetime.fromisoformat(proc['start'])<datetime.datetime.fromisoformat(monitor['UTC'].replace('Z','+00:00'))<=datetime.datetime.fromisoformat(proc['end'])
identities=[{'pid':x['pid'],'start_ticks':x['start_ticks'],'type':'engine/init'} for v in raw['init'].values() for x in v['identities']]
identities += [{'pid':proc['runner_pid'],'start_ticks':proc['runner_starttick'],'type':'outer'},{'pid':proc['child_pid'],'start_ticks':proc['child_starttick'],'type':'controller'}]
for x in identities:
 try:s=(pathlib.Path('/proc')/str(x['pid'])/'stat').read_text().rsplit(')',1)[1].split();x['current_exact_present']=int(s[19])==x['start_ticks'];x['current_start_ticks']=int(s[19])
 except FileNotFoundError:x['current_exact_present']=False
assert not any(x['current_exact_present'] for x in identities)
eventcounts={}
for line in (B/'native165-mechanism-r1.monitor.jsonl').open():
 v=json.loads(line);k=v.get('kind','unknown');eventcounts[k]=eventcounts.get(k,0)+1
(D/'binding.json').write_text(json.dumps({'issue':'quoridor-4lc.168','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_Git':source,'native_binary_sha256':binarysha,'model_sha256':modelsha,'source_binding':sources,'preregister_Git_sha256':hashlib.sha256(pr).hexdigest(),'fixed_inputs_Git_sha256':hashlib.sha256(fi).hexdigest(),'native_timer_only_operational_difference_supported':True,'fixed_Web_Git':'751186344fc52ad0c29bc65922e62c6fa915f006','crossbackend_root_only':cross,'phase':{'start':proc['start'],'end':proc['end'],'exit':proc['exit'],'stop_reason':proc['stop_reason'],'remaining':proc['remaining'],'unknown_adopted':proc['unknown_adopted'],'saved_model_receipts_equal':True,'reader_callbacks':readerrows,'monitor_end':monitor['UTC'],'pending':monitor['pending_children'],'timer':monitor['active_monitor_timer'],'monitor_event_counts':eventcounts,'current_identities':identities,'source_write_stopped_for_StageA_only':True,'new_StageB_writer_may_continue':True,'not_allhost_allperiod_natural_exit':True},'minimal_references':refs,'new_NN':0,'native_binary_execution':0,'limits':['snapshots do not prove wholegame clocks or CPU cycles','current identity absence is current-only','reader receipts saved; no allperiod monitoring audit','source Git corresponds StageA; current differences are not replacement source']},indent=2)+'\n')
print(json.dumps({'source':source,'binarysha':binarysha,'crossbackend_max':max(x['max_abs'] for x in cross),'current_identities_absent':len(identities),'reader_callbacks':len(readerrows),'newNN':0}))
