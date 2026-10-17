# 433 結果前の保存解釈単位

433.2が科学結果を見る前に固定する会計と解釈。正本契約SHA256 `268115c0cb028257e42254745ba265e3159543b43fb944833d362e0672dd0192` に従う。実433実装・二系列・software・Build・数値結果の適格性はまだ未確認で、この文書は未来sourceの承認ではない。

速度の主時計はobserver OFFでの各実 `SearchSession.search` 呼出しを囲むnative `Search_call_seconds` の合計。各評価器で元のO/M/P/P/M/O二反復を維持し、二系列それぞれの合計と両系列合計を出す。P合計の二反復中央値<=O中央値かつ<=M中央値を評価器別の主な有限支持目安とする。二反復の中央値は二値の算術平均であり、有意差ではない。同じ固定系列で両Pがいずれかの対照中央値の1.10倍を超えた場合を明記し、その系列を含む一律利益を主張しない。「系列悪化も記す」という433契約を、結果後に別のhard gateへ変更しない。431の毎root初期化込みwhole条件を本件の主時計へ持ち込まない。

各passは二つのcanonical family、各系列最大16の真正・非終端・連続元局面、合計最大32。元prefix/fullhistory/turn、last-wall前後、選択手によらない固定元着手列、系列/color別四つの連続session IDを使う。同色の実次手番までの両色の着手をprefixから削らない。sessionごとに時間順でgroupして実行する場合は、その実scheduleも固定し、real-time交互対局と呼ばない。各passで四つのsessionを一度ずつ構築/破棄、異なるpass・方法・observer phase間はfresh。最大OFF384calls+ON192calls=576、nodes上限2,304,000,000、最大18passes/72session生成。実数・不足・未入場を上限と区別し、UNKNOWN/refill/warmup追加はしない。

現行の通常Search内部ではroot.clone、normal validation、ContextFingerprint/BoardCursor、NNUE prepare_context、invocation scratch/child storageの準備が主時計内にある。外側の元prefix→SigmaContext再生はmeasurement.prepareの別時計であり、通常Search内部の再構成と合わせ、どちらも0や再用済みと呼ばない。TT/ordering/model Arcは本来のsession寿命で再用し、存在しないcross-call FT/scratch pool再用を仮定しない。

起動を含む副時計W_passは実native子のguardian wall。input/model/setup、四つのsession初期化、prefix準備、Search、journal、drop/publication/process overheadを含む。Search/body/driver/setup/dropは内包時計なのでWへ再加算しない。modelロード等の孤立時計がなければ、その部位はUNKNOWNであり0にしない。

系列別の副時計は、B_sを系列sの二つのsession reset/teardownと全call_body_including_journalの実時間の和とする。R=W_pass−(B_0+B_1)。四sessionの対応と全段階が揃い、R>=0の場合だけ、A_s=B_s+R/2を同じ二系列へ固定配賦する。A_0+A_1=W_passを照合し、実n_s件の一探索あたり償却費をA_s/n_s、pass全体をW_pass/n_actualとする。n_actual/planned/completeを必ず併記し、欠測・負残差・session不一致・未実行を0埋めしない。部分実行の値を予定した全系列の保持支持に使わない。A_sは等配した会計単位で、孤立した系列の因果費用ではない。主時計をA_sやWへ結果後に差し替えない。

内訳ONはfreshな同一入力・同一連続session条件でO/M/P各一回。ONのSearch時間を同方式のOFF二反復と併記して観測費を示すが、ON−OFFをexact overhead補正として差し引かない。各rootでwall stock判定を固定し、次の二つの時間は重ねない。

- 壁ゼロ開始root：そのSearch呼出し全体をinitial-stock0 Search時間に計上し、途中到達最大部分木時間には計上しない。
- 残壁ありroot：最後の壁をmakeして双方stock0になった最大部分木だけ、入口から出口までを各一回計時。内側の同じstock0訪問を親のinclusive時間へ足さない。make、fingerprint/path/accumulator準備、undo、エラー復元のどの境界まで含むか、実sourceに従って固定・明記する。正常/TT/terminal/PVS/LMR/NodeLimit/cancel/errorのすべてで一度だけ閉じる。

残壁ありrootはT_search=T_reached_stock0_maximal+T_remainingで収支を示す。残りは在庫あり処理と周辺費であり、壁判定単体費ではない。負値・欠測はUNKNOWNとして保持し、0へclampしない。計時範囲がSearch呼出しを超えていないことも確認する。

visited nodesの分割は既存 `Search.enter` の実nodes加算と同じ成功地点で行い、N_stock0+N_positive=N_totalを各callで照合する。control/capで加算前に止まった試行をnodeにしない。root、iterative deepening、terminal/depth0/TT、safe-leafのenter済み経路、PVS/LMR再訪、中断を既存の意味で数える。frontier進入回数・depth/ply histogramとnodesは別の分母で、到達後の早期errorなら時間/entryがあってnode0でも矛盾とは限らない。evaluationは既存の実event地点に合わせ、proofはfresh M/goal-tail/sealed-tail/Pathとtyped TT再用の既存非重複originを維持する。未訪問の節約node、独立局面率、physical NNUE数へ換算しない。

同方式のOFF二反復とON一回について、同系列・root・完全history・session順序のvaluebits/action/PV/完成深さ/status/実nodes/既存全work/親復元を照合する。除外するのは時計と新しい診断fieldだけで、旧TT generation/namespace/workを都合よく除かない。observer flagで数学namespace/score/orderingを変えず、OFFで新しい内訳時計を呼ばない。OFFの診断0/欠落は計測無効であり機会不存在ではない。既存LMR observer/trialやcompleted-depth callbackは本件で有効にしない。

actual source/new tests/Build/input/result/STOPに未解決があればその実境界をUNKNOWNとし、old171/solver/成功suiteや宣言済み数値を再演して埋めない。source/数学の正しさ、連続Searchの有限速度、初期化償却、壁ゼロ開始、途中到達内訳、observer費を別々の範囲として報告する。一般速度/棋力、連続peak、全host静穏、金銭費用は別途証拠がなければUNKNOWN。
