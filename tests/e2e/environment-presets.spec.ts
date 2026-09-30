import { startDefaultMatch, restartMatch } from './start-match';
import { expect, test, type Page } from '@playwright/test';

const presets = ['warm-room', 'dark-room', 'forest', 'mountain'] as const;
const paths = ['tabletop/comfy-cafe-2k.hdr', 'environments/warm-restaurant-night-2k.hdr',
  'environments/epping-forest-02-2k.hdr', 'environments/qwantani-noon-2k.hdr'];
const settingsKey = 'quoridor.m1.settings.v1';
const resources = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources());
const state = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state());
async function ready(page: Page) {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
}
async function applied(page: Page, id: string) {
  await expect.poll(() => resources(page).then(x => [x.environment, x.activeEnvironment]), { timeout: 20_000 })
    .toEqual(['ready', id]);
  await expect.poll(() => resources(page).then(x => x.keyShadowSize)).toEqual([2048, 2048]);
}
async function menu(page: Page) {
  await page.locator('#open-menu').click();
  if (!await page.locator('#environment-select').isVisible()) await page.locator('.settings summary').click();
}
async function select(page: Page, id: string) { await page.locator('#environment-select').selectOption(id); }

test('environment presets retain game, camera and canvas; lazy assets and GPU counts remain bounded', async ({ page }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  const requests: string[] = [];
  page.on('request', req => { if (/assets\/(?:tabletop|environments)\/.*\.(hdr|png)/.test(req.url())) requests.push(req.url()); });
  await ready(page); await applied(page, 'warm-room');
  expect(requests).toHaveLength(2);
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  await page.locator('#mode-wall').click();
  const wall = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.click(wall.x, wall.y);
  await expect.poll(() => state(page).then(x => x.view?.ply)).toBe(2);
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  const before = await state(page);
  await menu(page); await page.locator('#flip').click();
  const camera = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  await page.locator('#board canvas').evaluate(el => el.setAttribute('data-instance', 'original'));
  const directions: (number[] | null)[] = [];
  const counts: number[][] = [];
  for (const id of [...presets.slice(1), ...presets, ...presets]) {
    await select(page, id); await applied(page, id);
    const r = await resources(page);
    directions.push(r.keyDirection);
    expect(r.assetTextures).toBe(4);
    // Wait for the beauty frame to bind the new filtered environment.
    await expect.poll(() => resources(page).then(x => x.submittedFrames)).toBeGreaterThan(0);
    await page.waitForTimeout(100);
    counts.push([(await resources(page)).gpuTextures, (await resources(page)).gpuRenderTargets]);
    expect((await state(page)).view).toEqual(before.view);
    expect((await state(page)).gameEpoch).toBe(before.gameEpoch);
    expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera())).toEqual(camera);
    await expect(page.locator('#board canvas')).toHaveAttribute('data-instance', 'original');
  }
  expect(new Set(directions.map(d => JSON.stringify(d))).size).toBe(4);
  expect(counts.slice(-4)).toEqual(counts.slice(-8, -4));
  expect(requests.filter(url => url.endsWith('beech-albedo.png'))).toHaveLength(1);
  const previousRequests = requests.length;
  await select(page, 'mountain'); expect(requests).toHaveLength(previousRequests);
  expect(errors).toEqual([]);
  console.log('Environment GPU texture/render-target counts:', counts);
});

test('environment selection persists and renderer recovery and reload use only the selected HDRI', async ({ page }) => {
  test.setTimeout(60_000);
  await ready(page); await applied(page, 'warm-room'); await menu(page);
  await select(page, 'forest'); await applied(page, 'forest');
  await page.locator('#no-animation').check();
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!).environmentId, settingsKey)).toBe('forest');
  await page.locator('#close-menu').click();
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('deviceLost'));
  await page.locator('#retry-renderer').click(); await applied(page, 'forest');
  const requests: string[] = [];
  page.on('request', req => { if (req.url().endsWith('.hdr')) requests.push(req.url()); });
  await page.reload(); await page.locator('#resume-game-choice').click(); await applied(page, 'forest');
  expect(requests).toHaveLength(1); expect(requests[0]).toContain(paths[2]);
  await menu(page); await expect(page.locator('#environment-select')).toHaveValue('forest');
  await expect(page.locator('#no-animation')).toBeChecked();
});

test('legacy and unknown environment settings preserve next match and motion without rewriting on read', async ({ page }) => {
  test.setTimeout(60_000);
  for (const extra of [{}, { environmentId: 'future-environment' }, { environmentId: 42 }]) {
    const old = { schemaVersion: 1, nextMatch: { mode: 'ai', humanSide: 0, simulations: 48 }, reducedMotion: true, ...extra };
    await page.addInitScript(({ key, old }) => { localStorage.clear(); localStorage.setItem(key, JSON.stringify(old)); }, { key: settingsKey, old });
    await ready(page); await applied(page, 'warm-room');
    expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!), settingsKey)).toEqual(old);
    await menu(page); await expect(page.locator('#no-animation')).toBeChecked();
    await expect(page.locator('#environment-select')).toHaveValue('warm-room');
    await page.locator('#close-menu').click(); await page.locator('#new-game').click();
    await expect(page.locator('#match-mode')).toHaveValue('ai');
    await expect(page.locator('#ai-budget')).toHaveValue('48');
  }
});

test('failed selection preserves the applied environment and persisted request; retry succeeds', async ({ page }) => {
  test.setTimeout(45_000);
  await ready(page); await applied(page, 'warm-room'); await menu(page);
  const before = await resources(page);
  await page.route(`**/${paths[1]}`, route => route.fulfill({ status: 404, body: 'Missing' }));
  await select(page, 'dark-room');
  await expect.poll(() => resources(page).then(x => x.environment)).toBe('error');
  const failed = await resources(page);
  expect([failed.activeEnvironment, failed.keyDirection, failed.keyIntensity, failed.assetTextures])
    .toEqual([before.activeEnvironment, before.keyDirection, before.keyIntensity, 4]);
  await expect(page.locator('#environment-status')).toContainText('暖かい室内を引き続き表示');
  expect(await page.evaluate(key => JSON.parse(localStorage.getItem(key)!).environmentId, settingsKey)).toBe('dark-room');
  await page.unroute(`**/${paths[1]}`); await page.locator('#retry-environment').click(); await applied(page, 'dark-room');
});

test('delayed, superseded and timed out requests retain lighting; disposal cannot revive a pending environment', async ({ page }) => {
  test.setTimeout(60_000);
  await ready(page); await applied(page, 'warm-room'); await menu(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/${paths[1]}`, async route => { await gate; await route.continue().catch(() => {}); });
  const before = await resources(page);
  await select(page, 'dark-room');
  await expect.poll(() => resources(page).then(x => x.environment)).toBe('loading');
  const during = await resources(page);
  expect([during.activeEnvironment, during.keyDirection, during.keyIntensity]).toEqual([before.activeEnvironment, before.keyDirection, before.keyIntensity]);
  await select(page, 'mountain'); await applied(page, 'mountain'); release();
  await page.waitForTimeout(200); expect((await resources(page)).activeEnvironment).toBe('mountain');
  await page.unroute(`**/${paths[1]}`);
  let releaseTimeout!: () => void;
  const timeoutGate = new Promise<void>(resolve => { releaseTimeout = resolve; });
  await page.route(`**/${paths[2]}`, async route => { await timeoutGate; await route.continue().catch(() => {}); });
  await select(page, 'forest');
  await expect.poll(() => resources(page).then(x => x.environment), { timeout: 15_000 }).toBe('error');
  expect((await resources(page)).activeEnvironment).toBe('mountain');
  await page.locator('#retry-environment').click();
  await expect.poll(() => resources(page).then(x => x.environment)).toBe('loading');
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.disposeForTest()); releaseTimeout();
  await expect(page.locator('#board canvas')).toHaveCount(0);
  await page.waitForTimeout(250); expect((await state(page)).phase).toBe('disposed');
});

for (const kind of ['denied', 'quota'] as const) test(`environment remains usable with ${kind} settings storage`, async ({ page }) => {
  await page.addInitScript(({ key, kind }) => {
    const native = Storage.prototype.setItem;
    Storage.prototype.setItem = function(name, value) {
      if (name === key) throw new DOMException('blocked', kind === 'quota' ? 'QuotaExceededError' : 'SecurityError');
      native.call(this, name, value);
    };
  }, { key: settingsKey, kind });
  await ready(page); await applied(page, 'warm-room'); await menu(page);
  await select(page, 'dark-room'); await applied(page, 'dark-room');
  await expect(page.locator('#settings-status')).toContainText(kind === 'quota' ? 'いっぱい' : '保存できません');
});

test('initial selected HDR failure uses a playable fallback and the settings retry restores it', async ({ page }) => {
  await page.addInitScript(key => localStorage.setItem(key, JSON.stringify({ schemaVersion: 1,
    nextMatch: { mode: 'pvp', humanSide: 0, simulations: 96 }, reducedMotion: true, environmentId: 'dark-room' })), settingsKey);
  await page.route(`**/${paths[1]}`, route => route.fulfill({ status: 404, body: 'Missing' }));
  await ready(page);
  await expect.poll(() => resources(page).then(x => x.environment)).toBe('fallback');
  expect((await resources(page)).activeEnvironment).toBeNull();
  expect((await resources(page)).keyIntensity).toBe(0);
  await page.locator('#board canvas').focus(); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
  await expect.poll(() => state(page).then(x => x.view?.ply)).toBe(1);
  await menu(page); await expect(page.locator('#environment-status')).toContainText('簡易背景');
  await page.unroute(`**/${paths[1]}`); await page.locator('#retry-environment').click(); await applied(page, 'dark-room');
  expect((await state(page)).view?.ply).toBe(1);
});

test('an environment request preserves the AI worker and its committed move', async ({ page }) => {
  test.setTimeout(60_000);
  await ready(page); await applied(page, 'warm-room');
  await page.locator('#new-game').click(); await page.locator('#match-mode').selectOption('ai');
  await page.locator('#ai-budget').selectOption('4096'); await page.locator('#dialog-start').click();
  await menu(page); await page.locator('#no-animation').check(); await page.locator('#close-menu').click();
  await expect(page.locator('#menu-dialog')).not.toBeVisible();
  const cell = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectCell(13));
  // Let the first AI reply initialize its Worker before measuring reuse.
  await page.mouse.click(cell.x, cell.y);
  await expect.poll(() => state(page).then(x => x.phase), { timeout: 20_000 }).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(2);
  await restartMatch(page);
  await expect.poll(() => state(page).then(x => [x.phase, x.view?.ply])).toEqual(['humanTurn', 0]);
  await page.mouse.click(cell.x, cell.y);
  const before = await state(page);
  expect(before.phase).toBe('aiThinking');
  const worker = await page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__!.workerGeneration);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route(`**/${paths[2]}`, async route => { await gate; await route.continue().catch(() => {}); });
  await menu(page); await select(page, 'forest');
  await expect.poll(() => state(page).then(x => x.view?.ply), { timeout: 20_000 }).toBe(2);
  expect((await state(page)).gameEpoch).toBe(before.gameEpoch);
  expect(await page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__!.workerGeneration)).toBe(worker);
  release(); await applied(page, 'forest');
  expect((await state(page)).view?.ply).toBe(2);
});
