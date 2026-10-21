import * as rules from '../../../../../games/othello/bridge/src';
import { createAIClient } from './ai-client';
import { createRepository } from './storage';
import { createSession, type Session } from './session';
import { createView } from './view';
import './style.css';

export function mountOthello(
  root: HTMLElement,
  signal: AbortSignal,
): { exitWarning(): string | undefined } {
  const lifetime = new AbortController();
  let session: Session | undefined;
  let view: ReturnType<typeof createView> | undefined;
  const handle = { exitWarning: () => session?.exitWarning() };
  function dispose(): void {
    if (lifetime.signal.aborted) return;
    lifetime.abort();
    signal.removeEventListener('abort', dispose);
    session?.dispose();
    view?.dispose();
    root.replaceChildren();
    root.classList.remove('othello');
  }
  // Establish teardown ownership before rendering, importing Wasm, or starting an async action.
  signal.addEventListener('abort', dispose, { once: true });
  if (signal.aborted) {
    dispose();
    return handle;
  }
  try {
    view = createView(root, lifetime.signal, {
      start: (mode, side) => void session?.start(mode, side),
      resume: () => void session?.resume(),
      play: (index) => void session?.play(index),
      pass: () => void session?.pass(),
      save: () => session?.save(),
      retryAI: () => session?.retryAI(),
    });
    session = createSession({
      rules,
      repository: createRepository(() => localStorage),
      ai: createAIClient(),
      changed: (state) => view?.render(state),
    });
    return handle;
  } catch (error) {
    dispose();
    throw error;
  }
}
