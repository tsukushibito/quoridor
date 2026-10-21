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

同一のraw tableに対しgenericは元i16値を読み、scalar SIMD解釈は元loader同様main項を±4092、ordering項を±16380へ制限する。auxiliary項は変更しない。外部oracleはgeneric専用であり、SIMDとの数値一致と呼ばない。port由来sourceのGPL-3.0-or-later帰属と[原GPL本文](../LICENSE.Egaroucid)を保持し、weightの公開・製品再配布条件は未認定のままとする。

[最初の実weight数値資格](../../../research-data/othello/strong-ai-n96/full-evaluator-numerical-v1.json)では、既観測の完全合法2系列と明示した境界fixtureから結果前に2032件を固定し、全60phase・D4・色手番・pass・終局近傍で元genericと64index、raw和、追加項、丸め、clamp、ordering、終局規約を照合した。不一致0。120着手と1passのfull recompute/play/undo/reapply、および同じ実weightのnative/Wasm計4064比較も一致した。H・教師再照会・fit・新Search/対局/RNGは使っていない。数値工程の包括4.834016124秒はsoftware工程と別で、内包時計を加算しない。

これで最初のscalar評価器単位を受け入れる。scalar SIMD table解釈のnative/Wasm一致は、元AVX実装の呼出一致ではない。元SIMD oracleと忠実なsinglethread探索の実source移植を既存2作者が並行し、変更した境界だけを次に資格化する。探索port完了・処理速度・棋力・browser全weight動作・製品default採用はまだ認定しない。

## 最初の受入単位と検証

最初の一まとまりは「全16形状・64配置・60段階のRust評価器、実weight読込、incremental更新、原engineとの数値一致」。同じ課題の既存core作者と基準接続作者を再用し、共通format/phase境界を先に固定する。core作者はRust実装、基準接続作者は外部static oracle・format/由来を担当する。sourceの実編集から進め、設計完成・親close・Root/人間ACKを入口にしない。

受入れでは同じ実weightで全phase、盤面向き/色反転、pass、terminal近傍を含む静的照合、full recompute対incremental、packing/符号/丸め/clampを確認する。native/Wasmで同じweightと演算意味を確認する。厳密小終盤は独立全探索/外部参照でWDL・実石差・early terminal・empty割当を分ける。固定深さ・選択pruningOFFのscore差から順に切り分け、tieの別着手を数値不一致と扱わない。

最初の入力はHを使わず、二つ程度の既観測・完全合法系列から各phase0..59の非終局state、D4/色手番、pass/phase59/満盤/early terminal境界を結果前に固定する案とする。総case数・oracle初期化・RAMは実装者と324が普通softwareの有限configへ具体化し、旧perft・教師896・原32局や成功suite全体を再演しない。

重要な評価/検索・score境界には固定差分の独立確認を使う。各parameter/runへの重複review、旧parity・教師896・旧32局・既成功suiteの再演を一般条件にしない。新規または実変更された境界だけを検証する。

## 性能・棋力・browserへの接続

評価単位の成立後、初期化を再用した連続探索でSearch時間、NPS、完成深度、全仕事、メモリを記録する。同実時間対局を主要評価とし、まず小さいprotocol/評価一致、次に未使用開始familyの両色で固定EgaroucidとEdaxへ進む。1thread・同TT上限・book/ponder OFF・実時計を固定adapterに結合する。原engineより弱くても小型評価へ戻さず、評価一致・探索条件・処理速度を分けて改善する。新たな対局量/停止/判定は入口ごとの実費と資源で結果前に固定し、設定だけから優越を主張しない。

実weightの符号化入力は合計38,716,218B、compact復号tableは73,963,392Bであり、旧16MiB配布目安を今回の構成へ適用できない。weight公開条件を確認した上で、この実サイズを配布設計の出発点とする。復号byte数はRSS/peakではなく、Worker256MiB目安の成立も未測定である。TT・入力の二重保持・ロード時間を含む実browser計測で見直す。50GBと実host RAM安全枠は維持する。既存Rust UIの確認/保存/再開とgeneration/request所有を再用し、新規/中断/局面変更で古い返信を適用しない。同期WasmのpostMessage取消だけに依存せず、Worker終了/再生成を使う。nativeでの一致/棋力をbrowserの速度/棋力へ読み替えない。製品defaultは別の受入判断まで維持する。

source/light prepはQuoridor435と並行する。soleMain/Git/index/sharedCargoは実行・統合324。実build/GPU/大きいIO/公平時計だけを実STOP・実CPU/RAMで調停し、新しい恒久roleや監視frameworkを設けない。source作業は明示CPUPlan、GPU0、library1、各family2GiB/host reserve4GiBを既存CycleResources/executeへ結合する。大容量段階の具体保持は50GB内で別に解決する。

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

旧residualは提案段階で採択/実装/fitされず、今回の人間選択で先行案から退けた。二形状専用model API・trainer/export・専用試験/未採用案は、具体的な直接比較用途が無ければ新core境界の統合時にGit履歴へ退役する。比較が必要な部分だけ対象/終了条件を定め、恒久shimや実験ID別のtrainerを残さない。現役のルール・UI・取消/保存・正しさの検査と、Gitだけでは復元できない科学データを削除対象へ混ぜない。
