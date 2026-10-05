"""Necessary stopped scientific evidence, one streaming pack, member byte restore."""
from pathlib import Path
import tarfile,hashlib,json,time
R=Path.cwd();T=R/'tools/ai-sigma-worker-balance';D=R/'research-data/ai-sigma/frame18-worker-balance';start=time.monotonic()
excluded={'pack.tar.gz','pack-members.json','pack-receipt.json','git-save-receipt.json','final-storage.json'}
files=sorted(p for root in[T,D] for p in root.rglob('*') if p.is_file() and p.name not in excluded)
members={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with tarfile.open(D/'pack.tar.gz','w:gz',compresslevel=1) as a:
 for p in files:a.add(p,arcname=str(p.relative_to(R)),recursive=False)
with tarfile.open(D/'pack.tar.gz','r:gz') as a:
 for m in a.getmembers():
  if m.isfile():
   h=hashlib.sha256(a.extractfile(m).read()).hexdigest()
   assert h==members[m.name]
(D/'pack-members.json').write_text(json.dumps(members,indent=2)+'\n')
p=D/'pack.tar.gz'
receipt=dict(archive_SHA=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,members=len(members),all_member_byte_restore_PASS=True,wall_s=time.monotonic()-start,raw_not_deleted=True)
(D/'pack-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
