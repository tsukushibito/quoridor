# Native data learning cycle

The package consumes Rust-produced, verified memory-mapped tensors. It reuses
`tools/nnue-training` configuration/model/measurement code. There is no Python board
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
