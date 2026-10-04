# frame15 入力標準化対照の独立批判 / quoridor-4lc.212

現時点は選定前。train-only標準化・同初期関数・同plainモデル/情報/容量/seed/batchの1対照を支持する。非0synthetic距離感度とlinear基準slopeの差だけでは原因を認定できない。元LR1e-4の早期利益2jointseedと距離基準の優位を保持し、この対照がoptimizer座標conditioningと予測軌跡をどう変えるかを見る。

最大1修正案は、標準化座標の実更新を元距離単位へ戻しfixedwitness予測変化と併記すること。u=(d−mu)/sigma、Wd'=Wd diag(sigma)、b'=b+Wd muで初期関数を保つが、その後はDeltaWd_raw=DeltaWd'/sigma、Delta b_raw=Delta b'−DeltaWd'(mu/sigma)。sigma≈.054では同LRの元単位更新が増幅される。normalized weight ratioだけで情報利用の改善とは呼ばない。既before/afterを使い追加forwardや新gateを要求しない。

有力代替は距離列の実効optimizer step制御だが、中心化とbias結合まで同じではない。今は新条件を増やさず保留し、大きなraw update/early利益が出た時に単純LR/parameter-groupで説明できるか再検討する。初期関数保存はf32で丸め差を含む有限parity<=1e-6、同tensorSHAとは異なる。mu/sigmaはtrain96game等重みの2distance列population moments、実f32使用、ゼロ分散typed扱いを必要独立算術で確認する。中心化+尺度+初期座標変換packageの対照で各要素の単独原因とはしない。

private sourceはh最終2distance列をscaled重みへ変換しbiasを補償、raw Modelは非登録referenceとしてstep0parityにだけ使う。原forward/dropout/tanh/optimizer全層を保持する経路を読取した。raw parity5901はscaled初期評価5901に加えて別課金する経路。sourceと保存receiptの有限対応であり、このcriticがモデルforwardする認証ではない。

primary200−old200を固定、全24val分母・train到達誤差/epoch/samples、初期/定数/距離とsecondary bestを保持する。単seed・再用val・observer overhead未分離、教師/history/分布を残す。旧test labels/results/raw/journal/mixedstatus/preview/173holdoutは未読・非転用。現成果は選定見解のみ、実結果未着で予測改善はまだ未判定。

210は受入れ済みに基づき本人close/backup、旧180/180と未検算probeを変更しない。212ready/showgoal+self/pause/割当→claim/staticsource実開始、readcharge30/120、科学算術job0、新NN/modelimport/forward/train/game/build/GPU0。保存forecast700KiB<=新1MiB、旧112832996維持込み113881572<117440512、unknown減額/親追加0。見解をexp/coordinatorへ届けaccepted配送確認、主211の承認gateではない。実停止receipt・moments/parametercounts/initialfunctionparity/曲線・primaryのcompact結果を待ち、fresh physics/supervisor窓admit後にNN0有限裁定する。期限05:15newcommand/05:20science/05:35submitをresetしない。
