# 429 新Sigmaデータの生成・変換・census

原1280 requestを一度だけ処理し、入力受理1204・欠測76を保持した。実入場/返却1204局は1190 GOALと14真正threefold draw、UNKNOWN0。通常MCTS converterは元のnative config・schedule・partition・完全prefix/STM/終端・64完成simulationを検査して62186適格行を保存し、通常TerminalCorpus readerも受理した。追加fit・評価forward・Search・arenaは実施していない。

| cohort                | request | 入場 | 欠測 | GOAL / draw | 適格T / V行  | model入力のdistinct数 |
| --------------------- | ------: | ---: | ---: | ----------- | ------------ | --------------------: |
| quantity 4/8/12/16ply |    1024 | 1018 |    6 | 1008 / 10   | 40614 / 9923 |                 50430 |
| early 2ply            |     256 |  186 |   70 | 182 / 4     | 9297 / 2352  |                 11613 |

prefix seed42920261017・split42920261018、長さ[4,8,12,16,2]の固定循環。quantity部分列は従来4長さの順序を保ち、request/global ordinalを実scheduleで固定した。元のrules-only32候補attempt、LR/延長/endpointの正本分類、既知355/421/423/426の6book・2576member除外を使用。結果による補充・再選択・旧423の再実行は0。

全1176 canonical families。quantity1016とearly186には共有26familyがある。joint partitionが共有familyのT/Vを統一し、両cohortや二色等を独立標本としない。正本raw/nativeのfamily・game IDは維持した。IDの正体はsource config/schedule SHA＋ordinal、compact rowindexであり、旧corpusの同名game-nとaliasしない。旧423の原203T53V/最終204T52VとID18の対応は不変。未知の公開/sealed provenanceはUNKNOWN。

在庫18..20の適格行はquantity T6/V0、early T907/V223。各集合内でこの高在庫行はすべてdistinct model入力だった。全新cacheの正本model_keys（geometry＋FP32 distance28B）では62043 distinct、重複超過143行、同一入力の異なるzは0、T/Vを跨ぐキー0、cohortを跨ぐキー0。model入力一致はhistory資格ではなく、prefix-family共有と同一入力も別の概念である。旧423とのmodel入力重複はBでは再検査せずUNKNOWN。

既存のT-only game×stock4層（16..20/8..15/1..7/0、各最大8、chronological等間隔）をそのまま適用した参考base viewはquantity14959＋early3863＝18822行。V12275行は全適格を保持。これはC担当のnested/global-distinct/matched viewではなく、その最終選択や不足は未確定。結果やzで行を選び直していない。raw q/rootmeanは解析用の保存値であり、教師は実outcome zSTMのみ。

160区間は各8 request・60000 logical Sigma rowsの独立上限、実受理数にgamesを合わせた単一直列producer。64完成simulations/move、200totalply、greedy、同d790 Sigma/CPU FP32 ORT/intra1/inter1/batch1。実logical＝physical＝executed3513011、warm/failed0。160×60000＝9600000の未使用分6086989は他区間/仕事へ移さない。元の必要overhead専用400000も追加科学の許可ではなく、今回の変換/censusの追加forwardは0。

原generation job62e05483のouter15676.074928531秒を一度保存。conversion native43.255940147秒は別段で、区間native/guard時計をouterへ二重加算しない。全作業費・LLM/admin費・continuous family RSS peakはUNKNOWN。CPU2/G6/family4GiB/GPU0/hostreserve4GiB、source/compact reader CPU8/G6/family1GiBで既存guardianを使用。G6は管理共有であり、fair-clock/global quietを主張しない。Main lifetime leaseはnative中に保持せず、必要な短いcaller intakeだけを使用した。

Root support-applicationのwhole128MiBは一度だけ適用済み。旧423の名指しcompressed Arrow/metadataとcompactのstatから、生成・変換・serial重複・TMP/controlの新positive83558400Bを予測した。これは完了保証や新予約ではなく、既存whole allocation guardが今回の新rootsを実制御した。モデル/公開T/Vのコピー、旧holding/targetの再課金、減少refundは0。最終directed使用はusage.jsonに保存する。

元の準備metadata path/shape失敗、collectorのeligible_rowsを辞書合計にする修復、sourceファイル名の誤指定、unused balanceのfield名訂正は原capture/erratumに保持。native生成・converterの再実行は0。元FAILED/NULL対disk/旧RAW/feesと旧323/342等のpause、models/weights/seals/defaultは不変。

原generation sequence STOP05:02:47.503425Z、outer STOP05:02:47.611162Z。変換STOP05:10:17.038803Z、compact reader STOP05:12:30.503212Z後にdirectwait/reap・fresh identity absence・handles/TMP終了を確認した。完全FileRefs/結果/停止はresult.json、result-STOP.json、completion.jsonから辿れる。保存データの量・初期stock被覆の有限観測であり、teacher改善・学習効果・棋力・一般化やモデル昇格の結論ではない。
