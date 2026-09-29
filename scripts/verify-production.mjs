import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';
import { resolve } from 'node:path';

const modes = [['root', '/'], ['subpath', '/quoridor/']];
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
  const preview = spawn(process.execPath, [resolve('node_modules/vite/bin/vite.js'), 'preview', '--host', '127.0.0.1', '--port', '4173', '--strictPort'],
    { cwd: resolve('apps/web'), env, stdio: 'inherit' });
  try {
    let ready = false;
    for (let i = 0; i < 50; i++) {
      try { const response = await fetch(`http://127.0.0.1:4173${base}`); if (response.ok) { ready = true; break; } } catch { /* retry */ }
      await delay(100);
    }
    if (!ready) throw new Error(`Preview failed to start for ${mode}`);
    await run('npm', ['run', 'test:e2e'], { ...env, E2E_BASE_URL: `http://127.0.0.1:4173${base}`, E2E_MODE: `production-${mode}` });
  } finally { preview.kill('SIGTERM'); await delay(300); }
}
