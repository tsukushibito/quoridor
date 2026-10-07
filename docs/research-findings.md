# NNUE研究の知見と次の判断

2026-10-06更新。[研究目標](design/ai-sigma-research-goal.md)はNNUE型Quoridor AIの最高棋力。Sigma同等は段階目標・比較基準であり、最高棋力と正式な同等水準は未立証。[現在の許可](design/ai-sigma-continuation-20261001.md)はユーザー指定の探索高速化と公開100万行GPU学習。本書を観測・限界・競合説明・次の人間判断の正本とし、担当・状態・依存はBeads、仕様は[設計](README.md)、数値と科学記録は原成果物へ置く。

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

探索初回の代表profileと同意味sort比較は終了し、sort変更は全仕事時間比1.00461、target時間比1.08149で速度利益を支持せず不採用。cold/warm一手系列の有限TT観測は実プレイヤー二手跨ぎの利益を証明しない。次はユーザー指定により、学習済みBESTの明示Scalar/Simd FT・差分・取り消し資格と停止版引渡し後に、同じ重み・計算順序の評価処理最適化を行う。推論ごとの配列確保/コピー削減・scratch再用を第一候補とし、plain whole-searchの同仕事比較で判定する。FTのSIMD資格は残差headのSIMD高速化ではない。計算順序/精度/モデル変更は人間判断へ戻す。現状は全合法手のsortとTT/PV・killer・任意policy・history順で、学習済み方策は既定で使わない。探索方式・ordering方式・選択的枝刈りなどの重要設計は、観測・競合・全費をRoot経由で人間へ提示する。[初回担当契約](../research-data/ai-sigma/search-optimization/task.md)を参照し、担当・進捗はBeadsで管理する。

ゾブリスト化の判断では、318の固定5局面H32/depth2 profileでTT key .49%、履歴1.81%、probe2.79%、store2.84%（exclusive合計7.93%）、sort17.29%、評価20.51%だった。孤立hash費は未分離、計測activeのwhole overhead約25%もあり、productionの改善上限や一般倍率へ換算しない。現TTは完全履歴キーのDefaultHasherをprobe/storeで再計算するため改善候補だが、まず一度計算したfingerprintの再用と履歴構築費を分けて比較するのが低改修費の競合。差分ゾブリストは盤面だけでなく反復回数・ply等の履歴意味を保ち、make/unmake/from-prefix対応と衝突時の完全キー確認を維持する。ハッシュ方式だけで意味上のTTヒット率は上がらない。ユーザー判断により低優先度の候補として保持し、実装・追加測定は割り当てない。代表的whole-searchでTT hash/履歴処理が支配費になった場合、又は高優先度の改善後に全費で利益が見込める場合に再検討する。[判断根拠](../research-data/ai-sigma/search-optimization/zobrist-assessment.json)。

## 選択済みの次の主学習

ユーザーは公開全域からの訓練100万行・validation5万行・最終評価5万行、元観測/反転兄弟の分割固定、別観測の盤面一致許容、epoch shuffleとGPU学習を選んだ。先頭入力群だけの抽出とvalidation一致による訓練一律削除を新主経路に使わない。不正入力を除き、公開z0は終了理由不明の教師として別に除外する。複数の条件付き勝敗観測を保持し、実distinct数と分布を報告する。既存モデル・特徴を固定し、初期から細かい曲線と全工程費を観測する。[319契約](../research-data/ai-sigma/public-million-learning/task.md)が実装・実行・資源・停止と検証を定める。受付・実装・実取得・実学習・独立評価を分け、結果は未測定。

319のデータ準備は全43blobのhashと実original/LR入力・ラベルbyte対応を報告し、18,914,078保存行をdecode、抽出候補5,674,588行をnative資格へ通した。適格decisive split候補はT3,063,833/V151,935/E153,672、実保持T1,000,000/V50,000/sealed E50,000。モデル入力distinctはそれぞれ323,366/28,709/28,669であり、100万行を100万種類や独立gameへ読み替えない。旧4,996は元Sigma全plane入力群なので、この新モデル入力identityとの単純な倍率比較も行わない。[集計とRoot読取点](../research-data/ai-sigma/public-million-learning/data-preparation-observed.json)。

data処理341.580264秒、controller全job341.814518秒、network1,664,424,671B、compact corpus191,400,000Bを保存した。時計は包摂するので合算しない。Job exit0/direct child回収/cleanup true/remaining空をRootが確認したが、入力変換・split・教師解釈の導入採用は独立レビュー319.1の確認待ちであり、GPU fitと最終評価はこの読取点で未開始。データ件数の成立を学習利益や棋力へ変換しない。

独立reviewはfreeze/test cache未照合、UNKNOWN露出のunexposed表示、sealed評価へのinitial追加、primary row monitorの未束縛を指摘した。通常修正を同reviewerへ戻す。さらにnative合法性だけではnaiveLRと元盤面の幾何対応・コピーzの妥当性を証明できないため、ユーザーはoriginal-onlyでT100万/V5万/E5万を新規抽出するv2を選択した。旧corpusと費を保存し、全43再取得系列を別に配分する。原観測alias distinct942,288/47,187/47,191を保持行数とした説明は訂正する。実保持original行は824,069/41,230/41,322で、LRのみ保持されたaliasを元観測へ読み替えない。

ユーザーは、original-onlyでフローと基準結果を確立した後、正しい左右反転をtrain batchで50%適用するオンラインaugmentationを比較する方向を承認した。新反転はnative再計算/二回復帰/合法遷移等のoracleで確認し、同元データ・初期・尺度・LR/batch・同更新回数/seenで比較する。独立した対局観測の増量と区別し、境界修正は同reviewerへ戻す。具体の追加fitは基準成立後の実残予算/保存と計時枠をRootが配分する。旧公開反転データの再使用、開封済みtestでの新候補再選定、追加arenaはこの方針承認だけでは開始しない。

original-only v2の復旧job `2c121563-6813-4226-a9e5-716c860cc9ba` は08:55:38 UTCにexit0/cleanup true/remaining空・子回収で終了した。cache manifestはT100万/V5万/sealed E5万、モデル入力distinct366,638/32,263/32,143。これは保存観測行と入力identityの集計であり、独立game数や100万種類ではない。Payload全資格・v2 train-only尺度と定数のbindingは担当が続けて確認する。GPUfit/testはこの読取時点で未開始。

先行v2 jobのチェック未完了後submitは取消・原費保持とした。さらに完了通知がnotLoadedから制限付き権限で復帰する管理不具合で結果確認を妨げたが、Rootは正式fullaccess再開し、mainの作成/再開/完了通知で承認済み権限を明示する通常修復を行った。38限定tests/プロジェクトRuff/AST一致は有限ソフト資格であり、次の実通知の成功は未認定。[修復証拠](../research-data/ai-sigma/task-session-permissions/repair.json)。旧data費/失敗・UNKNOWN・方法・モデルは不変更。その後のGPU供給・初期native資格は修復job `cd145ca4` でPASS/exit0/cleanup/remaining空となった。CPU/CUDA/native計10,313forward、native-CUDA差7.45e-9、同2048行の破棄Adam更新差7.28e-12。初回CPU3のSMT guard拒否とouter config拒否を含む全attempt10.501695秒を保存し、GPU3600秒の残3589.498305秒で固定original-only一fitを配分した。資格PASSは本fit・学習済みnative・最終test成功ではない。固定順の128/512/2048資格時計は最初のbackward等cold費が偏るためbatch変更の根拠にしない。

実行の連携では、学習のnative binary/libraryをSHA付きprivate immutable参照へ束縛してから、既CPU2,3/RAM4/GPU6の固定fitと、CPU0,1/RAM2/GPU0の通常ビルド・限定ソフト検証を並行可とした。共有targetは318→320の一人ずつ、ビルドのexact STOPを担当間で直接渡す。profile・速度比較・arena実時計は学習停止後の非競合枠に残す。合計親資源・個別残費は増やさず、同時実行時間は公平な速度比較に使わない。実開始は担当receiptで確認し、配分受理を実学習へ読み替えない。

original-only基準GPU fitは10:30:37 UTCに自然STOP/exit0/cleanup/remaining空・子回収。T100万保存行（366,638モデル入力distinct）を20epoch/156,260更新/2,000万seenまで学習し、fit/eval計51,878,032forward、whole742.821821秒だった。Rootは保存229点と実PNGを確認し、validation5万行のrowMSEは初期.856605583→末期.526443771、末期のfull-train MSE .517122594。記録最良は末期20epochで、今回の範囲では以前の小subsetの明確な末期退行を観測しない。収束・純粋な量の因果・独立game汎化・同時間棋力は未認定。許可されたcompile併走費を速度比較に使わず、trained native資格とfreeze/release後の一巡評価は別の受入れ条件として残す。[保存結果のRoot読取点](../research-data/ai-sigma/public-million-learning/baseline-fit-observed.json)。

凍結後の公開original-only保留5万行をBEST一候補/D/訓練由来定数だけで一巡し、row MSEは.529793889/.860192179/1.000029818、BEST符号正解率.80374だった。model入力distinct32,143、既知train入力35,887行MSE.514865732、未知入力14,113行.567753698。追加forwardなしの保存値集計であり、公開入力群を独立gameへ昇格せず、過去露出/historyはUNKNOWNとする。test開封後の再選定・再fitなし。この保留観測上の予測誤差改善を支持し、対局・同時間棋力は未測定。[最終評価・停止証拠と統合報告](../research-data/ai-sigma/public-million-learning/integration/report.md)。

同じ凍結BESTの追加native資格は19局面・16子局面/取り消しでScalar/Simd FT・差分更新・親accumulator/history/ply復帰がPASS、CPUとの最大差3.13e-7。残差headはScalarのまま。工程全体は期限終了で失敗し、数値段の親directwaitは未記録だが、native子のdirectwait成功、guardian回収・remaining空と記録した科学PID不在を確認した。Rootは停止版53sourceとprivate ELFをSHA照合し、この限定数値証拠と停止を既評価高速化の引渡し条件として受け入れた。工程全体の成功・速度・棋力を認定せず、再資格やsealed評価を探索着手の追加条件にしない。容量は完成済みRoot結果と既予約を共有し、短い検証の起動前/実行中に共有Cargo cache全体を反復走査する任意ガードを外した。[限定受入れと実配送](../research-data/ai-sigma/search-optimization/learning-native-handoff-accepted.json)。

続く同算術のinline入力バッファ候補は、固定BESTの独立oracleと8plain runで数値/探索結果が一致した。4組AB/BA合計のwhole-process時間比1.009769、target時間比1.026430で探索全体の利益は未支持。推論micro比.961114を全体の利益へ外挿せず、Rootは不採用を受け入れ、main評価器を変更しない。実行bitの初回起動拒否を保存し、2job完了後の追加測定は開始しない。Rootは保存値から時間比を再計算し、80member archiveの復元SHAを照合した。[結果と受入れ](../research-data/ai-sigma/search-optimization/evaluation-result/report.md)。

## 選択済みの棋力評価環境

ユーザーは既存Linux release Rust arenaを拡張する専用セッションを選んだ。評価器比較は同探索、探索比較は同凍結評価器、全体比較は固定Sigma設定とし、同時間棋力と同仕事の処理速度を分ける。開始prefix/historyを保存し担当側交換のpairで集計する。Sigma参照のabs(Q)<=0.2は暫定主book目安で、均衡や校正確率の保証ではない。初期盤面と傾いた・戦術診断を別群にする。

現arenaの単純scoreはunknownを除外するため、全予定slot/完了率/完全pair/部分pair/失敗理由と不確実性を併記する入口へ整える。100ms/手主条件・500ms補助条件を設定可能にし、時計・depth/node cap・最終完成反復・モデル初期化・TTと全caller費を区別する。[320契約](../research-data/ai-sigma/arena-evaluation/task.md)の初回は実装・fixture・小動作確認のみ。実用大book生成、凍結学習モデル本対局、十分量の棋力評価は別の具体配分で、環境の受付やソフト資格から強さを認定しない。重要な時計・集計・開局設計の変更はRoot経由で人間へ戻す。

## 次に人間が選ぶ事項

百万種類規模はユーザーの暫定設計目標で、理論的な必要最小量ではない。316の提案は、まず公開全43ファイル全域をtarget-freeに調べ、distinct適格モデル入力の量、反射/crosscycle露出、分布の代表性を測ること。小候補がDを超えることを本調査の開始条件にしない。取得・調査・新学習は未開始である。[316提案の正本](../research-data/ai-sigma/frame24-learning-analysis/next-main-learning-proposal-v1.md)。

| 競合案                              | 変わる判断                                               | 保存・全工程費の条件                                                                                                        |
| ----------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 全43のtarget-free多様性調査         | 百万種類規模の適格入力が存在するか、代表分割をどう作るか | Original/augmentation half対応を全域で確認できる場合640MiB inclusive案。確認不能で全行ledgerが必要なら1.25GiB案へ事前見直し |
| 全cycle・全域の層別input-only pilot | 量とalias集中の見込みを小さく調べる                      | 256MiB inclusive案。全corpus distinct数の認定はできない                                                                     |
| 調査後のcompact供給・代表学習       | 条件付き観測を保持し、未見分割とGPU学習を設計する        | 768MiB開始案にindex/scratch/model/log/Gitを含めて再見積り。全dense cacheとは別                                              |

全公開入力のraw f32は約49.0GB、現dense cacheは約47.5GBで旧12GiB枠へ収まらない。Bitset等のcompact表現は提案で、資格decoder・bounded batch API・性能は未検証。Whole costには取得、decode、native資格、hash/group化、alias確認、export、保存Git/archive、失敗と回収を含む。確認済み未使用予約とfresh保存量を束縛し、UNKNOWNや保護資産を空きへ換算しない。古い小subsetのthroughputを全域の保証にしない。

多様性調査を受け、人間が未見分割、条件付きラベル、epoch/sampler、GPU batch、曲線/選定間隔を選ぶ。GPUを本学習の主経路候補として、host展開・転送・更新・選定・保存・回収まで計測する。同batch再現と大batch/prefetch変更は別介入。CUDA4,000step追加比較とMPC校正は保留候補で、残予算や実装容易性だけでは開始しない。探索高速化の初回配分は上記契約へ限定し、データ・学習方針は変更しない。[タスク型研究](design/ai-research-team.md)に従って明示配分する。

学習側の独立セッションは319契約の仕事へ再用する。上の316競合案は過去の判断材料であり、全域censusの達成を今回100万行学習の入口にしない。大batchへの変更、追加データ規模・ラベル・モデル・特徴の変更、学習後の次の研究方向は実観測と全費からRoot経由で人間が選ぶ。

## 次の学習条件の優先度再検討（2026-10-06・未実行案）

現在のoriginal-only基準は訓練100万観測行/モデル入力distinct366,638、全43由来。20epochでfull train MSE .517123、validation .526444、最後の記録点が最良。10→15→20epochのvalidation .559321→.539274→.526444で改善は継続し、現在の曲線に持続的な過学習悪化は見られない。訓練にない入力14,300行でもD .731775→NNUE .563647だが、選定validationであり未見game棋力の証拠ではない。全公開originalのdistinctや新行追加によるdistinct増分は未確定。

ユーザーの優先度再検討に対する推奨は、現在のnative資格・凍結評価で基準を確認した後、学習率の詳細sweepよりデータ規模/多様性拡大を先行させること。学習率がデータに依存することだけでは増量の最適性は証明されないが、主要な次データ規模を先に決めることで小corpus専用の詳細調整を避ける。第一増量案は同source/original-only/alias split/モデルを保持した入れ子100万→200万観測行と実distinct/phase/source/条件付き勝敗の増分観測。元candidate T2,524,945という記録は保存2m corpusや2m種類の成立を意味せず、再処理・取得・新保存・供給・学習/eval・回収の全費とfresh資源配分を先に提案する。今のseries残/保存余裕/GPU残だけで開始しない。

比較では同じ100万データの学習継続を低費用な対照候補として残す。現モデルが未収束なので、増量candidateだけ学習仕事を増やして純量効果と呼ばず、同seen/更新数の比較と適正露出での収束比較を分ける。batch128/LR3e-5を基準として固定し、増量とLR/architecture変更を一実験に混ぜない。大きな最適化失敗・振動が出れば学習率の粗い見直しを前へ戻すが、現曲線だけでLR最適や新データ無用とは言わない。

正しい左右反転は既承認の次段候補として維持するが、対称入力の補完であり独立対局の増加とはしない。batch/供給最適化はデータ規模に対して供給/転送/更新/evalの支配費が現れた場合に優先する。特徴/モデル幅/教師変更は現状の適合と検証改善から最初の介入にせず、有力競合として保持する。探索の同算術評価処理高速化は学習のnative引渡し後に別writerで並行する。

この順位はRootの提案で、新データ規模・新fit・追加取得・GPU/forward予算・最終test再利用の実配分ではない。次の人間判断は増量の具体規模と全工程費を確認した条件選択。現在のforward残は約811万で、同じ20epochの追加学習を自動許可する量ではない。未選定評価と過去露出の扱いを保ち、opened testから候補を選び直さない。

ユーザーは反復NNUE評価・探索の通常hotpathで一時heap確保を避ける原則を承認した。小さなbounded bufferはstack、可変/大scratchはmodel/session/workerのsetup所有として再用し、長期weights/TTのheapは許容する。unsafe未初期化・巨大per-depthstackやFP計算順変更を代用にしない。前inline候補の速度不採用結果は維持し、原則だけで速度・断片化・latency改善を認定しない。[設計原則](design/ai-rust-migration.md#repeated-evaluation-memory)、[同担当への継続配分](../research-data/ai-sigma/search-optimization/heap-avoidance-continuation.json)。

棋力評価環境は単一Rust runnerのbook全履歴・受理時計・色交換pair・全予定分母・manifest/audit/journal復元をmainへ統合した。機能確認4予定slotはD/D人工一手ゴール2件と事前取消2件。対局は双方P1勝ち・完了pair .5、取消は未開始/unknown2で引分けへ変換しない。初回guardが完全履歴15手を追加手1手と誤認した失敗を保持し、対局は再実行せず第二jobで保存値のaudit/recoverを完了した。一pairのCIは出さず、strict_unknownは暫定受理時計、硬い返却・公平な棋力/Elo・二版search adapter・同時間Sigmaは未認定。[統合と運用証拠](../research-data/ai-sigma/arena-evaluation/integration/report.md)。

## 探索担当の自律継続と検証優先度

2026-10-06、ユーザーは検証候補の列挙・優先度決定と、不在中の自律的な作業継続を指示した。その後「時間枠や計算上限は設けないで。進められるだけ進めて。明日進捗確認するときに状況を見て停止をリクエストする」と明示した。[現行契約](../research-data/ai-sigma/search-optimization/autonomous-processing-contract.json)では、Rootが暫定設定した4時間・累積30分・各job5分・最大12job/6介入・2,000万forwardの上限を撤去する。停止指示まで同じ担当・worktreeで許可済みの同意味処理を継続する。CPU0/1・family RAM2GiB・GPU0は維持し、旧費・失敗・UNKNOWN・消費済みslotを取り直さない。重要な研究設計の変更は人間へ戻し、別の実行可能な候補へ進む。この一覧は全項目の実施義務ではない。

| 優先     | 検証候補                                                    | 判定と次の動き                                                                                                                                                                                  |
| -------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1        | ヒープ回避の現介入、accepted topology・所有・再入性         | 通常評価の確保回数/bytes、全幅での入力対応、初期化/コピー、親復帰を確認。速度不支持とメモリ原則の成立を分け、広い形状を未対応のまま完了としない。                                               |
| 2        | 凍結した今回BESTでの実caller支配費                          | 旧B3817の20.51%等を新重みの実績へ流用せず、評価・特徴/accumulator・距離/合法手・sort・TT/履歴と全費を必要な粒度で測る。時計の介入費、cold/warmと共有分母を分ける。                              |
| 3        | 評価入力、特徴/accumulator、undo用scratchの確保・コピー再用 | 同算術で反復確保を減らす。full/delta、複数モデル/session、P1/P2、make/unmake、cancel/errorの親復帰を独立referenceで確認。新shared mutable状態や巨大per-depth stackを避ける。                    |
| 3        | terminal/TT値が確定するchildでの不要な評価更新              | sourceの順序と費を先に確認。葉/terminal/TTの数学だけでなく資格検査・error/cancel/予算意味も保てる範囲で延期・省略を比較。                                                                       |
| 3        | 同壁配置の距離map・合法手・特徴計算の重複                   | 両goal全81升、壁追加、jump/P2、履歴を参照実装と照合。駒依存の計算を壁だけのcacheへ混同せず、既DSU/exact fallbackを維持。                                                                        |
| 4        | 実プレイヤー二手跨ぎの永続TT                                | 合法な両側の履歴を進め、同じプレイヤーの次turnで保持を検証。cold/warm、useful bound/cutoff/ordering-only、nodes、初期化/reset/drop/全caller費を出す。単に同rootを反復したhitを代用にしない。    |
| 4        | TT/PVで重複する合法性検査・key/hash生成                     | fullhistory/ply/model namespace/完全key衝突照合を維持したまま同計算の再用だけを比較。hitを得るためのkey省略・世代/置換方針変更をしない。                                                        |
| 5        | legal Action buffer・sort周辺の一時領域と再計算             | 現 comparator/最終Action順を維持し、生成・採点・PVのbufferを安全に再用。旧sort_unstable比較の不支持を保持し、同候補を根拠なく反復しない。                                                       |
| 5        | 残差headの同算術処理、layout・ループ・不要初期化            | 固定加算順序・FP32・活性化・scaleを保つものだけ実装。FT SIMDの既資格とheadを分ける。reduction順/FMA/精度変更は提案まで。                                                                        |
| 6        | 実callerの初期化・誤り・取消・時計・保存費                  | モデルload、TT/session作成・reset・drop、provider/move適用、completed depth/PV/node/leafとreturned/acceptedを別に測る。速度比較で未記録を0にせず、arenaのfairclock保証を勝手に昇格しない。      |
| 全介入   | 正しさ、性能退行、代表性、累積効果                          | 序盤/壁多数/jump/P1P2/終盤/履歴つき入力を結果前固定。baseline/candidateの値bits・Action/PV/depth/必要counterと親復帰を確認し、plain AB/BA全費・個別悪化を保存。一介入効果と累積版の効果を区別。 |
| 保留     | ゾブリスト、TT容量・置換方式の変更                          | 低優先度の候補というユーザー判断を維持。実測で支配費になれば比較提案へ戻し、今は新方式を実装しない。                                                                                            |
| 設計まで | MPC/ProbCut、LMR、futility、静止探索/延長、厳密solver       | 校正pair/戦術層・未選定評価・ON/OFF比較の不足と全費を整理する。今回の処理最適化許可で選択的枝刈り・新探索をONにしない。                                                                         |
| 設計まで | aspiration/新move picker/学習ordering・並列探索             | node削減と追加費、同時間棋力・正しさの検証案を提示。既探索window/order/並列性を変える実装は人間判断を待つ。                                                                                     |
| 設計まで | head SIMD/reduction変更・量子化・Wasm固有変更               | bit対応、許容誤差と精度/モデル条件、target依存の全費を示す。学習・特徴・モデル変更と同じ介入に混ぜない。                                                                                        |

優先2の結果で優先3〜5を更新する。小さな局所時計だけを根拠に選ばず、呼出回数・全費・判別できる不確実性を短く書いて着手する。反証・不支持や有限測定の揺れは保存し、安い診断一つの成功を別案の恒久gateにしない。必要なら判別に必要な測定時間を延ばすが、同条件の反復だけを独立局数へ数えない。大きな性能退行又はsource/数値不一致はその候補を採用保留にし、影響しない次候補へ移る。

通常の処理最適化・資格済み同条件測定は毎回人間へ返さず、この配分内で進める。重要設計は具体提案を保存して待ち、別の許可済み仕事を継続する。main採用・GitはRootが停止sourceと意味ある独立oracleを別に確認する。毎runの新reviewerや定期LLM監視、繰返しglobal/target容量scanを追加しない。GPU学習・教師/モデル変更・新arena対局・新取得・依存更新・必要資産削除は今回の対象外。

時間・計算量による作業停止上限は設けない。既存controller/guardianのjob全体経過時間を結果として残すが、累積予算の消費として扱わない。資料読取・整形・連絡・LLM作業の個別時計や過去UNKNOWNの監査を追加しない。研究判断に必要なwhole-search比較・支配費計測は維持し、介入時計と全job費を重複加算しない。原NEW90の費・予約・失敗・UNKNOWNは変更しない。明日の進捗確認は自動停止時刻ではなく、ユーザーの実際の停止指示を待つ。

探索の次profileで保存予測110,477,312Bが旧96MiBを9,814,016B超えたため、Rootは完了・main統合済み学習の予約768→736MiB、探索96→128MiBへ32MiBを前向きに移譲した。学習の最終必要予測754,305,575Bは新736MiBより17,446,361B小さく、合計864MiB・親12GiB・UNKNOWN128MiBは不変更。旧build未知予約や原資産は削除・取り直しせず、全target/global再scanやglobal freeからの新配分をしない。[移譲根拠](../research-data/ai-sigma/search-optimization/storage-reallocation-after-learning.json)。

ヒープ回避の最初のstreamed入力AA35版は、accepted幅1〜2048と同BESTの数値reference/full-delta/undoで限定一致し、観測head allocation88727→0、要求bytes24,843,560B減を達成した。一方、固定5root/depth3の8plain ABBAではprocess全時間比1.607596522/search1.621330671、micro2.600048715で全pair退行。Rootは保存recordsから再計算し、main不採用としてcanonical60d4475を保持する。繰返しReLU/iterator/compiler配置費は原因仮説で、heap原則やNNUE方式の否定ではない。次の小stack組立て改良はcanonical従来版を主対照として自律比較し、広幅・計算順と限定referenceを保つ。[結果・保存と不採用](../research-data/ai-sigma/search-optimization/streamed-input-result/report.md)。

## 全量公開データによる次の主学習方針（2026-10-07）

ユーザーは保存曲線の再分析と100万行の学習延長を次の主配分から外し、公開Sigma全量の適格original観測・正しく再構成した左右反転・ハイパーパラメータ調整を合わせて、効率的な収束を目指す方向を提案した。その後に同条件のSigmaとのMSE比較を行い、表現力増強と速度優先の縮小を選ぶ。Rootは次の主線として妥当と判断する。これは純量因果だけを分離する義務ではなく、全量での到達性能と全工程効率の最適化である。

公開43NPZの18,914,078保存行には旧naiveLRが含まれる。original前半9,457,039観測を原本とし、観測単位の不正と終了理由不明z0を分けて除外、有効な同入力別勝敗を保持する。全域の実適格・distinct数は準備の副産物として報告するが、独立census完了を入口にしない。原観測を訓練/validation/評価へ固定分割し、その兄弟反転を同splitに束縛。既開封評価は新候補の選定へ戻さず、新しい未開封評価の範囲・既露出を明示する。全公開データの利用と、評価用観測までtrainへ投入することは区別する。

旧後半plane flipをそのまま再使用せず、native幾何・壁anchor・両側視点・距離/feature・二回反転復帰・合法遷移のreferenceで正しい変換を確認する。正しい反転はまずtrain batchのonline augmentationとして保存二重化を避け、独立対局量と混同しない。主模型は現QF1+D/FT32/H32を固定し、GPU batch/LR/schedule等を新主corpus上の少数条件で粗く選定、validationの収束・振動・汎化とseen/updates/wallを比較して有力条件を収束まで進める。固定20epochのendpointを到達精度とはしない。評価結果を見て条件を再選定しない。

Sigma比較は凍結したモデル・同一の評価観測・同じSTM/±1尺度/targetでNNUEとSigma valueを測り、MCTS rootmeanをNN単体の基準へ混ぜない。Sigmaの公開data過去露出不明は留保し、全体/局面層のMSE・符号・校正とモデル推論/全探索費を併記する。MSE改善は公開観測上の予測支持で、同時間棋力とは区別する。差が残った場合も特徴・容量・最適化・教師の変動を切り分け、モデル/特徴拡張又は縮小・量子化の新重要設計を人間が選ぶ。

この節は次の方針の記録で、全量学習の新job開始ではない。実行前に全量のcompact/供給/保存、分割・評価基準、GPU/共有CPUと探索計時の非重複を具体化する。旧100万行run・開封結果・費/UNKNOWN・必要資産は保全する。

2026-10-07、ユーザーは学習側も時間枠・実行時間上限なく進めると明示した。上の全量方針を実配分へ移し、同じ学習セッションを再用する。終了時刻・累積GPU/CPU時間・MAXjob/forward・固定epochによる打切りを設けず、GPU batch/LR/scheduleを新主corpus上で調整しvalidation収束を科学的停止条件とする。CPU/RAM/VRAM/保存容量・停止要求・正確回収と既結果/未知費は保持する。旧曲線分析・100万行延長へ戻さない。[全量実行契約](../research-data/ai-sigma/public-full-learning/task.md)。新heavyは全量保存/供給の具体成立と公平計時の非競合後に開始し、新jobの開始は別に報告する。

全量担当は同セッションで実claim/source準備に着手。全originalを30%抽出/100万行切詰めなしで扱い、正規geometry20B+distance8B+z1B+由来5B+原input SHA32Bの66B/観測、正しい反転online供給を準備している（まだ導入未資格）。新growth900MiBをRootが確保。終了した固定運用の将来growth240MiBを前向き終了し、再取得可能なuvパッケージキャッシュだけをno-forceで除去、インストール済み環境・data/model/旧証拠・UNKNOWN128MiBは保全した。新scope/current+unused+UNKNOWN12,718,735,360B<12,884,901,888B、余166,166,528B。欠落した削除済みcache rootを限定再確認し、raw unknown観測も保存。全体scanを繰返さず完成結果を共有する。[容量配分と原証拠](../research-data/ai-sigma/public-full-learning/storage-admission.json)。旧learner保持736→728MiB、探索128→136MiBの追加8MiB移譲も同合計内で実施し、scratch次検証は予測140,156,928B<142,606,336B。学習のheavy readyで既探索jobの自然STOP後にslotを譲り、source準備は並行する。実取得/全量fitの成功はまだ未認定。

小stack入力（FT<=64は536B、広幅は同算術stream）とsetup-owned差分scratchは独立reference/P1P2/parent/error/cancelで限定一致し、head確保0、whole確保585,221→118,447を観測した。一方、小stackのcanonical基準search1.01810、scratch累積版1.04332で速度利益は未支持。メモリ原則の成立と速度採用を分け、main数学はまだ変更しない。同プレイヤー2合法ply後のTTでは初期target1240→1102node/cutoff1、3rootは同数/0、終盤399→397、seed/setup/drop全費も保存。全一般倍率・棋力へ外挿しない。[独立再集計と停止証拠](../research-data/ai-sigma/search-optimization/memory-and-tt-results/report.md)。探索scratch exactSTOP後の学習data/build優先を同学習担当へ実配送した。

全量入力境界323.1はr2の11path、独立10NN0 fixture、native exact1test PASSを照合し重大指摘なし。Rootは現11SHA一致を確認し、全original行別資格・既alias split/旧開封ID隔離・66B geometry→両QF1 view・正しいLR幾何を限定採用、全量データ準備を継続配分した。旧終局手番fixture失敗と途中版不整合は保存。実train-only50%/別RNG/fixedoriginalV caller、freeze/testとSigma入力は未確認の関連差分として同レビュワーへ追補し、data準備全体の恒久gateにしない。[入力境界の受入れ](../research-data/ai-sigma/public-full-learning/input-boundary-acceptance.json)。全corpus/liveGPU/汎化・棋力成功を先取りしない。

探索の壁map保存方式の次準備で4,804,608B不足が具体化し、Rootは完了旧学習保持728→723MiB（最終必要754,305,575Bを保持、余3,814,873B）、探索136→141MiBへ5MiBを前向き移譲した。予測147,410,944B<147,849,216B、余438,272B。合計864MiB・全量学習の別900MiB・親12GiB・未知128MiBは不変更。by-value方式は未実装/未資格で、同算術の独立referenceと全費判定を経る。全量data復旧のactualSTOPまで探索computeは開始せず、静的準備は継続する。[配分根拠](../research-data/ai-sigma/search-optimization/storage-reallocation-wallmaps.json)。

全量data初回は実探索STOPの27.087940秒後に開始し、実重複はなかった。遅れたSTART通知の解釈で担当が不要な自己取消を行い、105.863792秒/cancelledとpartialを管理失敗として保存した。buffered V/E/openedと0B exclusion gzipのため進捗countはdurablecheckpointではなく、同数学のflush/journal修復・別出力fullrestartへ進む。必要旧partial212,685,470Bを保存するとpeak1,089,155,545Bとなり、Rootは900→1040MiBへ140MiBを前向き追加。親同coverage予測12,865,536,000B<12,884,901,888B、余19,365,888B、UNKNOWN128MiB・旧資産/費不変更。再fullscan/partial成功化/全量subset化はしない。[復旧容量の根拠](../research-data/ai-sigma/public-full-learning/recovery-storage-admission.json)。

全量originalデータ復旧は2026-10-06T17:09:10.551108Zに自然終了、controller256.152866秒/子回収/cleanup成立。9,457,039元観測のうち9,255,077適格決着観測を保持し、T8,413,949/V419,150/newE371,978/旧開封隔離50,000。モデル入力distinctは各1,819,065/185,666/168,816/32,143で、game数ではない。201,962除外（native reason3=45,642、理由不明z0=156,320）、同入力別±1保持。Rootはmanifest SHA・4fileの66B×rows長・原分母算術・STOPreceiptを小確認し、payload再hash/評価labels読取を追加しなかった。GPUfitは未開始、actual onlineLR/RNG/fixedV/収束loop/frozenSigma callerは関連レビュー・実資格待ち。[全量データ結果](../research-data/ai-sigma/public-full-learning/full-data-result.json)。実行枠は探索の既coherent測定へ解放し、学習の新heavy readyで次slotを調整する。

WallMapsをprivate owned値にした修復版は、default Float/Quantized・queue全81cell/P1P2/635child・FT幅1〜2048/ScalarSimd・親/undo/error/cancelで限定一致。5rootの通常advance94,533回とhead88,727回のalloc/reallocは0、whole確保118,447→27,692、要求27,636,493→9,489,173Bを観測した。canonical累積search比1.055018/whole1.062009で速度利益は未支持、scratch版単独search比.996841も一般利益としない。Rootは対象SHAのsource捕捉・保存archive復元・28command directwaitの型訂正を確認し、main推論の採用は保留。[停止sourceと有限結果](../research-data/ai-sigma/search-optimization/wall-map-result/summary-preserved.json)。次のsmall-map pointer案は同意味の静的準備で、全量学習caller/GPU readyと次の実行枠を調整する。

全量T8,413,949原観測だけから尺度/定数を計算し、2026-10-06T18:06:48.431766Zに子回収/cleanup成立で終了した。定数z平均.009481279242、mu=[.104727805,.098713048]、sigma=[.051106475,.050166402]。D a0/b8は不変更。actual callerの関連独立レビューは重大指摘なし・11小NN0 PASSで、train-only正しい反転50%/別RNG、固定original V、fullV row選定、null horizon、T-only尺度、named INITIAL/BEST/LASTを静的確認。C1供給attemptとforwardの表示、C2診断CSV scope列は同担当/レビュワーで通常修正する。liveGPU/実batch・LR/config資格、Sigma/newE releaseは未達。[版と証拠](../research-data/ai-sigma/public-full-learning/caller-review/acceptance.json)。次は128/512/2048供給資格を比較してbatchを結果前固定、同init/order/scaleでLR3e-5/1e-4/3e-4と科学的収束を比較する許可済み計画であり、まだ本fit開始ではない。

探索のsmall-map pointer/workspace案へ追加5MiBをRootが前向き予約し、探索142→147MiB。必要153,440,256B<154,140,672B、余700,416B。親同coverage予測12,870,778,880B<12,884,901,888B、余14,123,008B、UNKNOWN128MiBと旧学習保持722MiBは不変更。追加全scan/必要資産削除/旧未知解放はしない。[配分根拠](../research-data/ai-sigma/search-optimization/storage-allocation-compact-map-workspace.json)。学習統計の実STOPで空いた枠は直接調整し、次のGPU供給/学習readyと探索時計を競合させない。

actual caller通常修復r3はC1供給attempt名/C2診断CSV scopeを解消し、同reviewerの関連2小NN0＋反転RNG mask確認で新指摘なし。2048元行の同一反転mask/初期Adam状態で128/512/2048 chunkの同目的更新を比較し、warmup後5測定medianで供給サイズを選ぶ静的計画を確認。Optional remaining-node修復も静的整合、原Rust compile failureは保存。Rootは固定r3のこの範囲のみ受入れ、liveCPU/CUDA/native数値・供給時間/VRAM・null trainer/checkpoints/画像・実3LR configs・Sigma/newEは実資格待ち。[関連修復の受入れ](../research-data/ai-sigma/public-full-learning/caller-review/repair-r3-acceptance.json)。

TT cached手だけの合法性確認候補は、全legalset/history/terminal/ply意味を保つ通常処理案として静的準備中、まだ未build/未資格。Rootは具体forecast159,207,424Bへ探索147→152MiBの追加5MiBを前向き配分し、余176,128B。親同coverage予測12,876,021,760B<12,884,901,888B、余8,880,128B、UNKNOWN128MiB・全旧資産/予約を保持。全域walk/未知解放/必要資産削除をせず、現在の学習supply実STOP後に全Action一致の独立oracleとwhole比較を行う。[配分根拠](../research-data/ai-sigma/search-optimization/storage-allocation-tt-legality.json)。

全量学習の供給修復job f09328c3は18:30:39.489088Zにexit0/全child wait/cleanupで終了。初期＋破棄2 Adam更新のCPU/CUDA/native対応、FT Scalar/Simd/full-delta/undoと小null-horizon trainerの自然停止/INITIAL-BEST-LAST/PNGを限定PASS。事前規則によりbatch2048を選択：同2048行の暖機後供給・転送・更新medianは128=.070205秒、512=.021780秒、2048=.007057秒。これは供給proxyで、batch間の収束/汎化優劣や本fit全時間を認定しない。旧18.413935秒compile失敗を含む全費59.393668秒を保存。Rootは小receipt/全childwait/版・privateELF SHA/選択規則を確認し、同init/order/scale/反転RNGで3LR3e-5/1e-4/3e-4の実config固定後の本fitへ進める。[実供給資格と選択](../research-data/ai-sigma/public-full-learning/supply-result/acceptance.json)。本fit/最終Sigma/newEは未実施、探索の具体TTentry自然STOP後に最初のfit枠を直接調整する。

初回fullfit前に3LR実config/input/guard/jobをlocked cohort db5076c6へ固定。batch2048・epoch4109updates/tail765・warmup257・診断514、LR以外同一、実qualified INITIAL2ddacbf8一致。r4関連独立レビューは重大/通常指摘0・純NN0 INITIAL不一致拒否1PASS。Rootは12設定SHAとcohort/binding、保存archive byte復元を確認。予定どおり科学的収束まで逐次fitへ進め、毎fitレビューや追加RootACKを要求しない。r3 live供給資格とr4静的/NN0 guard資格を分け、本fit/最適LR/最終Sigma-newE成功は先取りしない。[結果前に固定した条件](../research-data/ai-sigma/public-full-learning/cohort/acceptance.json)。

探索のordered FT membership案は、sorted ID契約を保ち、全parent順減算→child順加算を同順FPで行う二分探索反復の処理置換として静的準備のみ。Rootは具体次forecast164,712,448Bへ探索152→158MiBの追加6MiBを配分、余962,560B。親同coverage予測12,882,313,216B<12,884,901,888B、余2,588,672B、UNKNOWN128MiB/全旧assets/build上界保持。[配分根拠](../research-data/ai-sigma/search-optimization/storage-allocation-ordered-ft-membership.json)。初回fullfitを優先し、並行可なのは学習privateELF/libraryとsole target writerを確認したpure compile/test-no-run/Clippyのみ。FT/NN oracleとplain公平時計は実fitSTOP後、まだ未資格/未採用。

初回lr3e-5全量fitは20:26:33.705610Zに候補出力20MiB上限で失敗終了、controller5,107.178185秒/子回収/cleanup成立。時間/epoch上限・数値非finite・RAM/VRAM超過による停止ではない。149epoch/612,241updates/1,253,678,401seenまでfullV150点保存、last rowMSE .4593671733/記録最小.4593593780(step595,805)。科学的収束完了やcheckpoint freeze認定はせず、curve/checkpoint帰属は担当が回収する。診断JSON約9.95MBとsampling NPZ約6.35MBが出力を圧迫し、旧観測/source/費を保持したlossless compactログの通常修復へ。忠実な再開に必要なoptimizer/scheduler/selector/epoch-reflection RNG状態の有無を確認して次entryを具体化し、自動再run/seed変更/旧費の返却をしない。実行枠は探索の既finite numeric質問へ解放、全量fit復旧readyを次優先。[原失敗と保存観測](../research-data/ai-sigma/public-full-learning/first-fit-output-stop/report.json)。

初回fitの後続回収で、元r4 sourceとSHA一致fullV150点から固定EarlyStopping(patience8/min_delta1e-4)の初発epoch149をRootも純scalar再現した。significantbest141からstale8、厳密な記録最小BESTはepoch145/595,805step/.4593593780。LAST149とBEST145のdurable位置・native重みSHAが対応し、旧判定「科学的停止未完了/未確認」をこの狭い事実へ訂正する。Rootはoptimizer再runせずartifact-only帰属完了を選択し、その後同INITIALで残りLR1e-4/3e-4へ進める。原controller exit1/ログ出力失敗/5,107.178秒/欠落formalfreeze/invalid訪問NPZは保持、149全epochからの訪問数は明示derivedのみ、追加transient UNKNOWN。忠実resumeはscheduler/RNG等未保存のため不支持。全学習native live資格・cohort最終採用・Sigma/newEは未達。[保存traceからの停止帰属](../research-data/ai-sigma/public-full-learning/first-fit-output-stop/scientific-stop-attribution.json)。

探索のcanonical単独orderedFT比較は、旧複合版の不支持から単独効果を推定しないための別質問。修正後forecast169,955,328Bは追加4MiBでも不足し、Rootは158→163MiBの5MiBを別途配分。未配分prospective pool7,446,528Bから3,252,224Bのみ移し、旧268の4MiB保全予約を残す。残り1,990,656Bを親余裕から追加し、同coverage12,884,303,872B<12,884,901,888B、余598,016B/UNKNOWN128MiB・旧actual/assets/caps保持。全scan/全史audit/削除なし。過去の4MiB拒否は保存し、新しい具体財源と修正予測でのみ成立。[配分根拠](../research-data/ai-sigma/search-optimization/storage-allocation-canonical-ordered-ft.json)。学習の描画IO修復・次fitreadyを優先し、source準備から独立oracle/有限12pair比較へ直接調整する。

全量3LR固定cohortのfit観測が揃い、事前のfull original V rowMSE最小規則はLR3e-4を選ぶ。BESTは3e-5=.4593593780(epoch145)、1e-4=.4525317597(epoch102)、3e-4=.4486358588(epoch75)。第三fitは22:35:04.921210Zにexit0/科学的early stop75epoch/308,175updates/631,046,175seen、子回収/cleanup成立で終了。Rootは停止receipt・fresh記録PID identity不在・選定算術・BEST重み1c84ab39のbyte SHAを確認した。第一fitの原exit1/出力失敗と別artifact-only停止帰属、第二fitの初期PNG失敗は保持する。この比較は固定3候補内のvalidation選定であり最適LR・独立汎化・棋力・default採用の認定ではない。選定済み模型のnative資格、global freeze、同レビュワーでの関連Sigma/newE境界と一巡評価へ進め、追加fitを行わない。[検証選定と停止証拠](../research-data/ai-sigma/public-full-learning/cohort-result/validation-selection.json)。

ユーザーは比較範囲上端3e-4が最良だったことを受け、より大きい初期学習率の比較を明示指定した。上限は未確認であり、旧3LR内の最小選定を暫定結果として保持する。同INITIAL・batch2048・全T/固定V・optimizer/反転/スケジュールを固定し、1e-3→安定なら3e-3、改善する上端が続けば1e-2へ段階的に拡張する。新候補と保存容量は結果前に束縛、失敗/旧費を保持し、validationで範囲を絞る。最終Sigma/newEは拡張選定とfreeze後まで保留する。これは高LR比較の許可であり、feature/model変更・普遍的LR上限・追加保存の自動超過を意味しない。[継続契約](../research-data/ai-sigma/public-full-learning/task.md)。

高LR探索についてユーザーは最初に極端な上側値を試して二分探索のように絞る方針へ変更した。先の1e-3→3e-3案を置換し、まず初期LR0.1、悪化/非finiteなら既良好3e-4との倍率中点約.005477から絞る。validation MSEの単調性や普遍的安定上限は未証明で、同scheduleでの初期振動・減衰後の回復・最終観測を区別する。全他条件と未開封評価の保留、資源/旧出力保全は不変更。新候補・判定基準・inclusive保存予測を結果前に固定する。

ユーザーはヒープ回避の目的を「評価ごとの一時確保を避ける。事前確保ヒープは利用可」と明確化した。大きなmapのby-value案は確保削減とコピー/ABI変更が混在しており、純粋な一時確保回避の遅延原因と断定しない。探索担当へcanonical算術のままsetup-owned入力bufferを参照して使い、ReLUを一度処理・連続slice内積・不要なmap payload移動を避ける最小比較を優先する指示を渡した。既compact版の所有管理費/コピー因果は未分離、main adoption/速度利益は未認定。旧patch/負結果を保持し、容量/学習quiet slot成立後に独立referenceと実callerの比較を行う。

事前確保入力scratch案の必要予測174,936,064Bに対し、Rootは完了済み保守fweの将来用予約94→89MiBから探索163→168MiBへ5MiBを移譲した。既completed observerは保守source/records/verify実成果を含み、actual roots・全old build UNKNOWN・未知128MiBは保持する。親予測12,884,303,872B/12GiB不変、探索余1,224,704B。実資産の削除や再全scan・過去cap/費resetはなく、保守の新build/wholeverifyは配分しない。学習midpoint499b7cbeの実STOP/quiet後に実数値比較、許された別CPU purecompileは直接調整する。[保存配分](../research-data/ai-sigma/search-optimization/storage-allocation-evaluation-input-scratch.json)。

高LR上側0.1は科学的stop9epoch・検証BEST.4991794558で有限のまま旧3e-4より悪化、発散上限の証明とはしない。次の初期LR.005477225575は23:27:43.522226Zにexit0/科学的stop65epoch/子回収で終了し、BEST63epoch/.4284179384へ改善（旧.4486358588から約4.5%減）。BEST時の実LRは2.13954124e-5で、初期LRと減衰を含むtrajectoryの結果を区別する。Rootはreceipt/directwaitとBESTbyteSHA9e9c30dbを小確認、未開封Eは閉じたまま。既事前規則の次倍率中点.02340347319を同条件で準備し、結果前にconfig/capacityを固定して継続する。探索のpurecompileはprivatebinding条件で並行可、数値/公平clockは次fit実STOPを待つ。旧3LR/原失敗・全費・未知を保持する。[midpoint停止証拠](../research-data/ai-sigma/public-full-learning/cohort-result/bracket-midpoint1-stop-receipt-v1.json.gz)。

高LR midpoint2初期.02340347319は23:57:14.960425Zにexit0/科学的stop50epochで終了、BEST50 rowMSE.4304323988で incumbent midpoint1 .4284179384を改善しなかった。数値は有限、effective BEST LR9.141981716e-5で初期値と区別する。事前の倍率中点規則は次.01132193013を用意、未開封E/Sigmaは保留。全旧outputsと次20MiB・他17MiBを保全する保存不足に対し、Root保守将来予約89→86MiBから学習1040→1043MiB/evidence80→83MiBへ3MiB移譲した。親12,884,303,872B/12GiB・探索168MiB・UNKNOWN128MiB・全実資産不変、予測1,091,984,108B<1,093,664,768B。探索の既準備scratch一問を先に実quietで確認し、そのexactSTOP後に次fitを調整する。[前向き容量配分](../research-data/ai-sigma/public-full-learning/storage-allocation-midpoint3.json)。

事前確保・参照入力scratchは、setup各root280B一回・通常head88,727回のalloc/realloc0と、独立算術/全幅/実caller/親復帰/error/cancelの6限定fixture・24plain一致を確認。main基準whole比1.024989/search1.015319で速度利益は不支持、12組6速い/6遅い・中央値.996752、短いclockの確実な退行量も未認定。Rootは全停止source/依存SHA・main基準不変・小圧縮archive byte復元を確認し、source/proofs/旧2compile失敗を保存した。モデル入力scratchの通常確保削減は成立するが、全callerのheapzero・断片化/latency/棋力改善は未認定。API/所有と現役callerの採用判断を分け、main推論は不変更。[保存結果とsource](../research-data/ai-sigma/search-optimization/input-scratch-result/preservation.json)。

学習の最新人間指定は初期LR0.01固定と減衰率の調整で短いepoch/更新数での収束を狙うこと。midpoint3の自然STOP後、初期LR二分探索を盲継続しない。まずfactor0.5対0.25の準備案を作り、同条件でfullV到達閾値・更新/seen/全時間・実LR・最終MSEを比較する。新pairの規則/config/容量は結果前固定し、現1043MiBから2x20MiBを自動配分しない。旧fit/失敗を保全、newE/Sigmaは保留。[固定初期LRの準備案](../research-data/ai-sigma/public-full-learning/initial0p01-decay-focus-draft-v1.json)。

ユーザーの明示依頼でCriterion 0.8.2をdev-onlyで現役bench入口へ導入した。暖機/反復/統計による速度差判定を現役bench入口へ接続し、正しさ/確保counter/全process費は既存検査を再用する。TT cold/setup/drop込みとwarm履歴・seed費を区別し、未採用scratch APIを導入だけのためにmainへ混ぜない。必要なdev依存/取得をこの範囲に許可、現main APIのcompile/CLI資格と、学習STOP後の実測を分ける。Root保守将来予約86→22MiBから探索168→232MiBへ64MiB移譲し、親12,884,303,872B/12GiB・学習1043MiB・UNKNOWN128MiB・全実資産不変。新registry prefix/cache/linkerまで次forecast内へ明示し、全walkや旧未知返却をしない。[導入配分](../research-data/ai-sigma/search-optimization/storage-allocation-criterion.json)。

初期LR.01132193013 midpoint3は00:37:47.479416Zにexit0/科学的stop61epochで終了し、BEST58 rowMSE.4250526444へ改善（effective BEST LR2.211314479e-5）。次は最新人間指定の初期0.01固定・減衰倍率.5対.25で、旧LR二分探索は継続しない。結果前protocolは既best+.001=.4260526444と.44/.435/.43の実記録到達、更新/seen/全時間/実LRと最終精度を比較する。RootはFIRST .5候補のみ保存予測に5MiBを保守将来22→17MiBから移譲し、学習1043→1048MiB/evidence83→88MiB、親12,884,303,872B/12GiBと探索232MiB/UNKNOWN128不変。全旧出力・失敗を保全、第二.25は第一actualoutputから次proofを作る。Criterion導入の現在具体entryがあれば自然STOPを待ち、未使用slotを恒久予約しない。[第一候補容量](../research-data/ai-sigma/public-full-learning/storage-allocation-decay-first.json)。

Criterion依存の27追加packageは旧lockの全90identityを保持して取得したが、最初のlock解決手順誤りと次のbuild42MiB分類guard超過は失敗として保全した。記録された新growth合計63,135,744Bは元64MiB内で、残りbench ELF/linker・Clippy・圧縮proofの具体的forecastをRootが受け入れ、保守将来17→3MiBから追加14MiBを移譲、探索232→246MiB（親全体・学習1048MiB・UNKNOWN不変）。以後は新envelope全体で管理し、分類別の恣意的停止を増やさない。main導入は下記停止版の受入れで完了し、数値smoke/統計測定は未実行。初期0.01/factor.5の学習中は純software資格のみ実行した。[完了用配分](../research-data/ai-sigma/search-optimization/storage-allocation-criterion-build-finish.json)。

Criterionの停止最終版5pathをmainへ統合した。現main API/mathは不変、旧lock90identityを全保持して必要な27packageのみ追加。offline/locked release bench no-run・モデル未読のearly help・scoped release Clippy -D warningsはPASS。Rootはsource/依存SHA、圧縮実行image復元、全3command wait/cleanup、archive各memberと整形を照合した。headのfull FT事前計算はtimer外、探索呼出の通常root FT準備はtimer内で、cold TT/setup/dropと二手進行後warm seed費を明示する。旧4失敗・r5旧表示版・欠測wait/peak/costは保全。数値CLI smokeとCriterion速度統計は未実行で、学習exactSTOP後に同担当が非競合枠で継続する。source導入を速度利益/API scratch採用へ昇格しない。[受入証拠](../research-data/ai-sigma/search-optimization/criterion-introduction/acceptance.json)、[現在の使い方](development/rust-ai.md#criterionでnnue評価alphabetaを測定する)。

初期LR0.01・減衰倍率0.5の第一候補は01:28:33.511787Zにexit0/科学的early stop62epochで終了。BEST=LAST62、fullV rowMSE.4275190322で、事前の近似到達目標.4260526444は未到達（.44/.435/.43は12/20/32epoch）。有意なstop基準の更新は54でstale8、厳密BESTの微小改善62と区別する。実T各62visit/V optimizer0、PT/native parameter bytes/Adam/INITIAL・尺度・config・cache・source・artifact/PNGはmetadata範囲で確認、訓練済native live parity/global freeze/newE/Sigma releaseは未実施。全費2362.165468sは純Criterion compiler併走区間を含み、減衰の因果的速度差へ置換しない。[停止・保存結果](../research-data/ai-sigma/public-full-learning/cohort-result/decay-factor0p5-stop-collection-v1.json.gz)。

最新の直接人間指定は、次の検証runより先に現全量学習の全曲線を詳細分析すること。既定factor.25は変更せず保留し、第一actualroot4,927,300Bから算出した次evidence不足5,023,894B/+5MiB案は準備証拠のみで、Rootは配分・起動していない。trigger/cosineの議論を手法変更の採択にしない。分析は保存fullV/診断scope/実LR・decay/到達点/残余改善/失敗と併走の帰属を分け、newE/Sigma閉鎖を維持する。学習の未使用時計を恒久予約せず、既に許可した探索Criterionは具体容量・actual quiet条件が整えば継続できる。

全量8条件・583 fullV点の保存曲線分析が完了した。初期0.01は10epochでV.442085、BEST62の.427519まで残り.014566があり、10epochで同精度へ収束した証拠はない。近傍目標.4260526444への最初の到達は初期.0113の36epoch。初期0.01の16epochで.000307の改善が絶対閾値.0001を超えて待ち回数をリセットし、17〜19の3回不改善で初めて半減した。13〜19の純改善.000160に対し次epochは.005105改善したが、早期減衰の精度利益は未検証。変更しない観測prefix上の最初のtriggerはpatience1なら15、0なら10であり、その後の曲線を予測するものではない。次の人間判断は同triggerの倍率.25、早いPlateau trigger、予定したsmooth decayのどれを比較するか。手法変更/次fitは保留、旧失敗・費・UNKNOWN/newE/Sigma閉鎖は維持する。[全曲線報告](../research-data/ai-sigma/public-full-learning/saved-curve-analysis-v1/report.md)、[19epochまでの判定](../research-data/ai-sigma/public-full-learning/saved-curve-analysis-v1/first-decay-at19.json)。

Criterionの数値CLI確認と同一版反復測定は01:45:19.302605Zにexit0/全3bench directwait/cleanup[]で終了した。30 IDs PASS、5局面のhead bits/Action/PV/depth/stop/23counter/親履歴・保持メモリは3起動で一致。初期局面head/coldだけを同じELFで2回測定し、相対meanはhead−1.009%（95%CI −2.562〜+.767%）、cold+1.477%（+.640〜+2.394%）。headは差検出なし、coldはCIが1%noise閾値を跨ぐ。50samplesは独立process50回ではなく、候補比較/速度利益/採用は未実施。旧4software失敗・欠測wait/peak・全費は不変、main sourceを変更しない。[限定測定報告とraw証拠](../research-data/ai-sigma/search-optimization/criterion-smoke-v1/report.md)。

最新の直接人間指定により、次の探索速度の問いは従来版と事前確保したborrowed input版のCriterion比較と、明確な悪化が再現した場合の詳細profileによる原因調査となった。通常headをone-shot setupで代用せず、Search setup/drop込みの全探索とhead・processを分け、固定モデル/同算術/同探索結果を確認して交互process順・判定規則を結果前固定する。悪化判定は信頼区間とnoise閾値・process間の再現性を併用し、profileをplain比較から分離する。buffer access/check/初期化・copy・dispatch/inliningは候補仮説であり原因確定ではない。未採用FT/TT/maps/sortを混ぜず、main API/モデル採用は別。既存容量内の具体build/image/profile出力寿命予測が必要で、旧UNKNOWNを返却しない。準備中の現行TT費用測定を中断せず、学習の次実entryを優先し、そのactualSTOP後に比較clockを調整する。

学習担当への新しい直接人間指定は、有望と判断するscheduler条件を選び実際に試すこと。同担当は初期0.01/factor.5でpatienceだけ2→1とするONE条件を結果前固定した。Rootは8既存候補のnamed PT/native weightsが各保存rootに含まれることを直接metadata確認し、未使用将来weights16→10MiB/evidence88→94MiBへ6MiBを内部再分類した。学習総1048MiB・親12,884,303,872B/12GiB・探索246MiB・UNKNOWN128MiBは不変。新evidence予測98,295,388B/98,566,144B、全体1,097,544,153B/1,098,907,648BでONE入口のみ採用し、旧出力/失敗・空models rootを保全、factor.25は保留。既定INITIAL/cache/尺度/RNG/元V/early stopは変更せず、newE/Sigma閉鎖。現行Criterion TTのexactSTOP/cleanup後にfresh physicsと実guard/inputを新bindingへ固定して入る。[内部配分・直接資産証拠](../research-data/ai-sigma/public-full-learning/storage-allocation-trigger-patience1.json)。
