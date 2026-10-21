import test from 'node:test';
import assert from 'node:assert/strict';
import { loadTs } from './ts-fixture.mjs';

const { createNavigation, routeFromHash } = await loadTs(
  new URL('../../apps/web/src/app/navigation.ts', import.meta.url),
  {},
  { AbortController },
);
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
};
function fixture(hash = '') {
  const events = [],
    imports = [],
    signals = [];
  let location = hash;
  const module = {
    mountQuoridor(root, signal) {
      signals.push(signal);
      events.push(['mount', root]);
      signal.addEventListener('abort', () => events.push(['save', 'cancel-worker', 'dispose']));
      return { exitWarning: () => 'save warning' };
    },
  };
  const navigation = createNavigation({
    hash: () => location,
    home: (warning) => events.push(['home', warning]),
    loading: () => {
      const root = {};
      events.push(['loading']);
      return root;
    },
    load: () => {
      const pending = deferred();
      imports.push(pending);
      return pending.promise;
    },
    failed: (error) => events.push(['failed', error.message]),
  });
  return {
    navigation,
    events,
    imports,
    module,
    signals,
    go: (hash) => {
      location = hash;
      return navigation.update();
    },
  };
}

test('static-host hash routes preserve the base pathname and default unknown routes to home', () => {
  for (const path of ['https://example.test/', 'https://example.test/board/games/']) {
    assert.equal(routeFromHash(new URL(path).hash), 'home');
    assert.equal(routeFromHash(new URL('#/quoridor', path).hash), 'quoridor');
    assert.equal(new URL('#/quoridor', path).pathname, new URL(path).pathname);
  }
  assert.equal(routeFromHash('#/quoridor/'), 'quoridor');
  assert.equal(routeFromHash('#/othello'), 'home');
});

test('home does not import a game; selected entry mounts once and teardown precedes home', async () => {
  const f = fixture();
  await f.navigation.update();
  assert.equal(f.imports.length, 0);
  const opening = f.go('#/quoridor');
  assert.equal(f.imports.length, 1);
  f.imports[0].resolve(f.module);
  await opening;
  await f.go('#/quoridor/');
  assert.equal(f.imports.length, 1);
  await f.go('#/');
  assert.equal(f.signals[0].aborted, true);
  assert.deepEqual(f.events.slice(-2), [
    ['save', 'cancel-worker', 'dispose'],
    ['home', 'save warning'],
  ]);
});

test('returning home during import suppresses both late mount and late rejection', async () => {
  for (const outcome of ['resolve', 'reject']) {
    const f = fixture('#/quoridor');
    const opening = f.navigation.update();
    await f.go('#/');
    if (outcome === 'resolve') f.imports[0].resolve(f.module);
    else f.imports[0].reject(new Error('late failure'));
    await opening;
    assert.deepEqual(
      f.events.map((event) => event[0]),
      ['loading', 'home'],
    );
  }
});

test('back/forward into the game cannot adopt an older import into the new mount', async () => {
  const f = fixture('#/quoridor');
  const first = f.navigation.update();
  await f.go('#/');
  const second = f.go('#/quoridor');
  f.imports[1].resolve(f.module);
  await second;
  f.imports[0].resolve(f.module);
  await first;
  assert.equal(f.signals.length, 1);
  f.navigation.dispose();
  f.navigation.dispose();
  assert.equal(f.events.filter((event) => event[0] === 'save').length, 1);
});

test('current import failure is visible; a partially mounted game is aborted on failure', async () => {
  for (const stage of ['import', 'mount']) {
    const f = fixture('#/quoridor');
    const opening = f.navigation.update();
    if (stage === 'import') f.imports[0].reject(new Error('load failed'));
    else
      f.imports[0].resolve({
        mountQuoridor(root, signal) {
          signal.addEventListener('abort', () => f.events.push(['released']));
          throw new Error('load failed');
        },
      });
    await opening;
    assert.deepEqual(f.events.at(-1), ['failed', 'load failed']);
    if (stage === 'mount') assert.equal(f.events.at(-2)[0], 'released');
  }
});
