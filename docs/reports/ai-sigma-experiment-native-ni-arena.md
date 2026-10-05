# Native primary NI arena / quoridor-4lc.173

2026-10-03。新epoch2は33block・99pair・198局で固定の残時間guardにより停止した。候補95勝0分103敗、得点率95/198=0.4797979798。事前採択した5pp非劣性・片側95%の主方向wealthは1.885057588、劣性方向の別片側95%は0.438479351で、双方とも閾値20未達。**不確か**であり、非劣性・劣性の支持ではない。通常95%CIや停止後の精度保証へ変換しない。

対象は固定Sigma-Web751186のnative-hosted JSと151忠実Rust native、同ONNX d790、Python ORT1.30 CPUExecutionProvider/SEQUENTIAL/intra-inter1。CPU2/4/6の3arena、各専用2session、単一arena controller monotonic時計、402ms採用完了/411ms予定公開/500ms公開期限、両quiescent後の次t0という新登録modeに限る。browser・Sigma C++・世界最強・厳密等価への認定ではない。kernelCPU、全host/全TID、絶対clock誤差、定常共通conditional meanは実証していない。

## 結果前固定とepoch分離

新epoch2登録Git `8e14cf496047f3c2f19a5824abd219c82ce3b54f`。採択正本は[173-epoch2-adoption.json](../../research-data/ai-sigma/frame10-coordinator-start/173-epoch2-adoption.json)。fresh entropy/domain、全600pair seed/色順/core/blockを先に固定し、登録したblock6slotだけlazy NN0生成した。target長さは12/13/24/25/36/37/48/49を一度uniform8、カテゴリpawn/wall各.5・内一様、**いずれかlegal categoryが空ならproposal全体棄却**。合法順/非終端/距離>=3・差<=1/残壁双方>=2、max4096・firstacceptedを維持。旧開始3signature再利用又はcap欠測なら全登録6品質未知として停止する規則。結果によるseed/順/条件変更・成功補充は0。

旧epoch1は6terminal後06:53:42.574 readtimeout、callback未接続によるCONTROL_OR_INFRA_UNKNOWNを保持。登録6の品質は全未知、未来1194は未開始。旧wealth NI633/1200・負方向531/960、旧preregister `2fc9821dcd3eeeeab83dab06e296d022a983db69`、原600入力の497成功/103未生成・全attemptを保存した。勝敗を新設計判断へ用いず、48/49各先頭失敗seedのNN0 continuation348/408、追加92/152、合計553.528msのみを新設計根拠とした。旧成功prefixは補充/新正式入力へ流用していない。epoch2だけwealthを初期化し、旧stale SHA/497/ready時刻は旧provenanceへ分離した。

## 推論と全分母

固定λ主方向{1,2,4,6,8}/4・負方向{1,2,4,6}/4、各等重み、exact整数閾値20。全登録blockを順に一度だけ取り込み、未知はYlow/Yhighへ保守的に反映する。両方向は別片側5%で、同時両側95%ではない。JS BigIntと別Python整数算術で全33blockの積・分母・閾値判定が一致した。

全200block/600pair/1200gameのslot帳簿を保持。epoch2登録198は全品質既知、未来1002はNOT_STARTED(SCIENCE_DEADLINE_HEADROOM)のcapacityでwealthに加えない。解決済みprefix平均は.47979798。全1200capacityの記述識別区間は[0.0791666667, 0.9141666667]で、anytime推論の対象とは別。仮定はconditional bounded nullと定常共通μ、独立fresh opening/reset・同provider/policy/core均衡であり、周辺平均だけで成立しない。

## 時計・合法・保存検算

198局すべてGOAL。8268採用手、合法prefix/最終key/terminalを保存からNN0 replayし、各色の根648features/137NN bitsの一致を確認した（同RuleA decoderを共有するowner検算で、独立checkerではない）。採用完了最大401.998649985ms、公開最大420.955447018ms、CP schema failure0。537460 handNNと537460returnが対応、旧返却は次探索へ使わず、各次t0前にactiveNN/handles/search/pending zeroを照合した。late CP6618を不採用、discarded NN7271を別計上。cutoff timer観測は400.089655〜411.998981msであり、402ms停止の絶対誤差保証ではない。採用はactualend<=402のimmutable cacheのみ。

新reader10秒・最大1transport/schema readonly retry、初回失敗で全arena abort/stopCurrent/新search0、retry成功でもlost資格を救済しない。新epoch2 readerはREADYで終了。旧callback/readfaultと新NN0 timeout/pause/mockを別保存した。GPU174実forwardの停止/currentidentityを開始前照合し、GPU backendを混合していない。

## 実費

| 保存測定 | epoch2 |
| --- | ---: |
| job総wall（init・生成・管理含む） | 1565.520325秒 |
| GOAL game/sec | 0.126475522 |
| 有効first-root π/rootmean/z保存行/sec | 0.126475522（198行、holdout専用） |
| 全8268要求/sec | 5.281311（全手教師export速度ではない） |
| lazy NN0 generation | 49.972761秒 |
| ORT API await合計 | 2372.418195秒 |
| pipe span合計 | 2819.002431秒 |
| 原因側public後cleanup合計 | 1.248546秒 |
| common合法準備 / state advance | 0.314889 / 0.315176秒 |
| 総RSS peak | 2185297920B（guard4GiB内） |

API/pipe spanは重なり、3arena合計でもあるためwallへ加算しない。API awaitをkernelCPUへ変換しない。engine固有features/合法/history replay/JSON parse/CP配送/cloneを含む予算は固定したが、排他的component費の詳細はunknown。firstCP平均22.399297ms、最大120.740303ms。初期6session/startup6は別保存、旧epochのstartup6/handNN15645/heavy54.491439秒も別費として控除。累積handNN553105、品質heavy約1620.012秒で契約内。今回速度をそのまま外挿すると1200game約2.636時間だが、長い局面・fault・保存・追加initを保証しない。

## 停止・引渡しと次最大1案

新scienceは07:24:12開始、07:50:18頃に残時間guardで終了、全process回収/currentidentity/source対応を保存した。関連callback/ownedwait/inner close/outer stopは[science-stop-e2.json](../../research-data/ai-sigma/173-native-ni-arena/science-stop-e2.json)と全attempt archiveへ。必要source・旧失敗版は研究Git、原rawはarchiveと元作業領域を保持。pack全member byte復元、in-memory subtree Git復元とBeads backupをmanifestに記す。新NN/新科学/共有変更/旧証拠削除は0。

次案は**この有限native基準で、独立なnon-holdout入力の小さい教師生成batchを別配分**すること。採用したrootだけπ/leafNN/rootmean/終局z/視点/lineageを保存し、既160/162 schemaへ接続して有効教師行/secと保存費を測る。今回holdout198行は学習に使わない。実装差はcompact root exportに限定し、未立証NIを学習準備の恒久gateにしない。大量selfplay/本学習/NNUE/GPUの自動開始はしない。NI不足と将来正式評価費の見積りは保持する。

証拠: [epoch2-metrics.json](../../research-data/ai-sigma/173-native-ni-arena/epoch2-metrics.json)、[epoch2-inference.json](../../research-data/ai-sigma/173-native-ni-arena/epoch2-inference.json)、[epoch2-all-slots.json](../../research-data/ai-sigma/173-native-ni-arena/epoch2-all-slots.json)、[owner-replay.json](../../research-data/ai-sigma/173-native-ni-arena/owner-replay.json)、[holdout-root-export.json](../../research-data/ai-sigma/173-native-ni-arena/holdout-root-export.json)。

保存完了: source/data/report/全attempt pack Git `5a7ce76e100a8399dc53b73e9eb37607d9d1abf2`（70path exact byte復元）。Beads `backup sync` exit0、Backup synced in 234ms。pack 4,763,472B・320memberの全byte検証。[archive-manifest.json](../../research-data/ai-sigma/173-native-ni-arena/archive-manifest.json)、[git-restoration.json](../../research-data/ai-sigma/173-native-ni-arena/git-restoration.json)、[backup-receipt.json](../../research-data/ai-sigma/173-native-ni-arena/backup-receipt.json)。科学/source/helper停止、以後delivery metadataのみ。
