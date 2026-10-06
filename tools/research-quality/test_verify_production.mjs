import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { resolve } from 'node:path';
import test from 'node:test';
import configureVite from '../../apps/web/vite.config.ts';
import { verifyProduction } from '../../scripts/verify-production.mjs';

const root = resolve(import.meta.dirname, '../..');

function fixture({ failedE2E = false, ignoresTerm = false } = {}) {
  const commands = [];
  const previews = [];
  return {
    commands,
    previews,
    options: {
      env: { PREVIEW_PORT: '4179', APP_OUT_DIR: resolve(root, 'apps/web/dist') },
      run: async (command, args, env) => {
        commands.push({ command, args, env });
        if (failedE2E && args.includes('test:e2e')) throw new Error('synthetic browser failure');
      },
      spawn: (command, args, options) => {
        const child = new EventEmitter();
        Object.assign(child, {
          pid: 42,
          command,
          args,
          options,
          exitCode: null,
          signalCode: null,
          signals: [],
        });
        child.kill = (signal) => {
          child.signals.push(signal);
          if (ignoresTerm && signal === 'SIGTERM') return true;
          child.signalCode = signal;
          child.emit('exit', null, signal);
          return true;
        };
        previews.push(child);
        return child;
      },
      requireFreePort: async () => {},
      delay: async () => {},
      fetch: async () => ({ ok: true }),
    },
  };
}

test('root and subpath build and preview use separate verification directories', async () => {
  const { options, commands, previews } = fixture();
  await verifyProduction(options);
  const builds = commands.filter((call) => call.args.includes('build'));
  assert.equal(builds.length, 2);
  assert.deepEqual(
    builds.map((call) => call.env.APP_BASE),
    ['/', '/quoridor/'],
  );
  assert.deepEqual(
    builds.map((call) => call.env.APP_OUT_DIR),
    [
      resolve(root, '.artifacts/verify-production/root'),
      resolve(root, '.artifacts/verify-production/subpath'),
    ],
  );
  for (const [index, child] of previews.entries()) {
    assert.equal(child.args[child.args.indexOf('--outDir') + 1], builds[index].env.APP_OUT_DIR);
    assert.equal(child.options.env.APP_OUT_DIR, builds[index].env.APP_OUT_DIR);
    assert.deepEqual(child.signals, ['SIGTERM']);
  }
  const browserRuns = commands.filter((call) => call.args.includes('test:e2e'));
  assert.deepEqual(
    browserRuns.map((call) => call.env.E2E_BASE_URL),
    ['http://127.0.0.1:4179/', 'http://127.0.0.1:4179/quoridor/'],
  );
});

test('browser failure reaps the current preview and skips the next build', async () => {
  const { options, commands, previews } = fixture({ failedE2E: true });
  await assert.rejects(verifyProduction(options), /synthetic browser failure/);
  assert.equal(commands.filter((call) => call.args.includes('build')).length, 1);
  assert.deepEqual(previews[0].signals, ['SIGTERM']);
});

test('a preview ignoring TERM is killed and reaped', async () => {
  const { options, previews } = fixture({ ignoresTerm: true });
  await verifyProduction(options);
  assert.deepEqual(
    previews.map((child) => child.signals),
    [
      ['SIGTERM', 'SIGKILL'],
      ['SIGTERM', 'SIGKILL'],
    ],
  );
});

test('invalid preview port fails before building', async () => {
  const { options, commands } = fixture();
  options.env.PREVIEW_PORT = '0';
  await assert.rejects(verifyProduction(options), /PREVIEW_PORT/);
  assert.equal(commands.length, 0);
});

test('failed preview spawn reports the error without waiting for an exit that never occurs', async () => {
  const { options } = fixture();
  options.spawn = () => {
    const child = new EventEmitter();
    Object.assign(child, { exitCode: null, signalCode: null });
    child.kill = () => {
      throw new Error('No process was created');
    };
    queueMicrotask(() => child.emit('error', new Error('synthetic spawn failure')));
    return child;
  };
  await assert.rejects(verifyProduction(options), /synthetic spawn failure/);
});

test('normal builds use dist and refuse test hooks in that distribution', () => {
  const previous = {
    APP_OUT_DIR: process.env.APP_OUT_DIR,
    VITE_PHASE1_E2E: process.env.VITE_PHASE1_E2E,
  };
  try {
    delete process.env.APP_OUT_DIR;
    delete process.env.VITE_PHASE1_E2E;
    assert.equal(configureVite({ command: 'build' }).build.outDir, resolve(root, 'apps/web/dist'));
    assert.equal(configureVite({ command: 'build' }).build.emptyOutDir, undefined);
    process.env.VITE_PHASE1_E2E = '1';
    assert.throws(() => configureVite({ command: 'build' }), /dedicated APP_OUT_DIR/);
    assert.doesNotThrow(() => configureVite({ command: 'serve' }));
    process.env.APP_OUT_DIR = resolve(root, '.artifacts/verify-production/root');
    assert.equal(configureVite({ command: 'build' }).build.outDir, process.env.APP_OUT_DIR);
    assert.equal(configureVite({ command: 'build' }).build.emptyOutDir, true);
    process.env.APP_OUT_DIR = resolve(root, '.artifacts/verify-production/subpath');
    assert.equal(configureVite({ command: 'build' }).build.emptyOutDir, true);
    for (const protectedOutput of ['.artifacts', '.worktree/assets', '.artifacts/custom']) {
      process.env.APP_OUT_DIR = resolve(root, protectedOutput);
      assert.equal(configureVite({ command: 'build' }).build.emptyOutDir, false);
    }
  } finally {
    for (const [name, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  }
});
