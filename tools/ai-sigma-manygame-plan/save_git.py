"""Save owned paths as a local Git commit without reading/writing any index."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

D=Path('research-data/ai-sigma/183-manygame-gpu-plan')
T=Path('tools/ai-sigma-manygame-plan')
R=Path('docs/reports/ai-sigma-hypothesis-manygame-gpu-plan.md')
objects=set()

def git(args, data=None):
    p=subprocess.run(['git']+args,input=data,capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode())
    return p.stdout

def edit_tree(old, changes):
    entries={}
    if old:
        for item in git(['ls-tree','-z',old]).split(b'\0'):
            if not item: continue
            header,name=item.split(b'\t',1); mode,kind,oid=header.split(b' ')
            entries[name.decode()]=(mode,kind,oid)
    grouped={}
    for parts,blob in changes:
        grouped.setdefault(parts[0],[]).append((parts[1:],blob))
    for name,items in grouped.items():
        if len(items)==1 and not items[0][0]:
            entries[name]=(b'100644',b'blob',items[0][1].encode())
        else:
            previous=entries.get(name)
            assert previous is None or previous[1]==b'tree'
            child=edit_tree(previous[2].decode() if previous else None,items)
            entries[name]=(b'040000',b'tree',child.encode())
    data=b''.join(mode+b' '+kind+b' '+oid+b'\t'+name.encode()+b'\0' for name,(mode,kind,oid) in entries.items())
    tree=git(['mktree','-z'],data).decode().strip();objects.add(tree);return tree

def main():
    assert sys.argv[1] in ('source','final','metadata')
    files=[p for base in (T,D) for p in base.rglob('*') if p.is_file() and p.name!='private.index' and '__pycache__' not in p.parts]
    if R.exists(): files.append(R)
    index=Path(git(['rev-parse','--git-path','index']).decode().strip())
    index_sha=hashlib.sha256(index.read_bytes()).hexdigest()
    changes=[]
    for p in files:
        oid=git(['hash-object','-w','--',str(p)]).decode().strip();objects.add(oid); changes.append((p.parts,oid))
    for attempt in range(3):
        parent=git(['rev-parse','HEAD']).decode().strip()
        root=git(['rev-parse',parent+'^{tree}']).decode().strip()
        tree=edit_tree(root,changes)
        commit=git(['commit-tree',tree,'-p',parent,'-m','research: Sigma manygame NN0 plan '+sys.argv[1]]).decode().strip();objects.add(commit)
        p=subprocess.run(['git','update-ref','HEAD',commit,parent],capture_output=True)
        if p.returncode==0: break
    else: raise RuntimeError('shared HEAD changed on all bounded attempts')
    assert hashlib.sha256(index.read_bytes()).hexdigest()==index_sha
    gitdir=Path(git(['rev-parse','--git-common-dir']).decode().strip())
    retained=sum((gitdir/'objects'/oid[:2]/oid[2:]).stat().st_size for oid in objects if (gitdir/'objects'/oid[:2]/oid[2:]).exists())
    out={'phase':sys.argv[1],'Git':commit,'parent':parent,'tree':tree,'default_index_unchanged':True,'new_private_index':False,'referenced_loose_object_bytes_including_reused':retained,'objects':sorted(objects),'owned_files':len(files)}
    (D/('Git-'+sys.argv[1]+'.json')).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='objects'}))

if __name__=='__main__': main()
