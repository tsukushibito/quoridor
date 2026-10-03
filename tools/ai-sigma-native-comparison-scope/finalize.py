import os,subprocess,json,hashlib,datetime,time
from pathlib import Path
os.sched_setaffinity(0,{0})
ROOT=Path(__file__).resolve().parents[2];os.chdir(ROOT)
D=ROOT/'research-data/ai-sigma/166-native-comparison-scope';T=ROOT/'tools/ai-sigma-native-comparison-scope'
R=ROOT/'docs/reports/ai-sigma-critic-native-comparison-scope.md'
LOG=[];env=os.environ.copy();env['BEADS_ACTOR']='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'
def call(args,extra=None):
 e=env.copy();e.update(extra or {});start=time.monotonic();p=subprocess.run(args,env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
 rec={'command':args,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'exit':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode()};LOG.append(rec)
 (D/'finalize-attempts.json').write_text(json.dumps(LOG,ensure_ascii=False,indent=2)+'\n')
 if p.returncode:raise RuntimeError(rec)
 return p.stdout.decode()
call(['bash','scripts/dev/beads.sh','ready','--json'])
goal=json.loads(call(['bash','scripts/dev/beads.sh','show','quoridor-4lc','--json']))
selfissue=json.loads(call(['bash','scripts/dev/beads.sh','show','quoridor-4lc.166','--json']))
def first(x):return x[0] if isinstance(x,list) else x
for obj in [first(goal),first(selfissue)]:
 assert obj.get('status')=='in_progress' and 'paused-by-user' not in obj.get('labels',[]),'PAUSE_OR_STATUS'
assert first(selfissue).get('assignee')=='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b','OWNER_MISMATCH'
(D/'source-stop.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':'quoridor-4lc.166','science_child_started':False,'static_run_exit':0,'source_edit_stop':True,'other_owner_signal':False,'formal_ready':False,'scope':'166 static source only; management persistence remains'},indent=2)+'\n')
(D/'active-adoption.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'coordinator_message':'adopts timer asymmetry and epoch concerns; event-driven quiescence proposal accepted; wrapper changes to be fixed before scientific games','adoption_is_science_success':False,'source_snapshot':'static-result.json','source_limited_reflection_supported':True,'runtime_validation_pending_owner165':True,'kernel_CPU_equal':None,'proposal_count':1},indent=2)+'\n')
index=str(T/'private.index');ge={'GIT_INDEX_FILE':index}
call(['git','read-tree','HEAD'],ge)
files=sorted([p for p in T.rglob('*') if p.is_file() and p.name not in ['private.index','private.index.lock']]+[p for p in D.rglob('*') if p.is_file()]+[R])
relative=[str(p.relative_to(ROOT)) for p in files]
call(['git','add','--',*relative],ge)
call(['git','commit','-m','research: record critic native comparison scope and clock limits (166)'],ge)
commit=call(['git','rev-parse','HEAD'],ge).strip()
rest=[]
for p in files:
 # finalize attempts is appended by management, so compare committed version to manifest at commit only.
 if p.name=='finalize-attempts.json':continue
 q=subprocess.run(['git','show',commit+':'+str(p.relative_to(ROOT))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
 assert q.returncode==0 and q.stdout==p.read_bytes(),'RESTORE_MISMATCH '+str(p)
 rest.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(q.stdout).hexdigest(),'stream_bytes_equal':True})
(D/'git-restore.json').write_text(json.dumps({'data_commit':commit,'files':rest,'restored_count':len(rest),'method':'Git blob stream compared to original bytes; no duplicate source archives'},indent=2)+'\n')
call(['bash','scripts/dev/beads.sh','update','quoridor-4lc.166','--append-notes','166 source/static child stopped. Native-hosted fixed Sigma-Web JS + Rust native same-model CPU route conditionally supported; one event-driven quiescence proposal; native timer/epoch source reflection finite, runtime/provider/cleanup/CPU/NI pending. Report docs/reports/ai-sigma-critic-native-comparison-scope.md; data Git '+commit+'. No new NN/Chrome/build/game. Coordinator acceptance/close pending.'])
call(['bash','scripts/dev/beads.sh','backup','sync'])
(D/'handoff.json').write_text(json.dumps({'issue':'quoridor-4lc.166','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_commit':commit,'source_stopped':True,'scientific_child_count':0,'static_run_exit':0,'Git_stream_restore_supported':True,'Beads_notes_exit':0,'backup_sync_exit':0,'coordinator_acceptance_pending':True,'formal_ready':False,'NNUE_goal_complete':False},indent=2)+'\n')
# The persistence transcript is saved up to this point. Git helper commands below are printed in tool output.
subprocess.run(['git','add','--',str((D/'git-restore.json').relative_to(ROOT)),str((D/'handoff.json').relative_to(ROOT)),str((D/'finalize-attempts.json').relative_to(ROOT))],env={**env,**ge},check=True,timeout=60)
subprocess.run(['git','commit','-m','research: save 166 stream restore and backup handoff'],env={**env,**ge},check=True,timeout=60)
print(json.dumps({'data_commit':commit,'handoff_commit':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'stream_restored_files':len(rest),'backup_exit':0,'managed_elapsed_seconds':sum(r['elapsed_seconds'] for r in LOG)}))
