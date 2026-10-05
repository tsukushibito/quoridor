"""NN0 saved-payload checks and compact archival; no model load or new search."""
from pathlib import Path
import hashlib,json,datetime,time,os,tarfile,subprocess,io
R=Path.cwd();D=R/'research-data/ai-sigma/frame19-leaf-terminal';T=R/'tools/ai-sigma-frame19-leaf-terminal';start=time.monotonic()
os.sched_setaffinity(0,{2});sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();utc=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat();save=lambda n,x:(D/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
# Fresh read-only binding for the short NN0 collection; no saved quiet point reused.
loaded=json.load(open(R/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame19/running-loaded.json'));assert loaded['frame_start_fixed']=='2026-10-04T22:52:46Z'
assert loaded['parent_sha']==sha(R/'docs/design/ai-sigma-continuation-20261001.md')
mon=Path(loaded['run'])/'monitor-observation.json';assert time.time()-mon.stat().st_mtime<120
for role in ['scheduler','monitor']:
 z=loaded[role].get('process',loaded[role]);tick=int(Path('/proc',str(z['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]);assert str(tick)==str(z['start_ticks'])
for issue in ['quoridor-4lc','quoridor-4lc.240']:
 q=json.loads(subprocess.check_output(['bash','scripts/dev/beads.sh','show',issue,'--json']))[0];assert q['status']=='in_progress'and 'paused-by-user'not in q.get('labels',[])
 if issue.endswith('.240'):assert q['assignee']=='codex:01a0f31d-6d15-7620-bb63-4b4f878e4746'
index=Path('/workspaces/quoridor/.git/worktrees/ai-sigma/index');indexSHA=sha(index);assert indexSHA=='59880a1d93833b8a0ea250e9a2b1270c41ceb9f6666da9ab0edeb48991817072'
stop=json.load(open(D/'scientific-stop-v1.json'))
for p,h in stop['source_SHA'].items():assert sha(R/p)==h
for p,h in stop['payload_SHA'].items():assert sha(Path(p))==h
for pid,tick in stop['tracked_PIDticks'].items():
 p=Path('/proc',pid,'stat')
 if p.exists():assert int(p.read_text().rsplit(')',1)[1].split()[19])!=tick
profile=json.load(open(D/'profile-result-r2.json'));assert len(profile['results'])==64 and len(profile['matches'])==48
for r in profile['results']:
 assert r['stats']['processed']==8192 and r['completed_depth']==2 and r['partial_depth_discarded']==3
 assert [d['completed_depth']for d in r['depths']if d['status']=='COMPLETED']==[1,2]
 if r['engine']=='distance':assert r['stats']['NN']==0
for case in json.load(open(D/'exact-cases-r1.json'))['results']:
 assert case['status']=='COMPLETED'and len(case['values'])==case['legal_count']
 assert len({v['Action']for v in case['values']})==case['legal_count']
 assert case['argmax_Actions']==[v['Action']for v in case['values']if v['value']==max(w['value']for w in case['values'])]
 assert all(v['bound']=='EXACT_FINITE_DEPTH_FULL_WINDOW'for v in case['values'])
clocks=[]
for file in ['optional4-r1-hands.jsonl','remaining3-r1-hands.jsonl']:
 for line in open(D/file):
  h=json.loads(line);c=h['clock'];assert c['status']=='RECEIVED';assert c['elapsed_ms']<=100 and c['received_ms']-c['t0_ms']<=100
  z=c['response'];assert z['id']==h['id']and z['generation']==h['generation']
  assert z['validation']['valid']and z['validation']['legal']and z['search']['completed_depth']>=1 and z['search']['action_legal']
  assert z['search']['last_completed_only']and z['search']['parent_copy_key_history_restored']
  clocks.append(h)
assert len(clocks)==142
ledger=json.load(open(D/'optional4-final-ledger.json'));assert len(ledger['ledger'])==4 and ledger['ledger'][0]['status']=='UNKNOWN'
assert sum(s['status']=='TERMINAL'for s in ledger['ledger'])==3
from collections import Counter
engine_clock={}
for e in ['NNUE','distance']:
 rows=[h for h in clocks if h['engine']==e];engine_clock[e]={'received_hands':len(rows),'max_elapsed_ms':max(h['clock']['elapsed_ms']for h in rows),'completed_depth_counts':dict(Counter(h['clock']['response']['search']['completed_depth']for h in rows)),'processed_nodes':sum(h['clock']['response']['search']['stats']['processed']for h in rows),'NN_saved_hand_sum':sum(h['clock']['response']['search']['stats']['NN']for h in rows),'remaining3_hand_count':sum(h['slot']!=1 for h in rows)}
verification={'UTC':utc(),'scope':'saved output arithmetic/schema and clocks only;no additional RuleA replay/model/forward','NN':0,'clock_hands':len(clocks),'all_received_t1_le100':True,'max_received_ms':max(h['clock']['elapsed_ms']for h in clocks),'engines':engine_clock,'profile_common_completed_depth_values_Action_source_assertions':True,'exact_allrootchild_schema':16,'old_slot1_UNKNOWN_preserved':True,'source_and_payload_SHA_PASS':True,'current_scientific_exact_absence':True,'index_SHA':indexSHA,'binding_path':loaded['run'],'monitor_mtime':mon.stat().st_mtime,'CPU':[2],'current_self_RSS':int(Path('/proc/self/statm').read_text().split()[1])*4096,'science_NN_added':0,'no_fullhost_guarantee':True};save('saved-verification-v1.json',verification)
archive=D/'required-evidence-v1.tar.gz';assert not archive.exists()
# Preserve raw/clocks/config/log/failure/status once in compact pack; live originals remain for readers.
files=sorted(p for root in [D,T]for p in root.rglob('*')if p.is_file()and p!=archive and p.name not in ['process.lock','notify.lock']and p.suffix not in ['.pyc'])
usage=sum(p.stat().st_size for root in [D,T]for p in root.rglob('*')if p.is_file());assert usage+2*1024**2<7*1024**2
members=[]
with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
 for p in files:
  name=str(p.relative_to(R));tar.add(p,arcname=name,recursive=False);members.append({'path':name,'bytes':p.stat().st_size,'SHA':sha(p)})
with tarfile.open(archive,'r:gz')as tar:
 for x in members:
  b=tar.extractfile(x['path']).read();assert len(b)==x['bytes']and hashlib.sha256(b).hexdigest()==x['SHA']
save('archive-manifest-v1.json',{'UTC':utc(),'path':str(archive),'SHA':sha(archive),'bytes':archive.stat().st_size,'members':members,'restore_PASS':True,'restore':'stream each tar member bytes/SHA;no disk whole-copy','original_live_paths_preserved_for_241':True,'old_failed_source_versions':'Git25815e3,b7a4718;old236readonlyfac3c5c;no replacement','shared_input_references':{p:h for p,h in json.load(open(D/'exact-cases-settings-r1.json'))['sources'].items()if not p.startswith(str(T))and not p.startswith(str(D))}})
assert sha(index)==indexSHA
save('collection-process-v1.json',{'UTC':utc(),'wall_s':time.monotonic()-start,'NN':0,'model':0,'GPU':0,'archive_members':len(members),'archive_bytes':archive.stat().st_size,'index_unchanged':True,'current_self_RSS':int(Path('/proc/self/statm').read_text().split()[1])*4096,'RAM_guard':448*1024**2,'bounded_management_only':True})
print(json.dumps({'PASS':True,'hands':len(clocks),'archive_members':len(members),'archive_bytes':archive.stat().st_size,'wall_s':time.monotonic()-start,'engines':engine_clock}))
