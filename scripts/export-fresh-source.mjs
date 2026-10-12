import { execFileSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  statfsSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const scopes = {
  research: [
    "crates/",
    "python/",
    "tools/model-export/",
    "tools/research-session/",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain.toml",
    "scripts/export-fresh-source.mjs",
    "tools/research-quality/",
    "scripts/dev/",
    "docs/",
    ".agents/",
    "README.md",
    "AGENTS.md",
    "research-paths.json",
  ],
  product: [
    "apps/",
    "packages/",
    "tests/",
    "rust-toolchain.toml",
    "playwright.config.ts",
    "playwright.audio.config.ts",
    "LICENSE",
    "crates/",
    "web/",
    "src/",
    "public/",
    ".devcontainer/",
    "scripts/",
    "docs/",
    "README.md",
    "AGENTS.md",
    "package.json",
    "package-lock.json",
    "Cargo.toml",
    "Cargo.lock",
    "index.html",
    "vite.config.",
  ],
};
const forbidden =
  /(^|\/)(\.git|\.worktree|\.artifacts|artifacts|research-data|models|node_modules|\.venv|__pycache__|target|dist|build)(\/|$)|(^|\/)\:|\.(ses|tmp|pyc|onnx|bin|pt|pth|gz|zip|tar|wasm)$|(^|\/)index\.lock$/;
function sourcePath(root, name) {
  if (
    typeof name !== "string" ||
    !name ||
    isAbsolute(name) ||
    name
      .split(/[\\/]/)
      .some((part) => !part || part === "." || part === "..") ||
    forbidden.test(name)
  )
    throw Error("SOURCE_PATH_REFUSED:" + name);
  const file = join(root, name),
    stat = lstatSync(file);
  if (
    !stat.isFile() ||
    stat.isSymbolicLink() ||
    !realpathSync(file).startsWith(root + sep)
  )
    throw Error("SOURCE_TYPE_OR_ESCAPE:" + name);
  return { name, file, size: stat.size, mode: stat.mode & 0o7777 };
}
export function exportSource({
  root = process.cwd(),
  destination,
  scope,
  paths,
  maxBytes = 8 * 1024 * 1024,
}) {
  root = realpathSync(root);
  if (typeof destination !== "string" || !destination)
    throw Error("EXPLICIT_DESTINATION_REQUIRED");
  const dest = resolve(destination);
  if (existsSync(dest)) throw Error("DESTINATION_EXISTS");
  if (dest === root || root.startsWith(dest + sep))
    throw Error("DESTINATION_SOURCE_OVERLAP");
  if (
    dest.startsWith(root + sep) &&
    !dest.startsWith(join(root, ".artifacts") + sep)
  )
    throw Error("DESTINATION_MUST_BE_LIVE_OR_EXTERNAL");
  if (realpathSync(dirname(dest)) !== dirname(dest))
    throw Error("DESTINATION_PARENT_SYMLINK");
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1)
    throw Error("OUTPUT_BUDGET");
  if ((scope !== undefined) === (paths !== undefined))
    throw Error("EXACTLY_ONE_SCOPE_OR_PATHS_REQUIRED");
  if (scope !== undefined) {
    if (!scopes[scope]) throw Error("SOURCE_SCOPE");
    const listed = execFileSync(
      "git",
      [
        "-C",
        root,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
      ],
      { maxBuffer: 8 * 1024 * 1024 },
    )
      .toString()
      .split("\0")
      .filter(Boolean);
    paths = [...new Set(listed)].filter((name) => {
      if (
        forbidden.test(name) ||
        !scopes[scope].some((prefix) => name.startsWith(prefix))
      )
        return false;
      try {
        lstatSync(join(root, name));
        return true;
      } catch (error) {
        if (error.code === "ENOENT") return false;
        throw error;
      }
    });
  }
  if (
    !Array.isArray(paths) ||
    !paths.length ||
    new Set(paths).size !== paths.length
  )
    throw Error("SOURCE_PATH_LIST");
  const plan = paths.sort().map((name) => sourcePath(root, name));
  if (
    plan.some(
      (item) =>
        item.name === "source-manifest.json" ||
        item.name.startsWith("source-manifest.json/"),
    )
  )
    throw Error("MANIFEST_PATH_COLLISION");
  // Budget allocated output, including the exact manifest, directory entries and a failure reserve.
  // Use the destination filesystem's block size, with at least 4 KiB per allocation unit.
  const unit = Math.max(4096, statfsSync(dirname(dest)).bsize);
  const rounded = (bytes) => Math.ceil(bytes / unit) * unit;
  const directories = new Map([["", []]]);
  const addEntry = (parent, name) => {
    if (!directories.has(parent)) directories.set(parent, []);
    directories.get(parent).push(name);
  };
  for (const item of [...plan, { name: "source-manifest.json" }]) {
    let parent = "";
    const parts = item.name.split("/");
    for (let i = 0; i < parts.length; i++) {
      const name = parts[i];
      const child = parent ? parent + "/" + name : name;
      if (i === parts.length - 1 || !directories.has(child))
        addEntry(parent, name);
      if (i < parts.length - 1 && !directories.has(child))
        directories.set(child, []);
      parent = child;
    }
  }
  const logical = plan.reduce((n, item) => n + item.size, 0);
  // One extra block per file allows tail/preallocation overhead. Directory-entry
  // bounds include encoded names plus metadata, and a block for dot entries/growth.
  const sourceAllocated = plan.reduce(
    (n, item) => n + rounded(item.size) + unit,
    0,
  );
  const directoryAllocated = [...directories.values()].reduce(
    (n, names) =>
      n +
      unit +
      rounded(
        names.reduce((bytes, name) => bytes + Buffer.byteLength(name) + 32, 0),
      ),
    0,
  );
  // Refuse obviously oversized sources before hashing/materializing their bytes.
  if (sourceAllocated + directoryAllocated + 4 * unit > maxBytes)
    throw Error("OUTPUT_FORECAST");
  const entries = plan.map((item) => {
    const bytes = readFileSync(item.file);
    if (bytes.length !== item.size) throw Error("SOURCE_CHANGED:" + item.name);
    return {
      path: item.name,
      bytes: bytes.length,
      sha256: createHash("sha256").update(bytes).digest("hex"),
    };
  });
  const manifest = {
    schema: "source-export-v1",
    source_root: root,
    scope: scope ?? "explicit-paths",
    logical_bytes: logical,
    forecast_bytes: 0,
    max_bytes: maxBytes,
    budget_basis: "allocated-output-upper-bound",
    allocation_unit_bytes: unit,
    directory_count: directories.size,
    failure_reserve_bytes: 2 * unit,
    manifest_bytes: 0,
    entries,
    scientific_data_included: false,
    index_changed: false,
  };
  let manifestText;
  for (;;) {
    manifestText = JSON.stringify(manifest, null, 2) + "\n";
    const manifestBytes = Buffer.byteLength(manifestText);
    const forecast =
      sourceAllocated +
      directoryAllocated +
      rounded(manifestBytes) +
      unit +
      manifest.failure_reserve_bytes;
    if (
      manifest.manifest_bytes === manifestBytes &&
      manifest.forecast_bytes === forecast
    )
      break;
    manifest.manifest_bytes = manifestBytes;
    manifest.forecast_bytes = forecast;
  }
  if (
    !Number.isSafeInteger(manifest.forecast_bytes) ||
    manifest.forecast_bytes > maxBytes
  )
    throw Error("OUTPUT_FORECAST");
  // Preflight completes before any destination creation; no rm/reset/index operation.
  mkdirSync(dest);
  for (let i = 0; i < plan.length; i++) {
    const item = plan[i];
    const checked = sourcePath(root, item.name);
    if (checked.size !== item.size) throw Error("SOURCE_CHANGED:" + item.name);
    const before = readFileSync(item.file);
    if (createHash("sha256").update(before).digest("hex") !== entries[i].sha256)
      throw Error("SOURCE_CHANGED:" + item.name);
    const output = join(dest, item.name);
    mkdirSync(dirname(output), { recursive: true });
    // Write only this already validated snapshot: source growth cannot escape admission.
    writeFileSync(output, before, { flag: "wx", mode: checked.mode });
    chmodSync(output, checked.mode);
    if (
      createHash("sha256").update(readFileSync(output)).digest("hex") !==
      entries[i].sha256
    )
      throw Error("SOURCE_CHANGED:" + item.name);
  }
  writeFileSync(join(dest, "source-manifest.json"), manifestText, {
    flag: "wx",
  });
  return manifest;
}
function main() {
  const args = process.argv.slice(2),
    options = {};
  while (args.length) {
    const key = args.shift(),
      value = args.shift();
    if (!value) throw Error("ARGUMENT_VALUE");
    if (key === "--root") options.root = value;
    else if (key === "--destination") options.destination = value;
    else if (key === "--scope") options.scope = value;
    else if (key === "--paths-file")
      options.paths = JSON.parse(readFileSync(value, "utf8"));
    else if (key === "--max-bytes") options.maxBytes = Number(value);
    else throw Error("ARGUMENT:" + key);
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
if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
