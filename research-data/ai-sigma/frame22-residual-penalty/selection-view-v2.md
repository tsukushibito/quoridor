# 280 結果前の競合選定見解

目標は距離Dを超える有用NNUEである。小teacher誤差や今回の予算内で動くことを採択の十分条件にしない。現在のλ1は同教師・入力・評価器の下で、不利な補正幅を制約しながら有利な方向を残せるかを直接問う。今回の一対照を完了するが、その結果を方式・強度の最終選定にはしない。

| 候補 | 目標への期待と、今回何が分かるか | 全工程費と不足観測 | 順位を変える条件 |
| --- | --- | --- | --- |
| 出力幅罰則λ1 | Dを保って学習する補正の分散・不利alignmentを減らす。primary200を固定して旧BとD双方へのMSE/符号/方向を観察する | 現samebatch256kseen＋72k評価＋nativeparity＋selection2モデル、約33万NN。D縮小だけでも罰則は減る。旧/new selectionは既使用で、未選定family評価が別途必要 | primaryがD/旧B双方に改善し有利alignmentを保持すれば一candidateとして保持。Dへ戻るだけ/方向利益がなければ追加λ/LR循環より教師・入力情報へ |
| K/seed教師安定性・rootmean→leaf/horizon | D残差に再現する教師情報があるか、MCTS rootmean平均をminimax葉に使う意味が合うかを問う。高Kも真値ではない | 既序盤24root案は約31kNNだが序盤限定。均衡したopening/middle/lateの完全prefix抽出、同root複数seed＋K、terminal/leaf分母、取得・parity・記録費が必要。36roots×4repeat×(65+257)=46368NNは候補上界、Rust保存prefix抽出/現benchmark planの実仕様を確認し全warm課金。準備15–30分/科学30–180秒はUNKNOWNを含む見積 | λが縮小だけなら、同教師残差方向の安定性を先に判断し教師質投資を選ぶ。安定してもleafに有効とは限らず、後段同depth/root判断を分ける |
| 位置付き距離場・壁効果 | Sigma/Claustrophobiaの非局所情報を圧縮し、QF1/二距離では学びにくい戦略情報を渡す。DAG4一負例は全経路否定でない | mapの位置情報、壁変更効果・経路連結、P2/STM、native full/delta/undo、train-onlyscale、学習、同時間探索費を一緒に評価。実装/資格/保存/葉costを含め現残枠に全到達はUNKNOWN。277両map66.73%はadvance内部割合でwhole倍率や新feature費へ外挿不可。279bitparallelの同仕事全費は有力な土台だが結果待ち全稿gateにしない | 教師残差が安定し現入力で転移しない根拠が強まれば、必要一群だけを優先。教師情報が揺れるなら表現増量の結果を解釈しにくく順位を下げる |
| 独立family量/分布＋学習量 | 学習する補正の転移に必要な群・epochを拡げる。現Bの後半悪化縮小は材料 | 新36family追加は総132train・同256kseenでepochが変わりτ1分布も変わる。量効果の一意分離ではない。family数・分布を固定した入れ子と学習量対照、freeze後未使用family評価の生成/露出/資格/学習費が必要。273の48family/1720行/41.48sを単純倍率で未知の局面長・tailへ保証しない | 新情報/ターゲットの安定性と小candidate利益があれば一つのfreeze評価を優先。十分な学習量/代表性の根拠なしに同smallvalへ自動増量・選定を繰り返さない |

middle mass .872026/opening .090379/late .037595（late2game）のため、middle総signed寄与は露出分布を含む。phase固有原因や序盤教師品質を低順位にする証明ではない。現在12selectionは6gain/6loss・群区間が0を跨ぎ、36newtrainは小さな介入である。history形式互換UNVERIFIEDと教師/表現/最適化/分布の競合を残す。

本来の十分量を今回の12groupから確定しない。未選定familyのpaired primary差の独立game標準偏差σ、欲しい差/区間幅hを結果前定め、概算G≈(1.96σ/h)^2を初期計画に使い、小標本・非IID・多条件選定には追加の保守性を持たせる。σや真の効果は現在UNKNOWN、12groupを必要量の確定に使わない。新64/96family等は代表性・露出を検査するpilot候補で、数だけで強度認定しない。教師K/seedにはphase別のroot間・seed内変動、leaf意味には終局/履歴/horizonの対応、最終効用には凍結候補/Dの同時間探索・色交換/多様opening・全失敗含むWDLと不確かさが別に要る。準備/生成/モデル/parity/停止込み時間は現在の可用実経路で測り、単root NN費からarena全費を保証しない。

現在推薦はλ1primaryをこの一対照として測り、次に進むのは結果に応じ最大1の具体配分だけ。幅縮小だけなら教師安定性/leaf情報の一診断を優先し、位置付き特徴と量/学習量は有力保留。両selectionに方向を伴う改善があればfreezeした一candidateの新未選定family評価を先にする。今回新K・feature・arena・生成は開始しない。人数/全稿ACK/Root役SHA待ちは入口にせず、停止中runtimeを正currentfreeへ代用もしない。

## 科学後の更新と一次source確認

λ1 primary200旧val .480183対B .479679/D .489404、新selection .397369対B .399173/D .392634。新selection displacement .003043へ縮小しても不利alignment .001692が残り、D超えの転移利益は確認できない。LAST退行は大きく緩和したので幅制約の寄与は限定支持するが、追加λ/LR sweepを優先しない。ここからの次推薦は教師/leaf情報の安定性に関する一診断、位置付き場は有力次位、単純family/2000step反復は順位を下げる。新selectionの符号率改善をrootmean採択へ交換しない。

重要なsource修正: 現役 sigma_mcts.rs::Search::with_limits の第2引数は **generation** でseedではない。runtime.rs::benchmark のrepeat0..3は固定rootの独立乱数教師ではない。現固定root探索にroot RNG/Dirichlet noiseはなく、runtimeのtau乱数はroot snapshot後のAction抽選に用いられる。前便でrepeatをsteadyseedと呼んだのはAPIの取り違えで、teacher-source-review-v2.jsonへ訂正を保存した。これを教師ばらつきへ計上しない。現在K64/K256は **決定的な探索量感度** を問うものに修正する。同モデルで独立な教師の統計的seed不確実性を調べるには、別に妥当な確率的teacher定義/対称等価性・独立模型等が必要で、新規noiseを勝手に追加しない。

次の最大1案: 保存完全prefixのphase均衡rootでK64/K256教師感度を診断する。opening/middle/late各12root、train/selection各側6、可能なら一root/独立familyとし、label/loss前に機械的に選ぶ。各phaseに必要完了prefixが無ければNOT_AVAILABLEを保持し、late2gameから独立12lateを捏造しない。TeacherRow.prefixを現役Rust readerでstream抽出し、同RuleA/STM/terminalで再生する。benchmarkをreadonly再用する場合はrepeat4をwarm含め全課金し、36×4×322=46368NN候補上界、実plans/hidden warm/terminalを資格で束縛する。同root repeat一致は再現性であり独立観測ではない。代表群に対するK変化のD残差方向/Action/rootmean/終局訪問を記録し、K256も真値やminimax認証とはしない。これは序盤24root案よりphaseを拡げた計画で、現在実行0。

Kを増やしても教師の残差方向が安定しないなら、量を増やす前にtargetの取得品質/leaf用途を見直す。安定して現入力の学習補正だけが不利なら位置付きgoal距離場/壁効果の一群を低費用cacheへ渡す比較を上げる。K感度だけでrootmeanの葉真値は分からず、別の同完成horizon/terminal/history/全合法判断と最終同時間強度が不足する。局面抽出/資格15–30分、実科学30–180秒の前見積は未測で、phase完成分母と実backend initialization/tailを先計る。別seed教師誤差を測れるという根拠のない期待費は撤回する。新未選定family数の推定はσと目的差を要しUNKNOWN、12root/200stepが現caps内だから十分という理由で採用しない。
