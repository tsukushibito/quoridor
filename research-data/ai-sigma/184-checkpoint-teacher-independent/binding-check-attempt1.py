import pathlib,json,tarfile,hashlib,statistics,time,datetime,os,resource,subprocess
os.sched_setaffinity(0,{0});start=time.monotonic();A=pathlib.Path('research-data/ai-sigma/181-checkpoint-teacher');D=pathlib.Path('research-data/ai-sigma/184-checkpoint-teacher-independent');out={'NN_executed':0,'first_difference':None}
def sha(b):return hashlib.sha256(b).hexdigest()
def load(n):return json.loads((A/n).read_text())
try:
 m=load('archive-manifest.json');hs={}
 with tarfile.open(A/'attemptpack.tar.gz','r:gz')as tar:
  def read(n):
   b=tar.extractfile(n).read();assert sha(b)==m['members'][n],n;hs[n]=sha(b);return b
  base='.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER/';rows=[json.loads(x)for x in read(base+'runs/native181-measure-r1/rows.jsonl').splitlines()];ratios=[]
  assert [r['slot']for r in rows]==list(range(27));assert sum(r['NN_actual']for r in rows)==21600
  for fixture in ['initial-p1','asym-hv-p2','straight-jump-p2']:
   rr=[r for r in rows if r['fixture']==fixture];ref=next(r for r in rr if r['engine']=='reference');med={};rng={}
   for r in rr:
    cp=r['cp'];assert cp['root_visits']==cp['simulations']==r['NN_actual']==r['returned']==800;assert sum(e['visits']for e in cp['root_edges'])==799
    assert abs(r['elapsed_ms']-(r['final_CP_validation_end']-r['t0']))<1e-7
    assert r['first_NN']['features_bits']==ref['first_NN']['features_bits']and r['first_NN']['NN_bits']==ref['first_NN']['NN_bits'];assert cp['action']==ref['cp']['action']and cp['root_mean']==ref['cp']['root_mean'];assert [(e['action'],e['visits'])for e in cp['root_edges']]==[(e['action'],e['visits'])for e in ref['cp']['root_edges']]
   for engine in ['old','new','reference']:
    v=[r['elapsed_ms']for r in rr if r['engine']==engine and r['phase']=='steady'];assert len(v)==2;med[engine]=statistics.median(v);rng[engine]=[min(v),max(v)]
   ratios.append({'fixture':fixture,'median_ms':med,'range_ms':rng,'new_old':med['new']/med['old'],'new_JS':med['new']/med['reference']})
  adopt=sum(r['new_old']<=.9 for r in ratios)>=2 and all(r['new_old']<=1.05 for r in ratios);select=sum(r['new_JS']<=.95 for r in ratios)>=2 and all(r['new_JS']<=1.05 for r in ratios);assert not adopt and not select
  benchmark=load('benchmark-status.json');assert len(benchmark)==6 and all(x['status']=='NOT_STARTED'for x in benchmark)
  prod=json.loads(read(base+'runs/native181-production-r1/result.json'));flat=[g for core in prod['results']for g in core['results']];assert len(flat)==24;assert all(g['status']=='GOAL'for g in flat);assert prod['NN_actual']==77387 and prod['startup_actual']==3 and prod['primary']is None and prod['monitor_state']=='READY';assert all(x['exit']['code']==0 for x in prod['closed']);assert sum(x['usedNN']for x in prod['closed'])==77387
  source_receipts={n:read(n).decode().strip()for n in m['members']if n.endswith(('learner-source-git.txt','measurement-source-git.txt','production-source-git.txt'))}
 stop=load('science-stop.json');handoff=load('handoff-stop.json');assert sha((A/'science-stop.json').read_bytes())==handoff['science_stop_SHA256'];assert all(sha(pathlib.Path(p).read_bytes())==h for p,h in stop['source_hashes'].items())
 snapshot={}
 for n in ['teacher-rows.jsonl.gz','training-connection-rows.jsonl.gz','openings.json','production-preregister.json','learner-preregister.json','learner-training.json','learner-export.json','learner-reload.json','science-stop.json','handoff-stop.json']:
  b=(A/n).read_bytes();gh=subprocess.run(['git','show','63df8654e4bdcc5fadc4c4be11bc71bfa6770f61:'+str(A/n)],capture_output=True);assert gh.returncode==0;assert b==gh.stdout,n+' saved Git binding';snapshot[n]=sha(b)
 current=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   c=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()
   if '/tools/ai-sigma-native-checkpoint-teacher/'in c and int(p.name)!=os.getpid():current.append({'pid':int(p.name),'cmd':c})
  except OSError:pass
 out.update({'supported':True,'K800_ratios':ratios,'checkpoint_adoption':adopt,'newRust_selected':select,'benchmark_status':'all6 NOT_STARTED','source_receipts':source_receipts,'source_current_matches_stop':True,'snapshot_hashes':snapshot,'archive_members_verified':hs,'current_matching_181_science':current,'all_host_period_guarantee':False,'old173_read_by_this_check':0})
except BaseException as e:
 import traceback;out.update({'supported':False,'first_difference':str(e),'trace':traceback.format_exc()})
out.update({'elapsed_seconds':time.monotonic()-start,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid(),'end':datetime.datetime.now(datetime.timezone.utc).isoformat()});D.joinpath('binding-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['snapshot_hashes','archive_members_verified']}));assert out['supported']
