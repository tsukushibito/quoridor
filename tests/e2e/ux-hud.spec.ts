import { expect, test, type Page } from '@playwright/test';

const errors = new WeakMap<Page, string[]>();
test.beforeEach(async ({ page }) => {
  const found: string[] = []; errors.set(page, found);
  page.on('pageerror', error => found.push(error.message));
  page.on('console', message => { if (message.type() === 'error') found.push(message.text()); });
});
test.afterEach(async ({ page }) => { expect(errors.get(page)).toEqual([]); });
async function ready(page: Page): Promise<void> {
  await page.goto('./?forceWebGL=1');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase)).toBe('humanTurn');
}
async function state(page: Page) { return page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state()); }
async function cell(page: Page, id: number): Promise<void> {
  const point = await page.evaluate(cellId => window.__QUORIDOR_APP_TEST_API__!.projectCell(cellId), id);
  await page.mouse.click(point.x, point.y);
}
async function wall(page: Page, id: number): Promise<void> {
  const point = await page.evaluate(anchor => window.__QUORIDOR_APP_TEST_API__!.projectWall(anchor), id);
  await page.mouse.click(point.x, point.y);
}
async function start(page: Page, mode: 'pvp' | 'ai', side: '0' | '1' = '0', budget = '48'): Promise<void> {
  const previousEpoch = (await state(page)).gameEpoch;
  await page.locator('#new-game').click();
  await page.locator('#match-mode').selectOption(mode);
  if (mode === 'ai') {
    await page.locator('#human-side').selectOption(side);
    await page.locator('#ai-budget').selectOption(budget);
  }
  await page.locator('#dialog-start').click();
  await expect.poll(() => state(page).then(value => value.gameEpoch)).toBeGreaterThan(previousEpoch);
  await expect.poll(() => state(page).then(value => value.matchMode)).toBe(mode);
}

test('full-viewport canvas, floating HUD islands and board fit four viewports', async ({ page }) => {
  let initialized = false;
  for (const [width, height, minimumCellWidth] of [[1280, 720, 554.3], [1440, 900, 728.5],
    [1920, 1080, 902.6], [390, 844, 259.3]]) {
    const previousCanvasWidth = initialized ? await page.locator('#board canvas').evaluate(element => (element as HTMLCanvasElement).width) : null;
    await page.setViewportSize({ width, height });
    if (!initialized) { await ready(page); initialized = true; }
    else await expect.poll(() => page.locator('#board canvas').evaluate(element => (element as HTMLCanvasElement).width))
      .not.toBe(previousCanvasWidth);
    const bounds = await page.evaluate(() => {
      const api = window.__QUORIDOR_APP_TEST_API__!;
      const points = [0, 8, 72, 80].map(id => api.projectCell(id));
      const board = api.projectBoardBounds();
      const canvas = document.querySelector('#board canvas')!.getBoundingClientRect();
      const islands = ['.status-island', '.top-actions', '.action-hud'].map(selector =>
        document.querySelector(selector)!.getBoundingClientRect());
      const controls = ['#restart-game', '#new-game', '#open-menu', '#mode-move', '#mode-wall', '#orientation', '#undo']
        .map(selector => document.querySelector(selector)!.getBoundingClientRect());
      return { cellWidth: Math.max(...points.map(point => point.x)) - Math.min(...points.map(point => point.x)),
        board, canvas: { left: canvas.left, top: canvas.top, right: canvas.right, bottom: canvas.bottom },
        islands: islands.map(rect => ({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom,
          width: rect.width })),
        controls: controls.map(rect => ({ left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom })),
        gapHit: document.elementFromPoint(innerWidth >= 660 ? innerWidth / 2 : innerWidth - 4, 20)?.tagName,
        topbarPosition: getComputedStyle(document.querySelector('.topbar')!).position,
        toolbarPosition: getComputedStyle(document.querySelector('.action-hud')!).position,
        scrollHeight: document.documentElement.scrollHeight, scrollWidth: document.documentElement.scrollWidth };
    });
    expect(bounds.cellWidth).toBeGreaterThan(minimumCellWidth);
    expect(bounds.canvas.left).toBeCloseTo(0, 0);
    expect(bounds.canvas.top).toBeCloseTo(0, 0);
    expect(bounds.canvas.right).toBeCloseTo(width, 0);
    expect(bounds.canvas.bottom).toBeCloseTo(height, 0);
    expect(bounds.topbarPosition).toBe('fixed');
    expect(bounds.toolbarPosition).toBe('fixed');
    expect(bounds.gapHit).toBe('CANVAS');
    expect(bounds.board.left).toBeGreaterThanOrEqual(bounds.canvas.left - 1);
    expect(bounds.board.right).toBeLessThanOrEqual(bounds.canvas.right + 1);
    expect(bounds.board.top).toBeGreaterThanOrEqual(bounds.canvas.top - 1);
    expect(bounds.board.bottom).toBeLessThanOrEqual(bounds.canvas.bottom + 1);
    for (const island of bounds.islands) {
      expect(island.left).toBeGreaterThanOrEqual(bounds.canvas.left);
      expect(island.top).toBeGreaterThanOrEqual(bounds.canvas.top);
      expect(island.right).toBeLessThanOrEqual(bounds.canvas.right);
      expect(island.bottom).toBeLessThanOrEqual(bounds.canvas.bottom);
      expect(island.width).toBeLessThan(width * 0.85);
      expect(island.right <= bounds.board.left || island.left >= bounds.board.right ||
        island.bottom <= bounds.board.top || island.top >= bounds.board.bottom).toBe(true);
    }
    for (const rect of bounds.controls) {
      expect(rect.left).toBeGreaterThanOrEqual(0);
      expect(rect.top).toBeGreaterThanOrEqual(0);
      expect(rect.right).toBeLessThanOrEqual(width);
      expect(rect.bottom).toBeLessThanOrEqual(height);
    }
    expect(bounds.scrollHeight).toBeLessThanOrEqual(height + 1);
    expect(bounds.scrollWidth).toBeLessThanOrEqual(width + 1);
    await page.screenshot({ path: `artifacts/ux-${process.env.E2E_MODE || 'dev'}-${width}x${height}.png` });
    console.log(`HUD ${width}x${height}: cell corners ${bounds.cellWidth.toFixed(1)}px, full board ${
      (bounds.board.right - bounds.board.left).toFixed(1)}x${(bounds.board.bottom - bounds.board.top).toFixed(1)}px`);
  }
});

test('direct pointer, keyboard, dialog isolation, camera and restart keep one session canvas', async ({ page }) => {
  await ready(page);
  const initialKey = (await state(page)).view!.positionKey;
  await page.locator('#new-game').click();
  await page.locator('#match-mode').selectOption('ai');
  await page.keyboard.press('Escape');
  await expect(page.locator('#new-game')).toBeFocused();
  expect((await state(page)).view!.positionKey).toBe(initialKey);
  await page.keyboard.press('Enter');
  await expect(page.locator('#match-dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  expect((await state(page)).view?.ply).toBe(0);
  await cell(page, 0);
  expect((await state(page)).view?.ply).toBe(0);
  await cell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  await page.locator('#open-menu').click();
  const beforeMenu = (await state(page)).view!.positionKey;
  await page.locator('#flip').click();
  await page.locator('#reset-camera').click();
  await page.locator('#close-menu').click();
  expect((await state(page)).view!.positionKey).toBe(beforeMenu);
  await page.locator('#mode-wall').click();
  const p = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.move(p.x, p.y);
  await expect(page.locator('#preview-text')).toContainText('置けます');
  await wall(page, 27);
  expect((await state(page)).view?.horizontalWalls).toContain(27);
  await wall(page, 27);
  expect((await state(page)).view?.ply).toBe(2);
  await page.locator('#undo').click();
  expect((await state(page)).view?.ply).toBe(1);
  await page.locator('#mode-move').click();
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowUp');
  await page.keyboard.press('Escape');
  expect((await state(page)).selectedId).toBeNull();
  const canvas = await page.locator('#board canvas').evaluate(element => { (window as Window & { __canvas?: Element }).__canvas = element; return true; });
  expect(canvas).toBe(true);
  await page.locator('#restart-game').click();
  expect((await state(page)).view?.ply).toBe(0);
  expect(await page.locator('#board canvas').evaluate(element => element === (window as Window & { __canvas?: Element }).__canvas)).toBe(true);
});

test('flip, reset and resize keep direct screen picking mapped to Rust cells', async ({ page }) => {
  await ready(page);
  await page.locator('#open-menu').click();
  await page.locator('#flip').click();
  await page.locator('#close-menu').click();
  await cell(page, 13);
  expect((await state(page)).view?.pawns[0]).toBe(13);
  await page.locator('#undo').click();
  await page.locator('#open-menu').click();
  await page.locator('#reset-camera').click();
  await page.locator('#close-menu').click();
  await cell(page, 13);
  expect((await state(page)).view?.pawns[0]).toBe(13);
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  const previousCanvasWidth = await page.locator('#board canvas').evaluate(element => (element as HTMLCanvasElement).width);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.locator('#board canvas').evaluate(element => (element as HTMLCanvasElement).width))
    .not.toBe(previousCanvasWidth);
  await cell(page, 67);
  expect((await state(page)).view?.pawns[1]).toBe(67);
});

test('live PvP to either AI side and back uses one start action and no navigation', async ({ page }) => {
  await ready(page);
  let navigations = 0;
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });
  await cell(page, 13);
  await cell(page, 67);
  const oldEpoch = (await state(page)).gameEpoch;
  await start(page, 'ai', '1');
  await expect.poll(() => state(page).then(value => value.phase), { timeout: 20_000 }).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(1);
  expect((await state(page)).humanSide).toBe(1);
  expect((await state(page)).gameEpoch).toBeGreaterThan(oldEpoch);
  await page.locator('#restart-game').click();
  await expect.poll(() => state(page).then(value => value.phase), { timeout: 20_000 }).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(1);
  await start(page, 'ai', '0');
  expect((await state(page)).view?.ply).toBe(0);
  await cell(page, 13);
  await expect.poll(() => state(page).then(value => value.phase), { timeout: 20_000 }).toBe('humanTurn');
  await page.locator('#restart-game').click();
  expect((await state(page)).view?.ply).toBe(0);
  await start(page, 'pvp');
  expect((await state(page)).view?.ply).toBe(0);
  await cell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  expect(navigations).toBe(0);
});

test('saved startup discard and corrupt save exit start a playable match without another reload', async ({ page }) => {
  await ready(page);
  await cell(page, 13);
  let navigations = 0;
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });
  await page.reload();
  expect(navigations).toBe(1);
  await expect(page.locator('#startup-dialog')).toBeVisible();
  await page.locator('#startup-new-game').click();
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#human-side').selectOption('1');
  await page.locator('#dialog-start').click();
  await expect.poll(() => state(page).then(value => value.phase), { timeout: 20_000 }).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(1);
  expect(navigations).toBe(1);
  const key = await page.evaluate(() => window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY);
  await page.evaluate(gameKey => localStorage.setItem(gameKey, '42'), key);
  await page.reload();
  expect(navigations).toBe(2);
  await expect(page.locator('#startup-dialog')).toBeVisible();
  await page.locator('#startup-clear-save').click();
  expect(await page.evaluate(gameKey => localStorage.getItem(gameKey), key)).toBeNull();
  await page.locator('#dialog-cancel').click();
  await expect(page.locator('#startup-dialog')).toBeVisible();
  await expect(page.locator('#startup-message')).toContainText('設定を選んで開始');
  await expect(page.locator('#turn-heading')).not.toContainText('読み込めません');
  await page.locator('#startup-new-game').click();
  await page.locator('#match-mode').selectOption('pvp');
  await page.locator('#dialog-start').click();
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  await cell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  expect(navigations).toBe(2);
});

test('clearing a live save keeps play; failed deletion keeps the prior slot and reports failure', async ({ page }) => {
  await ready(page);
  const key = await page.evaluate(() => window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY);
  await page.locator('#open-menu').click();
  await page.locator('#clear-save').click();
  expect(await page.evaluate(gameKey => localStorage.getItem(gameKey), key)).toBeNull();
  await expect(page.locator('#save-status')).toContainText('今の対局は続けられます');
  await page.locator('#close-menu').click();
  await cell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  const previous = await page.evaluate(gameKey => localStorage.getItem(gameKey), key);
  expect(previous).not.toBeNull();
  await page.evaluate(gameKey => {
    const native = Storage.prototype.removeItem;
    Storage.prototype.removeItem = function (name) {
      if (name === gameKey) throw new Error('storage denied');
      native.call(this, name);
    };
  }, key);
  await page.locator('#open-menu').click();
  await page.locator('#clear-save').click();
  await expect(page.locator('#save-status')).toContainText('使えません');
  expect(await page.evaluate(gameKey => localStorage.getItem(gameKey), key)).toBe(previous);
  await page.locator('#close-menu').click();
  await cell(page, 67);
  expect((await state(page)).view?.ply).toBe(2);
});

test('restart after an ordinary completed PvP game starts the same mode without reload', async ({ page }) => {
  await ready(page);
  let navigations = 0;
  page.on('framenavigated', frame => { if (frame === page.mainFrame()) navigations++; });
  await page.locator('#open-menu').click();
  await page.locator('.settings summary').click();
  await page.locator('#no-animation').check();
  await page.locator('#close-menu').click();
  for (let move = 0; move < 8; move++) {
    await cell(page, 13 + move * 9);
    if (move < 7) await cell(page, move % 2 === 0 ? 75 : 76);
  }
  expect((await state(page)).phase).toBe('finished');
  expect((await state(page)).view?.winner).toBe(0);
  await page.locator('#restart-game').click();
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  expect((await state(page)).matchMode).toBe('pvp');
  expect((await state(page)).view?.ply).toBe(0);
  expect(navigations).toBe(0);
});

test('real touch tap previews and explicit confirm commits once', async ({ browser }) => {
  const context = await browser.newContext({ hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  const found: string[] = [];
  page.on('pageerror', error => found.push(error.message));
  page.on('console', message => { if (message.type() === 'error') found.push(message.text()); });
  try {
    await ready(page);
    const point = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectCell(13));
    await page.touchscreen.tap(point.x, point.y);
    expect((await state(page)).view?.ply).toBe(0);
    expect((await state(page)).selectedId).toBe(13);
    await expect(page.locator('#confirm-selection')).toBeVisible();
    await page.locator('#confirm-selection').click();
    expect((await state(page)).view?.ply).toBe(1);
    await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
    await page.locator('#mode-wall').click();
    await page.locator('#orientation').click();
    expect((await state(page)).orientation).toBe('vertical');
    const wallPoint = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
    await page.touchscreen.tap(wallPoint.x, wallPoint.y);
    expect((await state(page)).view?.ply).toBe(1);
    await page.locator('#confirm-selection').click();
    expect((await state(page)).view?.verticalWalls).toContain(27);
    expect(found).toEqual([]);
  } finally { await context.close(); }
});
