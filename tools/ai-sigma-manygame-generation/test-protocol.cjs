'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');
const { execFileSync } = require('child_process');
const I = require('../ai-sigma-common/generation/identity.cjs');
const { Broker } = require('../ai-sigma-common/generation/batch-broker.cjs');
const { GamePool } = require('../ai-sigma-common/generation/game-pool.cjs');
const { WorkerBroker } = require('../ai-sigma-common/generation/worker-broker.cjs');
const { Pipe } = require('../ai-sigma-common/process/json-line.cjs');
const { WorkerClient, sameProcess } = require('../ai-sigma-common/process/worker-client.cjs');
const { OwnedTree } = require('../ai-sigma-common/process/owned-tree.cjs');
const schema = require('../ai-sigma-common/generation/teacher-schema.cjs');
const { record } = require('../ai-sigma-common/generation/diagnostic-record.cjs');
const { ArtificialRegistry } = require('./mock-registry.cjs');
const { validateConfig, checkStart } = require('./config.cjs');

const ORACLE_GIT = '1811919718a1837b376a148291e0d43c3e9dd683';
function oracle(name, local = {}) {
  const source = execFileSync('git', ['show', ORACLE_GIT + ':tools/ai-sigma-manygame-generation/' + name], {
    cwd: path.resolve(__dirname, '../..'), encoding: 'utf8', maxBuffer: 256 * 1024,
  });
  const module = { exports: {} };
  vm.runInNewContext(source, {
    module, exports: module.exports, require: name => local[name] ?? require(name),
    setTimeout, clearTimeout, setImmediate, Float32Array, Uint32Array, console,
  }, { filename: name });
  return module.exports;
}

const id = (game, token = 1) => ({
  run_id: 'diagnostic', worker_id: 'w0', game_id: game,
  generation: 7, handle: 1, token, request_id: game + '.' + token,
});
const features = () => Array(648).fill(0);
function response(request) {
  const marker = new Float32Array(new Uint32Array(request.features_bits648.slice(0, 1)).buffer)[0];
  const logits = Array(136).fill(0);
  logits[0] = marker;
  const value = Math.fround(marker / 1000);
  return { id: request.id, logits, value, f32bits137: Array.from(new Uint32Array(new Float32Array([...logits, value]).buffer)) };
}

test('identity preserves the old wire contract and rejects non-finite feature bits', () => {
  const old = oracle('identity.cjs');
  assert.equal(JSON.stringify(I.validate(id('a'))), JSON.stringify(old.validate(id('a'))));
  assert(Object.isFrozen(I.validate(id('a'))));
  for (const bad of [{ ...id('a'), token: -1 }, { ...id('a'), worker_id: '' }]) {
    assert.throws(() => I.validate(bad), /IDENTITY_SCHEMA/);
  }
  const bits = features();
  bits[0] = 0x80000000; // negative zero is a finite float32 bit pattern.
  assert.equal(I.features(bits), bits);
  bits[0] = 0x7f800000;
  assert.throws(() => I.features(bits), /FEATURE_SCHEMA/);
});

test('batch broker supports every partial batch and preserves request attribution', async () => {
  for (let B = 1; B <= 8; B++) {
    const batches = [];
    const broker = new Broker(async rows => { batches.push(rows); return rows.map(response); });
    const results = await Promise.all(Array.from({ length: B }, (_, i) => broker.infer(id('g' + i), features())));
    await broker.quiescent();
    assert.equal(batches.length, 1);
    assert.equal(batches[0].length, B);
    assert(results.every((row, i) => I.key(row.identity) === I.key(id('g' + i))));
    broker.stop();
    assert.equal(broker.zero().pending_games, 0);
  }
});

test('cancel keeps physical in-flight ownership and rejects stale generation', async () => {
  let returnProvider;
  const broker = new Broker(rows => new Promise(resolve => { returnProvider = () => resolve(rows.map(response)); }), {
    maxBatch: 1, maxPendingGames: 2,
  });
  const pending = broker.infer(id('g'), features()).catch(error => error.message);
  assert.equal(broker.cancel('w0', 'g', 6, 'diagnostic').error, 'STALE_CANCEL_GENERATION');
  assert(broker.cancel('w0', 'g', 7, 'diagnostic').inflight);
  await assert.rejects(() => broker.infer(id('g', 2), features()), /ONE_PENDING_PER_GAME/);
  assert.equal(broker.zero().pending_games, 1);
  returnProvider();
  assert.equal(await pending, 'CANCEL_RETURN_DISCARDED');
  await broker.quiescent();
  assert.equal(broker.zero().pending_games, 0);
  assert.equal(broker.stats.discarded, 1);
});

test('queued cancel and sample cap refuse before a provider call', async () => {
  let calls = 0;
  const broker = new Broker(async rows => { calls++; return rows.map(response); }, { replyCap: 1 });
  const queued = broker.infer(id('queued'), features()).catch(error => error.message);
  broker.cancel('w0', 'queued', 7, 'diagnostic');
  assert.equal(await queued, 'CANCEL_QUEUED');
  await Promise.all(['a', 'b'].map(game => broker.infer(id(game), features()).catch(error => error.message)));
  await broker.quiescent();
  assert.equal(calls, 0);
  assert.equal(broker.stats.started, 0);
  assert.equal(broker.fault, 'SAMPLE_CAP');
});

test('unknown attribution or bad float32 output quarantines every affected request', async () => {
  for (const fault of ['id', 'float32']) {
    const broker = new Broker(async rows => {
      const answers = rows.map(response);
      if (fault === 'id') answers[0].id = 'unknown';
      else answers[0].f32bits137[0] = 1;
      return answers;
    });
    const statuses = await Promise.all(Array.from({ length: 12 }, (_, i) => (
      broker.infer(id('g' + i), features()).catch(error => error.message)
    )));
    await broker.quiescent();
    assert(statuses.every(status => typeof status === 'string' && status.startsWith('PROVIDER_OR_CONTROL_UNKNOWN:')));
    assert.equal(broker.zero().pending_games, 0);
    await assert.rejects(() => broker.infer(id('after'), features()));
  }
});

test('game pool preserves old synthetic search output, has no frame default and frees exact trees', async () => {
  const oldIdentity = oracle('identity.cjs');
  const old = oracle('gamepool.cjs', { './identity.cjs': oldIdentity });
  const output = async (Pool, Registry) => {
    const registry = new Registry();
    const broker = new Broker(async rows => rows.map(response));
    const pool = new Pool('w0', registry, broker, { run: 'diagnostic', maxHandles: 4 });
    const result = await pool.search('g', { K: 3 });
    assert.equal(registry.trees.size, 0);
    assert.equal(pool.games.size, 0);
    await broker.quiescent();
    broker.stop();
    return JSON.stringify(result);
  };
  assert.equal(await output(GamePool, ArtificialRegistry), await output(old.GamePool, old.ArtificialRegistry));
  assert.throws(() => new GamePool('w0', {}, {}), /POOL_CONFIG/);
});

test('backend cancel failure still attempts free, never reports cleanup success', async () => {
  const freed = [];
  const backend = {
    new: async () => 17, begin: async () => ({ done: true }),
    checkpoint: async () => ({ root_visits: 0, simulations: 0 }),
    cancel: async () => { throw Error('CANCEL_UNKNOWN'); }, free: async handle => freed.push(handle),
  };
  const pool = new GamePool('w0', backend, {}, { run: 'diagnostic' });
  await assert.rejects(() => pool.search('g'), /CANCEL_UNKNOWN/);
  assert.deepEqual(freed, [17]);
  assert.equal(pool.games.size, 0);
});

test('worker IPC rejects duplicate/stale token and waits for the explicit drain acknowledgement', async () => {
  const sent = [], broker = new WorkerBroker(message => sent.push(message));
  const pending = broker.infer(id('g'), features());
  await assert.rejects(() => broker.infer(id('g'), features()), /DUPLICATE_REQUEST_ID/);
  broker.handle({ kind: 'reply', request_id: 'unknown', data: {} });
  assert.equal(broker.pending.size, 1);
  broker.handle({ kind: 'reply', request_id: id('g').request_id, data: { identity: id('g', 2) } });
  await assert.rejects(() => pending, /REPLY_IDENTITY/);
  const drained = broker.quiescentGame('w0', 'g', 'diagnostic');
  const request = sent.at(-1);
  broker.handle({ kind: 'drained', id: 'unknown' });
  assert.equal(broker.waits.size, 1);
  broker.handle({ kind: 'drained', id: request.id });
  await drained;
  assert.equal(broker.waits.size, 0);
});

test('teacher schema target conventions match frozen recipe and diagnostics stay ineligible', () => {
  const old = oracle('schema.cjs');
  for (const side of [1, 2]) {
    for (const winner of [null, 0, 1, 2]) {
      assert.equal(JSON.stringify(schema.target({ side }, winner)), JSON.stringify(old.target({ side }, winner)));
    }
  }
  const diagnostic = record({ game_id: 'g', cp: { root_visits: 2, root_edges: [[8, 0, 1]] } }, {
    mapping136: [[8, 3]], lineage: 'diagnostic',
  });
  assert.equal(diagnostic.pi136[3], 1);
  assert.equal(diagnostic.z_stm, null);
  assert(!diagnostic.policy_eligible && !diagnostic.value_eligible && !diagnostic.joint_eligible);
});

function configuration() {
  return {
    run_id: 'fixture', issue: 'fixture-issue', owner: 'fixture-owner', goal_issue: 'fixture-goal',
    mode: 'RustCPU', openings_path: '/tmp/explicit-openings', job_out: '/tmp/explicit-new-run',
    beads_wrapper: '/explicit/beads.sh', heavy_start_cutoff_utc: '2027-01-01T00:00:00Z',
    science_deadline: '2027-01-01T00:10:00Z', window_end_utc: '2027-01-01T00:15:00Z',
    job_seconds: 30, cleanup_seconds: 5, active_per_worker: 2,
    workers: [{ cpu: 1, worker_id: 'w1', game_ids: ['g1', 'g2'] }],
    runtime: {
      python: '/explicit/python', model: '/explicit/model', nativeBridge: '/explicit/bridge',
      ortScript: '/explicit/ort.py', pipeTimeoutMs: 100, expectedORTVersion: 'fixture-version',
    },
    teacher: { K: 64, sampleCap: 128, maxNewPlies: 200, temperaturePlies: 16,
      modelSHA256: '0'.repeat(64), providerLabel: 'fixture', searchLabel: 'fixture' },
    resources: { ram_guard_bytes: 1024 * 1024, output_cap_bytes: 1024 * 1024,
      management_cpu_count: 1, management_cpu: 1, logical_cpu_limit: 2 },
    broker: { maxBatch: 8, maxPendingGames: 24, replyCap: 128, flushMs: 0.25 },
  };
}

test('config requires explicit environment, scientific settings, ownership and stop clocks', () => {
  const raw = configuration();
  assert.deepEqual(validateConfig(raw), raw);
  for (const field of ['runtime', 'teacher', 'science_deadline', 'owner', 'resources', 'openings_path']) {
    const bad = structuredClone(raw); delete bad[field];
    assert.throws(() => validateConfig(bad), /CONFIG_/);
  }
  const duplicate = configuration();
  duplicate.workers.push({ cpu: 2, worker_id: 'w2', game_ids: ['g1'] });
  assert.throws(() => validateConfig(duplicate), /GAME_ASSIGNMENT_DUPLICATE/);
  assert.throws(() => checkStart(raw, Date.parse(raw.heavy_start_cutoff_utc)), /NEWHEAVY_CUTOFF/);
  assert.throws(() => checkStart(raw, Date.parse(raw.science_deadline) - 1000), /NEWHEAVY_CUTOFF/);
});

test('FIFO pipe serializes requests and close waits for the exact child', async () => {
  const script = "require('readline').createInterface({input:process.stdin}).on('line',s=>console.log(s))";
  const pipe = new Pipe(process.execPath, ['-e', script]);
  const tree = new OwnedTree();
  const expected = require('../ai-sigma-common/process/worker-client.cjs').procIdentity(pipe.child.pid);
  tree.add(expected);
  assert(tree.sample().some(row => row.pid === pipe.child.pid));
  const values = await Promise.all([1, 2, 3].map(index => pipe.ask({ index })));
  assert.deepEqual(values, [{ index: 1 }, { index: 2 }, { index: 3 }]);
  const exit = await pipe.close();
  assert.equal(exit.code, 0);
  assert.equal(tree.sample().length, 0);
  assert(!sameProcess(expected));
});

test('timeout quarantines queued requests; SIGTERM-resistant owned child is reclaimed', async () => {
  const script = "process.on('SIGTERM',()=>{});process.stdin.resume();setInterval(()=>{},1000)";
  const pipe = new Pipe(process.execPath, ['-e', script], { timeoutMs: 50, closeGraceMs: 10, killGraceMs: 10 });
  const statuses = await Promise.all([1, 2].map(value => pipe.ask({ value }).catch(error => error.message)));
  assert.deepEqual(statuses, ['PIPE_TIMEOUT', 'PIPE_TIMEOUT']);
  const exit = await pipe.close();
  assert.equal(exit.signal, 'SIGKILL');
});

test('spawn failure produces a close receipt and does not leave a waiting child promise', async () => {
  const pipe = new Pipe('/definitely/not/a/command');
  await assert.rejects(() => pipe.ask({}), /ENOENT/);
  const exit = await pipe.close();
  assert.equal(exit.code, -2);
});

test('worker client dispatch/unknown-message routing and exact owned close use real IPC without NN', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'quoridor-protocol-test-'));
  const script = path.join(directory, 'worker.cjs');
  fs.writeFileSync(script, "process.on('message',q=>{if(q.op==='close'){process.send({id:q.id,data:{closed:true}});process.disconnect()}else process.send({id:q.id,data:q.op})})");
  const client = new WorkerClient({ script, cpu: 1, output: directory, timeoutMs: 1000, onMessage: () => false });
  try {
    assert.equal(await client.ask('synthetic'), 'synthetic');
    assert.deepEqual(await client.ask('close'), { closed: true });
    const exit = await client.exit;
    assert.equal(exit.code, 0);
    assert(!sameProcess(client.identity));
  } finally {
    if (sameProcess(client.identity)) await client.recover(50);
    fs.rmSync(directory, { recursive: true });
  }
});

test('real generation worker rejects missing runtime before any initialization or model call', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'quoridor-worker-config-test-'));
  const client = new WorkerClient({ script: path.join(__dirname, 'worker.cjs'), cpu: 1,
    output: directory, timeoutMs: 1000, onMessage: () => false });
  try {
    await assert.rejects(() => client.ask('init', { mode: 'RustCPU', run: 'fixture' }), /CONFIG_RUNTIME_TEACHER_REQUIRED/);
    const closed = await client.ask('close');
    assert.equal(closed.usedNN, 0);
    assert.equal(closed.startup_NN, 0);
    assert.deepEqual(closed.exits, []);
    assert.equal((await client.exit).code, 0);
  } finally {
    if (sameProcess(client.identity)) await client.recover(50);
    fs.rmSync(directory, { recursive: true });
  }
});

test('model provenance mismatch refuses the new driver before output or child start', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'quoridor-generation-config-test-'));
  try {
    const config = configuration();
    config.runtime.model = path.join(directory, 'synthetic-model-bytes');
    config.openings_path = path.join(directory, 'openings.json');
    config.job_out = path.join(directory, 'must-not-be-created');
    fs.writeFileSync(config.runtime.model, 'not a model; provenance fixture only');
    fs.writeFileSync(config.openings_path, JSON.stringify({ games: [{ game_id: 'g1' }, { game_id: 'g2' }] }));
    const child = require('node:child_process').spawnSync('taskset', ['-c', String(config.resources.management_cpu), process.execPath, '-e', "require(process.argv[1]).generate(JSON.parse(process.argv[2])).catch(e=>{console.error(e.message);process.exitCode=2;});", path.join(__dirname,'generate-run.cjs'), JSON.stringify(validateConfig(config))], {encoding:'utf8', timeout:5000});
    assert.equal(child.status, 2);
    assert.match(child.stderr, /MODEL_SHA_CHANGED/);
    assert(!fs.existsSync(config.job_out));
  } finally {
    fs.rmSync(directory, { recursive: true });
  }
});

test('VRAM accounting parser rejects unknown/external owners without invoking a GPU tool', () => {
  const { parseUsage, checkUsage } = require('../ai-sigma-common/process/gpu-guard.cjs');
  const rows = parseUsage('17, 12 MiB\n18, 3 MiB\n');
  assert.deepEqual(rows, [{ pid: 17, bytes: 12 * 1024 ** 2 }, { pid: 18, bytes: 3 * 1024 ** 2 }]);
  assert.throws(() => parseUsage('17, N/A'), /GPU_USAGE_UNKNOWN/);
  assert.throws(() => checkUsage(rows, new Set([17]), 16 * 1024 ** 2), /EXTERNAL_GPU_CURRENT_UNKNOWN/);
  assert.throws(() => checkUsage(rows, new Set([17, 18]), 15 * 1024 ** 2), /GPU_VRAM_GUARD/);
  assert.doesNotThrow(() => checkUsage(rows, new Set([17, 18]), 16 * 1024 ** 2));
});

test('expired or paused run-control refuses before starting a wrapper read', () => {
  const { RunControl } = require('../ai-sigma-common/process/run-control.cjs');
  const expired = new RunControl({ wrapper: '/must-not-be-executed', deadline: Date.now() - 1,
    pausePath: '/not-a-pause-file', onFailure: () => {} });
  assert.throws(() => expired.readIssue('fixture'), /PROCESSING_DEADLINE/);
  const pauseFile = fs.mkdtempSync(path.join(os.tmpdir(), 'quoridor-paused-test-'));
  try {
    const paused = new RunControl({ wrapper: '/must-not-be-executed', deadline: Date.now() + 1000,
      pausePath: pauseFile, onFailure: () => {} });
    assert.throws(() => paused.readIssue('fixture'), /PAUSED/);
  } finally {
    fs.rmSync(pauseFile, { recursive: true });
  }
});
