# Research build, manifest, run and finalization

`scripts/dev/research-lifecycle.py` is the maintained build/run/finalize entry; the approved arena361 source generalises experiment data beyond the original355/358 campaigns. A new affected image is still required before using that source for an arena RUN. It replaces the historical software-v4–v19 classifier/salvage path. Those artifacts, failures, fees and private images remain historical evidence; they are not prospective prerequisites. No source-review chain, diagnostic-span/count whitelist, transitive C/Make/header reconstruction, model copy or second scheduler is used.

A normal trusted offline Cargo build runs under frozen authored source, the adopted commit and necessary patch, Cargo.lock/dependency references, absolute tool identities/versions, features/flags and relevant environment. Generated outputs are protected by the isolated owned target and one writer. Cargo JSON `build-finished.success=true`, actual exit 0, returned guardian cleanup and structured runner executable artifacts are required. Multiple primary warning spans are ordinary Cargo output, preserved in the full bounded log. Clippy uses the ordinary affected scope with `-Dwarnings`; code must be repaired or an explicitly justified temporary code exception must name its retirement. There are no comparison-only diagnostic exceptions.

## Public commands and ownership

Submit one frozen build/run intent through existing `research-job.sh`; its `argv` is:

```text
ABS_PYTHON -B ABS/scripts/dev/research-lifecycle.py build --intent ABS_INTENT --sha256 SHA
ABS_PYTHON -B ABS/scripts/dev/research-lifecycle.py run --intent ABS_INTENT --sha256 SHA
```

The job passes its directory in `QUORIDOR_RESEARCH_JOB_DIR`; the child records its actual supervisor, own child identity, originating runtime/job and immutable config fingerprint. Final publication joins that SAME runtime result/config/finished state and explicit direct reaping; a sibling or matching-argv unrelated job is refused. `cycle_process.execute` remains the sole child guardian, extended with `cwd`, exact `env` and a bounded byte sink. Every command returns directwait, descendant/handle cleanup, mask restoration and final receipt persistence facts. Disk process records that still say pending/attempted are not substituted for returned facts. The scientific caller is a child of this guardian, not a separate lifecycle.

After the outer research-job has finished, the owner invokes:

```text
ABS_PYTHON -B ABS/scripts/dev/research-lifecycle.py finalize --operation ABS_OPERATION --job-result ABS_RESULT --sha256 SHA
```

`finalize` launches no child. It matches the actual job config to the admitted intent, checks the outer result/cleanup and every full command/version log, checks durable data and all predeclared independent finalizers, and publishes `manifest.json`. `candidate.json` is always provisional. Readers refuse an `INCOMPLETE` marker even if a manifest file exists. All files and directory sync/close obligations precede the final marker unlink. No fallible report or cleanup operation follows that commit in the collector. A crash/durability guarantee or all-channel error recovery is not claimed.

Exclusive operation directories refuse a duplicate/restarted submit. An exclusive `finalizing` marker prevents repeating independent finalizers. Missing completion is UNKNOWN; a failed/cancelled completion is never reusable as a successful build. The original exception object is re-raised with independent capture/publication/cleanup failures attached. Partial scientific files/censuses remain available, while unpublished/missing work stays UNKNOWN. No automatic retries or salvage promotion occur.

The canonical nonblocking `/workspaces/quoridor/.artifacts/rust-migration/target/arena-software-writer.lock` covers admission, source checks, imports/TMP/children, waits and the critical data checks. No queue or idle lease is taken. The whole source/target/private/TMP/output allocation, family RSS including controller reserve, host reserve, FS and actual physical cores are checked. A current named compiler/game/browser peer refuses entry; any genuinely READY higher-priority science is honored by the owner before submission. Instantaneous scans are not future quiet certificates.

Only arena355.1 owns the one common target/private pool. The Root handover supplies literal target ownership and old-target retirement, without replaying its historical certificate chain. The stable new target has a writer/support marker and may be reused by the same writer for an ordinary affected rebuild; a foreign/unmarked target is refused. A fresh private filename preserves previous images, within the shared private cap. Maintenance does not create this target or execute Cargo before source acceptance and current admission.

## Bound files and schemas

Every persisted reference is `{path, sha256, bytes, mode}`: canonical absolute path, lowercase SHA256, exact length and a four-digit octal custody mode. Model manifests retain their actual modes, including BEST43 `0600`. `BoundControl` fields inside native configurations retain their existing `{path, sha256}` shape. They are joined to the full experiment references, not substituted for them.

- `quoridor.research.lifecycle-intent.v1`: `kind`, `owner`, `writer` for build, `cwd`, `output`, `env`, `limits`, bound `support`, bound `admission`, `intent_sha256`, `finalizers`; build adds `source`, `source_adoption`, `target_handover`, `target`, `private`, `TMP`, `tools`, `dependency_refs`, `commands`; run adds `experiment`, `artifact`, `argv`, `data_root`, `data`, optional separately priced `owned_outputs` and `TMP`. Data declarations must be inside the charged data root. Overlapping allocation roots are deduplicated; a separate scientific output cannot escape the same lifetime census.
- `source`: `commit`, nullable bound `patch`, exact `files` references, absolute `workspace`, full `manifest` and `lock` FileRefs, `compiled_sources` (flat named-key → source FileRef projection) and `cargo_configs` ({path, file: FileRef|null} exact directly searched configurations including witnessed absence). Cargo cwd equals this adopted workspace, and each Cargo argv names the exact adopted manifest using `--manifest-path` before `--`. Cargo.lock is the same adopted dependency. CARGO_HOME and all directly searched ancestor/home config paths are frozen; no transitive generated-header reconstruction is added. Actual zero-model bindings must equal the adopted compiled projection key-for-key and hash-for-hash. Root `quoridor.research.source-adoption.v1` records `status=ACCEPTED` and this exact source once, at adoption. It is recorded in the build; it is not recursively executed per run.
- `tools`: names `CARGO`, `RUSTC`, `RUSTDOC`, `CC`, `CXX`, `AR`, and `PYTHON` when saved-only analysis is needed, each `{file, version_args, version}`. Versions are obtained by guarded finite commands. Environment is explicit, including offline/no-install/j1/incremental0 and opt3/debug0. Relevant dynamically loaded libraries have exact files and version strings in the experiment; there is no blanket dependency exemption.
- `commands`: `{name, role, argv}`, with test/lint/build/bindings roles. Cargo commands are `test`/`clippy`/`build`, `--offline --locked -j1 --message-format=json-render-diagnostics`; no `cargo run`, extra workload or lint-allow workaround is admitted. Bindings is the actual copied runner's `research-bindings` port.
- `limits`: `family_B`, `controller_B=67108864`, `host_reserve_B`, `owned_B`, `log_B`, `free_B`, `worker_cpu`, `guardian_cpu`. Issued phase admission binds these, `owner`, exact support SHA and canonical intent digest. The digest is the sorted compact JSON of the intent excluding only `admission` and `intent_sha256`, avoiding self-reference. Family maxima are 6GiB build/2GiB native, with at least 4GiB host reserve. These are refusal bounds, not predicted peaks or science horizons.
- `quoridor.research.build-manifest.v1`: `kind=build`, final `status`, `artifact`, `compiled_sources`, `source`, source-adoption reference, tools/env/dependencies, checks for EVERY attempted command and tool version with actual returned guardian/full-log/Cargo facts, `originating_job`, `outer_job_result`, `outer_job_state`, cleanup/remaining, original/secondary errors and exact completion times. Only PASS with no marker admits RUN. This is the single artifact acceptance manifest.
- `quoridor.research.experiment.v1`: `phase`, bound `build_manifest`, `config`, `inputs`, `models`, `dynamic_libraries`, `schedule`, `numerical_qualification`, `canonical_plan_sha256`, `rules`, `distance_units`, `value_perspective`, `planned_slots`, nullable `batch`, exact `argv` template. Only `@EXPERIMENT@` and `@EXPERIMENT_SHA256@` are replaced with the actual bound envelope path/SHA; this avoids a self-referential SHA while the run intent freezes the full resulting argv. Phases are generation/materialize/compare/arena, or saved-only analysis. Models are `{descriptor, weights, evaluator_sha256}`; libraries are `{file, version}`. No models/cache are copied.
- `quoridor.research.numerical-qualification.v1`: actual `status=PASS`, exact `phase`, artifact/compiled-source/config/schedule/input/descriptor/weights/evaluator SHA bindings, rules, distance units, STM perspective, `remaining=[]`; compare additionally records qualified generation-source digest. It retains current numerical/history/clock qualification. The source build does not mint it.
- `quoridor.research.completion.v1`: `kind=run`, final status, experiment/build references, actual returned checks, `data` with bound durable files and partial census, outer job/finalizer facts, original/secondary errors, cleanup and times. It is an operation completion, not an independent strength certificate.

`data` intent declarations are `{name, path, limit_B}` and `data_root` is a fresh owned output. For a bound arena operation, `journal` and `result` are mandatory. The native journal is streamed without substituting console data: full per-game moves/observations, unique local game, global family through config opening references, schedule colour, complete local batch and result correspondence are checked. The approved plan declares the full campaign denominator and its exact batch partition; completeness is checked against that declaration. Historical355 remains512 slots in32-row batches, and historical358 remains256 slots in32-row batches. Counts never select the mode or authority. Failed/partial files remain referenced; missing planned slots remain UNKNOWN. Native statuses `goal`, `draw`, `forfeit`, `unknown` are preserved, without inventing a timeout-forfeit rule.

Additional owed independent finalizers are optional predeclared `{kind: data|journal, path, limit_B}` and must produce actual bound `quoridor.research.data-finalizer.v1` receipts with PASS, remaining[], same actual intent SHA and full file references. Every obligation is attempted independently, even after another fails. They do not replace the mandatory native journal collector or require a new review per run.

## Approved arena plan and completion

The integration-issued RUN intent and phase admission contain the same `approved_plan: FileRef`, covered by the immutable admission/spec digest. The maintained job pins the raw intent SHA; its guardian passes the intent path, raw SHA and immediate parent PID. Native entry checks this trusted launch context before accepting the plan. Environment values alone are not unforgeable authority, and mutual consistency of substituted Experiment/plan/qualification never chooses the expected approval identity. This is the existing trusted integration boundary, with no approval registry, signature layer or additional finalizer.

`quoridor.research.arena-plan.v1` declares explicit `evaluator_fixed_depth` or `evaluator_wall_time` mode, rules/units/perspective, ordered input/model/book references, matchups, selected families, typed slots and Config FileRefs for each batch. Contiguous global slots and complete declared family/colour coverage must match the exact nonoverlapping ordered batch partition. Models, requested depth/node/clock limits, TT and quantities are configuration; no mode selection uses a count, issue/run name or known input SHA. FileRef1MiB and4096-slot metadata caps are refusal bounds, not quantities or execution grants.

A fixed-depth action must return the requested `DepthComplete` iteration with finite coherent value/PV/action after inherited error, snapshot and legality checks. Capped partial depth stays UNKNOWN; genuine goal/third-repetition terminals remain separate. Thinking-clock mode keeps the existing authority receipt, legality outside the clock and matching reserve/drain contract. Complete LF-delimited journal records are validated in order; a first invalid complete row stops later validation, and a torn tail refuses the whole result after retaining its valid prefix census. Raw files, planned unknown slots, original errors and cleanup facts remain bound.

The six new Rust definitions and four original Python methods still need affected software qualification. The supplied R1 publisher-shaped four-case method passed once and is retained without replay. Source adoption is not a build, numerical/model qualification or new game permission.

## Native caller migration

The new ports use `--experiment ABS --experiment-sha256 SHA`:

```text
quoridor-runner strength-book ...
quoridor-runner strength-configs ...
quoridor-runner arena ...
quoridor-runner value-search-compare ...
```

`research-bindings` is the single zero-model compiled-source/artifact port. A research arena uses `arena --experiment FILE --experiment-sha256 RAW_SHA`; generic config and separate cost-qualification diagnostics cannot dispatch that Experiment. Ordinary functional arena/selfplay controls remain distinct. The old `strength-arena` alias and compiled fixed358 plan hash are removed from the current source.

The compare config is `quoridor.value-search-strength.compare.v2`: canonical plan/resources/book/manifests/output, with the old recursive `qualification` field removed. The experiment binds that config externally, avoiding a config↔qualification hash cycle. Its intent header is v2 with separate experiment and config SHA plus build reference; `compare-result.v2` and `compare-intent.v2` both name `experiment_sha256` and `config_sha256` explicitly; the ambiguous result v1 `plan_sha256` field is removed prospectively. Failure/row/tree/PV/census v1 work domains remain unchanged. Failed partial files join through the outer bound experiment/config and exact durable refs.

Generation request replaces `old_admission` with `old_prefixes`, a bound JSON array of the SAME eight preserved OPEN prefixes. Its canonical scientific prefix digest, rejection logic, RNG and all128 family selection are unchanged. Materialization keeps book/templates/descriptors/weights/output; it binds the same experiment models and current image. The arena entry validates the approved JSON plan, exact declared Config FileRef, model identities, book/full-history references and schedule family/colour partition before runtime. No copied engine, alternate evaluator, TT change, rule/clock change or automatic calibration is introduced.

Saved-only analysis uses the same accepted build and experiment manifest, with `phase=analysis`, a pinned Python tool from the build, exact inputs/config/argv and fresh report output. It is run by this same guardian. The child receives `QUORIDOR_LIFECYCLE_INTENT` and `QUORIDOR_LIFECYCLE_PARENT_PID`; it validates the maintained caller context and must not reacquire the canonical lease. No new registry, nested lock, build target or native/model call is needed for that saved phase.

The maintained saved-analysis child is `python/quoridor_training/research355/stream355.py`. Its sibling modules contain the current scientific aggregation and file/lifecycle adapters; the current run intent binds all six runtime modules separately from historical build provenance. Configure its child argv as pinned Python, `-B`, the absolute script path, `--experiment`, the bound experiment path, `--experiment-sha256`, its raw SHA, and `--intent`, the exact parent intent path. This child writes only bounded report data; the parent remains the sole authoritative finalizer. Historical `.artifacts` source packets are reconstruction evidence, not current executable dependencies.

`scripts/dev/check-research.py` includes the maintained lifecycle adapter tests. The focused source-only command is `python3 -B -m unittest discover -s python/quoridor_training/research355 -p 'test_lifecycle*.py'`. These fixtures use synthetic inputs and mock the parent/build; they do not qualify a real build, model or scientific result.

Frozen science remains 128 families/512 colour slots, matched32/96 COMPLETE4 calls,8 ALLlegal depth2 trees and at most16 prebound differing parents/192 stronger calls. D is maintained `(0,8)` tanh of normalized wall distance; BEST51 and BEST43 exact descriptors/weights/coefficients are unchanged. Standard2p goal-first/legal-third/200 UNKNOWN, 100ms authority receipt/5ms reserve, legality outside, matching drain, PVS/fullwidth/TT4096/1MiB, ScalarFT/guarded head and thread1 remain unchanged. No N/fit/default/seal/pause323 decision is altered.

Each check records attempted argv/role, status, nullable `guardian_return`, nullable `full_log`, nullable `persisted_process_receipt`, `capture_complete`, original `primary` and independent `secondary` errors before throwing. A returned nonzero exit is retained even when rejected. An unreturned exception keeps the exact closed partial full capture and durable process receipt when available; its pending/attempted fields remain a separate provenance domain, not fabricated returned cleanup. Mandatory version/command logs and complete returned captures are checked independently at authoritative publication.

Scientific status and cleanup are separate: an authoritative FAILED can have cleanup_complete=true ONLY when the actual returned commands and SAME joined outer job prove directwait/cleanup. Unreturned or missing cleanup remains false/UNKNOWN. Such a finalized FAILED preserves validated available files and planned-denominator missingness, never qualifies BUILD or scientific completion. Candidate/INCOMPLETE stays inadmissible.

For saved analysis, phase=analysis/planned_slots=0 denotes a non-game operation; analysis config/report still retain the underlying512 scientific denominator. Numerical qualification remains a required non-null FileRef. Input/descriptor/weights/evaluator SHA fields are arrays in exact input/model order; compiled_sources_sha256 is SHA256 of serde JSON compact sorted full source map. Exact rules/units/perspective are research-standard-2p-threefold-goal-first-v1 / wall-distance/80 / side-to-move. Clock is in the exact bound arena config (engine time_ms100, strict_unknown, reserve5) and actual qualification, not a new experiment field. QUORIDOR_LIFECYCLE_INTENT is full intent-file SHA (not internal admission digest/path), PARENT_PID is actual immediate guardian parent. The saved-only child cannot reacquire the canonical lease.

## Generation-only bootstrap

`numerical_qualification` is null or omitted only for `phase=generation`. This phase requires
`models=[]`, `planned_slots=0`, `batch=null`, and the exact six-argument `strength-book`
Experiment template. The accepted matching build/artifact/source, explicit library file/version
array, config, two ordered full input references (fixed plan then original OPEN8), and complete
fixed512 schedule are checked before any output or geometry. A null library array is refused;
an empty array must reflect the actual absence of required dynamically loaded libraries.
The generation request output must equal the charged, fresh run `data_root`.
Every other phase requires a non-null numerical FileRef before asset/output admission.

Generation declares four durable data names: `start` → `generation-start.json`, `book` →
`book.json`, `schedule` → `schedule.json`, and `result` → `generation-result.json`.
There is no per-game journal because no games are played. The existing native bodies and
native book/result schemas are unchanged. Lifecycle `data.generation` uses
`quoridor.research.generation-evidence.v1`, binds the actual artifact, compiled source map,
Experiment/config/input/schedule references and rules, and records zero models/Search/games,
`numerical_qualification=null`, and the underlying scientific512 denominator. It checks
complete128 metadata and native start/book/schedule/result correspondence, without replaying
geometry or qualifying legal history, models or strength. Durable files remain individually
bound in `data.files`; final status/partial errors/owed finalizers retain normal lifecycle semantics.
Only the authoritative completion after directwait/cleanup/finalizers is consumable; candidate
or INCOMPLETE files never admit success. Generation PASS is data-operation completion,
not numerical PASS. Downstream materialize/compare/arena/analysis still require actual
book/history/input/model/clock qualification under the current image.

## Generation source domains and failed-origin inputs

The native arena generation domain has exactly34 maintained keys. The qualified research
artifact domain has exactly35: the same34 plus `runner/sigma_qualification.rs`. Publisher
`generation_source_correspondence` requires both complete named key sets, lowercase SHA256
values and equality of every shared value. Extra or missing keys are refused; there is no
unknown-key filtering. Neither the generator body nor full qualified artifact/numerical source
coverage changes. `data.generation.compiled_sources` remains the full35 qualified map;
`native_compiled_sources` retains the exact34 start/book map, with explicit domain names.
`generation_compiled_sources_sha256` is sorted-key compact JSON of the native34 map.
Raw `book_sha256`/`schedule_sha256` still join the original native result; separate
`book_semantic_sha256`/`schedule_semantic_sha256` describe sorted-key compact parsed values.
The frozen Experiment schedule FileRef, semantic9bfb and native output raw digests remain
separate. No source map or raw file is rewritten to force equality.

The maintained publisher's read-only `generation_input_data(completion_FileRef)` checks
an existing authoritative generation completion, whether PASS or FAILED, only after confirmed
cleanup and no INCOMPLETE marker. It joins the original bound intent/Experiment/build and
rechecks precisely the original four durable files, within their declared4MiB aggregate cap.
It returns the normal data envelope with `origin_completion`, `origin_status`, `origin_primary`
and `origin_secondary` intact. A data correspondence PASS does not change the failed origin,
create a replacement generation success certificate, or qualify history/models/numerics.
The helper starts no child and writes nothing; it copies no book or model and replays no
geometry. The caller uses the existing guardian/lifetime when used for a saved-data phase,
without nested lock acquisition. Downstream scientific input/history/model qualification and
current-image numerical/clock/lifetime admission remain necessary. No actual scientific input
qualification is minted by these synthetic source tests.

## Native image and current caller bindings

A successful immutable BuildManifest retains its complete authored source snapshot as build
provenance. RUN reuses the qualified artifact with its complete native compiled-source projection,
workspace Cargo manifest/lock, authored crate/build inputs, rust-toolchain, Cargo configurations
(including absence), dependency and tool file/version bindings. Pure Python/documentation/test
changes do not require another native build or a refresh of the historical authored snapshot.
BUILD and its finalization continue to verify the complete frozen build source.

Each current RUN intent requires `caller_sources`, an exact FileRef array for the adopted
`scripts/dev/research-lifecycle.py`, `scripts/dev/research-job.py`,
`python/quoridor_training/cycle_process.py`, and `python/quoridor_training/snapshot.py` in its
current maintained root. An analysis intent additionally binds `stream355.py`, `lifecycle355.py`,
`io355.py`, `observations355.py`, `producer355.py`, and `strength355.py` under
`python/quoridor_training/research355`. Analysis uses the pinned Python tool and `-B` plus that
exact maintained stream entry. The parent checks current caller/import and native/science refs
before entry and after direct return; it never runs tool version commands to refresh them.
Current source acceptance is recorded at adoption; these are ordinary entry FileRefs, not another
review/admission chain. Experiment/native schemas, scientific counts and numerical requirements
are unchanged. Caller source bindings belong to the run intent, not the old BuildManifest.

`generation_input_data` accepts only a canonical absolute SHA-bound `manifest.json` with no
`INCOMPLETE` sibling. A retained `candidate.json` is never authoritative even if the marker has
been removed. Valid data correspondence from a finalized FAILED manifest preserves the original
primary and all authoritative outer/owed secondary errors through its origin reference; it does
not change that run to PASS or mint numerical qualification.

## Finite command budget and stopped-owner failure publication

A prospective intent may bind `command_timeout_seconds` as a positive integer. The intent admission digest includes this field. The originating job must have a finite `max_runtime_seconds` at least 60 seconds greater, leaving the selected cleanup/publication reserve. For continuation360 the already selected pair is worker840/controller900. The monotonic deadline starts when the owning lifecycle invocation actually enters and is shared by its preparation and all commands; it never restarts on the next command. Source implementation and pre-launch preparation have no such clock. The existing guardian receives that deadline and retains its ordinary termination, directwait, handle and error behavior. Old intents without the field retain their original invocation facts; this change neither edits those intents nor authorizes a scientific retry. New approved finite operations should declare the field explicitly.

Normal `finalize` also handles a stopped single-command RUN whose owner exited before writing `candidate.json`. It first joins the original operation INCOMPLETE marker and copied/admitted intent to the canonical owned runtime result, config fingerprint, finished state, exact lifecycle argv, support, owner/output, and recorded supervisor/lifecycle/native identities. The lifecycle and native identities must be stopped; a supervisor still delivering a notification is administration. The exact originating result must be failed, timed_out or cancelled with nonzero exit, directreap and outer cleanup. Unrelated, live, ambiguous and duplicate origins refuse before a finalizing marker. Missing multi-command BUILD candidates are unsupported and refuse.

This produces only an authoritative FAILED/CANCELLED manifest through the same finalizer, without creating a candidate file or launching a child. Original exit/error facts remain primary. Available data files, missing footer errors, dated persisted running process receipt and owed finalizer errors remain separate. A missing returned guardian cannot prove inner cleanup, flush, sync, close, signal-mask restoration, final-record persistence or a complete scientific census. The operation's INCOMPLETE marker is removed last only after ordinary failure publication; the data journal's INCOMPLETE remains. Data and numerical status cannot become PASS. Publication IO errors retain the accumulated originating/secondary facts in the raised exception notes without recursive reporting. No retry, recovery registry, alternate executable or source-certificate chain is introduced.

The new owning tests are `tools/research-session/test_lifecycle_abnormal_exit.py`. They use actual small Python controller/child termination and deadline cleanup plus synthetic metadata fixtures; these are software tests, never scientific, model, native-image or numerical qualification.

### Independent origin for a missing candidate

The first claim retains `originating_job` in the operation's `INCOMPLETE` marker before child launch. A closed same-intent runtime is insufficient: its exact runtime, job, config fingerprint/FileRef, supervisor and lifecycle identities must equal that independently retained tuple. Ambiguous origin input refuses before `finalizing` is created.

Historical markers without this tuple require `finalize --origin-record PATH --origin-sha256 SHA`, naming one immutable Root integration-custody file under Main `research-data`. Schema `quoridor.research.operation-origin.v1`, status `ACCEPTED`, binds exact FileRefs `operation_marker`, `intent`, `result`, `state`, `persisted_process`, and the same `originating_job` tuple. Root derives that decision from already bound original STOP/origin evidence; the publisher never reconstructs a historical parent relationship from the offered runtime. This is one operation-specific input decision, not a recovery registry or another completion. Its FileRef remains in `abnormal_origin.independent_origin_custody`. Missing, mismatched, ambiguous or live origins refuse.

The original assessment remains timed out and incomplete. No successful candidate, guardian return, inner cleanup, journal close, numerical PASS or complete census is manufactured. Normal finalization alone publishes FAILED/CANCELLED and removes only the operation marker last.
