#!/usr/bin/env node
'use strict';

// Transport/ownership fixture only. No model, native search, or rule engine.
const { spawn } = require('node:child_process');
const readline = require('node:readline');
const { identity } = require('../process.cjs');
const config = JSON.parse(process.env.SIGMA_RUNTIME_CONFIG);
const mode = config.fixtureMode;
const emit = (value) => process.stdout.write(JSON.stringify(value) + '\n');
let child,
  active,
  stopped = false;
let closePromise;

async function init(request) {
  if (child) throw Error('INIT_ALREADY_STARTED');
  child = spawn(
    process.execPath,
    [
      '--max-old-space-size=32',
      '-e',
      "process.on('SIGTERM',()=>{});console.log('ready');setInterval(()=>{},1000)",
    ],
    { stdio: ['ignore', 'pipe', 'ignore'] },
  );
  await new Promise((resolve) => child.stdout.once('data', resolve));
  emit({ kind: 'owned', child: identity(child.pid), parent: identity(process.pid) });
  emit({ kind: 'init', id: request.id, data: { mock: true, descendant: identity(child.pid) } });
}

async function close() {
  if (closePromise) return closePromise;
  closePromise = (async () => {
    stopped = true;
    if (active) await active;
    if (child) {
      const done = new Promise((resolve) => child.once('close', resolve));
      child.kill('SIGKILL');
      await done;
    }
  })();
  return closePromise;
}

if (mode === 'bridge') {
  readline.createInterface({ input: process.stdin }).on('line', (line) => {
    const request = JSON.parse(line);
    require('fs').appendFileSync(config.fixtureLog, request.op + '\n');
    void (async () => {
      let data = {};
      if (request.op === 'raw') data = config.fixtureRoot;
      if (request.op === 'new') data = { handle: 1 };
      if (request.op === 'begin') {
        await new Promise((resolve) => setTimeout(resolve, 80));
        data = { done: false, pending: false };
      }
      emit({ ok: true, data });
    })();
  });
} else {
  readline.createInterface({ input: process.stdin }).on('line', (line) => {
    const request = JSON.parse(line);
    if (request.op === 'init') {
      void init(request).catch((error) => emit({ id: request.id, error: error.message }));
    } else if (request.op === 'stop') {
      if (mode === 'healthy') stopped = true;
    } else if (request.op === 'search') {
      if (mode === 'exit') {
        process.exit(7);
        return;
      }
      if (mode === 'json') {
        process.stdout.write('bad JSON\n');
        return;
      }
      if (mode === 'unknown') {
        emit({ id: -909, data: {} });
        return;
      }
      if (mode === 'timeout') return;
      active = (async () => {
        while (!stopped) await new Promise((resolve) => setTimeout(resolve, 5));
        emit({ id: request.id, kind: 'result', data: { cancelled: true, NN: 0 } });
      })();
    } else if (request.op === 'close' && mode === 'healthy') {
      void close().then(() => {
        emit({ id: request.id, data: { children_closed: true, NN: 0 } });
        process.stdin.destroy();
      });
    }
  });
  // Fault fixtures intentionally keep their parent alive/children open until recovery.
  if (mode !== 'healthy') setInterval(() => {}, 1000);
}
