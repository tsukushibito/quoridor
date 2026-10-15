# 零在庫近似leaf：一候補のsource凍結

実契約`zero-stock-approx-speed-20261015.md`に基づき、現Mainのalphabeta.rs・measurement.rsとPythonのmeasurement_config関数だけを短命guardで取り込みました。元OWN beforeimageはgzipで別保存し、Main/Git/index/Cargo・core/NNUE正本・model・元RAWは変更していません。新実装をnative/software/科学PASSとはしていません。

## 設定と有効方式

既存SearchSessionへ`set_zero_stock_approx_min_root_walls(Option<u8>)->Result<()>`を追加しました。未指定/NoneはOFF、整数0..20だけです。計測Settingsの同名Optionはserdeでbool/負数/float等を拒否し、21以上をrange拒否します。Python companionは現役research-lifecycle.py::measurement_configの関数差分だけで、null/未指定または`type(value) is int`の0..20を受理します。Pythonboolを整数として受理しません。

各Search開始時にrootの壁合計を取得し、0なら全root許可、正閾値ならroot合計>=閾値を判定します。さらにmax_depth<=max(root合計,1)なら無効です。結果のbooleanはstatsへ一度コピーし、反復深化中も各nodeでも閾値を再解決しません。rootは通常どおり全合法候補を比較します。

既存namespaceの末尾へ、有効ONの場合だけ`zero-stock406-wall-distance-stm-tie-win-v1`を追加します。閾値やroot合計はnamespaceへ入れません。有効ON/OFFが変わる時だけ既存TT/historyをclearし、同じ有効booleanならwarmの値/履歴を保持します。閾値の正値変更は次の実Searchで解決します。None指定は即OFFへ戻します。resetは要求閾値を残しつつ、root未知のため有効OFF/base namespaceへ戻し、通常のTT/history clearを行います。既存set_lmrの変更時は近似末尾成分を一時的に外してLMR成分を操作し、近似成分を同じ位置へ戻します。LMRの規則やprofile意味は変えていません。

## child・score・cache・会計

childの既存make→board/context/path更新→pool slot取得の後、既存closure内でtrue goal/threefoldを先に確認します。非終局かつ解決済みON・残りdepth>0・両stock0だけが近似branchです。片側だけ0やdepth0は元のadvance/head経路です。OFFではその旧経路とnode-limit時の会計順をbyte exactで維持します。

近似branchはnegamax entryを置換し、既存enter/control/node capを一度通します。その後、現在手番の壁距離dsと相手doからds<=doなら+1、他は−1を返します。既存nonterminal domainのadmissionを通し、domainに入らなければerrorで戻します。true terminalのutility/優先・fullhistory・TT key/depth/bounds・undoは元の正本です。近似値はゲームWDLでも全幅minimax証明でもなく、tree Exactやnominal depthをそれへ昇格させません。

距離は取得済みpool slot、immutable parentの順で、実際のEvalAccumulator::Floatだけが持つ既存cached_wall_distance_mapsのwall-key照合を利用します。pawn/STMは壁距離を変えません。別variantや違うwall keyは使えず、Position::wall_distanceへfallbackします。cacheを捏造/更新せず、独自BFS・新cache・evaluator・solverはありません。近似時にはeval.advance_move_context・head・ordering準備へ入らず、delta_updatesを増やしません。親とpool slotは元closureの同じerror/cancel/undo経路で回収します。

PVは、実終局に加えて実際の近似leafに到達したところで止めます。warm TTに別root由来の後続が残っても、探索していない近似leafの先をPVとして足しません。既存TT資格は削除しません。

## 結果と計測

SearchResultの公開statsにroot_walls_remaining、zero_stock_approx_permitted、zero_stock_approx_terminationsを追加しました。countは正常に返した近似leaf数で、試行やtrue terminal/head数とは別です。既存Stats初期化を使用するため、他runtime/arenaのSearchResult literalに偽の値を足すcompanionは不要です。

計測の各resultと既存completed-depth callbackへ上記の実値を載せます。reset時の有効booleanはroot未知なのでnull、各callのactual_selectivityはSearch後の実namespaceです。近似有効のcompleted_depth_semanticsは`approximate-leaf-nominal-not-game-WDL`です。partial/ErrをCOMPLETEへ変更する処理はありません。NNUEと固定Dで同じchild実装・setter・Settingsを使い、実model/inputのload/identity、journal/cleanup/collectorの正本は変更していません。

## 静的確認と未実行

対象Rustfmt、Python helper/NN0定義のRuff format/check、関数fragmentのformat/AST、strict GNU forward/inverse（offset0/fuzz0/newabsence）、現Main before対応、TT/fullhistory・評価/NNUE数学・negamax/root/LMR・ordering・child OFF・通常measurement driver/loader/publicationの保護byte確認はPASSです。source helper実行と整形だけで、authorのnative/type/test/Search/model/geometry/Perf/game/fit/Cargo実行は0です。

新RustはAI7定義（うちgoal/threefold1はdiagnostics限定）＋runner1、Python NN0は1定義です。全てUNBUILT/UNTYPED/UNRUN、Python定義は未import/未実行です。設定境界/root固定/last-wall後のpermit保持、深さ0/片側0、goal/threefold、合法action/PV、取消/cap/domain error/OFF advance error/親復元、switch/reset/warm、Floatのkey一致/不一致fallbackと親不変、8/8 tieと7/8 STM符号を対象にしています。toyのsynthetic境界は実測入力と区別し、runtimeでは従来どおりsynthetic rootを拒否します。既存小toy model helperはtestから再利用するためvisibilityだけを広げ、model数学をコピーしていません。

Rootに必要なresearch/research-diagnostics compile、限定new/affected選択、両feature Clippy/release/真正imageを依頼します。関連reviewは終局優先・1回入場・復元・有効boolean/TT/history切替・cache variant/key・approximate depth/Exactの意味に限定します。作者からreview dispatchはしません。具体filter/countはverification-plan.jsonです。

Rootが所有する4つの真正prefixと保存52fixture confusionは読み/複製/再計算していません。将来の速度96callsはRootのみ、null/4/0の既承認順とNNUE/D strata、TT1M/PVS/LMR OFF、同じ4roots・depth8・4M上限のままです。追加arena/閾値sweep/学習/既定採用は発行しません。cache hit頻度、近似のWDL正解率、性能、実RSS/stack/cache/copy費はUNKNOWNです。

元404/405の証拠、402/400の結果、旧FAILED/NULL/返却対persisted mask/費/UNKNOWNと、mixed/learner全準備・pipeline、323USERPAUSE、oldfits96/defaults/models/weights/seals/foreign変更は保持します。本人Beadsはreadのみでwrite0、状態/backup/closeは324に委ねます。
