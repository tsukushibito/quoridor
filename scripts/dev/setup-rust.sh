#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/project-env.sh"
update=false
case "${1:-}" in
  '') ;;
  --update) update=true ;;
  *) echo "Usage: $0 [--update]" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
mkdir -p "$QUORIDOR_ENV_REPORT_DIR"
exec 9>"$QUORIDOR_ENV_REPORT_DIR/rust-setup.lock"
flock 9

# Match the official Rust Feature's locations, including on the current container.
for directory in "$CARGO_HOME" "$RUSTUP_HOME"; do
  if [[ ! -d "$directory" ]]; then
    sudo install -d -o "$(id -u)" -g "$(id -g)" -m 0755 "$directory"
  fi
  [[ -w "$directory" ]] || { echo "Not writable: $directory" >&2; exit 1; }
done
missing=()
for package in build-essential pkg-config libssl-dev curl ca-certificates; do
  if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
    missing+=("$package")
  fi
done
if (( ${#missing[@]} )); then
  sudo apt-get update
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
fi
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
case "$(uname -m)" in
  x86_64) rust_host=x86_64-unknown-linux-gnu; pack_host=x86_64-unknown-linux-musl ;;
  aarch64) rust_host=aarch64-unknown-linux-gnu; pack_host=aarch64-unknown-linux-musl ;;
  *) echo 'Unsupported Linux architecture' >&2; exit 1 ;;
esac
if [[ ! -x "$CARGO_HOME/bin/rustup" ]]; then
  rustup_url="https://static.rust-lang.org/rustup/dist/$rust_host/rustup-init"
  curl -fLsS --retry 3 "$rustup_url" -o "$work_dir/rustup-init"
  curl -fLsS --retry 3 "$rustup_url.sha256" -o "$work_dir/rustup-init.sha256"
  rustup_sha="$(awk '{print $1}' "$work_dir/rustup-init.sha256")"
  [[ "$rustup_sha" =~ ^[[:xdigit:]]{64}$ ]]
  printf '%s  %s\n' "$rustup_sha" "$work_dir/rustup-init" | sha256sum -c -
  chmod +x "$work_dir/rustup-init"
  "$work_dir/rustup-init" -y --no-modify-path --profile minimal --default-toolchain none
fi
if [[ "$update" == true ]]; then
  rustup self update
  rustup update stable
elif ! rustup run stable rustc --version >/dev/null 2>&1; then
  rustup toolchain install stable --profile minimal
fi
rustup default stable
rustup target add --toolchain stable wasm32-unknown-unknown
rustup component add --toolchain stable rustfmt clippy rust-analyzer rust-src

if [[ "$update" == true || ! -x "$CARGO_HOME/bin/wasm-pack" ]]; then
  curl -fLsS --retry 3 -H 'Accept: application/vnd.github+json' \
    https://api.github.com/repos/wasm-bindgen/wasm-pack/releases/latest -o "$work_dir/release.json"
  read -r pack_version pack_url pack_sha < <(python3 - "$work_dir/release.json" "$pack_host" <<'PY'
import json, re, sys
release = json.load(open(sys.argv[1]))
assert not release['prerelease'] and not release['draft']
tag = release['tag_name']
assert re.fullmatch(r'v\d+\.\d+\.\d+', tag), tag
name = f'wasm-pack-{tag}-{sys.argv[2]}.tar.gz'
asset, = [a for a in release['assets'] if a['name'] == name]
digest = asset.get('digest', '')
assert re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'Missing release checksum'
print(tag[1:], asset['browser_download_url'], digest.removeprefix('sha256:'))
PY
  )
  [[ -n "$pack_version" && -n "$pack_url" && "$pack_sha" =~ ^[[:xdigit:]]{64}$ ]]
  if [[ ! -x "$CARGO_HOME/bin/wasm-pack" ]] || [[ "$(wasm-pack --version)" != "wasm-pack $pack_version" ]]; then
    curl -fLsS --retry 3 "$pack_url" -o "$work_dir/wasm-pack.tar.gz"
    printf '%s  %s\n' "$pack_sha" "$work_dir/wasm-pack.tar.gz" | sha256sum -c -
    tar -xzf "$work_dir/wasm-pack.tar.gz" -C "$work_dir"
    install -m 0755 "$work_dir/wasm-pack-v$pack_version-$pack_host/wasm-pack" "$CARGO_HOME/bin/wasm-pack"
  fi
fi
# Future login shells get the same environment without rebuilding. Existing shells
# can source project-env.sh. Do not overwrite a different installation's profile.
profile_file=/etc/profile.d/quoridor-rust.sh
printf '# Managed by quoridor setup-rust.sh\nexport CARGO_HOME=%q\nexport RUSTUP_HOME=%q\nexport WASM_PACK_CACHE=%q\nexport PATH="$CARGO_HOME/bin:$PATH"\n' \
  "$CARGO_HOME" "$RUSTUP_HOME" "$WASM_PACK_CACHE" > "$work_dir/profile.sh"
if [[ -f "$profile_file" ]] && ! grep -qx '# Managed by quoridor setup-rust.sh' "$profile_file"; then
  echo "Existing $profile_file has different Rust locations; reconcile them first." >&2
  exit 1
fi
sudo install -m 0644 "$work_dir/profile.sh" "$profile_file"
python3 - "$QUORIDOR_ENV_REPORT_DIR/rust-toolchain.json" <<'PY'
import datetime, json, os, subprocess, sys
report = {'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'cargo_home': os.environ['CARGO_HOME'], 'rustup_home': os.environ['RUSTUP_HOME']}
for tool in ['rustup', 'rustc', 'cargo', 'wasm-pack']:
    report[tool] = subprocess.check_output([tool, '--version'], text=True).strip()
report['targets'] = subprocess.check_output(['rustup','target','list','--installed','--toolchain','stable'],text=True).splitlines()
with open(sys.argv[1], 'w') as f: json.dump(report, f, indent=2); f.write('\n')
print(json.dumps(report, indent=2))
PY
