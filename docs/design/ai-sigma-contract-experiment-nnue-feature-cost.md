# NNUE-FEATURE-AND-DISTANCE-COST / quoridor-4lc.156 / 契約1・枠10

既experimentへ154の最大1案を採択し、NN0総コスト診断を実配分する。151科学source/runtime停止後、必要最小pack/Git/backup引渡しを完了し新自域へ切替、同役二重turn0。151の原結果/7勝9敗速報訂正/StageA ABI失敗/late reader不足を維持し、救済game/追加NNは0。155独立保存裁定の到着をこの静的準備のgateにしない。新最終目標NNUE型最高棋力、313/キャッシュは試案、Sigma同等/自前PV完成を予備試作の恒久gate0。今回はNNUE evaluator/αβ/学習モデルを実装0、まず特徴/距離/合法生成の支配費と正しさを問う。

自域 tools/ai-sigma-nnue-feature-cost/、research-data/ai-sigma/156-nnue-feature-cost/、.artifacts/ai-sigma/resume-20261003/NNUE-FEATURE-COST/、docs/reports/ai-sigma-experiment-nnue-feature-cost.md、単独writer experiment。元151 privatecrate/kernel/binary/model/RuleA/119/共有crates/root所有3docs/運用92はreadonly。必要pinned RuleAを自域コピー/ロードしてhash・source版をbind、必要source以外を全コピー0。writer coordinatorの契約は編集せず実装後source/run差分を保存。

固定入力は154事前4：151 initial-p1、asym-hv-p2、frame10-prefix-13、frame10-prefix-14。原stageA-inputs/DC205Fと測定r2state/history/features648へ合法prefixをNN0 replayしboard/pawns/wallremaining/side/history/ply/keyを対応。154で後2boardはplyのみ、全prefix replay未実施という不足を今回実検算で埋める。必要prefix欠測/不合法なら代替入力生成/直接state改変/NN0追加入力で補充せず未解決終了。teacher schemaはleafNN/rootmean/game結果と視点/予算/履歴を別保存、今回新teacher取得/学習export完成を要求0。

結果前に4入力それぞれ原legal順の先頭pawn最大8＋先頭wall最大8、計最大64root childを固定。空classは空のまま、後続状態から補充0。採用Actionは実合法集合へ確認し、元state/history合法適用で進める。順/caps/repeatを事前登録。各variantについて正しさ1遍、warm1遍、固定64repeatを1回だけ測定、入力index偶奇でAB/BA。短いstatic/schema/mock例外は同scope修復可、初回科学成功後の好成績採取反復/入力/回数変更0。browser command各30秒/全60秒、途中上限/欠測を全分母に残して自動拡大0。

共通出力は固定player/固定座標313binary（pawn81×2、壁anchor64×2、壁remaining11×2、turn1）＋後段に2距離scalar。距離はwall-only goal graphでpawnjumpを含む実勝利手数ではない。A=各state uncached2goal map BFS＋full313、B=boundedimmutable goal-map cache＋313差分更新。両variantのRuleA合法手生成/到達性判定と全context/statekey構築は同仕様/同範囲、別の未証明合法壁省略を混ぜない。全map81cell/距離2値/full vs delta313/合法手object順/terminal/history/key/parityで同出力を確認。各componentを別計測し、bundle総効果を個別因果/NNUE速度へ広げない。

map keyはH/V壁bits＋goalrow＋geometry/graph rule版のみ。pawn/side/wallremaining/ply/historyが変わっても同壁mapは再利用する一方、TT/teacher fullstate keyにはpawns/remaining/side/ply/historycount/rules/source/evaluatorversionを保持し、board-only TT bound再利用0。wall変更で別immutable map、cache miss/hit/evictionを記録、unmakeで親state/features/map handle/history/ply/terminal/合法集合を正確復帰。cache上限32壁配置の2map pair（数値保存bytesとobject overhead未測を分ける）、親livehandleをevictionで破壊0。

固定根child以外はNN0人工境界のみ：P2 jump/diagonal、H/V壁invalidation、pawn/side/historyのみ変更時mapreuse/合法集合やterminal差、200plydraw前goal、full-vs-delta更新/復帰、32capacity evictionのmock。人工操作を合法科学履歴や教師データへ混ぜない。キャッシュ正しさparity failureは失敗ログ/版を保存し同静的デバッグ枠で修復、科学性能行へ付替えず不一致残ならspeedclaim0で終了。距離不可達を勝敗/ゼロ距離へ置換0。

測定はBFScalls/cachehitsmisses、合法生成/到達判定、features full/delta変更entry、mapkey/lookup/cache、state/context/TTkey、make/unmake/復帰、1遍と全repeatの総wallを別記。cold/warm/AB順を分け、clockはbrowser performance、Nodeは起動/外監視/終了保存のみ。既NN/gpu/session/探索Worker/対局0。JS診断はRust/WasmNNUE throughputやαβ棋力の証明ではない。各入力B総費<Aかつ全parity/容量内なら小privateNNUE evaluator+αβ skeletonを次別配分候補に、利益なし/混在ならcache拡大を止め測定支配費へ変更、不一致/不足なら修復又は枝終了。現policy/モデル変更0、原baseline/教師を捨てない。

資源: 静的CPU[0]単1/RAM1GiB guard896MiB/command60s/総120s。NN0ChromeはCPU[2]単logical、browser/Node/descendant合計RAM2GiB guard1.75GiB、Nodeheap192MiB、他heavyと直列。研究全8GiB/CPU4内で155静的CPU0と可。既experiment2GiB保存予約内の新scope32MiB/guard28MiB、Chrome temp/依存/原保持＋有効未使用予約を二重加算せず current＋forecast確認、未知旧減額/追加親予約0、cache payload runtimeRAM別。新依存download/build/model学習0、既研究runtimeを使う。

起動直前151科学stop/currentidentity・外heavy/RAM/storage/pause/goal+self本人割当を通常現物確認、false/unknown/readerror/deadline/回収不能ならspawn0。151の同役後始末子を自己回収後Chrome、155の読み手が原pack/rawを参照中なら原データ削除0。私有filecaptured reader/有界retry/late typedfailure伝播、browsermain timer/monitorcallbacks/innercontrolled forcedとouterownedwait/currentidentityを別保存、現在不在≠自然/全期間/全host。active数で拒否0、同役dispatch競合/二重jobは拒否。

受領10分以内に本人claim/具体入力・事前登録/mock、処理受領45分又は03:10UTC、新heavy受領40分又は03:05、提出受領60分又は03:25の早側、時計reset0。準備/修復費用と科学費用を別記、全team累計未集計は未知。現枠10終了04:15:21・重04:05:21・監督04:10:21・monitor04:13:21/92責任/既saved settings維持。source/process停止、必要Git/input/run/reproduce/全attempt/結果/資源/停止/有限復元/hash・Beadsnotes/backup→coordinator。受入れcoordinator、goal/他者close0/NNUE最強/NI/棋力優位認定0。
