"""99.1 bounded NN0 preservation; no source/model/cache copying or deletion."""
import os,sys,json,time,pathlib,tarfile,hashlib,shutil,resource,datetime
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'research-data/ai-sigma';RUN=OUT/'retention-99'
DEADLINE=datetime.datetime.fromisoformat('2026-10-02T03:43:05+00:00')
SKIP={'target','build','node_modules','.venv','venv','__pycache__','t','tmp','temp','xdg-cache','xdg-config','browser-cache','browser-config','cache','profile','browser-profile','src','crates','apps','packages','tests','source','source-copy','snapshot','copy','job-source','canonical-source','upstream','dist','.git'}
SUFFIX={'.json','.jsonl','.csv','.tsv','.txt','.log','.md','.patch','.diff','.stdout','.stderr'}
OPS=('SCHEDULER','SUPERVISOR','READ-GUARD','READ-GUARD','CRITICAL-ROLES','DEADLINE','EXPERIMENT-POLICY','CONTRACT-IMPROVEMENT','RESUME-OPERATIONS')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def guard():
 assert datetime.datetime.now(datetime.timezone.utc)<DEADLINE,'processing deadline'
 rss=int(pathlib.Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE');assert rss<896*1024**2,'current RSS guard'
 assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<240*1024**2,'archive allocation guard (Git/temporary headroom reserved)'
def chosen(base):
 for b,ds,fs in os.walk(base,followlinks=False):
  ds[:]=sorted(d for d in ds if d not in SKIP and 'source' not in d.lower() and not pathlib.Path(b,d).is_symlink())
  for name in sorted(fs):
   p=pathlib.Path(b,name)
   if not p.is_symlink() and p.suffix in SUFFIX and name not in {'package.json','package-lock.json','tsconfig.json','registry.json'}:yield p
if __name__=='__main__':
 start=now();pid=os.getpid();tick=pathlib.Path('/proc/self/stat').read_text().split(') ')[1].split()[19];records=[]
 groups=[('resume-20261002','DIAGNOSTIC-ARENA'),('resume-20261002','DIAGNOSTIC-ARENA-INDEPENDENT')]
 for group in ['runs','verification','analysis','continuation-20261001']:
  for p in sorted((ROOT/'.artifacts/ai-sigma'/group).iterdir()):
   if p.is_dir() and not p.is_symlink() and (group!='continuation-20261001' or (p.name.startswith(('SIGMA-','CRITIC-')) and not any(x in p.name for x in OPS))):groups.append((group,p.name))
 for group,name in groups:
  guard();base=ROOT/'.artifacts/ai-sigma'/group/name;fs=list(chosen(base))
  if not fs:continue
  dest=OUT/'archives'/group;dest.mkdir(parents=True,exist_ok=True);archive=dest/(name+'.tar.gz')
  with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
   for p in fs:guard();tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
  sha=hashlib.sha256(archive.read_bytes()).hexdigest();records.append({'source':str(base.relative_to(ROOT)),'archive':str(archive.relative_to(ROOT)),'files':len(fs),'logical_bytes':sum(p.stat().st_size for p in fs),'archive_bytes':archive.stat().st_size,'sha256':sha,'representative':str(fs[0].relative_to(ROOT))})
  print(name,len(fs),archive.stat().st_size,flush=True)
 for name,files in [('DIAGNOSTIC-ARENA',['handoff-compact.json','measurement-environment.json','numeric-denominators.json']),('DIAGNOSTIC-ARENA-INDEPENDENT',['handoff-summary.json','preregister.json','clock-arithmetic.json','source-git-check.json'])]:
  dest=OUT/'summaries'/name;dest.mkdir(parents=True,exist_ok=True)
  for filename in files:shutil.copyfile(ROOT/'.artifacts/ai-sigma/resume-20261002'/name/filename,dest/filename)
 (RUN/'manifest.json').write_text(json.dumps({'issue':'quoridor-4lc.99.1','created':now(),'archives':records,'selection':{'extensions':sorted(SUFFIX),'excluded_directories':sorted(SKIP),'excluded_source_subtrees':True,'symlinks_followed':False},'restore':'git show <data-commit>:<archive> | tar -xz -C /workspaces/quoridor/.worktree/ai-sigma (stop writers/readers before overwriting)','shared_inputs':['models/experiments/ai-sigma/reference/sigma-pcr250/best.onnx','.artifacts/ai-sigma/runs/SIGMA-ORT-SEARCH/final.wasm','.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/ORT','.artifacts/ai-sigma/reference-fixtures/SIGMA-PARITY-PLAN/fixtures.json','.artifacts/ai-sigma/runs/SIGMA-INFERENCE-PROBE/ort-a.outputs.json'],'source_references':{'93':['dca3588570c293cb1883456901f4fa3f25a9ad4b','9496cae','132ec12','812a9e4'],'95':'a57e402de3dab717592ac6e853d236c47694d56a','legacy':'archived input/manifest/config/hash/command logs identify versions; untracked source snapshots retained in original workspace'},'unchanged_outcomes':'diagnostic/verification only; old failures/results preserved; no new formal NI or strength conclusion','protected':['resume-20261002/TAIL-TRANSPORT','continuation-20261001/scheduler','continuation-20261001/SIGMA-RESUME-OPERATIONS-92','all unGit sources','shared dependencies/models/DB'],'raw_copies':'93/95 retain while experiment97 references; other old raw retained until readers confirmed'},ensure_ascii=False,indent=2)+'\n')
 usage=resource.getrusage(resource.RUSAGE_SELF);(RUN/'archive-job.json').write_text(json.dumps({'pid':pid,'starttick':tick,'start':start,'end':now(),'affinity':sorted(os.sched_getaffinity(0)),'user_s':usage.ru_utime,'system_s':usage.ru_stime,'peak_rss_bytes':usage.ru_maxrss*1024,'exit':0,'archives':len(records),'archive_bytes':sum(x['archive_bytes'] for x in records)},indent=2)+'\n')
