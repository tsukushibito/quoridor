import { test, expect, type Page } from '@playwright/test';

const OTHELLO_SAVE = 'othello.game.v1';
const LEGACY_GAME = 'quoridor.m1.game.v1';
const LEGACY_SETTINGS = 'quoridor.m1.settings.v1';
const LEGACY_AUDIO = 'quoridor.audio.settings.v1';
const cell = (page: Page, index: number) => page.locator(`.othello-cell[data-index="${index}"]`);
const openOthello = async (page: Page) => {
  await page.locator('#choose-othello').click();
  await expect(page.locator('.othello h1')).toHaveText('Othello');
};
const leaveOthello = async (page: Page) => {
  await page.getByRole('link', { name: 'ゲーム一覧へ戻る' }).click();
  await expect(page.locator('.home-page')).toBeVisible();
};
async function legacySlots(page: Page) {
  return page.evaluate(
    ([game, settings, audio]) => [game, settings, audio].map((key) => localStorage.getItem(key!)),
    [LEGACY_GAME, LEGACY_SETTINGS, LEGACY_AUDIO],
  );
}
async function savedOthello(page: Page) {
  return page.evaluate((key) => localStorage.getItem(key), OTHELLO_SAVE);
}

test('new cross-game flow plays and saves both games, resumes legacy and Othello slots, preserves history and basepath', async ({
  page,
}) => {
  // Two real Quoridor mounts and teardown compile/render PBR on the assigned single CPU.
  // This test budget is independent of the unchanged process resource/deadline guard.
  test.setTimeout(120_000);
  const requests: string[] = [],
    errors: string[] = [];
  page.on('request', (request) => requests.push(request.url()));
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('./?forceWebGL=1#/');
  await expect(page.locator('#choose-othello')).toBeVisible();
  expect(
    requests.filter((url) => /\.wasm|ai\.worker|quoridor-|othello-|\.hdr|\.mp3|\.ogg/.test(url)),
  ).toEqual([]);
  await page.locator('#choose-quoridor').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase))
    .toBe('ready');
  await page.locator('#startup-new-game').click();
  await page.locator('#match-mode').selectOption('pvp');
  await page.locator('#dialog-start').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase))
    .toBe('humanTurn');
  const point = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectCell(13));
  await page.mouse.click(point.x, point.y);
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().view?.ply))
    .toBe(1);
  const replay = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay());
  await page.locator('.top-actions .home-link').click();
  await expect(page.locator('.home-page')).toBeVisible();
  const legacy = await legacySlots(page);
  expect(legacy[0]).toBeTruthy();
  await openOthello(page);
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 2 石 ／ 白 2 石');
  await cell(page, 19).click();
  await expect(page.locator('#othello-score')).toHaveText('黒 4 石 ／ 白 1 石');
  await expect(cell(page, 27)).toHaveAttribute('data-stone', '1');
  const othello = await savedOthello(page);
  await page.screenshot({ path: test.info().outputPath('othello-play.png') });
  await leaveOthello(page);
  expect(await legacySlots(page)).toEqual(legacy);
  await page.locator('#choose-quoridor').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase))
    .toBe('ready');
  await page.locator('#resume-game-choice').click();
  await expect
    .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase))
    .toBe('humanTurn');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay())).toEqual(
    replay,
  );
  expect(await savedOthello(page)).toBe(othello);
  await page.locator('.top-actions .home-link').click();
  await openOthello(page);
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 4 石 ／ 白 1 石');
  await expect(page.locator('#othello-players')).toContainText('ローカル2人');
  await page.goBack();
  await expect(page.locator('.home-page')).toBeVisible();
  await page.goForward();
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-turn')).toHaveText('白の手番');
  await page.goto('./?forceWebGL=1#/othello');
  expect(new URL(page.url()).pathname).toBe(new URL(test.info().project.use.baseURL!).pathname);
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 4 石 ／ 白 1 石');
  await expect(page.locator('canvas, dialog')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('Othello-only entry remains lazy on home, keyboard play and real bounded AI use explicit human colors', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const workers: string[] = [];
  page.on('worker', (worker) => workers.push(worker.url()));
  await page.goto('./#/');
  await openOthello(page);
  expect(workers).toEqual([]);
  await page.locator('#othello-new').click();
  await expect(cell(page, 19)).toHaveAttribute('aria-disabled', 'false');
  await cell(page, 19).focus();
  await page.keyboard.press('ArrowRight');
  await expect(cell(page, 20)).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('Enter');
  await expect(page.locator('#othello-score')).toHaveText('黒 4 石 ／ 白 1 石');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('#othello-mode').selectOption('ai');
  await page.locator('#othello-human-side').selectOption('2');
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-players')).toHaveText(
    '簡易AI（非学習）と対戦 · 人間：白 ／ 簡易AI：黒',
  );
  await expect(page.locator('#othello-score')).toHaveText('黒 4 石 ／ 白 1 石');
  await expect(page.locator('#othello-turn')).toHaveText('白の手番');
  expect(workers).toHaveLength(1);
  await expect(cell(page, 19)).toHaveAttribute('data-stone', '1');
  await leaveOthello(page);
  await openOthello(page);
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-players')).toContainText('人間：白 ／ 簡易AI：黒');
  await expect(page.locator('#othello-turn')).toHaveText('白の手番');
  expect(workers).toHaveLength(1);
});

test('Othello Worker pending cancellation terminates once and rejects a deliberately late message without mutation or legacy writes', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const Native = window.Worker;
    const monitor = { starts: 0, stops: 0, late: () => {} };
    (window as any).othelloWorker = monitor;
    window.Worker = class extends Native {
      override postMessage(message: any): void {
        monitor.starts++;
        const callback = (this as any).savedCallback;
        monitor.late = () =>
          callback(
            new MessageEvent('message', {
              data: { id: message.id, generation: message.generation, ok: true, move: 19 },
            }),
          );
        // Keep the real game-owned Worker pending; deliver the captured callback after teardown.
      }
      override addEventListener(type: any, callback: any, options?: any): void {
        if (type === 'message') (this as any).savedCallback = callback;
        super.addEventListener(type, callback, options);
      }
      override terminate(): void {
        monitor.stops++;
        super.terminate();
      }
    };
    localStorage.setItem('quoridor.m1.game.v1', 'legacy sentinel');
    localStorage.setItem('quoridor.m1.settings.v1', 'settings sentinel');
    localStorage.setItem('quoridor.audio.settings.v1', 'audio sentinel');
  });
  await page.goto('./#/othello');
  const legacy = await legacySlots(page);
  await page.locator('#othello-mode').selectOption('ai');
  await page.locator('#othello-human-side').selectOption('2');
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-turn')).toContainText('考えています');
  const confirmed = await savedOthello(page);
  await leaveOthello(page);
  await page.evaluate(() => (window as any).othelloWorker.late());
  await expect(page.locator('.othello, .othello-board, canvas')).toHaveCount(0);
  expect(await savedOthello(page)).toBe(confirmed);
  expect(await legacySlots(page)).toEqual(legacy);
  expect(
    await page.evaluate(() => ({
      starts: (window as any).othelloWorker.starts,
      stops: (window as any).othelloWorker.stops,
    })),
  ).toEqual({ starts: 1, stops: 1 });
});

test('leaving Othello during actual Wasm initialization cannot save or render the late result', async ({
  page,
}) => {
  let release!: () => void, requested!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const reached = new Promise<void>((resolve) => {
    requested = resolve;
  });
  await page.route('**/*othello_bg*.wasm', async (route) => {
    requested();
    await gate;
    await route.continue();
  });
  await page.goto('./#/othello');
  await page.locator('#othello-new').click();
  await reached;
  await leaveOthello(page);
  release();
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.othello, .othello-board')).toHaveCount(0);
  expect(await savedOthello(page)).toBeNull();
});

test('bad saves are retained, retry and explicit new are available, unavailable storage is visible through exit', async ({
  page,
}) => {
  await page.goto('./#/othello');
  await page.evaluate((key) => localStorage.setItem(key, '{broken'), OTHELLO_SAVE);
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-error')).not.toBeEmpty();
  expect(await savedOthello(page)).toBe('{broken');
  await page.locator('#othello-resume').click();
  expect(await savedOthello(page)).toBe('{broken');
  // The user's explicit new selection authorizes replacing the broken Othello slot.
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 2 石 ／ 白 2 石');
  await page.evaluate(() => {
    Storage.prototype.setItem = () => {
      throw new DOMException('quota', 'QuotaExceededError');
    };
  });
  await cell(page, 19).click();
  await expect(page.locator('#othello-save-status')).toContainText('保存できません');
  await leaveOthello(page);
  await expect(page.locator('#home-save-warning')).toContainText('Othelloを保存できません');
});

test('saved forced-pass and terminal fixtures render Rust status, wins and draw without JS rules', async ({
  page,
}) => {
  await page.goto('./#/othello');
  async function resume(board: number[], toMove: number) {
    await page.evaluate(
      ({ key, board, toMove }) =>
        localStorage.setItem(
          key,
          JSON.stringify({
            version: 1,
            game: 'othello',
            mode: 'local',
            humanSide: 1,
            state: { version: 1, board, toMove },
          }),
        ),
      { key: OTHELLO_SAVE, board, toMove },
    );
    await page.locator('#othello-resume').click();
  }
  const forced = Array<number>(64).fill(0);
  forced[0] = 1;
  forced[1] = 2;
  await resume(forced, 2);
  await expect(page.locator('#othello-guide')).toContainText('パスが必要');
  await page.locator('#othello-pass').click();
  await expect(page.locator('#othello-turn')).toHaveText('黒の手番');
  await cell(page, 2).click();
  await expect(page.locator('#othello-turn')).toHaveText('終局：黒の勝ち');
  await expect(page.locator('#othello-score')).toHaveText('黒 3 石 ／ 白 0 石');
  await resume(Array<number>(64).fill(2), 1);
  await expect(page.locator('#othello-turn')).toHaveText('終局：白の勝ち');
  await resume(
    Array.from({ length: 64 }, (_, i) => (i < 32 ? 1 : 2)),
    2,
  );
  await expect(page.locator('#othello-turn')).toHaveText('終局：引分け');
  await expect(page.locator('#othello-pass')).toBeHidden();
  expect(await page.locator('.othello-cell[aria-disabled="false"]').count()).toBe(0);
});

test('active Othello failed resume preserves corrupt slot on exit until explicit new choice', async ({
  page,
}) => {
  await page.goto('./#/othello');
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 2 石 ／ 白 2 石');
  await page.evaluate((key) => localStorage.setItem(key, '{active corrupt save'), OTHELLO_SAVE);
  await page.locator('#othello-resume').click();
  await expect(page.locator('#othello-error')).not.toBeEmpty();
  await page.locator('#othello-save').click();
  await expect(page.locator('#othello-save-status')).toContainText('元の保存を保持');
  expect(await savedOthello(page)).toBe('{active corrupt save');
  await leaveOthello(page);
  await expect(page.locator('#home-save-warning')).toContainText('元の保存を保持');
  expect(await savedOthello(page)).toBe('{active corrupt save');
  await openOthello(page);
  await page.locator('#othello-new').click();
  await expect(page.locator('#othello-score')).toHaveText('黒 2 石 ／ 白 2 石');
  expect(JSON.parse((await savedOthello(page))!).version).toBe(1);
});
