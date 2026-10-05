# 165 Native Sigma baseline の有限診断

2026-10-03、experiment、`quoridor-4lc.165`。契約d0136c1/親版11、受領04:37:21.307017UTC、処理06:27:21・提出06:42:21の早側を維持。原科学は05:25:07.645325に終了。原科学停止と後続NN0 control修復停止は別正本に保存した。受入れはcoordinator、親目標未達。

忠実Rust nativeと固定Sigma-Webのnative-hosted JSを、同ONNX・CPU ORT 1.30.0・各session intra/inter1・sequential・CPU2単logicalで比較した。固定Web751186、ONNX d790dac…08d、Rust native binary166dd0c…96f8。Sigma C++比較ではない。原151/Wasm/provider1.21、モデル、共有crate、92は編集していない。必要7未Git依存差分を含む私有9libraryはdependency-bindingへ結び、Cargo.lock/compiler/flagsを保存した。外部cached Cargo/Python環境をGitだけで再構成可能とは主張しない。

## 機構結果と原16局

StageA原版a09279c、raw dee3d3b5…3286。固定5入力×両engine K32、320CP・320手NN、startup2別。features648/NN137 f32bits、履歴、全CPのAction/path/訪問/ledgerに離散差・ledger差なし。rootN32/edge31、true mean、元合法順、P2変換、rootNN loop外を維持した。最初prior差2.1684e−19、最大prior差1.3878e−17、最大score差1.1102e−16。丸めによる救済なし。同Kは同CPU・棋力証明ではない。旧Wasmとの根NNは最大3.5763e−6の数値差でtol範囲内だが、別providerの離散軌跡一致を証明しない。

StageB原版19275b3、metadata修正e6b42a3/f63e8b3。AI未読master91031/SHA domain/xorshift32、prefix12/13/24/25各2、pawn/wall class内元合法順一様、事前条件の最初適合を採用。15proposalで8開始局面、固定色順の16局を完走し、全16 GOAL、**6勝0分10敗、平均.375**。pair Xiは `[0,.5,.5,0,.5,.5,1,0]`、同側winnerはpair2/3/5/6。未知0、全16の運用・純terminal品質識別区間はいずれも[.375,.375]（信頼区間ではない）。新局面のBFS条件は均衡・代表性・IIDを保証せず、8pairを16独立局面に換算しない。NI/Sigma同等・普遍劣性は未認定。

## 原clock/control不足と別版修復

原898手で保存publicは全500ms以内、旧世代CP不採用、次t0は前quiescence観測後。しかし旧arenaのadmit stampは合法検査/clone/cache代入**前**だった。最大401.999397msであり実採用完了時刻は欠測。旧402欄を時計成功・違反へ付替えない。pair1のactual IPC quiescent receiptも欠測で、gate観測欄のerratumを保持する。

また参照terminal-only loopがIPC stopを読めず、4手で約3–10.5秒のcleanupを発生した。reference cleanup合計35.927621秒、reference lateCP866733（候補80を含む全late866813）は不採用。deadline後のterminal backup数を有効探索量としない。原勝敗・採用手・raw・science-stopを保持し成功測定を再実行していない。これらにより原samewall時計・正式公平性は未成立、`formal_ready=false`。

新private adapter a78ea8336edc84c9716fee8972c86d94200941b6は両engineの各完成CP後に共通setImmediate event drainを入れ、IPC取消を処理する。browser setTimeoutの人工遅延は戻していない。mainは同期handler内でvalidate→clone→tentative cache代入→単controller monotonic完了stamp→402超過/unknown rollbackを行う。途中await/公開なし、前certified cacheを保持。policy/PUCT/f64/合法順/NN/model変更0。

`native165-control-repair-r1`は新ORT NN0/startup0/game0、2.973745秒、CPU2単1。保存320NN tapeによる10K32は各engineの原CP/path/訪問/ledgerとexact一致。人工draw199 terminal-only実参照processは44.870msで停止、stop→quiescence8.983ms、人工root評価1。取消後pipe中のCP63は不採用。pending人工NN0取消も双方discard1/activeNN0/handle0。実commit分岐で402直前/丁度/直後、unknown/backward、clone費跨ぎ、非法/世代/公開後/clone例外を確認した。**実ORT取消と新adapter samewall量は未再認証**。NN0結果を新品質・原clockの救済にしない。

## 実費と射程

品質job8本431.553877秒、対局部分405.653584秒、898手（候補448/参照450）、手NN40378、startup16別。対局部分.0394425局/秒（2.37局/分）、品質job全体.0370753局/秒（2.22局/分）。これは旧adapter限定の実費で、Wasm並列倍率や将来正式速度へ外挿しない。

| 保存計測 | 候補 | 参照 |
| --- | ---: | ---: |
| NN開始 / 採用cache時点NN | 18471 / 18048 | 21907 / 21415 |
| 保存cache K 中央値 / 平均 | 40 / 111.288 | 48 / 143.393 |
| firstCP配送平均ms | 44.627 | 17.101 |
| 初回API平均ms | 5.947 | 6.381 |
| steady API手内平均の平均ms | 5.920 | 5.987 |
| API全手合計秒 | 104.833 | 126.039 |
| NN pipe往復全手合計秒 | 137.258 | 166.313 |
| 原因側public後cleanup秒 | .194 | 35.928 |
| session初期化平均ms | 27.819 | 29.800 |
| startup warm往復平均ms | 7.022 | 6.235 |

APIはpipe区間内に含まれ、足して総費にしない。輸送差にはJSON/queue/OS等が混在する。保存cache量は原採用完了欠測の制約付き。特徴生成・合法生成・history replay単独費、全kernelCPU帰属、exact CP store時刻はunknown。両engineのfull prefix輸送と合法検査を含む共通時計、候補のRust raw確認等実装費の差を残し、性能量差から単因子棋力因果を導かない。

build14.257875秒（Cargo10.073988）、StageA5.592912秒、品質431.553877秒、heavy計451.404664秒/上限2100。管理NN0登録job13.238108秒（修復2.973745含む、失敗3attempt保持）/上限120。全team費・未包絡の編集/短read費はunknownで、job計測を全作業CPU保証にしない。最大owned+guardian current RSS950575104bytes、各科学guard内。全期瞬間peak保証ではない。

小exportはopening16行/8lineage group、14train/2validation。π136は採用edge訪問分布、rootmean・rootNN f32bits・game z・leafNN欠測・視点/予算/履歴を分離。160語彙を再利用したvariable-K/game-z diagnostic extensionで、shared schema未変更。16有効行/品質job秒=.0370753行/秒。一局opening一行のみ、全手teacher・学習・独立holdoutではない。export初回split例外と修正版のcommandを保持した。

## 停止・保存・次判断

原science-stop SHA `9becd64e4bfac3e3d145765a7586b0e3376ac49aaae87d5b6ebdb7d49aac671c`、別control-repair-stop SHA `b5d9b87d15cd93c4da198a3ee518c41de727acc867806857c653549160efb7c8`。各engine/Model EOF・searchzero・main timer・observer終端、outer ownedwait/remaining/unknown、登録identity現在不在を別に保存。失敗oracle-r1強制停止、他exit1、成功exit0を混同せず、自然/全期間/全host停止保証へ格上げない。source停止後のpack/集計helpersは科学源を変更しない。

全attemptのcommand/開始終了/版/log/入力/結果/監視をraw archiveとmanifestへ保存し、圧縮から全member hashのreadbackと少数実展開、私有sourceのGit bytes確認を行う。モデルと旧証拠は共有参照・保持し削除しない。復元手順はmanifest、source/model/provider/7依存差はbinding、費用はresults.json。成功科学行の再実行は今回許可していない。

**次案は最大1：修復adapterを別事前登録・配分の有限realORT取消/同時間診断で確認し、native評価・教師生成基準へ進む。** 実装追加は小さいIPC/clock診断に限定でき、既定source/tapeは成立している一方、原2.22局/分にはterminal cleanup費が混在するため新品質費を測る必要がある。一般棋力・NIを主張するには新独立native計画が別途必要。輸送最適化/GPU/学習/NNUEの自動拡大はしない。
