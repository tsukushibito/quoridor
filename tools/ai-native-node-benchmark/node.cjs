'use strict';
// Preserved production Node APIs, held weights and held CPU ORT process.
const readline = require('node:readline');
const { spawn } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const path = require('node:path');
const native = require('../ai-sigma-native/nnue.cjs');
const { search } = require('../ai-sigma-native/search.cjs');
const { createReference } = require('../ai-sigma-native/reference.cjs');
const [manifest, onnx, python] = process.argv.slice(2);
const { w, m } = native.load(manifest);
const { r, ctx } = createReference();
const started = performance.now();
const ort = spawn(
  python,
  ['-u', path.join(__dirname, '../ai-sigma-native/inference/ort.py'), onnx],
  {
    stdio: ['pipe', 'pipe', 'inherit'],
  },
);
let pending = null;
readline.createInterface({ input: ort.stdout }).on('line', (line) => {
  if (!pending) throw Error('UNEXPECTED_PROVIDER_REPLY');
  const { resolve, reject } = pending;
  pending = null;
  const reply = JSON.parse(line);
  if (!reply.ok) reject(Error(reply.error));
  else resolve(reply.data);
});
ort.on('exit', (code) => {
  if (pending) pending.reject(Error('PROVIDER_EOF_' + code));
  pending = null;
});
function infer(q) {
  if (pending) throw Error('ONLY_ONE_PENDING');
  return new Promise((resolve, reject) => {
    pending = { resolve, reject };
    ort.stdin.write(JSON.stringify(q) + '\n');
  });
}
function state(prefix, rules = native.q.r) {
  let s = rules.fromPrefix([]);
  for (const id of prefix) {
    const a = s.getLegalActions().find((a) => rules.rustAction(s, a) === id);
    if (!a) throw Error('ILLEGAL_PREFIX');
    s = s.next(a);
  }
  return s;
}
async function run(q) {
  if (q.op === 'eval') {
    const s = state(q.prefix);
    const acc = native.q.full(s, w);
    const start = performance.now();
    let sum = 0;
    let value = 0;
    for (let i = 0; i < q.iterations; i++) {
      value = native.valueScaled(acc, w, m);
      sum += value;
    }
    return { seconds: (performance.now() - start) / 1000, value, sum, evaluations: q.iterations };
  }
  if (q.op === 'search') {
    const s = state(q.prefix);
    const start = performance.now();
    const z = search(s, 'NNUE', w, m, {
      maxDepth: q.depth,
      nodeCap: 1_000_000,
      deadlineMs: Number(process.hrtime.bigint()) / 1e6 + 60_000,
      leafPackage: true,
      ordering: 'rootbest-first',
    });
    if (z.completed_depth !== q.depth) throw Error('INCOMPLETE_SEARCH');
    if (!s.getLegalActions().some((a) => native.q.r.rustAction(s, a) === z.Action))
      throw Error('ILLEGAL_ACTION');
    return {
      seconds: (performance.now() - start) / 1000,
      action: z.Action,
      value: z.value,
      depth: z.completed_depth,
      nodes: z.stats.processed,
      evaluations: z.stats.NN,
    };
  }
  if (q.op === 'mcts') {
    r.reset(false);
    ctx.nativeStopped = () => false;
    r.setClock({ spans: [], steps: [], simulations: 0 });
    const s = state(q.prefix, r);
    let calls = 0;
    let api = 0;
    let pipe = 0;
    const evaluator = async (position, legal) => {
      const t = performance.now();
      const bits = r.portState(position).features_bits;
      const n = await infer({ op: 'infer', features_bits: bits });
      pipe += (performance.now() - t) / 1000;
      api += n.API_ms / 1000;
      calls++;
      const perm = position.getCurrentPlayer() === 2 ? r.vertPolicyPermutation(9) : null;
      const ix = legal.map((a) => {
        const id = r.actionToIndex(a, 9);
        return perm ? perm[id] : id;
      });
      const max = Math.max(...ix.map((i) => n.logits[i]));
      const ex = ix.map((i) => Math.exp(n.logits[i] - max));
      const total = ex.reduce((a, b) => a + b, 0);
      return [ex.map((v) => v / total), n.value];
    };
    const start = performance.now();
    const root = await r.runMCTS(s, q.k - 1, evaluator, {});
    const cp = r.CP(root, 1);
    if (!s.getLegalActions().some((a) => r.rustAction(s, a) === cp.action))
      throw Error('ILLEGAL_ACTION');
    return {
      seconds: (performance.now() - start) / 1000,
      action: cp.action,
      value: cp.root_mean,
      root_visits: cp.root_visits,
      nn_calls: calls,
      nn_seconds: api,
      pipe_seconds: pipe,
      edges: cp.root_edges.map(([a, , visits, sum]) => [a, visits, sum]),
    };
  }
  throw Error('UNKNOWN_OPERATION');
}
(async () => {
  const info = await infer({ op: 'info' });
  console.log(
    JSON.stringify({ ready: true, init_seconds: (performance.now() - started) / 1000, info }),
  );
  try {
    for await (const line of readline.createInterface({ input: process.stdin })) {
      console.log(JSON.stringify(await run(JSON.parse(line))));
    }
  } finally {
    ort.stdin.end();
    if (ort.exitCode === null) await new Promise((resolve) => ort.once('exit', resolve));
  }
})().catch((e) => {
  console.error(e);
  ort.kill();
  process.exitCode = 1;
});
