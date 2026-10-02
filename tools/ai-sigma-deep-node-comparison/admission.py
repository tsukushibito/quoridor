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
    previous=[json.loads(p.read_text()) for p in runs.glob('deep132-*.process.json')]
    base.decide([],previous)
    heavy=[];metadata=[]
    if config['kind']!='protocol':
        heavy,metadata=physical_heavy_scan()
        base.decide(heavy,previous)
        stop_path=Path(config['dependency_stop'])
        if not stop_path.is_file():raise RuntimeError('DEPENDENCY129_STOP_NOT_RECEIVED')
        stop=json.loads(stop_path.read_text())
        if not stop.get('runtime_stopped') and not stop.get('source_runtime_stopped') and not stop.get('source_and_heavy_write_stopped') and not stop.get('source_and_browser_stopped'):
            raise RuntimeError('DEPENDENCY129_STOP_UNCONFIRMED')
    current=sum(p.stat().st_blocks*512 for folder in [out,tool,tool.parents[1]/'research-data/ai-sigma/132-deep-node-comparison'] for p in folder.rglob('*') if p.is_file())
    forecast=0 if config['kind']=='protocol' else config['forecast_bytes']
    if current+forecast>=469762048:raise RuntimeError('STORAGE_HEADROOM')
    now=datetime.datetime.now(datetime.timezone.utc)
    if now>=datetime.datetime.fromisoformat(config['newjob_deadline']):raise RuntimeError('NEWJOB_DEADLINE')
    heavy_used=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in previous if x['phase']!='protocol')
    if config['kind']!='protocol' and heavy_used+config['minimum_remaining_heavy_seconds']>600:raise RuntimeError('HEAVY_BUDGET')
    return {'UTC':now.isoformat(),'external_heavy':heavy,'recognized_infrastructure_metadata':metadata,'whole_host_no_load_not_proved':True,'prior_remaining_unknown':0,'current_allocated':current,'forecast':forecast,'guard':469762048,'heavy_used_seconds':heavy_used,'remaining_heavy_seconds':600-heavy_used,'decision':'launch_allowed','dependency_stop':config.get('dependency_stop'),'before_child_spawn':True}
