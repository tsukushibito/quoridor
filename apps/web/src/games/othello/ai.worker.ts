import { chooseMove, search } from '../../../../../games/othello/bridge/src';
import type { AIRequest, AIResponse } from './ai-client';

const scope = self as unknown as {
  onmessage: ((event: MessageEvent<AIRequest>) => void) | null;
  postMessage(response: AIResponse): void;
};
scope.onmessage = (event) => {
  const request = event.data;
  void (async () => {
    try {
      if (request.strategy === 'simple') {
        const move = await chooseMove(request.state);
        scope.postMessage({ ...request, move, searchResult: null, error: null });
      } else if (request.strategy === 'searchV1') {
        // Baseline v1 heuristic only, no model/global evaluator switch. This
        // synchronous Wasm call is cancelled by terminating this Worker.
        const result = await search(request.state, {
          timeMs: 1000,
          ttMiB: 32,
          maxDepth: 64,
          exactEmpties: 12,
        });
        scope.postMessage({ ...request, move: result.move, searchResult: result, error: null });
      } else {
        throw new Error('AIの方式を確認できません。');
      }
    } catch (error: unknown) {
      scope.postMessage({
        ...request,
        move: null,
        searchResult: null,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  })();
};
