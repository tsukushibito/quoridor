import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
let failures = 0;
for (const [command, args] of [['node', ['--version']], ['npm', ['--version']], ['rustc', ['--version']], ['cargo', ['--version']], ['wasm-pack', ['--version']], ['rustup', ['target', 'list', '--installed']]]) {
  const result = spawnSync(command, args, { encoding: 'utf8' });
  const output = (result.stdout || result.stderr || '').trim();
  console.log(`${command} ${args.join(' ')}: ${output}`);
  if (result.status !== 0) failures++;
  if (command === 'rustup' && !output.includes('wasm32-unknown-unknown')) failures++;
}
for (const feature of ['rules', 'ai']) {
  const name = feature === 'rules' ? 'quoridor_rules' : 'quoridor_ai';
  const file = resolve(`packages/engine-bridge/wasm/${feature}/${name}_bg.wasm`);
  console.log(`${feature} Wasm: ${existsSync(file) ? 'present' : 'missing; run npm run wasm:build'}`);
}
const vxgiFile = resolve('node_modules/three/examples/jsm/lighting/vxgi/VXGINode.js');
console.log(`official VXGI addon: ${existsSync(vxgiFile) ? 'present' : 'missing'}`);
if (!existsSync(vxgiFile)) failures++;
console.log(`PLAYWRIGHT_CDP_ENDPOINT: ${process.env.PLAYWRIGHT_CDP_ENDPOINT ? 'configured (not probed; Phase 5)' : 'not configured (optional until Phase 5)'}`);
if (failures) process.exit(1);
