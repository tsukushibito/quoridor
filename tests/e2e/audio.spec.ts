import { restartMatch } from './start-match';
import { expect, test, type Page } from '@playwright/test';

const key = 'quoridor.audio.settings.v1';
const initial = { schemaVersion: 1, muted: false, sfxEnabled: true, bgmEnabled: true, sfxVolume: 55, bgmVolume: 20 };
const audio = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.audio());
const state = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state());
async function ready(page: Page) {
  await page.goto('./?forceWebGL=1');
  await expect(page.locator('#startup-new-game')).toBeEnabled();
  // Prepare a game without a trusted gesture so autoplay/unlock assertions remain meaningful.
  await page.evaluate(() => { (document.querySelector('#startup-new-game')! as HTMLElement).click();
    (document.querySelector('#dialog-start')! as HTMLElement).click(); });
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
}
async function unlock(page: Page) {
  await page.locator('#open-menu').click();
  await expect.poll(() => audio(page).then(value => value.status)).toBe('ready');
  await expect.poll(() => audio(page).then(value => value.loaded.length)).toBe(7);
}
async function move(page: Page, id: number) {
  const point = await page.evaluate(cell => window.__QUORIDOR_APP_TEST_API__!.projectCell(cell), id);
  await page.mouse.click(point.x, point.y);
  await expect.poll(() => state(page).then(value => value.phase)).not.toBe('animating');
}
async function range(page: Page, id: string, value: number) {
  await page.locator(id).fill(String(value));
}

test('first gesture unlocks actual decoded audio; volume and mute preserve independent preferences', async ({ page }) => {
  await ready(page);
  expect((await audio(page)).contextState).toBeNull();
  expect((await audio(page)).counts.bgm).toBe(0);
  await unlock(page);
  expect((await audio(page)).counts.bgm).toBe(1);
  expect((await audio(page)).bgmDuration).toBeCloseTo(130.194, 1);
  const before = (await audio(page)).counts.move;
  await page.locator('#sound-preview').click();
  expect((await audio(page)).counts.move).toBe(before + 1);
  await range(page, '#sfx-volume', 73);
  await range(page, '#bgm-volume', 12);
  await expect(page.locator('#sfx-value')).toHaveText('73%');
  await expect.poll(() => audio(page).then(value => value.sfxLevel)).toBeCloseTo(0.73, 2);
  await expect.poll(() => audio(page).then(value => value.bgmLevel)).toBeCloseTo(0.12, 2);
  await page.locator('#sfx-enabled').uncheck();
  await expect(page.locator('#sound-preview')).toBeDisabled();
  await page.locator('#sound-muted').check();
  expect((await audio(page)).activeBgm).toBe(0);
  await range(page, '#sfx-volume', 74);
  expect((await audio(page)).settings.muted).toBe(true);
  await page.locator('#sound-muted').uncheck();
  expect((await audio(page)).settings.sfxEnabled).toBe(false);
  expect((await audio(page)).settings.sfxVolume).toBe(74);
  await range(page, '#bgm-volume', 0);
  expect((await audio(page)).activeBgm).toBe(0);
  await range(page, '#bgm-volume', 100);
  await expect.poll(() => audio(page).then(value => value.bgmLevel)).toBeCloseTo(1, 2);
  await page.locator('#bgm-enabled').uncheck();
  await range(page, '#bgm-volume', 20);
  expect((await audio(page)).settings.bgmEnabled).toBe(false);
  expect((await audio(page)).activeBgm).toBe(0);
  await page.locator('#close-menu').click();
  const clicks = (await audio(page)).counts.click;
  await page.locator('#sound-mute').click();
  await expect(page.locator('#sound-mute')).toHaveAttribute('aria-pressed', 'true');
  expect((await audio(page)).counts.click).toBe(clicks);
  await page.reload();
  await expect(page.locator('#startup-dialog')).toBeVisible();
  await page.locator('#resume-game-choice').click();
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  const restored = (await audio(page)).settings;
  expect(restored).toEqual({ ...initial, muted: true, sfxEnabled: false, bgmEnabled: false, sfxVolume: 74 });
  expect((await audio(page)).activeBgm).toBe(0);
});

test('committed human/AI moves and walls sound once; previews, undo, restore and renderer recovery do not replay', async ({ page }) => {
  await ready(page); await unlock(page);
  await page.locator('.settings summary').click();
  await page.locator('#no-animation').check();
  await page.locator('#close-menu').click();
  const before = await audio(page);
  await move(page, 0); // illegal
  expect((await audio(page)).counts.move).toBe(before.counts.move);
  await move(page, 13);
  expect((await audio(page)).counts.move).toBe(before.counts.move + 1);
  await page.locator('#mode-wall').click();
  const point = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.move(point.x, point.y);
  expect((await audio(page)).counts.wall).toBe(0);
  await page.mouse.click(point.x, point.y);
  expect((await audio(page)).counts.wall).toBe(1);
  await page.mouse.click(point.x, point.y);
  expect((await audio(page)).counts.wall).toBe(1);
  await page.locator('#undo').click();
  expect((await audio(page)).counts.undo).toBe(1);
  const saved = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay());
  const counts = (await audio(page)).counts;
  await page.evaluate(save => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(save, 'pvp', 0), saved);
  expect((await audio(page)).counts).toEqual(counts);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('renderError'));
  await page.locator('#retry-renderer').click();
  await expect.poll(() => page.locator('#board canvas').count()).toBe(1);
  expect((await audio(page)).counts).toEqual(counts);
  await page.locator('#new-game').click();
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#ai-budget').selectOption('48');
  await page.locator('#dialog-start').click();
  await move(page, 13);
  await expect.poll(() => state(page).then(value => value.view?.ply)).toBe(2);
  await expect.poll(() => state(page).then(value => value.phase)).toBe('humanTurn');
  const afterAi = (await audio(page)).counts;
  expect(afterAi.move - counts.move + afterAi.wall - counts.wall).toBe(2);
  expect(afterAi.bgm).toBe(1);
});

test('finishing a game emits one completion cue; restoring a finished game is silent', async ({ page }) => {
  await ready(page); await unlock(page);
  await page.locator('.settings summary').click(); await page.locator('#no-animation').check();
  await page.locator('#close-menu').click();
  for (const cell of [13, 67, 22, 58, 31, 49, 40, 48, 49, 47, 58, 46, 67, 45, 76]) await move(page, cell);
  await expect.poll(() => state(page).then(value => value.phase)).toBe('finished');
  expect((await audio(page)).counts.win).toBe(1);
  const replay = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay());
  const counts = (await audio(page)).counts;
  await page.evaluate(save => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(save, 'pvp', 0), replay);
  expect((await audio(page)).counts).toEqual(counts);
});

test('hidden tab stops sources and resumes music position without duplicate loops or SE backlog', async ({ page }) => {
  await ready(page); await unlock(page);
  await page.locator('#sound-preview').click();
  await expect.poll(() => audio(page).then(value => value.bgmPosition)).toBeGreaterThan(0.1);
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: true });
    document.dispatchEvent(new Event('visibilitychange')); });
  const paused = await audio(page);
  expect(paused.activeBgm).toBe(0); expect(paused.activeEffects).toBe(0);
  await page.locator('#sound-preview').click();
  expect((await audio(page)).counts.move).toBe(paused.counts.move);
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, value: false });
    document.dispatchEvent(new Event('visibilitychange')); });
  await expect.poll(() => audio(page).then(value => value.activeBgm)).toBe(1);
  expect((await audio(page)).bgmPosition).toBeGreaterThanOrEqual(paused.bgmPosition);
  expect((await audio(page)).counts.move).toBe(paused.counts.move);
  await page.locator('#close-menu').click(); await restartMatch(page);
  expect((await audio(page)).counts.bgm).toBe(2);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.disposeForTest());
  expect((await audio(page)).activeBgm).toBe(0); expect((await audio(page)).activeEffects).toBe(0);
  await expect.poll(() => audio(page).then(value => value.contextState)).toBe('closed');
});

test('asset HTTP/decode failure is recoverable and does not stop the game', async ({ page }) => {
  await page.route('**/assets/audio/pawn.wav', route => route.fulfill({ status: 404, body: '' }));
  await page.route('**/assets/audio/cozy-puzzle.mp3', route => route.fulfill({ status: 200, body: 'invalid audio' }));
  await ready(page); await page.locator('#open-menu').click();
  await expect.poll(() => audio(page).then(value => value.pending)).toBe(0);
  expect((await audio(page)).failures.sort()).toEqual(['bgm', 'move']);
  await expect(page.locator('#sound-status')).toContainText('対局は続けられます');
  await page.locator('#close-menu').click(); await move(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  await page.unroute('**/assets/audio/pawn.wav'); await page.unroute('**/assets/audio/cozy-puzzle.mp3');
  await page.locator('#open-menu').click(); await page.locator('#sound-retry').click();
  await expect.poll(() => audio(page).then(value => value.status)).toBe('ready');
  expect((await audio(page)).activeBgm).toBe(1);
});

test('autoplay denial retries from a gesture without replaying missed moves', async ({ page }) => {
  await page.addInitScript(() => {
    const original = AudioContext.prototype.resume;
    let fail = true;
    AudioContext.prototype.resume = function () {
      if (fail) return Promise.reject(new DOMException('Controlled autoplay denial', 'NotAllowedError'));
      return original.call(this);
    };
    (window as Window & { allowAudio?: () => void }).allowAudio = () => { fail = false; };
  });
  await ready(page); await page.locator('#open-menu').click();
  await expect(page.locator('#sound-status')).toContainText('音声を開始できません');
  await page.locator('#close-menu').click(); await move(page, 13);
  expect((await audio(page)).counts.move).toBe(0);
  await page.evaluate(() => (window as Window & { allowAudio: () => void }).allowAudio());
  await page.locator('#open-menu').click();
  await expect.poll(() => audio(page).then(value => value.status)).toBe('ready');
  expect((await audio(page)).counts.move).toBe(0);
});

test('unavailable audio and storage leave settings usable and games playable', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'AudioContext', { value: class { constructor() { throw new Error('Unavailable'); } } });
    Storage.prototype.setItem = () => { throw new DOMException('Storage disabled', 'QuotaExceededError'); };
  });
  await ready(page); await page.locator('#open-menu').click();
  await expect(page.locator('#sound-status')).toContainText('このブラウザでは音声を使えません');
  await range(page, '#sfx-volume', 40);
  await expect(page.locator('#sound-storage')).toContainText('今回の設定は使えます');
  expect((await audio(page)).settings.sfxVolume).toBe(40);
  await page.locator('#close-menu').click(); await move(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
});

test('saved mute prevents even the first gesture from starting audio', async ({ page }) => {
  await page.addInitScript(({ key, initial }) => localStorage.setItem(key, JSON.stringify({ ...initial, muted: true })), { key, initial });
  await ready(page); await page.locator('#open-menu').click();
  expect((await audio(page)).activeBgm).toBe(0); expect((await audio(page)).counts.click).toBe(0);
  await page.locator('#sound-muted').uncheck();
  await expect.poll(() => audio(page).then(value => value.activeBgm)).toBe(1);
});

test('the real audio graph produces music signal and becomes silent on mute', async ({ page }) => {
  await page.addInitScript(() => {
    const analysers: AnalyserNode[] = [];
    const original = AudioContext.prototype.createGain;
    AudioContext.prototype.createGain = function () {
      const gain = original.call(this), analyser = this.createAnalyser();
      analyser.fftSize = 2048; gain.connect(analyser); analysers.push(analyser); return gain;
    };
    (window as Window & { musicRms?: () => number }).musicRms = () => {
      const analyser = analysers[1]; if (!analyser) return 0;
      const samples = new Float32Array(analyser.fftSize); analyser.getFloatTimeDomainData(samples);
      return Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
    };
  });
  await ready(page); await unlock(page);
  const rms = () => page.evaluate(() => (window as Window & { musicRms: () => number }).musicRms());
  await expect.poll(rms).toBeGreaterThan(0.00001);
  await page.locator('#sound-muted').check();
  await expect.poll(rms).toBeLessThan(0.000001);
});

test('touch and keyboard controls fit desktop/320px/390px viewports with visible values', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true,
    isMobile: browser.browserType().name() !== 'firefox' });
  const page = await context.newPage();
  try {
    await ready(page);
    const point = await page.locator('#sound-mute').boundingBox();
    await page.touchscreen.tap(point!.x + point!.width / 2, point!.y + point!.height / 2);
    expect((await audio(page)).settings.muted).toBe(true);
    await page.touchscreen.tap(point!.x + point!.width / 2, point!.y + point!.height / 2);
    await unlock(page);
    await page.locator('#sfx-volume').focus(); await page.keyboard.press('Home');
    await expect(page.locator('#sfx-value')).toHaveText('0%');
    await page.keyboard.press('End'); await expect(page.locator('#sfx-value')).toHaveText('100%');
    for (const width of [320, 390, 1280]) {
      await page.setViewportSize({ width, height: 844 });
      await page.locator('#close-menu').click();
      const b = await page.locator('#sound-mute').boundingBox();
      expect(b!.width).toBeGreaterThanOrEqual(44); expect(b!.height).toBeGreaterThanOrEqual(44);
      expect(b!.x).toBeGreaterThanOrEqual(0); expect(b!.x + b!.width).toBeLessThanOrEqual(width);
      await page.locator('#open-menu').click();
      await expect(page.getByRole('heading', { name: 'サウンド', exact: true })).toBeVisible();
      await expect(page.getByLabel('効果音の音量', { exact: true })).toBeVisible();
      await page.screenshot({ path: `artifacts/audio-${width}.png` });
    }
  } finally { await context.close(); }
});
