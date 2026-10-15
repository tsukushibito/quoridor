# NNUEの弱さと公開Sigmaデータの前提（418）

実際に対局したBEST43を起点に、保存された学習・変換・native対応と固定upstreamの公開履歴を調べた。**前提の訂正はできたが、弱さの単独原因は特定できていない。** 新しい学習、forward、Search、対局、solver、build、テスト、sealed/newEの開封は行っていない。

実モデルはfresh353の重み046fe、descriptor46ec、evaluator96a5で、BEST43は物理epoch43を意味する。公開43NPZやSigma cycle43ではない。旧BEST51、100万行モデル、固定D追加学習とも別である。

公開fix43は修正後legacyの継続データで、後のscratch321 ONNXの全学習史でも、ランダム初期から43世代分の記録でもない。公開時84cfと固定751186の43ファイルはGit blob/sizeが一致する。モデルやNPZ本体を再取得・再hashした確認ではない。各shardの実生成checkpoint、棋力、game/historyは依然UNKNOWNで、ファイル番号を学習cycleへ339加算して対応付ける案は採用しない。

NNUEは世代quality/recency weightを付けず、T8,413,949行をepoch shuffleして学習した。データ番号1..20は実Tの5,719,421行、67.9755%を占め、BESTまで245,935,103回の行露出となる。この番号の範囲を「弱い初期20世代」と呼ぶ根拠はない。Sigma側はsource・時期によりrolling windowとrecency重みが異なり、READMEの30だけで固定train.pyの60/.99や歴史版30/.92の実runを代表できない。各世代の実累積exposureも、最後のbuffer重みだけでは復元できない。同じfix bufferでheadsが改善した原作者記録は、buffer全体が無価値という断定への反証材料である。

教師zは生成方策での実勝敗であり、raw value、MCTS root mean、最適WDLではない。同じ入力の別±1は直ちに破損を意味せず、方策・相手・history・世代などの欠測を含む。終了理由不明z0の除外による条件付けも残る。MCTS由来という理由だけでαβ教師に不適切とは結論しない。

ほかに三つの読み違いを訂正する。BEST行のtrain MSE0.426580は全Tではなく固定8,192行の診断で、V0.423871との差をfull train-validation gapとして扱わない。歴史的`game_equal`は実際には入力グループ均等で、game均等ではない。保存saturation48.5397%の閾値は`|v|>=.9`で、後の別分析の.99とは異なる。旧naiveLR半分は実BEST43の訓練対象外で、T-only corrected onlineLRを使っている。既存有限Python/native parityは大きな取り違えに対する反対材料だが、全局面・教師・棋力の証明ではない。

優先して分ける競合説明は、生成方策・行重み・探索葉分布の違い、表現/容量/最適化、validationの分割と重複、探索条件である。同深さ比較でも負け越した既存結果は「速度差だけ」の説明に反する一方、searched root値を静的NN出力や最適値へ読み替えることもできない。415は同評価器内LMR比較でありNNUE対固定Dの比較ではない。進行417の結果は先取りしていない。

[Astra Highの統合分析](analysis/report-ja.md)に、各仮説の証拠・反証/交絡・次に一つだけ確認する案と固定一次sourceを保存した。[Sol Highの実学習事実](facts/report-ja.md)はモデル→run→sampler→cache/ラベル→nativeの関係をまとめている。重要な新因果・棋力主張を採用しない記述的分析として受け入れる。古いデータ除去、新fit/forward/対局、特徴変更、paused学習再開はいずれも今回から発行しない。

原HTTP404、管理・formatter失敗、returnedとdisk receiptの違い、全費UNKNOWNを保持する。source/LLM/adminを含む全費やcontinuous peakはUNKNOWN。原科学runの費を今回へ再加算しない。実STOP・直接wait/reap・fresh identity・handles/TMP/owned[]と一度の対象使用はreceipt/archiveを参照する。研究LMR標準depth_rank、製品/generator enable OFF、全mixed/learner prep/pipelineと323 USERPAUSE、models/weights/seals/oldfits96/foreign変更を維持する。
