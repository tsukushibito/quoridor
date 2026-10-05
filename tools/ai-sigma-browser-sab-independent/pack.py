import pathlib,json,tarfile,hashlib,io,datetime,os
R=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');O=R/'.artifacts/ai-sigma/resume-20261002/BROWSER-SAB-INDEPENDENT';T=R/'tools/ai-sigma-browser-sab-independent';D=R/'research-data/ai-sigma/109-browser-sab-independent';D.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
stop=json.loads((O/'runtime-source-stopped-before-report.json').read_text());pid=stop['metadata_helper']['pid'];assert not pathlib.Path('/proc',str(pid)).exists(),'METADATA_HELPER_NOT_EXITED'
(O/'closeout-helper-exit.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':pid,'exit':0,'current_absent':True,'command':'UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 60s taskset -c 0 python3 -B tools/ai-sigma-browser-sab-independent/closeout.py'})+'\n')
files=[p for p in O.rglob('*') if p.is_file() and '/runs/t/' not in str(p) and p.name!='rows.json'];files+=list(p for p in T.iterdir() if p.is_file());entries=[]
archive=D/'109-run-evidence.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
 for p in sorted(files):
  b=p.read_bytes();name=str(p.relative_to(O)) if p.is_relative_to(O) else 'source/'+p.name;entries.append({'path':name,'bytes':len(b),'sha256':sha(b)});tar.add(p,arcname=name,recursive=False)
with tarfile.open(archive,'r:gz') as tar:
 for row in entries:
  b=tar.extractfile(row['path']).read();assert len(b)==row['bytes'] and sha(b)==row['sha256']
(D/'archive-manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.109','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_SHA256':sha(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'entries':entries,'restored_member_hashes_match':len(entries),'upstream_archive_reference_only':{'Git':'181ea3932d270a9f0e69145b57577b411ecbab62','SHA256':'a65f1194a61ef64907956110e86cf9eaf3d35aef3e11dd560680eaa7fdf6593a'},'browser_adjudication_evidence':'runs/109-functional-r3/independent-saved-browser-analysis.json','runtime_stop_SHA256':sha((O/'runtime-source-stopped-before-report.json').read_bytes())},indent=2)+'\n')
for n in ['independent-summary.json','runtime-source-stopped-before-report.json']:(D/n).write_bytes((O/n).read_bytes())
allocated=sum(p.stat().st_blocks*512 for root in [O,T,D] for p in root.rglob('*') if p.is_file());assert allocated<14680064
print(json.dumps({'bytes':archive.stat().st_size,'SHA256':sha(archive.read_bytes()),'members':len(entries),'allocated_total':allocated}))
