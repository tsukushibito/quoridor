# 距離基準以上のNNUEへ誘導する条件と次の小対照 / quoridor-4lc.265

2026-10-05 frame21、hypothesis。08:49:45受領、08:50本人claim、静的調査のみ。現役mainのRust/Python source、指定公開一次source、既保存train/validation集計を参照した。実装、モデルimport、NN、学習、コンパイル、対局、教師生成は実施していない。研究目標の棋力到達は未達。

最大1推薦は、固定距離関数を初期値として保持する残差モデルを共通条件とし、最短経路DAGの4値を足す対照である。疎盤面を持つことと、浅いネットが経路の選択肢を学習できることを分けて調べる。現NNUEの教師誤差を下げるだけでなく、特徴取得を含む同時間探索で距離評価を上回ることを次の採用条件にする。

## 現sourceで確定すること

`crates/quoridor-ai/src/alphabeta.rs` のDistanceEvaluatorは、手番側・相手側の壁だけの駒最短距離を/80でf32化し、`u=a+b*(d_other-d_self)` のtanhを返す。残壁、相手駒によるjump、履歴contextはこの式へ直接入らない。壁配置と駒位置はwall_distanceへ間接的に入る。残壁・jump・履歴は合法生成やSigmaContext/探索で扱われるので、AI全体がそれらを無視するという意味ではない。

QF1は各固定視点に自敵pawn81+81、H/V64+64、自敵残壁11+11=312を持つ。P2は180度回転・所属交換する。内部のWallMapsには両goalへの81升距離mapがあるが、後段へ出すのは両pawn位置の2値だけ。壁が変わればmapを作り直し、pawn移動ではmapを共有する。履歴・plyはNN入力にない。同盤面・同残壁・同手番でも履歴が違えば、教師探索の値は違い得る。

`python/quoridor_training/model.py` は共有FT→ReLUを手番/相手順に並べ、距離2値とconcatし、hidden ReLU→tanh valueを出す。実数演算では `ReLU(u)-ReLU(-u)=u` なので、hidden2unitを使えばQF1は距離関数を表現できる。標準化入力でも係数を±bσ、biasを `a+b*(μ_other−μ_self)` に直せる。これは静的な表現可能性の説明であり、現在重みがその解を学んだ、f32一致した、有限勾配で到達しやすいという証明ではない。FTを介さず距離2値がhiddenへ直接入るため、全mapが未入力であることだけを距離関数の再現失敗原因にはできない。

scaled_modelはtrainだけのμ/σを用い、hidden重み/biasを補償して初期関数を保持する。標準化は情報追加ではない。現在train.pyの距離momentと線形fitはrow重み、定数はfamily平均、samplingは設定でgame/rowを選べる。対照では係数・尺度・重み付けを明示して束縛し、重み付け差を特徴効果へ混ぜない。既manifestの係数を固定再用し、新しいfitを暗黙に加えない。

探索はterminalを先に処理し±2を返し、通常leafは[-1,1]に制限する。教師rootmean±1とこの±2の差は終局の優先を分ける設計で、数値差だけで不整合とは言えない。MCTS rootmeanはrootの探索平均で厳密minimaxでも終局zでもない。現データ型のalpha_beta教師は別型で、cache上のrootmean aliasは明記されたbounded_search_valueである。単一teacher type、STMのedge符号、terminal優先、履歴依存を維持して接続する必要がある。rootmeanMSEの最小化には「Dより強い手を選ぶ」「同wallで完成depthを失わない」という目的が直接入っていない。

## 既train/validationが示す限界

| 保存条件 | train gameMSE | validation gameMSE | 読み取れる範囲 |
| --- | ---: | ---: | --- |
| 旧200 clip(D+tanh residual)、LAST | .007437 | .759458 | trainfit可能でも新gameへ移らない。BESTは初期step0 .485147 |
| 216 standard200 | .548567 | .613916 | この早期点ではtrainでも距離基準未達 |
| 216 standard400 | .257283 | .648772 | trainfitと転移の差が大きい |
| learned400 hidden＋固定ridge .01 | .208594 | .612799 | 読出し変更で一部変わるが距離基準を超えない |

216保存距離基準はtrain .405944/val .485147、standard400残差と教師残差の相関はtrain .607/val .048。validation gap .163625は残差変動 .192934と交差項−.029310で説明され、clip/meanbiasだけに帰属できない。これらは小さい旧96train/24val・再用validationの条件であり、表現全般・残差設計全般・十分な教師量を否定しない。旧数値の距離基準/clip条件を、現在tanh DistanceEvaluatorの未測定MSEへ読み替えない。新方式は現在tanh baselineのtrain/valを同一評価で計上する必要がある。

## 公開sourceの特徴と本提案の違い

固定Sigma751186のgame.pyは8×9×9入力で、pawn/壁/残壁に両goalへの全升距離場を加える。9×9距離は/80、P2は上下反転でQF1の180度回転と異なる。内部mapだけでなくmapを入力している点がQF1との違いである。[Sigma固定source](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/game.py)

Claustrophobiaは調査時のcommitを `ae093653e62ad700e201706fa5ed767093d0d68e` に固定した。encode.rsの基本16planeには距離場、最短経路membership、合法壁、距離差、壁脅威場があり、optional20は壁効果を足す。/20 clip、P2は180度回転・所属交換。コメントはグラフ計算の再学習を減らす意図を述べるが、その意図や掲載速度は本NNUEの利益を証明しない。[Claustrophobia固定source](https://github.com/Plaaasma/Claustrophobia/blob/ae093653e62ad700e201706fa5ed767093d0d68e/src/encode.rs)

本[DAG4案の設計参照](../design/ai-nnue-feature-design.md)は、各側の最短経路件数と到達goal数を小さな後段へ圧縮する本研究の仮説である。参照AIがDAG4やT1の828/256構成を採用しているとは主張しない。全planesの移植より安い一方、経路位置や壁候補の真の遅延を失う。経路が途中で合流するため件数は独立経路数や耐壁性ではない。

## 次の実配分案：D保持＋DAG4の一対照

Aは現QF1-H32と固定 `u_D` による `v=tanh(u_D+R_QF1)`、Bは同じAへ4値だけを加える。Rはhiddenからの線形logitで出力headを0初期化し、初期vを現在Dにする。旧200のclip(D+tanhR)と異なる方式で、旧失敗を置換しない。head0時は初回の下層勾配0が構造上あり得るので、これを検査失敗にしない。tanh飽和は残り、Dへの固定skipも改善保証ではない。

4値はSTM/相手順の `log(1+min(C,255))/log(256)` と到達goal bitsetのpopcount/9。Cとgoal集合を距離下降辺のDAG上で求める。goal升のC=1、集合=そのgoal bit、他升は距離が1減る隣接先を合算/ORする。壁+goal+graph/feature版をcache keyにし、pawn手はlookup、壁手はDP更新、親map/履歴を変更しない。不可達を0距離や通常の経路数へ埋めない。残壁は既312に残し、壁を置けるかの解釈はネットへ与える。追加後段重みはH32で128、FTは312のまま。Aにも4入力分の0枠を設け、両条件のshape/共通初期tensorを合わせることができるが、有効情報・実効自由度の差は残る。

最初の小診断は、target/lossを見る前にIDを固定したtrain/valの12–24合法状態で、P2双対、同距離・異経路、pawn移動map共有、壁変更DP、make/unmake親復帰、D初期とf32尺度/出力parityをabs1e-6+rtol1e-6の結果前許容で検査する。これを教師誤差や棋力の証明にしない。旧Node/旧trainerは使わず、現Rust features/cache→mapped inputと現Python model/exportの版付き薄拡張にする。現在cacheは距離2値だけなので、DAGはweightsだけの変更では済まない。既原状態入力がない行を推測で埋めず、その行を不適格として全分母を保存する。

CPU学習は同train/val family・固定露出mask、rootmean単一教師、H32、gameequal、AdamWD0/LR1e-4、同seed/同batch順、400step×128の2条件を第一費用案とする。points0/1/2/5/10/20/50/100/200/400を固定し、game/row rootmeanとz診断・位相・D/定数差・飽和を保存する。5901適格行ならtrain102400＋eval118020＝220420 sample（別parityは別台帳）。初期を含めvalidationだけでBESTを選び、学習量/epoch/教師量を変えない。5901現cacheへの接続は未確認であり、この数量を実行保証にしない。現在大規模datasetを使う場合は行数とeval費を実配分前に置き換え、旧splitを黙って変えない。

実装/入力cache/export/有限検査を含め35–50分、CPU2single/RAM2GiB guard1.75GiBを次配分候補とし、各120s・科学合計5分程度を見積もる。source実装だけの見積ではない。feature DPは各goal81升の下降辺を処理し、map miss/wall更新で費用が出る。RAMは型・cache上限を決めてから配分し、feature→full/delta→leaf→探索までのinclusive総費と、重なるBFS/cache費を加算せず測る。最初のschema/保存局面診断で不足が見つかればそこまでで停止し、全基盤の完成を入口条件にしない。この課題265自体はこの科学を起動しない。

BがAおよび現在Dを固定val主指標で改善し、cache込みnative葉費も収まれば、候補/config/feature版/尺度/weights/選定規則をfreezeし、新未使用familyの独立評価を次節目に置く。その後の同資源・同wall・全合法・終局/履歴・失敗/未完成depth規則を固定した小対局で採用を決める。teacherMSEだけで既定昇格しない。Aのみ改善ならDを保持するparameterizationを優先し、DAG追加は保留。Bがtrainだけ改善なら経路情報の転移は不支持であり、教師分布/history/leaf-targetの一つを次の問いにする。両条件がtrainでも追加情報を使えない場合は入力尺度/gradient/教師残差の小sanityを選び直すが、自動sweepはしない。

| 競合候補 | 今回の順位と再検討条件 |
| --- | --- |
| 直接D項＋残差のみ | 最安の共通A。距離関数再発見を避けるが、旧条件で転移失敗がある。A対Bからplain→skipの単一因果は分離できない |
| DAG4 | 推薦。追加mapBFSなしの圧縮経路情報で、保持Dを超える残差の転移を小さく判別。更新実費は未測定 |
| 壁pair516/全map162/候補壁効果 | 16,512追加FT重み又は後段/壁更新費が増える。DAGが位置情報を失うことが実弱点なら順位を上げる |
| jump・残壁context・履歴 | jumpは局所的で安い。接触/残壁別で誤り集中、同入力・異履歴の教師矛盾が確認された場合に次候補。現在源だけで集中を認定しない |
| 強い教師/target・分布 | rootmean→minimax効用や情報欠落を直す候補。生成/再ラベル/独立評価まで費用を含める。特徴対照の条件内転移利益がない、又は同wall効果がない時に優先 |
| 容量/LR/探索費 | 低LR早期観測と尺度は既支持範囲を保持。幅・seed大量探索は原因分離が弱い。値改善が完成depthの損失で消える時は探索費を優先 |

## 保存・引渡し

local source SHAと公開commit/URLは自域source-map.jsonへ保存した。公開コードを取り込まず、新依存/モデル取得なし。old openedtest/173 raw・labelsを分析に使っていない。唯一の実作業は静的選定、科学job/NN/GPU0である。旧253の確認unusedから512KiBを移転し、旧retained512KiB・新forecast512KiB/guard768KiB、未知減額/親予約追加0。管理/read総180sを保守上限として計上し、旧費をresetしない。Git/indexは統括だけが扱い、停止後のpath/byte/SHAを渡す。採否と実科学は統括の後続具体配分であり、本稿ACKは主実験のgateではない。
