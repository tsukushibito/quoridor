# 固定Sigma-WebをRust/Wasmへ移す際の対応と最小検査

quoridor-4lc.150 / 契約2・枠10 / 2026-10-03。固定Sigma-Webの忠実な基準版を先に作る方向を支持する。候補C1.5/Q0の棋力因果を一つずつ解くことは移植の開始条件ではない。最大1案は、固定Webの同K遷移をprivate Rust/Wasmで再現し、人工評価・固定5入力で最初の機構差を特定した後、新8pair/16gameの同wall結果を別に測る、という151の配分である。今回の150は静的な仕様裁定であり、151の実装成功・NN一致・棋力同等を検証したものではない。

## 正本と移植範囲

Sigma-Web Git751186344fc52ad0c29bc65922e62c6fa915f006の保存 `mcts_worker.original.js` を読んだ。全ファイルSHAf2de9444e8960ca14d4d4acb5dd319e3f0a6a743c39b4032dce32068ebcfe8faは130保存bindingと一致。`MCTSNode`、`backup`、`selectLeaf`、`pickFromVisits`の4本文は、現在の移入reference-coreと独立に抽出してbytes一致を確認した。学習Pythonの既定値や「Sigmaならこうするはず」で正本を置換しない。reference-control/runMCTS/NN/時計adapterには後述の変更があり、4本文一致を全Web挙動一致にしない。

| 対象 | 揃える実仕様 | 見つける最小の不足 |
| --- | --- | --- |
| select | C=1、sqrt(parent.visitCount)、U=C×prior×sqrtN/(1+childN)、strict `>` | N+1、C1.5、epsilon tieやseed tie、候補Action昇順の残存 |
| Q/FPU | node手番側mean=valueSum/visitCount、N0は0。訪問childは-childmean。未訪問はparentmean−.2√(訪問済child.basePrior和) | root初NN値・祖先値を欠くedge平均代用、未訪問Q0、fpuReduction0をQ0と誤認、basePriorを訪問回数で重み付け |
| backup | leaf手番valueをleafからrootへ符号交替、各nodeのNとvalueSumを一度ずつ更新 | root視点を二重反転、depth偶奇/terminal値、非終端pseudo-leaf/capで分母変更 |
| 根とloop | 初根expand/backupはloop外。completed KならrootN K、edge和K−1、loop K−1 | JS numSims=Kを渡してrootN K+1、terminal backupをNN回数へ加算、root-only未公開 |
| finish | temp0はvisitCount最大をstrict `>`で先頭保持。K1の全childN0は先頭合法手 | 最大prior fallback、tie random、訪問分布sortで元順を失う |
| 合法順 | pawnは[0,1],[0,-1],[-1,0],[1,0],[-1,1],[1,1],[-1,-1],[1,-1]順。次にwallはy外/x内、各cellでH→V | 全H後全V、Rust209順、同legal集合だけで順一致と誤認 |
| Action/特徴 | Web136は方向8＋H64＋V64。Rust209は着地81＋H64＋V64。jump着地は実state.nextから求める。P2featuresと136policy垂直写像を一度ずつ | direction IDと着地IDの同一視、jumpを単純dx/dyだけで計算、P2二重flip、209へ136 permutation適用 |
| 数値 | NN137はf32の値。JS Numberはその値をf64で扱い、legal logitsだけmax減算→exp→元順sum→除算。prior/Q/score/ledgerもf64 | f32 softmax/累積、全136softmax後mask、並列和・再結合・無説明の丸め |
| 状態 | side/depth/pawns/wall残数/anchors/historyを保存。goal優先、depth200又は合法なしdraw | featureだけ同じで履歴差を落とす、第三反復を単純drawにする、NN値でterminalを判定 |
| actual request/取消 | root/loop/K・numSims/capsを実receiptで確認。checkpointは完成backup後だけ。確定後新NNなし、旧返却discard、自己旧zero、相手t0は旧ACK非前提 | configだけ変更、旧node512/depth24到達を見落とす、stale返却を新木へ混ぜる、receiver再選択 |

訪問済basePrior和は「N>0のchild各一回」の和であり、priorの訪問重み平均ではない。元順softmaxとそのpriorをそのまま持つ。rootの初NN値をmean ledgerへ入れることは140のtrue-mean機構と関係するが、140のf32/C1.5等を含む候補実装を係数だけ変えて固定Web再現と呼ばない。

JS Numberをf64へ対応させてもJS Math.exp/sqrtとRust/Wasmの超越関数がbit一致するとは限らない。compiler flags/fast-math/和の順序と、ABIでpriorをf32へ戻していないかも示す。値の閾値は `abs(a-b) <= 1e-4 + 1e-4*abs(reference)` を固定し、features648 bits/Action/historyの離散一致とは分ける。f32 NN出力はfinite・strict[-1,1]・同モデル/providerで照合するが、同じNN出力だけで探索演算の一致を認定しない。

## 元Webと研究運用の区別

原WebのrunMCTSは初根を無条件にexpandしてから取消を調べ、staleならnullを返す。loopのterminalではwinnerありをleaf手番−1、drawを0としてNNを呼ばずbackupする。合法な非終端rootから到達した勝者terminalではwinnerは直前手番なので、研究terminalResultのwinner対leaf手番値と一致する。人工的な「既勝者が手番」という到達不能状態にまでこの等価を広げない。

研究参照は、terminal rootをNN0で短絡し、完成root/各loopのcheckpointを保持し、generation/control guard・yield/setTimeout・clock spanを追加する。原Webはprogressを概ね40回に抑える。研究運用のterminal-root受付・completedCP保持・新NN開始cutoff・SAB採用をprivate portも同じadapter条件で使うことを支持するが、原Webの取消API・タイミングそのものを完全再現したとは呼ばない。非終端sameKの木遷移と、API受付/時計/取消を別に検査する。

原WebのNN例外/未sessionはランダムrollout fallbackに入る。今回の固定モデル比較では既strictfault分類を保持し、このfallbackを黙って混ぜない。元WebのmodelFullCanonicalはモデルpathの文字列で決まるが、研究では固定best.onnxのfull-canonical bindingを明示する。P2の値は既に手番側なので、valueまで自動反転しない。これらの範囲差は移植失敗や元棋力lossではなく、今回の固定比較契約の違いである。

RuleAでは次pawn状態のposition_history countが既2ならその手を除外する。depth/side/wall anchorsを含むキーを生成し、履歴Mapをcloneして進める。第三反復を新drawへ変更しない。キャッシュの合法順やstate lazy生成が同じ履歴へ作用することを確認する。共有RuleAを使う検査の独立性限界は残す。

## AI前の最小人工評価

151は人工value/prior streamを与え、以下をJS参照とprivate Rustで比較できる。150で行ったのは期待値の独自静的算術までであり、JS/Wasmを実行した人工conformance成功ではない。

1. 根NNだけ・K1。最大priorを第2子に置き、全edgeN0、rootN1/loop0で第1合法Actionを返すことを確認する。K2で最初の選択を追加し、root外backupのoff-by-oneを検出する。
2. strict first tie。equal score/equal visitsと、ほんの少し第2子が大きいケースを分け、epsilon tieやrandom seedを検出する。元壁順の先頭209 IDは81,145,82,146であり昇順ではない。
3. true node meanとdepth1/2 backup。初根value=.6、depth1 leaf−.4、depth2 leaf+.8のledgerはroot1.8/N3、子−1.2/N2、孫+.8/N1。rootmean=.6、訪問済basePrior和.25ならFPU=.5。edge平均やroot最新NN代用はこのledgerで判別する。複数訪問でもbasePriorは一回、現在priorとbasePriorが違う人工例でも元式を確認する。
4. 近goalの合法leaf・draw200・合法なし・repetition除外。goalとdrawが同時ならgoal優先、同terminalの再選択もNN0でN/valueが増える。terminalroot受付は研究wrapperのNN0短絡として別件数にする。
5. P2/jump/壁順/取消境界。136 permutationのinvolution、実着地209、features648、history/sideを確認。NN返却直前/直後の取消で旧完成CPは保持し、未完成backupを公開せず、旧結果を新treeへ使用しない。受信側の採用Action再選択0。

全探索kernelの再証明を開始gateにする必要はない。これらは安い人工境界と5入力で、実装を揃えたはずなのに不足が残る部分を直接判別する。

## 固定5入力のsameK

入力はinitial-p1/asym-hv-p2/straight-jump-p2と、149保存の未開始slot13/14（frame10-prefix-13/14、ply5/13、両P2）に固定した。150は保存5stateの特徴形式・648値finite・feature bytes SHAを静的確認し、必要5のみ自域保存した。原149の40未開始を救済する対局や正式holdoutではない。149入力全コピー/再生成/再NN0。履歴合法性の新browser replayは今回150では未実行で、151側の必要条件として残す。

両者K32/root込みの5×2検索で、各CPの選択path、NN request stateのkey/history/side/全features、NN logits/value、action別prior、N/valueSum/mean、訪問分布、finish Actionを対応させる。根以外もそのK32に実際に出たrequestだけを比較し、全旧deepを入口にしない。raw numSimsとcompletedKを同じ数字で渡さず、rootN32/edge31/loop31を確認する。terminalがあれば `NN + terminal-noNN backup = completed backup` の対応を別に示す。startup6は手NNと別。

数値tol通過とpath/訪問/Action一致は別判定である。最初の差は、入力/history→NN features/output→元順/softmax/prior→true mean/visitedPrior/score→選択→backup→finish→配送の順で位置を示す。scoreの上位2子の差とf64値も残す。超越関数の微小差が順位を変えた場合、NN不一致や棋力lossへ変換せず「数値差が離散選択に影響」と報告する。tie閾値や丸めを結果後に追加して一致に救済しない。不一致を修正する新runは旧失敗版/attemptと区別し、successful行を置換しない。

必要最小の原対計測対応で、trace/CP読取が政策を変えないことを確認する。132のK8 parity4・root4/共有nonroot9・未共有19/engineは有限根拠で、全deep/terminal枝/計測費用の校正ではなかった。140の280実selectはtrue-mean ledgerの必要性を支える有限保存根拠だが、固定Web全同一の証明ではない。140保存の必要7library actual hash/patch/currentmtimeをprivate build bindingに使い、Git-only再構成や全期間依存read auditを確保したと偽らない。新全体build/全史auditを150のgateにしない。

## 最後の同wall16gameと独立見解

151のAI前固定master74021・ply4/5/12/13各2・色交換16game・全attempt/全分母/両fault品質未知/巡回順を探索的確認として支持する。sameK機構一致後でもRustとJSの入力準備/探索速度、同wall内completed量、cancel/残NN/own_wait/timer tailが違えば実ActionとWDLは変わる。同policyの機構再現から同資源棋力を自動認定せず、初根同入力の量と全手の量分布を別分母で残す。API awaitやACK wallはkernel CPUではない。

重大な偏りは、合法ランダムprefixが均衡/通常対局/IID/代表性を保証しないことと、固定同モデル/同seedで盤面側優位により両色同側winnerが続く可能性である。色交換の8pairを16独立位置にせず、両色同側winnerと両色候補勝/負を分ける。8独立bounded pairを仮定しても両側95%Hoeffding幅は約±.4802と粗いので、NIや細かなgap推定には使えない。新入力をpriorや成績で選別するbalance条件は追加しない。全同結果は有限同wall差未検出まで。

忠実移植優先に、今回の着手を止める重大な反対はない。同じ探索機構を基準にすれば、残った差を実装・数値・速度・時計へ絞りやすく、各因子の勝率実験を先に重ねるより直接的である。ただし移植が本来の速度優位を失う可能性やf64/状態cloneの費用は最後の実測で判断する。完全軌跡一致を小さい数値差の隠蔽で買わず、差の最初の位置を残す。機構が揃っただけ、compileしただけ、16局完了しただけではSigma到達にしない。比較の実行・修正と採否は151/coordinatorにあり、150が実装を重複編集したり新承認gateを設けたりしない。

## 記録と停止

01:17:30UTC受領、ready/show goal+self/pauseなし・本人割当後01:17:42claim。開始と10分以内の具体速報をcoordinatorへ送信済み、通信受理と科学成功は別。早側処理01:37:30/newcommand01:34:30/提出01:47:30、親04:15:21を維持。自域checker r1はgoldenのraw_features_float32形式を149のfeatures_bitsにも誤適用してKeyErrorとなった。失敗版Git e0d085eとrun/sourcehash/logを保存し、r2は各保存形式を読み分けて成功。これはcheckerのschema失敗でNN不一致/移植失敗/棋力negativeではない。

新NN/Chrome/model-load/AIWorker/build/game/GPU/取得/委譲0、原130/132/140/149/151/source/kernel/model/role/defaultindex変更0。CPU0単1/RAM448MiB guard/各60秒/累計180秒、旧保守＋new2MiBは既112MiB内、追加予約・未知旧減額0。必要command/入力Git/hash・人工期待値・source前後hash/停止/復元は `research-data/ai-sigma/150-sigma-web-port-conformance/`。source/子停止→Git最小復元→backup/report後にcoordinator受入れ待ちとする。現在identity不在を自然終了/全期間保証へ広げない。formalNI/Sigma/actualgo/政策採用/goal他者close0。
