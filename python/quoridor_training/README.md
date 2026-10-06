# Native data learning cycle

The package consumes Rust-produced, verified memory-mapped tensors. Configuration, models, scaling and measurements live in this package. There is no Python board
reconstruction in the training hot path. `binding.features(library, prefixes)` optionally
calls the `quoridor-data` C ABI once per bulk batch (build `-p quoridor-data` to obtain its
shared library).

`python -m quoridor_training.train train --cache CACHE --output OUTPUT [--config JSON]`
records train/validation curves (including steps 0, 1, 2, 5, 10), checkpoints, scaling,
dataset signatures, native weights, ONNX and candidate freeze. The config exposes width,
optimizer, learning rate, samples/steps, CPU/CUDA device and measured limits. Corpus tensors
stay mapped on CPU; bounded batches move to CUDA. Train-only scaling and masks are fixed
before validation/test. Game sampling groups are prepared once, not scanned per step.

`python -m quoridor_training.train test --cache SEALED_CACHE --training TRAIN --output TEST`
checks frozen weight signatures before one test pass. Test observations do not select a
checkpoint or alter hyperparameters. Missing labels/ineligible rows remain excluded.
Repeated comparable validation use is tracked separately from an independent test or arena.

`quoridor-runner cycle --config JSON` orchestrates generation, cache, training, freeze,
one test and fresh native arena. The explicit virtualenv interpreter path is retained
without resolving it to the system Python. Each child is in its own process group with
bounded deadline and termination/wait cleanup; each stage has a log and failures persist.
The small cycle validates implementation connections, not highest AI strength.

Pinned public Sigma preparation uses `python -m quoridor_training.public_sigma --config JSON`.
It wraps the existing child guardian, processes one compressed shard at a time, and writes
lossless QF1 bitsets plus STM distances and binary source observation references. The plan
fixes sampling/split seeds before outcomes. The current protocol uses original first-half
observations, keeps independent same-input observations, and excludes unknown-termination z0. Eligibility
counts describe sampled candidates; unsampled eligibility is unknown.

The same `cache.load` and trainer consume bounded expanded batches. The compact loader
opens train/validation only; test labels stay in a separate partition until explicit test
release. Model-input groups are secondary metrics, not reconstructed games. Compact runs
save aggregate curves and compressed visit arrays, and can use epoch-based early stopping.
