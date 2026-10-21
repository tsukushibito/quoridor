import type { GameState } from '../../../../../games/othello/bridge/src';

export type AIRequest = { id: number; generation: number; state: GameState };
export type AIResponse = {
  id: number;
  generation: number;
} & ({ ok: true; move: number | null } | { ok: false; error: string });
type WorkerPort = Pick<
  Worker,
  'postMessage' | 'terminate' | 'addEventListener' | 'removeEventListener'
>;
export type AIClient = ReturnType<typeof createAIClient>;

export function createAIClient(
  factory: () => WorkerPort = () =>
    new Worker(new URL('./ai.worker.ts', import.meta.url), { type: 'module' }),
) {
  let worker: WorkerPort | undefined;
  let sequence = 0;
  let generation = 0;
  let pending:
    | {
        id: number;
        generation: number;
        resolve(move: number | null): void;
        reject(error: Error): void;
      }
    | undefined;
  function stop(): void {
    generation++;
    const old = pending;
    pending = undefined;
    old?.reject(new Error('AIの処理を取り消しました。'));
    if (worker) {
      worker.removeEventListener('message', message);
      worker.removeEventListener('error', failure);
      worker.removeEventListener('messageerror', failure);
      worker.terminate();
      worker = undefined;
    }
  }
  function message(event: Event): void {
    const data = (event as MessageEvent<AIResponse>).data;
    if (!pending || !data || data.id !== pending.id || data.generation !== pending.generation)
      return;
    const current = pending;
    pending = undefined;
    if (
      data.ok === true &&
      (data.move === null || (Number.isInteger(data.move) && data.move >= 0 && data.move < 64))
    )
      current.resolve(data.move);
    else
      current.reject(new Error(data.ok === false ? data.error : 'AIの応答形式を確認できません。'));
  }
  function failure(): void {
    const current = pending;
    pending = undefined;
    current?.reject(new Error('簡易AIを実行できませんでした。再試行できます。'));
    stop();
  }
  return {
    choose(state: GameState): Promise<number | null> {
      stop();
      return new Promise((resolve, reject) => {
        try {
          worker = factory();
          worker.addEventListener('message', message);
          worker.addEventListener('error', failure);
          worker.addEventListener('messageerror', failure);
          pending = { id: ++sequence, generation, resolve, reject };
          worker.postMessage({ id: sequence, generation, state } satisfies AIRequest);
        } catch (error) {
          stop();
          reject(error instanceof Error ? error : new Error(String(error)));
        }
      });
    },
    cancel: stop,
  };
}
