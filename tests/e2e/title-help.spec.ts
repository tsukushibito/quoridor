import { test, expect, type Page } from '@playwright/test';
const state = (page: Page) => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.state());
async function title(page: Page) {
  await page.goto('./?forceWebGL=1');
  await expect(page.locator('#startup-new-game')).toBeEnabled();
}
async function start(page: Page, mode = 'pvp', side = '0', budget = '96') {
  await page.locator('#startup-new-game').click();
  await page.locator('#match-mode').selectOption(mode);
  if (mode === 'ai') { await page.locator('#human-side').selectOption(side); await page.locator('#ai-budget').selectOption(budget); }
  await page.locator('#dialog-start').click();
  await expect(page.locator('#startup-dialog')).toBeHidden();
}
async function move(page: Page) {
  await page.locator('#board canvas').focus(); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Enter');
}

test('title, shared help, logo and cancel never create or overwrite a game', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await title(page);
  expect((await state(page)).view).toBeNull(); expect((await state(page)).paused).toBe(true);
  expect(await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'))).toBeNull();
  await expect(page.locator('#title-heading img')).toHaveAttribute('alt', 'QUORIDOR');
  expect(await page.locator('#title-heading img').evaluate(e => { const img=e as HTMLImageElement; const canvas=document.createElement('canvas');
    canvas.width=img.naturalWidth; canvas.height=img.naturalHeight; const ctx=canvas.getContext('2d')!; ctx.drawImage(img,0,0);
    return {width:img.naturalWidth,height:img.naturalHeight,alpha:ctx.getImageData(0,0,1,1).data[3]}; })).toEqual({width:2020,height:778,alpha:0});
  expect(await page.locator('.title-logo').evaluate(e=>getComputedStyle(e).animationIterationCount)).toBe('1');
  expect(await page.locator('.title-logo').evaluate(e=>getComputedStyle(e,'::after').animationIterationCount)).toBe('1');
  await page.locator('#title-help').click(); await expect(page.locator('#help-dialog')).toBeVisible();
  await expect(page.locator('#help-dialog')).toContainText('通れる横側へ斜めに');
  await page.keyboard.press('Escape'); await expect(page.locator('#title-help')).toBeFocused();
  await page.locator('#startup-new-game').click(); await page.keyboard.press('Escape');
  await expect(page.locator('#startup-new-game')).toBeFocused();
  expect((await state(page)).view).toBeNull(); expect(await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'))).toBeNull();
  expect(errors).toEqual([]);
});

test('restart confirmation protects save, and title round trip keeps the same game and camera', async ({ page }) => {
  await title(page); await start(page); await move(page);
  await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  const before = await state(page); const saved = await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'));
  await page.locator('#restart-game').click(); await expect(page.locator('#restart-dialog')).toBeVisible();
  expect((await state(page)).paused).toBe(true);
  await page.locator('#restart-cancel').click(); await expect.poll(() => state(page).then(s => s.paused)).toBe(false);
  expect((await state(page)).view?.positionKey).toBe(before.view?.positionKey);
  expect(await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'))).toBe(saved);
  const camera = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera());
  await page.locator('#open-menu').click(); await page.locator('#return-title').click();
  await expect(page.locator('#resume-game-choice')).toHaveText('対局に戻る');
  await expect(page.locator('#resume-game-choice')).toBeFocused();
  await page.locator('#title-help').click(); await page.keyboard.press('Escape');
  expect((await state(page)).paused).toBe(true);
  await page.locator('#resume-game-choice').click();
  const after = await state(page); expect(after.gameEpoch).toBe(before.gameEpoch); expect(after.view?.positionKey).toBe(before.view?.positionKey);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.camera())).toEqual(camera);
  // Live save operations use the same settings action while the title pauses the game.
  await page.locator('#open-menu').click(); await page.locator('#return-title').click();
  await page.locator('#open-menu').click(); await page.locator('#clear-save').click();
  expect(await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'))).toBeNull();
  await page.locator('#close-menu').click(); await page.locator('#resume-game-choice').click();
  await page.locator('#board canvas').focus(); await page.keyboard.press('ArrowUp'); await page.keyboard.press('Enter');
  await expect.poll(() => state(page).then(s=>s.phase)).toBe('humanTurn');
  expect(JSON.parse((await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1')))! ).replay.ply).toBe(2);
  await page.locator('#restart-game').click(); await page.locator('#restart-confirm').click();
  await expect.poll(() => state(page).then(s => s.view?.ply)).toBe(0);
  expect(JSON.parse((await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1')))! ).replay.actions).toEqual([]);
});

test('help freezes an in-flight tween and resumes it exactly once', async ({ page }) => {
  await title(page); await start(page);
  await page.evaluate(() => { const canvas=document.querySelector('#board canvas')! as HTMLElement; canvas.focus();
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    (document.querySelector('#open-help')! as HTMLElement).click(); });
  const before = await state(page); expect(before.phase).toBe('animating'); expect(before.paused).toBe(true);
  await page.waitForTimeout(350);
  const paused = await state(page); expect(paused.phase).toBe('animating'); expect(paused.revision).toBe(before.revision);
  await page.locator('#close-help').click(); await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn');
  expect((await state(page)).view?.ply).toBe(1);
});

test('help cancels AI without an error or stale move, then restarts the same turn', async ({ page }) => {
  test.setTimeout(60_000); // Includes two real 4096-simulation searches.
  await title(page); await start(page,'ai','0','4096');
  await page.locator('#open-menu').click(); await page.locator('.settings summary').click(); await page.locator('#no-animation').check(); await page.locator('#close-menu').click();
  await page.evaluate(() => { const canvas=document.querySelector('#board canvas')! as HTMLElement; canvas.focus();
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
    (document.querySelector('#open-help')! as HTMLElement).click(); });
  const before = await state(page); expect(before.phase).toBe('aiThinking'); expect(before.paused).toBe(true);
  await page.waitForTimeout(500); const paused = await state(page); expect(paused.view?.positionKey).toBe(before.view?.positionKey); expect(paused.phase).toBe('aiThinking');
  await page.locator('#close-help').click(); await expect.poll(() => state(page).then(s => s.view?.ply), {timeout:20000}).toBe(2);
  await expect.poll(() => state(page).then(s => s.phase)).toBe('humanTurn'); expect((await state(page)).paused).toBe(false);
});

test('saved game resumes from title; corrupt save survives help and cancelled new match', async ({ page }) => {
  test.setTimeout(60_000);
  await title(page); await start(page); await move(page); await expect.poll(() => state(page).then(s=>s.phase)).toBe('humanTurn');
  const key=(await state(page)).view?.positionKey;
  await page.reload(); await expect(page.locator('#resume-game-choice')).toBeEnabled();
  await page.locator('#resume-game-choice').click(); expect((await state(page)).view?.positionKey).toBe(key);
  await page.evaluate(()=>localStorage.setItem('quoridor.m1.game.v1','bad-save')); await page.reload();
  await expect(page.locator('#startup-message')).toContainText('読み込めません'); await expect(page.locator('#resume-game-choice')).toBeHidden();
  await page.locator('#title-help').click(); await page.keyboard.press('Escape'); await page.locator('#startup-new-game').click(); await page.keyboard.press('Escape');
  expect(await page.evaluate(()=>localStorage.getItem('quoridor.m1.game.v1'))).toBe('bad-save');
});

test('logo fallback and both reduced motion settings keep title usable', async ({ page }) => {
  await page.route('**/quoridor-title-logo.png', route=>route.abort()); await title(page);
  await expect(page.locator('.logo-fallback')).toBeVisible();
  await page.emulateMedia({reducedMotion:'reduce'});
  expect(await page.locator('.title-logo').evaluate(e=>getComputedStyle(e).animationName)).toBe('none');
  await page.emulateMedia({reducedMotion:'no-preference'}); await page.locator('#open-menu').click(); await page.locator('.settings summary').click(); await page.locator('#no-animation').check(); await page.locator('#close-menu').click();
  expect(await page.locator('.title-logo').evaluate(e=>getComputedStyle(e).animationName)).toBe('none');
  await start(page); await expect(page.locator('#turn-heading')).toContainText('先手');
});

test('renderer failure during help leaves recovery reachable and keeps the game', async ({ page }) => {
  await title(page); await start(page); const key=(await state(page)).view?.positionKey;
  await page.locator('#open-help').click(); await page.evaluate(()=>window.__QUORIDOR_APP_TEST_API__!.injectRenderFault('renderError'));
  await expect(page.locator('#help-dialog')).toBeHidden(); await expect(page.locator('#retry-renderer')).toBeFocused();
  await page.locator('#retry-renderer').click(); await expect(page.locator('#fault-panel')).toBeHidden();
  expect((await state(page)).view?.positionKey).toBe(key); expect((await state(page)).paused).toBe(false);
});


test('title settings share environments and music; help keeps one BGM without creating a game', async ({ page }) => {
  test.setTimeout(60_000);
  await title(page); await page.locator('#open-menu').click();
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.audio().status)).toBe('ready');
  if (!await page.locator('#environment-select').isVisible()) await page.locator('.settings summary').click();
  await page.locator('#environment-select').selectOption('forest');
  await expect.poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().activeEnvironment), {timeout:20000}).toBe('forest');
  await page.locator('#close-menu').click();
  expect((await state(page)).view).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('quoridor.m1.game.v1'))).toBeNull();
  const audio = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.audio());
  expect(audio.activeBgm).toBe(1);
  await page.locator('#title-help').click(); await page.waitForTimeout(300); await page.keyboard.press('Escape');
  const after = await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.audio());
  expect(after.activeBgm).toBe(1); expect(after.counts.bgm).toBe(audio.counts.bgm);
  await start(page);
  expect(await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.resources().activeEnvironment)).toBe('forest');
  expect((await page.evaluate(() => window.__QUORIDOR_APP_TEST_API__!.audio())).counts.bgm).toBe(audio.counts.bgm);
});
