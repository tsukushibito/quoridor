import { expect, test, type Page } from '@playwright/test';
import { startDefaultMatch } from './start-match';

const winning = [13, 67, 22, 58, 31, 49, 40, 48, 49, 47, 58, 46, 67, 45, 76];
const secondWinning = [3, 67, 2, 58, 3, 49, 2, 40, 3, 31, 2, 22, 3, 13, 2, 4];
const state = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state());
const audio = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.audio());
const review = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.review());
const meshes = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.presentation());
async function ready(page: Page) {
  await page.goto('./?forceWebGL=1');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase)).toBe('ready');
  await startDefaultMatch(page);
  await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  await expect.poll(() => audio(page).then(s => s.loaded.length)).toBe(7);
}
async function replay(page: Page, actions = winning, humanSide: 0 | 1 = 0) {
  return page.evaluate(async ({ actions, humanSide }) => {
    const game = await window.__QUORIDOR_RULES_TEST_API__!.createGame({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: humanSide });
    try { actions.forEach(id => game.applyAction(id)); return game.exportReplay(); } finally { game.dispose(); }
  }, { actions, humanSide });
}
async function restore(page: Page, actions = winning, mode: 'pvp' | 'ai' = 'pvp', humanSide: 0 | 1 = 0) {
  const save = await replay(page, actions, humanSide);
  await page.evaluate(({ save, mode, humanSide }) => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(save, mode, humanSide), { save, mode, humanSide });
  return save;
}
async function clickCell(page: Page, cell: number) {
  const p = await page.evaluate(cell => window.__QUORIDOR_APP_TEST_API__!.projectCell(cell), cell);
  await page.mouse.click(p.x, p.y);
}

test('central result, independent bidirectional review, focus, title round trip and restored result', async ({ page }) => {
  await ready(page); await restore(page);
  await expect(page.locator('#result-dialog')).toBeVisible();
  await expect(page.locator('#result-heading')).toHaveText('先手・丸い駒の勝ち！');
  await expect(page.locator('#result-total')).toHaveText('総手数 15手');
  await expect(page.locator('#result-review')).toBeFocused();
  for (const id of ['mode-move', 'mode-wall', 'orientation', 'confirm-selection', 'undo']) await expect(page.locator('#' + id)).toBeHidden();
  const original = await state(page);
  const saved = await page.evaluate(() => localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY));
  const counts = (await audio(page)).counts;
  await page.keyboard.press('Shift+Tab'); await expect(page.locator('#result-title')).toBeFocused();
  await page.keyboard.press('Tab'); await expect(page.locator('#result-review')).toBeFocused();
  await page.locator('#result-review').click();
  await expect(page.locator('#review-counter')).toHaveText('振り返り 15 / 15手');
  await expect.poll(() => audio(page).then(s => s.activeBgm)).toBe(1);
  await page.locator('#review-first').click();
  expect((await review(page)).view?.pawns).toEqual([4, 76]);
  await expect(page.locator('#review-prev')).toBeDisabled();
  await page.locator('#review-next').click(); expect((await review(page)).ply).toBe(1);
  await page.locator('#review-last').click(); expect((await review(page)).view?.positionKey).toBe(original.view?.positionKey);
  await page.locator('#review-prev').click(); expect((await review(page)).view?.winner).toBeNull();
  await page.locator('#board canvas').focus(); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
  await clickCell(page, 76);
  expect((await review(page)).ply).toBe(14);
  expect(await state(page)).toEqual(original);
  expect(await page.evaluate(() => localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY))).toBe(saved);
  const after = (await audio(page)).counts;
  for (const cue of ['move', 'wall', 'undo', 'win', 'lose'] as const) expect(after[cue]).toBe(counts[cue]);
  expect((await state(page)).aiStats).toBeNull();
  await page.locator('#open-menu').click(); const camera = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  await page.locator('#flip').click(); expect((await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera()))[2] * camera[2]).toBeLessThan(0);
  await page.locator('#close-menu').click(); await page.locator('#review-result').click();
  await expect(page.locator('#result-review')).toBeFocused();
  await page.keyboard.press('Escape'); await expect(page.locator('#finished-result')).toBeFocused();
  expect((await audio(page)).activeBgm).toBe(0);
  await page.locator('#finished-result').click(); await page.locator('#result-title').click();
  await expect(page.locator('#startup-dialog')).toBeVisible(); expect((await audio(page)).activeBgm).toBe(1);
  await page.locator('#resume-game-choice').click(); await expect(page.locator('#result-dialog')).toBeVisible();
  expect((await state(page)).view?.positionKey).toBe(original.view?.positionKey);
  expect((await audio(page)).counts.win).toBe(counts.win);
  await page.reload(); await expect(page.locator('#resume-game-choice')).toBeEnabled();
  await page.locator('#resume-game-choice').click(); await expect(page.locator('#result-dialog')).toBeVisible();
  expect((await audio(page)).counts.win).toBe(0); expect((await audio(page)).counts.lose).toBe(0);
});

test('winner wording covers both AI assignments and both PvP pieces; restart confirmation retains conditions', async ({ page }) => {
  await ready(page);
  for (const [actions, mode, side, heading] of [
    [winning, 'ai', 0, 'あなたの勝ち'], [winning, 'ai', 1, 'AIの勝ち'],
    [secondWinning, 'ai', 1, 'あなたの勝ち'], [secondWinning, 'ai', 0, 'AIの勝ち'],
    [secondWinning, 'pvp', 0, '後手・六角の駒の勝ち！'],
  ] as const) {
    await restore(page, [...actions], mode, side); await expect(page.locator('#result-heading')).toHaveText(heading);
    expect((await audio(page)).counts.win + (await audio(page)).counts.lose).toBe(0);
  }
  await restore(page, secondWinning, 'ai', 1);
  const before = await state(page); const saved = await page.evaluate(() => localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY));
  await page.locator('#result-again').click(); await expect(page.locator('#restart-dialog')).toBeVisible();
  await page.locator('#restart-cancel').click(); await expect(page.locator('#result-dialog')).toBeVisible();
  expect((await state(page)).view?.positionKey).toBe(before.view?.positionKey);
  expect(await page.evaluate(() => localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY))).toBe(saved);
  await page.locator('#result-again').click(); await page.locator('#restart-confirm').click();
  await expect(page.locator('#result-dialog')).toBeHidden();
  await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  expect((await state(page)).matchMode).toBe('ai'); expect((await state(page)).humanSide).toBe(1);
  expect((await state(page)).view?.ply).toBe(1); // AI remains first player.
});

test('last placement precedes one win/loss cue and 600ms BGM fade; browsing never replays it', async ({ page }) => {
  await page.addInitScript(() => {
    const starts: { duration: number; at: number; now: number }[] = [];
    const ramps: { value: number; span: number }[] = [];
    const create = AudioContext.prototype.createBufferSource;
    AudioContext.prototype.createBufferSource = function () {
      const source = create.call(this), start = source.start, context = this;
      source.start = function (when = 0, offset = 0, duration?: number) {
        starts.push({ duration: this.buffer?.duration ?? 0, at: when, now: context.currentTime });
        if (duration === undefined) start.call(this, when, offset); else start.call(this, when, offset, duration);
      }; return source;
    };
    // Observe native scheduling on the prototype so the test does not depend
    // on retaining one particular JavaScript AudioParam wrapper.
    const set = AudioParam.prototype.setValueAtTime, ramp = AudioParam.prototype.linearRampToValueAtTime;
    let start = 0;
    AudioParam.prototype.setValueAtTime = function (value, time) { start = time; return set.call(this, value, time); };
    AudioParam.prototype.linearRampToValueAtTime = function (value, time) {
      ramps.push({ value, span: time - start }); return ramp.call(this, value, time);
    };
    Object.assign(window, { presentationAudioStarts: starts, presentationAudioRamps: ramps });
  });
  await ready(page);
  for (const [mode, side, outcome] of [['pvp', 0, 'win'], ['ai', 1, 'lose']] as const) {
    await restore(page, winning.slice(0, -1), mode, side);
    if (mode === 'pvp') await clickCell(page, 76);
    await expect(page.locator('#result-dialog')).toBeVisible();
    expect((await audio(page)).counts[outcome]).toBe(1);
    expect((await audio(page)).activeBgm).toBe(0);
    const events = await page.evaluate(() => ({ starts: (window as any).presentationAudioStarts, ramps: (window as any).presentationAudioRamps }));
    const ending = events.starts.filter((e: any) => e.duration >= 1 && e.duration <= 2).at(-1);
    const placement = events.starts.filter((e: any) => e.duration > 0.2 && e.duration < 0.4).at(-1);
    expect(ending.at - ending.now).toBeCloseTo(0.6, 1);
    expect(ending.at).toBeGreaterThanOrEqual(placement.at + placement.duration);
    expect(events.ramps.some((e: any) => e.value === 0 && Math.abs(e.span - 0.6) < 0.01), JSON.stringify(events.ramps)).toBe(true);
    await expect.poll(() => audio(page).then(s => s.bgmLevel)).toBe(0);
    await page.locator('#result-board').click(); await page.locator('#finished-result').click();
    expect((await audio(page)).counts[outcome]).toBe(1);
  }
});

test('wall inserts vertically at full size in both orientations, sounds on seating and settles after recovery', async ({ page }) => {
  test.setTimeout(90000);
  await ready(page); await page.clock.install();
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 100));
  await page.locator('#mode-wall').click();
  for (const [orientation, anchor] of [['horizontal', 27], ['vertical', 40]] as const) {
    if (orientation === 'vertical') await page.locator('#orientation').click();
    const location = await page.evaluate(anchor => window.__QUORIDOR_APP_TEST_API__!.projectWall(anchor), anchor);
    const before = (await audio(page)).counts.wall;
    await page.mouse.click(location.x, location.y);
    const walls = (await meshes(page)).filter(m => m.kind === 'wall'); const start = walls.at(-1)!;
    expect(start.scale).toEqual([1, 1, 1]); expect(start.position[1]).toBeCloseTo(1.38);
    expect(start.rotation[1]).toBeCloseTo(orientation === 'horizontal' ? 0 : Math.PI / 2);
    expect((await audio(page)).counts.wall).toBe(before);
    await page.clock.runFor(176);
    const mid = (await meshes(page)).filter(m => m.kind === 'wall').at(-1)!;
    expect(mid.scale).toEqual(start.scale); expect(mid.position[0]).toBe(start.position[0]); expect(mid.position[2]).toBe(start.position[2]);
    expect(mid.position[1]).toBeGreaterThan(0.38); expect(mid.position[1]).toBeLessThan(0.7);
    await page.clock.runFor(192);
    expect((await meshes(page)).filter(m => m.kind === 'wall').at(-1)!.position[1]).toBeCloseTo(0.38);
    expect((await audio(page)).counts.wall).toBe(before + 1);
  }
  const p = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(18));
  await page.mouse.click(p.x, p.y);
  expect((await state(page)).phase).toBe('animating');
  const counts = (await audio(page)).counts.wall;
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('renderError'));
  await page.clock.resume(); await page.locator('#retry-renderer').click();
  await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  for (const wall of (await meshes(page)).filter(m => m.kind === 'wall')) { expect(wall.position[1]).toBeCloseTo(0.38); expect(wall.scale).toEqual([1, 1, 1]); }
  expect((await audio(page)).counts.wall).toBe(counts);
});

test('shared move markers replace the selected hint; reduced motion seats walls immediately', async ({ page }) => {
  await ready(page);
  await page.locator('#board canvas').focus(); await page.keyboard.press('ArrowDown');
  const selected = (await meshes(page)).find(m => m.kind === 'preview' && m.visible && m.radius !== undefined)!;
  const hints = (await meshes(page)).filter(m => m.kind === 'hint');
  expect(hints.every(m => m.radius === selected.radius && m.tube === selected.tube && m.position[1] === selected.position[1])).toBe(true);
  expect(hints.filter(m => m.visible && m.position[0] === selected.position[0] && m.position[2] === selected.position[2])).toHaveLength(0);
  expect(hints.find(m => m.visible)!.color).not.toBe(selected.color);
  await page.keyboard.press('Escape'); expect((await meshes(page)).filter(m => m.kind === 'hint').every(m => m.visible)).toBe(true);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.locator('#mode-wall').click();
  const p = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.click(p.x, p.y); expect((await state(page)).phase).toBe('humanTurn');
  expect((await meshes(page)).find(m => m.kind === 'wall')!.position[1]).toBeCloseTo(0.38);
  expect((await audio(page)).counts.wall).toBe(1);
});

test('renderer failure closes results and preserves review position through recovery', async ({ page }) => {
  await ready(page); await restore(page);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('deviceLost'));
  await expect(page.locator('#result-dialog')).toBeHidden(); await expect(page.locator('#retry-renderer')).toBeFocused();
  await page.locator('#retry-renderer').click(); await expect(page.locator('#result-dialog')).toBeVisible();
  await page.locator('#result-review').click(); await expect.poll(() => review(page).then(s => s.phase)).toBe('ready');
  await page.locator('#review-first').click();
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('backendError'));
  await page.locator('#retry-renderer').click(); await expect(page.locator('#fault-panel')).toBeHidden();
  expect((await review(page)).ply).toBe(0); expect((await state(page)).view?.ply).toBe(15);
  await page.locator('#review-last').click(); await page.locator('#review-result').click(); await expect(page.locator('#result-dialog')).toBeVisible();
  expect((await audio(page)).counts.win + (await audio(page)).counts.lose).toBe(0);
});

test('muted and hidden terminal animations stay silent and asset failure does not hide results', async ({ page }) => {
  await ready(page);
  for (const hidden of [false, true]) {
    await restore(page, winning.slice(0, -1));
    if (hidden) await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: true }); document.dispatchEvent(new Event('visibilitychange')); });
    else await page.locator('#sound-mute').click();
    const before = (await audio(page)).counts; await clickCell(page, 76);
    await expect(page.locator('#result-dialog')).toBeVisible();
    expect((await audio(page)).counts.win).toBe(before.win); expect((await audio(page)).counts.move).toBe(before.move);
    if (hidden) await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: false }); document.dispatchEvent(new Event('visibilitychange')); });
    else { await page.locator('#result-board').click(); await page.locator('#sound-mute').click(); }
    expect((await audio(page)).activeBgm).toBe(0);
  }
  await page.route('**/assets/audio/win.wav', route => route.fulfill({ status: 404, body: '' }));
  await page.reload(); await page.locator('#resume-game-choice').click(); await expect(page.locator('#result-dialog')).toBeVisible();
  await restore(page, winning.slice(0, -1)); await clickCell(page, 76);
  await expect(page.locator('#result-dialog')).toBeVisible(); expect((await audio(page)).counts.win).toBe(0);
});

test('icon and result/review controls fit narrow screens and support touch and keyboard', async ({ browser }) => {
  const context = await browser.newContext({ hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  try {
    await ready(page);
    for (const width of [320, 390, 1280]) {
      await page.setViewportSize({ width, height: 844 });
      for (const id of ['sound-mute', 'restart-game', 'new-game', 'open-help', 'open-menu']) {
        const button = page.locator('#' + id); const box = (await button.boundingBox())!;
        expect(box.width).toBeGreaterThanOrEqual(44); expect(box.height).toBeGreaterThanOrEqual(44);
        expect(box.x).toBeGreaterThanOrEqual(0); expect(box.x + box.width).toBeLessThanOrEqual(width);
        await expect(button).toHaveAttribute('aria-label', /.+/); await expect(button.locator('svg')).toBeVisible();
      }
      await restore(page); const box = (await page.locator('#result-dialog').boundingBox())!;
      expect(Math.abs(box.x + box.width / 2 - width / 2)).toBeLessThan(1);
      await page.screenshot({ path: `artifacts/presentation-result-${width}.png` });
      const b = (await page.locator('#result-review').boundingBox())!; await page.touchscreen.tap(b.x + b.width / 2, b.y + b.height / 2);
      await expect(page.locator('#review-counter')).toHaveText('振り返り 15 / 15手'); await page.locator('#review-prev').click();
      await page.screenshot({ path: `artifacts/presentation-review-${width}.png` });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.locator('#review-result').click(); await page.locator('#result-board').click();
    }
    await page.locator('#open-help').focus(); await page.keyboard.press('Enter'); await expect(page.locator('#help-dialog')).toBeVisible();
    await page.keyboard.press('Escape'); await expect(page.locator('#open-help')).toBeFocused();
  } finally { await context.close(); }
});

test('review reproduces every recorded pawn/wall position in both directions without touching the live replay', async ({ page }) => {
  await ready(page); const actions = [81, 152, ...winning];
  const views = await page.evaluate(async actions => {
    const game = await window.__QUORIDOR_RULES_TEST_API__!.createGame({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: 0 });
    try { const views = [game.getView()]; for (const action of actions) views.push(game.applyAction(action)); return views; }
    finally { game.dispose(); }
  }, actions);
  const save = await restore(page, actions);
  await page.locator('#result-review').click(); await expect.poll(() => review(page).then(s => s.phase)).toBe('ready');
  for (let ply = actions.length; ply >= 0; ply--) {
    expect((await review(page)).view).toEqual(views[ply]);
    if (ply) await page.locator('#review-prev').click();
  }
  expect((await meshes(page)).filter(m => m.kind === 'wall')).toHaveLength(0);
  for (let ply = 1; ply <= actions.length; ply++) {
    await page.locator('#review-next').click(); expect((await review(page)).view).toEqual(views[ply]);
  }
  expect((await meshes(page)).filter(m => m.kind === 'wall')).toHaveLength(2);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay())).toEqual(save);
});

test('failed review can retry, and leaving while its independent rules client loads cancels the stale result', async ({ page }) => {
  await ready(page); await restore(page);
  const before = await state(page);
  await page.evaluate(() => {
    const raw = window.__QUORIDOR_RULES_TEST_API__!.RawRulesGame;
    const original = raw.prototype.import_replay; let fail = true;
    raw.prototype.import_replay = function (json) { if (fail) { fail = false; throw new Error('Controlled review failure'); } return original.call(this, json); };
    const free = raw.prototype.free; let frees = 0;
    raw.prototype.free = function () { ++frees; free.call(this); };
    Object.assign(window, { reviewFrees: () => frees });
  });
  await page.locator('#result-review').click(); await expect(page.locator('#review-retry')).toBeVisible();
  await expect(page.locator('#review-status')).toContainText('対局と棋譜は保持');
  expect((await state(page)).view).toEqual(before.view); await expect(page.locator('#review-first')).toBeDisabled();
  await page.locator('#review-retry').click(); await expect.poll(() => review(page).then(s => s.phase)).toBe('ready');
  await page.locator('#review-result').click(); const frees = await page.evaluate(() => (window as any).reviewFrees());
  await page.evaluate(() => {
    (document.querySelector('#result-review')! as HTMLElement).click();
    (document.querySelector('#review-result')! as HTMLElement).click();
  });
  await expect(page.locator('#result-dialog')).toBeVisible(); await expect.poll(() => review(page).then(s => s.phase)).toBe('closed');
  await expect.poll(() => page.evaluate(() => (window as any).reviewFrees())).toBe(frees + 1);
  expect((await state(page)).view).toEqual(before.view);
});

test('title round trip and cancelled restart preserve an unfinished animation and its one placement sound', async ({ page }) => {
  await ready(page);
  await page.evaluate(() => {
    const canvas = document.querySelector('#board canvas')! as HTMLElement; canvas.focus();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    (document.querySelector('#restart-game')! as HTMLElement).click();
  });
  expect((await state(page)).phase).toBe('animating'); expect((await state(page)).paused).toBe(true);
  await page.locator('#restart-cancel').click(); await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  expect((await audio(page)).counts.move).toBe(1);
  await page.evaluate(() => {
    (document.querySelector('#mode-wall')! as HTMLElement).click();
    const canvas = document.querySelector('#board canvas')! as HTMLElement; canvas.focus();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    (document.querySelector('#open-menu')! as HTMLElement).click();
    (document.querySelector('#return-title')! as HTMLElement).click();
  });
  expect((await state(page)).phase).toBe('animating'); expect((await state(page)).paused).toBe(true);
  expect((await audio(page)).counts.wall).toBe(0);
  await page.locator('#resume-game-choice').click(); await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(2); expect((await audio(page)).counts.wall).toBe(1);
  expect((await meshes(page)).find(m => m.kind === 'wall')!.position[1]).toBeCloseTo(0.38);
});
