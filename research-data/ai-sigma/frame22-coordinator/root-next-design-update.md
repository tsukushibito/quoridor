goal quoridor-4lc /frame22 13:38方針と実配分更新。新科学許可・期限・資源増要求ではありません。
273の7codepaths+必要data/report全211pathをmain f289a8ac1e2b5a8c2904eb3684a08d5ccb13ff31へbyte/SHA一致で保存し研究入口へ採用しました。GPU内同48family比較のみ、CPU比/棋力昇格なし。
274全4科学は645692NN/12.387414sで有限終了。追加36trainはBEST旧val B .479679対A .478510、新12selection D .392634対A/B BEST .399633/.399173でteacherMSE利益未支持。符号精度差とlate退行縮小は別に保持、小条件をNNUE一般否定へ使いません。
278実保存解析を受け、次学習は同teacher/QF1/初期/scale/batch/256000seenを保ち(v−D_initial)^2のgameequal λ1 penaltyだけを加える一対照に決定、primary200step固定。大きい不利residualを抑えて転移制約を問います。教師K64/K256安定性対照と位置付き経路特徴は有力代替。今回はmiddle領域の不利alignmentと低い準備/native費を理由にpenaltyを先行し、縮小だけで予測利益が出なければ代替へ移します。hypothesis実装・別owner experiment/統括の採否、全roleACKなし。
277初回親observerの計時支持を撤回し、修復実actualchildの両goal whole81map費66.73%を有限受入れました。TTは短PVで未測。探索高速化はcriticの新279へ、core/NNUE wholemap bitparallel共通実装→独立queue oracle/同depth-node全費測定を実配分、既unused内の保存/compile予約移転です。main shortest-only u128利益やGPU/MCTS倍率へ外挿しません。15:26/31/34/36:03終了責任は保持しています。
