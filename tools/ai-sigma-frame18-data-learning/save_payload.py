"""Stream only current learning payload; retain generation packs and source versions."""
from pathlib import Path
import datetime,hashlib,json,tarfile,time
R=Path.cwd();D=R/'research-data/ai-sigma/frame18-data-learning';T=R/'tools/ai-sigma-frame18-data-learning';start=time.monotonic()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=D/'learning-evidence-v1.tar.gz';assert not out.exists()
current=sum(p.stat().st_size for r in[D,T]for p in r.rglob('*')if p.is_file())
forecast=current+128*1024**2+32*1024**2+16*1024**2
assert forecast<448*1024**2
files=[]
for sub in ['learning-runs','learning-checkpoints','learning-plan-v1','learning-guardian','test-evaluation-r1']:
 files +=[p for p in(D/sub).rglob('*')if p.is_file()]
files += [D/n for n in ['candidate-freeze-v1.json','scientific-final-stop.json','learning-test-summary.json','learning-test-curves.png','learning-test-curves.svg','protected-artifact-manifest.json','test-settings-r1.json']]
members={str(p.relative_to(D)):{'SHA':sha(p),'B':p.stat().st_size}for p in files}
with tarfile.open(out,'w:gz',compresslevel=1)as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(D)),recursive=False)
with tarfile.open(out,'r:gz')as tar:
 assert set(tar.getnames())==set(members)
 for member in tar:
  f=tar.extractfile(member);h=hashlib.sha256();size=0
  while b:=f.read(1024*1024):h.update(b);size+=len(b)
  assert h.hexdigest()==members[member.name]['SHA']and size==members[member.name]['B']
receipt={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(out.resolve()),'archive_SHA':sha(out),'archive_B':out.stat().st_size,'members':members,'member_bytes_restore_PASS':True,'generation_packs':'14 unchanged packs: existing pack-receipt.json restoration/Git evidence reused; no re-copy','scope_before_B':current,'forecast_including_Git_temp_and_archive_B':forecast,'guard_B':448*1024**2,'reservation_B':512*1024**2,'management_wall_s':time.monotonic()-start,'old_scope_discount_B':0,'parent_added_B':0,'original_source_deleted':False}
(D/'learning-payload-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k]for k in ['archive_B','management_wall_s','member_bytes_restore_PASS','scope_before_B','forecast_including_Git_temp_and_archive_B']}))
