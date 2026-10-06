import { defineConfig } from 'vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = dirname(fileURLToPath(import.meta.url));
const verificationOutputs = new Set(
  ['root', 'subpath'].map((mode) => resolve(webRoot, '../../.artifacts/verify-production', mode)),
);
export default defineConfig(({ command }) => {
  const outDir = resolve(webRoot, process.env.APP_OUT_DIR || 'dist');
  if (
    command === 'build' &&
    process.env.VITE_PHASE1_E2E === '1' &&
    outDir === resolve(webRoot, 'dist')
  ) {
    throw new Error('Builds with E2E hooks require a dedicated APP_OUT_DIR');
  }
  return {
    base: process.env.APP_BASE || '/',
    // Only these fixed verification directories are owned scratch outside the Vite root.
    build: {
      outDir,
      ...(process.env.APP_OUT_DIR ? { emptyOutDir: verificationOutputs.has(outDir) } : {}),
    },
    server: { host: '127.0.0.1', port: 5173, strictPort: true },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  };
});
