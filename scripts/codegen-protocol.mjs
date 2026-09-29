import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const target = resolve(root, 'packages/engine-bridge/src/generated/protocol.ts');
const result = spawnSync('cargo', ['run', '--quiet', '--locked', '-p', 'quoridor-wasm',
  '--no-default-features', '--features', 'rules', '--bin', 'generate-protocol'],
  { cwd: root, encoding: 'utf8' });
if (result.status !== 0) { process.stderr.write(result.stderr); process.exit(result.status ?? 1); }
const generated = result.stdout;
if (process.argv.includes('--check')) {
  let current = '';
  try { current = readFileSync(target, 'utf8'); } catch { /* missing generated source */ }
  if (current !== generated) {
    console.error('Generated protocol is stale; run npm run codegen:protocol.');
    process.exit(1);
  }
  console.log('Generated protocol matches Rust wire DTOs.');
} else {
  writeFileSync(target, generated);
  console.log('Generated protocol from Rust wire DTOs.');
}
