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
OUT=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-ROLE-REVIEW'
TOOLS=ROOT/'tools/ai-sigma-supervisor-role-review'
CFG=ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json'
STATE=MAIN/'.artifacts/research-team/scheduler-sigma-continuation-20261001'
REG=MAIN/'.artifacts/research-team/registry.json'
OLD_TOOLS=ROOT/'tools/ai-sigma-scheduler-deadline-update'
OLD_RUN=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-DEADLINE-UPDATE/live-1e01a363-ab4b-46e6-b44a-51e1116efeea'
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
def preserve():
 assert not (OUT/'before.json').exists(),'Before evidence already exists'
 paths=[r/'.agents/research-team/roles/supervisor.md' for r in (MAIN,ROOT)]+[r/'docs/design/ai-research-team.md' for r in (MAIN,ROOT)]+[CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md',REG,STATE/'state.json',STATE/'events.jsonl',OLD_TOOLS/'watch.py',OLD_TOOLS/'safe_state.py',OLD_RUN/'expectations.json',OLD_RUN/'monitor-process.json',OLD_RUN/'monitor-observation.json']
 rows=[]
 for i,p in enumerate(paths):
  b=p.read_bytes();copy=OUT/f'before-{i}-{p.name}';copy.write_bytes(b);rows.append({'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'copy':str(copy)})
 refs=[]
 for base in (MAIN,ROOT):
  refs.extend([base/'.agents/research-team/common.md']+[p for p in (base/'.agents/research-team/roles').glob('*.md') if p.name!='supervisor.md'])
 refs.extend([MAIN/'scripts/dev/research-team.py',MAIN/'scripts/dev/research-scheduler.py',ROOT/'docs/design/ai-sigma-continuation-20261001.md',ROOT/'docs/design/ai-sigma-contract-steward-supervisor-role-review.md'])
 st=state();monitor=json.loads((OLD_RUN/'monitor-process.json').read_text())['process'];reg=json.loads(REG.read_text())
 assert reg['roles']['supervisor']['thread_id']==THREAD and st['binding']['thread_id']==THREAD
 assert st['phase']=='running' and alive(st['process']) and alive(monitor)
 write('before.json',{'at':now(),'operator':proc(os.getpid()),'sources':rows,'immutable_refs':[{'path':str(p),'sha256':sha(p)} for p in refs],'state':st,'monitor':monitor,'registry':reg,'writer_basis':'Explicit .61 delegation; .58 coordinator confirms root/coordinator do not write this scope; Beads .61 assigned steward. Dispatch/registry locks and unchanged input checks exclude cooperating concurrent mutation, not all possible host writers.'})
def stop():
 preserve();before=json.loads((OUT/'before.json').read_text())
 with team.dispatch_lock(MAIN):
  st=state();assert st['binding']==before['state']['binding'] and st['process']==before['state']['process'] and alive(st['process'])
  owned=st.get('owned')
  if owned:
   assert owned['thread_id']==THREAD and owned.get('turn_id') and owned.get('run_id'),'Unknown owned turn; fail closed'
   uuid.UUID(owned['turn_id']);uuid.UUID(owned['run_id'])
  # Only this scheduler's journal-owned turn can be interrupted by its existing stop path.
  receipt=wrapper('stop',bool(owned));st=state();assert st['phase']=='stopped' and st.get('process') is None and not st.get('owned') and not st.get('recovery_required')
  write('scheduler-stopped.json',{'at':now(),'pre_stop_owned':owned,'receipt':receipt,'state':st,'process_observed':proc(before['state']['process']['pid']),'dispatch_lock_used':True,'only_owned_scheduler_or_its_exact_turn':True})
 # Monitor sees the stopped phase and exits through its own existing stop-report path.
 until=time.monotonic()+100
 while alive(before['monitor']) and time.monotonic()<until:time.sleep(.1)
 assert not alive(before['monitor']),'Monitor still alive; do not edit bound inputs or start a duplicate'
 write('monitor-stopped.json',{'at':now(),'identity':before['monitor'],'observed':proc(before['monitor']['pid']),'end':json.loads((OLD_RUN/'monitor-ended.json').read_text()),'state':state()})

ROLE_REVIEW='''停滞と役割定義/分担の見直しの必要性を自律判断する。新知見が増えたか、失敗で仮説が絞れたか、同じ修復への集中、代替仮説担当の機能、担当集中/引継ぎ/独立検証負荷、目標に必須の条件と特定実装に由来する条件の混同を短い観点にする。固定失敗回数だけで判断せず、正常な報告待ちと学習が進む失敗を停滞と混同しない。必要と判断した時だけ、根拠・不確実性・役割/分担変更案・期待効果・検証方法をcoordinatorへ報告する。無用な定期文書、毎回複数案、全証拠再計算を義務にしない。必要性判断/提案と変更後の効果点検はsupervisor、採用・課題配分・所有者を通じた安全な適用はcoordinator。改定で予算/製品範囲/実験許可を増やさず、監督自身のconfig変更やworker直接起動は禁止。'''
def edit():
 before=json.loads((OUT/'before.json').read_text());assert state()['phase']=='stopped' and not state().get('owned') and not alive(before['monitor'])
 for row in before['sources'][:9]:assert sha(row['path'])==row['sha256'],'Concurrent source change; fail closed'
 roles=[r/'.agents/research-team/roles/supervisor.md' for r in (MAIN,ROOT)]
 for p in roles:
  s=p.read_text();assert 'ユーザーpauseや17:00終了' in s
  s=s.replace('ユーザーpauseや17:00終了','ユーザーpauseや現継続正本の終了/監督停止期限')
  s=s.replace('1turn180秒以内、新tool読取は120秒で止め最後60秒に報告。','1turn180秒以内、owned開始から90秒以降は新metadata commandの開始禁止、読取処理と自己childは120秒前に止め最後60秒に報告。')
  s=s.replace('\n観測専用:', '\n'+ROLE_REVIEW+'\n\n観測専用:');p.write_text(s)
 for base in (MAIN,ROOT):
  p=base/'docs/design/ai-research-team.md';s=p.read_text();s+='\n## 継続枠の監督運用\n\n継続契約で登録するsupervisorは観測専用の独立saved sessionで、同時LLM上限に含む。'+ROLE_REVIEW+' 現継続正本の期限/停止条件と個別契約の90/120/180秒guardを守り、初期五役や他roleの権限を変更しない。\n';p.write_text(s)
 prompt=CFG.parent/'prompt.md';s=prompt.read_text();s=s.replace('accepted、点検内容、全期間遵守、棋力達成は区別。','accepted、点検内容、全期間遵守、棋力達成は区別。\n\n'+ROLE_REVIEW+' 保存済みobserveと継承済み文脈の範囲で判断し、観点追加のために新metadata commandや再計算を増やさない。')
 prompt.write_text(s)
 p=ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md';p.write_text(p.read_text()+'\n役割補足（.58委譲/.61安全適用）: '+ROLE_REVIEW+' 既存90/120/180秒gateと全期限を維持する。\n')
 s=(OLD_TOOLS/'watch.py').read_text().replace("SIGMA-DEADLINE-UPDATE'","SIGMA-SUPERVISOR-ROLE-REVIEW'").replace("'recovery_issue':'quoridor-4lc.53'","'recovery_issue':'quoridor-4lc.61'")
 s=s.replace("ROOT/'tools/ai-sigma-scheduler-deadline-update',","ROOT/'tools/ai-sigma-scheduler-deadline-update',\n                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-DEADLINE-UPDATE',\n                 ROOT/'tools/ai-sigma-supervisor-role-review',\n                 ROOT/'docs/reports/ai-sigma-steward-supervisor-role-review.md',")
 compile(s,str(TOOLS/'watch.py'),'exec');(TOOLS/'watch.py').write_text(s);(TOOLS/'safe_state.py').write_bytes((OLD_TOOLS/'safe_state.py').read_bytes())
 write('edited.json',{'at':now(),'hashes':{str(p):sha(p) for p in roles+[MAIN/'docs/design/ai-research-team.md',ROOT/'docs/design/ai-research-team.md',prompt,ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md',TOOLS/'watch.py',TOOLS/'safe_state.py']},'config_and_contract_unchanged':all(sha(p)==next(r['sha256'] for r in before['sources'] if r['path']==str(p)) for p in [CFG,CFG.parent/'contract.json'])})
async def refresh():
 host=cmd(['codex','app-server','daemon','version'],10);assert host['status']=='running'
 before=json.loads((OUT/'before.json').read_text())
 with team.dispatch_lock(MAIN),REG.with_suffix('.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  registry=team.load_registry(REG,MAIN);assert registry==before['registry'],'Another registry writer changed entries; fail closed'
  assert state()['phase']=='stopped' and not state().get('owned')
  async with team.AppServer(host,timeout=20) as server:
   t=await server.read_thread(THREAD);write('rpc-thread-before.json',t)
   assert t['id']==THREAD and t['status']['type'] in ('idle','notLoaded'),'Supervisor is not idle; no interrupt of other turn'
   original=await server.request('thread/resume',{'threadId':THREAD,'excludeTurns':True});write('rpc-resume-before.json',original)
   instructions,digest=team.role_definition('supervisor',Path(registry['definitions_root']))
   instructions+=f'\n\nRuntime registry: {REG}\nRole: supervisor\nClient: bash {MAIN}/scripts/dev/research-team.sh\n'
   params={'threadId':THREAD,'excludeTurns':True,'developerInstructions':instructions};write('rpc-resume-request.json',params)
   response=await server.request('thread/resume',params);write('rpc-resume-applied.json',response)
   reread=await server.read_thread(THREAD);write('rpc-thread-after.json',reread)
   assert reread['id']==THREAD and reread['status']['type']=='idle'
   settings={k:response.get(k) for k in ('model','modelProvider','reasoningEffort','cwd','approvalPolicy','sandbox')}
   assert all(original.get(k)==response.get(k) for k in settings),'Settings changed; fail closed'
   entry=registry['roles']['supervisor'];assert entry['thread_id']==THREAD;entry['definition_sha256']=digest;team.save_registry(REG,registry)
   actual=team.load_registry(REG,MAIN);assert actual==registry
   assert team.role_entry(actual,'supervisor')['definition_sha256']==digest
   write('session-applied.json',{'at':now(),'thread_id':THREAD,'definition_sha256':digest,'explicit_developer_payload_sha256':hashlib.sha256(instructions.encode()).hexdigest(),'payload_bytes':len(instructions.encode()),'same_settings':settings,'rpc_response_success':True,'developerInstructions_response_field_present':'developerInstructions' in response,'thread_read_developerInstructions_present':'developerInstructions' in reread,'explicit_body_readback_unconfirmed':'developerInstructions' not in reread and 'developerInstructions' not in response,'registry_supervisor_entry':actual['roles']['supervisor'],'other_entries_unchanged':all(actual['roles'][r]==before['registry']['roles'][r] for r in before['registry']['roles'] if r!='supervisor'),'ack_turn_started':False})

def restart():
 before=json.loads((OUT/'before.json').read_text());assert state()['phase']=='stopped' and not state().get('owned') and not alive(before['monitor']) and not alive(before['state']['process'])
 validation=wrapper('validate');epoch=now();receipt=wrapper('start');st=state();assert st['phase']=='running' and alive(st['process'])
 run=OUT/('live-'+str(uuid.uuid4()));run.mkdir()
 inputs=[CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',TOOLS/'watch.py',TOOLS/'safe_state.py',MAIN/'.agents/research-team/common.md',MAIN/'.agents/research-team/roles/supervisor.md',ROOT/'.agents/research-team/roles/supervisor.md']
 expected={'process':st['process'],'binding':st['binding'],'operation_epoch_utc':epoch,'input_hashes':{str(p):sha(p) for p in inputs}}
 (run/'expectations.json').write_text(json.dumps(expected,indent=2)+'\n')
 with (run/'console.log').open('w') as f:
  p=subprocess.Popen([sys.executable,'-B',str(TOOLS/'watch.py'),'--run-dir',str(run),'--expectations',str(run/'expectations.json')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=f,stderr=f,start_new_session=True)
 identity=proc(p.pid);until=time.monotonic()+15
 while time.monotonic()<until:
  if (run/'monitor-observation.json').exists():break
  if p.poll() is not None:raise RuntimeError('New monitor exited; no duplicate restart')
  time.sleep(.1)
 else:raise RuntimeError('New monitor unconfirmed')
 write('live-applied.json',{'at':now(),'operator':proc(os.getpid()),'validation':validation,'start_receipt':receipt,'state':state(),'monitor':identity,'run':str(run),'monitor_process':json.loads((run/'monitor-process.json').read_text()),'monitor_observation':json.loads((run/'monitor-observation.json').read_text()),'expectations':expected,'new_epoch':epoch,'full_period_success_claimed':False,'natural_next_body_and_effect_check_pending':True})

def observe():
 before=json.loads((OUT/'before.json').read_text());live=json.loads((OUT/'live-applied.json').read_text());session=json.loads((OUT/'session-applied.json').read_text());run=Path(live['run']);st=state()
 assert st['binding']==before['state']['binding'] and st['process']==live['state']['process'] and st['phase']=='running' and alive(st['process']) and alive(live['monitor'])
 assert not alive(before['monitor']) and not alive(before['state']['process'])
 registry=team.load_registry(REG,MAIN);entry=team.role_entry(registry,'supervisor')
 assert entry==session['registry_supervisor_entry'] and entry['thread_id']==THREAD
 assert all(registry['roles'][r]==before['registry']['roles'][r] for r in before['registry']['roles'] if r!='supervisor')
 inputs=live['expectations']['input_hashes'];assert all(sha(p)==h for p,h in inputs.items())
 unchanged=[{**r,'after_sha256':sha(r['path']),'unchanged':sha(r['path'])==r['sha256']} for r in before['immutable_refs']];assert all(r['unchanged'] for r in unchanged)
 for p in [CFG,CFG.parent/'contract.json',OLD_TOOLS/'watch.py',OLD_TOOLS/'safe_state.py']:
  row=next(r for r in before['sources'] if r['path']==str(p));assert sha(p)==row['sha256']
 assert (MAIN/'.agents/research-team/roles/supervisor.md').read_bytes()==(ROOT/'.agents/research-team/roles/supervisor.md').read_bytes()
 checks=[]
 for p in OUT.glob('short-*-end.json'):
  ident=json.loads(p.read_text())['process'];checks.append({'identity':ident,'current':proc(ident['pid']),'same_identity_alive':alive(ident)})
 for line in (OUT/'commands.jsonl').read_text().splitlines():
  ident=json.loads(line)['identity']
  if ident:checks.append({'identity':ident,'current':proc(ident['pid']),'same_identity_alive':alive(ident)})
 assert not any(c['same_identity_alive'] for c in checks)
 seen=set();allocated=0;logical=0
 for root in [OUT,TOOLS,ROOT/'docs/reports/ai-sigma-steward-supervisor-role-review.md']:
  stack=[root]
  while stack:
   p=stack.pop()
   try:s=p.lstat()
   except FileNotFoundError:continue
   key=(s.st_dev,s.st_ino)
   if key in seen:continue
   seen.add(key);allocated+=s.st_blocks*512;logical+=s.st_size
   if p.is_dir() and not p.is_symlink():stack.extend(p.iterdir())
 assert allocated<14*1024**2
 obs=json.loads((run/'monitor-observation.json').read_text());assert obs['own_scope_allocated_peak_bytes']<112*1024**2
 edited=json.loads((OUT/'edited.json').read_text());after_edited={p:sha(p) for p in edited['hashes']}
 assert after_edited==edited['hashes']
 write('after.json',{'at':now(),'state':st,'scheduler_observed':proc(st['process']['pid']),'monitor_observed':proc(live['monitor']['pid']),'expected_input_hashes':inputs,'edited_after_hashes':after_edited,'immutable_refs':unchanged,'old_watch_config_contract_unchanged':True,'registry_sha256':sha(REG),'registry_supervisor_entry':entry,'other_registry_entries_unchanged':True,'monitor_observation':obs,'new_scope_unique_allocated_bytes':allocated,'new_scope_logical_bytes':logical,'cpu_affinity':list(os.sched_getaffinity(0)),'rlimit_as':resource.getrlimit(resource.RLIMIT_AS),'increment_accounting_limit':'owned new artifacts/tools/report only; edited-document growth not exact global delta','settings_before_after':session['same_settings'],'explicit_developer_body_readback_unconfirmed':session['explicit_body_readback_unconfirmed'],'full_natural_turn_and_effect_check_pending':True,'cumulative_12GiB_not_reset':True,'extra_reservation':0,'original_short_read_parent_pid_missing':True})
 write('short-jobs-stopped.json',{'at':now(),'known_short_checks':checks,'no_known_short_identity_alive':True,'recorder_process':proc(os.getpid()),'recorder_exit_confirmed_by_caller':'synchronous command exit_code after return','original_short_read_parent_pid_missing':True,'long_scheduler':st['process'],'long_monitor':live['monitor'],'long_processes_continue':True,'stop_scheduler_utc':'2026-10-02T00:55:00Z','collect_monitor_utc':'2026-10-02T00:58:00Z','final_evidence_utc':'2026-10-02T01:00:00Z','owner':'01a0f31d-99ee-7d63-b162-bc1a59c457c6','natural_prompt_body_and_judgement_effect_check_owner':'same steward via next natural-turn evidence; supervisor reports own judgement/effect, coordinator adopts/applies','all_team_pid_zero_claimed':False})

if __name__=='__main__':
 action=sys.argv[1]
 try:
  if action=='refresh':asyncio.run(refresh())
  else:globals()[action]()
 except Exception as e:
  write('failure-'+action+'-'+str(uuid.uuid4())+'.json',{'at':now(),'error':str(e),'operator':proc(os.getpid()),'no_blind_retry':True});raise
 finally:
  r=resource.getrusage(resource.RUSAGE_SELF);write('short-'+action+'-'+str(uuid.uuid4())+'-end.json',{'at':now(),'process':proc(os.getpid()),'maxrss_kib':r.ru_maxrss,'exit_after_record':True})
