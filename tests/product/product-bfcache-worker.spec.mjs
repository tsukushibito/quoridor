import { expect, test } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

// One current-product lifecycle check. No synthetic events or research engine.
test.use({
  channel: 'chromium',
  headless: true,
  trace: 'off',
  video: 'off',
  screenshot: 'off',
  launchOptions: {
    ignoreDefaultArgs: ['--disable-back-forward-cache'],
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl'],
  },
});

async function capture(page) {
  return page.evaluate(() => {
    const app = window.__QUORIDOR_APP_TEST_API__;
    const persistence = window.__QUORIDOR_PERSISTENCE_TEST_API__;
    const diagnostics = window.__QUORIDOR_DIAGNOSTICS__;
    if (!app || !persistence || !diagnostics) throw new Error('PRODUCT_HOOKS_UNAVAILABLE');
    const raw = localStorage.getItem(persistence.GAME_KEY);
    const save = raw === null ? null : persistence.validateSavedMatch(JSON.parse(raw));
    return {
      state: app.state(),
      raw,
      save,
      workerReady: diagnostics.workerReady,
      workerGeneration: diagnostics.workerGeneration,
      rulesLoaded: diagnostics.rulesLoaded,
      rendererPhase: diagnostics.phase,
      audio: app.audio(),
      ai: app.aiDiagnostics(),
      renderer: app.resources(),
      canvasCount: document.querySelectorAll('#board canvas').length,
      documentToken: window.__N3L_CACHE_OBSERVATION__?.token,
    };
  });
}

function committed(record) {
  return {
    gameEpoch: record.state.gameEpoch,
    positionKey: record.state.view.positionKey,
    ply: record.state.view.ply,
    matchMode: record.state.matchMode,
    humanSide: record.state.humanSide,
  };
}

function assertConnected(record) {
  expect(record.state.phase).toBe('humanTurn');
  expect(record.state.paused).toBe(false);
  expect(record.state.matchMode).toBe('ai');
  expect(record.state.humanSide).toBe(1);
  expect(record.state.view.ply).toBe(1);
  expect(record.state.view.turn).toBe(1);
  expect(record.state.mode).toBe('move');
  expect(record.rulesLoaded).toBe(true);
  expect(record.workerReady).toBe(true);
  expect(record.workerGeneration).toBeGreaterThan(0);
  expect(record.ai.wasmMemoryBytes).toBeGreaterThan(0);
  // enterTurn deliberately clears state.aiStats; the accepted result retains diagnostics.
  expect(record.state.aiStats).toBeNull();
  expect(record.ai.highWaterBytes).toBeGreaterThan(0);
  expect(record.ai.slices.length).toBeGreaterThan(0);
  expect(record.rendererPhase).toBe('ready');
  expect(record.canvasCount).toBe(1);
  expect(record.audio.status).not.toBe('disposed');
  expect(record.save.replay.positionKey).toBe(record.state.view.positionKey);
  expect(record.save.replay.ply).toBe(record.state.view.ply);
  expect(record.save.match).toEqual({ mode: 'ai', humanSide: 1, simulations: 96 });
}

test('trusted BFCache return preserves connected product Worker-Wasm and controls', async ({
  page,
}, testInfo) => {
  // The single-core SwiftShader setup can consume most of the former 30s limit.
  // Leave time for the unchanged AI work, cache return and failure journal.
  test.setTimeout(90_000);
  const journal = {
    schema: 'quoridor.product-bfcache-worker.v1',
    outcome: 'PARTIAL',
    bundleBinding: process.env.N3L_PRODUCT_BUNDLE_BINDING ?? null,
    expectedWorkerPath: process.env.N3L_PRODUCT_WORKER_PATH ?? null,
    intendedProductAiRequests: 1,
    observedWorkerUrls: [],
    errors: [],
    errorOverflow: false,
    before: null,
    after: null,
    postInput: null,
    cache: null,
    primary: null,
    failureState: null,
    claims:
      'One completed opening AI turn and idle connected Worker across cache; no in-flight cancellation, second search, physical request-count or sound-output proof.',
  };
  let primary;
  const noteError = (message) => {
    if (journal.errors.length < 8) journal.errors.push(String(message).slice(0, 512));
    else journal.errorOverflow = true;
  };
  page.on('pageerror', (error) => noteError(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') noteError(`${message.text()} (${message.location().url})`);
  });
  page.on('worker', (worker) => {
    if (journal.observedWorkerUrls.length < 4)
      journal.observedWorkerUrls.push(worker.url().slice(0, 1024));
    else noteError('WORKER_OBSERVATION_OVERFLOW');
  });
  try {
    if (!/^[0-9a-f]{64}$/.test(journal.bundleBinding ?? ''))
      throw new Error('QUALIFIED_CURRENT_BUNDLE_BINDING_REQUIRED');
    if (!journal.expectedWorkerPath?.startsWith('/assets/'))
      throw new Error('QUALIFIED_CURRENT_WORKER_ASSET_PATH_REQUIRED');
    // An isolated Playwright context supplies empty storage. Never clear a shared profile.
    await page.addInitScript(() => {
      window.__N3L_CACHE_OBSERVATION__ = {
        token: crypto.randomUUID(),
        shows: [],
        hides: [],
        canvas: null,
      };
      window.addEventListener('pageshow', (event) => {
        const observation = window.__N3L_CACHE_OBSERVATION__;
        if (observation.shows.length < 4)
          observation.shows.push({ trusted: event.isTrusted, persisted: event.persisted });
      });
    });
    await page.goto('./?forceWebGL=1');
    await expect(page.locator('#startup-new-game')).toBeEnabled();
    await expect
      .poll(() =>
        page.evaluate(
          () => !!window.__QUORIDOR_APP_TEST_API__ && !!window.__QUORIDOR_PERSISTENCE_TEST_API__,
        ),
      )
      .toBe(true);
    expect(
      await page.evaluate(() =>
        localStorage.getItem(window.__QUORIDOR_PERSISTENCE_TEST_API__.GAME_KEY),
      ),
    ).toBeNull();
    await page.locator('#startup-new-game').click();
    await expect(page.locator('#match-dialog')).toBeVisible();
    await page.locator('#match-mode').selectOption('ai');
    await page.locator('#human-side').selectOption('1');
    // Verify the unchanged default; do not lower work to make a run pass.
    await expect(page.locator('#ai-budget')).toHaveValue('96');
    await page.locator('#dialog-start').click();
    await expect(page.locator('#startup-dialog')).toBeHidden();
    await expect
      .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().phase), {
        timeout: 45_000,
      })
      .toBe('humanTurn');
    await expect
      .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__?.state().view?.ply))
      .toBe(1);
    // The committed save must settle before exact byte comparison across cache.
    await expect
      .poll(() =>
        page.evaluate(() => {
          const p = window.__QUORIDOR_PERSISTENCE_TEST_API__;
          const raw = p && localStorage.getItem(p.GAME_KEY);
          if (!raw) return -1;
          return p.validateSavedMatch(JSON.parse(raw)).replay.ply;
        }),
      )
      .toBe(1);
    journal.before = await capture(page);
    assertConnected(journal.before);
    expect(journal.observedWorkerUrls.length).toBeGreaterThan(0);
    expect(
      journal.observedWorkerUrls.every(
        (url) => new URL(url).pathname === journal.expectedWorkerPath,
      ),
    ).toBe(true);
    expect(journal.before.state.selectedId).toBeNull();
    // Registered after the maintained product handler: observe its actual suspension.
    await page.evaluate(() => {
      const observation = window.__N3L_CACHE_OBSERVATION__;
      observation.canvas = document.querySelector('#board canvas');
      window.addEventListener('pagehide', (event) => {
        if (observation.hides.length >= 4) return;
        const app = window.__QUORIDOR_APP_TEST_API__;
        const diagnostics = window.__QUORIDOR_DIAGNOSTICS__;
        observation.hides.push({
          trusted: event.isTrusted,
          persisted: event.persisted,
          paused: app.state().paused,
          positionKey: app.state().view?.positionKey,
          workerGeneration: diagnostics.workerGeneration,
          audioStatus: app.audio().status,
        });
      });
    });
    await page.goto('./assets/ui/quoridor-title-logo.png');
    // A restored cached document does not issue a new load event. Observe the
    // real history commit, then the trusted pageshow that proves restoration.
    await page.goBack({ waitUntil: 'commit', timeout: 15_000 });
    await expect
      .poll(() =>
        page.evaluate((token) => {
          const observation = window.__N3L_CACHE_OBSERVATION__;
          return (
            !!observation?.shows.length &&
            (observation.token !== token || observation.shows.at(-1)?.persisted)
          );
        }, journal.before.documentToken),
      )
      .toBe(true);
    journal.cache = await page.evaluate(() => {
      const observation = window.__N3L_CACHE_OBSERVATION__;
      return {
        token: observation?.token,
        shows: observation?.shows ?? [],
        hides: observation?.hides ?? [],
        sameCanvas: observation?.canvas === document.querySelector('#board canvas'),
      };
    });
    const show = journal.cache.shows.at(-1);
    const hide = journal.cache.hides.at(-1);
    if (
      journal.cache.token !== journal.before.documentToken ||
      !show?.trusted ||
      !show.persisted ||
      !hide?.trusted ||
      !hide.persisted
    ) {
      journal.outcome = 'UNKNOWN_BFCACHE_UNAVAILABLE';
      throw new Error('TRUE_TRUSTED_SAME_DOCUMENT_BFCACHE_RETURN_NOT_OBSERVED');
    }
    expect(hide.paused).toBe(true);
    expect(hide.positionKey).toBe(journal.before.state.view.positionKey);
    expect(hide.workerGeneration).toBe(journal.before.workerGeneration);
    expect(hide.audioStatus).not.toBe('disposed');
    await expect
      .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__.state().paused))
      .toBe(false);
    journal.after = await capture(page);
    assertConnected(journal.after);
    expect(committed(journal.after)).toEqual(committed(journal.before));
    expect(journal.after.raw).toBe(journal.before.raw);
    expect(journal.after.workerGeneration).toBe(journal.before.workerGeneration);
    expect(journal.after.ai).toEqual(journal.before.ai);
    expect(journal.cache.sameCanvas).toBe(true);
    expect(journal.observedWorkerUrls.length).toBeGreaterThan(0);
    expect(
      journal.observedWorkerUrls.every(
        (url) => new URL(url).pathname === journal.expectedWorkerPath,
      ),
    ).toBe(true);
    // Actual keyboard selection exercises retained input; no Enter/commit/second AI request.
    await page.locator('#board canvas').focus();
    await page.keyboard.press('ArrowUp');
    const selected = (await capture(page)).state.selectedId;
    const pawn = journal.before.state.view.pawns[1];
    expect(selected).toBe(Math.max(0, Math.floor(pawn / 9) - 1) * 9 + (pawn % 9));
    await page.locator('#open-menu').click();
    await expect(page.locator('#menu-dialog')).toBeVisible();
    await page.locator('#save-now').click();
    await page.locator('#close-menu').click();
    await expect
      .poll(() => page.evaluate(() => window.__QUORIDOR_APP_TEST_API__.state().paused))
      .toBe(false);
    journal.postInput = await capture(page);
    assertConnected(journal.postInput);
    expect(committed(journal.postInput)).toEqual(committed(journal.before));
    expect(journal.postInput.raw).toBe(journal.before.raw);
    expect(journal.postInput.workerGeneration).toBe(journal.before.workerGeneration);
    expect(journal.observedWorkerUrls.length).toBeGreaterThan(0);
    expect(
      journal.observedWorkerUrls.every(
        (url) => new URL(url).pathname === journal.expectedWorkerPath,
      ),
    ).toBe(true);
    expect(journal.errors).toEqual([]);
    expect(journal.errorOverflow).toBe(false);
    journal.outcome = 'ASSERTIONS_PASS_CLEANUP_PENDING';
  } catch (error) {
    primary = error;
    if (journal.outcome === 'PARTIAL') journal.outcome = 'ASSERTION_OR_SETUP_FAILED';
    journal.primary = String(error?.stack ?? error).slice(0, 4096);
    try {
      journal.failureState = await capture(page);
    } catch (snapshotError) {
      journal.failureState = { unavailable: String(snapshotError).slice(0, 1024) };
    }
  }
  // Full bounded journal on success, UNKNOWN or failure. Attachment failure cannot erase primary.
  try {
    const body = Buffer.from(JSON.stringify(journal, null, 2));
    if (body.length > 262_144) throw new Error('PRODUCT_JOURNAL_BOUND');
    // Framework attachments may be cancelled when a test times out. Preserve
    // the same bounded bytes in the owned raw directory before attaching them.
    writeFileSync(join(process.env.N3L_RAW_DIR, 'product-journal.json'), body, { flag: 'wx' });
    await testInfo.attach('product-bfcache-worker-journal', {
      body,
      contentType: 'application/json',
    });
  } catch (secondary) {
    // Reporter serialization may omit AggregateError.errors; retain both facts in full capture.
    console.error(
      JSON.stringify({
        stage: 'PRODUCT_JOURNAL_FAILURE',
        primary: journal.primary,
        secondary: String(secondary?.stack ?? secondary).slice(0, 4096),
      }),
    );
    if (primary)
      throw new AggregateError([primary, secondary], 'PRODUCT_CHECK_AND_JOURNAL_FAILURE');
    throw secondary;
  }
  if (primary) throw primary;
});
