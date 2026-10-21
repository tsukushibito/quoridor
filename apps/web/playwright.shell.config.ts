import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const checkout = fileURLToPath(new URL('../..', import.meta.url));
const output = resolve(checkout, '.artifacts/web-game-shell129');
export default defineConfig({
  testDir: resolve(checkout, 'tests/e2e'),
  testMatch: 'web-shell.spec.ts',
  outputDir: resolve(output, 'browser-results'),
  workers: 1,
  retries: 0,
  reporter: 'list',
  timeout: 90_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: 'http://127.0.0.1:4189/shell-check/',
    browserName: 'chromium',
    headless: true,
    launchOptions: {
      args:
        process.env.WEB_SHELL_NO_RENDER === '1'
          ? ['--disable-gpu', '--disable-software-rasterizer', '--disable-dev-shm-usage']
          : [
              '--use-gl=angle',
              '--use-angle=swiftshader',
              '--enable-webgl',
              '--disable-dev-shm-usage',
            ],
    },
  },
  webServer: {
    command:
      'node node_modules/vite/bin/vite.js preview apps/web --outDir ../../.artifacts/web-game-shell129/dist-subpath --port 4189 --strictPort',
    cwd: checkout,
    url: 'http://127.0.0.1:4189/shell-check/',
    reuseExistingServer: false,
    timeout: 20_000,
    env: { APP_BASE: '/shell-check/' },
  },
});
