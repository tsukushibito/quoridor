import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import test from 'node:test';
import { SourceTextModule, SyntheticModule } from 'node:vm';

async function facade() {
  const calls = [];
  const result = (score) => JSON.stringify({ score, scoreKind: 'heuristic', proven: false });
  const exports = {
    default: async () => {
      calls.push(['init']);
    },
    search_json: (...args) => {
      calls.push(['baseline', ...args]);
      return result(77);
    },
    PatternModel: class {
      constructor(input) {
        if (input === 'bad') throw new Error('invalid pattern');
        this.id = input;
        calls.push(['construct', input]);
      }
      evaluate_json(state) {
        calls.push(['evaluate', this.id, state]);
        return result(123);
      }
      search_json(state, options) {
        calls.push(['search', this.id, state, options]);
        return result(456);
      }
      free() {
        calls.push(['free', this.id]);
      }
    },
  };
  const source = stripTypeScriptTypes(
    await readFile(new URL('../src/index.ts', import.meta.url), 'utf8'),
  );
  const module = new SourceTextModule(source, {
    importModuleDynamically: async (specifier) => {
      const values = specifier.endsWith('.js') ? exports : { default: '/othello.wasm' };
      const dependency = new SyntheticModule(Object.keys(values), function () {
        for (const [name, value] of Object.entries(values)) this.setExport(name, value);
      });
      await dependency.link(() => assert.fail('nested import'));
      await dependency.evaluate();
      return dependency;
    },
  });
  await module.link(() => assert.fail('static import'));
  await module.evaluate();
  return { api: module.namespace, calls };
}

test('pattern models own separate Wasm objects and never select a global evaluator', async () => {
  const { api, calls } = await facade();
  const state = { version: 1, board: Array(64).fill(0), toMove: 1 };
  const first = await api.loadPattern('model-a');
  const second = await api.loadPattern('model-b');
  assert.equal(first.kind, 'patternV1');
  assert.equal(first.evaluate(state).score, 123);
  assert.equal(second.search(state, { ttMiB: 0, maxDepth: 2 }).score, 456);
  assert.equal((await api.search(state, { timeMs: 0 })).score, 77);
  assert.equal(first.search(state).score, 456);
  assert.deepEqual(
    calls.filter(([name]) => name === 'construct'),
    [
      ['construct', 'model-a'],
      ['construct', 'model-b'],
    ],
  );
  assert.deepEqual(
    calls.filter(([name]) => name === 'search').map((c) => c.slice(1)),
    [
      ['model-b', JSON.stringify(state), '{"ttMiB":0,"maxDepth":2}'],
      ['model-a', JSON.stringify(state), '{}'],
    ],
  );
  assert.equal(calls.filter(([name]) => name === 'init').length, 1);
  first.free();
  first.free();
  second.free();
  assert.equal(calls.filter(([name]) => name === 'free').length, 2);
  assert.throws(() => first.evaluate(state), /freed/);
  assert.throws(() => first.search(state), /freed/);
});

test('pattern load errors and invalid search options fail at the explicit boundary', async () => {
  const { api, calls } = await facade();
  await assert.rejects(() => api.loadPattern('bad'), /invalid pattern/);
  const model = await api.loadPattern('good');
  for (const options of [{ timeMs: -1 }, { maxDepth: 65 }, { ttMiB: 129 }]) {
    assert.throws(() => model.search({}, options), RangeError);
  }
  assert.equal(calls.filter(([name]) => name === 'search').length, 0);
  model.free();
});
