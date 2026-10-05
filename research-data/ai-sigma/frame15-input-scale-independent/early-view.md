# 212 選定前の独立見解

同初期関数/同情報/同容量/同seed・batchを保持するtrain-only尺度対照を支持する。全層の初期勾配・非0局所感度があることは情報利用や最適化の健全性を保証せず、linear距離基準のslopeとの差だけで不良と判定しない。距離標準化は実用の1対照として低費用で、元trainfitと早期val軌跡が変わるかを判別できる。

最大1修正案は、既observed optimizer updateから隠れ層の距離2列とbiasを元の入力座標へ戻した実更新を記すこと。u=(d-mu)/sigma、Wd'=Wd*diag(sigma)、b'=b+Wd*muにより初期関数は同じ。しかし以後、DeltaWd_raw=DeltaWd'/sigma、Delta b_raw=Delta b'-DeltaWd'*(mu/sigma)で、Adamが標準化座標で動かす量は元座標でLR変更とbiasの結合を含む。sigmaが小さければ同LRでも元単位のupdateは大きくなる。元単位の実更新と同固定witnessの予測変化を対応させ、normalized weight normだけで「距離利用改善」としない。既stepのbefore/after値を使うなら追加forward不要、必須の新観測gateではない。

有力代替は距離列のoptimizer実効stepを制御する対照だが、中心化とbias結合を再現せず、この枠では新条件を増やさない。尺度1対照が大きいraw update/良い早期利益を示す場合に、より単純なLR/parameter-group調整で説明できるかを次に再検討する。逆に同初期関数で利益がなくてもC教師/history/分布や未観測の相関を残す。

mu/sigmaはtrain96の各gameを1/96、各行を1/n_gameとして算出し、実STM f32距離の2列からpopulation varianceを求める。valをfitへ使わない。保存f32mu/sigmaの実使用・ゼロ分散typed handling・raw initial tensor bindingと関数parity<=1e-6を照合する。同tensorSHA不変ではなく同初期関数である。中心化+尺度+初期重みの座標変換という一つのpackage効果で、どの要素の原因かは単独認定しない。

primary200-new minus old200を固定し、初期/定数/距離、全24val分母、train到達誤差/epoch/samples・bestsecondaryを保つ。単seed/再用validation、初期parity追加費、observer overhead未分離を残す。旧test全種/173holdout非読取、model/forward0。後続の停止保存metricsで必要算術を行い、全稿承認gateを作らない。
