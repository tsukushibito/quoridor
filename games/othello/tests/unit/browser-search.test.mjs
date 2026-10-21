// Source-only mock transport/host tests. No actual Wasm/search/browser executes.
import assert from 'node:assert/strict';
import test from 'node:test';
import { loadTs } from '../../../../tests/unit/ts-fixture.mjs';
const source = (name) =>
  new URL(`../../../../apps/web/src/games/othello/${name}.ts`, import.meta.url);
const flush = async () => {
  for (let i = 0; i < 12; i++) await Promise.resolve();
};
const request = (strategy) => ({
  strategy,
  token: { generation: 3, request: 8 },
  state: { version: 1, board: ['opaque'], toMove: 1 },
});
const result = {
  move: 19,
  score: 123,
  scoreKind: 'heuristic',
  completedDepth: 4,
  nodes: 20,
  elapsedMs: 1000.2,
  timedOut: true,
  cancelled: false,
  proven: false,
};
async function worker(port) {
  const replies = [],
    scope = { onmessage: null, postMessage: (value) => replies.push(value) };
  await loadTs(
    source('ai.worker'),
    { '../../../../../games/othello/bridge/src': port },
    { self: scope },
  );
  return {
    replies,
    async run(value) {
      scope.onmessage({ data: value });
      await flush();
      return replies.at(-1);
    },
  };
}

test('simple strategy calls only chooseMove and preserves explicit request identity', async () => {
  const calls = [];
  const w = await worker({
    chooseMove: async (state) => {
      calls.push(state);
      return 19;
    },
    search: () => assert.fail('unexpected search'),
  });
  const req = request('simple'),
    reply = await w.run(req);
  assert.equal(calls[0], req.state);
  assert.equal(reply.state, req.state);
  assert.equal(reply.token, req.token);
  assert.equal(reply.strategy, 'simple');
  assert.equal(reply.move, 19);
  assert.equal(reply.searchResult, null);
  assert.equal(reply.error, null);
});

test('searchV1 calls baseline search with the fixed budget and returns untouched actual result', async () => {
  const calls = [];
  const w = await worker({
    chooseMove: () => assert.fail('unexpected simple'),
    search: async (state, options) => {
      calls.push({ state, options });
      return result;
    },
  });
  const req = request('searchV1'),
    reply = await w.run(req);
  assert.equal(calls[0].state, req.state);
  assert.equal(
    JSON.stringify(calls[0].options),
    JSON.stringify({ timeMs: 1000, ttMiB: 32, maxDepth: 64, exactEmpties: 12 }),
  );
  assert.equal(reply.strategy, 'searchV1');
  assert.equal(reply.state, req.state);
  assert.equal(reply.token, req.token);
  assert.equal(reply.searchResult, result);
  assert.equal(reply.move, result.move);
  assert.equal(reply.error, null);
  assert.equal(reply.searchResult.timedOut, true); // Not normalized to a transport error.
});

test('Worker failure and unknown strategy report retryable errors without hidden fallback', async () => {
  const w = await worker({
    chooseMove: () => assert.fail('no simple fallback'),
    search: () => {
      throw Error('search failed');
    },
  });
  const req = request('searchV1'),
    failed = await w.run(req);
  assert.match(failed.error, /search failed/);
  assert.equal(failed.searchResult, null);
  assert.equal(failed.move, null);
  assert.equal(failed.strategy, 'searchV1');
  assert.equal(failed.state, req.state);
  const unknown = await w.run(request('learned'));
  assert.match(unknown.error, /方式/);
  assert.equal(unknown.move, null);
});

class Worker {
  listeners = new Map();
  stopped = 0;
  addEventListener(name, fn) {
    this.listeners.set(name, fn);
  }
  removeEventListener(name, fn) {
    if (this.listeners.get(name) === fn) this.listeners.delete(name);
  }
  postMessage(value) {
    this.request = value;
  }
  terminate() {
    this.stopped++;
  }
  emit(data) {
    this.listeners.get('message')?.({ data });
  }
}
test('transport carries strategy/raw diagnostics to Rust, strips extra wire keys, revokes old workers', async () => {
  const { createAIClient } = await loadTs(source('ai-client'), {});
  const workers = [],
    replies = [],
    client = createAIClient(() => {
      const w = new Worker();
      workers.push(w);
      return w;
    });
  const req = request('searchV1');
  client.run(req, (reply) => replies.push(reply));
  const stale = workers[0].listeners.get('message');
  client.run({ ...req, strategy: 'simple', token: { generation: 4, request: 9 } }, (reply) =>
    replies.push(reply),
  );
  assert.equal(workers[0].stopped, 1);
  assert.equal(workers[0].listeners.size, 0);
  stale({ data: { ...req, move: 19, searchResult: result, error: null } });
  assert.equal(replies.length, 0);
  const actual = {
    ...workers[1].request,
    strategy: 'searchV1',
    move: 19,
    searchResult: { malformed: 'must reach Rust validation' },
    error: null,
    extra: 'not an Action field',
  };
  workers[1].emit(actual);
  assert.equal(replies[0].strategy, 'searchV1');
  assert.equal(replies[0].searchResult, actual.searchResult);
  assert.equal(Object.hasOwn(replies[0], 'extra'), false);
  assert.equal(workers[1].stopped, 1);
});

test('bad wire response retains requested search identity in its error completion', async () => {
  const { createAIClient } = await loadTs(source('ai-client'), {}),
    w = new Worker(),
    replies = [];
  const client = createAIClient(() => w),
    req = request('searchV1');
  client.run(req, (value) => replies.push(value));
  w.emit({ ...req, strategy: 'unknown', move: 99, error: null });
  assert.equal(replies[0].strategy, 'searchV1');
  assert.equal(replies[0].token, req.token);
  assert.equal(replies[0].state, req.state);
  assert.equal(replies[0].searchResult, null);
  assert.equal(replies[0].move, null);
  assert.ok(replies[0].error);
});

test('thin host forwards Rust strategy and synchronously cancels/discards revoked completion', async () => {
  const { createHost } = await loadTs(source('host'), {}),
    actions = [],
    callbacks = [];
  let cancelled = 0;
  const req = request('searchV1');
  const host = createHost({
    createUI: async () => ({
      free() {},
      dispatch(action) {
        actions.push(action);
        return {
          view: { generation: action.kind === 'new' ? 3 : 4, exitWarning: null },
          effects: action.kind === 'new' ? [{ kind: 'think', ...req }] : [{ kind: 'cancelWorker' }],
        };
      },
    }),
    ai: {
      cancel() {
        cancelled++;
      },
      run(request, reply) {
        callbacks.push({ request, reply });
      },
    },
    repository: {
      read() {
        throw Error('unexpected read');
      },
      write() {
        throw Error('unexpected write');
      },
    },
    confirm: () => true,
    render() {},
    failure: assert.fail,
  });
  host.send({ kind: 'new', mode: 'ai', humanSide: 2, strategy: 'searchV1' });
  await flush();
  assert.equal(callbacks[0].request.strategy, 'searchV1');
  const before = cancelled;
  host.send({ kind: 'setup', mode: 'ai', humanSide: 2, strategy: 'simple' });
  assert.equal(cancelled, before + 1);
  callbacks[0].reply({ ...req, move: 19, searchResult: result, error: null });
  assert.deepEqual(
    actions.map((a) => a.kind),
    ['new', 'setup'],
  );
  host.dispose();
});
