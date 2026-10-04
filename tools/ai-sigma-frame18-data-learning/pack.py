"""Stop-first owned raw archive, streaming member verification and Git byte save."""
from pathlib import Path
import argparse,datetime,hashlib,json,subprocess,tarfile,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('config');a=p.parse_args()
c=json.loads(Path(a.config).read_text());O=Path(c['job_out']);st=time.monotonic()
assert O.is_relative_to(D)
pr=json.loads((O/'process.json').read_text());assert pr['current_exact_absent']and pr['all_child_waited']
assert (O/'summary.json').exists()and(O/'metadata.jsonl.gz').exists()and(O/'labels.jsonl.gz').exists()
members=[q for q in O.rglob('*')if q.is_file()and (q.suffix=='.jsonl'or q.name in['stdout.txt'])]
archive=O/'raw-evidence.tar.gz';assert not archive.exists()
manifest={str(q.relative_to(O)):{'SHA':sha(q),'B':q.stat().st_size}for q in members}
with tarfile.open(archive,'w:gz',compresslevel=6)as t:
    for q in members:t.add(q,arcname=str(q.relative_to(O)),recursive=False)
with tarfile.open(archive,'r:gz')as t:
    seen=set()
    for m in t:
        assert m.isfile()and m.name in manifest
        h=hashlib.sha256();f=t.extractfile(m)
        while b:=f.read(1024*1024):h.update(b)
        assert h.hexdigest()==manifest[m.name]['SHA']and m.size==manifest[m.name]['B'];seen.add(m.name)
assert seen==set(manifest)
receipt={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(archive.relative_to(R)),
 'archive_SHA':sha(archive),'archive_B':archive.stat().st_size,'members':manifest,'member_byte_restore_PASS':True,
 'process_SHA':sha(O/'process.json'),'reader_export_stopped':True,'source_reference':c['source_git']}
(O/'raw-archive.json').write_text(json.dumps(receipt,indent=2)+'\n')
files=[str(q.relative_to(R))for q in O.iterdir()if q.is_file()and q.name not in['stdout.txt']]
commit=subprocess.check_output(['/usr/bin/python3','-B',str(R/'tools/ai-sigma-frame18-data-learning/save_git.py'),*files],text=True).strip()
# Every file being removed is this owner's stopped raw member; canonical/effective data remain.
for q in members:q.unlink()
receipt.update(Git=commit,raw_owned_duplicate_removed_B=sum(v['B']for v in manifest.values()),
               pack_Git_restore_cleanup_wall_s=time.monotonic()-st,old_scopes_removed_B=0)
(O/'pack-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k]for k in['Git','archive_B','raw_owned_duplicate_removed_B','pack_Git_restore_cleanup_wall_s']}))
