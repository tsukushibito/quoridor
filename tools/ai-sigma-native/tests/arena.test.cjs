'use strict';
const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('node:fs'),
  os = require('node:os'),
  path = require('node:path');
const { validateConfig, validatePlan, checkStart } = require('../arena/config.cjs');
const { run, Records } = require('../arena/run.cjs');
function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'native-arena-contract-')),
    out = path.join(root, 'new-output');
  const c = {
    schema: 'native-arena-run-v1',
    run: 'synthetic',
    issue: 'test.1',
    goal_issue: 'test',
    owner: 'test-owner',
    weight_manifest: path.join(root, 'weights.json'),
    openings: path.join(root, 'openings.json'),
    hands: path.join(out, 'hands.jsonl'),
    counter_file: path.join(out, 'counter.json'),
    output: path.join(out, 'result.json'),
    output_root: out,
    beads_wrapper: path.join(root, 'beads.sh'),
    pause_path: path.join(root, 'pause'),
    NNcap: 1,
    node_cap: 1,
    max_depth: 1,
    budget_ms: 100,
    margin_ms: 10,
    init_timeout_ms: 100,
    cleanup_ms: 1100,
    transport: {
      maxQueueMessages: 4,
      maxQueueBytes: 4096,
      maxReplyBytes: 4096,
      maxRequestBytes: 4096,
      maxStderrBytes: 512,
      stopTimeoutMs: 20,
      closeGraceMs: 20,
      killGraceMs: 20,
    },
    resources: {
      affinity: [0],
      logical_cpu_limit: 1,
      ram_guard_bytes: 512 * 1024 * 1024,
      output_cap_bytes: 128 * 1024,
      max_snapshot_bytes: 8192,
    },
    slots: [0],
    ordering: 'rootbest-first',
    end_utc: new Date(Date.now() + 60000).toISOString(),
    heavy_start_cutoff_utc: new Date(Date.now() + 40000).toISOString(),
  };
  const plan = {
    slots: [{ slot: 0, opening: 'start', NNUE_side: 1, distance_mode: 'clip' }],
    openings: [{ id: 'start', prefix: [] }],
  };
  fs.writeFileSync(c.openings, JSON.stringify(plan));
  return { c, plan, root, clean: () => fs.rmSync(root, { recursive: true }) };
}
const control = () => ({
  start: async () => {},
  stop: async () => {},
  check: () => {},
  receipts: [],
});
test('explicit arena budgets/resources/paths refuse collisions and insufficient collection time', () => {
  const f = fixture();
  try {
    assert.equal(validateConfig(f.c), f.c);
    for (const patch of [
      { budget_ms: undefined },
      { margin_ms: 100 },
      { cleanup_ms: 1 },
      { output: f.c.openings },
      { slots: [] },
      { ordering: 'unknown' },
      { resources: { ...f.c.resources, affinity: [0, 1] } },
    ])
      assert.throws(() => validateConfig({ ...f.c, ...patch }));
    assert.throws(() => checkStart({ ...f.c, end_utc: new Date(Date.now() + 100).toISOString() }));
  } finally {
    f.clean();
  }
});
test('planned denominator rejects unknown/duplicate slot or opening and illegal prefix before spawning', async () => {
  const f = fixture();
  let spawns = 0;
  class MustNotSpawn {
    constructor() {
      spawns++;
    }
  }
  try {
    for (const patch of [{ slots: [9] }, { slots: [0, 0] }])
      assert.throws(() => {
        validateConfig({ ...f.c, ...patch });
        validatePlan(f.plan, { ...f.c, ...patch });
      });
    for (const plan of [
      { ...f.plan, slots: [] },
      { ...f.plan, slots: [...f.plan.slots, ...f.plan.slots] },
      { ...f.plan, openings: [{ id: 'start', prefix: [{ type: 'pawn', direction: [9, 9] }] }] },
    ]) {
      fs.writeFileSync(f.c.openings, JSON.stringify(plan));
      await assert.rejects(run(f.c, { Worker: MustNotSpawn, makeControl: control }));
    }
    assert.equal(spawns, 0);
    assert.equal(fs.existsSync(f.c.output_root), false);
  } finally {
    f.clean();
  }
});
test('initialization refusal is recorded with all slots retained and child close in finally', async () => {
  const f = fixture();
  let closed = 0;
  class InitFailure {
    async take() {
      return { type: 'SCHEMA_ERROR' };
    }
    async close() {
      closed++;
      return { waited: true };
    }
  }
  try {
    const result = await run(f.c, { Worker: InitFailure, makeControl: control });
    assert.equal(closed, 1);
    assert.match(result.failure, /INIT_NOT_READY/);
    assert.equal(result.clock_valid, false);
    assert.equal(result.planned_all_slots, 1);
    assert.equal(result.WDL.unknown, 1);
    assert.equal(result.ledger[0].status, 'NOT_COMPLETED');
    assert.equal(JSON.parse(fs.readFileSync(f.c.output)).failure, result.failure);
  } finally {
    f.clean();
  }
});
test('pause/ownership refusal precedes child spawn; existing evidence never truncated', async () => {
  const f = fixture();
  let spawns = 0;
  class NoSpawn {
    constructor() {
      spawns++;
    }
  }
  try {
    const result = await run(f.c, {
      Worker: NoSpawn,
      makeControl: () => ({
        ...control(),
        start: async () => {
          throw Error('PAUSED_OR_UNASSIGNED');
        },
      }),
    });
    assert.equal(result.failure, 'PAUSED_OR_UNASSIGNED');
    assert.equal(spawns, 0);
    const before = fs.readFileSync(f.c.output);
    await assert.rejects(run(f.c, { Worker: NoSpawn, makeControl: control }), /EEXIST/);
    assert.deepEqual(fs.readFileSync(f.c.output), before);
    assert.equal(spawns, 0);
  } finally {
    f.clean();
  }
});
test('new output has a measured run cap including snapshot and terminal recording reserve', () => {
  const f = fixture();
  try {
    const records = new Records(f.c);
    records.write('hands', { small: true }, true);
    assert.throws(
      () => records.write('hands', { large: 'x'.repeat(f.c.resources.output_cap_bytes) }, true),
      /OUTPUT_CAP/,
    );
    assert.throws(() => records.write('output', { large: 'x'.repeat(9000) }), /SNAPSHOT_CAP/);
    records.write('output', { failure: 'OUTPUT_CAP' });
    records.close();
    assert.match(fs.readFileSync(f.c.output, 'utf8'), /OUTPUT_CAP/);
  } finally {
    f.clean();
  }
});

test('normal replies require a finite monotone global NN counter before adoption', async () => {
  for (const allNN of [undefined, NaN, -1, 2]) {
    const f = fixture();
    class BadCounter {
      async take() {
        return { type: 'READY' };
      }
      async request() {
        return { status: 'RECEIVED', response: { allNN, validation: { valid: true } } };
      }
      async close() {
        return { waited: true };
      }
    }
    try {
      const result = await run(f.c, { Worker: BadCounter, makeControl: control });
      assert.match(result.failure, /NN_COUNTER/);
      assert.equal(result.clock_valid, false);
      assert.equal(result.samples, 0);
      assert.equal(result.WDL.unknown, 1);
    } finally {
      f.clean();
    }
  }
});
