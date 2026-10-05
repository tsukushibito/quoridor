"""Archive necessary run controls and failed-check logs, then verify every file."""
import json,hashlib,tarfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/COOPERATIVE-ARENA'
DATA=ROOT/'research-data/ai-sigma/103-cooperative-arena'
active_job=os.environ.get('SIGMA_DUMMY_RUN_ID','')
files=sorted(p for p in OUT.iterdir() if p.is_file() and not (active_job and p.name.startswith(active_job+'.')))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
archive=DATA/'run-controls.tar.gz'
assert not archive.exists()
with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
 for p in files:tf.add(p,arcname=p.name,recursive=False)
with tarfile.open(archive) as tf:
 restored={m.name:hashlib.sha256(tf.extractfile(m).read()).hexdigest() for m in tf if m.isfile()}
assert manifest==restored
result={'archive':str(archive.relative_to(ROOT)),'SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'restored_files':len(manifest),'restored_hashes':manifest,'includes_failed_checks':True,'includes_PID_command_resource_evidence':True,'live_control_files_retained':True}
(DATA/'run-controls-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['archive','SHA256','bytes','restored_files']}))
