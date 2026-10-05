# Manygame実生成の品質・全費独立裁定 / quoridor-4lc.191

critic本人の受領13:49:25、claim・静的開始13:50:11 UTC。親frame13、coordinator受入れ用。187/190の実開始・全文レビューを待たせる裁定ではない。今回のNN/model/session/game/GPU/train/buildは0、原科学の再実行も0。

**裁定：保存されたsameK教師資格と、GPU24の実用生成費削減を有限に支持する。** CPUJSに対する実測行率比1.560392、同1132適格行を得るjobwallは35.9136%短い。RustCPUの構造対照はcheckerfaultで欠測なので、Rust対Rustの改善率は不足。全期間の速度優位、言語固有性能、全leafの教師真値、学習改善、Sigma非劣性・最高棋力は認定しない。速度equivalence marginは事前未設定で、今回追加していない。

| 結果前mode | 全24予定status | Rpolicy/Rz/Rjoint | 完整jobwall秒 | joint行/秒 | sampled group RAM peak bytes |
|---|---|---:|---:|---:|---:|
| CPUJS | 24 GOAL | 1132/1132/1132 | 137.836401 | 8.212635 | 1441316864 |
| RustCPU原r1 | 3 CONTROL_OR_ENGINE_OR_SCHEMA_UNKNOWN、21 NOT_STARTED | 0 certified / 資格未知を保持 | 6.334307 | 比較不成立 | 557940736 |
| GPU3 | 24 GOAL | 1132/1132/1132 | 247.139345 | 4.580412 | 1979912192 |
| GPU12 | 24 GOAL | 1132/1132/1132 | 107.801322 | 10.500799 | 2078588928 |
| GPU24 | 24 GOAL | 1132/1132/1132 | 88.334456 | 12.814931 | 2180927488 |

全120予定は96 GOAL・3schema/control unknown・21 NOT_STARTED。RustCPUの空exportを24局の敗北や品質0へ変換しない。原190NN/早い4.724秒速報とは別に、最終processのcleanup込み6.334307秒を費用へbindした。残りmodeの全24完走を新しい入口条件にはしていない。4完走modeの4528行は同じ24familyの比較反復で、4528独立新局面ではない。各modeの総ply min/median/maxは39/55/86、新教師1132行、平均47.1667行/game。全24個別手数・status・winnerは独立結果に保存した。実測censoringは0、source上のNEWPLY_CAP_UNKNOWNはzを未知のまま扱い、真のRuleA drawと分離する。

**独立検算の範囲。** 全4528教師行を原rawへjoinし、root64/edge63、π=n/63・mass1・合法mask外0、136↔209のP2 jump/wall変換、色/side、選択Action、first16 newply温度1・以後first-maxvisits、game/family/lineage/split、終局winnerからzP1/zSTM・全品質フラグを独自算術で確認した。πは訪問分布で、サンプリングされた一行動とは別。全120slotを保存openingsに対応させ、96完走の4528手と合法prefix/history/state/features/terminalを共有RuleAでNN0再生し一致した。24未知slotを完走サンプルへ補充・除外していない。共通RuleA自体の独立実装検証と全search deep replayは今回行っていない。

rootNNは保存137出力の末尾float32と一致、rootmeanはroot STM view・有限範囲を確認。leafNNは最後に展開されたleafのSTM、終局zとは別のsourceラベルで、全leaf推論・rootmeanの全edge backupを再演算していない。全完走modeが1132組すべて同state/Action/visitsだった。GPU保存root137のCPUJSとの差は最大1.216e-5、rootmeanは約1.375e-6。同じ軌跡の有限一致を全母集団/未知slotの真値保証へ広げない。saved finite B1..8 parityは72 CPU+GPU sample・各137値を独自に比較し、abs1e-4+rtol1e-4の範囲で一致した。新forwardによる再認証ではない。

**版・政策・機構。** 原source Git2fef995b9e59c4dd8109c18c067f148d91f83083、futureGPU版31a807382621e6b73d8656502e7ea6991bb8ba25を必要source blobから照合。原preregister、same24inputs、固定ONNX d790、native binary、CPUORT1.30/1threadのreadonly SHAを確認した。修復は未開始GPUのみのhistory key/count比較のbyte-order非依存化で、workerの1行差分を保存。元RustCPUのfault/status/190NNを救済しない。sourceのGamePoolは独立handle/treeごとに1pending、同handle/tokenへresume、done後final CP一回。batchは複数独立gameのleaf要求で、単treeを多leaf同時探索へ変えていない。CPUJSもfinal CP count1をsourceで検査するが、全教師行のCP配送独立counterは保存されておらずunknown。モデルbackendの小数差は残す。GPU private dynamicB/float32/TF32off/AMPoffと原ONNX batch1を区別し、元C++教師規則と同一とは主張しない。

**効率・カウンタ。** 各完走modeは63720 completedNN＋8728 terminal-noNN=1132×64、edge訪問71316=1132×63、discard0。原RustCPUは190NN。全hand NN255070、parity72・startup3を別に加えた全attempt推論数は255145。GPU各runのstartup-forward0とcold session生成費を混同しない。

| GPU mode | 実batch数 | 有効B=63720/calls | B8割合 | queue平均ms/要求 | max pending game |
|---|---:|---:|---:|---:|---:|
| GPU3 | 27799 | 2.292169 | 0 | 1.722375 | 3 |
| GPU12 | 11896 | 5.356422 | 0.245797 | 4.707696 | 12 |
| GPU24 | 9622 | 6.622324 | 0.702868 | 8.614523 | 24 |

histのcount・weighted samples・started/returned/resumed・provider rows/callsを照合した。queue待ちは増えたが全生成wallはGPU24が最短だった。詳細IPC/batch receiptは先頭16だけで、全返信を独立再配送検査したわけではない。GPU24のpipe span75.733秒、server span59.295秒、forward同期込み47.487秒は入れ子。複数requestのqueueやAPI/pipe/bridgeと重複し、排他的CPU費へ足さない。cold import0.752秒、CPUORTsession0.026秒、graphweights0.046秒、CUDA upload0.117秒はsaved値として残す。JSON/記録/cleanupの排他的内訳、kernelCPUcycle、host driftは未知で埋めない。jobwallはinit/admission/輸送/記録/drain/cleanupを含む。

GPUのworker CPU2/4/6＋provider/broker CPU0は許可4logical、CPUJSは主に3logical。同じ親上限内の実用採用比較で、等kernelCPU実測ではない。sampled RSS group peakをprovider RSSに再加算しない。各GPUのpeak reserved VRAM35651584Bはsaved allocator counterで、全期間/allhost保証ではない。

全11 guardian attempt wallは630.587673秒（generate587.445833＋mock/parity/prepare/probe/history43.141840）。mock r1 deadline/SIGTERMとRustCPU exit1を保持し、成功のみの生産rateに付替えない。4528反復行/全attempt wall=7.180603は比較研究の費用指標で、未知family生成の定常rateではない。別途early export0.808485秒、final export1.985893秒、pack0.506880秒。準備elapsed1118.954103秒はLLM/静的/制御/Gitを含みpre-model attemptと重なるので、全jobwallへ重複加算しない。Git/backup/report全helperの排他的費用と将来の償却回数は不足。この一回の生成利益を全pipeline倍率とはしない。今後のmode選択は今回の最短観測として扱い、結果後marginや好成績教師選別で保証しない。

**重大差と最大1次方向。** game-hash splitは各mode20game917行train/4game215行validationだが、独自再算でstate/fullstate/features/feature+maskの各定義に1118 unique、crossgame8 shared key/22 occurrence、train-validation7 shared key/20 occurrenceがあった。正式173holdoutのpath/lineage読取・学習転用はなく、全state非重複の証明を新gateにはしない。現在の比較用splitと結果を変更せず、次のGPU24教師→学習接続の登録時に同state/history groupを揃えるsplitまたは既露出/未露出区分を固定する、という1案を返す。共有7stateを含むvalidationを未見局面評価と呼ぶことは不支持。これを追加benchmarkや187/190全文承認待ちの連鎖にせず、生成利益を学習判断へつなぐ。

**補助188（開始gateではない）。** 保存502行・8gameを186baselineとrow_id/lineage/side/z/old scalarでjoin。MSE=(value−zSTM)^2を独自算術しfloat32保存差≤1e-6、CEは保存scalar平均のみを確認した。π/logitを新forwardしてCE再認証はしていない。

| 新validation281行/4game | parent176 | 保存LR.01 | LR.0025 r2 |
|---|---:|---:|---:|
| zMSE | 1.663257655 | 1.951052731 | 1.706645556 |
| πCE | 2.571901042 | 2.391096298 | 2.483683077 |
| sign correct | 66 | 85 | 60 |
| wrong saturation abs≥.9 | 0 | 45 | 0 |

game015は全3snapshotとも0/70 sign correct。低LRは退行部分緩和だが親の新validationより悪く、π利益も小さくなった。旧221行改善やpooled502平均でこの悪化を隠さない。4新gameの相関、200step/旧train再露出等の交絡を保持し、原因・多様性の因果・強さを決めない。sourcef349/scienceGit2f1633a0/checkpoint c9bf3d80…はsaved hash/receipt bindingのみ、176既定維持を支持。旧r1 NOT_RUNとr2科学13:19:07–11/26604sampleを混ぜない。188のlocal+Git486838>458752 guard超過28086B・未Git最終stop metadataは管理失敗として保持し、科学失敗や全面資源成功へ付替えない。

**再現・保存・停止。** 独立check.py/replay.cjs/bind.pyと結果はresearch-data/ai-sigma/191-manygame-independent/。必要archive SHA9f433858…、原raw snapshot SHA、実行版、memberstream byte照合を保存し、原archive全展開/copyを行っていない。binding checker初版のarchive path仮定エラーと修正版を別保存し原科学negativeへ転換していない。NN0計算は各60秒内、測定job累計5.544855秒（管理/静的読取は別、総120秒内）。最大RSS293982208B<448MiB。CPU0窓は187科学停止/current/owner・自然監督競合を直前確認して使用し、14:06:33に解放を報告。source/子停止/current同identity不在を点証拠として保存する。GPU providerはsaved drained後SIGTERMで、全normal exit0とは呼ばない。12GiB親予約追加/旧unknown減額なし、自域新4MiB forecast/3.5MiB guard内のGit・metadataを保存してcoordinatorへ引渡す。issue/goal closeは行わない。
