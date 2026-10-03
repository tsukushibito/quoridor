# 枠10：baseline対Sigmaのgapを測る入力分布

quoridor-4lc.148の結論は、AI結果を使わない合法prefixを4/5/12/13ply各8、計32局面として固定し、各局面で候補色を交換する64局の同wall比較を選ぶこと。coordinatorは速報を結果前Git `9bafd9ef12298d2b587599f12ea02b4ba5f21123` に採択し149へ配送した。今回148では生成・NN・Chrome・対局・buildを実施していない。C145案やsamecompletedの自動追加は保留され、現Q0/C1.5/finish/order/f32/modelと固定Sigmaを保持する。重大な異論はない。

最初に判別する不確実性は、既敗戦線や狭いoracleを選ばずに作った新分布で、現baselineの対Sigma scoreがどちらへ、どの程度ずれるかである。129と144のroot1全passは狭い尺度の感度不足、119の固定8prefix・W4L12はその既入力条件の弱さである。どちらも新分布の棋力差を決めない。局所C/FPU調査よりこの問いを先にする。旧119の結果を新標本へ合算しない。

## 最大1案と結果前の固定

生成器はbrowser mainのRuleA initial Stateから実合法手を適用する。両class非空ならpawn/wallを1/2で選び、そのclassの既合法順から一様indexを取る。片class空なら非空だけを使い、class乱数は消費しない。xorshift32 unsignedのclass/index乱数消費は既119に合わせる。これはclass内の一様選択であり全合法Actionの一様選択ではない。壁候補が多い盤面でもpawnが極端に少なくなる分布を避けるための明示した人工分布である。

master61041からdomainを分けたSHA256で各slotの最大8attempt seedを固定した。seed表は [recommended-seeds.json](../../research-data/ai-sigma/frame10-gap-sampling/recommended-seeds.json)、SHA `a82f2d01875180aa6a4a53be6e62d1ae11b9ab01ef2b3d37e5a1b40a7ede5c04`。8blockで4層を巡回し、blockごと候補色順を交互にする。各層で色1先・色2先が4回ずつとなる。固定searchseed1979を両AIへ適用し、生成seedと探索seedを分ける。

各slotは最初の合法非終端・非旧signature状態を採用する。途中又はtargetでのterminal、no-legal、不合法生成、旧119との完全signature一致を拒否し、全attempt/history/理由を保存する。8attempt不成立は未生成2gameとして残し補充しない。旧119全8をWDLによらず一律除外し、既敗戦prefixを選び込まない。新集合内の重複・同状態合流は保持してflagし、再生成で都合よく多様性を増やさない。NN/value/prior/pathbalance/旧勝敗による選別、盤面・壁数・手番の直接変更はしない。生成・全32slotの条件をAI load前に固定する。

採択補足のsignatureはtrueState key＋キー順正規化history_counts＋sideのcanonical JSONである。148の静的結果に載せた旧ply/position keyは参照inventoryだけで、完全signatureの構成・照合を済ませたものではない。履歴によるrepetition状態を落とさない採択定義を優先する。149が元historyから生成する責務であり、148は新replayや原棋譜全展開を行っていない。

整数だけのNN0 probeでは、連番61001..61032の最初class乱数が32/32wallになった。固定hash由来表の最初attemptはpawn18/wall14だった。hash表を観測balanceに合わせて再選定していない。このprobeは初回乱数の偏りを示すだけで、合法生成後の分布、暗号学的独立性、旧119の全生成偏りを証明しない。

## 出口と反証

各prefixで候補の色1/色2 scoreをW1/D.5/L0とし、Xiを両scoreの平均にする。主平均は4層各8pairの等重みである。先後交換の2gameは独立64標本と扱わず、32pairを単位にする。両試合で同じ盤面側winnerならXi=.5として保持し、候補両色勝・両色敗・引分と区別する。局面優位による尺度の飽和は捨てず、その割合を報告する。

全予定64gameの分母を保つ。参照fault・共有不明・未開始・未完了・未生成はscore区間[0,1]で、全meanの識別区間を[sum lower/64, sum upper/64]とする。片色欠測のpairは既知score/2から(既知score+1)/2、両色欠測は[0,1]。候補責任faultlossを0とした運用scoreを分け、純粋な手品質では非終端faultを未知とする。complete-only平均はmと選別限界を併記する補助で、主分母へ置換しない。

独立bounded pairという追加仮定の両側95%Hoeffding幅はsqrt(log40/(2×32))=.2400807。未知mean識別区間の両端へこの幅を加え[0,1]へclipする参考区間を採択した。固定PRNG・生成条件・重複・共有状態・時間driftについて独立性と被覆を立証していない。64gameで大きい差を探索する設計で、.05程度の正式NIを判定する精度ではない。合法性・層・色の均等配分は、難易度均衡、人間対局への代表性、IID/holdoutを保証しない。

参考区間を含め.5より低い方向なら、この生成分布とbrowser条件での不足を支持し、改善又は別事前登録分布での検証を優先する。逆方向なら現baselineを保持し別分布へ検証を進める。どちらも政策採用・Sigma同等・119敗因の認定ではない。.5を跨ぐ、層で混在する、全Xi=.5又は同盤面側winnerが多い場合は差又は感度が未確定で、現政策を保持する。失敗・未完了で区間が広ければ基盤不成立と品質差を分ける。途中結果を見た標本追加、好成績subset、停止順変更は行わない。

同wall500ms/cutoff402/adopt411・同modelが主比較である。最初の同入力はkey/history/side/featuresとNN出力、完成・採用量を対応させ、後続の異なる状態のNN総量比を同仕事量や因果と呼ばない。startup、API開始、完了NN、採用CP NN、terminal-noNN、backup/completed、discard、自待ち、ACK wall、cleanup残処理は別分母にする。同completedは量と政策を調べる将来の競合手段として保持するが、同NN仕事量/同CPUではなく、今回の長期勝敗の問いを置換せず自動追加しない。

## 費用・採否・実施範囲

RuleAのglobal200plyをprefix込みとすると、新手最大12,256、500ms思考の名目上限6,128秒。初期案32job×240秒=7,680秒は見積りであり、採択実予算ではない。coordinator補足はjob最大600秒・生成込みheavy総7,200秒で、名目思考との差は1,072秒。準備・NN初期化・回収・長いAPI awaitを含む全完了保証はない。親の絶対終了04:15:21UTCと149自身の早側期限で止め、未完了と層別欠測を残す。巡回順は期限時の層偏りを減らすが解消を保証しない。writerは後続experiment149、必要保存の独立確認はcritic、採択と受入れはcoordinator。期待runtimeは新実行許可ではない。

148受領00:28:22.929797UTC、ready/show goal+self・本人割当・pauseなし確認後本人claim。開始報告と10分以内の設計速報は既App Server経路にaccepted steer配送済み（科学受入れとは別）。処理期限00:48:22.929797、提出00:53:22.929797を維持する。今回CPU0静的checker1回だけ、wall .021902秒、child CPU .015856秒、wait peak RSS15,294,464B、guard448MiB。seed256個/32slot/層/色順/費用/欠測算術のfixtureを確認し成功、NN/Chrome/game/build/新合法状態生成0。前後source/input SHA一致。子の自然終了をowned waitで観測し、現在不在と全host/全期間保証を区別した。

旧保守保持11,560,048Bを減額せず新2MiB forecastを足すと13,657,200Bでcombined14MiB内。raw全copy・原archive展開・親予約追加0。管理通信/Beads/Gitの全費用をchecker時間へ含めていない。元成果と旧145提案は変更しない。静的結果・受領/採択binding・停止と最小Git復元は自己dataに保存し、backup/report後にcoordinator受入れへ渡す。今回棋力結果は未実施である。
