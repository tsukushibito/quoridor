# NNUE teacher, distance residual and tanh verification

Human authorization: 2026-10-08. Beads epic `quoridor-4lc.342`; integration
`quoridor-4lc.342.4`, learner `.342.1`, search `.342.2`, arena `.342.3`.
This is independent of paused `quoridor-4lc.323`. Existing BEST51 and closed
331/336 results are historical references, not a new baseline or reusable fit.
The machine contract is
[plan.json](../../research-data/ai-sigma/teacher-distance-tanh-v1/plan.json);
[whole preparatory/pilot support](../../research-data/ai-sigma/teacher-distance-tanh-v1/resources-pilot.json)
retains the original 50GB proof and all historical charges and UNKNOWNs.
The [forward compiler-recovery overlay](../../research-data/ai-sigma/teacher-distance-tanh-v1/compiler-recovery-resources-v1.json)
adds the retained unexpected toolchain and prospective failure/TMP reserve while
holding every original component upper. It does not change the failed job's
status or certify the unobserved installer peak. Future compiler children bind
absolute RUSTC/RUSTDOC, explicit RUSTUP_TOOLCHAIN and RUSTUP_AUTO_INSTALL=0.
Beads remains the source of task state; this document defines the experiment.

## Current executable boundary

Implement maintained data/schema/model/search/native interfaces and qualify their
changed boundaries. Generate and report exactly the 64-game pilot below. After
measured throughput, costs and coverage, the human chooses full generation
quantity N. N is currently unset. Do not choose 1000/10000, launch full generation,
four fits or the 96 development games before that decision. Source preparation
may continue while N is pending. Eight-way combinations, multiple seeds, added
data and model/default adoption remain future human decisions.

The learner owns data labels/cache/Python training, model and export; search owns
AI/NNUE score, terminal, TT and native interfaces; arena owns runner generation,
clocks, outcome auditing and pilot controls. Each writes a separate managed
worktree based on `e2e7181`, with only the integrator changing main/Git/index.
Consumers use stopped, bound schema/interface handoffs; no owner-wide idle or
reply-only ACK is a dependency. Independent reviews cover changed label/split,
math/score and pilot evidence boundaries; reuse unchanged passing proof.

The D-only pilot needs its actually consumed generator/label/chronology and
integer-distance boundaries. It does not wait for unconsumed six-view NNUE score
implementation or whole342.2 completion; unchanged fixed-D interfaces may reuse
their passing source proof. Later time-controlled evaluations explicitly bind
[343's thinking-clock contract](sigma-deadline-control-repair-v1.md): authority
receipt of the immutable Action within100ms including communication, legality
outside thinking and admitted-work drain before opponent time. Old331/336
full-caller acceptance is historical and is not silently inherited.

## Fixed-D pilot and data

Both sides use frozen original D(a0,b8), alpha-beta depth3, max_nodes100000, PVS,
TT4096. There is no per-move wall timeout. Solver, continuation ordering and
contact-distance correction are OFF. Preserve actual completed depth, limits,
nodes and existing root value without an additional search. Incomplete search
must not be described as completed depth3.

Schedule four new prefixes at each length4..19, exactly64 games. Prefix RNG seed
is20261008; generation is legal and target-blind. Use at most32 candidate attempts
per requested prefix, reject terminal prefixes and exact/reflected duplicate
prefixes, and preserve planned failures if attempts are exhausted. Do not use the
arena evaluation book or manufacture independent data through deterministic
colour-swapped repeats of identical D/D games. 64 measures operational coverage
of16 prefix lengths, not statistical sufficiency for training.

Use standard2p plus legal third-occurrence draw and goal priority. The200
operational ply cap, error, cancellation, forfeit or lack of a legal completed
move is UNKNOWN, with neither teacher and eligibility false. Preserve all
scheduled, failed and censored cases; no blind retry or replacement. Validate
parent/move/repetition chronology, full prefix/history and goal precedence.

Persist game/family IDs, exact prefix/history, STM, rules/source/search metadata,
termination reason, winner and both terminal integer wall-only distances. For
each eligible goal-completed row, z is +1/-1 in that row's STM perspective and
the distance teacher is opponent terminal distance minus own terminal distance.
For genuine threefold z=0 and the distance LEARNING target=0, while preserving
the actual geometric terminal margin separately even if nonzero. UNKNOWN has no
true terminal teacher; final geometry, when available, is separate from a
terminal state. Do not overwrite scalar-z storage or reconstruct missing old
public history/terminal states.

Split the full corpus T80/V20 by complete game family, keeping identical and
reflected prefix series in the same group. Freeze deterministic grouping and
split before outcomes, with uniform row eligibility across all conditions and
no output-based filtering. Record the deterministic whole-family rounding rule
in the schema/manifest. Pilot examples may be retained only under explicit same
generator/source/family-partition provenance. Existing sealed labels stay unread.

Report whole throughput/costs, completion/draw/UNKNOWN fractions, distinct and
duplicate positions, pawn-contact, wall-stock, opening/endgame coverage,
row/storage quantities and priced full-volume options. The human N decision
follows this report; pilot costs are not refunded.

## Four fits after N

| Condition | Teacher             | Distance bypass | Training output |
| --------- | ------------------- | --------------- | --------------- |
| A         | outcome             | ON              | scaled tanh     |
| B         | raw terminal margin | ON              | scaled tanh     |
| C         | outcome             | ON              | linear          |
| D         | outcome             | OFF             | scaled tanh     |

One seed and common freshly initialized parameters, input order, RNG and T-only
statistics. QF1+D/FT32/H32/Zero4/FP32, dropout0, ScalarFT and adopted guarded AVX2
noFMA head. Initialize the output head to zero. Distance inputs remain in D;
removing them is a separate future experiment. BEST51 is not fine-tuned or
silently reinterpreted from logit residual to distance-step residual.

Let s = integer current(opponent distance - own distance) + NN residual when
bypass is ON, and s = NN output when OFF. NN residual/output is in raw distance
steps. F(s)=80*tanh(s/80); linear output=s. Outcome targets are80*z; margin targets
remain raw steps. MSE is divided by80² for shared loss units; report raw score
errors too. No label clipping or replacing raw margin with tanh labels. Existing
D features use D/80 before T-only standardization; the integer bypass comes from
canonical integer geometry, not reconstruction from rounded standardized input.
Record actual input statistics and zero-variance handling; do not fit score
units/scales from V or outcomes.

Common Adam: batch2048, initialLR.01, decay.5, plateau patience1, existing minLR
1e-6, reflection50%, workers2, weight_decay0. Initial seed19080311 and reflection
seed19080314; warmup min(257, updates_per_epoch). Normalized V-MSE selects strict
BEST. Significant improvement threshold max(abs1e-8, rel1e-4\*reference), early-stop
patience8; keep strict BEST separate from significant-improvement reset. Freeze
the complete recipe after N. No training wall cap, manual epoch accuracy choice
or LR sweep. Scientific/physical failure stops the affected fit and preserves it;
an UNKNOWN in-progress optimizer update is not automatically recovered.

## Score and inference contracts

Four models produce six evaluation configurations: A-F, A-raw, B-F, C-raw, C-F,
D-F. A/C raw and F views share identical parameters; changing inference view
does not add a fit. Explicit model identity includes score version/units,
distance bypass, training and deployed transforms, scale and parameter SHA.
Dataset/cache identity includes both teachers and terminal provenance.

Use weight-derived conservative legal-input score bounds, outward conservative
arithmetic and finite parameter/output guards. Freeze one compatible match score
convention in which true WIN/LOSS dominate every allowed nonterminal value for
all views/opponents. Refuse unrepresentable/unsafe bounds; do not clip raw scores
to disguise range errors. Terminal status is explicit, not inferred from
abs(value)==2 or another magic number. Preserve default production model/score
behaviour; experiments require explicit configuration. Model/view/score version
separates TT sessions. Qualify terminal adapters and PVS/TT windows against the
new value contract while retaining original fixed-D nonterminal math.

## Qualification and later evaluation

Independent integer geometry/margin/STM/draw/UNKNOWN/reflection/family tests must
reject invalid/partial outcomes without labels. Check linear residual add,
scaled tanh, source/inverse provenance, finite parameters, saturation, gradients
and learning curves. Teacher-specific MSE does not rank different objectives;
report both teacher errors/signs and games with explicit units/scopes. Numeric
tables/CSV suffice; images require explicit human request.

For each model, independent Torch16 fixed-input references plus affected legal
child/full-delta/parentundo/error/cancel/Counted boundaries. Numerical alert is
abs1e-5 + rel1e-4\*abs(reference) on raw-step scores divided by80; retain raw-step
discrepancies too. Reuse unaffected proof rather than repeat unrelated suites.
Complete common small trees check monotone raw/F ranking, ties, terminal
dominance and PVS/TT validity. Adaptive search reports actual Action/PV/depth/work,
not exact cross-model counters. Finite qualification is not all-model proof.

Report head/full-delta/setup/drop cold-search costs, achieved depths, nodes,
evaluations, cutoffs and real work changes. Shallower work is not speed and fewer
nodes is not arithmetic throughput. Isolate quantitative jobs from builds,
browser and CPU/GPU analysis; do not bundle profiling/ordering/solver experiments.

Only after N and all six frozen native/caller qualifications: six ×16=96 planned
development games versus unchanged fixedD, the existing OPEN eight-family
colour-paired book,100ms total/5ms reserve, realTT4096/thread1/equal CPU and current
legal-third/goal-first/200UNKNOWN rules. Keep failures/late/cap/UNKNOWN in planned
denominators and complete-pair bounds; no conversion to losses/draws or reruns.
One seed/small correlated book supports no Elo, general superiority or default
promotion. Report one-factor and train/deployment interaction, uncertainty and
whole fees.

## Execution and acceptance

Before each owner's first ordinary command verify applied danger-full-access,
approvalPolicy never, model gpt-6.1-sol/high and saved session cwd. Keep source
immutable for readers/jobs, one canonical nonblocking Cargo writer, fresh
physical/resource/input/private/proof guards and isolated actual fair intervals.
Use the existing finite job/wait/cleanup/notification procedure, no periodic LLM
supervisor or duplicate status framework. Raw/failure/source/private/TMP/review/
Git/cleanup costs all belong to the supported whole phase. Main full phase is
gated by explicit N, then actual bindings/readerSTOP/physics/soleCargo/fairquiet;
there is no additional human method ACK. Paused323, seals, historical results,
fees, UNKNOWNs, old models and production defaults remain unchanged.
