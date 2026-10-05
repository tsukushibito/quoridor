'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { once } = require('node:events');
const { Worker } = require('../arena/protocol.cjs');
const script = __dirname + '/fake-transport.cjs';
const clock = () => Number(process.hrtime.bigint()) / 1e6;
const command = { kind: 'SEARCH', id: 1, generation: 1, key: 'position', history: 'history' };
const valid = (r) => ({ valid: r.search?.Action === 7 });
function worker(t, mode, options = {}) {
  const w = new Worker(mode, script, [], {
    closeGraceMs: 500,
    killGraceMs: 200,
    stopTimeoutMs: 400,
    ...options,
  });
  t.after(() => w.close());
  return w;
}
async function ready(w) {
  assert.equal((await w.take(1500)).type, 'READY');
}

test('positive caps and affinity are validated before spawning', () => {
  for (const name of [
    'maxQueueMessages',
    'maxQueueBytes',
    'maxReplyBytes',
    'maxRequestBytes',
    'stopTimeoutMs',
    'closeGraceMs',
  ])
    assert.throws(() => new Worker('normal', script, [], { [name]: 0 }), /TRANSPORT_OPTION/);
  for (const affinity of [[], [-1], [0, 0], [NaN]])
    assert.throws(() => new Worker('normal', script, [], { affinity }), /TRANSPORT_AFFINITY/);
  assert.throws(() => new Worker('normal', script, [], { spawnArgs: [1] }), /TRANSPORT_SPAWN_ARGS/);
});

test('affinity/spawnArgs work and stale identity is discarded before validation', async (t) => {
  const w = worker(t, 'stale', { affinity: [0], spawnArgs: ['--no-warnings'] });
  await ready(w);
  const r = await w.request(command, 500, valid, null, 25);
  assert.equal(r.status, 'RECEIVED');
  assert.equal(r.response.validation.valid, true);
  assert.equal(r.obsolete.length, 1);
  assert.equal(r.obsolete[0].reason, 'STALE_IDENTITY_DISCARD');
  assert.equal(r.response.deadline_ms, r.t0_ms + 475);
  assert.equal((await w.close()).waited, true);
});

test('one pending waiter and one request per worker', async (t) => {
  const w = worker(t, 'delayed');
  await ready(w);
  const pending = w.take(200);
  await assert.rejects(w.take(100), /WAITER_CONCURRENCY/);
  await assert.rejects(w.request(command, 100), /REQUEST_CONCURRENCY/);
  assert.equal((await pending).type, 'WAIT_TIMEOUT');
  const request = w.request(command, 500, valid);
  await assert.rejects(w.request(command, 500), /REQUEST_CONCURRENCY/);
  await assert.rejects(w.take(100), /WAITER_CONCURRENCY/);
  assert.equal((await request).status, 'RECEIVED');
});

test('late result is not adopted and is recorded by stop', async (t) => {
  const w = worker(t, 'late');
  await ready(w);
  const r = await w.request(command, 40, valid);
  assert.equal(r.status, 'OUTER_DEADLINE');
  assert.equal(r.response, null);
  const stop = await w.stop(2);
  assert.equal(stop.status, 'STOP_ACK');
  assert.equal(stop.discarded_late_responses.length, 1);
  assert.equal(stop.discarded_late_responses[0].adopted, false);
});

test('complete parse plus validation is inside the outer clock', async (t) => {
  const w = worker(t, 'normal');
  await ready(w);
  const r = await w.request(command, 40, () => {
    const end = clock() + 60;
    while (clock() < end) {}
    return { valid: true };
  });
  assert.equal(r.status, 'OUTER_DEADLINE');
  assert.ok(r.elapsed_ms >= 60);
});

test('broken stdin produces typed failure and owned collection', async (t) => {
  const w = worker(t, 'closed-stdin');
  await ready(w);
  const r = await w.request({ ...command, payload: 'x'.repeat(65536) }, 500);
  assert.equal(r.status, 'STDIN_ERROR');
  const cleanup = await w.close();
  assert.equal(cleanup.waited, true);
  assert.equal(cleanup.failure.type, 'STDIN_ERROR');
});

for (const options of [{ maxQueueMessages: 2 }, { maxQueueBytes: 80 }]) {
  test('queue overflow is typed and bounded ' + JSON.stringify(options), async (t) => {
    const w = worker(t, 'flood', options);
    // Startup burst must be observed before a consumer can drain it.
    await once(w.p.stdout, 'data');
    const message = await w.take(500);
    assert.equal(message.type, 'QUEUE_CAP');
    assert.equal(w.queueBytes, 0);
    const cleanup = await w.close();
    assert.equal(cleanup.waited, true);
  });
}

for (const mode of ['large-line', 'unterminated-large', 'malformed']) {
  test('invalid/oversized reply reaps owned child: ' + mode, async (t) => {
    const w = worker(t, mode, { maxReplyBytes: 128 });
    const message = await w.take(1000);
    assert.equal(message.type, mode === 'malformed' ? 'SCHEMA_ERROR' : 'REPLY_CAP');
    assert.equal(w.pending.length, 0);
    assert.equal((await w.close()).waited, true);
  });
}

test('request byte overflow and stale metadata byte overflow are bounded', async (t) => {
  const w = worker(t, 'normal', { maxRequestBytes: 128 });
  await ready(w);
  assert.equal(
    (await w.request({ ...command, payload: 'x'.repeat(1000) }, 500)).status,
    'REQUEST_CAP',
  );
  assert.equal((await w.close()).waited, true);
  const stale = worker(t, 'stale-bytes', { maxQueueBytes: 450 });
  await ready(stale);
  const r = await stale.request(command, 500);
  assert.equal(r.status, 'QUEUE_CAP');
  assert.ok(r.obsolete.length <= 2);
  assert.equal((await stale.close()).waited, true);
});

test('spawn error has no invented pid or signal and still observes close', async (t) => {
  const w = worker(t, 'normal', { executable: '/nonexistent-owned-transport-fixture' });
  assert.equal((await w.take(500)).type, 'PROCESS_ERROR');
  const c = await w.close();
  assert.equal(c.waited, true);
  assert.equal(c.spawned, false);
  assert.equal(c.owned_pid, null);
  assert.deepEqual(c.signals, []);
});

test('exit is distinct from stdio close and repeated close is idempotent', async (t) => {
  const w = worker(t, 'delayed-stdio');
  await ready(w);
  const exiting = once(w.p, 'exit');
  const first = w.close();
  const second = w.close();
  await exiting;
  assert.equal(w.closed, null);
  const [a, b] = await Promise.all([first, second]);
  assert.equal(a.waited, true);
  assert.equal(b.waited, true);
  assert.ok(a.wall_ms >= 150);
  assert.deepEqual(a.signals, []);
  assert.deepEqual((await w.close()).signals, []);
});

test('unresponsive owned child is TERM/KILL collected after bounded stop', async (t) => {
  const w = worker(t, 'ignore-stop', { stopTimeoutMs: 40, killGraceMs: 80 });
  await ready(w);
  const stop = await w.stop(2);
  assert.equal(stop.status, 'STOP_TIMEOUT_KILLED');
  assert.equal(stop.cleanup.waited, true);
  assert.deepEqual(
    stop.cleanup.signals.map((s) => s.signal),
    ['SIGTERM', 'SIGKILL'],
  );
  assert.ok(stop.cleanup.signals.every((s) => s.pid === w.p.pid));
});

test('close cancels pending request without adopting output; EOF is explicit', async (t) => {
  const w = worker(t, 'delayed');
  await ready(w);
  const pending = w.request(command, 500);
  const cleanup = await w.close();
  assert.equal((await pending).status, 'CLOSING');
  assert.equal(cleanup.waited, true);
  const eof = worker(t, 'eof');
  await ready(eof);
  assert.equal((await eof.request(command, 500)).status, 'EOF');
  assert.equal((await eof.close()).waited, true);
});
