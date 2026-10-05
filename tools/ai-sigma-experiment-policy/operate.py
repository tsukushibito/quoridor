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
OUT=ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-EXPERIMENT-POLICY-85'
TOOLS=ROOT/'tools/ai-sigma-experiment-policy'
CFG=ROOT/'.artifacts/ai-sigma/continuation-20261001/scheduler/scheduler.json'
STATE=MAIN/'.artifacts/research-team/scheduler-sigma-continuation-20261001'
REG=MAIN/'.artifacts/research-team/registry.json'
OLD_TOOLS=ROOT/'tools/ai-sigma-critical-roles-v2'
OLD_RUN=Path('/workspaces/quoridor/.worktree/ai-sigma/.artifacts/ai-sigma/continuation-20261001/SIGMA-CRITICAL-ROLES-V2/live-79bb1e40-571c-4e28-a433-b1c2e10859a5')
THREAD='01a0f6b5-b1bd-7752-b0bb-74a336e459a4'
OUT.mkdir(parents=True,exist_ok=True);(OUT/'tmp').mkdir(exist_ok=True)
os.sched_setaffinity(0,{0});os.environ.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'))
spec=importlib.util.spec_from_file_location('research_team',MAIN/'scripts/dev/research-team.py')
team=importlib.util.module_from_spec(spec);spec.loader.exec_module(team)
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,v):
 p=OUT/n;temporary=p.with_suffix(p.suffix+'.tmp');temporary.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');os.replace(temporary,p)
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


ROLES=['coordinator','hypothesis','experiment','critic','steward','supervisor']
POLICY=MAIN/'docs/development/ai-research-experiments.md'
CUTOFF=dt.datetime(2026,10,1,23,36,45,tzinfo=dt.timezone.utc)
async def prepare_stop():
 assert not (OUT/'before.json').exists()
 paths=[b/p for b in (MAIN,ROOT) for p in ['.agents/research-team/common.md','docs/design/ai-research-team.md','.agents/research-team/templates/experiment-contract.md','.agents/research-team/templates/handoff.md']]+[POLICY,ROOT/'docs/design/ai-sigma-continuation-20261001.md',REG,CFG,CFG.parent/'contract.json',CFG.parent/'prompt.md',ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md']
 sources=[]
 for i,p in enumerate(paths):
  data=p.read_bytes();copy=OUT/f'before-{i}-{p.name}';copy.write_bytes(data);sources.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'copy':str(copy)})
 registry=team.load_registry(REG,MAIN);st=state();monitor=json.loads((OLD_RUN/'monitor-process.json').read_text())['process']
 rolehash={str(b/f'.agents/research-team/roles/{r}.md'):sha(b/f'.agents/research-team/roles/{r}.md') for b in (MAIN,ROOT) for r in ROLES}
 write('before.json',{'at':now(),'operator':proc(os.getpid()),'sources':sources,'role_hashes':rolehash,'registry':registry,'state':st,'monitor':monitor,'policy_sha256':sha(POLICY),'no_full_history_or_source_copy':True})
 host=cmd(['codex','app-server','daemon','version'],10)
 with team.dispatch_lock(MAIN):
  async with team.AppServer(host,timeout=15) as server:
   t=await server.read_thread(THREAD);assert t['status']['type'] in ('idle','notLoaded') and not st.get('owned')
   assert state()['process']==st['process'] and state().get('owned') is None and alive(st['process']) and alive(monitor)
   receipt=wrapper('stop');assert state()['phase']=='stopped' and not state().get('owned')
   until=time.monotonic()+100
   while alive(monitor) and time.monotonic()<until:time.sleep(.1)
   assert not alive(monitor),'Old monitor not stopped; no source edits'
   write('operation-stopped.json',{'at':now(),'state':state(),'receipt':receipt,'old_monitor':monitor,'monitor_observed':proc(monitor['pid']),'dispatch_lock_held_through_monitor_exit':True,'new_role_turns_started':0})

def edit():
 before=json.loads((OUT/'before.json').read_text());assert state()['phase']=='stopped' and not alive(before['monitor'])
 assert all(sha(r['path'])==r['sha256'] for r in before['sources'])
 common=(MAIN/'.agents/research-team/common.md').read_text()
 old='- 基準コード、差分、seed、入力とモデルのハッシュ、依存lockfile、実行コマンド、測定環境を記録する。成功候補は独立した再実行と批判を通す。nativeの速度をWasmの速度と同一視しない。'
 new='- 実行記録はissue/run ID、Git版（未コミットなら基準と必要な差分）、設定・入力参照、再現コマンド、開始/終了、成否・必要な結果/ログで管理する。seed・モデル・依存版・時間/メモリは問いの再現と判断に必要なものを記録する。全ソース/依存/過去成果の複製や全履歴hashを毎回要求しない。主張に必要な独立検証を行い、nativeの速度をWasmと同一視しない。'
 assert old in common;common=common.replace(old,new)
 addition='- [AI研究の実行・再実行・記録](../../docs/development/ai-research-experiments.md)を適用する。課題/コード版/runを分け、許可範囲と総予算内の修正版デバッグ・再現・性能測定は反復可能。通常確認へ一律一回/一窓/NN再試行ゼロを課さない。正式棋力評価の条件/集計/停止/エラー扱いは結果前に固定し、良い成績だけの選別・敗北の無条件置換を禁止する。研究コードのローカルGit管理を許可し、製品main統合/push/公開は許可しない。進行中の個別許可差分と残予算はcoordinatorが明示し、終了窓の再開・旧結果の上書き・資源/期限/権限拡張はしない。\n'
 common+='\n'+addition
 with team.dispatch_lock(MAIN),REG.with_suffix('.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  registry=team.load_registry(REG,MAIN);assert registry==before['registry']
  for base in (MAIN,ROOT):(base/'.agents/research-team/common.md').write_text(common)
  for role in ROLES:
   _,digest=team.role_definition(role,MAIN);registry['roles'][role]['definition_sha256']=digest
  team.save_registry(REG,registry)
  write('source-digest-transition.json',{'at':now(),'registry_sha256':sha(REG),'roles':registry['roles'],'permanent_application_pending_until_idle':True,'communication_digests_match_source':True,'transient_multi_file_atomicity_not_claimed':True})
 for name in ['docs/development/ai-research-experiments.md','.agents/research-team/templates/experiment-contract.md','.agents/research-team/templates/handoff.md']:
  p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((MAIN/name).read_bytes())
 for base in (MAIN,ROOT):
  p=base/'docs/design/ai-research-team.md';p.write_text(p.read_text()+'\n研究の再実行・記録は[AI研究の実行・再実行・記録](../development/ai-research-experiments.md)を正本とする。許可した総予算でデバッグ/再現/性能測定を反復し、正式評価の成績選別はしない。Git版/run/必要なログ結果で管理し、全コピー/全履歴hashを義務にしない。研究ローカルGit管理は可、製品main統合/push/公開と期限/予算拡張は不可。\n')
 parent=ROOT/'docs/design/ai-sigma-continuation-20261001.md';text=parent.read_text();text=text.replace('主checkout製品/UI/描画/M2/commit/push/公開は対象外。研究worktreecodex/ai-sigmaで新copyに実装し旧入力をhashで固定。','主checkout製品/UI/描画/M2への統合、push、公開は対象外。研究worktreecodex/ai-sigmaでは研究コードのローカルGit管理を許可する。コード版/runと必要な差分・入力参照を記録し、新copyや全入力hashを一律必須にしない。')
 text+='\n運用記録・再実行補足（ユーザー明示.85/.85.1）: docs/development/ai-research-experiments.mdを現作業へ適用する。旧新copy必須/研究commit禁止/一律一回制限の矛盾を置換する。期限・資源・正式比較・旧結果は不変、進行個別許可差分/残予算はcoordinatorが担当へ明示する。既終了窓の遡及再開や過去結果置換はしない。\n';parent.write_text(text)
 supplement='ユーザー明示.85の再実行・記録規約を継承。許可範囲/総予算内の修正版デバッグ・再現/性能測定は反復可、一律一回/一窓/NN再試行ゼロや全コピー/全履歴hashは標準義務でない。正式成績選別/旧結果置換/終了窓再開は不可。Git版/run/必要な結果ログで管理、研究local commit可、製品main統合/push/公開不可。進行許可差分はcoordinator判断。監督は新規NNを実行せず、既90/120/180と周期/期限を維持する。'
 for p in [CFG.parent/'prompt.md',ROOT/'docs/design/ai-sigma-contract-supervisor-continuation.md']:p.write_text(p.read_text()+'\n'+supplement+'\n')
 source=(OLD_TOOLS/'watch.py').read_text().replace("SIGMA-CRITICAL-ROLES-V2'","SIGMA-EXPERIMENT-POLICY-85'").replace("'recovery_issue':'quoridor-4lc.82.1'","'recovery_issue':'quoridor-4lc.85.1'")
 source=source.replace("ROOT/'tools/ai-sigma-critical-roles-v2',","ROOT/'tools/ai-sigma-critical-roles-v2',\n                 ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-CRITICAL-ROLES-V2',\n                 ROOT/'tools/ai-sigma-experiment-policy',\n                 ROOT/'docs/reports/ai-sigma-steward-experiment-policy.md',")
 compile(source,str(TOOLS/'watch.py'),'exec');(TOOLS/'watch.py').write_text(source);(TOOLS/'safe_state.py').write_bytes((OLD_TOOLS/'safe_state.py').read_bytes())

async def refresh_pass(background=False):
 host=cmd(['codex','app-server','daemon','version'],10);registry=team.load_registry(REG,MAIN)
 path=OUT/'sessions-applied.json';results=json.loads(path.read_text())['roles'] if path.exists() else {}
 async with team.AppServer(host,timeout=15) as server:
  for role in ROLES:
   if dt.datetime.now(dt.timezone.utc)>=CUTOFF:break
   if results.get(role,{}).get('permanent_applied'):continue
   thread=registry['roles'][role]['thread_id']
   with team.dispatch_lock(MAIN),REG.with_suffix('.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    t=await server.read_thread(thread);status=t['status']['type'];text,digest=team.role_definition(role,MAIN);text+=f'\n\nRuntime registry: {REG}\nRole: {role}\nClient: bash {MAIN}/scripts/dev/research-team.sh\n'
    if status in ('idle','notLoaded'):
     params={'threadId':thread,'excludeTurns':True,'developerInstructions':text};write('rpc-'+role+'-request.json',params)
     original=await server.request('thread/resume',{'threadId':thread,'excludeTurns':True});write('rpc-'+role+'-before.json',original)
     applied=await server.request('thread/resume',params);write('rpc-'+role+'-applied.json',applied)
     settings={k:applied.get(k) for k in ('model','modelProvider','reasoningEffort','cwd','approvalPolicy','sandbox')};assert all(original.get(k)==applied.get(k) for k in settings)
     reread=await server.read_thread(thread);write('rpc-'+role+'-reread.json',reread)
     results[role]={'at':now(),'thread_id':thread,'permanent_applied':True,'definition_sha256':digest,'payload_sha256':hashlib.sha256(text.encode()).hexdigest(),'settings':settings,'body_readback_unavailable':True,'active_interrupt_or_resume':False}
    elif status=='active' and not results.get(role,{}).get('supplement_accepted'):
     turns=await server.turns(thread);active=next((x for x in turns if x['status']=='inProgress'),None);assert active,'Active turn unknown; no blind steer'
     body='ユーザー明示.85/.85.1規約補足。研究への新実行依頼ではない。重複writer/新role起動0。進行中の許可差分/残予算はcoordinator判断、終了窓再開/旧結果置換0。全文:\n'+POLICY.read_text()
     params={'threadId':thread,'expectedTurnId':active['id'],'input':[{'type':'text','text':body,'text_elements':[]}]};write('steer-'+role+'-request.json',params)
     response=await server.request('turn/steer',params);write('steer-'+role+'-response.json',response)
     results[role]={'at':now(),'thread_id':thread,'turn_id':active['id'],'supplement_accepted':True,'permanent_applied':False,'definition_sha256':digest,'supplement_sha256':hashlib.sha256(body.encode()).hexdigest(),'active_interrupt_or_resume':False}
    elif role not in results:results[role]={'thread_id':thread,'permanent_applied':False,'reason':'Unknown/non-idle status; fail closed'}
   write('sessions-applied.json',{'at':now(),'roles':results,'permanent_pending':[r for r in ROLES if not results.get(r,{}).get('permanent_applied')],'forced_interrupts':0,'new_role_turns':0})
 return results

async def finish_idle():
 write('idle-refresher-process.json',{'at':now(),'process':proc(os.getpid()),'admission_cutoff':CUTOFF.isoformat(),'no_new_turns':True})
 try:
  while dt.datetime.now(dt.timezone.utc)<CUTOFF:
   results=await refresh_pass(True)
   if all(results.get(r,{}).get('permanent_applied') for r in ROLES):break
   await asyncio.sleep(5)
 finally:
  write('idle-refresher-ended.json',{'at':now(),'process':proc(os.getpid()),'all_permanent':all(json.loads((OUT/'sessions-applied.json').read_text())['roles'].get(r,{}).get('permanent_applied') for r in ROLES),'stop_on_cutoff_no_extension':True})
  if dt.datetime.now(dt.timezone.utc)<CUTOFF and (OUT/'handoff-ready.json').exists():await deliver_handoff()

async def deliver_handoff():
 for issue in ('quoridor-4lc','quoridor-4lc.85','quoridor-4lc.85.1'):team.require_issue(issue,MAIN)
 host=cmd(['codex','app-server','daemon','version'],10);registry=team.load_registry(REG,MAIN)
 async with team.AppServer(host,timeout=15) as server:
  for name,target in [('root','01a0f2e9-357d-7ef3-a2fe-b16f80accda5'),('coordinator',registry['roles']['coordinator']['thread_id'])]:
   if dt.datetime.now(dt.timezone.utc)>=CUTOFF:break
   thread=await server.read_thread(target);ids=set(x['thread_id'] for x in registry['roles'].values())|{'01a0f2e9-357d-7ef3-a2fe-b16f80accda5'}
   active=0
   for ident in ids:
    value=await server.read_thread(ident);active+=value['status']['type']=='active'
   if thread['status']['type']!='active' and active>=3:
    write(name+'-handoff-undelivered.json',{'at':now(),'reason':'global3 no spare slot; no blind send','active_observed':active});continue
   status=json.loads((OUT/'sessions-applied.json').read_text())
   body='quoridor-4lc.85.1 適用報告。単独steward owner、重複writer/別適用turnを起動しないでください。.82.1受入れ理由を残して本人close済。\n'+(ROOT/'docs/reports/ai-sigma-steward-experiment-policy.md').read_text()+'\n最新恒久適用状態 '+json.dumps(status,ensure_ascii=False)+'\n終了証拠 '+str(OUT/'idle-refresher-ended.json')+'。root所有.85の受入れへ提出、目標/他者close0。'
   with team.dispatch_lock(MAIN):
    receipt=await server.deliver(target,body);write(name+'-handoff-delivery.json',{'at':now(),'receipt':receipt,'active_observed':active,'notification_only_no_new_research_authorization':True})
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
  if action in ('prepare_stop','refresh_pass','finish_idle'):asyncio.run(globals()[action]())
  else:globals()[action]()
 except Exception as e:write('failure-'+action+'-'+str(uuid.uuid4())+'.json',{'at':now(),'error':str(e),'operator':proc(os.getpid()),'blind_retry':False});raise
 finally:write('short-'+action+'-'+str(uuid.uuid4())+'-end.json',{'at':now(),'process':proc(os.getpid()),'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'exit_after_record':True})
