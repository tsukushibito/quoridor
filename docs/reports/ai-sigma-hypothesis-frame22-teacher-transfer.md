# frame22 教師情報とD保持NNUEの転移 / quoridor-4lc.274

独立36familyを追加したBは、固定旧validationで選んだBESTのrootmean誤差をAより改善しなかった。新12selection-valでもA/B BESTは初期距離Dを超えず、学習済み重みは採用しない。Bは2000step後のvalidation悪化を小さくしたが、原因を量・教師品質・表現の一つには絞れない。新selectionは選定診断であり、独立test・棋力評価ではない。

担当hypothesis。frame22の11:36:03–15:36:03 UTC許可内で、管理worktree `/.worktree/frame21-features` のPython比較adapterと自域診断だけを変更した。実パスは `/workspaces/quoridor/.worktree/frame21-features`。Rust、main学習source、親運用、共有環境、Git index/commitは変更していない。旧268科学、失敗版、openedtest/173正式198局は変更・再利用していない。科学は4jobを全消費し13:14:46.826002 UTCに全終了した。追加学習・forward・再評価は行わない。

## 保存教師の解析と対照の問い

旧train96/4653行、選定validation24/1248行の5901行を、元train/validation-canonical、training-labels、fixed-exposure-mask SHAへ束縛した。元maskは `10b502cd9e1c5334e56a3f460ef3edff7f822c8f52f69c3af53529c67c45d5f5`。解析はCPU1単1、NN0。rootmeanはK64探索教師で、厳密minimaxや初期局面の真の期待勝率ではない。zは一gameの終局結果であり、rootmean-z差だけで誤教師とは判定しない。

| 観測 | train | 旧選定validation |
| --- | ---: | ---: |
| rootmean-z相関（row） | .832520 | .831306 |
| rootmean-D相関（row） | .654913 | .524762 |
| D残差とz相関（row） | .741615 | .768064 |
| D rootmean game等重みMSE | .421411 | .489404 |
| rootmean-z game等重みMSE | .278202 | .279601 |
| 序盤rootmean-z game等重みMSE | .844405 | .653178 |
| 終盤rootmean-z game等重みMSE | .023963 | .063208 |
| abs(rootmean)>=.9行 | 2633/4653 | 639/1248 |

全game/cohort/phase/残壁/距離群は `analysis.json` に保持した。phase平均はそのphaseに行を持つgameに条件付けられ、群間で同じ分母とは限らない。row相関はgame内相関を含む。旧train内state/実QF1署名重複13行、val内2行、旧train-val間共有は0。historycountは欠測で、hashから反復回数を推測しなかった。

距離で説明し切れない教師情報と序盤の不確かさが残るため、今回の主差は独立family追加とし、target/rootmean・モデル・初期関数を保持した。rich経路は残差の予測力と更新費の根拠が増せば再検討する。DAG4一条件の不支持を全経路特徴の否定にしない。

## 固定A/B条件と新cache接続

Aは旧96train4653行。Bは登録最大完成prefix36の新train1328行を追加した132game/5981行。producer273のactive24/active48は同48familyの兄弟attemptで、ownerの結果前品質・wholeguardian費規則によりactive48だけをcanonical採択した。2条件を独立96familyと数えない。新144attempt案・future-eval16案は未実行保留、14:15 prefix0 branchは登録を保持したまま未使用である。

QF1 shared312→32×二視点、STM/相手concat64＋距離2＋route4、hidden32 ReLU、線形残差R。出力は `tanh(8*(raw_f32_dopp-raw_f32_dself)+R)`、head0初期化。route4は旧train統計で変換した後に両条件とも正確に0maskした。距離μ/σは旧trainだけから定めた共通固定値で、raw D skipへ尺度補償を二重適用しない。Adam LR1e-4/WD0、seed19080311、game等重みsampling、batch128、2000step、各256000学習samples。同形・同initial tensor SHA `ec4167ccb5042cfe937b23850a1b52d1cd9cf6c3fb1d348627bfe6cc7d023cc5`、fresh optimizerを保持した。

結果前の10評価点は `[0,1,5,20,50,100,200,400,1000,2000]`。BESTは固定旧valのgame等重みrootmeanMSEだけで選び、step0も候補にした。A/BともBEST200。新selectionの結果で候補・点・設定を選び直していない。256000/全train行数はA約55.0183 epoch、B約42.8022 epochで、game等重みsamplingの露出は均一row epochではない。同seedでもデータ追加によりbatch列は変わる。新tau1全plyと歴史的16以降argmaxの分布差を含むため、純数量因果ではない。

producer正本は main `research-data/ai-sigma/frame22-teacher-throughput/274-cache-handoff-v1.json`、`canonical-active48-cache-v1`、`registered-train-groups-v1.json`。元family UIDとselected run_idのaliasは登録prefix/ordinal/seedで束縛した。cache全体に許可selectionラベルを含むが、train partitionをstats/fit前に選び、mask predicateにはtarget/z/lossを使用しなかった。旧形式を復活するJSON全コピーは作っていない。

Python独立接線は native `quoridor-tensor-row-v2` の `metadata_schema` と `ids_order=P1_then_P2`、`distance_order=STM_then_opponent_f32`、`tensor_view_order=STM_then_opponent` を検査する。新1328行の元P1P2疎IDs＋sideを実cache STM順x/dへ対応し、float32 distance bitsを含む実モデル入力を確認した。新train対旧valのstate・history文字列・実入力・OR共有は各0、1328行/36group全適格、0eligible group0。

新旧history hash format互換は **UNVERIFIED**。文字列非一致を完全history非露出の保証にせず、state/actual input検査のcoverageと区別した。fullhistory/count欠測を推測で補完していない。

## 曲線と新selection一巡

| 条件/step | train rootmean gameMSE | 固定旧val rootmean gameMSE |
| --- | ---: | ---: |
| A initial | .421411 | .489404 |
| B initial | .409555 | .489404 |
| A BEST200 | .385503 | .478510 |
| B BEST200 | .380739 | .479679 |
| A 400 | .255723 | .524666 |
| B 400 | .263161 | .497147 |
| A LAST2000 | .030967 | .849425 |
| B LAST2000 | .032026 | .679028 |

A/Bの全10点、row/game等重み・group/cohort/phase・真z/sign/saturation・定数基準・gradient記録を各checkpoint `curves.json`、`gradients.json` と自域summaryに保存した。グラフは各 `learning-curves.svg`。train fitと旧val選定利益、後半悪化を分けて読む。

新selection12game392行は、A/B BEST/LASTと共通initialの5unique weight/configを `selection-diagnostic-freeze-v1.json` SHA `65ce4f5d13163aca6aa7e2af53ae1f1d566826398e160b3ef7b76aa4eabcca17` へforward前に固定した。登録新train最大36＋全旧train/旧valを参照し、label-free state OR history文字列 OR実STM-f32入力maskをforward前に確定した。全392行適格、除外0、予定12/G+12、0eligible0、欠測group0。主評価と全行secondaryは同じ分母になった。history形式互換の未確認はここにも残る。

| 固定モデル | 新selection rootmean gameMSE | 真z gameMSE | z符号正解率（row） |
| --- | ---: | ---: | ---: |
| Initial（距離のみ） | .392634 | .630042 | .724490 |
| A BEST200 | .399633 | .635317 | .767857 |
| B BEST200 | .399173 | .635439 | .750000 |
| A LAST2000 | .979297 | 1.165082 | .584184 |
| B LAST2000 | .921886 | 1.102489 | .591837 |

学習済みBESTの符号率は初期より高いが、元のrootmean主指標では改善せず、符号率へ採用基準を交換しない。解析f32 Dのrootmean MSE `.39263407267052125` とTorch initial `.39263407579270954` の有限差も保持した。定数基準は各対応trainだけから得た `data.json.constant` を再用し、新selectionへfitしていない。`distance_analytic` のconstant0は明示的な非fit参照であり、train-fit定数と混同しない。

`newselection-result-r1/result.json` に全group/phase・主/secondary・定数・真z/sign/saturation、`row-predictions.jsonl.gz` に必要per-row値、`mask.json` に全分母を保存した。newselectionは条件診断に開いた選定資料で、未来未使用eval0。旧openedtest/173を開いていない。

## 数値・ソフトウェア検証と管理失敗

A/B initial Dbit確認、Torch/native abs1e-6+rtol1e-6、full/deltaは元事前tolを保持した。A maxabs1.9371509552e-7、B1.7881393433e-7。Bは固定旧12＋新12（P1/P2各6）のwitnessで対応した。producer自己testはこの独立対応検証へ読み替えない。

fake v6の「9PASS」速報は誤りで、実ログは **8PASS/1FAIL** だった。整形済みcomprehensionへの文字列置換が不発で、metadata order拒否guardが挿入されていなかった。実ログ確認後に即訂正し、必要field・実metadata_schema/order検査をprospectiveに追加、v7/v8の9PASS、format/check/lintを確認してからBを開始した。旧Aの科学source/weights、v6 receipt/失敗ログ/当時source SHAは変更していない。失敗時ソース全byteはその時点でarchiveせず、hashとlogは保持するが完全復元を保証できない。この不足を `software-repair-v7.json` に明記し、修復成功を原失敗へ付け替えない。

smallfakeはpartition/test拒否・family漏洩・OR predicate/label非依存・実f32入力・共通scale・P2/STM・欠測label分母・schema/order拒否を対象にした。現在手書きPython7fileは担当範囲だけ既Ruffで整形→formatcheck/lint/ASTを実施し、最終receiptを保存する。凍結archiveは整形しない。

## 費用・保存と次の一案

| science job | child wall秒 | NN samples | peak family RSS B |
| --- | ---: | ---: | ---: |
| saved解析 | .397550 | 0 | 64147456 |
| A学習＋評価＋parity | 5.310011 | 315226 | 893341696 |
| B学習＋評価＋parity | 4.925750 | 328506 | 886513664 |
| 新selection一巡 | 1.754103 | 1960 | 627560448 |
| 合計 | 12.387414 | 645692 | peakは加算しない |

CPU1単1/Torch intra・inter1、GPU0、warm0。4/4科学job全停止/exit0/wait、science-ledger/各stopのPID-starttick identityは不在。A/B各256000学習、10点評価にparity216ずつ、新selection5×392=1960を全課金した。初期科学前にcurrent frame22 loaded24hash・正scheduler/monitor identity・実CPU/RAM/保存headroom・producer/foreign停止をfresh確認し、275/273/277の固定時間測定と重ねなかった。科学秒とsource/管理・待ちLLM経過を混同しない。source/管理の未測累積はUNKNOWN、必要検証の測定logを残す。

新32MiB出力予約と64MiB共有build/8MiB WT growthを区別し、旧2684MiB/UNKNOWN/旧予約をfree化しない。A/B initial/BEST/LAST PT・専用native manifest/weights・全曲線・parityは各learning-artifacts.tar.gzへ小圧縮保存、原永続checkpointも保持する。原科学源はA/B-science-source.tar.xz、selection-science-source.tar.xz、selection結果はselection-results.tar.gz。全memberをメモリ内展開して元len/SHAへ照合し、科学を実行して復元を試すことはしない。Git/index/commitは統括の単一ownerへ変更path/必要bytesを渡す。最終current/forecast/reader停止/notesbackupはhandoff正本を参照する。

次の最大1推薦は、**固定序盤rootのK64対K256教師安定性診断**。新登録familyからtrain12/selection12を各6opening cohort×2、ID順でlabel/lossを見る前に固定し、登録完全opening prefixの初手直前1rootだけを使う。現役 `crates/quoridor-runner/src/runtime.rs::benchmark` は既prefix＋MCTS rootmean/Action/nn_callsを記録し、repeat0..3（0warm/1..3 steadyseed）を実装済みである。両Kで同prefix/seed/model/RuleAを固定し、warmも含め24×4×((64+1)+(256+1))=30912NNを上界候補とする。これは未来2entryの計画であり274では起動しない。APIがこの上界を満たすかは有限資格で確認し、超過・終端はtyped不足とする。

全rootのseed内分散、K変更、D残差方向をopening群別に見る。K64の残差方向が不安定でK256で変わるなら少数高品質教師へ費用を投じるpriorityを上げる。両Kで安定なら、教師量・小LRの自動反復より位置付き経路/履歴/leaf接続の不足を優先する材料になる。高Kや複数seed平均も真値ではない。準備＋有限資格10–20分/科学30–120秒は未測見積で、2rootの実費からhard/上界を事前確定する。既benchmark batch1の費を多数game生成倍率で見積もらない。保持1MiB、現バックエンドのCPU/RAM/VRAMを実admitする。

rich経路やnative同完成depth leaf検査は有力だが、教師安定性が不明なまま特徴更新・取得・同wall費の大きい方式を増やすより、この小対照で品質改善へ投資する意味を先に判別したい。再学習へ進むなら新未使用family evalを事前split/freezeする必要がある。278の保存群解析は別ownerの競合選定で、全稿承認を本保存のgateにはしない。NNUE最高棋力・Sigma同等は未達のまま。
