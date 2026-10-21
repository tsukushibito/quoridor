// Source-only regression of the actual test Blob bootstrap's URL handling.
// Dynamic import and fetch are explicit fixture ports. No Worker/browser/Wasm,
// network, search, build, or previously successful suite is executed here.
import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import { loadTs } from '../../../../tests/unit/ts-fixture.mjs';

const path = new URL('../e2e/browser-search.spec.ts', import.meta.url);
const moduleUrl = 'https://fixture.invalid/sub/app/assets/ai.worker-hash.js';

async function loaderSource() {
  // Register the real spec without executing either rendered case. Its normal
  // beforeEach supplies the actual init script to this explicit fake page.
  const setups = [],
    scripts = new Map();
  const registration = () => {};
  registration.beforeEach = (fn) => setups.push(fn);
  class Blob {
    constructor(parts) {
      this.source = parts.join('');
    }
  }
  class FixtureURL extends URL {
    static createObjectURL(blob) {
      const url = `blob:fixture-${scripts.size}`;
      scripts.set(url, blob.source);
      return url;
    }
    static revokeObjectURL() {}
  }
  let script;
  const window = {
    Worker: class {
      constructor(url) {
        script = scripts.get(url);
      }
      addEventListener() {}
    },
  };
  await loadTs(
    path,
    {
      '@playwright/test': {
        test: registration,
        expect: () => assert.fail('no rendered assertions'),
      },
    },
    { window, URL: FixtureURL, Blob, location: { href: 'https://fixture.invalid/sub/app/' } },
  );
  assert.equal(setups.length, 1);
  await setups[0]({ page: { addInitScript: async (fn) => fn(), on() {} } });
  new window.Worker(moduleUrl);
  assert.equal(typeof script, 'string', 'actual Worker constructor emits its Blob bootstrap');
  return script;
}

async function run(body) {
  const calls = [],
    response = { fixture: 'response identity' },
    scope = {
      fetch: async (input, init) => {
        calls.push({ input, init });
        return response;
      },
      addEventListener() {},
      dispatchEvent() {},
      postMessage() {},
    };
  const blocked = () => assert.fail('No Wasm execution in source fixture');
  const context = vm.createContext({
    self: scope,
    URL,
    Request,
    WebAssembly: { instantiate: blocked, instantiateStreaming: blocked },
  });
  const module = new vm.SourceTextModule(`export const done = ${await loaderSource()};`, {
    context,
    importModuleDynamically: async (url) => {
      assert.equal(url, moduleUrl, 'imports actual product URL supplied by caller');
      const product = new vm.SourceTextModule(body, { context });
      await product.link(() => assert.fail('no nested import'));
      await product.evaluate();
      return product;
    },
  });
  await module.link(() => assert.fail('no static import'));
  await module.evaluate();
  await module.namespace.done;
  return { calls, response, scope };
}

test('Blob bootstrap resolves root-relative and relative fetches against actual Worker URL', async () => {
  const { calls } = await run(
    "await self.fetch('/assets/othello_bg-hash.wasm'); await self.fetch('./asset.bin');",
  );
  assert.equal(calls[0].input.href, 'https://fixture.invalid/assets/othello_bg-hash.wasm');
  assert.equal(calls[1].input.href, 'https://fixture.invalid/sub/app/assets/asset.bin');
});

test('Blob bootstrap preserves absolute URLs, Request/options, and original fetch response identity', async () => {
  const { calls, response, scope } = await run(`
    self.request=new Request('https://fixture.invalid/raw');
    self.options={method:'GET',headers:{'x-fixture':'preserve'}};
    self.first=await self.fetch(new URL('https://other.invalid/asset'),self.options);
    self.second=await self.fetch(self.request,self.options);
  `);
  assert.equal(calls[0].input.href, 'https://other.invalid/asset');
  assert.equal(calls[0].init, scope.options);
  assert.equal(calls[1].init, scope.options);
  assert.equal(calls[1].input, scope.request);
  assert.equal(scope.first, response);
  assert.equal(scope.second, response);
});
