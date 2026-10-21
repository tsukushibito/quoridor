import test from 'node:test';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { loadTs } from '../../../../tests/unit/ts-fixture.mjs';

class RulesBridgeError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}
const strings = await loadTs(
  new URL('../../../../apps/web/src/games/quoridor/ui/strings.ts', import.meta.url),
  {},
);
const { MatchUiController, installPageLifecycle } = await loadTs(
  new URL('../../../../apps/web/src/games/quoridor/ui/match-controller.ts', import.meta.url),
  {
    '@quoridor/engine-bridge': { RulesBridgeError },
    '../persistence/local-state': { makeSavedMatch: (replay, match) => ({ replay, match }) },
    './strings': strings,
  },
);
const save = { replay: { ply: 3 }, match: { mode: 'pvp', humanSide: 0, simulations: 96 } };
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
function fixture(read = { status: 'ok', value: save }) {
  const events = [],
    writes = [];
  const element = () => ({
    open: false,
    textContent: '',
    focus() {
      events.push('focus');
    },
    showModal() {
      this.open = true;
    },
    close() {
      this.open = false;
    },
  });
  const dialogs = Object.fromEntries(
    [
      'match',
      'menu',
      'help',
      'restart',
      'result',
      'note',
      'start',
      'startupNew',
      'newGame',
      'openMenu',
    ].map((name) => [name, element()]),
  );
  const session = {
    state: {
      view: null,
      gameEpoch: 1,
      revision: 0,
      mode: 'pvp',
      humanSide: 0,
      simulations: 96,
      phase: 'booting',
      paused: true,
    },
    async newGame() {
      this.state = {
        ...this.state,
        view: { ply: 0 },
        phase: 'humanTurn',
        revision: this.state.revision + 1,
      };
    },
    async restoreReplay(replay) {
      this.state = {
        ...this.state,
        view: { ...replay },
        phase: 'humanTurn',
        revision: this.state.revision + 1,
      };
      return this.state.view;
    },
    exportReplay: () => session.state.view,
  };
  const repository = {
    readGame: () => read,
    writeGame: (value) => {
      writes.push(value);
      return { status: 'ok' };
    },
    clearGame: () => ({ status: 'ok' }),
  };
  let failed = false,
    controller;
  const render = {
    available: () => true,
    failed: () => failed,
    changed: () => events.push('render'),
    syncActivity: () => {
      session.state.paused =
        controller.pageSuspended || controller.screen === 'title' || failed || dialogs.help.open;
      events.push(
        session.state.paused ? 'suspend-input-ai-render-audio' : 'resume-input-ai-render-audio',
      );
    },
    beginOperation: () => events.push('begin'),
    beforeNewGame() {},
    syncBoard: (view) => events.push(['board', view.ply]),
    frameMatch: () => events.push('frame'),
    rulesFault: (value) => events.push(['rulesFault', value]),
    focusSave: () => events.push('saveFocus'),
  };
  const ports = { session, repository, dialogs, render, inspectReplay: async () => {} };
  controller = new MatchUiController(ports);
  return {
    controller,
    ports,
    session,
    repository,
    dialogs,
    events,
    writes,
    fault: (value) => {
      failed = value;
    },
  };
}

test('saved startup choice survives renderer recovery and explicit resume adopts the saved game', async () => {
  const f = fixture();
  await f.controller.inspectStored();
  f.controller.openMatchDialog(true);
  assert.equal(f.dialogs.match.open, true);
  assert.equal(f.writes.length, 0);
  f.fault(true);
  f.controller.suspendDialogs();
  f.controller.matchClosed(true);
  assert.equal(f.dialogs.match.open, false);
  assert.equal(f.controller.savedCandidate, save);
  assert.equal(f.controller.gameChoice, 'pending');
  assert.equal(f.controller.screen, 'title');
  assert.equal(f.writes.length, 0);
  f.fault(false);
  f.controller.showStartup();
  await f.controller.restore(save);
  assert.equal(f.controller.screen, 'match');
  assert.equal(f.session.state.view.ply, 3);
  assert.equal(f.controller.savedCandidate, null);
  assert.equal(f.writes.length, 1);
});

test('corrupt data is retained through recovery until explicit new-match acceptance', async () => {
  const f = fixture({ status: 'invalid', reason: 'corrupt fixture' });
  assert.equal(f.controller.gameChoice, 'corrupt');
  assert.equal(f.controller.slotPresent, true);
  f.controller.suspendDialogs();
  f.controller.showStartup();
  f.controller.openMatchDialog(true);
  assert.equal(f.writes.length, 0);
  assert.equal(f.controller.slotPresent, true);
  await f.controller.startNewGame(save.match);
  assert.equal(f.session.state.view.ply, 0);
  assert.equal(f.controller.screen, 'match');
  assert.equal(f.writes.length, 1);
});

test('renderer recovery preserves the scope of an already confirmed restore until its session commits', async () => {
  const f = fixture();
  const pending = deferred();
  f.ports.session.restoreReplay = () => pending.promise;
  const operation = f.controller.restore(save);
  assert.equal(f.controller.busy, true);
  f.fault(true);
  f.controller.suspendDialogs();
  assert.equal(f.controller.busy, true);
  assert.equal(f.controller.savedCandidate, save);
  assert.equal(f.writes.length, 0);
  const view = { ply: 3 };
  f.session.state.view = view;
  f.session.state.phase = 'humanTurn';
  pending.resolve(view);
  await operation;
  assert.equal(f.controller.busy, false);
  assert.equal(f.controller.screen, 'match');
  assert.equal(f.controller.savedCandidate, null);
  assert.equal(f.writes.length, 1);
  assert.equal(f.session.state.paused, true);
  f.fault(false);
  f.ports.render.syncActivity();
  assert.equal(f.session.state.paused, false);
});

test('newer restore wins; old completion and final disposal cannot write UI or storage', async () => {
  const f = fixture();
  const older = deferred();
  f.ports.session.restoreReplay = () => older.promise;
  const first = f.controller.restore(save);
  f.ports.session.restoreReplay = async () => {
    f.session.state.view = { ply: 7 };
    f.session.state.phase = 'humanTurn';
    return f.session.state.view;
  };
  await f.controller.restore(save);
  const adopted = f.events.length,
    written = f.writes.length;
  older.resolve({ ply: 99 });
  await first;
  assert.equal(f.events.length, adopted);
  assert.equal(f.writes.length, written);
  const late = deferred();
  f.ports.session.restoreReplay = () => late.promise;
  const last = f.controller.restore(save);
  f.controller.dispose();
  const stopped = f.events.length;
  late.reject(Error('late failure'));
  await last;
  assert.equal(f.events.length, stopped);
  assert.equal(f.writes.length, written);
});

test('late saved inspection cannot resurrect an explicitly cleared candidate', async () => {
  const f = fixture();
  const pending = deferred();
  f.ports.inspectReplay = () => pending.promise;
  const inspection = f.controller.inspectStored();
  f.controller.clearSave(true);
  pending.reject(new RulesBridgeError('INVALID_REPLAY'));
  await inspection;
  assert.equal(f.controller.gameChoice, 'cleared');
  assert.equal(f.controller.savedCandidate, null);
  assert.equal(f.controller.slotPresent, false);
  assert.equal(f.writes.length, 0);
});

test('rules startup failure exposes recovery without adopting or overwriting the saved game', async () => {
  const f = fixture();
  f.controller.openMatchDialog(true);
  f.ports.render.beforeNewGame = () => {
    throw Error('controlled rules startup');
  };
  await f.controller.startNewGame(save.match);
  assert.equal(f.controller.rulesStartRequested, true);
  assert.equal(f.controller.busy, false);
  assert.equal(f.controller.savedCandidate, save);
  assert.equal(f.dialogs.match.open, false);
  assert.equal(f.writes.length, 0);
  assert.ok(
    f.events.some((event) => Array.isArray(event) && event[0] === 'rulesFault' && event[1]),
  );
});

test('cached page events suspend and restore committed state; final hide disposes once', async () => {
  const f = fixture();
  await f.controller.restore(save);
  const target = new EventTarget(),
    listeners = new AbortController();
  let disposals = 0;
  installPageLifecycle(
    target,
    f.controller,
    () => {
      disposals++;
      f.controller.dispose();
      listeners.abort();
    },
    listeners.signal,
  );
  const dispatch = (name, persisted) => {
    const event = new Event(name);
    Object.defineProperty(event, 'persisted', { value: persisted });
    target.dispatchEvent(event);
  };
  const view = f.session.state.view,
    saved = f.writes.length;
  dispatch('pagehide', true);
  assert.equal(f.controller.pageSuspended, true);
  assert.equal(f.session.state.paused, true);
  assert.equal(disposals, 0);
  dispatch('pageshow', true);
  assert.equal(f.controller.pageSuspended, false);
  assert.equal(f.session.state.paused, false);
  assert.equal(f.session.state.view, view);
  assert.equal(f.writes.length, saved);
  f.dialogs.help.open = true;
  dispatch('pagehide', true);
  dispatch('pageshow', true);
  assert.equal(f.session.state.paused, true);
  dispatch('pagehide', false);
  dispatch('pagehide', false);
  dispatch('pageshow', true);
  assert.equal(disposals, 1);
});

// Execute the actual main renderUi and startup click bindings with DOM/session
// ports. This checks the real disabled assignment, rather than mirroring it.
function actualStartup(f) {
  const events = new Map();
  const element = () => ({
    disabled: false,
    hidden: false,
    value: '',
    open: false,
    style: {},
    dataset: {},
    classList: { toggle() {} },
    setAttribute() {},
    querySelector() {
      return element();
    },
    querySelectorAll() {
      return [];
    },
    focus() {
      f.events.push('focus');
    },
    addEventListener(name, callback) {
      events.set(this, { ...(events.get(this) ?? {}), [name]: callback });
    },
    click() {
      if (!this.disabled) events.get(this)?.click?.();
    },
  });
  const values = {
    players: [element(), element()],
    walls: [element(), element()],
    matchDialog: Object.assign(f.dialogs.match, element()),
    menuDialog: f.dialogs.menu,
    dialogNote: f.dialogs.note,
  };
  const ui = new Proxy(values, {
    get(target, key) {
      return (target[key] ??= element());
    },
  });
  const board = {
    canvas: element(),
    backend: 'webgl2',
    diagnostics: () => ({}),
    setHints() {},
    setPreview() {},
  };
  f.session.aiWorkerState = { ready: false, generation: 0 };
  f.session.canUndo = () => false;
  const ending = new Proxy(
    {},
    {
      get(target, key) {
        return (target[key] ??= element());
      },
    },
  );
  const context = {
    flow: f.controller,
    session: f.session,
    ui,
    board,
    input: null,
    review: { state: { ply: 0, total: 0, phase: 'idle', view: null } },
    endScreen: 'result',
    audio: { setMusicActive() {} },
    diagnostics: {},
    settings: { reducedMotion: false, environmentId: 'forest' },
    disposed: false,
    settingsWarning: '',
    renderFault: null,
    rulesFault: false,
    rendererStarting: false,
    shell: element(),
    statusIsland: element(),
    footer: element(),
    boardCaption: element(),
    modeGroup: element(),
    saveGroup: element(),
    surfaces: {
      help: element(),
      restart: element(),
      helpButton: element(),
      returnTitle: element(),
    },
    ending,
    environmentPreset: () => ({ label: 'fixture' }),
    ja: strings.ja,
    listeners: new AbortController(),
    syncActivity: () => f.ports.render.syncActivity(),
  };
  const source = readFileSync(
    new URL('../../../../apps/web/src/games/quoridor/index.ts', import.meta.url),
    'utf8',
  );
  const render = source.slice(
    source.indexOf('  const renderUi = '),
    source.indexOf('  const onSession = '),
  );
  const ctx = vm.createContext(context);
  const renderUi = vm.runInContext(
    stripTypeScriptTypes(render + '\nrenderUi;', { mode: 'transform' }),
    ctx,
  );
  ctx.renderUi = renderUi;
  f.ports.render.changed = renderUi;
  f.ports.render.syncBoard = (view, focus) => f.events.push(['committed', view.ply, focus]);
  const wiring = source.slice(
    source.indexOf("  ui.matchDialog.addEventListener('close'"),
    source.indexOf('  ui.resume.addEventListener('),
  );
  vm.runInContext(stripTypeScriptTypes(wiring, { mode: 'transform' }), ctx);
  renderUi();
  return { ui, renderUi };
}
const committedView = (ply) => ({ ply, turn: 0, winner: null, wallsRemaining: [10, 10] });
for (const settlement of ['success', 'failure']) {
  for (const clearStatus of ['ok', 'unavailable']) {
    test(`actual startup clear serializes ${clearStatus} against restore ${settlement} and late settlement recovers controls`, async () => {
      const f = fixture(),
        pending = deferred();
      let clears = 0;
      f.repository.clearGame = () => {
        clears++;
        return { status: clearStatus };
      };
      f.ports.session.restoreReplay = () => pending.promise;
      const { ui } = actualStartup(f);
      const operation = f.controller.restore(save);
      assert.equal(ui.startupClear.disabled, true);
      ui.startupClear.click();
      assert.equal(f.controller.clearSave(true), false);
      assert.equal(clears, 0);
      assert.equal(f.controller.savedCandidate, save);
      assert.equal(f.controller.busy, true);
      await f.controller.inspectStored(); // A retry/inspection cannot steal the active operation generation.
      if (settlement === 'success') {
        const view = committedView(3);
        f.session.state.view = view;
        f.session.state.phase = 'humanTurn';
        pending.resolve(view);
      } else pending.reject(Error('late restore failure'));
      await operation;
      assert.equal(f.controller.busy, false);
      assert.equal(ui.startupClear.disabled, false);
      assert.equal(ui.startupNew.disabled, false);
      assert.equal(ui.startupResume.disabled, false);
      if (settlement === 'success') {
        assert.equal(f.controller.screen, 'match');
        assert.equal(f.writes.length, 1);
        assert.ok(
          f.events.some((event) => Array.isArray(event) && event[0] === 'committed' && event[2]),
        );
        const before = f.writes.length;
        f.controller.persistGame(true);
        assert.equal(f.writes.length, before + 1);
        assert.equal(f.controller.clearSave(), clearStatus === 'ok');
        if (clearStatus === 'ok') assert.ok(f.events.includes('saveFocus'));
      } else {
        assert.equal(f.controller.savedCandidate, save);
        assert.equal(f.writes.length, 0);
        ui.startupClear.click();
        assert.equal(clears, 1);
        assert.equal(f.controller.slotPresent, clearStatus !== 'ok');
        assert.equal(f.controller.gameChoice, clearStatus === 'ok' ? 'cleared' : 'pending');
        assert.equal(f.dialogs.match.open, true);
        f.dialogs.match.close();
        f.controller.matchClosed(false);
      }
      f.ports.session.restoreReplay = async () => {
        const view = committedView(3);
        f.session.state.view = view;
        f.session.state.phase = 'humanTurn';
        return view;
      };
      await f.controller.restore(save);
      assert.equal(f.controller.busy, false);
      assert.equal(ui.startupNew.disabled, false);
      f.controller.showTitle();
      ui.startupResume.click();
      assert.equal(f.controller.screen, 'match');
      assert.ok(f.events.includes('focus'));
      f.ports.session.newGame = async () => {
        f.session.state.view = committedView(0);
      };
      await f.controller.startNewGame(save.match);
      assert.equal(f.controller.busy, false);
      assert.equal(f.session.state.view.ply, 0);
    });
  }
}
