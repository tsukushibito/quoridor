# NNUE研究の知見と次の判断

2026-10-06更新。[研究目標](design/ai-sigma-research-goal.md)はNNUE型Quoridor AIの最高棋力。Sigma同等は段階目標・比較基準であり、最高棋力と正式な同等水準は未立証。[現在の許可](design/ai-sigma-continuation-20261001.md)では新しい研究実行は未配分。本書を観測・限界・競合説明・次の人間判断の正本とし、担当・状態・依存はBeads、仕様は[設計](README.md)、数値と科学記録は原成果物へ置く。

## 学習の適合と汎化

310の詳細曲線は旧432 train families/14,803行、再用144 validation families/4,733行、同初期重み・sampler設定・batch128で、A/B各4,000更新・512,000 seen・200実観測点を記録した。入力順と抽出回数histogramは一致するが、抽選sequenceは未記録で、完全に同じdraw列の証明ではない。旧302との共通23選定点と初期・末期重みは一致した。[数値と条件](../research-data/ai-sigma/frame24-learning-diagnosis/dense-saved-diagnosis-v1.json)、[曲線](../research-data/ai-sigma/frame24-learning-diagnosis/dense-learning-A-B-v1.png)。

| 条件      | 記録された最良validation family MSE |    step / seen | 末期validation family MSE | 末期の全train family MSE |
| --------- | ----------------------------------: | -------------: | ------------------------: | -----------------------: |
| A、LR1e-4 |                          .582860039 |  926 / 118,528 |                .747894928 |               .005187532 |
| B、LR3e-5 |                          .574216803 | 3817 / 488,576 |                .574924200 |               .249902146 |

距離基準Dのvalidation family MSEは.660867274。選定点でDより良いfamilyはA 99/144、B 100/144だが、他のfamilyは悪化した。Row平均の最小はA step925/.636472847、B step3075/.632563419で、family平均の最良点とは異なる。観測点間の連続最適点、未見局面への転移、同時間棋力を認定しない。

Aは末期にtrainへ強く適合しvalidation誤差と飽和が増え、Bは遅く適合して末期の選定品質を保った。この条件ではLRと露出に依存する過学習を支持する。trainへの適合から表現力不足だけを第一原因とはしない。入力多様性・代表性、教師と探索葉の意味、校正・正則化、特徴の転移が競合説明として残る。

復元抽出の512,000 seenは約34.5876回分の行露出で、完了epochではない。各train行の抽出は5–144回。高頻度train診断は固定2,048行・420/432 familiesのsubsetであり、全trainの測定は初期/末期だけ。表の全train値を最良checkpointの値や高頻度subset値へ読み替えない。[解釈と測定範囲](../research-data/ai-sigma/frame24-learning-diagnosis/final-report-v1.md)。

## 公開Sigmaデータの範囲と資格

固定Sigma source `751186344fc52ad0c29bc65922e62c6fa915f006` の公開43 NPZは18,914,078保存行を持つ。重複・augmentation込みの行数で、全体のdistinct状態・適格モデル入力数は未測定。使用subsetの `complete_groups` はoriginalの先頭index順に入力群を行capまで採り、全域を無作為・層別抽出したものではない。[全域調査の根拠と提案](../research-data/ai-sigma/frame24-learning-analysis/next-main-learning-proposal-v1.md)。

0041/0042を用いた公開z学習は、露出除外後train67,937行/4,996入力群、raw selection19,965行/20入力群、そのうちdecisive zの選定19,846行だった。使用subsetの狭さを全公開データ・教師・NNUEの欠陥へ拡張しない。保存行数、学習seen、入力群数、独立game数を区別する。公開sourceのgame/history/ply/絶対P1/P2は取得できず、canonical STMとvirtual side1を実P1/P2へ読み替えない。[原import引渡し](../research-data/ai-sigma/frame23-sigma-public-z-import/public-z-immutable-handoff-v3.json)、[実学習の入力・mask](../research-data/ai-sigma/frame23-public-sigma-z-learning/actual-input-binding-v1.json)。

公開z0は終了理由が不明なため主教師から除外し、証明済みRuleA draw=0とは区別した。raw z0は入力露出参照に残る。0041候補中の不適格な残壁planeを含む229行・113入力群は群ごと除外し、clipや補充はしなかった。Original/後半augmentationのbyte対応を確認した範囲は3 shardであり、正しい幾何反射を全43へ保証しない。V壁のpaddingを含む単純な列反転を正しい反射へ無言で修正しない。各視点QF1と全81升距離mapの資格、反射/crosscycle群、条件付きzの複数観測を保つ必要がある。

実学習は全raw selection（z0込み）と入力一致するtrain9,051行を除外した。資格除外と露出は重なり得るので単純加算しない。履歴を持つnativeデータではstate/history/実STM入力のいずれかによるOR露出、全saved runの実used unionと全raw validationを使う。公開データは履歴欠測のため実STM QF1+distanceのpredicateに限定され、空historyや入力非一致から完全な非露出・game独立を認定しない。将来評価を開いた後の再選定・学習転用はしない。

この同subsetの1m/2m seen比較では登録規則で1m step7813をfreezeし、selection row MSE .975691465（D 1.014010958、train-only定数1.000124479）だった。2m末期.986040469は追加露出の選定利益を支持しない。20入力群を再用した探索的選定であり、独立game汎化・棋力の証明ではない。公開checkpointは製品の既定weightsへ採用していない。[凍結条件・原分母](../research-data/ai-sigma/frame23-public-sigma-z-learning/final-saved-freeze-v1/candidate-freeze-v1.json)。

## 実行費と探索の検証

同H32・batch128・512更新のCPU/CUDA比較は、cold単回・CPU先行でwhole background 11.677261/13.493289秒、trainer 4.553716/6.672230秒だった。この小条件ではGPU時間利益を支持しないが、大きなモデル・batchや百万種類規模のGPU学習を否定しない。時計は入れ子で合算しない。設定・初期・入力順・抽出histogramが一致し、実draw列は未記録。記録されたgroup値の最大差2.384e-7は有限数値対応であり、棋力同等ではない。[比較数値](../research-data/ai-sigma/frame24-learning-diagnosis/foundation-comparison-v1.json)、[比較曲線](../research-data/ai-sigma/frame24-learning-diagnosis/foundation-CPU-CUDA-v1.png)。

教師生成では同8新opening/seed・K32、同model・worker core2/4と推論owner core6で、CPU ORT/TensorRT各8局GOAL・446適格行・12,802 NN、保存Action/勝敗/手数/NN数が一致した。初期化から保存・回収を含む57.604253/11.337379秒、点倍率5.08。固定順・単回・単一host・小標本で、将来の生成倍率や純kernel倍率を保証しない。小CPU/GPU学習cycleのrelease arenaは各4局で学生0勝4敗、重み採用なし。接続成功を棋力改善へ変換しない。[生成比較](../research-data/ai-sigma/rust-migration/native-generation-comparison.json)、[検証と保存archive](../research-data/ai-sigma/rust-migration/verification.json)。

現在のRust coreへはframe21のu128層BFS `wall_distance`、frame22の両goal全81升bitparallel mapとNNUE supplier、frame23のcaller-local wall-post DSU＋曖昧候補のexact fallbackを採用した。Standalone legal_wall/playのexact検査は維持する。固定4prefixの有限同仕事比較で、frame21の探索時間比（候補/基準）はD .071–.089、NNUE .131–.189だったが、CPU ORT K64 MCTS .961–1.007は明確利益なし。全81 map変更のdepth2 NNUEは順序を反転した中央値合計比.724421/.829737。DSU変更は56組でAction/value/PV/depth/nodes等が一致し、NNUE計時合計比.521271–.740728だった一方、個別試行の悪化（最大1.33495）も保存した。異なる基準・旧width32・短いcaller計測の比を乗算したり、production全費、MCTS生成倍率、同時間棋力へ外挿しない。[frame21同仕事](../research-data/ai-sigma/frame21-search-efficiency/comparison-r1.json)、[MCTS費](../research-data/ai-sigma/frame21-mcts-cost/result.json)、[全81 map](../research-data/ai-sigma/frame22-map-efficiency/summary.json)、[DSU原結果](../research-data/ai-sigma/frame23-wall-legality-processing/finite-result-v1.json)。

これ以前の156の4入力・46合法child診断では距離map cacheと313差分特徴の対応は成立し、総費用は3入力で減り1入力で増えた。有限の壁配置を反復したJS/browser診断であり、現在のRust実αβや一般壁配置の速度実績ではない。個別distance lookup時計の欠測を0へ補わない。旧154でroot NN値とMCTS rootmeanの符号が異なる例もあり、rootNN・探索平均・真の終局zを別教師として保持する。[156の原結果](../research-data/ai-sigma/156-nnue-feature-cost/analysis.json)、[154の教師確認](../research-data/ai-sigma/154-nnue-preliminary/schema-results.json)。

永続TTと実callerの初期化/error/cancel/reset/全caller費計測は311/317の有限ソフト検証を経てmainへ採用した。実NNUEのwarm/cold性能・有効hit・同時間棋力は未測定。Whole callerはmove application/providerを含まず、構成時計は重複する。共有model bytes、error時の内部counterと孤立したhash/PV/provider費はUNKNOWN。MPCはOFF計画・schema検証のみで、校正pairとON実装は未成立。[最終研究引渡し](../research-data/ai-sigma/frame24-coordinator/final-stopped-coordinator-handoff.md)、[MPCの計画・限界](../research-data/ai-sigma/frame23-mpc-calibration-design/report-v1.md)。ソフト修正の成立を速度・棋力改善へ格上げしない。元の失敗・超過・UNKNOWNを成功で上書きしない。

## 次に人間が選ぶ事項

百万種類規模はユーザーの暫定設計目標で、理論的な必要最小量ではない。316の提案は、まず公開全43ファイル全域をtarget-freeに調べ、distinct適格モデル入力の量、反射/crosscycle露出、分布の代表性を測ること。小候補がDを超えることを本調査の開始条件にしない。取得・調査・新学習は未開始である。[316提案の正本](../research-data/ai-sigma/frame24-learning-analysis/next-main-learning-proposal-v1.md)。

| 競合案                              | 変わる判断                                               | 保存・全工程費の条件                                                                                                        |
| ----------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 全43のtarget-free多様性調査         | 百万種類規模の適格入力が存在するか、代表分割をどう作るか | Original/augmentation half対応を全域で確認できる場合640MiB inclusive案。確認不能で全行ledgerが必要なら1.25GiB案へ事前見直し |
| 全cycle・全域の層別input-only pilot | 量とalias集中の見込みを小さく調べる                      | 256MiB inclusive案。全corpus distinct数の認定はできない                                                                     |
| 調査後のcompact供給・代表学習       | 条件付き観測を保持し、未見分割とGPU学習を設計する        | 768MiB開始案にindex/scratch/model/log/Gitを含めて再見積り。全dense cacheとは別                                              |

全公開入力のraw f32は約49.0GB、現dense cacheは約47.5GBで旧12GiB枠へ収まらない。Bitset等のcompact表現は提案で、資格decoder・bounded batch API・性能は未検証。Whole costには取得、decode、native資格、hash/group化、alias確認、export、保存Git/archive、失敗と回収を含む。確認済み未使用予約とfresh保存量を束縛し、UNKNOWNや保護資産を空きへ換算しない。古い小subsetのthroughputを全域の保証にしない。

多様性調査を受け、人間が未見分割、条件付きラベル、epoch/sampler、GPU batch、曲線/選定間隔を選ぶ。GPUを本学習の主経路候補として、host展開・転送・更新・選定・保存・回収まで計測する。同batch再現と大batch/prefetch変更は別介入。CUDA4,000step追加比較、TT実NNUE性能、MPC校正は保留候補で、残予算や実装容易性だけでは開始しない。[タスク型研究](design/ai-research-team.md)に従って明示配分する。
