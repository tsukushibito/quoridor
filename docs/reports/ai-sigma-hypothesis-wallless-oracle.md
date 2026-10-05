# SIGMA-BOUNDED-WALLLESS-ORACLE / quoridor-4lc.142

**両壁0の合法2局面で、即goalを含まない複数手先の勝ち手と負け手を有限認証できた。AIの改修感度・棋力改善は未測定。** 契約1・親枠9、担当hypothesis。受領/claim開始19:13:05.626296UTC、処理19:53:05.626296／新heavy19:48:05.626296／提出20:08:05.626296の早側を維持。開始RPCとheavy停止RPCはacceptedで、科学的受入れではない。

登録Git8466495、mock訂正版・科学実行Git3866532。preregisterは科学生成前に固定し、幾何規則・seed41001/41002・attempt上限4・prefix上限160・depth6・適用node20000/root込み・watchdog20秒を変更していない。initial9盤/各10壁から全手RuleA合法確認で壁20枚を消費し、登録pawn列を適用した。両caseはattempt0で適合、実attempt2、未使用attempt枠6。終端/不適合の補充やAI/model/priorによる選別は0。生成・認証・証明木チェックはChromium main、Nodeは起動・監視・保存・回収のみ。

| 入力 | 合法prefix／手番／pawn位置 | 全合法pawn Actionとroot視点の認証payoff | 適用node／終端win,loss,draw | depth上限unknown葉 |
| --- | --- | --- | --- | --- |
| P1-race | 32ply／P1／[4,6],[3,3] | raw136 0:+1、1:−1、2:+1、3:+1 | 2352／43,47,0 | 1593 |
| P2-corridor | 33ply／P2／[4,5],[4,2] | raw136 0:−1、1:+1、2:+1、3:+1 | 3632／64,48,0 | 2527 |

raw136のpawn順は0:[0,+1],1:[0,−1],2:[−1,0],3:[+1,0]。両入力とも両player壁remaining0、非終端、root合法4、即goal0。全8root Actionはsingleton区間として認証され、root minimaxは両方[1,1]。depth上限の葉は[-1,1]のまま残す。自手番max・相手手番minを両端に適用するとrootの強制勝敗が確定するため、未知葉が存在してもこの認証と矛盾しない。全深部状態が解決したという主張ではない。

rootplayer視点を固定し、実goalを優先、true RuleA drawのみ0。jump/diagonal/合法集合/履歴による反復手禁止を実Stateで扱い、cache/pruningは使わない。root込み適用nodeと未適用unknown placeholderを区別する。両caseはnode/time cap未到達、depth6で停止。browser内認証処理約98.60/61.20msはこの有限処理だけの時間で、CPUや純NN費用ではない。

各caseの全proof木をparent/Action/side/interval/reason/appliedとして保存した。別の証明木walkがlegal集合・順・terminal・depth unknown・交互max/min・node件数を再集約し、全2352/3632適用nodeと全8root Actionの一致を確認した。同担当の別集約算法で、独立役の受入れや独立RuleA実装ではない。共有RuleA自体の誤りは除外できない。全prefix/key/history/side/盤面/648featurebitsを保存し、特徴生成はモデルloadではない。

mockは人工terminal/max/min/draw、depth/node/time unknown伝播、cap1、terminal優先、合法prefixからのjump/diagonal/near-goalを確認した。p142-oracle-r1は対角mockの壁を早く置いたためinvalid-prefixでexit1、科学case生成0。履歴順だけを訂正し旧失敗を保持、p142-oracle-r2でmockおよび固定2caseが成立した。初回科学成功を反復していない。合法な科学入力を人工盤面で置き換えず、depth2旧129の成功へ遡及しない。

起動必須branchはadmission false/unknown/readerror/ownership不足/期限でspawn0のmockを通した。各実起動直前に.140最終stop SHA16a3f57c2d38ebe046d364145ed292355ad352e164494791ba83d84db9e0c136、117同boot identityの現在不在、external heavy空、MemAvailableとcombined保存forecastを確認した。pauseは既monitorがChrome起動前に確認、141の裁定待ちをgateにしなかった。shared host/browser設定・依存・原sourceの編集0。

4監視jobはstatic2＋browser2、browser累計12.546146秒、static監視累計.137964秒。r1失敗を含め最大current runner+owned RSS1,280,319,488B、観測TID affinityはstatic[0]/browser[2]で各1logical、guard違反0。Nodeheap192MiB、Chrome RAM6GiB/guard5.5GiB、Go/NodeへのAS制限0。Chrome/tempを含む観測自域peak2,121,728B。旧保守8,908,800Bを減額せず、自域保持1,519,616B＋新Git内容の保守見積218,429B＋残文書131,072Bを加えたcombined forecast10,777,917Bは14MiB未満、追加予約0。保持・未使用16MiB予約・過去peakを区別し、全owner/全host12GiBの再監査をしたとは言わない。

自己71identityの現在不在、outer ownedwait remaining/unknown0、browser/Node停止、monitor callback停止、oracle active/timer0を本文前に保存・先報した。boundedStopのforced/outerwaitと現在不在を自然終了や全期間保証へ付け替えない。最初の短いread/claim/生成/Git/report管理commandの全CPU/RSS・厳密総wall、瞬間peak、全host期間保証は欠測。monitorの40ms標本内での上限確認である。必要RuleA/context/checkerのinline提供byte hash、browser document.scripts echo hash、現物hashは一致。独立network fetchdigestではない。科学source前後hashも一致した。停止先報後のpack/report helper作成は科学source再開ではなく、別の最終保存記録に区別する。

次は最大1案のみ：[next-proposal.json](../../research-data/ai-sigma/142-wallless-oracle/next-proposal.json)。別配分で全proofの独立NN0確認後、固定2入力のcandidate通常/root1/固定Sigmaの6要求を一度比較し、certified payoffを品質出口とする。root1が負け通常が勝つなら限定深部回帰尺度として保持、全条件が勝ちなら当尺度枝を終了し自動拡大しない。一般中盤・IID・均衡・holdoutではなく、prior-onlyで十分という可能性はまだ残る。現Q0/C1.5を維持、新NN/AIWorker/game/係数採用/正式NI/Sigma認定は今回0。

根拠は[finite-results.json](../../research-data/ai-sigma/142-wallless-oracle/finite-results.json)、[archive-manifest.json](../../research-data/ai-sigma/142-wallless-oracle/archive-manifest.json)、[resource-and-binding.json](../../research-data/ai-sigma/142-wallless-oracle/resource-and-binding.json)、[科学停止記録](../../research-data/ai-sigma/142-wallless-oracle/runtime-source-stopped-before-report.json)。runs.tar.gzは全科学attempt/生成/証明/失敗/mock/必要command/PID/starttick/admission/resource/回収を含む55member、SHA-size stream復元確認済。原archive全展開・共有rawコピー0。受入れはcoordinator、goal/他者close0。

再現（新配分がある場合だけ）：登録configを新run ID・現在配分期限に結び付け、`timeout 90s taskset -c 2 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 tools/ai-sigma-wallless-oracle/runner.py --config research-data/ai-sigma/142-wallless-oracle/oracle-config.json node --max-old-space-size=192 /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-wallless-oracle/entry.cjs <newrun>`。保存済run IDや期限を上書きしない。管理/必要記録の欠測はhandoffにも保持する。
