# Independent check of existing 512 paired performance

Issue 357.1: **clear, 0 blockers, 0 ordinary findings.** Both compact targets match the accepted original summary. No new games, model calls, search, build or original 355 replay occurred.

All 128 CSV rows correspond exactly to the original family IDs and both models' two-colour scores. BEST51 has 76 wins and BEST43 has 87 across 256 games per model. The new candidate improved 42 families, tied 55 and worsened 31. The signed family score-difference histogram in percentage points is -100:3, -50:28, 0:55, +50:39, +100:3. Net gain is 11 wins; mean paired difference is11/256=0.04296875, or 4.296875 percentage points. These are paired results against fixed D, not direct BEST43-versus-BEST51 games.

| Prebound prefix length | Families | BEST51 wins | BEST43 wins | Net wins | Mean difference, percentage points |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4 | 32 | 18 | 21 | +3 | +4.6875 |
| 8 | 32 | 17 | 24 | +7 | +10.9375 |
| 12 | 32 | 18 | 19 | +1 | +1.5625 |
| 16 | 32 | 23 | 23 | 0 | 0 |

The largest observed gain is in length 8. Length 16 has no net gain. This descriptive stratification does not identify a universal feature benefit or a causal mechanism.

I independently recalculated the specified new exploratory paired percentile interval: Python random.Random(35520261010), 10000 resamples, 128 randrange family draws each, integer new-minus-old wins summed then divided by 256. Each draw preserves both models and both colours together. Ascending samples and linear percentiles at 0.0125/0.9875 give **[-0.0390625,0.125]**, a 97.5% interval, exactly matching the stopped target. No seed, estimator or selection was changed.

The point estimate and 42-versus-31 family count are modestly encouraging observations. The interval includes zero, so this check does not establish superiority. This posthoc conditional empirical illustration assumes exchangeable families and does not correct shared initial state, generator or derived-seed dependence. It cannot supply population, guaranteed familywise, direct model-ranking, causal bypass or default-adoption conclusions. It does not amend the original 355's two confirmatory model-versusD intervals or turn its descriptive contrast into a third confirmatory test.

Three inputs were hash-checked before parsing and again after calculation: result 0faa356f, CSV f27061d7 and original summary 68f75563, 2236375 bytes total, below the issued 3 MiB read bound. Original Root's earlier 2 MiB overrun and pre-execution SyntaxError remain historical; no failed-model/data inference follows. Independent bootstrap-only perf_counter time was 0.17355890094768256 seconds. Tool wall time, reading, formatting and administration are separate scopes and are not added to it. Full-phase fees and continuous peaks remain UNKNOWN.

Actual readerSTOP: **2026-10-10T22:52:10.896944+00:00**. Static helper directly returned exit 0; owned readers/children/jobs/TMP/remaining are empty. The finite canonical nonblocking lock was released on completion; no hardware reservation or current/future global-quiet qualification is claimed.

Fixed result SHA: 0faa356fb4b1d201d9331466850beb0ac38b7480cf9c898b84a2452d4be9a6fb. CSV SHA: f27061d7ef8ff4346828094b01428204b5018d44fa4e9f0e8a7973f9a1beb4d8. Accepted summary SHA: 68f75563da88301dbc74290a3f50e180622eedc51fac5836b20488d0168c903d. Exact SHA/size/mode map and counters are in checks.json. Own inclusive output ceiling 128 KiB remains within the existing Root evidence allocation; no source/Main/Git/model/data writes or resource refunds.
