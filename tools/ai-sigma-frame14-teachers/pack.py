"""Preserve stopped194 evidence; test raw remains in its own sealed archive."""
from pathlib import Path
import hashlib,json,tarfile,time
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/frame14-teachers';A=ROOT/'.artifacts/ai-sigma/frame14-teachers';start=time.monotonic()
for p in A.rglob('process.json'):assert not json.loads(p.read_text())['remaining'],'CHILD_NOT_REAPED'
groups={'unsealed':{},'test-sealed':{}}
for p in sorted(A.rglob('*')):
    if not p.is_file():continue
    key='test-sealed' if 'test-sealed' in p.relative_to(A).parts else 'unsealed'
    groups[key][str(p.relative_to(ROOT))]={'SHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
archives={}
for key,members in groups.items():
    archive=D/('test-sealed/test-evidence.tar.gz' if key=='test-sealed' else 'all-attempt-evidence.tar.gz')
    with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
        for name in members:tar.add(ROOT/name,arcname=name,recursive=False)
    with tarfile.open(archive,'r:gz')as tar:
        restored={}
        for item in tar.getmembers():
            b=tar.extractfile(item).read();restored[item.name]={'SHA256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
    assert restored==members
    archives[key]={'path':str(archive.relative_to(ROOT)),'SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'members':members,'all_member_SHA_restore':True}
manifest={'issue':'quoridor-4lc.194','archives':archives,'test_raw_remains_sealed':True,'test_targets_analyzed':False,'extract_base':str(ROOT),'old_or_live_data_deleted':False,'pack_wall_s':time.monotonic()-start}
(D/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'archives':{k:{p:v[p]for p in ['path','SHA256','bytes']}for k,v in archives.items()},'wall_s':manifest['pack_wall_s']}))
