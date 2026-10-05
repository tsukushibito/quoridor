'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { Engine } = require('../controller.cjs');
const { OwnedProcesses, identity } = require('../process.cjs');
const os = require('node:os');
const fixture = path.join(__dirname, 'fake-controller.cjs');

function running(row) {
  try {
    const fields = fs
      .readFileSync(`/proc/${row.pid}/stat`, 'utf8')
      .split(')')
      .at(-1)
      .trim()
      .split(/\s+/);
    return Number(fields[19]) === row.start_ticks && fields[0] !== 'Z';
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

function fixtureEngine(mode) {
  return new Engine('reference', null, {
    workerScript: fixture,
    fixtureMode: mode,
    pipeTimeoutMs: 200,
  });
}

for (const mode of ['timeout', 'json', 'unknown', 'exit']) {
  test(`controller ${mode} rejects pending work and recalls the declared owned descendant`, async () => {
    const engine = fixtureEngine(mode);
    const info = await engine.init(true);
    const pending = engine.request({ op: 'search' });
    await assert.rejects(() => pending);
    const firstClose = engine.close();
    assert.equal(firstClose, engine.close());
    const close = await firstClose;
    assert.deepEqual(close.ownership.remaining, []);
    assert(close.ownership.owned.some((row) => row.pid === info.descendant.pid));
    assert(!running(info.descendant));
    assert.equal(engine.pending.size, 0);
    assert(engine.fault);
  });
}

test('close during active IPC waits for cancellation and child close instead of CLOSE_ACTIVE', async () => {
  const engine = fixtureEngine('healthy');
  const info = await engine.init(true);
  const active = engine.request({ op: 'search' });
  const close = await engine.close();
  assert.equal((await active).data.cancelled, true);
  assert.equal(close.receipt.children_closed, true);
  assert.equal(close.exit.code, 0);
  assert.deepEqual(close.ownership.remaining, []);
  assert(!running(info.descendant));
});

test('current worker prevents duplicate init and rejects unspecified/non-finite search budgets before search', async () => {
  const engine = new Engine('reference', null, { pipeTimeoutMs: 1000 });
  const info = await engine.init(true);
  assert.equal(info.mock, true);
  await assert.rejects(() => engine.init(true), /INIT_ALREADY_STARTED/);
  const valid = {
    op: 'search',
    legal_prefix: [],
    K: 1,
    generation: 1,
    NN_limit: 0,
    watchdog_ms: 100,
    mock: {},
  };
  for (const field of ['K', 'generation', 'NN_limit', 'watchdog_ms']) {
    const request = { ...valid };
    delete request[field];
    await assert.rejects(() => engine.request(request), new RegExp('SEARCH_CONFIG_' + field));
    await assert.rejects(
      () => engine.request({ ...valid, [field]: null }),
      new RegExp('SEARCH_CONFIG_' + field),
    );
  }
  const close = await engine.close();
  assert.equal(close.receipt.NN_total, 0);
  assert.equal(close.receipt.startup_separate, 0);
  assert.equal(close.exit.code, 0);
  assert.deepEqual(close.ownership.remaining, []);
});

test('ownership declaration refuses a live unrelated process and never signals it', async () => {
  const sibling = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { stdio: 'ignore' });
  const siblingIdentity = identity(sibling.pid);
  const engine = new Engine('reference', null, { pipeTimeoutMs: 1000 });
  try {
    await engine.init(true);
    const owner = identity(engine.child.pid);
    const owned = new OwnedProcesses(owner);
    assert.throws(
      () => owned.declare({ ...siblingIdentity, ppid: owner.pid }, owner),
      /PROCESS_PARENT_CURRENT_MISMATCH/,
    );
    assert(running(siblingIdentity));
  } finally {
    await engine.close();
    const exited = new Promise((resolve) => sibling.once('close', resolve));
    sibling.kill('SIGTERM');
    await exited;
  }
});

test('canonical candidate cancellation joins the active bridge and frees it before child pipe close', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'quoridor-controller-bridge-'));
  const fixtureLog = path.join(directory, 'ops.txt');
  const { r } = require('../reference.cjs').createReference();
  const root = r.portState(r.fromPrefix([]));
  const engine = new Engine('new', null, {
    pipeTimeoutMs: 1000,
    nativeBridge: fixture,
    fixtureMode: 'bridge',
    fixtureLog,
    fixtureRoot: { features_bits: root.features_bits, effective_legal: root.legal },
  });
  try {
    const info = await engine.init(true);
    const child = info.identities.find((row) => row.pid !== engine.child.pid);
    await assert.rejects(() => engine.init(true), /INIT_ALREADY_STARTED/);
    assert(running(child));
    const active = engine.request({
      op: 'search',
      K: 1,
      generation: 1,
      NN_limit: 0,
      watchdog_ms: 500,
      legal_prefix: [],
      mock: {},
    });
    const limit = Date.now() + 500;
    while (
      (!fs.existsSync(fixtureLog) || !fs.readFileSync(fixtureLog, 'utf8').includes('begin')) &&
      Date.now() < limit
    ) {
      await new Promise((resolve) => setTimeout(resolve, 5));
    }
    assert(fs.readFileSync(fixtureLog, 'utf8').includes('begin'));
    const close = await engine.close();
    const result = (await active).data;
    assert.equal(result.NN_calls, 0);
    assert.equal(result.completed, 0);
    const ops = fs.readFileSync(fixtureLog, 'utf8').trim().split('\n');
    assert.deepEqual(ops, ['raw', 'new', 'begin', 'cancel', 'free']);
    assert.equal(close.exit.code, 0);
    assert.equal(close.receipt.NN_total, 0);
    assert.equal(close.receipt.exit[0].code, 0);
    assert(!running(child));
    assert.deepEqual(close.ownership.remaining, []);
  } finally {
    await engine.close();
    fs.rmSync(directory, { recursive: true });
  }
});

test('stdio close unknown returns a bounded receipt without inventing collection', async () => {
  const engine = Object.create(Engine.prototype);
  Object.assign(engine, {
    timeout: 15,
    child: { stdin: { destroyed: true } },
    closed: false,
    fault: Error('fixture refusal'),
    owned: { recover: async () => ({ remaining: [], unresolved: [{ reason: 'unproven child' }] }) },
    exit: new Promise(() => {}),
    err: '',
    observer: null,
  });
  const result = await engine.closeOwned();
  assert.equal(result.exit, null);
  assert.equal(result.stdio_collected, false);
  assert.equal(result.error, 'STDIO_COLLECTION_TIMEOUT');
  assert.equal(result.ownership.unresolved.length, 1);
});
