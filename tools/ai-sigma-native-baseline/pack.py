"""Finite local raw preservation/readback; never starts NN or deletes originals."""
import json,hashlib,tarfile,time,datetime,os
from pathlib import Path
R=Path(__file__).resolve().parents[2];A=R/'.artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE';D=R/'research-data/ai-sigma/165-native-baseline';T=R/'tools/ai-sigma-native-baseline'
start=time.monotonic();members=[]
for p in sorted(A.rglob('*')):
 if not p.is_file() or 'build' in p.relative_to(A).parts or 'finite-restore' in p.relative_to(A).parts:continue
 members.append({'name':str(p.relative_to(A)),'bytes':p.stat().st_size,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()})
archive=D/'native165-raw.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
 for m in members:tar.add(A/m['name'],arcname=m['name'],recursive=False)
assert archive.stat().st_size<8*1024**2,'ARCHIVE_FORECAST'
restore=A/'finite-restore';restore.mkdir(exist_ok=True);chosen={'runs/native165-pair01-r1/control-summary.json','runs/native165-control-repair-r1/result.json','runs/native165-mechanism-r1/pause-monitor-stop.json'};actual=[]
with tarfile.open(archive,'r:gz') as tar:
 for m in members:
  body=tar.extractfile(m['name']).read();assert len(body)==m['bytes'];assert hashlib.sha256(body).hexdigest()==m['SHA256']
  if m['name'] in chosen:
   dest=restore/Path(m['name']).name;dest.write_bytes(body);assert hashlib.sha256(dest.read_bytes()).hexdigest()==m['SHA256'];actual.append({'member':m['name'],'restored_path':str(dest.relative_to(R)),'SHA256':m['SHA256']})
manifest={'issue':'quoridor-4lc.165','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(archive.relative_to(R)),'archive_bytes':archive.stat().st_size,'archive_SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'original_raw_retained':True,'members':members,'all_members_roundtrip_SHA256_verified':True,'finite_extraction_verified':actual,'source_refs':{'StageA':'a09279c','StageB':['19275b3','e6b42a3','f63e8b3'],'NN0_control_repair':'a78ea8336edc84c9716fee8972c86d94200941b6'},'code_dependencies':['dependency-binding.json','source-binding.json','model-binding-current.json','control-repair-binding-before-run.json'],'reproduction':'Archive paths are relative to .artifacts/ai-sigma/resume-20261003/NATIVE-BASELINE. Source and configuration version are the per-run started/process command and git_commit. Rebuild private native crate with recorded compiler, offline locked cached Cargo and jobs1. Existing external Cargo/Python ORT environments and original shared model are required and not reconstructed by Git alone. Restoring records does not authorize rerunning original successful science. New-adapter runtime validation requires separate allocation/preregistration.','wall_s':time.monotonic()-start,'NN':0,'scope_bytes_and_unused_forecast_within_existing_experiment_2GiB_not_new_parent_reservation':True}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ['archive_bytes','archive_SHA256','wall_s']}));print('members',len(members),'finite_extract',len(actual))
