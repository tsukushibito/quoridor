import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const endpoint = process.env.CHROME_CDP_URL ?? 'http://127.0.0.1:9222';
const appUrl = process.env.APP_URL ?? 'http://127.0.0.1:5173';
const screenshotPath = fileURLToPath(
  new URL('../../.artifacts/webgpu-smoke/host-webgpu.png', import.meta.url),
);

async function waitForDiagnostics(page) {
  await page.waitForFunction(
    () => ['ready', 'failed'].includes(window.__QUORIDOR_DIAGNOSTICS__?.phase ?? ''),
    undefined,
    { timeout: 60_000 },
  );
  return page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__);
}

const browser = await chromium.connectOverCDP(endpoint, { isLocal: false });
let page;

try {
  const context = browser.contexts()[0];
  if (!context) throw new Error('Chrome default browser context was not found.');

  page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });

  const response = await page.goto(appUrl, { waitUntil: 'domcontentloaded' });
  if (!response?.ok()) throw new Error(`Vite returned HTTP ${response?.status() ?? 'no response'}.`);

  const webgpu = await waitForDiagnostics(page);
  console.log('WebGPU diagnostics:', webgpu);
  if (
    webgpu?.phase !== 'ready' ||
    !webgpu.webgpuAvailable ||
    !webgpu.webgpuAdapterAvailable ||
    webgpu.rendererBackend !== 'webgpu' ||
    !webgpu.vxgiEnabled ||
    !webgpu.frameRendered
  ) {
    throw new Error('Host Chrome did not render a WebGPU/VXGI frame.');
  }

  await mkdir(dirname(screenshotPath), { recursive: true });
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const fallbackUrl = new URL(appUrl);
  fallbackUrl.searchParams.set('forceWebGL', '1');
  await page.goto(fallbackUrl.href, { waitUntil: 'domcontentloaded' });
  const fallback = await waitForDiagnostics(page);
  console.log('Forced WebGL2 diagnostics:', fallback);
  if (
    fallback?.phase !== 'ready' ||
    fallback.rendererBackend !== 'webgl2' ||
    fallback.vxgiEnabled ||
    !fallback.frameRendered
  ) {
    throw new Error('WebGL2 fallback was incorrectly treated as VXGI success.');
  }

  if (errors.length > 0) throw new Error(`Chrome reported errors:\n${errors.join('\n')}`);
  console.log(`Host WebGPU/VXGI smoke passed. Screenshot: ${screenshotPath}`);
} finally {
  await page?.close();
  await browser.close();
}
