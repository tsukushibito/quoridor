import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const browserErrors = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  browserErrors.set(page, errors);
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
});
test.afterEach(async ({ page }) => { expect(browserErrors.get(page)).toEqual([]); });

async function ready(page: Page): Promise<void> {
  await page.goto('./?forceWebGL=1');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase)).toBe('humanTurn');
}
async function state(page: Page) { return page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state()); }
async function point(page: Page, kind: 'cell' | 'wall', id: number) {
  await page.locator('#board canvas').evaluate(element => element.scrollIntoView({ block: 'center' }));
  return page.evaluate(({ kind, id }) => kind === 'cell'
    ? window.__QUORIDOR_APP_TEST_API__!.projectCell(id)
    : window.__QUORIDOR_APP_TEST_API__!.projectWall(id), { kind, id });
}
async function selectAndConfirm(page: Page, kind: 'cell' | 'wall', id: number): Promise<void> {
  const location = await point(page, kind, id);
  await page.mouse.click(location.x, location.y);
}
async function openMenu(page: Page): Promise<void> {
  await page.locator('#open-menu').click();
  if (!await page.locator('#no-animation').isVisible()) await page.locator('.settings summary').click();
}
async function closeMenu(page: Page): Promise<void> { await page.locator('#close-menu').click(); }
async function startPvp(page: Page): Promise<void> {
  await page.locator('#new-game').click();
  await page.locator('#match-mode').selectOption('pvp');
  await page.locator('#dialog-start').click();
}
async function settle(page: Page): Promise<void> {
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().phase)).toMatch(/humanTurn|finished/);
}

test('real pointer game reaches winner, then undo/new and camera remain usable', async ({ page }) => {
  await ready(page);
  expect((await state(page)).view?.legalMask.filter(x => x === 1).length).toBe(131);
  for (let move = 0; move < 8; move++) {
    await selectAndConfirm(page, 'cell', 13 + move * 9);
    await settle(page);
    if (move < 7) expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().hints))
      .toBe((await state(page)).view?.legalMask.slice(0, 81).filter(x => x === 1).length);
    if (move < 7) { await selectAndConfirm(page, 'cell', move % 2 === 0 ? 75 : 76); await settle(page); }
  }
  const terminal = await state(page);
  expect(terminal.phase).toBe('finished');
  expect(terminal.view?.winner).toBe(0);
  expect(terminal.view?.ply).toBe(15);
  expect(terminal.view?.legalMask.every(x => x === 0)).toBe(true);
  await selectAndConfirm(page, 'cell', 75);
  expect((await state(page)).view?.ply).toBe(15);
  await page.getByRole('button', { name: '壁を置く' }).click();
  await selectAndConfirm(page, 'wall', 27);
  expect((await state(page)).view?.ply).toBe(15);
  const before = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  await openMenu(page);
  await page.getByRole('button', { name: '反対側から見る' }).click();
  const flipped = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  expect(flipped[2]).toBeCloseTo(-before[2], 4);
  expect((await state(page)).view?.positionKey).toBe(terminal.view?.positionKey);
  await page.getByRole('button', { name: '視点を戻す' }).click();
  await closeMenu(page);
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).view?.ply).toBe(14);
  expect((await state(page)).phase).toBe('humanTurn');
  await startPvp(page);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().view?.ply)).toBe(0);
  expect((await state(page)).view?.pawns).toEqual([4, 76]);
});

test('wall orientation, illegal preview, keyboard, and static layer', async ({ page }) => {
  await ready(page);
  const initial = await state(page);
  const hints = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().hints);
  expect(hints).toBe(initial.view?.legalMask.slice(0, 81).filter(x => x === 1).length);
  await page.getByRole('button', { name: '壁を置く' }).click();
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().nonWallStatic)).toBe(0);
  const firstWall = await point(page, 'wall', 27);
  await page.mouse.move(firstWall.x, firstWall.y);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().nonWallStatic)).toBe(0);
  await page.mouse.click(firstWall.x, firstWall.y);
  await settle(page);
  expect((await state(page)).view?.horizontalWalls).toContain(27);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(1);
  const illegal = await point(page, 'wall', 27);
  await page.mouse.click(illegal.x, illegal.y);
  await expect(page.locator('#preview-text')).toContainText('置けません');
  expect((await state(page)).view?.ply).toBe(1);
  await page.locator('#board canvas').focus();
  await page.keyboard.press('r');
  expect((await state(page)).orientation).toBe('vertical');
  await page.getByRole('button', { name: /壁の向き/ }).click();
  expect((await state(page)).orientation).toBe('horizontal');
  await page.getByRole('button', { name: /壁の向き/ }).click();
  expect((await state(page)).orientation).toBe('vertical');
  await page.keyboard.press('ArrowUp');
  expect((await state(page)).selectedId).toBeNull();
  expect((await state(page)).view?.ply).toBe(1);
  const view = (await state(page)).view!;
  const vertical = view.legalMask.findIndex((value, id) => id >= 145 + 18 && id <= 145 + 45 && value === 1);
  expect(vertical).toBeGreaterThan(145);
  await selectAndConfirm(page, 'wall', vertical - 145);
  await settle(page);
  expect((await state(page)).view?.verticalWalls).toContain(vertical - 145);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(2);
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).view?.verticalWalls).not.toContain(vertical - 145);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(1);
  await page.getByRole('button', { name: '駒を動かす' }).click();
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowUp');
  expect((await state(page)).selectedId).toBe(67);
  await page.keyboard.press('Escape');
  expect((await state(page)).selectedId).toBeNull();
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('Enter');
  await settle(page);
  expect((await state(page)).view?.pawns[1]).toBe(67);
});

test('drag and UI isolation, interrupted animations, reduced motion, repeated new and disposal', async ({ page }) => {
  await page.clock.install();
  await ready(page);
  const canvas = page.locator('#board canvas');
  const originalKey = (await state(page)).view?.positionKey;
  const p = await point(page, 'cell', 13);
  await page.mouse.move(p.x, p.y); await page.mouse.down();
  await canvas.evaluate(element => element.dispatchEvent(new PointerEvent('pointercancel', { pointerId: 1, bubbles: true })));
  await page.mouse.up();
  expect((await state(page)).selectedId).toBeNull();
  expect((await state(page)).view?.ply).toBe(0);
  await page.mouse.move(p.x, p.y); await page.mouse.down(); await page.mouse.move(p.x + 60, p.y + 25, { steps: 8 }); await page.mouse.up();
  expect((await state(page)).view?.positionKey).toBe(originalKey);
  expect((await state(page)).selectedId).toBeNull();
  const cameraBefore = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  await page.mouse.move(p.x, p.y); await page.mouse.down({ button: 'right' });
  await page.mouse.move(p.x + 80, p.y + 35, { steps: 8 }); await page.mouse.up({ button: 'right' });
  const cameraAfter = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  expect(cameraAfter[0]).not.toBeCloseTo(cameraBefore[0], 3);
  expect((await state(page)).view?.positionKey).toBe(originalKey);
  const distanceBefore = Math.hypot(...cameraAfter);
  await page.mouse.wheel(0, -350);
  await page.waitForTimeout(100);
  expect(Math.hypot(...await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera()))).not.toBeCloseTo(distanceBefore, 2);
  await openMenu(page);
  await page.getByRole('button', { name: '視点を戻す' }).click();
  await closeMenu(page);
  const resetPoint = await point(page, 'cell', 13);
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowDown');
  expect((await state(page)).selectedId).toBe(13);
  await page.getByRole('button', { name: '壁を置く' }).click();
  expect((await state(page)).selectedId).toBeNull();
  expect((await state(page)).view?.ply).toBe(0);
  await page.mouse.click(5, 5);
  expect((await state(page)).view?.ply).toBe(0);
  expect((await state(page)).selectedId).toBeNull();
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 10_000));
  await selectAndConfirm(page, 'wall', 27);
  expect((await state(page)).phase).toBe('animating');
  expect((await state(page)).view?.ply).toBe(1);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(0);
  await selectAndConfirm(page, 'wall', 40);
  expect((await state(page)).view?.ply).toBe(1);
  await page.getByRole('button', { name: '1手戻す' }).click();
  await page.clock.resume();
  await page.waitForTimeout(260);
  expect((await state(page)).view?.ply).toBe(0);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().walls)).toBe(0);
  await page.getByRole('button', { name: '駒を動かす' }).click();
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 10_000));
  await selectAndConfirm(page, 'cell', 13);
  expect((await state(page)).phase).toBe('animating');
  expect((await state(page)).view?.ply).toBe(1);
  await page.locator('#restart-game').click();
  await page.clock.resume();
  await page.waitForTimeout(260);
  expect((await state(page)).view?.ply).toBe(0);
  await openMenu(page);
  await page.locator('#no-animation').check();
  await closeMenu(page);
  await page.getByRole('button', { name: '壁を置く' }).click();
  await selectAndConfirm(page, 'wall', 27);
  expect((await state(page)).phase).toBe('humanTurn');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(1);
  await page.evaluate(() => { (window as Window & { __canvasReference?: HTMLCanvasElement }).__canvasReference = document.querySelector('#board canvas')!; });
  for (let i = 0; i < 3; i++) {
    await page.locator('#restart-game').click();
    await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().phase)).toBe('humanTurn');
  }
  expect(await page.evaluate(() => document.querySelector('#board canvas') === (window as Window & { __canvasReference?: HTMLCanvasElement }).__canvasReference)).toBe(true);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().canvasCount)).toBe(1);
  await page.getByRole('button', { name: '駒を動かす' }).click();
  const again = await point(page, 'cell', 13);
  for (let i = 0; i < 4; i++) await page.mouse.click(again.x, again.y);
  expect((await state(page)).view?.ply).toBe(1);
  await page.locator('#restart-game').click();
  await openMenu(page);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().phase)).toBe('humanTurn');
  await page.locator('#no-animation').uncheck();
  await closeMenu(page);
  await page.getByRole('button', { name: '壁を置く' }).click();
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 10_000));
  await selectAndConfirm(page, 'wall', 27);
  expect((await state(page)).phase).toBe('animating');
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.disposeForTest());
  await page.clock.resume();
  await page.waitForTimeout(260);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().phase)).toBe('disposed');
  expect(await canvas.count()).toBe(0);
});

test('narrow viewport keeps controls accessible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  for (const name of ['駒を動かす', '壁を置く', '1手戻す', '新しい対局', 'やり直す'])
    await expect(page.getByRole('button', { name })).toBeVisible();
  await openMenu(page);
  for (const name of ['反対側から見る', '視点を戻す']) await expect(page.getByRole('button', { name })).toBeVisible();
  await closeMenu(page);
  await selectAndConfirm(page, 'cell', 13);
  await settle(page);
  expect((await state(page)).view?.pawns[0]).toBe(13);
  await page.getByRole('button', { name: '壁を置く' }).click();
  await selectAndConfirm(page, 'wall', 27);
  await settle(page);
  expect((await state(page)).view?.horizontalWalls).toContain(27);
  mkdirSync('artifacts', { recursive: true });
  await page.screenshot({ path: `artifacts/phase2-${process.env.E2E_MODE || 'dev'}-narrow.png`, fullPage: true });
});
