# quoridor-4lc.187 / Sigma型多数game共有GPUの実生成比較

統括からexperimentへ新現在配分。親frame13明示許可12:45:15–14:45:15UTC、重開始停止14:35:15/監督14:40:15/monitor14:43:15。旧frame12は停止済みで期限/結果を延長しない。本人ready/show goal+self/pause/担当確認→187だけclaimし実開始を報告する。worktree /workspaces/quoridor/.worktree/ai-sigma。単独writerはexperiment、tools/ai-sigma-manygame-generation/、research-data/ai-sigma/187-manygame-generation/、docs/reports/ai-sigma-experiment-manygame-generation.mdだけ。185/177/181/176はreadonly再利用。親本文/運用92/registry/他者source/default Git indexを変更しない。通常root再承認待ち0。

主問い:3CPU workerが多数の独立gameを多重化して共有GPU maxB8へ送る方式は、現在最速CPUJS生成に対して同Kの適格教師/全job時間を改善するか。176のGPU3/maxB2不採用をGPU一般へ拡張せず、公開Sigma C++の全探索/教師規則と同一とは呼ばない。同Rust CPU対GPUは構造比較、CPUJSは実用採用対照として別解釈。根/探索数値対応は有限の範囲、棋力NIではない。

185 evidence591b0dbe/handoffefa765f5のgamepool/broker/ID/取消/tapeを再利用し、実Rust Registry multi-handle worker、予算付き177 Torch folded dynamicB real provider、fullgame/outcome/全手teacher exportを薄く接続する。既binary166dd0c4/ONNXd790/CPU ORT1.30 intra/inter1を維持、新build/依存取得/共有環境更新0。GPUは既torchCUDA/VRAM6GiB、原ONNX batch1を変更せず私有folded dynamicBを明記する。3worker CPU2/4/6、各game1pending、独立tree、共通broker CPU0、FIFO native pipe、ID run/worker/game/generation/handle/token/request。取消inflightは物理返却/破棄まで所有を保持しgeneration/handle再利用禁止。stale/EOF/値schema/providerfaultは全affectedのtyped unknown、旧成功を補充しない。partial batch/stop/drainの185 mockを再用し実モデル未確認B3/5/6/7だけ小固定fixture parityで確認する。B1..8 heterogeneous CPUORT対CUDA abs1e-4+rtol1e-4、原174/177 tol不変更。長い全役gateを作らない。

結果前に新fresh24game openings0/4/8/12/16/20各4・合法生成/seed/family/actionseedを固定。モデル/規則/K64 rootN64 edge和63/root初回NN含む/温度tau1初16newplyその後argmax/newply200cap/合法P2 mapping/終局z視点を各mode同条件にする。原173正式198holdout学習0。π=訪問63分布、rootNN/rootmean/leafNN/z/side/history/lineage別、打切りzunknown/value maskfalse、rootterminal/K1/不明mappingにπを捏造0。game単位split、crossmode siblingsは同familyでまとめる。新比較データを旧learnerへ自動混合0。

固定比較mode候補をCPUJS3heldsession、RustCPU3serial、GPU3active、GPU12active、GPU24activeとする。各24予定/各job最大300s、GPU各別job model held中のmaxB8実batch、起動終了も費用へ含める。実装上必要なら科学結果前に最小mode群へ絞り理由/予定分母を固定して報告する。結果を見て有利なmodeだけ報告しない。GPU各job<=30min、maxNN各mode307200（24*200*64）/総1536000、startup別、parity/debug追加sample2048までを別台帳。実model partialparityとsource/schema/mockを先に固定し、高価な成功科学行を置換再実行0。デバッグは同187内、失敗source/log/typed不足を保持して有界修復可。

全jobheavy合計1800s、NN cap上記、実装費目安45–60分、science14:20/処理14:30/提出14:40/newheavy14:15早側。CPU計算最大4logical、CPUcontrol3+管理pool内/GPU3+CPU0 provider-management。RAM CPU4GiB guard3.5/GPU6GiB guard5.5、親合計8GiB、GPUVRAM6GiB。hyp188 CPU8短学習は187重job前に実停止を確認し、並行NN heavy0/CPU5を作らない。LLMactive数gate0。自然監督CPU0のexactowned/次予定と窓は必要現物admit、周期変更/92affinity変更/監督interrupt0。個別job timeoutと回収/保存を含む残余を確認、窓不足は減数量/未実施分母保持で報告し親を延長0。

新保存256MiB予約/guard224MiBは既experiment2044MiBの確認済未使用から配分し、旧未知量減額/親追加予約0。current保持+Git+一時+forecastを直前確認。in-memory subtree Gitでdefaultindex不変更、必要raw/失敗/版/全statusを保存、最小pack member SHA/必要Git bytes復元/Beads notes/backup。全host/全期間/瞬間peakの保証へ現在不在を格上げ0。科学/source/所有子停止を先に報告し保存helpersは別。

採否はRpolicy/Rz/Rjoint各全分母・全attempt初期化/生成/探索/推論/輸送/記録/cleanup/jobwall・game/sec・batch分布/queue待ち/RAMVRAMでCPUJS同条件と比較する。raw行数/単batch倍率を実生成倍率へしない。GPU利益なし又はCPU/IPC支配ならGPUbranchを終了しCPU採用経路で前進、比較診断の自動連鎖0。成立なら有効教師保存を具体成果にし、教師品質/多様性/棋力は別に残す。実装が長引けば最小実生成→必要データ保存を優先、未接続をmock成功で代替0。本人受付/claim実開始→15分以内準備又は最初科学速報→停止/結果/費用/次1判断を統括へ送る。受入れcloseはcoordinator、goal達成close0。188/critic全文待ちは開始gate0。
