import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

async function ready(page: Page): Promise<void> {
  await page.goto('./?forceWebGL=1');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase)).toBe('humanTurn');
}
async function state(page: Page) { return page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state()); }
async function clickCell(page: Page, cell: number): Promise<void> {
  await page.locator('#board canvas').evaluate(element => element.scrollIntoView({ block: 'center' }));
  const point = await page.evaluate(id => window.__QUORIDOR_APP_TEST_API__!.projectCell(id), cell);
  await page.mouse.click(point.x, point.y);
}
async function openMenu(page: Page): Promise<void> {
  await page.locator('#open-menu').click();
  if (!await page.locator('#no-animation').isVisible()) await page.locator('.settings summary').click();
}
async function closeMenu(page: Page): Promise<void> { await page.locator('#close-menu').click(); }
async function openMatch(page: Page): Promise<void> { await page.locator('#new-game').click(); }
async function startMatch(page: Page): Promise<void> { await page.locator('#dialog-start').click(); }
async function saved(page: Page) {
  return page.evaluate(() => JSON.parse(localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY)!) as {
    match: { mode: string; humanSide: number; simulations: number }; replay: { ply: number; positionKey: string; actions: number[] } });
}

test('one PvP slot resumes via real UI, preserves next-game settings and undo, then explicit new game replaces it', async ({ page }) => {
  await ready(page);
  await clickCell(page, 13);
  await expect.poll(() => saved(page).then(x => x.replay.ply)).toBe(1);
  const key = (await state(page)).view!.positionKey;
  await openMatch(page);
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#human-side').selectOption('1');
  await page.locator('#ai-budget').selectOption('192');
  await page.locator('#dialog-cancel').click();
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  expect((await saved(page)).match).toEqual({ mode: 'pvp', humanSide: 0, simulations: 96 });
  await page.reload();
  await expect(page.getByRole('button', { name: '前の対局を再開' })).toBeVisible();
  expect((await state(page)).view).toBeNull();
  await page.locator('#startup-new-game').click();
  await expect(page.locator('#match-mode')).toHaveValue('ai');
  await expect(page.locator('#human-side')).toHaveValue('1');
  await expect(page.locator('#ai-budget')).toHaveValue('192');
  await page.locator('#dialog-cancel').click();
  await page.getByRole('button', { name: '前の対局を再開' }).click();
  expect((await state(page)).view?.positionKey).toBe(key);
  expect((await state(page)).matchMode).toBe('pvp');
  await expect(page.locator('#board canvas')).toBeFocused();
  await page.keyboard.press('ArrowUp');
  expect((await state(page)).selectedId).not.toBeNull();
  await page.keyboard.press('Escape');
  expect((await state(page)).selectedId).toBeNull();
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).view?.ply).toBe(0);
  expect((await saved(page)).replay.ply).toBe(0);
  await openMenu(page);
  await expect(page.locator('#no-animation')).toBeChecked();
  await closeMenu(page);
  await openMatch(page);
  await startMatch(page);
  await expect.poll(() => state(page).then(x => x.phase)).toMatch(/aiThinking|humanTurn/);
  expect((await saved(page)).match).toEqual({ mode: 'ai', humanSide: 1, simulations: 192 });
});

test('both AI sides resume active assignment independent of edited next-game controls', async ({ page }) => {
  for (const side of [0, 1] as const) {
    await ready(page);
    await openMatch(page);
    await page.locator('#match-mode').selectOption('ai');
    await page.locator('#human-side').selectOption(String(side));
    await page.locator('#ai-budget').selectOption('48');
    await startMatch(page);
    await openMenu(page);
    await page.locator('#no-animation').check();
    await closeMenu(page);
    await expect.poll(() => state(page).then(x => x.phase), { timeout: 20000 }).toBe('humanTurn');
    const before = await state(page);
    expect((await saved(page)).match).toEqual({ mode: 'ai', humanSide: side, simulations: 48 });
    await openMatch(page);
    await page.locator('#match-mode').selectOption('pvp');
    await page.locator('#dialog-cancel').click();
    await page.reload();
    await expect(page.getByRole('button', { name: '前の対局を再開' })).toBeVisible();
    await page.getByRole('button', { name: '前の対局を再開' }).click();
    await expect.poll(() => state(page).then(x => x.phase), { timeout: 20000 }).toBe('humanTurn');
    expect((await state(page)).view?.positionKey).toBe(before.view?.positionKey);
    expect((await state(page)).matchMode).toBe('ai');
    expect((await state(page)).humanSide).toBe(side);
    if (side === 1) expect(await page.getByRole('button', { name: '1手戻す' }).isDisabled()).toBe(true);
    await page.evaluate(() => localStorage.clear());
  }
});

test('committed pawn and wall animation states save immediately; AI thought resumes once', async ({ page }) => {
  await ready(page);
  await clickCell(page, 13);
  expect((await saved(page)).replay.ply).toBe(1);
  await page.reload();
  await page.getByRole('button', { name: '前の対局を再開' }).click();
  expect((await state(page)).view?.ply).toBe(1);
  await page.getByRole('button', { name: '壁を置く' }).click();
  const wall = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.click(wall.x, wall.y);
  expect((await saved(page)).replay.ply).toBe(2);
  await page.reload();
  await page.getByRole('button', { name: '前の対局を再開' }).click();
  expect((await state(page)).view?.horizontalWalls).toContain(27);
  await openMatch(page);
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#ai-budget').selectOption('4096');
  await startMatch(page);
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  await clickCell(page, 13);
  expect((await state(page)).phase).toBe('aiThinking');
  expect((await saved(page)).replay.ply).toBe(1);
  await page.reload();
  await page.getByRole('button', { name: '前の対局を再開' }).click();
  await expect.poll(() => state(page).then(x => x.view?.ply), { timeout: 20000 }).toBe(2);
  await expect.poll(() => state(page).then(x => x.phase), { timeout: 20000 }).toBe('humanTurn');
  await page.waitForTimeout(400);
  expect((await state(page)).view?.ply).toBe(2);
});

test('corrupt slot remains until explicit clear or replacement; settings corruption is independent', async ({ page }) => {
  await ready(page);
  const api = await page.evaluate(() => ({ GAME_KEY: window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY,
    SETTINGS_KEY: window.__QUORIDOR_PERSISTENCE_TEST_API__!.SETTINGS_KEY }));
  await page.evaluate(({ gameKey, settingsKey }) => {
    localStorage.setItem(gameKey, '42');
    localStorage.setItem(settingsKey, '{"schemaVersion":99}');
  }, { gameKey: api.GAME_KEY, settingsKey: api.SETTINGS_KEY });
  await page.reload();
  await expect(page.locator('#save-status')).toContainText('読み込めません');
  await expect(page.locator('#settings-status')).toContainText('既定');
  expect(await page.evaluate(key => localStorage.getItem(key), api.GAME_KEY)).toBe('42');
  expect((await state(page)).view).toBeNull();
  await page.locator('#startup-clear-save').click();
  expect(await page.evaluate(key => localStorage.getItem(key), api.GAME_KEY)).toBeNull();
  await startMatch(page);
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  const valid = await saved(page);
  await page.evaluate(({ key, value }) => localStorage.setItem(key, JSON.stringify(value)), {
    key: api.GAME_KEY, value: { ...valid, replay: { ...valid.replay, positionKey: '0'.repeat(42) } },
  });
  await page.reload();
  await expect(page.locator('#save-status')).toContainText('読み込めません');
  expect((await state(page)).view).toBeNull();
  await page.locator('#startup-new-game').click();
  await startMatch(page);
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  expect((await saved(page)).replay.positionKey).not.toBe('0'.repeat(42));
  mkdirSync('artifacts', { recursive: true });
  await page.screenshot({ path: `artifacts/phase4-${process.env.E2E_MODE || 'dev'}-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await openMenu(page);
  await expect(page.getByRole('button', { name: '保存を消す' })).toBeVisible();
  await page.screenshot({ path: `artifacts/phase4-${process.env.E2E_MODE || 'dev'}-narrow.png`, fullPage: true });
});

test('storage adapter rejects malformed envelopes and blocked/quota operations without altering prior data', async ({ page }) => {
  await ready(page);
  const result = await page.evaluate(() => {
    const api = window.__QUORIDOR_PERSISTENCE_TEST_API__!;
    const replay = window.__QUORIDOR_APP_TEST_API__!.exportReplay();
    const valid = { schemaVersion: 1, rulesetId: 'standard-2p-v1', match: { mode: 'pvp', humanSide: 0, simulations: 96 }, replay };
    const content = new Map<string, string>();
    const port = { getItem: (key: string) => content.get(key) ?? null,
      setItem: (key: string, value: string) => { content.set(key, value); }, removeItem: (key: string) => { content.delete(key); } };
    const repo = new api.LocalStateRepository(() => port);
    const roundtrip = repo.writeGame(valid as never).status === 'ok' && repo.readGame().status === 'ok';
    const original = content.get(api.GAME_KEY)!;
    const invalid = [
      null, 42, [], { ...valid, schemaVersion: 2 }, { ...valid, rulesetId: 'other' },
      { ...valid, match: { ...valid.match, humanSide: 1 } },
      { ...valid, replay: { ...replay, actions: [999], ply: 1 } },
      { ...valid, replay: { ...replay, actions: [13], ply: 2 } },
      { ...valid, replay: { ...replay, positionKey: '-1' } },
      { ...valid, replay: { ...replay, actions: Array(4097).fill(13), ply: 4097 } },
      { ...valid, extra: true },
    ];
    const rejected = invalid.map(value => { content.set(api.GAME_KEY, JSON.stringify(value)); return repo.readGame().status; });
    content.set(api.GAME_KEY, 'x'.repeat(70_001)); const oversized = repo.readGame().status;
    content.set(api.GAME_KEY, original);
    const deniedRead = new api.LocalStateRepository(() => ({ ...port, getItem: () => { throw new Error('denied'); } })).readGame().status;
    const deniedGetter = new api.LocalStateRepository(() => { throw new Error('getter denied'); }).writeGame(valid as never).status;
    const quotaRepo = new api.LocalStateRepository(() => ({ ...port,
      setItem: () => { throw new DOMException('full', 'QuotaExceededError'); } }));
    const quota = quotaRepo.writeGame(valid as never).status;
    const priorIntact = content.get(api.GAME_KEY) === original;
    let badSettings = false;
    try { api.validateSettings({ schemaVersion: 1, nextMatch: valid.match, reducedMotion: 'yes' } as never); }
    catch { badSettings = true; }
    return { roundtrip, rejected, oversized, deniedRead, deniedGetter, quota, priorIntact, badSettings };
  });
  expect(result.roundtrip).toBe(true);
  expect(result.rejected).toEqual(Array(11).fill('invalid'));
  expect(result.oversized).toBe('invalid');
  expect(result.deniedRead).toBe('unavailable');
  expect(result.deniedGetter).toBe('unavailable');
  expect(result.quota).toBe('quota');
  expect(result.priorIntact).toBe(true);
  expect(result.badSettings).toBe(true);
});

test('quota failure leaves previous slot while live play continues', async ({ page }) => {
  await ready(page);
  const key = await page.evaluate(() => window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY);
  const previous = await page.evaluate(k => localStorage.getItem(k), key);
  await page.evaluate(k => {
    const native = Storage.prototype.setItem;
    Storage.prototype.setItem = function (name, value) {
      if (name === k) throw new DOMException('full', 'QuotaExceededError');
      native.call(this, name, value);
    };
  }, key);
  await clickCell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  expect(await page.evaluate(k => localStorage.getItem(k), key)).toBe(previous);
  await expect(page.locator('#save-status')).toContainText('いっぱい');
  await openMenu(page);
  await page.getByRole('button', { name: '今すぐ保存' }).click();
  expect((await state(page)).view?.ply).toBe(1);
});
