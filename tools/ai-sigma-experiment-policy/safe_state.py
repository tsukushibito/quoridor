"""Bounded read recovery and exact-identity validation; no live fault injection."""
import datetime as dt
import json
from pathlib import Path
import time
import uuid

class Unavailable(RuntimeError):
    pass

def read_bounded(path, validate=lambda value:value, *, parse=json.loads,
                 attempts=5, delay=0.1, seconds=2, log=lambda event:None):
    start=time.monotonic();last=None
    for attempt in range(1,attempts+1):
        try:
            with Path(path).open('rb') as f: data=f.read(3*1024**2+1)
            if len(data)>3*1024**2:raise ValueError('bounded input too large')
            value=parse(data.decode())
            result=validate(value)
            if attempt>1:log({'event':'bounded_read_recovered','path':str(path),'attempts':attempt,
                              'elapsed_seconds':time.monotonic()-start})
            return result
        except (OSError,ValueError,KeyError,TypeError,Unavailable) as error:
            last=error
            log({'event':'bounded_read_failed','path':str(path),'attempt':attempt,
                 'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'error_type':type(error).__name__,
                 'error':str(error),'elapsed_seconds':time.monotonic()-start})
            if attempt==attempts or time.monotonic()-start+delay>=seconds:break
            time.sleep(delay)
    raise Unavailable(f'Persistent/unknown read after bounded attempts: {path}; {last}')

def validate_state(state, binding, process):
    if not isinstance(state,dict) or state.get('binding')!=binding:
        raise Unavailable('Unknown runtime binding; no guessed ownership')
    if state.get('phase') not in ('running','stopped'):
        raise Unavailable('Unknown phase')
    actual=state.get('process')
    if state['phase']=='running' and actual!=process:
        raise Unavailable('Scheduler identity changed')
    if state['phase']=='stopped' and actual is not None:
        raise Unavailable('Stopped state retains unexpected identity')
    owned=state.get('owned')
    if owned:
        if not isinstance(owned,dict) or owned.get('thread_id')!=binding['thread_id']:
            raise Unavailable('Unknown owned thread')
        try:
            uuid.UUID(owned['run_id'])
            if owned.get('turn_id'):uuid.UUID(owned['turn_id'])
            started=dt.datetime.fromisoformat(owned['started_at'].replace('Z','+00:00'))
            if started.tzinfo is None or owned.get('max_turn_seconds')!=180:raise ValueError()
        except (ValueError,KeyError,AttributeError,TypeError):
            raise Unavailable('Unknown owned run/turn/start/contract')
    return state

def signal_identity(expected, observed, current_boot, signaler):
    if (not expected or not observed or expected.get('boot_id')!=current_boot
        or expected['pid']!=observed['pid']
        or str(expected['start_ticks'])!=str(observed['start_ticks'])
        or observed.get('state')=='Z'):
        raise Unavailable('Stored owned process identity not confirmed; signal forbidden')
    return signaler(expected)
