# Dev Container storage policy

This project keeps generated state out of the host checkout and separates caches by purpose.

| Data | Location | Persistence |
| --- | --- | --- |
| Managed Git worktrees | `${containerWorkspaceFolder}/.worktree` | `volume` mode |
| Shared Beads database | `${containerWorkspaceFolder}/.worktree/.beads-state` | worktrees named volume; independent of individual worktrees |
| Beads full database backup | `${containerWorkspaceFolder}/.artifacts/beads-backup` | host checkout, Git-ignored; not protection against host loss |
| Godot editor/import cache | `/home/vscode/.cache/godot` | named volume |
| Inference models and framework downloads | `/home/vscode/.cache/inference` | named volume only in NVIDIA mode |
| Training Python, uv packages and virtual environment | `$INFERENCE_CACHE_DIR/python`, `$INFERENCE_CACHE_DIR/uv`, `$INFERENCE_CACHE_DIR/envs/quoridor-training` | same named volume |
| Rust toolchains / Cargo / wasm-pack cache | `/usr/local/rustup`, `/usr/local/cargo` | container-local; restored by Feature and setup script |

## Worktrees

When worktree mode is `volume`, create and remove worktrees only with `scripts/dev/manage_worktree.sh`.
The helper places them below `.worktree`, locks every managed worktree, refuses dirty removal, and never deletes branches.
The main checkout remains the integration checkout; perform task work in a managed worktree.

## Beads

Use `bash scripts/dev/beads.sh` from any worktree to access the shared embedded Dolt database. The wrapper resolves the main checkout and serializes CLI access with a file lock. Do not initialize separate worktree databases or use `bd worktree` to manage worktrees. `bash scripts/dev/setup-beads.sh` installs/restores the CLI without rebuilding; `--update` backs up with the existing binary before installing the latest stable release. postCreate restores the CLI and preserves the database. Full backup/restore uses `bd backup`, not a JSONL export. See [the workflow](../docs/development/beads-workflow.md).

## Inference models

When GPU mode is `nvidia`, place See-Through, DWPose, Hugging Face, Torch, and similar model downloads under `$INFERENCE_CACHE_DIR`.
The generated environment maps Hugging Face hub/Xet/assets and Torch caches into that directory. Do not place these general-purpose model weights in the repository or in `/home/vscode/.codex`.

Quoridor AI models are an explicit exception: repository-local storage is allowed. Only final adopted models and their provenance, distribution terms, hash, size, and feature-schema manifests belong in Git, under `apps/web/public/models/`. Keep all experimental, comparison, and intermediate training models under `models/experiments/`, excluded from Git regardless of size. Add the ignore rule when that directory is introduced. Check the final model's distribution size before adoption.

Framework and CUDA package versions remain project-managed; this Dev Container only exposes the NVIDIA GPU and persistent cache.

Godot remains on software rendering (`LIBGL_ALWAYS_SOFTWARE=1`). NVIDIA access is for inference compute, not editor or Xvfb rendering.

## Toolchain updates

The postCreate hook runs .devcontainer/update-toolchain.sh after container creation or rebuild. It updates Godot 4.x to the latest stable release, Node.js to the latest LTS, and Codex CLI, uv, gdtoolkit, and VS Code CLI to their current stable releases. These versions can change between container builds; the exact installed versions and update time are recorded in /home/vscode/.local/share/godot-devcontainer/toolchain.json.

To update the tools in an existing container, run:

    bash .devcontainer/update-toolchain.sh

The updater does not run on each container start.

## Rust and Python setup

Rust uses the official Dev Container Feature. `scripts/dev/setup-project.sh` also installs the environment into an existing container without rebuilding. Add `--update` to update Rust stable, wasm-pack, managed Python and training dependencies. Python packages are recorded in `tools/training/uv.lock`; check and commit its changes after successful updates. The current training target is Linux x86_64 with an NVIDIA GPU.

postCreate updates and verifies Rust, then restores and verifies the Python training environment. Training libraries are installed, but no model training is started. Runtime version and verification reports are written to `~/.local/share/quoridor/`. See `docs/development/rust-python-environment.md` for individual commands and storage overrides.
