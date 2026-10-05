'use strict';
const fs = require('fs'),
  assert = require('assert'),
  { Worker } = require('./protocol.cjs'),
  { now } = require('../search.cjs');
(async () => {
  const results = [];
  for (const mode of [
    'valid',
    'stale',
    'late',
    'incomplete',
    'eof',
    'parse-validation-overshoot',
  ]) {
    const w = new Worker('NONE', __dirname + '/fake-worker.cjs', [mode]);
    assert.equal((await w.take(2000)).type, 'READY');
    const c = { kind: 'SEARCH', id: mode, generation: 1, key: 'fixed', history: 'fixed' };
    const v = await w.request(c, 100, (x) => {
      if (mode === 'parse-validation-overshoot') {
        const st = now();
        while (now() - st < 115) {}
      }
      return {
        valid:
          x.search.status === 'COMPLETED_ACTION' &&
          x.search.completed_depth >= 1 &&
          x.search.Action === 7,
      };
    });
    const adopted = v.status === 'RECEIVED' && v.response?.validation?.valid === true;
    const reap = await w.close();
    assert(reap.waited);
    if (mode === 'valid' || mode === 'stale') assert(adopted);
    else assert(!adopted);
    if (mode === 'stale') assert.equal(v.obsolete.length, 1);
    if (mode === 'parse-validation-overshoot')
      assert(v.elapsed_ms > 100 && v.status === 'OUTER_DEADLINE');
    results.push({ mode, adopted, clock: v, cleanup: reap });
  }
  fs.writeFileSync(
    process.argv[2],
    JSON.stringify(
      { UTC: new Date().toISOString(), samples: 0, checks: results.length, PASS: true, results },
      null,
      2,
    ) + '\n',
  );
  console.log(JSON.stringify({ clock_fixture_PASS: true, checks: results.length, samples: 0 }));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
