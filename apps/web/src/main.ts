import {
  RulesClient,
  rulesWasmUrl,
  validateReplayShape,
  type GameView,
} from '@quoridor/engine-bridge';
import { vxgi } from 'three/addons/lighting/vxgi/VXGINode.js';
import { SessionController, type Transition } from './session/session-controller';
import { BoardRenderer, type Backend, type RendererFault } from './render/three-context';
import { InputRouter } from './input/input-router';
import {
  DEFAULT_SETTINGS,
  LocalStateRepository,
  makeSavedMatch,
  type LocalSettings,
  type MatchOptions,
  validateMatchOptions,
} from './persistence/local-state';
import { ENVIRONMENT_PRESETS, environmentPreset, isEnvironmentId } from './environment-presets';
import { ja } from './ui/strings';
import { ReviewController } from './session/review-controller';
import { createResultReview } from './ui/result-review';
import { setIconButton } from './ui/icons';
import { createTitleHelp } from './ui/title-help';
import { MatchUiController, installPageLifecycle } from './ui/match-controller';
import { installAudioControls } from './audio/audio-controls';
import './style.css';
import './ui/title-help.css';

if (import.meta.env.VITE_PHASE1_E2E === '1') void import('./test-support/rules-test-api');
interface Diagnostics {
  phase: 'loading' | 'ready' | 'failed';
  backend: Backend;
  giEnabled: false;
  rulesWasmUrl: string;
  rulesLoaded: boolean;
  workerReady: boolean;
  vxgiAddonAvailable: boolean;
  workerGeneration: number;
  error?: string;
}
declare global {
  interface Window {
    __QUORIDOR_DIAGNOSTICS__?: Diagnostics;
  }
}
const diagnostics: Diagnostics = {
  phase: 'loading',
  backend: 'unknown',
  giEnabled: false,
  rulesWasmUrl,
  rulesLoaded: false,
  workerReady: false,
  vxgiAddonAvailable: typeof vxgi === 'function',
  workerGeneration: 0,
};
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
        <label>${ja.thoughtBudget}<select id="ai-budget"><option value="48">速い（48）</option><option value="96">標準（96）</option><option value="192">じっくり（192）</option><option value="4096">長考（4096）</option></select></label><p class="match-note">思考量を増やすと検討が増え、待ち時間が長くなります。</p><p id="active-match" class="match-note"></p>
        <p id="ai-status" class="help" aria-live="off" hidden></p><div id="ai-actions" class="actions" hidden><button id="cancel-ai" type="button">${ja.cancelAi}</button><button id="retry-ai" type="button">${ja.retryAi}</button><button id="take-control" type="button">${ja.takeControl}</button></div>
      </div>
      <section class="panel save-panel" aria-label="${ja.saveHeading}"><p class="section-label">${ja.saveHeading}</p><p id="save-status" role="status" aria-live="polite" tabindex="-1"></p><div class="actions"><button id="resume-game" type="button">${ja.resume}</button><button id="save-now" type="button">${ja.saveNow}</button><button id="clear-save" type="button">${ja.clearSave}</button></div><details id="storage-detail-wrap" hidden><summary>${ja.errorDetail}</summary><code id="storage-detail"></code></details></section>
      <div class="panel score-panel"><p class="section-label">${ja.playersHeading}</p><div id="player-0" class="player-card active"><span class="player-icon round">●</span><div><strong>${ja.first}</strong><small>${ja.remainingWalls} <b id="walls-0">10</b> 枚</small></div></div>
        <div id="player-1" class="player-card"><span class="player-icon hex">⬡</span><div><strong>${ja.second}</strong><small>${ja.remainingWalls} <b id="walls-1">10</b> 枚</small></div></div></div>
      <div class="panel"><p class="section-label">${ja.actionHeading}</p><div class="segmented"><button id="mode-move" class="active" type="button">${ja.move}</button><button id="mode-wall" type="button">${ja.wall}</button></div>
        <button id="orientation" class="orientation" type="button">${ja.wallDirection}: <b>${ja.horizontal}</b> <kbd>R</kbd></button><p id="preview-text" class="help" aria-live="polite">${ja.guideMove}</p></div>
      <div class="panel actions"><button id="undo" type="button">${ja.undo}</button><button id="new-game" class="accent" type="button">${ja.newGame}</button></div>
      <div class="panel"><p class="section-label">${ja.cameraHeading}</p><div class="actions"><button id="flip" type="button">${ja.flip}</button><button id="reset-camera" type="button">${ja.resetCamera}</button></div></div>
      <details class="panel settings"><summary>${ja.settings}</summary>
        <label for="environment-select">${ja.environment}<select id="environment-select">${ENVIRONMENT_PRESETS.map((preset) => `<option value="${preset.id}">${preset.label}</option>`).join('')}</select></label>
        <p id="environment-status" role="status" aria-live="polite"></p><button id="retry-environment" type="button" hidden>${ja.retryEnvironment}</button><label><input id="no-animation" type="checkbox"> ${ja.noAnimation}</label><p id="settings-status"></p><p>${ja.guideKeyboard}</p><p id="backend-label">${ja.diagnostics}: ${ja.preparing} · ${ja.giOff}</p></details>
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
const surfaces = createTitleHelp(
  shell,
  menuDialog,
  topActions,
  `${import.meta.env.BASE_URL}assets/ui/quoridor-title-logo.png`,
);
const ending = createResultReview(shell, layout);
setIconButton(restart, 'restart', ja.restart);
setIconButton(newGame, 'newGame', ja.newGame);
setIconButton(openMenu, 'settings', ja.more);
setIconButton(surfaces.helpButton, 'help', '遊び方');
const startupDialog = surfaces.title;
shell.append(menuDialog, matchDialog);
faultGroup.remove();
shell.append(faultGroup);
actionGroup.remove();
sidebar.remove();
const ui = {
  heading: $<HTMLElement>('#turn-heading'),
  ply: $<HTMLElement>('#ply-label'),
  guide: $<HTMLElement>('#board-guide'),
  players: [$<HTMLElement>('#player-0'), $<HTMLElement>('#player-1')],
  walls: [$<HTMLElement>('#walls-0'), $<HTMLElement>('#walls-1')],
  move: $<HTMLButtonElement>('#mode-move'),
  wall: $<HTMLButtonElement>('#mode-wall'),
  orientation: $<HTMLButtonElement>('#orientation'),
  preview: $<HTMLElement>('#preview-text'),
  undo: $<HTMLButtonElement>('#undo'),
  newGame: $<HTMLButtonElement>('#new-game'),
  restart: $<HTMLButtonElement>('#restart-game'),
  openMenu: $<HTMLButtonElement>('#open-menu'),
  confirmTouch: $<HTMLButtonElement>('#confirm-selection'),
  menuDialog: $<HTMLDialogElement>('#menu-dialog'),
  closeMenu: $<HTMLButtonElement>('#close-menu'),
  matchDialog: $<HTMLDialogElement>('#match-dialog'),
  dialogCancel: $<HTMLButtonElement>('#dialog-cancel'),
  dialogStart: $<HTMLButtonElement>('#dialog-start'),
  dialogNote: $<HTMLElement>('#match-dialog-note'),
  startupDialog: $<HTMLElement>('#startup-dialog'),
  startupMessage: $<HTMLElement>('#startup-message'),
  startupNew: $<HTMLButtonElement>('#startup-new-game'),
  startupResume: $<HTMLButtonElement>('#resume-game-choice'),
  startupClear: $<HTMLButtonElement>('#startup-clear-save'),
  flip: $<HTMLButtonElement>('#flip'),
  reset: $<HTMLButtonElement>('#reset-camera'),
  motion: $<HTMLInputElement>('#no-animation'),
  backend: $<HTMLElement>('#backend-label'),
  matchMode: $<HTMLSelectElement>('#match-mode'),
  humanSide: $<HTMLSelectElement>('#human-side'),
  budget: $<HTMLSelectElement>('#ai-budget'),
  aiStatus: $<HTMLElement>('#ai-status'),
  aiActions: $<HTMLElement>('#ai-actions'),
  cancelAi: $<HTMLButtonElement>('#cancel-ai'),
  retryAi: $<HTMLButtonElement>('#retry-ai'),
  takeControl: $<HTMLButtonElement>('#take-control'),
  faultPanel: $<HTMLElement>('#fault-panel'),
  faultTitle: $<HTMLElement>('#fault-title'),
  faultText: $<HTMLElement>('#fault-text'),
  faultDetail: $<HTMLElement>('#fault-detail'),
  retryRenderer: $<HTMLButtonElement>('#retry-renderer'),
  retryRules: $<HTMLButtonElement>('#retry-rules'),
  reload: $<HTMLButtonElement>('#reload-app'),
  activeMatch: $<HTMLElement>('#active-match'),
  saveStatus: $<HTMLElement>('#save-status'),
  resume: $<HTMLButtonElement>('#resume-game'),
  saveNow: $<HTMLButtonElement>('#save-now'),
  clearSave: $<HTMLButtonElement>('#clear-save'),
  storageDetailWrap: $<HTMLElement>('#storage-detail-wrap'),
  storageDetail: $<HTMLElement>('#storage-detail'),
  settingsStatus: $<HTMLElement>('#settings-status'),
  environment: $<HTMLSelectElement>('#environment-select'),
  environmentStatus: $<HTMLElement>('#environment-status'),
  retryEnvironment: $<HTMLButtonElement>('#retry-environment'),
};

async function bootstrap(): Promise<void> {
  const repository = new LocalStateRepository();
  const settingsRead = repository.readSettings();
  let settings: LocalSettings =
    settingsRead.status === 'ok' ? settingsRead.value : DEFAULT_SETTINGS;
  let settingsWarning =
    settingsRead.status === 'invalid'
      ? ja.settingsInvalid
      : settingsRead.status === 'unavailable'
        ? ja.settingsUnavailable
        : '';
  let board: BoardRenderer | null = null;
  let input: InputRouter | null = null;
  let rendererStarting = false;
  let renderFault: RendererFault | 'startup' | null = null;
  let rulesFault = false;
  let disposed = false;
  let matchFramed = false;
  let endScreen: 'result' | 'board' | 'review' = 'result';
  let finishedTag = '';
  const review = new ReviewController();
  const session = new SessionController();
  session.pause();
  const listeners = new AbortController();
  const audio = installAudioControls(
    topActions,
    ui.menuDialog,
    listeners.signal,
    import.meta.env.BASE_URL,
  );
  ui.matchMode.value = settings.nextMatch.mode;
  ui.humanSide.value = String(settings.nextMatch.humanSide);
  ui.budget.value = String(settings.nextMatch.simulations);
  ui.motion.checked = settings.reducedMotion;
  ui.environment.value = settings.environmentId;

  const flow = new MatchUiController({
    session,
    repository,
    dialogs: {
      match: ui.matchDialog,
      menu: ui.menuDialog,
      help: surfaces.help,
      restart: surfaces.restart,
      result: ending.dialog,
      note: ui.dialogNote,
      start: ui.dialogStart,
      startupNew: ui.startupNew,
      newGame: ui.newGame,
      openMenu: ui.openMenu,
    },
    render: {
      available: () => board !== null,
      failed: () => renderFault !== null,
      changed: () => renderUi(),
      syncActivity: () => syncActivity(),
      beginOperation: () => {
        audio.cancelEffects();
        endScreen = 'result';
        review.close();
      },
      beforeNewGame: () => {
        if (
          import.meta.env.VITE_PHASE1_E2E === '1' &&
          !rulesStartupFaultInjected &&
          new URLSearchParams(location.search).get('testRulesStartupFailure') === '1'
        ) {
          rulesStartupFaultInjected = true;
          throw new Error('Controlled rules initialization failure');
        }
      },
      syncBoard: (view, focus) => syncBoard(view, focus),
      frameMatch: () => frameMatchOnce(),
      rulesFault: (value) => {
        rulesFault = value;
        if (value)
          queueMicrotask(() => {
            if (!disposed && !ui.retryRules.hidden) ui.retryRules.focus({ preventScroll: true });
          });
      },
      focusSave: () => ui.saveStatus.focus({ preventScroll: true }),
    },
    inspectReplay: async (candidate) => {
      let temporary: RulesClient | null = null;
      try {
        temporary = await RulesClient.createGame({
          firstPlayer: 0,
          wallsPerPlayer: 10,
          humanPlayer: candidate.match.humanSide,
        });
        temporary.importReplay(candidate.replay);
      } finally {
        temporary?.dispose();
      }
    },
  });

  const syncActivity = (): void => {
    const paused =
      flow.pageSuspended ||
      flow.screen === 'title' ||
      surfaces.help.open ||
      surfaces.restart.open ||
      !!renderFault;
    board?.setPaused(paused);
    audio.setHidden(flow.pageSuspended || document.hidden);
    if (paused) session.pause();
    else session.resume();
  };
  const selectedMatch = (): MatchOptions =>
    validateMatchOptions({
      mode: ui.matchMode.value,
      humanSide: Number(ui.humanSide.value),
      simulations: Number(ui.budget.value),
    });
  const renderUi = (): void => {
    const state = session.state;
    const finished = state.phase === 'finished';
    const reviewing = finished && endScreen === 'review';
    const view = reviewing && review.state.view ? review.state.view : state.view;
    if (!flow.busy)
      audio.setMusicActive(
        flow.screen === 'title' || !finished || reviewing,
        finished ? 0.6 : 0.025,
      );
    diagnostics.workerReady = session.aiWorkerState.ready;
    diagnostics.workerGeneration = session.aiWorkerState.generation;
    diagnostics.rulesLoaded = view !== null;
    const active =
      flow.screen === 'match' &&
      !state.paused &&
      state.phase === 'humanTurn' &&
      !renderFault &&
      !rulesFault &&
      !flow.busy &&
      !ui.matchDialog.open &&
      !ui.menuDialog.open;
    shell.dataset.screen = flow.screen;
    shell.classList.toggle('reduced-motion', settings.reducedMotion);
    ui.startupDialog.hidden = flow.screen !== 'title';
    statusIsland.hidden = flow.screen === 'title';
    footer.hidden = boardCaption.hidden = flow.screen === 'title' || finished;
    modeGroup.hidden = ui.undo.hidden = finished;
    ending.actions.hidden = flow.screen !== 'match' || !finished || endScreen === 'result';
    ending.finished.hidden = reviewing;
    ending.review.hidden = !reviewing;
    ending.counter.textContent = `${ja.reviewing} ${review.state.ply} / ${state.view?.ply ?? 0}手`;
    ending.status.hidden = !reviewing || !['loading', 'error'].includes(review.state.phase);
    ending.status.textContent = review.state.phase === 'error' ? ja.reviewFailed : ja.reviewLoading;
    ending.retry.hidden = review.state.phase !== 'error';
    const reviewReady =
      reviewing && review.state.phase === 'ready' && !renderFault && !rulesFault && !flow.busy;
    ending.first.disabled = ending.prev.disabled = !reviewReady || review.state.ply === 0;
    ending.next.disabled = ending.last.disabled =
      !reviewReady || review.state.ply === review.state.total;
    ending.actions.querySelectorAll<HTMLButtonElement>('button').forEach((button) => {
      if (![ending.first, ending.prev, ending.next, ending.last].includes(button))
        button.disabled = !!renderFault || !!rulesFault || flow.busy;
    });
    saveGroup.hidden = flow.screen === 'title' && !view;
    ui.restart.hidden = ui.newGame.hidden = surfaces.helpButton.hidden = flow.screen === 'title';
    surfaces.returnTitle.hidden = !view;
    ui.startupMessage.textContent =
      flow.gameChoice === 'corrupt' ||
      flow.gameChoice === 'cleared' ||
      flow.storageUnavailable ||
      rulesFault ||
      flow.saveMessage === ja.restoreFailed
        ? flow.saveMessage
        : finished
          ? '対局は終了しています。結果や棋譜を確認できます。'
          : view
            ? '対局を中断しています。戻って続きを遊べます。'
            : flow.savedCandidate
              ? '前の対局があります。続きを遊べます。'
              : '駒を進めて、反対側の端を目指しましょう。';
    ui.startupResume.hidden = !view && !flow.savedCandidate;
    ui.startupNew.classList.toggle('accent', ui.startupResume.hidden);
    ui.startupResume.textContent = view ? '対局に戻る' : '続きから遊ぶ';
    ui.startupClear.hidden = !flow.slotPresent || !!view;
    ui.heading.textContent = renderFault
      ? ja.renderStopped
      : rulesFault && !view
        ? ja.rulesStopped
        : flow.gameChoice === 'pending'
          ? ja.resumePrompt
          : flow.gameChoice === 'corrupt' && !view
            ? ja.saveCorrupt
            : flow.gameChoice === 'cleared' && !view
              ? ja.startNew
              : reviewing
                ? ja.reviewing
                : state.phase === 'booting'
                  ? ja.loading
                  : state.phase === 'recoverableError'
                    ? view
                      ? ja.aiInterrupted
                      : ja.error
                    : state.phase === 'aiThinking'
                      ? ja.thinking
                      : state.phase === 'animating'
                        ? ja.animating
                        : view?.winner !== null && view?.winner !== undefined
                          ? `${view.winner === 0 ? ja.first : ja.second}${ja.winner}`
                          : view
                            ? `${view.turn === 0 ? ja.first : ja.second}${ja.turn}`
                            : ja.loading;
    ui.ply.textContent = `${view?.ply ?? 0} ${ja.ply}`;
    ui.walls.forEach((element, player) => {
      element.textContent = String(view?.wallsRemaining[player] ?? 10);
    });
    ui.players.forEach((element, player) =>
      element.classList.toggle('active', view?.turn === player && view.winner === null),
    );
    ui.undo.disabled = !session.canUndo() || !!renderFault || !!rulesFault || flow.busy;
    ui.newGame.disabled = !board || !!renderFault || flow.busy;
    ui.restart.disabled = !view || !!renderFault || !!rulesFault || flow.busy;
    ui.dialogStart.disabled = !board || !!renderFault || flow.busy;
    ui.startupNew.disabled = !board || !!renderFault || flow.busy;
    ui.startupClear.disabled = flow.busy;
    ui.startupResume.disabled =
      (!view && !flow.savedCandidate) || !board || !!renderFault || !!rulesFault || flow.busy;
    ui.confirmTouch.hidden = !input?.needsConfirmation() || !active;
    ui.resume.hidden = flow.gameChoice !== 'pending' || flow.savedCandidate === null;
    ui.resume.disabled = !board || !!renderFault || !!rulesFault || flow.busy;
    ui.saveNow.disabled = !view || flow.busy;
    ui.clearSave.hidden = !flow.slotPresent;
    ui.clearSave.disabled = flow.busy;
    ui.retryRenderer.disabled = rendererStarting;
    ui.saveStatus.textContent = flow.saveMessage;
    ui.storageDetailWrap.hidden = flow.storageDetail === '';
    ui.storageDetail.textContent = flow.storageDetail;
    ui.settingsStatus.textContent = settingsWarning;
    const assets = board?.diagnostics();
    const requestedLabel = environmentPreset(settings.environmentId).label;
    const failedEnvironment = assets?.environment === 'error' || assets?.environment === 'fallback';
    ui.environment.disabled = !board || !!renderFault;
    ui.retryEnvironment.hidden = !failedEnvironment;
    ui.environmentStatus.textContent =
      assets?.environment === 'ready'
        ? `${requestedLabel}${ja.environmentReady}`
        : failedEnvironment
          ? `${requestedLabel}${ja.environmentFailed}${assets.activeEnvironment ? ` ${environmentPreset(assets.activeEnvironment).label}${ja.environmentKept}` : ja.environmentFallback}`
          : `${requestedLabel}${ja.environmentLoading}`;
    ui.humanSide.disabled = ui.budget.disabled = ui.matchMode.value !== 'ai';
    ui.activeMatch.textContent = view
      ? `${state.mode === 'ai' ? ja.versusAi : ja.pvp}${state.mode === 'ai' ? ` · ${state.humanSide === 0 ? ja.humanFirst : ja.humanSecond}` : ''}`
      : '';
    const showAi =
      !!view &&
      state.mode === 'ai' &&
      (state.phase === 'aiThinking' || state.phase === 'recoverableError');
    boardCaption.classList.toggle('ai-active', showAi);
    ui.aiStatus.hidden = !showAi;
    ui.aiActions.hidden = !showAi;
    ui.aiStatus.textContent =
      state.phase === 'aiThinking'
        ? `${ja.thinking} ${state.aiStats ? `${ja.aiProgress} ${state.aiStats.simulations}/${state.simulations}` : ''}`
        : state.error?.includes('build mismatch')
          ? ja.buildMismatch
          : state.error === 'AI search cancelled'
            ? ja.aiStopped
            : ja.aiFailed;
    ui.cancelAi.hidden = state.phase !== 'aiThinking';
    ui.retryAi.hidden = state.phase !== 'recoverableError';
    ui.takeControl.hidden = state.phase !== 'recoverableError';
    ui.move.classList.toggle('active', (input?.mode ?? 'move') === 'move');
    ui.wall.classList.toggle('active', input?.mode === 'wall');
    ui.move.setAttribute('aria-pressed', String((input?.mode ?? 'move') === 'move'));
    ui.wall.setAttribute('aria-pressed', String(input?.mode === 'wall'));
    ui.orientation.querySelector('b')!.textContent =
      input?.orientation === 'vertical' ? ja.vertical : ja.horizontal;
    ui.guide.textContent = input?.mode === 'wall' ? ja.guideWall : ja.guideMove;
    board?.setHints(view, active && input?.mode === 'move');
    if (board)
      board.canvas.style.visibility = flow.screen === 'title' || view ? 'visible' : 'hidden';
    if (!active) board?.setPreview(null, false);
    const aiMismatch = showAi && !!state.error?.includes('build mismatch');
    ui.faultPanel.hidden = !renderFault && !rulesFault && !aiMismatch;
    ui.faultTitle.textContent = renderFault
      ? ja.renderStopped
      : aiMismatch
        ? ja.buildMismatchTitle
        : ja.rulesStopped;
    ui.faultText.textContent = renderFault
      ? ja.renderRecovery
      : aiMismatch
        ? ja.buildMismatch
        : ja.rulesRecovery;
    ui.faultDetail.textContent = renderFault ?? state.error ?? '';
    ui.retryRenderer.hidden = !renderFault;
    ui.retryRules.hidden = !rulesFault;
    ui.reload.hidden = false;
    ui.backend.textContent = `${ja.diagnostics}: ${board?.backend.toUpperCase() ?? ja.preparing} · ${ja.giOff}`;
    const showResult =
      flow.screen === 'match' &&
      finished &&
      endScreen === 'result' &&
      !renderFault &&
      !rulesFault &&
      !flow.busy &&
      !ui.matchDialog.open &&
      !ui.menuDialog.open &&
      !surfaces.help.open &&
      !surfaces.restart.open;
    if (showResult) {
      ending.setResult(state);
      if (!ending.dialog.open) ending.dialog.showModal();
    } else if (ending.dialog.open) ending.dialog.close();
  };
  const onSession = (): void => {
    const state = session.state;
    const tag = state.phase === 'finished' ? `${state.gameEpoch}:${state.view?.winner}` : '';
    if (tag && tag !== finishedTag) {
      finishedTag = tag;
      endScreen = 'result';
      review.close();
    }
    renderUi();
    flow.persistGame();
  };
  review.subscribe(() => {
    if (disposed) return;
    if (endScreen === 'review' && review.state.view) board?.setView(review.state.view);
    renderUi();
  });
  session.subscribe(onSession);

  const animate = (transition: Transition): void => {
    input?.clear();
    if (!board || renderFault) {
      session.suspendForRendererFailure();
      return;
    }
    board.animate(transition.before, transition.after, transition.actionId, () => {
      const state = session.state;
      if (
        disposed ||
        state.phase !== 'animating' ||
        state.gameEpoch !== transition.gameEpoch ||
        state.revision !== transition.revision
      )
        return;
      const outcome =
        transition.after.winner === null
          ? null
          : state.mode === 'pvp' || transition.after.winner === state.humanSide
            ? 'win'
            : 'lose';
      audio.playPlacement(transition.actionId < 81 ? 'move' : 'wall', outcome);
      session.finish(transition.gameEpoch, transition.revision);
    });
  };
  session.setTransitionSink(animate);
  const suspendDialogsForFault = (retry: HTMLButtonElement): void => {
    flow.suspendDialogs();
    queueMicrotask(() => {
      if (!disposed && !retry.hidden) retry.focus({ preventScroll: true });
    });
  };
  const renderFailed = (kind: RendererFault | 'startup'): void => {
    if (disposed || renderFault) return;
    renderFault = kind;
    audio.cancelEffects();
    suspendDialogsForFault(ui.retryRenderer);
    session.suspendForRendererFailure();
    input?.dispose();
    input = null;
    board?.dispose();
    board = null;
    diagnostics.phase = 'failed';
    diagnostics.error = kind;
    diagnostics.backend = 'unknown';
    flow.persistGame(true);
    renderUi();
  };
  let startupFaultInjected = false;
  let rulesStartupFaultInjected = false;
  const ensureRenderer = async (): Promise<void> => {
    if (disposed || board || rendererStarting) return;
    rendererStarting = true;
    renderUi();
    try {
      if (
        import.meta.env.VITE_PHASE1_E2E === '1' &&
        !startupFaultInjected &&
        new URLSearchParams(location.search).get('testRenderStartupFailure') === '1'
      ) {
        startupFaultInjected = true;
        throw new Error('Controlled renderer startup failure');
      }
      const created = await BoardRenderer.create($<HTMLElement>('#board'), renderFailed, {
        environmentId: settings.environmentId,
        overlayBounds: () => {
          const bounds = (element: HTMLElement): DOMRect | undefined =>
            element.getClientRects().length ? element.getBoundingClientRect() : undefined;
          const tops = [bounds(statusIsland)?.bottom, bounds(topActions)?.bottom].filter(
            (value): value is number => value !== undefined,
          );
          const bottom = footer.hidden ? undefined : bounds(footer)?.top;
          return {
            ...(tops.length ? { top: Math.max(...tops) } : {}),
            ...(bottom !== undefined ? { bottom } : {}),
          };
        },
        onAssetsUpdate: () => {
          if (!disposed) renderUi();
        },
      });
      if (disposed) {
        created.dispose();
        return;
      }
      board = created;
      renderFault = null;
      board.canvas.setAttribute('aria-label', ja.boardLabel);
      board.setReducedMotion(settings.reducedMotion);
      board.setPaused(session.state.paused);
      input = new InputRouter(
        board,
        () => ({
          ...session.state,
          phase:
            renderFault ||
            rulesFault ||
            flow.busy ||
            flow.screen !== 'match' ||
            session.state.paused
              ? 'recoverableError'
              : session.state.phase,
        }),
        (id, epoch, revision) => {
          const transition = session.apply(id, epoch, revision);
          if (transition) animate(transition);
        },
        (target, legal) => {
          ui.preview.textContent = target
            ? legal
              ? ja.legal
              : ja.illegal
            : input?.mode === 'wall'
              ? ja.guideWall
              : ja.guideMove;
          ui.confirmTouch.hidden = !input?.needsConfirmation();
          ui.confirmTouch.disabled = !legal;
        },
        renderUi,
      );
      if (session.state.view)
        board.setView(
          endScreen === 'review' && review.state.view ? review.state.view : session.state.view,
        );
      diagnostics.backend = board.backend;
      diagnostics.phase = 'ready';
      delete diagnostics.error;
      renderUi();
    } catch {
      renderFailed('startup');
    } finally {
      rendererStarting = false;
      renderUi();
    }
  };
  const syncBoard = (view: GameView, focus: boolean): void => {
    audio.cancelEffects();
    input?.clear();
    board?.cancelAnimation();
    board?.setView(view);
    if (focus) board?.canvas.focus({ preventScroll: true });
  };
  const frameMatchOnce = (): void => {
    renderUi();
    if (!matchFramed && board) {
      board.fitToViewport();
      matchFramed = true;
    }
  };
  const updateSettings = (): void => {
    try {
      settings = {
        schemaVersion: 1,
        nextMatch: selectedMatch(),
        reducedMotion: ui.motion.checked,
        environmentId: isEnvironmentId(ui.environment.value)
          ? ui.environment.value
          : settings.environmentId,
      };
    } catch {
      settingsWarning = ja.settingsInvalid;
      renderUi();
      return;
    }
    board?.setReducedMotion(settings.reducedMotion);
    const result = repository.writeSettings(settings);
    settingsWarning =
      result.status === 'ok'
        ? ''
        : result.status === 'quota'
          ? ja.settingsQuota
          : ja.settingsUnavailable;
    renderUi();
  };
  ui.move.addEventListener('click', () => input?.setMode('move'), { signal: listeners.signal });
  ui.wall.addEventListener('click', () => input?.setMode('wall'), { signal: listeners.signal });
  ui.orientation.addEventListener('click', () => input?.toggleOrientation(), {
    signal: listeners.signal,
  });
  ui.confirmTouch.addEventListener('click', () => input?.confirmSelection(), {
    signal: listeners.signal,
  });
  for (const select of [ui.matchMode, ui.humanSide, ui.budget])
    select.addEventListener('change', updateSettings, { signal: listeners.signal });
  ui.motion.addEventListener('change', updateSettings, { signal: listeners.signal });
  ui.environment.addEventListener(
    'change',
    () => {
      updateSettings();
      void board?.setEnvironment(settings.environmentId);
    },
    { signal: listeners.signal },
  );
  ui.retryEnvironment.addEventListener(
    'click',
    () => {
      void board?.setEnvironment(settings.environmentId);
    },
    { signal: listeners.signal },
  );
  ui.undo.addEventListener(
    'click',
    () => {
      if (renderFault || rulesFault || flow.busy || session.state.phase === 'finished') return;
      const view = session.undo();
      if (view) {
        syncBoard(view, true);
        audio.play('undo');
      }
    },
    { signal: listeners.signal },
  );
  ui.newGame.addEventListener('click', () => flow.openMatchDialog(), { signal: listeners.signal });
  const restartMatch = (): void => {
    const state = session.state;
    if (state.view)
      void flow.startNewGame(
        validateMatchOptions({
          mode: state.mode,
          humanSide: state.humanSide,
          simulations: state.simulations,
        }),
      );
  };
  const requestRestart = (): void => {
    if (!session.state.view) return;
    if (session.state.view.ply === 0) restartMatch();
    else {
      if (session.state.phase === 'finished') {
        endScreen = 'result';
        review.close();
        if (session.state.view) board?.setView(session.state.view);
      }
      if (ending.dialog.open) ending.dialog.close();
      input?.clear();
      surfaces.restart.showModal();
      syncActivity();
      renderUi();
    }
  };
  ui.restart.addEventListener('click', requestRestart, { signal: listeners.signal });
  $<HTMLButtonElement>('#result-again').addEventListener('click', requestRestart, {
    signal: listeners.signal,
  });
  $<HTMLButtonElement>('#restart-cancel').addEventListener(
    'click',
    () => surfaces.restart.close(),
    { signal: listeners.signal },
  );
  $<HTMLButtonElement>('#restart-confirm').addEventListener(
    'click',
    () => {
      surfaces.restart.close();
      restartMatch();
    },
    { signal: listeners.signal },
  );
  surfaces.restart.addEventListener(
    'close',
    () => {
      syncActivity();
      renderUi();
      if (!renderFault && !ending.dialog.open) ui.restart.focus();
    },
    { signal: listeners.signal },
  );
  let helpOrigin: HTMLElement = surfaces.helpButton;
  const openHelp = (origin: HTMLElement): void => {
    helpOrigin = origin;
    input?.clear();
    surfaces.help.showModal();
    surfaces.help.scrollTop = 0;
    syncActivity();
    renderUi();
  };
  surfaces.helpButton.addEventListener('click', () => openHelp(surfaces.helpButton), {
    signal: listeners.signal,
  });
  $<HTMLButtonElement>('#title-help').addEventListener(
    'click',
    (event) => openHelp(event.currentTarget as HTMLElement),
    { signal: listeners.signal },
  );
  for (const selector of ['#close-help', '#close-help-bottom'])
    $(selector).addEventListener('click', () => surfaces.help.close(), {
      signal: listeners.signal,
    });
  surfaces.help.addEventListener(
    'close',
    () => {
      syncActivity();
      renderUi();
      if (!renderFault && !rulesFault) helpOrigin.focus();
    },
    { signal: listeners.signal },
  );
  const returnTitle = (): void => {
    const wasReviewing = endScreen === 'review';
    flow.showTitle();
    endScreen = 'result';
    review.close();
    audio.cancelEffects();
    if (wasReviewing && session.state.view) board?.setView(session.state.view);
    if (ending.dialog.open) ending.dialog.close();
    input?.clear();
    flow.closeMenuForTitle();
    syncActivity();
    renderUi();
    ui.startupResume.focus();
    // Restart the one-shot logo entrance on each visit without hiding the menu.
    const logo = $<HTMLElement>('.title-logo');
    logo.getAnimations().forEach((animation) => animation.cancel());
    logo.style.animation = 'none';
    void logo.offsetWidth;
    logo.style.animation = '';
  };
  surfaces.returnTitle.addEventListener('click', returnTitle, { signal: listeners.signal });
  $<HTMLButtonElement>('#result-title').addEventListener('click', returnTitle, {
    signal: listeners.signal,
  });
  const showResult = (): void => {
    endScreen = 'result';
    review.close();
    if (session.state.view) syncBoard(session.state.view, false);
    renderUi();
  };
  const showFinishedBoard = (): void => {
    endScreen = 'board';
    if (ending.dialog.open) ending.dialog.close();
    renderUi();
    $<HTMLButtonElement>('#finished-result').focus();
  };
  const openReview = (): void => {
    if (session.state.phase !== 'finished' || renderFault || flow.busy) return;
    endScreen = 'review';
    audio.cancelEffects();
    input?.clear();
    if (ending.dialog.open) ending.dialog.close();
    void review.open(session.exportReplay()).then(() => {
      if (!disposed && endScreen === 'review' && review.state.phase === 'ready')
        ending.first.focus();
    });
    renderUi();
  };
  for (const id of ['result-review', 'finished-review'])
    $('#' + id).addEventListener('click', openReview, { signal: listeners.signal });
  for (const id of ['finished-result', 'review-result'])
    $('#' + id).addEventListener('click', showResult, { signal: listeners.signal });
  $<HTMLButtonElement>('#result-board').addEventListener('click', showFinishedBoard, {
    signal: listeners.signal,
  });
  ending.dialog.addEventListener(
    'cancel',
    (event) => {
      event.preventDefault();
      showFinishedBoard();
    },
    { signal: listeners.signal },
  );
  ending.dialog.addEventListener(
    'keydown',
    (event) => {
      if (event.key !== 'Tab') return;
      const buttons = [
        ...ending.dialog.querySelectorAll<HTMLButtonElement>('button:not(:disabled)'),
      ];
      const target =
        event.shiftKey && document.activeElement === buttons[0]
          ? buttons.at(-1)
          : !event.shiftKey && document.activeElement === buttons.at(-1)
            ? buttons[0]
            : null;
      if (target) {
        event.preventDefault();
        target.focus();
      }
    },
    { signal: listeners.signal },
  );
  ending.retry.addEventListener('click', openReview, { signal: listeners.signal });
  ending.first.addEventListener('click', () => review.seek(0), { signal: listeners.signal });
  ending.prev.addEventListener('click', () => review.seek(review.state.ply - 1), {
    signal: listeners.signal,
  });
  ending.next.addEventListener('click', () => review.seek(review.state.ply + 1), {
    signal: listeners.signal,
  });
  ending.last.addEventListener('click', () => review.seek(review.state.total), {
    signal: listeners.signal,
  });
  ui.dialogStart.addEventListener(
    'click',
    () => {
      try {
        void flow.startNewGame(selectedMatch());
      } catch {
        ui.dialogNote.textContent = ja.settingsInvalid;
      }
    },
    { signal: listeners.signal },
  );
  ui.dialogCancel.addEventListener('click', () => ui.matchDialog.close(), {
    signal: listeners.signal,
  });
  ui.matchDialog.addEventListener('close', () => flow.matchClosed(!!renderFault || rulesFault), {
    signal: listeners.signal,
  });
  ui.startupNew.addEventListener('click', () => flow.openMatchDialog(true), {
    signal: listeners.signal,
  });
  ui.startupClear.addEventListener(
    'click',
    () => {
      const cleared = flow.clearSave(true);
      flow.openMatchDialog(true);
      if (!cleared) ui.dialogNote.textContent = ja.storageUnavailable;
    },
    { signal: listeners.signal },
  );
  ui.startupResume.addEventListener(
    'click',
    () => {
      if (session.state.view) {
        flow.showMatch();
        endScreen = 'result';
        syncActivity();
        renderUi();
        if (!ending.dialog.open) board?.canvas.focus();
      } else if (flow.savedCandidate) void flow.restore(flow.savedCandidate);
    },
    { signal: listeners.signal },
  );
  ui.resume.addEventListener(
    'click',
    () => {
      if (flow.savedCandidate) void flow.restore(flow.savedCandidate);
    },
    { signal: listeners.signal },
  );
  ui.openMenu.addEventListener(
    'click',
    () => {
      input?.clear();
      flow.openMenu();
    },
    { signal: listeners.signal },
  );
  ui.closeMenu.addEventListener('click', () => ui.menuDialog.close(), { signal: listeners.signal });
  ui.menuDialog.addEventListener('close', () => flow.menuClosed(!!renderFault || rulesFault), {
    signal: listeners.signal,
  });
  ui.saveNow.addEventListener('click', () => flow.persistGame(true), { signal: listeners.signal });
  ui.clearSave.addEventListener('click', () => flow.clearSave(), { signal: listeners.signal });
  ui.cancelAi.addEventListener('click', () => session.cancelAi(), { signal: listeners.signal });
  ui.retryAi.addEventListener('click', () => session.retryAi(), { signal: listeners.signal });
  ui.takeControl.addEventListener(
    'click',
    () => {
      session.switchToPvp();
      renderUi();
    },
    { signal: listeners.signal },
  );
  ui.flip.addEventListener('click', () => board?.flipCamera(), { signal: listeners.signal });
  ui.reset.addEventListener('click', () => board?.resetCamera(), { signal: listeners.signal });
  ui.retryRenderer.addEventListener(
    'click',
    () => {
      void ensureRenderer().then(() => {
        syncActivity();
        flow.showStartup();
      });
    },
    { signal: listeners.signal },
  );
  ui.retryRules.addEventListener(
    'click',
    () => {
      rulesFault = false;
      if (flow.savedCandidate) void flow.inspectStored().then(() => flow.showStartup());
      else if (flow.rulesStartRequested || flow.screen === 'match' || ui.matchDialog.open)
        void flow.startNewGame(selectedMatch());
      else flow.showStartup();
    },
    { signal: listeners.signal },
  );
  ui.reload.addEventListener('click', () => location.reload(), { signal: listeners.signal });
  const dispose = (): void => {
    if (disposed) return;
    disposed = true;
    flow.dispose();
    listeners.abort();
    input?.dispose();
    input = null;
    review.dispose();
    session.dispose();
    board?.dispose();
    board = null;
  };
  installPageLifecycle(window, flow, dispose, listeners.signal);
  if (import.meta.env.VITE_PHASE1_E2E === '1') {
    const support = await import('./test-support/app-test-api');
    support.installAppTestApi({
      session,
      review,
      audio,
      board: () => board,
      input: () => input,
      dispose,
      restoreReplay: async (save, mode, humanSide) => {
        const match = { mode, humanSide, simulations: 96 } as MatchOptions;
        await flow.restore(makeSavedMatch(validateReplayShape(save), match));
      },
      injectRenderFault: (kind) => {
        if (kind === 'deviceLost' && board)
          board.renderer.onDeviceLost({
            api: 'WebGL',
            message: 'Controlled loss',
            reason: null,
            originalEvent: null,
          } as Parameters<typeof board.renderer.onDeviceLost>[0]);
        else if (kind === 'backendError' && board)
          board.renderer.onError('Controlled backend error');
        else renderFailed('renderError');
      },
    });
  }
  if (flow.savedCandidate) await flow.inspectStored();
  await ensureRenderer();
  flow.showStartup();
  renderUi();
}
void bootstrap().catch((error) => {
  diagnostics.phase = 'failed';
  diagnostics.error = error instanceof Error ? error.message : String(error);
  ui.heading.textContent = ja.error;
  ui.faultPanel.hidden = false;
  ui.faultTitle.textContent = ja.rulesStopped;
  ui.faultText.textContent = ja.reloadGuidance;
  ui.faultDetail.textContent = diagnostics.error;
});
