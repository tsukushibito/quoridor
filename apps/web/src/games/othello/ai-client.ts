import type { GameState, UiToken } from '../../../../../games/othello/bridge/src';
export type AIRequest = { token: UiToken; state: GameState };
export type AIResponse = AIRequest & { move: number | null; error: string | null };
type WorkerPort = Pick<
  Worker,
  'postMessage' | 'terminate' | 'addEventListener' | 'removeEventListener'
>;
export type AIClient = ReturnType<typeof createAIClient>;

// Transport correlation uses Rust-issued tokens; no JS game/session generations.
export function createAIClient(
  factory: () => WorkerPort = () =>
    new Worker(new URL('./ai.worker.ts', import.meta.url), { type: 'module' }),
) {
  let active: { worker: WorkerPort; message: EventListener; failure: EventListener } | undefined;
  function cancel() {
    const old = active;
    active = undefined;
    if (!old) return;
    old.worker.removeEventListener('message', old.message);
    old.worker.removeEventListener('error', old.failure);
    old.worker.removeEventListener('messageerror', old.failure);
    old.worker.terminate();
  }
  return {
    cancel,
    run(request: AIRequest, reply: (response: AIResponse) => void) {
      cancel();
      try {
        const worker = factory();
        const message: EventListener = (event) => {
          if (active?.worker !== worker) return;
          const data = (event as MessageEvent<AIResponse>).data;
          if (
            !data ||
            data.token?.generation !== request.token.generation ||
            data.token?.request !== request.token.request
          )
            return;
          cancel();
          if (
            (data.move === null ||
              (Number.isInteger(data.move) && data.move >= 0 && data.move < 64)) &&
            (data.error === null || typeof data.error === 'string') &&
            data.state
          )
            reply(data);
          else
            reply({
              ...request,
              move: null,
              error: 'AIの応答形式を確認できません。再試行できます。',
            });
        };
        const failure: EventListener = () => {
          if (active?.worker !== worker) return;
          cancel();
          reply({
            ...request,
            move: null,
            error: '簡易AIを実行できませんでした。再試行できます。',
          });
        };
        active = { worker, message, failure };
        worker.addEventListener('message', message);
        worker.addEventListener('error', failure);
        worker.addEventListener('messageerror', failure);
        worker.postMessage(request);
      } catch (error) {
        cancel();
        reply({
          ...request,
          move: null,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    },
  };
}
