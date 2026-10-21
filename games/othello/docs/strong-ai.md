# ブラウザ内Rust Othello AIの強化

2026-10-22 JSTの人間の直接依頼「最強オセロAIを作成して。」を採用する。[添付要求仕様](strong-ai-requirements-ja.txt)を原文のまま保存した（15,857B、SHA256 `e1a866a06ce3feee0078e91e11254c4ef2bd7f71aa3a3b092425dc657e9b2fb1`）。本書はOthello強化の設計正本で、担当・状態・依存はBeads `quoridor-n96` / `quoridor-n96.1` に置く。研究観測は `research-data/othello/` へ保存する。既存Quoridor研究の再開・予算転用・モデル採用を含まない。

## 目標と判定

主評価はdesktop browser内の自作Rust/Wasm、探索1thread、1秒/手、book OFF、ponder OFF。同じ実時間と事前に固定したメモリ上限で終局まで対局する。native対native、Wasm対外部native、利用可能な公式browser版との比較を区別する。初期配布目安はエンジンと重み合計16MiB以内、TT32MiB、探索Worker全体256MiB以内とし、実測と実機の制約から変更理由を残す。初期source作業はGPU0、各実装family2GiB（controller64MiBを含む）、host reserve4GiB。実CPU/RAM/VRAMは各入場で既存制御が確認する。

正しく動くこと、強豪と比較可能なこと、事前同等幅で同等と判定されたこと、優位性が支持されたことを別に報告する。優位の主指標は相手ごとの得点率と開始family単位の95%区間。両相手それぞれで下端>.5を必要とし、片方のみ・区間が.5を含む・不完全を隠さない。同等幅は本評価前に別に定める。現在の簡易policyや実装完了を優位の根拠にはしない。

## 共通コアと境界

現GameStateの64要素board、version1、黒1/白2、row-major index、合法手・パス・終局・保存JSONを維持する。Vec/ray参照とcorner/flip/ID簡易policyを独立参照・初期対照として使う。新しいu64盤面、PVS/Negamax、TT、反復深化、時計、厳密終盤は同じRustコアをnative/Wasmから使う。TTは深さ・bound・探索modeを区別し、未完了結果を厳密値として保存しない。パスは着手深さを消費せず、双方着手不能なら空きが残っても終局。原規約の実石差と、外部engineの評価値・空き割当規約は別に対応付ける。厳密終盤に確率pruningを使わない。

最初にbitboard/ray照合、軽いperft、小終盤の独立全探索、native/Wasmと時計・中断を確認する。GameStateの公開境界を変更する場合は、既存Othelloのルール・パス・終局・JSON・非法入力テストも関連する通常software検査として、新しい探索テストと一緒に一度確認する。無関係なQuoridor科学・移行suiteは再演しない。中断時は最後の完了反復の合法手へ戻す。同期WasmへpostMessageするだけで取消できるとは扱わず、内部時計とWorker終了・再生成で遅延結果を無効化する。Quoridorと共通chooserは維持し、OthelloのUI・対局制御をRust主体へ移す。JS/TSはWasm起動とブラウザAPIの最小接続に限る。

## 最初のnative接続仕様

CLIは1行1JSON要求/応答、stdoutはJSONのみ、diagnosticsはstderr。`op` は `new`, `status`, `play`, `pass`, `simple`, `search`。new以外は既存GameStateの `state`、playは `move`。応答は `ok` と `state` / `status` / `move`、失敗は `ok:false,error`。search要求は `timeMs`（暫定1000）、`ttMiB`（32）、`maxDepth`（64）、`exactEmpties`（12）。search応答はmoveに加えて `score`, `scoreKind`, `completedDepth`, `nodes`, `elapsedMs`, `timedOut`, `proven` を返す。heuristic値と証明済み最終石差を明示的に分ける。native専用I/O・時計とWasmブラウザ時計は外側、探索と評価は共通Rust。実装時の必要な追加fieldはcallerと同時に記録する。

## baselineと小評価

一次資料は[Edax](https://github.com/abulmo/edax-reversi)、[Egaroucid](https://github.com/Nyanyan/Egaroucid)、[技術解説](https://www.egaroucid.nyanyan.dev/ja/technology/explanation/)、[公開学習データ](https://www.egaroucid.nyanyan.dev/ja/technology/train-data/)。取得済release metadataはEdax v4.7、Egaroucid GUI v7.8.3。console案内7.8.1と混同せず、最初に起動できる公式Console7.8.1または固定source buildを選び、実commit・source/weight/book/dataそれぞれの条件、hash、起動args、1thread/時計/無book/無ponderを実確認する。公開dataは再配布禁止で本文をGitへ入れない。原C/C++engineを自作Rust runtimeへ隠して配布しない。

初期smokeは各相手4開始family×両色=8局。目的はprotocol・合法終局・費用の確認で、優位性判定には使わない。未学習の簡易評価器が強豪に大敗しても、その結果だけでbitboard方式や学習方針を不支持とせず、予定した少量pattern学習・export・parityへ進む。簡易policyへの勝利も強豪超えの根拠にしない。最小native接続を、Rust UIや全工程の完成待ちにしない。Rustルールを対戦制御の正本とし、違法手・timeout・crashも結果へ残す。時間対局に恣意的aggregate node capを足して未完了にしない。学習/調整familyと最終判定familyを分け、最終局数・停止・判定はpilot費用と分散から結果前に固定する。fair timing中は重いbuild/学習/対局/IO競合を調整する。

## 少量学習と改善

最初のpipeline pilotは、小さな自前の簡易policy到達対局の結果で学習・export・parityを一巡させる。これは固定外部教師やminimax真値の代用資格ではない。出発設定は24個のD4/色・STM同値を除いた開始familyをT16/V8へ分離し、4個のprotocol-smoke familyとその同値開始を除外、最終評価namespaceを別に保持する。実際の24開始stateとsplitを終局ラベル生成前に固定する。Rustが合法遷移・パス・終局・実石差を確認し、非終局のplacement8..60を4刻みで観測する。行にはgameId/openingFamily/state/labelKind=gameOutcome/targetCentidiscsを持たせ、実終局黒白石差を観測手番へ符号変換して100倍する。trainerの跨行整合確認だけで真の終局到達を認定しない。対称重複のcross-split排除を事前に決め、欠損を再抽出で補わない。

最初の評価器は2個の6cell shape、全8D4 occurrence、4phaseの共有tableで、STM centidiscsを16lookupの和から[-6400,6400]へclampする。ternaryはempty0/STM1/opponent2、shape-listを下位tritから符号化する。phaseはmin(3,clamp(occupied-4,0,60)//15)。expanded tableは[4][2][729]、色反転で符号が反転する2912独立parameterを用い、量子化はties-even・scale1、反対称性を表現できるi16範囲[-32767,32767]とする。modelは128KiB以内の厳密schemaをload時に一度検証し、探索へ明示的に借用する。baselineとimmutable pattern ownerを分け、隠れたglobal evaluatorの変更やnodeごとのJSON/hash処理を行わない。nativeの宣言modelIdはcallerVerifiedであり、実ファイルSHA/bytesと実imageの束縛は起動側が担う。終盤の証明済み実石差は学習評価から独立させる。

初回trainerはfloat64 normalized SGD、seed20261022、max64epoch、LR.1、ridge.001、validation非改善patience8を出発固定とし、trainだけで更新する。epoch0を含む実quantized/clamped V-MSE最小のFPとexportを保存し、checkpointはbest-fpとbest-patternの2個に限る。非有限・範囲違反・時間/資源/取消で停止する。入力4096行/16MiB、学習600秒以内を実configで小さく解決し、全体32MiB以内の有限データ・終局証拠・2checkpointを最初の支持案とする。loss低下やparity成功を棋力改善へ読み替えない。実データ・fitの入場条件と結論は通常の資源制御・結果記録で管理する。

最初の学習方式は対称性を共有するphase別pattern table。小さな合法到達系列と固定外部教師/厳密小終盤からPython学習・export・共通Rust利用を一巡させる。教師推定値、対局結果、厳密値を区別し、STM・board向き・色反転・phase・石差規約を固定する。game/opening系列単位split、対称局面の重複を把握し、random row splitだけで独立と呼ばない。既存重みも条件・format・phase・視点の対応確認後に利用できるが、少量自前学習とPython/native/Wasm parityを省略しない。

次の固定強豪教師pilotは新128開始familyをT96/V16/H16へ分け、既存4smokeと24tiny開始のD4/色・STM同値を除外した実state・splitをラベル取得前に固定する。Hは開始stateの排除確認だけに使い、今回のtrajectory・教師・fit・selectorへ入れない。placement8,12,20,24,36,40,48,52の各最大8観測を出発案とし、T/Vの予定上限896件、教師attemptの絶対上限1024件を区別する。欠損を新seedや重複で補充しない。固定Console7.8.1-engine＋既存fixed-time adapterは1秒・1探索thread・book/ponder OFF、初期化は一度、独立局面のTT resetは別計測、要求のmonotonic上限1100msを維持する。途中反復・取消join・輸送を実protocolが分離できなければUNKNOWN/nullのまま残す。実RAM、全体期限、serializerと保持量は新configへ入場前に解決し、tinyの32MiB/F1GiBを引き継がない。

静的教師rowは `teacherEstimate` とし、固定idに束縛したraw STM engine-disc値×100をtargetへ保存する。Egaroucidの勝者空き割当は自作Rustの実石差と異なり、教師推定を終局zや自作のexact値へ変換しない。kindごとに条件を分け、gameOutcomeだけが同一gameの終局値整合を要求する。rowの教師metadataはid/rawSTMScore/scorePerspective/scoreUnits/scaleToCentidiscs/bound/provenと5個の任意計測値に限定し、reportedBudgetMs/nodes/scoreKind等は生の応答証拠へ保持する。報告depth/probabilityからprovenやboundを推定しない。T/V/H parserとmetadataの[限定software資格](../../../research-data/othello/strong-ai-n96/teacher-label-software-v1.json)は、実教師・学習・棋力の証拠ではない。

量・時間・容量・checkpoint寿命・plateau/非有限STOPを小pilotのconfigへ結果前に固定する。大型data、NNUE、並列探索、選択pruningを初回に同時投入しない。改善候補は仮説→最小変更→開発集合比較→未使用familyで最終判断。NPS/depth/lossだけで棋力採用しない。各段階で動く最良版、失敗・費・未検証を保持し、最強目標の未達を明記する。

既存のmanaged Worktree・Beads・CPUPlan/CycleResources・job取消/回収/完了通知を再用し、専用manager・常駐監督・全員ACKを増やさない。50GB decimalは共通基盤と両ゲームの合計。Quoridor USERPAUSE323/342.17、seals/newE/oldfits96、models/defaults、原RAW/FAILED/NULL/UNKNOWN費を維持する。

## 強教師一巡後の評価器比較

固定128開始・896教師ラベル・一回のfit/export/parityは[実結果](../../../research-data/othello/strong-ai-n96/strong-teacher-pattern-v1.json)へ保存した。学習済みBESTはepoch10で、Vは選択集合のまま、未観測parameterも残る。weak outcomeとteacher estimateのV-MSEは別標的なので数値の大小だけで教材や棋力を順位付けしない。現v1と製品defaultを維持する。

次は一候補の強教師量子化V-BEST対v1 heuristicを、同一native image・共通PVS/TT/反復/厳密終盤で評価器だけ明示的に切り替え、新dev16family両色32局で比較する。opening seed2026102202、旧smoke4/tiny24/教師128のD4・色/STM同値から分離し、全開始stateと割当を結果前に固定する。H16は候補選びへ使わない。1000ms＋100ms transport、1探索thread、TT上限32MiB、maxDepth64/exactEmpties12、book/ponder OFF、モデル・process初期化一回を別費とし、各手実費を残す。恣意node上限を足さず、outer出発案2400秒は実入場前に固定する。

原32局・16個の完全両色pairがすべて正常資格の場合に限り、family平均の得点率と一度の95%family区間を出す。bootstrap出発案は10000回/seed2026102203で、具体的なRNG・percentile法もconfigへ固定する。下端>.5ならその有限dev条件で改善支持、.5を跨げば未決着、上端<.5なら不支持。失敗・UNKNOWN・未入場があれば予定分母32の得点範囲と失敗を報告し、完成pairだけを選んで採否用CIを出さない。追加seed・同じ32局の再演・結果後補充で救済せず、同等や一般最強を認定しない。

Rust主体UIは同じ既存コア担当が別の有限source作業として並行する。Rustが確認済み状態・保存可否・resume/new・view/effectsと応答tokenを所有し、TSをDOM/storage/Workerの薄いhostへ移す。同期Wasmの取消をpostMessageだけで済ませず、Workerの終了・再生成と古い応答の無効化を実browserで確認する。chooser/Quoridor/defaultを維持し、native棋力や学習lossをUI source開始条件にしない。

## 初回学習候補の同一image比較

強教師V-BESTを現v1 heuristicと同じnative image2678で比較する入口を追加した。評価器以外は同じPVS/TT/時計/厳密終盤とし、1探索thread・1000ms＋100ms返却許容・TT上限32MiB・depth64/exact12・book/ponder OFFを固定する。新dev16familyの両色32局を予定し、seed2026102202、既存smoke4/tiny24/teacher128のD4/色・STM同値rootを除外する。H16はラベル/特徴/loss/selectorへ使わない。実開始state/configは対局前に凍結する。

原32局/16完全pairとsetup/cleanup/identity/時計がすべて正常の場合だけ、family平均をMT19937 seed2026102203・10000回でresampleしR7の95%区間を報告する。下端>.5はこの有限dev条件の改善支持、上端<.5は不支持、それ以外は未決着。不完全なら予定32分母とUNKNOWN込み得点範囲を残し、完成pairだけのCIを出さない。補充/結果後seed追加なし。[結果前の対応source証拠](../../../research-data/othello/strong-ai-n96/native-comparison-software-v1.json)にある当時のUNRUNは凍結記録として保持する。

実行した原32局は全件正常終局、16完全pair、学習候補3勝2分27敗、得点率12.5%だった。原arenaが一度計算したfamily95%区間は[3.125%,23.4375%]で、上端<50%の事前条件に従い、このnative開発条件で候補の改善は不支持とする。独立確認は同じ原記録・設定・全分母・時計・cleanup・統計法を認めた。現v1と製品defaultを維持し、同等・一般的なpattern学習の不可能性・敗因・browser棋力へ広げない。[原結果・独立確認・復元証拠](../../../research-data/othello/strong-ai-n96/native-comparison-result-v1.json)。

対局outer1159.073003907秒にはcommand1158.709165507秒を含み、加算しない。後続の1961保存遷移のRustルールreplayと独立レビューは別工程で、新しいsearch/game/bootstrapは行っていない。16familyは旧root同値を除いた開発開始であり、共有prefix・後の到達局面まで独立とは証明しない。RSS peakはUNKNOWN。返却探索scoreのzeroや深さ差は記述値で、静的評価や敗因の因果証拠ではない。H16はroot identity排除だけに用い、trajectory/ラベル/feature/loss/selectorへ入れていない。同じ896行への追加fit、seed救済、追加教師、同じ32局の再演は発行しない。

## Rust主体UIの実動作

OthelloUiが確認済みGameState、確認/再開、保存可否、generation/requestとAI応答受理を所有し、薄いTS hostがDOM/storage/Worker effectを実行する。同期Wasmへcancelメッセージが届くことに依存せず、取消/新規/再開/setup/disposeでWorkerをterminateして所有権を破棄する。

Rust8・actual Wasm7・生成型/Web型/Viteと新規実ブラウザ5ケースを確認した。破損/読み込み中/読み込み失敗のslotは明示newまたは有効resumeまで保持し、古い実Worker応答は盤面/保存へ反映しない。テストの通信/Storage barrierは明示した実装境界の検査で、探索時間・棋力測定ではない。malformed GameState応答はCancel→Retryを要する回復制限を残す。[実証と制限](../../../research-data/othello/strong-ai-n96/rust-ui-v1.json)。UIのAIは既存簡易policyのまま。
