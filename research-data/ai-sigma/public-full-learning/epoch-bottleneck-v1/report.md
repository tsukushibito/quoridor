# 全量学習の1エポック実パイプライン計測

quoridor-4lc.323.2。2026-10-07。計測だけを実施し、元323のpause、newE/Sigma未開封、候補非採用を維持した。plainと詳細で全T一巡・4109更新、50%反転抽選4209397行、fullVの初期/epoch1値、INITIAL/BEST/LAST weights SHAが完全一致した。旧callerのconfig・INITIAL・尺度・教師・元行順・seed・FP32・Adam・batch2048は変更していない。

## 結果

学習loopではCPU特徴展開単体2.435秒に対し、H2D供給caller7.239秒が大きい。全CPU供給（読出し・geometry反転・展開・抽選・copy）は4.936秒。したがって展開単体をキャッシュするだけでは供給時間全体を除けない。H2D値にはpageable配列からの確保/転送API/side tensor生成/CPU待ちが含まれ、純粋なPCIe DMA時間や帯域律速の証明ではない。複数の有限性検査・launch/sync、初期dense診断のPNG費も無視できない。

## plainの全体と範囲

| scope（互いに重ならないwall） |     秒 |
| ----------------------------- | -----: |
| initialization                | 12.633 |
| initial_evaluation            |  3.303 |
| training_loop                 | 32.401 |
| fixed_diagnostic              | 17.479 |
| epoch_boundary                | 10.816 |
| finalize                      |  2.499 |

post-warmup3852更新の平均は約7.602ms/update（診断/境界を除く、中央値ではない）。

plain actual train call79.130秒、子起動/終了/guardianを含む79.763秒。学習loop単体32.401秒、初期化・初期評価・終了保存を除いたepoch1の学習+固定診断+境界は60.695秒。初期化12.633秒にはTorch import/model/CUDA setup、cache hash/geometry検査/group setup、T統計を含む。詳細でcache load等3.764秒、T統計1.019秒（内gather0.272秒）が観測された。初期評価3.303秒はfullV419150+Tdiag8192と保存/描画を含む。

初回update0.498秒。warmup257更新合計3.104秒、その後3852更新合計29.282秒。ただし各update計測は固定診断/epoch境界を除く。初回Adam等の準備を含むため、最初のupdateを定常batch時間として扱わない。全phaseを追加してwholeを作らず、上のlifecycleだけをwall partitionとして用いる。

このfirst epochはepoch1のfullT評価と、初期dense診断91記録点を含む。後半の通常epochや従前の中央値32秒と同じ費ではない。fullTはepoch1と5epoch周期の既設定であり、今回の全費を全epochへ外挿しない。

## 詳細instrumentationの学習loop

表の分母は詳細loop35.944秒。CPU wallの区間でありGPU kernel時間ではない。CPU_supplyの内訳は別表とし、二重に足さない。

| scope                                       |    秒 | 詳細loop比 |
| ------------------------------------------- | ----: | ---------: |
| epoch_sampling_shuffle_index                | 0.259 |       0.7% |
| index_attempted_visit_accounting            | 0.384 |       1.1% |
| zero_grad                                   | 0.246 |       0.7% |
| CPU_supply                                  | 4.936 |      13.7% |
| H2D_features_distance_side                  | 7.239 |      20.1% |
| explicit_CUDA_synchronize_wait              | 0.699 |       1.9% |
| GPU_training_forward                        | 2.904 |       8.1% |
| loss_target_H2D_and_finite_check            | 2.226 |       6.2% |
| GPU_backward                                | 5.714 |      15.9% |
| finite_gradient_check                       | 3.353 |       9.3% |
| GPU_Adam_step                               | 2.079 |       5.8% |
| finite_parameter_check                      | 2.769 |       7.7% |
| index_successful_visit_accounting           | 0.368 |       1.0% |
| unattributed_rest_including_instrumentation | 2.769 |       7.7% |

| CPU_supplyの内訳（包含）                                        |    秒 |
| --------------------------------------------------------------- | ----: |
| compact_gather_read                                             | 0.742 |
| CPU_correctLR_geometry                                          | 0.585 |
| CPU_geometry_to_QF1                                             | 2.435 |
| supply_including_reflection_RNG（外側、gather/反転/展開を含む） | 4.899 |

読み出し0.742秒は既memmap行のgather/copyのCPU wallであり、物理disk IOだけの時間ではない。callerによる全SHA/validation/statistics scan後の観測で、OS cacheを消去・リセットしていない。plain→detailedの固定順1pairで、warmcache/装置clock変動を統計的に分離していない。

## GPU非同期・待ち・代表区間

既導入torch.profiler/Kinetoを1025–1040の16成功updateだけで起動。1025の既固定診断も維持され、代表区間は追加8評価batchを含む。新依存取得0・巨大trace出力0。209 key averagesとCUDA event集計だけを保存した。

実kernel/memcpy/memset活動の集計は108.027ms、うちHtoD38.581ms（活動集計の35.7%）、DtoH0.353ms。CPU user-rangeに対応する合成CUDA range9種を除外した。rangeと実kernelを合計すると二重計数になる。活動はoverlap可能なので、この108msをwindow wallやGPU利用率にしない。代表区間の正確な独立wallは未保存で、活動率・全epochへの純DMA外挿はUNKNOWN。

CUDA eventのstream elapsedはtrainingのH2D50.295ms/forward20.807ms/backward46.622ms/Adam11.047ms/gradient finite12.148ms/parameter finite16.049ms等。これはCPU enqueue間のGPU stream idleを含み得る。CPU enqueue wallや純kernel時間と等置しない。backwardの純kernelをrecord_functionだけに帰属することはasync autogradのため保持key averagesでは未分離。raw event/range値をそのまま残す。

代表区間にはcudaMemcpyAsync222回、cudaStreamSynchronize174回、cudaDeviceSynchronize65回。CPU selfの待ち/API費はそれぞれ52.888/30.689/5.793ms。GPU kernel・CPU待ち・外側spanは包含/並行しており加算しない。実callerのbatch転送後/forward後/update後同期とbool finite判定は保持しており、CPU供給とGPU計算を明示的に先読み重複する経路ではない。

plain loopのprocess CPU/wallは0.985core相当（割当2logicalに対し約49.2%、親trainerのprocess CPUのみでplot子CPUは含まない）。whole lifecycle中のNVML時間重みGPU利用はplain21.8%/詳細23.2%、最大sample69%/68%。whole-device/rolling sampleで初期化/評価/PNGを含み、train-only占有率や連続絶対peakの証明ではない。

## 評価・描画・保存

詳細epoch境界11.218秒の内fullT予測7.680秒、fullV予測0.393秒、T/V等metric集計0.982秒、PNG2process待ち2.136秒。各predict内にはCPU供給/転送/GPU forward/DtoHが含まれ、内訳を再加算しない。診断91点はselectorではなくoriginal固定T/V subsetで、反転RNGを消費しない。

初期dense固定診断17.590秒の内PNG10process待ち11.145秒、metric集計2.803秒。全lifecycleのPNG16process待ちは17.608秒。ここは描画計算だけでなく外部plot環境のprocess起動/import/終了を含む。checkpoint PT+native全7saveのwallは合計約0.023秒、最後のvisit圧縮0.223秒。CSV/JSONLのその他記録やPython帳簿は未帰属remainderに残り、0扱いしない。数値記録を減らさずPNG更新頻度/起動費を減らす案は検討余地があるが、今回変更・速度実証はしていない。

## instrumentation overhead・資格・制約

actual train call plain79.130→詳細82.576秒、観測差+3.446秒/+4.35%。loop32.401→35.944秒/+10.94%。profiler開始0.028秒、停止/集計0.688秒は詳細loopに既に含まれる。詳細のphase値はobserver/profilerの追加費を含む。plainも同じ計測入口のlifecycle時計と既guardianを持つため、完全にhook無しhistorical版との差ではない。1pairの観測差を精密な補正係数・公平な速度比へしない。

各modeの成功model rows19132566 =train8413949 +full selector9260441 +診断1458176。full selectorは初期Tdiag8192/V419150とepoch1全T8413949/V419150。ONNX/newE/Sigma/native live forward0。全T visit最小/最大1・attempted4109・sampler seen8413949・反転draw4209397とfullV曲線を保存sampling/曲線JSONで確認した。INITIAL/BEST/LAST weight byte SHAは両mode完全一致し、INITIALは既資格2ddacbf…7414adと一致。保存された診断weightsを選定/cohortに加えず、freeze.jsonを作らない。

job6b4627ea START03:55:09.848909Z、自然STOP03:57:53.039033Z、controller全費163.249098159秒。worker+plain trainer+detailed trainerのdirectwait/cleanuptrue/remaining[]、記録3科学PID/start不存在確認。原323pauseは維持。新extra計測/改善run/native/testを自動実行しない。

sampled familyRSS（controller reserve込み）2958528512B<4GiB、whole-device VRAM1809334272B<6GiB。NVML telemetry追加guardian CPU0.4066秒、3022samples。保存actual5,113,048B<14MiB guard、control/source/summaryは512KiB forecast内で最終確認。旧データ/モデル/失敗/費/UNKNOWNを保全し、Root future overlayの変更を旧usedmanifest不一致にしない。

## 改善候補（提案のみ）

1. pageable dense特徴の転送callerを優先検討：compact GPU展開/保持、または再利用pinned buffer+供給先読み。H2D callerはCPU展開単体より大きいが、方式の速度優位や必要VRAMは未実証。
2. 全数値観測/全V selectorを保持してPNG process起動の頻度・寿命を見直す。first epochのlarge IO費に根拠がある。通常後半epochの削減幅は別。
3. finite検査・loss等の細粒度GPU launch/syncをまとめる実装案。検査自体を取り除いたり失敗を見逃す提案ではなく、同じ検査タイミング/非finite停止/算術を保つ資格が必要。
4. CPU geometry変換の再利用/最適化。今回の展開単体はloopの約6.8%で、これだけを省いて全パイプラインが劇的に速くなるとは言えない。

根因・方式優位性の採用はRootの関連独立レビュー判断へ戻す。モデル/batch/precision/worker数/特徴/math/teacher/seedは変えていない。

## 正本・再構成元

同dir analysis.json/raw runtime/config/plan/control/forecast/preflight/stop-receipt.json。実dataは既asset参照でnewE/openedをmapしない。stopped-source.tar.gzは今回3maintained source、train-before.py.txtは旧r6 sourceの限定証拠。source/config/math-call-check/3NN0/formatter確認を保持。Rootがmain/Git唯一writer、今回main/index/ref操作0。
