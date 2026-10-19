import test from 'node:test';
import { registerHooks } from 'node:module';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
  existsSync,
  unlinkSync,
  chmodSync,
  lstatSync,
  readdirSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { exportSource } from '../../scripts/export-fresh-source.mjs';
function fixture(t) {
  const base = mkdtempSync(join(tmpdir(), 'source-export-contract-')),
    root = join(base, 'source'),
    destination = join(base, 'export');
  mkdirSync(root);
  writeFileSync(join(root, 'code.py'), 'print("source only")\n');
  t.after(() => rmSync(base, { recursive: true }));
  return { base, root, destination };
}
test('source export binds current bytes and protects existing destination', (t) => {
  const f = fixture(t),
    result = exportSource({ ...f, paths: ['code.py'] });
  assert.equal(result.entries.length, 1);
  assert.equal(readFileSync(join(f.destination, 'code.py'), 'utf8'), 'print("source only")\n');
  assert.throws(() => exportSource({ ...f, paths: ['code.py'] }), /DESTINATION_EXISTS/);
  assert.equal(result.index_changed, false);
});
test('invalid, science, temp, symlink and oversize sources refuse before creating output', (t) => {
  const f = fixture(t);
  mkdirSync(join(f.root, 'research-data'));
  writeFileSync(join(f.root, 'research-data/raw.json'), '{}');
  writeFileSync(join(f.root, ':memory:.ses'), 'temporary');
  symlinkSync(join(f.root, 'code.py'), join(f.root, 'link.py'));
  for (const paths of [
    ['../source/code.py'],
    ['research-data/raw.json'],
    [':memory:.ses'],
    ['link.py'],
    ['code.py', 'code.py'],
  ]) {
    assert.throws(() => exportSource({ ...f, paths }));
    assert.equal(existsSync(f.destination), false);
  }
  assert.throws(() => exportSource({ ...f, paths: ['code.py'], maxBytes: 1 }), /OUTPUT_FORECAST/);
  assert.equal(existsSync(f.destination), false);
});
test('destination and scope are explicit; tracked source tree is never replaced', (t) => {
  const f = fixture(t);
  assert.throws(() => exportSource({ root: f.root, paths: ['code.py'] }), /EXPLICIT_DESTINATION/);
  assert.throws(() => exportSource(f), /EXACTLY_ONE_SCOPE/);
  assert.throws(
    () => exportSource({ ...f, destination: join(f.root, 'new-code'), paths: ['code.py'] }),
    /LIVE_OR_EXTERNAL/,
  );
  assert.equal(readFileSync(join(f.root, 'code.py'), 'utf8'), 'print("source only")\n');
});

function allocated(path) {
  const stat = lstatSync(path);
  return (
    stat.blocks * 512 +
    (stat.isDirectory()
      ? readdirSync(path).reduce((bytes, child) => bytes + allocated(join(path, child)), 0)
      : 0)
  );
}
for (const layout of ['tiny', 'deep', 'long']) {
  test(`allocated forecast includes exact manifest and ${layout} paths before destination creation`, (t) => {
    const f = fixture(t);
    const paths =
      layout === 'tiny'
        ? Array.from({ length: 32 }, (_, index) => `tiny-${index}.py`)
        : layout === 'deep'
          ? ['a/b/c/d/e/f/g/h/file.py']
          : Array.from(
              { length: 6 },
              (_, index) =>
                `${('long-directory-name-'.repeat(6) + '/').repeat(10)}file-${index}.py`,
            );
    for (const path of paths) {
      mkdirSync(join(f.root, path, '..'), { recursive: true });
      writeFileSync(join(f.root, path), 'x');
    }
    assert.throws(() => exportSource({ ...f, paths, maxBytes: 5000 }), /OUTPUT_FORECAST/);
    assert.equal(existsSync(f.destination), false);
    const manifest = exportSource({ ...f, paths });
    assert.equal(
      manifest.manifest_bytes,
      readFileSync(join(f.destination, 'source-manifest.json')).length,
    );
    assert.ok(allocated(f.destination) <= manifest.forecast_bytes);
    const second = join(f.base, 'too-small');
    assert.throws(
      () =>
        exportSource({ ...f, destination: second, paths, maxBytes: manifest.forecast_bytes - 1 }),
      /OUTPUT_FORECAST/,
    );
    assert.equal(existsSync(second), false);
  });
}
test('scope export retains current modified/untracked bytes, omits tracked deletion and preserves index', (t) => {
  const f = fixture(t);
  const git = (...args) => execFileSync('git', ['-C', f.root, ...args], { timeout: 15000 });
  git('init', '--initial-branch=main');
  git('config', 'user.name', 'Fixture');
  git('config', 'user.email', 'fixture@example.invalid');
  writeFileSync(join(f.root, 'Cargo.toml'), '# tracked old\n');
  writeFileSync(join(f.root, 'README.md'), 'old\n');
  git('add', '.');
  git('commit', '-qm', 'fixture');
  unlinkSync(join(f.root, 'Cargo.toml'));
  writeFileSync(join(f.root, 'README.md'), 'current bytes\n');
  mkdirSync(join(f.root, 'scripts'));
  writeFileSync(join(f.root, 'scripts/new.mjs'), 'export const value = 1;\n');
  const before = readFileSync(join(f.root, '.git/index'));
  const result = exportSource({ ...f, scope: 'product' });
  assert.deepEqual(
    result.entries.map((entry) => entry.path),
    ['README.md', 'scripts/new.mjs'],
  );
  assert.equal(readFileSync(join(f.destination, 'README.md'), 'utf8'), 'current bytes\n');
  assert.equal(
    readFileSync(join(f.destination, 'scripts/new.mjs'), 'utf8'),
    'export const value = 1;\n',
  );
  assert.deepEqual(readFileSync(join(f.root, '.git/index')), before);
  assert.throws(
    () => exportSource({ ...f, destination: join(f.base, 'missing'), paths: ['Cargo.toml'] }),
    /ENOENT/,
  );
});

// Link the actual exporter to explicit filesystem ports; synthetic growth stays
// in bounded RAM and never writes a 1 MiB fixture to the task's artifact store.
let mockId = 0;
async function mutableSource(event, collision, failWrite = false) {
  const url = new URL('../../scripts/export-fresh-source.mjs', import.meta.url);
  const imported = url.href + '?mutation=' + ++mockId;
  const key = '__exportFixture' + mockId;
  let source = Buffer.from('x'),
    mode = 0;
  const files = new Map(),
    dirs = new Set(['/source', '/fixture']),
    writes = [];
  const output = '/fixture/export/code.py';
  const io = {
    existsSync: (path) => files.has(path) || dirs.has(path),
    realpathSync: (path) => path,
    statfsSync: () => ({ bsize: 4096 }),
    lstatSync: () => ({
      size: source.length,
      mode: 0o100761,
      isFile: () => true,
      isSymbolicLink: () => false,
    }),
    readFileSync: (path) => Buffer.from(path === '/source/code.py' ? source : files.get(path)),
    mkdirSync: (path) => {
      dirs.add(path);
      if (path === '/fixture/export' && collision) files.set(collision, Buffer.from('keep'));
    },
    writeFileSync: (path, bytes, options) => {
      writes.push({ path, flag: options.flag, bytes: Buffer.byteLength(bytes) });
      if (options.flag !== 'wx') throw Error('Exclusive write required');
      if (files.has(path)) throw Error('EEXIST');
      if (path === output && event) source = Buffer.alloc(1024 * 1024, event === 'grow' ? 1 : 2);
      files.set(path, Buffer.from(bytes));
      if (path === output) mode = options.mode & ~0o077;
      if (path === output && failWrite) throw Error('EIO');
    },
    chmodSync: (path, bits) => {
      if (path === output) mode = bits;
    },
    copyFileSync: () => {
      throw Error('Unbounded source reopen');
    },
  };
  globalThis[key] = io;
  const hooks = registerHooks({
    resolve(specifier, context, next) {
      if (context.parentURL === imported) {
        if (specifier === 'node:fs') return { url: 'fixture:fs-' + mockId, shortCircuit: true };
        if (specifier === 'node:child_process')
          return { url: 'fixture:child-' + mockId, shortCircuit: true };
        if (!['node:crypto', 'node:path', 'node:url'].includes(specifier))
          throw Error('Blocked import: ' + specifier);
      }
      return next(specifier, context);
    },
    load(path, context, next) {
      if (path === imported)
        return { source: readFileSync(url, 'utf8'), format: 'module', shortCircuit: true };
      if (path.startsWith('fixture:fs-'))
        return {
          source:
            'const io=globalThis[' +
            JSON.stringify(key) +
            '];' +
            Object.keys(io)
              .map((name) => 'export const ' + name + '=io.' + name + ';')
              .join(''),
          format: 'module',
          shortCircuit: true,
        };
      if (path.startsWith('fixture:child-'))
        return {
          source: 'export const execFileSync=()=>{throw Error("Blocked Git/runtime");};',
          format: 'module',
          shortCircuit: true,
        };
      return next(path, context);
    },
  });
  let exporter;
  try {
    exporter = await import(imported);
  } finally {
    hooks.deregister();
    delete globalThis[key];
  }
  return {
    run: () =>
      exporter.exportSource({
        root: '/source',
        destination: '/fixture/export',
        paths: ['code.py'],
        maxBytes: 32768,
      }),
    files,
    writes,
    mode: () => mode,
    sourceBytes: () => source.length,
    simulatedAllocated: () =>
      [...files.values()].reduce((sum, bytes) => sum + Math.ceil(bytes.length / 4096) * 4096, 4096),
  };
}
for (const mutation of ['grow', 'replace']) {
  test(`source ${mutation} after admitted read writes only the hashed one-byte snapshot`, async () => {
    const f = await mutableSource(mutation),
      result = f.run(),
      bytes = f.files.get('/fixture/export/code.py');
    assert.equal(f.sourceBytes(), 1048576);
    assert.equal(bytes.length, 1);
    assert.equal(result.entries[0].bytes, 1);
    assert.equal(result.entries[0].sha256, createHash('sha256').update(bytes).digest('hex'));
    assert.equal(f.mode(), 0o761);
    assert.equal(result.manifest_bytes, f.files.get('/fixture/export/source-manifest.json').length);
    assert.ok(f.simulatedAllocated() <= result.forecast_bytes && result.forecast_bytes <= 32768);
    assert.ok(f.writes.every((write) => write.flag === 'wx'));
  });
}
test('mutation and write failure stay bounded; exclusive file/manifest collisions preserve their bytes', async () => {
  const failed = await mutableSource('grow', null, true);
  assert.throws(() => failed.run(), /EIO/);
  assert.equal(failed.files.get('/fixture/export/code.py').length, 1);
  assert.equal(failed.files.has('/fixture/export/source-manifest.json'), false);
  assert.ok(failed.simulatedAllocated() <= 32768);
  for (const path of ['/fixture/export/code.py', '/fixture/export/source-manifest.json']) {
    const f = await mutableSource('replace', path);
    assert.throws(() => f.run(), /EEXIST/);
    assert.equal(f.files.get(path).toString(), 'keep');
    assert.ok(f.simulatedAllocated() <= 32768);
  }
});
test('source permissions survive exclusive snapshot publication', (t) => {
  const f = fixture(t);
  chmodSync(join(f.root, 'code.py'), 0o761);
  exportSource({ ...f, paths: ['code.py'] });
  assert.equal(lstatSync(join(f.destination, 'code.py')).mode & 0o7777, 0o761);
});

test('current scopes omit retired Web roots and require exact root filenames', async (t) => {
  const f = fixture(t);
  const paths = [
    'apps/web/index.html',
    'apps/web/src/main.ts',
    'apps/web/vite.config.ts',
    'packages/engine-bridge/src/index.ts',
    'Cargo.toml',
    'Cargo.toml.saved',
    'package.json',
    'package.json.old',
    'README.md',
    'README.md.saved',
    'pyproject.toml',
    'pyproject.toml.saved',
    'python/quoridor_training/current.py',
    'tools/model-export/export.py',
    'web/retired.js',
    'src/retired.js',
    'public/retired.css',
    'index.html',
    'vite.config.ts',
  ];
  for (const path of paths) {
    mkdirSync(join(f.root, path, '..'), { recursive: true });
    writeFileSync(join(f.root, path), 'synthetic source only\n');
  }
  // Mock ONLY Git's file-list port. No Git command/index/repository is created;
  // the actual exporter still applies its normal filesystem/hash/publication checks.
  const imported =
    new URL('../../scripts/export-fresh-source.mjs', import.meta.url).href + '?current-scope';
  const hooks = registerHooks({
    resolve(specifier, context, next) {
      if (context.parentURL === imported && specifier === 'node:child_process')
        return { url: 'fixture:scope-files', shortCircuit: true };
      return next(specifier, context);
    },
    load(url, context, next) {
      if (url === 'fixture:scope-files')
        return {
          source:
            "export const execFileSync = (command, args) => { if (command !== 'git' || !args.includes('ls-files')) throw Error('Unexpected subprocess'); return Buffer.from(" +
            JSON.stringify(paths.join('\0')) +
            '); };',
          format: 'module',
          shortCircuit: true,
        };
      return next(url, context);
    },
  });
  let exporter;
  try {
    exporter = await import(imported);
  } finally {
    hooks.deregister();
  }
  const product = exporter.exportSource({ ...f, scope: 'product' });
  assert.deepEqual(
    product.entries.map((entry) => entry.path),
    [
      'Cargo.toml',
      'README.md',
      'apps/web/index.html',
      'apps/web/src/main.ts',
      'apps/web/vite.config.ts',
      'package.json',
      'packages/engine-bridge/src/index.ts',
    ],
  );
  const research = exporter.exportSource({
    ...f,
    scope: 'research',
    destination: join(f.base, 'research'),
  });
  assert.deepEqual(
    research.entries.map((entry) => entry.path),
    [
      'Cargo.toml',
      'README.md',
      'pyproject.toml',
      'python/quoridor_training/current.py',
      'tools/model-export/export.py',
    ],
  );
  for (const path of paths)
    assert.equal(readFileSync(join(f.root, path), 'utf8'), 'synthetic source only\n');
});
