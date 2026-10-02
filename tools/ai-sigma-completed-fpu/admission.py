"""Guard current owned recovery, physical heavy jobs and forecast before spawn."""
import datetime
import json
import os
from pathlib import Path
import importlib.util
source=Path(__file__).resolve().parent.parent/'ai-sigma-diverse-prefix/admission.py'
spec=importlib.util.spec_from_file_location('readonly119admission',source)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def admit(config,out,tool,runs):
    previous=[json.loads(p.read_text()) for p in runs.glob('fpu123-*.process.json')]
    base.decide([],previous)
    heavy=[]
    if config['kind']!='protocol':
        for record in base.scan_processes(exclude={os.getpid()}):
            # Metadata/protocol runners pinned CPU0 are not physical Chrome/NN.
            if Path(record['exe']).name.startswith('python') and os.sched_getaffinity(record['pid'])=={0}:
                continue
            heavy.append(record)
        base.decide(heavy,previous)
        stop_path=Path(config['dependency_stop'])
        if not stop_path.is_file():raise RuntimeError('CRITIC122_STOP_NOT_RECEIVED')
        stop=json.loads(stop_path.read_text())
        if not stop.get('runtime_stopped') and not stop.get('source_runtime_stopped'):
            raise RuntimeError('CRITIC122_STOP_UNCONFIRMED')
    current=sum(p.stat().st_blocks*512 for folder in [out,tool,tool.parents[1]/'research-data/ai-sigma/123-completed-fpu'] for p in folder.rglob('*') if p.is_file())
    forecast=0 if config['kind']=='protocol' else config['forecast_bytes']
    if current+forecast>=58720256:raise RuntimeError('STORAGE_HEADROOM')
    now=datetime.datetime.now(datetime.timezone.utc)
    if now>=datetime.datetime.fromisoformat(config['newjob_deadline']):raise RuntimeError('NEWJOB_DEADLINE')
    heavy_used=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in previous if x['phase']!='protocol')
    if config['kind']!='protocol' and heavy_used+config['minimum_remaining_heavy_seconds']>300:raise RuntimeError('HEAVY_BUDGET')
    return {'UTC':now.isoformat(),'external_heavy':heavy,'prior_remaining_unknown':0,'current_allocated':current,'forecast':forecast,'guard':58720256,'heavy_used_seconds':heavy_used,'remaining_heavy_seconds':300-heavy_used,'decision':'launch_allowed','dependency_stop':config.get('dependency_stop'),'before_child_spawn':True}
