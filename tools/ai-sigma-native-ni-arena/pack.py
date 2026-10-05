"""Post-stop compact archive and byte restoration check; no process execution."""
from pathlib import Path
import os,json,tarfile,hashlib,datetime
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'.artifacts/ai-sigma/resume-20261003/NATIVE-NI-ARENA';D=ROOT/'research-data/ai-sigma/173-native-ni-arena';T=ROOT/'tools/ai-sigma-native-ni-arena'
def size(p):return sum(f.lstat().st_blocks*512 for f in p.rglob('*') if f.is_file() or f.is_symlink())
def sha(b):return hashlib.sha256(b).hexdigest()
for p in (A/'runs').glob('*.process.json'):
 x=json.loads(p.read_text());assert not x['remaining'] and not x['unknown_adopted'],'OWN_NOT_STOPPED'
 for i in x['tracked']+[{'pid':x['runner_pid'],'start_ticks':x['runner_starttick']}]:
  try:s=Path('/proc/'+str(i['pid'])+'/stat').read_text().rsplit(')',1)[1].split()
  except FileNotFoundError:continue
  assert int(s[19])!=i['start_ticks'],'CURRENT_IDENTITY_PRESENT'
archive=D/'all-attempt-records.tar.gz';assert not archive.exists(),'PACK_ALREADY_EXISTS'
files=sorted(p for p in A.rglob('*') if p.is_file() and not p.is_symlink());current=size(A)+size(D)+size(T)
# Conservative uncompressed archive plus Git duplicate and small metadata headroom.
forecast=sum(p.stat().st_size for p in files)*2+32*1024*1024
assert current+forecast<448*1024*1024,'SAVE_FORECAST_GUARD'
members={str(p.relative_to(A)):{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in files}
with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(A)),recursive=False)
with tarfile.open(archive,'r:gz')as tar:
 assert set(tar.getnames())==set(members),'PACK_MEMBER_SET'
 for name,m in members.items():
  b=tar.extractfile(name).read();assert len(b)==m['bytes'] and sha(b)==m['sha256'],'PACK_RESTORE_BYTES'
manifest={'issue':'quoridor-4lc.173','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(archive.relative_to(ROOT)),
 'archive_SHA256':sha(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'all_member_byte_restoration_verified':True,'member_count':len(members),'members':members,
 'original_artifacts_retained':True,'old_evidence_deleted':False,'model_binary_dependencies':'read-only binding.json; no model or dependency copies',
 'restore_into':'.artifacts/ai-sigma/resume-20261003/NATIVE-NI-ARENA-RESTORE (create only for consumer need)',
 'source_restore':'local research Git versions in source-freeze/preregister and runner .inputs records',
 'prewrite_current_allocated':current,'prewrite_conservative_archive_Git_forecast':forecast,'current_plus_forecast_guard':448*1024*1024,'new_parent_reservation':0,
 'private_index':'in-memory subtree only; existing shared index untouched'}
(D/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:manifest[k]for k in ['archive_bytes','member_count','all_member_byte_restoration_verified','prewrite_current_allocated','prewrite_conservative_archive_Git_forecast']}))
