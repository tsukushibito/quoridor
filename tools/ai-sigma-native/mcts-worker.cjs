'use strict';
const fs = require('fs'),
  readline = require('readline'),
  { Pipe } = require('../ai-sigma-common/process/json-line.cjs'),
  { now, controlDrain } = require('./control.cjs'),
  { identity } = require('./process.cjs'),
  { createReference } = require('./reference.cjs');
const runtime = JSON.parse(process.env.SIGMA_RUNTIME_CONFIG ?? '{}');
const optimized = process.argv[2] === 'new',
  engine = ['old', 'new'].includes(process.argv[2]) ? 'candidate' : process.argv[2],
  { ctx, r } = createReference();
let rust = null,
  ort = null,
  active = null,
  activePromise = null,
  initPromise = null,
  initialized = false,
  shutdownPromise = null,
  stopped = false,
  closing = false,
  nnTotal = 0,
  startupTotal = 0;
function required(name) {
  if (typeof runtime[name] !== 'string' || !runtime[name]) throw Error('RUNTIME_CONFIG_' + name);
  return runtime[name];
}

const emit = (x) => process.stdout.write(JSON.stringify(x) + '\n');
const unpack = (x) => {
  if (!x.ok) throw Error(x.error);
  return x.data;
};
let bridge = null;
const call = async (x) => {
  const t = now(),
    request = JSON.stringify(x);
  const z = await rust.ask(x);
  if (bridge) {
    bridge.count++;
    bridge.request_bytes += Buffer.byteLength(request) + 1;
    bridge.response_bytes += Buffer.byteLength(JSON.stringify(z)) + 1;
    bridge.wall_ms += now() - t;
    bridge.ops[x.op] = (bridge.ops[x.op] ?? 0) + 1;
  }
  return unpack(z);
};
function ownPipe(pipe) {
  emit({ kind: 'owned', child: identity(pipe.child.pid), parent: identity(process.pid) });
  pipe.child.once('error', (error) => {
    if (!closing) {
      stopped = true;
      emit({ kind: 'fatal', error: 'CHILD_ERROR:' + error.message });
      void shutdown();
    }
  });
  pipe.child.once('close', (code, signal) => {
    if (!closing) {
      stopped = true;
      emit({ kind: 'fatal', error: 'CHILD_EXIT:' + code + ':' + signal });
      void shutdown();
    }
  });
  return pipe;
}

function validateSearch(q) {
  for (const name of ['K', 'generation', 'NN_limit']) {
    if (!Number.isSafeInteger(q[name]) || q[name] < (name === 'K' ? 1 : 0))
      throw Error('SEARCH_CONFIG_' + name);
  }
  if (!Number.isFinite(q.watchdog_ms) || q.watchdog_ms <= 0)
    throw Error('SEARCH_CONFIG_watchdog_ms');
  if (!Array.isArray(q.legal_prefix)) throw Error('SEARCH_CONFIG_legal_prefix');
  if (
    q.mock?.delay_ms !== undefined &&
    (!Number.isFinite(q.mock.delay_ms) || q.mock.delay_ms < 0)
  ) {
    throw Error('SEARCH_CONFIG_mock_delay_ms');
  }
}

async function init(mock = false) {
  if (!Number.isFinite(runtime.pipeTimeoutMs) || runtime.pipeTimeoutMs <= 0) {
    throw Error('RUNTIME_CONFIG_pipeTimeoutMs');
  }
  if (engine === 'candidate')
    rust = ownPipe(new Pipe(required('nativeBridge'), [], { timeoutMs: runtime.pipeTimeoutMs }));
  if (!mock) {
    ort = ownPipe(
      new Pipe(required('python'), ['-u', __dirname + '/inference/ort.py', required('model')], {
        timeoutMs: runtime.pipeTimeoutMs,
      }),
    );
    const info = unpack(await ort.ask({ op: 'info' })),
      bits = r.portState(r.fromPrefix([])).features_bits,
      start = now();
    const warm = unpack(await ort.ask({ op: 'infer', features_bits: bits }));
    startupTotal++;
    return {
      info,
      startup: {
        count: 1,
        wall_ms: now() - start,
        API_ms: warm.API_ms,
        root_NN_bits: warm.NN_bits,
      },
      identities: [
        identity(process.pid),
        ...(rust ? [identity(rust.child.pid)] : []),
        identity(ort.child.pid),
      ],
    };
  }
  return {
    mock: true,
    identities: [identity(process.pid), ...(rust ? [identity(rust.child.pid)] : [])],
  };
}
function cpShape(x, g, nn) {
  return {
    generation: g,
    action: x.action,
    root_visits: x.root_visits,
    simulations: x.simulations,
    root_mean: x.root_mean,
    root_valueSum: x.root_valueSum,
    root_edges: x.root_edges,
    nn_calls: nn,
  };
}
async function search(q) {
  validateSearch(q);
  const start = now();
  bridge = { count: 0, request_bytes: 0, response_bytes: 0, wall_ms: 0, ops: {} };
  stopped = false;
  let handle = null,
    cp = null,
    trace = null,
    root = null,
    primary = null,
    discardedNN = 0;
  const numeric = [],
    CPs = [],
    spans = [];
  let count = 0,
    completed = 0,
    firstNN = null,
    last_leafNN = null;
  ctx.nativeStopped = () => stopped || now() - start > q.watchdog_ms;
  r.reset(!!q.trace);
  const state =
      q.mock?.artificial_state && engine === 'reference'
        ? new r.State(q.mock.artificial_state)
        : r.fromPrefix(q.legal_prefix),
    prefix = [];
  let cursor = r.fromPrefix([]);
  for (const a of q.legal_prefix) {
    prefix.push(r.rustAction(cursor, a));
    cursor = cursor.next(a);
  }
  const rootState = r.portState(state);
  const infer = async (bits) => {
    if (stopped) throw Error('guard');
    if (count >= q.NN_limit) throw Error('NN_BUDGET');
    const t = now();
    let n;
    if (q.mock?.tape) {
      const row = q.mock.tape[count];
      if (!row || JSON.stringify(row.features_bits) !== JSON.stringify(bits))
        throw Error('NN0_TAPE_FEATURE_MISMATCH');
      n = {
        logits: row.policy_logits,
        value: row.value,
        NN_bits: row.NN_bits,
        API_ms: 0,
        process_CPU_ms: 0,
      };
    } else if (q.mock) {
      if (q.mock.delay_ms) await new Promise((resolve) => setTimeout(resolve, q.mock.delay_ms));
      const logits = Array(136).fill(q.mock.logit ?? 0);
      if (q.mock.bias != null) logits[q.mock.bias] = 4;
      n = {
        logits,
        value: q.mock.value ?? 0.25,
        NN_bits: Array.from(
          new Uint32Array(new Float32Array([...logits, q.mock.value ?? 0.25]).buffer),
        ),
        API_ms: 0,
        process_CPU_ms: 0,
      };
    } else {
      nnTotal++;
      count++;
      n = unpack(await ort.ask({ op: 'infer', features_bits: bits }));
    }
    if (q.mock) count++;
    if (firstNN === null)
      firstNN = {
        features_bits: bits,
        NN_bits: n.NN_bits,
        policy_logits: n.logits,
        value: n.value,
      };
    spans.push({
      index: count,
      request_ms: t - start,
      return_ms: now() - start,
      pipe_ms: now() - t,
      API_ms: n.API_ms,
      process_CPU_ms: n.process_CPU_ms,
    });
    if (stopped) {
      discardedNN++;
      throw Error('guard');
    }
    return n;
  };
  const progress = (x) => {
    if (q.final_only && !x.final_only_delivery) {
      completed = x.simulations;
      return;
    }
    cp = cpShape(x, q.generation, count);
    completed = cp.simulations;
    if (q.trace) CPs.push(cp);
    emit({ kind: 'cp', id: q.id, engine, cp, worker_elapsed_ms: now() - start });
  };
  try {
    if (engine === 'candidate') {
      const raw = await call({ op: 'raw', fixture: { prefix } });
      if (
        JSON.stringify(raw.features_bits) !== JSON.stringify(rootState.features_bits) ||
        JSON.stringify(raw.effective_legal) !==
          JSON.stringify(r.terminalResult(state) ? [] : rootState.legal)
      )
        throw Error('ROOT_INPUT_MISMATCH');
      handle = (
        await call({
          op: 'new',
          prefix,
          simulations: q.K,
          generation: q.generation,
          trace: !!q.trace,
        })
      ).handle;
      while (!stopped) {
        const z = await call({ op: 'begin', handle, generation: q.generation });
        if (stopped) break;
        let finished = !!z.done;
        if (z.pending) {
          const n = await infer(z.features_bits);
          last_leafNN = {
            value: n.value,
            side: z.turn + 1,
            ply: z.ply,
            view: 'last expanded NN leaf side-to-move',
          };
          if (q.trace)
            numeric.push({ ...z, policy_logits: n.logits, value: n.value, NN_bits: n.NN_bits });
          if (stopped) break;
          const resumed = await call({
            op: 'resume',
            handle,
            generation: q.generation,
            token: z.token,
            logits: n.logits,
            value: n.value,
          });
          completed = resumed.simulations;
          finished = !!resumed.done;
        }
        if (optimized) {
          await controlDrain();
          if (stopped) break;
          if (finished) {
            const x = await call({ op: 'checkpoint', handle, generation: q.generation });
            progress({ ...x, final_only_delivery: true });
            break;
          }
        } else {
          const x = await call({ op: 'checkpoint', handle, generation: q.generation });
          progress({
            ...x,
            final_only_delivery: x.simulations === q.K || x.terminal_value !== null,
          });
          await controlDrain();
          if (x.simulations === q.K || x.terminal_value !== null) break;
        }
      }
      if (q.trace) trace = await call({ op: 'trace', handle, generation: q.generation });
    } else {
      const evaluator = async (s, legal) => {
        const bits = r.portState(s).features_bits,
          n = await infer(bits);
        last_leafNN = {
          value: n.value,
          side: s.getCurrentPlayer(),
          ply: s.depth,
          view: 'last expanded NN leaf side-to-move; not necessarily final simulation',
        };
        if (q.trace)
          numeric.push({
            ...r.portState(s),
            path: r.portPath(r.evaluationNode),
            node_index: vmEval('portId(portEvaluationNode)'),
            policy_logits: n.logits,
            value: n.value,
            NN_bits: n.NN_bits,
          });
        const perm = s.isPlayer1Turn() ? null : r.vertPolicyPermutation(9),
          ix = legal.map((a) => {
            const i = r.actionToIndex(a, 9);
            return perm ? perm[i] : i;
          }),
          max = Math.max(...ix.map((i) => n.logits[i])),
          ex = ix.map((i) => Math.exp(n.logits[i] - max)),
          sum = ex.reduce((a, b) => a + b, 0);
        return [ex.map((v) => v / sum), n.value];
      };
      const c = {
        simulations: 0,
        spans: [],
        steps: [],
        onComplete: (root) => {
          if (q.final_only) completed = root.visitCount;
          else progress(r.CP(root, q.generation));
        },
      };
      r.setClock(c);
      root = await r.runMCTS(state, q.K - 1, evaluator, null);
      if (q.final_only && root)
        progress({ ...r.CP(root, q.generation), final_only_delivery: true });
      if (q.trace) trace = r.trace();
    }
  } catch (e) {
    if (e.message !== 'guard') primary = { message: e.message, stack: e.stack };
    if (q.trace && engine === 'reference') trace = r.trace();
  } finally {
    if (handle !== null) {
      await call({ op: 'cancel', handle, generation: q.generation });
      await call({ op: 'free', handle });
    }
    r.setClock(null);
    r.reset(false);
  }
  return {
    engine,
    fixture_id: q.fixture_id,
    K: q.K,
    cp,
    CPs,
    numeric,
    trace,
    spans,
    primary,
    root_state: rootState,
    first_NN: firstNN,
    last_leafNN,
    completed,
    NN_calls: count,
    discardedNN,
    terminal_noNN: completed - (count - discardedNN),
    zero: { activeNN: 0, handles: 0, active: false },
    request_ms: now() - start,
    NN_total: nnTotal,
    startup_separate: startupTotal,
    worker_stop_ms: now() - start,
    bridge,
    cache_hits: 0,
    returned_NN: count,
    active_NN: 0,
  };
}
function vmEval(s) {
  return require('vm').runInContext(s, ctx);
}
async function shutdown() {
  if (shutdownPromise) return shutdownPromise;
  closing = true;
  stopped = true;
  shutdownPromise = (async () => {
    const errors = [];
    if (initPromise)
      try {
        await initPromise;
      } catch (error) {
        errors.push(String(error));
      }
    if (activePromise)
      try {
        await activePromise;
      } catch (error) {
        errors.push(String(error));
      }
    const exit = [];
    // Child handles are never overwritten by another init; every spawned pipe closes.
    for (const pipe of [rust, ort]) {
      if (pipe)
        try {
          exit.push(await pipe.close());
        } catch (error) {
          errors.push(String(error));
        }
    }
    return { exit, errors, NN_total: nnTotal, startup_separate: startupTotal };
  })();
  return shutdownPromise;
}

const reader = readline.createInterface({ input: process.stdin });
reader.on('line', (line) => {
  let q;
  try {
    q = JSON.parse(line);
  } catch (_) {
    emit({ kind: 'fatal', error: 'JSON_INPUT' });
    void shutdown();
    return;
  }
  if (q.op === 'stop') {
    if (active && q.id === active.id) stopped = true;
    return;
  }
  if (q.op === 'close') {
    void shutdown()
      .then((data) => {
        emit({ kind: 'closed', id: q.id, data });
        process.stdin.destroy();
      })
      .catch((error) => {
        emit({ kind: 'closed', id: q.id, error: error.stack });
        process.exitCode = 1;
        process.stdin.destroy();
      });
    return;
  }
  if (closing) {
    emit({ id: q.id, error: 'ENGINE_CLOSING' });
    return;
  }
  if (q.op === 'init') {
    if (initialized || initPromise) {
      emit({ kind: 'init', id: q.id, error: 'INIT_ALREADY_STARTED' });
      return;
    }
    initPromise = init(q.mock);
    void initPromise
      .then((data) => {
        initialized = true;
        emit({ kind: 'init', id: q.id, data });
      })
      .catch((error) => {
        emit({ kind: 'init', id: q.id, error: error.stack });
        void shutdown();
      });
    return;
  }
  if (q.op === 'search') {
    if (!initialized) {
      emit({ id: q.id, error: 'NOT_INITIALIZED' });
      return;
    }
    if (active) {
      emit({ id: q.id, error: 'ACTIVE_OLD' });
      return;
    }
    try {
      validateSearch(q);
    } catch (error) {
      emit({ id: q.id, error: error.message });
      return;
    }
    active = q;
    activePromise = search(q);
    void activePromise
      .then((data) => emit({ kind: 'result', id: q.id, data }))
      .catch((error) => emit({ kind: 'result', id: q.id, error: error.stack }))
      .finally(() => {
        active = null;
        activePromise = null;
      });
    return;
  }
  emit({ id: q.id, error: 'OP' });
});
reader.once('close', () => {
  void shutdown();
});
