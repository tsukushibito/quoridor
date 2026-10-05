"""238 exact task runner: fresh frame19 stop/cleanup/current/physical admission."""
from pathlib import Path
import ast,datetime,hashlib,json,os,signal,subprocess,time,sys
D=Path('research-data/ai-sigma/frame19-native-independent');P=Path('research-data/ai-sigma/frame19-native-arena');R=Path.cwd();os.sched_setaffinity(0,{0});mode=sys.argv[1];assert mode in ['clock','replay'];utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
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
 current=[];foreign=[];alltab=table();skip=set(exclude)
 changed=True
 while changed:
  before=len(skip);skip.update(pid for pid,z in alltab.items()if z['PPID']in skip);changed=len(skip)>before
 for pid,z in alltab.items():
  if pid==os.getpid()or pid in skip or anc.get(pid)==z['tick']or z['state']=='Z':continue
  try:argv=Path('/proc',str(pid),'cmdline').read_bytes().decode().split('\0');aff=sorted(os.sched_getaffinity(pid));exe=Path(argv[0]).name
  except(OSError,UnicodeError,IndexError):continue
  # Executable identity first: git hash-object arguments ending.py are NOT Python.
  if not exe.startswith(('python','node')):continue
  script=next((a for a in argv[1:6]if a.endswith(('.py','.cjs','.js'))and' 'not in a and '\n'not in a and Path(a).is_file()),'')
  if any(k in script for k in ['tools/ai-sigma-','tools/nnue-training/','research-data/ai-sigma/','.artifacts/ai-sigma/continuation-20261001/']):
   q={**z,'script':script,'affinity':aff,'argv':argv[:7]};current.append(q)
   if not script.endswith(('/save_git.py','/save.py','/pack.py','/scheduler.py','/watch.py')):foreign.append(q)
 return current,foreign
assert utc()<'2026-10-05T00:38:00+00:00';stopfile=P/'science-stop-v1.json';stop=json.loads(stopfile.read_text());assert stop['source_writer_stopped']and stop['science_stopped']and stop['children_waited_exactabsent'];bound={str(stopfile):sha(stopfile)}
for field in ['source_SHA','payload_SHA']:
 for p,h in stop[field].items():assert sha(p)==h;bound[p]=h
for name in ['background-preflight-r1','background-pilot-r1','background-pilot-r2','background-later4-r1']:
 p=P/name/'result.json';q=json.loads(p.read_text());assert q['cleanup_complete']and not q['remaining'];bound[str(p)]=sha(p)
allr=json.loads((P/'all-attempt-result-v1.json').read_text())
for q in allr['processes']:
 assert q['all_child_waited']and q['current_exact_absent']and not q['remaining']
 for pid,tick in {str(q['runner_pid']):q['runner_tick'],**q['tracked']}.items():assert int(pid)not in tab or str(tab[int(pid)]['tick'])!=str(tick)
for n in ['openings8-v1.json','pilot-r2-hands.jsonl','later4-r1-hands.jsonl','pilot-r1-hands.jsonl','preflight-settings-r1.json','pilot-settings-r2.json','later4-settings-r1.json']:
 p=P/n;bound[str(p)]=sha(p)
for n in ['reference.cjs','game.js','context.js','reference-core-native.js','trace-reference.js','common.cjs']:
 p=R/'tools/ai-sigma-native-baseline'/n;bound[str(p)]=sha(p)
save('stopped-inputs.json',{'UTC':utc(),'SHA':bound,'testlabel_read':False,'old229_entrypoint_used':False})
loadedp=R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame19/running-loaded.json';loaded=json.loads(loadedp.read_text());assert loaded['parent_sha']==sha(R/'docs/design/ai-sigma-continuation-20261001.md');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
for role in ['scheduler','monitor']:
 q=loaded[role].get('process',loaded[role]);assert str(tab[q['pid']]['tick'])==str(q['start_ticks'])and q['boot_id']==boot
for p,h in loaded['input_hashes'].items():assert sha(p)==h
mp=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mp.stat().st_mtime<120;sch=json.loads(Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json').read_text());assert sch['phase']=='running'and not sch.get('recovery_required');quiet=sch['next_at']-time.time();current,foreign=physics();gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,check=True,timeout=5).stdout.strip()
entry=D/('check-clock-arena.py'if mode=='clock'else'replay.cjs');out=D/(mode+'-result.json');task='frame19-clock-arena-238-v1'if mode=='clock'else'frame19-rule-replay-238-v1';assert not out.exists();suffix='clock-repaired'if mode=='clock'and(D/'clock-process.json').exists()else mode
if mode=='clock':ast.parse(entry.read_text());cmd=['python3','-B',str(entry)]
else:cmd=['node','--max-old-space-size=384',str(entry)]
cmd+=['--task',task,'--input-manifest',str(D/'stopped-inputs.json'),'--out',str(out)];assert not any('229' in x or 'check-data' in x for x in cmd)
allocated=sum(p.stat().st_blocks*512 for p in D.iterdir()if p.is_file())+(R/'docs/reports/ai-sigma-critic-frame19-native-arena.md').stat().st_blocks*512;forecast=allocated+1572864;assert forecast<2097152;assert sum(q['RSS']for q in current)+536870912<8*1024**3
admit={'UTC':utc(),'producer_stop_background_child_SHA':bound,'runtime':str(loadedp),'monitor':str(mp),'owned':sch.get('owned'),'nextquiet_s':quiet,'current':current,'foreign':foreign,'GPU':gpu,'ancestor_PIDticks':anc,'scope_allocated':allocated,'forecast_including_uniqueGit_tmp_metadata':forecast,'scopeguard3145728':True,'pool66166784_unused61972480':True,'parentadd':0,'old_unknown_discount':0,'argv':cmd,'entry_SHA':sha(entry),'expected_task':task,'expected_output_schema':'frame19-native-independent-v1','CPU':[0],'RAMguard':469762048,'not_allhost_future_guarantee':True};save(suffix+'-admission.json',admit)
if foreign or gpu or quiet<90:save(suffix+'-NOT_STARTED.json',{'typed':'CURRENT_PHYSICAL_COMPETITION_OR_QUIET','newNN':0});print(json.dumps({'NOT_STARTED':True,'foreign':foreign,'quiet':quiet}));raise SystemExit(0)
print(json.dumps({'START_PLAN':mode,'UTC':utc(),'CPU':[0],'newNN':0,'hard45':True}),flush=True)
start=utc();t=time.monotonic();p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);tick=table()[p.pid]['tick'];reason=None;peak=0
while True:
 try:stdout,stderr=p.communicate(timeout=.05);break
 except subprocess.TimeoutExpired:
  _,foreign=physics((p.pid,));tt=table();family={p.pid};changed=True
  while changed:
   before=len(family);family.update(pid for pid,z in tt.items()if z['PPID']in family);changed=len(family)>before
  rss=sum(tt.get(pid,{}).get('RSS',0)for pid in family);peak=max(peak,rss)
  if foreign or rss>=469762048 or time.monotonic()-t>=45:
   reason='FOREIGN_STARTED'if foreign else'RAM_GUARD'if rss>=469762048 else'45SEC_GUARD';os.killpg(p.pid,signal.SIGTERM)
   try:stdout,stderr=p.communicate(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate(timeout=2)
   break
(D/(suffix+'-calc.log')).write_bytes(stdout+stderr);q=table().get(p.pid);rec={'startUTC':start,'endUTC':utc(),'PID':p.pid,'tick':tick,'argv':cmd,'entry_SHA':sha(entry),'exit':p.returncode,'wait':True,'current_exact_absent':q is None or q['tick']!=tick,'wall':time.monotonic()-t,'reason':reason,'peakRSS_point':peak,'newNN':0,'charge45':True};save(suffix+'-process.json',rec)
if p.returncode==0:
 result=json.loads(out.read_text());assert result['task']==admit['expected_task']and result['schema']==admit['expected_output_schema'];rec['output_identity_verified']=True;save(suffix+'-process.json',rec)
print(json.dumps({**rec,'stdout':stdout.decode()[:5500],'stderr':stderr.decode()[:1500]}))
