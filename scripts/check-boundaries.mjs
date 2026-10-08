import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// Python 3.11+ is already required by the development environment; no package resolution.
process.stdout.write(
  execFileSync(
    'python3',
    [
      '-B',
      fileURLToPath(new URL('./check-boundaries.py', import.meta.url)),
      'crates/quoridor-wasm/Cargo.toml',
    ],
    { timeout: 30000, maxBuffer: 128 * 1024 },
  ),
);
