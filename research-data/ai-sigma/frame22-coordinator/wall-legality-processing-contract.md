# 同情報の壁合法性・到達性処理最適化

親quoridor-4lc / frame22-extension23。Rootのユーザー「取り入れられる部分はできるだけ取り入れよう」を実装・測定へ接続する。NNUE最高棋力に向けた探索費削減を問うが、速度を棋力/教師倍率へ代えない。285生成/286学習/287独立評価は維持する。

## 問い・優先と担当

Claustrophobia固定commit ae093653e62ad700e201706fa5ed767093d0d68e の bitboard.rs / encode.rs を一次参照する。main現legal_action_idsは候補壁ごとにgeometry→両pawn reachable、playで壁を再検査する。現在u128両goal全81mapは採用済み。まず代表prefixの現caller費/countersと壁密度別skip余地を短く観測し、実callerへ一つの障害グラフを再用する合法性検査を実装する。candidate wallの両端と中点の3post、全border接続を扱い、追加が閉路を作り得ない場合だけ正確reachabilityを省く。閉路候補は従来の正確BFSへ。片側端点だけの近道は採用しない。

担当は既critic saved session。279のcore/NNUE同情報実装経験と287のfuture待ちの静的余地による選定で、役名固定ではない。自作の正しさ検査・時間観測は本人証拠、main採用の独立source/算術レビューは別owner統括。287の学習ownerからの独立性を維持し、futurelabelsは候補/finalmask/settings凍結まで開封0。新セッション・subagent・全ACK0。

比較候補はcaller-local再構成/再用とcontext incremental/rollback。Position Copyの拡大/復帰費を含め、初手から恒久context層を増やさない。DSU構築/マスク構築/候補検査/正確BFS/play再検査を含める。boolean reachabilityがscalar距離/全81を求めない薄経路と共有WallEdgesが追加利益を持つなら同課題内の最大2介入で比較する。脅威plane/最短経路wall-filterは現QF1消費側が使わず今回は追加しない。局所distance差分は影響伝播・undoの全費未測で有力保留、全81再計算禁止0。安い第一案の小利益だけで残案を一律打切りせず、回収費/実caller利益から次判断を返す。

## 編集所有・版

managed WT /workspaces/quoridor/.worktree/frame21-search を再用、新WT0。本人のみ core/src/position.rs と必要core correctness tests、専用診断example/test、自己guard/report/dataがwriter。必要lib exportだけ追加可。AI/NNUE production数学/IDs/STM/TT/ordering/model/scale/履歴鍵は編集0。旧275/277/279比較scaffoldは停止archive/Gitpointを保持し、現在mainの必要core/AI/NNUE版へ明示source alignmentしてから現caller比較を行う。WTに残る旧scaffoldを現productionとして測らない。alignmentは保存済旧源/最後reader停止を本人確認して必要pathだけ、main編集/Git/index0。比較専用baselineは本課題の同仕事比較終了・停止保存後に不要経路を撤去する。Git再構成不能data/models/raw/failuresは保持。

scope research-data/ai-sigma/frame23-wall-legality-processing、report docs/reports/ai-sigma-critic-frame23-wall-legality-processing.md。main統合/indexは統括のみ、本人source/report停止path+bytesSHAを引渡す。新source復元コピー恒久化0。

## 総資源と保存済unusedの移譲

新親予算0。CPU3single/RAMcurrent2GiB guard1.75/GPU0、運用CPU0/current1GiBと全CPU4/RAM8に含める。CPU3は285worker2のphysical siblingなのでfixedtime/compile/モデルforwardは285/286実jobへ重ねず、static分析/編集は並行する。fresh current extension23 24hash/config/contract/正scheduler+monitor PIDtick/owner/nopause/実foreignCPU/RSSを各入口で本人確認。LLM人数/運用ownedをcomputebusyへ変換しない。

prospective conserved移譲:285 source/read300→240から60秒、compile/test180→60から120秒、data1GiB→992MiBからsharedoptimizer build32MiB。287 scientificNN100k→50kから50kNN、science600→360から240秒、management180→150から30秒、data8MiB→6MiBからoptimizerdata2MiB。287評価MAX2/各180秒/主3モデル・mask・凍結条件を維持。optimizer source60/compile120/manage30/NN50k/processed250k/science240秒/MAX3（各≤120秒）/data2MiB/build32MiB。未知/read/LLM/旧科学cap/失敗は保持する。各oldownerの全attempt/currentunusedと必要残費を確認し、移譲未成立項目をoptimizerは使用しない。不足は具体費/担当/次機会を返して統括が同親残内で再配分、旧budgetreset0。保管は92がfresh aggregateへnewscope/buildと残forecastを確認してからheavy。確認待ちにstaticsourceを止める全ACKgate0。

NN予定は品質full/delta≤10k、同仕事比較≤30k、逆順/確認≤10kの保守割当。最初から実root/depth/node/全planned行上界を結果前固定、数値キャップへ収めるために未成立結果を性能不支持へ変換しない。NN0caller microcostも科学job/wallへ含める。science/compile/management時計は包摂を明示して合計を偽加算せず、UNKNOWNは別保持。各build/generator guard、PIDtick/argv、wait/現在identity不在を保存する。

## 検証と採否

現Linux release。壁密度0/疎/密・border/midpoint閉路・maze/不可達候補・複数最短路・P2/jump/terminalを含む固定legal prefixesを結果前指定。従来正確reachability/queue mapをoracleに全legal Action集合と各候補可否、全必要81距離/両pawn到達、Copy親不変/undo/履歴復帰を照合。途中終局/無効壁/再構成/単独playも確認し、midpointだけ接続する反例を必須にする。NNUE scalar/SIMD/full-deltaの対応は変更経路に応じた意味ある既検査で有限確認。

同model/depth/node予定仕事でAction/value/PV/counters/履歴復帰を照合し、順序交互+逆順の局所callerと全search elapsed/RSS/init/再構成/復帰を分けて測る。局所BFS skip率だけで全探索/生成倍率を主張しない。teacher native callerへ使う場合の同K適格行/全job秒は別の後続測定で、本課題から倍率推定0。perfは現command未検出で外部CPU profiler未利用、取得せず既区間timer/countersを用いる。profiler全項目完備を入口にしない。

変更手書きRust/Python/configのみformat→必要lint/test→review。凍結baseline/旧data書換え0。17:15頃までに具体実装選択/費の短報、測定は主285/286の実stop後natural quietへ調整、science/source22:30/save22:45。親heavy23:26/監督23:31/monitor23:34/save23:36:03不変更。結果が不支持/不成立でも失敗/費/元sourceを保存し条件付き次案と必要費を返す。新feature/model/teacher/train/arena/dependency取得/共有env更新/push公開0。
