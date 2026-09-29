#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/project-env.sh"
export RUSTUP_TOOLCHAIN=stable
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
mkdir -p "$work_dir/src"
cat > "$work_dir/Cargo.toml" <<'TOML'
[package]
name = "quoridor-env-smoke"
version = "0.1.0"
edition = "2024"
[lib]
crate-type = ["cdylib", "rlib"]
[dependencies]
wasm-bindgen = "0.2"
TOML
cat > "$work_dir/src/lib.rs" <<'RS'
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn add(a: u32, b: u32) -> u32 {
    a + b
}

#[cfg(test)]
mod tests {
    #[test]
    fn native_export() {
        assert_eq!(super::add(20, 22), 42);
    }
}
RS
cargo test --manifest-path "$work_dir/Cargo.toml"
cargo fmt --manifest-path "$work_dir/Cargo.toml" --check
cargo clippy --manifest-path "$work_dir/Cargo.toml" --locked -- -D warnings
wasm-pack build "$work_dir" --target web --dev --out-dir pkg
node --input-type=module - "$work_dir/pkg" <<'JS'
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
const directory = process.argv[2];
const engine = await import(pathToFileURL(`${directory}/quoridor_env_smoke.js`));
await engine.default({ module_or_path: readFileSync(`${directory}/quoridor_env_smoke_bg.wasm`) });
assert.equal(engine.add(20, 22), 42);
console.log('Rust native + wasm-bindgen web exports: passed (Node.js Wasm runtime)');
JS
mkdir -p "$QUORIDOR_ENV_REPORT_DIR"
python3 - "$QUORIDOR_ENV_REPORT_DIR/rust-verification.json" <<'PY'
import datetime, json, subprocess, sys
report = {'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'native_test_fmt_clippy':'passed', 'wasm_pack_web_export_in_node':'passed',
          'browser_worker':'not tested'}
for tool in ['rustc','wasm-pack','node']:
    report[tool] = subprocess.check_output([tool,'--version'],text=True).strip()
with open(sys.argv[1], 'w') as f: json.dump(report,f,indent=2); f.write('\n')
PY
