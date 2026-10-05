"""Post-stop evidence, archive/Git restore, early coordinator report; no scientific replay."""
import json,os,sys,hashlib,subprocess,datetime,shutil,time,resource
from pathlib import Path
root=Path(__file__).resolve().parents[2];os.chdir(root);os.sched_setaffinity(0,{0});start=time.monotonic();out=root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP';data=root/'research-data/ai-sigma/frame10-baseline-gap';run=sys.argv[1];directory=out/'runs'/run
p=json.loads((out/'runs'/(run+'.process.json')).read_text());assert not p['remaining'] and not p['unknown_adopted']
refs={}
for x in [*p['tracked'],{'pid':p['runner_pid'],'start_ticks':p['runner_starttick']}]:refs[(x['pid'],x['start_ticks'])]={'pid':x['pid'],'start_ticks':x['start_ticks']}
same=[]
for x in refs.values():
 try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 if int(s[19])==x['start_ticks']:same.append(x)
assert not same,'CURRENT_SAME_IDENTITY'
def get(name):
 path=directory/(name+'.json');return json.loads(path.read_text()) if path.exists() else None
summary=get('summary');model=get('finally-model-drop');timer=get('main-timers-stop');monitor=get('pause-monitor-stop');observer=get('outer-main-observer-stop');inner=get('outer-controlled-stop')
before=json.loads((out/'runs'/(run+'.inputs.json')).read_text())['source'];after={k:hashlib.sha256(Path(k).read_bytes()).hexdigest() for k in before};science_names=['adapters.cjs','input.js','main.js','diagnose.cjs','browser.cjs','runner.py','admission.py'];science_match=all(before[k]==after[k] for k in before if Path(k).name in science_names)
stop={'issue':'quoridor-4lc.149','run':run,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'scientific_source_before_after_exact':science_match,'source_before':before,'source_after':after,'postprocessing_helper_changes_separate':[k for k in before if before[k]!=after[k]],'Model2_drop':model,'main_timer_message':timer,'monitor_stop':None if monitor is None else {k:monitor.get(k) for k in ['pending_children','all_owned_read_callbacks_waited','active_monitor_timer','state','failure']},'outer_main_observer':observer,'innercontrolled':inner,'outersole_root_ownedwait':{'kernel_boundary':p['kernel_boundary'],'remaining':p['remaining'],'unknown_adopted':p['unknown_adopted'],'exit':p['exit'],'stop_reason':p['stop_reason']},'current_identities':list(refs.values()),'current_same_identity':same,'current_absence_not_natural_fullperiod_allhost':True,'scientific_runtime_stopped_before_body':True,'new_process_only_after_next_admission':True}
assert science_match,'SCIENTIFIC_SOURCE_DRIFT'
if p['exit']==0:
 assert model and not model['handles'] and not model['activeNN'],'MODEL_ZERO'
 assert timer and not timer['main_timers'] and not timer['pending_messages'],'TIMER_MESSAGE_ZERO'
 assert monitor and not monitor['pending_children'] and not monitor['active_monitor_timer'],'MONITOR_ZERO'
 assert observer and not observer['active_timer'] and not observer['inflight_callback'],'OBSERVER_ZERO'
 assert inner and inner['remaining_pids']==0,'INNER_NOT_ZERO'
stop_path=data/(run+'.stop.json');stop_path.write_text(json.dumps(stop,indent=2)+'\n')
sha=hashlib.sha256(stop_path.read_bytes()).hexdigest();games=(summary or {}).get('games',[])
body=out/(run+'-stop-report.md');body.write_text(f"goal quoridor-4lc / 本人149 {run} heavy停止。終了 {p['end']}、job exit {p['exit']}、ownedwait remaining/unknown空・現在sameidentity0、science source前後一致。Model2/search/main timer-message/監視callbackは停止正本に分離（欠測は欠測）。stop {stop_path} SHA{sha}。全attempt保存、group正常終了では実開始{(summary or {}).get('games_started')}、game結果 {json.dumps([{'id':g['id'],'status':g['status'],'winner':g['winner'],'reason':g['reason'],'new_public':len(g['actions'])} for g in games],ensure_ascii=False)}。途中成績を停止/入力/順/置換へ使用0。原group1の4未知を全64分母に保持、以後登録未開始条件だけ続行、期限/予算/政策維持。現在不在を自然/全期間保証にしません。\n")
env={**os.environ,'UV_NO_SYNC':'1','UV_OFFLINE':'1','PYTHONDONTWRITEBYTECODE':'1'}
# Heavy stop bulletin precedes prose/archive work.
with (out/(run+'-stop-receipt.json')).open('w') as f:subprocess.run(['bash','/workspaces/quoridor/scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str(body)],env=env,stdout=f,check=True,timeout=45)
subprocess.run([sys.executable,str(root/'tools/ai-sigma-baseline-gap-frame10/archive.py'),run],env=env,check=True,timeout=60)
subprocess.run([sys.executable,str(root/'tools/ai-sigma-baseline-gap-frame10/aggregate.py')],env=env,check=True,timeout=60)
idx=out/'private-index';git_env={**env,'GIT_INDEX_FILE':str(idx)}
# Only own data and postprocessing helper sources, default index never touched.
for attempt in range(2):
 subprocess.run(['git','read-tree','HEAD'],env=git_env,check=True,timeout=30)
 subprocess.run(['git','add','--','research-data/ai-sigma/frame10-baseline-gap','tools/ai-sigma-baseline-gap-frame10'],env=git_env,check=True,timeout=30)
 commit=subprocess.run(['git','commit','-m',f'research(149): preserve {run} stopped attempts and full64 bounds'],env=git_env,timeout=45)
 if commit.returncode==0:break
else:raise RuntimeError('PRIVATE_GIT_COMMIT_FAILED')
if idx.exists():idx.unlink()
archive=data/(run+'.tar.gz');m=json.loads((data/(run+'.manifest.json')).read_text());git_bytes=subprocess.check_output(['git','show','HEAD:'+str(archive.relative_to(root))],timeout=30);assert hashlib.sha256(git_bytes).hexdigest()==m['archive_SHA256'],'ARCHIVE_GIT_RESTORE'
# Own stopped raw now safely reconstructible via Git+manifest; no active self/other references.
for x in [out/'runs'/(run+'.monitor.jsonl'),out/'runs'/(run+'.owned-ledger.jsonl')]:
 if x.exists():x.unlink()
shutil.rmtree(directory)
record={'run':run,'helper_pid':os.getpid(),'helper_starttick':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),'wall_seconds':time.monotonic()-start,'current_RSS':int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[21])*4096,'past_ru_maxrss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'child_callbacks_waited':True,'archive_Git_restored':True,'Git':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}
(out/(run+'-finish-record.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));assert record['current_RSS']<939524096 and record['wall_seconds']<60,'STATIC_BUDGET'
