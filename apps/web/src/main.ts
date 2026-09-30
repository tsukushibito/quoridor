import { RulesBridgeError, RulesClient, rulesWasmUrl, validateReplayShape, type GameView } from '@quoridor/engine-bridge';
import { vxgi } from 'three/addons/lighting/vxgi/VXGINode.js';
import { SessionController, type MatchMode, type SessionState, type Transition } from './session/session-controller';
import { BoardRenderer, type Backend, type RendererFault } from './render/three-context';
import { InputRouter } from './input/input-router';
import { DEFAULT_SETTINGS, LocalStateRepository, makeSavedMatch, type LocalSettings,
  type MatchOptions, type SavedMatch, validateMatchOptions } from './persistence/local-state';
import { ja } from './ui/strings';
import './style.css';

if (import.meta.env.VITE_PHASE1_E2E === '1') void import('./test-support/rules-test-api');
interface Diagnostics {
  phase: 'loading' | 'ready' | 'failed'; backend: Backend; giEnabled: false;
  rulesWasmUrl: string; rulesLoaded: boolean; workerReady: boolean; vxgiAddonAvailable: boolean;
  workerGeneration: number; error?: string;
}
declare global { interface Window { __QUORIDOR_DIAGNOSTICS__?: Diagnostics } }
const diagnostics: Diagnostics = { phase: 'loading', backend: 'unknown', giEnabled: false, rulesWasmUrl,
  rulesLoaded: false, workerReady: false, vxgiAddonAvailable: typeof vxgi === 'function', workerGeneration: 0 };
if (import.meta.env.VITE_PHASE1_E2E === '1') window.__QUORIDOR_DIAGNOSTICS__ = diagnostics;
const root = document.querySelector<HTMLDivElement>('#app');
if (!root) throw new Error('App root is missing');
root.innerHTML = `
<main class="shell">
  <header class="topbar"><div class="brand"><span class="brand-mark">Q</span><span>${ja.title}</span></div><span class="phase-pill">${ja.local}</span></header>
  <section class="game-layout">
    <div class="board-panel"><div class="board-heading"><div><p class="eyebrow">${ja.boardEyebrow}</p><h1 id="turn-heading" aria-live="polite">${ja.loading}</h1></div><span id="ply-label" class="ply">0 ${ja.ply}</span></div>
      <div id="board" class="board-canvas" aria-label="${ja.boardLabel}"></div>
      <div class="board-caption"><span id="board-guide">${ja.guideMove}</span><span>9 × 9</span></div></div>
    <aside class="sidebar" aria-label="${ja.controlsLabel}">
      <section id="fault-panel" class="panel fault-panel" role="alert" hidden><strong id="fault-title"></strong><p id="fault-text"></p><div class="actions"><button id="retry-renderer" type="button">${ja.retryRenderer}</button><button id="retry-rules" type="button">${ja.retryRules}</button><button id="reload-app" type="button">${ja.reload}</button></div><details><summary>${ja.errorDetail}</summary><code id="fault-detail"></code></details></section>
      <div class="panel match-panel"><p class="section-label">${ja.matchHeading}</p><label>${ja.matchSettings}<select id="match-mode"><option value="pvp">${ja.pvp}</option><option value="ai">${ja.versusAi}</option></select></label>
        <label>${ja.humanSide}<select id="human-side"><option value="0">${ja.humanFirst}</option><option value="1">${ja.humanSecond}</option></select></label>
        <label>${ja.thoughtBudget}<select id="ai-budget"><option value="48">48</option><option value="96">96</option><option value="192">192</option><option value="4096">4096（${ja.longThought}）</option></select></label><p class="match-note">${ja.applyOnNew}</p><p id="active-match" class="match-note"></p>
        <p id="ai-status" class="help" aria-live="off" hidden></p><div id="ai-actions" class="actions" hidden><button id="cancel-ai" type="button">${ja.cancelAi}</button><button id="retry-ai" type="button">${ja.retryAi}</button><button id="take-control" type="button">${ja.takeControl}</button></div>
      </div>
      <section class="panel save-panel" aria-label="${ja.saveHeading}"><p class="section-label">${ja.saveHeading}</p><p id="save-status" role="status" aria-live="polite" tabindex="-1"></p><div class="actions"><button id="resume-game" type="button">${ja.resume}</button><button id="save-now" type="button">${ja.saveNow}</button><button id="clear-save" type="button">${ja.clearSave}</button></div><details id="storage-detail-wrap" hidden><summary>${ja.errorDetail}</summary><code id="storage-detail"></code></details></section>
      <div class="panel score-panel"><p class="section-label">${ja.playersHeading}</p><div id="player-0" class="player-card active"><span class="player-icon round">●</span><div><strong>${ja.first}</strong><small>${ja.remainingWalls} <b id="walls-0">10</b> 枚</small></div></div>
        <div id="player-1" class="player-card"><span class="player-icon hex">⬡</span><div><strong>${ja.second}</strong><small>${ja.remainingWalls} <b id="walls-1">10</b> 枚</small></div></div></div>
      <div class="panel"><p class="section-label">${ja.actionHeading}</p><div class="segmented"><button id="mode-move" class="active" type="button">${ja.move}</button><button id="mode-wall" type="button">${ja.wall}</button></div>
        <button id="orientation" class="orientation" type="button">${ja.wallDirection}: <b>${ja.horizontal}</b> <kbd>R</kbd></button><p id="preview-text" class="help" aria-live="polite">${ja.guideMove}</p></div>
      <div class="panel actions"><button id="undo" type="button">${ja.undo}</button><button id="new-game" class="accent" type="button">${ja.newGame}</button></div>
      <div class="panel"><p class="section-label">${ja.cameraHeading}</p><div class="actions"><button id="flip" type="button">${ja.flip}</button><button id="reset-camera" type="button">${ja.resetCamera}</button></div></div>
      <details class="panel settings"><summary>${ja.settings}</summary><label><input id="no-animation" type="checkbox"> ${ja.noAnimation}</label><p id="settings-status"></p><p>${ja.guideKeyboard}</p><p id="backend-label">${ja.diagnostics}: ${ja.preparing} · ${ja.giOff}</p></details>
    </aside>
  </section>
</main>`;

const $ = <T extends HTMLElement>(selector: string): T => {
  const value = root.querySelector<T>(selector);
  if (!value) throw new Error(`Missing UI element: ${selector}`);
  return value;
};
// The board fills the viewport. Only the small interactive HUD islands sit
// above it; dialogs remain native modal overlays.
const shell = $<HTMLElement>('.shell');
const topbar = $<HTMLElement>('.topbar');
const layout = $<HTMLElement>('.game-layout');
const sidebar = $<HTMLElement>('.sidebar');
const headingGroup = $<HTMLElement>('.board-heading');
const playersGroup = $<HTMLElement>('.score-panel');
const matchGroup = $<HTMLElement>('.match-panel');
const saveGroup = $<HTMLElement>('.save-panel');
const faultGroup = $<HTMLElement>('.fault-panel');
const modeGroup = $<HTMLElement>('#mode-move').closest<HTMLElement>('.panel')!;
const cameraGroup = $<HTMLElement>('#flip').closest<HTMLElement>('.panel')!;
const settingsGroup = $<HTMLElement>('.settings');
const activeMatch = $<HTMLElement>('#active-match');
const aiStatus = $<HTMLElement>('#ai-status');
const aiActions = $<HTMLElement>('#ai-actions');
const undo = $<HTMLButtonElement>('#undo');
const newGame = $<HTMLButtonElement>('#new-game');
const actionGroup = undo.closest<HTMLElement>('.panel')!;
const topActions = document.createElement('nav');
topActions.className = 'top-actions';
topActions.setAttribute('aria-label', ja.matchHeading);
const statusIsland = document.createElement('div');
statusIsland.className = 'status-island';
const restart = document.createElement('button');
restart.id = 'restart-game';
restart.type = 'button';
restart.textContent = ja.restart;
const openMenu = document.createElement('button');
openMenu.id = 'open-menu';
openMenu.type = 'button';
openMenu.textContent = ja.more;
topActions.append(restart, newGame, openMenu);
headingGroup.append(activeMatch);
statusIsland.append(headingGroup, playersGroup);
topbar.append(statusIsland, topActions);
const boardCaption = $<HTMLElement>('.board-caption');
boardCaption.append(aiStatus, aiActions, $<HTMLElement>('#preview-text'));
const footer = document.createElement('footer');
footer.className = 'action-hud';
const confirmTouch = document.createElement('button');
confirmTouch.id = 'confirm-selection';
confirmTouch.type = 'button';
confirmTouch.hidden = true;
confirmTouch.textContent = ja.confirmPlacement;
footer.append(modeGroup, undo, confirmTouch);
layout.append(footer);
const menuDialog = document.createElement('dialog');
menuDialog.id = 'menu-dialog';
menuDialog.className = 'app-dialog menu-dialog';
menuDialog.setAttribute('aria-label', ja.more);
menuDialog.innerHTML = `<div class="dialog-head"><h2>${ja.more}</h2><button id="close-menu" type="button">${ja.close}</button></div>`;
menuDialog.append(cameraGroup, saveGroup, settingsGroup);
const matchDialog = document.createElement('dialog');
matchDialog.id = 'match-dialog';
matchDialog.className = 'app-dialog match-dialog';
matchDialog.setAttribute('aria-labelledby', 'match-dialog-title');
matchDialog.innerHTML = `<h2 id="match-dialog-title">${ja.newGame}</h2><p id="match-dialog-note"></p>`;
matchDialog.append(matchGroup);
const matchButtons = document.createElement('div');
matchButtons.className = 'dialog-actions';
matchButtons.innerHTML = `<button id="dialog-cancel" type="button">${ja.cancel}</button><button id="dialog-start" class="accent" type="button">${ja.startMatch}</button>`;
matchDialog.append(matchButtons);
const startupDialog = document.createElement('dialog');
startupDialog.id = 'startup-dialog';
startupDialog.className = 'app-dialog startup-dialog';
startupDialog.setAttribute('aria-labelledby', 'startup-title');
startupDialog.innerHTML = `<h2 id="startup-title">${ja.resumeHeading}</h2><p id="startup-message"></p><div class="dialog-actions"><button id="resume-game-choice" type="button">${ja.resume}</button><button id="startup-new-game" class="accent" type="button">${ja.startNew}</button><button id="startup-clear-save" type="button">${ja.clearSave}</button></div>`;
shell.append(menuDialog, matchDialog, startupDialog);
faultGroup.remove();
layout.append(faultGroup);
actionGroup.remove();
sidebar.remove();
const ui = {
  heading: $<HTMLElement>('#turn-heading'), ply: $<HTMLElement>('#ply-label'), guide: $<HTMLElement>('#board-guide'),
  players: [$<HTMLElement>('#player-0'), $<HTMLElement>('#player-1')],
  walls: [$<HTMLElement>('#walls-0'), $<HTMLElement>('#walls-1')],
  move: $<HTMLButtonElement>('#mode-move'), wall: $<HTMLButtonElement>('#mode-wall'),
  orientation: $<HTMLButtonElement>('#orientation'), preview: $<HTMLElement>('#preview-text'),
  undo: $<HTMLButtonElement>('#undo'), newGame: $<HTMLButtonElement>('#new-game'),
  restart: $<HTMLButtonElement>('#restart-game'), openMenu: $<HTMLButtonElement>('#open-menu'),
  confirmTouch: $<HTMLButtonElement>('#confirm-selection'),
  menuDialog: $<HTMLDialogElement>('#menu-dialog'), closeMenu: $<HTMLButtonElement>('#close-menu'),
  matchDialog: $<HTMLDialogElement>('#match-dialog'), dialogCancel: $<HTMLButtonElement>('#dialog-cancel'),
  dialogStart: $<HTMLButtonElement>('#dialog-start'), dialogNote: $<HTMLElement>('#match-dialog-note'),
  startupDialog: $<HTMLDialogElement>('#startup-dialog'), startupMessage: $<HTMLElement>('#startup-message'),
  startupNew: $<HTMLButtonElement>('#startup-new-game'), startupResume: $<HTMLButtonElement>('#resume-game-choice'),
  startupClear: $<HTMLButtonElement>('#startup-clear-save'),
  flip: $<HTMLButtonElement>('#flip'), reset: $<HTMLButtonElement>('#reset-camera'),
  motion: $<HTMLInputElement>('#no-animation'), backend: $<HTMLElement>('#backend-label'),
  matchMode: $<HTMLSelectElement>('#match-mode'), humanSide: $<HTMLSelectElement>('#human-side'),
  budget: $<HTMLSelectElement>('#ai-budget'), aiStatus: $<HTMLElement>('#ai-status'),
  aiActions: $<HTMLElement>('#ai-actions'), cancelAi: $<HTMLButtonElement>('#cancel-ai'),
  retryAi: $<HTMLButtonElement>('#retry-ai'), takeControl: $<HTMLButtonElement>('#take-control'),
  faultPanel: $<HTMLElement>('#fault-panel'), faultTitle: $<HTMLElement>('#fault-title'),
  faultText: $<HTMLElement>('#fault-text'), faultDetail: $<HTMLElement>('#fault-detail'),
  retryRenderer: $<HTMLButtonElement>('#retry-renderer'), retryRules: $<HTMLButtonElement>('#retry-rules'),
  reload: $<HTMLButtonElement>('#reload-app'), activeMatch: $<HTMLElement>('#active-match'),
  saveStatus: $<HTMLElement>('#save-status'), resume: $<HTMLButtonElement>('#resume-game'),
  saveNow: $<HTMLButtonElement>('#save-now'), clearSave: $<HTMLButtonElement>('#clear-save'),
  storageDetailWrap: $<HTMLElement>('#storage-detail-wrap'), storageDetail: $<HTMLElement>('#storage-detail'),
  settingsStatus: $<HTMLElement>('#settings-status'),
};

async function bootstrap(): Promise<void> {
  const repository = new LocalStateRepository();
  const settingsRead = repository.readSettings();
  let settings: LocalSettings = settingsRead.status === 'ok' ? settingsRead.value : DEFAULT_SETTINGS;
  const gameRead = repository.readGame();
  let savedCandidate: SavedMatch | null = gameRead.status === 'ok' ? gameRead.value : null;
  let slotPresent = gameRead.status === 'ok' || gameRead.status === 'invalid';
  let gameChoice: 'pending' | 'corrupt' | 'cleared' | 'active' = gameRead.status === 'ok' ? 'pending' : gameRead.status === 'invalid' ? 'corrupt' : 'active';
  let saveMessage: string = gameChoice === 'pending' ? ja.resumePrompt : gameChoice === 'corrupt' ? ja.saveCorrupt :
    gameRead.status === 'unavailable' ? ja.storageUnavailable : ja.noSave;
  let storageDetail = gameRead.status === 'invalid' ? gameRead.reason : '';
  let settingsWarning = settingsRead.status === 'invalid' ? ja.settingsInvalid :
    settingsRead.status === 'unavailable' ? ja.settingsUnavailable : '';
  let board: BoardRenderer | null = null;
  let input: InputRouter | null = null;
  let rendererStarting = false;
  let renderFault: RendererFault | 'startup' | null = null;
  let rulesFault = false;
  let busy = false;
  let operation = 0;
  let disposed = false;
  let suppressSave = false;
  let lastAttemptTag = '';
  let matchFromStartup = false;
  let matchStarted = false;
  let suppressMatchClose = false;
  let suppressMenuClose = false;
  const session = new SessionController();
  const listeners = new AbortController();
  ui.matchMode.value = settings.nextMatch.mode;
  ui.humanSide.value = String(settings.nextMatch.humanSide);
  ui.budget.value = String(settings.nextMatch.simulations);
  ui.motion.checked = settings.reducedMotion;

  const selectedMatch = (): MatchOptions => validateMatchOptions({ mode: ui.matchMode.value,
    humanSide: Number(ui.humanSide.value), simulations: Number(ui.budget.value) });
  const saveTag = (state: SessionState): string => `${state.gameEpoch}:${state.revision}:${state.mode}:${state.humanSide}:${state.simulations}`;
  const setSaveMessage = (message: string, detail = ''): void => { saveMessage = message; storageDetail = detail; renderUi(); };
  const persistGame = (force = false): void => {
    const state = session.state;
    if (disposed || suppressSave || gameChoice !== 'active' || !state.view || state.phase === 'booting') return;
    const tag = saveTag(state);
    if (!force && tag === lastAttemptTag) return;
    lastAttemptTag = tag;
    let outcome;
    try { outcome = repository.writeGame(makeSavedMatch(session.exportReplay(), {
      mode: state.mode, humanSide: state.humanSide, simulations: state.simulations })); }
    catch (error) { setSaveMessage(ja.saveFailed, error instanceof Error ? error.message : String(error)); return; }
    if (outcome.status === 'ok') {
      slotPresent = true; savedCandidate = null;
      setSaveMessage(ja.saved);
    } else setSaveMessage(outcome.status === 'quota' ? ja.storageQuota : ja.storageUnavailable);
  };
  const renderUi = (): void => {
    const state = session.state, view = state.view;
    diagnostics.workerReady = session.aiWorkerState.ready;
    diagnostics.workerGeneration = session.aiWorkerState.generation;
    diagnostics.rulesLoaded = view !== null;
    const active = state.phase === 'humanTurn' && !renderFault && !rulesFault && !busy &&
      !ui.matchDialog.open && !ui.menuDialog.open && !ui.startupDialog.open;
    ui.heading.textContent = renderFault ? ja.renderStopped : rulesFault && !view ? ja.rulesStopped :
      gameChoice === 'pending' ? ja.resumePrompt : gameChoice === 'corrupt' && !view ? ja.saveCorrupt :
        gameChoice === 'cleared' && !view ? ja.startNew :
        state.phase === 'booting' ? ja.loading : state.phase === 'recoverableError' ? (view ? ja.aiInterrupted : ja.error)
          : state.phase === 'aiThinking' ? ja.thinking : state.phase === 'animating' ? ja.animating :
            view?.winner !== null && view?.winner !== undefined ? `${view.winner === 0 ? ja.first : ja.second}${ja.winner}` :
              view ? `${view.turn === 0 ? ja.first : ja.second}${ja.turn}` : ja.loading;
    ui.ply.textContent = `${view?.ply ?? 0} ${ja.ply}`;
    ui.walls.forEach((element, player) => { element.textContent = String(view?.wallsRemaining[player] ?? 10); });
    ui.players.forEach((element, player) => element.classList.toggle('active', view?.turn === player && view.winner === null));
    ui.undo.disabled = !session.canUndo() || !!renderFault || !!rulesFault || busy;
    ui.newGame.disabled = !board || !!renderFault || busy;
    ui.restart.disabled = !view || !!renderFault || !!rulesFault || busy;
    ui.dialogStart.disabled = !board || !!renderFault || busy;
    ui.startupNew.disabled = !board || !!renderFault || busy;
    ui.startupResume.disabled = !savedCandidate || !board || !!renderFault || !!rulesFault || busy;
    ui.confirmTouch.hidden = !input?.needsConfirmation() || !active;
    ui.resume.hidden = gameChoice !== 'pending' || savedCandidate === null;
    ui.resume.disabled = !board || !!renderFault || !!rulesFault || busy;
    ui.saveNow.disabled = !view || busy;
    ui.clearSave.hidden = !slotPresent;
    ui.clearSave.disabled = busy;
    ui.retryRenderer.disabled = rendererStarting;
    ui.saveStatus.textContent = saveMessage;
    ui.storageDetailWrap.hidden = storageDetail === '';
    ui.storageDetail.textContent = storageDetail;
    ui.settingsStatus.textContent = settingsWarning;
    ui.humanSide.disabled = ui.budget.disabled = ui.matchMode.value !== 'ai';
    ui.activeMatch.textContent = view ? `${state.mode === 'ai' ? ja.versusAi : ja.pvp}${state.mode === 'ai' ? ` · ${state.humanSide === 0 ? ja.humanFirst : ja.humanSecond}` : ''}` : '';
    const showAi = !!view && state.mode === 'ai' && (state.phase === 'aiThinking' || state.phase === 'recoverableError');
    boardCaption.classList.toggle('ai-active', showAi);
    ui.aiStatus.hidden = !showAi;
    ui.aiActions.hidden = !showAi;
    ui.aiStatus.textContent = state.phase === 'aiThinking'
      ? `${ja.thinking} ${state.aiStats ? `${ja.aiProgress} ${state.aiStats.simulations}/${state.simulations}` : ''}`
      : state.error?.includes('build mismatch') ? ja.buildMismatch :
        state.error === 'AI search cancelled' ? ja.aiStopped : ja.aiFailed;
    ui.cancelAi.hidden = state.phase !== 'aiThinking';
    ui.retryAi.hidden = state.phase !== 'recoverableError';
    ui.takeControl.hidden = state.phase !== 'recoverableError';
    ui.move.classList.toggle('active', (input?.mode ?? 'move') === 'move');
    ui.wall.classList.toggle('active', input?.mode === 'wall');
    ui.move.setAttribute('aria-pressed', String((input?.mode ?? 'move') === 'move'));
    ui.wall.setAttribute('aria-pressed', String(input?.mode === 'wall'));
    ui.orientation.querySelector('b')!.textContent = input?.orientation === 'vertical' ? ja.vertical : ja.horizontal;
    ui.guide.textContent = input?.mode === 'wall' ? ja.guideWall : ja.guideMove;
    board?.setHints(view, active && input?.mode === 'move');
    if (board) board.canvas.style.visibility = view ? 'visible' : 'hidden';
    if (!active) board?.setPreview(null, false);
    const aiMismatch = showAi && !!state.error?.includes('build mismatch');
    ui.faultPanel.hidden = !renderFault && !rulesFault && !aiMismatch;
    ui.faultTitle.textContent = renderFault ? ja.renderStopped : aiMismatch ? ja.buildMismatchTitle : ja.rulesStopped;
    ui.faultText.textContent = renderFault ? ja.renderRecovery : aiMismatch ? ja.buildMismatch : ja.rulesRecovery;
    ui.faultDetail.textContent = renderFault ?? state.error ?? '';
    ui.retryRenderer.hidden = !renderFault;
    ui.retryRules.hidden = !rulesFault;
    ui.reload.hidden = false;
    ui.backend.textContent = `${ja.diagnostics}: ${board?.backend.toUpperCase() ?? ja.preparing} · ${ja.giOff}`;
  };
  const onSession = (): void => { renderUi(); persistGame(); };
  session.subscribe(onSession);

  const animate = (transition: Transition): void => {
    input?.clear();
    if (!board || renderFault) { session.suspendForRendererFailure(); return; }
    board.animate(transition.before, transition.after, transition.actionId,
      () => session.finish(transition.gameEpoch, transition.revision));
  };
  session.setTransitionSink(animate);
  const suspendDialogsForFault = (retry: HTMLButtonElement): void => {
    // A modal in the top layer would hide the fault actions on the board.
    // Suppress its deferred close handler so it cannot reopen startup over recovery.
    suppressMatchClose = true;
    suppressMenuClose = true;
    matchFromStartup = false;
    matchStarted = false;
    if (ui.matchDialog.open) ui.matchDialog.close();
    if (ui.menuDialog.open) ui.menuDialog.close();
    if (ui.startupDialog.open) ui.startupDialog.close();
    queueMicrotask(() => { if (!disposed && !retry.hidden) retry.focus({ preventScroll: true }); });
  };
  const renderFailed = (kind: RendererFault | 'startup'): void => {
    if (disposed || renderFault) return;
    renderFault = kind;
    suspendDialogsForFault(ui.retryRenderer);
    session.suspendForRendererFailure();
    input?.dispose(); input = null;
    board?.dispose(); board = null;
    diagnostics.phase = 'failed'; diagnostics.error = kind; diagnostics.backend = 'unknown';
    persistGame(true);
    renderUi();
  };
  let startupFaultInjected = false;
  let rulesStartupFaultInjected = false;
  const ensureRenderer = async (): Promise<void> => {
    if (disposed || board || rendererStarting) return;
    rendererStarting = true;
    renderUi();
    try {
      if (import.meta.env.VITE_PHASE1_E2E === '1' && !startupFaultInjected &&
        new URLSearchParams(location.search).get('testRenderStartupFailure') === '1') {
        startupFaultInjected = true; throw new Error('Controlled renderer startup failure');
      }
      const created = await BoardRenderer.create($<HTMLElement>('#board'), renderFailed);
      if (disposed) { created.dispose(); return; }
      board = created; renderFault = null;
      board.canvas.setAttribute('aria-label', ja.boardLabel);
      board.setReducedMotion(settings.reducedMotion);
      input = new InputRouter(board, () => ({ ...session.state,
        phase: renderFault || rulesFault || busy ? 'recoverableError' : session.state.phase }),
      (id, epoch, revision) => { const transition = session.apply(id, epoch, revision); if (transition) animate(transition); },
      (target, legal) => { ui.preview.textContent = target ? (legal ? ja.legal : ja.illegal) :
        (input?.mode === 'wall' ? ja.guideWall : ja.guideMove);
        ui.confirmTouch.hidden = !input?.needsConfirmation();
        ui.confirmTouch.disabled = !legal; }, renderUi);
      if (session.state.view) board.setView(session.state.view);
      diagnostics.backend = board.backend;
      diagnostics.phase = 'ready'; delete diagnostics.error;
      renderUi();
    } catch { renderFailed('startup'); }
    finally { rendererStarting = false; renderUi(); }
  };
  const syncBoard = (view: GameView, focus: boolean): void => {
    input?.clear(); board?.cancelAnimation(); board?.setView(view);
    if (focus) board?.canvas.focus({ preventScroll: true });
  };
  const startNewGame = async (options: MatchOptions, focus = true): Promise<void> => {
    if (disposed || renderFault || !board) return;
    const currentOperation = ++operation;
    busy = true; suppressSave = true; renderUi();
    try {
      if (import.meta.env.VITE_PHASE1_E2E === '1' && !rulesStartupFaultInjected &&
        new URLSearchParams(location.search).get('testRulesStartupFailure') === '1') {
        rulesStartupFaultInjected = true; throw new Error('Controlled rules initialization failure');
      }
      await session.newGame(options);
      if (disposed || currentOperation !== operation) return;
      const state = session.state;
      if (!state.view || state.error) {
        rulesFault = !state.view;
        if (rulesFault) suspendDialogsForFault(ui.retryRules);
        ui.dialogNote.textContent = ja.rulesUnavailable;
        setSaveMessage(ja.rulesUnavailable, state.error ?? '');
        return;
      }
      rulesFault = false; gameChoice = 'active'; savedCandidate = null;
      if (ui.matchDialog.open) { matchStarted = true; ui.matchDialog.close(); }
      if (ui.startupDialog.open) ui.startupDialog.close();
      syncBoard(state.view, focus);
      suppressSave = false; persistGame(true);
    } catch (error) {
      if (currentOperation === operation) { rulesFault = !session.state.view;
        if (rulesFault) suspendDialogsForFault(ui.retryRules);
        ui.dialogNote.textContent = ja.rulesUnavailable;
        setSaveMessage(ja.rulesUnavailable, error instanceof Error ? error.message : String(error)); }
    } finally {
      if (currentOperation === operation) { busy = false; suppressSave = false; renderUi(); }
    }
  };
  const restore = async (save: SavedMatch, focus = true): Promise<void> => {
    if (disposed || renderFault || !board) return;
    const currentOperation = ++operation;
    busy = true; suppressSave = true; renderUi();
    try {
      const view = await session.restoreReplay(save.replay, save.match);
      if (disposed || currentOperation !== operation) return;
      rulesFault = false; gameChoice = 'active'; savedCandidate = null; slotPresent = true;
      if (ui.startupDialog.open) ui.startupDialog.close();
      syncBoard(view, focus);
      setSaveMessage(ja.saved);
    } catch (error) {
      if (currentOperation === operation) setSaveMessage(ja.restoreFailed,
        error instanceof Error ? error.message : String(error));
    } finally {
      if (currentOperation === operation) { busy = false; suppressSave = false; persistGame(); renderUi(); }
    }
  };
  const inspectStored = async (): Promise<void> => {
    if (!savedCandidate) return;
    const candidate = savedCandidate;
    let temporary: RulesClient | null = null;
    try {
      temporary = await RulesClient.createGame({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: candidate.match.humanSide });
      temporary.importReplay(candidate.replay);
      rulesFault = false;
      gameChoice = 'pending';
      setSaveMessage(ja.resumePrompt);
    } catch (error) {
      if (error instanceof RulesBridgeError && (error.code === 'INVALID_REPLAY' || error.code === 'INVALID_JSON')) {
        gameChoice = 'corrupt'; savedCandidate = null;
        setSaveMessage(ja.saveCorrupt, error.code);
      } else {
        rulesFault = true;
        suspendDialogsForFault(ui.retryRules);
        setSaveMessage(ja.rulesUnavailable, error instanceof Error ? error.message : String(error));
      }
    } finally { temporary?.dispose(); }
  };
  const updateSettings = (): void => {
    try { settings = { schemaVersion: 1, nextMatch: selectedMatch(), reducedMotion: ui.motion.checked }; }
    catch { settingsWarning = ja.settingsInvalid; renderUi(); return; }
    board?.setReducedMotion(settings.reducedMotion);
    const result = repository.writeSettings(settings);
    settingsWarning = result.status === 'ok' ? '' : result.status === 'quota' ? ja.settingsQuota : ja.settingsUnavailable;
    renderUi();
  };
  const showStartup = (): void => {
    if (disposed || !board || renderFault || rulesFault || session.state.view || gameChoice === 'active' || ui.startupDialog.open) return;
    ui.startupMessage.textContent = savedCandidate ? ja.resumePrompt : saveMessage;
    ui.startupResume.hidden = !savedCandidate;
    ui.startupClear.hidden = !slotPresent;
    ui.startupNew.textContent = slotPresent ? ja.discardStart : ja.startNew;
    ui.startupDialog.showModal();
    renderUi();
  };
  const openMatchDialog = (fromStartup = false): void => {
    if (disposed || busy || !board || renderFault || ui.matchDialog.open) return;
    suppressMatchClose = false;
    matchFromStartup = fromStartup;
    if (ui.startupDialog.open) ui.startupDialog.close();
    ui.dialogNote.textContent = fromStartup && slotPresent ? ja.resumePrompt : ja.newMatchHint;
    ui.dialogStart.textContent = fromStartup && slotPresent ? ja.discardStart : ja.startMatch;
    ui.matchDialog.showModal();
    renderUi();
  };
  ui.move.addEventListener('click', () => input?.setMode('move'), { signal: listeners.signal });
  ui.wall.addEventListener('click', () => input?.setMode('wall'), { signal: listeners.signal });
  ui.orientation.addEventListener('click', () => input?.toggleOrientation(), { signal: listeners.signal });
  ui.confirmTouch.addEventListener('click', () => input?.confirmSelection(), { signal: listeners.signal });
  for (const select of [ui.matchMode, ui.humanSide, ui.budget]) select.addEventListener('change', updateSettings, { signal: listeners.signal });
  ui.motion.addEventListener('change', updateSettings, { signal: listeners.signal });
  ui.undo.addEventListener('click', () => { if (renderFault || rulesFault || busy) return;
    const view = session.undo(); if (view) syncBoard(view, true); }, { signal: listeners.signal });
  ui.newGame.addEventListener('click', () => openMatchDialog(), { signal: listeners.signal });
  ui.restart.addEventListener('click', () => {
    const state = session.state;
    if (state.view) void startNewGame(validateMatchOptions({
      mode: state.mode, humanSide: state.humanSide, simulations: state.simulations }));
  }, { signal: listeners.signal });
  ui.dialogStart.addEventListener('click', () => {
    try { void startNewGame(selectedMatch()); }
    catch { ui.dialogNote.textContent = ja.settingsInvalid; }
  }, { signal: listeners.signal });
  ui.dialogCancel.addEventListener('click', () => ui.matchDialog.close(), { signal: listeners.signal });
  ui.matchDialog.addEventListener('close', () => {
    if (suppressMatchClose || renderFault || rulesFault) {
      suppressMatchClose = false; matchStarted = false; matchFromStartup = false; renderUi(); return;
    }
    if (matchStarted) { matchStarted = false; matchFromStartup = false; renderUi(); return; }
    if (matchFromStartup && !session.state.view) showStartup();
    else ui.newGame.focus({ preventScroll: true });
    matchFromStartup = false;
    renderUi();
  }, { signal: listeners.signal });
  ui.startupDialog.addEventListener('cancel', event => {
    if (!session.state.view) event.preventDefault();
  }, { signal: listeners.signal });
  ui.startupNew.addEventListener('click', () => openMatchDialog(true), { signal: listeners.signal });
  ui.startupClear.addEventListener('click', () => {
    const outcome = repository.clearGame();
    if (outcome.status === 'ok') {
      slotPresent = false; savedCandidate = null; gameChoice = 'cleared';
      setSaveMessage(ja.saveClearedStartup);
    } else setSaveMessage(ja.storageUnavailable);
    openMatchDialog(true);
    if (outcome.status !== 'ok') ui.dialogNote.textContent = ja.storageUnavailable;
  }, { signal: listeners.signal });
  ui.startupResume.addEventListener('click', () => { if (savedCandidate) void restore(savedCandidate); }, { signal: listeners.signal });
  ui.resume.addEventListener('click', () => { if (savedCandidate) void restore(savedCandidate); }, { signal: listeners.signal });
  ui.openMenu.addEventListener('click', () => { input?.clear(); suppressMenuClose = false;
    ui.menuDialog.showModal(); renderUi(); }, { signal: listeners.signal });
  ui.closeMenu.addEventListener('click', () => ui.menuDialog.close(), { signal: listeners.signal });
  ui.menuDialog.addEventListener('close', () => {
    if (suppressMenuClose || renderFault || rulesFault) suppressMenuClose = false;
    else ui.openMenu.focus({ preventScroll: true });
    renderUi();
  }, { signal: listeners.signal });
  ui.saveNow.addEventListener('click', () => persistGame(true), { signal: listeners.signal });
  ui.clearSave.addEventListener('click', () => { const result = repository.clearGame();
    if (result.status === 'ok') { slotPresent = false; savedCandidate = null;
      lastAttemptTag = saveTag(session.state);
      setSaveMessage(ja.saveCleared); ui.saveStatus.focus({ preventScroll: true }); }
    else setSaveMessage(ja.storageUnavailable); }, { signal: listeners.signal });
  ui.cancelAi.addEventListener('click', () => session.cancelAi(), { signal: listeners.signal });
  ui.retryAi.addEventListener('click', () => session.retryAi(), { signal: listeners.signal });
  ui.takeControl.addEventListener('click', () => { session.switchToPvp(); renderUi(); }, { signal: listeners.signal });
  ui.flip.addEventListener('click', () => board?.flipCamera(), { signal: listeners.signal });
  ui.reset.addEventListener('click', () => board?.resetCamera(), { signal: listeners.signal });
  ui.retryRenderer.addEventListener('click', () => { void ensureRenderer().then(() => {
    if (board && !session.state.view && gameChoice === 'active' && !rulesFault) void startNewGame(selectedMatch(), false);
    else showStartup();
  }); }, { signal: listeners.signal });
  ui.retryRules.addEventListener('click', () => { rulesFault = false;
    if (savedCandidate) void inspectStored().then(showStartup);
    else if (gameChoice === 'active') void startNewGame(selectedMatch());
    else showStartup(); }, { signal: listeners.signal });
  ui.reload.addEventListener('click', () => location.reload(), { signal: listeners.signal });
  const dispose = (): void => { if (disposed) return; disposed = true; listeners.abort(); input?.dispose(); input = null;
    session.dispose(); board?.dispose(); board = null; };
  window.addEventListener('pagehide', dispose, { once: true, signal: listeners.signal });
  if (import.meta.env.VITE_PHASE1_E2E === '1') {
    const support = await import('./test-support/app-test-api');
    support.installAppTestApi({ session, board: () => board, input: () => input, dispose,
      restoreReplay: async (save, mode, humanSide) => {
        const match = { mode, humanSide, simulations: 96 } as MatchOptions;
        await restore(makeSavedMatch(validateReplayShape(save), match));
      },
      injectRenderFault: kind => {
        if (kind === 'deviceLost' && board) board.renderer.onDeviceLost({ api: 'WebGL', message: 'Controlled loss', reason: null,
          originalEvent: null } as Parameters<typeof board.renderer.onDeviceLost>[0]);
        else if (kind === 'backendError' && board) board.renderer.onError('Controlled backend error');
        else renderFailed('renderError');
      } });
  }
  if (savedCandidate) await inspectStored();
  await ensureRenderer();
  if (board && gameChoice === 'active' && !session.state.view && !rulesFault) await startNewGame(selectedMatch(), false);
  else showStartup();
  renderUi();
}
void bootstrap().catch(error => { diagnostics.phase = 'failed'; diagnostics.error = error instanceof Error ? error.message : String(error);
  ui.heading.textContent = ja.error; ui.faultPanel.hidden = false; ui.faultTitle.textContent = ja.rulesStopped;
  ui.faultText.textContent = ja.reloadGuidance; ui.faultDetail.textContent = diagnostics.error; });
