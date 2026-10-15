# 407：近似の発動条件と評価方法の独立設定（私有source準備）

406の固定source・速度96 calls・入力・imageには変更していない。基準はimmutable Git `7bf4e3a4a3497158e9458a22b8814e1069e52e5b`。本成果は私有patchと未実行テスト定義であり、Main採用・native成立・性能や棋力の結果ではない。Mainへの統合と必要softwareは406の実速度検証STOP後、407の数値比較は未承認である。

## 設定と実効状態

既存 `zero_stock_approx_min_root_walls` の意味はそのまま。追加する `zero_stock_approx_method` は `race` または `fixed_d` の文字列とし、省略時は `race`。明示null、bool、数値、未知名は拒否する。閾値のnull/OFFと方法名のnullは別契約である。

AIの小さな `ZeroStockApproxMethod::{Race, FixedD}` が名前・method IDの正本になる。`SearchSession::set_zero_stock_approx_method` は発動を許可しない。既存setterによる閾値設定と、各Searchのrootによる一度の許可解決が別に必要である。自由関数Search・製品・生成・arenaの既定はOFFのまま。

実効OFFで方法だけ変更してもnamespace・TT・historyを変更しない。実効ONで方法を変更した場合だけ、末尾method IDの交換とTT/historyのclearを一度行う。同じ方法の再設定ではclearしない。root stock数や閾値そのものはnamespaceに加えない。LMRの切替でも現在の近似methodを末尾に保ち、reset後は未解決OFFへ戻し要求設定だけ保持する。次のSearchにはbooleanと方法を値で渡し、iterative deepening中に変化させない。

raceは元の `zero-stock406-wall-distance-stm-tie-win-v1` を継続使用。fixed Dは `zero-stock407-fixed-D-a0-b8-tanh-v1`。同じ閾値でも評価方法が違うTT値は共有しない。

## 距離と数学の所有

406の実距離取得は不変である。実Float accumulatorの既存wall-key照合cacheを、pooled child、parentの順で参照し、実keyに合わなければ既存 `Position::wall_distance` を使用する。Quantized/DistanceStepをFloat扱いしない。pawn/手番が違っても同じ壁のgoal距離表を使える性質は変更しない。sentinel81、到達不能error、二距離間のcancel確認とscore-domain検査も維持する。

既存 `DistanceEvaluator` の計算部分だけをprivate `evaluate_distances(own, other)` に抽出する。通常の固定D評価も新しい近似葉も、この一つの数式所有者を呼ぶ。既存の `/80`、f64→f32、演算順、係数・finite検査、f64 tanh/Clipの本文を保持し、固定D近似の係数は既存 `new(0.0, 8.0)` のみ。新しい評価器や係数設定、距離生成、cacheを作らない。

cacheが使えれば二つの距離参照を借用し、新しいmap生成はない。使えなければ406と同じ実wall_distance計算費を払う。fixed Dの正規化とtanhはrace比較より追加の計算となる。実cache hit率・動的呼出数・BFS省略数・RSS増分・速度・棋力はUNKNOWNで、sourceから利益を主張しない。近似側からNNUE advance/headを呼ばない点は共通である。

## 結果と保護範囲

`SearchResult.stats` に方法enumを追加する。これは `zero_stock_approx_permitted` がtrueの場合だけ実効methodとして読む。OFFのselector値を近似の実行と解釈しない。測定setupは要求方法と未解決null、各callは要求名と実効ID/nullを記録し、callback/結果も同じ実効IDを出す。深さは引き続き近似葉を持つnominal depthであり、真の終局WDLや全幅minimaxの証明ではない。

`child`、`zero_stock_approx_leaf`、`enter`、`control`、`negamax`、`root_depth`、順位/PVS/LMR条件、PV境界はbyte exact。true goal/threefold優先、正child depth・双方stock0の条件、depth0の元評価、undo/parent/history/node/delta会計は406と共通のまま。別TT容量・LMR規則・static項・rule/model/default・393/398 geometryなどの変更は含まない。406の既存テストファイルも変更しない。

## 静的確認と残る検証

標準patchのfuzz0・offset0でforward/inverseを適用し、全文一致と新テストのabsence復元を確認した。Python publisherは `measurement_config` 外がbyte exact、Rustの保護関数と固定D数式本文も比較した。RustfmtとRuffによる対象限定整形、Python AST/静的lintの結果は各guarded receiptを参照する。

新AI4定義は名前/OFFとwarm、ON method切替とTT/history、固定D正本とのbit一致とNNUE非実行、depth0/cancel/error復元を扱う。runner1定義はserdeの省略/拒否と実効結果、Python NN0 1定義は方法と閾値の独立性を扱う。すべてUNBUILT/UNTYPED/UNRUN（PythonもNOT_RUN）。exact名・feature・filter・必要な既存影響境界は `verification-plan.json` に記した。既存406の成功を再演していない。

独立確認をRootが必要と判断する場合の問いは、実効OFFの方法変更がnumeric authorityを変えないこと、ONのreset/warmとLMR末尾管理、cache由来の正しい二距離を同じ固定D数学へ渡すこと、結果に要求と実効を混同しないことである。本leafからreviewerはdispatchしていない。

## 実行境界

実turn_contextはgpt-6.1-sol/high、danger-full-access、approval never、今回の送信指定cwd `/workspaces/quoridor`。writerはOWN407だけ。保存managed worktreeのcrateやOWN406は書き換えていない。必要なsourceは指定Git objectから一時的に再構成し、往復証明後に一時全文を削除してsparse patchだけを残した。恒常source mirror・Main/index/commit/sharedCargo・native/test/model/Search/Perf/gameは0。

既存CycleResources/execute/Captureを使い、workerCPU3/guardian7の実distinct physical・available affinity、family768MiB/host reserve4GiB/GPU0、各有限source command120秒、no_new_privs、取消・directwait・fullcaptureを適用した。私有immutable objectだけの準備なのでcanonical writer lease/global quietを要求していない。これは406のsoftware・review・timing成立を認定するものではない。

各returned guardianのsettled maskと、persisted receiptのpending/attemptedは別の事実として保存する。最後のfresh identity/handles/TMP/ownedと一度のOWN実使用は `source-STOP.json`。普通作業のstorage budgetはNone、global使用量は測っていない。mixed/learner全prep/pipeline・323USERPAUSE、旧RAW/FAILED/費/UNKNOWNはそのまま。
