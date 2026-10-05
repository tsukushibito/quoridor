import json,hashlib,tarfile,time,io,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[2];A=R/'.artifacts/ai-sigma/resume-20261003/NATIVE-RUNTIME-READY';D=R/'research-data/ai-sigma/170-native-runtime-ready';T=R/'tools/ai-sigma-native-runtime-ready';start=time.monotonic();members=[];buf=io.BytesIO()
for p in sorted(A.rglob('*')):
 if p.is_file() and 'finite-restore' not in p.relative_to(A).parts:members.append({'name':str(p.relative_to(A)),'bytes':p.stat().st_size,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()})
with tarfile.open(fileobj=buf,mode='w:gz',compresslevel=9) as tar:
 for m in members:tar.add(A/m['name'],arcname=m['name'],recursive=False)
blob=buf.getvalue();current=sum(p.stat().st_blocks*512 for base in [A,D,T] for p in base.rglob('*') if p.is_file());assert current+2*len(blob)+131072+65536<7340032,'PACK_AND_GIT_FORECAST_GUARD'
archive=D/'native170-raw.tar.gz';archive.write_bytes(blob);chosen={'runs/native170-solo-r1/control-summary.json','runs/native170-parallel-r1/pause-monitor-stop.json','runs/native170-mock-r1/result.json'};restore=A/'finite-restore';restore.mkdir(exist_ok=True);actual=[]
with tarfile.open(archive,'r:gz') as tar:
 for m in members:
  b=tar.extractfile(m['name']).read();assert hashlib.sha256(b).hexdigest()==m['SHA256'] and len(b)==m['bytes']
  if m['name'] in chosen:
   p=restore/(m['name'].split('/')[1]+'-'+Path(m['name']).name);p.write_bytes(b);assert hashlib.sha256(p.read_bytes()).hexdigest()==m['SHA256'];actual.append({'member':m['name'],'restore':str(p.relative_to(R)),'SHA256':m['SHA256']})
x={'issue':'quoridor-4lc.170','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(archive.relative_to(R)),'archive_bytes':len(blob),'archive_SHA256':hashlib.sha256(blob).hexdigest(),'members':members,'all_member_roundtrip_verified':True,'finite_extraction_verified':actual,'current_before_pack':current,'Git_and_privateindex_forecast_bytes':len(blob)+131072,'guard':7340032,'preserved_original_final_results':True,'temporary_progress_reconstructible':'progress-retention.json /progress-cleanup.json, metadata Gitcac3f6eb','readonly165_source_dependency':'binding.json and stopped a78ea833, binary166dd0c4/shared ONNX d790/provider1.30 external cached environment','source':{'firstNN0':'0e4c9899','science':'bd7ffde0d46f51ec35d8faa4091f526c95ccc914'},'reproduction':'Archive members relative to .artifacts/ai-sigma/resume-20261003/NATIVE-RUNTIME-READY. Each started/process records exact command/version/input/config/affinity; original dependencies retained readonly. Restoring does not authorize replacing completed scientific requests; new measurement requires next allocation/preregistration. Progress snapshots can be byte-recreated from retained result.rows and saved group_start_ms under original Node JSON formatter.','wall_s':time.monotonic()-start,'NN':0,'new_Git_only_full_environment_claim':False}
(D/'manifest.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ['archive_bytes','archive_SHA256','current_before_pack','wall_s']}));print('members',len(members))
