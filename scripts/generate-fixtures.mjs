import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const target = resolve(root, 'tests/fixtures/rules/native-views.json');
const result = spawnSync('cargo', ['run', '--quiet', '--locked', '-p', 'quoridor-wasm',
  '--no-default-features', '--features', 'rules', '--bin', 'export-fixtures'],
  { cwd: root, encoding: 'utf8' });
if (result.status !== 0) { process.stderr.write(result.stderr); process.exit(result.status ?? 1); }
const generated = result.stdout;
if (process.argv.includes('--check')) {
  let current = '';
  try { current = readFileSync(target, 'utf8'); } catch { /* absent fixture */ }
  if (current !== generated) { console.error('Native fixtures are stale; run node scripts/generate-fixtures.mjs.'); process.exit(1); }
  console.log('Native rule fixtures match Rust.');
} else {
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, generated);
  console.log('Generated native rule fixtures.');
}
