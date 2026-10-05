"""Guard current owned recovery, physical heavy jobs and forecast before spawn."""
import datetime
import json
import os
from pathlib import Path
import importlib.util
import time
import hashlib
source=Path(__file__).resolve().parent.parent/'ai-sigma-diverse-prefix/admission.py'
spec=importlib.util.spec_from_file_location('readonly119admission',source)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def infrastructure_metadata(uid,argv):
    if not argv:return False
    command=argv[0]
    if uid==0 and command in ['/sbin/docker-init','/bin/sh','sleep']:
        return True
    return command.startswith('sshd: ') and ('[listener]' in command or '[priv]' in command or '@notty' in command)

def physical_heavy_scan():
    start=time.monotonic();heavy=[];metadata=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        if time.monotonic()-start>3:raise RuntimeError('ADMISSION_READ_TIMEOUT')
        try:
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            argv=[x.decode('utf8') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            if fields[0]=='Z':continue
            if not argv:raise RuntimeError('LIVE_COMMAND_UNKNOWN')
            uid=int(next(x.split()[1] for x in (p/'status').read_text().splitlines() if x.startswith('Uid:')))
            try:executable=os.readlink(p/'exe')
            except PermissionError:
                if not infrastructure_metadata(uid,argv):raise RuntimeError('EXECUTABLE_OWNER_UNKNOWN')
                metadata.append({'pid':int(p.name),'ppid':int(fields[1]),'start_ticks':int(fields[19]),'uid':uid,'command':argv[0],'argv_SHA256':hashlib.sha256(json.dumps(argv).encode()).hexdigest(),'reason':'recognized container/SSH infrastructure; executable read permission unavailable, outside owned research compute scope'})
                continue
            record={'pid':int(p.name),'ppid':int(fields[1]),'start_ticks':int(fields[19]),'state':fields[0],'exe':executable,'argv':argv[1:]}
            if not base.classify_process(record):continue
            if Path(executable).name.startswith('python') and os.sched_getaffinity(record['pid'])=={0}:continue
            heavy.append(record)
        except (FileNotFoundError,ProcessLookupError):
            if p.exists():raise RuntimeError('PROCESS_READ_UNKNOWN')
        except Exception as error:raise RuntimeError('ADMISSION_READ_ERROR '+p.name+' '+type(error).__name__) from error
    return heavy,metadata

def admit(config,out,tool,runs):
    previous=[json.loads(p.read_text()) for p in runs.glob('quality134-*.process.json')]
    base.decide([],previous)
    heavy=[];metadata=[]
    if config['kind']!='protocol':
        heavy,metadata=physical_heavy_scan()
        base.decide(heavy,previous)
        stop_path=Path(config['dependency_stop'])
        if not stop_path.is_file():raise RuntimeError('DEPENDENCY133_STOP_NOT_RECEIVED')
        if hashlib.sha256(stop_path.read_bytes()).hexdigest()!=config['dependency_stop_SHA256']:raise RuntimeError('DEPENDENCY133_STOP_SHA')
        stop=json.loads(stop_path.read_text())
        if stop.get('issue')!='quoridor-4lc.133' or not stop.get('source_write_stopped') or any(job['remaining'] or job['unknown_adopted'] for job in stop.get('jobs',[stop.get('job',{})])):raise RuntimeError('DEPENDENCY133_STOP_UNCONFIRMED')
        if stop['Model2_drop']['handles'] or stop['Model2_drop']['activeNN'] or stop['main_timers']['main_timers'] or stop['main_timers']['pending_messages']:raise RuntimeError('DEPENDENCY133_MODEL_TIMER_NOT_ZERO')
        if stop['boot']!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():raise RuntimeError('DEPENDENCY_BOOT')
        same=[]
        identities=json.loads(Path(config['dependency_identities']).read_text())
        for reference in identities['process_refs']:
            if hashlib.sha256(Path(reference['path']).read_bytes()).hexdigest()!=reference['SHA256']:raise RuntimeError('DEPENDENCY_PROCESS_CHANGED')
        for identity in identities['identities']:
            path=Path('/proc')/str(identity['pid'])/'stat'
            try: fields=path.read_text().rsplit(')',1)[1].split()
            except FileNotFoundError:continue
            if int(fields[19])==identity['start_ticks']:same.append(identity)
        if same:raise RuntimeError('DEPENDENCY133_STILL_OWNED')
        memory={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemFree:'))}
        if memory['MemAvailable']<6442450944:raise RuntimeError('PHYSICAL_RAM_HEADROOM')
        previous_started=[json.loads(p.read_text()) for p in runs.glob('quality134-*.started.json')]
        previous_result=[]
        for prior in previous_started:
            prior_config=json.loads(Path(prior['command'][-1]).read_text()) if prior['command'][-2]=='--config' else None
            if prior_config is None:continue
            if prior_config['kind']=='protocol':continue
            result_path=runs/prior_config['run_id']/'browser-result.json'
            if not result_path.is_file():raise RuntimeError('PREVIOUS_STARTED_GAME_COUNT_UNKNOWN')
            previous_result.append(json.loads(result_path.read_text()))
        if sum(x['started_games'] for x in previous_result)+len(config['games'])>8:raise RuntimeError('ROLLOUT_START_CAP')
        if sum(sum(bool(r['spec'].get('functional')) for r in x['rows']) for x in previous_result)+(2 if config.get('connection') else 0)>2:raise RuntimeError('FUNCTION_START_CAP')
    current=sum(p.stat().st_blocks*512 for folder in [out,tool,tool.parents[1]/'research-data/ai-sigma/134-local-move-quality'] for p in folder.rglob('*') if p.is_file())
    forecast=0 if config['kind']=='protocol' else config['forecast_bytes']
    if current+forecast>=117440512:raise RuntimeError('STORAGE_HEADROOM')
    now=datetime.datetime.now(datetime.timezone.utc)
    if now>=datetime.datetime.fromisoformat(config['newjob_deadline']):raise RuntimeError('NEWJOB_DEADLINE')
    heavy_used=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in previous if x['phase']!='protocol')
    if config['kind']!='protocol' and heavy_used+config['minimum_remaining_heavy_seconds']>1800:raise RuntimeError('HEAVY_BUDGET')
    return {'UTC':now.isoformat(),'external_heavy':heavy,'recognized_infrastructure_metadata':metadata,'whole_host_no_load_not_proved':True,'prior_remaining_unknown':0,'current_allocated':current,'forecast':forecast,'guard':117440512,'heavy_used_seconds':heavy_used,'remaining_heavy_seconds':1800-heavy_used,'decision':'launch_allowed','dependency_stop':config.get('dependency_stop'),'dependency_same_identity':same if config['kind']!='protocol' else [],'physical_RAM_headroom':memory if config['kind']!='protocol' else None,'before_child_spawn':True}
