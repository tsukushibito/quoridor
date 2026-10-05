import os,sys,json,pathlib,time,datetime,subprocess,signal,hashlib
ROOT=pathlib.Path('/workspaces/quoridor'); BOOT=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
OUT=pathlib.Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
kind=sys.argv[2]; limit=float(sys.argv[3]); argv=sys.argv[4:]
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def proc(pid):
 try:
  p=pathlib.Path('/proc')/str(pid);s=(p/'stat').read_text().rsplit(')',1)[1].split();status=(p/'status').read_text();rss=int(status.split('VmRSS:')[1].split()[0])*1024 if 'VmRSS:' in status else 0
  return dict(pid=int(pid),ppid=int(s[1]),pgid=int(s[2]),tick=int(s[19]),cpu=int(s[11])+int(s[12]),rss=rss,argv=(p/'cmdline').read_bytes().decode(errors='replace').strip('\0').split('\0'),boot=BOOT)
 except (OSError,ValueError,IndexError):return None
def snapshot():return {int(p.name):v for p in pathlib.Path('/proc').iterdir() if p.name.isdigit() and (v:=proc(p.name))}
def ancestors(ps):
 ids={os.getpid()};cur=os.getpid()
 while cur in ps and ps[cur]['ppid'] not in ids:
  cur=ps[cur]['ppid'];ids.add(cur)
 return ids
def scientific(p):
 a=p['argv']; exe=pathlib.Path(a[0]).name if a else ''
 if exe in ('cargo','rustc','search_work','quoridor-runner','profile_native','measure_native'):return True
 if exe.startswith('python'):
  script=next((v for v in a[1:] if v.endswith('.py') and not v.startswith('-')), '')
  return bool(script and any(v in script for v in ('quoridor_training','frame21','ai-sigma','guard.py','model_cause')) and not any(v in script for v in ('research-scheduler','research-job','research-team')))
 return False
ps0=snapshot(); ownanc=ancestors(ps0);time.sleep(.25);ps1=snapshot()
foreign=[p for pid,p in ps1.items() if pid not in ownanc and scientific(p) and not (kind=='compile' and pathlib.Path(p['argv'][0]).name in ('cargo','rustc')) and pid in ps0 and p['tick']==ps0[pid]['tick'] and p['cpu']-ps0[pid]['cpu']>=2]
receipt=json.loads((ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame21/record-repair-loaded.json').read_text())
state=json.loads((ROOT/'.artifacts/research-team/frame21/scheduler/state.json').read_text())
storage=json.loads((ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame21/storage-current-admission.json').read_text())
mem={k:int(v.split()[0])*1024 for line in pathlib.Path('/proc/meminfo').read_text().splitlines() for k,v in [line.split(':',1)]}
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
admit=dict(at=stamp(),kind=kind,argv=argv,boot=BOOT,own_ancestors=sorted(ownanc),foreign_cpu=foreign,frame21_running_receipt=receipt,frame21_current_state=state,storage_at=storage['at'],storage_admission=storage['admission'],mem_available=mem['MemAvailable'],ORT_DISABLE_TELEMETRY=os.environ.get('ORT_DISABLE_TELEMETRY'),entry_sha=sha(argv[0]),physics_point_only=True)
expect=json.loads((ROOT/'.artifacts/ai-sigma/continuation-20261001/SIGMA-RESUME-OPERATIONS-92/frame21/expectations.json').read_text())
admit['current24']={path:sha(path)==wanted for path,wanted in expect['input_hashes'].items()}
admit['payload_sha']=sha(argv[3]) if len(argv)>3 and argv[0]=='/usr/bin/taskset' else None
admit['core_source_sha']=sha('/workspaces/quoridor/.worktree/frame21-search/crates/quoridor-core/src/position.rs')
# Loaded receipt identities are checked separately from active LLM ownership.
for field in ('process','monitor'):
 r=receipt.get(field)
 if isinstance(r,dict):
  pid=r.get('pid');actual=proc(pid) if pid else None;admit[field+'_current']=actual
  if not actual or actual['tick'] != int(r.get('start_ticks',r.get('start_tick',r.get('tick')))):
   admit['identity_error']=field
admit['current_loaded_hashes_match'] = (sha(state['binding']['config_path'])==state['config_sha256'] and sha(state['binding']['contract_file'])==state['contract_sha256'] and state['phase']=='running')
(OUT/'admission.json').write_text(json.dumps(admit,indent=2)+'\n')
if foreign or not all(admit['current24'].values()) or not admit['current_loaded_hashes_match'] or admit.get('identity_error') or storage['admission']!='within' or mem['MemAvailable']<4*1024**3:
 (OUT/'process.json').write_text(json.dumps(dict(status='NOT_STARTED_PHYSICS',at=stamp(),foreign=foreign),indent=2)+'\n');sys.exit(78)
start=time.monotonic();started=stamp(); identities={};peak=0;cause=None
with (OUT/'stdout.log').open('w') as out,(OUT/'stderr.log').open('w') as err:
 child=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True);ident=proc(child.pid)
 (OUT/'actual-start.json').write_text(json.dumps(dict(at=started,identity=ident,argv=argv),indent=2)+'\n')
 while child.poll() is None:
  ps=snapshot(); owned={p for p,v in ps.items() if v['pgid']==child.pid}; identities.update({p:ps[p] for p in owned});peak=max(peak,sum(ps[p]['rss'] for p in owned))
  if peak>int(1.75*1024**3):cause='RSS_GUARD'
  if time.monotonic()-start>limit:cause='WALL_GUARD'
  if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,10,5,10,28,tzinfo=datetime.timezone.utc):cause='FRAME_DEADLINE'
  foreign_now=[v for pid,v in ps.items() if pid not in ownanc and pid not in owned and scientific(v) and not (kind=='compile' and pathlib.Path(v['argv'][0]).name in ('cargo','rustc')) and pid in ps1 and v['tick']==ps1[pid]['tick'] and v['cpu']-ps1[pid]['cpu']>=2]
  if foreign_now:cause='FOREIGN_CPU'
  if cause:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL)
   break
  ps1=ps;time.sleep(.1)
 rc=child.wait()
remaining=[proc(p) for p,v in identities.items() if proc(p) and proc(p)['tick']==v['tick']]
(OUT/'process.json').write_text(json.dumps(dict(started=started,ended=stamp(),wall_seconds=time.monotonic()-start,exit_code=rc,cause=cause,peak_rss=peak,leader=ident,children=list(identities.values()),remaining=remaining,waited=True,current_exact_absent=not remaining,task='frame21-search-work-267-v2',kind=kind),indent=2)+'\n')
sys.exit(rc if rc>=0 else 1)
