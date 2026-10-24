import { createUI } from '../../../../../games/othello/bridge/src';
import { createAIClient } from './ai-client';
import { createRepository } from './storage';
import { createHost } from './host';
import { createView } from './view';
import './style.css';

export function mountOthello(
  root: HTMLElement,
  signal: AbortSignal,
): { exitWarning(): string | undefined } {
  const lifetime = new AbortController();
  let host: ReturnType<typeof createHost> | undefined;
  let view: ReturnType<typeof createView> | undefined;
  const handle = { exitWarning: () => host?.exitWarning() };
  function dispose() {
    if (lifetime.signal.aborted) return;
    lifetime.abort();
    signal.removeEventListener('abort', dispose);
    try {
      host?.dispose();
    } finally {
      view?.dispose();
      root.replaceChildren();
      root.classList.remove('othello');
    }
  }
  // Teardown is owned before DOM creation or the first asynchronous Wasm load.
  signal.addEventListener('abort', dispose, { once: true });
  if (signal.aborted) {
    dispose();
    return handle;
  }
  try {
    host = createHost({
      createUI,
      ai: createAIClient(),
      repository: createRepository(() => localStorage),
      confirm: (message) => window.confirm(message),
      render: (state) => view?.render(state),
      failure: (message) => view?.failure(message),
      clearModelFiles: () => view?.clearModelFiles(),
    });
    view = createView(
      root,
      lifetime.signal,
      (action) => host?.send(action),
      (files) => host?.selectModelFiles(files),
    );
    return handle;
  } catch (error) {
    dispose();
    throw error;
  }
}
