import { RulesBridgeError, type GameView } from '@quoridor/engine-bridge';
import {
  makeSavedMatch,
  type LocalStateRepository,
  type MatchOptions,
  type SavedMatch,
} from '../persistence/local-state';
import type { SessionController, SessionState } from '../session/session-controller';
import { ja } from './strings';

type DialogPorts = {
  match: HTMLDialogElement;
  menu: HTMLDialogElement;
  help: HTMLDialogElement;
  restart: HTMLDialogElement;
  result: HTMLDialogElement;
  note: HTMLElement;
  start: HTMLButtonElement;
  startupNew: HTMLButtonElement;
  newGame: HTMLButtonElement;
  openMenu: HTMLButtonElement;
};
type MatchPorts = {
  session: Pick<SessionController, 'state' | 'newGame' | 'restoreReplay' | 'exportReplay'>;
  repository: Pick<LocalStateRepository, 'readGame' | 'writeGame' | 'clearGame'>;
  dialogs: DialogPorts;
  render: {
    available(): boolean;
    failed(): boolean;
    changed(): void;
    syncActivity(): void;
    beginOperation(): void;
    beforeNewGame(): void;
    syncBoard(view: GameView, focus: boolean): void;
    frameMatch(): void;
    rulesFault(value: boolean): void;
    focusSave(): void;
  };
  inspectReplay(save: SavedMatch): Promise<void>;
};

// Owns saved-slot decisions and their asynchronous operations. Newer operations
// and final disposal invalidate the same generation; callers cannot adopt stale work.
export class MatchUiController {
  private candidate: SavedMatch | null;
  private present: boolean;
  private choice: 'pending' | 'corrupt' | 'cleared' | 'active';
  private message: string;
  private detail: string;
  private savingSuppressed = false;
  private lastAttemptTag = '';
  private generation = 0;
  private stopped = false;
  private working = false;
  private currentScreen: 'title' | 'match' = 'title';
  private pageHidden = false;
  private suppressMatchClose = false;
  private suppressMenuClose = false;
  private matchStarted = false;
  private startRequested = false;
  readonly storageUnavailable: boolean;

  constructor(private readonly ports: MatchPorts) {
    const read = ports.repository.readGame();
    this.storageUnavailable = read.status === 'unavailable';
    this.candidate = read.status === 'ok' ? read.value : null;
    this.present = read.status === 'ok' || read.status === 'invalid';
    this.choice =
      read.status === 'ok' ? 'pending' : read.status === 'invalid' ? 'corrupt' : 'active';
    this.message =
      this.choice === 'pending'
        ? ja.resumePrompt
        : this.choice === 'corrupt'
          ? ja.saveCorrupt
          : read.status === 'unavailable'
            ? ja.storageUnavailable
            : ja.noSave;
    this.detail = read.status === 'invalid' ? read.reason : '';
  }
  get savedCandidate(): SavedMatch | null {
    return this.candidate;
  }
  get slotPresent(): boolean {
    return this.present;
  }
  get gameChoice(): typeof this.choice {
    return this.choice;
  }
  get saveMessage(): string {
    return this.message;
  }
  get storageDetail(): string {
    return this.detail;
  }
  get busy(): boolean {
    return this.working;
  }
  get screen(): 'title' | 'match' {
    return this.currentScreen;
  }
  get pageSuspended(): boolean {
    return this.pageHidden;
  }
  get rulesStartRequested(): boolean {
    return this.startRequested;
  }
  private current(operation: number): boolean {
    return !this.stopped && operation === this.generation;
  }
  private setMessage(message: string, detail = ''): void {
    if (this.stopped) return;
    this.message = message;
    this.detail = detail;
    this.ports.render.changed();
  }
  private saveTag(state: SessionState): string {
    return `${state.gameEpoch}:${state.revision}:${state.mode}:${state.humanSide}:${state.simulations}`;
  }
  persistGame(force = false): void {
    const state = this.ports.session.state;
    if (
      this.stopped ||
      this.savingSuppressed ||
      this.choice !== 'active' ||
      !state.view ||
      state.phase === 'booting'
    )
      return;
    const tag = this.saveTag(state);
    if (!force && tag === this.lastAttemptTag) return;
    this.lastAttemptTag = tag;
    let outcome;
    try {
      outcome = this.ports.repository.writeGame(
        makeSavedMatch(this.ports.session.exportReplay(), {
          mode: state.mode,
          humanSide: state.humanSide,
          simulations: state.simulations,
        }),
      );
    } catch (error) {
      this.setMessage(ja.saveFailed, error instanceof Error ? error.message : String(error));
      return;
    }
    if (outcome.status === 'ok') {
      this.present = true;
      this.candidate = null;
      this.setMessage(ja.saved);
    } else this.setMessage(outcome.status === 'quota' ? ja.storageQuota : ja.storageUnavailable);
  }
  private begin(): number {
    const operation = ++this.generation;
    this.working = true;
    this.savingSuppressed = true;
    this.ports.render.beginOperation();
    this.ports.render.changed();
    return operation;
  }
  private adopt(view: GameView, focus: boolean): void {
    this.ports.render.rulesFault(false);
    this.choice = 'active';
    this.candidate = null;
    const dialogs = this.ports.dialogs;
    if (dialogs.help.open) dialogs.help.close();
    if (dialogs.restart.open) dialogs.restart.close();
    this.showMatch();
    this.ports.render.syncActivity();
    this.ports.render.frameMatch();
    this.ports.render.syncBoard(view, focus);
  }
  private rulesFailed(error: string): void {
    const fault = !this.ports.session.state.view;
    this.ports.render.rulesFault(fault);
    if (fault) this.suspendDialogs();
    this.ports.dialogs.note.textContent = ja.rulesUnavailable;
    this.setMessage(ja.rulesUnavailable, error);
  }
  async startNewGame(options: MatchOptions, focus = true): Promise<void> {
    if (this.stopped || this.ports.render.failed() || !this.ports.render.available()) return;
    this.startRequested = true;
    const operation = this.begin();
    try {
      this.ports.render.beforeNewGame();
      await this.ports.session.newGame(options);
      if (!this.current(operation)) return;
      const state = this.ports.session.state;
      if (!state.view || state.error) {
        this.rulesFailed(state.error ?? '');
        return;
      }
      this.startRequested = false;
      if (this.ports.dialogs.match.open) {
        this.matchStarted = true;
        this.ports.dialogs.match.close();
      }
      this.adopt(state.view, focus);
      this.savingSuppressed = false;
      this.persistGame(true);
    } catch (error) {
      if (this.current(operation))
        this.rulesFailed(error instanceof Error ? error.message : String(error));
    } finally {
      if (this.current(operation)) {
        this.working = false;
        this.savingSuppressed = false;
        this.ports.render.changed();
      }
    }
  }
  async restore(save: SavedMatch, focus = true): Promise<void> {
    if (this.stopped || this.ports.render.failed() || !this.ports.render.available()) return;
    const operation = this.begin();
    try {
      const view = await this.ports.session.restoreReplay(save.replay, save.match);
      if (!this.current(operation)) return;
      this.present = true;
      this.adopt(view, focus);
      this.setMessage(ja.saved);
    } catch (error) {
      if (this.current(operation))
        this.setMessage(ja.restoreFailed, error instanceof Error ? error.message : String(error));
    } finally {
      if (this.current(operation)) {
        this.working = false;
        this.savingSuppressed = false;
        this.persistGame();
        this.ports.render.changed();
      }
    }
  }
  async inspectStored(): Promise<void> {
    if (this.stopped || this.working || !this.candidate) return;
    const candidate = this.candidate;
    const operation = ++this.generation;
    try {
      await this.ports.inspectReplay(candidate);
      if (!this.current(operation) || candidate !== this.candidate) return;
      this.ports.render.rulesFault(false);
      this.choice = 'pending';
      this.setMessage(ja.resumePrompt);
    } catch (error) {
      if (!this.current(operation) || candidate !== this.candidate) return;
      if (
        error instanceof RulesBridgeError &&
        (error.code === 'INVALID_REPLAY' || error.code === 'INVALID_JSON')
      ) {
        this.choice = 'corrupt';
        this.candidate = null;
        this.setMessage(ja.saveCorrupt, error.code);
      } else {
        this.ports.render.rulesFault(true);
        this.suspendDialogs();
        this.setMessage(
          ja.rulesUnavailable,
          error instanceof Error ? error.message : String(error),
        );
      }
    }
  }
  clearSave(fromStartup = false): boolean {
    // Clearing must not invalidate an accepted, still-committing match operation.
    if (this.stopped || this.working) return false;
    const outcome = this.ports.repository.clearGame();
    if (outcome.status === 'ok') {
      ++this.generation;
      this.present = false;
      this.candidate = null;
      if (fromStartup) this.choice = 'cleared';
      else this.lastAttemptTag = this.saveTag(this.ports.session.state);
      this.setMessage(fromStartup ? ja.saveClearedStartup : ja.saveCleared);
      if (!fromStartup) this.ports.render.focusSave();
    } else this.setMessage(ja.storageUnavailable);
    return outcome.status === 'ok';
  }
  showMatch(): void {
    if (!this.stopped) this.currentScreen = 'match';
  }
  showTitle(): void {
    if (!this.stopped) this.currentScreen = 'title';
  }
  showStartup(): void {
    if (this.stopped || this.ports.session.state.view) return;
    this.showTitle();
    this.ports.render.syncActivity();
    this.ports.render.changed();
  }
  openMatchDialog(fromStartup = false): void {
    const dialogs = this.ports.dialogs;
    if (
      this.stopped ||
      this.working ||
      !this.ports.render.available() ||
      this.ports.render.failed() ||
      dialogs.match.open
    )
      return;
    if (dialogs.result.open) dialogs.result.close();
    this.suppressMatchClose = false;
    if (dialogs.help.open) dialogs.help.close();
    if (dialogs.restart.open) dialogs.restart.close();
    dialogs.note.textContent = this.present
      ? '開始すると今の対局と保存した進行を置き換えます。開始するまでは変更しません。'
      : ja.newMatchHint;
    dialogs.start.textContent = fromStartup && this.present ? ja.discardStart : ja.startMatch;
    dialogs.match.showModal();
    this.ports.render.changed();
  }
  matchClosed(fault: boolean): void {
    const suppressed = this.suppressMatchClose || fault || this.matchStarted;
    this.suppressMatchClose = false;
    this.matchStarted = false;
    if (!suppressed && !this.stopped)
      (this.currentScreen === 'title'
        ? this.ports.dialogs.startupNew
        : this.ports.dialogs.newGame
      ).focus({ preventScroll: true });
    if (!this.stopped) this.ports.render.changed();
  }
  openMenu(): void {
    this.suppressMenuClose = false;
    this.ports.dialogs.menu.showModal();
    this.ports.render.changed();
  }
  closeMenuForTitle(): void {
    this.suppressMenuClose = true;
    this.ports.dialogs.menu.close();
  }
  menuClosed(fault: boolean): void {
    if (!this.stopped && !this.suppressMenuClose && !fault)
      this.ports.dialogs.openMenu.focus({ preventScroll: true });
    this.suppressMenuClose = false;
    if (!this.stopped) this.ports.render.changed();
  }
  suspendDialogs(): void {
    // A renderer fault suspends dialogs, not an already confirmed match change.
    // Keep its operation/save scope until the session finishes or is superseded.
    this.suppressMatchClose = true;
    this.suppressMenuClose = true;
    this.matchStarted = false;
    for (const dialog of [
      this.ports.dialogs.result,
      this.ports.dialogs.match,
      this.ports.dialogs.menu,
      this.ports.dialogs.help,
      this.ports.dialogs.restart,
    ])
      if (dialog.open) dialog.close();
  }
  setPageSuspended(value: boolean): void {
    if (this.stopped || this.pageHidden === value) return;
    this.pageHidden = value;
    this.ports.render.syncActivity();
    this.ports.render.changed();
  }
  dispose(): void {
    this.stopped = true;
    ++this.generation;
  }
}

// Cache suspension keeps listeners, renderer, audio and the committed session alive.
// Irreversible teardown is reserved for a document that will not be restored.
export function installPageLifecycle(
  target: EventTarget,
  controller: MatchUiController,
  dispose: () => void,
  signal: AbortSignal,
): void {
  target.addEventListener(
    'pagehide',
    (event) => {
      if ((event as PageTransitionEvent).persisted) controller.setPageSuspended(true);
      else dispose();
    },
    { signal },
  );
  target.addEventListener(
    'pageshow',
    (event) => {
      if ((event as PageTransitionEvent).persisted) controller.setPageSuspended(false);
    },
    { signal },
  );
}
