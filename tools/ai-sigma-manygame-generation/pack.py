"""Archive necessary stopped 187 evidence, verify every member; do not delete live/old copies."""
from pathlib import Path
import gzip,hashlib,io,json,tarfile,time
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/187-manygame-generation';A=ROOT/'.artifacts/ai-sigma/resume-20261003/MANYGAME-GENERATION';start=time.perf_counter();members={}
for p in sorted(A.rglob('*')):
 if not p.is_file():continue
 # Only this scope's private stopped artifacts. Raw allturns/partials/failedsource receipts retained.
 name=str(p.relative_to(ROOT));members[name]={'SHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
archive=D/'all-attempt-evidence.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
 for name in members:tar.add(ROOT/name,arcname=name,recursive=False)
with tarfile.open(archive,'r:gz')as tar:
 found={}
 for item in tar.getmembers():
  b=tar.extractfile(item).read();found[item.name]={'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
assert found==members
manifest={'issue':'quoridor-4lc.187','archive':'research-data/ai-sigma/187-manygame-generation/'+archive.name,'archiveSHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_bytes':archive.stat().st_size,'members':members,'all_member_SHA_verified':True,'extract_base':str(ROOT),'live_source_not_deleted':True,'model_dependency_binary_shared_reference_only':True,'pack_wall_s':time.perf_counter()-start}
(D/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items()if k!='members'}))
