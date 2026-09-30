import { RulesClient, validateReplayShape, type GameView, type SavedGame } from '@quoridor/engine-bridge';

export type ReviewState = Readonly<{ phase: 'closed' | 'loading' | 'ready' | 'error';
  ply: number; total: number; view: GameView | null; error: string | null }>;
const initial: ReviewState = { phase: 'closed', ply: 0, total: 0, view: null, error: null };

/** Owns a disposable copy of a completed game. Seeking never touches the live session or storage. */
export class ReviewController {
  private client: RulesClient | null = null;
  private replay: SavedGame | null = null;
  private generation = 0;
  private stateValue: ReviewState = initial;
  private listeners = new Set<() => void>();
  get state(): ReviewState { return this.stateValue; }
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener); return () => this.listeners.delete(listener);
  }
  private set(state: ReviewState): void {
    this.stateValue = state; for (const listener of this.listeners) listener();
  }
  async open(save: SavedGame): Promise<void> {
    this.close();
    const generation = this.generation;
    this.set({ ...initial, phase: 'loading' });
    let client: RulesClient | null = null;
    try {
      const replay = validateReplayShape(structuredClone(save));
      client = await RulesClient.createGame(replay.initialConfig);
      if (generation !== this.generation) { client.dispose(); return; }
      const view = client.importReplay(replay);
      if (view.winner === null) throw new Error('Only completed games can be reviewed');
      this.client = client; this.replay = replay;
      this.set({ phase: 'ready', ply: view.ply, total: replay.ply, view, error: null });
    } catch (error) {
      client?.dispose();
      if (generation === this.generation) this.set({ ...initial, phase: 'error',
        error: error instanceof Error ? error.message : String(error) });
    }
  }
  seek(ply: number): void {
    if (!this.client || !this.replay || this.stateValue.phase !== 'ready' || !Number.isInteger(ply) ||
      ply < 0 || ply > this.replay.ply || ply === this.stateValue.ply) return;
    try {
      let view = this.client.getView();
      if (ply < view.ply) view = this.client.undoToPly(ply);
      // undo truncates the review client's history; the untouched replay retains future actions.
      while (view.ply < ply) view = this.client.applyAction(this.replay.actions[view.ply]!);
      this.set({ ...this.stateValue, ply: view.ply, view, error: null });
    } catch (error) {
      this.set({ ...this.stateValue, phase: 'error',
        error: error instanceof Error ? error.message : String(error) });
    }
  }
  close(): void {
    ++this.generation; this.client?.dispose(); this.client = null; this.replay = null;
    this.set(initial);
  }
  dispose(): void { this.close(); this.listeners.clear(); }
}
