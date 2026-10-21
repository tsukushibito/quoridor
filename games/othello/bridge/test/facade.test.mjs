import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import test from 'node:test';
import { SourceTextModule, SyntheticModule } from 'node:vm';

const state = { version: 1, board: Array(64).fill(0), toMove: 1 };
const next = { ...state, toMove: 2 };
const status = {
  black: 7,
  white: 4,
  legalMoves: [12, 29],
  mustPass: false,
  terminal: false,
  winner: null,
};
const searchResult = {
  move: 12,
  score: 125,
  scoreKind: 'heuristic',
  completedDepth: 3,
  nodes: 145,
  elapsedMs: 10,
  timedOut: true,
  cancelled: false,
  proven: false,
};

async function facade({ failInit = false, failRule = false, move = 12 } = {}) {
  const calls = [];
  let imports = 0;
  let initializations = 0;
  const record =
    (name, result) =>
    (...args) => {
      calls.push([name, ...args]);
      if (failRule) throw 'core rejected state';
      return JSON.stringify(result);
    };
  const exports = {
    default: async (options) => {
      assert.deepEqual(options, { module_or_path: '/generated-othello.wasm' });
      initializations++;
      if (failInit && initializations === 1) throw new Error('init failed');
    },
    new_game_json: record('new', state),
    legal_moves_json: record('legal', [12, 29]),
    apply_move_json: record('play', next),
    pass_turn_json: record('pass', next),
    status_json: record('status', status),
    choose_move_json: record('choose', { move }),
    search_json: record('search', searchResult),
  };
  const source = stripTypeScriptTypes(
    await readFile(new URL('../src/index.ts', import.meta.url), 'utf8'),
  );
  const module = new SourceTextModule(source, {
    importModuleDynamically: async (specifier) => {
      imports++;
      const values =
        specifier === '../wasm/othello.js'
          ? exports
          : specifier === '../wasm/othello_bg.wasm?url'
            ? { default: '/generated-othello.wasm' }
            : assert.fail(`unexpected import ${specifier}`);
      const synthetic = new SyntheticModule(Object.keys(values), function () {
        for (const [name, value] of Object.entries(values)) this.setExport(name, value);
      });
      await synthetic.link(() => assert.fail('unexpected nested import'));
      await synthetic.evaluate();
      return synthetic;
    },
  });
  await module.link(() => assert.fail('facade must not statically import runtime modules'));
  await module.evaluate();
  return {
    api: module.namespace,
    calls,
    imports: () => imports,
    initializations: () => initializations,
  };
}

test('module evaluation is idle; concurrent requests share one lazy initialization', async () => {
  const loaded = await facade();
  assert.equal(loaded.imports(), 0);
  assert.equal(loaded.initializations(), 0);
  const [game, view] = await Promise.all([loaded.api.newGame(), loaded.api.status(state)]);
  assert.deepEqual(game, state);
  assert.deepEqual(view, status);
  assert.equal(loaded.imports(), 2);
  assert.equal(loaded.initializations(), 1);
});

test('all six operations preserve the JSON boundary and parent input', async () => {
  const loaded = await facade();
  const before = JSON.stringify(state);
  assert.deepEqual(await loaded.api.newGame(), state);
  assert.deepEqual(await loaded.api.legalMoves(state), [12, 29]);
  assert.deepEqual(await loaded.api.play(state, 275), next);
  assert.deepEqual(await loaded.api.pass(state), next);
  assert.deepEqual(await loaded.api.status(state), status);
  assert.equal(await loaded.api.chooseMove(state), 12);
  assert.deepEqual(loaded.calls, [
    ['new'],
    ['legal', before],
    ['play', before, 275],
    ['pass', before],
    ['status', before],
    ['choose', before],
  ]);
  assert.equal(JSON.stringify(state), before);
  assert.equal(loaded.initializations(), 1);
});

test('null choice is unwrapped and core errors propagate', async () => {
  const loaded = await facade({ move: null });
  assert.equal(await loaded.api.chooseMove(state), null);
  const failed = await facade({ failRule: true });
  for (const call of [
    () => failed.api.newGame(),
    () => failed.api.legalMoves(state),
    () => failed.api.play(state, 19),
    () => failed.api.pass(state),
    () => failed.api.status(state),
    () => failed.api.chooseMove(state),
  ]) {
    await assert.rejects(call, (error) => error === 'core rejected state');
  }
});

test('invalid u32 transport values reject before Wasm import or coercion', async () => {
  const loaded = await facade();
  for (const index of [-1, 19.5, NaN, Infinity, 2 ** 32, 2 ** 32 + 19]) {
    await assert.rejects(() => loaded.api.play(state, index), RangeError);
  }
  assert.equal(loaded.imports(), 0);
});

test('initialization failure permits a later request to retry', async () => {
  const loaded = await facade({ failInit: true });
  await assert.rejects(() => loaded.api.newGame(), /init failed/);
  assert.deepEqual(await loaded.api.newGame(), state);
  assert.equal(loaded.initializations(), 2);
});

test('search forwards state/options and preserves score provenance and timing', async () => {
  const loaded = await facade();
  const options = { timeMs: 25, ttMiB: 0, maxDepth: 4, exactEmpties: 6 };
  assert.deepEqual(await loaded.api.search(state, options), searchResult);
  assert.deepEqual(await loaded.api.search(state), searchResult);
  assert.deepEqual(loaded.calls, [
    ['search', JSON.stringify(state), JSON.stringify(options)],
    ['search', JSON.stringify(state), '{}'],
  ]);
  const failed = await facade({ failRule: true });
  await assert.rejects(
    () => failed.api.search(state),
    (error) => error === 'core rejected state',
  );
});

test('invalid search transport options fail before Wasm loading', async () => {
  const loaded = await facade();
  for (const options of [
    { timeMs: -1 },
    { timeMs: 0.5 },
    { timeMs: Infinity },
    { timeMs: 2 ** 53 },
    { ttMiB: 129 },
    { maxDepth: 65 },
    { exactEmpties: NaN },
  ]) {
    await assert.rejects(() => loaded.api.search(state, options), RangeError);
  }
  assert.equal(loaded.imports(), 0);
});
