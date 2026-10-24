import type {
  FullModelSpec,
  FullSearchResult,
  GameState,
  ModelIdentity,
  SearchResult,
  UiStrategy,
  UiToken,
} from '../../../../../games/othello/bridge/src';
export type ModelFiles = { main: File | null; ending: File | null };
export type AIRequest = {
  token: UiToken;
  state: GameState;
  strategy: UiStrategy;
  model?: FullModelSpec;
};
export type AIResponse = AIRequest & {
  move: number | null;
  searchResult: SearchResult | null;
  fullResult?: FullSearchResult | null;
  modelIdentity?: ModelIdentity | null;
  error: string | null;
};
export type ModelResponse = {
  identity: ModelIdentity | null;
  mainBytes: number | null;
  endingBytes: number | null;
  error: string | null;
};
type WorkerPort = Pick<
  Worker,
  'postMessage' | 'terminate' | 'addEventListener' | 'removeEventListener'
>;
type Pending = { clean(): void; fail(message: string): void };
export type AIClient = ReturnType<typeof createAIClient>;
const sameToken = (a: UiToken | undefined, b: UiToken) =>
  a?.generation === b.generation && a.request === b.request;
const sameIdentity = (a: ModelIdentity | undefined | null, b: ModelIdentity) =>
  a?.version === b.version && a.mainSha256 === b.mainSha256 && a.endingSha256 === b.endingSha256;
const detail = (e: unknown) => (e instanceof Error ? e.message : String(e));

// Rust owns game/request authority. This host owns only pending transport and local immutable Files.
export function createAIClient(
  factory: () => WorkerPort = () =>
    new Worker(new URL('./ai.worker.ts', import.meta.url), { type: 'module' }),
) {
  let worker: WorkerPort | undefined;
  let ready: ModelIdentity | undefined;
  let files: { main: File; ending: File; identity: ModelIdentity } | undefined;
  let pending: Pending | undefined;
  let closed = false;
  let resetNeeded = false;

  function finish(operation: Pending) {
    if (pending !== operation) return false;
    pending = undefined;
    operation.clean(); // revoke first; detach listeners and timer before any callback/termination
    return true;
  }
  function cancel() {
    const old = pending;
    pending = undefined;
    old?.clean();
    const previous = worker;
    worker = undefined;
    ready = undefined;
    previous?.terminate();
  }
  function forget() {
    try {
      cancel();
    } finally {
      files = undefined;
      resetNeeded = false;
    }
  }
  function operation(fail: (message: string) => void): {
    owner: Pending;
    timer(ms: number): void;
    listen(onMessage: (data: any) => void): void;
  } {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let listening: WorkerPort | undefined;
    let message: EventListener | undefined;
    let failure: EventListener | undefined;
    const owner: Pending = {
      clean() {
        if (timer !== undefined) clearTimeout(timer);
        timer = undefined;
        if (listening && message && failure) {
          listening.removeEventListener('message', message);
          listening.removeEventListener('error', failure);
          listening.removeEventListener('messageerror', failure);
        }
        listening = undefined;
      },
      fail(text) {
        if (!finish(owner)) return;
        const previous = worker;
        worker = undefined;
        ready = undefined;
        previous?.terminate();
        fail(text);
      },
    };
    pending = owner;
    return {
      owner,
      timer(ms) {
        if (timer !== undefined) clearTimeout(timer);
        timer = setTimeout(
          () => owner.fail('AIの応答が時間内に届きませんでした。再試行できます。'),
          ms,
        );
      },
      listen(onMessage) {
        if (!worker) throw new Error('AI Workerが準備されていません。');
        listening = worker;
        const target = worker;
        message = (event) => {
          if (pending === owner && worker === target) onMessage((event as MessageEvent).data);
        };
        failure = () => owner.fail('AIを実行できませんでした。再試行できます。');
        target.addEventListener('message', message);
        target.addEventListener('error', failure);
        target.addEventListener('messageerror', failure);
      },
    };
  }
  async function buffers(main: File, ending: File, spec: FullModelSpec, verify: boolean) {
    if (main.size !== spec.mainBytes || ending.size !== spec.endingBytes)
      throw new Error('評価ファイルのサイズが一致しません。指定の2ファイルを選択してください。');
    const values = await Promise.all([main.arrayBuffer(), ending.arrayBuffer()]);
    if (verify) {
      const hex = async (buffer: ArrayBuffer) =>
        Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', buffer)), (b) =>
          b.toString(16).padStart(2, '0'),
        ).join('');
      const hashes = await Promise.all(values.map(hex));
      if (hashes[0] !== spec.identity.mainSha256 || hashes[1] !== spec.identity.endingSha256)
        throw new Error('評価ファイルの内容が一致しません。指定の2ファイルを選択してください。');
    }
    return values;
  }
  // One transfer/decode per Worker. Immutable File handles are retained for an explicit retry.
  function initialize(
    token: UiToken,
    spec: FullModelSpec,
    pair: { main: File; ending: File },
    verify: boolean,
    op: ReturnType<typeof operation>,
    onReady: () => void,
  ) {
    void buffers(pair.main, pair.ending, spec, verify)
      .then((values) => {
        if (pending !== op.owner || closed) return;
        if (verify) files = { ...pair, identity: spec.identity };
        worker = factory();
        op.listen((data) => {
          if (!sameToken(data?.token, token)) return;
          if (data.kind === 'fullError') {
            op.owner.fail(String(data.error));
            return;
          }
          if (data.kind !== 'fullReady' || !sameIdentity(data.identity, spec.identity)) {
            op.owner.fail('評価ファイルの準備応答を確認できません。');
            return;
          }
          ready = spec.identity;
          if (!finish(op.owner)) return;
          onReady();
        });
        worker.postMessage(
          { kind: 'fullInit', token, model: spec, main: values[0], ending: values[1] },
          values,
        );
      })
      .catch((e) => op.owner.fail(detail(e)));
  }

  function load(
    selected: ModelFiles,
    token: UiToken,
    spec: FullModelSpec,
    reply: (value: ModelResponse) => void,
  ) {
    if (closed) return;
    forget(); // a wrong newly-selected pair must never fall back to the previous model
    const failed = (error: string) =>
      reply({ identity: null, mainBytes: null, endingBytes: null, error });
    const op = operation(failed);
    op.timer(spec.readyTimeoutMs);
    if (!selected.main || !selected.ending) {
      op.owner.fail('評価用と終盤用の2ファイルを選択してください。');
      return;
    }
    initialize(token, spec, { main: selected.main, ending: selected.ending }, true, op, () =>
      reply({
        identity: spec.identity,
        mainBytes: spec.mainBytes,
        endingBytes: spec.endingBytes,
        error: null,
      }),
    );
  }
  function run(
    request: AIRequest,
    reply: (response: AIResponse) => void,
    phase?: (value: 'initializing' | 'thinking', identity: ModelIdentity) => void,
  ) {
    if (closed) return;
    const failed = (error: string) =>
      reply({
        ...request,
        move: null,
        searchResult: null,
        fullResult: null,
        modelIdentity: request.model?.identity ?? null,
        error,
      });
    if (pending) cancel();
    const spec = request.strategy === 'fullModel' ? request.model : undefined;
    if (request.strategy === 'fullModel' && !spec) {
      failed('評価ファイルの指定を確認できません。');
      return;
    }
    const start = () => {
      if (closed) return;
      const op = operation(failed);
      try {
        if (!worker) worker = factory();
        op.listen((data) => {
          if (!sameToken(data?.token, request.token)) return;
          if (data.kind === 'fullPreCall' && spec) {
            if (sameIdentity(data.identity, spec.identity)) phase?.('thinking', spec.identity);
            else op.owner.fail('AIの評価ファイル識別子が一致しません。');
            return;
          }
          if (data.kind === 'fullError') {
            op.owner.fail(String(data.error));
            return;
          }
          if (data.kind !== undefined && data.kind !== 'fullResult') {
            op.owner.fail('AIの応答形式を確認できません。');
            return;
          }
          if (
            !(
              data.move === null ||
              (Number.isInteger(data.move) && data.move >= 0 && data.move < 64)
            ) ||
            !data.state ||
            !['simple', 'searchV1', 'fullModel'].includes(data.strategy) ||
            !(data.error === null || typeof data.error === 'string')
          ) {
            op.owner.fail('AIの応答形式を確認できません。再試行できます。');
            return;
          }
          if (!finish(op.owner)) return;
          if (!spec) {
            const old = worker;
            worker = undefined;
            ready = undefined;
            old?.terminate();
          }
          // Rust validates original state, strategy, identity, rules and the actual result schema.
          reply({
            token: data.token,
            state: data.state,
            strategy: data.strategy,
            move: data.move,
            searchResult: data.searchResult ?? null,
            fullResult: data.fullResult ?? null,
            modelIdentity: data.modelIdentity ?? null,
            error: data.error ?? null,
          });
        });
        if (spec) {
          op.timer(spec.replyTimeoutMs); // starts at ready dispatch; preCall does not restart it
          worker.postMessage({ kind: 'fullSearch', request, reset: resetNeeded });
          resetNeeded = false;
        } else worker.postMessage(request);
      } catch (e) {
        op.owner.fail(detail(e));
      }
    };
    if (!spec) {
      cancel();
      start();
      return;
    }
    if (worker && sameIdentity(ready, spec.identity)) {
      start();
      return;
    }
    cancel();
    if (!files || !sameIdentity(files.identity, spec.identity)) {
      failed('評価ファイルをもう一度選択してください。');
      return;
    }
    phase?.('initializing', spec.identity);
    const op = operation(failed);
    op.timer(spec.readyTimeoutMs);
    initialize(request.token, spec, files, false, op, start);
  }
  return {
    load,
    run,
    cancel,
    forget,
    reset() {
      resetNeeded = true;
    },
    dispose() {
      if (closed) return;
      closed = true;
      forget();
    },
  };
}
