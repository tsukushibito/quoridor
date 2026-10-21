import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const mode = process.argv[2];
if (mode !== 'dev' && mode !== 'release') {
  console.error('Usage: node scripts/build-wasm.mjs dev|release');
  process.exit(2);
}
for (const [game, feature, name] of [
  ['quoridor', 'rules', 'quoridor_rules'],
  ['quoridor', 'ai', 'quoridor_ai'],
  ['othello', '', 'othello'],
]) {
  const args = [
    'build',
    '--target',
    'web',
    mode === 'release' ? '--release' : '--dev',
    '--out-dir',
    resolve(root, `games/${game}/bridge/wasm/${feature}`),
    '--out-name',
    name,
    resolve(root, `games/${game}/crates/${game}-wasm`),
    '--locked',
    '--no-default-features',
    ...(feature ? ['--features', feature] : []),
  ];
  const result = spawnSync('wasm-pack', args, { cwd: root, stdio: 'inherit', env: process.env });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
console.log(`Built ${mode} Quoridor rules/AI and Othello Wasm.`);
