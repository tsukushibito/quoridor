import type { GameView } from '@quoridor/engine-bridge';
import { targetFromPlane, type Orientation, type Target } from '../render/board-coordinates';
import type { BoardRenderer } from '../render/three-context';

export type Mode = 'move' | 'wall';
type Context = { view: GameView | null; phase: string; gameEpoch: number; revision: number };
export class InputRouter {
  mode: Mode = 'move';
  orientation: Orientation = 'horizontal';
  private selection: { target: Target; gameEpoch: number; revision: number } | null = null;
  private touchSelection = false;
  private hover: Target | null = null;
  private down: { id: number; button: number; pointerType: string; x: number; y: number; dragged: boolean } | null = null;
  private readonly abort = new AbortController();
  constructor(private readonly board: BoardRenderer, private readonly context: () => Context,
    private readonly onAction: (id: number, epoch: number, revision: number) => void,
    private readonly onPreview: (target: Target | null, legal: boolean) => void,
    private readonly onModeChanged: () => void) {
    const signal = this.abort.signal;
    const canvas = board.canvas;
    canvas.addEventListener('pointerdown', event => this.pointerDown(event), { signal });
    canvas.addEventListener('pointermove', event => this.pointerMove(event), { signal });
    canvas.addEventListener('pointerup', event => this.pointerUp(event), { signal });
    canvas.addEventListener('pointercancel', () => { this.down = null; this.clear(); }, { signal });
    canvas.addEventListener('lostpointercapture', () => { if (this.down) { this.down = null; this.clear(); } }, { signal });
    canvas.addEventListener('pointerleave', () => { if (!this.down && !this.touchSelection) this.clear(); }, { signal });
    canvas.addEventListener('contextmenu', event => event.preventDefault(), { signal });
    document.addEventListener('pointerdown', event => {
      if (event.target !== canvas && !(event.target instanceof Node &&
        document.getElementById('confirm-selection')?.contains(event.target))) this.clear();
    }, { signal });
    document.addEventListener('keydown', event => this.keyDown(event), { signal });
  }
  setMode(mode: Mode): void { this.mode = mode; this.clear(); this.onModeChanged(); }
  setOrientation(orientation: Orientation): void { this.orientation = orientation; this.clear(); this.onModeChanged(); }
  toggleOrientation(): void { this.setOrientation(this.orientation === 'horizontal' ? 'vertical' : 'horizontal'); }
  clear(): void { this.selection = null; this.touchSelection = false; this.hover = null; this.renderPreview(); }
  selectedId(): number | null { return this.selection?.target.id ?? null; }
  needsConfirmation(): boolean { return this.touchSelection && this.selection !== null; }
  confirmSelection(): void {
    const state = this.active(), selection = this.selection;
    if (state && selection && selection.gameEpoch === state.gameEpoch && selection.revision === state.revision &&
      this.legal(selection.target, state)) this.onAction(selection.target.id, state.gameEpoch, state.revision);
    this.clear();
  }
  private active(): Context | null {
    const state = this.context();
    return !document.querySelector('dialog[open]') && state.phase === 'humanTurn' && state.view ? state : null;
  }
  private target(clientX: number, clientY: number): Target | null {
    const point = this.board.planePoint(clientX, clientY);
    return point ? targetFromPlane(point.x, point.z, this.mode, this.orientation) : null;
  }
  private legal(target: Target, state: Context): boolean { return state.view?.legalMask[target.id] === 1; }
  private renderPreview(): void {
    const state = this.active();
    const selected = this.selection && state && this.selection.gameEpoch === state.gameEpoch && this.selection.revision === state.revision
      ? this.selection.target : null;
    const target = state ? selected ?? this.hover : null;
    const legal = !!target && this.legal(target, state!);
    this.board.setPreview(target, legal);
    this.onPreview(target, legal);
  }
  private pointerDown(event: PointerEvent): void {
    if (event.button !== 0 && event.button !== 2) return;
    this.down = { id: event.pointerId, button: event.button, pointerType: event.pointerType,
      x: event.clientX, y: event.clientY, dragged: false };
    if (event.button === 0) this.board.canvas.focus({ preventScroll: true });
    if (event.button === 2) this.clear();
  }
  private pointerMove(event: PointerEvent): void {
    if (this.down && this.down.id === event.pointerId) {
      if (Math.hypot(event.clientX - this.down.x, event.clientY - this.down.y) > 7) {
        this.down.dragged = true; this.clear();
      }
      return;
    }
    if (!this.selection && this.active()) { this.hover = this.target(event.clientX, event.clientY); this.renderPreview(); }
  }
  private pointerUp(event: PointerEvent): void {
    const down = this.down;
    this.down = null;
    if (!down || down.id !== event.pointerId || down.button !== 0 || down.dragged ||
      Math.hypot(event.clientX - down.x, event.clientY - down.y) > 7) { this.clear(); return; }
    const target = this.target(event.clientX, event.clientY);
    if (!target || !this.active()) { this.clear(); return; }
    const state = this.active(); if (!state) { this.clear(); return; }
    if (down.pointerType === 'touch') {
      this.selection = { target, gameEpoch: state.gameEpoch, revision: state.revision };
      this.touchSelection = true;
      this.hover = null; this.renderPreview();
    } else {
      this.selection = null; this.touchSelection = false;
      if (this.legal(target, state)) { this.onAction(target.id, state.gameEpoch, state.revision); this.clear(); }
      else { this.hover = target; this.renderPreview(); }
    }
  }
  private keyDown(event: KeyboardEvent): void {
    if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
    if (document.querySelector('dialog[open]')) return;
    const focused = document.activeElement;
    if (focused !== this.board.canvas && focused !== document.body) return;
    if (event.key === 'Escape') { this.clear(); return; }
    if (event.key.toLowerCase() === 'r') { event.preventDefault(); this.toggleOrientation(); return; }
    const state = this.active(); if (!state?.view) return;
    if (event.key === 'Enter' || event.key === ' ') {
      if (this.selection) { event.preventDefault(); this.confirmSelection(); }
      return;
    }
    const delta = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] }[event.key];
    if (!delta) return;
    event.preventDefault();
    const current = this.selection?.target;
    if (this.mode === 'move') {
      const cell = current?.kind === 'pawn' ? current.id : state.view.pawns[state.view.turn]!;
      const col = Math.max(0, Math.min(8, cell % 9 + delta[0]!));
      const row = Math.max(0, Math.min(8, Math.floor(cell / 9) + delta[1]!));
      this.selection = { target: { kind: 'pawn', id: row * 9 + col }, gameEpoch: state.gameEpoch, revision: state.revision };
    } else {
      const anchor = current?.kind === 'wall' ? current.anchor : 27;
      const col = Math.max(0, Math.min(7, anchor % 8 + delta[0]!));
      const row = Math.max(0, Math.min(7, Math.floor(anchor / 8) + delta[1]!));
      const next = row * 8 + col;
      this.selection = { target: { kind: 'wall', anchor: next, orientation: this.orientation,
        id: (this.orientation === 'horizontal' ? 81 : 145) + next }, gameEpoch: state.gameEpoch, revision: state.revision };
    }
    this.touchSelection = false;
    this.renderPreview();
  }
  dispose(): void { this.abort.abort(); this.clear(); this.down = null; }
}
