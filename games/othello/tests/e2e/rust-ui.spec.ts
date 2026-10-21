import { expect, test, type Page } from '@playwright/test';

// Root runs this file against config.use.baseURL and the real bundled application.
// Test-only barriers delay transport delivery/initialization, never replace Rust
// rules or manufacture AI moves. They are not search-budget/timing measurements.
const SAVE = 'othello.game.v1';
const CORRUPT = '{bad'; // Same malformed literal used by the changed Rust boundary tests.
const WASM = /\/[^/]*othello[^/]*\.wasm(?:\?|$)/;
type WorkerRecord = { id: number; terminated: number; replies: number };
type Probe = {
  workers: WorkerRecord[];
  owners: { created: number[]; freed: number[] };
  writes: string[];
  readMode: 'normal' | 'fail' | 'leaveWhilePending';
  pendingRead: { before: string | null; after: string | null; saveDisabled: boolean } | null;
  raw(): string | null;
  seed(raw: string): void;
  deliver(id: number): void;
};
declare global {
  interface Window {
    __othelloUIProbe: Probe;
  }
}

async function observe(page: Page) {
  await page.addInitScript(
    ({ key }) => {
      const originalGet = Storage.prototype.getItem;
      const originalSet = Storage.prototype.setItem;
      const raw = () => originalGet.call(localStorage, key);
      const retained = new Map<
        number,
        { worker: Worker; listener?: EventListenerOrEventListenerObject; data?: unknown }
      >();
      const probe: Probe = (window.__othelloUIProbe = {
        workers: [],
        owners: { created: [], freed: [] },
        writes: [],
        readMode: 'normal',
        pendingRead: null,
        raw,
        seed(value) {
          originalSet.call(localStorage, key, value);
        },
        deliver(id) {
          const record = retained.get(id);
          if (!record?.listener || record.data === undefined)
            throw Error('No genuine Worker reply captured');
          const event = new MessageEvent('message', { data: record.data });
          if (typeof record.listener === 'function') record.listener.call(record.worker, event);
          else record.listener.handleEvent(event);
        },
      });
      Storage.prototype.setItem = function (name, value) {
        if (this === localStorage && name === key) probe.writes.push(value);
        return originalSet.call(this, name, value);
      };
      Storage.prototype.getItem = function (name) {
        if (this !== localStorage || name !== key) return originalGet.call(this, name);
        if (probe.readMode === 'fail') {
          probe.readMode = 'normal';
          throw new DOMException('test-only resume read failure', 'SecurityError');
        }
        if (probe.readMode === 'leaveWhilePending') {
          probe.readMode = 'normal';
          const before = raw();
          const save = document.querySelector<HTMLButtonElement>('#othello-save')!;
          // A synchronous, reentrant browser-storage barrier: Rust has emitted
          // ReadSave but Loaded has not returned. Force the disabled Save action
          // to check Rust refusal, then deliver route teardown before returning.
          save.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          probe.pendingRead = { before, after: raw(), saveDisabled: save.disabled };
          location.hash = '#/';
          window.dispatchEvent(new HashChangeEvent('hashchange'));
          return before;
        }
        return originalGet.call(this, name);
      };

      const NativeWorker = window.Worker;
      window.Worker = class extends NativeWorker {
        private record: WorkerRecord;
        constructor(url: string | URL, options?: WorkerOptions) {
          super(url, options); // Actual product Worker, actual simple-policy Wasm.
          this.record = { id: probe.workers.length, terminated: 0, replies: 0 };
          probe.workers.push(this.record);
          const capture = { worker: this } as {
            worker: Worker;
            listener?: EventListenerOrEventListenerObject;
            data?: unknown;
          };
          retained.set(this.record.id, capture);
          super.addEventListener('message', (event) => {
            this.record.replies++;
            capture.data = event.data;
            event.stopImmediatePropagation(); // Explicit reply-delivery barrier.
          });
        }
        override addEventListener(
          type: string,
          listener: EventListenerOrEventListenerObject | null,
          options?: boolean | AddEventListenerOptions,
        ) {
          if (!listener) return;
          if (type === 'message') retained.get(this.record.id)!.listener = listener;
          super.addEventListener(type, listener, options);
        }
        override terminate() {
          this.record.terminated++;
          super.terminate();
        }
      };

      // Count real Rust UI allocations and explicit frees, including an owner
      // created after a held init completes following route teardown. All original
      // Wasm exports execute unchanged; only the JS instance.exports view is observed.
      const wrap = (instance: WebAssembly.Instance) => {
        const exports = instance.exports;
        if (typeof exports.othelloui_new !== 'function') return instance;
        const observed = { ...exports };
        observed.othelloui_new = (...args: number[]) => {
          const pointer = (exports.othelloui_new as (...args: number[]) => number)(...args);
          probe.owners.created.push(pointer);
          return pointer;
        };
        observed.__wbg_othelloui_free = (...args: number[]) => {
          probe.owners.freed.push(args[0]!);
          return (exports.__wbg_othelloui_free as (...args: number[]) => void)(...args);
        };
        return new Proxy(instance, {
          get(target, property) {
            return property === 'exports' ? observed : Reflect.get(target, property, target);
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
    },
    { key: SAVE },
  );
}

function dialogs(page: Page) {
  const choices: boolean[] = [];
  const messages: string[] = [];
  page.on('dialog', async (dialog) => {
    expect(dialog.type()).toBe('confirm');
    messages.push(dialog.message());
    if (choices.shift() ?? true) await dialog.accept();
    else await dialog.dismiss();
  });
  return {
    async click(selector: string, accepted = true) {
      const before = messages.length;
      choices.push(accepted);
      await page.locator(selector).click();
      // A pending-read teardown may also display the real exit confirmation.
      await expect.poll(() => messages.length).toBeGreaterThan(before);
    },
  };
}
const raw = (page: Page) => page.evaluate(() => window.__othelloUIProbe.raw());
const seed = (page: Page, value: string) =>
  page.evaluate((value) => window.__othelloUIProbe.seed(value), value);
const stones = (page: Page) =>
  page.locator('.othello-cell[data-stone="1"], .othello-cell[data-stone="2"]');
const worker = (page: Page, id: number) =>
  page.evaluate((id) => window.__othelloUIProbe.workers[id], id);
async function replyReady(page: Page, id: number) {
  await expect.poll(async () => (await worker(page, id))?.replies).toBe(1);
  await expect.poll(() => page.workers().length).toBe(1);
}
async function stale(page: Page, id: number) {
  const before = await raw(page),
    writes = await page.evaluate(() => window.__othelloUIProbe.writes.length);
  const view = await page.locator('#othello-error, .othello-match').allTextContents();
  await page.evaluate((id) => window.__othelloUIProbe.deliver(id), id);
  expect(await raw(page)).toBe(before);
  expect(await page.evaluate(() => window.__othelloUIProbe.writes.length)).toBe(writes);
  expect(await page.locator('#othello-error, .othello-match').allTextContents()).toEqual(view);
}
async function home(page: Page) {
  await page.getByRole('link', { name: 'ゲーム一覧へ戻る' }).click();
  await expect(page.locator('.othello-page')).toHaveCount(0);
  await expect(page.locator('canvas')).toHaveCount(0);
  await expect.poll(() => page.workers().length).toBe(0);
}
async function forceSaveRefusal(page: Page, expected: string) {
  await expect(page.locator('#othello-save')).toBeDisabled();
  await page.locator('#othello-save').dispatchEvent('click');
  expect(await raw(page)).toBe(expected);
}

test.beforeEach(async ({ page }) => {
  await observe(page);
});

test('actual confirmation/cancel, local and simple-AI modes, and both human colors', async ({
  page,
}) => {
  const confirm = dialogs(page);
  await page.goto('#/othello');
  await confirm.click('#othello-new', false);
  await expect(page.locator('.othello-match')).toBeHidden();
  expect(await raw(page)).toBeNull();
  await confirm.click('#othello-new');
  await expect(stones(page)).toHaveCount(4);
  await page.locator('.othello-cell[data-index="19"]').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 4 石 ／ 白 1 石');
  const moved = await raw(page);
  await confirm.click('#othello-new', false);
  expect(await raw(page)).toBe(moved);
  await page.locator('#othello-mode').selectOption('ai');
  await expect(page.locator('#othello-side-label')).toBeVisible();
  await confirm.click('#othello-new');
  await expect(page.locator('#othello-players')).toContainText('人間：黒');
  expect(await page.evaluate(() => window.__othelloUIProbe.workers.length)).toBe(0);
  await page.locator('.othello-cell[data-index="19"]').click();
  await replyReady(page, 0);
  await page.evaluate(() => window.__othelloUIProbe.deliver(0));
  await expect(stones(page)).toHaveCount(6);
  await expect(page.locator('#othello-turn')).toHaveText('黒の手番');
  await page.locator('#othello-human-side').selectOption('2');
  await confirm.click('#othello-new');
  await expect(page.locator('#othello-players')).toContainText('人間：白');
  await replyReady(page, 1);
  await expect(stones(page)).toHaveCount(4);
  await page.evaluate(() => window.__othelloUIProbe.deliver(1));
  await expect(stones(page)).toHaveCount(5);
  await expect(page.locator('#othello-turn')).toHaveText('白の手番');
});

test('corrupt and failed resume preserve the exact slot through Save/home; explicit new and valid resume may replace it', async ({
  page,
}) => {
  const confirm = dialogs(page);
  await page.goto('#/othello');
  await confirm.click('#othello-new');
  const initial = (await raw(page))!;
  await page.evaluate(() => localStorage.setItem('quoridor.rust-ui-test-sentinel', 'untouched'));
  await seed(page, CORRUPT);
  await confirm.click('#othello-resume');
  await expect(page.locator('#othello-error')).toContainText('保存形式を確認できません');
  await forceSaveRefusal(page, CORRUPT);
  await home(page);
  expect(await raw(page)).toBe(CORRUPT);
  await page.goto('#/othello');
  await confirm.click('#othello-new');
  expect(await raw(page)).toBe(initial);
  const spaced = `  ${initial}  `;
  await seed(page, spaced);
  await page.evaluate(() => {
    window.__othelloUIProbe.readMode = 'fail';
  });
  await confirm.click('#othello-resume');
  await expect(page.locator('#othello-error')).toContainText('test-only resume read failure');
  await forceSaveRefusal(page, spaced);
  await home(page);
  expect(await raw(page)).toBe(spaced);
  await page.goto('#/othello');
  await confirm.click('#othello-resume');
  await expect(stones(page)).toHaveCount(4);
  expect(await raw(page)).toBe(initial);
  expect(await page.evaluate(() => localStorage.getItem('quoridor.rust-ui-test-sentinel'))).toBe(
    'untouched',
  );
});

test('real Worker cancellation/new/resume/setup/dispose revoke captured genuine replies and recreate ownership', async ({
  page,
}) => {
  const confirm = dialogs(page),
    unrelatedWasm: string[] = [];
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith('.wasm') && !path.includes('othello')) unrelatedWasm.push(path);
  });
  await page.goto('#/othello');
  await page.locator('#othello-mode').selectOption('ai');
  await expect(page.locator('#othello-side-label')).toBeVisible();
  await page.locator('#othello-human-side').selectOption('2');
  await confirm.click('#othello-new');
  await replyReady(page, 0);
  await page.locator('#othello-cancel').click();
  expect((await worker(page, 0))!.terminated).toBe(1);
  await expect.poll(() => page.workers().length).toBe(0);
  await stale(page, 0);
  await page.locator('#othello-retry-ai').click();
  await replyReady(page, 1);
  await stale(page, 0);
  await confirm.click('#othello-new');
  expect((await worker(page, 1))!.terminated).toBe(1);
  await replyReady(page, 2);
  await stale(page, 1);
  await confirm.click('#othello-resume');
  expect((await worker(page, 2))!.terminated).toBe(1);
  await replyReady(page, 3);
  await stale(page, 2);
  await page.locator('#othello-mode').selectOption('local');
  expect((await worker(page, 3))!.terminated).toBe(1);
  await stale(page, 3);
  await page.locator('#othello-retry-ai').click();
  await replyReady(page, 4);
  await home(page);
  expect((await worker(page, 4))!.terminated).toBe(1);
  await stale(page, 4);
  await expect.poll(() => page.evaluate(() => window.__othelloUIProbe.owners.freed.length)).toBe(1);
  // Same document reentry: no reload to hide retained callbacks or lifetime leaks.
  await page.evaluate(() => {
    location.hash = '#/othello';
  });
  await expect(page.locator('.othello-page')).toBeVisible();
  await confirm.click('#othello-new');
  await expect(stones(page)).toHaveCount(4);
  await stale(page, 4);
  await expect(page.locator('#othello-players')).toContainText('ローカル2人');
  expect(unrelatedWasm).toEqual([]);
  await home(page);
  expect(await page.evaluate(() => window.__othelloUIProbe.owners.created.length)).toBe(2);
  expect(await page.evaluate(() => window.__othelloUIProbe.owners.freed.length)).toBe(2);
});

test('pending Rust ReadSave refuses Save and teardown overwrite before its raw completion returns', async ({
  page,
}) => {
  const confirm = dialogs(page);
  await page.goto('#/othello');
  await confirm.click('#othello-new');
  await page.locator('.othello-cell[data-index="19"]').click();
  const moved = (await raw(page))!;
  await confirm.click('#othello-new');
  const original = ` ${moved}  `;
  await seed(page, original);
  const writes = await page.evaluate(() => window.__othelloUIProbe.writes.length);
  await page.evaluate(() => {
    window.__othelloUIProbe.readMode = 'leaveWhilePending';
  });
  await confirm.click('#othello-resume');
  await expect(page.locator('.othello-page')).toHaveCount(0);
  expect(await page.evaluate(() => window.__othelloUIProbe.pendingRead)).toEqual({
    before: original,
    after: original,
    saveDisabled: true,
  });
  expect(await raw(page)).toBe(original);
  expect(await page.evaluate(() => window.__othelloUIProbe.writes.length)).toBe(writes);
  expect(await page.evaluate(() => window.__othelloUIProbe.owners.freed.length)).toBe(1);
  await expect(page.locator('canvas')).toHaveCount(0);
});

test('lazy Wasm failure retries; a late real UI owner is freed after home and reentry works', async ({
  page,
}) => {
  const confirm = dialogs(page);
  let requests = 0;
  const fail = async (route: import('@playwright/test').Route) => {
    // Do not poison a dev server's ?url ESM module cache; fail the Wasm fetch.
    if (route.request().resourceType() === 'script') {
      await route.continue();
      return;
    }
    requests++;
    await route.abort('failed');
  };
  await page.route(WASM, fail);
  await page.goto('#/othello');
  expect(requests).toBe(0);
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-error')).toContainText('再試行できます');
  expect(requests).toBeGreaterThan(0);
  expect(await raw(page)).toBeNull();
  await page.unroute(WASM, fail);
  let release!: () => void,
    entered = false;
  const barrier = new Promise<void>((resolve) => {
    release = resolve;
  });
  const hold = async (route: import('@playwright/test').Route) => {
    if (route.request().resourceType() === 'script') {
      await route.continue();
      return;
    }
    entered = true;
    await barrier;
    await route.continue();
  };
  await page.route(WASM, hold);
  try {
    await page.locator('#othello-new').click();
    await expect.poll(() => entered).toBe(true);
    await home(page);
    expect(await raw(page)).toBeNull();
  } finally {
    release();
  }
  await expect
    .poll(() => page.evaluate(() => window.__othelloUIProbe.owners.created.length))
    .toBe(1);
  await expect.poll(() => page.evaluate(() => window.__othelloUIProbe.owners.freed.length)).toBe(1);
  expect(await raw(page)).toBeNull();
  await page.unroute(WASM, hold);
  await page.evaluate(() => {
    location.hash = '#/othello';
  });
  await expect(page.locator('.othello-page')).toBeVisible();
  await confirm.click('#othello-new');
  await expect(stones(page)).toHaveCount(4);
  await home(page);
  expect(await page.evaluate(() => window.__othelloUIProbe.owners.created.length)).toBe(2);
  expect(await page.evaluate(() => window.__othelloUIProbe.owners.freed.length)).toBe(2);
});
