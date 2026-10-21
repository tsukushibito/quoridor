import test from 'node:test';
import assert from 'node:assert/strict';
import { loadTs } from './ts-fixture.mjs';

const source = (name) => new URL(`../../apps/web/src/games/othello/${name}.ts`, import.meta.url);
const { createSession } = await loadTs(source('session'), {});
const { createRepository, validateSaved, SAVE_KEY } = await loadTs(source('storage'), {});
const { createAIClient } = await loadTs(source('ai-client'), {});
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
const flush = async () => {
  for (let i = 0; i < 15; i++) await Promise.resolve();
};
const initial = () => ({
  version: 1,
  board: Array.from({ length: 64 }, (_, i) =>
    i === 27 || i === 36 ? 2 : i === 28 || i === 35 ? 1 : 0,
  ),
  toMove: 1,
});
const saved = (state = initial(), mode = 'local', humanSide = 1) => ({
  version: 1,
  game: 'othello',
  state,
  mode,
  humanSide,
});
const startingStatus = () => ({
  black: 2,
  white: 2,
  legalMoves: [19, 26, 37, 44],
  mustPass: false,
  terminal: false,
  winner: null,
});
function fixture(overrides = {}) {
  const writes = [],
    calls = [],
    changes = [];
  let view;
  const next = { ...initial(), toMove: 2 };
  next.board[19] = 1;
  next.board[27] = 1;
  const rules = {
    newGame: async () => initial(),
    status: async (state) =>
      state.toMove === 1
        ? startingStatus()
        : { ...startingStatus(), black: 4, white: 1, legalMoves: [18] },
    play: async (state, index) => {
      calls.push(['play', state, index]);
      return next;
    },
    pass: async (state) => {
      calls.push(['pass', state]);
      return { ...state, toMove: state.toMove === 1 ? 2 : 1 };
    },
    ...overrides.rules,
  };
  let cancels = 0;
  const ai = {
    choose: async () => 19,
    cancel: () => {
      cancels++;
    },
    ...overrides.ai,
  };
  const repository = {
    load: async () => saved(),
    save: (value) => writes.push(structuredClone(value)),
    ...overrides.repository,
  };
  const session = createSession({
    rules,
    ai,
    repository,
    changed: (value) => {
      view = value;
      changes.push(value);
    },
  });
  return {
    session,
    writes,
    calls,
    changes,
    rules,
    ai,
    get view() {
      return view;
    },
    get cancels() {
      return cancels;
    },
  };
}

test('storage reads/writes only its versioned key and never deletes corrupt or inaccessible saves', async () => {
  const values = new Map([
    ['quoridor.m1.game.v1', 'legacy-game'],
    ['quoridor.m1.settings.v1', 'legacy-settings'],
    ['quoridor.audio.v1', 'legacy-audio'],
  ]);
  const writes = [];
  const repository = createRepository(() => ({
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      writes.push(key);
      values.set(key, value);
    },
  }));
  const checked = [];
  const rules = {
    status: async (state) => {
      checked.push(state);
      return startingStatus();
    },
  };
  await assert.rejects(repository.load(rules));
  repository.save(saved());
  assert.equal(writes[0], SAVE_KEY);
  assert.deepEqual(JSON.parse(JSON.stringify(await repository.load(rules))), saved());
  assert.equal(checked.length, 1);
  values.set(SAVE_KEY, '{broken');
  await assert.rejects(repository.load(rules));
  assert.equal(values.get(SAVE_KEY), '{broken');
  assert.equal(values.get('quoridor.m1.game.v1'), 'legacy-game');
  assert.equal(values.get('quoridor.m1.settings.v1'), 'legacy-settings');
  assert.equal(values.get('quoridor.audio.v1'), 'legacy-audio');
  const blocked = createRepository(() => {
    throw new Error('denied');
  });
  await assert.rejects(blocked.load(rules), /denied/);
  assert.throws(() => blocked.save(saved()), /denied/);
});

test('save envelope is strict; Rust owns all board validation and rejects unknown/malformed states', async () => {
  let validations = 0;
  const rules = {
    status: async () => {
      validations++;
      return startingStatus();
    },
  };
  for (const value of [
    null,
    [],
    {},
    { ...saved(), version: 2 },
    { ...saved(), game: 'quoridor' },
    { ...saved(), mode: 'learned' },
    { ...saved(), humanSide: 0 },
    { ...saved(), humanSide: '1' },
    { ...saved(), extra: 1 },
  ]) {
    await assert.rejects(validateSaved(value, rules));
  }
  assert.equal(validations, 0);
  const malformed = { ...saved(), state: { ...initial(), board: [9], extra: 1 } };
  await assert.rejects(
    validateSaved(malformed, {
      status: async (state) => {
        assert.equal(state, malformed.state);
        throw new Error('Rust invalid state');
      },
    }),
    /Rust invalid state/,
  );
  assert.equal(await validateSaved(saved(), rules).then((s) => s.state.board.length), 64);
});

test('session does not initialize rules or AI until selected; local moves use Rust results and save confirmed state', async () => {
  let initialized = 0,
    choices = 0;
  const f = fixture({
    rules: {
      newGame: async () => {
        initialized++;
        return initial();
      },
    },
    ai: {
      choose: async () => {
        choices++;
        return 19;
      },
    },
  });
  assert.equal(initialized, 0);
  await f.session.start('local', 1);
  assert.equal(initialized, 1);
  await f.session.play(0);
  assert.equal(f.calls.length, 0);
  await f.session.play(19);
  assert.equal(f.calls[0][0], 'play');
  assert.equal(f.view.status.black, 4);
  assert.equal(f.view.game.state.board[27], 1);
  assert.equal(f.writes.length, 2);
  assert.equal(choices, 0);
  f.session.dispose();
  f.session.dispose();
  assert.equal(f.writes.length, 3);
});

test('Rust-forced pass, terminal wins and draws are consumed without a JS rules implementation', async () => {
  for (const winner of [1, 2, null]) {
    let statusCalls = 0;
    const f = fixture({
      rules: {
        status: async () =>
          ++statusCalls === 1
            ? { ...startingStatus(), legalMoves: [], mustPass: true }
            : { black: 32, white: 32, legalMoves: [], mustPass: false, terminal: true, winner },
      },
    });
    await f.session.start('local', 1);
    await f.session.play(19);
    assert.equal(f.calls.length, 0);
    await f.session.pass();
    assert.equal(f.calls[0][0], 'pass');
    assert.equal(f.view.status.terminal, true);
    assert.equal(f.view.status.winner, winner);
    await f.session.pass();
    await f.session.play(19);
    assert.equal(f.calls.length, 1);
    f.session.dispose();
  }
});

test('dispose during delayed init/status/resume saves no unconfirmed state and ignores late success/failure', async () => {
  for (const stage of ['newGame', 'status', 'resume']) {
    for (const outcome of ['resolve', 'reject']) {
      const gate = deferred();
      const options =
        stage === 'resume'
          ? { repository: { load: () => gate.promise } }
          : { rules: { [stage]: () => gate.promise } };
      const f = fixture(options);
      const pending = stage === 'resume' ? f.session.resume() : f.session.start('local', 1);
      await flush();
      const count = f.changes.length;
      f.session.dispose();
      if (outcome === 'reject') gate.reject(new Error('late init failure'));
      else
        gate.resolve(
          stage === 'status' ? startingStatus() : stage === 'resume' ? saved() : initial(),
        );
      await pending;
      assert.equal(f.changes.length, count);
      assert.equal(f.writes.length, 0);
    }
  }
});

test('a newer start supersedes an older init and disposals save only the confirmed turn', async () => {
  const gate = deferred();
  let first = true;
  const f = fixture({
    rules: {
      newGame: () => {
        if (first) {
          first = false;
          return gate.promise;
        }
        return Promise.resolve(initial());
      },
    },
  });
  const old = f.session.start('ai', 2);
  await f.session.start('local', 1);
  gate.resolve(initial());
  await old;
  assert.equal(f.view.game.mode, 'local');
  assert.equal(f.writes.length, 1);
  f.session.dispose();
});

test('delayed AI results and failures cannot mutate or save after exit; human may not play AI turn', async () => {
  for (const outcome of ['resolve', 'reject']) {
    const gate = deferred();
    const f = fixture({ ai: { choose: () => gate.promise } });
    await f.session.start('ai', 2);
    assert.equal(f.view.thinking, true);
    await f.session.play(19);
    assert.equal(f.calls.length, 0);
    f.session.dispose();
    const changes = f.changes.length,
      writes = f.writes.length;
    outcome === 'resolve' ? gate.resolve(19) : gate.reject(new Error('late AI'));
    await flush();
    assert.equal(f.calls.length, 0);
    assert.equal(f.changes.length, changes);
    assert.equal(f.writes.length, writes);
    assert.equal(f.writes.at(-1).state.toMove, 1);
  }
});

test('AI errors allow retry; AI action is applied and validated by Rust; forced AI pass needs no Worker', async () => {
  let attempts = 0;
  const f = fixture({
    ai: {
      choose: async () => {
        if (++attempts === 1) throw new Error('worker failed');
        return 19;
      },
    },
  });
  await f.session.start('ai', 2);
  await flush();
  assert.match(f.view.error, /worker failed/);
  f.session.retryAI();
  await flush();
  assert.equal(f.calls[0][0], 'play');
  assert.equal(f.view.game.state.toMove, 2);
  assert.equal(f.view.status.black, 4);
  f.session.dispose();
  let calls = 0;
  const pass = fixture({
    rules: {
      status: async () =>
        ++calls === 1 ? { ...startingStatus(), legalMoves: [], mustPass: true } : startingStatus(),
    },
    ai: {
      choose: () => {
        throw new Error('must not start a Worker for pass');
      },
    },
  });
  await pass.session.start('ai', 2);
  await flush();
  assert.equal(pass.calls[0][0], 'pass');
  assert.equal(pass.view.error, '');
  pass.session.dispose();
});

test('init/resume failures permit retry and explicit new selection; save failure remains honest on exit', async () => {
  let reads = 0;
  const f = fixture({
    repository: {
      load: async () => {
        if (++reads === 1) throw new Error('bad save retained');
        return saved();
      },
      save: () => {
        throw new Error('quota');
      },
    },
  });
  await f.session.resume();
  assert.match(f.view.error, /bad save retained/);
  await f.session.resume();
  assert.match(f.view.saveMessage, /保存できません/);
  await f.session.start('local', 1);
  assert.equal(f.view.error, '');
  f.session.dispose();
  assert.match(f.session.exitWarning(), /quota/);
});

class FakeWorker {
  listeners = new Map();
  requests = [];
  stops = 0;
  addEventListener(name, fn) {
    this.listeners.set(name, fn);
  }
  removeEventListener(name) {
    this.listeners.delete(name);
  }
  postMessage(request) {
    this.requests.push(request);
  }
  terminate() {
    this.stops++;
  }
  message(data) {
    this.listeners.get('message')?.({ data });
  }
}
test('Worker client is lazy, matches both request and generation, cancels pending and terminates exactly once', async () => {
  const workers = [];
  const client = createAIClient(() => {
    const worker = new FakeWorker();
    workers.push(worker);
    return worker;
  });
  assert.equal(workers.length, 0);
  const first = client.choose(initial());
  const firstRejected = assert.rejects(first);
  const stale = workers[0].listeners.get('message');
  const second = client.choose(initial());
  await firstRejected;
  assert.equal(workers[0].stops, 1);
  const worker = workers[1],
    request = worker.requests[0];
  let resolved = false;
  void second.then(() => {
    resolved = true;
  });
  stale({ data: { ...workers[0].requests[0], ok: true, move: 19 } });
  worker.message({ ...request, generation: request.generation - 1, ok: true, move: 19 });
  worker.message({ ...request, id: request.id + 1, ok: true, move: 19 });
  await flush();
  assert.equal(resolved, false);
  worker.message({ ...request, ok: true, move: 19 });
  assert.equal(await second, 19);
  client.cancel();
  client.cancel();
  assert.equal(worker.stops, 1);
  assert.equal(worker.listeners.size, 0);
});

test('Worker errors, message errors, invalid replies and construction failures reject and can retry', async () => {
  for (const kind of ['error', 'messageerror', 'reply']) {
    const worker = new FakeWorker();
    const client = createAIClient(() => worker);
    const pending = client.choose(initial());
    const rejected = assert.rejects(pending);
    if (kind === 'reply') worker.message({ ...worker.requests[0], ok: true, move: 99 });
    else worker.listeners.get(kind)({});
    await rejected;
    client.cancel();
    assert.equal(worker.stops, 1);
  }
  const client = createAIClient(() => {
    throw new Error('construction failed');
  });
  await assert.rejects(client.choose(initial()), /construction failed/);
});

test('mount synchronously establishes abort ownership, releases DOM and ignores late initialization', async () => {
  const gate = deferred();
  let actions,
    latest,
    listenersSignal,
    releases = 0;
  const root = {
    classList: { remove() {} },
    replaceChildren() {
      releases++;
    },
  };
  const { mountOthello } = await loadTs(
    source('index'),
    {
      '../../../../../games/othello/bridge/src': {
        newGame: () => gate.promise,
        status: async () => startingStatus(),
      },
      './ai-client': { createAIClient },
      './storage': { createRepository },
      './session': { createSession },
      './view': {
        createView: (_root, signal, events) => {
          listenersSignal = signal;
          actions = events;
          return {
            render: (v) => {
              latest = v;
            },
            dispose: () => {
              releases++;
            },
          };
        },
      },
      './style.css': {},
    },
    {
      AbortController,
      localStorage: {
        getItem: () => null,
        setItem: () => {
          throw new Error('late write');
        },
      },
    },
  );
  const controller = new AbortController();
  const handle = mountOthello(root, controller.signal);
  actions.start('local', 1);
  assert.equal(latest.busy, true);
  controller.abort();
  assert.equal(listenersSignal.aborted, true);
  const before = latest;
  gate.resolve(initial());
  await flush();
  assert.equal(latest, before);
  assert.equal(releases, 2);
  assert.equal(handle.exitWarning(), undefined);
  mountOthello(root, controller.signal);
  assert.equal(releases, 3);
});

test('exit during human or AI apply/status preserves the previous confirmed state and releases the Worker', async () => {
  for (const actor of ['human', 'ai']) {
    for (const stage of ['play', 'status']) {
      const gate = deferred();
      let validations = 0;
      const f = fixture({
        rules: {
          play: async () => (stage === 'play' ? gate.promise : { ...initial(), toMove: 2 }),
          status: async () => (++validations === 1 ? startingStatus() : gate.promise),
        },
      });
      await f.session.start(actor === 'ai' ? 'ai' : 'local', actor === 'ai' ? 2 : 1);
      const pending = actor === 'human' ? f.session.play(19) : Promise.resolve();
      await flush();
      f.session.dispose();
      const count = f.changes.length;
      const cancellations = f.cancels;
      const writes = f.writes.length;
      gate.resolve(
        stage === 'play'
          ? { ...initial(), toMove: 2 }
          : { ...startingStatus(), black: 4, white: 1 },
      );
      await pending;
      await flush();
      assert.equal(f.changes.length, count);
      assert.equal(f.cancels, cancellations);
      assert.equal(f.writes.length, writes);
      assert.deepEqual(f.writes.at(-1).state, initial());
    }
  }
});

test('Worker entry delegates only the fixed bridge API and echoes correlation for success/failure', async () => {
  let reject = false;
  const responses = [],
    calls = [];
  const scope = { onmessage: null, postMessage: (response) => responses.push(response) };
  await loadTs(
    source('ai.worker'),
    {
      '../../../../../games/othello/bridge/src': {
        chooseMove: async (state) => {
          calls.push(state);
          if (reject) throw new Error('Wasm init failed');
          return 19;
        },
      },
    },
    { self: scope },
  );
  const state = initial();
  scope.onmessage({ data: { id: 7, generation: 3, state } });
  await flush();
  assert.equal(calls[0], state);
  assert.deepEqual(JSON.parse(JSON.stringify(responses[0])), {
    id: 7,
    generation: 3,
    ok: true,
    move: 19,
  });
  reject = true;
  scope.onmessage({ data: { id: 8, generation: 4, state } });
  await flush();
  assert.equal(responses[1].id, 8);
  assert.equal(responses[1].generation, 4);
  assert.equal(responses[1].ok, false);
  assert.match(responses[1].error, /Wasm init failed/);
});

test('a failed or pending resume cannot overwrite a corrupt slot with an older active match on exit', async () => {
  for (const stage of ['pending', 'failed']) {
    const gate = deferred();
    const f = fixture({ repository: { load: () => gate.promise } });
    await f.session.start('local', 1);
    assert.equal(f.writes.length, 1);
    const resuming = f.session.resume();
    if (stage === 'failed') {
      gate.reject(new Error('corrupt save retained'));
      await resuming;
    }
    f.session.dispose();
    if (stage === 'pending') {
      gate.reject(new Error('late corrupt save'));
      await resuming;
    }
    assert.equal(f.writes.length, 1, 'unreadable slot must not be replaced by teardown');
    assert.match(f.session.exitWarning(), /保存.*保持/);
  }
});
