import subprocess,pathlib,json,time,datetime,os,hashlib
os.sched_setaffinity(0,{0}); D=pathlib.Path('research-data/ai-sigma/182-k800-cost-independent');started=time.monotonic();commands=[]
def run(args,data=None,limit=15):
 p=subprocess.run(args,input=data,capture_output=True,timeout=limit);commands.append({'command':args[:6],'exit':p.returncode,'stderr':p.stderr.decode()[:700]});assert p.returncode==0,(args[:6],p.stderr.decode()[:700]);return p.stdout
def commit(message):
 files=[p for p in D.iterdir() if p.is_file() and p.name!='save.log']+[pathlib.Path('docs/reports/ai-sigma-critic-k800-cost-independent.md')];changes={}
 for p in files:
  name=str(p);assert not p.is_absolute() and name and all(s for s in name.split('/'));assert name.startswith(str(D)+'/') or name=='docs/reports/ai-sigma-critic-k800-cost-independent.md';changes[name]=run(['git','hash-object','-w','--stdin'],p.read_bytes()).decode().strip()
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
own=json.loads(run(['bash','scripts/dev/beads.sh','show','quoridor-4lc.182','--json']));own=own[0] if isinstance(own,list) else own;assert own['status']=='in_progress' and own['assignee']=='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'
cid,files=commit('research: critic 182 independent K800 cost and teacher direction')
restore=[]
for p in files:
 b=run(['git','show',cid+':'+str(p)]);assert b==p.read_bytes();restore.append({'path':str(p),'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()})
(D/'restore-check.json').write_text(json.dumps({'data_git':cid,'exact_Git_stream_restore':True,'files':restore},indent=2)+'\n')
run(['bash','scripts/dev/beads.sh','update','quoridor-4lc.182','--append-notes','Own archive-member NN0 arithmetic supports all30 warm6/steady24 root800edge799 NN24000 startup6. C/R median1.322332/1.325008/1.229342 with minmax/paired ratios saved; no prereg speed margin, no language-only/C++/NI/fullteacher extrapolation. Allroot Action/visits/mean/firstNN137bits exact, edgef64max1.38778e-17; sharedRuleA root inputs30 replay supports limited, no full deep. Scientific job196.368316s/allowned199.525562s; internal Ccheckpoint800/2404calls/response7.657-8.055MB, API insidepipe/bridge nonexclusive. ONE concern181 K800 route selection provisional forK64 teachercost; existing6game quality Rjoint/allattemptjobwall veto/fallback beforeproduction, no speeddiagnosis chain. donefalse terminal-noNN drains; rootterminal0/K1edge0 no forgedpi; cancelledpartial typedunknown. CPU0 children stopped, ~.719s/charge3s<=120/RSS59.6MB<448guard; newNN/model/game/build/train0. Report docs/reports/ai-sigma-critic-k800-cost-independent.md; dataGit '+cid+'. Original180/181write0; coordinator accepts/closes.'])
run(['bash','scripts/dev/beads.sh','backup','sync'])
(D/'handoff.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'source_stopped':True,'science_children_stopped':True,'NN_backend_game_build_GPU_train':0,'Beadsbackup_sync':True,'Git_restore':True,'full_private_index':False,'management_seconds':time.monotonic()-started,'commands':commands},indent=2)+'\n');hand,_=commit('research: 182 independent stop restoration and backup')
body='goal quoridor-4lc /182 final SUPPORT limited saved30sameK800 warm6 steady24 NN24000+startup6. Own raw-member arithmetic/rootNN0 sharedRuleA replay: Action/legalorder/visits/rootmean/firstroot648+137f32 bits exact, edgef64max1.38778e-17, no all deep/backend rerun. Currentbinary166dd0c4/modeld790 and scientificsourceca7ddb93/providerORT1.30CPU1/core2 bind. MedianC/R1.322332/1.325008/1.229342, pairratio ranges1.148894-1.496409/1.190958-1.339064/1.134692-1.378275; speedmargin unset =>ratio/width only,no equivalence/NI/C++/purelanguage claim. Scientific196.368316s/allowned199.525562s, unknownstaticcost retained; Cbridge2404calls/checkpoint800/7.657-8.055MB, APIinsidepipe/nonexclusive. ONE concern:181 K800newJS routing provisional forK64teacher efficiency; existing6K64 quality Rjoint/allattemptjobwall can veto/fallback beforeproduction, fixbefore newresults; no newbenchmark/gate chain, reserve24lineage+learner progress. Cancellation partialcompleted can lag root until finalCP; rootterminal0/K1edge0 no policyrow, done/noNN/control-drain semantics limitedreview not181implementationacceptance. Own CPU0science stopped~.719s/RSS59.6MB/newNN-model-session-game-build-GPU-train0; original180/181write0. Report docs/reports/ai-sigma-critic-k800-cost-independent.md. DataGit '+cid+' handoffGit '+hand+'. Necessary Gitstreamrestore/Beadsnotes+backup done; coordinator acceptance/close.'
(D/'final-report.txt').write_text(body+'\n');p=subprocess.run(['timeout','25s','bash','scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str((D/'final-report.txt').resolve())],capture_output=True,timeout=30);(D/'final-report-transport.json').write_bytes(p.stdout);(D/'final-report.stderr').write_bytes(p.stderr)
(D/'delivery.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'handoff_git':hand,'transport_exit':p.returncode,'management_seconds':time.monotonic()-started,'commands':commands},indent=2)+'\n');delivery,_=commit('research: preserve 182 final coordinator delivery');print(json.dumps({'data_git':cid,'handoff_git':hand,'delivery_git':delivery,'report_exit':p.returncode,'transport':p.stdout.decode()[:900],'elapsed_seconds':time.monotonic()-started}));assert p.returncode==0,p.stderr.decode()[:800]
