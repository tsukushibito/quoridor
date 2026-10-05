# frame20 Dclip/Dtanh 保存独立裁定 — quoridor-4lc.251

全8予定局・340採用手の時計、合法prefix、履歴、勝者、全attempt費を有限に支持する。Dclip/DtanhのNNUE成績はともに2勝2敗。同入力・同完成深さではDの値・採用Actionが変わるが、今回の2familyからtanhの一般的な戦略利益、公平性、NNUE最高棋力は認定しない。既Dclipをtanhへ昇格する根拠は不足している。

担当はsaved critic `01a0f31d-8227-7e03-a7e6-915b4918c11b`。frame20終了02:51:02 UTC、個別算術入口02:14・停止02:16・保存02:24を維持した。旧246/241/238/234の費と旧229最終NOT_RUNは変更していない。本件は新source45+calc45=90秒の保守課金、MAX1で終了。新NN/model import/forward/学習/GPU/対局/旧test・173正式holdout読取は0。

## 入力・版・独立入口

producer249の停止正本は `research-data/ai-sigma/frame20-distance-arena/scientific-stop-v1.json`、SHA `cf5db4806967e4d1011a77a946b50009c2d5bf5859b7983342aff56db774eb76`。停止源・payload・原hands2・各process・3background cleanupを `stopped-inputs.json` に束縛した。原bytesは251-retained-inputs/archive-manifest参照で読み、全rawコピー・全pack展開は行っていない。source/currenthash前後一致はこのsnapshotを支持し、全人物理隔離や未来不変を保証しない。

正運用ROLE-RESPONSIBILITIES-252のscheduler556338/tick41842377・monitor556359/tick41842391、config e443a613…719cbdd/contract c4028354…a28193、24currenthashと物理CPU/RAM/GPU/ownedを実行直前に確認した。自然supervisor LLM activeだけを拒否理由にせず、実CPU子の非競合を確認した。旧停止runtimeを新freeに代用していない。

専用entry `tools/ai-sigma-frame20-distance-arena-independent/check-distance.py` SHA `370ca5a876a347afbc388958e731bb7c1b50e72b2e90b946632bdde23bf1c6cd`、task `frame20-distance-arena-independent-251-v1`、schema `distance-arena-independent-v1`。実argvと期待outputをadmissionに保存しpostで一致確認した。01:59:43.769288→01:59:44.153554 UTC、PID560891/tick41860014、exit0/wait/exact不在、0.384310279秒、family RSS観測peak97,042,432B。共有RuleA子PID560892/tick41860023もexit0/wait/exact不在。専用MAX1を再実行していない。ROLE252更新待ちは静的pending/0jobで、科学失敗やretryとして数えていない。

## 条件・全分母・配送

旧242と同じ2opening prefix/entropy/action seed2166843942を使う新8slot。family0はclipP1→tanhP1→tanhP2→clipP2、family1は逆順。8独立初期局面ではなく2familyの色交換・方式兄弟である。全8TERMINAL、UNKNOWN0/NOT_STARTED0。全340記録が期限内completeparse・identity/generation/key/fullhistory・合法完成Actionとして採用され、late-valid破棄0。partial depthは採用していない。共有RuleA再生で初期prefix、全340手（P2 168手）、履歴、全root合法手数、終局winnerを照合した。

| slot | family | D | NNUE側 | 手数 | NNUE結果 |
|---|---|---|---:|---:|---|
| 1 | 0 | clip | 1 | 46 | L |
| 2 | 0 | tanh | 1 | 46 | L |
| 3 | 0 | tanh | 2 | 50 | W |
| 4 | 0 | clip | 2 | 52 | W |
| 5 | 1 | tanh | 1 | 33 | W |
| 6 | 1 | clip | 1 | 51 | W |
| 7 | 1 | clip | 2 | 31 | L |
| 8 | 1 | tanh | 2 | 31 | L |

保存clock6fixtureは正常採用、stale identity排除、late101.149759ms拒否、未完成非採用、EOF、parse検証超過116.062952ms拒否とcleanupを必要算術で確認した。現保存fixtureの範囲であり、新hardware時計の再測定や旧248/244未実施条件の救済ではない。

## 数学・探索と同入力対応

frozen candidate.f32 SHA `b81792d5ba00c6d79b58cada2fc81d84ea822db48c04420b4e269fb9b71841b3`、manifest SHA `9bc786e82c3b73a462da4a30e1d884678ef9f7bdb757560dd6bb437fa4b25d40`。距離係数a=.06038215201109912/b=7.925687690687516、STM順距離f32/scale/NNUE経路を維持した。旧242とのterminal/ordered/child/delta/negamax源は同一。全legal・rootbest・TTnoise0・90ms inner/100ms parent・32768node capを保持し、非terminal Dの `clip(u,-1,1)` を `f32(Math.tanh(u))` へ変える。terminalは先に処理される。保存preflight4条件・8commondepth列の値/Action一致を確認したが、新forward再認証は0。

選定前懸念は、tanhが飽和同値だけでなく全非terminal値とterminal相対尺度を変え、Math.tanh費も変える点だった。`D_nonterminal_saturated` は変換前 `abs(u)>=1` 件数であり、tanh出力の端点件数・選択rootの極値起源ではない。下表は到達局面が異なる集計なのでmatchedwork単独原因へ広げない。外部の提案採否は未確認で、ここでは指標の意味を明示した。

| 条件/engine | 採用手 | 完成depth平均 | processed | NN / D eval | 変換前abs(u)>=1 | 配送最大ms | 最小余白ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| clip/NNUE | 90 | 4.688889 | 185749 | NN138715 | — | 98.570980 | 1.429020 |
| clip/D | 90 | 5.866667 | 268351 | D193313 | 18230 | 93.550464 | 6.449536 |
| tanh/NNUE | 80 | 2.812500 | 164755 | NN129527 | — | 98.779367 | 1.220633 |
| tanh/D | 80 | 4.600000 | 240691 | D186271 | 24907 | 94.944573 | 5.055427 |

32768cap到達は全条件0。手数・history・到達stateの差が全体depth平均に含まれる。異なる到達stateの比からtanhによる探索劣化や改善を一意に選ばない。

同board+STM+全記録RuleAcount-history一致だけを独自pair化した115組について以下を確認した。最初12witnessと全pair列SHA `ec5009bff1671f50892a62ba4757899c4808bbbfa1c9d5c28cd7127de365afae` を保存した。

| engine | pair | tanh深い/同じ/浅い | 同完成depth列 | 値最大差 | Action差列 | 配送差平均tanh-clip ms |
|---|---:|---|---:|---:|---:|---:|
| NNUE | 57 | 0/55/2 | 150 | 0 | 0 | +.091288 |
| D | 58 | 0/57/1 | 275 | .211324871 | 6 | +.184882 |

NNUE最終Action差1組は完成depth差と分離し、共通depthでは一致した。D最終Action差1組と共通depth6列の変化は今回介入で許容され、計算bugとは扱わない。全root exactchildren/全argmaxはNOT_RECORDED、selected failsoft値を全minimax真値へ拡張しない。

## 全費・有限判断

| attempt | known=charged NN | guardian秒 | 終了 |
|---|---:|---:|---|
| preflight | 5500 | 1.016560590 | exit0/wait/exact不在 |
| family0 | 156272 | 17.821079367 | exit0/wait/exact不在 |
| family1 | 111970 | 13.261598019 | exit0/wait/exact不在 |
| 全3attempt | 273742 | 32.099237976 | original/inflight UNKNOWNなし |

保存counterとprocessを独自に足し戻した。背景wait、controller/search inclusive span、外elapsedをexclusive費に足さない。producer管理aggregate wallはUNKNOWNのまま保持し、初期default affinity→CPU2の管理補足を科学成績へ付け替えない。独立検算の0.384310秒と保守90/90はproducer科学費から分ける。旧frameの失敗・UNKNOWN費は変更していない。

有限支持は全分母・保存clock/合法・数学介入・同入力共通horizon・全attempt費まで。共有RuleA、producer停止/NNcounter/保存fixtureに依存し、全leaf教師truth、現forward、全deep、IID、同時間の一般棋力、公平性の正式認定は不足する。2familyのWDL不変は効果なしの一般証明でもない。

次の最大1方向は、clip/tanhの少数arena反復より、rootmean蒸留値をleafへ使う意味をhistory・完成horizonと結び付けた固定入力診断を費用付きで優先すること。Dの極値同値解消だけではNNUE未見棋力を説明できず、今回Dの値/Action変化もWDL利益につながっていない。新科学/学習/条件を自動追加せず、既Dclip対照と今回結果を別に保持する。

保存正本は `research-data/ai-sigma/frame20-distance-arena-independent/{result,replay,process,admission,stopped-inputs,scientific-stop,Git-byte-receipt}.json`。科学源停止とGit byte復元/Beads close・backupは別receiptで確認する。親最高棋力goalは未達のまま。
