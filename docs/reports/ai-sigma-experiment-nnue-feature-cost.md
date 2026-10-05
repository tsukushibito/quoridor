# 156 NNUE特徴・距離の総費用診断

固定4入力・46合法root childの出力parityは成立したが、cache＋差分313の総費用は3入力で減り1入力で増えた。事前分岐に従い、一般cache拡大と今回の結果だけを根拠とするNNUE evaluator/αβ実装への移行を止め、合法生成・到達判定とcontext再生の費用を次の検討対象とする。これはJS browser診断であり、Rust/Wasm NNUE速度・棋力・最強・NIを認定しない。

契約はcoordinator Git `08f852c82fac21639e445b90e698617e55def8d7`、goal `quoridor-4lc`、本人子 `quoridor-4lc.156`。151必要停止・Git `0e13191`/handoff `f8444bd`/backupを先に完了し、ready/show goal+selfのpauseなし/本人割当後claimした。受領時計は02:20:06.755129 UTC、処理03:05:06.755129/newheavy03:00:06.755129/提出03:20:06.755129でresetしなかった。155裁定到着は入口条件にしていない。原151/149/model/shared/root文書は変更していない。

## 入力・結果前固定

151 `stageA-inputs.json` SHA `dc205f8d7e00ee52aca51845ddbca5e3085d0aebdb22c3f4ceb6fa139cd10954` とr2 reference root記録SHA `d37215cbc7914519ca24ab254c5e413d21e780389094faed537280a059c234d2` の必要4行を参照した。初期状態から合法prefixをRuleAで再生し、key/history/ply/side/648 featuresのf32 bitsを直接一致確認した。prefix13/14の元boardはplyだけだったため、今回の実replay後pawns/remaining/side/key/history/featurebitsを `fixed-actions.json` に保存した。欠測を直接board書換えや代替入力で補っていない。

RuleA必要本文のみ自域へ同bytesコピー。game.js SHA `dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5`、context.js SHA `66be1d634dadbdb8bf3cc1e8cb4bc06ebbc549c3813c46176bb3097b98a52b3c`。actual served hashも保存。原合法順の先頭pawn最大8、wall最大8を入力ごとに固定し、実数11/11/12/12、計46 child。空class補充・後続状態からの補充はない。各variant correctness1/warm1/64repeatを1回、順AB/BA/AB/BA。科学成功行の再測定・交換は0。

結果前sourceは `c08c5fa`、反復除外fixture追加 `2975af7`、未開始修復 `45eea73`、科学r3 `d6a4a20`。原policy/model/NNは使用せず、NN/モデル/探索Worker/対局/build/download/学習は全0。

## 実装の比較範囲

両者は固定player・固定座標の313binary（pawn162、壁anchor128、壁remaining22、turn1）と後段2距離scalarを返す。Aは各評価stateで2goal/81cellのuncached BFSとfull313。Bは壁segments＋geometry9＋RuleA版＋goal0/8をkeyにした上限32配置×2mapと313差分更新。map数値payload最大容量20,736byte、科学実保持は9pair/5,832byte、JS object overheadは未測定。scientific warm以降は同有限9壁配置に対するhitであり、一般探索の壁churnを代表しない。

両variantで同じRuleA legal生成・到達判定・`State.next`/合法prefix再生・履歴・terminal・fullTT/context key構築を行う。原RuleA自体もpawnで距離mapを共有し、壁で再計算する。その原処理を両者に残した上で、追加encoding距離map取得のuncached/cacheを比較した。B cacheを合法壁生成へ注入してBFSを省略する最適化は実装していない。TT/teacher keyはpawns/remaining/side/ply/正規化history/rules/source/evaluator版を持ち、board-only bound再利用は0。

makeはimmutableな親から `State.next`、unmakeは保存した親state/features/map handleへの復帰である。in-place Rust undo実装やαβを測っていない。evictionはcacheの参照だけを外しlive parent mapを変更しない。全81map/2scalar/full-vs-delta313/合法object順/terminal/context/history/復帰をexact比較。46 childのA/B保存9項目対応も本人の別集計器で再確認したが、独立検証ではない。

人工NN0 fixtureはP2 jump/diagonal、H/V invalidation、pawn/side/history mapreuse、第三反復手除外、goal優先200draw、delta/親復帰、40wall配置によるcapacity32 eviction/livehandle保持。合法科学入力・teacherデータとは別記録である。科学cache eviction0、mockでは退去あり。不可達距離を0/勝敗へ変換しない。

## 結果

| 入力 | 順 | child | A 64repeat総ms | B 総ms | B/A | BFS map calls A/B | 到達判定calls 各variant |
|---|---|---:|---:|---:|---:|---:|---:|
| initial-p1 | AB | 11 | 176.9 | 157.4 | .8898 | 2688/1152 | 24256 |
| asym-hv-p2 | BA | 11 | 133.6 | 181.2 | 1.3563 | 2944/1408 | 28864 |
| frame10-prefix-13 | AB | 12 | 253.2 | 205.8 | .8128 | 3200/1536 | 36224 |
| frame10-prefix-14 | BA | 12 | 253.2 | 232.1 | .9167 | 3456/1792 | 44288 |

固定予定分母は全4入力/46 child、各variantの測定child数2944、correctness46/warm46は別。未開始科学入力0。全parity成立、delta最大4entry、同variantの到達判定数は一致。B科学cache hit/missはcorrectness＋warm＋science累計でinitial/asym783/9、prefix13/14 849/9。これを64repeatだけのmissと誤読しない。BFS map callsには共通のState再生/next内計算も含む。

成分はbrowser performance.nowでprepare/合法生成/make/map/feature/contextkey/terminal/unmakeを保存し、map内BFS、mapkey/cachelookupも保存した。nested成分は重複するため全列の和を総費用にしない。合法生成は64repeatでA 147.8/66.3/159.3/89.3ms、B 137.8/106.2/126.4/86.0ms。prefix14 prepareはA130.2/B111.9ms。合法生成・history replayの費用が多く、評価map回避だけでは全入力の利益を保証しなかった。同仕様の共通成分差は順序/JIT/GC/監視・clock分解能等も含み、cache単独因果を認定しない。1回測定なので分散・独立性・信頼区間を立証していない。

**timer欠測**：`components_ms.distance_lookup` は事前ゼロ初期化の漏れで内部NaNがJSON nullとなった。全8科学行で欠測として保存し、0や補間へ変換しない。外側 `total_ms` は独立に取得した有限時刻差でこの欠測の加算を使わない。原rawを修正せず `analysis.json` にerratumを保存。成功科学測定を再実行して良い列へ交換していない。clockの細かい0表示も真の費用0の保証ではなく、細粒度成分の精度には限界がある。

## 失敗・運用・費用

r1はrunner出力parent未作成でFileNotFound、admission/Chrome/science前にexit1。元失敗を保存して私有runnerのみ修復。r2はbrowser RULE_SHA未配線のready入力検査で失敗、科学測定未開始。旧cleanupが進行中の自己owned Beads readerもSIGTERMしたため、終了の遅いBEADS_READ_ERRORを科学エラーとは別保存した。57byte/原read output/hash/signal/時刻を保持。r3はRULE_SHAを明示配送し、monitor stopで全callbackを待ってからbrowser cleanupを行う。readerのschema例外は最大1 bounded retry、pause/readerror/unknownの許可化は0。r3はREADY/primary null/controlFailure null/exit0。r2を良い科学行で置換したとは扱わない。

安いmockはpause/readerror/unready/ready、admission false/unknown/readerror/ownedremainingの拒否でspawn0を確認。実heavy直前に151停止SHA `c6868015bac31ea2e975ed384675bc0ad8b16a39b0c9aae566c5cef0ff0b297e`・現在exact identity・source hash・外heavy・RAM・既experiment保持/forecastを再確認した。既helper callback回収とsole-rootの所有を保持。他ownerへのsignal/interrupt0。NN/Model/Workerなし、main timer/message0、monitor callback wait、innercontrolled forced cleanup、outer sole-root wait/remainingunknown空、現在identity不在は別保存。forcedを自然終了へ、現在不在を全期間/全host保証へ格上げしない。

科学job r3外期間02:33:25.167747→02:33:32.359001 UTC（7.191254秒）、r2 4.535024秒、r1実command観測.066820488秒、重費用有限合計11.793098488秒/全60秒内。全browser＋Node＋descendant current RSS観測peak1,280,385,024byte、guard1,879,048,192byte/配分2GiB。CPU[2]単logical、Nodeheap192MiB。短い静的準備・修復・Git/報告等の全team費用は集計未完了で未知、無料/0とはしない。各短いcommand上限60秒・static120秒を維持し、build/model/GPU費0。現在保持/forecast/有効未使用予約/過去peakを起動admissionと最終manifestに分け、親予約増0/旧未知量減額0。

## 次案は最大1

次別配分候補は、**合法な固定root contextを一度だけreplayしてimmutable親を再利用し、必要childでのRuleA合法生成・到達判定を保つNN0費用診断**。必要費用は同4入力/最大46child、先にkey/history/side/terminal/full313/全map/合法順/復帰parityを確認する小JS mock＋30秒以内browser1job、保存8MiB程度の別配分。原uncached/small parent mapsを対照にし、一般cache容量拡大や未証明の合法壁省略は行わない。反証は履歴/context alias、復帰不一致、又は共通合法生成が依然支配して総費用が減らないこと。その場合は当変更を止め、測定された到達判定の実装費へ対象を変える。ここでは実行しない。

root157 Git `0872cbbadc718c1240f81868fcb912d7e1e6e251` の方策出力によるαβ手順序付け候補も認識した。将来は評価値のみ＋TT/履歴/安い順序を基準に、小policy head/軽量採点器を候補として保持する。最初は順序のみで手除外・深さ変更を分け、方策生成/合法対応/並べ替え総費と同時間棋力/価値精度を別測定する。方策教師は保存MCTS root visit分布で、leaf/rootvalueを付替えない。今回追加policy/NN/αβ/学習0。現混在結果はその候補の優位性を支持せず、費用の支配箇所を先に確認する選択へ反映した。

原結果・必要raw・全attempt・source/run/command・型付き失敗・欠測・資源・停止は対応research-dataと最小archiveへ保存し、Git復元/backup後coordinatorへ引渡す。受入れはcoordinator、親goal/他者close/棋力認定は行わない。
