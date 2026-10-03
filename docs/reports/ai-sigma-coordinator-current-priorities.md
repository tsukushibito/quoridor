# 現在の優先順位と教師生成・学習計画

2026-10-03 frame13。開始12:45:15/終了14:45:15UTC、重開始停止14:35:15、監督14:40:15、monitor14:43:15。親13と92運用はsteward唯一writer。統括は本計画・担当契約・Beadsを所有する。native教師生成の効率と最小NNUE接続を主とし、旧枠の成績・期限・失敗を保持する。173正式198holdoutは学習へ転用しない。Sigma NI/NNUE最高棋力は未達。

## 現在の判断

187の同24入力/K64比較は5mode全120slotを保持し、CPUJS/GPU3/GPU12/GPU24各24GOAL・各1132適格policy/value/joint行を得た。全modejob時間（初期化・回収込み）は137.836401/247.139345/107.8013/88.3345秒、joint率8.212635/4.580412/10.500799/12.814931行秒。GPU24のCPUJS比1.560392、GPU12比1.278615、GPU3比.557727。独立191保存算術/共有RuleA再生と必要source/parity/188保存502値の最終有限裁定も支持する。191科学子/source停止・Git737b5605のreport/算術/replay/binding/stop byte照合とbackup後に統括受入れclose。今回は多数game・共有GPUbatchで実生成利益を有限に確認した。単回固定順・host/warm・CPUJS管理pool2,4,6対GPU0,2,4,6の差、全deep未検証を残す。速度一般保証・教師真値・棋力・元Sigma C++全規則の同一性は認定しない。

RustCPU対照はhistory表示順schemaで3UNKNOWN/21NOT_STARTED、190NN返却・適格行0。JS localeSortとRust byte-sort表示差をNN0で区別し、未開始GPUだけcanonical key/count検査へ修正した。原失敗の補充・救済なし。同Rust CPU構造比は不明、CPUJS実用対照比と分ける。全11attempt630.587673秒は記録された計算job費であり、全team/準備費ではない。正常4mode物理handNN254880はexact、失敗Rustの190はlogical要求で物理UNKNOWN<=190、parity72/startup3別で総physicalforward上限255145。191報告のexact総数表現は187最終counter資格により訂正し、統括受入れ記録に残した。速度・全slot・教師資格は不変。

GPU24を次の独立教師生成の候補へ採用する。現在default/backend/旧learnerを自動変更せず、新生成はこの枠で追加しない。全modeでtrain-val共有7state key/20occurrenceが独立算術にも一致した。game splitだけで独立validationとは扱えない。次の生成・学習ではstate/history重複がつなぐgame群をgroup化し、学習結果前にsplitを固定する。元split/速度結果は書き換えない。同入力兄弟modeを独立教師件数として合算しない。

## 残枠の到達点と配分

| 担当 | 現在の到達点・次判断 | 個別期限・資源 |
| --- | --- | --- |
| experiment187 | 共有GPU多数game実生成を停止、各mode全教師/全fault/実batch/全費・必要archive/Git復元/backupを引渡す。主科学子の回収を本人13:48確認、今は保存処理のみ | newheavy14:15/science14:20/process14:30/submit14:40。CPU4/RAM8/VRAM6親内、GPUjob30分、保持256MiBは既experiment2044MiB内 |
| hypothesis190 | QF1-H32二視点312疎特徴＋後段距離2、既2762学習教師のrootmean value蒸留、full/delta/undoと小探索を有限接続。13:42:53静的開始、13:58:22–23 NN0復元終了。学習14:00:56–59/200step31151sample、native14:02:12/515child full-delta/undo＋Torch固定27対応を本人報告。差8.94e-8。depth1完成/depth2 NODE_CAP未採用、新val rootmeanMSE.994812は定数.715720より悪く重み採用/棋力認定0。統括が修正版Git8bb9e8a2のreport/科学10path、weights archive両member byte/hash、48game weighted集計を有限照合。最終storage/backup/helper停止receiptを本人から待つ。 | CPU8単1/RAM1GiB guard896、science60s/modeljob30s/sample65536。newscience14:28/stop14:32/process14:36/submit14:41。384KiB予約/320KiBguard、uniqueGit・二つの重み保存・残metadataを先forecast |
| critic191 | 全120slot・全教師資格・全費・source/provider/parityの独立有限裁定。13:50:11.649562 claim/static準備開始、短CPU0算術・再生は終了通知済。NN/model/game/GPU0 | static120s/job60s/CPU0単1/RAM512guard448、新4MiBは既critic112MiB内。newscript14:26/compute14:30/process14:35/submit14:41 |

187は最終引渡し後に統括有限受入れclose済み。187実重計算中は190/191の実CPU子を重ねない。187科学停止と191短算術終了の通知を受け、190は直前owner/current/RAM確認で実処理する。自然監督CPU0との窓も各ownerが確認する。source/metadataの軽い準備と実計算を分け、CPU5・LLMactive数gate・全稿相互承認・運用全史gateを作らない。

## 小LR対照と保存失敗の受入れ

188受領13:02:32.710953、claim/static13:03:52.463619（以前の13:03前という時刻要約を訂正）。旧r1はpython不在exit127と13:12入口期限でscience0停止。新future r2は同issue・同未使用予算・新事前登録で13:19:07.788647–11.028623にCPU8単1を一回実行、3.239972秒/202forward/200step/26604sample/GPU0、子回収。旧r1結果/期限を遡及変更しない。

新validation zMSEは176親1.663258、181 LR.01 1.951053、188 LR.0025 1.706646。退行緩和を部分支持するが親よりまだ悪い。新4gameのうち2/4は親より悪化、符号正解66→85→60、015は全model0/70。逆符号飽和45→0は方向修正の証明ではない。全8gameπCEは親より改善し.01より改善量が小さい。176既定を維持し181/188は代替候補保存。LR原因/一般化/棋力改善を認定せず、同8gameを使うLR選別を自動反復しない。

科学Git2f1633a0b96914e8f962f31e0405e370c8c2a809の41対象byte/旧r1不変・保存502算術を統括が有限照合し、188を停止保存済み課題として受入れcloseした。一方local257150+uniqueGit229688=486838Bは448KiBguard458752Bを28086B超過。512KiB予約/combined内でもguard成功にはしない。最後必要stop manifest1805Bを別保持、通常metadata追加停止、未作成項目は未完とする。旧量減額/削除/増額で救済しない。190はこの失敗を受けuniqueGitと全最終metadataのforecastを前倒しした。

## NNUE設計と保持する評価範囲

root189のQF1設計Git e2897f5ebfddf84f8c86a7e04394081ec596032a、到達QF-T1追補Git e8dbab151a32f8f8727889709103f42ab87fc9aaを受領。root所有の2設計pathは統括/担当編集0。現190は各視点312/共有H32/距離2の別小条件で、rootmean K64を教師としz/rootNNを分離する。新小学習をSigma重み・製品NNUE・棋力達成と扱わない。T1の828特徴/H256/接触壁ペア/経路・選択policy/αβPVS全実装やPV退行解消を開始gateにしない。残費不足なら小接続と未着手項目を保存する。

既176+181の48game2762教師・train2260/val502を再利用する。正式173holdout非転用。validation再利用、4game相関、追加step/旧再露出の交絡を保持し、多様性単独の因果を認定しない。180K800現RustはJSより23–33%遅く、181checkpoint削減は限定採否未達でCPUJS基準を維持した。176 GPU3/maxB2負利益からGPU一般を除外せず今回多数game接続を測った。固定751186 selfplay_cpp.pyのworker数とgame数分離を参照したが既定2048/max1024の複製や歴史学習設定の証明はしない。

## 監督・停止責任

92親13 SHA160ca38306c6ddaaf81b874771afd0a52f5127dd5b7924588b6fab688bf80f8e、scheduler3534745/start28492381・monitor3534758/start28492397の本人running/loaded24hash一致を受領。期限通知14:35:15、監督+scheduler14:40:15、monitor14:43:15、証拠14:45:15は92 owner。統括は親/運用binding編集・92再配送・強制tick0。自然turnのcompleted/finishと全期間/外部NN停止保証は分ける。

監督提案のRjoint全費・全予定打切り手数、低LRのπ利益減/価値方向、保存uniqueGit forecastを採用した。効果は実結果へ限定し、手続きや配送acceptedを科学受入れとしない。個別課題はsource/子停止・必要保存と有限検証後にcloseでき、goal未達は維持する。

190の保存集計を統括NN0で再計算し、全validation502のrootmeanMSE.704042→.646561は定数.697566より改善、新281は.717160→.994812で定数.715720より悪化と確認した。機能接続の有限受入れと重み採用を分離する。初期最終Gitdf42/a7は報告path未収録、担当savehelper修正版8bbでreport/科学不変のbyte復元を確認した。元保存失敗を科学negativeへ変換せず保持。現在は190最終metadata/backup停止receipt待ちで実science追加0、閉じるための新LLM専用turnも起動しない。次枠候補はGPU24のfresh独立教師を露出group splitで固定し、固定QF1のvalue汎化を少数で判別する一案。未許可の次枠や現在14:35重開始上限を超えた実行は行わない。
