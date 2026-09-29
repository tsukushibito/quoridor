import { test, expect } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { readFileSync } from 'node:fs';

const fixtures = JSON.parse(readFileSync('tests/fixtures/ai/native-search.json', 'utf8')) as Array<{
  name: string; payload: { meta: { gameEpoch: number; revision: number; positionKey: string };
    snapshot: number[]; limits: { simulations: number; maxNodes: number; maxDepth: number }; seed: string };
  expected: { actionId: number | null; stats: unknown } }>;

test('rules Wasm, real AI Worker parity, restart, and rendered scene', async ({ page }) => {
  const errors: string[] = [];
  const wasm: { url: string; contentType: string }[] = [];
  const workers: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('worker', worker => workers.push(worker.url()));
  page.on('response', response => {
    if (new URL(response.url()).pathname.endsWith('.wasm') && !response.url().includes('?import'))
      wasm.push({ url: response.url(), contentType: response.headers()['content-type'] || '' });
  });
  await page.goto('./?forceWebGL=1');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase)).toBe('ready');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_RULES_TEST_API__ !== undefined)).toBe(true);
  const initial = await page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__);
  expect(initial?.rulesLoaded).toBe(true);
  expect(initial?.backend).toBe('webgl2');
  expect(initial?.giEnabled).toBe(false);
  expect(initial?.vxgiAddonAvailable).toBe(true);
  expect(initial?.workerReady).toBe(false); // Default PvP does not start AI.
  const result = await page.evaluate(async input => {
    const ai = new window.__QUORIDOR_RULES_TEST_API__!.AiClient();
    try {
      await ai.startWorker();
      const results = [];
      for (const fixture of input) results.push(await ai.search({ ...fixture.payload.meta,
        snapshot: new Uint8Array(fixture.payload.snapshot), limits: fixture.payload.limits, seed: fixture.payload.seed }));
      const context = input[0]!;
      const pending = ai.search({ ...context.payload.meta, snapshot: new Uint8Array(context.payload.snapshot),
        limits: { simulations: 4096, maxNodes: 2048, maxDepth: 48 }, seed: context.payload.seed })
        .then(() => 'resolved', () => 'invalidated');
      await ai.restart();
      const stale = await pending;
      const after = await ai.search({ ...context.payload.meta, snapshot: new Uint8Array(context.payload.snapshot),
        limits: context.payload.limits, seed: context.payload.seed });
      return { results, stale, after, generation: ai.workerGeneration };
    } finally { ai.dispose(); }
  }, fixtures);
  for (const [index, actual] of result.results.entries()) {
    const expected = fixtures[index]!.expected;
    expect(actual!.actionId).toBe(expected.actionId);
    for (const field of ['simulations', 'nodes', 'edges', 'maxDepthReached', 'policyFallbacks', 'valueFallbacks', 'budgetExhausted'] as const)
      expect(actual!.stats[field]).toBe((expected.stats as Record<string, unknown>)[field]);
    expect(actual!.stats.highWaterBytes).toBe(actual!.stats.arenaBytes);
    expect(actual!.stats.arenaBytes).toBeGreaterThan(0);
    expect(actual!.stats.arenaBytes).toBeLessThanOrEqual(64 * 1024 * 1024);
  }
  expect(result.after?.actionId).toBe(fixtures[0]!.expected.actionId);
  expect(result.stale).toBe('invalidated');
  expect(result.generation).toBe(3);
  expect(workers.length).toBeGreaterThanOrEqual(2);
  const basePath = new URL(process.env.E2E_BASE_URL || 'http://127.0.0.1:5173/').pathname;
  expect(workers.every(url => new URL(url).pathname.startsWith(basePath))).toBe(true);
  expect(new Set(wasm.map(response => new URL(response.url).pathname)).size).toBe(2);
  expect(wasm.every(response => new URL(response.url).pathname.startsWith(basePath))).toBe(true);
  expect(wasm.every(response => response.contentType.startsWith('application/wasm'))).toBe(true);
  expect(errors).toEqual([]);
  mkdirSync('artifacts', { recursive: true });
  const mode = process.env.E2E_MODE || 'dev';
  await page.screenshot({ path: `artifacts/phase2-${mode}-desktop.png`, fullPage: true });
});
