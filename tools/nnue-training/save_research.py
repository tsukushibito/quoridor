"""Local files-only research Git save, in-memory trees; never an index."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zlib

D=Path('research-data/ai-sigma/frame14-learning')
T=Path('tools/nnue-training')
REPORT=Path('docs/reports/ai-sigma-hypothesis-frame14-learning.md')
DOC=Path('docs/development/nnue-training.md')
objects=set()


def git(*args,data=None):return subprocess.check_output(['git',*args],input=data)


def edit_tree(old,changes):
    entries={}
    if old:
        for entry in git('ls-tree','-z',old).split(b'\0'):
            if not entry:continue
            header,name=entry.split(b'\t',1);mode,kind,oid=header.split(b' ')
            entries[name.decode()]=(mode,kind,oid)
    grouped={}
    for parts,oid in changes:grouped.setdefault(parts[0],[]).append((parts[1:],oid))
    for name,items in grouped.items():
        if len(items)==1 and not items[0][0]:entries[name]=(b'100644',b'blob',items[0][1].encode())
        else:
            prior=entries.get(name)
            assert prior is None or prior[1]==b'tree'
            oid=edit_tree(prior[2].decode() if prior else None,items)
            entries[name]=(b'040000',b'tree',oid.encode())
    raw=b''.join(mode+b' '+kind+b' '+oid+b'\t'+name.encode()+b'\0' for name,(mode,kind,oid) in entries.items())
    tree=git('mktree','-z',data=raw).decode().strip();objects.add(tree);return tree


def save(phase):
    files=[p for base in(T,D) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [p for p in(DOC,REPORT) if p.exists()]
    index=Path(git('rev-parse','--git-path','index').decode().strip());index_sha=hashlib.sha256(index.read_bytes()).hexdigest()
    changes=[]
    for p in files:
        oid=git('hash-object','-w','--',str(p)).decode().strip();objects.add(oid);changes.append((p.parts,oid))
    for attempt in range(3):
        parent=git('rev-parse','HEAD').decode().strip();tree=edit_tree(git('rev-parse',parent+'^{tree}').decode().strip(),changes)
        commit=git('commit-tree',tree,'-p',parent,'-m','research: frame14 QF1 learning '+phase).decode().strip();objects.add(commit)
        if subprocess.run(['git','update-ref','HEAD',commit,parent],capture_output=True).returncode==0:break
    else:raise RuntimeError('bounded HEAD CAS failed')
    assert hashlib.sha256(index.read_bytes()).hexdigest()==index_sha
    j={'phase':phase,'Git':commit,'parent':parent,'tree':tree,'objects':sorted(objects),'files':len(files),'index_unchanged':True,'privateindex':0,'experimental_weights_in_Git':False}
    (D/('Git-'+phase+'.json')).write_text(json.dumps(j,indent=2)+'\n');print(json.dumps({k:v for k,v in j.items() if k!='objects'}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase');save(p.parse_args().phase)
