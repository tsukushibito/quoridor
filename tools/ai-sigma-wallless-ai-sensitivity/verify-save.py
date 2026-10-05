from pathlib import Path
import json,subprocess,hashlib,tarfile,io,os,datetime
R=Path(__file__).resolve().parents[2];D=R/'research-data/ai-sigma/144-wallless-ai-sensitivity';O=R/'.artifacts/ai-sigma/resume-20261002/WALLLESS-AI-SENSITIVITY'
version=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();paths=subprocess.check_output(['git','-C',str(R),'ls-tree','-r','--name-only',version,'--','tools/ai-sigma-wallless-ai-sensitivity','research-data/ai-sigma/144-wallless-ai-sensitivity','docs/reports/ai-sigma-experiment-wallless-ai-sensitivity.md'],text=True).splitlines();checks=[]
for p in paths:
 raw=subprocess.check_output(['git','-C',str(R),'show',version+':'+p]);assert raw==(R/p).read_bytes(),p;checks.append({'path':p,'SHA256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
raw=subprocess.check_output(['git','-C',str(R),'show',version+':research-data/ai-sigma/144-wallless-ai-sensitivity/runs.tar.gz']);m=json.loads((D/'archive-manifest.json').read_text());assert hashlib.sha256(raw).hexdigest()==m['SHA256']
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
 for x in m['members']:
  b=tar.extractfile(x['member']).read();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['SHA256']
pid=os.getpid();s=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split();x={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data_report_Git':version,'all_Git_current_exact':True,'Git_files':checks,'archive_SHA256':m['SHA256'],'archive_members_restored':len(m['members']),'restore':'Git stream to memory, each archive member hashed; no source/model full copy','helper_identity':{'pid':pid,'start_ticks':int(s[19])},'helper_current_RSS':int(s[21])*4096,'source_hash_after':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'tools/ai-sigma-wallless-ai-sensitivity').glob('*') if p.is_file()},'scientific_source_stopped_before_report':True,'no_more_NN':True};(O/'git-restore-check.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'Git':version,'files':len(checks),'members':len(m['members'])}))
