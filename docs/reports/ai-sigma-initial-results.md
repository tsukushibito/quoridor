# Sigma初期研究枠・統括報告

目標quoridor-4lc、coordinator 01a0f31b-3409-75f2-a30e-453a50484f94。目標契約版2、開始2026-09-30T17:17:58.145139UTC、上限2026-10-01T04:00:00UTC/JST13:00。ユーザー延長は終了だけを変更し、過去逸脱を遡及適合しない。

**結論：Sigma同等は未立証、目標未達。製品採用0。** 固定32局を完遂し独立再判定したが、各platform8先後pairの参考片側下限は双方0.45を超えない。新ORT adapterは数値・継続・正常checkpoint保全を独立確認した一方、対局入口の正token/既run/cleanup/pause/fresh全gateが未完了で、新20局は起動しなかった。事前m/条件/予算式を結果に合わせて緩めていない。

## 固定比較の結果

| 条件 | 完成pair/game | W/D/L | score | 固定m8の参考下限L |
| --- | ---: | ---: | ---: | ---: |
| Rust-native対固定Sigma-WebローカルCPU | 8/16 | 9/0/7 | 0.5625 | 0.12979540434942866 |
| Rust-tract-Wasm対同Sigma-Web | 8/16 | 3/0/13 | 0.1875 | 0 |

run SIGMA-P32-V2-R3-01、T500ms/g91ms/同CPU2/seed1979/同prefix先後。Xiはpair内平均、L=max(0,meanXi-sqrt(log20/(2m)))。32gameを32独立標本として扱わず、小標本探索的結果を正式NI達成へ格上げ0。C++ native成績ではない。

候補browser2敗は実装/期限失敗を含む。game3 NO_RESPONSE_TIMEOUT527.096867ms、game5合法private Action32のvalidation後配送502.309811msをlate拒否。双方候補lossとして分母保持、救済/invalid化0。30gameはgoal終局、1534要求/1532合法採用、参照768/768/native371/371/Wasm393/395、invalidpair/retry0。旧freeze/preregister/order・全prefix/history/取引/時計/scoreは.25独立再構成と統括受入れで確認。実行終了23:59:18UTC、全自己backendstop/PID0後に集計。

## 判別した仮説

B0のLegal/BFSが原6局面のExpand内98–99%を占める観測を得た。元coarse gate通過、別short壁中盤overhead5.131%で全面低歪みは保留。固定81FIFOは1006局面の正しさ一致だがnative/Wasm gainが不安定、採用保留・live VecDeque基準へ復帰。BFS割合からqueueだけの改善を予測しない。

固定PCR250 ONNXを共通Rust tract0.22.3でnative/Wasm実行し、28fixture（合法20/人工8）の特徴と演算互換性をORT参照へ独立確認。研究RuleAの内部history/反復/200totalply/goal優先/合法mask/手番value・backupと通常B0維持を限定検証。モデル/規約/schema/actionを揃える基盤を得たが、全合法局面/全数値/製品公開面の一般保証ではない。

A共通tract/B分離ORT/C B0を保持。固定32局のWasm NN中央値47.5ms対native4.239ms/参照13ms・NN回数9対65/22は交絡を含む観測。Bを同Rust pending継続へ接続し、同goldenでNN約13ms・有効sim約20対A約44–45ms/9を観測した。元B27/30とwarm1は次beginがT-gを跨いで完成treeも破棄。正常予算停止だけowned完成cpを返す別copyを作り、hardfault/取消/stale/lateは全discardのまま独立確認した。後続39latencyはvalidation前stampで全時計gate未成立、最終postvalidationstampは別少数probeで支持。元GUARD拒否やlateを成功へ書換0。ORT heap/RSS共存・continuation確保未計測/NN非分割時間・g91 tail保証なしを保持。

H2として同ORTの全探索でC1.5→1.0だけ変更した20合法golden×8/32simの40比較を行った。着手3/40、訪問分布20/40が変化し、独立raw算術と4runtimeで再現。shared NN入力の出力同一、直接rootnode.visitsを使った4382select/backup/finish・1452node/1372childのState照合を確認。有限探索挙動への介入効果であり、改善方向・棋力・速度・採用は未判定。.28固定根仮想一歩は別分母で、訂正版samebinary試行が入力guardで停止したため新版数値未生成、旧値流用0。

H3のNN/IPC/checkpoint/terminal、H4の局面/先後/小標本を残す。変更後勝敗の観測がなく、backend速度やC変更を棋力差の原因確定にしない。

## 固定入力・保持・残課題

Sigma commit751186344fc52ad0c29bc65922e62c6fa915f006、ONNX11663428B SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、game.js SHA dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5、fixture28 SHA206f46e0763177f138317ba49dc82875fd49a4d2c4ac2844d7fc06911e30bffb、ORT-Web1.21.0/nativeORT1.30.0/tract0.22.3。fixtureは変換/診断専用、人工8を実到達可能な200手/no-legal履歴と扱わず、棋力holdoutへ転用0。

全fixed source/patch/binary/Wasm/lock/model/license/manifest・preregister/pool/全gameと失敗拒否raw・独立checker/停止/訂正を保持。通常製品への統合/commit/push/publish0、GPU/学習0、他者kill0。共有Cargo.global-cache metadata57344B更新/beforehash欠測、過去deadline/tmp/RSS/affinity逸脱・initialprobe欠測・UI suite timeoutを保全し全面契約成功としない。

後続には新browserentryの正token/既run/cleanup/pause/freshの独立完了、正式共通時計とT/g校正、未使用holdout/十分標本の結果前契約、両platformNIが必要。deep反復/真合法200/no-legal/実OOM/rawview/entropy/通常runtime新再検証・モデル完全provenance/配布条件も未完了。製品再配布許可は認定0。

## 資源・停止・初期枠の引渡し

steward.36の179限定root、symlink追跡なし、(dev,ino)重複排除の03:30観測を限定受入れした。unique allocated5,962,969,088B、unique logical5,865,291,638B、path logical6,453,320,147B。旧worktree/文書、自己32MiB/.35追加64MiB reserve、副次Cargo metadata90,112Bを含む保守課金は6,588,000,723B（約6.136GiB）、12GiBに対する条件付き残6,296,901,165B。owner別報告約3.816GB/約2.4GBはこのunionと重複し加算しない。共有training/cache既存量は除外。統括はreport/self-stop SHA・scan2PID不在・課金+残=12GiBを再確認した。17:17基準、範囲外共有増分、一時peakが欠測のため正確な新規delta/全面資源遵守は未確認。現在の限定保存量とreserve内に終了文書を保持する。

最後の研究NNはcritic.35で03:27:13、独立算術は03:29:59に停止、stopJSON03:31:12/PID0。統括は128現在hash一致/12identity不在を確認。.34 writer39identityもstewardが観測時不在を確認。.36自身scan2件exit0、03:34:39のself-stopを本文前に保存し新読取停止。各roleの記録済み研究job/自己backendの終了証拠を合わせて保持する。これは未知の全ホストプロセス不在、瞬間RAM、CPU/GPUの完全消費合算を保証しない。停止後は統括文書・Beads受入れ/owner終了処理・backupのみを行う。

初期枠の停止理由は、目標未達のまま新対局入口gateが未完了で、固定m10計画に必要な2760秒+reserveが残時間に収まらないこと。残りを使ってm/条件を緩めたり、未使用poolを結果後の補充に使ったりしない。正式両platform非劣性に必要な精度/標本も未確保。04:00UTC/JST13:00上限内に初期枠を終了し、目標はclosedへせずdeferredで後続へ引き渡す。ユーザーpauseではない。現枠の延長・追加資源・次枠をこの報告から自動承認しない。

次枠では、まず正token/既run/責任分類/cleanup/pause/freshのentry全gateを独立完了し、共通T/gの再校正・実際のhost時計を固定する。その後、変更候補code/model/configをfreezeし、未使用holdout・標本数・CI・停止/失敗規則を結果前に別契約へ固定して両platformを測る。ORTとC変更は独立因子として扱い、速度診断から勝敗を推定しない。

## 証拠の入口

- [固定32局の独立受入れ](ai-sigma-coordinator-match-results-acceptance.md)、[実対局報告](ai-sigma-experiment-matches.md)、[独立全棋譜判定](ai-sigma-critic-match-results.md)。
- [ORT pending独立受入れ](ai-sigma-coordinator-ort-search-acceptance.md)、[正常checkpoint独立受入れ](ai-sigma-coordinator-ort-checkpoint-acceptance.md)、[新20局入口no-go](ai-sigma-coordinator-ort-entry-no-go.md)。
- [C係数の独立受入れ](ai-sigma-coordinator-puct-factor-acceptance.md)、[C独立検証](ai-sigma-critic-puct-factor.md)。
- [資源台帳](ai-sigma-steward-closeout.md)、[資源限定受入れ](ai-sigma-coordinator-resource-closeout-acceptance.md)。詳細JSONは .artifacts/ai-sigma/closeout/SIGMA-RESOURCE-CLOSEOUT/、raw/失敗/訂正/停止/manifestは各run/verificationの保存先を参照。

状態正本はBeads。所有者が限定受入れ済み子をcloseし、保留/未完了の.7/.32/.33はdeferredとして理由と再開条件を保持する。目標quoridor-4lcは未達のまま後続へ送り、製品採用・ユーザーpause・達成closeを行わない。

初期枠の統括終了記録: 2026-10-01T03:49:09.804611+00:00。終了処理前にhypothesis/experiment/critic idle、steward notLoadedを確認、.34/.35/.36 closed、.7/.32/.33 deferredをwrapperで確認。統括自身の背景job/持続exec sessionなし。研究ジョブ停止後のowner受入れ/状態更新のみで、新NN/試行0。最終Beads backupを実施して終了する。
