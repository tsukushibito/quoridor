import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const mode = process.argv[2];
if (mode !== 'dev' && mode !== 'release') {
  console.error('Usage: node scripts/build-wasm.mjs dev|release');
  process.exit(2);
}
for (const [feature, name] of [['rules', 'quoridor_rules'], ['ai', 'quoridor_ai']]) {
  const args = ['build', '--target', 'web', mode === 'release' ? '--release' : '--dev',
    '--out-dir', resolve(root, `packages/engine-bridge/wasm/${feature}`), '--out-name', name,
    resolve(root, 'crates/quoridor-wasm'), '--locked', '--no-default-features', '--features', feature];
  const result = spawnSync('wasm-pack', args, { cwd: root, stdio: 'inherit', env: process.env });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
console.log(`Built ${mode} rules and AI Wasm with separate features.`);
