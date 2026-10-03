import subprocess,pathlib,json,time,datetime,os,hashlib
os.sched_setaffinity(0,{0}); D=pathlib.Path('research-data/ai-sigma/179-native-teacher-independent');started=time.monotonic();commands=[]
def run(args,data=None,limit=15):
 p=subprocess.run(args,input=data,capture_output=True,timeout=limit);commands.append({'command':args[:6],'exit':p.returncode,'stderr':p.stderr.decode()[:700]});assert p.returncode==0,(args[:6],p.stderr.decode()[:700]);return p.stdout
def commit(message):
 files=[p for p in D.iterdir() if p.is_file() and p.name!='save.log']+[pathlib.Path('docs/reports/ai-sigma-critic-native-teacher-independent.md')];changes={}
 for p in files:
  name=str(p);assert not p.is_absolute() and name and all(s for s in name.split('/'));assert name.startswith(str(D)+'/') or name=='docs/reports/ai-sigma-critic-native-teacher-independent.md';changes[name]=run(['git','hash-object','-w','--stdin'],p.read_bytes()).decode().strip()
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
own=json.loads(run(['bash','scripts/dev/beads.sh','show','quoridor-4lc.179','--json']));own=own[0] if isinstance(own,list) else own;assert own['status']=='in_progress' and own['assignee']=='codex:01a0f31d-8227-7e03-a7e6-915b4918c11b'
cid,files=commit('research: independent saved native teacher and learner verdict 179')
restored=[]
for p in files:
 b=run(['git','show',cid+':'+str(p)]);assert b==p.read_bytes();restored.append({'path':str(p),'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
(D/'restore-check.json').write_text(json.dumps({'data_git':cid,'exact_Git_stream_restore':True,'files':restored},indent=2)+'\n')
run(['bash','scripts/dev/beads.sh','update','quoridor-4lc.179','--append-notes','Saved independent verification supports24CPU GOAL1409teacher rows, K64/root64edge63/piP2mapping/z/lineage split20train1188+4val221; fourdefinitions unique1384/1388/1384/1385 and trainvalshared0. SharedRuleA NN0 replay24+4arena matches, no deepsearch guarantee. Checkpoint/source/export SHA and5saved parityreceipts bind, no model forward/reload. SavedπCE/zMSE fit improve vsuntrained; student4diagnostic0W4L not improvement/NI/cause attribution. ONE proposal quality denominators/allattemptcost ledger. Production198.496598s; knownallcompute235.726026s+export/overlap236.583166s; missingcostunknown. CPU0 scientific children stopped, originalwrite0. Report docs/reports/ai-sigma-critic-native-teacher-independent.md; dataGit '+cid+'. Coordinatoraccept/close.'])
run(['bash','scripts/dev/beads.sh','backup','sync'])
(D/'handoff.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'source_stopped':True,'science_children_stopped':True,'NN_forward_GPU_game_train':0,'Beads_backup_sync':True,'Git_restore':True,'full_private_index':False,'management_seconds':time.monotonic()-started,'commands':commands},indent=2)+'\n');hand,_=commit('research: 179 stop restore and backup handoff')
body='goal quoridor-4lc /179 final: SUPPORT limited24CPU GOAL1409teachers /20train1188+4val221 /200step checkpoint ONNX /all4new diagnostic. Own pi63/mask/P2jump-wall/z/side/hashsplit/4overlap arithmetic and NN0 sharedRuleA24+4 replay match; crossgame16keys37occurrences/train-valshared0, fullstateholdout/deepsearch not proved. Dataset/checkpoint/ONNX SHA +frozen source +5saved reload/export receipts bind; no newmodel/forward. Saved baselinepiCE/zMSE train andval improved; 0W4L means connection not strength/improvement/NI, cause unknown. ONE adoption quality Rpolicy/Rz/Rjoint overallattemptjobwall alongside production; production198.496598s 7.098358rows/s; recordedcompute235.726026s +export/overlap236.583166s, uninstrumentedcostunknown. GPUoriginalCPU001unknown/6NOT_STARTED and laterNN0rootjoin separate, newgeneration倍率notestablished. Staticmeasured~1.047s/charge5s <=90, peak203374592 <=448MiB, ownedsciencechildren stopped. Sourcewriter original0, privateindex0, failuresretainednotloss. Report docs/reports/ai-sigma-critic-native-teacher-independent.md. DataGit '+cid+' handoffGit '+hand+'. Gitstreamrestore/Beadsnotes+backup complete; coordinatoraccept/close.'
(D/'final-report.txt').write_text(body+'\n');p=subprocess.run(['timeout','25s','bash','scripts/dev/research-team.sh','report','--to','coordinator','--issue','quoridor-4lc','--body-file',str((D/'final-report.txt').resolve())],capture_output=True,timeout=30);(D/'final-report-transport.json').write_bytes(p.stdout);(D/'final-report.stderr').write_bytes(p.stderr)
(D/'delivery.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_git':cid,'handoff_git':hand,'transport_exit':p.returncode,'management_seconds':time.monotonic()-started,'commands':commands},indent=2)+'\n');delivery,_=commit('research: save 179 final coordinator delivery');print(json.dumps({'data_git':cid,'handoff_git':hand,'delivery_git':delivery,'report_exit':p.returncode,'transport':p.stdout.decode()[:800],'elapsed_seconds':time.monotonic()-started}));assert p.returncode==0,p.stderr.decode()[:800]
