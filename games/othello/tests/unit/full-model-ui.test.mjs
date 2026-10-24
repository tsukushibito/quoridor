// Model-free transport/host/Worker fixtures. No real model, rules, browser or search.
import assert from 'node:assert/strict';
import test from 'node:test';
import { loadTs } from '../../../../tests/unit/ts-fixture.mjs';
const source = (name) =>
  new URL('../../../../apps/web/src/games/othello/' + name + '.ts', import.meta.url);
const flush = async () => {
  for (let i = 0; i < 24; i++) await Promise.resolve();
};
const identity = { version: 1, mainSha256: '11'.repeat(32), endingSha256: '22'.repeat(32) };
const spec = {
  identity,
  mainBytes: 3,
  endingBytes: 2,
  interpretation: 'simd',
  hashLevel: 20,
  readyTimeoutMs: 30000,
  replyTimeoutMs: 1100,
  options: {
    timeMs: 1000,
    maxDepth: 60,
    fixedDepth: null,
    selectivity: null,
    mpc: true,
    etc: true,
    stability: true,
    parity: true,
    shallowOrdering: true,
  },
};
const token = (request = 1, generation = 1) => ({ generation, request });
const request = (n = 1) => ({
  token: token(n),
  state: { opaque: 'Rust validates this fixture state' },
  strategy: 'fullModel',
  model: spec,
});
const result = { move: 19, opaque: 'actual schema is independently checked by Rust fixture tests' };
class Worker {
  listeners = new Map();
  sent = [];
  stops = 0;
  addEventListener(name, callback) {
    this.listeners.set(name, callback);
  }
  removeEventListener(name, callback) {
    if (this.listeners.get(name) === callback) this.listeners.delete(name);
  }
  postMessage(value, transfer) {
    this.sent.push({ value, transfer });
  }
  terminate() {
    assert.equal(this.listeners.size, 0, 'detach before terminate');
    this.stops++;
  }
  emit(value) {
    this.listeners.get('message')?.({ data: value });
  }
}
async function clientFixture() {
  const workers = [],
    timers = new Map(),
    digests = [];
  let next = 0,
    reads = 0;
  const { createAIClient } = await loadTs(
    source('ai-client'),
    {},
    {
      setTimeout(fn, ms) {
        const id = ++next;
        timers.set(id, { fn, ms });
        return id;
      },
      clearTimeout(id) {
        timers.delete(id);
      },
      crypto: {
        subtle: {
          async digest(name, buffer) {
            assert.equal(name, 'SHA-256');
            digests.push(buffer);
            return new Uint8Array(32).fill(new Uint8Array(buffer)[0] === 1 ? 0x11 : 0x22).buffer;
          },
        },
      },
    },
  );
  const client = createAIClient(() => {
    const w = new Worker();
    workers.push(w);
    return w;
  });
  const files = {
    main: {
      size: 3,
      async arrayBuffer() {
        reads++;
        return new Uint8Array([1, 1, 1]).buffer;
      },
    },
    ending: {
      size: 2,
      async arrayBuffer() {
        reads++;
        return new Uint8Array([2, 2]).buffer;
      },
    },
  };
  async function load() {
    const values = [];
    client.load(files, token(), spec, (v) => values.push(v));
    await flush();
    const w = workers.at(-1);
    assert.equal(w.sent[0].value.kind, 'fullInit');
    assert.equal(w.sent[0].transfer.length, 2);
    w.emit({ kind: 'fullReady', token: token(), identity });
    assert.equal(values[0].error, null);
    assert.equal(timers.size, 0);
    return w;
  }
  return { client, workers, timers, digests, files, load, reads: () => reads };
}
function respond(w, req) {
  w.emit({
    kind: 'fullResult',
    token: req.token,
    state: req.state,
    strategy: req.strategy,
    move: 19,
    searchResult: null,
    fullResult: result,
    modelIdentity: identity,
    error: null,
  });
}

test('fixture full ordinary replies reuse idle Worker and Files; reset is explicit', async () => {
  const f = await clientFixture(),
    w = await f.load(),
    replies = [];
  for (const n of [2, 3]) {
    const req = request(n);
    f.client.run(req, (r) => replies.push(r));
    assert.equal(w.sent.at(-1).value.kind, 'fullSearch');
    assert.equal(w.sent.at(-1).value.reset, false);
    assert.equal([...f.timers.values()][0].ms, 1100);
    respond(w, req);
    assert.equal(f.timers.size, 0);
    assert.equal(w.listeners.size, 0);
    assert.equal(w.stops, 0);
  }
  assert.equal(f.workers.length, 1);
  assert.equal(f.reads(), 2);
  assert.equal(f.digests.length, 2);
  assert.equal(replies[0].fullResult, result);
  assert.equal(replies[0].searchResult, null);
  f.client.reset();
  const req = request(4);
  f.client.run(req, (r) => replies.push(r));
  assert.equal(w.sent.at(-1).value.reset, true);
  respond(w, req);
  f.client.dispose();
  assert.equal(w.stops, 1);
});

test('fixture cancel revokes listeners/timer before termination; retry loads fresh owner without stale commit', async () => {
  const f = await clientFixture(),
    w = await f.load(),
    replies = [],
    stages = [];
  const req = request(2);
  f.client.run(
    req,
    (r) => replies.push(r),
    (p) => stages.push(p),
  );
  const stale = w.listeners.get('message');
  w.emit({ kind: 'fullPreCall', token: req.token, identity });
  assert.deepEqual(stages, ['thinking']); // observed message, not proof of engine entry
  f.client.cancel();
  assert.equal(f.timers.size, 0);
  assert.equal(w.stops, 1);
  stale({ data: { kind: 'fullResult', ...req, move: 19, fullResult: result, error: null } });
  assert.equal(replies.length, 0);
  const retry = request(3);
  f.client.run(
    retry,
    (r) => replies.push(r),
    (p) => stages.push(p),
  );
  await flush();
  assert.equal(f.workers.length, 2);
  const replacement = f.workers[1];
  replacement.emit({ kind: 'fullReady', token: retry.token, identity });
  assert.equal(replacement.sent.at(-1).value.kind, 'fullSearch');
  respond(replacement, retry);
  assert.equal(replies.length, 1);
  assert.equal(f.reads(), 4);
  assert.equal(f.digests.length, 2, 'immutable Files need no second hash');
  f.client.dispose();
});

test('fixture wrong pair refuses before construction and disposed async load cannot create a late owner', async () => {
  const f = await clientFixture(),
    replies = [];
  f.client.load({ ...f.files, main: { size: 1, arrayBuffer: assert.fail } }, token(), spec, (r) =>
    replies.push(r),
  );
  await flush();
  assert.ok(replies[0].error);
  assert.equal(f.workers.length, 0);
  assert.equal(f.reads(), 0);
  let release;
  const main = {
    size: 3,
    arrayBuffer: () =>
      new Promise((resolve) => {
        release = resolve;
      }),
  };
  f.client.load({ ...f.files, main }, token(2), spec, (r) => replies.push(r));
  f.client.dispose();
  release(new Uint8Array([1, 1, 1]).buffer);
  await flush();
  assert.equal(f.workers.length, 0);
  assert.equal(replies.length, 1);
  assert.equal(f.timers.size, 0);
});

test('fixture reply deadline ends ownership without pretending synchronous Wasm was interrupted', async () => {
  const f = await clientFixture(),
    w = await f.load(),
    replies = [];
  f.client.run(request(2), (r) => replies.push(r));
  [...f.timers.values()][0].fn();
  assert.equal(w.stops, 1);
  assert.equal(f.timers.size, 0);
  assert.equal(replies[0].move, null);
  assert.equal(replies[0].fullResult, null);
  assert.ok(replies[0].error);
  f.client.dispose();
});

test('fixture actual Worker adapter retains the owner and passes unchanged full result/options', async () => {
  const sent = [],
    calls = [],
    scope = { onmessage: null, postMessage: (v) => sent.push(v) };
  const owner = {
    clear() {
      calls.push('clear');
    },
    free() {
      calls.push('free');
    },
    search(state, options) {
      calls.push({ state, options });
      return result;
    },
  };
  await loadTs(
    source('ai.worker'),
    {
      '../../../../../games/othello/bridge/src': {
        chooseMove: assert.fail,
        search: assert.fail,
        async createFullModel(main, ending, value) {
          calls.push({ main, ending, value });
          return owner;
        },
      },
    },
    { self: scope },
  );
  scope.onmessage({
    data: {
      kind: 'fullInit',
      token: token(),
      model: spec,
      main: new Uint8Array(3).buffer,
      ending: new Uint8Array(2).buffer,
    },
  });
  await flush();
  assert.equal(sent[0].kind, 'fullReady');
  const req = request(2);
  scope.onmessage({ data: { kind: 'fullSearch', request: req, reset: false } });
  await flush();
  assert.equal(sent[1].kind, 'fullPreCall');
  assert.equal(sent[2].fullResult, result);
  assert.equal(calls[2].state, req.state);
  assert.equal(calls[2].options, spec.options);
  scope.onmessage({ data: { kind: 'fullSearch', request: request(3), reset: true } });
  await flush();
  assert.equal(calls.filter((v) => v === 'clear').length, 2);
  assert.equal(calls.filter((v) => v === 'free').length, 0);
  assert.equal(calls.filter((v) => typeof v === 'object' && 'main' in v).length, 1);
});

test('fixture a wrong hash replaces no valid owner and never falls back to previous Files', async () => {
  const f = await clientFixture(),
    old = await f.load(),
    replies = [];
  f.client.load(
    {
      ...f.files,
      main: {
        size: 3,
        async arrayBuffer() {
          return new Uint8Array([2, 2, 2]).buffer;
        },
      },
    },
    token(2),
    spec,
    (r) => replies.push(r),
  );
  await flush();
  assert.ok(replies[0].error);
  assert.equal(old.stops, 1);
  assert.equal(f.workers.length, 1);
  f.client.run(request(3), (r) => replies.push(r));
  assert.ok(replies[1].error);
  assert.equal(f.workers.length, 1);
  f.client.dispose();
});

test('fixture host carries Rust model effects and strips transport-only spec before dispatch', async () => {
  const { createHost } = await loadTs(source('host'), {});
  const actions = [],
    callbacks = [],
    loads = [],
    writes = [];
  let generation = 1,
    cancels = 0,
    disposals = 0,
    frees = 0;
  const req = request(2),
    host = createHost({
      createUI: async () => ({
        free() {
          frees++;
        },
        dispatch(action) {
          actions.push(action);
          if (action.kind === 'cancel') generation++;
          return {
            view: { generation, exitWarning: null },
            effects:
              action.kind === 'loadModel'
                ? [{ kind: 'loadModel', token: token(), spec }]
                : action.kind === 'modelReply'
                  ? [{ kind: 'think', ...req }]
                  : action.kind === 'cancel'
                    ? [{ kind: 'cancelWorker' }]
                    : [],
          };
        },
      }),
      ai: {
        cancel() {
          cancels++;
        },
        dispose() {
          disposals++;
        },
        forget() {},
        reset() {},
        load(files, value, options, reply) {
          loads.push({ files, value, options, reply });
        },
        run(value, reply, phase) {
          callbacks.push({ value, reply, phase });
        },
      },
      repository: {
        read: assert.fail,
        write(...args) {
          writes.push(args);
        },
      },
      confirm: assert.fail,
      render() {},
      failure: assert.fail,
    });
  const selected = {
    main: { fixture: 'immutable File port' },
    ending: { fixture: 'ending File port' },
  };
  host.selectModelFiles(selected);
  await flush();
  host.send({ kind: 'loadModel' });
  assert.equal(loads[0].files, selected);
  assert.equal(loads[0].options, spec);
  loads[0].reply({ identity, mainBytes: 3, endingBytes: 2, error: null });
  callbacks[0].phase('thinking', identity);
  callbacks[0].reply({
    ...req,
    move: 19,
    searchResult: null,
    fullResult: result,
    modelIdentity: identity,
    error: null,
  });
  const completion = actions.find((v) => v.kind === 'aiReply');
  assert.equal(completion.fullResult, result);
  assert.equal(Object.hasOwn(completion, 'model'), false);
  assert.equal(Object.hasOwn(completion, 'files'), false);
  host.send({ kind: 'cancel' });
  const count = actions.length;
  callbacks[0].reply({ ...req, move: 19, searchResult: null, fullResult: result, error: null });
  assert.equal(actions.length, count);
  assert.equal(writes.length, 0);
  assert.ok(cancels > 0);
  host.dispose();
  assert.equal(disposals, 1);
  assert.equal(frees, 1);
});
