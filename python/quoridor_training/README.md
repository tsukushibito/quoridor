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
The maintained `original-full-v1` producer gives all43 original first-halves a per-row
native qualification opportunity. It stores 66B canonical geometry/STM distances/z/sourceID/
raw-input SHA, retains decisive same-input observations, isolates known opened original IDs,
and excludes unknown-termination z0. Naive LR teachers are not consumed. The historical174B
ID reader exists only for bound opened-ID intake; no174B production loader or sampler remains.

The same `cache.load` and trainer consume bounded QF1 batches. Online correct LR uses a
separate train-only Bernoulli RNG; original validation and diagnostics consume no reflection
RNG. `training.supply_workers` defaults to0; explicitly choose2 in config or normal CLI
`--supply-workers 2` for the qualified packed FP32/ordered prefetch supply. A bound input
requires the configured worker mode, and the guardian accepts no caller overrides. Workers
hold bounded batch slots, not a model/CUDA state or duplicate corpus. Buffer reuse waits for
transfer and consumer completion, and prefetch attempts never count as successful updates.

`train statistics` saves original T-only scale/constant before a bound fit. Full-original
training supports null scientific horizons with fullV epoch selection and scientific early
stopping. INITIAL/BEST/LAST retain their own states/positions. Curves are lossless append-only
JSONL.gz plus CSV, and visits use the v2 range/explicit NPZ encoding. The trainer never makes
PNG/SVG automatically; the maintained plotting CLI reads the requested saved JSONL.gz and
writes only the chosen image. Cleanup/recording failure cannot suppress other owed finalization.
The mathematical model, precision, optimizer, teachers, split and RNG order remain fixed.
