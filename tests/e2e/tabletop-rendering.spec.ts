import { startDefaultMatch, restartMatch } from './start-match';
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

async function ready(page: Page): Promise<void> {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase)).toBe('humanTurn');
}
async function assets(page: Page, expected: 'ready' | 'fallback'): Promise<void> {
  await expect.poll(() => page.evaluate(() => {
    const resources = window.__QUORIDOR_APP_TEST_API__!.resources();
    return [resources.environment, resources.wood];
  }), { timeout: 15_000 }).toEqual([expected, expected]);
}
async function move(page: Page): Promise<void> {
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().view?.ply)).toBe(1);
}

test('local HDRI and wood survive restart and renderer recovery, with desktop/mobile evidence', async ({ page }) => {
  test.setTimeout(60_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  const requests: string[] = [];
  page.on('request', request => { if (request.url().includes('/assets/tabletop/')) requests.push(request.url()); });
  await page.setViewportSize({ width: 1440, height: 900 });
  await ready(page); await assets(page, 'ready');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().assetTextures)).toBe(4);
  const lightDirection = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().keyDirection);
  expect(lightDirection).not.toBeNull();
  expect(Math.hypot(...lightDirection!)).toBeCloseTo(1, 6);
  expect(lightDirection![1]).toBeGreaterThan(0);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().keyShadowSize)).toEqual([2048, 2048]);
  await expect.poll(() => page.evaluate(() => {
    const resource = window.__QUORIDOR_APP_TEST_API__!.resources();
    const canvas = document.querySelector<HTMLCanvasElement>('#board canvas')!;
    return { enabled: resource.aoEnabled, size: resource.aoSize, expected: [canvas.width / 2, canvas.height / 2] };
  })).toEqual({ enabled: true, size: [720, 450], expected: [720, 450] });
  for (let i = 0; i < 3; i++) await restartMatch(page);
  expect(requests).toHaveLength(2); // New matches reuse the scene and GPU assets.
  await move(page);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('deviceLost'));
  await page.locator('#retry-renderer').click();
  await assets(page, 'ready');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().aoEnabled)).toBe(true);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().keyDirection)).toEqual(lightDirection);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().keyShadowSize)).toEqual([2048, 2048]);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().view?.ply)).toBe(1);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().assetTextures)).toBe(4);
  expect(requests).toHaveLength(4);
  // Once the newly loaded material has been drawn, an idle board submits no frames.
  await page.waitForTimeout(250);
  const frames = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().submittedFrames);
  await page.waitForTimeout(250);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().submittedFrames)).toBe(frames);
  await page.getByRole('button', { name: '壁を置く' }).click();
  const wall = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.click(wall.x, wall.y);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(1);
  await page.mouse.move(5, 250);
  mkdirSync('.artifacts/tabletop', { recursive: true });
  await page.screenshot({ path: `.artifacts/tabletop/${process.env.E2E_MODE || 'dev'}-desktop.png` });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().aoSize)).toEqual([195, 422]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `.artifacts/tabletop/${process.env.E2E_MODE || 'dev'}-mobile.png` });
  expect(errors).toEqual([]);
});

test('missing environment/wood keep play usable and a retry can restore the assets', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/assets/tabletop/**', route => route.fulfill({ status: 404, body: 'Missing fixture' }));
  await ready(page); await assets(page, 'fallback');
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().assetTextures)).toBe(0);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().keyDirection)).toBeNull();
  await move(page);
  await restartMatch(page);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().view?.ply)).toBe(0);
  await page.unroute('**/assets/tabletop/**');
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('renderError'));
  await page.locator('#retry-renderer').click();
  await assets(page, 'ready');
  await move(page);
  expect(errors).toEqual([]);
});

test('disposing during asset download cannot revive the scene', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let requested = 0;
  await page.route('**/assets/tabletop/**', async route => {
    requested++;
    await gate;
    // Requests are normally canceled by the scene's AbortController.
    await route.continue().catch(() => {});
  });
  await ready(page);
  await expect.poll(() => requested).toBe(2);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().environment)).toBe('loading');
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.disposeForTest());
  release();
  await expect(page.locator('#board canvas')).toHaveCount(0);
  await page.waitForTimeout(300);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state().phase)).toBe('disposed');
  expect(errors).toEqual([]);
});
