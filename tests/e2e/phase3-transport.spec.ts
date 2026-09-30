import { startDefaultMatch } from './start-match';
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const fixture = JSON.parse(readFileSync('tests/fixtures/ai/native-search.json', 'utf8'))[0] as {
  payload: { meta: { gameEpoch: number; revision: number; positionKey: string }; snapshot: number[];
    limits: { simulations: number; maxNodes: number; maxDepth: number }; seed: string };
  expected: { actionId: number; stats: Record<string, unknown> };
};

test('transport resolves ready/search on restart and dispose, rejects current corruption, ignores stale tags', async ({ page }) => {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => !!window.__QUORIDOR_RULES_TEST_API__)).toBe(true);
  const outcome = await page.evaluate(async f => {
    class FakeWorker {
      onmessage: ((event: MessageEvent<unknown>) => void) | null = null;
      onerror: ((event: ErrorEvent) => void) | null = null;
      onmessageerror: (() => void) | null = null;
      sent: unknown[] = [];
      terminated = false;
      autoReady = true;
      autoAck = true;
      postMessage(value: unknown): void {
        this.sent.push(value);
        if (typeof value !== 'object' || value === null || !('type' in value)) return;
        if (value.type === 'init' && this.autoReady) {
          const request = value as { protocolVersion: number; engineBuildId: string; workerGeneration: number };
          setTimeout(() => this.emit({ type: 'ready', protocolVersion: request.protocolVersion,
            engineBuildId: request.engineBuildId, workerGeneration: request.workerGeneration }), 0);
        }
        if (value.type === 'cancel' && this.autoAck) {
          const request = value as { meta: unknown };
          setTimeout(() => this.emit({ type: 'cancelled', meta: request.meta }), 0);
        }
      }
      emit(data: unknown): void { if (!this.terminated) this.onmessage?.({ data } as MessageEvent<unknown>); }
      terminate(): void { this.terminated = true; }
    }
    const workers: FakeWorker[] = [];
    const factory = (): Worker => { const worker = new FakeWorker(); workers.push(worker); return worker as unknown as Worker; };
    const AiClient = window.__QUORIDOR_RULES_TEST_API__!.AiClient;
    const client = new AiClient(factory);
    const context = { ...f.payload.meta, snapshot: new Uint8Array(f.payload.snapshot), limits: f.payload.limits, seed: f.payload.seed };
    const firstReady = client.startWorker().then(() => 'ready', () => 'rejected');
    const firstGeneration = client.workerGeneration;
    await client.restart();
    const restartedReady = await firstReady;
    const running = client.search(context).then(() => 'resolved', () => 'rejected');
    await new Promise(resolve => setTimeout(resolve, 0));
    const worker = workers.at(-1)!;
    const start = worker.sent.find(v => typeof v === 'object' && v !== null && 'type' in v && v.type === 'start') as
      { payload: { meta: Record<string, unknown> } };
    const meta = start.payload.meta;
    const valid = { type: 'result', meta, result: f.expected, sliceMs: 2, sliceSamples: [1, 2], wasmMemoryBytes: 1048576 };
    worker.emit({ ...valid, meta: { ...meta, requestId: Number(meta.requestId) + 9 } });
    worker.emit({ type: 'progress', meta: { ...meta, positionKey: '0'.repeat(42) }, stats: f.expected.stats, sliceMs: 1 });
    const pendingAfterStale = await Promise.race([running, new Promise(resolve => setTimeout(() => resolve('pending'), 20))]);
    worker.emit({ ...valid, result: { ...f.expected, actionId: 999 } });
    const corrupt = await running;
    const terminatedAfterCorrupt = worker.terminated;
    const second = client.search(context).then(() => 'resolved', () => 'rejected');
    await new Promise(resolve => setTimeout(resolve, 0));
    const current = workers.at(-1)!;
    const newStart = current.sent.find(v => typeof v === 'object' && v !== null && 'type' in v && v.type === 'start') as
      { payload: { meta: Record<string, unknown> } };
    current.emit({ ...valid, meta: newStart.payload.meta });
    const validOutcome = await second;
    current.emit({ ...valid, meta: newStart.payload.meta }); // duplicate completion
    current.autoAck = false;
    const third = client.search(context).then(() => 'resolved', () => 'cancelled');
    await new Promise(resolve => setTimeout(resolve, 0));
    const thirdStart = current.sent.filter(v => typeof v === 'object' && v !== null && 'type' in v && v.type === 'start').at(-1) as
      { payload: { meta: Record<string, unknown> } };
    client.cancel();
    current.emit({ ...valid, meta: thirdStart.payload.meta }); // result racing after cancellation
    const cancelled = await third;
    const generationBeforeWatchdog = client.workerGeneration;
    await new Promise(resolve => setTimeout(resolve, 300));
    const generationAfterWatchdog = client.workerGeneration;
    await client.startWorker();
    const readyAfterWatchdog = client.workerGeneration;
    const afterWatchdog = client.search(context).then(() => 'resolved', () => 'rejected');
    await new Promise(resolve => setTimeout(resolve, 0));
    const recoveredWorker = workers.at(-1)!;
    const recoveredStart = recoveredWorker.sent.find(v => typeof v === 'object' && v !== null && 'type' in v && v.type === 'start') as
      { payload: { meta: Record<string, unknown> } };
    recoveredWorker.emit({ type: 'error', meta: thirdStart.payload.meta, code: 'STALE', message: 'old error' });
    recoveredWorker.emit({ ...valid, meta: { ...recoveredStart.payload.meta, workerGeneration: Number(recoveredStart.payload.meta.workerGeneration) - 1 } });
    const pendingAfterStaleError = await Promise.race([afterWatchdog, new Promise(resolve => setTimeout(() => resolve('pending'), 20))]);
    recoveredWorker.emit({ ...valid, meta: recoveredStart.payload.meta });
    const recovered = await afterWatchdog;
    client.dispose();
    const disposedStart = client.startWorker().then(() => 'ready', () => 'rejected');
    const disposed = await disposedStart;
    const pendingReadyClient = new AiClient(() => { const w = new FakeWorker(); w.autoReady = false; return w as unknown as Worker; });
    const pendingReady = pendingReadyClient.startWorker().then(() => 'ready', () => 'rejected');
    pendingReadyClient.dispose();
    const faultClient = new AiClient(factory);
    await faultClient.startWorker();
    const failedSearch = faultClient.search(context).then(() => 'resolved', () => 'rejected');
    await new Promise(resolve => setTimeout(resolve, 0));
    workers.at(-1)!.onerror?.({ message: 'forced worker error', preventDefault() {} } as ErrorEvent);
    const workerError = await failedSearch;
    await faultClient.startWorker();
    const messageFailed = faultClient.search(context).then(() => 'resolved', () => 'rejected');
    await new Promise(resolve => setTimeout(resolve, 0));
    workers.at(-1)!.onmessageerror?.();
    const messageError = await messageFailed;
    faultClient.dispose();
    const mismatchWorker = new FakeWorker(); mismatchWorker.autoReady = false;
    const mismatchClient = new AiClient(() => mismatchWorker as unknown as Worker);
    const mismatchReady = mismatchClient.startWorker().then(() => 'ready', () => 'rejected');
    mismatchWorker.emit({ type: 'ready', protocolVersion: 2, engineBuildId: 'wrong-build', workerGeneration: mismatchClient.workerGeneration });
    const mismatch = await mismatchReady;
    mismatchClient.dispose();
    const disposingClient = new AiClient(factory);
    await disposingClient.startWorker();
    const disposingSearch = disposingClient.search(context).then(() => 'resolved', () => 'rejected');
    await new Promise(resolve => setTimeout(resolve, 0));
    disposingClient.dispose();
    const disposedSearch = await disposingSearch;
    return { firstGeneration, restartedReady, pendingAfterStale, corrupt, terminatedAfterCorrupt,
      validOutcome, cancelled, generationBeforeWatchdog, generationAfterWatchdog, readyAfterWatchdog,
      disposed, pendingReady: await pendingReady, pendingAfterStaleError, recovered, workerError, messageError, mismatch, disposedSearch,
      cancellationMs: client.diagnostics().cancellationMs };
  }, fixture);
  expect(outcome.firstGeneration).toBe(1);
  expect(outcome.restartedReady).toBe('rejected');
  expect(outcome.pendingAfterStale).toBe('pending');
  expect(outcome.corrupt).toBe('rejected');
  expect(outcome.terminatedAfterCorrupt).toBe(true);
  expect(outcome.validOutcome).toBe('resolved');
  expect(outcome.cancelled).toBe('cancelled');
  expect(outcome.generationAfterWatchdog).toBeGreaterThan(outcome.generationBeforeWatchdog);
  expect(outcome.readyAfterWatchdog).toBeGreaterThan(outcome.generationAfterWatchdog);
  expect(outcome.pendingAfterStaleError).toBe('pending');
  expect(outcome.recovered).toBe('resolved');
  expect(outcome.disposed).toBe('rejected');
  expect(outcome.pendingReady).toBe('rejected');
  expect(outcome.workerError).toBe('rejected');
  expect(outcome.messageError).toBe('rejected');
  expect(outcome.mismatch).toBe('rejected');
  expect(outcome.disposedSearch).toBe('rejected');
  expect(outcome.cancellationMs.at(-1)).toBeGreaterThanOrEqual(240);
});

test('session rejects a malformed current AI action without changing Rust game', async ({ page }) => {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => !!window.__QUORIDOR_SESSION_TEST_API__)).toBe(true);
  const result = await page.evaluate(async () => {
    const AiClient = window.__QUORIDOR_RULES_TEST_API__!.AiClient;
    class BadAi extends AiClient {
      override async search() {
        return { actionId: 999, stats: { simulations: 1, nodes: 1, edges: 1, arenaBytes: 1,
          highWaterBytes: 1, maxDepthReached: 1, policyFallbacks: 0, valueFallbacks: 0, budgetExhausted: false } };
      }
    }
    const session = new window.__QUORIDOR_SESSION_TEST_API__!.SessionController(new BadAi());
    await session.newGame({ mode: 'ai', humanSide: 1, simulations: 1 });
    await new Promise(resolve => setTimeout(resolve, 0));
    const state = session.state;
    session.dispose();
    return { phase: state.phase, ply: state.view?.ply, key: state.view?.positionKey, error: state.error };
  });
  expect(result.phase).toBe('recoverableError');
  expect(result.ply).toBe(0);
  expect(result.key).toBe('044c0a0a0200000000000000000000000000000000');
  expect(result.error).toContain('illegal action');
});

test('restored AI undo returns to the prior human decision and ignores a late result', async ({ page }) => {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => !!window.__QUORIDOR_SESSION_TEST_API__)).toBe(true);
  const cases = await page.evaluate(async () => {
    const rules = window.__QUORIDOR_RULES_TEST_API__!;
    const AiClient = rules.AiClient;
    type AiReply = Awaited<ReturnType<InstanceType<typeof AiClient>['search']>>;
    class WaitingAi extends AiClient {
      pendingReplies: Array<(reply: AiReply) => void> = [];
      cancellations = 0;
      override search(): Promise<AiReply> { return new Promise(resolve => this.pendingReplies.push(resolve)); }
      override cancel(): void { this.cancellations++; }
    }
    const makeSave = async (actions: number[], humanSide: 0 | 1 = 0) => {
      const game = await rules.createGame({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: humanSide });
      try {
        for (const action of actions) game.applyAction(action);
        return game.exportReplay();
      } finally { game.dispose(); }
    };
    const opening = [13, 67, 22, 58];
    const terminalActions: number[] = [];
    for (let move = 0; move < 8; move++) {
      terminalActions.push(13 + move * 9);
      if (move < 7) terminalActions.push(move % 2 === 0 ? 75 : 76);
    }
    const check = async (actions: number[], humanSide: 0 | 1, expectedPly: number | null,
      mode: 'ai' | 'pvp' = 'ai', late = false, cancelled = false) => {
      const ai = new WaitingAi();
      const session = new window.__QUORIDOR_SESSION_TEST_API__!.SessionController(ai);
      try {
        const save = await makeSave(actions, humanSide);
        await session.restoreReplay(save, { mode, humanSide, simulations: 96 });
        const before = session.state;
        const canUndo = session.canUndo();
        const oldRevision = before.revision;
        if (cancelled) session.cancelAi();
        const undone = session.undo();
        const after = session.state;
        if (late && ai.pendingReplies[0]) {
          ai.pendingReplies[0]({ actionId: before.view!.legalMask.findIndex(bit => bit === 1),
            stats: { simulations: 1, nodes: 1, edges: 1, arenaBytes: 1, highWaterBytes: 1,
              maxDepthReached: 1, policyFallbacks: 0, valueFallbacks: 0, budgetExhausted: false } });
          await new Promise(resolve => setTimeout(resolve, 0));
        }
        const stable = session.state;
        return { before: { phase: before.phase, ply: before.view?.ply, turn: before.view?.turn, winner: before.view?.winner },
          canUndo, undoPly: undone?.ply ?? null, after: { phase: after.phase, ply: after.view?.ply, turn: after.view?.turn,
            winner: after.view?.winner, revision: after.revision }, oldRevision, stablePly: stable.view?.ply,
          stableKey: stable.view?.positionKey, afterKey: after.view?.positionKey,
          cancellations: ai.cancellations, expectedPly };
      } finally { session.dispose(); }
    };
    const failedUndo = async () => {
      const ai = new WaitingAi();
      const session = new window.__QUORIDOR_SESSION_TEST_API__!.SessionController(ai);
      try {
        await session.restoreReplay(await makeSave([13]), { mode: 'ai', humanSide: 0, simulations: 96 });
        const before = session.state;
        const game = (session as unknown as { client: { undoToPly: (ply: number) => unknown } }).client;
        game.undoToPly = () => { throw new Error('forced undo failure'); };
        const undone = session.undo();
        const failed = session.state;
        session.retryAi();
        const retried = session.state;
        session.cancelAi();
        session.switchToPvp();
        const takeover = session.state;
        return { undone, beforeKey: before.view?.positionKey, failedKey: failed.view?.positionKey,
          failedPhase: failed.phase, failedError: failed.error, failedRevision: failed.revision,
          beforeRevision: before.revision, retriedPhase: retried.phase,
          takeoverPhase: takeover.phase, takeoverMode: takeover.mode, takeoverTurn: takeover.view?.turn };
      } finally { session.dispose(); }
    };
    return {
      humanFirstOpening: await check([13], 0, 0, 'ai', true),
      humanFirstMidgame: await check(opening.slice(0, 3), 0, 2),
      aiFirstOpening: await check([13], 1, null),
      aiFirstThinking: await check(opening.slice(0, 2), 1, 1),
      aiFirstMidgame: await check(opening, 1, 3),
      cancelled: await check([13], 0, 0, 'ai', true, true),
      humanFirstCompleted: await check(opening.slice(0, 2), 0, 0),
      aiFirstCompleted: await check(opening.slice(0, 3), 1, 1),
      humanWins: await check(terminalActions, 0, 14),
      aiWins: await check(terminalActions, 1, 13),
      pvp: await check(opening.slice(0, 3), 0, 2, 'pvp'),
      failedUndo: await failedUndo(),
    };
  });
  const { failedUndo, ...undoCases } = cases;
  for (const [name, result] of Object.entries(undoCases)) {
    expect(result.undoPly, name).toBe(result.expectedPly);
    expect(result.canUndo, name).toBe(result.expectedPly !== null);
    if (result.expectedPly === null) {
      expect(result.after.ply, name).toBe(result.before.ply);
      expect(result.after.revision, name).toBe(result.oldRevision);
      continue;
    }
    expect(result.after.ply, name).toBe(result.expectedPly);
    expect(result.after.phase, name).toBe('humanTurn');
    expect(result.after.turn, name).toBe(name === 'pvp' ? 0 : name.startsWith('aiFirst') || name === 'aiWins' ? 1 : 0);
    expect(result.after.revision, name).toBe(result.oldRevision + 1);
    expect(result.stablePly, name).toBe(result.expectedPly);
    expect(result.stableKey, name).toBe(result.afterKey);
  }
  expect(cases.humanFirstOpening.before.phase).toBe('aiThinking');
  expect(cases.humanFirstMidgame.before.phase).toBe('aiThinking');
  expect(cases.aiFirstThinking.before.phase).toBe('aiThinking');
  expect(cases.aiFirstMidgame.before.phase).toBe('aiThinking');
  expect(cases.cancelled.cancellations).toBeGreaterThanOrEqual(2);
  expect(cases.humanWins.before).toMatchObject({ phase: 'finished', winner: 0 });
  expect(cases.aiWins.before).toMatchObject({ phase: 'finished', winner: 0 });
  expect(failedUndo).toMatchObject({ undone: null, failedPhase: 'recoverableError',
    failedError: 'forced undo failure', retriedPhase: 'aiThinking', takeoverPhase: 'humanTurn',
    takeoverMode: 'pvp', takeoverTurn: 1 });
  expect(failedUndo.failedKey).toBe(failedUndo.beforeKey);
  expect(failedUndo.failedRevision).toBe(failedUndo.beforeRevision);
});

test('public AI bridge rejects malformed budgets, keys, snapshots and seeds', async ({ page }) => {
  await page.goto('./?forceWebGL=1');
  await startDefaultMatch(page);
  await expect.poll(() => page.evaluate(() => !!window.__QUORIDOR_RULES_TEST_API__)).toBe(true);
  const checks = await page.evaluate(async f => {
    const api = window.__QUORIDOR_RULES_TEST_API__!;
    const game = await api.createGame();
    const ai = new api.AiClient();
    try {
      const key = game.getView().positionKey;
      const base = { ...f.payload.meta, snapshot: new Uint8Array(f.payload.snapshot), limits: f.payload.limits, seed: f.payload.seed };
      const candidates = [
        { ...base, seed: '18446744073709551616' },
        { ...base, seed: '-1' },
        { ...base, limits: { ...base.limits, simulations: -1 } },
        { ...base, limits: { ...base.limits, simulations: 1.5 } },
        { ...base, limits: { ...base.limits, maxNodes: 0 } },
        { ...base, limits: { ...base.limits, maxDepth: 49 } },
        { ...base, gameEpoch: 0 },
        { ...base, positionKey: '0'.repeat(42) },
        { ...base, snapshot: new Uint8Array([123, 125]) },
      ];
      const rejected = [];
      for (const candidate of candidates) rejected.push(await ai.search(candidate).then(() => false, () => true));
      const valid = await ai.search(base);
      return { rejected, validAction: valid.actionId, keyBefore: key, keyAfter: game.getView().positionKey };
    } finally { ai.dispose(); game.dispose(); }
  }, fixture);
  expect(checks.rejected).toEqual(Array(9).fill(true));
  expect(checks.validAction).toBe(fixture.expected.actionId);
  expect(checks.keyAfter).toBe(checks.keyBefore);
});
