#!/usr/bin/env bash
set -euo pipefail

workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
persistent_paths=(/home/vscode/.local /home/vscode/.cache/godot /home/vscode/.cache/uv /home/vscode/.codex)
if [[ "false" == true ]]; then
  persistent_paths+=(/home/vscode/.cache/ms-playwright /home/vscode/.local/share/playwright-chatgpt-profile)
fi
if [[ "nvidia" == nvidia ]]; then persistent_paths+=(/home/vscode/.cache/inference); fi
if [[ "volume" == volume ]]; then persistent_paths+=("$workspace_root/.worktree"); fi
if [[ "true" == true ]]; then persistent_paths+=(/home/vscode/.config/gh); fi
if [[ "true" == true ]]; then persistent_paths+=(/home/vscode/.vscode-data); fi
if [[ "true" == true ]]; then persistent_paths+=(/home/vscode/.ssh); fi
sudo mkdir -p "${persistent_paths[@]}"
sudo chown -R vscode:vscode "${persistent_paths[@]}"
mkdir -p /home/vscode/.local/bin

if [[ "false" == true ]]; then
  chmod 0700 /home/vscode/.local/share/playwright-chatgpt-profile
  bash "$workspace_root/.devcontainer/install-google-chrome.sh"
fi

if git -C "$workspace_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git config --global --add safe.directory "$workspace_root"
  if [[ "volume" == volume ]]; then
    bash "$workspace_root/scripts/dev/manage_worktree.sh" lock-existing
  fi
  if [[ "true" == true ]]; then
    git -C "$workspace_root" lfs install --local
  fi
elif [[ "true" == true ]]; then
  git lfs version >/dev/null
fi

bash "$workspace_root/.devcontainer/update-toolchain.sh"

if [[ "true" == true ]]; then
  chmod 0700 /home/vscode/.ssh
fi

bash "$workspace_root/scripts/dev/verify_env.sh"
