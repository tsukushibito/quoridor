"""NN0 protocol example, not a real Registry, game, engine or GPU broker."""
from collections import deque
import json
import time
import os
import resource


class Pool:
    def __init__(self):
        self.live = {}
        self.queue = deque()
        self.inflight = []
        self.log = []
        self.stopped = False

    def open(self, game, generation, handle):
        assert game not in self.live
        self.live[game] = dict(generation=generation, handle=handle, token=0, pending=False)

    def ask(self, game):
        if self.stopped:
            raise ValueError('STOPPED')
        s = self.live[game]
        if s['pending']:
            raise ValueError('ONE_PENDING')
        s['pending'] = True
        s['token'] += 1
        key = ('mock-run', 'worker-0', game, s['generation'], s['handle'], s['token'])
        self.queue.append(key)
        return key

    def dispatch(self, max_batch=8):
        assert not self.inflight and 1 <= max_batch <= 8
        self.inflight = [self.queue.popleft() for _ in range(min(max_batch, len(self.queue)))]
        return list(self.inflight)

    def finish(self, returned, error=None):
        expected = self.inflight
        if error or returned != expected:
            self.log.append(dict(fault=error or 'ID_ATTRIBUTION', affected=expected))
            self.stop()  # Freeze run; no replacement of fault rows.
            self.inflight = []
            return
        for key in returned:
            _, _, game, generation, handle, token = key
            s = self.live.get(game)
            if not s or (s['generation'], s['handle'], s['token']) != (generation, handle, token):
                self.log.append(dict(discard='STALE_GENERATION_HANDLE_TOKEN', id=key))
                continue
            assert s['pending']
            s['pending'] = False
            self.log.append(dict(resume=key))
        self.inflight = []

    def cancel(self, game):
        self.live.pop(game, None)
        self.queue = deque(k for k in self.queue if k[2] != game)

    def stop(self):
        self.stopped = True
        self.log.extend(dict(discard='STOP_QUEUED', id=k) for k in self.queue)
        self.queue.clear()
        self.live.clear()


def rejects(fn, expected):
    try:
        fn()
    except ValueError as e:
        assert str(e) == expected
        return
    raise AssertionError('missing refusal')


def check():
    p = Pool()
    for g, h in [('a', 1), ('b', 2), ('c', 3)]:
        p.open(g, 1, h)
        p.ask(g)
    rejects(lambda: p.ask('a'), 'ONE_PENDING')
    keys = p.dispatch()
    assert len(keys) == 3  # Partial batch flushed explicitly; no wait for eight.
    p.cancel('b')
    p.open('b', 2, 4)
    new_b = p.ask('b')
    p.finish(keys)
    assert len([r for r in p.log if 'resume' in r]) == 2
    assert p.live['b']['pending']  # Old result cannot resume replacement game.
    assert p.dispatch() == [new_b]
    p.finish([new_b])
    p.ask('a')
    p.stop()
    rejects(lambda: p.ask('a'), 'STOPPED')
    assert not p.live and not p.queue and not p.inflight
    faults = []
    for mode in ['reordered_ID', 'provider_error', 'stop_inflight']:
        q = Pool()
        for g, h in [('a', 1), ('b', 2)]:
            q.open(g, 1, h)
            q.ask(g)
        k = q.dispatch()
        if mode == 'reordered_ID':
            q.finish(list(reversed(k)))
        elif mode == 'provider_error':
            q.finish([], 'PROVIDER_FAILURE')
        else:
            q.stop()
            q.finish(k)
            assert all('resume' not in r for r in q.log)
        assert not q.live and not q.queue and not q.inflight
        faults.append(dict(mode=mode, log=q.log))
    return dict(status='PASS', NN=0, game=0, GPU=0, real_engine=0,
                partial_B=3, cases=['onepending', 'partial', 'stale', 'replacement',
                                    'stop_queue', 'stop_inflight', 'bad_ID', 'provider_error'],
                successful_log=p.log, faults=faults)


if __name__ == '__main__':
    started = time.monotonic()
    result = check()
    result.update(pid=os.getpid(), affinity=sorted(os.sched_getaffinity(0)),
                  wall_seconds=time.monotonic()-started,
                  peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    print(json.dumps(result, indent=2))
