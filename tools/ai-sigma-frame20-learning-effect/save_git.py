"""Batched authorized subtree save, no disk/default index; verify saved blob bytes."""
import subprocess,sys
from pathlib import Path
def run(args,body=None):return subprocess.check_output(['git',*args],input=body).strip()
files=sys.argv[1:]
for f in files:assert f.startswith(('tools/ai-sigma-frame20-learning-effect/','research-data/ai-sigma/frame20-learning-effect/','docs/reports/ai-sigma-experiment-frame20-learning-effect.md'))
blobs=run(['hash-object','-w','--stdin-paths'],(''.join(f+'\n'for f in files)).encode()).splitlines();assert len(files)==len(blobs)
updates={}
for f,h in zip(files,blobs):
 d=updates
 for p in f.split('/')[:-1]:d=d.setdefault(p,{})
 d[f.split('/')[-1]]=h
empty=run(['mktree'],b'')
def update(tree,changes):
 items={}
 for x in run(['ls-tree','-z',tree]).split(b'\0'):
  if not x:continue
  meta,name=x.split(b'\t',1);mode,typ,h=meta.split(b' ');items[name]=(mode,typ,h)
 for name,change in changes.items():
  n=name.encode()
  if isinstance(change,dict):
   mode,typ,child=items.get(n,(b'040000',b'tree',empty));assert typ==b'tree';items[n]=(b'040000',b'tree',update(child.decode(),change))
  else:items[n]=(b'100644',b'blob',change)
 data=b''.join(m+b' '+t+b' '+h+b'\t'+n+b'\0'for n,(m,t,h)in items.items());return run(['mktree','-z'],data)
for attempt in range(5):
 base=run(['rev-parse','HEAD']).decode();root=run(['rev-parse',base+'^{tree}']).decode()
 tree=update(root,updates).decode()
 parents=['-p',base]
 # PreNN syntax version created during a concurrent HEAD CAS is retained.
 # No failed management-source parent exists for 256.
 commit=run(['commit-tree',tree,*parents],b'research(256): save one-root finite diagnosis and retained failed source\n').decode()
 result=subprocess.run(['git','update-ref','HEAD',commit,base],capture_output=True)
 if result.returncode==0:break
 if attempt==4:raise RuntimeError(result.stderr.decode())
data=subprocess.check_output(['git','cat-file','--batch'],input=b''.join(h+b'\n'for h in blobs));pos=0
for f,h in zip(files,blobs):
 e=data.index(b'\n',pos);header=data[pos:e].split();assert header[0]==h and header[1]==b'blob';size=int(header[2]);b=data[e+1:e+1+size];assert b==Path(f).read_bytes();pos=e+1+size+1
print(commit)
