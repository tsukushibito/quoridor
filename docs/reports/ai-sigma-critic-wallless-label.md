# SIGMA-WALLLESS-LABEL-INDEPENDENT / quoridor-4lc.143

142の固定2入力の有限ラベルを支持する。保存証明木の全状態・区間をbrowser mainで独立検算し、別のbounded solverで各状態を1回再計算すると全root区間が一致した。この2状態のAI選択を勝ち手/負け手へ採点できる。合法性・depth6認証だけで小改修感度や一般棋力を保証しない。144のstatic開始gateではなく、heavy停止と有限支持は最終本文より先に統括へ報告済み。NN/モデル/AIWorker/新game/build/取得0、formalNI/Sigma/政策採用/actual_go未認定。

契約/選定Git b564b3f1cc9b1c0e230e4bf5834a0df9884eea23、親枠9。本人19:45:29UTC受領、ready/show goal+self・pause無し・本人割当確認後143のみclaimし実開始を報告した。早側処理20:15/newrun20:10/提出20:25UTC。原成果・モデル・RuleA・default Git index・他担当scopeはreadonly。CPU0静的単logical/180秒/896MiB guard、Chrome NN0 CPU2単logical/120秒・単job90秒/5.5GiB guardを継承した。

原登録8466495、科学3866532、data9143e12、handoff63d46ddを区別。handoff9b091fc47bfe95e93fd860ea44d6886f1a35d4cb60ababcee5950f7a9c34ede2、science-stop3dc910cd05a94ca4fc07c81920bba246ccf0ee224e4bc5d08197730dc7a03a31、final-source-stop071a90d7206ca4385aa708679e6c6e1344cf20a48f0a956673eda3745f160a70、archive5aa75aeb9c640d0dceb91de026da08535face3086a23287adc8b182f8d570b60を現物照合し、必要canonicalはhandoff Git blob一致を確認した。必要generation2・label2・停止receiptだけstream読取し、必要member SHA/size一致。統括の55member復元確認を独立科学検算とはしていない。原archive全copy/全展開0。

独立checkerは元142のcheckerを呼び出し・コピーしていない。原compact proofを親indexの前向き順序で全状態へ復元し、実legal action object/順序・手番・goal/draw・depth未知・全合法子の被覆を検査。その後逆順で区間max/minを独自再集約し、全nodeの保存区間と比較した。別solverは明示stackを使った反復DFSと帰り側区間計算で、depth6/node20000/watchdog20秒を固定。成功検索の反復0、cap増加・入力追加0。

| 固定入力 | prefix/side | pawns P1 / P2 | node | terminal | depth未知葉 | 再計算ms | root区間（実legal順） |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| P1-race | 32 / P1 | [4,6] / [3,3] | 2352 | 90 | 1593 | 74.200 | [1,1],[-1,-1],[1,1],[1,1] |
| P2-corridor | 33 / P2 | [4,5] / [4,2] | 3632 | 112 | 2527 | 87.600 | [-1,-1],[1,1],[1,1],[1,1] |

保存walkと独立solverはnode/terminal/depth未知件数も一致。最大探索depth6、node/time cap欠測placeholder0、即goal0、真draw0。未知葉は全て[-1,1]を維持し、0/draw/lossで補完しない。それでもminimax boundsの伝播により全4root区間はsingletonに収束し、両入力とも勝ち手3/負け手1、根全体[1,1]を再算した。未知葉が残ることと根区間が認証できることは両立する。

合法prefixを独自ループで初期Stateからreplayし、壁20消費後の両残数0/0、手番、pawn位置、key/全history、全648featuresを確認した。seed41001/41002・attempt0の壁shuffleと事前pawn scriptにも一致し、adopted前に不合法/terminalを通過していない。保存全attemptは各1、生成はAIなしという元source/receiptに対応する。原ラベル番号は実legal actionのpolicy-head indexであり、Rustの209 Action空間と同一番号ではない。

| 実legal object（方向） | label index | P1 Rust Action / payoff | P2 Rust Action / payoff |
| --- | ---: | --- | --- |
| pawn [0,1] | 0 | 67 / +1 | 31 / -1 |
| pawn [0,-1] | 1 | 49 / -1 | 13 / +1 |
| pawn [-1,0] | 2 | 57 / +1 | 21 / +1 |
| pawn [1,0] | 3 | 59 / +1 | 23 / +1 |

独自index式と元actionToIndex(…,9)を実Action objectに照合した。payoffは各root手番側の視点。P2だからラベル番号をさらにcanonical model frameへ反転して採点するのではなく、実board上のobject対応で採点する。小mockで自側max/相手min、未知がdrawにならないこと、両視点のgoal符号、goalがdrawより先、真draw0、実RuleA近goal合法手とAction index対応を確認した。

全合法判定・proof/minimax・時刻watchdogはChromium main内。Nodeは起動/外側監視/回収/終了後保存で、JSON textをbrowser内parseした。AIWorkerは禁止stub、Model/NNは0。game/context/自己checkerをinline供給し、document.scriptsのbrowser echo digestと供給source hash一致を照合。独立fetchではない。共有RuleA・特徴/Action実装を使うため、その共通バグを排除する独立ルール証明ではなく、固定trueState/historyに対する有限ラベル認証である。一般wall中盤・全deepモデル・長期棋力へ外挿しない。

尺度としては旧即goal/priorだけの全pass例より非自明な手の区別を持つ。ただし両状態は両壁0の固定race/corridorで、4手中3手が勝ちなのでAI条件が全てpassする余地がある。root1とK32の強い予算差を区別できても小改修感度は未認定。最大1次案として、既144の事前固定6要求を感度校正に使い、全6payoffを残して事前出口へ従う案を支持する。全passならこの尺度の同形式反復を終了し、通常だけ負・root1だけ負・通常がroot1より悪い逆方向は局所の修復判断へ返す。因子原因や係数採用を自動認定せず、新実行をこの提案から開始しない。

初回p143-label-r1は再利用runnerでadmission呼出しの接続が抜け、Node入口がadmissionファイル無しを検出して停止した。Node1/Chrome0/solver0、Git e70a71b・失敗log・sourcehash・commandを保持した。修正885eb8eはadmitとlaunch_if_allowedを子spawn前の必須分岐に接続。false/unknown/readerror/deadlineはspawn0。r2は直前admission true、142runtime71と復元helper7を分けて現在不在、最終source hash、外heavy0、MemAvailable headroom、自己保存/回収を確認した。

r2の環境Git文字列candidate-r2はGit IDではない。原値を変更せず欠陥として保持し、実際の全launch source hash→885eb8e Git blob→終了後現物一致で測定版をbindした。科学resultを失敗へ付替えず、版ラベルの不備を隠していない。原142のNN前mock失敗も今回結果へ混ぜない。

Chromeの2solver完遂後、inner forced/controlled・waited、outer sole-explicit-root boundary・owned ledger・registered_live/unknown_adopted0、monitor全read callback待ち/timer停止、main_active false/timer-message0、NN/Model/AIWorker0を別receiptで確認した。heavy-stopの速報はouter32identity、最終はstatic/初回・innerのみ短child3も加えた46identity現在不在で別分母。最初の自己closure43→46修正はsource監査追加でheavy終了・科学結果は不変。現在不在は自然終了/全期間/全host保証ではない。最終closure helperはsnapshot時稼働を明示し、handoffで終了後不在を再確認する。

管理heavy合計8.559496秒/120秒（Chrome未開始r1も含む）、CPU2、最大観測currentRSS1,344,892,928B/5.5GiB guard、全観測TIDは指定CPU。管理static0.836244秒/180秒、CPU0、各60秒以内。161.8msは独立solver部分wallで全job/team費用ではない。短いmanagement/Git/復元/保存commandの全期間PID/RSS・瞬間peakは欠測として残す。

初期critic artifact allocated79,884,288B＋forecast8MiBはcombined112MiB内、最終自己allocated1,335,296B（新scope7MiB guard内）とGit/report forecast2MiBを保守合算しても既guard内。旧未知保持減額0・親追加予約0・原正本削除0。自己36member archiveに必要入力/proof・全attempt/停止receiptを保存しstream復元一致を確認。本文/source/Git/最終handoff/backupはheavy停止速報に後続する。受入れcoordinator、goal/他者close0。

再現入口は固定[config](../../research-data/ai-sigma/143-wallless-label-independent/config.json)を用いた `python3 tools/ai-sigma-wallless-label-independent/runner.py --config <config> node <entry.cjs> <newrun>`。旧期限や成功2行を再起動する許可ではなく、新配分内でのみ使う。[独立結果](../../research-data/ai-sigma/143-wallless-label-independent/independent-results.json)・[入力/hash参照](../../research-data/ai-sigma/143-wallless-label-independent/input-and-binding.json)・[heavy先報根拠](../../research-data/ai-sigma/143-wallless-label-independent/heavy-stop.json)・[最終停止](../../research-data/ai-sigma/143-wallless-label-independent/runtime-source-stopped-before-report.json)・[全失敗](../../research-data/ai-sigma/143-wallless-label-independent/failures.json)・[復元manifest](../../research-data/ai-sigma/143-wallless-label-independent/archive-manifest.json)。
