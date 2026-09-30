import { startDefaultMatch, restartMatch } from './start-match';
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const errors = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  const found: string[] = []; errors.set(page, found);
  page.on('pageerror', error => found.push(error.message));
  page.on('console', message => { if (message.type() === 'error') found.push(message.text()); });
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase)).toBe('humanTurn');
});
test.afterEach(async ({ page }) => { expect(errors.get(page)).toEqual([]); });
async function state(page: Page) { return page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state()); }
async function clickCell(page: Page, cell: number): Promise<void> {
  await page.locator('#board canvas').evaluate(el => el.scrollIntoView({ block: 'center' }));
  const point = await page.evaluate(id => window.__QUORIDOR_APP_TEST_API__!.projectCell(id), cell);
  await page.mouse.click(point.x, point.y);
}
async function configure(page: Page, side: 0 | 1, budget = '48'): Promise<void> {
  await page.locator('#new-game').click();
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#human-side').selectOption(String(side));
  await page.locator('#ai-budget').selectOption(budget);
  await page.locator('#dialog-start').click();
}
async function openMenu(page: Page): Promise<void> {
  await page.locator('#open-menu').click();
  if (!await page.locator('#no-animation').isVisible()) await page.locator('.settings summary').click();
}
async function closeMenu(page: Page): Promise<void> { await page.locator('#close-menu').click(); }
async function waitHuman(page: Page): Promise<void> {
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().phase), { timeout: 20000 }).toBe('humanTurn');
}

test('human first, AI answer, undo decision, and replay restore cancellation', async ({ page }) => {
  await configure(page, 0);
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  await clickCell(page, 13);
  await expect.poll(() => state(page).then(s => s.view?.ply), { timeout: 20000 }).toBe(2);
  await waitHuman(page);
  const answered = await state(page);
  expect(answered.view?.pawns[0]).toBe(13);
  expect(answered.matchMode).toBe('ai');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.aiDiagnostics().highWaterBytes)).toBeGreaterThan(0);
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).view?.ply).toBe(0);
  expect((await state(page)).phase).toBe('humanTurn');
  const save = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay());
  await configure(page, 0, '4096');
  await clickCell(page, 13);
  expect((await state(page)).phase).toBe('aiThinking');
  await page.evaluate(async replay => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(replay, 'pvp', 0), save);
  expect((await state(page)).view?.ply).toBe(0);
  expect((await state(page)).matchMode).toBe('pvp');
  const before = await state(page);
  await expect(page.evaluate(async () => window.__QUORIDOR_APP_TEST_API__!.restoreReplay({ ...window.__QUORIDOR_APP_TEST_API__!.exportReplay(), actions: [999] }, 'pvp', 0)))
    .rejects.toThrow();
  expect((await state(page)).view?.positionKey).toBe(before.view?.positionKey);
});

test('AI first opening, responsive controls, and full UI game', async ({ page }) => {
  test.setTimeout(120_000);
  await configure(page, 1, '192');
  const camera = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  await openMenu(page);
  await page.getByRole('button', { name: '反対側から見る' }).click();
  expect((await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera()))[2]).toBeCloseTo(-camera[2], 3);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  await waitHuman(page);
  expect((await state(page)).view?.ply).toBe(1);
  expect(await page.getByRole('button', { name: '1手戻す' }).isDisabled()).toBe(true);
  // The second player deliberately moves side to side; the AI must still finish
  // an ordinary opening without a position injection or direct action call.
  for (let i = 0; i < 100; i++) {
    const current = await state(page);
    if (current.phase === 'finished') break;
    expect(current.phase).toBe('humanTurn');
    const pawn = current.view!.pawns[1]!;
    const legal = current.view!.legalMask;
    const targets = [75, 76, pawn - 1, pawn + 1, pawn - 9, pawn + 9];
    const target = targets.find(id => id >= 0 && id <= 80 && id !== pawn && legal[id] === 1);
    expect(target).toBeDefined();
    await clickCell(page, target!);
    await expect.poll(() => state(page).then(s => s.phase), { timeout: 20000 }).toMatch(/humanTurn|finished/);
  }
  const final = await state(page);
  expect(final.phase).toBe('finished');
  expect(final.view?.winner).toBe(0);
  expect(final.view?.legalMask.every(bit => bit === 0)).toBe(true);
  const key = final.view?.positionKey;
  await clickCell(page, 75);
  expect((await state(page)).view?.positionKey).toBe(key);
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).phase).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(final.view!.ply - 2);
  await restartMatch(page);
  await waitHuman(page);
  expect((await state(page)).view?.ply).toBe(1);
  mkdirSync('artifacts', { recursive: true });
  await page.screenshot({ path: `artifacts/phase3-${process.env.E2E_MODE || 'dev'}-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.locator('#new-game').click();
  await expect(page.locator('#match-mode')).toBeVisible();
  await expect(page.locator('#human-side')).toBeVisible();
  await expect(page.locator('#ai-budget')).toBeVisible();
  await page.screenshot({ path: `artifacts/phase3-${process.env.E2E_MODE || 'dev'}-narrow.png`, fullPage: true });
});

test('human first and AI second complete a standard game through pointer input', async ({ page }) => {
  test.setTimeout(120_000);
  await configure(page, 0, '48');
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  for (let i = 0; i < 100; i++) {
    const current = await state(page);
    if (current.phase === 'finished') break;
    expect(current.phase).toBe('humanTurn');
    const pawn = current.view!.pawns[0]!;
    const legal = current.view!.legalMask;
    const target = [3, 4, pawn + 1, pawn - 1, pawn + 9, pawn - 9]
      .find(id => id >= 0 && id <= 80 && id !== pawn && legal[id] === 1);
    expect(target).toBeDefined();
    await clickCell(page, target!);
    await expect.poll(() => state(page).then(s => s.phase), { timeout: 20000 }).toMatch(/humanTurn|finished/);
  }
  const final = await state(page);
  expect(final.phase).toBe('finished');
  expect(final.view?.winner).toBe(1);
  expect(final.view?.legalMask.every(bit => bit === 0)).toBe(true);
});

test('cancel, retry, undo, and PvP fallback during real AI thought preserve the board', async ({ page }) => {
  await configure(page, 0, '4096');
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  await clickCell(page, 13);
  const first = await state(page);
  expect(first.view?.ply).toBe(1);
  expect(first.phase).toBe('aiThinking');
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).view?.ply).toBe(0);
  await page.waitForTimeout(350);
  expect((await state(page)).view?.ply).toBe(0);
  await clickCell(page, 13);
  expect((await state(page)).phase).toBe('aiThinking');
  // Deliver the user's cancel click promptly, before a fast local Worker finishes.
  await page.locator('#cancel-ai').evaluate((button: HTMLButtonElement) => button.click());
  expect((await state(page)).phase).toBe('recoverableError');
  const key = (await state(page)).view?.positionKey;
  await page.waitForTimeout(350);
  expect((await state(page)).view?.positionKey).toBe(key);
  await page.getByRole('button', { name: 'AIを再試行' }).click();
  expect((await state(page)).phase).toBe('aiThinking');
  await page.locator('#cancel-ai').evaluate((button: HTMLButtonElement) => button.click());
  await page.getByRole('button', { name: '2人対戦に切り替える' }).click();
  expect((await state(page)).matchMode).toBe('pvp');
  expect((await state(page)).phase).toBe('humanTurn');
  await configure(page, 0, '4096');
  await clickCell(page, 13);
  expect((await state(page)).phase).toBe('aiThinking');
  await restartMatch(page);
  await page.waitForTimeout(350);
  expect((await state(page)).view?.ply).toBe(0);
  await clickCell(page, 13);
  expect((await state(page)).phase).toBe('aiThinking');
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.disposeForTest());
  await page.waitForTimeout(350);
  expect((await state(page)).phase).toBe('disposed');
  expect(await page.locator('#board canvas').count()).toBe(0);
});

test('undo and new game cancel the AI result animation without stale completion', async ({ page }) => {
  test.setTimeout(60_000);
  await page.clock.install();
  await configure(page, 0, '4096');
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  const opening = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay());
  for (const operation of ['undo', 'new', 'load'] as const) {
    await clickCell(page, 13);
    expect((await state(page)).phase).toBe('aiThinking');
    await openMenu(page);
    await page.locator('#no-animation').uncheck();
    await closeMenu(page);
    await page.clock.pauseAt(await page.evaluate(() => Date.now() + 10_000));
    await expect.poll(() => state(page).then(s => ({ phase: s.phase, ply: s.view?.ply })), { timeout: 20000 })
      .toEqual({ phase: 'animating', ply: 2 });
    expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().animating)).toBe(true);
    if (operation === 'undo') await page.getByRole('button', { name: '1手戻す' }).click();
    else if (operation === 'new') await restartMatch(page);
    else await page.evaluate(async replay => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(replay, 'pvp', 0), opening);
    await page.clock.resume();
    await page.waitForTimeout(260);
    expect((await state(page)).view?.ply).toBe(0);
    expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().animating)).toBe(false);
    if (operation === 'load') break;
    await openMenu(page);
    await page.locator('#no-animation').check();
    await closeMenu(page);
  }
});
