import subprocess,pathlib,json,time,datetime,os,hashlib
os.sched_setaffinity(0,{0}); D=pathlib.Path('research-data/ai-sigma/frame15-learning-diagnostic-independent');started=time.monotonic();commands=[]
def run(args,data=None,limit=15):
 p=subprocess.run(args,input=data,capture_output=True,timeout=limit);commands.append({'command':args[:6],'exit':p.returncode,'stderr':p.stderr.decode()[:700]});assert p.returncode==0,(args[:6],p.stderr.decode()[:700]);return p.stdout
def commit(message):
 files=[p for p in D.iterdir() if p.is_file() and p.name!='save.log']+[pathlib.Path('docs/reports/ai-sigma-critic-learning-diagnostic.md')];changes={}
 for p in files:
  name=str(p);assert not p.is_absolute() and name and all(s for s in name.split('/'));assert name.startswith(str(D)+'/') or name=='docs/reports/ai-sigma-critic-learning-diagnostic.md';changes[name]=run(['git','hash-object','-w','--stdin'],p.read_bytes()).decode().strip()
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

