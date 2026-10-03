import json,gzip,tarfile,pathlib,hashlib,time,datetime,resource,os
os.sched_setaffinity(0,{0});st=time.monotonic();A=pathlib.Path('research-data/ai-sigma/181-checkpoint-teacher');D=pathlib.Path('research-data/ai-sigma/184-checkpoint-teacher-independent');rows={r['row_id']:r for r in map(json.loads,gzip.open(A/'teacher-rows.jsonl.gz','rt'))};games=json.loads((A/'all-game-status.json').read_text());m=json.loads((A/'archive-manifest.json').read_text());out={'NN_executed':0,'first_difference':None};seen=set();bound=[]
try:
 with tarfile.open(A/'attemptpack.tar.gz','r:gz')as t:
  def read(n):
   b=t.extractfile(n).read();assert hashlib.sha256(b).hexdigest()==m['members'][n];bound.append(n);return b
  base='.artifacts/ai-sigma/resume-20261003/CHECKPOINT-TEACHER/runs/native181-production-r1/'
  for core in [2,4,6]:
   finals=[json.loads(x)for x in read(base+'core'+str(core)+'/rows.jsonl').splitlines()]
   for r in finals:
    assert r['row_id']not in seen;seen.add(r['row_id']);tr=rows[r['row_id']];assert all(tr[k]==v for k,v in r.items()),r['row_id']+' final source join'
   gg=[json.loads(x)for x in read(base+'core'+str(core)+'/games.jsonl').splitlines()];assert all(g in games for g in gg)
   close=json.loads(read(base+'core'+str(core)+'/close.json'));assert close['zero']and close['closed']['exit']['code']==0
  assert seen==set(rows);reg=json.loads(read(base+'registered-games.json'));out['registered_shape']=list(reg)if isinstance(reg,dict)else len(reg)
 out.update({'supported':True,'all_final_rows_joined':len(seen),'members':bound,'source_CP_root_labels_preserved':True})
except BaseException as e:
 import traceback;out.update({'supported':False,'first_difference':str(e),'trace':traceback.format_exc()})
out.update({'elapsed_seconds':time.monotonic()-st,'maxRSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'PID':os.getpid(),'end':datetime.datetime.now(datetime.timezone.utc).isoformat()});D.joinpath('raw-join.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out));assert out['supported']
