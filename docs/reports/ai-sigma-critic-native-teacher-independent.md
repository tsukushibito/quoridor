# Native教師データ・小学習接続の保存独立検証

quoridor-4lc.179 / 契約1 / critic。受領2026-10-03 09:57:04UTC、claim・静的読取開始09:57:48.740713UTC。新command10:14:04、処理10:17:04、提出10:27:04UTCの固定早側を維持する。176の原CPU成果の採択と新GPUbranchの入口は別である。

## 裁定

**有限支持**：全24CPU自己対局GOALから1409行の教師を保存し、game split、CPU200step、checkpoint/ONNX、独立lineageの全予定4診断へ接続した。今回の独立算術と共有RuleA再生で最初の差は検出しなかった。**不足**：教師の棋力、学生の改善、Sigma同等・NI・最高棋力、GPU生成倍率。4診断は0W0D4Lであり、誤教師・hidden32の能力・200step不足を一意に選べない。今回新NN/session/forward/学習/対局/GPUは全0。

## 教師の分母・視点・対応

1409/1409行でrootN64、edge63、整数非負訪問数、π=visits/63、合法mask外mass0、mass1を独自Python算術で確認した。保存legal_order209とmapping136は単射・順対応し、実盤面destinationから方向を計算する独自変換でP2の上下反転・壁anchor反転を照合した。P2 jump対応46entry、P2 wall対応46688entry。共有RuleAによるNN0再生では全24局1409newhandsのstate key/side/ply/history/features648/合法順/採用Action/最終key/GOAL・winner・手数が一致した。

πは教師分布で、温度1の初16newplyの実サンプリング行動とは異なる。以後tau0のstrict first argmaxを確認した。rootNNは保存NN137最後のf32bitsと一致、rootmeanはroot手番視点、leafNNは最後の展開leaf自身のside/plyであり別ラベルである。全行の終局winnerからz_p1とz_stmの符号、policy/value/joint eligibilityを再算した。打切りzunknownをdraw0へ救済した行はない。Rpolicy=Rz=Rjoint=1409、保存completed NN81768、terminal-noNN8408、discard0、配送CP1409。81768+8408=1409×64であり、startupは別分母。

2入力の保存allCP/finalOnly結果はroot/firstNN bits・root_edgesが一致し、CP数64→1、rootmean=rootValueSum/64、rootValueSum=rootNN−ΣchildValueSumの算術を確認した。全1409行には深部backup全ledgerがなく、全探索deepの再認証はしていない。特徴・合法性の再生はownerと同じRuleA/固定Web由来sourceを共有するので、別ルール実装による完全独立検証ではない。独自π・mapping・z・split・重複・費用算術と区別する。

## split・漏洩の範囲

SHA256(lineage)の先頭32bit modulo5によるgame splitを再算した。train20game1188行、validation4game221行。train/validation game lineageは分離している。保存四定義を独自に再集計した。

| 定義 | unique | crossgame共有key / 行occurrence | train-validation共有key |
| --- | ---: | ---: | ---: |
| position key | 1384 | 16 / 37 | 0 |
| state+side+ply+canonical history counts | 1388 | 16 / 37 | 0 |
| features648 | 1384 | 16 / 37 | 0 |
| features648+legalmask136 | 1385 | 16 / 37 | 0 |

同game内の相関、未観測将来のstate重複、共通開始盤面の重複、独立state holdoutは保証しない。新native176-train- lineage、openings/source・raw参照から旧173正式198局を教師へ取り込んでいないことを有限支持する。単に文字列173がないことだけを完全な出自証明にはしていない。future arena/正式holdoutを学習へ転用しない。

## 学習と診断

learner-preregisterのsource SHAと現在凍結learn.py等7sourceを一致確認した。from-scratch seed17680311、648→32ReLU→policy136/value1tanh、手動SGD.01、minibatch128、最終200step固定。損失は合法mask付きπCE+z_stm MSE、rootmean auxiliary0、価値unknown mask方式である。保存未学習基準と最終損失は以下。

| split | πCE前→後 | zMSE前→後 |
| --- | --- | --- |
| train | 3.861991→2.484510 | 1.013208→0.207420 |
| validation | 3.903287→2.514467 | 1.047608→0.684094 |

これは保存評価receiptのfit改善であり、今回独立forwardで再測定していない。checkpointSHA c1abf195c272eb9a143ad0f88d209b7741c8c9bca0c2318de37af759ea9c2351、ONNXSHA 54ed35d8b175d342d8fe50339fd918dd138c1bfb6c376c90bd50daf791b6ca7a、datasetSHA a8e79d3bdcc7f5d9d7c7105a476f37e3168fc44eec47ea221a57dddd6ae2e94aを現物と照合した。保存weights-only/bit-equal reloadと事前固定先頭5rowのORT1.30CPU1thread parity（policy最大abs9.53674e−7、value6.39819e−7、abs1e−5+rel1e−4、batch1経路）をsource/rowID/SHAへbindした。binary hashと保存receiptは新backend実行の再認証ではない。

全予定4arena slotは新native176-eval-2lineageの両色、K32 fixedK診断である。共有RuleAで110newhandsを再生して開始prefix/合法性/最終key/GOAL/winner/student scoreに対応、全4loss、欠測0。保存primary null、monitor READY、2engine exit0と原run残process空を照合した。500ms正式samewall判定ではない。

## 費用・提案は最大1

成功生成3job wallは72.162764+70.974192+55.359642=198.496598s、7.098358行/s、0.120909game/s。export .633781sは別。記録済compute全attemptは235.726026s（generate198.496598、arena16.666095、repair14.422605、learn3.724501、mock2.416227）。exportと保存overlap checkerを加えた既知小計236.583166sで、1409行/既知小計は約5.956行/sだが、GPU根repair等も含む研究支出でありCPU production速度とは異なる。学習loop.192540s、Python全体1.479662s、managed learn3.724501sは包含関係にあり重複加算しない。生成3coresのsearchwall/JSON pipe/API awaitは重なり、kernelCPUやjobwallへ加算しない。

generate-b3-r1 CONTROL_STALEとarena-r1 EXTERNAL_COMPUTE_ALLOCATION_UNKNOWNは科学子未開始の管理attempt、wall欠測をunknownのまま保持する。opening生成・source/Git/Beads/報告/pack・一部debug・cleanup個別費は未計測。scope内計測費を全研究総費へ格上げしない。

**唯一の採択提案**：K64と合法・z・lineage品質を保ち、Rpolicy/Rz/Rjointそれぞれの有効行/全attempt jobwallを成功production rateと併記する。176のcost-ledgerが既にこの区分を提供するので、採択時にunknown費を残したまま利用できる。探索量削減や成功runだけの算入を効率改善にしない。新計測/新学習/全承認を入口に追加しない。

GPU原r1/r2ではCPU001 raw欠測をUNKNOWNのまま保持し、後着NN0 firstteacherroot joinは新有限比較としてargmax13/visits/π一致、実tau1 action89とは別、と記録される。原欠測tapeの復元や全deep保証ではない。追加6生成は通知時点全NOT_STARTEDで生成倍率未成立。後続GPU修復・新benchmarkはこのCPU裁定の分母に混ぜない。

## 保存・停止

受領forecast94,715,014Bは既critic guard117,440,512B内、旧unknown88,190,086Bを減額せず新scope2MiBを計上した。CPU0科学算術+NN0 replay+小binding約1.047s（保守charge5s/90s）、peak203,374,592BはRAM guard448MiB内。直前current確認・GPU停止通知と科学子終了PIDを保存した。後着GPU再開の不在や全host/全期間は保証しない。python未導入名による管理exit127とchecker r1 whitespace SyntaxErrorを修復版と分けて保存し、原棋力lossにしなかった。必要source/hash/raw参照・コマンドは本issue自域に保持する。原176/177/173・役割・親・registryは編集していない。Git stream復元・Beadsbackup後にcoordinatorへ引渡し、受入れcloseはcoordinatorが行う。
