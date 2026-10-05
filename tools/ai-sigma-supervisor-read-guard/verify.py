"""Small deterministic boundary checks plus real owned-child cleanup diagnostics."""
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'.artifacts/ai-sigma/continuation-20261001/SIGMA-SUPERVISOR-READ-GUARD'
spec=importlib.util.spec_from_file_location('readguard',HERE/'guard.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
os.sched_setaffinity(0,{0});os.environ.update(g.ENV)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
# Focused nullable owned-clock regression; no live dispatch/history replay.
if '--unbounded-clock' in sys.argv:
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--unbounded-clock',action='store_true');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    wall=g.OPERATION_BEGIN+dt.timedelta(hours=1);run,turn=str(uuid.uuid4()),str(uuid.uuid4())
    owned={'run_id':run,'turn_id':turn,'thread_id':g.THREAD,'started_at':wall.isoformat(),'max_turn_seconds':None}
    b=g.binding(owned,run,turn,wall=wall,mono=1000,boot='fixture');checks=[]
    def check(name,fn,reject=False):
        try:fn()
        except g.Rejected:assert reject,name
        else:assert not reject,name
        checks.append(name)
    for age in (181,1201):check('elapsed-'+str(age),lambda age=age:g.admit(b,'read_start',wall=wall+dt.timedelta(seconds=age),mono=1000+age))
    check('hard-end',lambda:g.admit(b,'finish',wall=g.OPERATION_END,mono=1000),True)
    check('finish-reserve',lambda:g.admit(b,'finish',wall=g.OPERATION_END-dt.timedelta(seconds=35),mono=1000,required_seconds=36),True)
    check('wrong-turn',lambda:g.binding(owned,run,str(uuid.uuid4()),wall=wall,mono=1000),True)
    check('unknown-limit',lambda:g.binding({k:v for k,v in owned.items() if k!='max_turn_seconds'},run,turn,wall=wall,mono=1000),True)
    for value in (0,True,-1):check('invalid-'+str(value),lambda value=value:g.binding({**owned,'max_turn_seconds':value},run,turn,wall=wall,mono=1000),True)
    finite=g.binding({**owned,'max_turn_seconds':180},run,turn,wall=wall,mono=1000,boot='fixture')
    check('finite-kept',lambda:g.admit(finite,'finish',wall=wall+dt.timedelta(seconds=181),mono=1181),True)
    migrated=g.binding(owned,run,turn,prior=finite,wall=wall+dt.timedelta(seconds=181),mono=1181,boot='fixture')
    assert migrated['mapped_start_monotonic']==finite['mapped_start_monotonic'] and migrated['turn_deadline_utc'] is None
    checks.append('migration-keeps-clock')
    core=[{'id':g.GOAL,'status':'in_progress','labels':[]},{'id':g.SELF,'status':'in_progress','assignee':'codex:'+g.THREAD,'labels':[]}]
    check('pause',lambda:g.require_unpaused([core[0],{**core[1],'labels':['paused-by-user']}]),True)
    check('unknown-owner',lambda:g.require_unpaused([core[0],{**core[1],'assignee':'unknown'}]),True)
    live=g.binding({**owned,'started_at':(g.utc_now()-dt.timedelta(seconds=181)).isoformat()},run,turn)
    assert g.run_child([sys.executable,'-B','-c','import json;print(json.dumps({"after180":True}))'],args.output/'child.json',live,timeout=2)['after180']
    checks.append('real-child-after180')
    check('child-timeout',lambda:g.run_child([sys.executable,'-B','-c','import time;time.sleep(5)'],args.output/'timeout.json',live,timeout=.1),True)
    assert json.loads((args.output/'timeout.json').read_text())['reaped']
    g.write(args.output/'verification.json',{'checks':checks,'passed':len(checks),'live_dispatch':False,'self':g.proc(os.getpid())})
    print(json.dumps({'passed':len(checks)}));raise SystemExit(0)

# Focused 106 regression mode; no historical scenario replay or live dispatch.
if '--summary-only' in sys.argv:
    import argparse
    import hashlib
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary-only', action='store_true')
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    checks = []
    def passed(name): checks.append(name)
    def references(rows):
        return [{k: x[k] for k in g.DEPENDENCY_REFERENCE_FIELDS if k in x}
                if isinstance(x, dict) else {'id': x} for x in rows or []]
    parent = {'id': g.GOAL, 'status': 'in_progress', 'assignee': 'coordinator',
              'dependency_type': 'parent-child', 'labels': ['current'],
              'description': 'long description'*1000, 'notes': 'parent notes'*10000,
              'dependencies': [{'id': 'nested', 'notes': 'recursive history'}]}
    rows = [parent, {'issue_id': 'child', 'depends_on_id': g.GOAL, 'type': 'blocks'}, 'string-id']
    short = g.dependency_summary(rows)
    assert references(rows) == references(short)
    assert all(not {'description', 'notes', 'dependencies'} & x.keys() for x in short)
    assert short[0]['labels'] == parent['labels']
    passed('embedded-and-edge-schema-id-relation-preserved-no-history')
    source = args.snapshot.read_bytes()
    old = json.loads(source)
    directory = args.snapshot.parent
    prefix = '168586309281762'
    raw_paths = [directory/(prefix+'-core-attempt-1.stdout'), directory/(prefix+'-selected-attempt-1.stdout')]
    issues = sum((json.loads(path.read_text()) for path in raw_paths), [])
    new = {**old, 'issues': g.issue_summary(issues)}
    assert [x['id'] for x in new['issues']] == [x['id'] for x in old['issues']]
    assert new['current_issue_ids'] == old['current_issue_ids']
    for before, after in zip(old['issues'], new['issues']):
        assert references(before['dependencies']) == references(after['dependencies'])
        assert before['notes_tail'] == after['notes_tail']
        assert before['status'] == after['status'] and before['assignee'] == after['assignee']
    current = json.loads((directory/(prefix+'-current-attempt-1.stdout')).read_text())
    children = sorted(directory.glob(prefix+'-children-*-attempt-1.stdout'))
    for path in children: current += json.loads(path.read_text())
    ready = {x.get('id') for x in json.loads((directory/(prefix+'-ready-attempt-1.stdout')).read_text())}
    assert g.select_current(current, ready) == [x['id'] for x in old['issues'][2:]]
    passed('actual-raw-selected-ids-relations-current-selection-and-note-tails-preserved')
    # Authorization continues to inspect the original rows, not summaries.
    core = [{'id': g.GOAL, 'status': 'in_progress', 'labels': []},
            {'id': g.SELF, 'status': 'in_progress', 'assignee': 'codex:'+g.THREAD, 'labels': []}]
    g.require_unpaused(core)
    for bad in ([core[0], {**core[1], 'labels': ['paused-by-user']}],
                [core[0], {**core[1], 'assignee': 'unknown'}]):
        try: g.require_unpaused(bad)
        except g.Rejected: pass
        else: raise AssertionError('authorization refusal changed')
    passed('pause-and-unknown-owner-refusal-maintained')
    wall = g.OPERATION_END
    owned = {'run_id': str(uuid.uuid4()), 'turn_id': str(uuid.uuid4()), 'thread_id': g.THREAD,
             'started_at': (wall-dt.timedelta(seconds=1)).isoformat(), 'max_turn_seconds': 180}
    bound = g.binding(owned, owned['run_id'], owned['turn_id'], wall=wall, mono=100)
    try: g.admit(bound, 'read_start', wall=wall, mono=100)
    except g.Rejected: pass
    else: raise AssertionError('hard end must reject')
    passed('absolute-operation-deadline-refusal-maintained')
    now = g.utc_now(); owned['started_at'] = now.isoformat()
    live = g.binding(owned, owned['run_id'], owned['turn_id'])
    path = args.output/'child-timeout.json'
    try:
        g.run_child([sys.executable, '-B', '-c', 'import time;time.sleep(5)'], path, live, timeout=.1)
    except g.Rejected: pass
    else: raise AssertionError('owned child timeout must reject')
    stop = json.loads(path.read_text())
    assert stop['reaped'] and stop['cause'] == 'timeout/deadline'
    passed('owned-short-child-timeout-reaped')
    raw_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.snapshot, *raw_paths]}
    assert hashlib.sha256(args.snapshot.read_bytes()).hexdigest() == hashlib.sha256(source).hexdigest()
    old_stdout = json.dumps(old, ensure_ascii=False).encode()
    new_stdout = json.dumps(new, ensure_ascii=False).encode()
    assert len(new_stdout) < len(old_stdout)/4
    g.write(args.output/'reduced-snapshot.json', new)
    result = {'passed': len(checks), 'checks': checks, 'snapshot_ref': str(args.snapshot),
              'raw_sha256': raw_hashes, 'old_snapshot_file_bytes': len(source),
              'old_model_stdout_bytes': len(old_stdout), 'new_model_stdout_bytes': len(new_stdout),
              'new_snapshot_file_bytes': (args.output/'reduced-snapshot.json').stat().st_size,
              'reported_old_token_estimate': 209667, 'tokenizer_count_verified': False,
              'selected_ids': [x['id'] for x in new['issues']],
              'self': g.proc(os.getpid()), 'self_maxrss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'old_raw_modified': False, 'live_dispatch': False, 'future_whole_turn_verified': False}
    g.write(args.output/'verification.json', result)
    print(json.dumps({k: result[k] for k in ('passed', 'old_snapshot_file_bytes', 'old_model_stdout_bytes', 'new_model_stdout_bytes', 'new_snapshot_file_bytes')}))
    raise SystemExit(0)

START=g.stamp();results=[]
W=dt.datetime(2026,10,1,10,0,tzinfo=dt.timezone.utc)
RUN=str(uuid.uuid4());TURN=str(uuid.uuid4())
owned={'run_id':RUN,'turn_id':TURN,'thread_id':g.THREAD,'started_at':W.isoformat(),'max_turn_seconds':180}
b=g.binding(owned,RUN,TURN,wall=W,mono=1000,boot='mock-boot')
def case(name,fn,reject=False):
    try:v=fn()
    except g.Rejected as e:
        assert reject,(name,str(e));results.append({'name':name,'passed':True,'rejected':str(e)});return
    assert not reject,name
    results.append({'name':name,'passed':True,'value':v})
for phase,limit in [('read_start',90),('read_finish',120),('finish',180)]:
    for delta,rej in [(-0.001,False),(0,True),(0.001,True)]:
        age=limit+delta
        case(f'{phase}:{age}',lambda phase=phase,age=age:g.admit(b,phase,wall=W+dt.timedelta(seconds=age),mono=1000+age),rej)
case('wrong-run',lambda:g.binding(owned,str(uuid.uuid4()),TURN,wall=W,mono=1000,boot='mock-boot'),True)
case('wrong-turn',lambda:g.binding(owned,RUN,str(uuid.uuid4()),wall=W,mono=1000,boot='mock-boot'),True)
case('unknown-start',lambda:g.binding({**owned,'started_at':None},RUN,TURN,wall=W,mono=1000,boot='mock-boot'),True)
case('future-start',lambda:g.binding(owned,RUN,TURN,wall=W-dt.timedelta(seconds=1),mono=1000,boot='mock-boot'),True)
case('changed-start',lambda:g.binding({**owned,'started_at':(W+dt.timedelta(seconds=1)).isoformat()},RUN,TURN,prior=b,wall=W+dt.timedelta(seconds=5),mono=1005,boot='mock-boot'),True)
case('reboot',lambda:g.binding(owned,RUN,TURN,prior=b,wall=W+dt.timedelta(seconds=5),mono=1005,boot='other-boot'),True)
case('rerun-same-deadline',lambda:g.binding(owned,RUN,TURN,prior=b,wall=W+dt.timedelta(seconds=20),mono=1020,boot='mock-boot')==b)
case('wall-backward-does-not-extend',lambda:g.admit(b,'read_start',wall=W+dt.timedelta(seconds=10),mono=1090),True)
case('monotonic-backward',lambda:g.admit(b,'read_start',wall=W+dt.timedelta(seconds=10),mono=999),True)
now=g.utc_now();live=g.binding({**owned,'started_at':(now-dt.timedelta(seconds=1)).isoformat()},RUN,TURN)
path=OUT/'environment-diagnostic.json'
code="import os,json,datetime;print(json.dumps({'affinity':list(os.sched_getaffinity(0)),'env':{k:os.getenv(k) for k in ('UV_NO_SYNC','UV_OFFLINE','PYTHONDONTWRITEBYTECODE')},'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))"
v=g.run_child([sys.executable,'-B','-c',code],path,live,timeout=2)
assert v['affinity']==[0] and all(v['env'][k]=='1' for k in g.ENV)
row=json.loads(path.read_text());assert row['started']['utc'] and row['finished']['utc'] and row['reaped']
results.append({'name':'real-environment-affinity-stamps','passed':True,'result':v})
path=OUT/'timeout-diagnostic.json'
code="import subprocess,sys,json,time,os;child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)']);print(json.dumps({'parent_pid':os.getpid(),'child_pid':child.pid}),flush=True);time.sleep(10)"
case('real-timeout-owned-group-cleanup',lambda:g.run_child([sys.executable,'-B','-c',code],path,live,timeout=0.15),True)
ids=json.loads(path.with_suffix('.stdout').read_text());row=json.loads(path.read_text())
states=[]
for k,pid in ids.items():
    p=g.proc(pid);assert p is None or p['state']=='Z',(k,p)
    states.append({'name':k,'pid':pid,'observed':p,'running':False})
assert row['reaped'] and row['cause']=='timeout/deadline'
results.append({'name':'timeout-parent-and-descendant-not-running','passed':True,'identities':states,
                'zombie_if_any_is_not_running_and_not_claimed_reaped_by_us':True})
# An expired invocation must not execute a diagnostic at all.
expired={**live,'mapped_start_monotonic':time.monotonic()-90,
         'started_at':(g.utc_now()-dt.timedelta(seconds=90)).isoformat()}
never=OUT/'expired-child.json'
case('expired-launch-blocked',lambda:g.run_child([sys.executable,'-B','-c','raise SystemExit(99)'],never,expired),True)
assert not never.exists() and not never.with_suffix('.stdout').exists()
original_live=g.live_owned;original_child=g.run_child
commands=[]
cached_owned={**owned,'started_at':g.utc_now().isoformat()}
batch_bound=g.binding(cached_owned,RUN,TURN)
batch_state={'process':{'pid':1000963,'start_ticks':'9899975'},'owned':cached_owned}
def mock_live(run,turn,prior):
    assert run==RUN and turn in (None,TURN)
    g.admit(batch_bound,'read_start');return batch_bound,batch_state
def mock_child(args,path,bound,**kw):
    g.admit(bound,'read_start' if kw.get('phase','read')=='read' else 'finish')
    commands.append(args)
    if 'ready' in args:return [{'id':'quoridor-4lc.42'}]
    if 'show' in args:return [{'id':'quoridor-4lc.40','status':'in_progress','assignee':'codex:'+g.THREAD,'labels':[]},
                             {'id':'quoridor-4lc','status':'in_progress','labels':[]}]
    if 'status' in args:return {'supervisor':{'status':{'type':'active'}}}
    return {'reaped':True,'mock':True,'started':g.stamp(),'finished':g.stamp()}
try:
    g.live_owned=mock_live;g.run_child=mock_child
    batchdir=OUT/('mock-batch-'+RUN);batchdir.mkdir(exist_ok=False)
    observed=g.observe(batchdir,RUN,TURN);assert observed['read_command_count']==3 and len(commands)==3
    observed2=g.observe(batchdir,RUN,TURN);assert observed2['cached'] and len(commands)==3
    def forbidden_live(*args,**kwargs):raise AssertionError('finish must not refresh runtime metadata')
    g.live_owned=forbidden_live
    finalized=g.finish(batchdir,RUN,TURN,'mock bookkeeping only')
    assert finalized['owned_command_children_reaped'] and len(commands)==5
    assert commands[-2][2]=='update' and commands[-1][2]=='backup'
    results.append({'name':'mock-batch-once-cached-repeat-finish-no-fresh-runtime','passed':True,
                    'commands_recorded':len(commands),'live_Beads_mutation':False})
finally:g.live_owned=original_live;g.run_child=original_child
u=resource.getrusage(resource.RUSAGE_SELF);c=resource.getrusage(resource.RUSAGE_CHILDREN)
result={'started':START,'finished':g.stamp(),'results':results,'passed':len(results),'failed':0,
        'self':g.proc(os.getpid()),'self_maxrss_kib':u.ru_maxrss,'child_maxrss_kib':c.ru_maxrss,
        'self_user_cpu_s':u.ru_utime,'self_sys_cpu_s':u.ru_stime,'child_user_cpu_s':c.ru_utime,'child_sys_cpu_s':c.ru_stime,
        'live_supervisor_dispatch_or_steer':False,'NN_build_download':False,'side_DB_cache_write_test':False}
g.write(OUT/'verification.json',result)
print(json.dumps({'passed':len(results),'failed':0,'pid':os.getpid(),'self_maxrss_kib':u.ru_maxrss,'child_maxrss_kib':c.ru_maxrss}))
