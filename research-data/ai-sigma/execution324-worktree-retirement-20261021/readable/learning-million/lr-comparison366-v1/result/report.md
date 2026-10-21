# Fixed low/high learning-rate comparison (issue 366)

Both independent high-LR warmstarts completed 200 updates / 50 epochs. The tenfold LR produced substantially lower outcome-teacher training error, but worse outcome validation error at LAST. For the raw completed-D6 teacher, both training and validation error decreased relative to the saved low-LR run. These are conditional measurements on the same opened validation families; they establish neither strength nor a generally optimal LR.

[Four-view PDF](low-high-lr-curves.pdf) overlays all saved points for A/B training teacher crossed with outcome/raw evaluated teacher, LR1e-4/1e-3, T217/V76 and each teacher's frozen analytic-distance/T-only-constant guides. The PDF is one page, 33310 bytes. No additional predictions or fits were made for plotting.

## Fixed inputs and actual work

One unchanged eight-game corpus, 341 immutable compact rows, six train / two validation families fixed before outcomes; 293 common eligible rows (217 T + 76 V), 48 excluded for BOTH teachers. The shared seven-binary manifest is 522b2dd6/43204B; the original generation plan285e remains truthful. Initial weights046fe / descriptor46ec / evaluator96a5 and scale f643 are unchanged. Both new candidates independently start the same initial weights with fresh Adam; B does not start from A. Only base optimizer LR differs from the accepted low-LR configurations.

Batch64, Adam betas(.9,.999), eps1e-8, weight decay0, same seed/order/reflection0.5, standardized head distance, FT32H32/Zero4QF1/tanhFP32, incumbent T-only scale and output bypass OFF remain fixed. No convergence early stop, new data, teacher mixing, model change, sweep, extra fit or play experiment.

Each run has 10850 training rows plus 3223 full-split selector rows = 14073 all-work forwards, below16023. Both complete exactly200 updates / 50 epochs and 11 full T/V evaluation points at updates0,20,...,200 (epochs0,5,...,50). INITIAL/BEST/LAST are the three checkpoint kinds; the 11 points are measurements, not 11 extra weights.

At step0 the initialized optimizer reports base LR. The maintained selected update path sets LR=base\*update/20 for updates1..20, then leaves base LR constant through200; high-LR update1 is5e-5, update20 is1e-3. All eleven saved high-LR observation points record1e-3; all saved low-LR points record1e-4. Per-update LR telemetry beyond these points was not emitted separately.

## INITIAL / BEST / LAST on both teachers

Full-split row-weighted MSE; the complete precision table and saturation values are in checkpoint-outcomes.csv / checkpoint-outcomes.json.

| Candidate | Checkpoint (update) |      z T |      z V | raw D6 T | raw D6 V |
| --------- | ------------------- | -------: | -------: | -------: | -------: |
| low A     | INITIAL (0)         | 0.607617 | 0.988319 | 0.324686 | 0.388978 |
| low A     | BEST (200)          | 0.508543 | 0.959763 | 0.313861 | 0.372287 |
| low A     | LAST (200)          | 0.508543 | 0.959763 | 0.313861 | 0.372287 |
| high A    | INITIAL (0)         | 0.607617 | 0.988319 | 0.324686 | 0.388978 |
| high A    | BEST (20)           | 0.544961 | 0.970754 | 0.322094 | 0.378706 |
| high A    | LAST (200)          | 0.094703 | 1.358004 | 0.489841 | 0.565931 |
| low B     | INITIAL (0)         | 0.607617 | 0.988319 | 0.324686 | 0.388978 |
| low B     | BEST (200)          | 0.637636 | 0.964890 | 0.231327 | 0.346032 |
| low B     | LAST (200)          | 0.637636 | 0.964890 | 0.231327 | 0.346032 |
| high B    | INITIAL (0)         | 0.607617 | 0.988319 | 0.324686 | 0.388978 |
| high B    | BEST (200)          | 0.666724 | 0.643014 | 0.078241 | 0.147568 |
| high B    | LAST (200)          | 0.666724 | 0.643014 | 0.078241 | 0.147568 |

High-LR A selects BEST at update20 (5 epochs); low-LR A, low-LR B and high-LR B select update200. Each selection uses its own teacher validation MSE with strict improvement. High-LR A LAST z T/V is0.094703/1.358004 versus low-LR0.508543/0.959763. Even high-LR A BEST z V0.970754 is above the low-LR BEST0.959763. Faster training reduction therefore did not yield better observed outcome validation in this fixed run.

High-LR B LAST/BEST raw D6 T/V is0.078241/0.147568 versus low-LR0.231327/0.346032. Its cross-teacher z V is0.643014 versus low-LR B0.964890; that comparison does not establish playing strength or a causal advantage. The raw D6 validation MSE remains above both its own T-only constant guide0.128861 and analytic-D guide0.032598.

Frozen guide MSEs (T/V): outcome constant0.999809/1.000191, analyticD0.785288/0.752184; raw D6 constant0.089834/0.128861, analyticD0.017759/0.032598. Constants are estimated only on the corresponding mapped teacher T scope. Analytic staticD is a guide, not completedD6 ground truth.

The trainer's existing saturation measure is abs(prediction)>=0.9 (different from diagnostic364's0.99 threshold). High-LR A LAST T/V saturation is0.649770/0.605263 versus low-LR0.460829/0.500000. High-LR B is0.115207/0.223684 versus low-LR0.396313/0.473684. All recorded predictions/metrics and exported FP32 parameters passed the actual owning finite checks; no post-fit scoring campaign was run.

## Authority, timing, cleanup and limits

Original A PASS327fc11a/12734B finalized2026-10-11T23:37:33.757924Z; original B PASS5dd7a6f6/12735B finalized23:41:33.037267Z. Both normal sole finalizations report cleanuptrue/nullprimary/secondary[]/remaining[] and remove INCOMPLETE last. The manifests and exact output inventories remain authoritative. Late background notifications must not duplicate collection, finalization or costs.

A original command wall2.921330839046277s; B2.8646435249829665s; pair5.7859743640292435s counted once. Controller A4.047317415010184s/B5.2838677890831605s are separate scopes and are not added. Render original command wall0.9263629310298711s is separately counted once; nested trainer/export/selector/cleanup/admin costs are not added and these are not universal rate guarantees.

A source/cache/model collector STOP23:38:53.642242Z; B23:42:09.938671Z; saved-curve render readerSTOP23:48:54.880379Z/canonical release23:48:54.881036Z. Direct children reaped, recorded descendants and handles cleaned, owned readers/children/jobs/TMP remaining[]; returned mask/persist completion remains distinct from persisted pending/attempted process records. Exact trainer child UTC START/STOP, continuous family peaks and whole-work fees remain UNKNOWN. Render TMP was removed after stopped custody.

Current genuine nativeBuild ef4 / image39288 / full38+generator47 supports current source correspondence; pinned training3.14 is an ordered admitted input, while immutable Build Python3.11 remains build tooling. The fit does not execute native code. Old converter aeec/d5 and migration7a682 remain cache-publication history. Actual framework/cache/warmstart scopes were reused without replay or manufacture of native parity or strength qualification.

Fresh canonical nonblocking leases, current source/model/cache/ordered inputs/library references, physical RAM/FS, distinct CPU2 worker/4 guardian, thread1/GPU0 and2GiB family within3GiB upper were checked at each fit. Render used the installed plotting environment, saved scalar observations only, the same finite guards and <=8MiB PDF cap. Exact source/input refs matched after; no dependency install, model copy, source mirror or payload retirement occurred.

Only two related V families, opened V selection, shared corpus/common initial weights and deterministic seeds limit generalization. The fixed comparison provides no universal LR optimality, convergence, causal strength, legal-move result, population inference or default adoption. Existing323 pause/seals/fullN and all prior failures/partial models/raw/masks/floors remain unchanged.

Current author artifacts are frozen for Root metadata/result verification; Main findings/design/plan/Git are owned by Root. Issue366 awaits that acceptance before owner closure.
