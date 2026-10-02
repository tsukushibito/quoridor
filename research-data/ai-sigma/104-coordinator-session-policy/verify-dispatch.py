"""Exercise the owned dispatcher without starting research or an App Server turn."""
import asyncio
import contextlib
import json
import pathlib
import sys
import tempfile
import types

source = pathlib.Path('.artifacts/ai-sigma/resume-20261002/dispatch.py')
ns = {'__name__': 'dispatch_verification'}
exec(compile(source.read_text(), str(source), 'exec'), ns)
original = ns['m']
results = []


def case(name, *, role='experiment', status='idle', paused=False,
         existing=False, filename='input.md', ambiguous=False, locked=False):
    reads, requests = [], []
    target_id = ('01a0f2e9-357d-7ef3-a2fe-b16f80accda5'
                 if role == 'root' else 'saved-experiment')

    class FakeServer:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def read_thread(self, tid):
            reads.append(tid)
            assert tid == target_id, 'Other roles must not be read for admission'
            return {'id': tid, 'status': {'type': status}, 'cwd': str(ns['CWD'])}

        async def turns(self, tid):
            assert tid == target_id
            return ([] if ambiguous else [{'id': 'exact-active-turn', 'status': 'inProgress'}])

        async def request(self, method, params):
            requests.append((method, params))
            return {'turnId': 'exact-active-turn'}

        deliver = original.AppServer.deliver

    @contextlib.contextmanager
    def lock(root):
        if locked:
            raise RuntimeError('dispatch lock held')
        yield

    def require(issue, root):
        if paused:
            raise RuntimeError('issue paused')

    # Extra active and unknown roles exist; consulting them would fail above.
    registry = {'roles': {k: {'thread_id': k} for k in
                         ('experiment', 'active1', 'active2', 'active3', 'unknown')}}
    ns['m'] = types.SimpleNamespace(
        dispatch_lock=lock, require_issue=require,
        load_registry=lambda *args: registry,
        command_json=lambda *args: {}, AppServer=FakeServer,
        role_entry=lambda data, key: {'thread_id': target_id},
    )
    with tempfile.TemporaryDirectory() as output:
        ns['OUT'] = pathlib.Path(output)
        (ns['OUT'] / filename).write_text('Current authorized task/report')
        if existing:
            (ns['OUT'] / (pathlib.Path(filename).stem + '-delivery.json')).write_text('{}')
        sys.argv = [str(source), role, 'quoridor-4lc.103', filename]
        error = None
        try:
            asyncio.run(ns['main']())
        except Exception as exc:
            error = str(exc)
        denied = paused or existing or ambiguous or locked or (
            filename == 'root-review96-ack.md' and status != 'active')
        if denied:
            assert not requests, (name, requests)
            if not (filename == 'root-review96-ack.md' and status != 'active'):
                assert error, name
        else:
            expected = 'turn/steer' if status == 'active' else 'turn/start'
            assert len(requests) == 1 and requests[0][0] == expected, requests
            if status == 'active':
                assert requests[0][1]['expectedTurnId'] == 'exact-active-turn'
        results.append({'case': name, 'passed': True, 'requests': len(requests),
                        'target_only_reads': len(reads), 'expected_rejection': error})


case('idle recipient, >=3 others active and unknown irrelevant')
case('active recipient steers exact turn', status='active')
case('pause rejects before App Server', paused=True)
case('existing receipt prevents duplicate send', existing=True)
case('unknown active turn prevents a second start', status='active', ambiguous=True)
case('dispatch lock prevents concurrent writer', locked=True)
case('root idle acknowledgement does not restart root', role='root', filename='root-review96-ack.md')
case('root active acknowledgement steers', role='root', status='active', filename='root-review96-ack.md')
pathlib.Path('research-data/ai-sigma/104-coordinator-session-policy/verification.json').write_text(
    json.dumps({'cases': results, 'all_pass': True, 'NN': 0, 'real_RPC': 0}, indent=2) + '\n')
print('8 cases passed; no real RPC/NN')
