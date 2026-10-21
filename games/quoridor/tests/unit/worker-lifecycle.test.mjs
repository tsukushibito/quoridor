import test from 'node:test';
import assert from 'node:assert/strict';
import { loadTs } from '../../../../tests/unit/ts-fixture.mjs';

const protocol = await loadTs(new URL('../../bridge/src/protocol.ts', import.meta.url), {});
const context = {
  gameEpoch: 1,
  revision: 0,
  positionKey: '0'.repeat(42),
  snapshot: new TextEncoder().encode(
    JSON.stringify({
      schemaVersion: 1,
      rulesetId: protocol.RULESET_ID,
      positionKey: '0'.repeat(42),
    }),
  ),
  limits: { simulations: 48, maxNodes: 128, maxDepth: 8 },
  seed: '1',
};
const stats = {
  simulations: 1,
  nodes: 1,
  edges: 1,
  arenaBytes: 1,
  highWaterBytes: 1,
  maxDepthReached: 1,
  policyFallbacks: 0,
  valueFallbacks: 0,
  budgetExhausted: false,
};
const meta = (requestId, workerGeneration = 1) => ({
  protocolVersion: protocol.PROTOCOL_VERSION,
  engineBuildId: protocol.ENGINE_BUILD_ID,
  rulesetId: protocol.RULESET_ID,
  gameEpoch: 1,
  revision: 0,
  positionKey: context.positionKey,
  requestId,
  workerGeneration,
});

async function fixture() {
  const sent = [],
    tasks = new Map();
  let nextTimer = 0,
    freed = 0,
    terminated = 0;
  const worker = { postMessage: (message) => sent.push(message), close() {} };
  class Search {
    step() {
      return true;
    }
    finish_json() {
      return JSON.stringify({ actionId: 13, stats });
    }
    free() {
      freed++;
    }
  }
  await loadTs(
    new URL('../../bridge/src/ai.worker.ts', import.meta.url),
    {
      '../wasm/ai/quoridor_ai.js': {
        default: async () => ({ memory: { buffer: { byteLength: 1024 } } }),
        AiSearch: Search,
        ai_engine_build_id: () => protocol.ENGINE_BUILD_ID,
        ai_protocol_version: () => protocol.PROTOCOL_VERSION,
      },
      '../wasm/ai/quoridor_ai_bg.wasm?url': { default: 'blocked-fixture.wasm' },
      './protocol': protocol,
    },
    {
      self: worker,
      setTimeout: (fn) => {
        tasks.set(++nextTimer, fn);
        return nextTimer;
      },
      clearTimeout: (id) => tasks.delete(id),
    },
  );
  const messages = [];
  const host = {
    onmessage: null,
    onerror: null,
    onmessageerror: null,
    postMessage: (message) => messages.push(message),
    terminate: () => {
      terminated++;
    },
  };
  const { AiClient } = await loadTs(new URL('../../bridge/src/ai-client.ts', import.meta.url), {
    './protocol': protocol,
  });
  const client = new AiClient(() => host);
  async function receive(message) {
    await worker.onmessage({ data: message });
  }
  async function dispatch() {
    while (messages.length) await receive(messages.shift());
  }
  function deliver() {
    while (sent.length) host.onmessage?.({ data: sent.shift() });
  }
  async function ready() {
    const promise = client.startWorker();
    await dispatch();
    deliver();
    await promise;
  }
  return {
    client,
    receive,
    dispatch,
    deliver,
    ready,
    sent,
    tasks,
    freed: () => freed,
    terminated: () => terminated,
  };
}

test('queued completion followed by cancellation acknowledges without restarting the Worker', async (t) => {
  const f = await fixture();
  t.after(() => f.client.dispose());
  await f.ready();
  const promise = f.client.search(context);
  const rejected = assert.rejects(promise, /invalidated/);
  await Promise.resolve();
  await f.dispatch();
  for (const [id, fn] of f.tasks) {
    f.tasks.delete(id);
    fn();
  }
  assert.equal(f.sent[0].type, 'result');
  assert.equal(f.freed(), 1);
  f.client.cancel();
  await f.dispatch();
  assert.deepEqual(
    f.sent.map((message) => message.type),
    ['result', 'cancelled'],
  );
  f.deliver();
  await rejected;
  assert.equal(f.client.isReady, true);
  assert.equal(f.terminated(), 0);
  assert.equal(f.client.diagnostics().cancellationMs.length, 1);
});

test('stale generations and a different live request cannot acknowledge or free the search', async (t) => {
  const f = await fixture();
  t.after(() => f.client.dispose());
  await f.ready();
  await f.receive({
    type: 'start',
    payload: {
      schemaVersion: 1,
      meta: meta(2),
      snapshot: Array.from(context.snapshot),
      limits: context.limits,
      seed: '1',
    },
  });
  for (const request of [meta(2, 2), meta(1), { ...meta(2), revision: 1 }])
    await f.receive({ type: 'cancel', meta: request });
  assert.equal(f.sent.length, 0);
  assert.equal(f.freed(), 0);
  await f.receive({ type: 'cancel', meta: meta(2) });
  assert.equal(f.sent.length, 1);
  assert.equal(f.sent[0].type, 'cancelled');
  assert.equal(f.freed(), 1);
});

test('more than ten thousand cancellation acknowledgements retain bounded recent samples', async (t) => {
  const f = await fixture();
  t.after(() => f.client.dispose());
  await f.ready();
  for (let index = 0; index < 10005; index++) {
    const promise = f.client.search(context);
    const rejected = assert.rejects(promise, /invalidated/);
    await Promise.resolve();
    await f.dispatch();
    f.client.cancel();
    await f.dispatch();
    f.deliver();
    await rejected;
  }
  assert.equal(f.client.diagnostics().cancellationMs.length, 10000);
  assert.equal(f.terminated(), 0);
  assert.equal(f.freed(), 10005);
});

test('dispose terminates a pending Worker and late queued responses cannot restart or settle it', async () => {
  const f = await fixture();
  await f.ready();
  let progress = 0;
  const pending = f.client.search({
    ...context,
    onProgress: () => {
      progress++;
    },
  });
  const rejected = assert.rejects(pending, /invalidated/);
  await Promise.resolve();
  await f.dispatch();
  for (const [id, fn] of f.tasks) {
    f.tasks.delete(id);
    fn();
  }
  f.client.dispose();
  f.client.dispose();
  f.deliver();
  await rejected;
  assert.equal(f.terminated(), 1);
  assert.equal(f.client.isReady, false);
  assert.equal(progress, 0);
  await assert.rejects(f.client.startWorker(), /disposed/);
});
