// Source-only facade fixtures; these do not qualify real generated Wasm typing.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import test from 'node:test';
import { SourceTextModule, SyntheticModule } from 'node:vm';

test('UI facade loads lazily, shares initialization, and owns independent Rust objects', async () => {
  const calls = [];
  let id = 0;
  const exports = {
    default: async () => calls.push(['init']),
    OthelloUi: class {
      constructor() {
        this.id = ++id;
        calls.push(['new', this.id]);
      }
      dispatch_json(raw) {
        calls.push(['dispatch', this.id, raw]);
        return JSON.stringify({ view: { generation: this.id }, effects: [] });
      }
      free() {
        calls.push(['free', this.id]);
      }
    },
  };
  const module = new SourceTextModule(
    stripTypeScriptTypes(await readFile(new URL('../src/index.ts', import.meta.url), 'utf8')),
    {
      importModuleDynamically: async (name) => {
        const values = name.endsWith('.js') ? exports : { default: '/othello.wasm' };
        const dependency = new SyntheticModule(Object.keys(values), function () {
          for (const [key, value] of Object.entries(values)) this.setExport(key, value);
        });
        await dependency.link(() => assert.fail('nested import'));
        await dependency.evaluate();
        return dependency;
      },
    },
  );
  await module.link(() => assert.fail('static import'));
  await module.evaluate();
  assert.equal(calls.length, 0);
  const [one, two] = await Promise.all([module.namespace.createUI(), module.namespace.createUI()]);
  assert.equal(calls.filter(([name]) => name === 'init').length, 1);
  assert.equal(one.dispatch({ kind: 'resume' }).view.generation, 1);
  assert.equal(two.dispatch({ kind: 'save' }).view.generation, 2);
  assert.deepEqual(
    calls.filter(([name]) => name === 'dispatch'),
    [
      ['dispatch', 1, '{"kind":"resume"}'],
      ['dispatch', 2, '{"kind":"save"}'],
    ],
  );
  one.free();
  one.free();
  assert.throws(() => one.dispatch({ kind: 'save' }), /freed/);
  two.free();
  assert.deepEqual(
    calls.filter(([name]) => name === 'free'),
    [
      ['free', 1],
      ['free', 2],
    ],
  );
});
