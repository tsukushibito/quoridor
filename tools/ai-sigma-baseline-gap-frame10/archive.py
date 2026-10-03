"""Post-stop own-data pack; verify member SHA before rotating only self unused raw."""
import json,sys,hashlib,tarfile,datetime,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'.artifacts/ai-sigma/resume-20261003/BASELINE-GAP';runs=out/'runs';data=root/'research-data/ai-sigma/frame10-baseline-gap'
run=sys.argv[1];assert run.startswith('gap149-') and '/' not in run
process=json.loads((runs/(run+'.process.json')).read_text());assert not process['remaining'] and not process['unknown_adopted']
for x in [*process['tracked'],{'pid':process['runner_pid'],'start_ticks':process['runner_starttick']}]:
 try:s=Path(f"/proc/{x['pid']}/stat").read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:continue
 assert int(s[19])!=x['start_ticks'],'CURRENT_SAME_IDENTITY'
files=sorted([p for p in (runs/run).rglob('*') if p.is_file()]+[p for p in runs.glob(run+'.*') if p.is_file()]+[out/'configs'/(run+'.json')]);assert files
archive=data/(run+'.tar.gz');assert not archive.exists(),'ARCHIVE_ALREADY_EXISTS'
manifest={'issue':'quoridor-4lc.149','run':run,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'process_exit':process['exit'],'members':[],'archive':str(archive),'working_raw_rotation':'only own stopped unused run; no shared or prior experiment paths touched','claims':'restoration checks archive bytes, not independent science validation'}
with tarfile.open(archive,'w:gz',compresslevel=6) as t:
 for p in files:
  name=str(p.relative_to(out));b=p.read_bytes();manifest['members'].append({'member':name,'SHA256':hashlib.sha256(b).hexdigest(),'size':len(b)});t.add(p,arcname=name,recursive=False)
with tarfile.open(archive) as t:
 for row in manifest['members']:
  b=t.extractfile(row['member']).read();assert len(b)==row['size'] and hashlib.sha256(b).hexdigest()==row['SHA256'],'ARCHIVE_RESTORE'
manifest['archive_SHA256']=hashlib.sha256(archive.read_bytes()).hexdigest();manifest['stream_restore_all_members']=True
(data/(run+'.manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
result=runs/run/'browser-result.json'
if not result.exists():result=result.with_name('partial-browser-result.json')
if result.exists():
 d=json.loads(result.read_text());count={'issue':'quoridor-4lc.149','run':run,'started_games':d.get('started_games',0),'games':[{'id':g['id'],'status':g['status'],'reason':g['reason'],'winner':g['winner']} for g in d.get('games',[])],'result_member':str(result.relative_to(out)),'result_SHA256':hashlib.sha256(result.read_bytes()).hexdigest(),'archive':str(archive),'archive_SHA256':manifest['archive_SHA256']}
 (runs/(run+'.game-count.json')).write_text(json.dumps(count,indent=2)+'\n')
# Rotation is a separate post-Git action; preservation/restoration must precede removal.
print(json.dumps({'run':run,'members':len(files),'archive_bytes':archive.stat().st_size,'SHA256':manifest['archive_SHA256'],'stream_restored':True,'working_raw_removed':False}))
