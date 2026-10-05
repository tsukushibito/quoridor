import subprocess,pathlib,json,time,datetime,os,hashlib
os.sched_setaffinity(0,{0}); D=pathlib.Path('research-data/ai-sigma/frame16-raw-cv-independent');started=time.monotonic();commands=[]
def run(args,data=None,limit=15):
 p=subprocess.run(args,input=data,capture_output=True,timeout=limit);commands.append({'command':args[:6],'exit':p.returncode,'stderr':p.stderr.decode()[:700]});assert p.returncode==0,(args[:6],p.stderr.decode()[:700]);return p.stdout
def commit(message):
 files=[p for p in D.iterdir() if p.is_file() and p.name!='save.log']+[pathlib.Path('docs/reports/ai-sigma-critic-raw-cv.md')];changes={}
 for p in files:
  name=str(p);assert not p.is_absolute() and name and all(s for s in name.split('/'));assert name.startswith(str(D)+'/') or name=='docs/reports/ai-sigma-critic-raw-cv.md';changes[name]=run(['git','hash-object','-w','--stdin'],p.read_bytes()).decode().strip()
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

if __name__=='__main__':
 intake=json.load(open(D/'intake.json'));idx=pathlib.Path(run(['git','rev-parse','--git-path','index']).decode().strip());current_index=hashlib.sha256(idx.read_bytes()).hexdigest();assert current_index==intake['index_SHA']
 source=[D/'check.py',D/'run.py'];process=json.load(open(D/'process.json'));q=pathlib.Path('/proc/'+str(process['PID']));absent=not q.exists() or (q/'stat').read_text().split()[21]!=process['tick'];assert absent and process['exit']==0
 marker=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_science_stopped=True,source_SHA={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in source},PID=process['PID'],tick=process['tick'],wait=True,current_exact_absent=absent,static_charge=120,cap=120,oldcaps={'217':180,'214':120,'212':120,'210':180},newNN=0,source_stop_scope=['check.py','run.py'],save_helper_management=True,science_after_stop=False,index_SHA=current_index)
 (D/'stop.json').write_text(json.dumps(marker,indent=2)+'\n')
 actual=sum(p.stat().st_size for p in D.iterdir()if p.is_file())+pathlib.Path('docs/reports/ai-sigma-critic-raw-cv.md').stat().st_size;forecast=actual+262144+65536+131072;assert forecast<716800
 (D/'storage-final-admission.json').write_text(json.dumps(dict(actual_scope=actual,uniqueGit_forecast=262144,temp_forecast=65536,metadata_forecast=131072,forecast=forecast,scope_guard=716800,new_reserve=1048576,old_undiscounted=115978724,total=117027300,guard=117440512,old_unknown_discount=0,parent_added=0),indent=2)+'\n')
 cid,files=commit('critic219: independently verify raw train-game CV and exposure; no validation promotion')
 for p in files:assert run(['git','show',cid+':'+str(p)])==p.read_bytes(),str(p)
 receipt=dict(commit=cid,files=len(files),byte_restore_PASS=True,index_before=current_index,index_after=hashlib.sha256(idx.read_bytes()).hexdigest(),defaultindex_changed=False,privateindex_used=False,source_child_stopped=True,management_wall=time.monotonic()-started,commands=commands)
 assert receipt['index_after']==current_index;(D/'Git-byte-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt[k]for k in ('commit','files','byte_restore_PASS','management_wall')}))
