import { defineConfig } from '@playwright/test';
import maintained from '../../playwright.config.ts';

// A single explicitly invoked product case; the ordinary E2E suite is unchanged.
if (!process.env.E2E_BASE_URL || !process.env.N3L_RAW_DIR)
  throw new Error('Owned preview URL and output directory must be bound before discovery');
export default defineConfig({
  ...maintained,
  testDir: '../../games/quoridor/tests/product',
  testMatch: 'product-bfcache-worker.spec.mjs',
  workers: 1,
  retries: 0,
  reporter: 'list',
  timeout: 30_000,
  // Shader initialization and one real AI turn share the single browser CPU.
  expect: { ...maintained.expect, timeout: 45_000 },
  outputDir: process.env.N3L_RAW_DIR,
  webServer: undefined,
  use: { ...maintained.use, baseURL: process.env.E2E_BASE_URL },
});
