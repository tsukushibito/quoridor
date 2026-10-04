"""Check own stable Git bytes and weights by memory restoration, no NN."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

D = Path('research-data/ai-sigma/frame14-head-control')
T = Path('tools/ai-sigma-qf1-head-control')
report = Path('docs/reports/ai-sigma-hypothesis-head-control.md')
commit = json.loads((D/'Git-scientific.json').read_text())['Git']
files = [p for p in D.rglob('*') if p.is_file() and 'jobs' not in p.parts
         and not p.name.startswith('Git-') and p.name != 'restore.json']
files += list(T.glob('*.py'))+[report]
checks = []
for path in files:
    raw = subprocess.check_output(['git','show',commit+':'+str(path)])
    assert raw == path.read_bytes(), str(path)
    checks.append({'path':str(path),'B':len(raw),'SHA':hashlib.sha256(raw).hexdigest()})
archive = subprocess.check_output(['git','show',commit+':'+str(D/'weights.tar.xz')])
members = json.loads((D/'weights-manifest.json').read_text())['members']
with tarfile.open(fileobj=io.BytesIO(archive), mode='r:xz') as src:
    for member in members:
        raw = src.extractfile(member['member']).read()
        assert len(raw)==member['B'] and hashlib.sha256(raw).hexdigest()==member['SHA']
receipt = {'Git':commit,'current_Git_bytes_PASS':True,'scientific_and_report_paths':checks,
           'archive_memory_restored_members':members,'no_disk_duplicate':True,'NN':0,
           'defaultindex_unchanged':json.loads((D/'Git-scientific.json').read_text())['index_unchanged']}
(D/'restore.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'Git':commit,'paths':len(checks),'PASS':True,'NN':0}))
