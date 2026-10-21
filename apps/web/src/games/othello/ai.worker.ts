import { chooseMove } from '../../../../../games/othello/bridge/src';
import type { AIRequest, AIResponse } from './ai-client';

const scope = self as unknown as {
  onmessage: ((event: MessageEvent<AIRequest>) => void) | null;
  postMessage(response: AIResponse): void;
};
scope.onmessage = (event) => {
  const { token, state } = event.data;
  void chooseMove(state).then(
    (move) => scope.postMessage({ token, state, move, error: null }),
    (error: unknown) =>
      scope.postMessage({
        token,
        state,
        move: null,
        error: error instanceof Error ? error.message : String(error),
      }),
  );
};
