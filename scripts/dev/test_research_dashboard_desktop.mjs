/** Desktop acceptance for stopped renderer fixtures or a bound final file. No server. */
import assert from 'node:assert/strict';
import { readFile, writeFile, realpath } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const options = {};
const tail = process.argv.slice(2);
assert.equal(tail.length % 2, 0, 'Arguments must be explicit name/value pairs');
for (let index = 0; index < tail.length; index += 2) {
  const [name, value] = [tail[index], tail[index + 1]];
  assert.ok(
    [
      '--mode',
      '--html',
      '--expected',
      '--snapshot',
      '--result',
      '--playwright',
      '--chromium',
      '--cases',
    ].includes(name),
  );
  assert.equal(options[name], undefined, 'Duplicate option');
  options[name] = value;
}
const mode = options['--mode'];
assert.ok(['fixture', 'final'].includes(mode));
for (const name of ['--html', '--result', '--playwright', '--chromium'])
  assert.ok(options[name], name);
const html = await realpath(options['--html']);
const fixture = mode === 'fixture';
const expected = fixture ? JSON.parse(await readFile(options['--expected'], 'utf8')) : null;
const snapshot = fixture ? JSON.parse(await readFile(options['--snapshot'], 'utf8')) : null;
const { chromium } = await import(pathToFileURL(options['--playwright']).href);
const browserErrors = [];
const externalRequests = [];
const requests = [];
const completed = [];
const cleanupErrors = [];
const started = new Date().toISOString();
let browser;
let context;
let page;
let primary;
const selected = options['--cases']?.split(',');
const fixtureCases = [
  'layout',
  'activity',
  'primary-history',
  'keyboard-close',
  'filter-scroll',
  'time-reload',
  'translation-security',
  'closed-task-live-job',
  'secondary-pause',
];
const finalCases = ['final-layout-dialog', 'final-time-security-reload'];
const cases = fixture ? fixtureCases : finalCases;
assert.ok(
  !selected || selected.every((name) => cases.includes(name)),
  'Only named unfinished cases may be selected',
);

async function check(name, action) {
  if (!cases.includes(name) || (selected && !selected.includes(name))) return;
  await page.goto(pathToFileURL(html).href, {
    waitUntil: 'load',
    timeout: 10000,
  });
  await action();
  completed.push(name);
}
const rows = () => page.getByRole('button').and(page.locator('[aria-haspopup="dialog"]'));
const cells = (row) => row.locator(':scope > *');
const ownerRow = (name) => rows().filter({ hasText: name });
const search = () =>
  page
    .getByRole('searchbox', { name: /検索|search/i })
    .or(page.getByRole('textbox', { name: /検索|search/i }));
const waitFilter = () => page.getByRole('checkbox', { name: /待|wait/i });
const closeButton = (dialog) => dialog.getByRole('button', { name: /閉|close/i });
async function countVisibleRows() {
  let count = 0;
  for (const row of await rows().all()) if (await row.isVisible()) count += 1;
  return count;
}
async function open(row, key) {
  assert.equal(await row.count(), 1, 'One accessible row per session');
  if (key) {
    await row.focus();
    await page.keyboard.press(key);
  } else await row.click();
  const dialog = page.getByRole('dialog');
  await dialog.waitFor({ state: 'visible' });
  const label = await dialog.getAttribute('aria-label');
  const labelledBy = await dialog.getAttribute('aria-labelledby');
  assert.ok(label?.trim() || labelledBy?.trim(), 'Dialog needs an accessible name');
  if (labelledBy) {
    assert.ok(
      await page.evaluate(
        (ids) => ids.split(/\s+/).every((id) => document.getElementById(id)?.textContent.trim()),
        labelledBy,
      ),
    );
  }
  assert.ok(
    await dialog.evaluate((node) => node.contains(document.activeElement)),
    'Focus enters dialog',
  );
  assert.equal(await closeButton(dialog).count(), 1, 'A visible accessible close button');
  assert.equal(await closeButton(dialog).isVisible(), true);
  return dialog;
}
async function originals(dialog) {
  for (const summary of await dialog.locator('details > summary').all()) {
    if ((await summary.isVisible()) && !(await summary.evaluate((node) => node.parentElement.open)))
      await summary.click();
  }
}
async function fullText(dialog, value) {
  const text = await dialog.innerText();
  const values = await dialog
    .locator('input[readonly], textarea[readonly]')
    .evaluateAll((nodes) => nodes.map((node) => node.value).join('\n'));
  assert.ok(
    (text + '\n' + values).includes(value),
    'Detail exposes full literal: ' + value.slice(0, 80),
  );
}
async function noOverflow() {
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1),
    false,
    'Desktop has no horizontal overflow',
  );
}
async function security() {
  assert.equal(await page.evaluate(() => globalThis.DESKTOP_INJECTED), undefined);
  assert.equal(await page.locator('img, iframe, object, embed').count(), 0);
  assert.deepEqual(browserErrors, []);
  assert.deepEqual(externalRequests, [], 'No attempted external requests');
  assert.ok(
    requests.every((url) => url === pathToFileURL(html).href),
    'Only this file may be requested',
  );
}

try {
  browser = await chromium.launch({
    executablePath: options['--chromium'],
    headless: true,
    timeout: 15000,
    args: ['--disable-gpu', '--disable-background-networking'],
  });
  context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    offline: true,
    serviceWorkers: 'block',
  });
  await context.route(/^(https?|wss?):/, async (route) => {
    externalRequests.push(route.request().url());
    await route.abort();
  });
  context.on('request', (request) => {
    requests.push(request.url());
    if (/^(https?|wss?):/.test(request.url())) externalRequests.push(request.url());
  });
  if (fixture)
    await context.addInitScript(
      ({ now }) => {
        const Original = Date;
        class FixtureDate extends Original {
          constructor(...args) {
            super(...(args.length ? args : [now]));
          }
          static now() {
            return now;
          }
        }
        globalThis.Date = FixtureDate;
      },
      { now: Date.parse(expected.fixed_browser_now) },
    );
  page = await context.newPage();
  page.setDefaultTimeout(3000);
  page.on('pageerror', (error) => browserErrors.push(String(error)));

  await check('layout', async () => {
    const columns = await rows()
      .first()
      .evaluate((row) => getComputedStyle(row).gridTemplateColumns.split(/\s+/).filter(Boolean));
    assert.equal(columns.length, 4, 'Exactly four desktop columns');
    assert.equal(await countVisibleRows(), expected.groups, 'One row per session');
    const row = ownerRow(expected.multi_owner_marker);
    assert.equal(await cells(row).count(), 4);
    const box = await row.boundingBox();
    assert.ok(box.height <= 88, 'A compact row, not a multi-paragraph issue list');
    const ellipsis = await row.locator('*').evaluateAll(
      (nodes) =>
        nodes.filter((node) => {
          const style = getComputedStyle(node);
          return (
            style.textOverflow === 'ellipsis' &&
            style.whiteSpace === 'nowrap' &&
            node.scrollWidth > node.clientWidth
          );
        }).length,
    );
    assert.ok(ellipsis >= 2, 'Long current/next text uses actual single-line ellipsis');
    await noOverflow();
    await page.setViewportSize({ width: 1440, height: 900 });
    await noOverflow();
    await page.setViewportSize({ width: 1280, height: 800 });
  });
  await check('activity', async () => {
    for (const [name, state] of Object.entries(expected.state_rows)) {
      const text = await cells(ownerRow(name)).nth(1).innerText();
      assert.match(text, new RegExp(state.positive, 'i'), name);
      assert.doesNotMatch(text, new RegExp(state.negative, 'i'), name);
    }
    const idle = await open(ownerRow('Confirmed runtime session'));
    assert.match(
      await idle.innerText(),
      /LLM.*(idle|待機)/i,
      'Idle LLM and confirmed computation must coexist',
    );
    await closeButton(idle).click();
  });
  await check('primary-history', async () => {
    const row = ownerRow(expected.multi_owner_marker);
    const primaryText = await cells(row).nth(2).innerText();
    assert.match(primaryText, /CURRENT TASK/);
    assert.doesNotMatch(primaryText, /HISTORICAL TITLE|SECOND UNRESOLVED TASK/);
    const dialog = await open(row);
    assert.match(
      await dialog.innerText(),
      /(?:未完了|unresolved)[^\n]*2|2[^\n]*(?:未完了|unresolved)/i,
      'Two unresolved tasks remain discoverable',
    );
    await originals(dialog);
    for (const id of [expected.current_id, expected.secondary_id, expected.history_id])
      await fullText(dialog, id);
    const current = snapshot.groups
      .flatMap((group) => group.issues)
      .find((issue) => issue.id === expected.current_id);
    for (const field of ['title', 'stage', 'next_action', 'wait_reason'])
      await fullText(dialog, current[field]);
    await fullText(dialog, current.evidence_paths[0]);
    await fullText(dialog, 'fixture-reviewer');
    await fullText(dialog, 'failed');
    const detailText = await dialog.innerText();
    assert.match(detailText, /履歴|history|完了済/i, 'History is separate');
    assert.match(detailText, /原文|English/i, 'Original source text is discoverable');
    assert.ok(
      detailText.indexOf(expected.current_id) < detailText.indexOf(expected.history_id),
      'Current precedes completed history',
    );
    await closeButton(dialog).click();
  });
  await check('keyboard-close', async () => {
    const row = ownerRow('Source-only session');
    for (const key of ['Enter', 'Space']) {
      const dialog = await open(row, key);
      if (key === 'Enter') await page.keyboard.press('Escape');
      else await closeButton(dialog).click();
      await dialog.waitFor({ state: 'hidden' });
      assert.ok(
        await row.evaluate(
          (node) => node === document.activeElement || node.contains(document.activeElement),
        ),
        'Close returns focus to originating row',
      );
    }
  });
  await check('filter-scroll', async () => {
    await search().fill('デスクトップ検証');
    await waitFilter().check();
    assert.equal(
      await countVisibleRows(),
      snapshot.groups.filter((group) => group.issues.some((issue) => issue.waiting)).length,
    );
    const row = ownerRow(expected.multi_owner_marker);
    await row.scrollIntoViewIfNeeded();
    const before = await page.evaluate(() => window.scrollY);
    assert.ok(before > 0, 'Fixture exercises real page scrolling');
    const dialog = await open(row);
    await closeButton(dialog).click();
    assert.equal(await search().inputValue(), 'デスクトップ検証');
    assert.equal(await waitFilter().isChecked(), true);
    assert.ok(
      Math.abs((await page.evaluate(() => window.scrollY)) - before) <= 2,
      'Closing preserves scroll',
    );
    await waitFilter().uncheck();
    await search().fill('fixture-secondary');
    assert.equal(await countVisibleRows(), 1, 'Secondary issue is searchable');
    await search().fill('NO-SUCH-DESKTOP-FIXTURE');
    assert.equal(await countVisibleRows(), 0);
    assert.match(await page.locator('body').innerText(), /該当|一致|見つか|no.*match|empty/i);
  });
  await check('time-reload', async () => {
    const text = await page.locator('body').innerText();
    assert.match(text, /生成|generated/i);
    assert.match(text, /経過|生成から|elapsed|age|前/i);
    assert.match(text, /古|stale|静的|snapshot|スナップショット/i);
    assert.match(text, /手動|manual|research-dashboard\.py/i);
    assert.match(text, /2\s*時間|120\s*分|7200|2\s*h|120\s*m/i, 'Fixed snapshot age is two hours');
    const before = await page.locator('script[type="application/json"]').textContent();
    await Promise.all([
      page.waitForEvent('load'),
      page.getByRole('button', { name: /再読込|再読み込み|reload/i }).click(),
    ]);
    assert.equal(
      await page.locator('script[type="application/json"]').textContent(),
      before,
      'Reload only reads the existing static file',
    );
    assert.equal(page.url(), pathToFileURL(html).href);
  });
  await check('translation-security', async () => {
    assert.match(
      await page
        .getByRole('status')
        .filter({ hasText: /翻訳待ち|translation.*pending/i })
        .innerText(),
      /更新待ち|翻訳待ち|日本語.*待|translation.*pending/i,
    );
    assert.doesNotMatch(await page.locator('body').innerText(), /STALE JAPANESE MUST NOT APPEAR/);
    const unknown = await open(ownerRow('Unknown session'));
    await originals(unknown);
    await fullText(unknown, 'No verified runtime evidence');
    await closeButton(unknown).click();
    const hostile = await open(ownerRow(expected.multi_owner_marker));
    await originals(hostile);
    await fullText(hostile, expected.hostile);
    await security();
    const embedded = JSON.parse(
      await page.locator('script[type="application/json"]').textContent(),
    );
    assert.deepEqual(embedded.groups, snapshot.groups, 'English canonical inputs are unchanged');
  });
  await check('closed-task-live-job', async () => {
    const row = ownerRow('Closed-task live-job session');
    assert.match(
      await cells(row).nth(1).innerText(),
      /計算.*確認|confirmed.*(job|running)|running/i,
      'Confirmed computation remains visible despite administrative closure',
    );
    assert.doesNotMatch(
      await cells(row).nth(2).innerText(),
      /CLOSED TASK WITH LIVE CHILD/,
      'Closed task stays in history rather than becoming the current task',
    );
    const dialog = await open(row);
    await originals(dialog);
    await fullText(dialog, 'fixture-closed-live');
    assert.match(await dialog.innerText(), /履歴|history/i);
    assert.match(await dialog.innerText(), /LLM.*(未読|notLoaded|not loaded|未ロード)/i);
    await closeButton(dialog).click();
  });
  await check('secondary-pause', async () => {
    const dialog = await open(ownerRow(expected.multi_owner_marker));
    await originals(dialog);
    const task = dialog.locator('article').filter({ hasText: 'fixture-secondary-paused' });
    assert.equal(await task.count(), 1);
    const directText = await task.evaluate((node) => {
      const copy = node.cloneNode(true);
      copy.querySelectorAll('details').forEach((detail) => detail.remove());
      return copy.textContent;
    });
    assert.match(
      directText,
      /人間.*一時停止|ユーザー.*停止|明示.*停止|paused by (user|human)/i,
      'Secondary explicit pause is visible without expanding raw originals',
    );
    assert.match(directText, /依存|dependency/i, 'Supplied wait kind is retained alongside pause');
    await closeButton(dialog).click();
  });
  await check('final-layout-dialog', async () => {
    assert.equal(
      await rows()
        .first()
        .evaluate(
          (row) => getComputedStyle(row).gridTemplateColumns.split(/\s+/).filter(Boolean).length,
        ),
      4,
    );
    const count = await countVisibleRows();
    assert.ok(count > 0, 'Actual generated HTML has session rows');
    await noOverflow();
    const row = rows().first();
    const dialog = await open(row, 'Enter');
    assert.match(await dialog.innerText(), /現在|現状|current|状況/i);
    await page.keyboard.press('Escape');
    await dialog.waitFor({ state: 'hidden' });
    assert.ok(
      await row.evaluate(
        (node) => node === document.activeElement || node.contains(document.activeElement),
      ),
    );
  });
  await check('final-time-security-reload', async () => {
    const text = await page.locator('body').innerText();
    assert.match(text, /生成|generated/i);
    assert.match(text, /経過|生成から|elapsed|age|前/i);
    assert.match(text, /手動|manual|research-dashboard\.py/i);
    await security();
    const before = await page.locator('script[type="application/json"]').textContent();
    await Promise.all([
      page.waitForEvent('load'),
      page.getByRole('button', { name: /再読込|再読み込み|reload/i }).click(),
    ]);
    assert.equal(await page.locator('script[type="application/json"]').textContent(), before);
    await security();
  });
} catch (error) {
  primary = error;
} finally {
  for (const [name, object] of [
    ['context', context],
    ['browser', browser],
  ]) {
    try {
      if (object) await object.close();
    } catch (error) {
      cleanupErrors.push({ name, error: String(error) });
    }
  }
  const result = {
    mode,
    started,
    stopped: new Date().toISOString(),
    completed,
    unrun: cases.filter(
      (name) => !completed.includes(name) && (!selected || selected.includes(name)),
    ),
    outcome: primary || cleanupErrors.length ? 'FAIL' : 'PASS',
    primary: primary?.stack ?? null,
    cleanupErrors,
    contextClosed: Boolean(context) && !cleanupErrors.some((e) => e.name === 'context'),
    browserClosed: Boolean(browser) && !cleanupErrors.some((e) => e.name === 'browser'),
    requests,
    externalRequests,
    browserErrors,
    viewport: 'desktop1280x800/1440x900 only',
    modelCalls: 0,
  };
  await writeFile(options['--result'], JSON.stringify(result, null, 2) + '\n', {
    flag: 'wx',
  });
  console.log(JSON.stringify(result));
}
if (primary) throw primary;
assert.deepEqual(cleanupErrors, []);
