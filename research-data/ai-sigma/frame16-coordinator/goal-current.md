# 現在のNNUE研究優先順位（frame16連続延長17）

2026-10-04 09:00 UTC時点。開始05:55:50/終了09:55:50 UTC（18:55:50 JST）、新heavy09:45:50、監督09:50:50、monitor09:53:50、最終保存09:55:50。CPU合計4/RAM current8GiB/保持＋未使用予約12GiB/GPU推論6GiB・1job30分、GPU学習は旧確認未使用残のみ。同saved六role/model-effort、累積cap reset0。親main/mirrorと運用writerは92一人。最高棋力goal未達、旧testを選定へ戻さず173正式198局非学習。

## 主配分と判断を変える問い

ユーザーの「大規模増量前に生成を高速化」「構成維持自体を目的にしない」「Graph以外も簡単なら目安達成後でも実装」を適用する。最大の未解決点は、少数trainのfit/gapだけではデータ不足を除外できず、桁の違う独立局数の検証を同品質・多様性で実用の費用にできるか。保存済みprofileと実sourceで安い冗長処理を先に除き、広いRust pump/配列protocol/C++移植の費用を同時に負わず、品質を保つ有効行とgame/全attempt費で採否を決める。

221 experimentの現在主仕事はsingle-encode＋bits-only wireの最大1package。providerの捨てる第一JSON encodeと送信用第二encodeを1回にし、応答ID＋137uint32からbrokerが検査後にf32 logits/valueを復元する。入力/モデル/Graph B1..8/active24/maxB8/flush.25ms/3worker/K64/root64edge63/tau/RuleA/P2/history/探索は保持。二変更同時なので単独因果としない。stdout9～10秒はencode/pipewait混合、全額節約は保証しない。

08:48:49同saved experimentへ実配送、claim継続・私有codec-control source準備を受領。sourceGit571d939b、49mock応答/10不正schema・ID/取消/EOF/guardを保存。222独立の最大1指摘はuint32 cast前の型/整数/範囲検査。現wireでNumber.isInteger＋0..4294967295をtyped-array前に確認し採用、NaN/Inf拒否とsigned-zero/subnormal復元を別確認。roundtripだけを数値同等根拠にしない。予定432NNは同異入力oldgraph/CPU対newcodecのbit対応・数値許容を別検証。現時点実parity/生成/速度0、静的mockを科学効果にしない。

最大2生成job各48・hard300秒/physical NN180000、parity含新362000以下、原406620＋新上界768620<900000。新heavy650を原1800残内、新static60を原70/180残内、新管理180を原150/600残内。新64MiB予約/56MiBguardは既experiment1980MiB確認未使用1179754496→1112645632Bから配分。旧221予約128MiB・forecast116807935B保持、unknown減額/親追加0。新science09:15:50/stop09:25:50/save09:38:50/submit09:43:50。[実契約](../../research-data/ai-sigma/frame16-coordinator/221-low-cost-codec-contract.md)。全予定fault/unknown/NOT_STARTEDと停止を保持、成功置換・benchmark訓練混合0。root ACK/全文/全役承認を開始gateにしない。

222同savedへ08:48:50実配送・codec静的開始受領。source30＋停止後必要NN0算術30=新60、CPU0単1/RAM224MiB、旧phase1/2計150を保持。新65536B/forecast51200B、旧117289444＋新=117354980<117440512B。公表停止版source/parity/status/costへ束縛して品質分母・全費・主配分の意味を独立裁定する。旧検算/forward/旧test/173読取を追加しない。[独立契約](../../research-data/ai-sigma/frame16-coordinator/222-low-cost-codec-contract.md)。

96fresh段階pilotは提案段階で、統括tool構文失敗が実tool呼出前に起き契約/Beads/dispatch0。未配分記録を保持し、最新user steerによりcodecを優先した。96を実生成済み/実配分済みとしない。

## 既測定と採用範囲

| 同環境・model・K64の有限比較 | 実観測と判断 |
| --- | --- |
| B8→B24→B8 samefresh48 | 各48GOAL/1554joint/81096NN、113.865411/112.110926/118.946577秒。B24時間3.6897%減だがB8間差5.08秒・固定順/hostwarm/尾部が残り既定昇格0。B増-only打切り |
| Graph B1..8 same48×2 | 84.954613/86.499517秒、平均85.727065対B8平均116.405994。時間26.3551%減/率1.357867。logical81096＋warm/capture108/各81204を課金。有限生成候補として受入れ |
| Graph品質/費境界 | parity324/16fixture CPUtol PASS・eagergraph0、全1554state/features/history/legal/action/visitsのowner対応・RuleA π/z資格。222必要算術独立PASS。全leaf/教師truth/IID/学習・棋力認定0、固定順hostwarm残る |

Graph source36a6ac06、科学停止08:32:15/allwait/exactabsent、必要科学bytes ca1f0d47/current保存1f157041、pack4580587B/必要復元PASS。旧三job/600parity immutable、新graph162732NN/177.488723実秒、原含406620NN/528.406687実秒＋旧入口失敗actualUNKNOWN。保守5秒会計は実測と別、旧1.1秒手記を救済しない。static原70/180、管理150/600保持。[有限受入れ](../../research-data/ai-sigma/frame16-coordinator/221-graph-finite-acceptance.json)。source/結果/Git/index保存を受入れたことと生成方式の一般速度/教師品質認定は別。

ユーザー採択目安は同品質K64の初期化・探索・輸送・記録・回収込み1000game60分、次30分。実密度32.375joint/gameで必要8.993/17.986行秒。Graph jobだけ29.766分、既知資格/pack/Git配賦込み31.509675分＋未知freeze/dispatch/backup/将来規模費。初期60は短い外挿の見込み内、全工程30は未成立、実1000 NOT_RUN・現在の1000生成許可なし。K64≠Sigma公開K800品質。改善開発/検証投資と将来productionを分け、回収シナリオを固定保証・新gateにしない。

## 競合案と再検討

配列転送＋既Rust多handle pumpは有力。framing/ID/取消/復帰/build/interface対応を含み、現JSONのwire量・重複spanだけで排他的支配費を断定しない。薄codec後に全費を阻む輸送/尾部が残り、今後の予定生成で改修検証費が回収できる時に主順位を上げる。

Sigma固定751186のC++ selfplay一次sourceを統括が再閲覧済み。thread/game分離・配列get_batch/put_resultsは参考再用可能だがTT/noise/FPU/PCR/solver/温度/straggler/float探索とboard/model/教師出力対応の費用が残る。未変更のC++を忠実Web教師と等価としない。新取得/build/共有更新/巨大移植は現在配分なし。

223静的独立architecture見解はGraphの低接続費を支持し、Graph利益小ならarraypumpへ変更する分岐を保存。本人closed/backup・科学0、旧費保持。今回のGraph利益は小さくないが、速度目安だけを薄い有益改善の打切り理由にしない。追加Graph sweep・fresh独立test・LR/幅/arena・synthetic診断は現在保留。codecの実全費/qualityから採否を更新し、量/多様性検証へ渡す。

## 保存した学習分析の境界

216は必要phase1～5を保存・本人close済み。phase6はUSER_PRIORITY_REORDERで実science未開始/fit/NN/子0。NN29505・static144.628333/180、旧費reset0。D train .405944/val .485147、standard200 .548567/.613916はearly fit不足、standard400 .257283/.648772はlater汎化差。hiddenridge.01 train .208594/val .612799、raw626.01 .161374/.781449、rawCV λ1 OOF .382828<foldD .408041だがfullval .548893>D。216 phase1/2とCVの必要独立算術を217/219が有限支持、phase3/5はowner-only。OOF→val差 .088960はwithin .086704が記述点推定で主だが固定game区間は0跨ぎ。walls群はremainingstockで配置壁数とは違う。これらからデータ十分/全特徴無効/teacher唯一原因を決めない。旧24/48/96量比較は高LR・粗い早期曲線が交絡し、今後の量検証へ残す。

## Supervisor復旧と運用所有

延長17の親main/mirror/Git f893cb825/指定SHAと09時台期限は07:38:42running-loaded・root07:39:44受入れ済み。旧scheduler4133634/35249387・monitor4133648/35249412の自然4turnは全turn_limit/interrupted/items0、現監督成果なし。起動/loadedを実点検成功へ変換しない。

最新明示user「上限撤廃」はSupervisor 180秒1turn capをnull等で撤廃する。period20分、09:50:50運用end、pause/end exactownedのみ回収/他者turn保護/通信timeout/子資源guard/settings/親終了は維持。92solewriterへ08:48:53同active実steerでmain scheduler/tests/docsと研究copy/config/contract/prompt/有効親本文の秩序停止・nullable回帰・validate・再開/loaded・実点検成果到達を配分。rootの同92直接補足と整合し、統括は重複編集/適用turnを作らない。[契約](../../research-data/ai-sigma/frame16-coordinator/92-unbounded-supervisor-recovery-contract.md)。

旧scheduler08:51:43 operator-stop、ownednull/exactabsence・外部NN停止falseを保持。現在ファイルconfig/contract nullを観測したが新running-loadedは未確認。旧nextquietを新freeとしない。codec静的は継続、実science前に正current runtime/owned/実CPU子/RAM/GPUを本人freshadmitする。LLM active人数だけでは拒否せず、物理競合・所有回収は調整。nullableloadedと180秒越え無中断、実tool→判断/通知の到達を分けて後続観測する。旧4失敗と運用gapは保持する。
