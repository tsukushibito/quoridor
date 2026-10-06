# Dev Container storage policy

This project keeps generated state out of the host checkout and separates caches by purpose.

| Data                                                 | Location                                                                                                | Persistence                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Managed Git worktrees                                | `${containerWorkspaceFolder}/.worktree`                                                                 | `volume` mode                                                |
| Research models/checkpoints/inputs                   | `${containerWorkspaceFolder}/.worktree/assets`                                                          | same worktrees named volume; independent of checkouts        |
| Shared Beads database                                | `${containerWorkspaceFolder}/.worktree/.beads-state`                                                    | worktrees named volume; independent of individual worktrees  |
| Beads full database backup                           | `${containerWorkspaceFolder}/.artifacts/beads-backup`                                                   | host checkout, Git-ignored; not protection against host loss |
| Inference models and framework downloads             | `/home/vscode/.cache/inference`                                                                         | named volume only in NVIDIA mode                             |
| Training Python, uv packages and virtual environment | `$INFERENCE_CACHE_DIR/python`, `$INFERENCE_CACHE_DIR/uv`, `$INFERENCE_CACHE_DIR/envs/quoridor-training` | same named volume                                            |
| Rust toolchains / Cargo / wasm-pack cache            | `/usr/local/rustup`, `/usr/local/cargo`                                                                 | container-local; restored by Feature and setup script        |

## Worktrees

When worktree mode is `volume`, create and remove worktrees only with `scripts/dev/manage_worktree.sh`.
The helper places them below `.worktree`, locks every managed worktree, refuses dirty removal, and never deletes branches.
The main checkout is the durable canonical research checkout. Use managed worktrees for parallel changes and comparisons, with one writer per file and one integration owner for normal Git index/commit operations. Do not maintain perpetual copies of roles, documentation or active source. Keep required models, checkpoints and inputs under `.worktree/assets/` on the same persistent volume, independent of code checkouts. Preserve the shared Beads database and locks and all active worktrees. Retire obsolete checkouts only after preserving unique information, verifying restoration and waiting for asset readers to stop naturally; use the managed helper for registered worktrees. Record original-to-current asset paths without changing historical run records. Do not retain compatibility symlinks or obsolete source trees as assets.

## Beads

Use `bash scripts/dev/beads.sh` from any worktree to access the shared embedded Dolt database. The wrapper resolves the main checkout and serializes CLI access with a file lock. Do not initialize separate worktree databases or use `bd worktree` to manage worktrees. `bash scripts/dev/setup-beads.sh` installs/restores the CLI without rebuilding; `--update` backs up with the existing binary before installing the latest stable release. postCreate restores the CLI and preserves the database. Full backup/restore uses `bd backup`, not a JSONL export. See [the workflow](../docs/development/beads-workflow.md).

## Inference models

When GPU mode is `nvidia`, place See-Through, DWPose, Hugging Face, Torch, and similar model downloads under `$INFERENCE_CACHE_DIR`.
The generated environment maps Hugging Face hub/Xet/assets and Torch caches into that directory. Do not place these general-purpose model weights in the repository or in `/home/vscode/.codex`.

Quoridor AI models are an explicit exception: repository-local storage is allowed. Only final adopted models and their provenance, distribution terms, hash, size, and feature-schema manifests belong in Git, under `apps/web/public/models/`. Keep experimental and comparison models under `.worktree/assets/models/` and intermediate training checkpoints under `.worktree/assets/checkpoints/`, excluded from Git regardless of size. Resolve these persistent assets through `research-paths.json`; do not bind them to a disposable code checkout. Check the final model's distribution size before adoption.

Framework and CUDA package versions remain project-managed; this Dev Container only exposes the NVIDIA GPU and persistent cache.

## AI research data

Preserve experiment and verification data in the canonical main Git history under `research-data/ai-sigma/`. Keep small configurations, summaries and reproduction manifests directly in Git; use compressed per-experiment/run archives for large observations and necessary logs. `.artifacts/ai-sigma/` is the live-output and extraction workspace. Verify Git preservation and restoration, and maintain active readers' paths, before removing redundant working copies. This is local research Git storage; it does not authorize pushing or publishing data.

Resolve code, data, live output, legacy models and shared environments through `research-paths.json`; record resolved absolute asset paths and hashes in each run. Moving the code checkout does not require copying models or changing the shared environment. New models/checkpoints belong in an explicitly bound ignored asset location; retained legacy paths remain valid until their readers and reproduction manifests are migrated.

Use `scripts/dev/research-storage.py` with a directed roots/reservations manifest to account for current allocated bytes and overlaps. Shared Git, dependencies and uv cache have explicit categories; same device/inode storage is charged once, and reservation accounting adds only its unused portion. Logical file bytes, inode allocation, reflink physical sharing and past peak are distinct. Unknown retained storage stays unknown, never free capacity. The current bounded observation and unresolved attribution are in `research-data/ai-sigma/262-maintainability/storage-current.json`; it does not authorize parent-budget admission.

Reproducible, unused binaries, Wasm builds, build caches and duplicate source copies are disposable. Preserve uncommitted source, active runtime files and the minimum shared inputs/models/dependencies needed for reproduction. Account for Git storage and temporary migration copies within the existing research storage limit. See `docs/development/ai-research-experiments.md` for the current rules.

Godot is not a project requirement. Its previous installed tools and cache volume are left untouched, while new containers no longer mount or prepare that cache. NVIDIA access is for inference/training compute; browser and Xvfb rendering keep their own settings.

## Toolchain updates

The postCreate hook runs .devcontainer/update-toolchain.sh after container creation or rebuild. It updates Node.js to the latest LTS, and Codex CLI, uv, and VS Code CLI to their current stable releases. These versions can change between container builds; the exact installed versions and update time are recorded in /home/vscode/.local/share/quoridor/toolchain.json.

To update the tools in an existing container, run:

    bash .devcontainer/update-toolchain.sh

The updater does not run on each container start.

## Rust and Python setup

Rust uses the official Dev Container Feature. `scripts/dev/setup-project.sh` also installs the project environment into an existing container without rebuilding. Its `--update` updates Rust stable, wasm-pack and Beads; it does not update managed Python or training dependencies. Explicit `setup-training.sh --update` handles those dependencies, recorded in `tools/training/uv.lock`; check and commit lock changes after successful updates. The current training target is Linux x86_64 with an NVIDIA GPU.

postCreate prepares and verifies Rust and the shared Beads tools. Training is optional: explicitly run `bash scripts/dev/setup-training.sh` to restore and verify the existing locked environment, or add `--update` for a requested dependency update. Neither postCreate nor `setup-project.sh` starts training setup. Existing installed environments, dependency caches and models remain unchanged by this source maintenance. Runtime version and verification reports are written to `~/.local/share/quoridor/`. See `docs/development/rust-python-environment.md` for individual commands and storage overrides.
