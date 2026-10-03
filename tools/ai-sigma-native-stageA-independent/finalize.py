import os,pathlib,json,subprocess,time,datetime,hashlib
os.sched_setaffinity(0,{0});R=pathlib.Path(__file__).resolve().parents[2];os.chdir(R);D=R/'research-data/ai-sigma/168-native-stageA-independent';T=R/'tools/ai-sigma-native-stageA-independent';REPORT=R/'docs/reports/ai-sigma-critic-native-stageA-independent.md';env={**os.environ,'BEADS_ACTOR':'codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'};logs=[]
def call(a,extra=None):
 start=time.monotonic();p=subprocess.run(a,env={**env,**(extra or {})},capture_output=True,timeout=60);rec={'command':a,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-start,'exit':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode()};logs.append(rec);(D/'finalize-attempts.json').write_text(json.dumps(logs,indent=2)+'\n');assert p.returncode==0,rec;return p.stdout
ready=json.loads(call(['bash','scripts/dev/beads.sh','ready','--json']))
compact=[]
for id in ['quoridor-4lc','quoridor-4lc.168']:
 x=json.loads(call(['bash','scripts/dev/beads.sh','show',id,'--json']))[0];assert x['status']=='in_progress' and 'paused-by-user' not in x.get('labels',[]);compact.append({k:x.get(k) for k in ['id','status','assignee','labels']})
assert compact[-1]['assignee']==env['BEADS_ACTOR']
(D/'final-admission.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issues':compact,'pause':False,'owner_confirmed':True},indent=2)+'\n')
children=[]
for p in D.glob('*.process.json'):
 x=json.loads(p.read_text());assert x['wait_completed'] and x['exit']==0
 try:s=pathlib.Path('/proc')/str(x['PID'])/'stat';present=s.exists() and s.read_text().rsplit(')',1)[1].split()[19]==x['start_ticks']
 except FileNotFoundError:present=False
 assert not present;children.append({'run':x['run'],'PID':x['PID'],'start_ticks':x['start_ticks'],'exact_identity_current_absent':True,'exit':x['exit']})
(D/'source-stop.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'issue':'quoridor-4lc.168','scientific_rerun':0,'source_edit_stopped':True,'static_children':children,'native_replay':0,'NN':0,'other_owner_signalled':False,'formal_ready':False,'management_persistence_only_remains':True},indent=2)+'\n')
ge={'GIT_INDEX_FILE':str(T/'private.index')};call(['git','read-tree','HEAD'],ge)
files=sorted([p for base in [D,T] for p in base.rglob('*') if p.is_file() and p.name not in ['private.index','private.index.lock']]+[REPORT]);paths=[str(p.relative_to(R)) for p in files]
call(['git','add','--',*paths],ge);call(['git','commit','-m','research: independently check saved native StageA mechanism (168)'],ge);commit=call(['git','rev-parse','HEAD'],ge).decode().strip();restore=[]
for p in files:
 if p.name=='finalize-attempts.json':continue
 b=subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R))],timeout=60);assert b==p.read_bytes();restore.append({'path':str(p.relative_to(R)),'SHA256':hashlib.sha256(b).hexdigest(),'Git_stream_equal':True})
(D/'git-restore.json').write_text(json.dumps({'data_commit':commit,'files':restore,'count':len(restore),'raw_not_copied':True},indent=2)+'\n')
call(['bash','scripts/dev/beads.sh','update','quoridor-4lc.168','--append-notes','168 self source/static children stopped. Independent saved arithmetic: fixed10 searches/320CP/320NN+startup2; exact discrete and ledger differences null, f64 prior/score differences separate. Source a09279c and binary166dd0c4 bound; oldWasm5root numeric max3.5762787e-6 separate. r1 checker schema KeyError retained/r2exit0; science negative0. No nativebinary replay or new NN. docs/reports/ai-sigma-critic-native-stageA-independent.md; dataGit '+commit+'. Coordinator acceptance/close pending; StageB/NI outside.'])
call(['bash','scripts/dev/beads.sh','backup','sync'])
size=sum(p.stat().st_blocks*512 for base in [D,T] for p in base.rglob('*') if p.is_file())+REPORT.stat().st_blocks*512
intake=json.loads((D/'intake.json').read_text());st=intake['storage'];total=st['old_conservative']+sum(st['prior_measured_allocated'].values())+max(st['new_forecast'],size);assert total<st['guard']
summary={'issue':'quoridor-4lc.168','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_commit':commit,'source_stopped':True,'children_stopped':True,'Git_stream_restore_count':len(restore),'Beadsnotes_exit':0,'backup_exit':0,'science_reexecution_NN':0,'formal_ready':False,'coordinator_acceptance_pending':True,'old_unknown_discount':0,'new_storage_current_allocated':size,'new_storage_forecast':st['new_forecast'],'current_plus_forecast':total,'storage_guard':st['guard'],'managed_static_conservative_seconds':81.90789632900851,'finalization_elapsed_seconds':sum(x['elapsed_seconds'] for x in logs)}
(D/'handoff.json').write_text(json.dumps(summary,indent=2)+'\n')
subprocess.run(['git','add','--',str((D/'git-restore.json').relative_to(R)),str((D/'handoff.json').relative_to(R)),str((D/'finalize-attempts.json').relative_to(R))],env={**env,**ge},check=True,timeout=60)
subprocess.run(['git','commit','-m','research: preserve 168 stop restore and Beads backup'],env={**env,**ge},check=True,timeout=60)
print(json.dumps({**summary,'handoff_commit':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()}))
