'use strict';
// Owned, NN-free process fixture; no research model or game implementation.
const { createInterface } = require('node:readline');
const { spawn } = require('node:child_process');
const mode = process.argv[2];
const write = (x) => process.stdout.write(JSON.stringify(x) + '\n');
const timers = new Set();
const later = (ms, fn) => {
  const timer = setTimeout(() => {
    timers.delete(timer);
    fn();
  }, ms);
  timers.add(timer);
};
const keepalive = setInterval(() => {}, 1000);
if (mode === 'ignore-stop') process.on('SIGTERM', () => {});
if (mode === 'closed-stdin') {
  require('node:fs').closeSync(0);
  write({ type: 'READY' });
} else if (mode === 'flood') {
  process.stdout.write(
    Array.from(
      { length: 10 },
      (_, i) => JSON.stringify({ type: 'EVENT', id: i, payload: 'x'.repeat(100) }) + '\n',
    ).join(''),
  );
} else if (mode === 'large-line') write({ type: 'EVENT', payload: 'x'.repeat(4096) });
else if (mode === 'unterminated-large') process.stdout.write('x'.repeat(4096));
else if (mode === 'malformed') process.stdout.write('{broken}\n');
else {
  write({ type: 'READY' });
  createInterface({ input: process.stdin }).on('line', (line) => {
    const c = JSON.parse(line);
    if (c.kind === 'SEARCH') {
      const result = {
        type: 'RESULT',
        id: c.id,
        generation: c.generation,
        key: c.key,
        history: c.history,
        allNN: 0,
        deadline_ms: c.deadline_ms,
        search: { status: 'COMPLETED_ACTION', completed_depth: 1, Action: 7 },
      };
      if (mode === 'eof') process.exit(0);
      else if (mode === 'stale') {
        write({ ...result, generation: c.generation - 1 });
        write(result);
      } else if (mode === 'stale-bytes') {
        // Individually legal replies but retained stale metadata must also be bounded.
        for (let i = 0; i < 5; i++) later(i * 15, () => write({ ...result, id: 'x'.repeat(180) }));
      } else if (mode === 'late' || mode === 'delayed') later(100, () => write(result));
      else write(result);
    } else if (c.kind === 'STOP') {
      if (mode !== 'ignore-stop') {
        const ack = () => write({ type: 'STOP_ACK', id: c.id, allNN: 0 });
        if (mode === 'late') later(150, ack);
        else ack();
      }
    } else if (c.kind === 'CLOSE' && mode !== 'ignore-stop') {
      for (const timer of timers) clearTimeout(timer);
      clearInterval(keepalive);
      if (mode === 'delayed-stdio')
        spawn(process.execPath, ['-e', 'setTimeout(()=>{},180)'], {
          stdio: ['ignore', process.stdout, process.stderr],
        });
      process.exit(0);
    }
  });
}
