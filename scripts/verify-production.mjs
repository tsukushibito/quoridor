import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';
import { resolve } from 'node:path';

const modes = [['root', '/'], ['subpath', '/quoridor/']];
const port = Number(process.env.PREVIEW_PORT ?? 4173);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PREVIEW_PORT must be a TCP port');
function requireFreePort() {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once('error', error => reject(new Error(`Preview port ${port} unavailable: ${error.message}`)));
    probe.listen(port, '127.0.0.1', () => probe.close(error => error ? reject(error) : resolve()));
  });
}
function run(command, args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { env, stdio: 'inherit' });
    child.on('exit', code => code === 0 ? resolve() : reject(new Error(`${command} ${args.join(' ')} failed: ${code}`)));
  });
}
await run('npm', ['run', 'wasm:build'], process.env);
for (const [mode, base] of modes) {
  const env = { ...process.env, APP_BASE: base, VITE_PHASE1_E2E: '1' };
  await run('npm', ['run', 'build', '-w', '@quoridor/web'], env);
  await requireFreePort();
  const preview = spawn(process.execPath, [resolve('node_modules/vite/bin/vite.js'), 'preview', '--host', '127.0.0.1', '--port', String(port), '--strictPort'],
    { cwd: resolve('apps/web'), env, stdio: 'inherit' });
  let previewFailure = null;
  preview.on('error', error => { previewFailure = error; });
  preview.on('exit', (code, signal) => { previewFailure = new Error(`Preview exited before verification (${code ?? signal})`); });
  try {
    // Let --strictPort reject an occupied port before accepting any HTTP response.
    await delay(350);
    if (previewFailure) throw previewFailure;
    let ready = false;
    for (let i = 0; i < 50; i++) {
      if (previewFailure) throw previewFailure;
      try { const response = await fetch(`http://127.0.0.1:${port}${base}`); if (response.ok && !previewFailure) { ready = true; break; } } catch { /* retry */ }
      await delay(100);
    }
    if (!ready) throw new Error(`Preview failed to start for ${mode}`);
    await run('npm', ['run', 'test:e2e'], { ...env, E2E_BASE_URL: `http://127.0.0.1:${port}${base}`, E2E_MODE: `production-${mode}` });
  } finally { preview.kill('SIGTERM'); await delay(300); }
}
