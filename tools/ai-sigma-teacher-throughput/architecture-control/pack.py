"""Stream only new221 owned evidence into a small replayable archive."""
from pathlib import Path
import datetime,hashlib,json,tarfile,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame16-teacher-throughput/architecture-control';start=time.monotonic();names=[]
for p in(D/'jobs').rglob('*'):
 if p.is_file():names.append(p)
# New evidence only. Never duplicate legacy sources/models/raw or a previous pack.
for p in D.glob('*-teacher-rows.jsonl.gz'):names.append(p)
for p in D.glob('*-all-status.json'):names.append(p)
archive=D/'graph-evidence-r1.tar.gz';assert not archive.exists(),'ARCHIVE_ALREADY_EXISTS'
members=[]
with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
 for p in sorted(names):
  n=str(p.relative_to(D));tar.add(p,arcname=n,recursive=False);members.append(dict(member=n,B=p.stat().st_size,SHA=hashlib.sha256(p.read_bytes()).hexdigest()))
with tarfile.open(archive,'r:gz')as tar:
 for m in members:
  b=tar.extractfile(m['member']).read();assert len(b)==m['B']and hashlib.sha256(b).hexdigest()==m['SHA']
manifest=dict(UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive=str(archive.relative_to(R)),archive_B=archive.stat().st_size,archive_SHA=hashlib.sha256(archive.read_bytes()).hexdigest(),members=members,byte_restore_PASS=True,wall_s=time.monotonic()-start,includes='new221 jobs/raw/qualification records only',old_source_model_copy=False,raw_retention='owned stopped raw kept in place until accepted; no fullraw extra copy outside archive')
(D/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items()if k!='members'}))
