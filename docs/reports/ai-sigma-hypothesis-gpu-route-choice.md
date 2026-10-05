# 固定ONNXの折り込み済み推論を既PyTorch CUDAへ載せる

quoridor-4lc.171 / 契約1、Git1849f98998afc383fdb1d87054d5df1411a8baf7。受領時計はintake.json、本人claim/静的開始2026-10-03 06:29:08UTC。goal/self・pause無し本人担当確認済み。CPU0静的処理に4arena実競合は観測しなかった。170 science-stopと保存停止を参照し、現在process読取は有限観測で全host/全期間保証ではない。開始報告と最大1案速報を既App Serverへ送った。

推奨は**固定ONNX d790の折り込み済みConv重み・残存BN・headを、そのまま使う私有PyTorch推論adapter**。既torchCUDAとonnx/numpyだけで、9x9/F128/R10/gpool3/6/9/local pawn/pooled valueの小forwardを作る。研究専用ORTGPUを新取得するより既環境を使える実装候補として選ぶ。モデル対応・数値parity・速度はまだ未測定。GPUはCPU native評価170や正式NIの開始gateにしない。

## 静的に揃ったものと不足

root観測result.json SHA427f7ec1fcf1e249caa7f2827f5a9ab9c95819a0dcb4b95aa12161b60db3fe78は、RTX3060・torch2.14+cu130・実CUDA tensor1+1/readCPU/synchronize成功を保存している。ここからCUDA計算の基本成立は支持する。SigmaモデルNNや学習成立は支持しない。既ORT1.30はAzure/CPUのみでCUDA/TensorRT providerを持たない。このORT不足をGPU全体不能へ変換しない。171ではtorch import・CUDA API・model session/forwardを一切行っていない。

既Sigma原source dual_network.py/export_onnx.pyは保存source-manifestのcommit751186344fc52ad0c29bc65922e62c6fa915f006と現在hashが一致。exportは元runs/models_9x9_pcr/best.ptをCPU/eval、dummy1x8x9x9、opset17/dynamo=Falseで固定ONNXへ出す。原モデルのdefaultはboard7/F64/R6かつ新headなので、default constructorを固定d790の代用にしない。原moduleはDEVICE判定でCUDA APIを呼ぶため静的調査でimportしていない。

ONNXを既onnxで静的load/checkerした。model11663428B/SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d、IR8/opset17、input FLOAT[1,8,9,9]、policy_logits[1,136]/value[1,1]。179node/16op、83 FLOAT initializer全finite・external0、2908299float/11633196 raw weight bytes。raw initializer hash・全node属性・小整数Constantはgraph-evidence.json/static-values-check.jsonへ保存し、重み本体は複製しない。

| sourceとgraphの対応 | 実際のd790 | adapterへの移送 |
| --- | --- | --- |
| trunk | conv8→128、residual index0..9、gpool index2/5/8 | sourceの順序・skip Add/ReLUを保持 |
| 通常Conv/BN | 24Convのうち21がONNX生成名のW+b、直後BNは折込済み | 21Convをbias有りのf32 convolutionとして直接使用。既folded W/bを再fold/逆算しない |
| gpool | 3Conv1は128→128のraw W、96 regular/32 poolへsplit、残6BN | 6BNのgamma/beta/running mean/var、epsilon9.999999747e-6、training_mode0を保持。mean/max→64→96 biasをbroadcast |
| pawn | 入力plane0/1のmask×trunk sumとglobal mean、384→64→8 | 位置/視点の変換を加えずraw8 logits、softmaxは既探索側へ |
| walls | H/V1x1 conv→ReLU→上左8x8→row-major flatten | pawn8/H64/V64で136を維持。合法Action/P2 mappingは既native encoderに帰属 |
| value | 128→32conv、mean+max64→128→1/tanh | 生の手番視点valueを維持し符号変更しない |
| FC | Gemm7、alpha/beta1・transB1 | 保存W[output,input]/biasを同方向linearへ |

選んだ3checkpoint pathでは元best.ptは不存在。全host不存在や将来取得不可とはしない。ONNXのfolded W+bから元の未folded conv/BN state_dictを名前だけで復元できない。したがって原DualNetworkへの単純load_state_dict、strict=Falseで欠けた重みを乱数で埋める、warm_startでhead再初期化する経路は採らない。元BNの分解を復元する必要もない。推論adapterはgraphが実際に持つ全係数を使い、同一initializer bits・操作順序を明示する。ONNXとGPUの出力bit一致までは仮定せず、演算kernel/丸め差をparityで評価する。

16opはConv/Relu/Add/Constant/Slice/BatchNormalization/ReduceMean/ReduceMax/Concat/Gemm/Unsqueeze/Mul/ReduceSum/Gather/Reshape/Tanh。汎用ONNX runtimeを新作せず、既sourceの小forwardと24Conv/6BN/7FCの名前対応だけを私有化する。Constant由来のshape/sliceを固定batch1に照合し、知らないgraph/hash/属性を拒否する。元sourceの全training/game依存を取り込まない。

## 最大1の次配分案と費用

担当experiment、私有tools/ai-sigma-sigma-torch-gpu-parity/と課題別research-dataのみを提案する。171はこの実装を実行しない。作るのはfixed-hash loader/weight-map/small forwardと有限benchmark、既native evaluatorに差し替え可能な常駐request adapterまでの小境界。元model/source/170/共有環境はreadonly。新依存/install/download/学習0、ONNX/checkpoint重複保存0。実装見積り30〜45分・おおむね150〜250行、管理/import/CPU確認計60秒、科学測定計180秒・全command90秒以内、RAM2GiB/guard1.75GiB、CPU1logical、VRAM6GiB/job30分以内、追加保存source/log/metadata2MiBを配分時に確認する。root CUDA probeのpeak658552KiBは今回512MiBとは別で、次測定にRAM増配を要する根拠だがモデルpeakの上限保証ではない。8GiB/4logicalの現在他owner量を確認し、4arena同時計測へ重ねない。親11期限内へ収まらなければ次枠提案に止める。

固定入力は160のinitial648 f32bits一件（診断用）を事前選び、batch1維持。CPU ORT固定d790、torch adapter CPU、torch adapter CUDAを同じ入力で比較し、各warm1+steady8の計27forwardを上限とする。新モデル/weights初期化変更・学習0。全136logits/valueのshape/finite、abs1e-5+rtol1e-4を結果前のparity規則とし、CPU ORT対torchCPUとtorchCPU対GPUを分けて最大差を保存。FP32、TF32/AMP無効、eval/inference-only、BN統計固定と実設定を記録する。toleranceを結果後に緩めない。失敗や再試行はtyped分類で全attemptを残し、有限数を良い結果で置き換えない。

初期化（graph/weights parse、CUDA context、重みH2D、必要初回library投入）を別計上し、各要求はhost input ready→H2D→kernel投入→明示同期→D2H→host出力readyを単一host時計で測る。GPU内event区間は補助指標であり非同期launchだけを推論完了時間にしない。常駐重みを毎forward転送せず、cold/warm/steadyの全値を残す。最小native request経路で同payload/JSON/IPC待ち/出力配送を含む総費も同じ8要求に対応させ、純forward費と二重計上せず分ける。CPU対照はORT1threadとtorchCPU1thread、thread/RSS/VRAM/停止wait・環境hashを記録する。GPUの速さを文字列やtensor足算から埋めない。

成功しparityと総要求費がCPUより改善すれば、別の対局/教師生成配分で採用可能性を調べる。parity成功でも単入力無差・悪化/JSON・IPCまたは多数小kernel支配ならCPU nativeを優先し、batch throughput利得は未確認として残す。parity不成立は層/重み対応/FP32設定を最小範囲で調べ、GPU教師や棋力結果へ進めない。構造復元の費用が見積りを超えるなら枝終了してCPUを優先し、ORTGPU別環境に必要な依存/容量を別配分として報告する。共有ORTへの上書きは提案しない。OOM/provider/回収不能はtyped不成立で停止し上限拡張0。

固定ONNXはbatch1。batch8への黙示変更0、8件のbatch1をbatch8成功としない。単入力費用が悪くても多数selfplayでbatchが有利な可能性は残るが、今回の次案はまずbatch1だけで判別する。葉latency/有効教師行sec/対局総費の改善と棋力を分ける。GPUモデル・速度・label品質/同wall棋力・正式NIは未立証のまま、170 CPU nativeと独立統計設計を継続する。

## 今回の資源・保存・停止

CPU0単1、static60秒、RAM512MiB/guard448MiB。graph検査peak86600KiB、内部0.084836秒、finite/constants追加検査peak67000KiB。新model session/forward/CUDA/学習/NN/build/game/取得/依存更新/委譲0。管理reportの一回dispatch lock拒否と有界一回retry成功を保存し、科学失敗にしない。usageLimitExceeded再発は観測していない。

旧未確認保持14596875Bを減額せず、新scope+Git+metadataforecast524288Bを加え15121163B<15MiB15728640B、16MiB既予約内、親追加/移管/削除0。実currentと最終forecastはstop.json/Git記録に保存。私有index全tree複製0、自域files-only CASでGit保存、必要pathをGit stream復元照合する。原164・170・モデル・rootdocsへのwrite0。自己source/同期子終了、ownedwait残0と現在不在のみを記録し全期間/自然終了保証へ拡大しない。Beadsbackup sync後coordinatorへ返す。受付/transport acceptedと本人開始/科学成立/受入れを分け、goal/他者close0。
