# 同horizon保存列からleaf意味と距離等値を区別する / quoridor-4lc.243

次の一案は、距離対照Dの**非終端出力だけをclipから固定tanhへ変える同完成depth診断**とする。凍結NNUEの再学習より先に、距離順位をclipで失い得ることと、終局伝播による同値を区別し、strict-greaterの同値手選択に依存する範囲を確認する。これは未来の具体配分候補であり、今回実装・計算・対局を起動していない。242の同prefix・同wall package比較は独立に継続し、この文書を入口条件にしない。

239有限受入れの21Git/current byte確認を読み、この実質243 turnで本人239close・backup exit0を完了した。243は2026-10-04 23:57:51 UTC受領、ready/show goal+selfの本人割当・frame19/no pause確認後claim、23:58:34静的開始。科学CPUjob/NN/model/Torch/forward/fit/game/GPUは全0。旧239/240の失敗・UNKNOWN・費用・期限は変更していない。親終了2026-10-05 00:52:46、本人source/report停止00:12・保存00:18を適用する。

## 保存列で絞れたこと

240の停止正本SHA `445775e90e3c6f380852174b38278ee5a08a7ca8d144755f2e4f25884293f638`、compact SHA `2a4a5b4f4a5877afb0aab588ca5e466110b3c5bf2628f8870389567a12c1641c` は指定現物と一致。必要sourceとmetadataのSHAを自域 `source-bindings.json` に保存した。12source/10payloadの全面再検算は追加していない。下表はcompactの既保存値の引用で、新算術や探索ではない。

|239固定case|NNUE depth1→2|D depth1→2|言える範囲|
|---|---|---|---|
|0 / slot2 ply27|最大Action142→11、depth2値−.169671386|両depthで全94合法手が−1最大同値|元NNUE Action11とdepth2列は一致。Dにはこの有限horizonでroot順位がない|
|1 / slot3 ply10|両depthでAction85、.507779121→.485877097|10手の最大集合に85を含む、.038688969→.060382154|NNUEの選択をDのstrict劣位と断定できない|
|2 / slot5 ply14|Action98→83、−.293424040→−.213966087|最大集合10→12手、両方に83を含む|NNUEのdepth依存は確認できるが、Dとの比較は同値の中の選択も含む|
|3 / slot7 ply40|depth1 Action19/−.942107439、depth2全3手−1|depth1 Action19/−.555737615、depth2全3手−1|元depth12をdepth2との対応証拠にしない。−1だけで各手の終局由来を確定しない|

最初3caseのNNUE depth2値は元239ログと差0、選択手も最大列に含まれる。これはその根・履歴・深さの実装対応を支持し、arenaの悪い結果を数値接続の一般的失敗へ直結する説明を弱める。合法な選択が強い手であること、探索先の教師真値、より深い最善手は証明しない。元arena非bestのfail-soft値を全root-child exact値へ昇格していない。

早報のcase0「全94手clip−1」は断定が過剰だった。正しくは「全94 exact root value−1、clip/terminal起源の内訳未記録」で、case3同様UNKNOWNを維持する。統括の同active補足に従って本reportを修正し、早報元bytesを保持して `early-erratum.json` に訂正を残す。compactの値・旧科学は変更しない。

`exact-cases.cjs` は全合法root-childを個別full windowで評価し、各child内部はαβを使う。最大値・同値集合はこの固定leaf関数と有限depthのexact列である。`engine.cjs` の通常反復深化は前回完成bestを先頭へ移し、更新は `v > value`。同値は先に訪れた手を維持する。したがってrootbest-firstは枝刈り費だけでなく、同値集合内の採用手にも影響し得る。全合法手を保つorderingの影響と、値を変えるleafの影響を分ける必要がある。

240の同仕事profileではbaseline/candidate各processed262144・NN125128、完成depth2、値/Action一致、wholewall16061.169→6553.425msというowner有限観測がある。packageはleaf終局判定とDの重複term除去を含むため、単独改修の排他的費用へ分解しない。optional4の3W/1UNKNOWNは236とprefixが異なり、勝率改善のpaired根拠ではない。242の新paired結果は本選定時点では未読・未観測である。

## leafの意味と残る競合説明

入力はQF1二固定視点312の疎特徴とwall-only goal距離2値。`qf1.cjs:input` は距離を/80にし、手番側・相手側順へ一度だけ並べる。NNUEは共有accumulatorをそのSTM順へconcatし、距離をtrain-onlyのmu/sigmaで標準化してhidden/ReLU/tanhへ渡す。`native.cjs:valueScaled` はf32演算・f32 tanh出力、Dは標準化前の同STM距離から `u=f32(a+b*(dopp-dself))` を作りclip[-1,1]にする。ここで凍結metadataのa=.06038215201109912、b=7.925687690687516。係数・尺度・checkpoint/freezeは変更しない。

両探索はterminalを先に処理する。winnerは現在STMで±1、200ply又は全合法なしは0、その後に非終端leafを評価し、各edgeで符号反転する。RuleAは三回目のpositionへのpawn移動を合法集合から除く。反復を単に引分値に置き換えていない。内/root full合法と葉pawn存在/fullfallbackの意味を保持する。

MCTSのrootmeanは `valueSum/visitCount`。backupごとにSTM符号を反転するが、探索配分はprior/PUCT/FPUと有限K64に依存する。rootmean回帰誤差の改善は、全合法minimaxの各leafを校正した証拠ではない。temperatureは保存教師の訪問分布・自己対局の選択に関係し、今回のαβleafにpolicy/温度を追加していない。TT/noise/policy除外0も維持している。

NNUEとDの基礎入力には履歴カウント・残りplyがない。同盤面入力でも合法な将来手・200plyまでの距離が異なり得る一方、検索Stateは完全RuleA/historyを保持する。239のboard+side再訪26/完全history+ply context再訪0は、入力aliasの可能性を示すが、その損失寄与は未測定。今回4caseはarenaを見た後に機械規則で抽出した探索的診断で、未見性能・badmove真値ではない。

Dのaは0でないため、非終端leafのrootへの符号はhorizonの奇偶により切り替わる。固定盤面距離差を仮定した式は `(-1)^h*a + b*s_root` となるが、実際は手で距離が変わる。これはSTM fitのtempo成分も含み、符号実装バグと断定しない。case1/2の奇偶値差をNNUEのhorizon誤差だけへ帰属させない。

終局とclip飽和は同じ±1を返す。NNUEもf32 tanhの丸めで端点に達し得る。compactの−1だけから「全手が実終局負け」と推定しない。leaf provenanceが無いためcase3のこの解釈は **TERMINAL_OR_SATURATION_UNKNOWN**。horizon不足、履歴alias、MCTS rootmeanとminimaxのtarget差はいずれも残る。

## 最大1の未来対照

条件は **D_clip対D_tanh** の一つ。NNUE本体・係数・距離計算・RuleA/history・全合法・clone/復帰・root order・node/deadlineを固定し、非終端leafだけ `f32(tanh(u))` に変える。terminalは従来どおり±1/0を先に返す。tanhは再fitや新targetを使わない固定写像で、元Dの教師回帰値そのものではない。clipの非可逆な同値化へ感度を見るための別conditionであり、元D成績を変更しない。

現在の合法距離範囲0..80と固定係数では|u|<8であり、提案版では実f32非終端出力が±1未満かを有限fixtureで確認する。出力端点を未知のままterminal区別PASSにしない。tanhは奇関数で単調なので、終局無しの有限treeでは符号反転とmin/maxに整合し、rawの順位を保つ圧縮になる。旧clipは飽和領域の順位を失う。実treeでは終局の混在・floatの同値・剪定があるため、全child値・tie集合・terminal provenanceを測ってから判定する。

対象は同じ固定4case、depth1/2の全合法root-child列。新prefixや勝敗でcaseを選び直さない。各root-childでextremumを決めるleafのterminal種別・terminal値と、非終端raw u/preclip・clip後・tanh値、根の同値集合を少数集約で保存する。同値のprincipal witnessだけでは他のextremal leafの由来を一般化しない。両Dのみでよく新NNforward0、入力parity・終局優先・P2符号・全合法・親history/buffer復帰・未完成列discardを有限検証する。nodecap/期限で打切りなら当該列UNKNOWN、別depthへの置換や成功補充をしない。

見積は薄private adapter+確認10–15分、未来CPU2単1/RAM512MiB guard448、科学1job hard60s/合計processed guard65536、新NN0、保存1MiB程度。元240列は全16conditionでprocessed63172だったが、proposalのclip/tanh両Dのnode数は未実測で、旧値を上限保証にしない。新科学の実行には統括の具体配分・current owner/RAM/runtime/storageのfresh admitが必要。今回243は提案までで一切起動しない。

clip同値集合がtanhで分かれ、非終端距離順位・strict-first手が変わるなら、D対照の飽和交絡を明示し、次の同資源手選択比較を組む理由になる。これはtanh手の強さ支持ではない。終局が全てを決める/順位と選択が変わらないならclip説明の優先度を下げ、teacher-rootmean→minimax leaf又は履歴文脈への次検証を再検討する。その場合も今回4caseから原因唯一にはしない。

|有力保留|今回の優先理由・再検討契機|
|---|---|
|新leaf-target/calibrationの再学習|新target取得・train-only fit/valfreeze・未開封独立評価が必要。clipという対照側の交絡を先に安く判別する。将来は元model/scale/teacher品質を保持し旧openedtestを選定へ戻さない|
|history特徴/teacher文脈追加|RuleAの合法差が入力に無いという構造根拠はあるが、case0再訪だけで寄与を示せない。clip不支持で同horizonの文脈差が残る時に順位を上げる|
|深さ/ordering/探索費改修|242がpackageの同wall差を別に測る。243からseed/clock/条件を変更せず、その結果を後続判断に使う。速度・完成depthだけで棋力を認定しない|

採否理由は二経路を分ける。242は固定NNUEの教師誤差改善を同wall効用へ移せるかを測る現在配分で、本案は対照Dの飽和と終局伝播の交絡を小費用で調べる未来候補である。tanhは係数・入力が同じでも新heuristicで、D一般向上や公平基準完成を認定しない。改善判定の最終目的は同探索資源の手選択利益であり、この静的選定やteacher MSEを棋力へ代えない。最高NNUE目標は未達。

## 保存・費用

自域は `research-data/ai-sigma/frame19-leaf-meaning-selection/` と本reportのみ。新1MiB予約、guard768KiB、source/report+必要uniqueGit/temp/残metadata forecast512KiB以内。旧2392MiBほか全予約・UNKNOWNを保持し、親追加/未知減額0。source-read上界60秒、管理90秒、科学CPUjob0。部分path探索の不在はsource-bindingsに記録し科学失敗にしない。新rawteacher/PT/testlabel/173labelsは読んでいない。停止/hash、currentbytes復元、Beads notes/close/backupと配送receiptは自域小metadataへ記録する。
