import { chooseMove, search, createFullModel } from '../../../../../games/othello/bridge/src';
import type {
  FullModel,
  FullModelSpec,
  ModelIdentity,
  UiToken,
} from '../../../../../games/othello/bridge/src';
import type { AIRequest } from './ai-client';
type Init = {
  kind: 'fullInit';
  token: UiToken;
  model: FullModelSpec;
  main: ArrayBuffer;
  ending: ArrayBuffer;
};
type FullRequest = { kind: 'fullSearch'; request: AIRequest; reset: boolean };
let model: FullModel | undefined;
let identity: ModelIdentity | undefined;
const sameIdentity = (a: ModelIdentity | undefined, b: ModelIdentity) =>
  a?.version === b.version && a.mainSha256 === b.mainSha256 && a.endingSha256 === b.endingSha256;
const detail = (e: unknown) => (e instanceof Error ? e.message : String(e));
self.onmessage = async (event: MessageEvent<AIRequest | Init | FullRequest>) => {
  const data = event.data;
  if ('kind' in data && data.kind === 'fullInit') {
    try {
      if (model) throw new Error('評価ファイルはWorkerごとに一度だけ読み込めます。');
      model = await createFullModel(
        new Uint8Array(data.main),
        new Uint8Array(data.ending),
        data.model,
      );
      model.clear();
      identity = data.model.identity;
      self.postMessage({ kind: 'fullReady', token: data.token, identity });
    } catch (e) {
      model?.free();
      model = undefined;
      identity = undefined;
      self.postMessage({ kind: 'fullError', token: data.token, error: detail(e) });
    }
    return;
  }
  if ('kind' in data && data.kind === 'fullSearch') {
    const request = data.request;
    try {
      if (
        !model ||
        !request.model ||
        request.strategy !== 'fullModel' ||
        !sameIdentity(identity, request.model.identity)
      )
        throw new Error('評価ファイルが準備されていません。');
      if (data.reset) model.clear(); // genuine Rust new-game/reset boundary, never every move
      self.postMessage({ kind: 'fullPreCall', token: request.token, identity });
      // A posted message cannot interrupt this synchronous call. The parent terminates this Worker.
      const fullResult = model.search(request.state, request.model.options);
      self.postMessage({
        kind: 'fullResult',
        token: request.token,
        state: request.state,
        strategy: request.strategy,
        move: fullResult.move,
        fullResult,
        searchResult: null,
        modelIdentity: identity,
        error: null,
      });
    } catch (e) {
      self.postMessage({ kind: 'fullError', token: request.token, error: detail(e) });
    }
    return;
  }
  if ('kind' in data) return;
  const request = data;
  try {
    const searchResult =
      request.strategy === 'searchV1'
        ? await search(request.state, {
            timeMs: 1000,
            ttMiB: 32,
            maxDepth: 64,
            exactEmpties: 12,
          })
        : null;
    if (request.strategy !== 'simple' && request.strategy !== 'searchV1')
      throw new Error('AIの方式を確認できません。');
    const move = searchResult ? searchResult.move : await chooseMove(request.state);
    self.postMessage({ ...request, move, searchResult, error: null });
  } catch (e) {
    self.postMessage({ ...request, move: null, searchResult: null, error: detail(e) });
  }
};
