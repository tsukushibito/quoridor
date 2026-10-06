#!/usr/bin/env bash
set -euo pipefail

workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
local_bin="$HOME/.local/bin"
local_opt="$HOME/.local/opt"
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
mkdir -p "$local_bin" "$local_opt/node"
export PATH="$local_bin:$PATH"
export UV_TOOL_BIN_DIR="$local_bin"
export UV_TOOL_DIR="$HOME/.local/share/uv/tools"

apt_arch="$(dpkg --print-architecture)"
case "$apt_arch" in
  amd64)
    node_arch="x64"
    uv_arch="x86_64"
    ;;
  arm64)
    node_arch="arm64"
    uv_arch="aarch64"
    ;;
  *)
    echo "Unsupported architecture: $(dpkg --print-architecture); expected amd64 or arm64." >&2
    exit 1
    ;;
esac

github_asset() {
  local release_json="$1"
  local asset_name="$2"
  jq -er --arg name "$asset_name" '
    [.assets[] | select(.name == $name)] |
    if length != 1 then error("expected exactly one release asset")
    else .[0] |
      select(.digest | type == "string" and startswith("sha256:")) |
      [.browser_download_url, (.digest | sub("^sha256:"; ""))] | @tsv
    end
  ' <<<"$release_json"
}

download_verified() {
  local url="$1"
  local expected_sha="$2"
  local destination="$3"
  [[ "$expected_sha" =~ ^[[:xdigit:]]{64}$ ]] || {
    echo "Release metadata did not provide a valid SHA-256 digest for $url" >&2
    exit 1
  }
  curl --fail --location --retry 3 --silent --show-error --output "$destination" "$url"
  printf '%s  %s\n' "$expected_sha" "$destination" | sha256sum --check --strict -
}

echo "Resolving the latest Node.js LTS release..."
node_index="$(curl --fail --location --retry 3 --silent --show-error https://nodejs.org/dist/index.json)"
node_version="$(jq -er --arg platform "linux-$node_arch" '
  [.[] | select(.lts != false and (.files | index($platform) != null))] |
  sort_by(.version | ltrimstr("v") | split(".") | map(tonumber)) |
  last | .version
' <<<"$node_index")"
node_archive="node-$node_version-linux-$node_arch.tar.xz"
node_base_url="https://nodejs.org/dist/$node_version"
curl --fail --location --retry 3 --silent --show-error \
  --output "$work_dir/$node_archive" "$node_base_url/$node_archive"
curl --fail --location --retry 3 --silent --show-error \
  --output "$work_dir/SHASUMS256.txt" "$node_base_url/SHASUMS256.txt"
node_sha="$(awk -v name="$node_archive" '$2 == name { print $1; found=1; exit } END { if (!found) exit 1 }' "$work_dir/SHASUMS256.txt")"
printf '%s  %s\n' "$node_sha" "$work_dir/$node_archive" | sha256sum --check --strict -
node_install_dir="$local_opt/node/$node_version"
rm -rf -- "$node_install_dir"
mkdir -p "$node_install_dir"
tar -xJf "$work_dir/$node_archive" --strip-components=1 -C "$node_install_dir"
for command_name in node npm npx corepack; do
  if [[ -x "$node_install_dir/bin/$command_name" ]]; then
    ln -sfn "$node_install_dir/bin/$command_name" "$local_bin/$command_name"
  fi
done

echo "Resolving the latest stable uv release..."
uv_release="$(curl --fail --location --retry 3 --silent --show-error \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  -H 'User-Agent: quoridor-devcontainer' \
  https://api.github.com/repos/astral-sh/uv/releases/latest)"
uv_archive="uv-$uv_arch-unknown-linux-gnu.tar.gz"
read -r uv_url uv_sha < <(github_asset "$uv_release" "$uv_archive")
download_verified "$uv_url" "$uv_sha" "$work_dir/uv.tar.gz"
mkdir "$work_dir/uv"
tar -xzf "$work_dir/uv.tar.gz" -C "$work_dir/uv"
install -m 0755 "$work_dir/uv/uv-$uv_arch-unknown-linux-gnu/uv" "$local_bin/uv"
install -m 0755 "$work_dir/uv/uv-$uv_arch-unknown-linux-gnu/uvx" "$local_bin/uvx"

echo "Installing the latest Codex CLI..."
npm config set prefix "$HOME/.local" --location=user
npm install --global @openai/codex@latest

echo "Updating VS Code CLI from Microsoft's signed stable APT repository..."
# The Dev Container base image already configures this repository in
# /etc/apt/sources.list.d/vscode.sources with its matching Microsoft keyring.
# Do not add a second entry for the same URL with a different Signed-By path.
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends code

mkdir -p "$HOME/.local/share/quoridor"
version_file="$HOME/.local/share/quoridor/toolchain.json"
version_tmp="$version_file.tmp"
node_runtime_version="$(node --version)"
codex_version="$(codex --version)"
uv_version="$(uv --version)"
vscode_version="$(VSCODE_IPC_HOOK_CLI=/tmp/code-cli-must-not-use-vscode-ipc.sock code-cli --version | head -n 1)"
jq -n \
  --arg updated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg architecture "$apt_arch" \
  --arg node "$node_runtime_version" \
  --arg codex "$codex_version" \
  --arg uv "$uv_version" \
  --arg vscode_cli "$vscode_version" \
  '{updated_at:$updated_at, architecture:$architecture, tools:{node:$node, codex:$codex, uv:$uv, vscode_cli:$vscode_cli}}' \
  >"$version_tmp"
mv -f -- "$version_tmp" "$version_file"

echo "Installed toolchain versions:"
cat "$version_file"
bash "$workspace_root/scripts/dev/verify_env.sh"
