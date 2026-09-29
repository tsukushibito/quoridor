import { execFileSync } from 'node:child_process';
import { copyFileSync, lstatSync, mkdirSync, readFileSync, readlinkSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';

// Git enumerates the checked-in baseline plus the accepted uncommitted Phase 0–4 sources.
// Ignored dependencies, Wasm, build output, screenshots, and this destination are absent.
const root = resolve('.');
const destination = resolve('artifacts/fresh-source-phase4/source');
const listed = execFileSync('git', ['ls-files', '-z', '--cached', '--others', '--exclude-standard']);
const paths = [...new Set(listed.toString().split('\0').filter(Boolean))].sort();
const lines = [];
rmSync(destination, { recursive: true, force: true });
for (const path of paths) {
  const from = join(root, path);
  const to = join(destination, path);
  mkdirSync(dirname(to), { recursive: true });
  rmSync(to, { force: true });
  if (lstatSync(from).isSymbolicLink()) symlinkSync(readlinkSync(from), to);
  else copyFileSync(from, to);
  const actual = createHash('sha256').update(readFileSync(from)).digest('hex');
  lines.push(`${actual}  ${path}`);
}
const manifest = `${lines.join('\n')}\n`;
writeFileSync(resolve('artifacts/fresh-source-phase4/source-manifest.sha256'), manifest);
console.log(`Exported ${paths.length} source paths to ${destination}`);
console.log(`Manifest SHA256: ${createHash('sha256').update(manifest).digest('hex')}`);
