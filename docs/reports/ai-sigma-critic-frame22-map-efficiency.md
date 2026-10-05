# NNUE共通whole81距離map：有限同仕事比較 / quoridor-4lc.279

両goalの全81距離をcoreの共通bitparallelで計算する候補は、独立queue oracleと有限NNUE品質検査に通り、固定4root・depth2のNNUE探索では両測定順で時間を短縮した。steady prefix別中央値の合計比は0.724421 / 0.829737。現main全経路・同時間棋力・MCTS教師生成倍率は未測定である。統括の別ownerによるreadonly source reviewはmask共有・sentinel・STM算術・cache共有を支持したが、自己検査と独立性能認定を分ける。

## 実装と比較境界

managed WT `/workspaces/quoridor/.worktree/frame21-search` の `crates/quoridor-core/src/position.rs` に `Position::wall_distance_maps() -> [[u8;81];2]` を追加した。水平/垂直壁からblocked-edge maskを一度構築し、goalごとのfrontier層をu128で展開し、各層を81個のu8へmaterializeする。不可達は81。既 `wall_distance` も同private `WallEdges` を使う。駒・jump・手番はwall-only graphの障害に含めない。

`crates/quoridor-nnue/src/features.rs` のWallMaps生成だけを共通APIへ移した。旧live queue実装は削除し、具体比較用のqueue binary/source archiveと独立test oracleへ分離した。壁不変の駒手は既Arcを共有し、壁手はmapを更新する。STM距離のf64/80→f32、sorted sparseIDs、full/delta算術、history、TT、ordering、モデルを変更していない。Sigma648距離map callerは変更0。main編集・Git/index操作0。

比較のAI/NNUE libは停止済275/277の私有scaffoldで、Owned evaluator wrapperにより275のscratch再用を有効にしていない。queueと候補は同core/AI/lib/example source、NNUE map supplierのみが異なる凍結2binaryである。normal依存では277のcfg(test) hookは実行されない。prototype AI/libをmainへmergeする根拠にしない。最終採用対象の限定path/hashと比較専用pathは `source-science-stop.json` へ束縛した。

## 品質と費の定義

独立VecDeque queueとedge判定から、両goalの全81値を検査した。raw graph457 geometry（壁単独・交差/重複・遮断・決定的乱数を含む）と180度交換、固定4合法prefixの503 child、合法make/unmake・全history/ply復帰・terminal/jump/P2を有限検査した。raw不合法geometryのgraph値一致を合法game資格と混同しない。

Scalar/Simdの1,006 child比較、3,018 native NN評価では、独立queue由来full inputと候補fullのfeatures/value bitsが一致した。full/delta差は最大1.1920929e-7、登録許容2e-6以内。親accumulator/featuresは不変だった。cache testは駒手Arc共有、壁手Arc更新、不可達Input errorを支持する。core RuleAと既NNUE実装を使う検査で、教師truth・全deep・モデル正しさの独立証明ではない。

小map測定は同489壁変更childに、旧fixed81 queueと候補をwarm1/steady3で交互実行した。候補のmask構築と両goal81値materializationを含むsteady中央値は72,975ns、queueは410,250ns、比0.177879。Arc/cache・推論は含まない。内部maskだけの排他費は未分離である。

候補のactual delta_context包摂観測は駒手28件13,564ns、壁手978件488,621ns。これはmap/IDs/FT/validation/clone等を含み、別のmap費へ足し合わせない。277の66.73%を今回whole探索の排他的律速や倍率へ読み替えない。

## 同仕事結果

旧固定モデルwidth32、4合法prefix、D/L、depth2/nodecap3000、CPU3単1、GPU0。初回queue→bitはwarm1+steady3、反転bit→queueはwarm1+steady1。全96 search row（48対）でcompleteddepth2、Action/value bits/PV/nodes/leaf NN/delta/TT/stop、全history/ply根復帰が一致した。

| 順序      | NNUE steady中央値合計比 |  D対照比 | 内部whole process比 |
| --------- | ----------------------: | -------: | ------------------: |
| queue→bit |                0.724421 | 0.958327 |            0.771508 |
| bit→queue |                0.829737 | 1.063151 |            1.050005 |

比はbit/queue。NNUEは全4rootで両順序とも短縮した。Dとwhole processは方向が揺れ、短い計測・host/order・load/coldの交絡が残る。whole processにはload/setup/探索/出力が含まれ、guardian/child spanは包摂なので加算しない。秒未満の少数caller結果からproduction job全費、全生成Rjoint、同wall完成depth、棋力を認定しない。

## 全費・失敗・停止

279科学は登録MAX3の3jobを使用し、全exit0/wait/current exact不在。native NN31,026/150,000、processed58,536/500,000、科学guardian0.783824秒/180、compile/check/lint105.244009秒/180。品質のgraph走査回数をsearch processedへ混ぜない。旧275/277のNN・費・失敗・capsは保持した。

`build-bit-r1` は旧scheduler/monitorの不一致によりprestart停止し子/NN0。controller artifact allowlistの不足は科学前に修正した。runnerに存在しないresearch featureを指定したlint入口失敗は原log/processを保持し、featureを外した同scope修復でlintを通した。保存集計のscratch snippetはfixture名を整数として扱いempty medianで失敗したが、NN/science0であり最終集計器では正しいfixture名を用いた。集計器のunused import lintも修正前失敗として保持する。通信dispatch lock・coordinator role refresh拒否は科学支持へ変換しない。初期14:10目安は実装済みだが品質実行は14:11:55となった偏差を保持する。

全手書きRustを対象限定rustfmt/check、core/NNUE/runner exampleをclippy -D warnings、PythonをRuff format/check、手書きconfig/reportをPrettierで検査した。比較凍結source/dataは再整形しない。入力checkpoint/ONNX取得・Torch/ORT新session・GPU・学習・gameは0。科学モデル読取は登録legacy manifest+candidate.f32のみで終了した。

science/input/source SHA、PID-starttick・wait/exact不在・current loaded/24hash・物理point admissionは `source-science-stop.json` と各processに保存。pointを未来や全host不在へ広げない。sourcepack/evidencepackはmember SHA/bytesをstream復元照合し、原科学logを保持する。統括だけがGit保存/限定main統合を行う。scope2MiB、旧2755+2771+本2792=8MiB、shared32MiBを既unused内に保持し、旧unknown128MiBの減額・親予約追加0。

## 採否と次判断

core共通mapとNNUE supplierを限定main採用候補として引き渡す。独立source reviewを受領した範囲と自己品質・性能証拠を分け、prototype scaffoldは比較archiveで保持する。旧live queue互換を恒常維持する提案はしない。

次最大1方向は、共通map採用後の**新NNUEモデル/幅・実caller条件での最小同仕事確認**である。今回の旧width32 caller結果を新特徴・幅へ外挿せず、必要になった時に限定測定する。今枠に新条件/測定を追加せず、教師真batchと独立学習評価の主接線を維持する。root fullhistory TTの手跨ぎ機会は277短PVで未測定のままで、今回の利益からTT改造やhistory圧縮を正当化しない。最高目標は未達である。

再現設定は `preregister.json`、実entrypointは `run_guard.py` → `run_joined.py`（task `frame22-map-efficiency-279-v1`）、集計はNN0の `summarize_saved.py`。archiveの復元経路は `archive-manifest.json` を参照する。再実行は保存入力参照であり本報告は新run許可ではない。

## 統括指定の最終統合境界

停止後の統括指示により、main候補はcore Position/WallEdges/map API、NNUE supplier/cacheと、独立wholemap oracle・rotation・legal prefix undo・terminal/jump・cache共有の正しさテストに限定する。`whole_maps.rs` 後半の `queue_control` / `whole_maps_finite_cost` は比較archiveだけに保持する。`MAP279_MODEL` / env依存の `map_regression.rs`、私有 `map_work.rs`、旧AI/lib scaffoldはmain常用経路へ移さない。generic正しさテストの279 tagを外す管理差は統括の統合版で行い、原科学source/quality bytesと区別する。本人sourceの再編集・再科学は0。

統括のmain NN0 core/tests/cache検証と追加release16MiBは独立統合作業である。旧275 shared128MiB内の保守会計は既net45,047,808 + 277予約16MiB + 279予約32MiB + 統括16MiB =112,156,672B、上限134,217,728B内。現物の減少は予約解放に使わない。この会計は将来growth保証ではなく、統括が実開始前にfresh headroomを確認する。
