"""234 single bounded job, dedicated argv/task/output; prebind stop and cleanup."""
from pathlib import Path
import ast,datetime,hashlib,json,os,signal,subprocess,time
D=Path('research-data/ai-sigma/frame18-native-independent');P=Path('research-data/ai-sigma/frame18-native-connection');R=Path.cwd();os.sched_setaffinity(0,{0});utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
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
def physics(exclude=()):
 current=[];foreign=[]
 for pid,z in table().items():
  if pid in (os.getpid(),*exclude)or anc.get(pid)==z['tick']or z['state']=='Z':continue
  try:argv=Path('/proc',str(pid),'cmdline').read_bytes().decode().split('\0');aff=sorted(os.sched_getaffinity(pid))
  except(OSError,UnicodeError):continue
  script=next((a for a in argv[1:5]if a.endswith(('.py','.cjs','.js'))and' 'not in a and '\n'not in a and Path(a).is_file()),'')
  if any(k in script for k in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/','.artifacts/ai-sigma/continuation-20261001/']):
   q={**z,'script':script,'affinity':aff,'argv':argv[:6]};current.append(q)
   if not script.endswith(('/save_git.py','/save.py','/pack.py','/scheduler.py','/watch.py')):foreign.append(q)
 return current,foreign
assert utc()<'2026-10-04T14:24:00+00:00';stopfile=P/'science-stop.json';assert sha(stopfile)=='54618c6654e45228faa8b620a57b94809bdbbf93ab3c437082b105c07c9f9bed';stop=json.loads(stopfile.read_text());assert stop['source_science_writer_stopped']and stop['children_waited']and stop['current_exact_absent'];bound={str(stopfile):sha(stopfile)}
for field in ['sources_SHA','payload_SHA']:
 for p,h in stop[field].items():assert sha(p)==h;bound[p]=h
for name in ['background-parity-r1','background-search-r2']:
 p=P/name/'result.json';q=json.loads(p.read_text());assert q['cleanup_complete']and q['exit_code']==0 and not q['remaining'];bound[str(p)]=sha(p)
for name in ['parity-r1','search-r2']:
 p=P/'guardians'/name/'process.json';q=json.loads(p.read_text());assert q['all_child_waited']and q['current_exact_absent']and not q['remaining']and q['exit']==0;bound[str(p)]=sha(p)
 for pid,tick in {str(q['runner_pid']):q['runner_tick'],**q['tracked']}.items():assert int(pid)not in tab or str(tab[int(pid)]['tick'])!=str(tick)
loadedp=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame18/running-loaded.json';loaded=json.loads(loadedp.read_text());assert loaded['parent_sha']==sha(R/'docs/design/ai-sigma-continuation-20261001.md')
for role in ['scheduler','monitor']:
 q=loaded[role].get('process',loaded[role]);assert str(tab[q['pid']]['tick'])==str(q['start_ticks'])
mp=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mp.stat().st_mtime<120;sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert sch['phase']=='running'and not sch.get('recovery_required');quiet=sch['next_at']-time.time();current,foreign=physics();gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
entry=D/'check-native.py';out=D/'result.json';assert entry.name=='check-native.py'and not out.exists();ast.parse(entry.read_text());cmd=['python3','-B',str(entry),'--task','native-234-saved-v1','--out',str(out)];assert not any('229' in x or 'check-data' in x for x in cmd)
allocated=sum(p.stat().st_blocks*512 for p in D.iterdir()if p.is_file())+(R/'docs/reports/ai-sigma-critic-native-connection.md').stat().st_blocks*512;forecast=allocated+131072+65536+65536;assert forecast<524288;assert sum(q['RSS']for q in current)+268435456<8*1024**3
admit={'UTC':utc(),'producer_stop_background_child_SHA':bound,'runtime':str(loadedp),'monitor':str(mp),'owned':sch.get('owned'),'nextquiet_s':quiet,'current':current,'foreign':foreign,'GPU':gpu,'ancestor_PIDticks':anc,'scope_allocated':allocated,'forecast_including_uniqueGit_tmp_metadata':forecast,'parentadd':0,'old_unknown_discount':0,'argv':cmd,'entry_SHA':sha(entry),'expected_task':'native-234-saved-v1','expected_output_schema':'native-independent-result-v1','CPU':[0],'RAMguard':234881024,'not_allhost_future_guarantee':True};save('admission.json',admit)
if foreign or gpu or quiet<60:save('NOT_STARTED.json',{'typed':'CURRENT_PHYSICAL_COMPETITION_OR_QUIET','newNN':0});print(json.dumps({'NOT_STARTED':True,'foreign':foreign,'quiet':quiet}));raise SystemExit(0)
start=utc();t=time.monotonic();p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);tick=table()[p.pid]['tick'];reason=None
while True:
 try:stdout,stderr=p.communicate(timeout=.05);break
 except subprocess.TimeoutExpired:
  _,foreign=physics((p.pid,));rss=table().get(p.pid,{}).get('RSS',0)
  if foreign or rss>=234881024 or time.monotonic()-t>=45:
   reason='FOREIGN_STARTED'if foreign else 'RAM_GUARD'if rss>=234881024 else '45SEC_GUARD';os.killpg(p.pid,signal.SIGTERM)
   try:stdout,stderr=p.communicate(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=2)
   break
(D/'calc.log').write_bytes(stdout+stderr);q=table().get(p.pid);rec={'startUTC':start,'endUTC':utc(),'PID':p.pid,'tick':tick,'argv':cmd,'entry_SHA':sha(entry),'exit':p.returncode,'wait':True,'current_exact_absent':q is None or q['tick']!=tick,'wall':time.monotonic()-t,'reason':reason,'newNN':0,'onejob_cap45':True};save('process.json',rec)
if p.returncode==0:
 result=json.loads(out.read_text());assert result['task']==admit['expected_task']and result['schema']==admit['expected_output_schema'];rec['output_identity_verified']=True;save('process.json',rec)
print(json.dumps({**rec,'stdout':stdout.decode()[:2200],'stderr':stderr.decode()[:1200]}))
