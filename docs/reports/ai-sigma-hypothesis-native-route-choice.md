# Native経路は常駐CPU ORTと既JSON境界を先行する

quoridor-4lc.164 / 契約1・親11。受領2026-10-03 04:38:34.800333UTC、本人claim/静的開始04:38:38UTC。契約Git d0136c1293dc66be2d165d5c012a40b898655f23。速報04:43:54UTCを既App Serverへ配送済み。165の開始gateにはしない。

推奨は最大1経路：151の忠実Rust探索を小さいnative JSONL workerで公開し、固定Sigma-Web751186の探索をNodeへhostし、両者の評価を既Python ORT1.30 CPUExecutionProviderの常駐sessionへ渡す。固定ONNX d790を継承し、session/model初期化を毎手・毎NNで繰り返さない。既境界と既依存を再利用できるため、今はRust用ORT binding追加やPyTorchへの教師置換より実装費が小さいと判断する。実速度の優越は未測定。

## 現物根拠と不足

| 境界 | 確認結果 | まだ必要なこと |
| --- | --- | --- |
| Rust151 | private crateはrlib/cdylib、JSON new/begin/resume/checkpoint/cancel。generation/token、648 f32bits、NN f32→tree f64、合法順序を保持。ORT/TCH依存なし | native executable/stdinstdout wrapper、取消/終了、モデル評価接続。ort_call等の名前はJSON ABIでありORT linkageではない |
| 固定参照 | reference-core.jsはC1/FPU.2、安定順序、root初期backupと後続simulation。評価callbackを持つ | Node vm/global/timer adapterが必要。module export済みとは扱わない。setTimeout yieldを除く変更も記録する |
| CPU backend | 既専用環境でORT1.30.0のmetadata取得exit0。available providersはAzureExecutionProvider/CPUExecutionProvider、native共有libraryあり | 固定Sigmaモデルのnative session/数値/機構parity、時計と実速度は今回未実行 |
| PyTorch | dist-infoは2.14.0+cu130。162 toyのCPU学習・checkpoint・ONNX5行parityは既有限成立 | toyは新初期重み。固定Sigmaの元PyTorch構造/state_dict移送は今回選定範囲で未確認。ONNX教師をtorchでそのまま使えるとはしない |
| Rust cache | 指定Cargo registry直下にort/ort-sys/onnxruntime/tch/torch-sys該当なし | 全host不存在を主張しない。新binding取得は今推奨経路に不要 |
| GPU | ORT CUDA/TensorRT providerなし、providers_cuda libraryなし。/dev/dxgとlibcuda.so.1は存在 | CUDA build文字列だけで実GPU inference成立とはしない。torch import/CUDA API/モデルsession/GPU実行0 |

モデルは保存正本の11663428B、SHA256 d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908dを参照した。既静的checkerの入力[1,8,9,9]、出力[1,136]/[1,1]、external weights0を使い、新model load/NNで再検算していない。必要source7境界の現物hashはstatic-evidence.jsonに保存した。

これはSigmaC++比較ではなく、固定Web探索をnative host/CPU ORTへ移す新条件である。ORT WASM→native CPU、Node event loop、Rust⇄評価器の輸送差を隠さない。Root K32はroot NNを含む32 backup・通常edge和31という既定義を明示し、terminal-noNNをNN数へ足さない。libraryの未指定simulations4096を測定条件へ流入させない。

## 輸送費と同wallの限界

NN0 codec診断をCPU0で実施した。160 initial fixtureの648整数bitsをcompact JSONで再読込し全一致、request4113B/synthetic zero136-logit reply611B。warm1/測定8のcodec往復中央値0.055281ms、peakRSS15280KiB。これはPython serialize/parseだけでIPC0、Rust/Node/NN/queue/clock0であり、実経路速度を予測する値ではない。fixture hash・全8値・command・stdoutはcodec-result.json/command-codec.jsonへ保存。synthetic replyを教師へ混ぜない。

常駐sessionなら初期化費を分離できるが、Rust側のJSON/pipe待ちと参照側直接callbackの費用は等しいとは限らない。samewallでは入力可能t0→合法応答配送のwrapper全体、旧NN残CPU、自待ち、相手clock、競合を記録・帰属する。NN数/完成backup/terminal別分母を併記し、輸送減だけを探索改善や棋力と呼ばない。実輸送が支配的と判明した時点でin-process C ABI等への最小変更を別配分する。現時点では追加経路を自動実装しない。

## 結果で変える次判断

CPU最小prototypeを165で即優先する判断を支持する。151の5固定入力sameK32で入力bits/合法Action/P2反転・壁/飛越実着地/history/ply/key/value符号/採用手/訪問を必要範囲で比較する。native float差やtie-order差を構造障害と区別する。成立なら既165の条件付き8pair16診断で起動・NN・輸送・記録・停止の総費とWDLを保存し、native正式計画と有効教師行/secの費用へ進む。機構不一致なら新基盤を増設せずwrapper/数値/clockの最小修復へ。依存不足ならtyped不成立とし、未確認を実行済みにしない。159のCPU並列成績を新backendへそのまま移さない。

GPUはCPU経路の開始gateにしない。将来別配分の最小測定は、担当experimentのprivate範囲・固定同モデル・CPU対実GPUの単局面warm1+steady8、初期化/転送/queue/結果取得込み、数値parity、VRAM6GiB/job30min内、全attempt/typed fault/回収を保存する。現在ORTGPU provider不足ならsession作成/対応operatorが阻害点となる。既PyTorch CUDA buildのみからONNX実行対応や速度を埋めない。batch8は固定batch1 graphが対応するかを先に確認し、不対応なら欠測とする。8回のbatch1は真batch8ではない。単leaf latency改善と多数selfplay/batch throughput改善を分け、成立・無差/悪化・不成立ならそれぞれGPU追加候補/CPU維持/最小環境測定案へ。今回このGPU測定・取得・設定変更は開始していない。

旧browser600pair/1200gameのNI計画は保存し、新nativeの参照/backend/clock/資源/分布/固定標本を結果前に別定義する。16診断・教師・toy5行を独立正式holdoutへ付替えない。162 pipeline入口成立は本PV構造/大量selfplay/独立arena/棋力や全学習基盤readyを意味しない。Sigma同等・NNUE最高棋力は未達のまま。

## 費用・停止・再現

今回NN/game/build/train/GPU/modelsession/download/install/envupdate/再委譲0。CPU番号0・1logical、RAM512MiB/guard448MiB。ORT metadata import peak49460KiB・0.174695sでありモデル初期化を含まない。新保持上限128KiBとGit/index/metadata forecastを旧combined14498727Bへ保守加算し14629799B<14MiB、16MiB既予約内、旧未知保持減額0/追加予約0。private全tree indexを作らずfiles-only tree/CASで自域だけ保存する。

読み取り失敗は推測path2件不存在、shell python command不存在(exit127)を保存し、python3へ静的修復した。科学失敗/NN不一致へ変換しない。codecは1command成功、provider metadataは1command成功。前162 source/子exact identity不在は受領時確認、今回短い子は同期waitで回収。現在不在を全期間/自然全終了保証としない。自己科学source停止・現在資源/全欠測/Git復元はstop.json/restoration.json、保存版はGit-final.json参照。受入れはcoordinator、goal/他者close0。

再現は既環境でprovider-metadata.json記載command（モデルsessionなし）、taskset -c 0 python3 -B tools/ai-sigma-native-route-choice/codec.py。これはNN0管理診断の再現でありnative対局の再現commandではない。必要小正本をGit streamで照合し、Beads backup sync後に既App Serverへ返す。
