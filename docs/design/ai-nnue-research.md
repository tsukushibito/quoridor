# NNUE型Quoridor AIの研究方針

決定日: 2026-10-03。ユーザーとの議論から、最終目標と研究で重要な仮説を残す。[研究目標](ai-sigma-research-goal.md)が到達目標、[現行実行枠](ai-sigma-continuation-20261001.md)が実行期限・資源配分の正本。状態・担当・次課題はBeadsで管理し、この文書をタスク一覧にしない。

## 到達経路と設計の位置付け

### 2026-10-22の直接依頼：本家比較とjoint policy/value

人間の「コリドールも最強AIへ」という追加依頼を、既存goal内の新しい具体工程として採用する。Othello強化とは別goalで、source準備は並行し、shared Cargo・GPU教師/学習・公平な時間対局だけを実行・統合担当が調整する。Cedar BEST58305（`35cbb…`）、Control/LMR/path_tail、製品defaultを対照として保持する。323/342.17のprep/pipeline USERPAUSE、newE/oldfits96/sealsは新工程にも使用しない。

到達経路は **固定教師の模倣 → 同じ評価器による探索比較 → 有望候補の有限自己対局学習 → 独立比較** とする。最初にhybridの切替閾値を実装したり、大規模gridを回したりしない。旧18.2の4prefix・5教師行・2更新は機能確認であり、実学習や棋力の証拠ではない。

本家Claustrophobiaは固定v1.3.1のterminal `mcts::run_mcts` とそのweightsへ束縛する。Python/Torch/StaticHeadを毎手cold起動する費用を100ms比較へ無自覚に混ぜず、既存のengine/session ownerで一度準備して保持する最小の接続を優先する。起動・初回準備費は別に保存し、着手ごとの入力・推論・探索・返却を共通caller時計へ含める。独自常駐サービスは作らない。上流内部がboard-onlyなら履歴を認識する探索と同一とは呼ばず、goal-first/threefold/完全履歴の最終裁定は共通arenaが担う。最初の接続確認は別の未封印dev開始4family・両色8局、100ms/5ms、1探索thread、book/ponder OFF、200ply。cap到達を確定drawへ変えない。完成した合法結果をこの時計で返せない場合は不足を保存し、5秒や極端なsimulation制限を十分な100ms本家比較と呼ばない。1秒は別条件とする。

初回joint学習の出発案は、未封印の最大512 game/opening familyを結果前にT384/V64/H64へ分け、各family最大64の異なる非終局観測、最大32,768元観測とする。LR siblingsは同split、trueLRを加える教師attemptは最大65,536向き行。高残壁11..20を約半分、5..10と0..4を各約1/4の抽出目安とし、不足をコピーで補充しない。canonical局面/LR/共有祖先prefixの跨ぎを教師結果前に処理し、family根拠のない旧row bankのrandom splitを独立検証と呼ばない。Hはtrainer/selectorから隔離し、初回教師付与を必須にしない。事前学習への露出と今回未使用を区別する。

教師は固定Claustrophobia単体の同一joint forward、FP32の合法mask後temperature1 policyとraw STM value。visit分布π・探索q・終局zをこの静的出力と混同しない。Cedarの312特徴・32/32 shared/valueと尺度をwarmstartし、policy209だけを固定seedの未学習headから始める。既存trainer/exportを使い、fresh Adam beta(.9,.999)/eps1e-8/decay0、batch1024、既存multiplicityとLR反転0.5を明示する。旧optimizerの完全resumeではない。

一本の候補を2段階で学習する。head準備段は`freeze=value`、LR1e-3、最大4T相当。joint段はそのheadと同じCedar重みから`freeze=none`、fresh Adam LR3e-5、value MSE＋0.1×合法policy CEとする。joint段は最低8T・最大64T相当、約1Tごとに全Vと固定Tpanelを観測し、実draws・ceil・tailを入場前に解決する。有意改善deltaはmax(1e-5,1e-4×significant-best)、3回非改善でLR半減、floor1e-6、6回連続非改善でplateau STOP。T改善/V悪化が3観測続けば過学習STOP、非有限・資源・取消は即STOP。strict V joint最小BESTを選び、改善中の上限STOPも未収束pilotとして残す。教師1200秒、両fit段の独占wall合計900秒を出発上限案とし、必要な修正は結果前に実入力・資源と理由からconfigへ確定する。INITIAL/BEST/LASTと必要restartの実保持を算出して50GBへ結合する。value MSE、CE、teacher entropyとの差KL、合法top1/top3、層別coverage、draws/更新/LR/全費を別に保存する。

学習BESTの最初の探索比較は、同じnew valueによるMCTS(learned prior)対αβ(policy orderingなし)、およびそのαβ対旧Cedar αβの2対照を出発案とする。dev32family両色・各64局/計128局、100ms/5ms、同CPU/memoryと固定Control/LMR/path_tailで、実c_puct・上限・初期化/TT/resetを結果前に確定する。64局は大差と費用を見る規模であり、小差の決着を保証しない。orderingは必要なら同joint重みの別dev32familyで一つのON/OFFを確認する。新value・ordering・探索を一括変更した勝ちをMCTSの純因果とはしない。有望な一候補だけを未使用Hまたは追加固定した独立familyでSigma・固定Clausへ比較し、最終局数・family区間・停止はpilotの差・分散・費用から結果前に決める。

次の自己対局cycleはB/Cの自然結果から一世代・一学習・一独立比較へ有限化する。この段階では生成件数をまだ発行しない。完全履歴、game/opening/世代/model/search/seed/時間、温度処理前後のvisit π、定義付きroot STM q、実終局zを分離して保存する。新世代/旧best/教師anchor比率はcoverage・忘却・費用から一案を選び、独立同時間対局で更新を採否する。打切り・違法・timeout/UNKNOWNを勝敗へ捏造せず、native結果をbrowser優位へ読み替えない。実設定・担当・状態は既存configとBeads `quoridor-4lc.435`、観測は[研究知見](../research-findings.md)へ集約する。

最終目標はNNUE型で最強のQuoridor AI。NNUEは局面評価ネットワークの設計であり、探索方式ではない。NNUE評価＋αβ探索を主候補とし、必要ならNNUEを用いる他の探索も比較する。既存の方策・価値NN＋MCTSは、まずSigma同等を確かめる基準、学習データ生成、NNUEとの比較に使う。

現在の主軸はRustのNNUE評価＋αβとPython学習を用いる実装・学習・棋力比較。確認済みのSigma MCTSと既モデルは教師生成・基準・対照として再利用し、モデル差と探索差を切り分ける。重要な研究方向・データ・学習方式・特徴・モデルの変更は人間が選び、Rootが受入れ済み方針とタスクの許可範囲で配分する。自前PVモデルの完成をNNUE研究の開始条件にしない。

NNUEの棋力優位性はQuoridorでは未検証の仮説。公開資料の調査では既存のQuoridor NNUE実装・強い学習済みモデルを確認できていないが、不存在を証明したものではない。CPU短時間に適するという見込みを、実証済みの優位性として扱わない。

具体的な到達構成・初期構成・特徴の意味と次元・差分更新・距離cache・教師・比較方法は[Quoridor NNUEの特徴設計案](ai-nnue-feature-design.md)にまとめる。**現時点の完成形候補QF-T1は、各視点828の疎特徴（盤面312＋局所壁ペア516）、共有256幅の二視点NNUE、経路/移動16＋context4、532→32→32の後段からvalueと選択的136方策、αβ/PVS**。機械的に求める経路情報と学習する戦略判断を組み合わせ、同時間棋力で不要な費用を削る。未実測の到達案であり採用済みモデルではない。

推奨初期試作QF1は二視点の疎盤面312＋後段の距離2値とし、T1とは分ける。下記313入力は既存の予備診断用の基準案で、詳細案QF1は手番を結合順に分離した各視点312入力とする。T1の全実装・大量教師・自前PV完成を小試作の入口にしない。

## 最短距離を計算して与え、戦略判断を学習する

壁による通行可否から最短距離を機械的に計算できる。モデルに盤面から経路計算を学ばせる代わりに、計算結果を特徴として与える方針は有力。ただし、この距離は将来の壁配置や駒の飛び越しまで含む勝利までの実際の手数ではない。距離が同じでも手番、残り壁、代替経路、壁1枚による迂回の大きさで価値は変わる。

最初の試作候補は次の通り。採用済み仕様や必須の全比較ではなく、小さく判別できる案から選ぶ。

| 部分                   | 基本案                                                                 | 狙い・費用                                                                                                    |
| ---------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 差分更新する盤面特徴   | 両駒の位置81×2、壁位置・向き64×2、両者の残り壁数11×2、手番1の計313入力 | 固定座標・固定プレイヤー識別なら1手で変更する特徴を少数にできる。視点変換で毎手全入力を入れ替えない構成を選ぶ |
| 後段へ追加する経路特徴 | 各駒のゴールまでの最短距離、必要なら距離差                             | 密な距離マップを最初の差分更新層へ直接入れるより、更新費用を分離しやすい。距離差は冗長なので効果を実測する    |
| 必要に応じた拡張       | 駒と壁の組み合わせ、代替最短経路、壁への弱さ・配置効果                 | 迂回や位置関係の判断を助ける可能性。入力数、更新量、教師データ量と計算費用が増える                            |
| ネットワークと出力     | 浅い全結合モデルの局面評価、整数演算向け量子化                         | αβ探索の高頻度な評価をCPU/Wasmで実行。量子化前後の数値と棋力を確認する                                        |

入力数だけから速度・モデル規模を判断しない。NNUEには有効入力が少なく、毎手の変更箇所が少ない特徴が適する。距離マップ、合法壁マップ、壁の影響をそのまま全て入力すると、壁1枚や駒移動で多くの値が変わり、特徴生成・更新が支配的になる可能性がある。経路情報は少数の値を後段へ入れる方式と、より豊かな特徴との棋力・速度の交換条件を調べる。

探索・評価器・学習サイクル全体の改善候補と判断の考え方は[改善候補集合](ai-nnue-optimization-agenda.md)を参照する。個別の着手状態はBeads、観測と次の判断は[研究知見](../research-findings.md)で管理する。

## 距離計算と探索全体の高速化

壁配置から各ゴール列への距離マップを計算・保存し、壁が変わらない駒移動では新しい駒位置の値を参照する。壁変更時の更新と探索のmake/unmakeで、親局面のキャッシュを壊さず再利用できる実装を考える。合法性判定、特徴生成、手の順序付けで同じ距離・経路情報を重複計算しない。

必要な値だけを求めるBFSの早期終了、ビットボードによる到達集合の更新、既存経路が残る壁候補での合法性再検査省略、同一壁配置のキャッシュなどを高速化候補とする。個別の駒の距離が不変でも全マスの距離マップが不変とは限らず、キャッシュの有効条件を区別する。壁は両プレイヤーのゴールへの経路を残す必要がある。省略・近似で合法性や教師ラベルを壊さない。

NN単体の推論時間に加えて、合法手生成、BFS、特徴生成、差分更新、探索木・置換表、手の確定までを測る。Rust nativeのビット演算/SIMDの効果をWasmへそのまま仮定しない。主要な指標は同じ持ち時間での棋力と探索量、RAM、モデル配布サイズ。速い評価関数でも手の順序付けや枝刈りが弱ければ、壁候補の多い局面で探索が広がる。

## 方策出力によるαβ探索の手の順序付け

2026-10-03のユーザー指示により、評価値だけのNNUEに加え、評価値＋方策を出力してムーブオーダリングに使う構成も研究対象とする。NNUEの差分更新は出力を評価値だけに限定しない。置換表は既に探索した局面の最善手を優先できるが、未探索局面や残りの候補の順位を方策が補える。置換表があるだけで方策の効果が薄いとは判断しない。

五目並べ・連珠AIの[Rapfi論文](https://arxiv.org/html/2503.13178v1#A4)は、差分更新型Mixnetの価値・方策出力とαβ探索を組み合わせ、置換表を併用しながら方策で手の順位と探索深さを調整する。[実装](https://github.com/dhbloo/rapfi/blob/master/Rapfi/search/movepick.cpp)でも、置換表の手を先に試し、残りを方策・履歴等で順序付けする。Stockfish型の全結合NNUEと同じ構造ではなく、この実績はQuoridorでの優位性や方策単独の棋力寄与を証明するものではない。

| 比較候補                                           | 目的                                                         |
| -------------------------------------------------- | ------------------------------------------------------------ |
| 評価値のみ＋置換表・履歴・安い距離等の順序付け     | 方策なしの基準を作る                                         |
| 評価値＋小さい方策head、または別の軽量な手の採点器 | 追加推論費用に対して枝刈りと棋力が改善するか調べる           |
| 方策を根・浅い局面・候補が多い局面に限定           | 毎内部局面で計算する構成との費用対効果を必要に応じて比較する |

順序付けだけならsoftmaxで確率化せず、合法手に対応するlogit・スコアの順位を使える。初期比較では方策を探索順に用い、低い方策の手を除外する枝刈りや探索深さの変更は別の因子として扱う。壁候補が多いQuoridorで有効かは仮説であり、方策の誤りによる探索の偏りも見る。

価値評価器・入力・教師データ・探索設定をできる範囲で揃え、方策追加による価値精度の変化も区別する。方策生成・合法手対応・並べ替えの費用、探索ノード数・枝刈り・到達深さを測り、最終的には同資源・同思考時間の対局棋力で判断する。ノード数削減だけを高速化・棋力向上としない。根や葉の評価値のみでは方策の教師分布にならず、基準MCTSの根の訪問回数分布などを保存・利用する案を検討する。

これらは研究候補であり、全案の実装・学習や比較完了を他の研究の開始条件にしない。重要な優先順位は費用・知見を示して人間が選び、Rootが有効なタスクの許可範囲で実行を配分する。

## 学習と比較

棋力比較と自己対局データ生成はネイティブを主環境にし、Wasmは必要な数値・探索対応と製品動作の確認に絞る。大規模Wasm評価の完了を学習・ネイティブ比較の入口にせず、両環境の棋力認定を分ける。CPU/GPU、推論バッチと対局並列数は最小実測で選び、候補と参照の資源・思考時間を揃える。固定Sigma-Webをネイティブ上で動かす参照とSigmaのC++実装等を無告知で置き換えない。

推論単体の速さに加え、初期化・特徴生成・探索・輸送・記録を含む総費用、対局数／時間、有効学習局面数／時間と棋力を見る。必要なボトルネックから改善し、既存の教師・実装・評価結果を再利用する。個別の高速化や大きいバッチの導入を目的化せず、次の評価・学習結果を得る時間が短くなるかで配分を見直す。

Rust生成→Python学習→freeze/test→native arenaの小cycle接続は整備済み。代表的な大量入力の供給と有効な本学習・モデル採用は未成立であり、現状と限界は[研究知見](../research-findings.md)を参照する。Sigmaの重みをNNUEへ直接移植することはできない。基準MCTSの探索評価と対局結果をNNUEの教師として利用する案から始め、教師の誤り・偏りを引き継ぐ点、局面の多様性、終盤・壁配置への対応を評価する。自己対局や再ラベルで改善する経路も検討する。

学習損失や教師との一致だけで強さを認定しない。評価用の対局・局面を学習用データと分け、既知の教師局面への適合を汎化や棋力向上と混同しない。同じモデルで探索を変える比較、同じ探索でモデルを変える比較を必要に応じて使い、モデル・探索・実行速度の効果を切り分ける。NNUE＋αβとPV＋MCTSの総合比較では両方を含めた構成差として解釈する。

「最強」の比較対象・版と条件はRootが人間と具体化し、必要な独立レビューを依頼する。Sigma同等は最初の段階目標、最終的にはClaustrophobia等の有力AIも比較対象とする。CPUのみ／GPUあり、短・中・長の思考時間を分け、同じ実行場所・資源で測る。ブラウザUIを持つnativeサーバーAIとブラウザ内AIを、同じブラウザ実行として扱わない。NNUEは対局時CPUでも学習にはGPUを使える。GPUの有無だけで方式の勝敗を決めず、推論バッチ化・投入待ち・実探索への効果を測る。

GPU学習は明示タスクの期限・資源上限に従って具体化する。重要な変更は観測・競合案・全工程費を示して人間が選び、Rootは主張や採用判断に必要な時だけ独立レビューを依頼する。全候補の実装完了や相互承認を研究開始の条件にしない。

## 参考にした公開実装

- [Stockfish NNUE設計](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html)：疎な入力、少数の差分更新、量子化、CPU評価。
- [Rapfi論文](https://arxiv.org/html/2503.13178v1)：差分更新型Mixnetの方策・価値出力とαβ探索。方策による手の順序付け・深さ調整と置換表の併用を参照する。
- [Sigma入力](https://github.com/bartolomeo3000/SigmaQuoridor/blob/main/game.py)：8×9×9、駒・壁区間・残り壁・ゴールへの距離マップ。手番視点へ上下反転。
- [Claustrophobia入力](https://github.com/Plaaasma/Claustrophobia/blob/main/src/encode.rs)：16チャンネルと20チャンネル拡張。距離、最短経路、合法壁、距離差、壁1枚の影響を明示特徴化。手番視点へ180度回転。採用モデルでの有効構成は別途版を固定して確認する。

これらの特徴から棋力の優劣を断定しない。比較に使用するコード・モデルはGit版と入力仕様を特定する。

### 419：候補順位へ戻る葉評価の有限診断

[419保存報告](../../research-data/ai-sigma/nnue-loss-leaf419/report-ja.md)は、固定3親・H2/H3の共通候補木において、同じ葉のNNUE/D値を用いる完全backupと事前固定endpoint介入を対応させた。slot4/ply11 H2の同一葉[156,91]をD値へ置くと固定C内の156→68が変わる一方、H3には代替応手の未置換葉が元候補を維持する例がある。これは保存木内の数値的依存であり、Dの正しさ、C外を含む介入後root argmax、旧敗戦の因果、真のWDLや一般棋力を認定しない。旧warm95ms/TT4Kと今回cold/timeNone/TT1Mも区別する。

原nativeはOutput.finish後の全stdout再出力でcapture上限に達しFAILED、保存40COMPLETEとouter/later cleanupは別scopeとして保全した。今後のmeasure CLIは保存結果の小receiptだけを返す通常consumer修復を採用し、元40を再演していない。単一PV葉への説明を全代替応手へ拡張せず、未確定部分の新Search/介入/fitは自動発行しない。

### 429：量・露出・開始coverageを分けた比較条件

この節は429完了時の設計・費用提案を記録する。後の明示委任432で四fitと一候補の評価を実行した結果は末尾の432節に分ける。ここに残す「将来」「提案」は429時点の範囲である。

保存423のWはBEST43から新Sigma outcome zだけで追加学習した条件で、公開データとの混合ではない。末尾118更新まで新T/V lossが下がったが、必要更新数・原因・棋力改善は未確定である。Fは初期化だけでなくLR、warmup、更新量も異なるため、その訓練適合とV悪化から一要因の効果を取り出さない。[保存設定と曲線の分析](../../research-data/ai-sigma/nnue-data-expansion429/saved-learning-analysis/report-ja.md)を比較設計の出発点とする。

| 分けたい問い       | 条件の対応                                                          | 計算量と限界                                                                            |
| ------------------ | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| データ多様性       | 共通V12275と同BEST43、nested T3735/14940を29880 draws/117更新で比較 | 平均露出8/2。測定panelのsupport・全forwardや総wallまで同じとはしない                    |
| 同じ大viewの更新量 | 同じT14940の独立したshortと8露出runを比較                           | long119520 draws/467更新、tail224。訓練drawsも4倍であり同計算比較ではない               |
| 開始coverage       | 従来4/8/12/16ply recipeと2plyを同distinct3735・29880 drawsで比較    | 量と序盤を同時変更した一対で原因を認定せず、stock・game・family・同入力の対応を保存する |

現行callerではpartial batchが最終更新だけで、短い118更新は117×256+152=30104 draws、長いrunのstep118は118×256=30208 drawsとなり104多い。INITIAL/BEST/LASTのみの現行保存では非BESTの途中weightsも保証されない。従って現行経路で正確な三比較を満たす案は、小view8N、大view同じ8N draws、同じ大view8×4N draws、early matched-Nの8N drawsという将来の四fitとして費用を示す。117 full updates/29952 drawsや256整除の実Nを選ぶ場合も、元条件と同じとして黙って代替しない。途中partial batchやcheckpoint経路の新設は発行しない。

実数に応じて目安を解決し、重複や反復露出をdistinctへ数えない。元423のsplit/RAWとID18の明示的fit-view対応を残し、新viewの共通VをTから隔離する。初期化、正規化、z loss、reflection、fresh Adam、更新座標のLRを揃える。具体的なfit・評価条件と実費はデータ実数に基づく次の提案とし、429の生成・変換許可を学習や対局へ拡張しない。

現行の`mixture.training_view`は、省略可能な4MiB以下のFileRefで、本文の`cache_manifest_sha256`と昇順・重複なしの整数`indices`を実cacheへ結び付ける。選択可能なのは既存の適格T・game/stock cap後の候補の部分集合だけで、同cacheの適格Vは全件を保持する。未指定時の抽出は変えない。実viewは通常のordered Experiment.inputsとRUN全体の入力保護へ含める。これはnested/matched viewを表現するsource上の能力であり、実distinct数・cache census・新fitの成立を認定するものではない。

429の元160sliceと一度の変換では、1280要求／1204返却（1190GOAL・14true-threefold）／入力欠測76、適格T49911/V12275を保存した。量／2plyのstock18..20はT6/V0対T907/V223で、二cohortのcanonical familyは26共有する。実viewはquantity3735/14940、early3735で、目標3763/15052の不足を補充しなかった。四在庫帯のquotaだけを正確に4倍にし、各familyや個別stockを等重みとする比較ではない。

実shortは116×256+184=29880 draws/117更新、longは466×256+224=119520 draws/467更新。四条件の訓練＋測定上界2308648は保存した提案値で、実fit/INITIAL/native重み対応/対局の費用や結果ではない。small LR orbit3735は元partialに保存済み、large/earlyと旧423との直接model-input overlapはUNKNOWNのまま。詳細は[実データ・viewと費用提案](../../research-data/ai-sigma/nnue-data-expansion429/report-ja.md)を正本とし、新たなfit/eval/arenaを自動開始しない。

### 430：同一入力・更新列でのstatic教師比較

同じ選択T3763/common V2498、BEST43/fresh Adam、30104 draws/118 updates/tail152、reflection15038、実stream76f6467bで新Z/S/Cを学習し、LAST118だけを対局へ出した。S/Cは実際の反転盤面と完全historyから付けた別ラベルであり、旧z・splitを上書きしない。共通mixed_batch/train_mixtureがmanifest/configの教師名・column・row対応を消費し、三つの学習loopを複製しない。モデルごとに異なるSigma8/C20の正本encoderはコードに残し、NNUE特徴・数学は変えていない。終了済み419の専用実行field/branch/専用testはGit復元元を保全して撤去した。

固定64共有family・各両色128局ではCvsZ67/61、score.5234375、95%[.4609375,.5859375]で下限>.5はNOT_MET。SvsZ63/65、.4921875、[.421875,.5625]は記述的。全256GOAL/UNKNOWN0だが一般優越・劣位・等価・原因やモデル昇格の結論ではない。各教師への誤差低下と対局を区別し、元RAW/FAILED/費UNKNOWNを残す。[有限結果と原参照](../../research-data/ai-sigma/static-teacher-distillation430/report-ja.md)を正本とする。429の四fitは引き続き未実行提案である。

### 432：同じ実勝敗zでのデータ量・学習量・序盤分布の有限実行

[432保存結果](../../research-data/ai-sigma/nnue-learning-scale432/report-ja.md)では429の固定viewを用い、四独立fitを実行した。A/B/Dは29880 draws/117更新/tail184、Cは119520 draws/467更新/tail224。量small3735行/796familyとlarge14940行/811family、early3735行/149familyを区別し、同draw数のsupport差・同viewの学習量・分布差の三比較を混同しない。Cの途中117更新を独立Bへ代用しない。

既存common trainer/training_view/evaluateを維持し、追加のstock-family n/macro z-MSE、decisive/zero、Draw0 mean-abs、.9/.99飽和を同じpredictionから集計する。空層はnull、層family数は加算しない。固有view/seed/観測点/endpoint/表示・候補規則はconfig/manifestに置く。必要な新三定義だけを一度確認し、旧fitや成功suiteを再演しなかった。全newV12275/236familyは各観測点、TはA/D全3735・B/C8192panel、公開T8192固定、opened publicV419150はLASTのみである。

固定LASTのnewV family z-MSEはA.835774397/B.833926958/C.766460997/D.831157305。事前のnative適格B/C/D最小規則でC LAST467を選んだ。CのnewVはINITIAL.859740646から下がる一方、公開T panelは.428704088から.457743676へ増えた。公開V LASTもC.453408904と他三条件の.425695/.425904/.426614を併記し、未測定のpublicV INITIAL差や汎化の因果を作らない。

選択C対BEST43の独立固定192family/両色384局は185勝2分197敗、score48.4375%、95%[44.0104167%,52.8645833%]で事前改善基準未達だった。一度のfamily bootstrapだけを使い、A/B/Dの棋力順位・一般劣位・等価や原因を認定しない。実fit＋native2337787 logical rows、arena1670199748 charged nodes、内包時計の非加算と全費UNKNOWNを保存した。追加学習・対局・モデル/default昇格は自動発行しない。

## Cedar v1（シダー）：研究呼称と探索調整（2026-10-18）

Cedar v1は原324.7で研究優先候補になったClaustrophobia静的教師NNUE、新C BEST58305、weights `35cbb976be12e24ac6ff8204bf1937fd79673484ddc792065b6aabb6cbb36f0e` の名称対応である。原Cラベル・model identity/path・重み・製品登録をrenameせず、固定の特徴・出力数学を維持する。人間の直接決定により、まず両側LMR ON/depth_rankを固定したCedarのpath_tail ON/OFF棋力比較（quoridor-4lc.324.8、元512両色1024局/16G）を行い、並行設計するLMR調整（quoridor-4lc.324.9）では現depth_rank対OFFから少数・一要因候補を検証する。既存共通search/arenaと解決済run configを使い、候補選択データと最終確認を区別する。最適は試した条件内の選択だけとし、本家Claustrophobia/Sigma比較は探索調整後の判断へ送る。新教師・学習・モデル/default昇格は含めない。原結果と最新判断は[研究知見](../research-findings.md#cedar-v1シダーの探索調整へ方針更新2026-10-18人間直接決定)、具体scopeは[第一段階契約](../../.artifacts/research-team/integration324/cedar-path-tail-strength-v1/task.md)と[有限LMR計画](../../.artifacts/research-team/integration324/cedar-lmr-tuning-v1/task.md)に置く。

### Cedar第一段階の有限結果とLMR条件

原324.8の再利用512family両色ではpath_tail ONが514勝1分509敗、得点率50.244140625%、事前family95%区間48.53515625〜51.953125%で未決着だった。同等性/効果不存在とはせず、既定やモデルを変更しない。次のLMR有限選択・確認は事前未決着分岐の両側path_tailを使い、depth_rank/OFF/fixed_oneの試した範囲だけを扱う。旧96保存修復と新928の異なる実tuple・原FAILED・費用と、別の深度/探索量addendumを分けて保持する。[原結果](../../research-data/ai-sigma/cedar-path-tail-strength/report-ja.md)、[研究知見と次判断](../research-findings.md#cedar-path_tail-onoffの原1024局32482026-10-18)を参照する。

### 現行確認後のLMRパラメータ調整と独立評価（2026-10-19 JST、人間直接指示）

「調整まで計画に含めておいて」という直接指示により、以下を後続計画へ加えた。元324.9の確認と保存解析は完了し、UNRESOLVED_RETAIN_DRとして現行depth_rankを維持する。続く324.14も両比較を完了した。これらの成績・原枠・通知先は変えず、324.9.4でCedar・現Controlを固定したLMRのtyped設定・整数範囲設計を完了した。追加の人間直接指示により、係数の数値調整前に[324.15の駒・壁近傍優先](lightweight-move-ordering-v1.md#履歴同点群の駒壁近傍優先32415後続計画)を別候補として比較した。全384局の事前規則は候補を支持せず、現Control・履歴同点の追加採点Offを維持する。このorderingとCedar・共通head・path_tailを固定した324.9.5の粗比較128局・SPSA8更新128局・一設定確認320局は完了した。確認側は候補163勝0分157敗、family95%区間48.125〜53.75%で、結果前の規則から基準係数0.7844 / 2.4696 / 3 / 4 / 3を維持する。追加探索・対局・学習は発行しない。現行枠の残額・UNKNOWNを新しい権利にせず、後続の状態と参照は既存の324/324.9のBeadsへ置く。

続く人間の「その計画で進めて」により、実行順序を、元L2保存解析の完了→[324.14の履歴同点群への追加採点ON/OFF比較](lightweight-move-ordering-v1.md#cedar履歴同点群だけの安い二次採点324142026-10-19人間直接依頼)と現状維持の判断→追加された324.15の近傍候補検証→採用または現状維持の構成固定→LMR係数調整と独立確認、とする。14は現行depth_rankと評価器を固定し、既存TT/PV/killer/合成動的履歴全体の有無を比較しない。固定済みの連続時間・同時間棋力の両段階を行い、差が曖昧なら現行方式を維持して次段階へ進む。結論を得るために無限定増量しない。typed LMR設定化・係数範囲の設計は並行できるが、係数探索中はordering・評価器を同時変更しない。後続の具体規模・停止・設定範囲は着手時に既承認方針内で解決し、現L2・旧UNKNOWN・未使用quotaを転用しない。実時計とreader/native STOP・資源だけを調整し、parent closeや人間ACKを入口にしない。

14の採否は、固定128局/64familyの正規資格が揃い、事前family95%区間の下端が0.5を上回れば、候補を次のLMR調整用の研究ordering設定へ選ぶ。それ以外は現Controlを維持する。TIMEの有限基準は別に報告し、時間改善を追加の採用条件にせず、時間が中立・悪化でも棋力側を実施する。未確定を効果不存在と呼ばず、製品/generator/model/defaultをこの判定だけで変更しない。

324.14の全128局/64family/UNKNOWN0では候補65勝0分63敗、得点率50.78125%、唯一のfamily95%区間は46.09375〜55.46875%だった。事前規約の下端>50%を満たさないため、**Controlを維持し、履歴同点時の追加採点はOffに固定する**。連続時間の事前基準も未達だったが、棋力比較は予定どおり実施した。優越・同等・効果なしの認定にはせず、この構成とCedar・path_tailを固定して次段階へ進む。[14の保存報告と適用範囲](../../.worktree/assets/perf/cedar-history-tie-ordering-v1/numeric-v1/final-saved-analysis-v1/report-ja.md)。

324.9.4のtyped入口はsource commit `94825364`、型初期化の限定修正`281a7bd5`として統合した。`lmr_parameters`の完全な型付き設定でintercept、log_divisor、min_depth、min_rank、max_extraを渡し、省略時と明示baselineは元の整数表・namespaceを保つ。customはsessionで一度tableを作り、実効係数bitとthreshold/capをTT・履歴のreset/記録へ束縛する。baselineは0.7844/2.4696/3/4/3、許容範囲はそれぞれ[0,2]/[1,4]/[3,63]/[4,63]/[0,8]。有限表算術ではintercept±0.05で123cell、divisor±0.10で253cellが対向設定間で変わったが、実探索の訪問頻度・費用重み・棋力は未測定である。

新しいRust5定義は各1件PASS、affected Clippyとreleaseを完了し、[通常BUILDと実imageの資格](../../.artifacts/research-team/integration324/cedar-lmr-tuning-v1/typed-parameters-adoption-v1/software-v2/collection-v1/qualification-and-STOP.json)を保存した。最初のrunner型検査は既存の現役fixtureにoptional fieldが欠けて失敗し、`None`の初期化だけを修正して成功済みAI3件を再演せず続けた。これは設定・softwareの資格であり、係数数値調整や新対局の発行ではない。15は後続の人間並行指示から近傍候補の限定関連確認・Main採用・新7定義各1PASS・affected Clippy/releaseのsoftware資格まで完了した。続く研究判断でTIME128calls/16sessions/128Mを維持し、棋力側は旧未実行128局案から保存book全192family/384局・12×250M非融通/3Gへ具体化した。全資格後の唯一family95下端>.5を採用条件とし、TIMEは採用gateにしない。新15の1088MiB保持と実資源/STOPの通常入口から比較し、曖昧ならControlを維持して追加反復しない。係数調整はその構成固定後とする。

1. 共通LMR経路に対し、係数・開始深さ/順位・追加減深上限を既存typed設定から与える。省略時の現行`depth_rank`動作と保護条件・再探索・停止を維持する。実効設定全体をTT/ordering再利用のnamespaceと実行記録へ束縛し、条件の変更ごとにコードを書き換える運用にしない。調整専用の複製探索器や汎用制御frameworkは追加しない。typed設定化・範囲設計と、別途有限化する数値調整を区別する。
2. 源流の有限算術で整数丸め後の減深表が同一になる無効な摂動を除き、係数範囲・摂動幅を選ぶ。表の差を実訪問頻度・効果へ変換せず、保存頻度がなければUNKNOWNとする。その確認だけの新しいprofile campaignを入口に足さない。実探索は整数深度のままとする。
3. 原15完了後の研究判断により、最初は定数項0.7844とlog積の除数2.4696だけを調整する。開始深さ3・開始順位4・追加減深上限3、整数丸め、保護・再探索条件を固定し、離散条件を同時調整しない。少数の粗い比較と有限SPSAについて範囲・摂動幅・step/decay・更新数・少数両色pair・候補選択/停止を結果前に解決する。各更新や最終確認を機械的512局にせず、総games/nodes/実wall/setup/control/回収費・同時RAW/保持寿命と50GB内forecastを一度具体化する。旧未使用quota/UNKNOWN/wholeは転用・返金しない。
4. 調整に使った開始局面・対局とは別の開始局面で、選んだ一設定と固定基準を独立比較する。同時間の棋力を主目的とし、nodes・再探索・完成深度は補助指標とする。確認局数は期待差、family単位の不確実性と費用から決め、512局を常に十分・最適とは扱わない。現行L2を後から調整用へ転用せず、独立確認の結果で再選択しない。
5. 将来のNNUE更新との交互改善では、NNUE比較中はLMRを固定し、LMR調整中はNNUEを固定する。有望なモデル更新時にはLMRを再確認するが、毎学習で全面SPSAを必須にしない。この計画はUSERPAUSE中の学習・生成を再開する指示ではない。

既存task sessionを自然な境界で再用し、新しい常設役や周期監督を設けない。実施の入口で必要な資源・有限規模を通常解決することと、人間の再承認や現在の確認作業へのACK gateを作ることを区別する。全FAILED/RAW/UNKNOWNと費用、50GB、323/342.17 USERPAUSE、封印、現行model/weights/defaults、foreign変更を保持する。

324.15は全384局・192両色family・UNKNOWN0で完了した。Neighbourは196勝1分187敗、family score51.171875%、唯一のPCG64/10000/seed3241520261020/linear95区間は48.046875〜54.296875%。事前の下端>50%を満たさず、**Control・tie extra Offを維持し、追加反復しない**。TIME128calls/16sessionsも元AND基準未達だが、棋力採否のgateではない。一般優越・同等・効果不存在・Elo・model/default昇格は認定しない。[原結果・来歴・限界](../../.worktree/assets/perf/cedar-history-neighbour-ordering-v1/numeric-v1/final-saved-analysis-v1/report-ja.formatted.md)、[Root有限受入れ](../../.artifacts/research-team/integration324/cedar-history-neighbour-ordering-v1/final192-route-v1/final-acceptance.json)。9.4の設定化と整数範囲を再用した324.9.5の有限576局も完了し、上記の一設定確認から基準係数を維持する。旧15/L2/14/13/UNKNOWNや未使用枠を転用せず、ordering・評価器を同時変更しない。

324.9.5の終端候補はintercept0.7790528198594694 / log_divisor2.4755123490139317、離散条件3/4/3は固定で、基準と整数表10セルが異なった。事前分離したfamily32..191の160両色pairを唯一の確認標本とし、PCG64 seed3249520261020 / 10000 / linear95を全320資格・実STOP後に一度だけ実行した。得点率50.9375%、下端48.125%は事前採用条件>50%を満たさず、**RETAIN_BASELINE、追加反復・再選択なし**。coarse/updateの256局を合算せず、歴史的432/15露出YES・訪問頻度UNKNOWN・一般優越/同等/無効果を認定しない限界を保持する。[結果・費用・適用範囲](../research-findings.md#cedar二係数lmrの有限調整一設定確認を完了324952026-10-19)、[原576完了packet](../../.worktree/assets/perf/cedar-lmr-tuning-implementation-v1/two-coefficient-recipe-v1/future-confirmation-v1/final-handoff-v1/packet.json)。

### 五設定調整の不完全停止とSigma対Cedar小試験（2026-10-19）

人間直接依頼の324.9.6は、整数座標384局、二係数64更新1024局、最後の一設定512局を最大1920局/30.72Gとして結果前固定した。最初のdepth128局は正規完了し探索用にdepth4を選んだが、続くrank比較が親commonメモリguardで停止した。保存90行のrow predicateはPASSでも閉じたnormal publicationとterminal node会計が欠けるため、rank feedbackはINCOMPLETEである。元規則に従い後段SPSA/確認を止め、別中心から再開・補充せず、現行基準0.7844/2.4696/3/4/3を維持する。部分rowの判定を原FAILEDの成功や、理論表差からの実訪問頻度へ読み替えない。[元結果・不明点・費用](../research-findings.md#cedar五設定lmrのrank段階は不完全停止324962026-10-19)。

別の人間直接依頼324.19は、同じ現行Cedar NNUE＋αβ/PVSと固定Sigma policy/value＋原MCTSを100ms/5ms・先頭8 canonical開始の両色16局で比較した。保存原出力の通常predicateを一度だけ判定した別DATA_VALIDATEDはCedar6勝0分10敗/UNKNOWN0、pairは1勝1敗6組・両敗2組。元normal operationの省略値/null比較FAILEDは変更していない。今回からモデル単独の優劣、一般棋力、NNUE＋MCTSや本家Claustrophobiaの成績を推定せず、新policyの学習・大量比較・追加調整は発行しない。[原条件・保存判定・限界](../research-findings.md#sigma-mcts対cedarの16局小試験324192026-10-19)。

その後の人間直接指示により、324.9.6はインフラ停止からの前向き回復へ進める。元のINCOMPLETE/FAILEDは保存し、保存済み成功90行を再対局せず欠測6枠も補充しない。結果前に固定した両候補共通29完全familyを使い、真正未入場の元op7・32局/512Mの通常資格完了後だけrankを選ぶ。過去RSSは不明のまま、実証したPID再利用時のRSS誤計上だけを最小修正し、既存1laneと管理用RAMを明示して再開する。最大1920局/30.72G、元モデル・時計・family split・後段採否は維持する。[回復規則・診断と限界](../research-findings.md#cedar五設定lmrのrank段階は不完全停止324962026-10-19)。

### 五設定調整のfirst32後を前向き改訂（2026-10-19、人間直接指示）

探索用4/6/4は小標本の暫定点であり、極大値とは認定しない。受付済みfirst32ジョブ`0a8a9255-7e4d-4584-b4e9-de4f12fa3e21`の512局/8.192G・入力・caller・通知先・元の一度の回収を凍結したまま、未発行の後半32更新だけを置き換える。旧64更新recipe・後半template・結果を上書きせず、first32全32 operationsの正規資格・UNKNOWN0・実native＋collection STOP後に、その最後の更新後中心を使う。途中bestを選ばず、旧64更新完了とも呼ばない。

新しい後続は、係数中心とcap4を固定した8対照×32局（各512M、計256局/4.096G）、選んだ一つの開始条件で16更新×16局の短SPSA（各256M、計256局/4.096G）、最後の一設定512局/256確認familyの順とする。広域候補(depth,rank)は(3,6),(6,6),(8,6),(4,4),(4,12),(4,16),(6,12),(8,16)、基準は4/6。正規完了した候補の得点率>50%から最大を選び、同率は基準からのL1距離、次に(depth,rank)昇順で決める。改善候補がなければ4/6を保つ。結果前に同じ整数表を省略・重複排除できるが、余りを他へ貸与しない。予定した実対照が不完全/UNKNOWNなら依存経路はINCOMPLETEで止める。32局は粗選別であり、極大値・一般優越や表差からの訪問頻度を認定しない。

短SPSAはfirst32の中心x32を元の正規化base/scales/box内で継承し、元c/a式のk=32..47、step clip0.08を使う。新しい16の均衡Delta・入力/色/seed/順序・対応と時間/保持寿命を後続結果前のconfigへ固定する。tuning256はfirst32で既に使う計画なので、未入場の後半logical枠と未露出familyを区別し、tuningのみのラベル非参照割付と共有family依存を明示する。確認256familyは選択に使わない。384+512+256+256+512=1920局、6.144+8.192+4.096+4.096+8.192=30.72G、75600秒と50GBを維持し、実費控除・元FAILED/6 UNKNOWN/opaque-heldを保つ。最終一設定・唯一のfamily区間・結果後の再選択禁止は変更しない。[採用済みの版別計画](../../.artifacts/research-team/integration324/cedar-lmr-tuning-v1/five-parameter-v1/post-first32-revision-v3/plan.json)。実行中は軽い私有plan/configだけを準備し、新しい重要な選択・中心継承境界だけを既存Maxが関連確認する。20の独立準備も継続し、重い工程は実native＋collection STOPへ配分する。親closeや人間/相談の返信を入口にしない。

first32は全32 normal operations・512局/256完全pair/UNKNOWN0で完了し、実native＋collection STOPを受けた。更新後中心x32は元base/scales上で`[0.2226745836277075, 0.02981210828444443]`、係数は`0.8289349167255415 / 2.4815248433137778`、整数は4/6/4である。この中心だけを広域比較へ渡し、旧64終端・途中best・次trialと区別する。元512成功局は再対局対象から除外する。[first32と実STOPの受入れ](../../.artifacts/research-team/integration324/cedar-lmr-tuning-v1/five-parameter-v1/first32-result-acceptance-v1/acceptance.json)。

### Claustrophobia単体教師のpolicy/value学習接続環境（324.18.2、2026-10-19）

人間直接指示により、現Cedarを新artifactの初期値として既存policy209を明示有効化し、既存単一train loop/optimizer/sampler/exportへjoint policy/value targetを接続する。版固定Claustrophobiaの既存`static_teacher_heads.policy_value`一回のforwardから、合法mask後policy分布とSTM valueを取得する。core209・STM/左右反転・jump/H/V・value符号/尺度・splitは既存正本を共用し、stream/chunk/manifestとcheckpoint/restart、Python→Rust policy/value export・fingerprint/新head identityを対応させる。元value教師にpolicy列があるとは仮定しない。既存18.1の4prefix/48sim確認と上限は独立に保持する。

既存作者High18を自然境界で順次再用し、私有source/configから着手する。変更した座標/目標/split/export境界だけ既存Maxが関連確認する。必要な実接続が不足する場合だけ、最大16真正fixture/教師16行/optimizer2stepの機能smokeを一度、実条件を固定して実STOP後の適合windowへ置ける。本学習・全件教師付与・巨大ラベル配列・大量checkpoint・棋力campaignは未発行で、現value-only Cedar/model files/default/数学・全pause/seals/foreignは変えない。20やLMR後続はこの新準備を待たない。[完成条件・担当・資源・限定確認](../../.artifacts/research-team/integration324/nnue-policy-value-training-v1/task.md)。

### 広域比較完了とshort前のordering分析（324.9.6、2026-10-19）

first32中心を固定した8対照は256局/128完全pair、全normal manifest/data PASS・UNKNOWN0で完了した。候補順の得点率は0.5/0.5/0.53125/0.40625/0.53125/0.46875/0.4375/0.40625。固定した最大点・L1距離・tuple規則から、係数0.8289349167255415/2.4815248433137778、深さ8/順位6/上限4を探索用に選んだ。16共有tuning family・既露出開始での粗選別であり、極大値・一般優越・CI・default変更ではない。元256成功局は再対局から除外し、旧6 UNKNOWN/1.536G opaque-heldを保持する。[通常結果・選択・実STOP受入れ](../../.artifacts/research-team/integration324/cedar-lmr-tuning-v1/five-parameter-v1/revised-wide-result-acceptance-v1/acceptance.json)。

人間の順序確認に従い、この実STOP後は既存17の52探索→残壁別tie機会・実順位変更の保存分析とordering変更の具体的根拠の判断→20診断78探索の窓を維持する。この17判断を後続short16更新のnative開始前に返す。元384局比較後のRETAIN_CONTROLを履歴として残し、機会数や順位変化だけで棋力改善・採用を認定しない。具体候補がなければControl/ordering固定でshort係数再調整→元独立512へ進む。候補が具体化した場合は必要な有限検証・未使用確認集合・資源の扱いを具体報告し、この通知から新ordering実装・追加対局・上限増加を自動発行しない。同じ設定の最終確認を先に重複実行せず、親close/人間返信・一律ACKを入口にしない。保存分析は元normal出力の公開counterだけで、欠落はUNKNOWN、新observer/観測再計算/旧RAW再読は行わない。

18の元有限接続は真正captured test artifact f899上で4prefix各12sim・計48 real NNUE heads、constructor/failed0を完了し、元fake9を含む57/64・head48/256、実native＋collection STOPを受け入れた。uniform/ScalarFTの機能接続であり、learned policyやrelease image d0eでの速度・棋力資格とはしない。元preentry FAILED2件・費UNKNOWNは保存した。[元4prefixの結果・実STOP受入れ](../../.artifacts/research-team/integration324/nnue-mcts-foundation-v1/finite-result-acceptance-v1/acceptance.json)。新18.2のjoint教師/学習環境は独立の私有source準備として続き、本学習・全件教師付与は未発行である。

17の元52探索の保存分析では実際のtie/class並べ替え・pull順位変更が確認されたが、新ordering候補を支持する根拠には至らずControlを維持した。20の元診断78も実native＋通常回収・解析STOPを終え、行参照準備一候補の採否は別窓とする。レビュー済みの短期continuationを現行Main caller分離と合成し、採択8/6/4・x32を継ぐ元16更新→独立512局へ通常継続する。中立templateは実行せず、normal parameter ownerが各更新の両armを導出する。新候補/確認集合の再選択や追加局、旧FAILEDの成功化は行わない。[実分析・制限と継続境界](../research-findings.md#残壁別ordering機会の実保存診断324172026-10-19)。

短期16更新は全正規256局/128pair/UNKNOWN0で完了し、終端のみの係数`0.8268918342000571 / 2.493874970133201`・8/6/4を元独立512局の一設定へ固定した。元基準との有効表が異なりskip条件は満たさない。確認集合は選択に戻さず、元1ea image/同Cedar/同100ms/元相手条件を保つ。20の行参照候補はsoftware PASSまでで、性能は元104 ABBA未実施、最終確認のimageには使わない。[正規短期結果・会計と未実施工程](../research-findings.md#五設定調整の短期16更新と最終一設定324962026-10-19)。

### 五設定LMRの最終確認と基準維持（2026-10-19）

原独立確認512局/256完全family pairは全正規資格・UNKNOWN0で終了した。固定した終端候補0.8268918342000571/2.493874970133201・8/6/4は249勝0分263敗、得点率0.486328125。唯一の元family bootstrap区間[0.453125, 0.51953125]は事前条件lower>0.5に達せず、元基準0.7844/2.4696・3/4/3を維持する。一般劣位・同等・無効果や極大値を認定せず、確認結果で選択へ戻らない。原1920slotsの1914資格済み/旧rank6 UNKNOWN、opaque-held/FAILED/費用・歴史的露出/lineage依存を保持し、このcampaignから追加対局や再CIを発行しない。製品・モデル既定は不変。[確認結果・一度の区間・会計と限界](../research-findings.md#五設定lmrの唯一の最終確認は基準維持324962026-10-19)。

18.2のjoint教師/単一train loop/restart/export接続はMainへ統合したが、実corelib softwareは初回コンパイルの型module参照を修復中であり、新Rust3・実教師/2update機能smokeは未資格である。完成条件や本学習未発行は変えず、旧metadata成功を再演せず実未完工程だけを進める。20の元104連続Search比較も別の真正software/資源・実STOP窓へ置き、親closeや返信を入口にしない。

18.2の実softwareは新Rust3各1PASS・affected Clippy・現release cdylib生成を完了した。初回型パスと新テスト内Clippy書式の元失敗を保存し、成功済み定義を再演しない。新corelibの3公開symbolと実STOPは確認済みだが、最大16教師/2updateの機能smokeは未入場であり、本学習・全件教師の許可や学習済みpolicy品質は推定しない。20の元104ABBAを次の適合窓へ置き、18.2の軽い設定は並行、Torch等はその実native＋collectionSTOP後に配分する。[実softwareと残る接続](../research-findings.md#joint-policyvalue接続の実corelib-software資格3241822026-10-19)。

2026-10-19の人間直接指示により、今後の追加LMR広域比較は、現行orderingの小規模順位品質診断と具体候補があればその有限採否を先に決めてから具体化する。終了した元1920/final512/249勝263敗/RETAIN_BASELINEは確定保存し再開しない。policy導入後も変更がLMRへ及ぼす影響を見て必要範囲だけ調整し、毎回全campaignを再演しない。18.2の接続環境は並行継続する。[順位品質診断の条件](lightweight-move-ordering-v1.md#現行順位の質を確認する有限診断324212026-10-19人間直接指示)。

18.2の固定4prefix入口は、既存native SigmaContext・trueLR・model_keyとPAIR37 publisherを再用するconfigured `prefix_fixture` としてMainへ統合した。T0,2/V1,3を固定し、同一/LRのcross-splitを拒否し、self-LRは補充しない。限定source確認はSOURCE_CLEARであり、新Rust2・publisher1・新prefix symbolを含むcdylibはこれから実確認する。旧metadata成功や旧Rust3は再演しない。機能smokeは最大8 orientations/16教師attempts/TOTAL2更新で未入場、本学習・全件教師は未発行のままである。[固定sourceと限定確認](../../.artifacts/research-team/integration324/nnue-policy-value-training-v1/prefix-software-v1/source-adoption.json)。

固定prefix入口の新Rust2・publisher1・affected Clippy・新cdylibが実PASSとなり、prefix_keysを含む4公開symbolと実STOPを確認した。旧成功定義の再演はない。これにより元c27に無かった真正fixture入口のsoftware依存を解決したが、actual class manifest・現model stat・normal Experimentと最大16教師/TOTAL2更新の機能smokeは未完である。[software結果と範囲](../research-findings.md#固定prefixからjoint学習fixtureへの実software接続3241822026-10-19)。

18.2の環境構築は一度の真正機能smokeまで完了した。固定4prefix/4 classes/5向き、C教師5行、実step1中断とLAST/statusからTOTAL2更新へのrestart、native shared/policy fingerprintとexportの対応を保存した。既存Cedar/value-only/製品経路は維持し、機能確認モデルの研究採用や本学習・全件教師を発行しない。[実結果と限界](../research-findings.md#claustrophobia単体教師のjoint学習接続環境を機能確認3241822026-10-19)。

### 435永続接続の限定software到達点

追加の[履歴系列・分割・publisher境界](../../research-data/ai-sigma/quoridor-strong-ai435/trajectory-input-software-v1.json)は、既存InputConfigへ任意の有限trajectoryを接続し、native完全履歴/ContextRecord、壁層quota、exact/LR重複と同系列/prefix/endpoint componentを分割前にまとめる。H=Testの全native keyを教師/cache前に排除し、欠損・衝突・実T/V/Hを残す。既存single-root/4:1経路は現役のまま。512×200は生成pathの上限案であり、prefix再生・native key・二乗component joinを含む全仕事の上限ではない。実bulk保持/全工程CPU・期限と実分割を凍結してから教師へ入場する。

独立source確認はSOURCE_CLEAR、新Rust4・関連Clippy・measurement compile・releaseも通った。元E0282 compile失敗はテスト未実行のまま保持し、新fixtureの2型注記だけを直した。software outer169.397484997秒へ内包command秒を加算しない。MainのPythonはRuff100の整形差だけで作者版と全AST一致。最終の同source再検査上限を初回と同じ64MiBに揃える修復も一度含む。実512系列・教師・H/J fitの成功ではない。

本家正常接続用の新dev4根は旧single-root入口で4/4生成済み。Root回収コードが入れ子JSONを誤読した外側FAILEDと、正常native出力を分け、同じ保存出力を再抽選せず回収した。feature callbackライブラリのcompile/symbol資格は実モデルロード/forward/100ms返答とは区別する。次の8局はその実モデル/setup/同時計の正常入口を束縛し、Cedar/defaultを維持する。

[435のsource/software記録](../../research-data/ai-sigma/quoridor-strong-ai435/persistent-source-software-v1.json)は、persistent子の一回初期化と各手reply、最後のEOF/group/direct-waitを分離し、R1/O1修復後の3関連検査・Clippy・measurement compile・releaseを記録する。旧FAILEDと旧sourceでのcat成功は保持し、今回のモデル応答や棋力へ資格を転用しない。PythonのMain統合は共通Ruff100へ整形し、author sourceとの全AST一致を確認した。

Bの出発上限はT384/V64/H64、各family64 unique観測、32768元行（trueLR込み65536向き、H無ラベルならT/V向き57344）。wall11..20を半分、5..10と0..4を各四分の一の目安とし、独立fullhistory/family・LR重複/共有prefix除外の根拠と不足を教師前に固定する。例Hは元Cedar shared/value固定＋fresh policy209、freeze=value/LR1e-3/max4T。Jは同Cedar＋保存headからfreeze=none/freshAdam3e-5、value MSE＋.1legal CE、min8T/max64T。fresh Adamとphase境界を完全resumeと呼ばず、実T・batch1024・draw/ceil/tail・有意改善/LR半減/過学習/plateau STOP・V選択を入場configで確定する。H/J合計fit900秒・teacher1200秒は出発案で、上限停止を収束成功に変換せず、既存models/defaultを維持する。現時点でこの入力・教師・fitは未発行。
