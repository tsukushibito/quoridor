import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const modes = [
  ['root', '/'],
  ['subpath', '/quoridor/'],
];

function requireFreePort(port) {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once('error', (error) =>
      reject(new Error(`Preview port ${port} unavailable: ${error.message}`)),
    );
    probe.listen(port, '127.0.0.1', () =>
      probe.close((error) => (error ? reject(error) : resolve())),
    );
  });
}

function run(command, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd: root, env, stdio: 'inherit' });
    child.once('error', reject);
    child.once('exit', (code, signal) =>
      code === 0
        ? resolve()
        : reject(new Error(`${command} ${args.join(' ')} failed: ${code ?? signal}`)),
    );
  });
}

async function stopPreview(child, wait) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise((resolve) => child.once('exit', resolve));
  child.kill('SIGTERM');
  const stopped = await Promise.race([exited.then(() => true), wait(1000).then(() => false)]);
  if (!stopped) {
    child.kill('SIGKILL');
    await exited;
  }
}

// Dependency injection keeps orchestration tests free of builds and browser jobs.
export async function verifyProduction(options = {}) {
  const envSource = options.env ?? process.env;
  const port = Number(envSource.PREVIEW_PORT ?? 4173);
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new Error('PREVIEW_PORT must be a TCP port');
  const execute = options.run ?? run;
  const launch = options.spawn ?? spawn;
  const wait = options.delay ?? delay;
  const request = options.fetch ?? fetch;
  const freePort = options.requireFreePort ?? requireFreePort;
  await execute('npm', ['run', 'wasm:build'], envSource);
  for (const [mode, base] of modes) {
    const outDir = resolve(root, '.artifacts/verify-production', mode);
    const env = { ...envSource, APP_BASE: base, APP_OUT_DIR: outDir, VITE_PHASE1_E2E: '1' };
    await execute('npm', ['run', 'build', '-w', '@quoridor/web'], env);
    await freePort(port);
    const preview = launch(
      process.execPath,
      [
        resolve(root, 'node_modules/vite/bin/vite.js'),
        'preview',
        '--outDir',
        outDir,
        '--host',
        '127.0.0.1',
        '--port',
        String(port),
        '--strictPort',
      ],
      { cwd: resolve(root, 'apps/web'), env, stdio: 'inherit' },
    );
    let previewFailure = null;
    preview.on('error', (error) => {
      previewFailure = error;
    });
    preview.on('exit', (code, signal) => {
      previewFailure = new Error(`Preview exited before verification (${code ?? signal})`);
    });
    try {
      await wait(350);
      if (previewFailure) throw previewFailure;
      let ready = false;
      for (let i = 0; i < 50; i++) {
        if (previewFailure) throw previewFailure;
        try {
          const response = await request(`http://127.0.0.1:${port}${base}`);
          if (response.ok && !previewFailure) {
            ready = true;
            break;
          }
        } catch {
          /* retry */
        }
        await wait(100);
      }
      if (!ready) throw new Error(`Preview failed to start for ${mode}`);
      await execute('npm', ['run', 'test:e2e'], {
        ...env,
        E2E_BASE_URL: `http://127.0.0.1:${port}${base}`,
        E2E_MODE: `production-${mode}`,
      });
    } finally {
      await stopPreview(preview, wait);
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  await verifyProduction();
}
