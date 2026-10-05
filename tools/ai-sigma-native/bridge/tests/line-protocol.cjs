'use strict';
// NN0 IPC fixture: binary supplied explicitly; no model/ORT/training/game run.
const assert = require('node:assert/strict');
const { Pipe } = require('../../../ai-sigma-common/process/json-line.cjs');
const { createRules } = require('../../rules.cjs');
async function verify(binary) {
  assert(binary, 'EXPLICIT_NATIVE_BRIDGE_BINARY');
  const pipe = new Pipe(binary, [], { timeoutMs: 1000 });
  let closed;
  try {
    const state = createRules().r.fromPrefix([]);
    const bits = Array.from(new Uint32Array(new Float32Array(state.toNNInput()).buffer));
    const raw = await pipe.ask({ op: 'raw', fixture: { prefix: [] } });
    assert.equal(raw.ok, true);
    assert.deepEqual(raw.data.features_bits, bits);
    const fresh = await pipe.ask({ op: 'new', prefix: [], generation: 7, simulations: 2 });
    assert.equal(fresh.ok, true);
    const handle = fresh.data.handle;
    const begin = await pipe.ask({ op: 'begin', handle, generation: 7 });
    assert.equal(begin.ok, true);
    assert.equal(begin.data.pending, true);
    const cancel = await pipe.ask({ op: 'cancel', handle, generation: 7 });
    assert.equal(cancel.data.discarded, true);
    const refused = await pipe.ask({ op: 'begin', handle, generation: 7 });
    assert.equal(refused.error, 'STALE_GENERATION');
    const freed = await pipe.ask({ op: 'free', handle });
    assert.equal(freed.data.freed, true);
    assert.equal((await pipe.ask({ op: 'begin', handle, generation: 7 })).error, 'INVALID_SESSION');
  } finally {
    closed = await pipe.close();
  }
  assert.equal(closed.code, 0);
  console.log(
    JSON.stringify({
      protocol: 'native-json-line',
      status: 'PASS',
      NN: 0,
      model_forward: 0,
      child_collected: true,
      exit: closed,
    }),
  );
}
verify(process.argv[2]).catch((error) => {
  console.error(error.stack);
  process.exitCode = 1;
});
