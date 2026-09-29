import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
const manifest = readFileSync(resolve('crates/quoridor-wasm/Cargo.toml'), 'utf8');
if (!/^ai = \[[^\n]*"dep:quoridor-ai"[^\n]*\]$/m.test(manifest) || !/^default = \[\]$/m.test(manifest) ||
  !/^quoridor-ai = \{[^\n]*optional = true[^\n]*\}$/m.test(manifest) ||
  /^rules = \[[^\n]*quoridor-ai[^\n]*\]$/m.test(manifest)) {
  throw new Error('AI dependency must remain optional, with no default features');
}
console.log('Wasm feature boundary: AI dependency is optional.');
