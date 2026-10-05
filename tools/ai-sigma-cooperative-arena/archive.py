"""Preserve one completed run, verify restored bytes, then trim live duplicates."""
import json,hashlib,tarfile,sys,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA'
DATA=ROOT/'research-data/ai-sigma/103-cooperative-arena'
DATA.mkdir(parents=True,exist_ok=True)
run=sys.argv[1]
base=OUT/run
assert json.loads((base/'summary.json').read_text())['secondary']==[]
assert json.loads((base/'backend-stop.json').read_text())['controlledPID0']
files=sorted(p for p in base.rglob('*') if p.is_file())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest={str(p.relative_to(OUT)):sha(p) for p in files}
archive=DATA/(run+'.tar.gz')
assert not archive.exists()
with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
 for p in files:tf.add(p,arcname=str(p.relative_to(OUT)),recursive=False)
restored={}
with tarfile.open(archive,'r:gz') as tf:
 for member in tf:
  assert member.isfile()
  restored[member.name]=hashlib.sha256(tf.extractfile(member).read()).hexdigest()
assert restored==manifest
# Keep the minimal analysis and stop controls accessible; full responses remain in verified archive.
keep={'summary.json','analysis.json','config.json','ready.json','backend-stop.json','pause-monitor-stop.json'}
removed=[]
for p in files:
 if p.parent==base and p.name in keep:continue
 if sha(p)!=manifest[str(p.relative_to(OUT))]:raise RuntimeError('INPUT_CHANGED_DURING_ARCHIVE')
 removed.append(str(p.relative_to(OUT)))
 p.unlink()
for p in sorted(base.rglob('*'),key=lambda p:len(p.parts),reverse=True):
 if p.is_dir() and not any(p.iterdir()):p.rmdir()
result={'issue':'quoridor-4lc.103','run':run,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(archive.relative_to(ROOT)),'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'restored_files':len(restored),'restored_hashes':manifest,'live_duplicate_removed_paths':removed,'runtime_stopped_before_archive':True,'restoration':'tarfile streamed every file; hash equality; no whole duplicate extraction'}
(DATA/(run+'.archive-manifest.json')).write_text(json.dumps(result,indent=2)+'\n')
for name in keep:
 p=base/name
 if p.exists():(DATA/(run+'-'+name)).write_bytes(p.read_bytes())
print(json.dumps({k:result[k] for k in ['run','archive','archive_sha256','bytes','restored_files']}))
