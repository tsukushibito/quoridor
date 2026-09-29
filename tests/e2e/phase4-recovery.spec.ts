import { expect, test, type Page } from '@playwright/test';

async function state(page: Page) { return page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state()); }
async function clickCell(page: Page, cell: number): Promise<void> {
  await page.locator('#board canvas').evaluate(element => element.scrollIntoView({ block: 'center' }));
  const point = await page.evaluate(id => window.__QUORIDOR_APP_TEST_API__!.projectCell(id), cell);
  await page.mouse.click(point.x, point.y); await page.mouse.click(point.x, point.y);
}
async function ready(page: Page): Promise<void> {
  await page.goto('./?forceWebGL=1');
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
}

test('controlled renderer and rules startup failures recover through visible UI', async ({ page }) => {
  const unexpected: string[] = []; page.on('pageerror', error => unexpected.push(error.message));
  await page.goto('./?forceWebGL=1&testRenderStartupFailure=1');
  await expect(page.locator('#fault-title')).toHaveText('描画を停止しました');
  expect(await page.locator('#board canvas').count()).toBe(0);
  await page.getByRole('button', { name: '描画を再試行' }).click();
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  expect(await page.locator('#board canvas').count()).toBe(1);
  await clickCell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  await page.evaluate(() => localStorage.clear());
  await page.goto('./?forceWebGL=1&testRulesStartupFailure=1');
  await expect(page.locator('#fault-title')).toHaveText('ルールエンジンを開始できません');
  expect((await state(page)).view).toBeNull();
  await page.getByRole('button', { name: '対局の開始を再試行' }).click();
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  expect(await page.locator('#board canvas').count()).toBe(1);
  expect(unexpected).toEqual([]);
});

test('device-loss and backend/runtime fault handlers preserve committed play and rebuild one renderer', async ({ page }) => {
  const unexpected: string[] = []; page.on('pageerror', error => unexpected.push(error.message));
  await ready(page);
  await clickCell(page, 13);
  const before = await state(page);
  expect(before.view?.ply).toBe(1);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('deviceLost'));
  await expect(page.locator('#fault-title')).toHaveText('描画を停止しました');
  expect(await page.locator('#board canvas').count()).toBe(0);
  expect((await state(page)).view?.positionKey).toBe(before.view?.positionKey);
  await page.getByRole('button', { name: '描画を再試行' }).click();
  await expect(page.locator('#board canvas')).toHaveCount(1);
  expect((await state(page)).view?.positionKey).toBe(before.view?.positionKey);
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  await page.getByRole('button', { name: '壁を置く' }).click();
  const wall = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectWall(27));
  await page.mouse.click(wall.x, wall.y); await page.mouse.click(wall.x, wall.y);
  const placed = await state(page);
  expect(placed.view?.horizontalWalls).toContain(27);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('backendError'));
  await page.getByRole('button', { name: '描画を再試行' }).click();
  await expect(page.locator('#board canvas')).toHaveCount(1);
  expect((await state(page)).view?.positionKey).toBe(placed.view?.positionKey);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().staticWalls)).toBe(1);
  await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('renderError'));
  await page.getByRole('button', { name: '描画を再試行' }).click();
  await expect(page.locator('#board canvas')).toHaveCount(1);
  expect((await state(page)).view?.ply).toBe(2);
  await page.getByRole('button', { name: '1手戻す' }).click();
  expect((await state(page)).view?.ply).toBe(1);
  expect(unexpected).toEqual([]);
});

test('AI build mismatch shows reload guidance and PvP takeover keeps the Rust game', async ({ page }) => {
  const unexpected: string[] = []; page.on('pageerror', error => unexpected.push(error.message));
  await page.addInitScript(() => {
    class WrongBuildWorker {
      onmessage: ((event: MessageEvent<unknown>) => void) | null = null;
      onerror: ((event: ErrorEvent) => void) | null = null;
      onmessageerror: (() => void) | null = null;
      postMessage(value: unknown): void {
        if (typeof value === 'object' && value !== null && 'type' in value && value.type === 'init') {
          const request = value as { protocolVersion: number; workerGeneration: number };
          setTimeout(() => this.onmessage?.({ data: { type: 'ready', protocolVersion: request.protocolVersion,
            engineBuildId: 'wrong-wasm-build', workerGeneration: request.workerGeneration } } as MessageEvent<unknown>), 0);
        }
      }
      terminate(): void {}
    }
    window.Worker = WrongBuildWorker as unknown as typeof Worker;
  });
  await ready(page);
  const key = (await state(page)).view?.positionKey;
  await page.locator('#match-mode').selectOption('ai');
  await page.locator('#human-side').selectOption('1');
  await page.getByRole('button', { name: '新しい対局' }).click();
  await expect.poll(() => state(page).then(x => x.phase)).toBe('recoverableError');
  await expect(page.locator('#fault-title')).toHaveText('AIの版が一致しません');
  expect((await state(page)).view?.positionKey).toBe(key);
  await page.getByRole('button', { name: 'AIを再試行' }).click();
  await expect.poll(() => state(page).then(x => x.phase)).toBe('recoverableError');
  await page.getByRole('button', { name: '2人対戦に切り替える' }).click();
  expect((await state(page)).matchMode).toBe('pvp');
  expect((await state(page)).phase).toBe('humanTurn');
  await clickCell(page, 13);
  expect((await state(page)).view?.ply).toBe(1);
  expect(unexpected).toEqual([]);
});

test('invalid replay restore leaves live view, epoch, revision, selection, and saved slot intact', async ({ page }) => {
  await ready(page);
  const point = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.projectCell(13));
  await page.mouse.click(point.x, point.y);
  const before = await state(page);
  expect(before.selectedId).toBe(13);
  const save = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.exportReplay());
  const raw = await page.evaluate(() => localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY));
  await expect(page.evaluate(async replay => window.__QUORIDOR_APP_TEST_API__!.restoreReplay({ ...replay,
    actions: [999], ply: 1 }, 'pvp', 0), save)).rejects.toThrow();
  await expect(page.evaluate(async replay => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(replay, 'pvp', 1), save)).rejects.toThrow();
  const after = await state(page);
  expect(after.view?.positionKey).toBe(before.view?.positionKey);
  expect(after.gameEpoch).toBe(before.gameEpoch);
  expect(after.revision).toBe(before.revision);
  expect(after.selectedId).toBe(before.selectedId);
  expect(await page.evaluate(() => localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__!.GAME_KEY))).toBe(raw);
  await page.keyboard.press('Enter');
  expect((await state(page)).view?.ply).toBe(1);
});

test('repeated new/restore operations keep one canvas and terminal AI replay resumes without search', async ({ page }) => {
  await ready(page);
  const save = await page.evaluate(async () => {
    const rules = await window.__QUORIDOR_RULES_TEST_API__!.createGame();
    try {
      for (let move = 0; move < 8; move++) {
        rules.applyAction(13 + move * 9);
        if (move < 7) rules.applyAction(move % 2 === 0 ? 75 : 76);
      }
      return rules.exportReplay();
    } finally { rules.dispose(); }
  });
  await page.evaluate(async replay => window.__QUORIDOR_APP_TEST_API__!.restoreReplay(replay, 'ai', 0), save);
  expect((await state(page)).phase).toBe('finished');
  await page.reload();
  await page.getByRole('button', { name: '前の対局を再開' }).click();
  expect((await state(page)).phase).toBe('finished');
  expect((await state(page)).view?.winner).toBe(0);
  const generation = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.aiDiagnostics().slices.length);
  await page.waitForTimeout(250);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.aiDiagnostics().slices.length)).toBe(generation);
  await page.getByRole('button', { name: '新しい対局' }).dblclick();
  await expect.poll(() => state(page).then(x => x.phase)).toBe('humanTurn');
  expect(await page.locator('#board canvas').count()).toBe(1);
  expect((await state(page)).view?.ply).toBe(0);
});

test('blocked localStorage getter does not prevent keyboard play', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'localStorage', {
    configurable: true, get() { throw new Error('storage denied'); },
  }));
  await ready(page);
  await expect(page.locator('#save-status')).toContainText('使えません');
  await page.locator('#board canvas').focus();
  await page.keyboard.press('ArrowDown');
  expect((await state(page)).selectedId).toBe(13);
  await page.keyboard.press('Enter');
  expect((await state(page)).view?.ply).toBe(1);
});

test('concurrent new/restore uses the last replacement and invalid options leave AI request live', async ({ page }) => {
  await ready(page);
  const result = await page.evaluate(async () => {
    const Controller = window.__QUORIDOR_SESSION_TEST_API__!.SessionController;
    const AiClient = window.__QUORIDOR_RULES_TEST_API__!.AiClient;
    type Reply = Awaited<ReturnType<InstanceType<typeof AiClient>['search']>>;
    class WaitingAi extends AiClient {
      resolveReply: ((reply: Reply) => void) | null = null;
      cancellations = 0;
      override search(): Promise<Reply> { return new Promise(resolve => { this.resolveReply = resolve; }); }
      override cancel(): void { this.cancellations++; }
    }
    const pvp = new Controller();
    const ai = new WaitingAi();
    const thinking = new Controller(ai);
    try {
      await pvp.newGame({ mode: 'pvp' });
      const initial = pvp.state;
      const transition = pvp.apply(13, initial.gameEpoch, initial.revision)!;
      pvp.finish(transition.gameEpoch, transition.revision);
      const save = pvp.exportReplay();
      const replacements = await Promise.allSettled([
        pvp.newGame({ mode: 'pvp' }), pvp.newGame({ mode: 'pvp' }),
        pvp.restoreReplay(save, { mode: 'pvp', humanSide: 0, simulations: 96 }),
      ]);
      const finalPvp = { ply: pvp.state.view?.ply, key: pvp.state.view?.positionKey, epoch: pvp.state.gameEpoch };
      await thinking.newGame({ mode: 'ai', humanSide: 1, simulations: 48 });
      const before = { epoch: thinking.state.gameEpoch, revision: thinking.state.revision,
        key: thinking.state.view?.positionKey, phase: thinking.state.phase, cancellations: ai.cancellations };
      const invalidNew = await thinking.newGame({ mode: 'wrong' as never }).then(() => false, () => true);
      const invalidLoad = await thinking.restoreReplay(save, { mode: 'ai', humanSide: 1, simulations: 48 })
        .then(() => false, () => true);
      const unchanged = { epoch: thinking.state.gameEpoch, revision: thinking.state.revision,
        key: thinking.state.view?.positionKey, phase: thinking.state.phase, cancellations: ai.cancellations };
      ai.resolveReply?.({ actionId: 13, stats: { simulations: 1, nodes: 1, edges: 1, arenaBytes: 1,
        highWaterBytes: 1, maxDepthReached: 1, policyFallbacks: 0, valueFallbacks: 0, budgetExhausted: false } });
      await new Promise(resolve => setTimeout(resolve, 0));
      return { replacements: replacements.map(item => item.status), finalPvp, expectedKey: transition.after.positionKey,
        before, unchanged, invalidNew, invalidLoad, aiPly: thinking.state.view?.ply, aiPhase: thinking.state.phase };
    } finally { pvp.dispose(); thinking.dispose(); }
  });
  expect(result.replacements).toEqual(['fulfilled', 'fulfilled', 'fulfilled']);
  expect(result.finalPvp.ply).toBe(1);
  expect(result.finalPvp.key).toBe(result.expectedKey);
  expect(result.finalPvp.epoch).toBeGreaterThan(1);
  expect(result.before.phase).toBe('aiThinking');
  expect(result.invalidNew).toBe(true);
  expect(result.invalidLoad).toBe(true);
  expect(result.unchanged).toEqual(result.before);
  expect(result.aiPly).toBe(1);
  expect(result.aiPhase).toBe('humanTurn');
});
