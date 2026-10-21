import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
const checkout = fileURLToPath(new URL('.', import.meta.url));
export default defineConfig({
  testDir: checkout,
  testMatch: [
    fileURLToPath(new URL('./tests/e2e/**/*.spec.ts', import.meta.url)),
    fileURLToPath(new URL('./games/quoridor/tests/e2e/**/*.spec.ts', import.meta.url)),
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173/',
    browserName: 'chromium',
    headless: true,
    launchOptions: { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl'] },
  },
  reporter: 'list',
  workers: 1,
  timeout: 30_000,
  // Local SwiftShader can spend several seconds compiling the first PBR/IBL frame.
  expect: { timeout: 10_000 },
});
