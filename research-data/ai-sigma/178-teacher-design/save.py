import subprocess,pathlib,json,time,datetime,os,hashlib
os.sched_setaffinity(0,{0}); D=pathlib.Path('research-data/ai-sigma/178-teacher-design');started=time.monotonic();commands=[]
def run(args,data=None,limit=15):
 p=subprocess.run(args,input=data,capture_output=True,timeout=limit);commands.append({'command':args[:6],'exit':p.returncode,'stderr':p.stderr.decode()[:700]});assert p.returncode==0,(args[:6],p.stderr.decode()[:700]);return p.stdout
def commit(message):
 files=[p for p in D.iterdir() if p.is_file() and p.name!='save.log']+[pathlib.Path('docs/reports/ai-sigma-critic-native-teacher-design.md')];changes={}
 for p in files:
  name=str(p);assert not p.is_absolute() and name and all(s for s in name.split('/'));assert name.startswith(str(D)+'/') or name=='docs/reports/ai-sigma-critic-native-teacher-design.md';changes[name]=run(['git','hash-object','-w','--stdin'],p.read_bytes()).decode().strip()
 for attempt in range(4):
  head=run(['git','rev-parse','HEAD']).decode().strip()
  def tree(base,updates):
   entries={}
   if base:
    for line in run(['git','ls-tree','-z',base]).split(b'\0'):
     if line:
      meta,name=line.split(b'\t',1);assert name;mode,typ,oid=meta.decode().split();entries[name.decode()]=(mode,typ,oid)
   branches={}
   for path,oid in updates.items():
    if '/' not in path:entries[path]=('100644','blob',oid)
    else:
     first,rest=path.split('/',1);assert first and rest;branches.setdefault(first,{})[rest]=oid
   for first,sub in branches.items():entries[first]=('040000','tree',tree(entries.get(first,(None,None,None))[2],sub))
   buf=b''.join((mode+' '+typ+' '+oid+'\t'+name).encode()+b'\0' for name,(mode,typ,oid) in sorted(entries.items()));return run(['git','mktree','-z'],buf).decode().strip()
  root=tree(head+'^{tree}',changes);cid=run(['git','commit-tree',root,'-p',head,'-m',message]).decode().strip();p=subprocess.run(['git','update-ref','HEAD',cid,head],capture_output=True)
  if p.returncode==0:return cid,files
 raise RuntimeError('HEAD contention; objects retained without overwrite')
intake=json.loads((D/'intake.json').read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(intake['submission_deadline'])
own=json.loads(run(['bash','scripts/dev/beads.sh','show','quoridor-4lc.178','--json']));own=own[0] if isinstance(own,list) else own;assert own['status']=='in_progress' and own['assignee']=='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'
refs=[]
for name in ['research-data/ai-sigma/160-pv-pipeline-bootstrap/schema.json','research-data/ai-sigma/160-pv-pipeline-bootstrap/final-report.md','research-data/ai-sigma/162-pv-cpu-smoke/final-report.md','research-data/ai-sigma/frame10-coordinator-start/174-gpu-finite-acceptance.json','tools/ai-sigma-pv-pipeline-bootstrap/bootstrap.py','tools/ai-sigma-native-baseline/engine.cjs','tools/ai-sigma-native-baseline/common.cjs']:
 b=pathlib.Path(name).read_bytes();refs.append({'path':name,'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()})
(D/'source-references.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'references':refs,'read_scope':'minimal teacher schema/source and finite prior outcomes; no original modification'},indent=2)+'\n')
cid,files=commit('research: critic 178 teacher quality and efficiency design')
restore=[]
for p in files:
 b=run(['git','show',cid+':'+str(p)]);assert b==p.read_bytes();restore.append({'path':str(p),'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()})
(D/'restore-check.json').write_text(json.dumps({'commit':cid,'exact_Git_stream_restore':True,'files':restore},indent=2)+'\n')
run(['bash','scripts/dev/beads.sh','update','quoridor-4lc.178','--append-notes','Static design supports176 initial CPU generation; ONE recommendation qualification ledger Rpolicy/Rz/Rjoint with allattempt/jobwall. K64 root64-edge63/NN counters distinct, zunknown value mask, pi != sampledaction, game split crossgame overlap limitations, final-only source correspondence/GPU finite parity. NN0 sixbadmock pass, CPU0 static child stopped/earlyreport to coordinator for hyp177 scheduling. Report docs/reports/ai-sigma-critic-native-teacher-design.md; dataGit '+cid+'. Acceptance/close coordinator.']);run(['bash','scripts/dev/beads.sh','backup','sync'])
(D/'handoff.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'science_source_stopped':True,'science_children_stopped':True,'NN_game_build_GPU_train':0,'Beads_backup_sync':True,'restore':True,'full_private_index':False,'management_elapsed_seconds':time.monotonic()-started,'commands':commands},indent=2)+'\n');hand,_=commit('research: save 178 stop restoration and handoff')
body='goal quoridor-4lc /178 final: claim/static start09:08:47.422339; ONE recommendation quality qualification/allattempt cost ledger: Rpolicy/Rz/Rjoint separately over totaljobwall including init/generation/search/NN/transport/record/cleanup. Supports176 initial CPU generation/learner connection without fulltext gate. K64 rootN64/edge63 pi, rootNN/rootmean/leaf/z and actualNN/terminalnoNN separate; truncated zunknown/valuemaskfalse; tau1 first16newply sampled action != teacherpi. Game lineage split holds exports/resumes, crossgame state/feature overlap remains;173formal198holdout excluded. Final-only CP preserves per-sim eventdrain/cancel/math and final root, firstCP semantics differ; removing JSON may leave internal root_edges construction. GPU1745input finite parity/batch1 timing not truebatch/fullgeneration/NI; independentsearch1pending batch != single-tree multileaf change. SmallNN0 P2jump/walls136/pi63/sign/signature/censoring sixbadmock pass, current science child absent; CPU0 static end09:12 relayed through coordinator for hyp177 scheduling. NewNN/game/GPU/train0. Report docs/reports/ai-sigma-critic-native-teacher-design.md. DataGit '+cid+' handoffGit '+hand+'. Source/children stopped, Git restoration/Beadsbackup complete; coordinator accepts/closes.'
(D/'final-report.txt').write_text(body+'\n');p=subprocess.run(['taskset','-c','0','timeout','25s','bash','scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str((D/'final-report.txt').resolve())],capture_output=True,timeout=30);(D/'final-report-transport.json').write_bytes(p.stdout);(D/'final-report.stderr').write_bytes(p.stderr)
(D/'delivery.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'handoff_git':hand,'transport_exit':p.returncode,'management_elapsed_seconds':time.monotonic()-started,'PID':os.getpid(),'commands':commands},indent=2)+'\n');delivery,_=commit('research: preserve 178 final delivery metadata');print(json.dumps({'data_git':cid,'handoff_git':hand,'delivery_git':delivery,'report_exit':p.returncode,'transport':p.stdout.decode()[:900],'elapsed_seconds':time.monotonic()-started}));assert p.returncode==0,p.stderr.decode()[:800]
