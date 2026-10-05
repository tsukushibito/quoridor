import { execFileSync } from 'node:child_process';
import {
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  writeFileSync,
} from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scopes = {
  research: [
    'crates/',
    'python/',
    'tools/model-export/',
    'tools/research-team/',
    'tools/training/',
    'Cargo.toml',
    'Cargo.lock',
    'rust-toolchain.toml',
    'scripts/export-fresh-source.mjs',
    'tools/research-quality/',
    'scripts/dev/',
    'docs/',
    '.agents/',
    'README.md',
    'AGENTS.md',
    'research-paths.json',
  ],
  product: [
    'apps/',
    'packages/',
    'tests/',
    'rust-toolchain.toml',
    'playwright.config.ts',
    'playwright.audio.config.ts',
    'LICENSE',
    'crates/',
    'web/',
    'src/',
    'public/',
    '.devcontainer/',
    'scripts/',
    'docs/',
    'README.md',
    'AGENTS.md',
    'package.json',
    'package-lock.json',
    'Cargo.toml',
    'Cargo.lock',
    'index.html',
    'vite.config.',
  ],
};
const forbidden =
  /(^|\/)(\.git|\.worktree|\.artifacts|artifacts|research-data|models|node_modules|\.venv|__pycache__|target|dist|build)(\/|$)|(^|\/)\:|\.(ses|tmp|pyc|onnx|bin|pt|pth|gz|zip|tar|wasm)$|(^|\/)index\.lock$/;
function sourcePath(root, name) {
  if (
    typeof name !== 'string' ||
    !name ||
    isAbsolute(name) ||
    name.split(/[\\/]/).some((part) => !part || part === '.' || part === '..') ||
    forbidden.test(name)
  )
    throw Error('SOURCE_PATH_REFUSED:' + name);
  const file = join(root, name),
    stat = lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || !realpathSync(file).startsWith(root + sep))
    throw Error('SOURCE_TYPE_OR_ESCAPE:' + name);
  return { name, file, size: stat.size };
}
export function exportSource({
  root = process.cwd(),
  destination,
  scope,
  paths,
  maxBytes = 8 * 1024 * 1024,
}) {
  root = realpathSync(root);
  if (typeof destination !== 'string' || !destination) throw Error('EXPLICIT_DESTINATION_REQUIRED');
  const dest = resolve(destination);
  if (existsSync(dest)) throw Error('DESTINATION_EXISTS');
  if (dest === root || root.startsWith(dest + sep)) throw Error('DESTINATION_SOURCE_OVERLAP');
  if (dest.startsWith(root + sep) && !dest.startsWith(join(root, '.artifacts') + sep))
    throw Error('DESTINATION_MUST_BE_LIVE_OR_EXTERNAL');
  if (realpathSync(dirname(dest)) !== dirname(dest)) throw Error('DESTINATION_PARENT_SYMLINK');
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw Error('OUTPUT_BUDGET');
  if ((scope !== undefined) === (paths !== undefined))
    throw Error('EXACTLY_ONE_SCOPE_OR_PATHS_REQUIRED');
  if (scope !== undefined) {
    if (!scopes[scope]) throw Error('SOURCE_SCOPE');
    const listed = execFileSync(
      'git',
      ['-C', root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
      { maxBuffer: 8 * 1024 * 1024 },
    )
      .toString()
      .split('\0')
      .filter(Boolean);
    paths = listed.filter(
      (name) => !forbidden.test(name) && scopes[scope].some((prefix) => name.startsWith(prefix)),
    );
  }
  if (!Array.isArray(paths) || !paths.length || new Set(paths).size !== paths.length)
    throw Error('SOURCE_PATH_LIST');
  const plan = paths.sort().map((name) => sourcePath(root, name));
  const logical = plan.reduce((n, p) => n + p.size, 0),
    forecast = logical + plan.length * 512 + 4096;
  if (forecast > maxBytes) throw Error('OUTPUT_FORECAST');
  // Preflight completes before any destination creation; no rm/reset/index operation.
  mkdirSync(dest);
  const entries = [];
  for (const item of plan) {
    // Recheck source path and bytes after preflight. Parallel edits produce typed refusal.
    const checked = sourcePath(root, item.name);
    if (checked.size !== item.size) throw Error('SOURCE_CHANGED:' + item.name);
    const before = readFileSync(item.file),
      sha256 = createHash('sha256').update(before).digest('hex');
    const output = join(dest, item.name);
    mkdirSync(dirname(output), { recursive: true });
    copyFileSync(item.file, output, 1);
    if (createHash('sha256').update(readFileSync(output)).digest('hex') !== sha256)
      throw Error('SOURCE_CHANGED:' + item.name);
    entries.push({ path: item.name, bytes: before.length, sha256 });
  }
  const manifest = {
    schema: 'source-export-v1',
    source_root: root,
    scope: scope ?? 'explicit-paths',
    logical_bytes: logical,
    forecast_bytes: forecast,
    max_bytes: maxBytes,
    entries,
    scientific_data_included: false,
    index_changed: false,
  };
  writeFileSync(join(dest, 'source-manifest.json'), JSON.stringify(manifest, null, 2) + '\n', {
    flag: 'wx',
  });
  return manifest;
}
function main() {
  const args = process.argv.slice(2),
    options = {};
  while (args.length) {
    const key = args.shift(),
      value = args.shift();
    if (!value) throw Error('ARGUMENT_VALUE');
    if (key === '--root') options.root = value;
    else if (key === '--destination') options.destination = value;
    else if (key === '--scope') options.scope = value;
    else if (key === '--paths-file') options.paths = JSON.parse(readFileSync(value, 'utf8'));
    else if (key === '--max-bytes') options.maxBytes = Number(value);
    else throw Error('ARGUMENT:' + key);
  }
  const result = exportSource(options);
  console.log(
    JSON.stringify({
      exported: result.entries.length,
      logical_bytes: result.logical_bytes,
      forecast_bytes: result.forecast_bytes,
    }),
  );
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
