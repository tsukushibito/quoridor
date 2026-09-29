import { AiClient, RulesClient, validateReplayShape, type AiStats, type GameView, type SavedGame } from '@quoridor/engine-bridge';

export type MatchMode = 'pvp' | 'ai';
export type Phase = 'booting' | 'humanTurn' | 'aiThinking' | 'animating' | 'finished' | 'recoverableError' | 'disposed';
export type SessionState = Readonly<{ phase: Phase; gameEpoch: number; revision: number; view: GameView | null;
  mode: MatchMode; humanSide: 0 | 1; simulations: number; aiStats: AiStats | null; error: string | null }>;
export type Transition = { before: GameView; after: GameView; actionId: number; gameEpoch: number; revision: number };
const initial: SessionState = { phase: 'booting', gameEpoch: 0, revision: 0, view: null,
  mode: 'pvp', humanSide: 0, simulations: 96, aiStats: null, error: null };

export class SessionController {
  private client: RulesClient | null = null;
  private readonly ai: AiClient;
  private stateValue: SessionState = initial;
  private listeners = new Set<(state: SessionState) => void>();
  private aiToken = 0;
  private transitionSink: ((transition: Transition) => void) | null = null;
  private replacementBaseline: { state: SessionState; client: RulesClient | null } | null = null;
  constructor(ai = new AiClient()) { this.ai = ai; }
  get state(): SessionState { return this.stateValue; }
  get aiDiagnostics(): ReturnType<AiClient['diagnostics']> { return this.ai.diagnostics(); }
  get aiWorkerState(): { ready: boolean; generation: number } {
    return { ready: this.ai.isReady, generation: this.ai.workerGeneration };
  }
  setTransitionSink(sink: (transition: Transition) => void): void { this.transitionSink = sink; }
  subscribe(listener: (state: SessionState) => void): () => void {
    this.listeners.add(listener); listener(this.stateValue);
    return () => this.listeners.delete(listener);
  }
  private set(next: SessionState): void {
    this.stateValue = next;
    for (const listener of this.listeners) listener(next);
  }
  private invalidateAi(): void { ++this.aiToken; this.ai.cancel(); }
  private enterTurn(): void {
    const current = this.stateValue;
    if (!current.view || current.phase === 'disposed') return;
    if (current.view.winner !== null) { this.set({ ...current, phase: 'finished', error: null, aiStats: null }); return; }
    if (current.mode === 'ai' && current.view.turn !== current.humanSide) {
      this.set({ ...current, phase: 'aiThinking', error: null, aiStats: null });
      void this.think();
    } else this.set({ ...current, phase: 'humanTurn', error: null, aiStats: null });
  }
  private async think(): Promise<void> {
    const current = this.stateValue;
    if (!this.client || current.phase !== 'aiThinking' || !current.view) return;
    const token = ++this.aiToken;
    const { gameEpoch, revision, view } = current;
    let snapshot: Uint8Array;
    try { snapshot = this.client.exportSearchSnapshot(); }
    catch (error) { this.failAi(token, error); return; }
    try {
      const result = await this.ai.search({ gameEpoch, revision, positionKey: view.positionKey,
        snapshot: new Uint8Array(snapshot), seed: '1979',
        limits: { simulations: current.simulations, maxNodes: Math.min(2048, Math.max(32, current.simulations * 2)), maxDepth: 32 },
        onProgress: stats => {
          if (token === this.aiToken && this.stateValue.phase === 'aiThinking' &&
            this.stateValue.gameEpoch === gameEpoch && this.stateValue.revision === revision)
            this.set({ ...this.stateValue, aiStats: stats });
        } });
      const now = this.stateValue;
      if (token !== this.aiToken || now.phase !== 'aiThinking' || now.gameEpoch !== gameEpoch || now.revision !== revision ||
        !now.view || now.view.positionKey !== view.positionKey || now.view.winner !== null ||
        now.mode !== 'ai' || now.view.turn === now.humanSide) return;
      const id = result.actionId;
      if (id === null || now.view.legalMask[id] !== 1) throw new Error('AI returned an illegal action');
      const after = this.client!.applyAction(id);
      const nextRevision = revision + 1;
      this.set({ ...now, phase: 'animating', revision: nextRevision, view: after, aiStats: result.stats, error: null });
      const transition: Transition = { before: now.view, after, actionId: id, gameEpoch, revision: nextRevision };
      if (this.transitionSink) this.transitionSink(transition);
      else this.finish(gameEpoch, nextRevision);
    } catch (error) { this.failAi(token, error); }
  }
  private failAi(token: number, error: unknown): void {
    if (token !== this.aiToken || this.stateValue.phase !== 'aiThinking') return;
    this.set({ ...this.stateValue, phase: 'recoverableError', error: error instanceof Error ? error.message : String(error) });
  }
  async newGame(options: { mode?: MatchMode; humanSide?: 0 | 1; simulations?: number } = {}): Promise<void> {
    if (this.stateValue.phase === 'disposed') return;
    const previous = this.stateValue;
    const mode = options.mode ?? previous.mode;
    const humanSide = options.humanSide ?? previous.humanSide;
    const simulations = options.simulations ?? previous.simulations;
    if ((mode !== 'pvp' && mode !== 'ai') || (humanSide !== 0 && humanSide !== 1) ||
      !Number.isInteger(simulations) || simulations < 0 || simulations > 4096) throw new Error('Invalid match options');
    const baseline = this.replacementBaseline ?? { state: previous, client: this.client };
    this.replacementBaseline = baseline;
    this.invalidateAi();
    const gameEpoch = previous.gameEpoch + 1;
    const revision = previous.revision + 1;
    this.set({ phase: 'booting', gameEpoch, revision, view: null, mode, humanSide, simulations, aiStats: null, error: null });
    try {
      const client = await RulesClient.createGame({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: humanSide });
      let view: GameView;
      try { view = client.getView(); } catch (error) { client.dispose(); throw error; }
      if (this.stateValue.gameEpoch !== gameEpoch) { client.dispose(); return; }
      this.client = client; this.replacementBaseline = null;
      baseline.client?.dispose();
      this.set({ ...this.stateValue, view });
      this.enterTurn();
    } catch (error) {
      if (this.stateValue.gameEpoch === gameEpoch) {
        this.replacementBaseline = null;
        this.client = baseline.client;
        const old = baseline.state, view = old.view;
        const phase = !view ? 'recoverableError' : view.winner !== null ? 'finished' :
          old.mode === 'ai' && view.turn !== old.humanSide ? 'recoverableError' : 'humanTurn';
        this.set({ ...old, phase, gameEpoch, revision, aiStats: null,
          error: error instanceof Error ? error.message : String(error) });
      }
    }
  }
  apply(actionId: number, gameEpoch: number, revision: number): Transition | null {
    const current = this.stateValue;
    if (current.phase !== 'humanTurn' || !current.view || !this.client || current.gameEpoch !== gameEpoch || current.revision !== revision ||
      (current.mode === 'ai' && current.view.turn !== current.humanSide) || current.view.legalMask[actionId] !== 1) return null;
    try {
      const after = this.client.applyAction(actionId);
      const nextRevision = revision + 1;
      this.set({ ...current, phase: 'animating', revision: nextRevision, view: after, aiStats: null, error: null });
      return { before: current.view, after, actionId, gameEpoch, revision: nextRevision };
    } catch { return null; }
  }
  finish(gameEpoch: number, revision: number): void {
    const current = this.stateValue;
    if (current.phase !== 'animating' || current.gameEpoch !== gameEpoch || current.revision !== revision || !current.view) return;
    this.enterTurn();
  }
  private undoTarget(current: SessionState): number | null {
    const view = current.view;
    if (!view || current.phase === 'disposed' || current.phase === 'booting') return null;
    // Rust's View contains the authoritative next turn, including after a win.
    // Its opposite is the most recent actor even when replay restored the history.
    const previousActor = view.turn === 0 ? 1 : 0;
    const plies = current.mode === 'pvp' || previousActor === current.humanSide ? 1 : 2;
    return view.ply >= plies ? view.ply - plies : null;
  }
  canUndo(): boolean { return this.undoTarget(this.stateValue) !== null; }
  undo(): GameView | null {
    const current = this.stateValue;
    const target = this.undoTarget(current);
    if (!this.client || target === null) return null;
    this.invalidateAi();
    try {
      const view = this.client.undoToPly(target);
      const humanTurn = current.mode === 'pvp' || view.turn === current.humanSide;
      this.set({ ...current, phase: humanTurn ? 'humanTurn' : 'recoverableError',
        revision: current.revision + 1, view, aiStats: null,
        error: humanTurn ? null : 'Undo did not return to a human decision' });
      return view;
    } catch (error) {
      if (current.mode === 'ai') this.set({ ...current, phase: 'recoverableError', aiStats: null,
        error: error instanceof Error ? error.message : String(error) });
      return null;
    }
  }
  cancelAi(): void {
    if (this.stateValue.phase !== 'aiThinking') return;
    this.invalidateAi();
    this.set({ ...this.stateValue, phase: 'recoverableError', error: 'AI search cancelled' });
  }
  retryAi(): void {
    if (this.stateValue.phase !== 'recoverableError' || !this.stateValue.view || this.stateValue.mode !== 'ai') return;
    this.enterTurn();
  }
  switchToPvp(): void {
    if (this.stateValue.phase === 'disposed' || !this.stateValue.view) return;
    this.invalidateAi();
    this.set({ ...this.stateValue, mode: 'pvp', phase: this.stateValue.view.winner === null ? 'humanTurn' : 'finished', error: null, aiStats: null });
  }
  suspendForRendererFailure(): void {
    const current = this.stateValue;
    if (current.phase === 'disposed') return;
    this.invalidateAi();
    if (!current.view || (current.phase !== 'animating' && current.phase !== 'aiThinking')) return;
    const aiTurn = current.mode === 'ai' && current.view.winner === null && current.view.turn !== current.humanSide;
    this.set({ ...current, phase: aiTurn ? 'recoverableError' : current.view.winner === null ? 'humanTurn' : 'finished',
      aiStats: null, error: aiTurn ? 'Renderer interrupted AI turn' : null });
  }
  async restoreReplay(save: unknown, options: { mode: MatchMode; humanSide: 0 | 1; simulations: number }): Promise<GameView> {
    const before = this.stateValue;
    if (before.phase === 'disposed') throw new Error('Session disposed');
    if (options.mode !== 'pvp' && options.mode !== 'ai') throw new Error('Invalid mode');
    if (options.humanSide !== 0 && options.humanSide !== 1) throw new Error('Invalid side');
    if (!Number.isInteger(options.simulations) || options.simulations < 0 || options.simulations > 4096) throw new Error('Invalid budget');
    const checked = validateReplayShape(save);
    if (checked.initialConfig.humanPlayer !== options.humanSide) throw new Error('Saved player assignment differs from match settings');
    const replacement = await RulesClient.createGame({ firstPlayer: 0, wallsPerPlayer: 10, humanPlayer: options.humanSide });
    let view: GameView;
    try { view = replacement.importReplay(checked); }
    catch (error) { replacement.dispose(); throw error; }
    if (this.stateValue.gameEpoch !== before.gameEpoch || this.stateValue.revision !== before.revision || this.stateValue.phase === 'disposed') {
      replacement.dispose(); throw new Error('Session changed during restore');
    }
    this.invalidateAi();
    this.client?.dispose(); this.client = replacement; this.replacementBaseline = null;
    this.set({ phase: 'booting', gameEpoch: before.gameEpoch + 1, revision: before.revision + 1, view,
      mode: options.mode, humanSide: options.humanSide, simulations: options.simulations, aiStats: null, error: null });
    this.enterTurn();
    return view;
  }
  exportReplay(): SavedGame { if (!this.client) throw new Error('No game'); return this.client.exportReplay(); }
  dispose(): void {
    if (this.stateValue.phase === 'disposed') return;
    this.invalidateAi(); this.ai.dispose(); this.client?.dispose(); this.client = null;
    this.replacementBaseline = null;
    this.set({ ...this.stateValue, phase: 'disposed', gameEpoch: this.stateValue.gameEpoch + 1,
      revision: this.stateValue.revision + 1, view: null, aiStats: null, error: null });
    this.listeners.clear(); this.transitionSink = null;
  }
}
