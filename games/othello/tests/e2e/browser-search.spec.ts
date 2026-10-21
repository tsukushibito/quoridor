import { expect, test, type Page } from '@playwright/test';
import type { AIRequest, AIResponse } from '../../../../apps/web/src/games/othello/ai-client';

// Root-only rendered qualification, relative to use.baseURL. No rules/search
// mocks: a test-only module Worker loader observes the genuine search_json entry
// and retains genuine replies. It calls original Wasm exports unchanged.
type Record = {
  entered: number;
  terminated: number;
  request: AIRequest | null;
  reply: AIResponse | null;
};
type Probe = { records: Record[]; deliver(id: number): void };
declare global {
  interface Window {
    __othelloSearchProbe: Probe;
  }
}
async function observe(page: Page) {
  await page.addInitScript(() => {
    // Self-contained function serialized into a test-only Blob module loader.
    async function bootstrap(moduleUrl: string) {
      const scope = self as unknown as { postMessage(value: unknown): void };
      // This test-only Blob has no HTTP base URL. Preserve the actual product
      // Worker's fetch resolution (including Vite's root-relative Wasm asset)
      // while forwarding original inputs/options and real responses unchanged.
      const nativeFetch = self.fetch.bind(self);
      self.fetch = (input, init) =>
        nativeFetch(
          typeof input === 'string' || input instanceof URL ? new URL(input, moduleUrl) : input,
          init,
        );
      const wrap = (instance: WebAssembly.Instance) => {
        const original = instance.exports;
        if (typeof original.search_json !== 'function') return instance;
        const observed = { ...original };
        observed.search_json = (...args: number[]) => {
          scope.postMessage({ __othelloSearchEntered: true });
          return (original.search_json as (...args: number[]) => unknown)(...args);
        };
        return new Proxy(instance, {
          get(target, key) {
            return key === 'exports' ? observed : Reflect.get(target, key, target);
          },
        });
      };
      const instantiate = WebAssembly.instantiate.bind(WebAssembly);
      WebAssembly.instantiate = (async (
        input: BufferSource | WebAssembly.Module,
        imports?: WebAssembly.Imports,
      ) => {
        if (input instanceof WebAssembly.Module) return wrap(await instantiate(input, imports));
        const result = await instantiate(input, imports);
        return { ...result, instance: wrap(result.instance) };
      }) as typeof WebAssembly.instantiate;
      const streaming = WebAssembly.instantiateStreaming.bind(WebAssembly);
      WebAssembly.instantiateStreaming = async (response, imports) => {
        const result = await streaming(response, imports);
        return { ...result, instance: wrap(result.instance) };
      };
      let ready = false;
      const queued: unknown[] = [];
      self.addEventListener('message', (event) => {
        if (!ready) {
          event.stopImmediatePropagation();
          queued.push(event.data);
        }
      });
      await import(moduleUrl); // The actual served product Worker, not a fixed source fallback.
      ready = true;
      for (const data of queued) self.dispatchEvent(new MessageEvent('message', { data }));
    }
    const retained = new Map<
      number,
      { worker: Worker; listener?: EventListenerOrEventListenerObject }
    >();
    const probe: Probe = (window.__othelloSearchProbe = {
      records: [],
      deliver(id) {
        const held = retained.get(id),
          reply = probe.records[id]?.reply;
        if (!held?.listener || !reply) throw Error('No genuine reply to deliver');
        const event = new MessageEvent('message', { data: reply });
        if (typeof held.listener === 'function') held.listener.call(held.worker, event);
        else held.listener.handleEvent(event);
      },
    });
    const Native = window.Worker;
    window.Worker = class extends Native {
      private entry: Record;
      private shim: string;
      constructor(url: string | URL, options?: WorkerOptions) {
        const moduleUrl = new URL(String(url), location.href).href;
        const shim = URL.createObjectURL(
          new Blob([`(${bootstrap.toString()})(${JSON.stringify(moduleUrl)})`], {
            type: 'text/javascript',
          }),
        );
        super(shim, { ...options, type: 'module' });
        this.shim = shim;
        this.entry = { entered: 0, terminated: 0, request: null, reply: null };
        const id = probe.records.length;
        probe.records.push(this.entry);
        retained.set(id, { worker: this });
        super.addEventListener('message', (event) => {
          if (event.data?.__othelloSearchEntered) this.entry.entered++;
          else this.entry.reply = event.data;
          event.stopImmediatePropagation(); // Explicit transport delivery barrier only.
        });
      }
      override postMessage(
        message: unknown,
        options?: Transferable[] | StructuredSerializeOptions,
      ) {
        this.entry.request = message as AIRequest;
        if (Array.isArray(options)) super.postMessage(message, options);
        else super.postMessage(message, options);
      }
      override addEventListener(
        type: string,
        listener: EventListenerOrEventListenerObject | null,
        options?: boolean | AddEventListenerOptions,
      ) {
        if (!listener) return;
        if (type === 'message')
          retained.get(probe.records.indexOf(this.entry))!.listener = listener;
        super.addEventListener(type, listener, options);
      }
      override terminate() {
        this.entry.terminated++;
        super.terminate();
        URL.revokeObjectURL(this.shim);
      }
    };
  });
}
const record = (page: Page, id: number) =>
  page.evaluate((id) => window.__othelloSearchProbe.records[id], id);
const raw = (page: Page) => page.evaluate(() => localStorage.getItem('othello.game.v1'));
const stones = (page: Page) =>
  page.locator('.othello-cell[data-stone="1"], .othello-cell[data-stone="2"]');
async function entered(page: Page, id: number) {
  await expect
    .poll(async () => {
      const current = await record(page, id);
      if (current?.reply?.error)
        throw new Error(`Worker failed before search entry: ${current.reply.error}`);
      return current?.entered;
    })
    .toBe(1);
  await expect.poll(() => page.workers().length).toBe(1);
}
async function completed(page: Page, id: number) {
  await expect.poll(async () => !!(await record(page, id))?.reply).toBe(true);
}
async function stale(page: Page, id: number) {
  const before = await raw(page),
    view = await page.locator('.othello-match, #othello-error').allTextContents();
  await page.evaluate((id) => window.__othelloSearchProbe.deliver(id), id);
  expect(await raw(page)).toBe(before);
  expect(await page.locator('.othello-match, #othello-error').allTextContents()).toEqual(view);
}
async function startSearch(page: Page) {
  await page.locator('#othello-mode').selectOption('ai');
  await expect(page.locator('#othello-strategy-label')).toBeVisible();
  await expect(page.locator('#othello-strategy')).toHaveValue('simple');
  await page.locator('#othello-human-side').selectOption('2');
  await page.locator('#othello-strategy').selectOption('searchV1');
  await page.locator('#othello-new').click();
}
test.beforeEach(async ({ page }) => {
  await observe(page);
  page.on('dialog', async (dialog) => {
    expect(dialog.type()).toBe('confirm');
    await dialog.accept();
  });
});

test('optional browser searchV1 uses actual baseline Wasm and saves explicit strategy; legacy stays simple', async ({
  page,
}, info) => {
  await page.goto('#/othello');
  await startSearch(page);
  await entered(page, 0);
  await completed(page, 0);
  const actual = (await record(page, 0))!;
  expect(actual.request?.strategy).toBe('searchV1');
  expect(actual.reply?.strategy).toBe('searchV1');
  expect(actual.reply?.token).toEqual(actual.request?.token);
  expect(actual.reply?.state).toEqual(actual.request?.state);
  expect(actual.reply?.error).toBeNull();
  expect(actual.reply?.searchResult?.cancelled).toBe(false);
  expect(actual.reply?.searchResult?.move).toBe(actual.reply?.move);
  await info.attach('actual-search-result.json', {
    body: JSON.stringify(actual),
    contentType: 'application/json',
  });
  // Actual elapsed/depth/proof are retained; no exact 1000ms or strength assertion.
  await expect(page.locator('#othello-players')).toContainText('探索AI（非学習・1秒）');
  await page.evaluate(() => window.__othelloSearchProbe.deliver(0));
  await expect(stones(page)).toHaveCount(5);
  expect(JSON.parse((await raw(page))!).strategy).toBe('searchV1');
  const legacy = JSON.parse((await raw(page))!);
  delete legacy.strategy;
  await page.evaluate(
    (value) => localStorage.setItem('othello.game.v1', value),
    JSON.stringify(legacy),
  );
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-strategy')).toHaveValue('simple');
  await expect(page.locator('#othello-players')).toContainText('簡易AI（非学習）');
  expect(JSON.parse((await raw(page))!).strategy).toBe('simple');
});

test('browser search Worker entry is revoked by cancel/strategy/new/resume/dispose; genuine stale reply cannot save', async ({
  page,
}, info) => {
  await page.goto('#/othello');
  await startSearch(page);
  await entered(page, 0);
  await completed(page, 0);
  // Retain one actual completed reply for stale-strategy/board delivery checks.
  const initial = await raw(page);
  await page.locator('#othello-cancel').click();
  await expect.poll(() => page.workers().length).toBe(0);
  expect((await record(page, 0))!.terminated).toBe(1);
  await stale(page, 0);
  await page.locator('#othello-retry-ai').click();
  await entered(page, 1);
  expect((await record(page, 1))!.reply).toBeNull();
  await page.locator('#othello-strategy').selectOption('simple');
  await expect.poll(() => page.workers().length).toBe(0);
  expect((await record(page, 1))!.terminated).toBe(1);
  expect(await raw(page)).toBe(initial);
  await page.locator('#othello-new').click();
  await completed(page, 2);
  expect((await record(page, 2))!.request?.strategy).toBe('simple');
  await page.evaluate(() => window.__othelloSearchProbe.deliver(2));
  await expect(stones(page)).toHaveCount(5);
  await stale(page, 0);
  await page.locator('#othello-strategy').selectOption('searchV1');
  await page.locator('#othello-new').click();
  await entered(page, 3);
  expect((await record(page, 3))!.reply).toBeNull();
  await page.locator('#othello-new').click();
  expect((await record(page, 3))!.terminated).toBe(1);
  await entered(page, 4);
  await stale(page, 0);
  expect((await record(page, 4))!.reply).toBeNull();
  await page.locator('#othello-resume').click();
  expect((await record(page, 4))!.terminated).toBe(1);
  await entered(page, 5);
  await stale(page, 0);
  expect((await record(page, 5))!.reply).toBeNull();
  await page.getByRole('link', { name: 'ゲーム一覧へ戻る' }).click();
  await expect(page.locator('.othello-page')).toHaveCount(0);
  await expect.poll(() => page.workers().length).toBe(0);
  expect((await record(page, 5))!.terminated).toBe(1);
  await stale(page, 0);
  await expect(page.locator('canvas')).toHaveCount(0);
  await info.attach('actual-worker-lifecycle.json', {
    body: JSON.stringify(await page.evaluate(() => window.__othelloSearchProbe.records)),
    contentType: 'application/json',
  });
});
