import json,hashlib,tarfile,datetime,gzip,shutil,io
from pathlib import Path
R=Path('/workspaces/quoridor/.worktree/ai-sigma');O=R/'.artifacts/ai-sigma/resume-20261003/SIGMA-WEB-PORT';D=R/'research-data/ai-sigma/151-sigma-web-port';runs=O/'runs';manifest=[]
science=['port151-stageA-r1','port151-stageA-r2']+[f'port151-stageB-group{i}-r1' for i in range(1,5)]
def groupfiles(n):
 return [p for p in (runs/n).rglob('*') if p.is_file()]+[p for p in runs.glob(n+'.*') if p.is_file()]
groups=[(n,groupfiles(n)) for n in science];other=[]
for p in runs.rglob('*'):
 if not p.is_file() or any(p.is_relative_to(runs/n) or p.parent==runs and p.name.startswith(n+'.') for n in science):continue
 if any(x in ['t','xdg-cache','xdg-config'] for x in p.relative_to(runs).parts) or p.name.startswith('port151-pack-r1.'):continue
 other.append(p)
other += [p for p in O.glob('*') if p.is_file() and p.suffix in ['.json','.md']]
other += [p for p in (O/'build').glob('*') if p.is_file()]
other += [p for p in (O/'monitor-mock').glob('*') if p.is_file()]
groups.append(('control',other));restore=O/'restore-minimum';restore.mkdir(exist_ok=True)
for name,files in groups:
 archive=D/(name+'.tar.gz');members=[]
 with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
  for p in sorted(set(files)):
   namep=str(p.relative_to(O));b=p.read_bytes();members.append({'name':namep,'bytes':len(b),'SHA256':hashlib.sha256(b).hexdigest()});tar.add(p,arcname=namep,recursive=False)
 wanted=set()
 if name=='control':wanted={'build/faithful.wasm','build/build-binding.json'}
 else:
  wanted={f'runs/{name}/summary.json',f'runs/{name}/finally-model-drop.json',f'runs/{name}/pause-monitor-stop.json',f'runs/{name}.process.json'}
  if 'stageA' in name:wanted.add(f'runs/{name}/browser-result.json')
  else:
   games=[m['name'] for m in members if '/completed-game-' in m['name']];wanted.add(games[0])
 restored=[]
 with tarfile.open(archive,'r:gz') as tar:
  actual=tar.getmembers();assert [m.name for m in actual]==[m['name'] for m in members]
  for m,expected in zip(actual,members):
   stream=tar.extractfile(m);h=hashlib.sha256();size=0;dest=restore/name/m.name;f=None
   if m.name in wanted:dest.parent.mkdir(parents=True,exist_ok=True);f=dest.open('wb')
   while chunk:=stream.read(1048576):
    h.update(chunk);size+=len(chunk)
    if f:f.write(chunk)
   if f:f.close();assert hashlib.sha256(dest.read_bytes()).hexdigest()==expected['SHA256'];restored.append(m.name)
   assert size==expected['bytes'] and h.hexdigest()==expected['SHA256']
 manifest.append({'archive':str(archive.relative_to(R)),'bytes':archive.stat().st_size,'SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'member_count':len(members),'members':members,'all_members_SHA_size_stream_verified':True,'minimum_extracted_and_rehashed':restored,'runtime_expanded_source':str(O),'minimal_restore_path':str(restore/name)})
(D/'archive-manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.151','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archives':manifest,'not_all_source_models_or_targets_copied':True,'old_failure_and_all16_game_journals_preserved':True},indent=2)+'\n')
print(json.dumps({'archives':len(manifest),'members':sum(x['member_count'] for x in manifest),'compressed_bytes':sum(x['bytes'] for x in manifest),'all_stream_and_min_restore_verified':True}))
