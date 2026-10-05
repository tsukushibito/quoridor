# Sigma比較条件・事前判定・H1計測案の独立検証

SIGMA-COMPARE-CRITIC / 試行1 / 契約版1
目標issue quoridor-4lc、子issue quoridor-4lc.4。
報告元 critic / 01a0f31d-8227-7e03-a7e6-915b4918c11b。
報告先 coordinator / 01a0f31b-3409-75f2-a30e-453a50484f94。

**判定**: 固定Web NN-MCTSを主参照にする方法は支持する。C++ tournamentは独立したnative候補であり、Webと同じAI設定ではない。現コードのsnapshot・時計だけでは正式比較は不成立。H1の計測は下記の排他分母・祖先情報・overhead確認を条件にgo、最適化の採用と棋力/速度の達成は保留。非劣性はペアを単位とする固定標本の方法を提案するが、近接した棋力を十分な検出力で認定する両platformの標本は今回の残枠に保守的には収まらない。

## 契約・実施内容・入力

[目標契約版1](../design/ai-sigma-research-goal.md)を全文読み継承。[子契約](../design/ai-sigma-contract-critic-comparison.md)、AGENTS、common/critic、team design、AI設計§8/14.4/14.5、storage policy、handoffを確認した。旧準備試験契約を今回へ流用していない。開始は2026-09-30 17:45:48 UTC、当役期限は18:15:48 UTC。全体期限は2026-10-01 01:17:58.145139 UTC/JST10:17:58。18:02 UTC時点の全体残りは約7時間16分。30分以内の限定読取・方法確認、1CPU/1GiB/32MiB、GPU0、再委譲0。

作業場所 /workspaces/quoridor/.worktree/ai-sigma、branch codex/ai-sigma、HEAD 1482df8da6dd91c95db211aeaa914af775b2bc76。自子issueだけclaimし、目標・起動検証.1・他担当issueの所有者を変えていない。唯一のファイル書込みは本報告。ソース・registry・主checkout・モデル・依存・lockfile・UI/描画/M2を編集せず、build/性能測定/対戦/学習/モデル取得を開始していない。

[初期仮説報告](ai-sigma-hypothesis-initial.md)のSHA256は指定8b4938e6bd1774a5313f808f8c5c0de3a67618c00cc63a4cd6efd404fde9a032と一致。[基盤初期報告](ai-sigma-steward-initial.md)も指定52b8d53b07cf725f1b53510048abfd0c4d4d13b03461f0c814e16695cb4ff5a5と一致。launch.jsonの移入・期限情報を確認した。これらは証拠・提案であり、性能・正しさを報告者間の合意で認定していない。

### 読んだコード版と途中変更

17:51–17:52 UTC頃に読んだB0のposition.rs、ai/lib.rs、measure_native.rsは初期報告と同じhashで、HEAD基準コードとして以下の説明に使用した。
- crates/quoridor-core/src/position.rs: 0a2a1c26e6d4e5fb41fb58b69c92ab5f1d082b8e2da2dc26440b2eaec22d57f7
- crates/quoridor-ai/src/lib.rs: f18b5a2b9bcdf0646a1eccaca9e5191884a6910a66fe3e22fe03ec7a329ebdec
- crates/quoridor-ai/src/bin/measure_native.rs: a32ec56a90cfb25469100cc7b3ecfb9c5976bd81d52dd51855280668cd791d2b

17:58:57 UTCのhash化時にはexperimentのprofiling変更が入った。18:01:53 UTCにも以下が同じだった。HEADは変わっていない。
- position.rs: b12e79a99cf3441cf4acebbea1b827dce24b02db6fb2269021964872535e3ab6
- ai/lib.rs: 7ff1a13dceda7f3f2cb831321bdc56e509808c09006b697901e8328a924f8a21
- 新規 core/src/profiling.rs: 22acb71670ae5af82bdcab4304b9cfb48a0b40eec1972d703983c73bf2c40299
- 新規 ai/src/bin/profile_native.rs: 3de35f93278084c83d778c0b9143cbe3b7dd84416da9ca2991f4182ba3d17ab8

読取diffはoptional profiling span、cap counters、feature wiringの変更だった。これらの現在版をH1計測の方法について限定読取した。ビルド済み正しさや最終計測器の受入れを行ったという意味ではない。以下のローカルmanifestは17:58:57 UTCの観測であり、後続のexperiment成果物の版を代弁しない。

## 独立一次照合の支持・不支持・保留

Sigma固定commit: **751186344fc52ad0c29bc65922e62c6fa915f006**。現在配信されるPagesやmainとは同一視しない。限定6ファイルをraw取得してhash化し、重要部分を直接読んだ。

| 一次text path | bytes | SHA256 |
| --- | ---: | --- |
| docs/game.js | 27877 | dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5 |
| docs/mcts_worker.js | 17775 | f2de9444e8960ca14d4d4acb5dd319e3f0a6a743c39b4032dce32068ebcfe8fa |
| cpp/engine.hpp | 23271 | 72a674b1b02a680ef375be81d78b33914d125183789a1680c6e4d8dde72c6557 |
| cpp/tournament.hpp | 22727 | f507cec6ce0e6e77314b89e5b6bd915c293f69506e0cc789131d3fcbd5becad5 |
| tournament_cpp.py | 32644 | ceb08e9dbc90851838341c5a6a07d56f9d6bd07513879d4a27430a8755f2aa2b |
| docs/app.js | 93099 | b585302b0af1295dbea23fe0a59781c568ead0be79fc6bc13ccb2273fe6dc9bd |

全6件は初期仮説報告のtext hashと一致した。原文のディスク保存はしていない。

| 主張 | 独立判定・根拠 | 残る検証 |
| --- | --- | --- |
| Sigma規約は駒手の3回目反復を禁止し、Webは200ply/合法手なしをdrawとする | 支持。game.js:296–302/386–407。keyは駒位置・手番parity・壁anchor集合。C++はbase history＋simulation overlayを数える | Rust adapterとの全合法集合/終局parity |
| action/特徴はRustと直接同じではない | 支持。Sigma136方向/壁logits、Rust209着地点/壁IDs。P2は縦反転。壁planeはanchorではなく2segment。value backupは手番ごと反転 | 実モデル出力/native/Wasm一致 |
| Web既定ORTは単一threadとは限らない | 支持。mcts_worker.js:44–46のisolation条件で最大8。providerはwasm。app.jsの9×9はbest.onnx | ORT JS/Wasm実bytes版、実worker/CPU使用 |
| Web NN-MCTSとnative tournamentは同じ設定/solverではない | 支持。Web FPU0.2、C++ AgentSpec0.1。tournamentは共有TTを使わず着手後arenaをclear。この限定経路にsolver接続は見なかった | 全selfplay/solverの監査はしていない |
| native driverを--threads 1だけで公平にできる | 不支持。自動CUDA/MPS選択、モデル別inference thread、複数対局/推論batchが別にある | CPU固定・torch/BLAS設定・OS実観測 |
| driverの既定値もWeb200ply/temp0に一致する | 不支持の補足。tournament_cpp.py:244–246はmax_moves100、temp1.0。C++ TConfigの200とdriver fallbackを混ぜてはいけない | 比較presetで--max-moves 200/--temp 0を明示 |
| H1のBFS支配、solverバグ、モデル配布可能性 | 保留。今回コード照合と小さい規約確認のみ | 計測、反証fixture、モデルprovenanceの別検証 |

一次URL:
[game.js](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/game.js#L386)、
[Web worker](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/mcts_worker.js#L21)、
[C++ engine](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/engine.hpp#L88)、
[tournament](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/cpp/tournament.hpp#L47)、
[driver defaults](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/tournament_cpp.py#L244)、
[app model/worker](https://github.com/bartolomeo3000/SigmaQuoridor/blob/751186344fc52ad0c29bc65922e62c6fa915f006/docs/app.js#L144)。

### 短い実行確認（性能試験ではない）

固定raw game.jsをメモリでNodeへ渡し、合法な初期局面からの手順で以下をassertした。Rustやモデルは実行していない。
- 136要素P2 permutationが自己逆写像。
- 初期9×9/10壁で上下の駒手4手サイクルを1回行うと初期key count=2。2回目の最後の戻り手は幾何学的に合法だが、合法集合から除外される。
- 初期から各駒を3回前進しP1をさらに1回前進したP2手番で、直線jumpの着地点は[4,3]。
- その局面からP2がH(4,3)、P1がH(4,5)を合法に置くと、P2直線jumpが禁止され斜め回避が合法。
- 648要素の特徴、P2自駒one-hot、P2残壁/10、H anchorの縦反転、depth200のdraw。

観測raw:
~~~text
PID 621075, affinity [0]
input_sha256 dfa438a500d6808e21bf8fef72a299cd762ac5e8be25251dd38607abb2d046c5
exit 0
{"permutation":136,"featureElements":648,"repeatThirdRejected":true,"straightJumpLanding":[4,3],"diagonalJump":true,"P2Feature":true,"ply200Draw":true}
child_peak_RSS_KiB 50740
~~~
これはSigma側の小さいfixture成立の確認。Rustとのparity完了、全規約の正しさ、性能改善は支持しない。最初の同じ補助スクリプトはshell引用のfixture失敗（SyntaxError、exit1）で実行されず、引用を直して上記を再実行した。研究のnegative resultと区別する。

## 問い1: 比較を成立させる最小経路と規約

### 参照経路を分けて固定する

**ブラウザ主参照案**: 固定commitの9×9/各10壁、docs/models_9x9/best.onnx、Web NN-MCTS、C_PUCT1.0/FPU0.2/temp0、ORT WASM numThreads=1、GPU推論なし、先読み/analysis workerなし。UIのsim sliderは採用しない。root expansionを含めて同実時間へ置き換える最小adapterだけを作り、原文・patch・生成JS/Wasm・ONNXのSHA256を固定する。モデル名をhash名へ変更してmodels_9x9判定を失うとP2が壊れるので、full-canonicalをmanifestで明示し、path判定との一致をテストする。

mcts_worker.js:72–101/385–387はNN未準備や推論例外時にrolloutへ戻る。このままでは「NN-MCTS参照」の対局に別評価器が混ざる。参照fixtureではモデルready・NN呼出し成功・fallback回数0を必須にし、失敗は記録して試験不成立にする。fallbackを隠した対局をSigma成績として採用しない。これは参照の探索を弱める提案ではない。

**native候補案**: C++ tournament+同系統PTモデルのCPU torch。固定presetは9×9/10壁、200 total plies、temp0、C_PUCT1.0/FPU0.1、leaf_batch1、max_batch1、parallel1、探索worker1。shared NN TTなし・arena毎手破棄・この経路のsolverなしを保持。Webに似せるためFPU/TT/solverを変更しない。元driverのtemp1/max_moves100を黙って使わない。PTとWeb ONNXのschema・policy/value数値parityは別途必要。

native driverはモデル同士のmanagerであり、Rustの着手をそのまま注入する外部agent APIと共通deadlineは、この限定コードでは確認できなかった。rootへ任意の盤面・履歴を供給し、1手の途中停止/finishとRustとの交互着手ができるadapterが必要。torch extension build・1手境界・時間制御・固定PT照合が未実施で、今回枠内の準備費用は未計測。Web経路より安価と断定しない。

最小の準備負担を下げる**代案**はRust native CLI対同じローカルChromium内Sigma Web worker。これなら参照ONNX・history・FPUをブラウザ試験と共通化でき、PT/extensionの準備を省けるという設計上の利点がある。ただし分類は「Rust-native対Sigma-Webのローカル対局」。C++ native対局の代用・native/Web同一性能の根拠にはならない。統括が目標のnative/ローカル条件としてこの限定した参照を採択するなら、事前に名称と結論の範囲を契約へ固定する。正統なC++参照まで必要なら別のnative adapter契約を配分する。Python MCTSへの置換もreuse等が変わるため、読んでいない経路を安価な同等版とは推薦しない。

### 規約adapterの比較

| 案 | 必要な変更と評価 |
| --- | --- |
| A: Rust研究探索をSigma規約へ揃える | 推薦する比較専用案。製品standard-2p-v1は保持し、研究用rule contextを探索へ渡す。Sigma側の合法手/機能を弱めない。履歴伝達とdraw終端処理は必須 |
| B: Sigma研究版の反復禁止を外して双方を標準規約へ揃える | 内部探索まで変える必要があり、参照AIそのものの規約変更。強く/弱くなる方向は未測定。原Sigmaに対する到達認定へ流用しない。別変更版としてのみ扱う |
| rootで不正手を拒否/再検索するだけ | no-go。内部のpolicy/展開/backup/solverは不正な継続局面を評価でき、拒否までの時間も公平でなくなる |

Aでは次の情報・処理をnative/Wasm共通の研究contextで持つ。
1. 初期から現在までの合法Action履歴、または検証済みのposition-count map＋現在total ply。開始fixtureのprefixを含む。盤面だけのSnapshotDtoにはhistory countsがなく、plyだけでも復元不能。
2. 比較keyは(P1/P2位置、side-to-move、H/V anchor集合)。Sigmaのkey semanticsを再現し、Zobrist単独の衝突を合法性判定の唯一の根拠にしない。各対局のcountsは独立。rootの現在局面はbaseへ1度だけ含める。
3. 探索pathのoverlayにroot以後の各childを追加し、候補駒手の次key countが2以上なら除外。rootだけでなく**すべての展開、transition、合法policy mask**に適用する。copy/push-popで兄弟へhistoryを漏らさない。壁設置後もkey記録を維持する。
4. goal勝利を優先し、その後200 total pliesまたは合法手なしをdraw/value0とする。深部leafやnode/depth cap fallbackでもcontextの終端判定を先にする。200手を「開始fixture後200手」と取り違えない。
5. same boardでも履歴/remaining pliesが違えば、合法集合や証明は再利用しない。将来のTT/木reuseではrule-context keyが必要。NNの生logits/valueキャッシュとhistory依存のmasked policy/solver確定値を分離する。

B0の壁のみBFS特徴はPawnの反復禁止を含む完全対局距離ではない。ヒューリスティックとして保持できるが、そこから厳密勝敗を認定しない。法則の一致は合法継続と終端/backupで確認する。adapterに関係ない評価係数や探索方針を同時変更しない。

### 対戦前parity gate

16–32個程度の小さい合法replay fixtureを固定する案。ここで手を選別して棋力holdoutへ転用しない。
- 初期/P2手番、左右端と両ゴール手前、straight jump、後壁/盤端での斜めjump、壁で隣接が遮断されjump不能。
- H/V overlap/crossing、片側到達遮断、残壁0/1/10、非対称H/V配置。
- 同じ盤面のhistory count=1/2、simulation overlayだけで2になるcase、兄弟path復帰、ply198/199/200、200手目goalとdrawの優先。
- P1/P2で全合法行動の集合を実座標へ変換し比較。Rust H=81+a/V=145+a → Sigma H=8+a/V=72+a。駒はその局面の合法directionを実着地点へ写す。jumpも方向IDを保持したまま2マス着地する。壁/Pawnの写像のinjectivityとround-tripを確認する。
- P2はcell y→8-y、wall anchor y→7-y。特徴H segmentはy→7-y、V segmentはy→8-y。残壁plane/10、壁のみBFS map/80、手番側の順番。壁anchorビットをそのままplaneに置かない。
- raw model logitsとlegal masked priors、valueのfinite/range/視点。pawnとwall両方の1-ply/2-ply backup、終局loss=-1/draw0を確認。
- graph/dtype/opset・元モデルSHA256・変換版hashを記録し、PT/ONNX/採用Rust native/Wasmの絶対・相対誤差閾値をfixture実行前に固定。閾値の見積りと一致は未確認。モデル未取得なのでこのgateは未通過。

### 時計・終了・資源の条件案

時計はmonotonic。t0は共通のimmutable position/historyが供給可能になった時点、各AI側のadapter/serializationを始める前。正式elapsedはroot生成、履歴変換/盤面復元、合法手、特徴、NN、探索/yield、checkpoint、finish、Action変換・validity check、呼出し元への結果配送を含む。共通審判の棋譜保存/次手applyとUI演出は双方同じく時計外。モデル取得・初回ロードと所定warmupは対局時計外に分離してcold/startupとして記録。前手の未完了仕事/cleanupを次手や相手の時計外へ漏らさない。

候補T={0.1,0.5,1.0}sは未採択。勝敗を一度も見ず、別calibration fixtureで双方の非分割op・root expansion・finish/transportのp50/p95/p99/最大値とsample数を測る。例えば30局面×10warm samples=300/経路を事前固定し、guard gをp99/最大値＋finish/yield余裕から決める。gがT/4を超える候補や、結果配送がTを超える候補を排除し、残った最短の共通Tを選ぶ案。両backend/platformに共通Tが必要なら全4条件を通る最短値。latency分位は母集団tailの保証ではない。独立300 samplesで超過0なら二項片側95%超過率上限は約0.994%、という条件付き目安にすぎない。

adapterはT-gで新しい重い処理を止め、Tまでに**完全に確定・配送した最後の合法checkpoint**を使う。T後に完了した推論/backup/手を利用しない。deadlineでcheckpointがない場合はtimeout負け。非分割opとbrowser同期処理は外部cancelだけで止まると仮定せず、check/yield/必要時自プロセス終了と古いgen応答破棄を設計する。graceを追加するならTに含めて双方同値を事前固定し、結果後の例外を設けない。根拠なしにSigmaのsimulation数を少なくして速く終わらせる代替は不可。cap-hitやdeadline前終了はそのまま記録し、速度/棋力の意味を分ける。

CPU条件は推論まで含めて固定する。
- C++ worker1、parallel1、leaf_batch1/max_batch1、device=cpuを明示し自動GPU選択を使わない。torch.set_num_threads(1)とset_num_interop_threads(1)を推論開始前に設定。OMP/MKL/OPENBLAS/BLIS等も1、動的thread増加なしを事前設定。補助inference threadがあるため「--threads1だからOS threadが1」とは書かない。
- WebはORT session作成前にnumThreads1、wasm provider、proxyなし。model session・analysis worker・複数対局・相手手番の先読みを追加しない。
- 両AIと関連計算子プロセスを同じ指定論理CPUへpinし、着手は交互、対局並列0（同時は1対局）。同platform比較の重いチームjobは止めた窓で行う。SMT sibling、P/E core、background CPU、温度/周波数条件を記録する。CPU0でcriticが読取したことを正式計測の無競合証明に使わない。
- torch getter、ORT設定、PID/TID一覧、affinity、/proc taskのCPU時間差、browser child/workerを実観測する。idle helperを含む総thread数と実行中compute thread数を区別する。
- 同じengine RAM上限とbrowser/nativeの測定範囲をmanifestで固定する。Rust arena64MiBだけでtorch/ORT/RSSまで同一資源と呼ばない。

[ORT flags公式資料](https://onnxruntime.ai/docs/tutorials/web/env-flags-and-session-options.html)はnumThreads1の明示とsession前設定を支持する。
[torch intra-op](https://docs.pytorch.org/docs/2.14/generated/torch.set_num_threads.html)、
[inter-op](https://docs.pytorch.org/docs/2.14/generated/torch.set_num_interop_threads.html)を確認した。ここで提案した実機の制限・競合はまだ実測していない。

## 問い2: 事前非劣性判定と今回予算

### 推薦する主方式

各platform別にRustの勝ち1/引き分け0.5/負け0を記録。開始手順iの先後2ゲームをまとめ、
X_i=(score_i_first+score_i_second)/2 ∈ [0,1] とする。mペア、N=2mゲームなら平均Xが(W+0.5D)/Nと等しい。ペア内の相関は自由で、2m個の独立BernoulliとしてWilson/binomial CIを計算しない。

簡単で保守的な主判定は固定mで
**L=max(0, mean(X)-sqrt(log(1/0.05)/(2m)))、L>0.45**。
5ポイント許容、片側95%。下限が0.45以下なら非劣性未立証であり、劣ると証明したことではない。native/browserそれぞれ成功し、両者成功時だけ全体到達とする。両方を必要とするintersection-union判定なら全体の誤認定は5%以下で、片方だけ選ぶOR判定とは違う。

これは独立ペアのHoeffding boundから導く方法。決定的な複製は標本に足さない。より再現可能なsampling設計は、候補選択前に合法なユニーク開始履歴の大きな有限pool Uを定義・hashし、そこから一様非復元抽出したm件を固定する方式。各pairの条件が固定された有限母集団として扱える場合も同じboundを使える。Uに対する平均という限定したestimandを報告し、全Quoridor局面へ一般化しない。IID samplingと非復元samplingを結果後に切り替えない。

固定seedで同じ初期局面だけを繰り返した結果には、未知の局面分布へ向けたCIは付けない。異なる履歴が同じ盤面/counts/turn/remaining-plyへ落ちる場合も重複を検査する。実時間のOS jitterやsession間学習/キャッシュがpair間の依存を作るなら上記仮定を吟味し、seed変更だけで独立と認定しない。参照・候補の更新/学習はholdout中に行わず、pair順は固定乱数でrandomizeして時刻とplatform orderを記録する。

数式は[Bardenet–Maillard, arXiv:1309.4029v2, Proposition 1.2/Lemma 1.1](https://arxiv.org/pdf/1309.4029v2)の[0,1]有限母集団の非復元boundを独立確認し、下限へ反転したもの。Hoeffding1963原publisherは403で本文を読めず、原論文全体を確認したとは記録しない。t CI・cluster bootstrap等は感度分析にできるが、結果を見て狭いCIを主判定へ選び直さない。低分散を使う方法に替えるなら新しい事前契約と未使用holdoutで行う。

### 結果前に固定する実験項目

1. 正式holdoutはH1/latency/model parity用fixture、学習/係数選択/候補比較局面から分離する。pool生成規則・prefix長分布・排除条件・座標/履歴count・hash・抽出seed・m・pair順を固定。開始時点で終局/不正なfixtureは**結果前**に除く。先後pairは同じ初期手順/局面を使ってengine割当を交換する。
2. 一つの候補code/model/configを探索的比較の後にfreeze。temperature0、root noiseなし、参照tie order保持、Rust seed/tie order保持。time limitでのsimulation数は結果であり一致させない。複数候補を同じholdoutで選ぶなら事前alpha分配等が必要で、勝った候補だけをこの片側95%判定へ提出しない。
3. 200 total plies、Sigma内部反復禁止、goal優先、合法手なしdrawを固定。開始prefixを含めて200まで。timeout・候補自身のcrash/違法手は負けとして分母に含め、棋力と実装failure件数を併記する。参照NN fallback/model不一致は試験不成立。審判/接続障害は事前分類し、結果を使わずログで判定、pair全体を同じseedで再実行する回数上限を事前固定。上限を超えるなら試験不成立/保留とし、都合の悪いpairを削除して新局面を補充しない。
4. 固定mを最後まで実施する。勝敗による早期成功/失敗停止や、CIが都合よくなったところで終了しない。安全停止・pause・deadlineは許すがm未達なら正式判定未完了。再開は同じ版・入力・m・採番で、残枠/許可内に限る。
5. invalid件数・再試行・重複・未完了を全件保存。native/browserの生pair表とCIを別に出し、pool/config変更版を混ぜない。

### 標本数と時間の確認

以下はメモリ内の数式計算であり、対戦実測ではない。mは**各platformのペア数**。

| m | 各platformゲーム数 | 下限から引く幅 | PASSに必要なscore（厳密に超える） | 両platform・200ply・T=0.1sの最大思考時間 |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 200 | 0.122387 | 0.572387 | 2.222時間 |
| 200 | 400 | 0.086541 | 0.536541 | 4.444時間 |
| 400 | 800 | 0.061194 | 0.511194 | 8.889時間 |
| 600 | 1200 | 0.049964 | 0.499964 | 13.333時間 |
| 1800 | 3600 | 0.028847 | 0.478847 | 40.000時間 |

2platformで4mゲーム、1ゲーム最大200手、1手Tなので最大4m×200×T秒。終了/記録/準備/再試行の時間は上表へさらに加算する。T=0.5/1sなら各時間は5/10倍。短い実対局なら小さくなるが、未測定の平均手数を実績として使わない。

scoreがちょうど0.50でも区間幅5points未満にするには600ペア/1200gamesが必要。ただしその近辺はpower約50%の境界で、「1200gamesで十分な検出力」とはしない。同じ分布自由boundで真のmean=0.50で80%以上の検出力を保守的に確保する十分条件は
m ≥ ceil((sqrt(log20)+sqrt(log5))²/(2×0.05²)) = 1800ペア。
これは**この方式の十分条件**であり、普遍的な最小必要標本数ではない。draw/先後相関で分散が低い場合に別の事前方式が効率的になる余地はある。

**今回枠の提案**:
- Tをlatency preflightで決定してから、準備と終了余裕を除いたR秒に対し、保守的にはm_budget=floor(R/[4×200×(T+固定overhead)])を決める。mとCI方式を勝敗前に固定する。約7時間16分の全残量をすべて対戦へ使うと仮定しても、T0.1でmは約327以下、T0.5で約65以下、T1で約32以下。実際は準備枠を引くのでさらに小さい。
- 0.1sが成立し必要準備時間を別途確保できるならm100/200を探索的開始数にするのは予算上可能性がある。現状はmodel/adapterが未整備で、対戦開始をgoとは判定していない。
- 小さいmでもこの固定boundがL>0.45になるほど強いscoreを出せば、統計上の非劣性証拠にはできる。しかし**近い棋力を確実に判定する精度/powerはない**。事前に探索的試験と定めた結果は、後から認定用へ格上げしない。
- 近接同等の両platform認定まで要求する正式計画（例m600以上、あるいは80% power目的m1800）は保守的には残枠外。今回で成立しなければ「同等未立証/目標未達」と残し、探索的成績・parity/latencyだけを報告する。n/CI/許容差を対戦後に緩めて達成にしない。

## 問い3: H1の最小判別計測

**go（必要な計測器修正を含む）**。experimentへ最適化の開始を依頼するものではなく、元B0対照保存と観測へ進む方法を支持する。現在のprofiling版を無条件受入れしない。

### 固定対照と分母

元3局面initial/opening/walled-midgame、192 sims/seed1979/512nodes/depth24、step4、warmup1＋3 samplesを最初の維持対照として保存する。native-search.jsonは96sims fixtureなのでその期待値を192sims結果へ使わない。instrumented/uninstrumentedでseed・合法列挙順・tie・合法集合・距離・全transition・最終手・root edge visits/prior/value bit pattern・statsを比較する。合法順だけの変更も維持対照で同じと扱わない。

T_searchはsession生成直前からfinish直後まで（元CLIの範囲）。cleanup/drop/JSON出力を含む製品の着手elapsedとは別。T_expandはexpand呼出しの総inclusive時間（互いに重複しないexpand区間の和）。expand外のcap safe_value/transition/select/backupはT_expandへ混ぜない。

H1の事前主割合を
**R_exp = T_expand内の「legal_action_idsまたはwall_distanceの部分木の和集合」 / T_expand**
と定義する。BFSがlegalの内側にある場合は1回だけ。evaluate内のBFS/その内側のqueue確保も含める。play内のBFSがexpand/evaluateから呼ばれた分は含め、探索transitionから呼ばれた分は分母外。関数名/起点のoperational definitionを固定し、全ての幾何学処理一般を測ったとは言わない。

同時に **R_all=同じlegal/BFS和集合の全検索時間 / T_search** と f_expand=T_expand/T_search を記録する。R_exp>0.5でも展開が小さいなら全体の主要因と認定しない。完全にその箇所を除去できたとしても、全体改善の理想上限は1/(1-R_all)。固定queueだけでこの上限へ達すると主張しない。

- R_exp≥0.50: 展開コストについてH1を支持する条件。
- R_exp<0.20: この3fixtureでの展開支配仮説を不支持。
- 0.20≤R_exp<0.50: 判別不足。
- 3局面の結論が分かれる、cap/overheadで分類が変わる場合は局面別支持と保留を併記し、平均だけで消さない。単なるLLM合意やsourceのループ数は実測の代用にならない。

### 排他集計・確保・overhead

nested spanはstackで親のinclusiveから子inclusiveを引く。exclusiveだけを足す。legal inclusive＋distance inclusive＋evaluate inclusiveを総時間として足さない。探索全体の排他分類はvalidation/init、expandのlegal以外、legalのBFS以外、BFS、evaluateの既分類以外、transitionの既分類以外、select、backup/その他、確保（時計を分ける場合）とし、すべての区間を一度だけ数える。さらにExpand祖先の有無を別軸で保持する。

**現在読んだprofiling.rsに必要な補足**: metrics[kind][直近parent]だけではDistance(parent=Transition)がEvaluate→Transition内かSearch→Transition内かを区別できず、Distance(parent=Evaluate)もexpand内evaluateとcap fallbackを区別できない。したがってglobal Legal/DistanceをT_expandで割って主閾値へ入れるのは不可。stackにExpand祖先flag/phaseを付けるか、R_expの和集合時間を独立にchargeする必要がある。parent行列をinclusiveで再帰的に足して祖先時間を復元しようとしても、集約でどの呼出しに属したかが失われている。cap0で一部を推定できても、transition起点差と条件を明記し、主判定は直接のcontext集計を推薦する。

BFS回数/訪問cell数、合法壁候補数と成功数、evaluate/play/select/expand回数、実heap alloc/dealloc/bytes、arena high-water、depth/node/arena cap-hit、policy/value fallbackを記録する。VecDeque確保のコードを読んだだけで実allocator回数を認定しない。グローバルallocatorのtimingはそれ自体が歪むので、まずallocation countだけの別run（出力一致を確認）とowner別カウントを行う案。allocation時間を別timerにした場合は親から差し引き、H1和集合に含まれるownerのallocを1度だけ戻す。既存array stackのtimer自身が追加確保しないことも検証する。

先に**未instrumented baseline**を原入力hash/ビルド版/CPU/RAM/command/seed/raw resultとともに保存。その後、同じcompiler/release/limitsでtiming版とcoarse/count版を交互の順番で比較する。3 warm samplesは原再現を保持するがoverheadの分位推定には不足なので、最小判別用には事前固定で各fixture10 warm samples程度へ増やす案（元3sample結果も残す）。有利なsampleだけを採らない。
overhead=(instrumented median / uninstrumented median)-1、caseごとのp50/p95/最大・回数を出す。例えば主分類はoverhead≤5%を事前gateとし、超えるなら粗いphase計測/低頻度sampleへ戻す。5%は提案閾値で、今回実測で満たした値ではない。境界50/20%から数pointsしか離れない場合はoverhead≤5%でも判定保留。空timerの平均を全callに掛けて差し引くだけで正確な内訳とは扱わない。残差・timer bookkeepingが大きい場合は「計測不成立」とし、H1不支持と混同しない。

### 小さいholdoutと結果後の分岐

元3局面はP1手番のみ（prefix0/6/12）、序中盤偏り。原3を変更せず、小さい別集計にP2初期、P2 jump、壁が多い局面、双方残壁0/1、ゴール目前の相手脅威、斜め回避を足す案。すべて合法replay/checked positionで作り、採択前にhash・seedを固定。性能診断用fixtureと正式棋力holdoutを共有しない。

現在のprofile_native.rs:30–37にP2/jump/many-wallsが既に追加されていることは読取確認した。これは原3とは別枠で報告し、endgame/diagonalも必要なら次の小fixtureとして扱う。多壁fixtureの生成順を実行時に変えると別入力になるので生成規則と生成後positionを固定する。今回そのRust fixtureを実行確認していない。

cap-hitがある場合は現在limit条件の測定をまず残す。fallback evaluateの時間/回数を別記し、capを緩めた診断を同じ192/512/24対照へ混ぜない。seed1979/tie orderを保持した主実験の後、別seed数件や合法列挙orderに敏感なcaseを感度分析へ回す。seedの結果を見て原3に有利なものへ変更しない。

合法/BFSが支配し、holdoutにも適用できるなら固定queue等の**1要因**試作を次契約の候補にする。低割合ならevaluate/transition/select/確保・capのどこが大きいかを根拠に別枝へ向かう。いずれも今回criticは実装しない。nativeのR_expや高速化だけでWasmのslice/cancel/メモリや棋力改善を認定しない。

## 支持しない結論・未検証・失敗の区別

モデルSHA256/graph/provenance/配布可否、PT→ONNX数値一致、Rust native/Wasm推論一致、実thread数とOS無競合、同時間対戦、solverの厳密性/バグ、H1の実時間割合、性能/棋力達成は**未検証**。rootの拒否だけで規約が同じ、sim数だけで資源が同じ、nativeの結果でbrowserも同等、200gamesだから十分な精度、という結論は支持しない。

stewardの主checkoutへ流れる依存問題は重要な入力制約として継承した。今回は隔離build/ブラウザを起動していないので、その解消はexperiment側の実測/生成物provenanceで確認する。現在のsource変更を「自分が検証済みの元B0」とは呼ばない。

研究negative resultは今回なし。原文source観測、Sigma側だけのfixture確認、数式計算、未整備の比較adapter、補助scriptの引用失敗をそれぞれ区別した。ここで作成したfixture確認と統計案の最終採択は統括または別の検証担当へ渡す。

## 再現コマンド・観測環境・資源

限定読取はtimeout10–55秒、taskset -c0。Node確認はtimeout25秒のPython parentと8秒のNode child、node --max-old-space-size=128。CPUs許可0–19のうち当役はCPU0にpinした。自己PID619134（原文読取）/621075（Node確認parent）/623242（manifest読取）のaffinity[0]を確認した。メモリはNode child peak50,740KiBを観測。全tool/processの累積CPU秒やLLM基盤RSSは独立集計しておらず、0 CPU消費とは書かない。

ローカルtool raw取得はユニーク6原文217,393 bytes、再読込みを含む505,026 bytes（メモリ）。Web工具による一次資料/PDFの取得量はこのローカル数値へ含めていない。モデル取得0、依存更新0、clone0、build0、対戦0、正式性能job0、GPU/学習0。原文のファイル保存0。新規永続成果物は本報告のみで32MiB以内。共有Beads backup/ホスト履歴は全体基盤台帳の扱いに従う。

取得・hash再確認の最小コマンド（この報告の再検証用、モデル取得なし）:
~~~bash
PYTHONDONTWRITEBYTECODE=1 timeout 20s taskset -c 0 python3 -B - <<'PY'
import urllib.request, hashlib
base = "https://raw.githubusercontent.com/bartolomeo3000/SigmaQuoridor/751186344fc52ad0c29bc65922e62c6fa915f006/"
for p in ["docs/game.js", "docs/mcts_worker.js", "cpp/engine.hpp",
          "cpp/tournament.hpp", "tournament_cpp.py", "docs/app.js"]:
    b = urllib.request.urlopen(base+p, timeout=3).read(150000)
    assert len(b) < 150000
    print(p, len(b), hashlib.sha256(b).hexdigest())
PY
~~~

統計の算術再現:
~~~bash
PYTHONDONTWRITEBYTECODE=1 timeout 5s taskset -c 0 python3 -B - <<'PY'
import math
for m in (100,200,400,600,1800):
    e=math.sqrt(math.log(20)/(2*m))
    print(m, 2*m, e, .45+e, 4*m*200*.1/3600)
print(math.ceil((math.sqrt(math.log(20))+math.sqrt(math.log(5)))**2/(2*.05**2)))
PY
~~~
これらの原文読取・算術は独立再実行した。H1/対局/推論の再実行は本契約外で行っていない。

## 書込み停止・保持する証拠・引き渡し

本報告を保存・hash/byte数確認した後はファイル書込みを停止する。自分が起動した短い処理は終了し、バックグラウンドjob/exec session残存なし。他者のjob/App Serverを停止していない。送信直前にwrapperでready、目標と自子issueをshowし、pauseがない場合だけbackup sync後に指定reportを送る。子issueは受入れ待ちin_progressを維持し、統括受入れ後に本人close、目標をcloseしない。

保持する証拠は本報告、固定URL/text hash、以下のlocal入力manifest、原入力2報告/launch.json、toolのraw観測/退出状態、Beads/通信履歴。原文・モデル・一時buildを生成しておらず、削除を行わない。

統括への必要な判断:
- 反復/200plyの比較専用contextを採択し、内部探索parityと時計adapterの別実装/検証範囲を配分する。正式対局はそのgate通過までno-go。
- native候補をC++ tournamentとして固定するか、最小ローカル比較をRust-native対Sigma-Webと明記して始めるかを、準備費用の実測前提で決める。
- H1計測は祖先context・排他分母・未instrumented baseline・overhead gateを満たす条件でgo。現在の親種別だけの集約からR_expを直接認定しない。
- T/m/統計方式/holdout/停止規則を結果前に固定し、今回で精度/標本が足りなければ未達と明記する。

報告済みと受入れ済みは別。これは研究権限の拡張やpause解除ではない。

## Local入力SHA256（2026-09-30 17:58:57 UTC）

| Path | SHA256 |
| --- | --- |
| AGENTS.md | c03050bdfe00ecf86558945f0100ca6265d33e7447743cc277aeffea546f6edb |
| docs/design/ai-sigma-research-goal.md | 4b0fee4e7b7c9f2de07a6baf0c2fd5f649718511e419366af9464471d4524b7d |
| docs/design/ai-sigma-contract-critic-comparison.md | 8401597aa7c47b62f839fd1de82fe150aacac848fb465eeadd3ac79e3a2f32d5 |
| docs/design/ai-research-team.md | 13d757d4cad2b68d1ad1fb106360b91108cbcce0d74718ac1813599635eab123 |
| docs/design/quoridor-3d-webapp-design-rust-wasm-v1.md | c4dbe22719bcd60ad0c9e8586a37d4e0be6bcc2dbd863cea21f8e322093ab577 |
| .agents/research-team/common.md | 56c4d2aed25c083e6292d11efb0afa2c70a8f26709e5ad5a50029c8ef8d55add |
| .agents/research-team/roles/critic.md | 91b6fb67f814257a42456b65385f0186ebdd8967ef859004f18d3166b0e1f8ad |
| .agents/research-team/templates/handoff.md | 8139c0ad5a3a4eccc5ba7654807effa350debfcc32c5320aeffba4e9b8e2f753 |
| .devcontainer/storage-policy.md | bc27c254d4cde6342329d9f27c376da786857d58ea8b6cf0ea5e0ba78fabb099 |
| docs/reports/ai-sigma-hypothesis-initial.md | 8b4938e6bd1774a5313f808f8c5c0de3a67618c00cc63a4cd6efd404fde9a032 |
| docs/reports/ai-sigma-steward-initial.md | 52b8d53b07cf725f1b53510048abfd0c4d4d13b03461f0c814e16695cb4ff5a5 |
| crates/quoridor-core/src/position.rs | b12e79a99cf3441cf4acebbea1b827dce24b02db6fb2269021964872535e3ab6 |
| crates/quoridor-core/src/game.rs | 543995676fb46cc4e80d0fccb650875eb901a4b4d71187788ee09dfbaf01a420 |
| crates/quoridor-ai/src/lib.rs | 7ff1a13dceda7f3f2cb831321bdc56e509808c09006b697901e8328a924f8a21 |
| crates/quoridor-ai/src/bin/measure_native.rs | a32ec56a90cfb25469100cc7b3ecfb9c5976bd81d52dd51855280668cd791d2b |
| crates/quoridor-wasm/src/wire.rs | 4a28ac6169e32e3ff34681d7b1ea8617a485f9557260a885980c1ec2fd5364a2 |
| packages/engine-bridge/src/ai.worker.ts | d88394b5bacc5ead5d205e4616a186ae7ec67135c44f7293367d46258c535aa6 |
| Cargo.lock | f1b7e28714344098c70588371a8869a128612c40e0762c4cd0fbc0677309f346 |
| package-lock.json | 00623ab83b120debff85f750fad8b056f0bc55bd9f85385025d401629776e56e |
| tools/training/uv.lock | 6b562f85005518a8e38556722d536c342c17da18b0d7040fcd0e80bb662671b3 |
| tools/research-team/uv.lock | d0c4f15d3beebfd2f5c37d76cebd8dcbcd562e79b3c357721dba2d8961e00658 |
| tests/fixtures/ai/native-search.json | dc16fa83288ff3087dd91ac3fd78d59e929ecbd3d8e19f442405563709c9c38b |
| /workspaces/quoridor/.artifacts/research-team/sigma-launch/launch.json | 306b71b7d1a0363a363450e5cba2f4315970eb82378fa85597b2388dca926d28 |


保存・停止確認: 2026-09-30T18:16:14.649248+00:00。開始17:45:48 UTCから30分上限内。保存前の検査で入力2報告と18:01:53のprofiling4ファイルhashは一致。保存直前の40746 bytesに本確認行を追記した。以下の通信とBeads wrapper以外の処理を停止、ファイル書込み停止。
