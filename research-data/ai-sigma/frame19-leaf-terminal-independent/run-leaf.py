"""241 single bounded job. Exact task/schema, stopped inputs, current frame19 admission."""
from pathlib import Path
import ast,datetime,hashlib,json,os,signal,subprocess,time
D=Path('research-data/ai-sigma/frame19-leaf-terminal-independent');P=Path('research-data/ai-sigma/frame19-leaf-terminal');R=Path.cwd();os.sched_setaffinity(0,{0});utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def table():
 z={}
 for p in Path('/proc').iterdir():
  if p.name.isdigit():
   try:s=(p/'stat').read_text().rsplit(')',1)[1].split();z[int(p.name)]={'PID':int(p.name),'PPID':int(s[1]),'tick':s[19],'RSS':int(s[21])*4096,'state':s[0]}
   except(OSError,ValueError):pass
 return z
tab=table();anc={};pp=tab[os.getpid()]['PPID']
while pp in tab and pp not in anc:anc[pp]=tab[pp]['tick'];pp=tab[pp]['PPID']
def family(tt,roots):
 f=set(roots);changed=True
 while changed:
  n=len(f);f.update(pid for pid,z in tt.items()if z['PPID']in f);changed=len(f)>n
 return f
def physics(exclude=()):
 current=[];foreign=[];tt=table();skip=family(tt,exclude)
 for pid,z in tt.items():
  if pid==os.getpid()or pid in skip or anc.get(pid)==z['tick']or z['state']=='Z':continue
  try:argv=Path('/proc',str(pid),'cmdline').read_bytes().decode().split('\0');aff=sorted(os.sched_getaffinity(pid));exe=Path(argv[0]).name
  except(OSError,UnicodeError,IndexError):continue
  if not exe.startswith(('python','node')):continue
  script=next((a for a in argv[1:6]if a.endswith(('.py','.cjs','.js'))and' 'not in a and'\n'not in a and Path(a).is_file()),'')
  if any(k in script for k in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/','.artifacts/ai-sigma/continuation-20261001/']):
   q={**z,'script':script,'affinity':aff,'argv':argv[:7]};current.append(q)
   if not script.endswith(('/save_git.py','/save.py','/pack.py','/scheduler.py','/watch.py')):foreign.append(q)
 return current,foreign
assert utc()<'2026-10-05T00:36:00+00:00';assert not(D/'process.json').exists();stopfile=P/'scientific-stop-v1.json';assert sha(stopfile)=='445775e90e3c6f380852174b38278ee5a08a7ca8d144755f2e4f25884293f638';stop=json.loads(stopfile.read_text());assert stop['sourcewriter_scientific_stopped']and stop['all_scientific_childwait']and stop['current_exact_absent']and not stop['further_science_authorized'];bound={str(stopfile):sha(stopfile)}
for field in ['source_SHA','payload_SHA']:
 for p,h in stop[field].items():assert sha(p)==h;bound[p]=h
cp=P/'scientific-compact-v1.json';assert sha(cp)=='2a4a5b4f4a5877afb0aab588ca5e466110b3c5bf2628f8870389567a12c1641c';bound[str(cp)]=sha(cp)
for p in sorted(P.glob('background-*/result.json')):
 q=json.loads(p.read_text());assert q['cleanup_complete']and not q['remaining'];bound[str(p)]=sha(p)
assert len(list(P.glob('background-*/result.json')))==5
for p in sorted((P/'guardians').glob('*/process.json')):
 q=json.loads(p.read_text());assert q['all_child_waited']and q['current_exact_absent']and not q['remaining'];bound[str(p)]=sha(p)
 for pid,tick in {str(q['runner_pid']):q['runner_tick'],**q['tracked']}.items():assert int(pid)not in tab or str(tab[int(pid)]['tick'])!=str(tick)
for n in ['openings4-v1.json','optional4-r1-hands.jsonl','remaining3-r1-hands.jsonl','exact-cases-preregister-v1.json','preregister-v1.json','fixture-profile-settings-r2.json','optional4-settings-r1.json','remaining3-settings-r1.json','exact-cases-settings-r1.json','optional4-r1-censored-ledger.json']:
 p=P/n;bound[str(p)]=sha(p)
pr=json.loads((P/'exact-cases-preregister-v1.json').read_text());assert sha(pr['source'])==pr['sourceSHA'];bound[pr['source']]=pr['sourceSHA']
for n in ['reference.cjs','game.js','context.js','reference-core-native.js','trace-reference.js','common.cjs']:
 p=R/'tools/ai-sigma-native-baseline'/n;bound[str(p)]=sha(p)
save('stopped-inputs.json',{'UTC':utc(),'SHA':bound,'testlabel_read':False,'old229_or238_checker_executed':False})
loadedp=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame19/running-loaded.json';loaded=json.loads(loadedp.read_text());assert loaded['parent_sha']==sha(R/'docs/design/ai-sigma-continuation-20261001.md');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
for role in ['scheduler','monitor']:
 q=loaded[role].get('process',loaded[role]);assert str(tab[q['pid']]['tick'])==str(q['start_ticks'])and q['boot_id']==boot
for p,h in loaded['input_hashes'].items():assert sha(p)==h
mp=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mp.stat().st_mtime<120;sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert sch['phase']=='running'and not sch.get('recovery_required');quiet=sch['next_at']-time.time();current,foreign=physics();gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
entry=D/'check-leaf.py';out=D/'result.json';ast.parse(entry.read_text());assert not out.exists();task='frame19-leaf-terminal-241-v1';cmd=['python3','-B',str(entry),'--task',task,'--input-manifest',str(D/'stopped-inputs.json'),'--out',str(out)];assert entry.name=='check-leaf.py'and not any('check-data' in x or 'check-clock' in x for x in cmd)
allocated=sum(p.stat().st_blocks*512 for p in D.iterdir()if p.is_file())+(R/'docs/reports/ai-sigma-critic-frame19-leaf-terminal.md').stat().st_blocks*512;forecast=allocated+196608+32768+65536;assert forecast<524288;assert sum(q['RSS']for q in current)+536870912<8*1024**3
admit={'UTC':utc(),'producer_stop_background_child_SHA':bound,'runtime':str(loadedp),'monitor':str(mp),'owned':sch.get('owned'),'nextquiet_s':quiet,'current':current,'foreign':foreign,'GPU':gpu,'ancestor_PIDticks':anc,'scope_allocated':allocated,'forecast_incl_uniqueGit_tmp_metadata':forecast,'new_reservation1048576':1048576,'guard786432':786432,'pool_before49389568_after48340992':True,'parentadd0':True,'oldunknown_discount0':True,'argv':cmd,'entry_SHA':sha(entry),'expected_task':task,'expected_output_schema':'leaf-terminal-independent-v1','child_argv':['node','--max-old-space-size=384',str(D/'replay-leaf.cjs'),'--task','frame19-leaf-replay-241-v1'],'CPU':[0],'RAMguard':469762048,'onejob':True,'not_future_allhost_guarantee':True};save('admission.json',admit)
if foreign or gpu or quiet<90:save('NOT_RUN.json',{'typed':'CURRENT_PHYSICAL_COMPETITION_OR_QUIET','newNN':0,'calc_started':False});print(json.dumps({'NOT_RUN':True,'foreign':foreign,'quiet':quiet}));raise SystemExit(0)
print(json.dumps({'START_PLAN':task,'UTC':utc(),'CPU':[0],'newNN':0,'max1_hard45':True}),flush=True);start=utc();t=time.monotonic();p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);tick=table()[p.pid]['tick'];reason=None;peak=0
while True:
 try:stdout,stderr=p.communicate(timeout=.05);break
 except subprocess.TimeoutExpired:
  _,foreign=physics((p.pid,));tt=table();rss=sum(tt.get(pid,{}).get('RSS',0)for pid in family(tt,[p.pid]));peak=max(peak,rss)
  if foreign or rss>=469762048 or time.monotonic()-t>=45:
   reason='FOREIGN_STARTED'if foreign else'RAM_GUARD'if rss>=469762048 else'45SEC_GUARD';os.killpg(p.pid,signal.SIGTERM)
   try:stdout,stderr=p.communicate(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=2)
   break
(D/'calc.log').write_bytes(stdout+stderr);q=table().get(p.pid);rec={'startUTC':start,'endUTC':utc(),'PID':p.pid,'tick':tick,'argv':cmd,'entry_SHA':sha(entry),'exit':p.returncode,'wait':True,'current_exact_absent':q is None or q['tick']!=tick,'wall':time.monotonic()-t,'reason':reason,'peakRSS_point':peak,'newNN':0,'conservative_calc_charge45':True};save('process.json',rec)
if p.returncode==0:
 result=json.loads(out.read_text());assert result['task']==admit['expected_task']and result['schema']==admit['expected_output_schema'];rec['output_identity_verified']=True;save('process.json',rec)
print(json.dumps({**rec,'stdout':stdout.decode()[:14000],'stderr':stderr.decode()[:1600]}))
