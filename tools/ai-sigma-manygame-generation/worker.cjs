'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { performance } = require('perf_hooks');
const { validateWorkerSettings } = require('./config.cjs');
const { WorkerBroker } = require('../ai-sigma-common/generation/worker-broker.cjs');
const { Pipe } = require('../ai-sigma-common/process/json-line.cjs');
const { GamePool } = require('../ai-sigma-common/generation/game-pool.cjs');
const { Broker } = require('../ai-sigma-common/generation/batch-broker.cjs');
const { target, validate } = require('../ai-sigma-common/generation/teacher-schema.cjs');
const { Engine } = require('../ai-sigma-native/controller.cjs');
const { r } = require('../ai-sigma-native/reference.cjs').createReference();

const core = Number(process.argv[2]);
const out = process.argv[3];
let worker = 'w' + core;
let settings, mode, datasetMode, run, engine, rust, ort, pool, broker;
let aborted = false;
let usedNN = 0,
  generation = 0,
  API_ms = 0,
  pipe_ms = 0,
  startup = 0;
fs.mkdirSync(out, { recursive: true });
const save = (name, value) => fs.writeFileSync(path.join(out, name), JSON.stringify(value) + '\n');
const append = (name, value) =>
  fs.appendFileSync(path.join(out, name), JSON.stringify(value) + '\n');
const remote = new WorkerBroker((message) => process.send(message));

function unwrap(response) {
  if (!response.ok) throw Error(response.error?.message ?? response.error);
  return response.data;
}

class Registry {
  async call(request) {
    return unwrap(await rust.ask(request));
  }
  async new(fixture, generation, K) {
    let state = r.fromPrefix([]);
    const prefix = [];
    for (const action of fixture.legal_prefix) {
      prefix.push(r.rustAction(state, action));
      state = state.next(action);
    }
    return (await this.call({ op: 'new', prefix, simulations: K, generation, trace: false }))
      .handle;
  }
  begin(handle, generation) {
    return this.call({ op: 'begin', handle, generation });
  }
  resume(handle, generation, token, NN) {
    return this.call({
      op: 'resume',
      handle,
      generation,
      token,
      logits: NN.logits,
      value: NN.value,
    });
  }
  checkpoint(handle, generation) {
    return this.call({ op: 'checkpoint', handle, generation });
  }
  cancel(handle, generation) {
    return this.call({ op: 'cancel', handle, generation });
  }
  free(handle) {
    return this.call({ op: 'free', handle });
  }
}

async function init(request) {
  settings = validateWorkerSettings(request, request.mode);
  mode = request.mode;
  datasetMode = request.datasetMode ?? mode;
  run = request.run;
  worker = request.worker_id ?? worker;
  const started = performance.now();
  let info;
  if (mode === 'CPUJS') {
    engine = new Engine('reference', settings.runtime.model, settings.runtime);
    info = await engine.init(false);
    assert.equal(info.info.version, settings.runtime.expectedORTVersion);
    assert.deepStrictEqual(info.info.affinity, [core]);
    startup = 1;
  } else {
    rust = new Pipe(settings.runtime.nativeBridge, [], {
      timeoutMs: settings.runtime.pipeTimeoutMs,
    });
    if (mode === 'RustCPU') {
      ort = new Pipe(
        settings.runtime.python,
        ['-u', settings.runtime.ortScript, settings.runtime.model],
        {
          timeoutMs: settings.runtime.pipeTimeoutMs,
        },
      );
      info = unwrap(await ort.ask({ op: 'info' }));
      assert.equal(info.version, settings.runtime.expectedORTVersion);
      assert.deepStrictEqual(info.providers, ['CPUExecutionProvider']);
      assert.deepStrictEqual(info.affinity, [core]);
      broker = new Broker(
        async (items) => {
          const rows = [];
          for (const item of items) {
            const started = performance.now();
            const NN = unwrap(await ort.ask({ op: 'infer', features_bits: item.features_bits648 }));
            API_ms += NN.API_ms;
            pipe_ms += performance.now() - started;
            rows.push({ id: item.id, logits: NN.logits, value: NN.value, f32bits137: NN.NN_bits });
          }
          return rows;
        },
        { ...request.broker, replyCap: settings.teacher.sampleCap },
      );
    } else broker = remote;
    pool = new GamePool(worker, new Registry(), broker, {
      run,
      maxHandles: request.active_per_worker,
    });
  }
  save('init.json', { info, mode, startup_NN: startup, wall_ms: performance.now() - started });
  return { info, mode, startup_NN: startup };
}

async function search(spec, state, prefix) {
  const currentGeneration = ++generation,
    started = performance.now(),
    K = settings.teacher.K;
  let data;
  if (mode === 'CPUJS') {
    let checkpoints = 0;
    const answer = await engine.request(
      {
        op: 'search',
        legal_prefix: prefix,
        generation: currentGeneration,
        K,
        final_only: true,
        NN_limit: settings.teacher.sampleCap - usedNN,
        watchdog_ms: settings.runtime.pipeTimeoutMs,
        trace: false,
      },
      () => checkpoints++,
    );
    data = answer.data;
    usedNN += data.NN_calls;
    assert(!data.primary, data.primary?.message);
    assert.equal(checkpoints, 1);
    assert.equal(JSON.stringify(data.root_state), JSON.stringify(r.portState(state)));
    API_ms += data.spans.reduce((sum, span) => sum + span.API_ms, 0);
    pipe_ms += data.spans.reduce((sum, span) => sum + span.pipe_ms, 0);
  } else {
    const result = await pool.search(spec.game_id, {
      K,
      generation: currentGeneration,
      fixture: { legal_prefix: prefix },
    });
    usedNN += result.counters.started;
    if (result.typed) throw Error(result.typed);
    data = {
      cp: result.cp,
      first_NN: result.first_NN,
      last_leafNN: result.last_leafNN,
      NN_calls: result.counters.returned,
      discardedNN: result.counters.discarded,
      terminal_noNN:
        result.counters.completed - (result.counters.returned - result.counters.discarded),
    };
    const root = r.portState(state);
    assert(result.firstPending, 'ROOT_NN_MISSING');
    for (const field of ['key', 'legal', 'turn', 'ply']) {
      assert.equal(
        JSON.stringify(result.firstPending[field]),
        JSON.stringify(root[field]),
        'ROOT_BINDING_' + field,
      );
    }
    const canonical = (values) =>
      [...values].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
    assert.equal(
      JSON.stringify(canonical(result.firstPending.history)),
      JSON.stringify(canonical(root.history)),
      'ROOT_BINDING_HISTORY_MEMBERSHIP_COUNTS',
    );
    assert.equal(JSON.stringify(result.first_NN.features_bits), JSON.stringify(root.features_bits));
  }
  assert(!aborted, 'CONTROL_ABORT');
  assert(data.cp && data.cp.root_visits === K && data.cp.simulations === K, 'SEARCH_K_INCOMPLETE');
  return { ...data, wall_ms: performance.now() - started };
}

function randomGenerator(seed) {
  let value = parseInt(seed.slice(0, 8), 16) || 1;
  return () => {
    value ^= value << 13;
    value ^= value >>> 17;
    value ^= value << 5;
    value >>>= 0;
    return value / 4294967296;
  };
}

function chooseAction(checkpoint, edgeSum, newPly, random) {
  if (newPly < settings.teacher.temperaturePlies) {
    let remaining = random() * edgeSum;
    for (const edge of checkpoint.root_edges) {
      remaining -= edge[2];
      if (remaining < 0) return edge[0];
    }
  } else {
    const maximum = Math.max(...checkpoint.root_edges.map((edge) => edge[2]));
    return checkpoint.root_edges.find((edge) => edge[2] === maximum)[0];
  }
}

function teacherRow(spec, state, data, newPly, random) {
  const checkpoint = data.cp,
    legal = state.getLegalActions();
  const mapping = legal.map((action) => {
    const index = r.actionToIndex(action, 9);
    return [
      r.rustAction(state, action),
      state.getCurrentPlayer() === 2 ? r.vertPolicyPermutation(9)[index] : index,
    ];
  });
  const order = mapping.map((entry) => entry[0]),
    visits = Array(136).fill(0);
  assert.equal(
    JSON.stringify(checkpoint.root_edges.map((edge) => edge[0])),
    JSON.stringify(order),
    'LEGAL_ORDER',
  );
  for (const [action, , count] of checkpoint.root_edges) {
    const entry = mapping.find((entry) => entry[0] === action);
    assert(entry);
    visits[entry[1]] = count;
  }
  const edgeSum = visits.reduce((sum, count) => sum + count, 0);
  assert.equal(edgeSum, settings.teacher.K - 1);
  const action = chooseAction(checkpoint, edgeSum, newPly, random);
  assert(order.includes(action), 'ACTION_LEGAL');
  return {
    row_id: spec.game_id + '-' + datasetMode + '-ply-' + state.depth,
    game_id: spec.game_id,
    family: spec.family,
    lineage: spec.family + '|' + datasetMode,
    split: spec.split,
    side: state.getCurrentPlayer(),
    ply: state.depth,
    new_ply: newPly,
    state_key: state._positionKey(),
    history_counts: Array.from(state.position_history),
    history_reconstruction: 'frozen opening plus preceding row actions',
    features648_bits: data.first_NN.features_bits,
    NN137_bits: data.first_NN.NN_bits,
    legal_order209: order,
    mapping136: mapping,
    visits136: visits,
    pi136: visits.map((count) => count / edgeSum),
    rootN: settings.teacher.K,
    edgeSum,
    rootNN: data.first_NN.value,
    rootmean: checkpoint.root_mean,
    leafNN: data.last_leafNN,
    rootNN_view: 'root side-to-move',
    rootmean_view: 'root side-to-move',
    NN_completed: data.NN_calls - data.discardedNN,
    terminal_noNN: data.terminal_noNN,
    NN_discarded: data.discardedNN,
    action209: action,
    action: legal[order.indexOf(action)],
    tau: newPly < settings.teacher.temperaturePlies ? 1 : 0,
    model: settings.teacher.modelSHA256,
    provider: settings.teacher.providerLabel,
    search: settings.teacher.searchLabel,
    seed: spec.sampling_seed,
    source: process.env.SIGMA_SOURCE ?? null,
    wall_ms: data.wall_ms,
    z_p1: null,
    z_stm: null,
    value_eligible: false,
  };
}

async function game(spec) {
  const rows = [],
    started = performance.now(),
    random = randomGenerator(spec.sampling_seed);
  let newPly = 0,
    result;
  append('starts.jsonl', {
    game_id: spec.game_id,
    UTC: new Date().toISOString(),
    family: spec.family,
  });
  if (!spec.generated) {
    const unknown = { game_id: spec.game_id, status: 'GENERATION_UNKNOWN', winner: null, rows: 0 };
    append('games.jsonl', unknown);
    return unknown;
  }
  let prefix = structuredClone(spec.opening.legal_prefix),
    state = r.fromPrefix(prefix);
  try {
    while (true) {
      if (aborted) throw Error('CONTROL_ABORT');
      const terminal = r.terminalResult(state);
      if (terminal) {
        // Rule draw threshold and the run's new-ply censor are distinct conditions.
        result = {
          status: terminal.winner ? 'GOAL' : state.depth >= 200 ? 'DRAW200' : 'DRAW_NOLEGAL',
          winner: terminal.winner,
        };
        break;
      }
      if (newPly >= settings.teacher.maxNewPlies) {
        result = { status: 'NEWPLY_CAP_UNKNOWN', winner: null };
        break;
      }
      const data = await search(spec, state, prefix),
        row = teacherRow(spec, state, data, newPly, random);
      validate(row, settings.teacher.K);
      rows.push(row);
      append('raw-rows.jsonl', row);
      prefix = [...prefix, row.action];
      state = state.next(row.action);
      newPly++;
    }
  } catch (error) {
    result = { status: 'CONTROL_OR_ENGINE_OR_SCHEMA_UNKNOWN', winner: null, error: error.stack };
    aborted = true;
    pool?.stop();
    engine?.stopCurrent();
    process.send({ kind: 'fault', game: spec.game_id, error: error.stack });
  }
  const completed = {
    game_id: spec.game_id,
    mode,
    family: spec.family,
    lineage: spec.family + '|' + datasetMode,
    split: spec.split,
    core,
    datasetMode,
    ...result,
    rows: rows.length,
    legal_prefix: prefix,
    plies: state.depth,
    elapsed_ms: performance.now() - started,
  };
  append('games.jsonl', completed);
  for (const row of rows) {
    target(row, completed.winner);
    validate(row, settings.teacher.K);
  }
  return completed;
}

async function games(request) {
  const results = [],
    queue = [...request.games];
  async function lane() {
    while (queue.length && !aborted) results.push(await game(queue.shift()));
  }
  await Promise.all(Array.from({ length: request.active }, lane));
  return { results, usedNN, unstarted: queue.map((spec) => spec.game_id) };
}

async function close() {
  aborted = true;
  pool?.stop();
  if (pool?.games.size || remote.pending.size || remote.waits.size) throw Error('CLOSE_NONZERO');
  if (mode === 'RustCPU') {
    await broker.quiescent();
    broker.stop();
  }
  const exits = [];
  if (engine) exits.push(await engine.close());
  if (ort) exits.push(await ort.close());
  if (rust) exits.push(await rust.close());
  const receipt = {
    usedNN,
    startup_NN: startup,
    API_ms,
    pipe_ms,
    exits,
    bridge: rust
      ? { calls: rust.calls, request_bytes: rust.requestBytes, response_bytes: rust.responseBytes }
      : null,
    zero: {
      handles: pool?.games.size ?? 0,
      pending: remote.pending.size,
      waits: remote.waits.size,
    },
  };
  save('close.json', receipt);
  return receipt;
}

process.on('message', (request) => {
  if (remote.handle(request)) return;
  if (request.kind === 'abort') {
    aborted = true;
    pool?.stop();
    engine?.stopCurrent();
    return;
  }
  void (async () => {
    if (request.op === 'init') return init(request);
    if (request.op === 'games') return games(request);
    if (request.op === 'close') return close();
    throw Error('OP');
  })()
    .then((data) => {
      process.send({ id: request.id, data });
      if (request.op === 'close') process.disconnect();
    })
    .catch((error) => process.send({ id: request.id, error: error.stack }));
});
