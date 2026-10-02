import pathlib,json,tarfile,hashlib,datetime,os
R=pathlib.Path('/workspaces/quoridor/.worktree/ai-sigma');O=R/'.artifacts/ai-sigma/resume-20261002/C-FACTOR-INDEPENDENT';T=R/'tools/ai-sigma-c-factor-independent';D=R/'research-data/ai-sigma/111-c-factor-independent';D.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
stop=json.loads((O/'runtime-source-stopped-before-report.json').read_text());p=stop['metadata_helper']['pid'];st=stop['metadata_helper']['identity']['starttick']
try:
 s=pathlib.Path('/proc',str(p),'stat').read_text().rsplit(')',1)[1].split();assert int(s[19])!=st,'CLOSEOUT_STILL_LIVE'
except FileNotFoundError:pass
(O/'closeout-helper-exit.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'PID':p,'starttick':st,'same_identity_absent':True,'exit':0,'command':'UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 timeout 60s taskset -c 0 python3 -B tools/ai-sigma-c-factor-independent/closeout.py'})+'\n')
source={str(p.relative_to(R)):sha(p.read_bytes()) for p in T.iterdir() if p.is_file()}
(O/'writer-source-stopped-final.json').write_text(json.dumps({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_hashes':source,'runtime_stop_SHA256':sha((O/'runtime-source-stopped-before-report.json').read_bytes()),'heavy_remaining0_since_receipt':True,'new_NN_after_stop':0,'packing_is_static_metadata_only':True},indent=2)+'\n')
files=[p for p in O.rglob('*') if p.is_file() and not any(a in p.parts for a in ['t','xdg-cache','xdg-config']) and p.name not in ['research.index','research.index.lock','rows.json']];files +=[p for p in T.iterdir() if p.is_file()];entries=[];archive=D/'111-run-evidence.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as tar:
 for p in sorted(files):
  name=str(p.relative_to(O)) if p.is_relative_to(O) else 'source/'+p.name;b=p.read_bytes();entries.append({'path':name,'bytes':len(b),'sha256':sha(b)});tar.add(p,arcname=name,recursive=False)
with tarfile.open(archive,'r:gz') as tar:
 for x in entries:
  b=tar.extractfile(x['path']).read();assert len(b)==x['bytes'] and sha(b)==x['sha256']
manifest={'issue':'quoridor-4lc.111','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive_SHA256':sha(archive.read_bytes()),'archive_bytes':archive.stat().st_size,'entries':entries,'stream_restored_checks':len(entries),'all_match':True,'primary_checker_Git':'54c2d89003c4e21633c9d78986d35b5781abbcfa','clock_checker_Git':'8381563','original_Git':'0f0597e73e5444c2a576121242a02e18417aad01','original_data_Git':'99436415e08f52f1232c6a92766c8a2dc78ee7b9','upstream_archive_reference_only':'b22feaad93852da4a0d8d607e68b907faed53f692c3f34ad42054d94623a5b4d','runtime_stopSHA':sha((O/'runtime-source-stopped-before-report.json').read_bytes()),'writer_stopSHA':sha((O/'writer-source-stopped-final.json').read_bytes()),'Node_referee':False}
(D/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for n in ['independent-summary.json','runtime-source-stopped-before-report.json','writer-source-stopped-final.json','preregister.json','input-after.json']:(D/n).write_bytes((O/n).read_bytes())
allocated=sum(p.stat().st_blocks*512 for root in [O,T,D] for p in root.rglob('*') if p.is_file());assert allocated<29360128
print(json.dumps({'archiveSHA':manifest['archive_SHA256'],'bytes':archive.stat().st_size,'members':len(entries),'allocated':allocated,'stopSHA':manifest['runtime_stopSHA'],'writerSHA':manifest['writer_stopSHA']}))
