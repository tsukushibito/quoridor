// Source-only transport fixtures. Scripted Rust-port outputs are not rule or
// controller implementations; real Rust/Wasm cases live in ui-wasm.test.mjs.
import assert from 'node:assert/strict';
import test from 'node:test';
import { loadTs } from './ts-fixture.mjs';

const source = (name) => new URL(`../../apps/web/src/games/othello/${name}.ts`, import.meta.url);
const { createHost } = await loadTs(source('host'), {});
const { createRepository } = await loadTs(source('storage'), {});
const { createAIClient } = await loadTs(source('ai-client'), {});
const flush = async () => {
  for (let i = 0; i < 8; i++) await Promise.resolve();
};
function deferred() {
  let resolve, reject;
  const promise = new Promise((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
}
const token = (generation, request = 1) => ({ generation, request });
const output = (generation, effects = [], extra = {}) => ({
  view: { generation, exitWarning: null, ...extra },
  effects,
});
function fixture(script) {
  const actions = [],
    writes = [],
    renders = [],
    errors = [],
    callbacks = [];
  let freed = 0,
    cancelled = 0,
    reads = 0,
    confirmations = 0;
  const ui = {
    dispatch(action) {
      actions.push(action);
      return script(action);
    },
    free() {
      freed++;
    },
  };
  const ports = {
    createUI: async () => ui,
    ai: {
      cancel() {
        cancelled++;
      },
      run(request, reply) {
        callbacks.push({ request, reply });
      },
    },
    repository: {
      read() {
        reads++;
        return '{corrupt';
      },
      write(key, raw) {
        writes.push({ key, raw });
      },
    },
    confirm() {
      confirmations++;
      return true;
    },
    render(view) {
      renders.push(view);
    },
    failure(message) {
      errors.push(message);
    },
  };
  const host = createHost(ports);
  return {
    host,
    ports,
    ui,
    actions,
    writes,
    renders,
    errors,
    callbacks,
    get freed() {
      return freed;
    },
    get cancelled() {
      return cancelled;
    },
    get reads() {
      return reads;
    },
    get confirmations() {
      return confirmations;
    },
  };
}

test('repository transfers raw bytes only and preserves other games and corrupt saves', () => {
  const data = new Map([
    ['quoridor.game.v1', 'untouched'],
    ['othello.game.v1', '{bad'],
  ]);
  const repo = createRepository(() => ({
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, raw) => data.set(key, raw),
  }));
  assert.equal(repo.read('othello.game.v1'), '{bad');
  assert.equal(data.get('othello.game.v1'), '{bad');
  repo.write('othello.game.v1', 'Rust-confirmed raw');
  assert.equal(data.get('othello.game.v1'), 'Rust-confirmed raw');
  assert.equal(data.get('quoridor.game.v1'), 'untouched');
  const denied = createRepository(() => {
    throw Error('storage denied');
  });
  assert.throws(() => denied.read('othello.game.v1'), /storage denied/);
  assert.throws(() => denied.write('othello.game.v1', 'raw'), /storage denied/);
});

test('lazy initialization is disposed before asynchronous import completes', async () => {
  const pending = deferred(),
    f = fixture(() => output(0));
  let starts = 0;
  f.ports.createUI = () => {
    starts++;
    return pending.promise;
  };
  assert.equal(starts, 0);
  f.host.send({ kind: 'resume' });
  assert.equal(starts, 1);
  f.host.dispose();
  f.host.dispose();
  pending.resolve(f.ui);
  await flush();
  assert.equal(f.freed, 1);
  assert.equal(f.actions.length, 0);
  assert.equal(f.renders.length, 0);
  assert.equal(f.writes.length, 0);
});

test('failed initialization retries and superseded initialization frees its owner', async () => {
  const pending = deferred(),
    f = fixture(() => output(2));
  let calls = 0;
  f.ports.createUI = () => {
    calls++;
    return calls === 1
      ? Promise.reject(Error('init failed'))
      : calls === 2
        ? pending.promise
        : Promise.resolve(f.ui);
  };
  f.host.send({ kind: 'resume' });
  await flush();
  assert.match(f.errors[0], /init failed/);
  f.host.send({ kind: 'resume' });
  f.host.send({ kind: 'new', mode: 'local', humanSide: 1 });
  await flush();
  let lateFreed = 0;
  pending.resolve({
    dispatch() {
      throw Error('late owner dispatched');
    },
    free() {
      lateFreed++;
    },
  });
  await flush();
  assert.equal(lateFreed, 1);
  assert.deepEqual(
    f.actions.map((a) => a.kind),
    ['new'],
  );
  f.host.dispose();
  assert.equal(f.freed, 1);
});

test('Rust generation changes synchronously cancel workers and discard old callbacks', async () => {
  const state = { version: 1, board: Array(64).fill(0), toMove: 1 };
  const f = fixture((action) =>
    action.kind === 'new'
      ? output(1, [{ kind: 'think', token: token(1), state }])
      : output(2, [{ kind: 'cancelWorker' }]),
  );
  f.host.send({ kind: 'new', mode: 'ai', humanSide: 2 });
  await flush();
  assert.equal(f.callbacks.length, 1);
  const before = f.cancelled;
  f.host.send({ kind: 'setup', mode: 'local', humanSide: 1 });
  assert.equal(f.cancelled, before + 1);
  f.callbacks[0].reply({ token: token(1), state, move: 19, error: null });
  assert.deepEqual(
    f.actions.map((a) => a.kind),
    ['new', 'setup'],
  );
  assert.equal(f.writes.length, 0);
  f.host.dispose();
  assert.equal(f.freed, 1);
});

test('revoked confirmation and pending save-read perform no browser operation', async () => {
  const f = fixture((action) =>
    action.kind === 'resume'
      ? output(3, [{ kind: 'confirm', token: token(3), message: 'confirm' }])
      : output(4, [{ kind: 'cancelWorker' }]),
  );
  f.host.send({ kind: 'resume' });
  await flush();
  assert.equal(f.confirmations, 1);
  // Start another confirmation synchronously and revoke it before its microtask.
  f.host.send({ kind: 'resume' });
  f.host.send({ kind: 'cancel' });
  await flush();
  assert.equal(f.confirmations, 1);
  const g = fixture(() =>
    output(1, [{ kind: 'readSave', token: token(1), key: 'othello.game.v1' }]),
  );
  g.host.send({ kind: 'resume' });
  await Promise.resolve();
  g.host.dispose();
  await flush();
  assert.equal(g.reads, 0);
  assert.equal(g.writes.length, 0);
  f.host.dispose();
});

test('resume forwards corrupt raw bytes and storage errors to Rust without validation or writes', async () => {
  const f = fixture((action) =>
    output(
      1,
      action.kind === 'resume'
        ? [{ kind: 'readSave', token: token(1), key: 'othello.game.v1' }]
        : [],
    ),
  );
  f.host.send({ kind: 'resume' });
  await flush();
  assert.equal(f.actions[1].kind, 'loaded');
  assert.equal(f.actions[1].raw, '{corrupt');
  assert.equal(f.actions[1].error, null);
  assert.equal(f.writes.length, 0);
  f.host.dispose();
  const g = fixture((action) =>
    output(
      2,
      action.kind === 'resume'
        ? [{ kind: 'readSave', token: token(2), key: 'othello.game.v1' }]
        : [],
    ),
  );
  g.ports.repository.read = () => {
    throw Error('read denied');
  };
  g.host.send({ kind: 'resume' });
  await flush();
  assert.match(g.actions[1].error, /read denied/);
  assert.equal(g.actions[1].raw, null);
  g.host.dispose();
});

test('only Rust write effects save; failures and final disposal acknowledge the exact token', async () => {
  const f = fixture((action) => {
    if (action.kind === 'save')
      return output(1, [
        { kind: 'writeSave', token: token(1), key: 'othello.game.v1', raw: 'confirmed' },
      ]);
    if (action.kind === 'written') return output(1, [], { exitWarning: action.error });
    return output(2, [{ kind: 'cancelWorker' }]);
  });
  f.ports.repository.write = () => {
    throw Error('quota');
  };
  f.host.send({ kind: 'save' });
  await flush();
  assert.equal(f.actions[1].kind, 'written');
  assert.equal(f.actions[1].token.request, 1);
  assert.match(f.host.exitWarning(), /quota/);
  f.host.dispose();
  assert.equal(f.writes.length, 0);
  const g = fixture((action) =>
    action.kind === 'dispose'
      ? output(7, [
          { kind: 'cancelWorker' },
          { kind: 'writeSave', token: token(7, 2), key: 'othello.game.v1', raw: 'final confirmed' },
        ])
      : output(6),
  );
  g.host.send({ kind: 'save' });
  await flush();
  g.host.dispose();
  assert.deepEqual(g.writes, [{ key: 'othello.game.v1', raw: 'final confirmed' }]);
  assert.deepEqual(
    g.actions.map((a) => a.kind),
    ['save', 'dispose', 'written'],
  );
  assert.equal(g.freed, 1);
});

class FakeWorker {
  listeners = new Map();
  sent = [];
  stopped = 0;
  addEventListener(name, listener) {
    this.listeners.set(name, listener);
  }
  removeEventListener(name, listener) {
    if (this.listeners.get(name) === listener) this.listeners.delete(name);
  }
  postMessage(request) {
    this.sent.push(request);
  }
  terminate() {
    this.stopped++;
  }
  emit(name, data) {
    this.listeners.get(name)?.({ data });
  }
}
test('transport honors Rust request identity, terminates replacements and removes all listeners', () => {
  const workers = [],
    replies = [];
  const client = createAIClient(() => {
    const w = new FakeWorker();
    workers.push(w);
    return w;
  });
  const request = {
    strategy: 'simple',
    token: token(1, 3),
    state: { version: 1, board: [], toMove: 1 },
  };
  client.run(request, (reply) => replies.push(reply));
  const oldListener = workers[0].listeners.get('message');
  workers[0].emit('message', { ...request, token: token(1, 4), move: 19, error: null });
  assert.equal(replies.length, 0);
  client.run({ ...request, token: token(2, 4) }, (reply) => replies.push(reply));
  assert.equal(workers[0].stopped, 1);
  assert.equal(workers[0].listeners.size, 0);
  oldListener({ data: { ...request, move: 19, error: null } });
  assert.equal(replies.length, 0);
  workers[1].emit('message', { ...request, token: token(2, 4), move: 19, error: null });
  assert.equal(replies.length, 1);
  assert.equal(workers[1].stopped, 1);
  assert.equal(workers[1].listeners.size, 0);
  client.cancel();
  assert.equal(workers[1].stopped, 1);
});

test('transport converts malformed/error/messageerror/construction/post failures to retryable replies', () => {
  for (const problem of ['message', 'error', 'messageerror', 'construction', 'post']) {
    const worker = new FakeWorker(),
      request = { strategy: 'simple', token: token(2, 8), state: { board: ['original'] } };
    const replies = [];
    if (problem === 'post')
      worker.postMessage = () => {
        throw Error('post failed');
      };
    const client = createAIClient(() => {
      if (problem === 'construction') throw Error('worker denied');
      return worker;
    });
    client.run(request, (reply) => replies.push(reply));
    if (['message', 'error', 'messageerror'].includes(problem))
      worker.emit(problem, { ...request, move: 99, error: null });
    assert.equal(replies.length, 1, problem);
    assert.equal(replies[0].state, request.state, problem);
    assert.equal(replies[0].move, null);
    assert.ok(replies[0].error);
    client.cancel();
  }
});

test('Worker entry echoes Rust ownership and calls only the unchanged simple policy', async () => {
  const replies = [],
    scope = { onmessage: null, postMessage: (value) => replies.push(value) };
  await loadTs(
    source('ai.worker'),
    {
      '../../../../../games/othello/bridge/src': {
        chooseMove: async () => 19,
        search: () => {
          throw Error('unexpected search');
        },
      },
    },
    { self: scope },
  );
  const request = { strategy: 'simple', token: token(4, 8), state: { board: ['opaque'] } };
  scope.onmessage({ data: request });
  await flush();
  assert.equal(replies[0].token, request.token);
  assert.equal(replies[0].state, request.state);
  assert.equal(replies[0].move, 19);
  assert.equal(replies[0].error, null);
});

test('mount owns teardown before asynchronous initialization and clears the DOM exactly once', async () => {
  const pending = deferred();
  let action,
    viewDisposed = 0,
    freed = 0,
    cleared = 0,
    rendered = 0;
  const root = {
    replaceChildren() {
      cleared++;
    },
    classList: { remove() {} },
  };
  const { mountOthello } = await loadTs(
    source('index'),
    {
      '../../../../../games/othello/bridge/src': { createUI: () => pending.promise },
      './ai-client': {
        createAIClient: () => ({
          cancel() {},
          run() {
            throw Error('unexpected AI');
          },
        }),
      },
      './storage': { createRepository },
      './host': { createHost },
      './view': {
        createView: (_root, signal, send) => {
          action = send;
          assert.equal(signal.aborted, false);
          return {
            render() {
              rendered++;
            },
            failure() {},
            dispose() {
              viewDisposed++;
            },
          };
        },
      },
      './style.css': {},
    },
    {
      AbortController,
      window: { confirm: () => true },
      localStorage: {
        getItem: () => null,
        setItem() {
          throw Error('unexpected write');
        },
      },
    },
  );
  const route = new AbortController();
  mountOthello(root, route.signal);
  action({ kind: 'resume' });
  route.abort();
  pending.resolve({
    dispatch() {
      throw Error('late dispatch');
    },
    free() {
      freed++;
    },
  });
  await flush();
  assert.equal(freed, 1);
  assert.equal(cleared, 1);
  assert.equal(viewDisposed, 1);
  assert.equal(rendered, 0);
  route.abort();
  assert.equal(cleared, 1);
  const aborted = new AbortController();
  aborted.abort();
  mountOthello(root, aborted.signal);
  assert.equal(cleared, 2);
});

test('DOM projection uses Rust labels/eligibility and releases listeners on abort', async () => {
  class Element extends EventTarget {
    dataset = {};
    children = [];
    attributes = new Map();
    hidden = false;
    disabled = false;
    focused = 0;
    value = '';
    textContent = '';
    append(child) {
      this.children.push(child);
    }
    replaceChildren() {
      this.children = [];
    }
    setAttribute(key, value) {
      this.attributes.set(key, value);
    }
    focus() {
      this.focused++;
    }
  }
  const elements = new Map();
  const root = {
    classList: { add() {} },
    innerHTML: '',
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, new Element());
      return elements.get(selector);
    },
  };
  const { createView } = await loadTs(
    source('view'),
    {},
    { document: { createElement: () => new Element() } },
  );
  const lifetime = new AbortController(),
    actions = [];
  const view = createView(root, lifetime.signal, (action) => actions.push(action));
  assert.match(root.innerHTML, /簡易AI（非学習）/);
  assert.match(root.innerHTML, /role="alert"/);
  assert.match(root.innerHTML, /aria-live="polite"/);
  const board = elements.get('.othello-board');
  assert.equal(board.children.length, 64);
  view.render({
    hasGame: true,
    strategy: 'simple',
    mode: 'ai',
    humanSide: 2,
    busy: false,
    error: 'Rust error',
    saveMessage: 'Rust save',
    title: 'Rust turn',
    players: 'Rust players',
    score: 'Rust score',
    notice: 'Rust notice',
    guide: 'Rust guide',
    passVisible: true,
    passDisabled: true,
    retryAiVisible: true,
    cancelVisible: false,
    saveDisabled: true,
    focusTurn: true,
    cells: [
      { index: 19, stone: 0, legal: true, enabled: false, label: 'D3 空き 合法手', text: '·' },
    ],
  });
  assert.equal(elements.get('#othello-turn').textContent, 'Rust turn');
  assert.equal(elements.get('#othello-error').textContent, 'Rust error');
  assert.equal(elements.get('#othello-pass').hidden, false);
  assert.equal(elements.get('#othello-pass').disabled, true);
  assert.equal(elements.get('#othello-save').disabled, true);
  assert.equal(elements.get('#othello-side-label').hidden, false);
  assert.equal(board.children[19].attributes.get('aria-disabled'), 'true');
  assert.equal(board.children[19].attributes.get('aria-label'), 'D3 空き 合法手');
  assert.equal(elements.get('#othello-turn').focused, 1);
  elements.get('#othello-mode').dispatchEvent(new Event('change'));
  assert.equal(actions[0].kind, 'setup');
  assert.equal(actions[0].mode, 'ai');
  assert.equal(actions[0].humanSide, 2);
  const arrow = new Event('keydown', { cancelable: true });
  Object.defineProperty(arrow, 'key', { value: 'ArrowRight' });
  board.children[6].dispatchEvent(arrow);
  assert.equal(board.children[7].focused, 1);
  board.children[7].dispatchEvent(arrow);
  assert.equal(board.children[8].focused, 0);
  const cell = board.children[19];
  lifetime.abort();
  view.dispose();
  cell.dispatchEvent(new Event('click'));
  assert.equal(actions.length, 1);
  assert.equal(board.children.length, 0);
});
