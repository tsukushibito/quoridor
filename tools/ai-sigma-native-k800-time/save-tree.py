"""Save only authorized small handoff files without a full on-disk Git index."""
import subprocess,sys,json
from pathlib import Path
def run(args,body=None):return subprocess.check_output(['git',*args],input=body).strip()
def entries(oid):
 result={}
 for x in run(['ls-tree','-z',oid]).split(b'\0'):
  if not x:continue
  meta,name=x.split(b'\t',1);mode,typ,h=meta.split(b' ');result[name]=(mode,typ,h)
 return result
def update(tree,parts,blob):
 items=entries(tree);name=parts[0].encode()
 if len(parts)==1:items[name]=(b'100644',b'blob',blob)
 else:
  mode,typ,child=items.get(name,(b'040000',b'tree',run(['mktree'],b'')));assert typ==b'tree';items[name]=(mode,typ,update(child.decode(),parts[1:],blob))
 data=b''.join(m+b' '+t+b' '+h+b'\t'+n+b'\0' for n,(m,t,h) in items.items());return run(['mktree','-z'],data)
base=run(['rev-parse','HEAD']).decode();tree=run(['rev-parse',base+'^{tree}']).decode()
for filename in sys.argv[1:]:
 assert filename.startswith(('tools/ai-sigma-native-k800-time/','research-data/ai-sigma/180-native-k800-time/','docs/reports/ai-sigma-experiment-native-k800-time.md'))
 blob=run(['hash-object','-w','--stdin'],Path(filename).read_bytes());tree=update(tree,filename.split('/'),blob).decode()
commit=run(['commit-tree',tree,'-p',base],b'research(180): save native teacher pipeline source and finite evidence\n').decode();subprocess.run(['git','update-ref','HEAD',commit,base],check=True)
for filename in sys.argv[1:]:assert run(['show',commit+':'+filename])+b'\n'==Path(filename).read_bytes() or subprocess.check_output(['git','show',commit+':'+filename])==Path(filename).read_bytes()
print(commit)
