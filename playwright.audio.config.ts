import { defineConfig } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import base from './playwright.config';

// The container's shared ~/.cache volume may be owned by root. Firefox needs a writable cache.
const browserCache = resolve('artifacts/browser-cache');
mkdirSync(browserCache, { recursive: true });
const firefoxEnv = { ...Object.fromEntries(Object.entries(process.env).filter(([, value]) => value !== undefined)),
  XDG_CACHE_HOME: browserCache };

export default defineConfig({
  ...base,
  testMatch: 'audio.spec.ts',
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox', headless: process.env.E2E_FIREFOX_HEADED !== '1',
      launchOptions: { args: [], env: firefoxEnv,
        firefoxUserPrefs: { 'webgl.force-enabled': true, 'gfx.webrender.software': true } } } },
    { name: 'webkit', use: { browserName: 'webkit', launchOptions: { args: [] } } },
  ],
});
