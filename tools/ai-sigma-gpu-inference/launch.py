"""Owned bounded wait/admission and one model child; no torch import in manager."""
import os,json,time,signal,subprocess,hashlib,datetime,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'research-data/ai-sigma/174-gpu-inference';T=Path(__file__).resolve().parent
S=Path('/workspaces/quoridor/.artifacts/research-team/scheduler-sigma-continuation-20261001/state.json')
REG=json.loads((D/'preregister.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
SELF=os.getpid();SELF_TICK=Path(f'/proc/{SELF}/stat').read_text().rsplit(')',1)[1].split()[19]
interrupt=False
signal.signal(signal.SIGTERM,lambda *_:globals().__setitem__('interrupt',True))
signal.signal(signal.SIGINT,lambda *_:globals().__setitem__('interrupt',True))

def identity(pid):
    try:
        s=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split();return {'pid':pid,'starttick':s[19],'ppid':int(s[1]),'pgid':int(s[2]),'RSS':int(s[21])*os.sysconf('SC_PAGE_SIZE'),'state':s[0]}
    except FileNotFoundError:return None

def proc_snapshot():
    ancestors={SELF};pid=SELF
    while pid>1:
        x=identity(pid)
        if not x:break
        pid=x['ppid'];ancestors.add(pid)
    rows=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) in ancestors:continue
        try:
            a=(p/'cmdline').read_bytes().replace(b'\0',b' '); x=identity(int(p.name))
            if not x or x['state']=='Z':continue
            if b'ai-sigma-' in a or b'research-team' in a or b'research-scheduler' in a:
                x['cmd']=a.decode(errors='replace')[:500];x['affinity']=sorted(os.sched_getaffinity(x['pid']));rows.append(x)
        except (FileNotFoundError,ProcessLookupError):pass
    return rows

def admit():
    now=time.time();assert now<REG['newheavy_cutoff_epoch'] and now+150<REG['science_deadline_epoch'],'DEADLINE'
    st=json.loads(S.read_text());cfg=Path(st['config_path']);assert st['phase']=='running' and not st['recovery_required'],'SCHEDULER_NOT_CURRENT'
    assert st['owned'] is None,'SUPERVISOR_OWNED'
    proc=st['process'];live=identity(proc['pid']);assert live and live['starttick']==str(proc['start_ticks']) and proc['boot_id']==boot,'SCHEDULER_IDENTITY'
    assert hashlib.sha256(cfg.read_bytes()).hexdigest()==st['config_sha256'],'SCHEDULER_CONFIG_BINDING'
    assert float(st['next_at'])-now>=150,'SUPERVISOR_WINDOW'
    rows=proc_snapshot()
    assert not any('NATIVE-NI-ARENA' in r['cmd'] or 'ai-sigma-native-ni-arena' in r['cmd'] for r in rows),'173_CURRENT_JOB'
    # Wait for a stopped-science handoff so 173 cannot start its next block during this job.
    stop_path=ROOT/'research-data/ai-sigma/173-native-ni-arena/science-stop.json'
    assert stop_path.exists(),'173_STOP_HANDOFF_PENDING'
    stop=json.loads(stop_path.read_text());assert stop.get('scientific_source_write_stopped') or stop.get('scientific_source_stopped') or stop.get('science_stopped'),'173_STOP_FLAG_PENDING'
    assert not any(stop.get(k) for k in ('current_same_identity','outer_remaining','unknown_adopted','remaining')),'173_NOT_COLLECTED'
    code=(ROOT/'tools/ai-sigma-native-ni-arena/runner.py').read_text();assert "'quality':4294967296" in code and "'quality':4831838208" in code,'173_RAM_ADJUSTMENT_PENDING'
    assert not any('supervisor' in r['cmd'] and r['pid']!=proc['pid'] for r in rows),'SUPERVISOR_CURRENT_UNKNOWN'
    known_other=sum(r['RSS'] for r in rows)
    assert known_other+2147483648+1073741824+536870912<8589934592,'PARENT_RAM'
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    assert available>2147483648+268435456,'PHYSICAL_RAM'
    q=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.free,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5);assert q.returncode==0,'GPU_HEADROOM_QUERY'
    cols=[x.strip() for x in q.stdout.strip().split(',')];assert len(cols)==4 and int(cols[2])*1024**2>=REG['VRAM_guard_B'],'GPU_HEADROOM'
    c=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5);assert c.returncode==0,'GPU_OWNER_QUERY'
    assert not c.stdout.strip(),'GPU_OTHER_COMPUTE_OWNER'
    for id in ('quoridor-4lc','quoridor-4lc.174'):
        p=subprocess.run(['bash',str(ROOT/'scripts/dev/beads.sh'),'show',id,'--json'],capture_output=True,text=True,timeout=8);assert p.returncode==0,'CONTROL_READ'
        o=json.loads(p.stdout)[0];assert o['status']=='in_progress' and not any('pause' in s for s in o.get('labels',[])),'CONTROL_PAUSE'
        if id.endswith('.174'):assert o['assignee']=='codex:01a0f31c-2e4b-7170-82c5-69e1428c2418','OWNER'
    prior=json.loads((D/'source-binding.json').read_text())
    for p,h in prior['source_hashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'SOURCE_CHANGED'
    current=sum(p.stat().st_size for base in (D,T) for p in base.rglob('*') if p.is_file())
    assert current+131072<262144,'STORAGE_FORECAST'
    assert 14596875+json.loads((D/'intake.json').read_text())['171_retained_conservative_B']+262144<15728640,'COMBINED_STORAGE'
    return {'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scheduler_next':st['next_at'],'scheduler_owned':None,'scheduler_identity':live,'173_stop_sha256':hashlib.sha256(stop_path.read_bytes()).hexdigest(),'selected_current':rows,'selected_RSS_sum_B':known_other,'MemAvailable_B':available,'GPU':q.stdout.strip(),'GPU_compute_owners':c.stdout.strip(),'CPU':[0],'RAM_guard_B':REG['RAM_guard_B'],'newheavy_cutoff':REG['newheavy_cutoff_epoch']}

result={'manager_pid':SELF,'manager_starttick':SELF_TICK,'boot_id':boot,'wait_start_epoch':time.time(),'waiting':True,'attempts':[],'model_jobs_started':0}
(D/'manager-current.json').write_text(json.dumps(result,indent=2)+'\n')
last_reason=None
while not interrupt and time.time()<REG['newheavy_cutoff_epoch']:
    try:a=admit();break
    except (AssertionError,OSError,ValueError,subprocess.TimeoutExpired) as e:
        reason=str(e)
        if reason!=last_reason:
            result['attempts'].append({'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'admission_deferred':reason});last_reason=reason
            (D/'manager-current.json').write_text(json.dumps(result,indent=2)+'\n');print('DEFERRED '+reason,flush=True)
        time.sleep(20)
else:
    result.update(waiting=False,model_jobs_started=0,end_epoch=time.time(),stop_reason='INTERRUPTED' if interrupt else 'NO_ADMISSIBLE_WINDOW',owned_wait_remaining=[])
    (D/'manager-stop.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);sys.exit(0)
(D/'admission.json').write_text(json.dumps(a,indent=2)+'\n')
launch=time.time();assert launch<REG['newheavy_cutoff_epoch'] and launch+150<REG['science_deadline_epoch']
for n in ('tmp','xdg-cache','xdg-config'):(D/n).mkdir(exist_ok=True)
env=os.environ.copy();env.update(UV_NO_SYNC='1',UV_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',BLIS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='0',CUDA_CACHE_DISABLE='1',TMPDIR=str(D/'tmp'),XDG_CACHE_HOME=str(D/'xdg-cache'),XDG_CONFIG_HOME=str(D/'xdg-config'))
cmd=['taskset','-c','0','/home/vscode/.cache/inference/envs/quoridor-training/bin/python','-B',str(T/'measure.py')]
log=(D/'run.stdout').open('w');err=(D/'run.stderr').open('w')
child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=err,start_new_session=True);ci=identity(child.pid);assert ci is not None
result.update(waiting=False,model_jobs_started=1,launch_epoch=launch,hard_deadline_epoch=launch+120,command=cmd,child_identity=ci)
(D/'manager-current.json').write_text(json.dumps(result,indent=2)+'\n');print('MODEL_JOB_STARTED '+str(child.pid),flush=True)
peak=0;why=None;tracked={};last_control=time.time()
while child.poll() is None:
    x=identity(child.pid);selfi=identity(SELF);rss=(x['RSS'] if x else 0)+(selfi['RSS'] if selfi else 0);peak=max(peak,rss)
    if x:tracked[(x['pid'],x['starttick'])]=x
    if interrupt:why='USER_OR_MANAGER_STOP'
    elif time.time()>=launch+120:why='JOB_HARD120'
    elif rss>=REG['RAM_guard_B']:why='RSS_GUARD'
    elif time.time()>=REG['science_deadline_epoch']:why='SCIENCE_DEADLINE'
    elif any('NATIVE-NI-ARENA' in r['cmd'] or 'ai-sigma-native-ni-arena' in r['cmd'] for r in proc_snapshot()):why='173_NEW_CURRENT_JOB'
    st=json.loads(S.read_text())
    if st['owned'] is not None:why='SUPERVISOR_NEW_OWNED'
    if time.time()-last_control>10:
        last_control=time.time()
        for id in ('quoridor-4lc','quoridor-4lc.174'):
            p=subprocess.run(['bash',str(ROOT/'scripts/dev/beads.sh'),'show',id,'--json'],capture_output=True,text=True,timeout=6)
            if p.returncode:why='CONTROL_READ_UNKNOWN';break
            o=json.loads(p.stdout)[0]
            if o['status']!='in_progress' or any('pause' in s for s in o.get('labels',[])):why='CONTROL_PAUSE';break
    if why:
        os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=3)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
        break
    time.sleep(.05)
child.wait(timeout=3);log.close();err.close()
result.update(end_epoch=time.time(),exit=child.returncode,stop_reason=why,peak_child_plus_manager_RSS_B=peak,tracked=list(tracked.values()),owned_wait_remaining=[],current_child_exact_identity_present=bool(identity(child.pid) and identity(child.pid)['starttick']==ci['starttick']),model_job_elapsed_s=time.time()-launch)
(D/'manager-stop.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('exit','stop_reason','model_job_elapsed_s','peak_child_plus_manager_RSS_B','current_child_exact_identity_present')}),flush=True)
