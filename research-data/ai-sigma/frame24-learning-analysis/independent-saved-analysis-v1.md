# Saved learning trajectories: finite independent analysis

The saved evidence supports investigating learning-rate and exposure effects before changing the teacher, representation, or sampling method. It does not identify a unique cause of weak transfer or measure playing strength. This analysis used configurations, scalar curves, prediction bytes, exported weights, and sampling counters; it imported no model and read no opened evaluation targets.

298 and 302A have the same initial weights, corpus, row order, optimizer, learning rate, and original replacement sampler. Their nine shared checkpoint weights and full validation predictions are byte-identical. Their different observation schedules therefore expose additional points on the same saved trajectory, rather than a new training intervention. Current repaired-source equivalence still needs a separate binding before prospective reuse.

| Saved run | Minimum recorded family-equal selection MSE | Recorded step | Final family-equal selection MSE |
| --- | ---: | ---: | ---: |
| 298, LR 1e-4 | 0.585894418 | 1000 | 0.851886855 |
| 302A, LR 1e-4 | 0.584376578 | 1250 | 0.747894928 |
| 302B, LR 3e-5 | 0.574644168 | 3750 | 0.574924200 |

These are minima among recorded points. A's early minimum remains unobserved between 1000 and 1500; B's between 3500 and 4000. A's row-equal minimum occurs at step800, demonstrating that selector weighting changes the reported best point. The repeated selection corpus is exploratory, not a newly held-out evaluation.

302A and B have identical row-use histograms: 512000 sampled training rows, 14803 distinct rows, minimum5 and maximum144 uses, coefficient of variation0.5502. All4733 validation rows have recorded use0. Family counts have coefficient of variation0.0282, consistent with the family-uniform then row-uniform replacement sampler. The actual sampled sequence was not saved, so histogram equality alone does not prove sequence equality. Mean34.5876 uses per training row is equivalent exposure; it is not completion of34 epochs.

The batch objective is row MSE within each sampled batch. Its expectation follows the family-weighted sampling distribution; full training row-equal MSE weights a different population. A low individual batch loss cannot be substituted for dataset MSE. Final training saturation rises to88.6% in302A and99.6% in298 while selection error worsens;302B has26.0% final saturation and a later sampled minimum. Learning rate, exposure, regularization, selection representativeness, and target/feature limitations remain competing explanations. This evidence does not establish a domain mismatch or justify a new architecture.

The prospective fixed-condition observation plan contains exactly200 points per case and a target-blind2048-row diagnostic subset plus full4733-row selection. Its conservative forward bound is3796612 across both cases, below3900000. Full training initial/final and exact saved-source/weight/input reuse remain separately accounted. Current verbose per-group artifacts exceed the6MiB output allocation, so compact canonical recording must be qualified before a fit. No observation density or required group evidence has been silently removed.

Evidence: saved-analysis-v3.json; output-preflight-gap-v1.json in the sibling diagnosis scope. Primitive metadata-read and source-patch failures are preserved separately. Measured NN0 command wall and unmeasured read/LLM costs are distinct; missing costs remain UNKNOWN. Producer ownership of earlier datasets and this independent saved-model analysis are separate from coordinator adoption and critic evaluation.
