import type {
  UiAction,
  UiController,
  UiEffect,
  UiToken,
  UiView,
} from '../../../../../games/othello/bridge/src';
import type { AIClient, ModelFiles } from './ai-client';
import type { Repository } from './storage';

export function createHost(ports: {
  createUI(): Promise<UiController>;
  ai: AIClient;
  repository: Repository;
  confirm(message: string): boolean;
  render(view: UiView): void;
  failure(message: string): void;
  clearModelFiles?(): void;
}) {
  let owner: UiController | undefined;
  let selected: ModelFiles = { main: null, ending: null };
  let closed = false;
  let boot = 0; // async import ownership only; game/request ownership lives in Rust
  let generation = -1;
  let warning: string | undefined;
  const detail = (e: unknown) => (e instanceof Error ? e.message : String(e));
  const owned = (token: UiToken) => !closed && !!owner && token.generation === generation;
  function dispatch(action: UiAction, final = false): void {
    if (!owner || (closed && !final)) return;
    const output = owner.dispatch(action);
    generation = output.view.generation;
    warning = output.view.exitWarning ?? undefined;
    if (!closed) ports.render(output.view);
    for (const effect of output.effects) execute(effect, final);
  }
  function execute(effect: UiEffect, final: boolean): void {
    if (effect.kind === 'cancelWorker') {
      ports.ai.cancel();
      return;
    }
    if (effect.kind === 'resetModel') {
      ports.ai.reset();
      return;
    }
    if (effect.kind === 'forgetModel') {
      ports.ai.forget();
      selected = { main: null, ending: null };
      ports.clearModelFiles?.();
      return;
    }
    if (!(final && effect.kind === 'writeSave') && !owned(effect.token)) return;
    if (effect.kind === 'loadModel') {
      ports.ai.load(selected, effect.token, effect.spec, (reply) => {
        if (owned(effect.token)) dispatch({ kind: 'modelReply', token: effect.token, ...reply });
      });
    } else if (effect.kind === 'writeSave') {
      let error: string | null = null;
      try {
        ports.repository.write(effect.key, effect.raw);
      } catch (e) {
        error = detail(e);
      }
      dispatch({ kind: 'written', token: effect.token, error }, final);
    } else if (effect.kind === 'readSave') {
      void Promise.resolve()
        .then(() => (owned(effect.token) ? ports.repository.read(effect.key) : null))
        .then(
          (raw) => {
            if (owned(effect.token))
              dispatch({ kind: 'loaded', token: effect.token, raw, error: null });
          },
          (e) => {
            if (owned(effect.token))
              dispatch({ kind: 'loaded', token: effect.token, raw: null, error: detail(e) });
          },
        );
    } else if (effect.kind === 'confirm') {
      void Promise.resolve()
        .then(() => (owned(effect.token) ? ports.confirm(effect.message) : false))
        .then(
          (accepted) => {
            if (owned(effect.token)) dispatch({ kind: 'confirm', token: effect.token, accepted });
          },
          (e) => {
            if (owned(effect.token))
              dispatch({ kind: 'confirm', token: effect.token, accepted: false, error: detail(e) });
          },
        );
    } else if (effect.kind === 'think') {
      ports.ai.run(
        {
          token: effect.token,
          state: effect.state,
          strategy: effect.strategy,
          ...(effect.model === undefined ? {} : { model: effect.model }),
        },
        (reply) => {
          if (!owned(effect.token)) return;
          try {
            dispatch({
              kind: 'aiReply',
              token: reply.token,
              state: reply.state,
              strategy: reply.strategy,
              move: reply.move,
              searchResult: reply.searchResult,
              fullResult: reply.fullResult ?? null,
              modelIdentity: reply.modelIdentity ?? null,
              error: reply.error,
            });
          } catch (e) {
            dispatch({
              kind: 'aiReply',
              token: effect.token,
              state: effect.state,
              strategy: effect.strategy,
              move: null,
              searchResult: null,
              error: detail(e),
            });
          }
        },
        (phase, modelIdentity) => {
          if (owned(effect.token))
            dispatch({ kind: 'aiPhase', token: effect.token, phase, modelIdentity });
        },
      );
    }
  }
  function send(action: UiAction): void {
    if (closed) return;
    if (owner) {
      dispatch(action);
      return;
    }
    const ticket = ++boot;
    ports.ai.cancel();
    void ports
      .createUI()
      .then((ui) => {
        if (closed || ticket !== boot) {
          ui.free();
          return;
        }
        owner = ui;
        dispatch(action);
      })
      .catch((e) => {
        if (!closed && ticket === boot)
          ports.failure('Othelloを読み込めませんでした。再試行できます。' + detail(e));
      });
  }
  return {
    send,
    selectModelFiles(value: ModelFiles): void {
      if (closed) return;
      selected = value;
      send({ kind: 'modelFilesChanged' });
    },
    dispose(): void {
      if (closed) return;
      closed = true;
      boot++;
      try {
        ports.ai.dispose();
      } finally {
        selected = { main: null, ending: null };
        if (owner) {
          try {
            dispatch({ kind: 'dispose' }, true);
          } finally {
            owner.free();
            owner = undefined;
          }
        }
      }
    },
    exitWarning: () => warning,
  };
}
