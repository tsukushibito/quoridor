# Distance-input diagnostic364

Distance inputs produced substantial head responses on this fixed saved corpus. The results do not support a blanket claim that these inputs have little effective influence. Tanh saturation often attenuated those responses, especially for the excluded rows. This experiment did not perturb board features, so it cannot compare distance importance against every other feature.

All three immutable snapshots were evaluated on the original341 rows:217 eligible train,76 eligible validation,48 excluded descriptive rows. Each received a baseline and independent own/opponent +/-1 integer-step interventions; all remained within0..80. Exactly5115 row-forwards were used, with no warmup, omitted state or additional model call. FT inputs, side, model parameters and frozen normalization stayed unchanged.

Magnitudes below are medians and p90 of absolute deltas, with full minimum/maximum ranges. Head means pre-tanh scalar; value means final tanh output. Each row is weighted equally. Excluded rows are descriptive, without target relabeling.

| Model          | Scope      | Change           | Head median / p90 / range              | Value median / p90 / range       |
| -------------- | ---------- | ---------------- | -------------------------------------- | -------------------------------- |
| INITIAL_BEST43 | eligible_T | own_minus_1      | 0.49111 / 7.66618 / 0–8.01475          | 0.0429574 / 0.415002 / 0–1.99787 |
| INITIAL_BEST43 | eligible_T | own_plus_1       | 0.512289 / 7.41604 / 0–8.10794         | 0.0571069 / 0.444373 / 0–1.99723 |
| INITIAL_BEST43 | eligible_T | opponent_minus_1 | 0.50885 / 7.29501 / 0–7.83473          | 0.0589901 / 0.425837 / 0–1.99705 |
| INITIAL_BEST43 | eligible_T | opponent_plus_1  | 0.522459 / 7.47958 / 0–7.70665         | 0.0502898 / 0.434082 / 0–1.99747 |
| INITIAL_BEST43 | eligible_V | own_minus_1      | 0.766281 / 7.75234 / 0.0543468–8.04265 | 0.0329973 / 0.540605 / 0–1.20018 |
| INITIAL_BEST43 | eligible_V | own_plus_1       | 0.755689 / 7.65899 / 0.0543469–8.03397 | 0.0769126 / 0.572773 / 0–1.59142 |
| INITIAL_BEST43 | eligible_V | opponent_minus_1 | 0.742012 / 7.51832 / 0.0573078–7.68022 | 0.076915 / 0.611445 / 0–1.41181  |
| INITIAL_BEST43 | eligible_V | opponent_plus_1  | 0.774381 / 7.57839 / 0.0591559–7.68022 | 0.0367689 / 0.541506 / 0–1.19117 |
| INITIAL_BEST43 | excluded   | own_minus_1      | 7.52479 / 8.04562 / 0.864668–8.27517   | 0 / 0.000540054 / 0–1.99844      |
| INITIAL_BEST43 | excluded   | own_plus_1       | 7.36523 / 8.12805 / 0.801619–8.29028   | 0 / 0.0010444 / 0–1.99894        |
| INITIAL_BEST43 | excluded   | opponent_minus_1 | 7.17013 / 7.80718 / 0.764436–7.98459   | 0 / 0.000682873 / 0–1.99851      |
| INITIAL_BEST43 | excluded   | opponent_plus_1  | 7.25464 / 7.76412 / 0.764435–7.94721   | 0 / 0.000486648 / 0–1.99798      |
| A200           | eligible_T | own_minus_1      | 0.495667 / 7.64723 / 0–8.0572          | 0.0431617 / 0.328316 / 0–1.99561 |
| A200           | eligible_T | own_plus_1       | 0.477883 / 7.36504 / 0–8.07324         | 0.0570245 / 0.39508 / 0–1.99846  |
| A200           | eligible_T | opponent_minus_1 | 0.487328 / 7.23494 / 0–7.76604         | 0.0639064 / 0.391021 / 0–1.99804 |
| A200           | eligible_T | opponent_plus_1  | 0.47969 / 7.42838 / 0–7.66002          | 0.0507849 / 0.361301 / 0–1.99452 |
| A200           | eligible_V | own_minus_1      | 0.72748 / 7.72473 / 0.0456999–8.01469  | 0.0365466 / 0.527849 / 0–1.58194 |
| A200           | eligible_V | own_plus_1       | 0.714514 / 7.6162 / 0.0457–7.99904     | 0.0861582 / 0.529911 / 0–1.69937 |
| A200           | eligible_V | opponent_minus_1 | 0.7064 / 7.48844 / 0.0492584–7.64786   | 0.0864304 / 0.527688 / 0–1.57757 |
| A200           | eligible_V | opponent_plus_1  | 0.735199 / 7.56103 / 0.0492585–7.64787 | 0.0448956 / 0.539743 / 0–1.575   |
| A200           | excluded   | own_minus_1      | 7.47523 / 8.0299 / 0.845814–8.23195    | 0 / 0.000357199 / 0–1.99823      |
| A200           | excluded   | own_plus_1       | 7.33534 / 8.08187 / 0.791139–8.28804   | 0 / 0.001021 / 0–1.99872         |
| A200           | excluded   | opponent_minus_1 | 7.15114 / 7.76002 / 0.741061–7.95512   | 0 / 0.000598329 / 0–1.99765      |
| A200           | excluded   | opponent_plus_1  | 7.21526 / 7.74784 / 0.741062–7.91725   | 0 / 0.000287277 / 0–1.99764      |
| B200           | eligible_T | own_minus_1      | 0.399438 / 7.35419 / 0–7.69475         | 0.0603435 / 0.458345 / 0–1.96216 |
| B200           | eligible_T | own_plus_1       | 0.394193 / 7.10857 / 0–7.76654         | 0.0783302 / 0.389827 / 0–1.22394 |
| B200           | eligible_T | opponent_minus_1 | 0.408028 / 7.17396 / 0–7.65698         | 0.0805815 / 0.395593 / 0–1.22394 |
| B200           | eligible_T | opponent_plus_1  | 0.426585 / 7.25772 / 0–7.5454          | 0.0674648 / 0.4436 / 0–1.96567   |
| B200           | eligible_V | own_minus_1      | 0.644076 / 7.4257 / 0.0440907–7.70789  | 0.052991 / 0.506161 / 0–1.29147  |
| B200           | eligible_V | own_plus_1       | 0.624403 / 7.32269 / 0.0440907–7.66365 | 0.0822214 / 0.433537 / 0–1.98735 |
| B200           | eligible_V | opponent_minus_1 | 0.616143 / 7.34264 / 0.0474706–7.51445 | 0.081533 / 0.478905 / 0–1.98517  |
| B200           | eligible_V | opponent_plus_1  | 0.648617 / 7.37825 / 0.0479422–7.51445 | 0.0662615 / 0.537123 / 0–1.30843 |
| B200           | excluded   | own_minus_1      | 7.20161 / 7.73089 / 0.738744–7.9087    | 0 / 0.474598 / 0–1.71539         |
| B200           | excluded   | own_plus_1       | 7.08395 / 7.76215 / 0.738743–7.91927   | 0 / 0.123556 / 0–1.63072         |
| B200           | excluded   | opponent_minus_1 | 7.03421 / 7.61017 / 0.668003–7.77976   | 0 / 0.0968817 / 0–1.63072        |
| B200           | excluded   | opponent_plus_1  | 7.12544 / 7.5769 / 0.668004–7.75969    | 0 / 0.474598 / 0–1.7064          |

Exact-zero and <=1e-6 fractions, followed by heuristic consistent/reversed fractions. The expected sign is positive for own-shorter/opponent-longer and negative for the opposite changes. Ties remain separate; no universal monotonicity is presumed and reversals would not establish a bug. All measured reversed fractions were zero for this corpus.

| Model          | Scope      | Change           | Head zero / small / consistent / reversed | Value zero / small / consistent / reversed |
| -------------- | ---------- | ---------------- | ----------------------------------------- | ------------------------------------------ |
| INITIAL_BEST43 | eligible_T | own_minus_1      | 2.765% / 2.765% / 97.235% / 0.000%        | 15.207% / 18.433% / 84.793% / 0.000%       |
| INITIAL_BEST43 | eligible_T | own_plus_1       | 3.687% / 3.687% / 96.313% / 0.000%        | 14.747% / 17.972% / 85.253% / 0.000%       |
| INITIAL_BEST43 | eligible_T | opponent_minus_1 | 2.765% / 2.765% / 97.235% / 0.000%        | 14.747% / 17.972% / 85.253% / 0.000%       |
| INITIAL_BEST43 | eligible_T | opponent_plus_1  | 2.765% / 2.765% / 97.235% / 0.000%        | 14.286% / 17.972% / 85.714% / 0.000%       |
| INITIAL_BEST43 | eligible_V | own_minus_1      | 0.000% / 0.000% / 100.000% / 0.000%       | 11.842% / 22.368% / 88.158% / 0.000%       |
| INITIAL_BEST43 | eligible_V | own_plus_1       | 0.000% / 0.000% / 100.000% / 0.000%       | 19.737% / 22.368% / 80.263% / 0.000%       |
| INITIAL_BEST43 | eligible_V | opponent_minus_1 | 0.000% / 0.000% / 100.000% / 0.000%       | 19.737% / 22.368% / 80.263% / 0.000%       |
| INITIAL_BEST43 | eligible_V | opponent_plus_1  | 0.000% / 0.000% / 100.000% / 0.000%       | 11.842% / 22.368% / 88.158% / 0.000%       |
| INITIAL_BEST43 | excluded   | own_minus_1      | 0.000% / 0.000% / 100.000% / 0.000%       | 70.833% / 79.167% / 29.167% / 0.000%       |
| INITIAL_BEST43 | excluded   | own_plus_1       | 0.000% / 0.000% / 100.000% / 0.000%       | 72.917% / 77.083% / 27.083% / 0.000%       |
| INITIAL_BEST43 | excluded   | opponent_minus_1 | 0.000% / 0.000% / 100.000% / 0.000%       | 72.917% / 79.167% / 27.083% / 0.000%       |
| INITIAL_BEST43 | excluded   | opponent_plus_1  | 0.000% / 0.000% / 100.000% / 0.000%       | 70.833% / 77.083% / 29.167% / 0.000%       |
| A200           | eligible_T | own_minus_1      | 3.687% / 3.687% / 96.313% / 0.000%        | 17.051% / 19.355% / 82.949% / 0.000%       |
| A200           | eligible_T | own_plus_1       | 3.687% / 3.687% / 96.313% / 0.000%        | 15.207% / 18.894% / 84.793% / 0.000%       |
| A200           | eligible_T | opponent_minus_1 | 3.687% / 3.687% / 96.313% / 0.000%        | 16.129% / 19.816% / 83.871% / 0.000%       |
| A200           | eligible_T | opponent_plus_1  | 3.226% / 3.226% / 96.774% / 0.000%        | 15.207% / 17.972% / 84.793% / 0.000%       |
| A200           | eligible_V | own_minus_1      | 0.000% / 0.000% / 100.000% / 0.000%       | 11.842% / 22.368% / 88.158% / 0.000%       |
| A200           | eligible_V | own_plus_1       | 0.000% / 0.000% / 100.000% / 0.000%       | 14.474% / 22.368% / 85.526% / 0.000%       |
| A200           | eligible_V | opponent_minus_1 | 0.000% / 0.000% / 100.000% / 0.000%       | 14.474% / 22.368% / 85.526% / 0.000%       |
| A200           | eligible_V | opponent_plus_1  | 0.000% / 0.000% / 100.000% / 0.000%       | 11.842% / 22.368% / 88.158% / 0.000%       |
| A200           | excluded   | own_minus_1      | 0.000% / 0.000% / 100.000% / 0.000%       | 68.750% / 77.083% / 31.250% / 0.000%       |
| A200           | excluded   | own_plus_1       | 0.000% / 0.000% / 100.000% / 0.000%       | 72.917% / 75.000% / 27.083% / 0.000%       |
| A200           | excluded   | opponent_minus_1 | 0.000% / 0.000% / 100.000% / 0.000%       | 72.917% / 77.083% / 27.083% / 0.000%       |
| A200           | excluded   | opponent_plus_1  | 0.000% / 0.000% / 100.000% / 0.000%       | 68.750% / 77.083% / 31.250% / 0.000%       |
| B200           | eligible_T | own_minus_1      | 4.608% / 4.608% / 95.392% / 0.000%        | 13.825% / 17.512% / 86.175% / 0.000%       |
| B200           | eligible_T | own_plus_1       | 4.147% / 4.147% / 95.853% / 0.000%        | 13.825% / 16.129% / 86.175% / 0.000%       |
| B200           | eligible_T | opponent_minus_1 | 4.147% / 4.147% / 95.853% / 0.000%        | 13.825% / 17.512% / 86.175% / 0.000%       |
| B200           | eligible_T | opponent_plus_1  | 4.147% / 4.147% / 95.853% / 0.000%        | 12.442% / 15.668% / 87.558% / 0.000%       |
| B200           | eligible_V | own_minus_1      | 0.000% / 0.000% / 100.000% / 0.000%       | 7.895% / 13.158% / 92.105% / 0.000%        |
| B200           | eligible_V | own_plus_1       | 0.000% / 0.000% / 100.000% / 0.000%       | 9.211% / 15.789% / 90.789% / 0.000%        |
| B200           | eligible_V | opponent_minus_1 | 0.000% / 0.000% / 100.000% / 0.000%       | 9.211% / 15.789% / 90.789% / 0.000%        |
| B200           | eligible_V | opponent_plus_1  | 0.000% / 0.000% / 100.000% / 0.000%       | 7.895% / 13.158% / 92.105% / 0.000%        |
| B200           | excluded   | own_minus_1      | 0.000% / 0.000% / 100.000% / 0.000%       | 66.667% / 75.000% / 33.333% / 0.000%       |
| B200           | excluded   | own_plus_1       | 0.000% / 0.000% / 100.000% / 0.000%       | 60.417% / 68.750% / 39.583% / 0.000%       |
| B200           | excluded   | opponent_minus_1 | 0.000% / 0.000% / 100.000% / 0.000%       | 60.417% / 72.917% / 39.583% / 0.000%       |
| B200           | excluded   | opponent_plus_1  | 0.000% / 0.000% / 100.000% / 0.000%       | 64.583% / 72.917% / 35.417% / 0.000%       |

Saturation is measured at abs(baseline value)>=0.99. Median attenuation ratios compare abs(value delta)/abs(head delta) only when the head delta is nonzero. A finite intervention can leave saturation or cross the output range, so saturation does not guarantee a small value change in every row.

| Model          | Scope      | Saturated / rows | Median attenuation: saturated range across4 changes | Median attenuation: not saturated range across4 changes |
| -------------- | ---------- | ---------------- | --------------------------------------------------- | ------------------------------------------------------- |
| INITIAL_BEST43 | eligible_T | 84 / 217         | 1.08225e-05–4.10761e-05                             | 0.706935–0.724872                                       |
| INITIAL_BEST43 | eligible_V | 33 / 76          | 1.48077e-07–4.55934e-07                             | 0.55781–0.711999                                        |
| INITIAL_BEST43 | excluded   | 48 / 48          | 0–0                                                 | no rows                                                 |
| A200           | eligible_T | 86 / 217         | 1.37797e-05–3.80427e-05                             | 0.725851–0.77915                                        |
| A200           | eligible_V | 32 / 76          | 3.10557e-07–5.55787e-07                             | 0.601592–0.724944                                       |
| A200           | excluded   | 48 / 48          | 0–0                                                 | no rows                                                 |
| B200           | eligible_T | 71 / 217         | 2.02904e-06–9.91989e-06                             | 0.823738–0.845853                                       |
| B200           | eligible_V | 29 / 76          | 1.23308e-06–2.39929e-06                             | 0.614178–0.781337                                       |
| B200           | excluded   | 45 / 48          | 0–0                                                 | 0.0910829–0.165326                                      |

INITIAL eligible-train median head deltas were0.491–0.522 and final-value deltas0.0430–0.0590. A200 retained comparable head response; B200 had eligible-train medians0.394–0.427. Eligible-validation median value deltas spanned0.0330–0.0864 across snapshots/changes. The original and A200 excluded48 rows were all saturated: median head changes about7.15–7.52 often yielded median final changes exactly0. B200 saturated45/48 excluded rows; large finite changes can still escape saturation.

Baseline rowwise saved predictions are absent from accepted362 output inventory. Available full train/validation MSE on both teachers agreed within1e-6 (largest observed aggregate difference3.3095828644302827e-7). This is aggregate correspondence, not a fabricated per-row counterpart. The diagnostic read only seven binary files and the compact manifest; detailed source/history reads were0. Parameter/input identities and same-forward tanh bit equality passed within the original execution. The metadata collector independently verified raw FP32 fields, distance transformations, census and every reported delta statistic without NumPy/Torch/model imports.

Original controller START2026-10-11T22:45:31.852330+00:00 STOP2026-10-11T22:45:35.147889+00:00, whole3.2960647749714553s. Original numerical child command wall2.7235995420487598s is nested and is not added to the controller whole. First model-forward START2026-10-11T22:45:33.784590+00:00; computation-finished2026-10-11T22:45:34.592846+00:00 is not process STOP. Exact child process UTC STOP remains UNKNOWN. Guardian source/data/model reader STOP2026-10-11T22:45:34.971646+00:00; metadata collector reader STOP2026-10-11T22:56:41.409850+00:00. Directwait/reap, process and handle cleanup passed; workers freshly absent and TMP empty.

Sampled family RSS plus64MiB controller maximum827916288B; child ru_maxrss581300KiB. Continuous family peak UNKNOWN. Full child capture223B; outer capture96B. Returned signal-mask restoration/final-record persistence completed; persisted process receipt still records pending/attempted. These remain distinct. Two source-preparation syntax/lint refusals are retained with UNKNOWN exact fees and0 scientific forwards.

The interventions may be inconsistent with board geometry. Results describe sensitivity on eight related saved families, not legal alternatives, causal defeat explanation, relative importance against unperturbed board features, general population monotonicity, strength, convergence or default policy. D6 targets differ from static distance. No model, data, teacher or scale was changed.
