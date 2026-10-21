import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as wasm from '../../packages/engine-bridge/wasm/rules/quoridor_rules.js';
import { loadTs } from './ts-fixture.mjs';

const protocol = await loadTs(
  new URL('../../packages/engine-bridge/src/protocol.ts', import.meta.url),
  {},
);
const rules = await loadTs(
  new URL('../../packages/engine-bridge/src/rules-client.ts', import.meta.url),
  {
    '../wasm/rules/quoridor_rules.js': {
      ...wasm,
      default: () =>
        wasm.default({
          module_or_path: readFileSync(
            new URL(
              '../../packages/engine-bridge/wasm/rules/quoridor_rules_bg.wasm',
              import.meta.url,
            ),
          ),
        }),
    },
    '../wasm/rules/quoridor_rules_bg.wasm?url': { default: 'owned-product-input.wasm' },
    './protocol': protocol,
  },
);
const environment = await loadTs(
  new URL('../../apps/web/src/games/quoridor/environment-presets.ts', import.meta.url),
  {},
);
const storage = await loadTs(
  new URL('../../apps/web/src/games/quoridor/persistence/local-state.ts', import.meta.url),
  {
    '@quoridor/engine-bridge': rules,
    '../environment-presets': environment,
  },
  { DOMException },
);
class HeldAi {
  isReady = false;
  workerGeneration = 0;
  calls = [];
  cancels = 0;
  disposed = false;
  cancel() {
    this.cancels++;
  }
  dispose() {
    this.disposed = true;
  }
  diagnostics() {
    return {};
  }
  search(request) {
    return new Promise((resolve) => {
      this.calls.push({ request, resolve });
    });
  }
}
const { SessionController } = await loadTs(
  new URL('../../apps/web/src/games/quoridor/session/session-controller.ts', import.meta.url),
  { '@quoridor/engine-bridge': { ...rules, AiClient: HeldAi } },
);

test('actual product rules save/new/restore retains legacy keys, data and current defaults', async () => {
  const memory = new Map();
  const repository = new storage.LocalStateRepository(() => ({
    getItem: (key) => memory.get(key) ?? null,
    setItem: (key, value) => memory.set(key, value),
    removeItem: (key) => memory.delete(key),
  }));
  const first = new SessionController();
  const next = new SessionController();
  try {
    await first.newGame();
    assert.equal(first.state.mode, 'pvp');
    assert.equal(first.state.simulations, 96);
    const state = first.state;
    const action = state.view.legalMask.findIndex((value) => value === 1);
    const move = first.apply(action, state.gameEpoch, state.revision);
    assert.ok(move);
    first.finish(move.gameEpoch, move.revision);
    const saved = storage.makeSavedMatch(first.exportReplay(), storage.DEFAULT_SETTINGS.nextMatch);
    assert.equal(repository.writeGame(saved).status, 'ok');
    assert.equal(repository.writeSettings(storage.DEFAULT_SETTINGS).status, 'ok');
    assert.equal(storage.GAME_KEY, 'quoridor.m1.game.v1');
    assert.equal(storage.SETTINGS_KEY, 'quoridor.m1.settings.v1');
    const exact = memory.get(storage.GAME_KEY);
    first.dispose();
    const read = repository.readGame();
    assert.equal(read.status, 'ok');
    await next.restoreReplay(read.value.replay, read.value.match);
    assert.equal(JSON.stringify(next.exportReplay()), JSON.stringify(saved.replay));
    assert.equal(memory.get(storage.GAME_KEY), exact);
    assert.equal(repository.readSettings().status, 'ok');
  } finally {
    first.dispose();
    next.dispose();
  }
});

test('dispose during rules bootstrap releases late-created game without changing disposed state', async () => {
  let resolve;
  let released = 0;
  const pending = new Promise((yes) => {
    resolve = yes;
  });
  const { SessionController: PendingSession } = await loadTs(
    new URL('../../apps/web/src/games/quoridor/session/session-controller.ts', import.meta.url),
    {
      '@quoridor/engine-bridge': {
        ...rules,
        RulesClient: { createGame: () => pending },
        AiClient: HeldAi,
      },
    },
  );
  const session = new PendingSession();
  const opening = session.newGame();
  session.dispose();
  const disposed = session.state;
  resolve({
    getView: () => ({ ply: 0 }),
    dispose: () => {
      released++;
    },
  });
  await opening;
  assert.equal(session.state, disposed);
  assert.equal(released, 1);
});

test('dispose cancels pending AI; delayed progress and completion cannot mutate the old session', async () => {
  const ai = new HeldAi();
  const session = new SessionController(ai);
  await session.newGame({ mode: 'ai', humanSide: 1 });
  assert.equal(session.state.phase, 'aiThinking');
  assert.equal(ai.calls.length, 1);
  const { request, resolve } = ai.calls[0];
  session.dispose();
  const disposed = session.state;
  request.onProgress({}, 0);
  resolve({ actionId: 13, stats: {} });
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(session.state, disposed);
  assert.equal(ai.disposed, true);
  assert.ok(ai.cancels > 0);
});

test('storage quota/unavailable and corrupt saves never report successful persistence or clear data', () => {
  const corrupt = '{corrupt';
  for (const name of ['QuotaExceededError', 'SecurityError']) {
    const repository = new storage.LocalStateRepository(() => ({
      getItem: () => corrupt,
      setItem: () => {
        throw new DOMException('blocked', name);
      },
      removeItem: () => {
        throw new DOMException('blocked', name);
      },
    }));
    assert.equal(repository.readGame().status, 'invalid');
    assert.equal(
      repository.writeSettings(storage.DEFAULT_SETTINGS).status,
      name === 'QuotaExceededError' ? 'quota' : 'failed',
    );
    assert.notEqual(repository.clearGame().status, 'ok');
    assert.equal(repository.readGame().status, 'invalid');
  }
  const blocked = new storage.LocalStateRepository(() => {
    throw new DOMException('blocked', 'SecurityError');
  });
  assert.equal(blocked.readGame().status, 'unavailable');
  assert.equal(blocked.writeSettings(storage.DEFAULT_SETTINGS).status, 'unavailable');
});
