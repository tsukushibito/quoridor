import { chooseMove } from '../../../../../games/othello/bridge/src';
import type { AIRequest, AIResponse } from './ai-client';

const scope = self as unknown as {
  onmessage: ((event: MessageEvent<AIRequest>) => void) | null;
  postMessage(response: AIResponse): void;
};
scope.onmessage = (event) => {
  const { id, generation, state } = event.data;
  void chooseMove(state).then(
    (move) => scope.postMessage({ id, generation, ok: true, move }),
    (error: unknown) =>
      scope.postMessage({
        id,
        generation,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      }),
  );
};
