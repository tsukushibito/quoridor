from pathlib import Path
import tarfile,gzip,json,hashlib,datetime,subprocess,io,os
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.artifacts/ai-sigma/resume-20261002/TAIL-TRANSPORT';DEST=ROOT/'research-data/ai-sigma/97-tail-transport';DEST.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Inputs are three fixed goldens, not the match/holdout pool.
fpath=ROOT/'.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json';rpath=ROOT/'.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json';ids=['initial-p1','asym-hv-p2','straight-jump-p2']
(OUT/'fixed-input-references.json').write_text(json.dumps({'fixtures':[r for r in json.loads(fpath.read_text())['fixtures']if r['id']in ids],'fixed_ORT_outputs':[r for r in json.loads(rpath.read_text())if r['id']in ids],'original_fixture_path':str(fpath),'original_fixture_sha256':sha(fpath),'original_ORT_reference_path':str(rpath),'original_ORT_reference_sha256':sha(rpath)},indent=2)+'\n')
files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.relative_to(OUT).parts[0]not in ['t','xdg-cache','xdg-config'])
archive=DEST/'runs-and-evidence.tar.gz';contents=[]
with archive.open('wb')as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,compresslevel=1)as zipped,tarfile.open(fileobj=zipped,mode='w|')as tar:
 for p in files:
  name=str(p.relative_to(OUT));info=tar.gettarinfo(str(p),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
  with p.open('rb')as f:tar.addfile(info,f)
  contents.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
expected={x['path']:x for x in contents};restored=[]
with tarfile.open(archive,'r:gz')as tar:
 for member in tar:
  assert member.isfile();data=tar.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==expected[member.name]['sha256'];assert len(data)==expected[member.name]['bytes'];restored.append(member.name)
assert set(restored)==set(expected)
for n in ['primary-config','preregister-factor','primary-analysis','runtime-source-stopped-before-report','fixed-input-references']:(DEST/(n+'.json')).write_bytes((OUT/(n+'.json')).read_bytes())
code=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
manifest={'issue':'quoridor-4lc.97','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime_code_git':'83bb0ce4ea55b210f1657913ab2d6f2fa728eac5','analysis_report_git':code,'run':'clock-factor-primary-r1','run_command_reference':'nn-primary-r1.started.json','archive':'runs-and-evidence.tar.gz','archive_sha256':sha(archive),'compressed_bytes':archive.stat().st_size,'uncompressed_bytes':sum(x['bytes']for x in contents),'files':contents,'restore_to':'.artifacts/ai-sigma/resume-20261002/TAIL-TRANSPORT/','restore_command':'tar -xzf research-data/ai-sigma/97-tail-transport/runs-and-evidence.tar.gz -C <new-output-directory>','restoration_content_sha256_checked':len(restored),'excluded_reproducible_TEMP_cache':True,'original_live_output_retained_for_reader':True,'all_success_failure_runs_retained':True,'phaseA_uncommitted_source_limit':'initial preflight r1 lacked game/context VM imports; inputs hash/log preserved, no exact initial preflight Git version. R2 import correction/R3 normal budget adapter test saved separately. NN primary exact Git bound.','no_model_dependency_copies':True,'formal_fairness':False,'actual_go':False}
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(OUT/'archive-preserved.json').write_text(json.dumps({k:v for k,v in manifest.items()if k!='files'},indent=2)+'\n')
print(json.dumps({'archive_bytes':manifest['compressed_bytes'],'restored_files':len(restored),'uncompressed_bytes':manifest['uncompressed_bytes'],'analysis_report_git':code}))
