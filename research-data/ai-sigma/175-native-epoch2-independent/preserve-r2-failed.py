import subprocess,pathlib,json,time,datetime,os,hashlib
os.sched_setaffinity(0,{0}); D=pathlib.Path('research-data/ai-sigma/175-native-epoch2-independent');started=time.monotonic();commands=[]
def run(args,data=None):
 p=subprocess.run(args,input=data,capture_output=True,timeout=30);commands.append({'command':args[:6],'exit':p.returncode,'stderr':p.stderr.decode()[:800]});assert p.returncode==0,(args[:6],p.stderr.decode()[:800]);return p.stdout
def commit(message):
 files=[p for p in D.iterdir() if p.is_file() and p.name!='preserve.log']+[pathlib.Path('docs/reports/ai-sigma-critic-native-epoch2-independent.md')];changes={str(p):run(['git','hash-object','-w','--stdin'],p.read_bytes()).decode().strip() for p in files}
 for attempt in range(4):
  head=run(['git','rev-parse','HEAD']).decode().strip()
  def tree(base,updates):
   entries={}
   if base:
    for line in run(['git','ls-tree','-z',base]).split(b'\0'):
     if line:
      meta,name=line.split(b'\t',1);mode,typ,oid=meta.decode().split();
      if name:entries[name.decode()]=(mode,typ,oid)
   branches={}
   for path,oid in updates.items():
    if '/' not in path:entries[path]=('100644','blob',oid)
    else:
     first,rest=path.split('/',1);branches.setdefault(first,{})[rest]=oid
   for first,sub in branches.items():entries[first]=('040000','tree',tree(entries.get(first,(None,None,None))[2],sub))
   buf=b''.join((mode+' '+typ+' '+oid+'\t'+name).encode()+b'\0' for name,(mode,typ,oid) in sorted(entries.items()))
   return run(['git','mktree','-z'],buf).decode().strip()
  root=tree(head+'^{tree}',changes);cid=run(['git','commit-tree',root,'-p',head,'-m',message]).decode().strip();p=subprocess.run(['git','update-ref','HEAD',cid,head],capture_output=True)
  if p.returncode==0:return cid,files
 raise RuntimeError('HEAD concurrent changes; objects preserved, no overwrite')
assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-10-03T08:10:00+00:00')
own=json.loads(run(['bash','scripts/dev/beads.sh','show','quoridor-4lc.175','--json']));own=own[0] if isinstance(own,list) else own;assert own['status']=='in_progress' and own['assignee']=='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'
cid,files=commit('research: critic 175 independent epoch2 uncertain verdict')
restore=[]
for p in files:
 b=run(['git','show',cid+':'+str(p)]);assert b==p.read_bytes();restore.append({'path':str(p),'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()})
(D/'restore-check.json').write_text(json.dumps({'commit':cid,'exact_Git_stream_restore':True,'files':restore},indent=2)+'\n')
run(['bash','scripts/dev/beads.sh','update','quoridor-4lc.175','--append-notes','Independent NN0 epoch2: 33block/99pair/198GOAL W95 D0 L103, quality unknown0, all33prefix NI/inferiority threshold20 unhit; wealth1.8850576/.4384794. UNCERTAIN supported. Clock8268 and NN537460 finite correspondence; conditionalmean/kernelCPU/drift/deepRuleA unresolved. Report docs/reports/ai-sigma-critic-native-epoch2-independent.md; Git '+cid+'. Own science source/children stopped, stream restore verified. Coordinator accepts/closes.']);run(['bash','scripts/dev/beads.sh','backup','sync'])
(D/'handoff.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'science_source_stopped':True,'science_children_stopped':True,'NN_game_build':0,'Beads_backup_sync':True,'restore':True,'full_private_index':False,'static_budget_seconds':120,'management_elapsed_seconds':time.monotonic()-started,'commands':commands},indent=2)+'\n');hand,_=commit('research: save 175 restoration stop and handoff')
body='goal quoridor-4lc /175 final NN0 independent verdict: receipt07:56:53, claim/static start07:57:21.940755. UNCERTAIN supported: epoch2 all33blocks/99pairs/198GOAL W95D0L103, qualityunknown0, mean95/198. All33 exact integer prefixes unhit threshold20, final NI1.8850575878/inferiority0.438479351. Pre-registration Git8e14cf496047f3c2f19a5824abd219c82ce3b54f matches; fixed lambdas/.45/core2/4/6 and headroom305, stop SCIENCE_DEADLINE_HEADROOM consistent. Future1002unregistered omitted from wealth; capacity interval[19/240,1097/1200] separate; oldepoch6qualificationunknown/wealth separate. Journal8268 public CP actualend<=402/public<=500/nextquiescent and NN537460started=returned finite correspondence, deviation0; admitmax401.998649985 is finite nearboundary, not clockprecision/CPUcycle/drift guarantee. Source/stop/close finite only; no deep RuleA/allhost guarantee. Next ONE direction: separate native teacher generation finalroot pi/rootmean/z/lineage -> existing learner, no formalholdout training, usefulteacherrows/jobtime; new execution0. Report docs/reports/ai-sigma-critic-native-epoch2-independent.md. DataGit '+cid+' handoffGit '+hand+'. Own source/children stopped, Git restoration and Beadsbackup complete. Acceptance/close coordinator.'
(D/'final-report.txt').write_text(body+'\n'); p=subprocess.run(['taskset','-c','0','timeout','35s','bash','scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str((D/'final-report.txt').resolve())],capture_output=True,timeout=40);(D/'final-report-transport.json').write_bytes(p.stdout);(D/'final-report.stderr').write_bytes(p.stderr)
(D/'delivery.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'handoff_git':hand,'transport_exit':p.returncode,'management_elapsed_seconds':time.monotonic()-started,'PID':os.getpid(),'commands':commands},indent=2)+'\n');delivery,_=commit('research: preserve 175 final delivery metadata');print(json.dumps({'data_git':cid,'handoff_git':hand,'delivery_git':delivery,'report_exit':p.returncode,'transport':p.stdout.decode()[:1200],'elapsed_seconds':time.monotonic()-started}));assert p.returncode==0,p.stderr.decode()[:1000]
