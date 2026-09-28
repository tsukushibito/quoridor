# Dev Container storage policy

This project keeps generated state out of the host checkout and separates caches by purpose.

| Data | Location | Persistence |
| --- | --- | --- |
| Managed Git worktrees | `${containerWorkspaceFolder}/.worktree` | `volume` mode |
| Godot editor/import cache | `/home/vscode/.cache/godot` | named volume |
| Inference models and framework downloads | `/home/vscode/.cache/inference` | named volume only in NVIDIA mode |

## Worktrees

When worktree mode is `volume`, create and remove worktrees only with `scripts/dev/manage_worktree.sh`.
The helper places them below `.worktree`, locks every managed worktree, refuses dirty removal, and never deletes branches.
The main checkout remains the integration checkout; perform task work in a managed worktree.

## Inference models

When GPU mode is `nvidia`, place See-Through, DWPose, Hugging Face, Torch, and similar model downloads under `$INFERENCE_CACHE_DIR`.
The generated environment maps Hugging Face hub/Xet/assets and Torch caches into that directory. Do not place model weights in the repository or in `/home/vscode/.codex`.
Framework and CUDA package versions remain project-managed; this Dev Container only exposes the NVIDIA GPU and persistent cache.

Godot remains on software rendering (`LIBGL_ALWAYS_SOFTWARE=1`). NVIDIA access is for inference compute, not editor or Xvfb rendering.

## Toolchain updates

The postCreate hook runs .devcontainer/update-toolchain.sh after container creation or rebuild. It updates Godot 4.x to the latest stable release, Node.js to the latest LTS, and Codex CLI, uv, gdtoolkit, and VS Code CLI to their current stable releases. These versions can change between container builds; the exact installed versions and update time are recorded in /home/vscode/.local/share/godot-devcontainer/toolchain.json.

To update the tools in an existing container, run:

    bash .devcontainer/update-toolchain.sh

The updater does not run on each container start.
