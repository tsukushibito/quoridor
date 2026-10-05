"""Single-owner supervisor role transition using the existing App Server client."""
import asyncio
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import uuid

ROOT=Path('/workspaces/quoridor/.worktree/ai-sigma');MAIN=Path('/workspaces/quoridor')
OUT=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-CRITICAL-ROLES-V2'
TOOLS=ROOT/'tools/ai-sigma-critical-roles-v2'
CFG=ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json'
STATE=MAIN/'.artifacts/research-team/scheduler-sigma-continuation-20261001'
REG=MAIN/'.artifacts/research-team/registry.json'
OLD_TOOLS=ROOT/'tools/ai-sigma-supervisor-role-review'
OLD_RUN=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-ROLE-REVIEW/live-05968fe5-4864-45d5-b034-a7e73b7faf36'
THREAD='01a0f6b5-b1bd-7752-b0bb-74a336e459a4'
OUT.mkdir(parents=True,exist_ok=True);(OUT/'tmp').mkdir(exist_ok=True)
os.sched_setaffinity(0,{0});os.environ.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'))
spec=importlib.util.spec_from_file_location('research_team',MAIN/'scripts/dev/research-team.py')
team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):
 (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def proc(pid):
 try:
  p=Path('/proc')/str(pid);s=(p/'stat').read_text().rsplit(')',1)[1].split()
  return {'pid':pid,'start_ticks':s[19],'state':s[0],'rss_bytes':int(s[21])*os.sysconf('SC_PAGE_SIZE'),'affinity':list(os.sched_getaffinity(pid)),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
 except OSError:return None
def alive(identity):
 p=proc(identity['pid'])
 return bool(p and p['state']!='Z' and all(str(identity[k])==str(p[k]) for k in ('pid','start_ticks','boot_id')))
def state():return json.loads((STATE/'state.json').read_text())
def cmd(args,seconds=35):
 p=subprocess.Popen(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True);identity=proc(p.pid)
 try:o,e=p.communicate(timeout=seconds)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:o,e=p.communicate(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);o,e=p.communicate(timeout=3)
  write('command-timeout-'+str(uuid.uuid4())+'.json',{'command':args,'identity':identity,'at':now(),'stdout':o,'stderr':e,'exit_code':p.returncode,'reaped':True});raise
 row={'at':now(),'command':args,'identity':identity,'exit_code':p.returncode,'stdout':o,'stderr':e,'reaped':True}
 with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 if p.returncode:raise RuntimeError(e or o)
 return json.loads(o)
def wrapper(action,interrupt=False):
 args=['bash',str(MAIN/'scripts/dev/research-scheduler.sh'),action,'--state-dir',str(STATE)]
 if action in ('validate','start','run'):args+=['--config',str(CFG)]
 if interrupt:args+=['--interrupt-owned-turn']
 return cmd(args,55 if action=='stop' else 30)

PROPOSAL=MAIN/'.artifacts/research-team/critical-supervision-v2'
ROLES=['supervisor','coordinator','critic']
THREADS={'supervisor':THREAD,'coordinator':'01a0f31b-3409-75f2-a30e-453a50484f94','critic':'01a0f31d-8227-7e03-a7e6-915b4918c11b'}
async def stop():
 assert not (OUT/'before.json').exists()
 manifest=json.loads((PROPOSAL/'manifest.json').read_text());paths=[]
 for role in ROLES:
  relative=f'.agents/research-team/roles/{role}.md';assert sha(PROPOSAL/relative)==manifest[relative]['proposed_sha256']
  for base in (MAIN,ROOT):
   p=base/relative;assert sha(p)==manifest[relative]['before_sha256'];paths.append(p)
 paths += [b/'docs/design/ai-research-team.md' for b in (MAIN,ROOT)]+[REG,CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md',STATE/'state.json',STATE/'events.jsonl',OLD_TOOLS/'watch.py',OLD_TOOLS/'safe_state.py',OLD_RUN/'expectations.json',OLD_RUN/'monitor-process.json']
 rows=[]
 for i,p in enumerate(paths):
  data=p.read_bytes();copy=OUT/f'before-{i}-{p.name}';copy.write_bytes(data);rows.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'copy':str(copy)})
 reg=json.loads(REG.read_text());st=state();monitor=json.loads((OLD_RUN/'monitor-process.json').read_text())['process']
 refs=[b/'.agents/research-team/common.md' for b in (MAIN,ROOT)]+[b/f'.agents/research-team/roles/{r}.md' for b in (MAIN,ROOT) for r in ['steward','hypothesis','experiment']]+[MAIN/'scripts/dev/research-team.py',MAIN/'scripts/dev/research-scheduler.py',ROOT/'docs/design/ai-sigma-continuation-20261001.md']+[PROPOSAL/'manifest.json',PROPOSAL/'design-addition.md']+[PROPOSAL/f'.agents/research-team/roles/{r}.md' for r in ROLES]
 write('before.json',{'at':now(),'operator':proc(os.getpid()),'sources':rows,'immutable_refs':[{'path':str(p),'sha256':sha(p)} for p in refs],'state':st,'monitor':monitor,'registry':reg,'manifest':manifest,'writer_basis':'Explicit user single-owner delegation; root/coordinator not writing scope; input hashes plus dispatch/registry locks, not host-wide writer proof'})
 host=cmd(['codex','app-server','daemon','version'],10)
 with team.dispatch_lock(MAIN):
  async with team.AppServer(host,timeout=15) as server:
   t=await server.read_thread(THREAD);write('supervisor-before-stop.json',t)
   assert t['status']['type'] in ('idle','notLoaded') and not st.get('owned') and not st.get('recovery_required'),'Active/unknown supervisor; no interrupt'
   current=state();assert current['process']==st['process'] and current['binding']==st['binding'] and current.get('owned') is None and alive(st['process']) and alive(monitor)
   receipt=wrapper('stop');current=state();assert current['phase']=='stopped' and not current.get('owned') and current.get('process') is None
   write('scheduler-stopped.json',{'at':now(),'receipt':receipt,'state':current,'owned_before':None,'interrupt_sent':False,'dispatch_lock_used':True})
 until=time.monotonic()+100
 while alive(monitor) and time.monotonic()<until:time.sleep(.1)
 assert not alive(monitor),'Monitor still alive; no source change or duplicate'
 write('monitor-stopped.json',{'at':now(),'identity':monitor,'observed':proc(monitor['pid']),'end':json.loads((OLD_RUN/'monitor-ended.json').read_text())})

async def apply():
 before=json.loads((OUT/'before.json').read_text());assert state()['phase']=='stopped' and not state().get('owned') and not alive(before['monitor'])
 host=cmd(['codex','app-server','daemon','version'],10);results={}
 async with team.AppServer(host,timeout=15) as server:
  for role in ROLES:
   thread=THREADS[role];until=time.monotonic()+75
   while True:
    with team.dispatch_lock(MAIN),REG.with_suffix('.lock').open('a') as lock:
     fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
     t=await server.read_thread(thread)
     with (OUT/'idle-observations.jsonl').open('a') as f:f.write(json.dumps({'at':now(),'role':role,'thread_id':thread,'status':t['status']})+'\n')
     if t['status']['type'] in ('idle','notLoaded'):
      registry=team.load_registry(REG,MAIN);entry=registry['roles'][role];assert entry['thread_id']==thread
      original=await server.request('thread/resume',{'threadId':thread,'excludeTurns':True});write('rpc-'+role+'-before.json',original)
      relative=f'.agents/research-team/roles/{role}.md';proposal=(PROPOSAL/relative).read_bytes()
      for base in (MAIN,ROOT):
       p=base/relative;assert sha(p)==before['manifest'][relative]['before_sha256'];p.write_bytes(proposal)
      text,digest=team.role_definition(role,Path(registry['definitions_root']));text+=f'\n\nRuntime registry: {REG}\nRole: {role}\nClient: bash {MAIN}/scripts/dev/research-team.sh\n'
      params={'threadId':thread,'excludeTurns':True,'developerInstructions':text};write('rpc-'+role+'-request.json',params)
      try:response=await server.request('thread/resume',params)
      except Exception as error:
       for base in (MAIN,ROOT):
        path=base/relative;row=next(x for x in before['sources'] if x['path']==str(path));path.write_bytes(Path(row['copy']).read_bytes())
       write('rpc-'+role+'-unconfirmed.json',{'at':now(),'error':str(error),'source_rolled_back_for_registry_communication':True,'saved_payload_application_unknown':True,'no_retry':True})
       results[role]={'applied':False,'thread_id':thread,'reason':'RPC unknown/failure; source restored, registry old, no blind retry'};break
      write('rpc-'+role+'-applied.json',response)
      settings={k:response.get(k) for k in ('model','modelProvider','reasoningEffort','cwd','approvalPolicy','sandbox')};assert all(original.get(k)==response.get(k) for k in settings)
      reread=await server.read_thread(thread);write('rpc-'+role+'-reread.json',reread);assert reread['status']['type']=='idle'
      entry['definition_sha256']=digest;team.save_registry(REG,registry);assert team.role_entry(team.load_registry(REG,MAIN),role)['definition_sha256']==digest
      results[role]={'applied':True,'at':now(),'thread_id':thread,'definition_sha256':digest,'explicit_payload_sha256':hashlib.sha256(text.encode()).hexdigest(),'settings':settings,'body_readback_unavailable':'developerInstructions' not in response and 'developerInstructions' not in reread,'active_interrupt_or_resume':False};break
    if time.monotonic()>=until or dt.datetime.now(dt.timezone.utc)>=dt.datetime(2026,10,1,23,22,tzinfo=dt.timezone.utc):
     results[role]={'applied':False,'reason':'Active/unknown role retained unchanged; bounded idle wait exhausted','thread_id':thread,'source_and_registry_kept_old_for_communication':True};break
    await asyncio.sleep(3)
 write('sessions-applied.json',{'at':now(),'roles':results,'active_interrupts':0,'forced_turns':0})
 # Integrate the short design addition once; preserve existing unrelated content.
 addition=(PROPOSAL/'design-addition.md').read_text()
 for base in (MAIN,ROOT):
  p=base/'docs/design/ai-research-team.md';text=p.read_text();heading='## 継続枠の監督運用'
  if heading in text:text=text.split(heading)[0].rstrip()+'\n\n'+heading+'\n\n'+addition
  else:text+='\n\n'+heading+'\n\n'+addition
  p.write_text(text)
 supplement='批判的監督v2: 統括の判断/契約/検証手順も評価し、複数点検の累積費用と目標に使える証拠増加を比較する。active/報告待ち/原因発見だけで改善提案を抑止しない。提案の採否/理由/担当/結果/確認時点を既存記録から追い、未回答や継続問題は新根拠で再提案する。通常の許可枠内デバッグ修正版確認と正式棋力条件の有利な再試行を区別し、必要範囲の最終固定版独立検証へ渡す。過去窓/NN許可/資源/製品範囲は拡張0。保存済み観測と既存90/120/180秒guard内で判断し、追加読取や全再計算を義務にしない。'
 for p in [CFG.parent/'prompt.md',ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md']:p.write_text(p.read_text()+'\n'+supplement+'\n')
 source=(OLD_TOOLS/'watch.py').read_text().replace("SIGMA-SUPERVISOR-ROLE-REVIEW'","SIGMA-CRITICAL-ROLES-V2'").replace("'recovery_issue':'quoridor-4lc.61'","'recovery_issue':'quoridor-4lc.82.1'")
 source=source.replace("ROOT/'tools/ai-sigma-supervisor-role-review',","ROOT/'tools/ai-sigma-supervisor-role-review',\n                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-ROLE-REVIEW',\n                 ROOT/'tools/ai-sigma-critical-roles-v2',\n                 ROOT/'docs/reports/ai-sigma-steward-critical-roles-v2.md',")
 compile(source,str(TOOLS/'watch.py'),'exec');(TOOLS/'watch.py').write_text(source);(TOOLS/'safe_state.py').write_bytes((OLD_TOOLS/'safe_state.py').read_bytes())

def restart():
 before=json.loads((OUT/'before.json').read_text());assert state()['phase']=='stopped' and not state().get('owned') and not alive(before['monitor']) and not alive(before['state']['process'])
 validation=wrapper('validate');epoch=now();receipt=wrapper('start');st=state();assert st['phase']=='running' and alive(st['process'])
 run=OUT/('live-'+str(uuid.uuid4()));run.mkdir();inputs=[CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',TOOLS/'watch.py',TOOLS/'safe_state.py',MAIN/'.agents/research-team/common.md']+[b/f'.agents/research-team/roles/{r}.md' for b in (MAIN,ROOT) for r in ROLES]
 expected={'process':st['process'],'binding':st['binding'],'operation_epoch_utc':epoch,'input_hashes':{str(p):sha(p) for p in inputs}};(run/'expectations.json').write_text(json.dumps(expected,indent=2)+'\n')
 with (run/'console.log').open('w') as f:p=subprocess.Popen([sys.executable,'-B',str(TOOLS/'watch.py'),'--run-dir',str(run),'--expectations',str(run/'expectations.json')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=f,stderr=f,start_new_session=True)
 identity=proc(p.pid);until=time.monotonic()+15
 while time.monotonic()<until:
  if (run/'monitor-observation.json').exists():break
  if p.poll() is not None:raise RuntimeError('New monitor exited; no duplicate')
  time.sleep(.1)
 else:raise RuntimeError('New monitor unconfirmed')
 write('live-applied.json',{'at':now(),'operator':proc(os.getpid()),'validation':validation,'start_receipt':receipt,'state':state(),'monitor':identity,'run':str(run),'monitor_process':json.loads((run/'monitor-process.json').read_text()),'expectations':expected,'new_epoch':epoch,'full_period_success_claimed':False})

if __name__=='__main__':
 action=sys.argv[1]
 try:
  if action in ('stop','apply'):asyncio.run(globals()[action]())
  else:globals()[action]()
 except Exception as e:write('failure-'+action+'-'+str(uuid.uuid4())+'.json',{'at':now(),'error':str(e),'operator':proc(os.getpid()),'blind_retry':False});raise
 finally:write('short-'+action+'-'+str(uuid.uuid4())+'-end.json',{'at':now(),'process':proc(os.getpid()),'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'exit_after_record':True})
