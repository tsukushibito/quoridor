import { startDefaultMatch } from './start-match';
import { expect, test } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import type { GameView } from '../../packages/engine-bridge/src/rules-client';

type Fixture = { name: string; actions: number[]; view: GameView };
const fixtures = JSON.parse(readFileSync('tests/fixtures/rules/native-views.json', 'utf8')) as Fixture[];

test.beforeEach(async ({ page }) => {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_RULES_TEST_API__ !== undefined)).toBe(true);
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_DIAGNOSTICS__?.phase)).toBe('ready');
});

test('R14: Wasm full views match native fixtures', async ({ page }) => {
  const actual = await page.evaluate(async (cases) => {
    const api = window.__QUORIDOR_RULES_TEST_API__!;
    const views = [];
    for (const fixture of cases) {
      const game = await api.createGame();
      try {
        for (const action of fixture.actions) game.applyAction(action);
        views.push({ name: fixture.name, view: game.getView() });
      } finally { game.dispose(); }
    }
    return views;
  }, fixtures.map(({ name, actions }) => ({ name, actions })));
  expect(actual).toEqual(fixtures.map(({ name, view }) => ({ name, view })));
});

test('public bridge validates replay, snapshot, errors, ownership, and lifetime', async ({ page }) => {
  const result = await page.evaluate(async () => {
    const api = window.__QUORIDOR_RULES_TEST_API__!;
    const code = (fn: () => unknown): string => {
      try { fn(); return 'NO_ERROR'; }
      catch (error) { return (error as { code?: string }).code ?? String(error); }
    };
    const game = await api.createGame();
    const raw = new api.RawRulesGame(JSON.stringify({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: 0 }));
    const rawErrors = [
      code(() => raw.apply_action('0.5')), code(() => raw.apply_action('-1')),
      code(() => raw.apply_action('65536')), code(() => raw.undo_to_ply('1.5')),
      code(() => raw.undo_to_ply('-1')),
      code(() => raw.import_replay('{bad json')),
    ];
    raw.free();
    const opening = [13, 67, 81, 66, 14, 65];
    for (const action of opening) game.applyAction(action);
    const before = game.getView();
    const replay = game.exportReplay();
    const snapshot = game.exportSearchSnapshot();
    const snapshotKey = api.validateSearchSnapshot(snapshot);
    snapshot[0] = 0xff;
    const malformedSnapshot = code(() => api.validateSearchSnapshot(snapshot));
    const savedSnapshotKey = api.validateSearchSnapshot(game.exportSearchSnapshot());
    const malformed = [
      { ...replay, schemaVersion: 2 },
      { ...replay, ply: -1 },
      { ...replay, ply: 1.5 },
      { ...replay, actions: [13, -1] },
      { ...replay, actions: [13, 209] },
      { ...replay, actions: [13, 2.5] },
      { ...replay, actions: [13, '67'] },
      { ...replay, initialConfig: { firstPlayer: 1, wallsPerPlayer: 10, humanPlayer: 0 } },
      { ...replay, positionKey: 'bad' },
      { ...replay, extra: true },
    ];
    const malformedCodes = malformed.map(save => code(() => game.importReplay(save)));
    const unchangedAfterImports = JSON.stringify(game.getView()) === JSON.stringify(before) &&
      JSON.stringify(game.exportReplay()) === JSON.stringify(replay);
    const actionErrors = [
      code(() => game.applyAction(-1)), code(() => game.applyAction(0.5)),
      code(() => game.applyAction(209)), code(() => game.applyAction(0)),
      code(() => game.undoToPly(-1)), code(() => game.undoToPly(1.5)),
      code(() => game.undoToPly(7)),
    ];
    const unchangedAfterActions = JSON.stringify(game.getView()) === JSON.stringify(before);
    const viewCopy = game.getView();
    viewCopy.legalMask.fill(9);
    const copiedView = game.getView().legalMask.every(x => x === 0 || x === 1);
    const undone = game.undoToPly(2);
    const restored = game.importReplay(replay);
    const replayRoundtrip = JSON.stringify(restored) === JSON.stringify(before) && undone.ply === 2;
    game.dispose();
    game.dispose();
    const afterDispose = [code(() => game.getView()), code(() => game.applyAction(13)),
      code(() => game.applyAction(-1)), code(() => game.undoToPly(-1)),
      code(() => game.importReplay(null)), code(() => game.exportReplay()),
      code(() => game.exportSearchSnapshot())];
    return { snapshotKey, savedSnapshotKey, malformedSnapshot, malformedCodes, rawErrors, unchangedAfterImports,
      actionErrors, unchangedAfterActions, copiedView, replayRoundtrip, afterDispose,
      originalKey: before.positionKey };
  });
  expect(result.snapshotKey).toBe(result.originalKey);
  expect(result.savedSnapshotKey).toBe(result.originalKey);
  expect(result.malformedSnapshot).toBe('INVALID_SNAPSHOT');
  expect(result.malformedCodes).toEqual(Array(10).fill('INVALID_REPLAY'));
  expect(result.rawErrors).toEqual(['OUT_OF_RANGE', 'OUT_OF_RANGE', 'OUT_OF_RANGE',
    'OUT_OF_RANGE', 'OUT_OF_RANGE', 'INVALID_REPLAY']);
  expect(result.unchangedAfterImports).toBe(true);
  expect(result.actionErrors).toEqual(['OUT_OF_RANGE', 'OUT_OF_RANGE', 'OUT_OF_RANGE', 'ILLEGAL_ACTION',
    'INVALID_UNDO', 'INVALID_UNDO', 'INVALID_UNDO']);
  expect(result.unchangedAfterActions).toBe(true);
  expect(result.copiedView).toBe(true);
  expect(result.replayRoundtrip).toBe(true);
  expect(result.afterDispose).toEqual(Array(7).fill('DISPOSED'));
});

test('Wasm apply plus complete View timing on varied midgame positions', async ({ page }) => {
  test.setTimeout(120_000);
  const metrics = await page.evaluate(async () => {
    const api = window.__QUORIDOR_RULES_TEST_API__!;
    const total = 144;
    const warmup = 24;
    let seed = 0x7e57b00b;
    const next = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0);
    const samples: number[] = [];
    const keys: string[] = [];
    for (let i = 0; i < total; i++) {
      const game = await api.createGame();
      try {
        let view = game.getView();
        const prepPlies = 14 + (i % 18);
        for (let ply = 0; ply < prepPlies && view.winner === null; ply++) {
          const legal = view.legalMask.flatMap((allowed, id) => allowed ? [id] : []);
          view = game.applyAction(legal[next() % legal.length]!);
        }
        if (view.winner !== null) continue;
        const legal = view.legalMask.flatMap((allowed, id) => allowed ? [id] : []);
        const action = legal[next() % legal.length]!;
        const key = view.positionKey;
        const start = performance.now();
        game.applyAction(action);
        game.getView();
        const elapsed = performance.now() - start;
        if (i >= warmup) { samples.push(elapsed); keys.push(key); }
      } finally { game.dispose(); }
    }
    const ordered = [...samples].sort((a, b) => a - b);
    const percentile = (p: number) => ordered[Math.ceil(ordered.length * p) - 1] ?? null;
    return { mode: 'Chromium software WebGL2, main thread',
      userAgent: navigator.userAgent, sampleCount: samples.length, warmupCount: warmup,
      distinctPositionKeys: new Set(keys).size, p50Ms: percentile(0.50), p95Ms: percentile(0.95),
      p99Ms: percentile(0.99), maxMs: ordered.at(-1) ?? null, samplesMs: samples };
  });
  expect(metrics.sampleCount).toBe(120);
  expect(metrics.distinctPositionKeys).toBeGreaterThan(100);
  mkdirSync('artifacts', { recursive: true });
  const mode = process.env.E2E_MODE || 'dev';
  writeFileSync(`artifacts/phase1-performance-${mode}.json`, JSON.stringify(metrics, null, 2));
  await test.info().attach('timing', { body: JSON.stringify(metrics, null, 2), contentType: 'application/json' });
});
