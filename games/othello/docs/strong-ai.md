# Egaroucid互換Rust Othelloコアの設計

2026-10-22 JSTの[人間直接方針変更の原文](full-clone-request-20261022-ja.md)を採用する。最初の最低到達目標は、Egaroucid Console7.8.1と同じ全パターン・placement別重み・実効探索手法を持つ高性能なsinglethread Rust cloneである。実装完了と同棋力・優越の実証は別に判定する。旧二形状/四phaseの増量・救済fitと未採択residual案を最初の目標にはしない。residualへの人間回答待ちはこの明示選択で解消し、新source/fit/対局を発行しない。

[最初の要求原文](strong-ai-requirements-ja.txt)と実行済み研究は履歴として保持する。本書を到達構成の正本、[研究知見](../../../docs/research-findings.md)を観測・限界・次判断の正本とし、担当・進行・依存はBeadsに置く。既存QuoridorのUSERPAUSE323/342.17、seals/newE/oldfits96、モデル/default、RAW/FAILED/NULL/UNKNOWN費とdecimal50GBを変更しない。

## 固定する原実装と資産

第一基準はtag `console_v7.8.1`、commit `570d5e0a478c9d720d75de06a5d31995f412704a` のEgaroucid Console7.8.1。GUI7.8.3、master、Edaxのパターン・重み・scoreを混ぜない。Edax4.7は独立した比較/参照相手として残す。

既存の保存先は `.worktree/assets/tools/othello-baselines-n96-v1/` のprovenance.json、egaroucid-ref.json、selected-members.json、egaroucid/src/engine/、egaroucid/bin/resources/。元版・導出元・必要noticesとsource/weight/book/data各条件を別に記録する。sourceはGPL3-or-later、weightはrepository licenseの存在と別grant未確認を区別してきた。今回の指示はRust port・format調査・ローカル同値確認を進める許可であり、未確認weightの公開/製品再配布を認定するものではない。その具体的な利用条件を調べつつ実装を進め、全法務調査や追加承認をclone全体のgateにしない。原C++は外部oracleとしてのみ使い、配布する自作エンジンに隠して組み込まない。

既存 `eval.egev2` は38,243,826B、SHA256 `0a8acbcbc23067933627f1bcc83c3f7ae6b7ff3e603d174a3364271fcaeeef2f`。終盤orderingの `eval_move_ordering_end.egev` は472,392B。現物のformatとdecoderを固定sourceに対応させ、学習済weightで強い初期版へ最短接続する。再download・恒常mirror・不用なweightコピーは作らない。自前学習が必要でも全パターン/全60段階を維持し、coverageと十分な量を別の有限configへ解決する。

## 到達構成

共通Rust coreがルール、bitboard、評価器、incremental特徴、探索、score/proof意味を所有する。native CLIとbrowser Workerは同じcoreと同じweight意味を使う。現GameStateの黒1/白2、row-major64cell、play/pass/terminal、version1保存境界とRust主体UIを再用する。JS/TSはload・Worker・DOM/storage接続に限る。

大きなweightは初期化時に一度だけdecodeしてimmutable ownerへ保持し、探索はborrowする。パターン長ごとの実長/offsetを使い、最大長へのpadding・対称tableの不要重複・複数の全weightコピーを避ける。node hotpathへheap、JSON、hash、全盤面再scanを足さない。着手・反転・undo・passの特徴index差分更新を実装し、full recomputeを検証参照にする。scalarを正しさの基準として先に完成し、SIMDはnative/Wasmそれぞれの実環境で効果と演算一致を確認して追加する。

## 評価・phase・終局の契約

固定sourceの `evaluate_common.hpp` はN_PATTERNS16、MAX_PATTERN_CELLS10、N_PATTERN_FEATURES64、N_PHASES60、PHASE_N_DISCS1、STEP32。 `evaluate_generic.hpp` のfeature_to_coord全64配置、feature_to_pattern、pattern_sizes、桁順・色反転・対称、eval_num_arr、付加項、四つの終盤moveordering patternを対応させる。元genericとSIMDのpacking/丸めの違いは明示し、名前だけ同じ近似へ置換しない。

pattern_sizesは `[8,9,8,9,8,9,7,10,10,10,10,10,10,10,10,10]`。元の列挙順で `res=res*3+digit` とし、player0/opponent1/empty2、swap_player_idxは0/1を交換して2を保持する。A1bit63の元向きとcoreのA1bit0を明示対応させる。旧tinyのLSB-first符号化や強制反対称性を移植先へ課さない。pattern和と `eval_num_arr[phase][own-count]` を足し、符号別±16、C++同様の0方向整数除算32、SCORE_MAX clampを行う。全64indexとraw和も照合し、丸め後だけ合う誤りを見逃さない。終盤orderingは別table・別clamp資格である。

一視点の実要素は1phase612425 i16（pattern＋追加65項）、全60phaseで36,745,500要素＝73,491,000B、終盤orderingは472,392Bというsource算術を出発支持とする。これはRSS/復号peakや新quotaの実測ではない。入力とdecode出力の二重保持、視点別全tableコピー、最大長paddingを避け、実ロード時の保持とpeakを確認する。

phaseは元 `search.hpp::phase()` 同様 `(n_discs-4)/PHASE_N_DISCS`。placement数に対応する60段階で、passでは進めない。phase0..59の元呼出資格、phase59と満盤/双方着手不能の境界をAPIへ明記し、無条件にphaseをclampしたり共有/補間して4phaseへ縮約しない。terminalは独立した終局経路へ送る。

STM/盤面向き/色、raw STEP単位、disc単位、丸め、clamp段階と外向けscore単位を型と入出力で区別する。元engineのwinner-empties評価規約、自作の実石差、WDLを混同しない。選択cutの結果をproven exactとしない。固定source/weightの同値を先に確立し、旧tinyのcentidisc・反対称i16 table契約をそのまま流用しない。

## 探索port

同じ固定版の実際に有効な処理を移す。PVS/反復深化だけの名前上のcloneにせず、次の対応をsource位置・有効条件・port状況・差の理由を持つ短い表へ整理する。

- TTのdepth/bound/selective資格・replacementと実moveordering、浅いordering評価。
- 潜在mobility、準偶数順、終盤ordering、確定石cut、ETC。
- ProbCut/MultiProbCutの元確率table・適用資格と、小空き終盤最適化。
- 実時間管理、最後の完了反復、取消と未完了の扱い。

元設定でinactiveの機能を必須の有効処理と偽らない。同じ評価/score単位なら元MPC係数と条件を初期値として使い、追加校正campaignを先行条件にしない。重要な差を加える場合は理由と範囲を保存する。最初はsinglethreadを完成させ、threadpool丸写しや独自scheduler/汎用探索frameworkを先に作らない。pass/厳密終盤/early terminalの規約は独立に確認し、selective結果とsolverの証明を分ける。

固定setting.hppではEND parity/stability、MID ETC/MPCはON、LAST4 stability/aspiration negascout/killer-orderingはOFF。YBWCの定義があってもsinglethread/pool0で実効しない並列を必須移植へ増やさない。実console/fixedadapterのcompile条件・runtime選択を対応表へ結び、宣言の存在を有効性やport完了と扱わない。

## 評価器の限定software資格

全16形状・64配置・60placement段階のscalar実装、compactな実weight decoder、play/flip/undo/passの差分更新と明示native/Wasm入口を実装した。[限定software資格](../../../research-data/othello/strong-ai-n96/full-evaluator-software-v1.json)は新Rust6定義、関連Clippy、native release、外部generic oracleと合成fixture、Wasm生成の8commandを記録する。包括22.691710681秒に内包時計を加算しない。固定差分の独立確認はSOURCE_CLEARであり、実weight数値一致・全探索port・棋力の資格とは区別する。

同一のraw tableに対しgenericは元i16値を読み、scalar SIMD解釈は元loader同様main項を±4092、ordering項を±16380へ制限する。auxiliary項は変更しない。最初の外部oracleはgeneric専用であり、後続の明示AVX2 profileとは区別する。port由来sourceのGPL-3.0-or-later帰属と[原GPL本文](../LICENSE.Egaroucid)を保持し、両Rust crateにも同じlicenseを明示した。weightの公開・製品再配布条件は未認定のままとする。

[最初の実weight数値資格](../../../research-data/othello/strong-ai-n96/full-evaluator-numerical-v1.json)では、既観測の完全合法2系列と明示した境界fixtureから結果前に2032件を固定し、全60phase・D4・色手番・pass・終局近傍で元genericと64index、raw和、追加項、丸め、clamp、ordering、終局規約を照合した。不一致0。120着手と1passのfull recompute/play/undo/reapply、および同じ実weightのnative/Wasm計4064比較も一致した。H・教師再照会・fit・新Search/対局/RNGは使っていない。数値工程の包括4.834016124秒はsoftware工程と別で、内包時計を加算しない。

後続の[実AVX評価資格](../../../research-data/othello/strong-ai-n96/full-evaluator-actual-simd-v1.json)では、固定版の実際のAVX2 callableと保存済みRust scalar-SIMD traceが同じ2032件で一致した。原2000件、保存済み2001件目の返答の回収、残り31件を合わせ、同じケースを再評価していない。最初の比較器がearly terminalにもphase=Noneを要求した失敗は保持する。63石のearly terminalはphase59というplacement metadataを保ちながらmidgame/tablePhaseを使わず、満盤ではphase60へ入らない。元FAILEDの包括0.839866422秒と追加31件の包括0.431008497秒を別々に保持する。元generic・Rust・Wasm・incrementalの成功は再演していない。これで最初の全パターン・全phase実weight評価器単位を受け入れるが、探索全体・性能・棋力・browser配布の証明にはしない。

## 探索の限定software・固定深さ資格

[探索software](../../../research-data/othello/strong-ai-n96/full-search-software-v1.json)は、明示native/Wasm ownerと外部の固定深さ参照を記録する。独立source確認で見つかった中央4セルのshallow合法手欠落とforced-passのshift64を修復し、新Rust2件・actual Wasm2件、関連Clippy/release/生成と新参照fixtureの8commandを確認した。包括33.956008821秒、旧9件の成功テストは再演していない。元fixture/Clippy失敗、SOURCE_NOT_CLEARと関連SOURCE_CLEARを別々に保存する。作者の[SOURCE_MAP](../crates/othello-core/src/full_search/SOURCE_MAP.md)にあるUNRUNは作者の引渡し時点の実行範囲であり、Rootの実資格は正本結果を参照する。

[最初の固定深さ比較](../../../research-data/othello/strong-ai-n96/full-search-numerical-v1.json)は、既観測の合法2系列から29の異なるstate/depthを結果前に固定した。浅い非選択21件、小終盤6件（forced pass1件を含む）、終局2件の計58要求で、同じ実weightのRustと元AVX参照のSTM未平滑値が全件一致し、今回は着手も全件一致した。元の四つの中央セルが埋まった記録局面だけを使用し、非終局の要求深さは空き数以下、両TTをケース時計の外でclearした。元参照は外部compileでMPCをOFFにしており、stock consoleでroot selectivity=6を指定しただけの条件とは区別する。包括1.417980500秒にsetup/reset/search/cleanupの内包時計を加算しない。入力準備の32件には共通初期盤面の3深さ分が重複していたため、入場前に29件へ統合し、失敗記録を保持して補充しなかった。H・新対局・教師・fitは0である。

この29件の有限一致は全探索の同値性や独立minimax証明ではない。その時点で残った専用終盤kernel・実効isolated-empty順序とclog orderingは、後述の別差分として移植・検証した。選択/MPC・深い境界、初期化再用の連続探索、処理速度・同時間対局、browser全weight動作・製品defaultは別の資格である。局所的な一致や元より弱いことを、小型評価路線へ戻す根拠にしない。

[専用終盤kernelと輸送修復](../../../research-data/othello/strong-ai-n96/full-search-kernels-v1.json)では、last1のPVS/lazy NWS、min/maxの視点・pass・窓を保つlast2..4、実際に有効なisolated-empty順序、clog prepassの浅い評価/TT順序を実装した。新しいkernel/clogのRust5定義と、後述する7係数bit-roundtripの新1定義が通過した。最初のClippy失敗はtest moduleの配置だけを直し、既成功5定義や旧9/R1/R2/evaluator suiteを再演していない。独立source確認は固定kernel差分と関連f64輸送差分でそれぞれSOURCE_CLEAR。scalar ray/通常bitboardと元AVX/LUT/register実装、helper/nodeの数え方、元のpost-budget延長を採用しないstrict whole-call clockの差は残す。

同じ実weight・記録2系列から固定した10局面/12条件（空き1/2/3/4/6、fixed10とtimed clog2）で、保存済みnative12応答、元参照の新規4応答と既存6参照、修復後のactual Wasm12応答を照合した。未平滑STM値・着手・深さ・proven/scoreKind・TTと全7係数が一致した。新しいnative4dd imageはbuild済みだがSearchを再実行しておらず、同じkernel sourceの旧c5dd imageによる保存結果を再用したという資格である。今回のWasm工程は包括1.227524234秒、新native/元engine要求0・H/新対局/教師/fit/統計0で、公平な速度比較ではない。

元e640工程ではnative12/元4まで完了した後にRootのWasm transport envelope検査で失敗し、保存返答だけから回収した。続く750工程の最初のWasm返答はscore等が一致した一方、MPC係数gがnativeのbit `3ffc70a545d535a4`に対し`3ffc70a545d535a5`で厳格なcontrol identityに失敗した。定数・許容誤差・比較項目を変えず、同じserde_json版の標準`float_roundtrip` featureで修復し、新1テスト/Clippy/native release/Wasm生成の包括10.863685434秒を別に記録した。修復後は失敗1＋未実行11のWasmだけを実行し、7係数すべてのbit一致を確認した。両原FAILED/NULL/費とdisk pending/attemptedは保持する。MPC OFFのこの比較からMPCによるscoreへの影響、選択探索全体、NPS・棋力・browser配布・weight公開条件を認定しない。

新しいSELECTIVE参照は、元のMPC/precalculationと初期化を保持した別compile profileとしてbuildし、境界fixtureと関連source確認が通った。root6でも浅いorderingはMPC74を使えるため、既受入れのcompile-OFF固定深さ29件と同条件ではない。非終局の参照provenは保守的にfalseのまま保持し、Rust側の終盤/level6のprovenと値一致だけから同一視しない。このsoftware工程はRust2/Python6・実生成型と変更baseline native/Wasm境界を含む11command、包括39.003354656秒で、実weight読込・元Search・選択数値・速度/棋力実験は0だった。

## 最初の受入単位と検証

最初の一まとまりは「全16形状・64配置・60段階のRust評価器、実weight読込、incremental更新、原engineとの数値一致」。同じ課題の既存core作者と基準接続作者を再用し、共通format/phase境界を先に固定する。core作者はRust実装、基準接続作者は外部static oracle・format/由来を担当する。sourceの実編集から進め、設計完成・親close・Root/人間ACKを入口にしない。

受入れでは同じ実weightで全phase、盤面向き/色反転、pass、terminal近傍を含む静的照合、full recompute対incremental、packing/符号/丸め/clampを確認する。native/Wasmで同じweightと演算意味を確認する。厳密小終盤は独立全探索/外部参照でWDL・実石差・early terminal・empty割当を分ける。固定深さ・選択pruningOFFのscore差から順に切り分け、tieの別着手を数値不一致と扱わない。

最初の入力はHを使わず、二つ程度の既観測・完全合法系列から各phase0..59の非終局state、D4/色手番、pass/phase59/満盤/early terminal境界を結果前に固定する案とする。総case数・oracle初期化・RAMは実装者と324が普通softwareの有限configへ具体化し、旧perft・教師896・原32局や成功suite全体を再演しない。

重要な評価/検索・score境界には固定差分の独立確認を使う。各parameter/runへの重複review、旧parity・教師896・旧32局・既成功suiteの再演を一般条件にしない。新規または実変更された境界だけを検証する。

2026-10-23のrequest-boundary実観測は[保存結果](../../../research-data/othello/strong-ai-n96/request-boundary-two-owner-observation-result-v1.json)へ結合した。Rustはdepth18 timeoutから17を保持し、その終端で成功PVSを後段pollが破棄した事象は観測されなかった。本家はdepth22のfuture待機満了後にjoinし21を保持した。instrumented owner各1入力の事実に限定し、同仕事・kernel速度・棋力差の原因や修復成功とはしない。次は実行を重ねず、現役評価器と固定本家の直接midgame経路をsourceで対応させる。

2026-10-23の[直接owner warm-work source](../../../research-data/othello/strong-ai-n96/direct-owner-warm-work-source-v1.json)は、既存4系列・16rootで現役評価と実play/eval/LIFOundoを呼ぶ有限carrierとする。両新imageのcompile-onlyと[限定したemitted-loop確認](../../../research-data/othello/strong-ai-n96/direct-owner-warm-work-emitted-loops-v1.json)で、実ownerの仕事とloop進行がsuccess backedge内に残ることを記録した。Rust black_boxと本家GNU asm barrier・bookkeepingの費用、実処理回数・同仕事・速度や対局差の原因は未証明である。計測はUNRUNで、実入力・回数・順序・資源・時計の入場を別途束縛し、Search/対局/benchmarkを自動再演しない。

## 性能・棋力・browserへの接続

評価単位の成立後、初期化を再用した連続探索でSearch時間、NPS、完成深度、全仕事、メモリを記録する。同実時間対局を主要評価とし、小さいprotocol/評価一致から有限なdevelopment対戦へ進む。後続の独立確認では未使用開始familyの両色で固定EgaroucidとEdaxへ進む。1thread・同TT上限・book/ponder OFF・実時計を固定adapterに結合する。原engineより弱くても小型評価へ戻さず、評価一致・探索条件・処理速度を分けて改善する。新たな対局量/停止/判定は入口ごとの実費と資源で結果前に固定し、設定だけから優越を主張しない。

2026-10-23の最初の同時間native比較は、未使用・未見・fit独立を認定しないprospective development対戦とする。性能比較の4系列とは別に、seed2026102302001..2016、mandatory pass後の16placement、各128actions上限・no refillで新16familyを準備する。利用可能なtyped endpointとHのidentity-only除外、新cohort内のplacement8以降のpass-inclusive identity・self/inter-family衝突停止を保持し、historical full-history coverageはUNKNOWNと明記する。古い全履歴の復元を入口にしない。

同日のrules-only生成b0788be4は16/16root・deficitなしで完了し、元packageを上記development範囲だけで採用した。[入力資格と元証拠](../../../research-data/othello/strong-ai-n96/native64-development16-generation-completion-v2.json)にfamily順・source・除外範囲・cleanupを固定し、未見性や対戦の実入場資格とは分ける。[現役native64 configへの実入力束縛](../../../research-data/othello/strong-ai-n96/native64-actual16-source-binding-v1.json)後、[通常64局条件ab830115](../../../research-data/othello/strong-ai-n96/native64-normal-condition-v1.json)を一度提出した。元完了イベントの回収では64/64局が完了し、各相手とも12勝2分18敗、得点率0.40625、保存95%区間[0.3125,0.484375]だった。[保存結果](../../../research-data/othello/strong-ai-n96/native64-normal-result-v1.json)はdevelopmentの観測に限定し、一般棋力・同等性・原因は未認定とする。結果解釈と時計・探索量の保存記録確認を既存担当へ配分した。

同じ16familyの両色で現Rust版と固定Egaroucid/Edaxを各32局、計64局とし、各相手の予定32局を分母に残す。実経路の1秒・1thread・active TT上限32MiB・book/ponder OFF、現行game停止上限とfirst-error規約を結果前に束縛する。記述的区間は既存family-bootstrap経路で一つのPCG64表10000×16、seed2026102302064、同じfamily順を両相手へ共有し、linear95%とする。相手ごとの予定32局が完結しなければその区間はNULL、失敗・未実行の補充や除外はしない。固定depthの32組raw/policy一致や平均時間比を一般棋力・同等性・最強・製品昇格へ読み替えず、時間比だけで初回対戦を拒否しない。必要な現役caller差分の通常source/software資格と実資源・時間・保持は、実入場前に統合担当が解決する。

実weightの符号化入力は合計38,716,218B、compact復号tableは73,963,392Bであり、旧16MiB配布目安を今回の構成へ適用できない。weight公開条件を確認した上で、この実サイズを配布設計の出発点とする。復号byte数はRSS/peakではなく、Worker256MiB目安の成立も未測定である。TT・入力の二重保持・ロード時間を含む実browser計測で見直す。50GBと実host RAM安全枠は維持する。既存Rust UIの確認/保存/再開とgeneration/request所有を再用し、新規/中断/局面変更で古い返信を適用しない。同期WasmのpostMessage取消だけに依存せず、Worker終了/再生成を使う。nativeでの一致/棋力をbrowserの速度/棋力へ読み替えない。製品defaultは別の受入判断まで維持する。

source/light prepはQuoridor435と並行する。soleMain/Git/index/sharedCargoは実行・統合324。実build/GPU/大きいIO/公平時計だけを実STOP・実CPU/RAMで調停し、新しい恒久roleや監視frameworkを設けない。source作業は明示CPUPlan、GPU0、library1、各family2GiB/host reserve4GiBを既存CycleResources/executeへ結合する。大容量段階の具体保持は50GB内で別に解決する。

## packed候補の次の有限development比較

[次条件](../../../research-data/othello/strong-ai-n96/packed-new-development64-condition-v1.json)では、有限ABBAを終えたpackedbd8ffc91を研究用候補として固定する。同じABBAや旧scalar/本家の成功検査は再演せず、既存担当が新development16生成と通常64局の設定を準備する。seeds2026102403001..3016、mandatory pass後16placements、各128actions上限、全16完成・衝突/lineage資格を対局前に凍結し、deficit時は補充しない。固定Console7.8.1/Edax4.7へ各両色32局、同1秒+100ms transport・1thread・activeTT上限32MiBとする。新sharedPCG64 seed2026102403064/10000×16/linear95を保存解析で一度だけ使い、相手ごとに不完全ならその区間はNULLとする。別bookの旧12勝2分18敗との差を対応効果、二つの95%記述区間を同時優越検定とは扱わない。

[追加除外identity](../../../research-data/othello/strong-ai-n96/native64-recorded-identity-exclusion-v1.json)は旧native64-prospectiveの保存済み144訪問点と16 endpoint記録を現typed入口へ結ぶ。canonical再計算や旧対局再演は行わず、endpoints-only/historyUNKNOWNを保持する。practical197の被覆は既存四familyの開始点系譜であり、別native64のf01開始は追加packageへ属する。後続対局・内部Search・child局面の全identity被覆はUNKNOWNのまま。[正常入口の準備](../../../research-data/othello/strong-ai-n96/packed-development64-normal-preparation-v1.json)で、seedを明示伝達する既存二ownerとNEW回帰検査をMainへCAS採用し、fake-only二検査の実2PASSを保持した。[新16生成9e9450fdの保存結果](../../../research-data/othello/strong-ai-n96/packed-development16-generation-result-v1.json)は16/16完成・deficit/UNRUN0で、roots0e323919をdevelopment入力として固定した。元.24246359197422862秒に内側.07622094906400889秒は加算せず、実cleanupとPID未報告の区別を保持する。この同16familyの64局設定も正常入口へ束縛済みだが、対局/その統計は未発行である。Quoridor解析修正版35e0603fを次の実STOP窓へ発行し、短いBsoftware/input窓と本64局を互いの全goalやACKへ待たせない。製品default・モデル・棋力認定は変更しない。

## 既往の結果と退役境界

以下は完了済みの履歴で、cloneの将来指示や再実行条件ではない。元RAW/モデル/入力/FAILED/UNKNOWN費とGit上の旧設計は保存する。

| 到達事実                            | 根拠と限界                                                                                                                                                                                                                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 固定外部16局を全終局                | [protocol smoke](../../../research-data/othello/strong-ai-n96/protocol-smoke-v1.json)。Edax1W7L/Ega0W1D7L、outer519.312600811秒。比較接続/費用であり一般棋力の判定ではない。                                                                                                          |
| 旧二形状・四phaseのtiny outcome学習 | [tiny learning](../../../research-data/othello/strong-ai-n96/tiny-pattern-learning-v1.json)。24終局、T196/V104、4116更新、全4phase parity。実装接続を受け入れ、製品評価は置換しなかった。                                                                                             |
| 旧896教師とfit                      | [strong teacher](../../../research-data/othello/strong-ai-n96/strong-teacher-pattern-v1.json)。T768/V128、quantized BEST10、plateau18、全4phase一致。winner-empties378行もteacherEstimateで、own solver truthではない。                                                               |
| 旧学習候補7ed9対v1                  | [原32局](../../../research-data/othello/strong-ai-n96/native-comparison-result-v1.json)。3W2D27L、得点.125、原一度のfamily区間[.03125,.234375]。このdev条件で改善不支持、現v1維持。一般のpattern学習の不可能性や敗因とはしない。                                                      |
| 保存診断                            | [有限診断](../../../research-data/othello/strong-ai-n96/saved-pattern-diagnostic-v1.json)。2857状態/5714静的評価、V-MSE改善とMAE/符号悪化、alias/空vector/未観測を区別。新Search/教師/fit/RNG0。原32局は開発で観測済みで最終独立集合に再利用しない。                                  |
| Rust主体UIと任意v1探索              | [UI](../../../research-data/othello/strong-ai-n96/rust-ui-v1.json)、[browser search](../../../research-data/othello/strong-ai-n96/browser-search-v1.json)。Rust8/Wasm7と描画5、追加Rust7/Wasm3/描画2。malformed GameStateのCancel→Retry制限、nominal clockとbrowser棋力未資格を保持。 |

旧residualは提案段階で採択/実装/fitされず、今回の人間選択で先行案から退けた。[退役と選択参照のsoftware資格](../../../research-data/othello/strong-ai-n96/retirement-selective-software-v1.json)で、直接比較の現役用途が無い二形状専用model API・trainer/export・専用試験と旧候補の固定launchを撤去した。旧版コードの復元元はGit履歴とし、恒久shimは置かない。共有のD4/色手番canonical処理だけをarenaへ移し、ルール・v1 heuristic・UI・取消/保存とfull evaluator/searchは維持した。元モデル・入力・実行結果・失敗費は削除していない。

固定sourceの追加読取りで、初回対応表が欠落機能として挙げたparity_case/parity_ordering_shuffle_mask_last4/parity_ordering_last3は定義だけで、activeなgeneric/SIMD PVS/NWS last4から使われていないと確認した。実効経路はempty1_bbによるisolated-empty partitionである。未使用tableをport要件へ追加せず、元の誤った説明は探索software正本の訂正欄とGit履歴へ残す。この訂正で元コード・実行画像・固定深さ29件の結果を変更しない。
