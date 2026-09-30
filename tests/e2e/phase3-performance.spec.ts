import { startDefaultMatch } from './start-match';
import { expect, test } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const fixtures = JSON.parse(readFileSync('tests/fixtures/ai/native-search.json', 'utf8')) as Array<{
  name: string; payload: { meta: { gameEpoch: number; revision: number; positionKey: string };
    snapshot: number[]; limits: { simulations: number; maxNodes: number; maxDepth: number }; seed: string } }>;
function percentile(sorted: number[], p: number): number { return sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * p) - 1)]!; }

test('Wasm Worker slice and cancellation baseline across varied positions', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => !!window.__QUORIDOR_RULES_TEST_API__)).toBe(true);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase)).toBe('ready');
  const observed = await page.evaluate(async items => {
    const ai = new window.__QUORIDOR_RULES_TEST_API__!.AiClient();
    await ai.startWorker();
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
    const results: Array<{ name: string; actionId: number | null; highWaterBytes: number }> = [];
    let rafMax = 0, timerMax = 0, lastFrame = performance.now(), lastTimer = performance.now(), running = true;
    const frame = (): void => { const now = performance.now(); rafMax = Math.max(rafMax, now - lastFrame); lastFrame = now; if (running) requestAnimationFrame(frame); };
    requestAnimationFrame(frame);
    const timer = setInterval(() => { const now = performance.now(); timerMax = Math.max(timerMax, now - lastTimer); lastTimer = now; }, 16);
    try {
      await new Promise(resolve => setTimeout(resolve, 1200));
      const idle = { rafMax, timerMax };
      rafMax = 0; timerMax = 0; lastFrame = performance.now(); lastTimer = performance.now();
      for (const item of items) for (let repeat = 0; repeat < 3; repeat++) {
        const result = await ai.search({ ...item.payload.meta, snapshot: new Uint8Array(item.payload.snapshot),
          limits: { ...item.payload.limits, simulations: 192 }, seed: item.payload.seed });
        results.push({ name: item.name, actionId: result.actionId, highWaterBytes: result.stats.highWaterBytes });
      }
      const item = items[2]!;
      let progress!: () => void;
      const progressSeen = new Promise<void>(resolve => { progress = resolve; });
      const pending = ai.search({ ...item.payload.meta, snapshot: new Uint8Array(item.payload.snapshot),
        limits: { simulations: 4096, maxNodes: 2048, maxDepth: 48 }, seed: item.payload.seed,
        onProgress: () => progress() }).then(() => 'completed', () => 'cancelled');
      await Promise.race([progressSeen, new Promise(resolve => setTimeout(resolve, 250))]);
      ai.cancel();
      const cancelOutcome = await pending;
      await new Promise(resolve => setTimeout(resolve, 300));
      return { results, cancelOutcome, idle, rafMax, timerMax, diagnostics: ai.diagnostics() };
    } finally { running = false; clearInterval(timer); ai.dispose(); }
  }, fixtures);
  const samples = observed.diagnostics.slices.toSorted((a, b) => a - b);
  expect(observed.results).toHaveLength(9);
  expect(samples.length).toBeGreaterThan(20);
  expect(observed.results.every(result => result.actionId !== null && result.highWaterBytes <= 64 * 1024 * 1024)).toBe(true);
  expect(observed.cancelOutcome).toBe('cancelled');
  expect(observed.diagnostics.cancellationMs.length).toBeGreaterThan(0);
  const report = { mode: process.env.E2E_MODE || 'dev', samples: samples.length,
    sliceMs: { p50: percentile(samples, .5), p95: percentile(samples, .95), p99: percentile(samples, .99), max: samples.at(-1) },
    cancellationMs: observed.diagnostics.cancellationMs, idleRafMaxMs: observed.idle.rafMax,
    idleTimerMaxMs: observed.idle.timerMax, rafMaxMs: observed.rafMax, timerMaxMs: observed.timerMax,
    highWaterBytes: observed.diagnostics.highWaterBytes, wasmMemoryBytes: observed.diagnostics.wasmMemoryBytes,
    positions: observed.results.map(result => result.name) };
  mkdirSync('artifacts', { recursive: true });
  writeFileSync(`artifacts/phase3-${report.mode}-measurements.json`, JSON.stringify(report, null, 2));
});
