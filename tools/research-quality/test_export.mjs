import test from 'node:test';
import assert from 'node:assert/strict';
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
  existsSync,
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
