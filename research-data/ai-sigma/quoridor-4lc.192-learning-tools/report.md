# quoridor-4lc.192 学習曲線・設定可能なNNUE学習環境

root所有のsoftware整備。前のframe13は終了したままで、新研究学習・教師生成・GPU・対局は開始していない。

`tools/nnue-training/` に設定JSON＋CLI override、QF1 value trainer、途中の全train/validation/cohort/group評価、early stopping、best/last checkpoint、PNG/SVG plot、CSV/JSON比較を実装した。steps / train samples / epochs equivalent / wallの軸を持つ。教師rootmean/z、学習率、幅、batch、optimizer、weight decay、dropout、sampling、scheduler、評価間隔等を指定できる。game等重みとrow重みを区別し、定数基準・欠測zを保存する。

手順: [NNUE学習環境](../../../docs/development/nnue-training.md)。既存176/181の48game/2762行を合法棋譜と履歴・特徴まで照合してQF1 exportし、train2260/validation502・40/8group・集合間state/history/features共有0をdry-runで確認した。元のsplitは変更せず、この研究データを追加学習していない。

5ソフトウェアテストはpass。人工6行・幅4の2stepとsample limitの機能確認だけを行い、一時重み・出力は終了時削除した。設定拒否、group露出拒否、欠測z、game等重み、early stopping、best選択、同run上書き拒否、全評価履歴、異なるvalidation比較のflag、PNG/SVG出力を確認した。詳細はverification.json/tests.log。

既存190の図を190-learning-curves.png/svgへ保存した。学習ログ4点と検証前後0/200stepだけを使い、途中のvalidation曲線を補っていない。190-plot-data.jsonは描画に使った数値と原入力SHA。最良stepや過学習が始まったstepは旧記録から判別できない。

新runは定期validationを保存するので、過学習・更新不足・cohort退行の判断材料になる。ただし曲線だけで原因や棋力を確定しない。validation選定と独立arena/holdoutを分け、正式173データは非学習。次の研究配分では固定validationと露出group splitを使い、データ増量と学習量の対照を明示する。

最初のexportはVM由来配列のprototype差によるNN0 assertで失敗し、内容比較へ修正後に全2762行が通った。共有training依存を変更せず、plot依存だけ隔離cache envへ導入した。CPU/GPUの実学習速度、新重みの精度や棋力は今回の成果に含まない。
