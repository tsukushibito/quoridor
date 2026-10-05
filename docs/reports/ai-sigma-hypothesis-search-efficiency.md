# 凍結評価器の探索効率・最小選定 / quoridor-4lc.233

frame18、hypothesis単独の静的選定。受付2026-10-04 13:54:42 UTC、claim・実静的開始13:56:33 UTC。旧231は有限受入れに基づき本人close・backup済み。モデル、Torch import、NN、compile、対局、GPU、科学CPUjobはいずれも0。232の私有実装はreadonlyであり、本稿は実装・性能・棋力の成功報告ではない。

## 選ぶ一つ

**前の完成depthのroot最善手を、次depthで最初に探索するordering**を主案にする。190のprobeは完成depthとroot最善Actionを既に保持するが、次depthでは元の合法手順から再開する。保存済みroot Actionを先頭へ移し、残りは元の順序を保つだけなら、追加policy推論・TT・可変盤面のmake/unmakeを導入せず、良いalphaを早く得る仮説を小さく判別できる。今回232は新しいscaled-f32評価器の意味接続と固定node診断を優先しているので、本案の実装を入口条件にしない。

実装対象は同じroot・history・side・ply・generation・RuleA版で完成した前depthのbestのみ。キャッシュされた合法配列を直接変更せず、新しい順序配列に一度だけ移す。Actionの既存型・座標を比較し、orderingのために全pawn ActionをrustActionへ変換しない。contextのpawn変換はnextを呼ぶため、余分なclone/path計算を作り得る。前depthのbestが現在の合法集合に無ければ元順序へ戻す。未完成depthからのPV・bestは採用にも次のorderingにも使わない。全PV木の保存は今回の主案に含めない。

これは探索順の変更で、全合法childを保持する。低prior手の除外、top-k、policy枝刈りは行わない。234の選定前懸念を反映し、将来policyを比較する場合もまずordering-onlyで追加計算・輸送費を含める。現在のQF1はvalue-onlyであり、別policy head/modelを足す費用と意味差から、policyは本案より後に置く。

## 値、Action、打切りを分ける

完成depthの全探索では同評価器・terminal・合法集合のroot minimax値が対応することを必要品質とする。しかし等値の複数Actionのうち先に訪れた手は変わり得る。元probeはstrict >でbestを更新し、狭い窓のfail-soft応答が等値でもexact値とは限らない。したがって == の応答だけで元の最小Actionへ戻す修正は安全な同値証明にならない。

次の結果前仕様で、rootのtie ruleを明記する。低改修版なら「先に訪れた完成depthのbestをstrict >時だけ更新」を固定し、等値Action差を別に記録する。元のAction選択を厳密保持したい場合は、等値bound候補のexact再探索などの追加費が必要で、それを無料のorderingと呼ばない。数値整合はf32評価器の既parity許容と探索boundの意味を区別する。

nodecap下では訪れる葉と完成depthが変わる。固定nodeで深くなることだけを同wall棋力や離散探索量一致の証明にしない。途中depthを完成PVにせず、最後の完成depth/Action/value、未完成理由、nodes/NN、取消・配送を保存する。terminal goal/draw/RuleAの第三反復による合法手制限を葉NNより優先し、historyをQF1の壁map keyへ読み替えない。

## 既sourceで分かった費用と測り方

State.getLegalActionsは `_legal_actions_cache` を持つ。terminalResultと展開が同Stateで呼んでも、二回目は通常cache hitであり、二回のAPI呼出しを二重の壁BFS費とは数えない。一方、childのnextは盤面・wall配列・history Mapをcopyし、pawn移動ではpath edges、wallではgoal距離とpath edgesを更新する。copyは距離/pathの参照を共有し、無条件に全距離gridを複製しているわけでもない。

qf1.deltaは単なる重み加減ではない。inputの特徴集合・壁map参照、両accumulatorのcopy、feature集合差とf32更新を含む。qf1のwall-only mapは別cache（256件超でclear）であり、Stateの距離計算との重複可能性はあるが、同goal/graph/座標/不可達処理の対応は未検証である。既cacheを確認せず新cacheを主案にしない。

次の固定root計測では、内包時間と排他的時間を分ける。以下を単純加算して全費や支配費にしない。

| 区間 | 含む処理と重複 | 必要counter |
| --- | --- | --- |
| terminal/合法取得 | goal/depth、legal cache miss時のpawn/history制限・壁合法BFS | 呼出し/hit/miss、合法数、壁検査/BFS数 |
| next全体 | copy、手の適用、距離/path、history記録 | pawn/wall別、copyと距離/pathの子区間 |
| q.input全体 | 両視点特徴、map lookup/miss BFS、STM距離 | map hit/miss/clear、active数 |
| full/delta全体 | q.inputに加えaccumulator copy/update | inputを除いた更新時間、removed/added数 |
| value | STM順ReLU/尺度補償、hidden/out/tanh | leaf/root NN数、terminal NN0 |
| control/order | 再帰/bound/ordering/nodeguard・取消確認 | cutoff、first-child費、完成depth/打切り |
| 全route | 入力受付→合法Action配送・回収・記録 | cold別、wholewall、pipe/JSON/待ち |

親子timerを入れるなら子区間を引いたexclusive値を別fieldにし、引けない場合はinclusiveと明記する。wall合法判定の一時segment変更中に新しい取消例外を投げるならfinally復帰が必要である。profiler自体のoverheadも全wallへ計上し、inner区間だけで採否を決めない。

## 競合との優先と再検討条件

| 有力保留 | 現在主案より後にする理由 | 再検討の観測 |
| --- | --- | --- |
| TT | RuleA履歴/side/pawns/HV/rem/goal/draw ply/context、depthとexact/lower/upper boundの完全性・RAM/key費を要する。特徴署名だけでは合法/終局を表さない | 同一探索contextの再訪が多く、key/lookup費を上回るreuse見込み |
| make/unmake | 既copyのhistory・壁temporary mutation・map参照・例外/取消で親復帰検証が広い | next/copy/historyが排他的全wallの大部分、必要QA費を回収可能 |
| 距離map/NN cache再用 | 現在legal/map cacheあり。StateとQF1の距離対応、weight/scale/input版とterminal/historyを分ける必要 | map miss/BFS又は同NN input反復の実費が主因 |
| root/上部policy ordering | value-only候補に追加policy経路が必要。全合法保持でも追加forward/IPC費がある | root orderingだけではcutoff改善が弱く、同費でpolicy順が有益との有限根拠 |

学習候補の新teacher誤差利益はnative探索での利益を保証しない。このため、今は追加LR/量選定に戻すより、凍結した同候補が正しい葉値として使え、探索順だけの小変更が費用を減らすかを分けて進める情報価値がある。学習の成功を検索高速化へ、検索速度・depthを棋力へ代入しない。

## 最小の次判別・費用

本scopeの実装/runは0。将来一つのprivate ownerが、同凍結評価器・scale・RuleA・固定非holdout root・depth/nodecapで元順と完成rootbest-firstを比較する。まず全合法集合exact/親復帰/完成値/打切り/tie差、次に各rootのnodes/NN/cutoff/wholewallを保存する。順序配列だけの実装は5–10分、品質・固定root対照・失敗記録は別5–10分が目安で未実測。232 exporter/parityに重ねて広い25–40分変更を開始しない。現frameで入らなければNOT_IMPLEMENTEDとして次の具体配分へ返す。

将来の同wall棋力診断は、同モデルの探索順だけを変え、独立root/familyと同CPU/thread/RAM・時計・terminal/tie/fault/停止規則を結果前固定する小対局を別配分する。root forward/action診断とは到達範囲が異なる。今回は対局を自動開始しない。総投資C=実装+QA+対照+失敗+資格+記録、回収root数は C/観測された一rootの全費削減Δt（Δt>0）で見積もる。Δt未観測なので倍率・回収局数は未知。Supervisorの自然点検は232の意味対応と本案の全合法/未完depth/全費/同wall効果を別追跡し、速度だけで強さを認定しない。

参照source/hashは自域source-bindings.json。228 freeze/候補は変更せず、229独立checker未完了を独立PASSへ救済しない。173・旧openedtestを読まず、親/共有source/232scopeを編集していない。
