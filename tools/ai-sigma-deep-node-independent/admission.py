import pathlib,json,os,datetime
R=pathlib.Path(__file__).resolve().parents[2];O=R/'.artifacts/ai-sigma/resume-20261002/DEEP-NODE-INDEPENDENT';heavy=[];errors=[];nonresearch=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  argv=(p/'cmdline').read_bytes().split(b'\0');exe=os.readlink(p/'exe')
  if pathlib.Path(exe).name in ['chrome','chromium','cargo','rustc'] and any(argv):heavy.append({'pid':int(p.name),'exe':exe,'argv':[a.decode(errors='replace') for a in argv]})
 except FileNotFoundError:pass
 except PermissionError as e:
  try:
   a=(p/'cmdline').read_bytes().split(b'\0');name=pathlib.Path(a[0].decode()).name if a[0] else ''
   if name in ['docker-init','sh','sshd:'] or name.startswith('sshd:'):nonresearch.append({'pid':int(p.name),'argv0':a[0].decode(),'exe_unreadable':True,'not_research_heavy_by_readable_argv':True})
   else:errors.append(str(e))
  except FileNotFoundError:pass
scopes=['CRITIC','INDEPENDENT','EVALUATION-PLAN'];tot=0;details=[];seen=set()
for parent in [R/'.artifacts/ai-sigma/continuation-20261001',R/'.artifacts/ai-sigma/resume-20261002']:
 for d in parent.iterdir():
  if not d.is_dir() or not any(n in d.name for n in scopes):continue
  size=0
  for p in d.rglob('*'):
   if p.is_file():
    s=p.stat();k=(s.st_dev,s.st_ino)
    if k not in seen:seen.add(k);size+=s.st_blocks*512
  tot+=size;details.append({'path':str(d.relative_to(R)),'allocated':size})
x={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'external_heavy':heavy,'readerrors':errors,'nonresearch_exe_unreadable':nonresearch,'critic_artifact_current_allocated':tot,'artifact_headroom_to112MiB':117440512-tot,'details':details,'MemAvailable':next(x for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable')),'parent_ledger':'research-data/ai-sigma/resource-ledger.json unchanged conservative envelope; old unknown not returned','reservation_new':0};(O/'admission.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ['external_heavy','readerrors','critic_artifact_current_allocated','artifact_headroom_to112MiB','MemAvailable']}));assert not heavy and not errors;assert tot<117440512
