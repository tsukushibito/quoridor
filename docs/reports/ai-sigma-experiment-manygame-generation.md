# 187 Sigma型多数game共有GPUの実生成比較

GPU24activeの共有maxB8は、この固定24game・同K64でCPUJSより適格教師/全job時間を1.5604倍にした。GPU12は1.2786倍、GPU3は0.5577倍。単回・固定順の局所的結果であり、棋力、教師真値、全tree精密同等や一般的生成倍率を認定しない。GPU一般の不採用へ旧176 GPU3/B2を拡張せず、現在のCPU default/既learnerは変更していない。

|mode|全24予定の結果|Rpolicy/Rz/Rjoint|全attempt jobwall s|Rjoint/s|CPUJS比|平均batch|sampled RSS peak GiB|
|---|---|---:|---:|---:|---:|---:|---:|
|CPUJS|24 GOAL /打切り0|1132/1132/1132|137.836401|8.212635|1.0000|—|1.3423|
|RustCPU|3 schema unknown /21未開始|0/0/0|6.334307|測定不成立|—|—|0.5196|
|GPU3|24 GOAL /打切り0|1132/1132/1132|247.139345|4.580412|0.5577|2.2922|1.8439|
|GPU12|24 GOAL /打切り0|1132/1132/1132|107.801322|10.500799|1.2786|5.3564|1.9358|
|GPU24|24 GOAL /打切り0|1132/1132/1132|88.334456|12.814931|1.5604|6.6223|2.0311|

全120予定を保持した。正常な4modeの計96局はすべてGOAL、各1132行、総4528行はRpolicy=Rz=Rjoint。各手root64/edge63、π=訪問/63、tau1初16newplyの実行動をπと別保存、rootNN/rootmean/leaf/z・手番/P1視点を区別した。全24slotの手数・terminal/censoring分布をmode別all-status/summaryへ保存し、完走局だけの教師品質改善とは言わない。新データは旧learnerへ混合していない。173正式holdoutの読取/教師転用0。

RustCPU-r1は3開始根のhistory照合例外で190NN返却後に停止、row0。JSのlocaleSortとRust BTree byte-sortの提示順が異なり、NN0の3実begin/rootでkey/count・features・legal/side/plyは対応した。未開始GPUのvalidatorだけcanonical key/count比較に修復した。旧RustCPUの3typed未知+21未開始、6.334307s、失敗版をそのまま保持し再実行/補充しない。このため同Rust CPU対GPUの構造速度比は未測定。未知をNN不一致/棋力敗北/正常0scoreへ変換していない。

実モデルparityは新固定heterogeneous B1..8、CPUORTとCUDAで全abs1e-4+rtol1e-4内（最大5.57676e-6、72sample）。保存済み初根の各GPU24件/計72根はfeatures・合法順・history key/count・side/ply/Kに対応し、final visits/π/argmax/実tau行動一致、rootNN/logits/rootmeanの数値差を別保存した。全deep NN/tree対応は未確認。共有RuleAの全4528行replayでfeatures/history/合法action/終局winner/zとπの資格を検算したが、独立ルール検証や教師真値ではない。

CPUJS各gameは専用held CPUORT1.30/intra/inter1/SEQUENTIAL、Rustは旧166dd0c4 binary、CUDAは原ONNX batch1を変更せずprivate177 folded dynamicB/TF32off/AMPoff/BN eval。CPUJS管理/worker pool2,4,6、GPUはworker2,4,6+broker/provider0の4logical。共通の親許可4logical内だが、実kernelCPU等量保証はない。自然supervisor終了/currentownednone/次予定、188子停止、GPU current不在/RAM/保存forecastを各job前にadmitした。順序CPUJS→RustCPU→GPU3→GPU12→GPU24、cold provider/session init・初回・cleanupをjobwallへ含む。steady/API/pipe/queueのawaitは重なり、排他CPU/kernel分解は不明。単回の順序・host・warm交絡を保持する。

実batch分布B1..8、queue合計/最大/先頭16receipt、provider stage sums、各worker bridge回数/bytes、init/close/started-returned-zero、sampled RSS/VRAMをraw archiveとsummaryへ保存した。GPU VRAM peak reservedは各35,651,584B。batch-fill増加が観測されるが、その相関だけで速度差の全原因を確定しない。every-sim checkpoint/root_edges構築は新Rust workerで呼ばず、各完成手の最終CP一回だけ。NN数の削減による品質利益とは解釈しない（正常4modeはすべてhandNN63,720）。

fresh entropy/domain/24opening0,4,8,12,16,20各4とaction seeds/family/splitは結果前固定。最大256/firstaccepted、class.5/内一様/選択emptyカテゴリはproposal棄却、途中terminal棄却を保持。重複は保持し、20train/4validationのfamily splitで全mode siblingsを同groupへ置く。正常modeごとposition/featuresは1118 unique、crossgame8keys22occ、train-val7keys20occ。fullstate(history/side/ply)とfeatures+legalmaskは別定義でoverlap-detailをsummaryに保存し、state独立holdout/IID/通常対局代表性を認定しない。

NN0 prepare/mock失敗/修正版/history probeを含む全attempt program jobwall630.587673s。handNN255,070（正常4mode254,880+失敗Rust190）、parity72、startup3を別計上し総255,145forward、既heavy1800/NN1536000+debug2048内。科学最後13:46:15.039終了、全子wait/current同identity不在を13:48確認。全工程準備elapsed、export/pack/Git/backup helpersはpipeline-cost-ledgerへ別記しproduction率と混同しない。

次1判断は、GPU24active/maxB8をこの資源・同教師規則の次のfresh独立lineage生成候補として統括へ渡す。今回の兄弟benchmarkを旧trainへ自動混合せず、拡大/学習配分を別に採択する。GPU3はこの方式の拡大候補から外す。追加診断や通常default変更は自動開始しない。

再現は私有README/config/source bindings。結果前source2fef995b、future-only history修復40011c34、GPU guardian/source31a80738。raw全attempt/全slot/全手/失敗・必要clock/cost/stopをall-attempt-evidence.tar.gzへまとめ、全member SHA検算。モデル・環境・旧source/binaryは共有参照のみ。Git復元/Beadsbackup/最終引渡しはhandoff.json参照。研究goalは未達のまま、個別受入れ/closeはcoordinator。
