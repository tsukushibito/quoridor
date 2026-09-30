import { SessionController } from '../session/session-controller';
import type { BoardRenderer } from '../render/three-context';
import type { InputRouter } from '../input/input-router';
import type { AudioController } from '../audio/audio-controller';
import { GAME_KEY, SETTINGS_KEY, LocalStateRepository, validateSavedMatch, validateSettings } from '../persistence/local-state';

type Owners = { session: SessionController; audio: AudioController; board: () => BoardRenderer | null; input: () => InputRouter | null;
  dispose: () => void; restoreReplay: (save: unknown, mode: 'pvp' | 'ai', humanSide: 0 | 1) => Promise<void>;
  injectRenderFault: (kind: 'deviceLost' | 'backendError' | 'renderError') => void };
declare global {
  interface Window {
    __QUORIDOR_SESSION_TEST_API__?: { SessionController: typeof SessionController };
    __QUORIDOR_PERSISTENCE_TEST_API__?: { GAME_KEY: typeof GAME_KEY; SETTINGS_KEY: typeof SETTINGS_KEY;
      LocalStateRepository: typeof LocalStateRepository; validateSavedMatch: typeof validateSavedMatch;
      validateSettings: typeof validateSettings };
    __QUORIDOR_APP_TEST_API__?: {
      state: () => ReturnType<typeof snapshot>;
      projectCell: (cell: number) => { x: number; y: number };
      projectWall: (anchor: number) => { x: number; y: number };
      projectBoardBounds: () => ReturnType<BoardRenderer['projectBoardBounds']>;
      camera: () => [number, number, number];
      resources: () => ReturnType<BoardRenderer['diagnostics']>;
      aiDiagnostics: () => SessionController['aiDiagnostics'];
      audio: () => ReturnType<AudioController['diagnostics']>;
      exportReplay: () => ReturnType<SessionController['exportReplay']>;
      restoreReplay: (save: unknown, mode: 'pvp' | 'ai', humanSide: 0 | 1) => Promise<void>;
      injectRenderFault: Owners['injectRenderFault'];
      disposeForTest: () => void;
    };
  }
}
function snapshot(owners: Owners) {
  const state = owners.session.state;
  return { phase: state.phase, paused: state.paused, gameEpoch: state.gameEpoch, revision: state.revision,
    matchMode: state.mode, humanSide: state.humanSide, aiStats: state.aiStats ? structuredClone(state.aiStats) : null,
    view: state.view ? structuredClone(state.view) : null, selectedId: owners.input()?.selectedId() ?? null,
    mode: owners.input()?.mode ?? 'move', orientation: owners.input()?.orientation ?? 'horizontal' };
}
export function installAppTestApi(owners: Owners): void {
  const board = (): BoardRenderer => { const current = owners.board(); if (!current) throw new Error('Renderer unavailable'); return current; };
  window.__QUORIDOR_SESSION_TEST_API__ = { SessionController };
  window.__QUORIDOR_PERSISTENCE_TEST_API__ = { GAME_KEY, SETTINGS_KEY, LocalStateRepository, validateSavedMatch, validateSettings };
  window.__QUORIDOR_APP_TEST_API__ = {
    state: () => snapshot(owners),
    projectCell: cell => board().projectCell(cell),
    projectWall: anchor => board().projectWall(anchor),
    projectBoardBounds: () => board().projectBoardBounds(),
    camera: () => board().cameraPosition(),
    resources: () => board().diagnostics(),
    aiDiagnostics: () => owners.session.aiDiagnostics,
    audio: () => owners.audio.diagnostics(),
    exportReplay: () => owners.session.exportReplay(),
    restoreReplay: owners.restoreReplay,
    injectRenderFault: owners.injectRenderFault,
    disposeForTest: owners.dispose,
  };
}
